"""journalctl CLI — qualitative journal for the halos ecosystem."""

import argparse
import json
import sys
from datetime import datetime, timezone

from .store import add_entry, list_entries, count_entries
from .window import window, window_month
from halos.eventsource.publish import fire_event


def cmd_add(args) -> int:
    tags = args.tags or ""
    source = args.source or "text"
    mood = args.mood or ""
    energy = args.energy or ""

    body = " ".join(args.text) if args.text else ""
    if not body:
        print("error: no text provided", file=sys.stderr)
        return 1

    entry = add_entry(
        raw_text=body,
        tags=tags,
        source=source,
        mood=mood,
        energy=energy,
    )

    fire_event("journal.entry.added", {
        "entry_id": entry["id"],
        "raw_text": body,
        "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        "source": source,
        "mood": mood or None,
        "energy": energy or None,
    })

    if args.json_out:
        print(json.dumps(entry, indent=2))
    else:
        print(f"Added entry #{entry['id']} at {entry['timestamp']}")

    return 0


def cmd_recent(args) -> int:
    days = args.days
    entries = list_entries(days=days, tags=args.tags)

    if args.json_out:
        print(json.dumps(entries, indent=2))
        return 0

    if not entries:
        print(f"No journal entries in the last {days} days.")
        return 0

    for e in entries:
        ts = e["timestamp"][:16].replace("T", " ")
        header = f"[{ts}]"
        if e.get("tags"):
            header += f" ({e['tags']})"
        if e.get("mood"):
            header += f" mood:{e['mood']}"
        if e.get("energy"):
            header += f" energy:{e['energy']}"
        if e.get("source") and e["source"] != "text":
            header += f" via:{e['source']}"
        print(f"{header}")
        print(f"  {e['raw_text']}")
        print()

    return 0


def cmd_window(args) -> int:
    if args.months:
        summary = window_month(no_cache=args.no_cache)
    else:
        summary = window(days=args.days, no_cache=args.no_cache)

    if args.json_out:
        print(json.dumps({"summary": summary, "days": args.days}))
    else:
        print(summary)

    return 0


def cmd_stats(args) -> int:
    total = count_entries()
    recent_7 = len(list_entries(days=7))
    recent_30 = len(list_entries(days=30))

    if args.json_out:
        print(json.dumps({
            "total": total,
            "last_7d": recent_7,
            "last_30d": recent_30,
        }))
    else:
        print(f"Total entries: {total}")
        print(f"Last 7 days:  {recent_7}")
        print(f"Last 30 days: {recent_30}")

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="journalctl",
        description="journalctl — qualitative journal for halos",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_out", help="JSON output"
    )

    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Add a journal entry")
    p_add.add_argument("text", nargs="*", help="Entry text")
    p_add.add_argument("--tags", default="", help="Comma-separated tags")
    p_add.add_argument(
        "--source", default="text", choices=["text", "voice", "agent"],
        help="Entry source (default: text)",
    )
    p_add.add_argument("--mood", default="", help="Freeform mood label")
    p_add.add_argument("--energy", default="", help="Freeform energy label")

    # recent
    p_recent = sub.add_parser("recent", help="List recent entries")
    p_recent.add_argument(
        "--days", type=int, default=7, help="Days to look back (default: 7)"
    )
    p_recent.add_argument("--tags", default=None, help="Filter by tags (comma-separated)")

    # window
    p_window = sub.add_parser("window", help="Sliding window summary")
    p_window.add_argument(
        "--days", type=int, default=7, help="Window size in days (default: 7)"
    )
    p_window.add_argument(
        "--months", type=int, default=0,
        help="Use monthly window (shorthand for --days 30)",
    )
    p_window.add_argument(
        "--no-cache", action="store_true", help="Force regeneration"
    )

    # stats
    sub.add_parser("stats", help="Entry count statistics")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    # Propagate top-level --json to subcommands
    if not hasattr(args, 'json_out'):
        args.json_out = False

    commands = {
        "add": cmd_add,
        "recent": cmd_recent,
        "window": cmd_window,
        "stats": cmd_stats,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
