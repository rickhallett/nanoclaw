"""calctl CLI -- unified schedule view.

Usage:
    calctl today [--json]                    # everything happening today
    calctl week [--json]                     # 7-day view
    calctl range --from DATE --to DATE       # arbitrary range
    calctl conflicts                         # overlapping commitments
    calctl free --duration 60 [--date DATE]  # find open slots
    calctl summary                           # one-liner for briefing integration
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from halos.common.log import hlog

from .engine import merge_events, find_conflicts, find_free_slots, day_bounds, week_bounds
from .sources import (
    CalendarEvent,
    NightctlSource,
    CronctlSource,
    GoogleCalendarSource,
)
from .briefing import text_summary


def _default_sources():
    """Return all available sources."""
    return [NightctlSource(), CronctlSource(), GoogleCalendarSource()]


def _format_event_line(ev: CalendarEvent) -> str:
    """Format a single event for terminal display."""
    time_str = ev.start.strftime("%H:%M")

    if ev.end:
        end_str = ev.end.strftime("%H:%M")
        time_part = f"{time_str}-{end_str}"
    else:
        time_part = time_str

    source_tag = f"({ev.source})"

    # Add metadata hints
    extras = []
    if ev.source == "nightctl":
        q = ev.metadata.get("quadrant", "")
        st = ev.metadata.get("status", "")
        if q:
            extras.append(q)
        if st:
            extras.append(st)
    if extras:
        source_tag = f"({ev.source}: {', '.join(extras)})"

    return f"  {time_part:<14} {ev.title}  {source_tag}"


def _format_day_header(dt: datetime) -> str:
    return dt.strftime("%A %Y-%m-%d")


def _print_events(events: list[CalendarEvent], json_out: bool) -> None:
    if json_out:
        print(json.dumps([e.to_dict() for e in events], indent=2))
        return

    if not events:
        print("No events.")
        return

    # Group by day
    days: dict[str, list[CalendarEvent]] = {}
    for ev in events:
        day_key = ev.start.strftime("%Y-%m-%d")
        days.setdefault(day_key, []).append(ev)

    for day_key in sorted(days.keys()):
        day_dt = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        print(_format_day_header(day_dt))
        for ev in days[day_key]:
            print(_format_event_line(ev))
        print()


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_today(args) -> int:
    start, end = day_bounds()
    sources = _default_sources()
    events = merge_events(sources, start, end)
    _print_events(events, getattr(args, "json_out", False))
    return 0


def cmd_week(args) -> int:
    start, end = week_bounds()
    sources = _default_sources()
    events = merge_events(sources, start, end)
    _print_events(events, getattr(args, "json_out", False))
    return 0


def cmd_range(args) -> int:
    try:
        start = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end += timedelta(days=1)  # inclusive end date
    except ValueError:
        print("ERROR: use --from YYYY-MM-DD --to YYYY-MM-DD", file=sys.stderr)
        return 1

    sources = _default_sources()
    events = merge_events(sources, start, end)
    _print_events(events, getattr(args, "json_out", False))
    return 0


def cmd_conflicts(args) -> int:
    start, end = week_bounds()
    sources = _default_sources()
    events = merge_events(sources, start, end)
    conflicts = find_conflicts(events)

    json_out = getattr(args, "json_out", False)

    if json_out:
        data = [
            {"a": a.to_dict(), "b": b.to_dict()}
            for a, b in conflicts
        ]
        print(json.dumps(data, indent=2))
        return 0

    if not conflicts:
        print("No conflicts found.")
        return 0

    print(f"{len(conflicts)} conflict(s):")
    for a, b in conflicts:
        print(f"  {a.start.strftime('%H:%M')}-{a.end.strftime('%H:%M')} {a.title}")
        print(f"    overlaps with")
        print(f"  {b.start.strftime('%H:%M')}-{b.end.strftime('%H:%M')} {b.title}")
        print()
    return 0


def cmd_free(args) -> int:
    duration_mins = args.duration

    if args.date:
        try:
            date = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print("ERROR: use --date YYYY-MM-DD", file=sys.stderr)
            return 1
    else:
        date = datetime.now(timezone.utc)

    start, end = day_bounds(date)
    sources = _default_sources()
    events = merge_events(sources, start, end)
    slots = find_free_slots(events, duration_mins, start, end)

    json_out = getattr(args, "json_out", False)

    if json_out:
        data = [
            {"start": s.isoformat(), "end": e.isoformat(), "duration_mins": int((e - s).total_seconds() / 60)}
            for s, e in slots
        ]
        print(json.dumps(data, indent=2))
        return 0

    if not slots:
        print(f"No free slots of {duration_mins}+ minutes found.")
        return 0

    print(f"Free slots ({duration_mins}+ min) on {date.strftime('%Y-%m-%d')}:")
    for slot_start, slot_end in slots:
        dur = int((slot_end - slot_start).total_seconds() / 60)
        print(f"  {slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}  ({dur} min)")
    return 0


def cmd_summary(args) -> int:
    print(text_summary())
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calctl",
        description="calctl -- unified schedule view",
    )
    sub = parser.add_subparsers(dest="command")

    # today
    p_today = sub.add_parser("today", help="Everything happening today")
    p_today.add_argument("--json", action="store_true", dest="json_out")

    # week
    p_week = sub.add_parser("week", help="7-day view")
    p_week.add_argument("--json", action="store_true", dest="json_out")

    # range
    p_range = sub.add_parser("range", help="Arbitrary date range")
    p_range.add_argument("--from", required=True, dest="from_date",
                          help="Start date (YYYY-MM-DD)")
    p_range.add_argument("--to", required=True, dest="to_date",
                          help="End date (YYYY-MM-DD)")
    p_range.add_argument("--json", action="store_true", dest="json_out")

    # conflicts
    p_conflicts = sub.add_parser("conflicts", help="Show overlapping commitments")
    p_conflicts.add_argument("--json", action="store_true", dest="json_out")

    # free
    p_free = sub.add_parser("free", help="Find open time slots")
    p_free.add_argument("--duration", type=int, required=True,
                         help="Minimum slot duration in minutes")
    p_free.add_argument("--date", default=None, help="Date to check (YYYY-MM-DD, default: today)")
    p_free.add_argument("--json", action="store_true", dest="json_out")

    # summary
    sub.add_parser("summary", help="One-liner for briefing integration")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "today": cmd_today,
        "week": cmd_week,
        "range": cmd_range,
        "conflicts": cmd_conflicts,
        "free": cmd_free,
        "summary": cmd_summary,
    }

    rc = dispatch[args.command](args) or 0
    sys.exit(rc)


if __name__ == "__main__":
    main()
