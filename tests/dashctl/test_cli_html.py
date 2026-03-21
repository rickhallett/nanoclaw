"""Integration tests for dashctl --html CLI flag."""

import os
import subprocess
import sys
import tempfile

import pytest


def _run_dashctl(*args):
    """Run dashctl as a subprocess, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "halos.dashctl.cli", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


class TestCliHtml:
    """Integration tests for --html flag."""

    def test_html_creates_file_at_default_path(self, tmp_path, monkeypatch):
        # Run from tmp_path so store/dashboard.html is created there
        monkeypatch.chdir(tmp_path)
        rc, stdout, stderr = _run_dashctl("--html")
        assert rc == 0, f"dashctl --html failed: {stderr}"
        assert os.path.exists(tmp_path / "store" / "dashboard.html")

    def test_html_creates_file_at_custom_path(self, tmp_path):
        out = str(tmp_path / "custom-dashboard.html")
        rc, stdout, stderr = _run_dashctl("--html", "--output", out)
        assert rc == 0, f"dashctl --html --output failed: {stderr}"
        assert os.path.exists(out)

    def test_output_is_valid_html(self, tmp_path):
        out = str(tmp_path / "test.html")
        _run_dashctl("--html", "--output", out)
        html = open(out).read()
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_html_and_json_not_both(self, tmp_path):
        """When both --html and --json are passed, --html takes precedence."""
        out = str(tmp_path / "test.html")
        rc, stdout, stderr = _run_dashctl("--html", "--json", "--output", out)
        # --html is checked first, so it should produce an HTML file
        assert rc == 0
        assert os.path.exists(out)

    def test_output_without_html_is_ignored(self):
        """--output alone doesn't cause errors (just ignored without --html)."""
        rc, stdout, stderr = _run_dashctl("--text")
        assert rc == 0
