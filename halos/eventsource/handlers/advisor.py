"""Advisor telephony projection — cross-advisor conversation history."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class AdvisorTelephonyHandler(ProjectionHandler):
    """Handles advisor.inbound/outbound events → conversation log."""

    tables = ["advisor_messages"]

    def handles(self) -> list[str]:
        return [
            "advisor.inbound.received",
            "advisor.outbound.sent",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS advisor_messages (
                source_event_id TEXT PRIMARY KEY,
                advisor TEXT NOT NULL,
                direction TEXT NOT NULL,
                platform TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL DEFAULT '',
                message_text TEXT NOT NULL DEFAULT '',
                message_len INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_advisor_msg_ts "
            "ON advisor_messages(advisor, timestamp DESC)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload
        direction = "inbound" if event.type == "advisor.inbound.received" else "outbound"
        db.execute(
            """
            INSERT OR IGNORE INTO advisor_messages
                (source_event_id, advisor, direction, platform, session_id,
                 user_id, message_text, message_len, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                p.get("advisor", event.source),
                direction,
                p.get("platform", ""),
                p.get("session_id", ""),
                p.get("user_id", ""),
                p.get("message_text", ""),
                p.get("message_len", 0),
                event.timestamp,
            ),
        )
