"""Fire-and-forget telemetry emitter with ClickHouse sink."""

import json
import os
import sys
import threading
import queue
from datetime import datetime, timezone
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError


# --- Configuration ---

_config = {
    "clickhouse_url": os.environ.get("BATHW_CLICKHOUSE_URL", ""),
    "enabled": True,
    "buffer_size": 100,
    "flush_interval_secs": 5,
}

_buffer: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1000)
_flush_thread: threading.Thread | None = None
_shutdown = threading.Event()


def configure(**kwargs: Any) -> None:
    """Override config at runtime. Call before first emit()."""
    _config.update(kwargs)


def emit(source: str, event: str, data: dict[str, Any] | None = None) -> None:
    """Emit a telemetry event. Non-blocking, fire-and-forget."""
    ts = datetime.now(timezone.utc)
    # ClickHouse DateTime64 format: no T separator, no Z suffix
    ch_ts = ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    entry = {
        "ts": ch_ts,
        "source": source,
        "event": event,
        "data": data or {},
    }

    # Write to stderr as structured JSON
    print(json.dumps({"telemetry": True, **entry}, default=str), file=sys.stderr)

    if not _config["enabled"] or not _config["clickhouse_url"]:
        return

    try:
        _buffer.put_nowait(entry)
    except queue.Full:
        pass

    _ensure_flush_thread()


def _ensure_flush_thread() -> None:
    global _flush_thread
    if _flush_thread is not None and _flush_thread.is_alive():
        return
    _flush_thread = threading.Thread(target=_flush_loop, daemon=True)
    _flush_thread.start()


def _flush_loop() -> None:
    while not _shutdown.is_set():
        _shutdown.wait(timeout=_config["flush_interval_secs"])
        _flush_buffer()


def _flush_buffer() -> None:
    events: list[dict] = []
    while not _buffer.empty():
        try:
            events.append(_buffer.get_nowait())
        except queue.Empty:
            break

    if not events:
        return

    by_table: dict[str, list[dict]] = {}
    for ev in events:
        table = _event_to_table(ev["source"], ev["event"])
        if table:
            row = _transform_row(table, ev)
            by_table.setdefault(table, []).append(row)

    for table, rows in by_table.items():
        _insert_clickhouse(table, rows)


# --- Event routing ---

_TABLE_MAP = {
    ("agentctl", "session_ended"): "agent_sessions",
    ("memctl", "note_created"): "memory_events",
    ("memctl", "note_pruned"): "memory_events",
    ("memctl", "note_archived"): "memory_events",
    ("memctl", "backlink_added"): "memory_events",
    ("memctl", "index_rebuilt"): "memory_events",
    ("memctl", "search_performed"): "memory_events",
    ("memctl", "enrich_proposed"): "memory_events",
    ("memctl", "enrich_accepted"): "memory_events",
}


def _event_to_table(source: str, event: str) -> str:
    return _TABLE_MAP.get((source, event), "raw_events")


# --- Row transforms (event envelope → ClickHouse column layout) ---

# Memory event_type enum values (must match schema)
_MEMORY_EVENT_TYPES = {
    "note_created", "note_pruned", "note_archived",
    "backlink_added", "index_rebuilt", "search_performed",
    "enrich_proposed", "enrich_accepted",
}


def _ch_ts(iso_str: str | None) -> str | None:
    """Convert ISO timestamp to ClickHouse DateTime64 format."""
    if not iso_str:
        return None
    return iso_str.replace("T", " ").replace("Z", "").rstrip("+00:00")


def _transform_row(table: str, ev: dict) -> dict:
    """Transform raw event envelope into a ClickHouse-compatible row."""
    d = ev.get("data", {})

    if table == "raw_events":
        return {
            "ts": ev["ts"],
            "source": ev["source"],
            "event": ev["event"],
            "data": json.dumps(d, default=str),
        }

    if table == "agent_sessions":
        return {
            "session_id": d.get("session_id", ""),
            "started_at": _ch_ts(d.get("started_at")) or ev["ts"],
            "ended_at": _ch_ts(d.get("ended_at")),
            "duration_ms": int(d.get("duration_ms", 0)),
            "group_name": d.get("group_name", ""),
            "channel": d.get("channel", ""),
            "trigger_type": d.get("trigger_type", ""),
            "model": d.get("model", ""),
            "input_tokens": int(d.get("input_tokens", 0)),
            "output_tokens": int(d.get("output_tokens", 0)),
            "cache_read_tokens": int(d.get("cache_read_tokens", 0)),
            "cache_write_tokens": int(d.get("cache_write_tokens", 0)),
            "total_cost_usd": float(d.get("total_cost_usd", 0.0)),
            "tool_calls": int(d.get("tool_calls", 0)),
            "turns": int(d.get("turns", 0)),
            "outcome": d.get("outcome", "success"),
            "intervention": bool(d.get("intervention", False)),
            "intervention_type": d.get("intervention_type"),
            "error_class": d.get("error_class"),
        }

    if table == "memory_events":
        event_type = ev["event"]
        if event_type not in _MEMORY_EVENT_TYPES:
            event_type = "note_created"
        return {
            "event_id": d.get("event_id", d.get("note_id", "")),
            "ts": ev["ts"],
            "event_type": event_type,
            "note_id": d.get("note_id", d.get("id")),
            "note_type": d.get("note_type", d.get("type")),
            "tags": d.get("tags", []),
            "entities": d.get("entities", []),
            "corpus_size": int(d.get("corpus_size", 0)),
            "search_query": d.get("search_query"),
            "search_results": int(d.get("search_results", 0)),
        }

    # Fallback: raw_events format
    return {
        "ts": ev["ts"],
        "source": ev["source"],
        "event": ev["event"],
        "data": json.dumps(d, default=str),
    }


# --- ClickHouse HTTP insert ---

def _insert_clickhouse(table: str, rows: list[dict]) -> None:
    url = _config["clickhouse_url"]
    if not url:
        return

    try:
        body = "\n".join(json.dumps(row, default=str) for row in rows)
        req = Request(
            f"{url}/?query=INSERT+INTO+bathw.{table}+FORMAT+JSONEachRow",
            data=body.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5) as resp:
            resp.read()
    except (URLError, OSError, Exception) as e:
        print(json.dumps({
            "telemetry": True, "level": "warn",
            "event": "clickhouse_insert_failed",
            "table": table, "rows": len(rows),
            "error": str(e)[:200],
        }), file=sys.stderr)


def flush() -> None:
    _flush_buffer()


def shutdown() -> None:
    _shutdown.set()
    _flush_buffer()
