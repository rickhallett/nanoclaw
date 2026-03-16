"""Tests for reportctl formatters."""
import json
import pytest

from halos.reportctl.formatters import (
    format_briefing,
    format_weekly,
    format_health,
    format_digest,
)


# ── fixtures ────────────────────────────────────────────────────


@pytest.fixture
def memctl_data():
    return {
        "available": True,
        "note_count": 42,
        "entities": 12,
        "tags": 8,
        "types": {"fact": 20, "decision": 15, "reference": 7},
        "orphans": 1,
        "drift": 2,
    }


@pytest.fixture
def todoctl_data():
    return {
        "available": True,
        "total": 10,
        "by_status": {"open": 5, "in-progress": 2, "done": 2, "blocked": 1},
        "by_priority": {1: 1, 2: 3, 3: 4, 4: 2},
    }


@pytest.fixture
def nightctl_data():
    return {
        "available": True,
        "total_jobs": 8,
        "by_status": {"pending": 2, "done": 5, "failed": 1},
        "pending": 2,
        "recent_failures": 1,
        "oldest_pending_age_hours": 36.5,
    }


@pytest.fixture
def activity_data():
    return {
        "notes_created": 5,
        "notes_modified": 8,
        "todos_created": 3,
        "todos_completed": 2,
        "jobs_created": 4,
        "jobs_completed": 3,
        "jobs_failed": 1,
    }


@pytest.fixture
def empty_data():
    return {
        "available": False,
        "note_count": 0,
        "entities": 0,
        "tags": 0,
        "types": {},
        "orphans": 0,
        "drift": 0,
        "total": 0,
        "by_status": {},
        "by_priority": {},
        "total_jobs": 0,
        "pending": 0,
        "recent_failures": 0,
        "oldest_pending_age_hours": None,
    }


# ── tests: briefing ────────────────────────────────────────────


def test_briefing_text(memctl_data, todoctl_data, nightctl_data):
    text = format_briefing(memctl_data, todoctl_data, nightctl_data)
    assert "MORNING BRIEFING" in text
    assert "Notes:      42" in text
    assert "Entities:   12" in text
    assert "Items:      10" in text
    assert "Pending:    2" in text
    assert "WARNING: 2 notes with index drift" in text
    assert "WARNING: 1 orphaned notes" in text


def test_briefing_json(memctl_data, todoctl_data, nightctl_data):
    text = format_briefing(memctl_data, todoctl_data, nightctl_data, json_out=True)
    data = json.loads(text)
    assert data["report"] == "briefing"
    assert data["memory"]["note_count"] == 42
    assert data["backlog"]["total"] == 10
    assert data["queue"]["pending"] == 2


def test_briefing_unavailable(empty_data):
    text = format_briefing(empty_data, empty_data, empty_data)
    assert "(not configured)" in text


# ── tests: weekly ───────────────────────────────────────────────


def test_weekly_text(activity_data, memctl_data, todoctl_data, nightctl_data):
    text = format_weekly(activity_data, memctl_data, todoctl_data, nightctl_data)
    assert "WEEKLY SUMMARY" in text
    assert "Notes created:    5" in text
    assert "Todos completed:  2" in text
    assert "Jobs failed:      1" in text


def test_weekly_json(activity_data, memctl_data, todoctl_data, nightctl_data):
    text = format_weekly(activity_data, memctl_data, todoctl_data, nightctl_data, json_out=True)
    data = json.loads(text)
    assert data["report"] == "weekly"
    assert data["activity"]["notes_created"] == 5


# ── tests: health ───────────────────────────────────────────────


def test_health_healthy(todoctl_data, nightctl_data):
    memctl = {
        "available": True, "note_count": 10, "entities": 5, "tags": 3,
        "types": {"fact": 10}, "orphans": 0, "drift": 0,
    }
    nightctl_ok = dict(nightctl_data, recent_failures=0, oldest_pending_age_hours=1.0)
    todoctl_ok = dict(todoctl_data, by_status={"open": 5, "done": 2})
    text = format_health(memctl, todoctl_ok, nightctl_ok)
    assert "HEALTHY" in text


def test_health_degraded(memctl_data, todoctl_data, nightctl_data):
    text = format_health(memctl_data, todoctl_data, nightctl_data)
    assert "DEGRADED" in text
    assert "drift" in text


def test_health_json(memctl_data, todoctl_data, nightctl_data):
    text = format_health(memctl_data, todoctl_data, nightctl_data, json_out=True)
    data = json.loads(text)
    assert data["report"] == "health"
    assert data["status"] == "DEGRADED"
    assert len(data["issues"]) > 0


# ── tests: digest ───────────────────────────────────────────────


def test_digest_text(activity_data):
    text = format_digest(activity_data, "24h")
    assert "ACTIVITY DIGEST (since 24h)" in text
    assert "Notes created:    5" in text


def test_digest_json(activity_data):
    text = format_digest(activity_data, "7d", json_out=True)
    data = json.loads(text)
    assert data["report"] == "digest"
    assert data["since"] == "7d"
    assert data["activity"]["jobs_failed"] == 1
