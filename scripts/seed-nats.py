#!/usr/bin/env python3
"""Seed NATS JetStream with existing trackctl/journalctl data.

Usage:
    # Port-forward NATS first:
    kubectl port-forward -n halo-fleet svc/nats 4222:4222 &
    
    uv run python scripts/seed-nats.py
"""

import asyncio
import json
import sqlite3
from pathlib import Path

import nats
from ulid import ULID


NATS_URL = "nats://localhost:4222"
NATS_USER = "hq"
NATS_PASS = "lxFDhD1sHNuGAmcE1kTPX6Ea6g9LzPXx"

STORE = Path("store")

TRACK_DOMAINS = [
    "movement",
    "zazen",
    "study-crafters",
    "study-neetcode",
    "study-source",
    "project",
]


def make_event(event_type: str, payload: dict, timestamp: str, source: str = "seed") -> dict:
    return {
        "id": str(ULID()),
        "type": event_type,
        "version": 1,
        "source": source,
        "timestamp": timestamp,
        "correlation_id": str(ULID()),
        "payload": payload,
    }


async def seed():
    nc = await nats.connect(NATS_URL, user=NATS_USER, password=NATS_PASS)
    js = nc.jetstream()
    published = 0

    # Seed track domains
    for domain in TRACK_DOMAINS:
        db_path = STORE / f"track_{domain}.db"
        if not db_path.exists():
            print(f"  skip {domain} (no db)")
            continue

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM entries ORDER BY id").fetchall()
        conn.close()

        for row in rows:
            event = make_event(
                event_type=f"track.{domain}.logged",
                timestamp=row["timestamp"],
                payload={
                    "entry_id": row["id"],
                    "domain": domain,
                    "duration_mins": row["duration_mins"],
                    "notes": row["notes"] or "",
                },
            )
            subject = f"halo.track.{domain}"
            ack = await js.publish(subject, json.dumps(event).encode())
            published += 1

        print(f"  track.{domain}: {len(rows)} entries")

    # Seed journal
    journal_db = STORE / "journal.db"
    if journal_db.exists():
        conn = sqlite3.connect(journal_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM entries ORDER BY id").fetchall()
        conn.close()

        for row in rows:
            tags = row["tags"]
            if tags:
                try:
                    tag_list = json.loads(tags)
                except json.JSONDecodeError:
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            else:
                tag_list = []

            event = make_event(
                event_type="journal.entry.added",
                timestamp=row["timestamp"],
                payload={
                    "entry_id": row["id"],
                    "raw_text": row["raw_text"],
                    "tags": tag_list,
                    "source": row["source"] or "text",
                    "mood": row["mood"] or None,
                    "energy": row["energy"] or None,
                },
            )
            subject = "halo.journal"
            ack = await js.publish(subject, json.dumps(event).encode())
            published += 1

        print(f"  journal: {len(rows)} entries")

    await nc.close()
    print(f"\nDone: {published} events published to HALO stream")


if __name__ == "__main__":
    asyncio.run(seed())
