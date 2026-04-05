"""Night domain projection — nightctl items and jobs."""

from __future__ import annotations

import json
import sqlite3

from ..core import Event, ProjectionHandler


class NightProjectionHandler(ProjectionHandler):
    """Handles night.* events → local night_items and night_jobs tables."""

    tables = ["night_items", "night_jobs"]

    def handles(self) -> list[str]:
        return [
            "night.item.created",
            "night.item.transitioned",
            "night.item.updated",
            "night.job.completed",
            "night.job.failed",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS night_items (
                item_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                quadrant TEXT NOT NULL DEFAULT 'q3',
                kind TEXT NOT NULL DEFAULT 'task',
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS night_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                duration_secs REAL,
                completed_at TEXT NOT NULL
            )
        """)

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload

        if event.type == "night.item.created":
            db.execute(
                """
                INSERT OR IGNORE INTO night_items
                    (item_id, title, quadrant, kind, tags, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            """,
                (
                    p["item_id"],
                    p["title"],
                    p.get("quadrant", "q3"),
                    p.get("kind", "task"),
                    json.dumps(p.get("tags", [])),
                    event.timestamp,
                    event.timestamp,
                ),
            )

        elif event.type == "night.item.transitioned":
            db.execute(
                "UPDATE night_items SET status = ?, updated_at = ? WHERE item_id = ?",
                (p["to_status"], event.timestamp, p["item_id"]),
            )

        elif event.type == "night.item.updated":
            for field_name, value in p.get("fields_changed", {}).items():
                if field_name in ("title", "quadrant", "kind"):
                    db.execute(
                        f"UPDATE night_items SET {field_name} = ?, updated_at = ? "
                        f"WHERE item_id = ?",
                        (value, event.timestamp, p["item_id"]),
                    )

        elif event.type in ("night.job.completed", "night.job.failed"):
            status = "completed" if event.type == "night.job.completed" else "failed"
            db.execute(
                """
                INSERT OR REPLACE INTO night_jobs
                    (job_id, status, result, error, duration_secs, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    p["job_id"],
                    status,
                    p.get("result"),
                    p.get("error"),
                    p.get("duration_secs"),
                    event.timestamp,
                ),
            )
