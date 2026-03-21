import argparse
import json
import sys

from . import config as cfgmod
from . import parser
from . import search


def main():
    ap = argparse.ArgumentParser(
        prog="logctl",
        description="Structured log reader for halos",
    )
    ap.add_argument("--config", default="", help="config file (default: ./logctl.yaml)")
    ap.add_argument("--json", action="store_true", dest="json_out", help="output as JSON")
    ap.add_argument("--verbose", action="store_true")

    sub = ap.add_subparsers(dest="command")

    # --- tail ---
    p_tail = sub.add_parser("tail", help="tail log output")
    p_tail.add_argument("--source", default="", help="filter by source module")
    p_tail.add_argument("--level", default="", help="filter by level (debug|info|warn|error)")
    p_tail.add_argument("-n", "--lines", type=int, default=0, help="number of lines (default: from config)")

    # --- search ---
    p_search = sub.add_parser("search", help="search across log files")
    p_search.add_argument("--text", default="", help="text to search for")
    p_search.add_argument("--source", default="", help="filter by source module")
    p_search.add_argument("--level", default="", help="filter by level")
    p_search.add_argument("--since", default="", help="time window (e.g. 1h, 24h, 7d)")

    # --- stats ---
    sub.add_parser("stats", help="log volume and distribution stats")

    # --- errors ---
    sub.add_parser("errors", help="shorthand for search --level error --since 24h")

    # --- fleet ---
    p_fleet = sub.add_parser("fleet", help="tail logs across all fleet instances")
    p_fleet.add_argument("--instance", default="", help="filter to a specific instance")
    p_fleet.add_argument("--level", default="", help="filter by level")
    p_fleet.add_argument("--conversations", action="store_true", help="show only message pairs (user → agent)")
    p_fleet.add_argument("--full", action="store_true", help="no truncation on conversation output")
    p_fleet.add_argument("--width", type=int, default=120, help="truncation width for conversations (default: 120)")
    p_fleet.add_argument("-n", "--lines", type=int, default=50, help="lines per source")

    # --- usage ---
    p_usage = sub.add_parser("usage", help="token usage and cost summary")
    p_usage.add_argument("--since", default="24h", help="time window (e.g. 1h, 24h, 7d)")
    p_usage.add_argument("--group", default="", help="filter to a specific group")
    p_usage.add_argument("--by", default="group", choices=["group", "model"], help="aggregate by field")

    # --- trace ---
    p_trace = sub.add_parser("trace", help="correlate events around a timestamp")
    p_trace.add_argument("timestamp", help="seed timestamp (ISO 8601 or HH:MM:SS.mmm)")
    p_trace.add_argument("--instance", default="", help="filter to a specific instance")
    p_trace.add_argument("--window", type=float, default=5.0, help="correlation window in seconds")

    args = ap.parse_args()
    if not args.command:
        ap.print_help()
        sys.exit(0)

    cfg = cfgmod.load(args.config)

    commands = {
        "tail": cmd_tail,
        "search": cmd_search,
        "stats": cmd_stats,
        "errors": cmd_errors,
        "fleet": cmd_fleet,
        "usage": cmd_usage,
        "trace": cmd_trace,
    }
    commands[args.command](cfg, args)


def cmd_tail(cfg, args):
    n = args.lines or cfg.tail_lines
    source_filter = args.source or None
    level_filter = args.level or None

    # Determine which files to tail
    if source_filter and source_filter in cfg.sources:
        files = {source_filter: cfg.sources[source_filter]}
    else:
        files = cfg.sources

    all_entries = []
    for name, path in files.items():
        entries = search.read_log_tail(path, n=n, fmt=cfg.format)
        all_entries.extend(entries)

    filtered = search.filter_entries(
        all_entries,
        level=level_filter,
        source=source_filter,
    )

    # Limit to n entries after filtering
    output = filtered[-n:]

    if args.json_out:
        json.dump([_entry_dict(e) for e in output], sys.stdout, indent=2)
        print()
    else:
        for e in output:
            print(parser.format_entry(e))


def cmd_search(cfg, args):
    text_filter = args.text or None
    source_filter = args.source or None
    level_filter = args.level or None
    since_filter = args.since or None

    all_entries = []
    for name, path in cfg.sources.items():
        entries = search.read_log_file(path, fmt=cfg.format)
        all_entries.extend(entries)

    filtered = search.filter_entries(
        all_entries,
        level=level_filter,
        source=source_filter,
        text=text_filter,
        since=since_filter,
    )

    if args.json_out:
        json.dump([_entry_dict(e) for e in filtered], sys.stdout, indent=2)
        print()
    else:
        for e in filtered:
            print(parser.format_entry(e))
        if not filtered:
            print("No matching log entries found.")


def cmd_stats(cfg, args):
    all_entries = []
    for name, path in cfg.sources.items():
        entries = search.read_log_file(path, fmt=cfg.format)
        all_entries.extend(entries)

    stats = search.compute_stats(all_entries)

    if args.json_out:
        json.dump(stats, sys.stdout, indent=2)
        print()
        return

    print(f"Total entries: {stats['total']}")
    print()
    print("By source:")
    for src, count in stats["by_source"].items():
        print(f"  {src:<20} {count}")
    print()
    print("By level:")
    for lvl, count in stats["by_level"].items():
        print(f"  {lvl:<10} {count}")
    print()
    print(f"Errors: {stats['error_count']} ({stats['error_rate']}%)")


def cmd_errors(cfg, args):
    all_entries = []
    for name, path in cfg.sources.items():
        entries = search.read_log_file(path, fmt=cfg.format)
        all_entries.extend(entries)

    filtered = search.filter_entries(
        all_entries,
        level="error",
        since="24h",
    )

    if args.json_out:
        json.dump([_entry_dict(e) for e in filtered], sys.stdout, indent=2)
        print()
    else:
        for e in filtered:
            print(parser.format_entry(e))
        if not filtered:
            print("No errors in the last 24 hours.")


def cmd_fleet(cfg, args):
    from .fleet import read_fleet_entries, read_fleet_conversations
    from .search import filter_entries

    instance = args.instance or None
    n = args.lines

    if args.conversations:
        pairs = read_fleet_conversations(instance_filter=instance, limit=n)
        if args.json_out:
            json.dump(pairs, sys.stdout, indent=2)
            print()
        else:
            w = 0 if args.full else args.width
            for p in pairs:
                inst = p["instance"]
                ts = p["timestamp"]
                user = p["user_message"]
                agent = p["agent_response"]
                u_display = user if not w else user[:w]
                a_display = agent if not w else agent[:w]
                status = "" if agent else "  [no response captured]"
                print(f"[{ts}] {inst}{status}")
                print(f"  USER:  {u_display}")
                if agent:
                    print(f"  AGENT: {a_display}")
                print()
            if not pairs:
                print("No conversations found.")
        return

    entries = read_fleet_entries(instance_filter=instance, n=n)

    if args.level:
        entries = filter_entries(entries, level=args.level)

    if args.json_out:
        json.dump([_entry_dict(e) for e in entries], sys.stdout, indent=2)
        print()
    else:
        for e in entries:
            print(parser.format_entry(e, show_instance=True))
        if not entries:
            print("No fleet log entries found.")


def cmd_usage(cfg, args):
    from pathlib import Path
    from .usage import read_usage, summarize

    usage_path = Path(cfg.data_dir) / "api-usage.jsonl"
    events = read_usage(usage_path, since=args.since)

    if args.group:
        events = [e for e in events if e.get("group") == args.group]

    if not events:
        print(f"No usage data found (looked in {usage_path}, since={args.since}).")
        return

    summary = summarize(events, by=args.by)

    if args.json_out:
        json.dump(summary, sys.stdout, indent=2, default=str)
        print()
        return

    print(f"Token usage (since {args.since}, by {args.by})")
    print("─" * 80)
    print(f"{'Group/Model':<30} {'Input':>10} {'Output':>10} {'Cache R':>10} {'Reqs':>6} {'Cost':>10}")
    print("─" * 80)

    for key, t in sorted(summary["by"].items(), key=lambda x: -x[1]["cost_usd"]):
        print(
            f"{key:<30} {t['input_tokens']:>10,} {t['output_tokens']:>10,} "
            f"{t['cache_read_tokens']:>10,} {t['requests']:>6} ${t['cost_usd']:>9.4f}"
        )

    total = summary["total"]
    print("─" * 80)
    print(
        f"{'TOTAL':<30} {total['input_tokens']:>10,} {total['output_tokens']:>10,} "
        f"{total['cache_read_tokens']:>10,} {total['requests']:>6} ${total['cost_usd']:>9.4f}"
    )


def cmd_trace(cfg, args):
    from .fleet import trace_event

    instance = args.instance or None
    entries = trace_event(
        seed_timestamp=args.timestamp,
        instance_filter=instance,
        window_seconds=args.window,
    )

    if args.json_out:
        json.dump([_entry_dict(e) for e in entries], sys.stdout, indent=2)
        print()
    else:
        print(f"Trace: {args.timestamp} (±{args.window}s window)")
        print("─" * 100)
        for e in entries:
            print(parser.format_entry(e, show_instance=True))
        if not entries:
            print("No correlated events found.")
        else:
            print("─" * 100)
            print(f"{len(entries)} events across {len(set(e.instance for e in entries))} instance(s)")


def _entry_dict(entry: parser.LogEntry) -> dict:
    """Convert a LogEntry to a JSON-serializable dict."""
    d = {
        "level": entry.level,
        "message": entry.message,
    }
    if entry.timestamp:
        d["timestamp"] = entry.timestamp
    if entry.source:
        d["source"] = entry.source
    if entry.instance:
        d["instance"] = entry.instance
    if entry.channel:
        d["channel"] = entry.channel
    if entry.data:
        d["data"] = entry.data
    return d
