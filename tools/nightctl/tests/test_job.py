"""Tests for job.py — creation, validation, schema, persistence."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nightctl_lib.job import Job, ValidationError, VALID_STATUSES, VALID_SCHEDULES

CFG_JOB = {
    "default_retries": 2,
    "default_timeout_secs": 300,
    "default_schedule": "overnight",
    "valid_schedules": ["overnight", "immediate", "once"],
    "valid_tags": ["maintenance", "memctl", "data", "infra"],
}


class TestJobCreate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _make(self, **kwargs):
        defaults = {
            "title": "Test job",
            "command": "echo test",
            "tags": ["maintenance"],
        }
        defaults.update(kwargs)
        return Job.create(self.tmp, CFG_JOB, **defaults)

    def test_creates_file_on_disk(self):
        job, _ = self._make()
        self.assertTrue(job.file_path.exists())
        self.assertGreater(job.file_path.stat().st_size, 0)

    def test_id_format_is_timestamp_plus_8_hex(self):
        job, _ = self._make()
        parts = job.id.split("-")
        self.assertEqual(len(parts), 3, f"Expected 3 parts, got {parts}")
        self.assertEqual(len(parts[0]), 8, "First part should be YYYYMMDD")
        self.assertEqual(len(parts[1]), 6, "Second part should be HHMMSS")
        self.assertEqual(len(parts[2]), 8, "Third part should be 8 hex chars")
        # hex chars must actually be hex
        int(parts[2], 16)

    def test_ids_are_unique_across_rapid_calls(self):
        ids = {Job.create(self.tmp, CFG_JOB, title=f"J{i}", command="echo")[0].id
               for i in range(20)}
        self.assertEqual(len(ids), 20, "All 20 rapidly-created jobs must have unique IDs")

    def test_status_is_pending_at_creation(self):
        job, _ = self._make()
        self.assertEqual(job.status, "pending")
        # verify it's in the file too, not just in-memory
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.status, "pending")

    def test_created_by_is_agent(self):
        job, _ = self._make()
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.data["created_by"], "agent")

    def test_filename_contains_slug_of_title(self):
        job, _ = self._make(title="Rebuild Memctl Index")
        self.assertIn("rebuild-memctl-index", job.file_path.name)

    def test_filename_starts_with_id(self):
        job, _ = self._make()
        self.assertTrue(job.file_path.name.startswith(job.id))

    def test_default_retries_from_config(self):
        job, _ = self._make()
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.retries, 2)

    def test_custom_retries_written_to_file(self):
        job, _ = self._make(retries=5)
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.retries, 5)
        self.assertEqual(reloaded.retries_remaining, 5)

    def test_retries_zero_written_as_zero_not_null(self):
        job, _ = self._make(retries=0)
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.retries, 0)
        self.assertIsInstance(reloaded.retries, int)

    def test_default_schedule_is_overnight(self):
        job, _ = self._make()
        self.assertEqual(job.schedule, "overnight")

    def test_custom_schedule_immediate(self):
        job, _ = self._make(schedule="immediate")
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.schedule, "immediate")

    def test_priority_written_to_file(self):
        job, _ = self._make(priority=2)
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.priority, 2)

    def test_tags_written_to_file(self):
        job, _ = self._make(tags=["memctl", "data"])
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.tags, ["memctl", "data"])

    def test_unknown_tag_produces_warning(self):
        _, warnings = self._make(tags=["unknown-tag"])
        self.assertTrue(any("unknown tag" in w for w in warnings))
        self.assertTrue(any("unknown-tag" in w for w in warnings))

    def test_known_tags_produce_no_warnings(self):
        _, warnings = self._make(tags=["maintenance"])
        self.assertEqual(warnings, [])

    def test_depends_on_written_to_file(self):
        job, _ = self._make(depends_on=["20260101-000000-abcdef12"])
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.depends_on, ["20260101-000000-abcdef12"])

    def test_empty_depends_on(self):
        job, _ = self._make(depends_on=[])
        reloaded = Job.from_file(job.file_path)
        self.assertIsInstance(reloaded.depends_on, list)
        self.assertEqual(len(reloaded.depends_on), 0)

    def test_entities_written_to_file(self):
        job, _ = self._make(entities=["project-alpha"])
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.data.get("entities"), ["project-alpha"])

    def test_created_timestamp_is_iso8601(self):
        job, _ = self._make()
        reloaded = Job.from_file(job.file_path)
        ts = reloaded.created
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

    def test_command_preserved_exactly(self):
        cmd = 'python3 -c "import sys; sys.exit(0)"'
        job, _ = self._make(command=cmd)
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.command, cmd)


class TestJobValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _make(self, **kwargs):
        return Job.create(self.tmp, CFG_JOB, **kwargs)

    def test_missing_title_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            self._make(command="echo hi")
        self.assertIn("title", str(ctx.exception).lower())

    def test_empty_title_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self._make(title="", command="echo hi")

    def test_whitespace_only_title_raises(self):
        with self.assertRaises(ValidationError):
            self._make(title="   ", command="echo hi")

    def test_missing_command_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            self._make(title="Test job")
        self.assertIn("command", str(ctx.exception).lower())

    def test_empty_command_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self._make(title="Test job", command="")

    def test_invalid_schedule_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            self._make(title="T", command="echo", schedule="daily")
        self.assertIn("daily", str(ctx.exception))

    def test_all_valid_schedules_accepted(self):
        for sched in ["overnight", "immediate", "once"]:
            job, _ = self._make(title=f"job-{sched}", command="echo", schedule=sched)
            self.assertEqual(job.schedule, sched)


class TestJobStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.job, _ = Job.create(self.tmp, CFG_JOB, title="T", command="echo hi")

    def test_all_valid_statuses_accepted(self):
        for s in VALID_STATUSES:
            self.job.set_status(s)
            self.assertEqual(self.job.status, s)

    def test_invalid_status_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.job.set_status("invalid")

    def test_invalid_status_does_not_change_current_status(self):
        self.job.set_status("claimed")
        try:
            self.job.set_status("bogus")
        except ValidationError:
            pass
        self.assertEqual(self.job.status, "claimed")

    def test_decrement_retries_reduces_remaining_by_1(self):
        self.job.data["retries_remaining"] = 2
        remaining = self.job.decrement_retries()
        self.assertEqual(remaining, 1)
        self.assertEqual(self.job.retries_remaining, 1)

    def test_decrement_retries_from_zero_goes_negative(self):
        self.job.data["retries_remaining"] = 0
        remaining = self.job.decrement_retries()
        self.assertEqual(remaining, -1)

    def test_retries_remaining_defaults_to_retries(self):
        job, _ = Job.create(self.tmp, CFG_JOB, title="X", command="echo", retries=3)
        self.assertEqual(job.retries_remaining, 3)


class TestJobPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_save_persists_status_change(self):
        job, _ = Job.create(self.tmp, CFG_JOB, title="Test", command="echo hi")
        job.set_status("done")
        job.save()
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.status, "done")

    def test_save_persists_retries_remaining(self):
        job, _ = Job.create(self.tmp, CFG_JOB, title="Test", command="echo hi", retries=2)
        job.decrement_retries()
        job.save()
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.retries_remaining, 1)

    def test_file_hash_changes_after_status_update(self):
        job, _ = Job.create(self.tmp, CFG_JOB, title="Test", command="echo hi")
        h1 = job.file_hash()
        job.set_status("claimed")
        job.save()
        h2 = job.file_hash()
        self.assertNotEqual(h1, h2, "File hash must change when content changes")

    def test_file_hash_stable_without_changes(self):
        job, _ = Job.create(self.tmp, CFG_JOB, title="Test", command="echo hi")
        h1 = job.file_hash()
        h2 = job.file_hash()
        self.assertEqual(h1, h2, "Hash must be stable when file hasn't changed")

    def test_from_file_preserves_all_fields(self):
        job, _ = Job.create(
            self.tmp, CFG_JOB,
            title="Full test", command="echo hi",
            tags=["maintenance", "data"], priority=3,
            retries=1
        )
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.id, job.id)
        self.assertEqual(reloaded.title, job.title)
        self.assertEqual(reloaded.command, job.command)
        self.assertEqual(reloaded.tags, job.tags)
        self.assertEqual(reloaded.priority, job.priority)
        self.assertEqual(reloaded.retries, job.retries)

    def test_from_file_nonexistent_raises(self):
        with self.assertRaises((FileNotFoundError, Exception)):
            Job.from_file(Path("/nonexistent/job.yaml"))


if __name__ == "__main__":
    unittest.main()
