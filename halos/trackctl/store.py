"""SQLite storage layer for trackctl domains.

Each domain gets its own .db file in the store/ directory.
Schema: entries(id INTEGER PRIMARY KEY, timestamp TEXT, duration_mins INTEGER, notes TEXT)
The schema is intentionally simple — all domains share the same table structure.
Domain-specific fields beyond the core set can be added via the notes column as JSON.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _store_dir() -> Path:
    """Resolve the store/ directory relative to the repo root."""
    # Walk up from this file to find the repo root (where store/ lives)
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "store").is_dir():
            return ancestor / "store"
    # Fallback: assume cwd
    return Path.cwd() / "store"


def db_path(domain: str) -> Path:
    """Return the path to a domain's SQLite database."""
    return _store_dir() / f"track_{domain}.db"


def _connect(domain: str) -> sqlite3.Connection:
    """Open (and initialize if needed) a domain database."""
    path = db_path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            duration_mins INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def add_entry(
    domain: str,
    duration_mins: int,
    notes: str = "",
    timestamp: Optional[str] = None,
) -> dict:
    """Add a new entry. Returns the created row as a dict.

    Args:
        domain: Domain name (e.g. 'zazen').
        duration_mins: Duration in minutes. Must be >= 0.
        notes: Optional freeform text.
        timestamp: ISO 8601 timestamp. Defaults to now (UTC).

    Returns:
        Dict with id, timestamp, duration_mins, notes.

    Raises:
        ValueError: If duration_mins is negative or domain is empty.
    """
    if not domain:
        raise ValueError("domain must not be empty")
    if duration_mins < 0:
        raise ValueError(f"duration_mins must be >= 0, got {duration_mins}")

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = _connect(domain)
    cur = conn.execute(
        "INSERT INTO entries (timestamp, duration_mins, notes) VALUES (?, ?, ?)",
        (timestamp, duration_mins, notes),
    )
    conn.commit()
    row_id = cur.lastrowid

    row = conn.execute("SELECT * FROM entries WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return dict(row)


def list_entries(domain: str, days: Optional[int] = None) -> list[dict]:
    """List entries, optionally limited to the last N days.

    Args:
        domain: Domain name.
        days: If set, only return entries from the last N days.

    Returns:
        List of entry dicts, newest first.
    """
    conn = _connect(domain)
    if days is not None and days > 0:
        # Filter by date — compare date portion of timestamp
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM entries WHERE timestamp >= ? ORDER BY timestamp DESC",
            (cutoff,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM entries ORDER BY timestamp DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_entry(domain: str, entry_id: int) -> bool:
    """Delete an entry by ID. Returns True if a row was deleted."""
    conn = _connect(domain)
    cur = conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def edit_entry(
    domain: str,
    entry_id: int,
    duration_mins: Optional[int] = None,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Edit an existing entry. Returns updated row or None if not found."""
    conn = _connect(domain)
    row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        conn.close()
        return None

    new_dur = duration_mins if duration_mins is not None else row["duration_mins"]
    new_notes = notes if notes is not None else row["notes"]

    conn.execute(
        "UPDATE entries SET duration_mins = ?, notes = ? WHERE id = ?",
        (new_dur, new_notes, entry_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    conn.close()
    return dict(updated) if updated else None


def daily_totals(domain: str, days: Optional[int] = None) -> dict[str, int]:
    """Return {date_str: total_minutes} for each day with entries.

    Args:
        domain: Domain name.
        days: If set, only include the last N days.

    Returns:
        Dict mapping 'YYYY-MM-DD' to total minutes that day.
    """
    conn = _connect(domain)
    query = "SELECT timestamp, duration_mins FROM entries ORDER BY timestamp"
    rows = conn.execute(query).fetchall()
    conn.close()

    totals: dict[str, int] = {}
    for r in rows:
        date_str = r["timestamp"][:10]  # YYYY-MM-DD
        totals[date_str] = totals.get(date_str, 0) + r["duration_mins"]

    if days is not None and days > 0:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        totals = {d: m for d, m in totals.items() if d >= cutoff}

    return totals
