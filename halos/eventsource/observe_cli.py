#!/usr/bin/env python3
"""Query the observation projection — view Aura's recent conversation."""

import sqlite3
import sys
from pathlib import Path

from halos.common.paths import store_dir


def main():
    db_path = store_dir() / "projection.db"
    if not db_path.exists():
        print("No projection database found.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    limit = 20
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass

    rows = conn.execute(
        "SELECT role, content, timestamp, session_id "
        "FROM observation_messages ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()

    if not rows:
        print("No observation messages yet.")
        return

    # Print oldest first
    for row in reversed(rows):
        role = row["role"].upper()
        ts = row["timestamp"][:19] if row["timestamp"] else ""
        content = row["content"]
        print(f"[{ts}] {role}: {content[:200]}")
        print()

    conn.close()


if __name__ == "__main__":
    main()
