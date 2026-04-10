"""Tests for changoctl SQLite store."""

import sqlite3

import pytest

from halos.changoctl.store import (
    get_inventory,
    restock,
    consume,
    _connect,
    add_quote,
    list_quotes,
    random_quote,
    list_consumption_history,
)


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_changoctl.db"


class TestInventory:
    def test_seed_on_connect(self, tmp_db):
        """First connect seeds all four items at stock 0."""
        conn = _connect(tmp_db)
        rows = conn.execute("SELECT * FROM inventory ORDER BY item").fetchall()
        conn.close()
        items = [dict(r)["item"] for r in rows]
        assert items == ["espresso", "lagavulin", "nos", "stimpacks"]
        for r in rows:
            assert dict(r)["stock"] == 0

    def test_get_inventory(self, tmp_db):
        inv = get_inventory(db_path=tmp_db)
        assert len(inv) == 4
        assert all(i["stock"] == 0 for i in inv)

    def test_restock_default(self, tmp_db):
        result = restock("espresso", db_path=tmp_db)
        assert result["stock"] == 1
        assert result["item"] == "espresso"

    def test_restock_quantity(self, tmp_db):
        result = restock("lagavulin", quantity=6, db_path=tmp_db)
        assert result["stock"] == 6

    def test_restock_accumulates(self, tmp_db):
        restock("nos", quantity=3, db_path=tmp_db)
        result = restock("nos", quantity=2, db_path=tmp_db)
        assert result["stock"] == 5

    def test_restock_invalid_item(self, tmp_db):
        with pytest.raises(ValueError, match="invalid item"):
            restock("bourbon", db_path=tmp_db)

    def test_consume_decrements(self, tmp_db):
        restock("stimpacks", quantity=3, db_path=tmp_db)
        result = consume("stimpacks", mood="locked-in", db_path=tmp_db)
        assert result["stock"] == 2
        assert result["log_entry"]["item"] == "stimpacks"
        assert result["log_entry"]["mood"] == "locked-in"
        assert result["log_entry"]["quantity"] == 1

    def test_consume_out_of_stock(self, tmp_db):
        """Out of stock: logs at quantity 0, stock stays 0."""
        result = consume("espresso", mood="grind", db_path=tmp_db)
        assert result["stock"] == 0
        assert result["log_entry"]["quantity"] == 0
        assert result["out_of_stock"] is True

    def test_consume_invalid_item(self, tmp_db):
        with pytest.raises(ValueError, match="invalid item"):
            consume("bourbon", db_path=tmp_db)


class TestQuotes:
    def test_add_quote(self, tmp_db):
        q = add_quote(
            "The cluster doesn't care about your feelings.",
            category="sardonic",
            db_path=tmp_db,
        )
        assert q["id"] == 1
        assert q["category"] == "sardonic"

    def test_add_quote_with_metadata(self, tmp_db):
        q = add_quote(
            "Ship it or shut up.",
            category="lethal",
            source_session="sess-001",
            source_module="nightctl",
            db_path=tmp_db,
        )
        assert q["source_session"] == "sess-001"
        assert q["source_module"] == "nightctl"

    def test_add_duplicate_raises(self, tmp_db):
        add_quote("Unique line.", category="strategic", db_path=tmp_db)
        with pytest.raises(sqlite3.IntegrityError):
            add_quote("Unique line.", category="strategic", db_path=tmp_db)

    def test_add_quote_invalid_category(self, tmp_db):
        with pytest.raises(ValueError, match="invalid category"):
            add_quote("Whatever.", category="funny", db_path=tmp_db)

    def test_list_quotes_all(self, tmp_db):
        add_quote("Line one.", category="sardonic", db_path=tmp_db)
        add_quote("Line two.", category="strategic", db_path=tmp_db)
        quotes = list_quotes(db_path=tmp_db)
        assert len(quotes) == 2

    def test_list_quotes_by_category(self, tmp_db):
        add_quote("Sardonic one.", category="sardonic", db_path=tmp_db)
        add_quote("Strategic one.", category="strategic", db_path=tmp_db)
        quotes = list_quotes(category="sardonic", db_path=tmp_db)
        assert len(quotes) == 1
        assert quotes[0]["category"] == "sardonic"

    def test_random_quote_empty(self, tmp_db):
        result = random_quote(db_path=tmp_db)
        assert result is None

    def test_random_quote_with_mood(self, tmp_db):
        add_quote("Fire line.", category="sardonic", db_path=tmp_db)
        add_quote("Calm line.", category="philosophical", db_path=tmp_db)
        result = random_quote(category="sardonic", db_path=tmp_db)
        assert result is not None
        assert result["category"] == "sardonic"

    def test_random_quote_no_match(self, tmp_db):
        add_quote("Only sardonic.", category="sardonic", db_path=tmp_db)
        result = random_quote(category="lethal", db_path=tmp_db)
        assert result is None


class TestHistory:
    def test_list_history_empty(self, tmp_db):
        history = list_consumption_history(db_path=tmp_db)
        assert history == []

    def test_list_history_after_consume(self, tmp_db):
        restock("espresso", quantity=2, db_path=tmp_db)
        consume("espresso", mood="grind", db_path=tmp_db)
        consume("espresso", mood="grind", db_path=tmp_db)
        history = list_consumption_history(db_path=tmp_db)
        assert len(history) == 2
        assert history[0]["id"] > history[1]["id"]

    def test_list_history_by_item(self, tmp_db):
        restock("espresso", quantity=1, db_path=tmp_db)
        restock("nos", quantity=1, db_path=tmp_db)
        consume("espresso", db_path=tmp_db)
        consume("nos", db_path=tmp_db)
        history = list_consumption_history(item="espresso", db_path=tmp_db)
        assert len(history) == 1
        assert history[0]["item"] == "espresso"

    def test_list_history_by_days(self, tmp_db):
        restock("espresso", quantity=1, db_path=tmp_db)
        consume("espresso", db_path=tmp_db)
        history = list_consumption_history(days=7, db_path=tmp_db)
        assert len(history) == 1
