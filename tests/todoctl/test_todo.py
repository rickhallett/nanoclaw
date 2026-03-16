"""Tests for halos.todoctl.todo — TodoItem create, parse, validate, transitions."""
from pathlib import Path

import pytest
import yaml

from halos.todoctl.todo import VALID_STATUSES, TodoItem, ValidationError, _slugify


# ---------------------------------------------------------------------------
# TodoItem.create()
# ---------------------------------------------------------------------------

class TestCreate:
    def test_create_writes_file(self, tmp_path):
        item = TodoItem.create(items_dir=tmp_path, title="Fix the build")
        assert item.file_path.exists()
        assert item.title == "Fix the build"
        assert item.status == "open"
        assert item.priority == 3

    def test_create_with_all_fields(self, tmp_path):
        item = TodoItem.create(
            items_dir=tmp_path,
            title="Deploy v2",
            priority=1,
            tags=["infra", "urgent"],
            context="Production deployment",
            due="2025-06-01",
        )
        assert item.priority == 1
        assert item.tags == ["infra", "urgent"]
        assert item.context == "Production deployment"
        assert item.due == "2025-06-01"

    def test_create_missing_title(self, tmp_path):
        with pytest.raises(ValidationError, match="title is required"):
            TodoItem.create(items_dir=tmp_path, title="")

    def test_create_whitespace_title(self, tmp_path):
        with pytest.raises(ValidationError, match="title is required"):
            TodoItem.create(items_dir=tmp_path, title="   ")


# ---------------------------------------------------------------------------
# TodoItem.from_file()
# ---------------------------------------------------------------------------

class TestFromFile:
    def test_parse_from_yaml(self, tmp_path):
        data = {
            "id": "20250101-120000",
            "title": "Test item",
            "status": "in-progress",
            "priority": 2,
            "tags": ["dev"],
            "context": "Testing context",
            "created": "2025-01-01T12:00:00Z",
            "due": "2025-02-01",
            "blocked_by": None,
        }
        p = tmp_path / "item.yaml"
        p.write_text(yaml.dump(data))
        item = TodoItem.from_file(p)
        assert item.id == "20250101-120000"
        assert item.title == "Test item"
        assert item.status == "in-progress"
        assert item.priority == 2
        assert item.tags == ["dev"]


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

class TestStatusTransitions:
    def _create_item(self, tmp_path, status="open"):
        item = TodoItem.create(items_dir=tmp_path, title="Transition test")
        item.data["status"] = status
        item.save()
        return item

    def test_open_to_in_progress(self, tmp_path):
        item = self._create_item(tmp_path, "open")
        item.data["status"] = "in-progress"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.status == "in-progress"

    def test_in_progress_to_done(self, tmp_path):
        item = self._create_item(tmp_path, "in-progress")
        item.data["status"] = "done"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.status == "done"

    def test_open_to_deferred(self, tmp_path):
        item = self._create_item(tmp_path, "open")
        item.data["status"] = "deferred"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.status == "deferred"

    def test_open_to_blocked(self, tmp_path):
        item = self._create_item(tmp_path, "open")
        item.data["status"] = "blocked"
        item.data["blocked_by"] = "other-item-id"
        item.save()
        reloaded = TodoItem.from_file(item.file_path)
        assert reloaded.status == "blocked"
        assert reloaded.blocked_by == "other-item-id"

    def test_all_valid_statuses(self):
        assert "open" in VALID_STATUSES
        assert "in-progress" in VALID_STATUSES
        assert "done" in VALID_STATUSES
        assert "blocked" in VALID_STATUSES
        assert "deferred" in VALID_STATUSES


# ---------------------------------------------------------------------------
# save() without file_path
# ---------------------------------------------------------------------------

class TestSaveErrors:
    def test_save_without_path_raises(self):
        item = TodoItem(data={"id": "x", "title": "y"})
        with pytest.raises(RuntimeError, match="No file path"):
            item.save()


# ---------------------------------------------------------------------------
# _slugify()
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_normal(self):
        assert _slugify("Fix the build") == "fix-the-build"

    def test_special_chars(self):
        assert _slugify("Deploy v2.0!") == "deploy-v20"

    def test_truncation(self):
        result = _slugify("a" * 200)
        assert len(result) <= 60
