"""Smoke tests for ledgerctl — end-to-end workflows."""

import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from halos.ledgerctl.journal import (
    Entry,
    Posting,
    append_entries,
    read_journal,
)
from halos.ledgerctl.importer import import_csv
from halos.ledgerctl.reports import balance, cashflow
from halos.ledgerctl.rules import add_rule, save_rules
from halos.ledgerctl.briefing import text_summary


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_store(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    return store


class TestFullWorkflow:
    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_manual_entries_then_balance(self, mock_hl, tmp_store):
        """Create a fresh journal, add 5 transactions, run balance."""
        journal = tmp_store / "ledger.journal"

        entries = [
            Entry(date=date(2026, 3, i + 1), payee=f"Shop {i + 1}", postings=[
                Posting(account="expenses:food", amount=float((i + 1) * 10)),
                Posting(account="assets:bank:checking"),
            ])
            for i in range(5)
        ]
        append_entries(entries, path=journal)

        # Verify journal
        loaded = read_journal(journal)
        assert len(loaded) == 5

        # Run balance
        result = balance(journal=journal, as_json=True)
        assert result["expenses:food"] == 10 + 20 + 30 + 40 + 50

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_import_categorise_balance(self, mock_hl, tmp_store):
        """Import a fixture CSV, verify categorisation, check balance."""
        journal = tmp_store / "ledger.journal"
        rules_file = tmp_store / "ledger-rules.yaml"

        # Set up rules
        save_rules([
            {"pattern": "COUNTDOWN|NEW WORLD|PAKNSAVE", "account": "expenses:food"},
            {"pattern": "BP 2GO|Z ENERGY", "account": "expenses:transport"},
            {"pattern": "VODAFONE", "account": "expenses:phone"},
            {"pattern": "EMPLOYER", "account": "income:salary"},
            {"pattern": "SPOTIFY", "account": "expenses:entertainment"},
        ], path=rules_file)

        # Import
        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal,
            rules_path=rules_file,
        )
        assert len(entries) == 10

        # Verify balance
        bal = balance(journal=journal, as_json=True)
        assert "expenses:food" in bal
        assert "expenses:transport" in bal

        # Verify cashflow
        cf = cashflow(journal=journal, as_json=True)
        assert cf["income"] == 5000.00
        assert cf["expenses"] > 0
        assert cf["net"] > 0  # Should be positive (5000 income vs ~400 expenses)

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_import_then_summary(self, mock_hl, tmp_store):
        """Import CSV then generate briefing summary."""
        journal = tmp_store / "ledger.journal"
        rules_file = tmp_store / "ledger-rules.yaml"

        save_rules([
            {"pattern": "COUNTDOWN", "account": "expenses:food"},
            {"pattern": "EMPLOYER", "account": "income:salary"},
        ], path=rules_file)

        import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal,
            rules_path=rules_file,
        )

        summary = text_summary(journal=journal, period="yearly")
        assert summary.startswith("ledgerctl:")
        assert "spent" in summary

    @patch("halos.ledgerctl.reports._has_hledger", return_value=False)
    def test_no_duplicate_on_reimport(self, mock_hl, tmp_store):
        """Full workflow: import, reimport, verify no duplication."""
        journal = tmp_store / "ledger.journal"
        rules_file = tmp_store / "ledger-rules.yaml"

        first = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal,
            rules_path=rules_file,
        )
        assert len(first) == 10

        second = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal,
            rules_path=rules_file,
        )
        assert len(second) == 0

        entries = read_journal(journal)
        assert len(entries) == 10


class TestBankModuleDiscovery:
    def test_all_banks_registered(self):
        from halos.ledgerctl.banks import all_banks
        banks = all_banks()
        assert "anz" in banks
        assert "wise" in banks

    def test_bank_has_required_attrs(self):
        from halos.ledgerctl.banks import get
        for name in ("anz", "wise"):
            bank = get(name)
            assert bank is not None
            assert hasattr(bank, "COLUMNS")
            assert hasattr(bank, "DATE_FORMAT")
            assert hasattr(bank, "DEFAULT_ACCOUNT")
            assert isinstance(bank.COLUMNS, dict)
            assert "date" in bank.COLUMNS
            assert "amount" in bank.COLUMNS
            assert "payee" in bank.COLUMNS
