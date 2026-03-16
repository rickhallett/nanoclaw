"""Tests for archive.py — archive (move done jobs) and hatch (permanent eject)."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nightctl_lib.job import Job
from nightctl_lib.manifest import Manifest
from nightctl_lib.archive import run_archive, run_hatch

CFG_JOB = {
    "default_retries": 2,
    "default_timeout_secs": 300,
    "default_schedule": "overnight",
    "valid_schedules": ["overnight", "immediate", "once"],
    "valid_tags": [],
}


class FakeCfg:
    def __init__(self, tmp, retention_days=30, dry_run=True):
        self.jobs_dir = tmp / "jobs"
        self.jobs_dir.mkdir(exist_ok=True)
        self.archive_dir = tmp / "archive"
        self.archive_dir.mkdir(exist_ok=True)
        self.runs_dir = tmp / "runs"
        self.runs_dir.mkdir(exist_ok=True)
        self.archive = {"retention_days": retention_days, "dry_run": dry_run}


def make_job(jobs_dir, title="Test", status="done", days_old=0):
    job, _ = Job.create(jobs_dir, CFG_JOB, title=title, command="echo hi")
    job.set_status(status)
    if days_old > 0:
        old_ts = (datetime.now(timezone.utc) - timedelta(days=days_old)).strftime("%Y-%m-%dT%H:%M:%SZ")
        job.data["created"] = old_ts
    job.save()
    return job


class TestDryRunVsExecute(unittest.TestCase):
    """Core test: dry-run must not move files; execute must."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = FakeCfg(self.tmp, retention_days=0, dry_run=False)
        self.manifest = Manifest(self.tmp / "MANIFEST.yaml")

    def test_dry_run_does_not_move_file(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=31)
        self.manifest.append(job)
        run_archive(self.cfg, self.manifest, execute=False)
        self.assertTrue(job.file_path.exists(), "dry-run must not move the file")

    def test_dry_run_returns_candidates_but_zero_archived(self):
        for i in range(3):
            j = make_job(self.cfg.jobs_dir, title=f"J{i}", status="done", days_old=31)
            self.manifest.append(j)
        results = run_archive(self.cfg, self.manifest, execute=False)
        self.assertEqual(results["candidates"], 3)
        self.assertEqual(results["archived"], 0)

    def test_execute_moves_file_off_disk(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=31)
        self.manifest.append(job)
        run_archive(self.cfg, self.manifest, execute=True)
        self.assertFalse(job.file_path.exists(), "job file must be moved by execute")

    def test_execute_file_appears_in_archive_dir(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=31)
        self.manifest.append(job)
        run_archive(self.cfg, self.manifest, execute=True)
        archived = list(self.cfg.archive_dir.glob(f"{job.id}-archived-*.yaml"))
        self.assertEqual(len(archived), 1)

    def test_execute_updates_manifest_status_to_archived(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=31)
        self.manifest.append(job)
        run_archive(self.cfg, self.manifest, execute=True)
        entry = self.manifest.get_entry(job.id)
        self.assertEqual(entry["status"], "archived")

    def test_dry_run_does_not_change_manifest_status(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=31)
        self.manifest.append(job)
        run_archive(self.cfg, self.manifest, execute=False)
        entry = self.manifest.get_entry(job.id)
        self.assertEqual(entry["status"], "done")


class TestArchiveEligibility(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = FakeCfg(self.tmp, retention_days=30, dry_run=False)
        self.manifest = Manifest(self.tmp / "MANIFEST.yaml")

    def test_done_job_over_retention_is_archived(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=31)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 1)

    def test_failed_job_over_retention_is_archived(self):
        job = make_job(self.cfg.jobs_dir, status="failed", days_old=31)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 1)

    def test_cancelled_job_over_retention_is_archived(self):
        job = make_job(self.cfg.jobs_dir, status="cancelled", days_old=31)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 1)

    def test_pending_job_never_archived(self):
        job = make_job(self.cfg.jobs_dir, status="pending", days_old=99)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 0)
        self.assertTrue(job.file_path.exists())

    def test_running_job_never_archived(self):
        job = make_job(self.cfg.jobs_dir, status="running", days_old=99)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 0)

    def test_recent_done_job_not_archived(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=0)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 0)
        self.assertTrue(job.file_path.exists())

    def test_retention_boundary_29_days_not_archived(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=29)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 0)

    def test_retention_boundary_30_days_is_archived(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=30)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 1)

    def test_retention_boundary_31_days_is_archived(self):
        job = make_job(self.cfg.jobs_dir, status="done", days_old=31)
        self.manifest.append(job)
        results = run_archive(self.cfg, self.manifest, execute=True)
        self.assertEqual(results["archived"], 1)


class TestHatch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def _make_cfg(self, dry_run=False):
        return FakeCfg(self.tmp, dry_run=dry_run)

    def _make_archived_file(self, cfg, name="20260101-000000-abcdef01-archived-20260101.yaml"):
        f = cfg.archive_dir / name
        f.write_text("id: test\nstatus: archived\n")
        return f

    def test_hatch_dry_run_shows_candidates_does_not_delete(self):
        cfg = self._make_cfg(dry_run=False)
        f = self._make_archived_file(cfg)
        results = run_hatch(cfg, execute=False)
        self.assertEqual(results["candidates"], 1)
        self.assertEqual(results["ejected"], 0)
        self.assertTrue(f.exists(), "file must not be deleted in dry-run")

    def test_hatch_execute_deletes_archived_files(self):
        cfg = self._make_cfg(dry_run=False)
        f = self._make_archived_file(cfg)
        results = run_hatch(cfg, execute=True)
        self.assertEqual(results["ejected"], 1)
        self.assertFalse(f.exists(), "file must be deleted by execute")

    def test_hatch_config_dry_run_blocks_execute(self):
        cfg = self._make_cfg(dry_run=True)
        self._make_archived_file(cfg)
        results = run_hatch(cfg, execute=True)
        self.assertIn("error", results)
        # file must still exist
        self.assertTrue(list(cfg.archive_dir.glob("*-archived-*.yaml")).__len__() > 0)

    def test_hatch_empty_archive_succeeds_with_zero_ejected(self):
        cfg = self._make_cfg(dry_run=False)
        results = run_hatch(cfg, execute=True)
        self.assertEqual(results["ejected"], 0)
        self.assertNotIn("error", results)

    def test_hatch_multiple_files_all_ejected(self):
        cfg = self._make_cfg(dry_run=False)
        for i in range(4):
            self._make_archived_file(cfg, f"2026010{i}-000000-abcdef0{i}-archived-20260101.yaml")
        results = run_hatch(cfg, execute=True)
        self.assertEqual(results["ejected"], 4)
        remaining = list(cfg.archive_dir.glob("*-archived-*.yaml"))
        self.assertEqual(len(remaining), 0)

    def test_hatch_only_affects_archived_pattern(self):
        cfg = self._make_cfg(dry_run=False)
        archived = self._make_archived_file(cfg)
        other = cfg.archive_dir / "some-other-file.yaml"
        other.write_text("id: other\n")
        run_hatch(cfg, execute=True)
        self.assertFalse(archived.exists())
        self.assertTrue(other.exists(), "hatch must only touch *-archived-* files")


if __name__ == "__main__":
    unittest.main()
