"""Tests for statusctl briefing integration."""

from unittest.mock import patch

from halos.statusctl.checks import CheckResult


class TestTextSummary:
    def test_format(self):
        fake_report = {
            "grade": "HEALTHY",
            "checks": [],
            "metrics": {
                "running": 2,
                "active": 3,
                "error_count_24h": 5,
                "cpu_pct": 12,
                "ram_pct": 26,
                "disk_pct": 45,
            },
        }

        with patch("halos.statusctl.briefing.health_report", return_value=fake_report):
            from halos.statusctl.briefing import text_summary
            result = text_summary()

        assert result.startswith("statusctl: HEALTHY")
        assert "2 containers" in result
        assert "3 sessions" in result
        assert "5 errors/24h" in result
        assert "CPU 12%" in result
        assert "RAM 26%" in result
        assert "Disk 45%" in result

    def test_degraded_format(self):
        fake_report = {
            "grade": "DEGRADED",
            "checks": [],
            "metrics": {
                "running": 0,
                "active": 0,
                "error_count_24h": 0,
                "cpu_pct": 0,
                "ram_pct": 0,
                "disk_pct": 0,
            },
        }

        with patch("halos.statusctl.briefing.health_report", return_value=fake_report):
            from halos.statusctl.briefing import text_summary
            result = text_summary()

        assert "DEGRADED" in result

    def test_missing_metrics_use_defaults(self):
        fake_report = {
            "grade": "DOWN",
            "checks": [],
            "metrics": {},
        }

        with patch("halos.statusctl.briefing.health_report", return_value=fake_report):
            from halos.statusctl.briefing import text_summary
            result = text_summary()

        # Should not crash, uses defaults
        assert "statusctl: DOWN" in result
        assert "0 containers" in result
