"""Tests for changoctl engine — sustain ritual and text_summary."""

import pytest
from unittest.mock import patch

from halos.changoctl.engine import sustain, text_summary
from halos.changoctl.store import restock, add_quote


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_changoctl.db"


class TestSustain:
    def test_sustain_with_stock(self, tmp_db):
        restock("espresso", quantity=3, db_path=tmp_db)
        result = sustain("grind", db_path=tmp_db)
        assert result["item"] == "espresso"
        assert result["stock"] == 2
        assert result["mood"] == "grind"
        assert result["action"].startswith("*")
        assert result["action"].endswith("*")
        assert result["out_of_stock"] is False

    def test_sustain_with_quote(self, tmp_db):
        restock("lagavulin", quantity=1, db_path=tmp_db)
        add_quote(
            "The margins are everything.",
            category="philosophical",
            db_path=tmp_db,
        )
        result = sustain("burnt-out", db_path=tmp_db)
        assert result["quote"] is not None
        assert result["quote"]["text"] == "The margins are everything."

    def test_sustain_no_matching_quote(self, tmp_db):
        restock("stimpacks", quantity=1, db_path=tmp_db)
        result = sustain("locked-in", db_path=tmp_db)
        assert result["quote"] is None

    def test_sustain_fallback_item(self, tmp_db):
        """Primary item empty, falls back to whatever has stock."""
        restock("lagavulin", quantity=2, db_path=tmp_db)
        result = sustain("grind", db_path=tmp_db)
        assert result["item"] == "lagavulin"
        assert result["out_of_stock"] is False

    def test_sustain_all_empty(self, tmp_db):
        """Everything out of stock — still works, logs qty 0."""
        result = sustain("fire", db_path=tmp_db)
        assert result["out_of_stock"] is True
        assert result["item"] == "nos"
        assert result["stock"] == 0

    def test_sustain_invalid_mood(self, tmp_db):
        with pytest.raises(ValueError, match="invalid mood"):
            sustain("chill", db_path=tmp_db)

    def test_sustain_formatted_output(self, tmp_db):
        restock("nos", quantity=1, db_path=tmp_db)
        add_quote("Ship it.", category="sardonic", db_path=tmp_db)
        result = sustain("fire", db_path=tmp_db)
        output = result["formatted"]
        assert "*" in output
        assert "Ship it." in output
        assert "nos:" in output
        assert "fire" in output


class TestTextSummary:
    def test_text_summary_empty(self, tmp_db):
        summary = text_summary(db_path=tmp_db)
        assert "espresso: 0" in summary
        assert "lagavulin: 0" in summary

    def test_text_summary_with_stock(self, tmp_db):
        restock("espresso", quantity=5, db_path=tmp_db)
        restock("lagavulin", quantity=2, db_path=tmp_db)
        summary = text_summary(db_path=tmp_db)
        assert "espresso: 5" in summary
        assert "lagavulin: 2" in summary

    def test_text_summary_includes_quote_count(self, tmp_db):
        add_quote("Test line.", category="sardonic", db_path=tmp_db)
        summary = text_summary(db_path=tmp_db)
        assert "1 quote" in summary
