"""Tests for config.py — loading, defaults, partial override, deep merge, path resolution."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nightctl_lib.config import load_config, DEFAULTS


class TestConfigDefaults(unittest.TestCase):
    """Verify defaults are applied when config file is empty."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config_path = Path(self.tmp) / "nightctl.yaml"
        self.config_path.write_text("# empty\n")
        self.cfg = load_config(str(self.config_path))

    def test_default_execution_mode_is_serial(self):
        self.assertEqual(self.cfg.execution["mode"], "serial")

    def test_default_max_workers_is_1(self):
        self.assertEqual(self.cfg.execution["max_workers"], 1)

    def test_default_timezone(self):
        self.assertEqual(self.cfg.execution["timezone"], "Europe/London")

    def test_default_overnight_window(self):
        self.assertEqual(self.cfg.execution["overnight_window"], "02:00-05:00")

    def test_default_retries_is_2(self):
        self.assertEqual(self.cfg.job["default_retries"], 2)

    def test_default_timeout_is_300(self):
        self.assertEqual(self.cfg.job["default_timeout_secs"], 300)

    def test_default_schedule_is_overnight(self):
        self.assertEqual(self.cfg.job["default_schedule"], "overnight")

    def test_default_valid_schedules_complete(self):
        schedules = self.cfg.job["valid_schedules"]
        self.assertIn("overnight", schedules)
        self.assertIn("immediate", schedules)
        self.assertIn("once", schedules)

    def test_notify_on_failure_is_true(self):
        self.assertTrue(self.cfg.notify["on_failure"])

    def test_notify_on_success_is_false(self):
        self.assertFalse(self.cfg.notify["on_success"])

    def test_archive_dry_run_is_true(self):
        self.assertTrue(self.cfg.archive["dry_run"])

    def test_archive_retention_days_is_30(self):
        self.assertEqual(self.cfg.archive["retention_days"], 30)

    def test_dirs_created_on_load(self):
        self.assertTrue(self.cfg.jobs_dir.exists())
        self.assertTrue(self.cfg.archive_dir.exists())
        self.assertTrue(self.cfg.runs_dir.exists())


class TestConfigPartialOverride(unittest.TestCase):
    """Verify partial overrides apply correctly without corrupting other defaults."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config_path = Path(self.tmp) / "nightctl.yaml"

    def _load(self, content):
        self.config_path.write_text(content)
        return load_config(str(self.config_path))

    def test_override_execution_mode_preserves_other_keys(self):
        cfg = self._load("execution:\n  mode: parallel\n")
        self.assertEqual(cfg.execution["mode"], "parallel")
        # other execution keys must survive the partial override
        self.assertEqual(cfg.execution["max_workers"], 1)
        self.assertEqual(cfg.execution["timezone"], "Europe/London")
        self.assertEqual(cfg.execution["overnight_window"], "02:00-05:00")

    def test_override_retries_preserves_other_job_keys(self):
        cfg = self._load("job:\n  default_retries: 5\n")
        self.assertEqual(cfg.job["default_retries"], 5)
        # other job keys must survive
        self.assertEqual(cfg.job["default_timeout_secs"], 300)
        self.assertEqual(cfg.job["default_schedule"], "overnight")

    def test_override_window_only(self):
        cfg = self._load('execution:\n  overnight_window: "23:00-06:00"\n')
        self.assertEqual(cfg.execution["overnight_window"], "23:00-06:00")
        self.assertEqual(cfg.execution["mode"], "serial")

    def test_override_archive_dry_run_to_false(self):
        cfg = self._load("archive:\n  dry_run: false\n")
        self.assertFalse(cfg.archive["dry_run"])
        # retention_days should still be default
        self.assertEqual(cfg.archive["retention_days"], 30)

    def test_override_notify_on_failure(self):
        cfg = self._load("notify:\n  on_failure: false\n")
        self.assertFalse(cfg.notify["on_failure"])
        # on_success default preserved
        self.assertFalse(cfg.notify["on_success"])

    def test_custom_queue_dir_is_absolute_after_resolution(self):
        custom = Path(self.tmp) / "myqueue"
        cfg = self._load(f"queue_dir: {custom}\n")
        self.assertTrue(cfg.queue_dir.is_absolute())
        self.assertEqual(cfg.queue_dir, custom)

    def test_retention_days_override(self):
        cfg = self._load("archive:\n  retention_days: 7\n")
        self.assertEqual(cfg.archive["retention_days"], 7)


class TestConfigPathResolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config_path = Path(self.tmp) / "nightctl.yaml"
        self.config_path.write_text("# empty\n")
        self.cfg = load_config(str(self.config_path))

    def test_all_paths_are_absolute(self):
        self.assertTrue(self.cfg.queue_dir.is_absolute())
        self.assertTrue(self.cfg.archive_dir.is_absolute())
        self.assertTrue(self.cfg.runs_dir.is_absolute())
        self.assertTrue(self.cfg.manifest_file.is_absolute())

    def test_jobs_dir_is_child_of_queue_dir(self):
        self.assertEqual(self.cfg.jobs_dir.parent, self.cfg.queue_dir)

    def test_archive_dir_not_same_as_jobs_dir(self):
        self.assertNotEqual(self.cfg.archive_dir, self.cfg.jobs_dir)

    def test_runs_dir_not_same_as_jobs_dir(self):
        self.assertNotEqual(self.cfg.runs_dir, self.cfg.jobs_dir)

    def test_manifest_file_inside_queue_dir(self):
        self.assertTrue(str(self.cfg.manifest_file).startswith(str(self.cfg.queue_dir)))

    def test_missing_config_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/path/nightctl.yaml")


class TestConfigInvalidYaml(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config_path = Path(self.tmp) / "nightctl.yaml"

    def test_empty_config_file_uses_all_defaults(self):
        self.config_path.write_text("")
        cfg = load_config(str(self.config_path))
        self.assertEqual(cfg.execution["mode"], "serial")
        self.assertEqual(cfg.job["default_retries"], 2)

    def test_comment_only_config_uses_all_defaults(self):
        self.config_path.write_text("# nothing here\n# just comments\n")
        cfg = load_config(str(self.config_path))
        self.assertEqual(cfg.archive["dry_run"], True)


if __name__ == "__main__":
    unittest.main()
