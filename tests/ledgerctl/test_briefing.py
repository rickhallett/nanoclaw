"""Tests for ledgerctl briefing integration."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from halos.ledgerctl.briefing import text_summary
from halos.ledgerctl.journal import Entry, Posting, append_entries


@pytest.fixture
def populated_journal(tmp_path):
    """Create a journal with known entries."""
    journal = tmp_path / "test.journal"
    entries = [
        Entry(date=date(2026, 3, 1), payee="Countdown", postings=[
            Posting(account="expenses:food", amount=380.00),
            Posting(account="assets:bank:anz:checking"),
        ]),
        Entry(date=date(2026, 3, 2), payee="BP 2GO", postings=[
            Posting(account="expenses:transport", amount=210.00),
            Posting(account="assets:bank:anz:checking"),
        ]),
        Entry(date=date(2026, 3, 3), payee="Random Shop", postings=[
            Posting(account="expenses:misc", amount=650.00),
            Posting(account="assets:bank:anz:checking"),
        ]),
        Entry(date=date(2026, 3, 1), payee="Employer", postings=[
            Posting(account="assets:bank:anz:checking", amount=5000.00),
            Posting(account="income:salary"),
        ]),
    ]
    append_entries(entries, path=journal)
    return journal


class TestTextSummary:
    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_summary_format(self, mock_hl, populated_journal):
        summary = text_summary(journal=populated_journal, period="yearly")
        assert summary.startswith("ledgerctl:")
        assert "spent" in summary
        assert "income" in summary
        assert "savings rate" in summary

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_summary_includes_categories(self, mock_hl, populated_journal):
        summary = text_summary(journal=populated_journal, period="yearly")
        # Should include top categories
        assert "food" in summary or "misc" in summary or "transport" in summary

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_summary_empty_journal(self, mock_hl, tmp_path):
        journal = tmp_path / "empty.journal"
        summary = text_summary(journal=journal)
        assert summary == ""

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_summary_savings_rate(self, mock_hl, populated_journal):
        summary = text_summary(journal=populated_journal, period="yearly")
        # Income 5000, expenses 1240, savings rate ~75%
        assert "savings rate:" in summary
