"""Integration tests for ledgerctl CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from halos.ledgerctl.cli import main
from halos.ledgerctl.journal import read_journal


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    """Set up a temporary store directory and patch journal/rules paths."""
    store = tmp_path / "store"
    store.mkdir()

    # Patch the store dir resolution to use our tmp dir
    monkeypatch.setattr(
        "halos.ledgerctl.journal._store_dir", lambda: store
    )
    monkeypatch.setattr(
        "halos.ledgerctl.rules._store_dir", lambda: store
    )
    return store


class TestAddCommand:
    def test_add_basic(self, tmp_store, capsys, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["ledgerctl", "add", "--account", "expenses:food",
             "--amount", "42.50", "--payee", "Test Store"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

        out = capsys.readouterr().out
        assert "added" in out
        assert "42.50" in out

        journal = read_journal(tmp_store / "ledger.journal")
        assert len(journal) == 1
        assert journal[0].payee == "Test Store"

    def test_add_with_date(self, tmp_store, capsys, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["ledgerctl", "add", "--account", "expenses:food",
             "--amount", "10", "--payee", "Test", "--date", "2026-01-15"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

        journal = read_journal(tmp_store / "ledger.journal")
        assert journal[0].date.isoformat() == "2026-01-15"

    def test_add_income(self, tmp_store, capsys, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["ledgerctl", "add", "--account", "income:salary",
             "--amount", "5000", "--payee", "Employer"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

        journal = read_journal(tmp_store / "ledger.journal")
        assert any(p.account == "income:salary" for p in journal[0].postings)


class TestBalanceCommand:
    def test_balance_json(self, tmp_store, capsys, monkeypatch):
        # Add an entry first
        from halos.ledgerctl.journal import Entry, Posting, append_entries
        from datetime import date
        append_entries([
            Entry(date=date(2026, 3, 21), payee="Test", postings=[
                Posting(account="expenses:food", amount=42.50),
                Posting(account="assets:bank"),
            ])
        ], path=tmp_store / "ledger.journal")

        monkeypatch.setattr("sys.argv", ["ledgerctl", "balance", "--json"])

        with patch("halos.ledgerctl.reports._has_hledger", return_value=False):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 0

        out = capsys.readouterr().out
        data = json.loads(out)
        assert "expenses:food" in data


class TestCategoriesCommand:
    def test_categories_output(self, tmp_store, capsys, monkeypatch):
        from halos.ledgerctl.journal import Entry, Posting, append_entries
        from datetime import date
        append_entries([
            Entry(date=date(2026, 3, 21), payee="Test", postings=[
                Posting(account="expenses:food", amount=42.50),
                Posting(account="assets:bank"),
            ])
        ], path=tmp_store / "ledger.journal")

        monkeypatch.setattr("sys.argv", ["ledgerctl", "categories"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

        out = capsys.readouterr().out
        assert "CATEGORY" in out
        assert "expenses:food" in out


class TestRulesCommand:
    def test_rules_list_empty(self, tmp_store, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["ledgerctl", "rules", "list"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

        out = capsys.readouterr().out
        assert "No rules" in out

    def test_rules_add_and_list(self, tmp_store, capsys, monkeypatch):
        # Add a rule
        monkeypatch.setattr(
            "sys.argv",
            ["ledgerctl", "rules", "add", "--pattern", "TEST", "--account", "expenses:test"],
        )
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

        # List rules
        monkeypatch.setattr("sys.argv", ["ledgerctl", "rules", "list"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

        out = capsys.readouterr().out
        assert "TEST" in out
        assert "expenses:test" in out
