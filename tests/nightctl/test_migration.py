"""Tests for todoctl → nightctl migration."""

import os
import pytest
from pathlib import Path

import yaml

from halos.nightctl.migrate_todoctl import migrate_item, run_migration
from halos.nightctl.item import Item


@pytest.fixture
def tmp_dirs(tmp_path):
    """Create source and dest directories for migration tests."""
    source = tmp_path / "backlog" / "items"
    dest = tmp_path / "queue" / "items"
    source.mkdir(parents=True)
    dest.mkdir(parents=True)
    return source, dest


def _write_todoctl_item(source_dir: Path, data: dict) -> Path:
    """Helper to write a todoctl-style YAML item."""
    item_id = data["id"]
    title_slug = data["title"].lower().replace(" ", "-")[:40]
    filename = f"{item_id}-{title_slug}.yaml"
    path = source_dir / filename
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return path


SAMPLE_TODOCTL_ITEM = {
    "id": "20260316-030915",
    "title": "Add workspace subdirectories to memctl",
    "status": "open",
    "priority": 2,
    "tags": ["memctl", "architecture"],
    "context": "memory/notes/ is flat. Need namespace support.",
    "created": "2026-03-16T03:09:15Z",
    "due": None,
    "blocked_by": None,
}


DONE_TODOCTL_ITEM = {
    "id": "20260316-030921",
    "title": "Overnight research: halos module brainstorm",
    "status": "done",
    "priority": 3,
    "tags": ["halos", "architecture"],
    "context": "Brainstorm nanoclaw capabilities.",
    "created": "2026-03-16T03:09:21Z",
    "due": None,
    "blocked_by": None,
    "modified": "2026-03-17T07:40:49Z",
}


ITEM_WITH_ENTITIES = {
    "id": "20260317-075446-291",
    "title": "Merge todoctl into nightctl: unified work tracker",
    "status": "open",
    "priority": 1,
    "tags": ["halos", "architecture"],
    "context": "nightctl becomes SSOT for all work items.",
    "created": "2026-03-17T07:54:46Z",
    "due": None,
    "blocked_by": None,
    "entities": ["todoctl", "nightctl"],
}


class TestMigrateItem:
    def test_basic_migration(self, tmp_dirs):
        source, dest = tmp_dirs
        result = migrate_item(SAMPLE_TODOCTL_ITEM, dest)

        assert result["outcome"] == "ok"
        assert result["id"] == "20260316-030915"
        assert result["status"] == "open"

        # Verify the file was written
        written_files = list(dest.glob("*.yaml"))
        assert len(written_files) == 1

        # Load and verify the migrated item
        item = Item.from_file(written_files[0])
        assert item.id == "20260316-030915"
        assert item.title == "Add workspace subdirectories to memctl"
        assert item.kind == "task"
        assert item.status == "open"
        assert item.priority == 2
        assert item.tags == ["memctl", "architecture"]
        assert item.context == "memory/notes/ is flat. Need namespace support."
        assert item.created == "2026-03-16T03:09:15Z"
        assert item.due is None
        assert item.blocked_by is None

    def test_preserves_status(self, tmp_dirs):
        source, dest = tmp_dirs
        result = migrate_item(DONE_TODOCTL_ITEM, dest)
        assert result["outcome"] == "ok"

        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert item.status == "done"

    def test_preserves_entities(self, tmp_dirs):
        source, dest = tmp_dirs
        result = migrate_item(ITEM_WITH_ENTITIES, dest)
        assert result["outcome"] == "ok"

        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert item.entities == ["todoctl", "nightctl"]

    def test_preserves_modified(self, tmp_dirs):
        source, dest = tmp_dirs
        result = migrate_item(DONE_TODOCTL_ITEM, dest)
        assert result["outcome"] == "ok"

        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert item.modified == "2026-03-17T07:40:49Z"

    def test_kind_defaults_to_task(self, tmp_dirs):
        source, dest = tmp_dirs
        result = migrate_item(SAMPLE_TODOCTL_ITEM, dest)
        assert result["outcome"] == "ok"

        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert item.kind == "task"

    def test_machine_fields_null(self, tmp_dirs):
        source, dest = tmp_dirs
        migrate_item(SAMPLE_TODOCTL_ITEM, dest)

        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert item.command is None
        assert item.schedule is None
        assert item.window is None
        assert item.plan is None
        assert item.plan_ref is None

    def test_dry_run_does_not_write(self, tmp_dirs):
        source, dest = tmp_dirs
        result = migrate_item(SAMPLE_TODOCTL_ITEM, dest, dry_run=True)
        assert result["outcome"] == "dry-run"

        written = list(dest.glob("*.yaml"))
        assert len(written) == 0

    def test_preserves_priority(self, tmp_dirs):
        source, dest = tmp_dirs
        for item_data in [SAMPLE_TODOCTL_ITEM, DONE_TODOCTL_ITEM, ITEM_WITH_ENTITIES]:
            migrate_item(item_data, dest)

        written = sorted(dest.glob("*.yaml"))
        priorities = []
        for f in written:
            item = Item.from_file(f)
            priorities.append(item.priority)
        assert 1 in priorities
        assert 2 in priorities
        assert 3 in priorities

    def test_preserves_tags(self, tmp_dirs):
        source, dest = tmp_dirs
        migrate_item(SAMPLE_TODOCTL_ITEM, dest)

        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert "memctl" in item.tags
        assert "architecture" in item.tags

    def test_preserves_created(self, tmp_dirs):
        source, dest = tmp_dirs
        migrate_item(SAMPLE_TODOCTL_ITEM, dest)

        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert item.created == "2026-03-16T03:09:15Z"


class TestRunMigration:
    def test_full_migration(self, tmp_dirs):
        source, dest = tmp_dirs

        # Write multiple items to source
        _write_todoctl_item(source, SAMPLE_TODOCTL_ITEM)
        _write_todoctl_item(source, DONE_TODOCTL_ITEM)
        _write_todoctl_item(source, ITEM_WITH_ENTITIES)

        results = run_migration(source, dest)
        assert len(results) == 3
        assert all(r["outcome"] == "ok" for r in results)

        # Verify all items load from dest
        items = []
        for f in sorted(dest.glob("*.yaml")):
            items.append(Item.from_file(f))
        assert len(items) == 3

    def test_empty_source(self, tmp_dirs):
        source, dest = tmp_dirs
        results = run_migration(source, dest)
        assert len(results) == 0

    def test_nonexistent_source(self, tmp_path):
        source = tmp_path / "nonexistent"
        dest = tmp_path / "dest"
        results = run_migration(source, dest)
        assert len(results) == 0

    def test_creates_dest_dir(self, tmp_dirs):
        source, _ = tmp_dirs
        dest = source.parent / "new_dest" / "items"

        _write_todoctl_item(source, SAMPLE_TODOCTL_ITEM)
        results = run_migration(source, dest)
        assert len(results) == 1
        assert dest.exists()

    def test_malformed_yaml_skipped(self, tmp_dirs):
        source, dest = tmp_dirs

        _write_todoctl_item(source, SAMPLE_TODOCTL_ITEM)
        # Write a malformed file
        bad_file = source / "bad-file.yaml"
        bad_file.write_text("{{invalid yaml")

        results = run_migration(source, dest)
        assert len(results) == 2

        ok_results = [r for r in results if r["outcome"] == "ok"]
        error_results = [r for r in results if "error" in r["outcome"]]
        assert len(ok_results) == 1
        assert len(error_results) == 1

    def test_dry_run_full(self, tmp_dirs):
        source, dest = tmp_dirs

        _write_todoctl_item(source, SAMPLE_TODOCTL_ITEM)
        _write_todoctl_item(source, DONE_TODOCTL_ITEM)

        results = run_migration(source, dest, dry_run=True)
        assert len(results) == 2
        assert all(r["outcome"] == "dry-run" for r in results)

        # Nothing written in dry-run
        written = list(dest.glob("*.yaml"))
        assert len(written) == 0

    def test_migrated_items_loadable_by_item_from_file(self, tmp_dirs):
        """Verify that every migrated item can be loaded by Item.from_file()."""
        source, dest = tmp_dirs

        _write_todoctl_item(source, SAMPLE_TODOCTL_ITEM)
        _write_todoctl_item(source, DONE_TODOCTL_ITEM)
        _write_todoctl_item(source, ITEM_WITH_ENTITIES)

        run_migration(source, dest)

        for f in dest.glob("*.yaml"):
            item = Item.from_file(f)
            item.validate()
            assert item.kind == "task"
            assert item.id
            assert item.title
