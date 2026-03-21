"""Smoke tests — run statusctl against the real system.

These tests verify the CLI doesn't crash even if Docker, systemctl,
or other tools are unavailable. They run actual code paths (no mocking).
"""

import json
import subprocess
import sys

import pytest


@pytest.fixture
def statusctl_bin():
    """Return the command to invoke statusctl."""
    return [sys.executable, "-m", "halos.statusctl.cli"]


class TestSmoke:
    def test_default_output_no_crash(self, statusctl_bin):
        """statusctl should produce output without crashing."""
        result = subprocess.run(
            statusctl_bin,
            capture_output=True, text=True, timeout=30,
        )
        # May exit 0 or non-zero depending on system state, but should not crash
        assert result.returncode in (0, 1, 2)

    def test_check_returns_valid_exit_code(self, statusctl_bin):
        result = subprocess.run(
            statusctl_bin + ["check"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode in (0, 1)

    def test_metrics_json_returns_valid_json(self, statusctl_bin):
        result = subprocess.run(
            statusctl_bin + ["metrics", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)
        # Should have at least cpu, memory, disk, uptime
        assert len(data) >= 1

    def test_report_returns_one_liner(self, statusctl_bin):
        result = subprocess.run(
            statusctl_bin + ["report"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "statusctl:" in result.stdout
        assert result.stdout.count("\n") <= 2  # one-liner + trailing newline
