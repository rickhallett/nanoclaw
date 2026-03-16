import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import load_config
from .collectors import collect_memctl, collect_todoctl, collect_nightctl, collect_activity
from .formatters import format_briefing, format_weekly, format_health, format_digest


def _parse_duration(s: str) -> timedelta:
    """Parse a duration string like '24h', '7d', '30m' into a timedelta."""
    m = re.match(r"^(\d+)\s*(h|d|m|w)$", s.strip().lower())
    if not m:
        raise ValueError(f"Invalid duration: {s!r}. Use format like '24h', '7d', '30m', '1w'.")
    val = int(m.group(1))
    unit = m.group(2)
    if unit == "m":
        return timedelta(minutes=val)
    elif unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    elif unit == "w":
        return timedelta(weeks=val)
    raise ValueError(f"Unknown unit: {unit}")


def _output(text: str, output_file: str | None, reports_dir: Path | None):
    """Print text or write to file."""
    if output_file:
        p = Path(output_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n")
        print(f"Report written to {p}")
    else:
        print(text)


def cmd_briefing(args, cfg):
    memctl = collect_memctl(cfg.memctl_config)
    todoctl = collect_todoctl(cfg.todoctl_config)
    nightctl = collect_nightctl(cfg.nightctl_config)
    text = format_briefing(memctl, todoctl, nightctl, json_out=args.json)
    _output(text, args.output, cfg.reports_dir)
    return 0


def cmd_weekly(args, cfg):
    since = datetime.now(timezone.utc) - timedelta(weeks=1)
    memctl = collect_memctl(cfg.memctl_config)
    todoctl = collect_todoctl(cfg.todoctl_config)
    nightctl = collect_nightctl(cfg.nightctl_config)
    activity = collect_activity(
        cfg.memctl_config, cfg.todoctl_config, cfg.nightctl_config, since
    )
    text = format_weekly(activity, memctl, todoctl, nightctl, json_out=args.json)
    _output(text, args.output, cfg.reports_dir)
    return 0


def cmd_health(args, cfg):
    memctl = collect_memctl(cfg.memctl_config)
    todoctl = collect_todoctl(cfg.todoctl_config)
    nightctl = collect_nightctl(cfg.nightctl_config)
    text = format_health(memctl, todoctl, nightctl, json_out=args.json)
    _output(text, args.output, cfg.reports_dir)
    return 0


def cmd_digest(args, cfg):
    duration = _parse_duration(args.since)
    since = datetime.now(timezone.utc) - duration
    activity = collect_activity(
        cfg.memctl_config, cfg.todoctl_config, cfg.nightctl_config, since
    )
    text = format_digest(activity, args.since, json_out=args.json)
    _output(text, args.output, cfg.reports_dir)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="reportctl",
        description="halOS periodic digest generator",
    )
    parser.add_argument("--config", default=None, help="Path to reportctl.yaml")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", default=None, help="Write report to file")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="subcommand")

    sub.add_parser("briefing", help="Morning briefing: corpus stats, open todos, pending jobs")
    sub.add_parser("weekly", help="Weekly summary: notes created, todos completed, jobs run")
    sub.add_parser("health", help="System health: index drift, orphans, queue status")

    digest = sub.add_parser("digest", help="Activity digest for a time window")
    digest.add_argument("--since", required=True, help="Time window, e.g. '24h', '7d', '1w'")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(4)

    dispatch = {
        "briefing": cmd_briefing,
        "weekly": cmd_weekly,
        "health": cmd_health,
        "digest": cmd_digest,
    }

    if args.subcommand in dispatch:
        sys.exit(dispatch[args.subcommand](args, cfg) or 0)
    else:
        parser.print_help()
        sys.exit(0)
