#!/usr/bin/env python3
"""Query dev commit activity from the Halostream projection.

Usage:
    halo-devlog                     # last 24h of commits across all repos
    halo-devlog --days 7            # last 7 days
    halo-devlog --repo stain        # filter by repo
    halo-devlog --summary           # per-repo summary counts
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from halos.common.paths import store_dir


def main():
    parser = argparse.ArgumentParser(
        prog="halo-devlog",
        description="Query dev commit activity from Halostream",
    )
    parser.add_argument("--days", type=int, default=1, help="Look back N days (default: 1)")
    parser.add_argument("--repo", help="Filter to a specific repo")
    parser.add_argument("--summary", action="store_true", help="Per-repo summary counts")
    parser.add_argument("--limit", type=int, default=100, help="Max commits to show")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args()

    db_path = store_dir() / "projection.db"
    if not db_path.exists():
        print("No projection database found.")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Check table exists
    table_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dev_commits'"
    ).fetchone()
    if not table_check:
        print("No dev commit data yet (table not created).")
        return 1

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    if args.summary:
        query = (
            "SELECT repo, COUNT(*) as commits, "
            "MIN(commit_timestamp) as first_commit, "
            "MAX(commit_timestamp) as last_commit "
            "FROM dev_commits WHERE commit_timestamp >= ? "
        )
        params: list = [cutoff]
        if args.repo:
            query += "AND repo = ? "
            params.append(args.repo)
        query += "GROUP BY repo ORDER BY commits DESC"

        rows = conn.execute(query, params).fetchall()
        if not rows:
            print(f"No commits in the last {args.days} day(s).")
            return 0

        if args.json_out:
            import json
            print(json.dumps([dict(r) for r in rows], indent=2))
        else:
            total = 0
            print(f"{'REPO':<20} {'COMMITS':>8}  {'LATEST'}")
            print("-" * 60)
            for r in rows:
                last = r["last_commit"][:16] if r["last_commit"] else ""
                print(f"{r['repo']:<20} {r['commits']:>8}  {last}")
                total += r["commits"]
            print("-" * 60)
            print(f"{'TOTAL':<20} {total:>8}")
        return 0

    # Detail view
    query = (
        "SELECT repo, sha, message, author, commit_timestamp "
        "FROM dev_commits WHERE commit_timestamp >= ? "
    )
    params = [cutoff]
    if args.repo:
        query += "AND repo = ? "
        params.append(args.repo)
    query += "ORDER BY commit_timestamp DESC LIMIT ?"
    params.append(args.limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        print(f"No commits in the last {args.days} day(s).")
        return 0

    if args.json_out:
        import json
        print(json.dumps([dict(r) for r in rows], indent=2))
    else:
        for r in rows:
            ts = r["commit_timestamp"][:16] if r["commit_timestamp"] else ""
            print(f"[{ts}] {r['repo']:<12} {r['sha']}  {r['message'][:80]}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
