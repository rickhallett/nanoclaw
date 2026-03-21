"""Smoke test: runs dashctl --html against real data and verifies output."""

import os
import subprocess
import sys
import tempfile

import pytest


@pytest.mark.smoke
class TestSmoke:
    """Smoke tests that exercise the full pipeline."""

    def test_html_export_produces_nonempty_file(self, tmp_path):
        out = str(tmp_path / "smoke-dashboard.html")
        result = subprocess.run(
            [sys.executable, "-m", "halos.dashctl.cli", "--html", "--output", out],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert os.path.exists(out)
        size = os.path.getsize(out)
        assert size > 100, f"HTML file suspiciously small: {size} bytes"

    def test_html_contains_dashboard_structure(self, tmp_path):
        out = str(tmp_path / "smoke-dashboard.html")
        subprocess.run(
            [sys.executable, "-m", "halos.dashctl.cli", "--html", "--output", out],
            capture_output=True,
            text=True,
            timeout=30,
        )
        html = open(out).read()
        # Should contain the header panel text
        assert "HAL METRICS" in html or "NanoClaw Dashboard" in html
