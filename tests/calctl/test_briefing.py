"""Unit tests for calctl briefing integration."""

from datetime import datetime, timezone
from unittest.mock import patch

from halos.calctl.briefing import text_summary
from halos.calctl.sources import CalendarEvent, Source


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 3, 21, hour, minute, tzinfo=timezone.utc)


class StubSource(Source):
    def __init__(self, events):
        self._events = events

    def fetch(self, start, end):
        return [e for e in self._events if start <= e.start < end]


class TestTextSummary:
    def test_no_events(self):
        stub = StubSource([])
        with patch("halos.calctl.briefing.NightctlSource", return_value=stub), \
             patch("halos.calctl.briefing.CronctlSource", return_value=stub), \
             patch("halos.calctl.briefing.GoogleCalendarSource", return_value=stub):
            result = text_summary()
        assert result == "calctl: no events today"

    def test_mixed_sources(self):
        gcal_events = [
            CalendarEvent("google_calendar", "Standup", _utc(9), _utc(10)),
            CalendarEvent("google_calendar", "1:1", _utc(14), _utc(15)),
        ]
        nc_events = [
            CalendarEvent("nightctl", "Fix bug", _utc(12)),
        ]
        cc_events = [
            CalendarEvent("cronctl", "Backup", _utc(2)),
        ]

        gcal_stub = StubSource(gcal_events)
        nc_stub = StubSource(nc_events)
        cc_stub = StubSource(cc_events)

        with patch("halos.calctl.briefing.NightctlSource", return_value=nc_stub), \
             patch("halos.calctl.briefing.CronctlSource", return_value=cc_stub), \
             patch("halos.calctl.briefing.GoogleCalendarSource", return_value=gcal_stub):
            result = text_summary()

        assert result.startswith("calctl:")
        assert "2 events" in result
        assert "1 task due" in result
        assert "1 cron job" in result

    def test_next_event_included(self):
        """The summary should include the next upcoming event."""
        # Set 'now' to before the first event
        now = _utc(8)
        events = [
            CalendarEvent("google_calendar", "Team standup", _utc(9), _utc(10)),
        ]
        stub = StubSource(events)

        with patch("halos.calctl.briefing.NightctlSource", return_value=stub), \
             patch("halos.calctl.briefing.CronctlSource", return_value=stub), \
             patch("halos.calctl.briefing.GoogleCalendarSource", return_value=stub), \
             patch("halos.calctl.briefing.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = text_summary()

        assert "next:" in result
        assert "Team standup" in result
        assert "09:00" in result

    def test_singular_forms(self):
        gcal_events = [
            CalendarEvent("google_calendar", "Solo meeting", _utc(10), _utc(11)),
        ]
        gcal_stub = StubSource(gcal_events)
        empty_stub = StubSource([])

        with patch("halos.calctl.briefing.NightctlSource", return_value=empty_stub), \
             patch("halos.calctl.briefing.CronctlSource", return_value=empty_stub), \
             patch("halos.calctl.briefing.GoogleCalendarSource", return_value=gcal_stub):
            result = text_summary()

        assert "1 event" in result
        # Should not say "1 events"
        assert "1 events" not in result
