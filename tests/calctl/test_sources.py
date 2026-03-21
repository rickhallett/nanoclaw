"""Unit tests for calctl sources — nightctl, cronctl, google calendar."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml
import pytest

from halos.calctl.sources import (
    NightctlSource,
    CronctlSource,
    GoogleCalendarSource,
    CalendarEvent,
    _parse_cron_field,
    _cron_next_runs,
    _parse_date_or_datetime,
)


def _utc(hour: int, minute: int = 0, day: int = 21, month: int = 3, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# NightctlSource
# ---------------------------------------------------------------------------


class TestNightctlSource:
    def test_items_with_due_date(self, tmp_path):
        item = {
            "id": "test-001",
            "title": "Fix the thing",
            "kind": "task",
            "status": "open",
            "quadrant": "q1",
            "due": "2026-03-21",
            "tags": [],
            "entities": [],
            "context": "",
            "blocked_by": None,
            "command": None,
            "schedule": None,
            "window": None,
            "depends_on": [],
            "retries": 2,
            "retries_remaining": 2,
            "timeout_secs": 300,
            "plan": None,
            "plan_ref": None,
            "created": "2026-03-20T10:00:00Z",
            "modified": "2026-03-20T10:00:00Z",
            "created_by": "agent",
        }
        (tmp_path / "test-001.yaml").write_text(yaml.dump(item))

        src = NightctlSource(items_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))

        assert len(events) == 1
        assert events[0].title == "Fix the thing"
        assert events[0].source == "nightctl"
        assert events[0].metadata["quadrant"] == "q1"
        assert events[0].metadata["status"] == "open"

    def test_items_without_due_filtered(self, tmp_path):
        item = {
            "id": "test-002",
            "title": "No due date",
            "kind": "task",
            "status": "open",
            "quadrant": "q3",
            "due": None,
            "tags": [],
            "entities": [],
            "context": "",
            "blocked_by": None,
            "command": None,
            "schedule": None,
            "window": None,
            "depends_on": [],
            "retries": 2,
            "retries_remaining": 2,
            "timeout_secs": 300,
            "plan": None,
            "plan_ref": None,
            "created": "2026-03-20T10:00:00Z",
            "modified": "2026-03-20T10:00:00Z",
            "created_by": "agent",
        }
        (tmp_path / "test-002.yaml").write_text(yaml.dump(item))

        src = NightctlSource(items_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert len(events) == 0

    def test_done_items_excluded(self, tmp_path):
        item = {
            "id": "test-003",
            "title": "Already done",
            "kind": "task",
            "status": "done",
            "quadrant": "q2",
            "due": "2026-03-21",
            "tags": [],
            "entities": [],
            "context": "",
            "blocked_by": None,
            "command": None,
            "schedule": None,
            "window": None,
            "depends_on": [],
            "retries": 2,
            "retries_remaining": 2,
            "timeout_secs": 300,
            "plan": None,
            "plan_ref": None,
            "created": "2026-03-20T10:00:00Z",
            "modified": "2026-03-20T10:00:00Z",
            "created_by": "agent",
        }
        (tmp_path / "test-003.yaml").write_text(yaml.dump(item))

        src = NightctlSource(items_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert len(events) == 0

    def test_due_out_of_range(self, tmp_path):
        item = {
            "id": "test-004",
            "title": "Future task",
            "kind": "task",
            "status": "open",
            "quadrant": "q2",
            "due": "2026-04-01",
            "tags": [],
            "entities": [],
            "context": "",
            "blocked_by": None,
            "command": None,
            "schedule": None,
            "window": None,
            "depends_on": [],
            "retries": 2,
            "retries_remaining": 2,
            "timeout_secs": 300,
            "plan": None,
            "plan_ref": None,
            "created": "2026-03-20T10:00:00Z",
            "modified": "2026-03-20T10:00:00Z",
            "created_by": "agent",
        }
        (tmp_path / "test-004.yaml").write_text(yaml.dump(item))

        src = NightctlSource(items_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert len(events) == 0

    def test_empty_directory(self, tmp_path):
        src = NightctlSource(items_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert events == []

    def test_missing_directory(self, tmp_path):
        src = NightctlSource(items_dir=tmp_path / "nonexistent")
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert events == []

    def test_legacy_int_priority_mapped(self, tmp_path):
        item = {
            "id": "test-005",
            "title": "Legacy priority",
            "kind": "task",
            "status": "open",
            "priority": 2,
            "due": "2026-03-21",
            "tags": [],
            "entities": [],
            "context": "",
            "blocked_by": None,
            "command": None,
            "schedule": None,
            "window": None,
            "depends_on": [],
            "retries": 2,
            "retries_remaining": 2,
            "timeout_secs": 300,
            "plan": None,
            "plan_ref": None,
            "created": "2026-03-20T10:00:00Z",
            "modified": "2026-03-20T10:00:00Z",
            "created_by": "agent",
        }
        (tmp_path / "test-005.yaml").write_text(yaml.dump(item))

        src = NightctlSource(items_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert len(events) == 1
        assert events[0].metadata["quadrant"] == "q2"


# ---------------------------------------------------------------------------
# CronctlSource
# ---------------------------------------------------------------------------


class TestCronctlSource:
    def test_enabled_job_produces_events(self, tmp_path):
        job = {
            "id": "morning-briefing",
            "title": "Morning briefing",
            "schedule": "0 6 * * *",
            "command": "hal-briefing morning",
            "enabled": True,
            "tags": [],
        }
        (tmp_path / "morning-briefing.yaml").write_text(yaml.dump(job))

        src = CronctlSource(jobs_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))

        assert len(events) == 1
        assert events[0].title == "Morning briefing"
        assert events[0].source == "cronctl"
        assert events[0].start == _utc(6, 0)

    def test_disabled_job_excluded(self, tmp_path):
        job = {
            "id": "disabled-job",
            "title": "Disabled",
            "schedule": "0 6 * * *",
            "command": "echo nope",
            "enabled": False,
        }
        (tmp_path / "disabled-job.yaml").write_text(yaml.dump(job))

        src = CronctlSource(jobs_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert len(events) == 0

    def test_multiple_runs_in_range(self, tmp_path):
        job = {
            "id": "hourly",
            "title": "Hourly check",
            "schedule": "0 * * * *",
            "command": "check.sh",
            "enabled": True,
        }
        (tmp_path / "hourly.yaml").write_text(yaml.dump(job))

        src = CronctlSource(jobs_dir=tmp_path)
        # 3-hour window
        events = src.fetch(_utc(10), _utc(13))
        assert len(events) == 3
        assert events[0].start == _utc(10)
        assert events[1].start == _utc(11)
        assert events[2].start == _utc(12)

    def test_empty_jobs_dir(self, tmp_path):
        src = CronctlSource(jobs_dir=tmp_path)
        events = src.fetch(_utc(0), _utc(0, day=22))
        assert events == []


# ---------------------------------------------------------------------------
# GoogleCalendarSource
# ---------------------------------------------------------------------------


class TestGoogleCalendarSource:
    def test_graceful_degradation_no_library(self):
        """Should return empty list and warn when google libs unavailable."""
        src = GoogleCalendarSource()
        with patch.dict("sys.modules", {"google.oauth2.credentials": None}):
            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                events = src.fetch(_utc(0), _utc(0, day=22))
                assert events == []

    def test_graceful_degradation_no_credentials(self, tmp_path):
        """Should return empty list when no token file exists."""
        src = GoogleCalendarSource(credentials_dir=tmp_path)
        import warnings
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            events = src.fetch(_utc(0), _utc(0, day=22))
            assert events == []

    def test_parse_gcal_time_datetime(self):
        """Verify parsing of Google Calendar dateTime format."""
        dt = GoogleCalendarSource._parse_gcal_time(
            {"dateTime": "2026-03-21T09:00:00+00:00"}
        )
        assert dt == _utc(9, 0)

    def test_parse_gcal_time_date(self):
        """Verify parsing of all-day event date format."""
        dt = GoogleCalendarSource._parse_gcal_time({"date": "2026-03-21"})
        assert dt == _utc(0, 0)

    def test_parse_gcal_time_empty(self):
        assert GoogleCalendarSource._parse_gcal_time({}) is None
        assert GoogleCalendarSource._parse_gcal_time(None) is None

    def test_mock_fetch_via_public_api(self):
        """Mock fetch() to verify event construction from API-like data."""
        src = GoogleCalendarSource()

        expected = [
            CalendarEvent(
                source="google_calendar",
                title="Team standup",
                start=_utc(9),
                end=_utc(10),
                metadata={
                    "location": "Room 42",
                    "attendees": ["alice@example.com"],
                    "event_id": "evt-001",
                    "html_link": "https://calendar.google.com/event/evt-001",
                },
            ),
        ]

        with patch.object(src, "fetch", return_value=expected):
            events = src.fetch(_utc(0), _utc(0, day=22))

        assert len(events) == 1
        assert events[0].title == "Team standup"
        assert events[0].source == "google_calendar"
        assert events[0].metadata["location"] == "Room 42"


# ---------------------------------------------------------------------------
# Cron parsing helpers
# ---------------------------------------------------------------------------


class TestCronParsing:
    def test_star(self):
        assert _parse_cron_field("*", 0, 59) == set(range(0, 60))

    def test_single_value(self):
        assert _parse_cron_field("5", 0, 59) == {5}

    def test_range(self):
        assert _parse_cron_field("1-5", 0, 59) == {1, 2, 3, 4, 5}

    def test_step(self):
        assert _parse_cron_field("*/15", 0, 59) == {0, 15, 30, 45}

    def test_comma_list(self):
        assert _parse_cron_field("1,5,10", 0, 59) == {1, 5, 10}

    def test_cron_next_runs_daily(self):
        runs = _cron_next_runs("0 6 * * *", _utc(0), _utc(0, day=22))
        assert len(runs) == 1
        assert runs[0] == _utc(6, 0)

    def test_cron_next_runs_every_30_min(self):
        runs = _cron_next_runs("*/30 10 * * *", _utc(10), _utc(11))
        assert len(runs) == 2
        assert runs[0] == _utc(10, 0)
        assert runs[1] == _utc(10, 30)

    def test_invalid_expr(self):
        """Invalid cron expression returns empty list."""
        assert _cron_next_runs("bad", _utc(0), _utc(23)) == []


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------


class TestDateParsing:
    def test_date_only(self):
        dt = _parse_date_or_datetime("2026-03-21")
        assert dt == datetime(2026, 3, 21, tzinfo=timezone.utc)

    def test_iso_datetime_z(self):
        dt = _parse_date_or_datetime("2026-03-21T14:30:00Z")
        assert dt == datetime(2026, 3, 21, 14, 30, tzinfo=timezone.utc)

    def test_none_value(self):
        assert _parse_date_or_datetime(None) is None

    def test_invalid_string(self):
        assert _parse_date_or_datetime("not-a-date") is None

    def test_datetime_passthrough(self):
        dt = datetime(2026, 3, 21, 10, 0, tzinfo=timezone.utc)
        assert _parse_date_or_datetime(dt) == dt
