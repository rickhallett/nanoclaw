#!/usr/bin/env python3
"""Query cross-advisor conversation history from the Halostream.

Usage:
    halo-telephony                          # last 24h of all advisor messages
    halo-telephony --advisor musashi         # filter to one advisor
    halo-telephony --summary                 # per-advisor message counts
    halo-telephony --days 7                  # last 7 days
    halo-telephony --direction inbound       # only user messages
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from halos.common.paths import store_dir


def main():
    parser = argparse.ArgumentParser(
        prog="halo-telephony",
        description="Query cross-advisor conversation history from Halostream",
    )
    parser.add_argument("--days", type=int, default=1, help="Look back N days (default: 1)")
    parser.add_argument("--advisor", help="Filter to a specific advisor")
    parser.add_argument("--direction", choices=["inbound", "outbound"], help="Filter by direction")
    parser.add_argument("--summary", action="store_true", help="Per-advisor message counts")
    parser.add_argument("--limit", type=int, default=50, help="Max messages to show")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args()

    db_path = store_dir() / "projection.db"
    if not db_path.exists():
        print("No projection database found.")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    table_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='advisor_messages'"
    ).fetchone()
    if not table_check:
        print("No advisor message data yet (table not created).")
        return 1

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    if args.summary:
        query = (
            "SELECT advisor, direction, COUNT(*) as count "
            "FROM advisor_messages WHERE timestamp >= ? "
        )
        params: list = [cutoff]
        if args.advisor:
            query += "AND advisor = ? "
            params.append(args.advisor)
        query += "GROUP BY advisor, direction ORDER BY advisor, direction"

        rows = conn.execute(query, params).fetchall()
        conn.close()

        if not rows:
            print(f"No messages in the last {args.days} day(s).")
            return 0

        if args.json_out:
            import json
            print(json.dumps([dict(r) for r in rows], indent=2))
        else:
            print(f"{'ADVISOR':<16} {'DIRECTION':<12} {'COUNT':>6}")
            print("-" * 40)
            for r in rows:
                print(f"{r['advisor']:<16} {r['direction']:<12} {r['count']:>6}")
        return 0

    # Detail view
    query = (
        "SELECT advisor, direction, message_text, timestamp "
        "FROM advisor_messages WHERE timestamp >= ? "
    )
    params = [cutoff]
    if args.advisor:
        query += "AND advisor = ? "
        params.append(args.advisor)
    if args.direction:
        query += "AND direction = ? "
        params.append(args.direction)
    query += "ORDER BY timestamp DESC LIMIT ?"
    params.append(args.limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        print(f"No messages in the last {args.days} day(s).")
        return 0

    if args.json_out:
        import json
        print(json.dumps([dict(r) for r in rows], indent=2))
    else:
        for r in reversed(rows):
            ts = r["timestamp"][:16] if r["timestamp"] else ""
            direction = ">>>" if r["direction"] == "inbound" else "<<<"
            text = r["message_text"][:120]
            print(f"[{ts}] {r['advisor']:<12} {direction} {text}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
