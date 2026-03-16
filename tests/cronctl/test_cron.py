"""Tests for halos.cronctl.cron — CronJob create, parse, validate, toggle."""
from pathlib import Path

import pytest
import yaml

from halos.cronctl.cron import CronJob, ValidationError, _slugify, validate_schedule


# ---------------------------------------------------------------------------
# CronJob.create()
# ---------------------------------------------------------------------------

class TestCreate:
    def test_create_writes_file(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path,
            title="Nightly backup",
            schedule="0 3 * * *",
            command="./backup.sh",
        )
        assert job.file_path.exists()
        assert job.title == "Nightly backup"
        assert job.schedule == "0 3 * * *"
        assert job.command == "./backup.sh"
        assert job.enabled is True

    def test_create_with_tags(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path,
            title="Check logs",
            schedule="*/5 * * * *",
            command="grep ERROR /var/log/app.log",
            tags=["monitoring", "logs"],
        )
        assert job.tags == ["monitoring", "logs"]

    def test_create_disabled(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path,
            title="Disabled job",
            schedule="0 0 * * *",
            command="echo hi",
            enabled=False,
        )
        assert job.enabled is False

    def test_create_missing_title(self, tmp_path):
        with pytest.raises(ValidationError, match="title is required"):
            CronJob.create(tmp_path, title="", schedule="0 0 * * *", command="echo")

    def test_create_missing_command(self, tmp_path):
        with pytest.raises(ValidationError, match="command is required"):
            CronJob.create(tmp_path, title="Test", schedule="0 0 * * *", command="")

    def test_create_missing_schedule(self, tmp_path):
        with pytest.raises(ValidationError, match="schedule is required"):
            CronJob.create(tmp_path, title="Test", schedule="   ", command="echo")

    def test_create_invalid_schedule(self, tmp_path):
        with pytest.raises(ValidationError, match="Invalid schedule"):
            CronJob.create(tmp_path, title="Test", schedule="bad", command="echo")


# ---------------------------------------------------------------------------
# CronJob.from_file()
# ---------------------------------------------------------------------------

class TestFromFile:
    def test_parse_from_yaml(self, tmp_path):
        data = {
            "id": "nightly-backup",
            "title": "Nightly backup",
            "schedule": "0 3 * * *",
            "command": "./backup.sh",
            "enabled": True,
            "tags": ["infra"],
            "created": "2025-01-01T00:00:00Z",
        }
        p = tmp_path / "nightly-backup.yaml"
        p.write_text(yaml.dump(data))
        job = CronJob.from_file(p)
        assert job.id == "nightly-backup"
        assert job.title == "Nightly backup"
        assert job.schedule == "0 3 * * *"
        assert job.tags == ["infra"]


# ---------------------------------------------------------------------------
# validate_schedule()
# ---------------------------------------------------------------------------

class TestValidateSchedule:
    def test_valid_every_minute(self):
        validate_schedule("* * * * *")

    def test_valid_specific_time(self):
        validate_schedule("30 2 * * *")

    def test_valid_step(self):
        validate_schedule("*/5 * * * *")

    def test_valid_range(self):
        validate_schedule("0-30 * * * *")

    def test_valid_list(self):
        validate_schedule("0,15,30,45 * * * *")

    def test_too_few_fields(self):
        with pytest.raises(ValidationError, match="expected 5 fields"):
            validate_schedule("* * *")

    def test_too_many_fields(self):
        with pytest.raises(ValidationError, match="expected 5 fields"):
            validate_schedule("* * * * * *")

    def test_invalid_field_alpha(self):
        with pytest.raises(ValidationError, match="Invalid schedule field"):
            validate_schedule("abc * * * *")

    def test_empty_string(self):
        with pytest.raises(ValidationError, match="expected 5 fields"):
            validate_schedule("")


# ---------------------------------------------------------------------------
# Enable/disable toggle
# ---------------------------------------------------------------------------

class TestToggle:
    def test_enable_disable(self, tmp_path):
        job = CronJob.create(
            jobs_dir=tmp_path,
            title="Toggle test",
            schedule="0 0 * * *",
            command="echo test",
        )
        assert job.enabled is True
        job.data["enabled"] = False
        job.save()

        reloaded = CronJob.from_file(job.file_path)
        assert reloaded.enabled is False

        reloaded.data["enabled"] = True
        reloaded.save()
        final = CronJob.from_file(job.file_path)
        assert final.enabled is True


# ---------------------------------------------------------------------------
# _slugify()
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_normal(self):
        assert _slugify("Nightly Backup") == "nightly-backup"

    def test_special_chars(self):
        assert _slugify("C++ & Rust!") == "c-rust"

    def test_truncation(self):
        result = _slugify("a" * 200)
        assert len(result) <= 60
