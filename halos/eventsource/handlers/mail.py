"""Mail triage projection — email classification and action log."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class MailTriageHandler(ProjectionHandler):
    """Handles mail.triage.executed events → triage action log."""

    tables = ["mail_triage"]

    def handles(self) -> list[str]:
        return ["mail.triage.executed"]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS mail_triage (
                source_event_id TEXT PRIMARY KEY,
                sender TEXT NOT NULL DEFAULT '',
                subject TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                label TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_mail_triage_ts "
            "ON mail_triage(timestamp DESC)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload
        db.execute(
            """
            INSERT OR IGNORE INTO mail_triage
                (source_event_id, sender, subject, action, reason, label, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                p.get("sender", ""),
                p.get("subject", ""),
                p.get("action", ""),
                p.get("reason", ""),
                p.get("label"),
                event.timestamp,
            ),
        )
