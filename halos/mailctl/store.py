"""SQLite storage layer for mailctl.

Single database: store/mail.db
Tables:
  - filters: Gmail filters created by mailctl (source of truth for what we manage)
  - actions: Audit log of all mailctl operations (create filter, delete filter, audit run)
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _store_dir() -> Path:
    """Resolve the store/ directory relative to the repo root."""
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "store").is_dir():
            return ancestor / "store"
    return Path.cwd() / "store"


def db_path() -> Path:
    return _store_dir() / "mail.db"


def _connect() -> sqlite3.Connection:
    """Open (and initialize if needed) the mail database."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_filter_id TEXT NOT NULL UNIQUE,
            sender TEXT NOT NULL,
            criteria TEXT NOT NULL,
            filter_action TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            sender TEXT,
            details TEXT
        )
    """)
    conn.commit()
    return conn


def add_filter(
    gmail_filter_id: str,
    sender: str,
    criteria: dict,
    filter_action: dict,
    reason: Optional[str] = None,
) -> dict:
    """Record a Gmail filter created by mailctl."""
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO filters (gmail_filter_id, sender, criteria, filter_action, reason, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (gmail_filter_id, sender, json.dumps(criteria), json.dumps(filter_action), reason, now),
    )
    conn.commit()
    log_action("create_filter", sender, {"gmail_filter_id": gmail_filter_id, "reason": reason})
    row = conn.execute(
        "SELECT * FROM filters WHERE gmail_filter_id = ?", (gmail_filter_id,)
    ).fetchone()
    conn.close()
    return dict(row)


def list_filters() -> list[dict]:
    """Return all managed filters."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM filters ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_filter(gmail_filter_id: str) -> bool:
    """Remove a filter record. Returns True if found and deleted."""
    conn = _connect()
    cursor = conn.execute("DELETE FROM filters WHERE gmail_filter_id = ?", (gmail_filter_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    if deleted:
        log_action("delete_filter", None, {"gmail_filter_id": gmail_filter_id})
    conn.close()
    return deleted


def log_action(action: str, sender: Optional[str] = None, details: Optional[dict] = None) -> None:
    """Append to the actions audit log."""
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO actions (timestamp, action, sender, details) VALUES (?, ?, ?, ?)",
        (now, action, sender, json.dumps(details) if details else None),
    )
    conn.commit()
    conn.close()


def list_actions(limit: int = 50) -> list[dict]:
    """Return recent actions."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM actions ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_filter_by_sender(sender: str) -> Optional[dict]:
    """Look up a filter by sender address."""
    conn = _connect()
    row = conn.execute("SELECT * FROM filters WHERE sender = ?", (sender,)).fetchone()
    conn.close()
    return dict(row) if row else None
