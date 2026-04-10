"""SQLite storage layer for changoctl.

Three tables: inventory (current stock), consumption_log (append-only history),
quotes (curated Chango lines). Schema auto-created on first connect.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import DB_PATH, VALID_ITEMS


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open and initialise the changoctl database."""
    path = db_path if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL UNIQUE,
            stock INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consumption_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            mood TEXT,
            timestamp TEXT NOT NULL,
            session_context TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_consumption_timestamp
        ON consumption_log(timestamp)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            source_session TEXT,
            source_module TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    # Seed inventory rows if empty
    count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if count == 0:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for item in sorted(VALID_ITEMS):
            conn.execute(
                "INSERT INTO inventory (item, stock, updated_at) VALUES (?, 0, ?)",
                (item, now),
            )
        conn.commit()
    return conn


def _validate_item(item: str) -> None:
    if item not in VALID_ITEMS:
        raise ValueError(f"invalid item: {item!r} (must be one of {VALID_ITEMS})")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_inventory(db_path: Optional[Path] = None) -> list[dict]:
    """Return all inventory rows."""
    conn = _connect(db_path)
    rows = conn.execute("SELECT * FROM inventory ORDER BY item").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stock(item: str, db_path: Optional[Path] = None) -> int:
    """Return current stock for a single item."""
    _validate_item(item)
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT stock FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    conn.close()
    return row["stock"] if row else 0


def restock(
    item: str, quantity: int = 1, db_path: Optional[Path] = None
) -> dict:
    """Add stock. Returns updated inventory row."""
    _validate_item(item)
    now = _now()
    conn = _connect(db_path)
    conn.execute(
        "UPDATE inventory SET stock = stock + ?, updated_at = ? WHERE item = ?",
        (quantity, now, item),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    conn.close()
    return dict(row)


def consume(
    item: str,
    mood: Optional[str] = None,
    session_context: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Consume one unit. Logs even when out of stock (quantity=0).

    Returns dict with keys: stock, out_of_stock, log_entry.
    """
    _validate_item(item)
    now = _now()
    conn = _connect(db_path)

    row = conn.execute(
        "SELECT stock FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    current_stock = row["stock"] if row else 0
    out_of_stock = current_stock <= 0

    if not out_of_stock:
        conn.execute(
            "UPDATE inventory SET stock = stock - 1, updated_at = ? WHERE item = ?",
            (now, item),
        )
        quantity = 1
    else:
        quantity = 0

    conn.execute(
        "INSERT INTO consumption_log (item, quantity, mood, timestamp, session_context) "
        "VALUES (?, ?, ?, ?, ?)",
        (item, quantity, mood, now, session_context),
    )
    conn.commit()

    new_stock_row = conn.execute(
        "SELECT stock FROM inventory WHERE item = ?", (item,)
    ).fetchone()
    log_row = conn.execute(
        "SELECT * FROM consumption_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    return {
        "stock": new_stock_row["stock"],
        "out_of_stock": out_of_stock,
        "log_entry": dict(log_row),
    }


def add_quote(
    text: str,
    category: str,
    source_session: Optional[str] = None,
    source_module: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict:
    """Add a curated quote. Returns created row."""
    from .config import VALID_CATEGORIES

    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"invalid category: {category!r} (must be one of {VALID_CATEGORIES})"
        )

    now = _now()
    conn = _connect(db_path)
    cur = conn.execute(
        "INSERT INTO quotes (text, category, source_session, source_module, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (text, category, source_session, source_module, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM quotes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return dict(row)


def list_quotes(
    category: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """List quotes, optionally filtered by category. Newest first."""
    conn = _connect(db_path)
    if category:
        rows = conn.execute(
            "SELECT * FROM quotes WHERE category = ? ORDER BY created_at DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM quotes ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def random_quote(
    category: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """Return a random quote, optionally filtered by category. None if empty."""
    conn = _connect(db_path)
    if category:
        row = conn.execute(
            "SELECT * FROM quotes WHERE category = ? ORDER BY RANDOM() LIMIT 1",
            (category,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_consumption_history(
    item: Optional[str] = None,
    days: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    """List consumption log entries, newest first."""
    from datetime import timedelta

    conn = _connect(db_path)
    query = "SELECT * FROM consumption_log"
    params: list = []
    clauses: list[str] = []

    if item:
        clauses.append("item = ?")
        params.append(item)

    if days is not None:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        clauses.append("timestamp >= ?")
        params.append(cutoff)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_quotes(db_path: Optional[Path] = None) -> int:
    """Total number of quotes."""
    conn = _connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    conn.close()
    return count
