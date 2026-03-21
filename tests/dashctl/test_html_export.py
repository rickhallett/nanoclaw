"""Unit tests for dashctl HTML export."""

import os
import tempfile

import pytest
from rich.panel import Panel
from rich.text import Text

from halos.dashctl.html_export import render_html


def _sample_panels():
    """Return a small list of Rich renderables for testing."""
    return [
        Panel(Text("Hello world", style="bold green"), title="Test Panel"),
        Panel("Second panel content", title="Stats"),
    ]


class TestRenderHtml:
    """Tests for render_html()."""

    def test_produces_valid_html_structure(self, tmp_path):
        out = str(tmp_path / "test.html")
        render_html(_sample_panels(), out)
        html = open(out).read()
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "<body>" in html
        assert "</body>" in html

    def test_contains_inline_styles(self, tmp_path):
        out = str(tmp_path / "out.html")
        render_html(_sample_panels(), out)
        html = open(out).read()
        # Rich inline styles show up as style= attributes in spans
        assert "style=" in html

    def test_dark_background_present(self, tmp_path):
        out = str(tmp_path / "out.html")
        render_html(_sample_panels(), out)
        html = open(out).read()
        assert "#1a1a2e" in html

    def test_timestamp_in_title(self, tmp_path):
        out = str(tmp_path / "out.html")
        render_html(_sample_panels(), out)
        html = open(out).read()
        assert "NanoClaw Dashboard" in html
        # Title should contain a UTC timestamp
        assert "UTC" in html

    def test_font_stack_present(self, tmp_path):
        out = str(tmp_path / "out.html")
        render_html(_sample_panels(), out)
        html = open(out).read()
        assert "Geist Mono" in html
        assert "JetBrains Mono" in html

    def test_empty_panels_produces_valid_html(self, tmp_path):
        out = str(tmp_path / "empty.html")
        render_html([], out)
        html = open(out).read()
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_creates_parent_directories(self, tmp_path):
        out = str(tmp_path / "nested" / "deep" / "test.html")
        render_html(_sample_panels(), out)
        assert os.path.exists(out)

    def test_returns_absolute_path(self, tmp_path):
        out = str(tmp_path / "out.html")
        result = render_html(_sample_panels(), out)
        assert os.path.isabs(result)
        assert result.endswith("out.html")

    def test_panel_content_appears_in_html(self, tmp_path):
        out = str(tmp_path / "out.html")
        render_html([Panel("unique-sentinel-text")], out)
        html = open(out).read()
        assert "unique-sentinel-text" in html
