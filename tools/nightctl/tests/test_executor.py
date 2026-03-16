"""Tests for executor.py — window check, serial run, retries, dep resolution, timeouts."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nightctl_lib.job import Job
from nightctl_lib.manifest import Manifest
from nightctl_lib.executor import Executor, _in_window, _parse_window
from nightctl_lib.notify import Notifier

CFG_JOB = {
    "default_retries": 2,
    "default_timeout_secs": 300,
    "default_schedule": "overnight",
    "valid_schedules": ["overnight", "immediate", "once"],
    "valid_tags": [],
}


def make_job(jobs_dir, title="Test", command="echo hi", priority=5,
             depends_on=None, retries=2, timeout_secs=300):
    job, _ = Job.create(jobs_dir, CFG_JOB, title=title, command=command,
                        priority=priority, depends_on=depends_on or [],
                        retries=retries, timeout_secs=timeout_secs)
    return job


class FakeCfg:
    def __init__(self, tmp):
        self.tmp = tmp
        self.execution = {
            "mode": "serial",
            "max_workers": 1,
            "overnight_window": "02:00-05:00",
            "timezone": "UTC",
        }
        self.notify = {"on_failure": False, "on_success": False}
        self.runs_dir = tmp / "runs"
        self.runs_dir.mkdir(exist_ok=True)


class TestWindowCheck(unittest.TestCase):
    def _fake_now(self, hour, minute, tz="UTC"):
        return datetime(2026, 3, 15, hour, minute, tzinfo=ZoneInfo(tz))

    def _check(self, window, hour, minute):
        fake = self._fake_now(hour, minute)
        with patch("nightctl_lib.executor.datetime") as mock_dt:
            mock_dt.now.return_value = fake
            return _in_window(window, "UTC")

    def test_in_window_start_boundary(self):
        self.assertTrue(self._check("02:00-05:00", 2, 0))

    def test_in_window_middle(self):
        self.assertTrue(self._check("02:00-05:00", 3, 30))

    def test_outside_window_one_minute_before(self):
        self.assertFalse(self._check("02:00-05:00", 1, 59))

    def test_outside_window_at_end_boundary(self):
        self.assertFalse(self._check("02:00-05:00", 5, 0))

    def test_outside_window_midday(self):
        self.assertFalse(self._check("02:00-05:00", 12, 0))

    def test_midnight_crossing_window_in_range_before_midnight(self):
        self.assertTrue(self._check("23:00-03:00", 23, 30))

    def test_midnight_crossing_window_in_range_after_midnight(self):
        self.assertTrue(self._check("23:00-03:00", 1, 0))

    def test_midnight_crossing_window_outside_range(self):
        self.assertFalse(self._check("23:00-03:00", 12, 0))

    def test_midnight_crossing_outside_at_end(self):
        self.assertFalse(self._check("23:00-03:00", 3, 0))

    def test_parse_window_returns_four_ints(self):
        sh, sm, eh, em = _parse_window("02:00-05:00")
        self.assertEqual((sh, sm, eh, em), (2, 0, 5, 0))

    def test_parse_window_with_minutes(self):
        sh, sm, eh, em = _parse_window("22:30-06:45")
        self.assertEqual((sh, sm, eh, em), (22, 30, 6, 45))


class TestExecutorRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = FakeCfg(self.tmp)
        self.manifest = Manifest(self.tmp / "MANIFEST.yaml")
        self.notifier = Notifier({"on_failure": False, "on_success": False})
        self.executor = Executor(self.cfg, self.manifest, self.notifier)

    def _run_force(self, limit=None, dry_run=False):
        return self.executor.run(force=True, limit=limit, dry_run=dry_run)

    def test_force_flag_bypasses_window(self):
        job = make_job(self.tmp)
        self.manifest.append(job)
        counts = self._run_force()
        self.assertEqual(counts["done"], 1)

    def test_outside_window_skips_all_without_force(self):
        self.cfg.execution["overnight_window"] = "00:00-00:01"
        job = make_job(self.tmp)
        self.manifest.append(job)
        counts = self.executor.run(force=False)
        self.assertTrue(counts.get("outside_window"))
        # job must remain pending — it was not executed
        entry = self.manifest.get_entry(job.id)
        self.assertEqual(entry["status"], "pending")

    def test_successful_job_marked_done_in_manifest(self):
        job = make_job(self.tmp, command="echo success")
        self.manifest.append(job)
        self._run_force()
        entry = self.manifest.get_entry(job.id)
        self.assertEqual(entry["status"], "done")

    def test_successful_job_marked_done_in_file(self):
        job = make_job(self.tmp, command="echo success")
        self.manifest.append(job)
        self._run_force()
        reloaded = Job.from_file(job.file_path)
        self.assertEqual(reloaded.status, "done")

    def test_run_record_written_for_each_job(self):
        j1 = make_job(self.tmp, title="A", command="echo a")
        j2 = make_job(self.tmp, title="B", command="echo b")
        self.manifest.append(j1)
        self.manifest.append(j2)
        self._run_force()
        self.assertEqual(len(list(self.cfg.runs_dir.glob(f"{j1.id}-run-*.yaml"))), 1)
        self.assertEqual(len(list(self.cfg.runs_dir.glob(f"{j2.id}-run-*.yaml"))), 1)

    def test_run_record_captures_stdout(self):
        try:
            import yaml
        except ImportError:
            from nightctl_lib import yaml_shim as yaml
        job = make_job(self.tmp, command="echo hello-world")
        self.manifest.append(job)
        self._run_force()
        run_files = list(self.cfg.runs_dir.glob(f"{job.id}-run-*.yaml"))
        self.assertEqual(len(run_files), 1)
        with open(run_files[0]) as f:
            record = yaml.safe_load(f)
        self.assertIn("hello-world", record["stdout"])
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["outcome"], "done")

    def test_failed_job_with_zero_retries_marked_failed(self):
        job = make_job(self.tmp, command="exit 1", retries=0)
        self.manifest.append(job)
        counts = self._run_force()
        self.assertEqual(counts["failed"], 1)
        self.assertEqual(self.manifest.get_entry(job.id)["status"], "failed")

    def test_failed_job_with_retries_returns_to_pending(self):
        job = make_job(self.tmp, command="exit 1", retries=2)
        self.manifest.append(job)
        self._run_force()
        # with retries remaining it should go back to pending, not failed
        entry = self.manifest.get_entry(job.id)
        self.assertEqual(entry["status"], "pending")

    def test_retries_remaining_decrements_on_failure(self):
        job = make_job(self.tmp, command="exit 1", retries=2)
        self.manifest.append(job)
        self._run_force()
        reloaded = Job.from_file(job.file_path)
        self.assertLess(reloaded.retries_remaining, 2)

    def test_priority_ordering_without_mocks(self):
        """Jobs must execute in priority order — verified by run record timestamps."""
        j_low = make_job(self.tmp, title="Low", command="echo low", priority=10)
        j_high = make_job(self.tmp, title="High", command="echo high", priority=1)
        j_mid = make_job(self.tmp, title="Mid", command="echo mid", priority=5)
        for j in [j_low, j_high, j_mid]:
            self.manifest.append(j)
        self._run_force()
        try:
            import yaml
        except ImportError:
            from nightctl_lib import yaml_shim as yaml
        def run_start(job_id):
            files = list(self.cfg.runs_dir.glob(f"{job_id}-run-*.yaml"))
            if not files:
                return None
            with open(files[0]) as f:
                return yaml.safe_load(f)["started"]
        t_high = run_start(j_high.id)
        t_mid = run_start(j_mid.id)
        t_low = run_start(j_low.id)
        self.assertIsNotNone(t_high)
        self.assertIsNotNone(t_mid)
        self.assertIsNotNone(t_low)
        self.assertLessEqual(t_high, t_mid)
        self.assertLessEqual(t_mid, t_low)

    def test_run_limit_stops_at_n_jobs(self):
        for i in range(5):
            self.manifest.append(make_job(self.tmp, title=f"Job {i}"))
        counts = self._run_force(limit=2)
        self.assertEqual(counts["done"], 2)
        remaining_pending = len(self.manifest.pending_jobs())
        self.assertEqual(remaining_pending, 3)

    def test_no_jobs_produces_zero_counts(self):
        counts = self._run_force()
        self.assertEqual(counts["done"], 0)
        self.assertEqual(counts["failed"], 0)
        self.assertEqual(counts["skipped"], 0)

    def test_exit_code_captured_in_run_record(self):
        try:
            import yaml
        except ImportError:
            from nightctl_lib import yaml_shim as yaml
        job = make_job(self.tmp, command="exit 42", retries=0)
        self.manifest.append(job)
        self._run_force()
        run_files = list(self.cfg.runs_dir.glob(f"{job.id}-run-*.yaml"))
        with open(run_files[0]) as f:
            record = yaml.safe_load(f)
        self.assertEqual(record["exit_code"], 42)
        self.assertEqual(record["outcome"], "failed")

    def test_job_timeout_recorded_in_run_record(self):
        try:
            import yaml
        except ImportError:
            from nightctl_lib import yaml_shim as yaml
        job = make_job(self.tmp, command="sleep 10", timeout_secs=1, retries=0)
        self.manifest.append(job)
        self._run_force()
        run_files = list(self.cfg.runs_dir.glob(f"{job.id}-run-*.yaml"))
        self.assertEqual(len(run_files), 1)
        with open(run_files[0]) as f:
            record = yaml.safe_load(f)
        self.assertEqual(record["outcome"], "timeout")
        self.assertEqual(record["exit_code"], -1)
        self.assertIn("timeout", record["stderr"])


class TestDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = FakeCfg(self.tmp)
        self.manifest = Manifest(self.tmp / "MANIFEST.yaml")
        self.notifier = Notifier({"on_failure": False, "on_success": False})
        self.executor = Executor(self.cfg, self.manifest, self.notifier)

    def test_dry_run_writes_no_run_records(self):
        job = make_job(self.tmp, command="echo hi")
        self.manifest.append(job)
        self.executor.run(force=True, dry_run=True)
        run_files = list(self.cfg.runs_dir.glob(f"{job.id}-run-*.yaml"))
        self.assertEqual(len(run_files), 0, "dry-run must not write run records")

    def test_dry_run_does_not_execute_command(self):
        # If the command actually runs it would create a sentinel file
        sentinel = self.tmp / "sentinel_created"
        job = make_job(self.tmp, command=f"touch {sentinel}")
        self.manifest.append(job)
        self.executor.run(force=True, dry_run=True)
        self.assertFalse(sentinel.exists(), "dry-run must not execute the command")


class TestDependencies(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = FakeCfg(self.tmp)
        self.manifest = Manifest(self.tmp / "MANIFEST.yaml")
        self.notifier = Notifier({"on_failure": False, "on_success": False})
        self.executor = Executor(self.cfg, self.manifest, self.notifier)

    def test_child_runs_after_dep_completes(self):
        dep = make_job(self.tmp, title="Dep", command="echo dep", priority=1)
        child = make_job(self.tmp, title="Child", command="echo child", priority=2,
                         depends_on=[dep.id])
        self.manifest.append(dep)
        self.manifest.append(child)
        counts = self.executor.run(force=True)
        self.assertEqual(counts["done"], 2)
        self.assertEqual(self.manifest.get_entry(child.id)["status"], "done")

    def test_child_skipped_when_dep_fails(self):
        dep = make_job(self.tmp, title="Dep", command="exit 1", retries=0)
        child = make_job(self.tmp, title="Child", command="echo child",
                         depends_on=[dep.id])
        self.manifest.append(dep)
        self.manifest.append(child)
        counts = self.executor.run(force=True)
        self.assertEqual(counts["failed"], 1)
        self.assertEqual(counts["skipped"], 1)
        # child must remain pending and must not have a run record
        self.assertEqual(self.manifest.get_entry(child.id)["status"], "pending")
        run_files = list(self.cfg.runs_dir.glob(f"{child.id}-run-*.yaml"))
        self.assertEqual(len(run_files), 0, "skipped child must have no run records")

    def test_job_with_nonexistent_dep_is_skipped(self):
        job = make_job(self.tmp, title="Orphan child",
                       depends_on=["20260101-000000-00000000"])
        self.manifest.append(job)
        counts = self.executor.run(force=True)
        self.assertEqual(counts["skipped"], 1)
        self.assertEqual(counts["done"], 0)

    def test_job_with_no_deps_always_runs(self):
        job = make_job(self.tmp, title="Free", command="echo free", depends_on=[])
        self.manifest.append(job)
        counts = self.executor.run(force=True)
        self.assertEqual(counts["done"], 1)


if __name__ == "__main__":
    unittest.main()
