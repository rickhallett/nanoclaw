"""Log line parsers for pino pretty-print, JSON, and plain text formats."""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class LogEntry:
    timestamp: Optional[str] = None
    level: str = "info"
    source: str = ""
    message: str = ""
    data: dict = None
    instance: str = ""       # fleet instance name (e.g., "ben", "dad", "prime")
    channel: str = ""        # log channel: "pm2", "container", "sqlite", "halos"

    def __post_init__(self):
        if self.data is None:
            self.data = {}


# Pino pretty-print format:
# [16:03:37.233] INFO (30081): Database initialized
# With ANSI codes: [16:03:37.233] \x1b[32mINFO\x1b[39m (30081): \x1b[36mDatabase initialized\x1b[39m
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_PINO_RE = re.compile(
    r"^\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s+"
    r"(\w+)\s+"
    r"\((\d+)\):\s+"
    r"(.+)$"
)
# Pino key-value continuation line: "    key: value"
_PINO_KV_RE = re.compile(r"^\s{4}(\w+):\s+(.+)$")

# Pino JSON format (when piped without pretty-print)
# {"level":30,"time":1710000000000,"msg":"Database initialized","pid":30081}
_PINO_LEVELS = {10: "trace", 20: "debug", 30: "info", 40: "warn", 50: "error", 60: "fatal"}

# halos structured format (YAML one-liner or JSON)
_HALOS_LEVELS = {"debug", "info", "warn", "error"}


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)


def parse_pino_pretty(line: str) -> Optional[LogEntry]:
    """Parse a pino pretty-printed log line."""
    clean = strip_ansi(line.rstrip())
    m = _PINO_RE.match(clean)
    if not m:
        return None
    timestamp, level, pid, message = m.groups()
    return LogEntry(
        timestamp=timestamp,
        level=level.lower(),
        source="nanoclaw",
        message=message.strip(),
        data={"pid": int(pid)},
    )


def parse_pino_json(line: str) -> Optional[LogEntry]:
    """Parse a pino JSON log line."""
    try:
        obj = json.loads(line.strip())
    except (json.JSONDecodeError, ValueError):
        return None

    if "level" not in obj and "msg" not in obj:
        return None

    level_num = obj.get("level", 30)
    level = _PINO_LEVELS.get(level_num, "info") if isinstance(level_num, int) else str(level_num)

    ts = obj.get("time")
    timestamp = None
    if isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            timestamp = dt.strftime("%H:%M:%S.%f")[:-3]
        except (OSError, ValueError):
            pass
    elif isinstance(ts, str):
        timestamp = ts

    # Extract known fields, put rest in data
    known = {"level", "time", "msg", "pid", "hostname", "name"}
    data = {k: v for k, v in obj.items() if k not in known}
    if "pid" in obj:
        data["pid"] = obj["pid"]

    return LogEntry(
        timestamp=timestamp,
        level=level,
        source=obj.get("name", "nanoclaw"),
        message=obj.get("msg", ""),
        data=data,
    )


def parse_halos_structured(line: str) -> Optional[LogEntry]:
    """Parse a halos structured log line (JSON or simple YAML-ish)."""
    stripped = line.strip()
    if not stripped:
        return None

    # Try JSON first
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict) and "event" in obj:
            return LogEntry(
                timestamp=obj.get("ts", ""),
                level=obj.get("level", "info"),
                source=obj.get("source", ""),
                message=obj.get("event", ""),
                data=obj.get("data", {}),
            )
    except (json.JSONDecodeError, ValueError):
        pass

    # Try YAML
    try:
        import yaml
        obj = yaml.safe_load(stripped)
        if isinstance(obj, dict) and "event" in obj:
            return LogEntry(
                timestamp=obj.get("ts", ""),
                level=obj.get("level", "info"),
                source=obj.get("source", ""),
                message=obj.get("event", ""),
                data=obj.get("data", {}),
            )
    except Exception:
        pass

    return None


def parse_plain(line: str) -> Optional[LogEntry]:
    """Parse a plain text log line — just wraps the raw text."""
    stripped = line.rstrip()
    if not stripped:
        return None
    return LogEntry(message=stripped)


def parse_line(line: str, fmt: str = "pino") -> Optional[LogEntry]:
    """Parse a log line according to the specified format.

    Falls back through parsers: pino pretty -> pino json -> halos structured -> plain.
    """
    if fmt == "pino":
        entry = parse_pino_pretty(line)
        if entry:
            return entry
        entry = parse_pino_json(line)
        if entry:
            return entry

    if fmt == "jsonl":
        entry = parse_pino_json(line)
        if entry:
            return entry
        entry = parse_halos_structured(line)
        if entry:
            return entry

    # halos structured logs
    entry = parse_halos_structured(line)
    if entry:
        return entry

    # Final fallback: plain text (skip blank lines and continuation lines for pino)
    return parse_plain(line)


def format_entry(entry: LogEntry, show_instance: bool = False) -> str:
    """Format a LogEntry for human-readable display."""
    parts = []
    if entry.timestamp:
        parts.append(f"[{entry.timestamp}]")
    if show_instance and entry.instance:
        parts.append(f"{entry.instance:<10}")
    if entry.channel:
        parts.append(f"{entry.channel:<10}")
    parts.append(f"{entry.level.upper():5s}")
    if entry.source and not show_instance:
        parts.append(f"({entry.source})")
    parts.append(entry.message)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Container log parser
# ---------------------------------------------------------------------------

def parse_container_log(filepath: str, instance: str = "") -> list[LogEntry]:
    """Parse a nanoclaw container log file (=== section format).

    Extracts agent-runner stderr lines and NANOCLAW_OUTPUT results.
    """
    from pathlib import Path

    p = Path(filepath)
    if not p.exists():
        return []

    content = p.read_text(errors="replace")
    entries = []

    # Extract timestamp from header
    ts = ""
    for line in content.splitlines()[:5]:
        if line.startswith("Timestamp:"):
            ts = line.split(":", 1)[1].strip()
            break

    # Parse stderr (agent-runner lines)
    in_stderr = False
    for line in content.splitlines():
        if line.startswith("=== Stderr ==="):
            in_stderr = True
            continue
        if line.startswith("=== ") and in_stderr:
            in_stderr = False
            continue
        if in_stderr and line.strip():
            level = "error" if "error" in line.lower() else "info"
            entries.append(LogEntry(
                timestamp=ts,
                level=level,
                source="agent-runner",
                message=strip_ansi(line.strip()),
                instance=instance,
                channel="container",
            ))

    # Parse stdout for results
    for chunk in content.split("---NANOCLAW_OUTPUT_START---")[1:]:
        end = chunk.find("---NANOCLAW_OUTPUT_END---")
        if end > 0:
            chunk = chunk[:end].strip()
        try:
            obj = json.loads(chunk)
            result = obj.get("result", "")
            status = obj.get("status", "")
            if result:
                entries.append(LogEntry(
                    timestamp=ts,
                    level="error" if status == "error" else "info",
                    source="agent",
                    message=f"[{status}] {str(result)[:200]}",
                    instance=instance,
                    channel="container",
                ))
        except (json.JSONDecodeError, KeyError):
            pass

    return entries


# ---------------------------------------------------------------------------
# SQLite message reader
# ---------------------------------------------------------------------------

def read_sqlite_messages(
    db_path: str,
    instance: str = "",
    limit: int = 50,
    since: str = "",
) -> list[LogEntry]:
    """Read messages from a nanoclaw SQLite database as LogEntries."""
    import sqlite3
    from pathlib import Path

    p = Path(db_path)
    if not p.exists():
        return []

    try:
        conn = sqlite3.connect(str(p))
        query = "SELECT sender_name, content, timestamp, is_from_me FROM messages"
        params = []
        if since:
            query += " WHERE timestamp > ?"
            params.append(since)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()
    except Exception:
        return []

    entries = []
    for sender, content, ts, is_from_me in reversed(rows):
        direction = "OUT" if is_from_me else "IN"
        entries.append(LogEntry(
            timestamp=ts,
            level="info",
            source=f"msg/{direction}",
            message=f"{sender}: {content[:200]}",
            instance=instance,
            channel="sqlite",
        ))
    return entries
