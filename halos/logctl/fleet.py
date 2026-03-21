"""Fleet-aware log discovery — finds all log sources across fleet instances."""

import heapq
from pathlib import Path
from typing import Optional

from .parser import (
    LogEntry,
    parse_container_log,
    read_sqlite_messages,
    strip_ansi,
    parse_line,
)
from .search import read_log_tail, read_log_file


def _fleet_manifest() -> list[dict]:
    """Load fleet instances from FLEET.yaml."""
    try:
        from halos.halctl.config import load_fleet_manifest
        manifest = load_fleet_manifest()
        return [i for i in manifest.get("instances", []) if i.get("status") == "active"]
    except Exception:
        return []


def _pm2_log_path(name: str) -> Path:
    """Return pm2 stdout log path for an instance."""
    return Path.home() / ".pm2" / "logs" / f"microhal-{name}-out.log"


def _container_logs(deploy_path: Path, limit: int = 5) -> list[Path]:
    """Return the most recent container log files."""
    logs_dir = deploy_path / "groups" / "telegram_main" / "logs"
    if not logs_dir.exists():
        return []
    return sorted(logs_dir.glob("container-*.log"), reverse=True)[:limit]


def _db_path(deploy_path: Path) -> Path:
    return deploy_path / "store" / "messages.db"


def discover_sources(
    instance_filter: Optional[str] = None,
    include_prime: bool = True,
) -> list[dict]:
    """Discover all log sources across the fleet.

    Returns list of dicts: {instance, channel, path, format}
    """
    sources = []

    # Prime
    if include_prime and not instance_filter:
        prime_pm2 = Path.home() / ".pm2" / "logs" / "nanoclaw-out.log"
        if prime_pm2.exists():
            sources.append({
                "instance": "prime",
                "channel": "pm2",
                "path": str(prime_pm2),
                "format": "pino",
            })

    # Fleet instances
    for inst in _fleet_manifest():
        name = inst["name"]
        if instance_filter and name != instance_filter:
            continue

        deploy = Path(inst["path"])
        if not deploy.exists():
            continue

        # pm2 log
        pm2 = _pm2_log_path(name)
        if pm2.exists():
            sources.append({
                "instance": name,
                "channel": "pm2",
                "path": str(pm2),
                "format": "pino",
            })

        # Container logs (most recent)
        for cl in _container_logs(deploy, limit=3):
            sources.append({
                "instance": name,
                "channel": "container",
                "path": str(cl),
                "format": "container",
            })

        # SQLite
        db = _db_path(deploy)
        if db.exists():
            sources.append({
                "instance": name,
                "channel": "sqlite",
                "path": str(db),
                "format": "sqlite",
            })

    return sources


def read_fleet_conversations(
    instance_filter: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Read user→agent message pairs from fleet SQLite databases.

    Returns list of dicts sorted by timestamp:
    {instance, timestamp, user_name, user_message, agent_response}
    """
    import sqlite3

    pairs: list[dict] = []
    import re
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    agent_output_re = re.compile(r"Agent output: (.+)")

    for inst in _fleet_manifest():
        name = inst["name"]
        if instance_filter and name != instance_filter:
            continue

        deploy = Path(inst["path"])
        db = _db_path(deploy)
        if not db.exists():
            continue

        # User messages from SQLite
        try:
            import sqlite3
            conn = sqlite3.connect(str(db))
            user_msgs = conn.execute(
                """SELECT sender_name, content, timestamp FROM messages
                   WHERE is_from_me = 0 ORDER BY timestamp ASC"""
            ).fetchall()
            conn.close()
        except Exception:
            continue

        # Agent responses from pm2 logs — extract "Telegram message sent" entries
        # paired with preceding "Agent output:" lines. Use the "message sent"
        # timestamp as the canonical agent response time.
        agent_responses: list[tuple[str, str]] = []  # (HH:MM:SS.mmm, text)
        pm2 = _pm2_log_path(name)
        if pm2.exists():
            try:
                timestamp_re = re.compile(r"^\[(\d{2}:\d{2}:\d{2}\.\d{3})\]")
                lines = pm2.read_text(errors="replace").splitlines()
                last_output = ""
                for line in lines:
                    clean = ansi_re.sub("", line)
                    m = agent_output_re.search(clean)
                    if m:
                        last_output = m.group(1).strip()
                    # "Telegram message sent" confirms delivery — pair with last output
                    if "Telegram message sent" in clean and last_output:
                        ts_match = timestamp_re.match(clean)
                        ts = ts_match.group(1) if ts_match else ""
                        if ts:
                            agent_responses.append((ts, last_output))
                        last_output = ""
            except Exception:
                pass

        # Pair user messages with agent responses.
        # pm2 timestamps are HH:MM:SS.mmm (no date). To infer dates we:
        #   1. Anchor the LAST entry's date to the log file's mtime
        #   2. Walk backwards through timestamps; when time jumps forward
        #      by >6h it means we crossed midnight, so decrement the date.
        # This correctly handles logs spanning multiple days.
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        # OBS.LOG.01: Infer per-entry dates by anchoring to mtime and
        # detecting midnight rollover, instead of assigning a single date
        # to all entries.
        anchor_date = now.date()
        if pm2.exists():
            try:
                mtime = datetime.fromtimestamp(pm2.stat().st_mtime, tz=timezone.utc)
                anchor_date = mtime.date()
            except Exception:
                pass

        def _assign_dates(
            timestamps: list[str], anchor: "datetime.date"  # noqa: F821
        ) -> list[str]:
            """Assign ISO dates to HH:MM:SS.mmm timestamps via rollover detection.

            Walk backwards from the last entry (anchored to `anchor` date).
            When the time jumps forward by >6h compared to the next entry,
            a midnight boundary was crossed, so decrement the date.
            """
            if not timestamps:
                return []
            from datetime import date as _date  # noqa: F811
            current_date = anchor
            dates: list[str] = [current_date.isoformat() + "T"] * len(timestamps)
            dates[-1] = current_date.isoformat() + "T"
            for i in range(len(timestamps) - 2, -1, -1):
                # Compare HH portion: if this entry's time is much later
                # than the next entry's time, we crossed midnight between them
                try:
                    h_cur = int(timestamps[i][:2])
                    h_next = int(timestamps[i + 1][:2])
                    if h_cur - h_next > 6:
                        current_date -= timedelta(days=1)
                except (ValueError, IndexError):
                    pass
                dates[i] = current_date.isoformat() + "T"
            return dates

        # Assign dates to agent response timestamps
        agent_hms = [ts for ts, _ in agent_responses]
        agent_dates = _assign_dates(agent_hms, anchor_date)

        def _normalise(ts: str) -> str:
            """Normalise any timestamp to comparable ISO-ish string."""
            if "T" in ts:
                return ts[:23]  # 2026-03-18T11:30:53.000
            # Fallback for bare HH:MM:SS — shouldn't happen after date assignment
            return f"{anchor_date.isoformat()}T{ts[:12]}"

        # Build ordered list of agent responses with full timestamps
        agent_iso: list[tuple[str, str]] = []
        for i, (agent_ts, agent_text) in enumerate(agent_responses):
            full_ts = f"{agent_dates[i]}{agent_ts}Z"
            agent_iso.append((full_ts, agent_text))

        # OBS.LOG.01: For each agent response, find the last user message
        # before it. Allow multiple agent responses per user message by
        # concatenating them instead of dropping later ones.
        response_for: dict[int, str] = {}
        for agent_full_ts, agent_text in agent_iso:
            a_norm = _normalise(agent_full_ts)
            best_idx = None
            for i, (sender, content, ts) in enumerate(user_msgs):
                u_norm = _normalise(ts)
                if u_norm <= a_norm:
                    best_idx = i
                else:
                    break
            if best_idx is not None:
                if best_idx in response_for:
                    # Append multi-part responses instead of dropping them
                    response_for[best_idx] += "\n---\n" + agent_text
                else:
                    response_for[best_idx] = agent_text

        for i, (sender, content, ts) in enumerate(user_msgs):
            pair = {
                "instance": name,
                "timestamp": ts,
                "user_name": sender,
                "user_message": content,
                "agent_response": response_for.get(i, ""),
            }
            pairs.append(pair)

    # Sort all pairs by timestamp across instances, take most recent
    pairs.sort(key=lambda p: p["timestamp"])
    return pairs[-limit:]


def read_fleet_entries(
    instance_filter: Optional[str] = None,
    n: int = 50,
    include_prime: bool = True,
) -> list[LogEntry]:
    """Read log entries from all fleet sources, sorted by timestamp."""
    sources = discover_sources(instance_filter, include_prime)
    all_entries: list[LogEntry] = []

    for src in sources:
        name = src["instance"]
        fmt = src["format"]
        path = src["path"]

        if fmt == "pino":
            entries = read_log_tail(path, n=n, fmt="pino")
            for e in entries:
                e.instance = name
                e.channel = "pm2"
            all_entries.extend(entries)

        elif fmt == "container":
            entries = parse_container_log(path, instance=name)
            all_entries.extend(entries)

        elif fmt == "sqlite":
            entries = read_sqlite_messages(path, instance=name, limit=n)
            all_entries.extend(entries)

    # Sort by timestamp (best effort — mixed formats)
    def _sort_key(e: LogEntry) -> str:
        return e.timestamp or ""

    all_entries.sort(key=_sort_key)
    return all_entries


def trace_event(
    seed_timestamp: str,
    instance_filter: Optional[str] = None,
    window_seconds: float = 5.0,
) -> list[LogEntry]:
    """Given a timestamp, find all related events within the correlation window.

    Reads all fleet sources and returns entries within ±window_seconds of
    the seed timestamp.
    """
    from datetime import datetime, timedelta, timezone

    # Parse seed timestamp
    seed_dt = None
    try:
        if "T" in seed_timestamp:
            seed_dt = datetime.fromisoformat(seed_timestamp.replace("Z", "+00:00"))
        else:
            # HH:MM:SS.mmm — assume today
            t = datetime.strptime(seed_timestamp, "%H:%M:%S.%f").time()
            seed_dt = datetime.combine(datetime.now(timezone.utc).date(), t, tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass

    if not seed_dt:
        return []

    window = timedelta(seconds=window_seconds)
    low = seed_dt - window
    high = seed_dt + window

    # Read everything (generous n for trace)
    all_entries = read_fleet_entries(instance_filter, n=200, include_prime=True)

    # Filter to window
    correlated = []
    for e in all_entries:
        if not e.timestamp:
            continue
        try:
            if "T" in e.timestamp:
                dt = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
            else:
                t = datetime.strptime(e.timestamp.split(".")[0], "%H:%M:%S").time()
                dt = datetime.combine(seed_dt.date(), t, tzinfo=timezone.utc)

            if low <= dt <= high:
                correlated.append(e)
        except (ValueError, TypeError):
            continue

    correlated.sort(key=lambda e: e.timestamp or "")
    return correlated
