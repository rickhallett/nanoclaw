"""Journal domain projection."""

from __future__ import annotations

import json
import sqlite3

from ..core import Event, ProjectionHandler


class JournalProjectionHandler(ProjectionHandler):
    """Handles journal.* events → local journal_entries table."""

    tables = ["journal_entries"]

    def handles(self) -> list[str]:
        return ["journal.entry.added"]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id INTEGER PRIMARY KEY,
                raw_text TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL DEFAULT 'text',
                mood TEXT,
                energy TEXT,
                timestamp TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                UNIQUE(source_event_id)
            )
        """)

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload

        if event.type == "journal.entry.added":
            db.execute(
                """
                INSERT OR IGNORE INTO journal_entries
                    (entry_id, raw_text, tags, source, mood, energy, timestamp, source_event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    p["entry_id"],
                    p.get("raw_text", ""),
                    json.dumps(p.get("tags", [])),
                    p.get("source", "text"),
                    p.get("mood"),
                    p.get("energy"),
                    event.timestamp,
                    event.id,
                ),
            )
