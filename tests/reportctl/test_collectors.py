"""Tests for reportctl collectors."""
import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from halos.reportctl.collectors import (
    collect_memctl,
    collect_todoctl,
    collect_nightctl,
    collect_activity,
    _parse_index_yaml,
    _id_after,
)


# ── fixtures ────────────────────────────────────────────────────


@pytest.fixture
def memctl_setup(tmp_path):
    """Create a mock memctl config and index file."""
    memory_dir = tmp_path / "memory"
    notes_dir = memory_dir / "notes"
    notes_dir.mkdir(parents=True)

    # Write two note files
    note1 = notes_dir / "20260310-120000-test-note.md"
    note1_content = "---\ntitle: Test Note\n---\nBody"
    note1.write_text(note1_content)
    note1_hash = hashlib.sha256(note1_content.encode()).hexdigest()

    note2 = notes_dir / "20260315-090000-another-note.md"
    note2_content = "---\ntitle: Another Note\n---\nBody2"
    note2.write_text(note2_content)
    note2_hash = hashlib.sha256(note2_content.encode()).hexdigest()

    # Write an orphan
    orphan = notes_dir / "20260301-000000-orphan.md"
    orphan.write_text("orphan note")

    # Build INDEX.md
    index_data = {
        "generated": "2026-03-16T00:00:00Z",
        "note_count": 2,
        "entities": ["entity-a", "entity-b"],
        "tag_vocabulary": ["tag1", "tag2", "tag3"],
        "notes": [
            {
                "id": "20260310-120000",
                "file": str(note1),
                "title": "Test Note",
                "type": "fact",
                "tags": ["tag1"],
                "summary": "Body",
                "hash": note1_hash,
                "backlink_count": 0,
                "modified": "2026-03-10T12:00:00Z",
            },
            {
                "id": "20260315-090000",
                "file": str(note2),
                "title": "Another Note",
                "type": "decision",
                "tags": ["tag2"],
                "summary": "Body2",
                "hash": note2_hash,
                "backlink_count": 1,
                "modified": "2026-03-15T09:00:00Z",
            },
        ],
    }

    index_file = memory_dir / "INDEX.md"
    yaml_block = yaml.dump(index_data, default_flow_style=False, sort_keys=False)
    index_file.write_text(
        "# MEMORY INDEX\n\n## MEMORY_INDEX\n```yaml\n" + yaml_block + "```\n"
    )

    # Write memctl.yaml
    memctl_config = tmp_path / "memctl.yaml"
    memctl_config.write_text(yaml.dump({
        "memory_dir": str(memory_dir),
        "index_file": str(index_file),
    }))

    return memctl_config


@pytest.fixture
def todoctl_setup(tmp_path):
    """Create a mock todoctl config and items."""
    items_dir = tmp_path / "backlog" / "items"
    items_dir.mkdir(parents=True)

    for i, (status, priority) in enumerate([
        ("open", 1), ("open", 2), ("in-progress", 3),
        ("done", 4), ("blocked", 2),
    ]):
        item = {
            "id": f"20260315-{i:06d}",
            "title": f"Item {i}",
            "status": status,
            "priority": priority,
            "tags": ["test"],
            "created": "2026-03-15T10:00:00Z",
        }
        (items_dir / f"20260315-{i:06d}-item-{i}.yaml").write_text(
            yaml.dump(item, default_flow_style=False)
        )

    config = tmp_path / "todoctl.yaml"
    config.write_text(yaml.dump({
        "backlog_dir": str(tmp_path / "backlog"),
        "items_dir": str(items_dir),
    }))
    return config


@pytest.fixture
def nightctl_setup(tmp_path):
    """Create a mock nightctl config and manifest."""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    runs_dir = queue_dir / "runs"
    runs_dir.mkdir()

    manifest = {
        "generated": "2026-03-16T00:00:00Z",
        "job_count": 3,
        "pending": 1,
        "done": 1,
        "failed": 1,
        "jobs": [
            {"id": "j1", "status": "pending", "created": "2026-03-14T10:00:00Z", "tags": []},
            {"id": "j2", "status": "done", "created": "2026-03-15T08:00:00Z", "tags": []},
            {"id": "j3", "status": "failed", "created": "2026-03-15T09:00:00Z", "tags": []},
        ],
    }
    (queue_dir / "MANIFEST.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False)
    )

    # Write a failed run record
    (runs_dir / "run-j3.yaml").write_text(
        yaml.dump({"id": "j3", "status": "failed", "exit_code": 1})
    )

    config = tmp_path / "nightctl.yaml"
    config.write_text(yaml.dump({
        "queue_dir": str(queue_dir),
        "manifest_file": str(queue_dir / "MANIFEST.yaml"),
        "runs_dir": str(runs_dir),
    }))
    return config


# ── tests: memctl collector ─────────────────────────────────────


def test_collect_memctl(memctl_setup):
    result = collect_memctl(memctl_setup)
    assert result["available"] is True
    assert result["note_count"] == 2
    assert result["entities"] == 2
    assert result["tags"] == 3
    assert result["types"] == {"fact": 1, "decision": 1}
    assert result["drift"] == 0
    assert result["orphans"] == 1  # the orphan note


def test_collect_memctl_missing_config(tmp_path):
    result = collect_memctl(tmp_path / "nonexistent.yaml")
    assert result["available"] is False
    assert result["note_count"] == 0


def test_collect_memctl_drift(memctl_setup):
    # Modify a note file to cause drift
    with open(memctl_setup) as f:
        cfg = yaml.safe_load(f)
    index_file = Path(cfg["index_file"])
    idx = _parse_index_yaml(index_file)
    note_file = Path(idx["notes"][0]["file"])
    note_file.write_text("MODIFIED CONTENT")

    result = collect_memctl(memctl_setup)
    assert result["drift"] == 1


# ── tests: todoctl collector ────────────────────────────────────


def test_collect_todoctl(todoctl_setup):
    result = collect_todoctl(todoctl_setup)
    assert result["available"] is True
    assert result["total"] == 5
    assert result["by_status"]["open"] == 2
    assert result["by_status"]["in-progress"] == 1
    assert result["by_status"]["done"] == 1
    assert result["by_status"]["blocked"] == 1


def test_collect_todoctl_missing_config(tmp_path):
    result = collect_todoctl(tmp_path / "nonexistent.yaml")
    assert result["available"] is False


def test_collect_todoctl_empty_items(tmp_path):
    items_dir = tmp_path / "backlog" / "items"
    items_dir.mkdir(parents=True)
    config = tmp_path / "todoctl.yaml"
    config.write_text(yaml.dump({"items_dir": str(items_dir)}))
    result = collect_todoctl(config)
    assert result["available"] is True
    assert result["total"] == 0


# ── tests: nightctl collector ───────────────────────────────────


def test_collect_nightctl(nightctl_setup):
    result = collect_nightctl(nightctl_setup)
    assert result["available"] is True
    assert result["total_jobs"] == 3
    assert result["pending"] == 1
    assert result["by_status"]["pending"] == 1
    assert result["by_status"]["done"] == 1
    assert result["by_status"]["failed"] == 1
    assert result["recent_failures"] == 1
    assert result["oldest_pending_age_hours"] is not None


def test_collect_nightctl_missing_config(tmp_path):
    result = collect_nightctl(tmp_path / "nonexistent.yaml")
    assert result["available"] is False


# ── tests: activity collector ───────────────────────────────────


def test_collect_activity(memctl_setup, todoctl_setup, nightctl_setup):
    since = datetime(2026, 3, 14, 0, 0, tzinfo=timezone.utc)
    result = collect_activity(memctl_setup, todoctl_setup, nightctl_setup, since)
    assert result["notes_modified"] >= 1  # note modified on 2026-03-15
    assert result["jobs_created"] >= 1


def test_collect_activity_no_configs(tmp_path):
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    missing = tmp_path / "missing.yaml"
    result = collect_activity(missing, missing, missing, since)
    assert result["notes_created"] == 0
    assert result["todos_created"] == 0
    assert result["jobs_created"] == 0


# ── tests: helpers ──────────────────────────────────────────────


def test_parse_index_yaml(tmp_path):
    index = tmp_path / "INDEX.md"
    yaml_data = yaml.dump({"note_count": 5, "notes": []})
    index.write_text(f"# Header\n```yaml\n{yaml_data}```\n")
    result = _parse_index_yaml(index)
    assert result["note_count"] == 5


def test_parse_index_yaml_missing(tmp_path):
    result = _parse_index_yaml(tmp_path / "nonexistent.md")
    assert result == {}


def test_id_after():
    since = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
    assert _id_after("20260316-120000", since) is True
    assert _id_after("20260314-120000", since) is False
    assert _id_after("bad-id", since) is False
