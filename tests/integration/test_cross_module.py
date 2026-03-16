"""Cross-module integration tests.

Verify that reportctl's collectors can read the actual output formats
produced by memctl, todoctl, and nightctl — no mocks, real serialisation.
"""
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import yaml

from halos.memctl import index as memctl_index
from halos.memctl import note as memctl_note
from halos.todoctl.todo import TodoItem
from halos.reportctl.collectors import (
    collect_memctl,
    collect_todoctl,
    collect_nightctl,
    collect_activity,
)
from halos.reportctl.formatters import format_briefing


# ── helpers ────────────────────────────────────────────────────


def _write_memctl_config(base: Path, memory_dir: Path, index_file: Path) -> Path:
    cfg_path = base / "memctl.yaml"
    cfg_path.write_text(yaml.dump({
        "memory_dir": str(memory_dir),
        "index_file": str(index_file),
    }))
    return cfg_path


def _write_todoctl_config(base: Path, items_dir: Path) -> Path:
    cfg_path = base / "todoctl.yaml"
    cfg_path.write_text(yaml.dump({
        "items_dir": str(items_dir),
    }))
    return cfg_path


def _write_nightctl_config(base: Path, manifest_file: Path, runs_dir: Path) -> Path:
    cfg_path = base / "nightctl.yaml"
    cfg_path.write_text(yaml.dump({
        "manifest_file": str(manifest_file),
        "runs_dir": str(runs_dir),
    }))
    return cfg_path


# ── Test 1: reportctl reads memctl's real index format ─────────


def test_reportctl_reads_memctl_index(tmp_path):
    """memctl index.write() -> reportctl collect_memctl()"""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    notes_dir = memory_dir / "notes"
    notes_dir.mkdir()

    index_file = memory_dir / "INDEX.md"

    # Create a real note file so hash comparison works
    note_content = textwrap.dedent("""\
        ---
        id: "20260316-120000-001"
        title: "Test fact"
        type: fact
        tags: [testing]
        entities: [Alice, Bob]
        confidence: high
        created: "2026-03-16T12:00:00Z"
        modified: "2026-03-16T12:00:00Z"
        expires: null
        ---

        This is a test note body.
    """)
    note_file = notes_dir / "20260316-120000-001-test-fact.md"
    note_file.write_text(note_content)

    note_hash = memctl_index.hash_file(str(note_file))

    # Build an Index using memctl's own dataclass and write it
    idx = memctl_index.Index(
        note_count=1,
        entities=["Alice", "Bob"],
        tag_vocabulary=["testing"],
        notes=[
            memctl_index.Entry(
                id="20260316-120000-001",
                file=str(note_file),
                title="Test fact",
                type="fact",
                tags=["testing"],
                entities=["Alice", "Bob"],
                summary="This is a test note body.",
                hash=note_hash,
                backlink_count=0,
                modified="2026-03-16T12:00:00Z",
            ),
        ],
    )
    memctl_index.write(str(index_file), idx)

    # Now let reportctl read it
    cfg_path = _write_memctl_config(tmp_path, memory_dir, index_file)
    result = collect_memctl(cfg_path)

    assert result["available"] is True
    assert result["note_count"] == 1
    assert result["entities"] == 2  # Alice, Bob
    assert result["tags"] == 1      # testing
    assert result["types"] == {"fact": 1}
    assert result["drift"] == 0     # hash matches


# ── Test 2: reportctl reads todoctl's real item format ─────────


def test_reportctl_reads_todoctl_items(tmp_path):
    """todoctl TodoItem.create() -> reportctl collect_todoctl()"""
    items_dir = tmp_path / "backlog" / "items"
    items_dir.mkdir(parents=True)

    # Create items via todoctl's own API
    item1 = TodoItem.create(items_dir, title="Fix the widget", priority=1,
                            tags=["bugfix"])
    item2 = TodoItem.create(items_dir, title="Add feature X", priority=2,
                            tags=["feature"])
    item3 = TodoItem.create(items_dir, title="Old done task", priority=3,
                            tags=["chore"])
    # Mark item3 as done
    item3.data["status"] = "done"
    item3.save()

    cfg_path = _write_todoctl_config(tmp_path, items_dir)
    result = collect_todoctl(cfg_path)

    assert result["available"] is True
    assert result["total"] == 3
    assert result["by_status"]["open"] == 2
    assert result["by_status"]["done"] == 1
    assert result["by_priority"][1] == 1
    assert result["by_priority"][2] == 1
    assert result["by_priority"][3] == 1


# ── Test 3: reportctl reads nightctl's real manifest format ────


def test_reportctl_reads_nightctl_manifest(tmp_path):
    """Write manifest in nightctl's exact format -> reportctl collect_nightctl()"""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    runs_dir = queue_dir / "runs"
    runs_dir.mkdir()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Write a MANIFEST.yaml in the exact format nightctl's Manifest produces
    manifest_data = {
        "generated": now_iso,
        "job_count": 3,
        "pending": 1,
        "done": 1,
        "failed": 1,
        "jobs": [
            {
                "id": "job-001",
                "file": str(tmp_path / "jobs" / "job-001.yaml"),
                "title": "Backup database",
                "schedule": "overnight",
                "priority": 1,
                "status": "pending",
                "tags": ["infra"],
                "depends_on": [],
                "created": now_iso,
                "hash": "",
            },
            {
                "id": "job-002",
                "file": str(tmp_path / "jobs" / "job-002.yaml"),
                "title": "Run migrations",
                "schedule": "overnight",
                "priority": 2,
                "status": "done",
                "tags": [],
                "depends_on": [],
                "created": now_iso,
                "hash": "",
            },
            {
                "id": "job-003",
                "file": str(tmp_path / "jobs" / "job-003.yaml"),
                "title": "Deploy",
                "schedule": "overnight",
                "priority": 3,
                "status": "failed",
                "tags": [],
                "depends_on": [],
                "created": now_iso,
                "hash": "",
            },
        ],
    }
    manifest_file = queue_dir / "MANIFEST.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(manifest_data, f, default_flow_style=False, sort_keys=False)

    # Write run records in the format nightctl's executor actually produces
    # (uses "outcome", not "status")
    run_record_pass = {
        "id": "job-002",
        "attempt": 1,
        "started": now_iso,
        "finished": now_iso,
        "exit_code": 0,
        "stdout": "ok",
        "stderr": "",
        "duration_secs": 5,
        "outcome": "done",
    }
    run_record_fail = {
        "id": "job-003",
        "attempt": 1,
        "started": now_iso,
        "finished": now_iso,
        "exit_code": 1,
        "stdout": "",
        "stderr": "error",
        "duration_secs": 2,
        "outcome": "failed",
    }
    with open(runs_dir / "job-002-run-1.yaml", "w") as f:
        yaml.dump(run_record_pass, f, default_flow_style=False, sort_keys=False)
    with open(runs_dir / "job-003-run-1.yaml", "w") as f:
        yaml.dump(run_record_fail, f, default_flow_style=False, sort_keys=False)

    cfg_path = _write_nightctl_config(tmp_path, manifest_file, runs_dir)
    result = collect_nightctl(cfg_path)

    assert result["available"] is True
    assert result["total_jobs"] == 3
    assert result["pending"] == 1
    assert result["by_status"]["pending"] == 1
    assert result["by_status"]["done"] == 1
    assert result["by_status"]["failed"] == 1
    # recent_failures counts run records with outcome == "failed"
    assert result["recent_failures"] == 1


# ── Test 4: memctl note -> reportctl activity ──────────────────


def test_memctl_note_activity(tmp_path):
    """Create a memctl note with known timestamp -> collect_activity() counts it."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    notes_dir = memory_dir / "notes"
    notes_dir.mkdir()
    index_file = memory_dir / "INDEX.md"

    # Use a recent timestamp so the activity window catches it
    recent_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-001"

    idx = memctl_index.Index(
        note_count=1,
        entities=["TestEntity"],
        tag_vocabulary=["test"],
        notes=[
            memctl_index.Entry(
                id=recent_id,
                file=str(notes_dir / "note.md"),
                title="Recent note",
                type="fact",
                tags=["test"],
                entities=["TestEntity"],
                summary="body",
                hash="abc123",
                backlink_count=0,
                modified=recent_iso,
            ),
        ],
    )
    memctl_index.write(str(index_file), idx)

    memctl_cfg = _write_memctl_config(tmp_path, memory_dir, index_file)
    # todoctl and nightctl configs that don't exist — activity should still work
    todoctl_cfg = tmp_path / "todoctl.yaml"
    nightctl_cfg = tmp_path / "nightctl.yaml"

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    activity = collect_activity(memctl_cfg, todoctl_cfg, nightctl_cfg, since)

    assert activity["notes_modified"] >= 1
    assert activity["notes_created"] >= 1


# ── Test 5: End-to-end briefing ────────────────────────────────


def test_end_to_end_briefing(tmp_path):
    """Set up all three modules' data -> format_briefing() includes all sources."""
    # -- memctl --
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    notes_dir = memory_dir / "notes"
    notes_dir.mkdir()
    index_file = memory_dir / "INDEX.md"

    note_file = notes_dir / "20260316-100000-001-e2e-note.md"
    note_file.write_text(textwrap.dedent("""\
        ---
        id: "20260316-100000-001"
        title: "E2E note"
        type: decision
        tags: [e2e]
        entities: [SystemX]
        confidence: high
        created: "2026-03-16T10:00:00Z"
        modified: "2026-03-16T10:00:00Z"
        expires: null
        ---

        End-to-end test note.
    """))
    note_hash = memctl_index.hash_file(str(note_file))
    idx = memctl_index.Index(
        note_count=1,
        entities=["SystemX"],
        tag_vocabulary=["e2e"],
        notes=[
            memctl_index.Entry(
                id="20260316-100000-001",
                file=str(note_file),
                title="E2E note",
                type="decision",
                tags=["e2e"],
                entities=["SystemX"],
                summary="End-to-end test note.",
                hash=note_hash,
                backlink_count=0,
                modified="2026-03-16T10:00:00Z",
            ),
        ],
    )
    memctl_index.write(str(index_file), idx)
    memctl_cfg = _write_memctl_config(tmp_path, memory_dir, index_file)

    # -- todoctl --
    items_dir = tmp_path / "backlog" / "items"
    items_dir.mkdir(parents=True)
    TodoItem.create(items_dir, title="E2E todo item", priority=2, tags=["e2e"])
    todoctl_cfg = _write_todoctl_config(tmp_path, items_dir)

    # -- nightctl --
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    runs_dir = queue_dir / "runs"
    runs_dir.mkdir()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_data = {
        "generated": now_iso,
        "job_count": 1,
        "pending": 1,
        "done": 0,
        "failed": 0,
        "jobs": [
            {
                "id": "e2e-job-001",
                "file": str(tmp_path / "jobs" / "e2e-job.yaml"),
                "title": "E2E job",
                "schedule": "overnight",
                "priority": 1,
                "status": "pending",
                "tags": [],
                "depends_on": [],
                "created": now_iso,
                "hash": "",
            },
        ],
    }
    manifest_file = queue_dir / "MANIFEST.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(manifest_data, f, default_flow_style=False, sort_keys=False)
    nightctl_cfg = _write_nightctl_config(tmp_path, manifest_file, runs_dir)

    # Collect all
    mem_data = collect_memctl(memctl_cfg)
    todo_data = collect_todoctl(todoctl_cfg)
    night_data = collect_nightctl(nightctl_cfg)

    # Format briefing
    briefing = format_briefing(mem_data, todo_data, night_data)

    # Assert text contains data from all three sources
    assert "MORNING BRIEFING" in briefing
    assert "Notes:" in briefing
    assert "1" in briefing  # note_count
    assert "Items:" in briefing
    assert "Jobs:" in briefing
    assert "Pending:" in briefing
