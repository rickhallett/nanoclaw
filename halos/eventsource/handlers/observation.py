"""Observation domain projection — external session monitoring."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class ObservationProjectionHandler(ProjectionHandler):
    """Handles observation.* events → local observation_messages table."""

    tables = ["observation_messages"]

    def handles(self) -> list[str]:
        return [
            "observation.aura.user",
            "observation.aura.assistant",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS observation_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                UNIQUE(source_event_id)
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_obs_session "
            "ON observation_messages(session_id, timestamp)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload
        db.execute(
            """
            INSERT OR IGNORE INTO observation_messages
                (id, session_id, role, content, timestamp, source_event_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                p.get("session_id", ""),
                p.get("role", ""),
                p.get("content", ""),
                event.timestamp,
                event.id,
            ),
        )
