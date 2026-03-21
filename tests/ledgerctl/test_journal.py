"""Tests for ledgerctl journal reader/writer."""

import os
from datetime import date
from pathlib import Path

import pytest

from halos.ledgerctl.journal import (
    Entry,
    Posting,
    append_entries,
    entry_exists,
    parse_journal,
    read_journal,
)


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_journal(tmp_path):
    """Return a path to a temporary journal file."""
    return tmp_path / "test.journal"


class TestPosting:
    def test_format_with_amount(self):
        p = Posting(account="expenses:food", amount=42.50, currency="$")
        formatted = p.format()
        assert "expenses:food" in formatted
        assert "$42.50" in formatted

    def test_format_negative_amount(self):
        p = Posting(account="assets:bank", amount=-100.00, currency="$")
        formatted = p.format()
        assert "-$100.00" in formatted

    def test_format_no_amount(self):
        p = Posting(account="assets:bank:anz:checking")
        formatted = p.format()
        assert "assets:bank:anz:checking" in formatted
        assert "$" not in formatted

    def test_format_large_amount_with_commas(self):
        p = Posting(account="income:salary", amount=5000.00, currency="$")
        formatted = p.format()
        assert "$5,000.00" in formatted


class TestEntry:
    def test_format_basic(self):
        entry = Entry(
            date=date(2026, 3, 21),
            payee="Countdown",
            postings=[
                Posting(account="expenses:food", amount=42.50),
                Posting(account="assets:bank:anz:checking"),
            ],
        )
        text = entry.format()
        assert "2026-03-21 Countdown" in text
        assert "expenses:food" in text
        assert "$42.50" in text
        assert "assets:bank:anz:checking" in text

    def test_format_with_comment(self):
        entry = Entry(
            date=date(2026, 3, 21),
            payee="Countdown",
            comment="weekly groceries",
            postings=[
                Posting(account="expenses:food", amount=42.50),
                Posting(account="assets:bank:anz:checking"),
            ],
        )
        text = entry.format()
        assert "; weekly groceries" in text


class TestParseJournal:
    def test_parse_sample_journal(self):
        entries = read_journal(FIXTURES / "sample_journal.journal")
        assert len(entries) == 20

    def test_parse_entry_fields(self):
        entries = read_journal(FIXTURES / "sample_journal.journal")
        first = entries[0]
        assert first.date == date(2026, 3, 1)
        assert first.payee == "Countdown"
        assert len(first.postings) == 2
        assert first.postings[0].account == "expenses:food"
        assert first.postings[0].amount == 42.50

    def test_parse_income_entry(self):
        entries = read_journal(FIXTURES / "sample_journal.journal")
        # 4th entry is the salary
        salary = entries[3]
        assert salary.payee == "Employer Ltd"
        assert any(p.account == "income:salary" for p in salary.postings)
        assert any(p.amount == 5000.00 for p in salary.postings)

    def test_parse_empty_string(self):
        entries = parse_journal("")
        assert entries == []

    def test_parse_single_entry(self):
        text = """2026-03-21 Test Payee
    expenses:food                           $10.00
    assets:bank:checking
"""
        entries = parse_journal(text)
        assert len(entries) == 1
        assert entries[0].payee == "Test Payee"
        assert entries[0].postings[0].amount == 10.00

    def test_parse_multi_posting_entry(self):
        text = """2026-03-21 Split Purchase
    expenses:food                           $30.00
    expenses:household                      $20.00
    assets:bank:checking
"""
        entries = parse_journal(text)
        assert len(entries) == 1
        assert len(entries[0].postings) == 3

    def test_parse_entry_with_comment(self):
        text = """2026-03-21 Countdown  ; weekly shop
    expenses:food                           $42.50
    assets:bank:checking
"""
        entries = parse_journal(text)
        assert len(entries) == 1
        assert entries[0].comment == "weekly shop"


class TestAppendEntries:
    def test_append_to_new_file(self, tmp_journal):
        entry = Entry(
            date=date(2026, 3, 21),
            payee="Test",
            postings=[
                Posting(account="expenses:food", amount=10.00),
                Posting(account="assets:bank"),
            ],
        )
        append_entries([entry], path=tmp_journal)
        assert tmp_journal.exists()

        entries = read_journal(tmp_journal)
        assert len(entries) == 1
        assert entries[0].payee == "Test"

    def test_append_preserves_existing(self, tmp_journal):
        entry1 = Entry(
            date=date(2026, 3, 20),
            payee="First",
            postings=[
                Posting(account="expenses:food", amount=10.00),
                Posting(account="assets:bank"),
            ],
        )
        entry2 = Entry(
            date=date(2026, 3, 21),
            payee="Second",
            postings=[
                Posting(account="expenses:transport", amount=20.00),
                Posting(account="assets:bank"),
            ],
        )
        append_entries([entry1], path=tmp_journal)
        append_entries([entry2], path=tmp_journal)

        entries = read_journal(tmp_journal)
        assert len(entries) == 2
        assert entries[0].payee == "First"
        assert entries[1].payee == "Second"

    def test_append_multiple_at_once(self, tmp_journal):
        entries = [
            Entry(
                date=date(2026, 3, i),
                payee=f"Payee {i}",
                postings=[
                    Posting(account="expenses:misc", amount=float(i * 10)),
                    Posting(account="assets:bank"),
                ],
            )
            for i in range(1, 6)
        ]
        append_entries(entries, path=tmp_journal)

        result = read_journal(tmp_journal)
        assert len(result) == 5

    def test_append_empty_list_is_noop(self, tmp_journal):
        append_entries([], path=tmp_journal)
        assert not tmp_journal.exists()

    def test_atomic_write(self, tmp_journal):
        """Verify no partial writes — file shouldn't have temp artifacts."""
        entry = Entry(
            date=date(2026, 3, 21),
            payee="Atomic Test",
            postings=[
                Posting(account="expenses:food", amount=42.50),
                Posting(account="assets:bank"),
            ],
        )
        append_entries([entry], path=tmp_journal)

        # No temp files should remain
        parent = tmp_journal.parent
        temps = list(parent.glob(".ledger_*.tmp"))
        assert temps == []


class TestRoundTrip:
    def test_write_then_read(self, tmp_journal):
        """Write entries, read them back, verify fields match."""
        original = Entry(
            date=date(2026, 3, 21),
            payee="Round Trip Test",
            postings=[
                Posting(account="expenses:food", amount=42.50, currency="$"),
                Posting(account="assets:bank:anz:checking"),
            ],
        )
        append_entries([original], path=tmp_journal)
        entries = read_journal(tmp_journal)

        assert len(entries) == 1
        restored = entries[0]
        assert restored.date == original.date
        assert restored.payee == original.payee
        assert restored.postings[0].account == "expenses:food"
        assert restored.postings[0].amount == 42.50
        assert restored.postings[1].account == "assets:bank:anz:checking"
        assert restored.postings[1].amount is None


class TestEntryExists:
    def test_finds_duplicate(self):
        entries = [
            Entry(
                date=date(2026, 3, 21),
                payee="Countdown",
                postings=[Posting(account="expenses:food", amount=42.50)],
            ),
        ]
        assert entry_exists(entries, date(2026, 3, 21), 42.50, "Countdown")

    def test_no_match_different_date(self):
        entries = [
            Entry(
                date=date(2026, 3, 21),
                payee="Countdown",
                postings=[Posting(account="expenses:food", amount=42.50)],
            ),
        ]
        assert not entry_exists(entries, date(2026, 3, 20), 42.50, "Countdown")

    def test_no_match_different_amount(self):
        entries = [
            Entry(
                date=date(2026, 3, 21),
                payee="Countdown",
                postings=[Posting(account="expenses:food", amount=42.50)],
            ),
        ]
        assert not entry_exists(entries, date(2026, 3, 21), 99.99, "Countdown")

    def test_case_insensitive_payee(self):
        entries = [
            Entry(
                date=date(2026, 3, 21),
                payee="Countdown",
                postings=[Posting(account="expenses:food", amount=42.50)],
            ),
        ]
        assert entry_exists(entries, date(2026, 3, 21), 42.50, "countdown")
