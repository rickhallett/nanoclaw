"""Query the Halostream projection for historical advisor messages.

Reads from the local SQLite projection database (same source as
halo-telephony) and returns structured results.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from halos.common.paths import store_dir


def _connect() -> sqlite3.Connection | None:
    """Open the projection DB. Returns None if unavailable."""
    db_path = store_dir() / "projection.db"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def list_messages(
    *,
    advisor: str | None = None,
    direction: str | None = None,
    days: int = 1,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return recent advisor messages from the projection."""
    conn = _connect()
    if conn is None:
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    query = (
        "SELECT advisor, direction, message_text, timestamp, platform, session_id "
        "FROM advisor_messages WHERE timestamp >= ? "
    )
    params: list[Any] = [cutoff]

    if advisor:
        query += "AND advisor = ? "
        params.append(advisor)
    if direction:
        query += "AND direction = ? "
        params.append(direction)

    query += "ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def summary(
    *,
    advisor: str | None = None,
    days: int = 1,
) -> list[dict[str, Any]]:
    """Per-advisor message counts."""
    conn = _connect()
    if conn is None:
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    query = (
        "SELECT advisor, direction, COUNT(*) as count "
        "FROM advisor_messages WHERE timestamp >= ? "
    )
    params: list[Any] = [cutoff]
    if advisor:
        query += "AND advisor = ? "
        params.append(advisor)
    query += "GROUP BY advisor, direction ORDER BY advisor, direction"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def print_messages(messages: list[dict], json_out: bool = False) -> None:
    """Print messages to stdout."""
    if not messages:
        print("No messages found.")
        return

    if json_out:
        print(json.dumps(messages, indent=2))
        return

    for r in reversed(messages):
        ts = (r.get("timestamp") or "")[:16]
        direction = ">>>" if r.get("direction") == "inbound" else "<<<"
        text = (r.get("message_text") or "")[:120]
        print(f"[{ts}] {r.get('advisor', '?'):<12} {direction} {text}")


def print_summary(rows: list[dict], json_out: bool = False) -> None:
    """Print summary to stdout."""
    if not rows:
        print("No messages found.")
        return

    if json_out:
        print(json.dumps(rows, indent=2))
        return

    print(f"{'ADVISOR':<16} {'DIRECTION':<12} {'COUNT':>6}")
    print("-" * 40)
    for r in rows:
        print(f"{r['advisor']:<16} {r['direction']:<12} {r['count']:>6}")
