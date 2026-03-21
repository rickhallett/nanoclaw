"""Unit tests for calctl engine — merge, sort, conflict detection, free slots."""

from datetime import datetime, timedelta, timezone

from halos.calctl.engine import (
    merge_events,
    sort_events,
    find_conflicts,
    find_free_slots,
    day_bounds,
    week_bounds,
)
from halos.calctl.sources import CalendarEvent, Source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(hour: int, minute: int = 0, day: int = 21, month: int = 3, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _ev(title: str, start_h: int, end_h: int | None = None, source: str = "test") -> CalendarEvent:
    start = _utc(start_h)
    end = _utc(end_h) if end_h is not None else None
    return CalendarEvent(source=source, title=title, start=start, end=end)


class StubSource(Source):
    def __init__(self, events: list[CalendarEvent]):
        self._events = events

    def fetch(self, start, end):
        return [e for e in self._events if start <= e.start < end]


class FailingSource(Source):
    def fetch(self, start, end):
        raise RuntimeError("source unavailable")


# ---------------------------------------------------------------------------
# Merge & Sort
# ---------------------------------------------------------------------------


class TestMergeEvents:
    def test_empty_sources(self):
        result = merge_events([], _utc(0), _utc(23))
        assert result == []

    def test_single_source(self):
        events = [_ev("A", 9, 10), _ev("B", 14, 15)]
        src = StubSource(events)
        result = merge_events([src], _utc(0), _utc(23))
        assert len(result) == 2
        assert result[0].title == "A"
        assert result[1].title == "B"

    def test_multiple_sources_merged_and_sorted(self):
        src1 = StubSource([_ev("Late", 14, 15, source="gcal")])
        src2 = StubSource([_ev("Early", 8, 9, source="nightctl")])
        result = merge_events([src1, src2], _utc(0), _utc(23))
        assert len(result) == 2
        assert result[0].title == "Early"
        assert result[1].title == "Late"

    def test_failing_source_does_not_break_merge(self):
        good = StubSource([_ev("OK", 10, 11)])
        bad = FailingSource()
        result = merge_events([good, bad], _utc(0), _utc(23))
        assert len(result) == 1
        assert result[0].title == "OK"


class TestSortEvents:
    def test_sort_by_start_time(self):
        events = [_ev("C", 15), _ev("A", 8), _ev("B", 12)]
        result = sort_events(events)
        assert [e.title for e in result] == ["A", "B", "C"]

    def test_tie_broken_by_source_then_title(self):
        e1 = CalendarEvent(source="z_source", title="Alpha", start=_utc(9))
        e2 = CalendarEvent(source="a_source", title="Beta", start=_utc(9))
        result = sort_events([e1, e2])
        assert result[0].source == "a_source"
        assert result[1].source == "z_source"


# ---------------------------------------------------------------------------
# Conflict Detection
# ---------------------------------------------------------------------------


class TestConflicts:
    def test_no_events_no_conflicts(self):
        assert find_conflicts([]) == []

    def test_non_overlapping(self):
        events = [_ev("A", 9, 10), _ev("B", 10, 11)]
        assert find_conflicts(events) == []

    def test_adjacent_no_conflict(self):
        """Events where one ends exactly when the other starts are not conflicting."""
        events = [_ev("A", 9, 10), _ev("B", 10, 11)]
        assert find_conflicts(events) == []

    def test_overlapping_pair(self):
        events = [_ev("A", 9, 11), _ev("B", 10, 12)]
        conflicts = find_conflicts(events)
        assert len(conflicts) == 1
        assert conflicts[0][0].title == "A"
        assert conflicts[0][1].title == "B"

    def test_multi_conflict(self):
        """Three overlapping events produce multiple conflict pairs."""
        events = [
            _ev("A", 9, 12),
            _ev("B", 10, 13),
            _ev("C", 11, 14),
        ]
        conflicts = find_conflicts(events)
        assert len(conflicts) == 3  # A-B, A-C, B-C

    def test_point_events_do_not_conflict(self):
        """Events without end time (deadlines) never conflict."""
        events = [
            _ev("Deadline", 10, None),
            _ev("Meeting", 10, 11),
        ]
        assert find_conflicts(events) == []


# ---------------------------------------------------------------------------
# Free Slot Computation
# ---------------------------------------------------------------------------


class TestFreeSlots:
    def test_no_events_full_day_free(self):
        day_start = _utc(0)
        day_end = _utc(0, day=22)  # next day
        slots = find_free_slots([], 60, day_start, day_end)
        assert len(slots) == 1
        assert slots[0] == (day_start, day_end)

    def test_one_event_two_gaps(self):
        day_start = _utc(0)
        day_end = _utc(0, day=22)
        events = [_ev("Meeting", 10, 11)]
        slots = find_free_slots(events, 60, day_start, day_end)
        # 00:00-10:00 (600min) and 11:00-24:00 (780min)
        assert len(slots) == 2
        assert slots[0] == (_utc(0), _utc(10))
        assert slots[1] == (_utc(11), _utc(0, day=22))

    def test_duration_filter(self):
        """Only gaps >= requested duration returned."""
        day_start = _utc(8)
        day_end = _utc(18)
        events = [
            _ev("A", 9, 10),
            _ev("B", 10, 11),  # 8:00-9:00 gap = 60min
        ]
        # Ask for 90 minute slots
        slots = find_free_slots(events, 90, day_start, day_end)
        # 8:00-9:00 is only 60min, too short
        # 11:00-18:00 is 420min
        assert len(slots) == 1
        assert slots[0] == (_utc(11), _utc(18))

    def test_overlapping_busy_periods_merged(self):
        day_start = _utc(8)
        day_end = _utc(18)
        events = [
            _ev("A", 9, 11),
            _ev("B", 10, 12),  # overlaps with A
        ]
        slots = find_free_slots(events, 30, day_start, day_end)
        # Free: 8:00-9:00 (60min) and 12:00-18:00 (360min)
        assert len(slots) == 2
        assert slots[0] == (_utc(8), _utc(9))
        assert slots[1] == (_utc(12), _utc(18))

    def test_point_events_ignored(self):
        """Deadlines (no end time) don't block free slots."""
        day_start = _utc(8)
        day_end = _utc(18)
        events = [_ev("Deadline", 12, None)]
        slots = find_free_slots(events, 60, day_start, day_end)
        assert len(slots) == 1
        assert slots[0] == (day_start, day_end)

    def test_day_completely_booked(self):
        day_start = _utc(8)
        day_end = _utc(18)
        events = [_ev("All day", 8, 18)]
        slots = find_free_slots(events, 30, day_start, day_end)
        assert slots == []


# ---------------------------------------------------------------------------
# Bounds helpers
# ---------------------------------------------------------------------------


class TestBounds:
    def test_day_bounds(self):
        dt = datetime(2026, 3, 21, 14, 30, tzinfo=timezone.utc)
        start, end = day_bounds(dt)
        assert start == datetime(2026, 3, 21, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 3, 22, 0, 0, tzinfo=timezone.utc)

    def test_week_bounds(self):
        dt = datetime(2026, 3, 21, 14, 30, tzinfo=timezone.utc)
        start, end = week_bounds(dt)
        assert start == datetime(2026, 3, 21, 0, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc)
