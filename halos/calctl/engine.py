"""Merge, sort, conflict detection, and free slot computation for calctl."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .sources import CalendarEvent, Source


def merge_events(sources: list[Source], start: datetime, end: datetime) -> list[CalendarEvent]:
    """Fetch events from all sources and merge into a single sorted list."""
    all_events: list[CalendarEvent] = []
    for src in sources:
        try:
            all_events.extend(src.fetch(start, end))
        except Exception:
            # Individual source failures should not break the whole view
            continue
    return sort_events(all_events)


def sort_events(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Sort events by start time, with ties broken by source name."""
    return sorted(events, key=lambda e: (e.start, e.source, e.title))


def find_conflicts(events: list[CalendarEvent]) -> list[tuple[CalendarEvent, CalendarEvent]]:
    """Find pairs of events with overlapping time intervals.

    Only events with both start and end times can conflict.
    Point-in-time events (end=None) do not conflict with anything.
    """
    # Filter to events that have a duration
    timed = [e for e in events if e.end is not None and e.end > e.start]
    timed.sort(key=lambda e: e.start)

    conflicts: list[tuple[CalendarEvent, CalendarEvent]] = []
    for i in range(len(timed)):
        for j in range(i + 1, len(timed)):
            a, b = timed[i], timed[j]
            # b starts after a ends — no overlap, and no further j will overlap a
            if b.start >= a.end:
                break
            # overlap: a.start < b.end and b.start < a.end
            conflicts.append((a, b))
    return conflicts


def find_free_slots(
    events: list[CalendarEvent],
    duration_mins: int,
    day_start: datetime,
    day_end: datetime,
) -> list[tuple[datetime, datetime]]:
    """Find gaps in the schedule where a block of `duration_mins` fits.

    Considers events with both start and end times as busy periods.
    Point-in-time events (end=None) are ignored for free-slot computation.

    Args:
        events: All events for the day.
        duration_mins: Minimum free slot duration in minutes.
        day_start: Start of the day window (UTC).
        day_end: End of the day window (UTC).

    Returns:
        List of (slot_start, slot_end) tuples where the gap >= duration_mins.
    """
    duration = timedelta(minutes=duration_mins)

    # Collect busy intervals
    busy = []
    for e in events:
        if e.end is not None and e.end > e.start:
            s = max(e.start, day_start)
            f = min(e.end, day_end)
            if s < f:
                busy.append((s, f))

    # Sort and merge overlapping busy intervals
    busy.sort()
    merged: list[tuple[datetime, datetime]] = []
    for s, f in busy:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], f))
        else:
            merged.append((s, f))

    # Find gaps between busy periods
    slots: list[tuple[datetime, datetime]] = []
    cursor = day_start

    for busy_start, busy_end in merged:
        if busy_start > cursor:
            gap = busy_start - cursor
            if gap >= duration:
                slots.append((cursor, busy_start))
        cursor = max(cursor, busy_end)

    # Check gap after last busy period
    if cursor < day_end:
        gap = day_end - cursor
        if gap >= duration:
            slots.append((cursor, day_end))

    return slots


def day_bounds(date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return (start_of_day, end_of_day) in UTC for the given date."""
    if date is None:
        date = datetime.now(timezone.utc)
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def week_bounds(date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return (start_of_today, end_of_7_days_from_now) in UTC."""
    if date is None:
        date = datetime.now(timezone.utc)
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end
