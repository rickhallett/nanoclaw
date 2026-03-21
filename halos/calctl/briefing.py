"""Briefing integration for calctl.

Provides text_summary() for inclusion in morning/nightly briefings.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .engine import merge_events, day_bounds
from .sources import NightctlSource, CronctlSource, GoogleCalendarSource


def text_summary() -> str:
    """One-liner summary of today's schedule.

    Example: "calctl: 3 events, 2 tasks due, 1 cron job | next: Team standup at 09:00"
    """
    now = datetime.now(timezone.utc)
    start, end = day_bounds(now)

    sources = [NightctlSource(), CronctlSource(), GoogleCalendarSource()]
    events = merge_events(sources, start, end)

    if not events:
        return "calctl: no events today"

    # Count by source
    gcal_count = sum(1 for e in events if e.source == "google_calendar")
    nightctl_count = sum(1 for e in events if e.source == "nightctl")
    cronctl_count = sum(1 for e in events if e.source == "cronctl")

    parts: list[str] = []
    if gcal_count:
        parts.append(f"{gcal_count} event{'s' if gcal_count != 1 else ''}")
    if nightctl_count:
        parts.append(f"{nightctl_count} task{'s' if nightctl_count != 1 else ''} due")
    if cronctl_count:
        parts.append(f"{cronctl_count} cron job{'s' if cronctl_count != 1 else ''}")

    summary = f"calctl: {', '.join(parts)}"

    # Find next upcoming event
    upcoming = [e for e in events if e.start >= now]
    if upcoming:
        nxt = upcoming[0]
        time_str = nxt.start.strftime("%H:%M")
        summary += f" | next: {nxt.title} at {time_str}"

    return summary
