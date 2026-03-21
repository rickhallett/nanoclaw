"""Integration tests for statusctl CLI."""

import json
import subprocess
import sys
from unittest.mock import patch

import pytest

from halos.statusctl.checks import CheckResult


def _mock_health_report(grade="HEALTHY", checks=None, metrics=None):
    """Create a mock health_report function."""
    if checks is None:
        checks = [
            {"name": "nanoclaw", "status": "ok", "message": "running", "metrics": {}},
            {"name": "docker", "status": "ok", "message": "running", "metrics": {}},
        ]
    if metrics is None:
        metrics = {
            "running": 2, "active": 3, "error_count_24h": 1,
            "cpu_pct": 10, "ram_pct": 25, "disk_pct": 40,
        }
    return {"grade": grade, "checks": checks, "metrics": metrics}


class TestCheckCommand:
    def test_healthy_exit_0(self):
        with patch("halos.statusctl.engine.health_report",
                   return_value=_mock_health_report("HEALTHY")):
            from halos.statusctl.cli import cmd_check
            from types import SimpleNamespace
            rc = cmd_check(SimpleNamespace())
        assert rc == 0

    def test_degraded_exit_1(self):
        report = _mock_health_report("DEGRADED", checks=[
            {"name": "sessions", "status": "warn", "message": "timeouts", "metrics": {}},
        ])
        with patch("halos.statusctl.engine.health_report", return_value=report):
            from halos.statusctl.cli import cmd_check
            from types import SimpleNamespace
            rc = cmd_check(SimpleNamespace())
        assert rc == 1

    def test_down_exit_1(self):
        report = _mock_health_report("DOWN", checks=[
            {"name": "nanoclaw", "status": "fail", "message": "not running", "metrics": {}},
        ])
        with patch("halos.statusctl.engine.health_report", return_value=report):
            from halos.statusctl.cli import cmd_check
            from types import SimpleNamespace
            rc = cmd_check(SimpleNamespace())
        assert rc == 1


class TestMetricsCommand:
    def test_json_output(self, capsys):
        fake_results = [
            CheckResult(name="cpu", status="ok", message="5%",
                        metrics={"cpu_pct": 5}),
            CheckResult(name="memory", status="ok", message="4/16 GB",
                        metrics={"ram_pct": 25}),
            CheckResult(name="disk", status="ok", message="45%",
                        metrics={"disk_pct": 45}),
            CheckResult(name="uptime", status="ok", message="3d 12h",
                        metrics={"uptime_days": 3}),
        ]

        with patch("halos.statusctl.checks.HostCheck.run", return_value=fake_results):
            from halos.statusctl.cli import cmd_metrics
            from types import SimpleNamespace
            rc = cmd_metrics(SimpleNamespace(json_out=True))

        assert rc == 0
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "cpu" in data
        assert "disk" in data

    def test_text_output(self, capsys):
        fake_results = [
            CheckResult(name="cpu", status="ok", message="5%", metrics={}),
        ]
        with patch("halos.statusctl.checks.HostCheck.run", return_value=fake_results):
            from halos.statusctl.cli import cmd_metrics
            from types import SimpleNamespace
            rc = cmd_metrics(SimpleNamespace(json_out=False))

        assert rc == 0
        output = capsys.readouterr().out
        assert "cpu" in output


class TestDefaultOutput:
    def test_rich_rendering_doesnt_crash(self, capsys):
        """Verify the default Rich output doesn't raise."""
        with patch("halos.statusctl.engine.health_report",
                   return_value=_mock_health_report()):
            from halos.statusctl.cli import cmd_default
            from types import SimpleNamespace
            # Should not raise
            cmd_default(SimpleNamespace(json_out=False))

    def test_json_output(self, capsys):
        with patch("halos.statusctl.engine.health_report",
                   return_value=_mock_health_report()):
            from halos.statusctl.cli import cmd_default
            from types import SimpleNamespace
            cmd_default(SimpleNamespace(json_out=True))

        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["grade"] == "HEALTHY"
