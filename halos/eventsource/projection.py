"""Projection engine — manages local SQLite read model from event stream."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .core import Event, ProjectionHandler


class ProjectionEngine:
    """Manages the local projection database and event processing.

    The projection is a disposable read model. Kill it, replay from
    the stream, get the same state back. The stream is truth.
    """

    def __init__(self, db_path: Path | str, handlers: list[ProjectionHandler]):
        self._db_path = Path(db_path)
        self._handlers = handlers
        self._handler_map: dict[str, list[ProjectionHandler]] = {}
        self._db: sqlite3.Connection | None = None

        for handler in handlers:
            for event_type in handler.handles():
                self._handler_map.setdefault(event_type, []).append(handler)

    @property
    def db(self) -> sqlite3.Connection:
        if self._db is None:
            raise RuntimeError("ProjectionEngine not open — call open() first")
        return self._db

    def open(self) -> None:
        """Open database and initialize schemas."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self._db_path))
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")

        self._db.execute("""
            CREATE TABLE IF NOT EXISTS _checkpoint (
                consumer TEXT PRIMARY KEY,
                stream_seq INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS _processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
        """)
        self._db.commit()

        for handler in self._handlers:
            handler.init_schema(self._db)
        self._db.commit()

    def last_checkpoint(self, consumer: str) -> int:
        """Return the last processed stream sequence number."""
        row = self.db.execute(
            "SELECT stream_seq FROM _checkpoint WHERE consumer = ?",
            (consumer,),
        ).fetchone()
        return row["stream_seq"] if row else 0

    def apply(self, event: Event, consumer: str) -> bool:
        """Apply a single event to the projection. Returns True if processed."""
        # Idempotency check
        existing = self.db.execute(
            "SELECT 1 FROM _processed_events WHERE event_id = ?",
            (event.id,),
        ).fetchone()
        if existing:
            return False

        # Dispatch to handlers
        handlers = self._handler_map.get(event.type, [])
        for handler in handlers:
            handler.apply(event, self.db)

        # Record processing
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO _processed_events (event_id, processed_at) VALUES (?, ?)",
            (event.id, now),
        )

        # Update checkpoint
        self.db.execute(
            """
            INSERT INTO _checkpoint (consumer, stream_seq, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(consumer) DO UPDATE SET
                stream_seq = excluded.stream_seq,
                updated_at = excluded.updated_at
        """,
            (consumer, event.stream_seq, now),
        )

        self.db.commit()
        return True

    def rebuild(self) -> None:
        """Drop and recreate all projection tables. Preserves nothing."""
        for handler in self._handlers:
            for table in getattr(handler, "tables", []):
                self.db.execute(f"DROP TABLE IF EXISTS {table}")

        for handler in self._handlers:
            handler.init_schema(self.db)
        self.db.commit()

        self.db.execute("DELETE FROM _processed_events")
        self.db.execute("DELETE FROM _checkpoint")
        self.db.commit()

    def close(self) -> None:
        if self._db:
            self._db.close()
            self._db = None
