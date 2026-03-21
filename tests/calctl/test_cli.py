"""Integration tests for calctl CLI."""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from halos.calctl.cli import build_parser, cmd_today, cmd_conflicts, cmd_free, cmd_summary
from halos.calctl.sources import CalendarEvent, Source


def _utc(hour: int, minute: int = 0, day: int = 21) -> datetime:
    return datetime(2026, 3, day, hour, minute, tzinfo=timezone.utc)


def _ev(title, start_h, end_h=None, source="test"):
    start = _utc(start_h)
    end = _utc(end_h) if end_h is not None else None
    return CalendarEvent(source=source, title=title, start=start, end=end)


class StubSource(Source):
    def __init__(self, events):
        self._events = events

    def fetch(self, start, end):
        return [e for e in self._events if start <= e.start < end]


class TestCLIParsing:
    def test_today_command(self):
        parser = build_parser()
        args = parser.parse_args(["today", "--json"])
        assert args.command == "today"
        assert args.json_out is True

    def test_week_command(self):
        parser = build_parser()
        args = parser.parse_args(["week"])
        assert args.command == "week"

    def test_range_command(self):
        parser = build_parser()
        args = parser.parse_args(["range", "--from", "2026-03-21", "--to", "2026-03-28"])
        assert args.command == "range"
        assert args.from_date == "2026-03-21"
        assert args.to_date == "2026-03-28"

    def test_conflicts_command(self):
        parser = build_parser()
        args = parser.parse_args(["conflicts"])
        assert args.command == "conflicts"

    def test_free_command(self):
        parser = build_parser()
        args = parser.parse_args(["free", "--duration", "60"])
        assert args.command == "free"
        assert args.duration == 60

    def test_free_with_date(self):
        parser = build_parser()
        args = parser.parse_args(["free", "--duration", "30", "--date", "2026-03-22"])
        assert args.date == "2026-03-22"

    def test_summary_command(self):
        parser = build_parser()
        args = parser.parse_args(["summary"])
        assert args.command == "summary"


class TestCmdToday:
    def test_json_output(self, capsys):
        stub_events = [_ev("Meeting", 9, 10, "google_calendar")]
        stub = StubSource(stub_events)

        with patch("halos.calctl.cli._default_sources", return_value=[stub]):
            parser = build_parser()
            args = parser.parse_args(["today", "--json"])
            rc = cmd_today(args)

        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Meeting"
        assert data[0]["source"] == "google_calendar"


class TestCmdConflicts:
    def test_with_overlapping_events(self, capsys):
        events = [
            _ev("A", 9, 11, "google_calendar"),
            _ev("B", 10, 12, "google_calendar"),
        ]
        stub = StubSource(events)

        with patch("halos.calctl.cli._default_sources", return_value=[stub]):
            parser = build_parser()
            args = parser.parse_args(["conflicts"])
            rc = cmd_conflicts(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "1 conflict" in out
        assert "A" in out
        assert "B" in out

    def test_no_conflicts(self, capsys):
        events = [
            _ev("A", 9, 10, "google_calendar"),
            _ev("B", 10, 11, "google_calendar"),
        ]
        stub = StubSource(events)

        with patch("halos.calctl.cli._default_sources", return_value=[stub]):
            parser = build_parser()
            args = parser.parse_args(["conflicts"])
            rc = cmd_conflicts(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "No conflicts" in out


class TestCmdFree:
    def test_finds_slots_json(self, capsys):
        events = [_ev("Busy", 10, 12, "google_calendar")]
        stub = StubSource(events)

        with patch("halos.calctl.cli._default_sources", return_value=[stub]):
            parser = build_parser()
            args = parser.parse_args(["free", "--duration", "60", "--date", "2026-03-21", "--json"])
            rc = cmd_free(args)

        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) >= 1
        for slot in data:
            assert "start" in slot
            assert "end" in slot
            assert "duration_mins" in slot
            assert slot["duration_mins"] >= 60


class TestCmdSummary:
    def test_output_format(self, capsys):
        from halos.calctl import briefing

        def mock_summary():
            return "calctl: 1 event, 1 task due, 1 cron job | next: Standup at 09:00"

        with patch.object(briefing, "text_summary", mock_summary), \
             patch("halos.calctl.cli.text_summary", mock_summary):
            parser = build_parser()
            args = parser.parse_args(["summary"])
            rc = cmd_summary(args)

        assert rc == 0
        out = capsys.readouterr().out.strip()
        assert out.startswith("calctl:")


class TestExitCodes:
    def test_today_returns_zero(self):
        stub = StubSource([])
        with patch("halos.calctl.cli._default_sources", return_value=[stub]):
            parser = build_parser()
            args = parser.parse_args(["today"])
            assert cmd_today(args) == 0
