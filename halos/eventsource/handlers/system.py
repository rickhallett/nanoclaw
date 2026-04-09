"""System events projection — advisor lifecycle and error tracking."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class SystemEventHandler(ProjectionHandler):
    """Handles system.* events → fleet lifecycle and error log."""

    tables = ["system_events"]

    def handles(self) -> list[str]:
        return [
            "system.advisor.started",
            "system.advisor.stopped",
            "system.error",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                source_event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                advisor TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                timestamp TEXT NOT NULL
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_system_ts "
            "ON system_events(timestamp DESC)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        import json
        db.execute(
            """
            INSERT OR IGNORE INTO system_events
                (source_event_id, event_type, advisor, payload_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.type,
                event.payload.get("advisor", event.source),
                json.dumps(event.payload),
                event.timestamp,
            ),
        )
