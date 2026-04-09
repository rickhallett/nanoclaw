"""Ingest git history into the Halostream as dev.commit.logged events.

Usage:
    # Auto-discover all repos under ~/code, publish via tunnel:
    NATS_PASS=xxx NATS_URL=nats://localhost:4222 python -m halos.eventsource.git_ingest --discover ~/code

    # Specific repos only:
    python -m halos.eventsource.git_ingest --repos halo:~/code/halo arcana:~/code/arcana

    # Dry run (print events to stdout):
    python -m halos.eventsource.git_ingest --discover ~/code --dry-run

    # Managed by cronctl — see cron/jobs/git-ingest.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .core import Event
from .publish import fire_event


def _git_log(repo_path: Path, since: str = "2 days ago") -> list[dict]:
    """Extract commits as structured dicts."""
    # Use %x00 as field separator to avoid JSON escaping issues
    fmt = "%h%x00%s%x00%an%x00%aI"
    result = subprocess.run(
        ["git", "-C", str(repo_path), "log", f"--format={fmt}",
         f"--since={since}", "--all"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"WARNING: git log failed for {repo_path}: {result.stderr.strip()}",
              file=sys.stderr)
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\0")
        if len(parts) < 4:
            continue
        commits.append({
            "sha": parts[0],
            "message": parts[1],
            "author": parts[2],
            "timestamp": parts[3],
        })
    return commits


def _to_events(repo_name: str, commits: list[dict]) -> list[Event]:
    """Convert git commits to Halostream events."""
    events = []
    for c in commits:
        event = Event.create(
            type="dev.commit.logged",
            source="git-ingest",
            payload={
                "repo": repo_name,
                "sha": c["sha"],
                "message": c["message"],
                "author": c["author"],
                "commit_timestamp": c["timestamp"],
            },
        )
        events.append(event)
    return events


def _discover_repos(root: Path) -> dict[str, Path]:
    """Find all git repos directly under root (non-recursive)."""
    repos: dict[str, Path] = {}
    if not root.is_dir():
        return repos
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / ".git").exists():
            repos[child.name] = child
    return repos


def main():
    parser = argparse.ArgumentParser(description="Ingest git history into Halostream")
    parser.add_argument("--since", default="1 day ago", help="Git log --since value")
    parser.add_argument("--dry-run", action="store_true", help="Print events, don't publish")
    parser.add_argument("--discover", type=Path, help="Auto-discover repos under this directory")
    parser.add_argument("--repos", nargs="*", help="repo:path pairs (e.g. halo:/path/to/halo)")
    args = parser.parse_args()

    # Resolve repos
    repos: dict[str, Path] = {}
    if args.repos:
        for spec in args.repos:
            name, _, path = spec.partition(":")
            repos[name] = Path(path)
    elif args.discover:
        repos = _discover_repos(args.discover)
    else:
        repos = _discover_repos(Path.home() / "code")

    if not repos:
        print("ERROR: no repos found", file=sys.stderr)
        sys.exit(1)

    # Extract and convert
    all_events: list[Event] = []
    for name, path in sorted(repos.items()):
        commits = _git_log(path, since=args.since)
        if not commits:
            continue
        events = _to_events(name, commits)
        all_events.extend(events)
        print(f"{name}: {len(commits)} commits", file=sys.stderr)

    # Sort by commit timestamp (oldest first for chronological replay)
    all_events.sort(key=lambda e: e.payload.get("commit_timestamp", ""))

    print(f"\nTotal: {len(all_events)} events", file=sys.stderr)

    if args.dry_run:
        for e in all_events:
            print(json.dumps({
                "type": e.type,
                "source": e.source,
                "payload": e.payload,
            }))
        return

    # Publish
    nats_pass = os.environ.get("NATS_PASS")
    if not nats_pass:
        print("ERROR: NATS_PASS not set. Use --dry-run or set NATS_PASS.", file=sys.stderr)
        sys.exit(1)

    published = 0
    for e in all_events:
        ok = fire_event(e.type, e.payload, source="git-ingest")
        if ok:
            published += 1
        else:
            print(f"FAILED: {e.payload['repo']}:{e.payload['sha']}", file=sys.stderr)

    print(f"\nPublished: {published}/{len(all_events)}", file=sys.stderr)


if __name__ == "__main__":
    main()
