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
