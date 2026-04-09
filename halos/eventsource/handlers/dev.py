"""Dev commit projection — git activity across all repos."""

from __future__ import annotations

import sqlite3

from ..core import Event, ProjectionHandler


class DevCommitProjectionHandler(ProjectionHandler):
    """Handles dev.commit.logged events → local dev_commits table."""

    tables = ["dev_commits"]

    def handles(self) -> list[str]:
        return ["dev.commit.logged"]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS dev_commits (
                source_event_id TEXT PRIMARY KEY,
                repo TEXT NOT NULL,
                sha TEXT NOT NULL,
                message TEXT NOT NULL,
                author TEXT NOT NULL,
                commit_timestamp TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_dev_repo_ts "
            "ON dev_commits(repo, commit_timestamp DESC)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload
        db.execute(
            """
            INSERT OR IGNORE INTO dev_commits
                (source_event_id, repo, sha, message, author, commit_timestamp, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                p.get("repo", "unknown"),
                p.get("sha", ""),
                p.get("message", ""),
                p.get("author", ""),
                p.get("commit_timestamp", event.timestamp),
                event.timestamp,
            ),
        )
