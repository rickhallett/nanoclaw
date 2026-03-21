"""Tests for ledgerctl categorisation rules."""

from pathlib import Path

import pytest

from halos.ledgerctl.rules import (
    add_rule,
    categorise,
    load_rules,
    save_rules,
    DEFAULT_ACCOUNT,
)


@pytest.fixture
def rules_file(tmp_path):
    return tmp_path / "ledger-rules.yaml"


@pytest.fixture
def sample_rules():
    return [
        {"pattern": "COUNTDOWN|NEW WORLD|PAKNSAVE", "account": "expenses:food"},
        {"pattern": "BP 2GO|Z ENERGY", "account": "expenses:transport"},
        {"pattern": "VODAFONE|SPARK", "account": "expenses:phone"},
        {"pattern": "EMPLOYER|SALARY", "account": "income:salary"},
        {"pattern": "SPOTIFY|NETFLIX", "account": "expenses:entertainment"},
    ]


class TestLoadSaveRules:
    def test_load_nonexistent_file(self, rules_file):
        rules = load_rules(rules_file)
        assert rules == []

    def test_save_and_load(self, rules_file, sample_rules):
        save_rules(sample_rules, rules_file)
        loaded = load_rules(rules_file)
        assert len(loaded) == 5
        assert loaded[0]["pattern"] == "COUNTDOWN|NEW WORLD|PAKNSAVE"
        assert loaded[0]["account"] == "expenses:food"

    def test_save_atomic(self, rules_file, sample_rules):
        """Verify no temp files remain after save."""
        save_rules(sample_rules, rules_file)
        temps = list(rules_file.parent.glob(".rules_*.tmp"))
        assert temps == []


class TestAddRule:
    def test_add_rule(self, rules_file):
        result = add_rule("TEST", "expenses:test", path=rules_file)
        assert len(result) == 1
        assert result[0]["pattern"] == "TEST"
        assert result[0]["account"] == "expenses:test"

    def test_add_multiple_rules(self, rules_file):
        add_rule("FIRST", "expenses:first", path=rules_file)
        result = add_rule("SECOND", "expenses:second", path=rules_file)
        assert len(result) == 2

    def test_add_rule_persists(self, rules_file):
        add_rule("PERSIST", "expenses:persist", path=rules_file)
        loaded = load_rules(rules_file)
        assert len(loaded) == 1
        assert loaded[0]["pattern"] == "PERSIST"


class TestCategorise:
    def test_exact_match(self, sample_rules):
        result = categorise("COUNTDOWN", rules=sample_rules)
        assert result == "expenses:food"

    def test_regex_alternation(self, sample_rules):
        assert categorise("NEW WORLD", rules=sample_rules) == "expenses:food"
        assert categorise("PAKNSAVE", rules=sample_rules) == "expenses:food"

    def test_case_insensitive(self, sample_rules):
        assert categorise("countdown", rules=sample_rules) == "expenses:food"

    def test_partial_match(self, sample_rules):
        assert categorise("COUNTDOWN NORTHLANDS", rules=sample_rules) == "expenses:food"

    def test_first_match_wins(self):
        """Rules are evaluated in order; first match wins."""
        rules = [
            {"pattern": "FOOD", "account": "expenses:food"},
            {"pattern": "FOOD", "account": "expenses:groceries"},
        ]
        assert categorise("FOOD MART", rules=rules) == "expenses:food"

    def test_uncategorised_fallback(self, sample_rules):
        result = categorise("SOME RANDOM MERCHANT", rules=sample_rules)
        assert result == DEFAULT_ACCOUNT

    def test_empty_rules(self):
        result = categorise("ANYTHING", rules=[])
        assert result == DEFAULT_ACCOUNT

    def test_invalid_regex_skipped(self):
        rules = [
            {"pattern": "[invalid", "account": "expenses:bad"},
            {"pattern": "GOOD", "account": "expenses:good"},
        ]
        # Invalid regex is skipped, falls through to next rule
        assert categorise("GOOD STUFF", rules=rules) == "expenses:good"

    def test_load_from_file(self, rules_file, sample_rules):
        save_rules(sample_rules, rules_file)
        # Pass path via the load_rules default
        result = categorise("VODAFONE", rules=load_rules(rules_file))
        assert result == "expenses:phone"
