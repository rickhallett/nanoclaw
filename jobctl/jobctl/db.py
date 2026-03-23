import sqlite3
import os
from pathlib import Path

DB_PATH = Path(os.environ.get("JOBCTL_DB", Path.home() / "code/nanoclaw/store/jobs.db"))


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS listings (
            id          TEXT PRIMARY KEY,
            company     TEXT NOT NULL,
            title       TEXT NOT NULL,
            url         TEXT,
            description TEXT,
            location    TEXT,
            salary      TEXT,
            source      TEXT NOT NULL DEFAULT 'manual',
            status      TEXT NOT NULL DEFAULT 'pending_review',
            score       REAL NOT NULL DEFAULT 0.0,
            notes       TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS materials (
            id          TEXT PRIMARY KEY,
            listing_id  TEXT NOT NULL REFERENCES listings(id),
            type        TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calibration (
            id          TEXT PRIMARY KEY,
            listing_id  TEXT NOT NULL REFERENCES listings(id),
            action      TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
