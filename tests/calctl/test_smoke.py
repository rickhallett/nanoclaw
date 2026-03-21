"""Smoke tests for calctl — runs against real data, verifies no crashes."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestSmoke:
    def test_today_does_not_crash(self):
        """Run calctl today against real nightctl items in queue/items/."""
        from halos.calctl.sources import NightctlSource
        from halos.calctl.engine import merge_events, day_bounds

        items_dir = PROJECT_ROOT / "queue" / "items"
        src = NightctlSource(items_dir=items_dir)
        start, end = day_bounds()
        # Should not raise
        events = src.fetch(start, end)
        assert isinstance(events, list)

    def test_today_json_valid(self):
        """Verify --json output is parseable JSON."""
        from halos.calctl.cli import build_parser, cmd_today
        from halos.calctl.sources import NightctlSource, Source
        from unittest.mock import patch

        items_dir = PROJECT_ROOT / "queue" / "items"

        class RealNightctl(Source):
            def fetch(self, start, end):
                return NightctlSource(items_dir=items_dir).fetch(start, end)

        # Stub out gcal and cronctl, use real nightctl
        empty_source = type("E", (Source,), {"fetch": lambda s, a, b: []})()
        sources = [RealNightctl(), empty_source, empty_source]

        with patch("halos.calctl.cli._default_sources", return_value=sources):
            import io
            from contextlib import redirect_stdout

            parser = build_parser()
            args = parser.parse_args(["today", "--json"])
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cmd_today(args)

            assert rc == 0
            output = buf.getvalue()
            data = json.loads(output)
            assert isinstance(data, list)

    def test_cronctl_source_real_jobs(self):
        """Load real cronctl jobs if they exist."""
        from halos.calctl.sources import CronctlSource
        from halos.calctl.engine import day_bounds

        jobs_dir = PROJECT_ROOT / "cron" / "jobs"
        src = CronctlSource(jobs_dir=jobs_dir)
        start, end = day_bounds()
        # Should not raise even if jobs_dir doesn't exist
        events = src.fetch(start, end)
        assert isinstance(events, list)

    def test_google_calendar_graceful(self):
        """GoogleCalendarSource should not crash when credentials are missing."""
        from halos.calctl.sources import GoogleCalendarSource
        from halos.calctl.engine import day_bounds

        src = GoogleCalendarSource()
        start, end = day_bounds()
        # Should return empty list, not crash
        events = src.fetch(start, end)
        assert isinstance(events, list)
