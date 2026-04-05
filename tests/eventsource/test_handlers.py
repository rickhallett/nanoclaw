"""Tests for domain projection handlers — track, night, journal."""

import json
import sqlite3
from pathlib import Path

import pytest

from halos.eventsource.core import Event
from halos.eventsource.projection import ProjectionEngine
from halos.eventsource.handlers.track import TrackProjectionHandler
from halos.eventsource.handlers.night import NightProjectionHandler
from halos.eventsource.handlers.journal import JournalProjectionHandler


CONSUMER = "test"


def _evt(event_type: str, payload: dict, seq: int = 1, source: str = "test") -> Event:
    return Event.create(
        type=event_type,
        source=source,
        payload=payload,
    ).with_seq(seq)


# ── Track handler ──────────────────────────────────────────────


@pytest.fixture
def track_engine(tmp_path: Path) -> ProjectionEngine:
    e = ProjectionEngine(tmp_path / "track.db", [TrackProjectionHandler()])
    e.open()
    yield e
    e.close()


class TestTrackHandler:
    def test_log_movement(self, track_engine):
        e = _evt("track.movement.logged", {
            "domain": "movement", "duration_mins": 45,
            "notes": "Morning run", "entry_id": 1,
        })
        track_engine.apply(e, CONSUMER)

        row = track_engine.db.execute(
            "SELECT * FROM track_entries WHERE id = 1"
        ).fetchone()
        assert row["domain"] == "movement"
        assert row["duration_mins"] == 45
        assert row["notes"] == "Morning run"

    def test_log_zazen(self, track_engine):
        e = _evt("track.zazen.logged", {
            "domain": "zazen", "duration_mins": 20,
            "notes": "", "entry_id": 2,
        })
        track_engine.apply(e, CONSUMER)

        row = track_engine.db.execute(
            "SELECT * FROM track_entries WHERE id = 2"
        ).fetchone()
        assert row["domain"] == "zazen"

    def test_log_study(self, track_engine):
        e = _evt("track.study.logged", {
            "domain": "study-neetcode", "duration_mins": 60,
            "entry_id": 3, "sub_domain": "neetcode",
        })
        track_engine.apply(e, CONSUMER)

        row = track_engine.db.execute(
            "SELECT * FROM track_entries WHERE id = 3"
        ).fetchone()
        assert row["domain"] == "study-neetcode"
        assert row["duration_mins"] == 60

    def test_delete_entry(self, track_engine):
        track_engine.apply(_evt("track.movement.logged", {
            "domain": "movement", "duration_mins": 30, "entry_id": 10,
        }, seq=1), CONSUMER)

        track_engine.apply(_evt("track.entry.deleted", {
            "domain": "movement", "entry_id": 10,
        }, seq=2), CONSUMER)

        row = track_engine.db.execute(
            "SELECT * FROM track_entries WHERE id = 10"
        ).fetchone()
        assert row is None

    def test_edit_entry(self, track_engine):
        track_engine.apply(_evt("track.movement.logged", {
            "domain": "movement", "duration_mins": 30,
            "notes": "original", "entry_id": 20,
        }, seq=1), CONSUMER)

        track_engine.apply(_evt("track.entry.edited", {
            "domain": "movement", "entry_id": 20,
            "duration_mins": 45, "notes": "corrected",
        }, seq=2), CONSUMER)

        row = track_engine.db.execute(
            "SELECT * FROM track_entries WHERE id = 20"
        ).fetchone()
        assert row["duration_mins"] == 45
        assert row["notes"] == "corrected"

    def test_edit_partial(self, track_engine):
        track_engine.apply(_evt("track.movement.logged", {
            "domain": "movement", "duration_mins": 30,
            "notes": "keep this", "entry_id": 21,
        }, seq=1), CONSUMER)

        track_engine.apply(_evt("track.entry.edited", {
            "domain": "movement", "entry_id": 21,
            "duration_mins": 60,
        }, seq=2), CONSUMER)

        row = track_engine.db.execute(
            "SELECT * FROM track_entries WHERE domain = 'movement' AND id = 21"
        ).fetchone()
        assert row["duration_mins"] == 60
        assert row["notes"] == "keep this"

    def test_same_entry_id_across_domains_do_not_collide(self, track_engine):
        track_engine.apply(_evt("track.movement.logged", {
            "domain": "movement", "duration_mins": 30, "entry_id": 1,
        }, seq=1), CONSUMER)
        track_engine.apply(_evt("track.zazen.logged", {
            "domain": "zazen", "duration_mins": 20, "entry_id": 1,
        }, seq=2), CONSUMER)

        rows = track_engine.db.execute(
            "SELECT domain, id, duration_mins FROM track_entries WHERE id = 1 ORDER BY domain"
        ).fetchall()
        assert [(r["domain"], r["id"], r["duration_mins"]) for r in rows] == [
            ("movement", 1, 30),
            ("zazen", 1, 20),
        ]


# ── Night handler ──────────────────────────────────────────────


@pytest.fixture
def night_engine(tmp_path: Path) -> ProjectionEngine:
    e = ProjectionEngine(tmp_path / "night.db", [NightProjectionHandler()])
    e.open()
    yield e
    e.close()


class TestNightHandler:
    def test_create_item(self, night_engine):
        e = _evt("night.item.created", {
            "item_id": "task-001", "title": "Deploy NATS",
            "quadrant": "q1", "kind": "task", "tags": ["infra"],
        })
        night_engine.apply(e, CONSUMER)

        row = night_engine.db.execute(
            "SELECT * FROM night_items WHERE item_id = 'task-001'"
        ).fetchone()
        assert row["title"] == "Deploy NATS"
        assert row["status"] == "open"
        assert row["quadrant"] == "q1"
        assert json.loads(row["tags"]) == ["infra"]

    def test_transition_item(self, night_engine):
        night_engine.apply(_evt("night.item.created", {
            "item_id": "t-1", "title": "X", "quadrant": "q2",
        }, seq=1), CONSUMER)

        night_engine.apply(_evt("night.item.transitioned", {
            "item_id": "t-1", "from_status": "open", "to_status": "active",
        }, seq=2), CONSUMER)

        row = night_engine.db.execute(
            "SELECT status FROM night_items WHERE item_id = 't-1'"
        ).fetchone()
        assert row["status"] == "active"

    def test_update_item_fields(self, night_engine):
        night_engine.apply(_evt("night.item.created", {
            "item_id": "t-2", "title": "Old title", "quadrant": "q3",
        }, seq=1), CONSUMER)

        night_engine.apply(_evt("night.item.updated", {
            "item_id": "t-2",
            "fields_changed": {"title": "New title", "quadrant": "q1"},
        }, seq=2), CONSUMER)

        row = night_engine.db.execute(
            "SELECT * FROM night_items WHERE item_id = 't-2'"
        ).fetchone()
        assert row["title"] == "New title"
        assert row["quadrant"] == "q1"

    def test_update_ignores_unsafe_fields(self, night_engine):
        night_engine.apply(_evt("night.item.created", {
            "item_id": "t-3", "title": "Safe",
        }, seq=1), CONSUMER)

        night_engine.apply(_evt("night.item.updated", {
            "item_id": "t-3",
            "fields_changed": {"status": "hacked"},
        }, seq=2), CONSUMER)

        row = night_engine.db.execute(
            "SELECT status FROM night_items WHERE item_id = 't-3'"
        ).fetchone()
        assert row["status"] == "open"

    def test_job_completed(self, night_engine):
        e = _evt("night.job.completed", {
            "job_id": "j-1", "result": "ok", "duration_secs": 12.5,
        })
        night_engine.apply(e, CONSUMER)

        row = night_engine.db.execute(
            "SELECT * FROM night_jobs WHERE job_id = 'j-1'"
        ).fetchone()
        assert row["status"] == "completed"
        assert row["duration_secs"] == 12.5

    def test_job_failed(self, night_engine):
        e = _evt("night.job.failed", {
            "job_id": "j-2", "error": "timeout", "duration_secs": 30.0,
        })
        night_engine.apply(e, CONSUMER)

        row = night_engine.db.execute(
            "SELECT * FROM night_jobs WHERE job_id = 'j-2'"
        ).fetchone()
        assert row["status"] == "failed"
        assert row["error"] == "timeout"


# ── Journal handler ────────────────────────────────────────────


@pytest.fixture
def journal_engine(tmp_path: Path) -> ProjectionEngine:
    e = ProjectionEngine(tmp_path / "journal.db", [JournalProjectionHandler()])
    e.open()
    yield e
    e.close()


class TestJournalHandler:
    def test_add_entry(self, journal_engine):
        e = _evt("journal.entry.added", {
            "entry_id": 1, "tags": ["movement", "body"],
            "source": "voice", "mood": "steady", "energy": "high",
            "raw_text": "Felt strong today",
        })
        journal_engine.apply(e, CONSUMER)

        row = journal_engine.db.execute(
            "SELECT * FROM journal_entries WHERE entry_id = 1"
        ).fetchone()
        assert row["source"] == "voice"
        assert row["mood"] == "steady"
        assert row["energy"] == "high"
        assert row["raw_text"] == "Felt strong today"
        assert json.loads(row["tags"]) == ["movement", "body"]

    def test_add_entry_minimal(self, journal_engine):
        e = _evt("journal.entry.added", {"entry_id": 2})
        journal_engine.apply(e, CONSUMER)

        row = journal_engine.db.execute(
            "SELECT * FROM journal_entries WHERE entry_id = 2"
        ).fetchone()
        assert row["source"] == "text"
        assert row["mood"] is None
        assert row["raw_text"] == ""

    def test_duplicate_entry_ignored_by_engine(self, journal_engine):
        e = _evt("journal.entry.added", {
            "entry_id": 3, "raw_text": "first",
        })
        assert journal_engine.apply(e, CONSUMER) is True
        assert journal_engine.apply(e, CONSUMER) is False

        count = journal_engine.db.execute(
            "SELECT COUNT(*) as c FROM journal_entries WHERE entry_id = 3"
        ).fetchone()
        assert count["c"] == 1


# ── Combined handlers ─────────────────────────────────────────


class TestCombinedProjection:
    def test_all_handlers_together(self, tmp_path: Path):
        """Verify handlers coexist in a single projection."""
        engine = ProjectionEngine(tmp_path / "combined.db", [
            TrackProjectionHandler(),
            NightProjectionHandler(),
            JournalProjectionHandler(),
        ])
        engine.open()

        engine.apply(_evt("track.movement.logged", {
            "domain": "movement", "duration_mins": 30, "entry_id": 1,
        }, seq=1), CONSUMER)

        engine.apply(_evt("night.item.created", {
            "item_id": "t-1", "title": "Test",
        }, seq=2), CONSUMER)

        engine.apply(_evt("journal.entry.added", {
            "entry_id": 1, "raw_text": "Hello",
        }, seq=3), CONSUMER)

        assert engine.db.execute("SELECT COUNT(*) as c FROM track_entries").fetchone()["c"] == 1
        assert engine.db.execute("SELECT COUNT(*) as c FROM night_items").fetchone()["c"] == 1
        assert engine.db.execute("SELECT COUNT(*) as c FROM journal_entries").fetchone()["c"] == 1
        assert engine.last_checkpoint(CONSUMER) == 3

        engine.close()
