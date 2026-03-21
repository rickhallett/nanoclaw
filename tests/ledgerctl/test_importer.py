"""Tests for ledgerctl CSV importer."""

from datetime import date
from pathlib import Path

import pytest

from halos.ledgerctl.importer import import_csv
from halos.ledgerctl.journal import read_journal, append_entries, Entry, Posting
from halos.ledgerctl.rules import save_rules


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_store(tmp_path):
    """Set up a temporary store directory."""
    store = tmp_path / "store"
    store.mkdir()
    return store


@pytest.fixture
def journal_file(tmp_store):
    return tmp_store / "ledger.journal"


@pytest.fixture
def rules_file(tmp_store):
    return tmp_store / "ledger-rules.yaml"


class TestANZImport:
    def test_import_basic(self, journal_file, rules_file):
        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        assert len(entries) == 10
        # Verify entries were written
        journal = read_journal(journal_file)
        assert len(journal) == 10

    def test_import_dates(self, journal_file, rules_file):
        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        # First row: 21/03/2026
        assert entries[0].date == date(2026, 3, 21)

    def test_import_amounts(self, journal_file, rules_file):
        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        # Countdown: $42.50 expense
        countdown = entries[0]
        assert any(p.amount == 42.50 for p in countdown.postings)

    def test_import_payees(self, journal_file, rules_file):
        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        payees = [e.payee for e in entries]
        assert "COUNTDOWN" in payees
        assert "EMPLOYER LTD" in payees

    def test_import_with_rules(self, journal_file, rules_file):
        """Categorisation rules should be applied during import."""
        save_rules([
            {"pattern": "COUNTDOWN|PAKNSAVE|NEW WORLD", "account": "expenses:food"},
            {"pattern": "BP 2GO|Z ENERGY", "account": "expenses:transport"},
        ], path=rules_file)

        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )

        # Countdown should be categorised as food
        countdown = entries[0]
        assert any(p.account == "expenses:food" for p in countdown.postings)

    def test_uncategorised_fallback(self, journal_file, rules_file):
        """Unmatched transactions go to expenses:uncategorised."""
        # No rules = everything uncategorised
        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        # UBER should be uncategorised (no rule for it)
        uber = [e for e in entries if "UBER" in e.payee][0]
        assert any(p.account == "expenses:uncategorised" for p in uber.postings)


class TestWiseImport:
    def test_import_basic(self, journal_file, rules_file):
        entries = import_csv(
            csv_path=FIXTURES / "wise_sample.csv",
            bank_name="wise",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        assert len(entries) == 10

    def test_import_income(self, journal_file, rules_file):
        """Positive amounts should create income-style entries."""
        entries = import_csv(
            csv_path=FIXTURES / "wise_sample.csv",
            bank_name="wise",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        # "Freelance payment" is +3200
        freelance = [e for e in entries if "Freelance" in e.payee][0]
        assert any(
            p.account == "assets:bank:wise" and p.amount == 3200.0
            for p in freelance.postings
        )


class TestDuplicateDetection:
    def test_no_duplicates_on_reimport(self, journal_file, rules_file):
        """Importing the same CSV twice should not create duplicates."""
        import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        # Import again
        second = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            journal_path=journal_file,
            rules_path=rules_file,
        )
        assert len(second) == 0
        # Journal should still have exactly 10 entries
        journal = read_journal(journal_file)
        assert len(journal) == 10


class TestDryRun:
    def test_dry_run_no_write(self, journal_file, rules_file):
        """Dry run should not modify the journal file."""
        entries = import_csv(
            csv_path=FIXTURES / "anz_sample.csv",
            bank_name="anz",
            dry_run=True,
            journal_path=journal_file,
            rules_path=rules_file,
        )
        assert len(entries) == 10
        assert not journal_file.exists()


class TestEdgeCases:
    def test_unknown_bank(self, journal_file, rules_file):
        with pytest.raises(ValueError, match="Unknown bank"):
            import_csv(
                csv_path=FIXTURES / "anz_sample.csv",
                bank_name="nonexistent",
                journal_path=journal_file,
                rules_path=rules_file,
            )

    def test_missing_csv(self, journal_file, rules_file):
        with pytest.raises(ValueError, match="not found"):
            import_csv(
                csv_path="/tmp/nonexistent.csv",
                bank_name="anz",
                journal_path=journal_file,
                rules_path=rules_file,
            )
