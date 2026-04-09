"""Track domain projection — movement, zazen, study."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class TrackProjectionHandler(ProjectionHandler):
    """Handles track.* events → local track_entries table + per-domain DBs."""

    tables = ["track_entries"]

    def handles(self) -> list[str]:
        return [
            "track.*.logged",
            "track.entry.deleted",
            "track.entry.edited",
        ]

    @staticmethod
    def _is_logged_event(event_type: str) -> bool:
        """Match track.{domain}.logged pattern for any domain."""
        parts = event_type.split(".")
        return len(parts) == 3 and parts[0] == "track" and parts[2] == "logged"

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

        if self._is_logged_event(event.type):
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
            self._write_domain_db(p["domain"], event, p)

        elif event.type == "track.entry.deleted":
            db.execute(
                "DELETE FROM track_entries WHERE id = ? AND domain = ?",
                (p["entry_id"], p["domain"]),
            )
            self._delete_domain_db(p["domain"], p["entry_id"])

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
            self._edit_domain_db(p["domain"], p)

    # --- Per-domain DB writes (trackctl reads these) ---

    @staticmethod
    def _domain_db(domain: str) -> sqlite3.Connection:
        """Open (and init) the per-domain track DB that trackctl reads."""
        from halos.common.paths import store_dir
        path = store_dir() / f"track_{domain}.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
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

    @classmethod
    def _write_domain_db(cls, domain: str, event: Event, p: dict) -> None:
        try:
            conn = cls._domain_db(domain)
            conn.execute(
                "INSERT OR IGNORE INTO entries (id, timestamp, duration_mins, notes) "
                "VALUES (?, ?, ?, ?)",
                (p["entry_id"], event.timestamp, p["duration_mins"], p.get("notes", "")),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Non-fatal — projection.db is the source of truth

    @classmethod
    def _delete_domain_db(cls, domain: str, entry_id: int) -> None:
        try:
            conn = cls._domain_db(domain)
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass

    @classmethod
    def _edit_domain_db(cls, domain: str, p: dict) -> None:
        try:
            conn = cls._domain_db(domain)
            sets: list[str] = []
            vals: list[object] = []
            if "duration_mins" in p:
                sets.append("duration_mins = ?")
                vals.append(p["duration_mins"])
            if "notes" in p:
                sets.append("notes = ?")
                vals.append(p["notes"])
            if sets:
                vals.append(p["entry_id"])
                conn.execute(
                    f"UPDATE entries SET {', '.join(sets)} WHERE id = ?",
                    vals,
                )
                conn.commit()
            conn.close()
        except Exception:
            pass
