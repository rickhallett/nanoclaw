"""Track domain projection — movement, zazen, study."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class TrackProjectionHandler(ProjectionHandler):
    """Handles track.* events → local track_entries table."""

    tables = ["track_entries"]

    _LOGGED_TYPES = frozenset(
        {
            "track.movement.logged",
            "track.zazen.logged",
            "track.study.logged",
        }
    )

    def handles(self) -> list[str]:
        return [
            "track.movement.logged",
            "track.zazen.logged",
            "track.study.logged",
            "track.entry.deleted",
            "track.entry.edited",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS track_entries (
                id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration_mins INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                source_event_id TEXT NOT NULL,
                PRIMARY KEY(domain, id),
                UNIQUE(source_event_id)
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_track_domain_ts "
            "ON track_entries(domain, timestamp DESC)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload

        if event.type in self._LOGGED_TYPES:
            db.execute(
                """
                INSERT OR IGNORE INTO track_entries
                    (id, domain, timestamp, duration_mins, notes, source_event_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    p["entry_id"],
                    p["domain"],
                    event.timestamp,
                    p["duration_mins"],
                    p.get("notes", ""),
                    event.id,
                ),
            )

        elif event.type == "track.entry.deleted":
            db.execute(
                "DELETE FROM track_entries WHERE id = ? AND domain = ?",
                (p["entry_id"], p["domain"]),
            )

        elif event.type == "track.entry.edited":
            sets: list[str] = []
            vals: list[object] = []
            if "duration_mins" in p:
                sets.append("duration_mins = ?")
                vals.append(p["duration_mins"])
            if "notes" in p:
                sets.append("notes = ?")
                vals.append(p["notes"])
            if sets:
                vals.extend([p["entry_id"], p["domain"]])
                db.execute(
                    f"UPDATE track_entries SET {', '.join(sets)} "
                    f"WHERE id = ? AND domain = ?",
                    vals,
                )
