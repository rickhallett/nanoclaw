"""Tests for ledgerctl reporting engine."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from halos.ledgerctl.journal import Entry, Posting, append_entries
from halos.ledgerctl.reports import balance, cashflow, categories, income, search


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_journal():
    return FIXTURES / "sample_journal.journal"


@pytest.fixture
def tmp_journal(tmp_path):
    return tmp_path / "test.journal"


@pytest.fixture
def populated_journal(tmp_journal):
    """Create a journal with known entries for deterministic testing."""
    entries = [
        Entry(date=date(2026, 3, 1), payee="Countdown", postings=[
            Posting(account="expenses:food", amount=42.50),
            Posting(account="assets:bank:anz:checking"),
        ]),
        Entry(date=date(2026, 3, 2), payee="BP 2GO", postings=[
            Posting(account="expenses:transport", amount=65.00),
            Posting(account="assets:bank:anz:checking"),
        ]),
        Entry(date=date(2026, 3, 3), payee="Employer", postings=[
            Posting(account="assets:bank:anz:checking", amount=5000.00),
            Posting(account="income:salary"),
        ]),
        Entry(date=date(2026, 3, 4), payee="Netflix", postings=[
            Posting(account="expenses:entertainment", amount=19.99),
            Posting(account="assets:bank:anz:checking"),
        ]),
    ]
    append_entries(entries, path=tmp_journal)
    return tmp_journal


class TestBalance:
    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_balance_from_fixture(self, mock_hl, sample_journal):
        result = balance(journal=sample_journal)
        assert isinstance(result, str)
        assert "expenses:food" in result

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_balance_json(self, mock_hl, populated_journal):
        result = balance(journal=populated_journal, as_json=True)
        assert isinstance(result, dict)
        assert "expenses:food" in result
        assert result["expenses:food"] == 42.50
        assert result["expenses:transport"] == 65.00

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_balance_empty_journal(self, mock_hl, tmp_journal):
        result = balance(journal=tmp_journal)
        assert "No transactions" in result

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_balance_json_empty(self, mock_hl, tmp_journal):
        result = balance(journal=tmp_journal, as_json=True)
        assert result == {}


class TestIncome:
    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_income_basic(self, mock_hl, populated_journal):
        result = income(journal=populated_journal, as_json=True)
        assert isinstance(result, dict)
        assert "income:salary" in result
        assert result["income:salary"] == 5000.00

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_income_text(self, mock_hl, populated_journal):
        result = income(journal=populated_journal)
        assert "income:salary" in result
        assert "5,000.00" in result

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_income_empty(self, mock_hl, tmp_journal):
        result = income(journal=tmp_journal)
        assert "No income" in result


class TestCashflow:
    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_cashflow_basic(self, mock_hl, populated_journal):
        result = cashflow(journal=populated_journal, as_json=True)
        assert result["income"] == 5000.00
        assert result["expenses"] == pytest.approx(42.50 + 65.00 + 19.99)
        assert result["net"] == pytest.approx(5000.00 - 42.50 - 65.00 - 19.99)

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_cashflow_text(self, mock_hl, populated_journal):
        result = cashflow(journal=populated_journal)
        assert "Income:" in result
        assert "Expenses:" in result
        assert "Net:" in result

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_cashflow_empty(self, mock_hl, tmp_journal):
        result = cashflow(journal=tmp_journal, as_json=True)
        assert result["income"] == 0
        assert result["expenses"] == 0
        assert result["net"] == 0


class TestCategories:
    def test_categories_basic(self, populated_journal):
        cats = categories(journal=populated_journal)
        assert "expenses:food" in cats
        assert "expenses:transport" in cats
        assert "expenses:entertainment" in cats

    def test_categories_sorted_by_amount(self, populated_journal):
        cats = categories(journal=populated_journal)
        amounts = list(cats.values())
        assert amounts == sorted(amounts, reverse=True)

    def test_categories_empty(self, tmp_journal):
        cats = categories(journal=tmp_journal)
        assert cats == {}


class TestSearch:
    def test_search_by_payee(self, sample_journal):
        results = search("Countdown", journal=sample_journal)
        assert len(results) >= 1
        assert all("Countdown" in r["payee"] for r in results)

    def test_search_regex(self, sample_journal):
        results = search("BP|Z Energy", journal=sample_journal)
        assert len(results) >= 2

    def test_search_no_match(self, sample_journal):
        results = search("XXXXNOTFOUNDXXXX", journal=sample_journal)
        assert results == []

    def test_search_result_format(self, sample_journal):
        results = search("Countdown", journal=sample_journal)
        r = results[0]
        assert "date" in r
        assert "payee" in r
        assert "postings" in r
        assert isinstance(r["postings"], list)


class TestPeriodFiltering:
    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_yearly_filter(self, mock_hl, sample_journal):
        """Yearly filter should include all 2026 entries."""
        result = balance(journal=sample_journal, period="yearly", as_json=True)
        # All entries are in 2026, so yearly should include everything
        assert len(result) > 0
