"""Tests for ProjectionEngine — the core replay/checkpoint/idempotency logic."""

import sqlite3
from pathlib import Path

import pytest

from halos.eventsource.core import Event, ProjectionHandler
from halos.eventsource.projection import ProjectionEngine


class CounterHandler(ProjectionHandler):
    """Trivial handler that counts events in a table."""

    tables = ["counter"]

    def handles(self) -> list[str]:
        return ["test.counted"]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS counter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                value INTEGER NOT NULL
            )
        """)

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        db.execute(
            "INSERT OR IGNORE INTO counter (event_id, value) VALUES (?, ?)",
            (event.id, event.payload["value"]),
        )


@pytest.fixture
def engine(tmp_path: Path) -> ProjectionEngine:
    e = ProjectionEngine(tmp_path / "test.db", [CounterHandler()])
    e.open()
    yield e
    e.close()


def _evt(value: int, seq: int = 1) -> Event:
    return Event.create(
        type="test.counted",
        source="test",
        payload={"value": value},
    ).with_seq(seq)


class TestProjectionEngine:
    def test_apply_processes_event(self, engine: ProjectionEngine):
        event = _evt(42, seq=1)
        assert engine.apply(event, "test-consumer") is True

        row = engine.db.execute("SELECT value FROM counter").fetchone()
        assert row["value"] == 42

    def test_idempotency(self, engine: ProjectionEngine):
        event = _evt(42, seq=1)
        assert engine.apply(event, "test-consumer") is True
        assert engine.apply(event, "test-consumer") is False

        count = engine.db.execute("SELECT COUNT(*) as c FROM counter").fetchone()
        assert count["c"] == 1

    def test_checkpoint_tracking(self, engine: ProjectionEngine):
        assert engine.last_checkpoint("test-consumer") == 0

        engine.apply(_evt(1, seq=5), "test-consumer")
        assert engine.last_checkpoint("test-consumer") == 5

        engine.apply(_evt(2, seq=10), "test-consumer")
        assert engine.last_checkpoint("test-consumer") == 10

    def test_multiple_consumers(self, engine: ProjectionEngine):
        event = _evt(1, seq=5)
        engine.apply(event, "consumer-a")
        engine.apply(_evt(2, seq=7), "consumer-b")

        assert engine.last_checkpoint("consumer-a") == 5
        assert engine.last_checkpoint("consumer-b") == 7

    def test_rebuild_clears_everything(self, engine: ProjectionEngine):
        engine.apply(_evt(1, seq=1), "test-consumer")
        engine.apply(_evt(2, seq=2), "test-consumer")

        engine.rebuild()

        count = engine.db.execute("SELECT COUNT(*) as c FROM counter").fetchone()
        assert count["c"] == 0
        assert engine.last_checkpoint("test-consumer") == 0

    def test_rebuild_allows_replay(self, engine: ProjectionEngine):
        event = _evt(42, seq=1)
        engine.apply(event, "test-consumer")
        engine.rebuild()

        # Same event can be applied again after rebuild
        assert engine.apply(event, "test-consumer") is True
        row = engine.db.execute("SELECT value FROM counter").fetchone()
        assert row["value"] == 42

    def test_unhandled_event_type_is_noop(self, engine: ProjectionEngine):
        event = Event.create(
            type="unknown.event",
            source="test",
            payload={},
        ).with_seq(1)

        # Should still process (mark as seen) but no handler fires
        assert engine.apply(event, "test-consumer") is True
        count = engine.db.execute("SELECT COUNT(*) as c FROM counter").fetchone()
        assert count["c"] == 0

    def test_not_opened_raises(self, tmp_path: Path):
        engine = ProjectionEngine(tmp_path / "unopened.db", [CounterHandler()])
        with pytest.raises(RuntimeError, match="not open"):
            engine.last_checkpoint("x")

    def test_close_and_reopen_preserves_state(self, tmp_path: Path):
        db_path = tmp_path / "persist.db"
        engine = ProjectionEngine(db_path, [CounterHandler()])
        engine.open()
        engine.apply(_evt(99, seq=3), "consumer")
        engine.close()

        engine2 = ProjectionEngine(db_path, [CounterHandler()])
        engine2.open()
        assert engine2.last_checkpoint("consumer") == 3
        row = engine2.db.execute("SELECT value FROM counter").fetchone()
        assert row["value"] == 99
        engine2.close()
