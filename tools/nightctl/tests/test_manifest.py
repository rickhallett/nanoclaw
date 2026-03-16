"""Tests for manifest.py — append, rebuild, verify, drift detection."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nightctl_lib.job import Job
from nightctl_lib.manifest import Manifest

CFG_JOB = {
    "default_retries": 2,
    "default_timeout_secs": 300,
    "default_schedule": "overnight",
    "valid_schedules": ["overnight", "immediate", "once"],
    "valid_tags": ["maintenance", "memctl", "data"],
}


def make_job(jobs_dir, title="Test", command="echo hi", tags=None, depends_on=None):
    job, _ = Job.create(jobs_dir, CFG_JOB, title=title, command=command,
                        tags=tags or [], depends_on=depends_on or [])
    return job


class TestManifestInit(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmp / "MANIFEST.yaml"

    def test_empty_manifest_returns_empty_list(self):
        m = Manifest(self.manifest_path)
        self.assertEqual(m.all_jobs(), [])
        self.assertIsInstance(m.all_jobs(), list)

    def test_manifest_file_not_written_until_save(self):
        Manifest(self.manifest_path)
        self.assertFalse(self.manifest_path.exists())

    def test_persisted_manifest_loads_correctly(self):
        m = Manifest(self.manifest_path)
        job = make_job(self.tmp)
        m.append(job)
        # reload from disk
        m2 = Manifest(self.manifest_path)
        self.assertEqual(len(m2.all_jobs()), 1)
        self.assertEqual(m2.all_jobs()[0]["id"], job.id)


class TestManifestAppend(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmp / "MANIFEST.yaml"
        self.m = Manifest(self.manifest_path)

    def test_append_three_unique_jobs(self):
        for i in range(3):
            self.m.append(make_job(self.tmp, title=f"Job {i}"))
        self.assertEqual(len(self.m.all_jobs()), 3)

    def test_appended_values_readable_from_disk(self):
        job = make_job(self.tmp, title="Persist check", tags=["maintenance"])
        self.m.append(job)
        # verify by reloading from disk, not reading in-memory state
        m2 = Manifest(self.manifest_path)
        entry = m2.get_entry(job.id)
        self.assertIsNotNone(entry, "Job not found in reloaded manifest")
        self.assertEqual(entry["id"], job.id)
        self.assertEqual(entry["title"], "Persist check")
        self.assertEqual(entry["status"], "pending")

    def test_append_stores_correct_hash(self):
        job = make_job(self.tmp)
        self.m.append(job)
        entry = self.m.get_entry(job.id)
        # hash must match actual file content
        import hashlib
        actual_hash = hashlib.sha256(job.file_path.read_bytes()).hexdigest()
        self.assertEqual(entry["hash"], actual_hash)

    def test_append_stores_depends_on(self):
        dep = make_job(self.tmp, title="Dep")
        child = make_job(self.tmp, title="Child", depends_on=[dep.id])
        self.m.append(dep)
        self.m.append(child)
        child_entry = self.m.get_entry(child.id)
        self.assertEqual(child_entry["depends_on"], [dep.id])

    def test_append_deduplicates_same_id(self):
        job = make_job(self.tmp)
        self.m.append(job)
        self.m.append(job)
        self.assertEqual(len(self.m.all_jobs()), 1)

    def test_reappend_updates_entry_not_duplicates(self):
        job = make_job(self.tmp)
        self.m.append(job)
        # simulate status update and re-append
        job.set_status("done")
        job.save()
        self.m.append(job)
        self.assertEqual(len(self.m.all_jobs()), 1)
        self.assertEqual(self.m.get_entry(job.id)["status"], "done")

    def test_append_writes_manifest_to_disk(self):
        self.m.append(make_job(self.tmp))
        self.assertTrue(self.manifest_path.exists())


class TestManifestUpdateStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmp / "MANIFEST.yaml"
        self.m = Manifest(self.manifest_path)
        self.job = make_job(self.tmp)
        self.m.append(self.job)

    def test_update_status_changes_in_memory_state(self):
        self.m.update_status(self.job.id, "done")
        entry = self.m.get_entry(self.job.id)
        self.assertEqual(entry["status"], "done")

    def test_update_status_persists_to_disk(self):
        self.m.update_status(self.job.id, "failed")
        # reload from disk to confirm persistence
        m2 = Manifest(self.manifest_path)
        self.assertEqual(m2.get_entry(self.job.id)["status"], "failed")

    def test_update_does_not_affect_other_jobs(self):
        job2 = make_job(self.tmp, title="Second")
        self.m.append(job2)
        self.m.update_status(self.job.id, "done")
        self.assertEqual(self.m.get_entry(job2.id)["status"], "pending")

    def test_pending_jobs_excludes_done(self):
        job2 = make_job(self.tmp, title="Second")
        self.m.append(job2)
        self.m.update_status(self.job.id, "done")
        pending = self.m.pending_jobs()
        pending_ids = [j["id"] for j in pending]
        self.assertNotIn(self.job.id, pending_ids)
        self.assertIn(job2.id, pending_ids)

    def test_pending_jobs_count_decreases_after_completion(self):
        job2 = make_job(self.tmp, title="B")
        job3 = make_job(self.tmp, title="C")
        self.m.append(job2)
        self.m.append(job3)
        self.assertEqual(len(self.m.pending_jobs()), 3)
        self.m.update_status(self.job.id, "done")
        self.assertEqual(len(self.m.pending_jobs()), 2)


class TestManifestVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmp / "MANIFEST.yaml"
        self.m = Manifest(self.manifest_path)

    def _statuses(self, results):
        return {r["id"]: r["status"] for r in results}

    def test_unmodified_job_is_match(self):
        job = make_job(self.tmp)
        self.m.append(job)
        statuses = self._statuses(self.m.verify(self.tmp))
        self.assertEqual(statuses[job.id], "MATCH")

    def test_modified_job_file_is_drift(self):
        job = make_job(self.tmp)
        self.m.append(job)
        job.set_status("claimed")
        job.save()  # modifies file after it was indexed
        statuses = self._statuses(self.m.verify(self.tmp))
        self.assertEqual(statuses[job.id], "DRIFT")

    def test_deleted_job_file_is_missing(self):
        job = make_job(self.tmp)
        self.m.append(job)
        job.file_path.unlink()
        statuses = self._statuses(self.m.verify(self.tmp))
        self.assertEqual(statuses[job.id], "MISSING")

    def test_unindexed_job_file_is_orphan(self):
        job = make_job(self.tmp)
        # deliberately do NOT append to manifest
        statuses = self._statuses(self.m.verify(self.tmp))
        self.assertEqual(statuses.get(job.id), "ORPHAN")

    def test_verify_correctly_classifies_mixed_state(self):
        j_ok = make_job(self.tmp, title="OK")
        j_drift = make_job(self.tmp, title="Drift")
        j_missing = make_job(self.tmp, title="Missing")
        self.m.append(j_ok)
        self.m.append(j_drift)
        self.m.append(j_missing)
        j_drift.set_status("running")
        j_drift.save()
        j_missing.file_path.unlink()
        statuses = self._statuses(self.m.verify(self.tmp))
        self.assertEqual(statuses[j_ok.id], "MATCH")
        self.assertEqual(statuses[j_drift.id], "DRIFT")
        self.assertEqual(statuses[j_missing.id], "MISSING")

    def test_rebuild_clears_drift(self):
        job = make_job(self.tmp)
        self.m.append(job)
        job.set_status("done")
        job.save()
        # drift exists before rebuild
        statuses_before = self._statuses(self.m.verify(self.tmp))
        self.assertEqual(statuses_before[job.id], "DRIFT")
        # rebuild clears it
        self.m.rebuild(self.tmp)
        statuses_after = self._statuses(self.m.verify(self.tmp))
        self.assertEqual(statuses_after[job.id], "MATCH")

    def test_corrupted_job_yaml_reported_as_orphan(self):
        # Write a file that looks like a job but has invalid YAML
        bad_file = self.tmp / "20260315-000000-badcafe0-bad-file.yaml"
        bad_file.write_text("id: [\nbad yaml\n")
        results = self.m.verify(self.tmp)
        orphans = [r for r in results if r["status"] == "ORPHAN"]
        self.assertEqual(len(orphans), 1)


class TestManifestRebuild(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmp / "MANIFEST.yaml"

    def test_rebuild_finds_correct_count(self):
        for i in range(4):
            make_job(self.tmp, title=f"Job {i}")
        m = Manifest(self.manifest_path)
        count, errors = m.rebuild(self.tmp)
        self.assertEqual(count, 4)
        self.assertEqual(errors, [])

    def test_rebuild_includes_all_job_ids(self):
        jobs = [make_job(self.tmp, title=f"Job {i}") for i in range(3)]
        m = Manifest(self.manifest_path)
        m.rebuild(self.tmp)
        for job in jobs:
            entry = m.get_entry(job.id)
            self.assertIsNotNone(entry, f"Job {job.id} not found after rebuild")

    def test_rebuild_removes_stale_entries(self):
        job = make_job(self.tmp)
        m = Manifest(self.manifest_path)
        m.append(job)
        job.file_path.unlink()  # delete from disk
        count, _ = m.rebuild(self.tmp)
        self.assertEqual(count, 0)
        self.assertIsNone(m.get_entry(job.id))

    def test_rebuild_is_idempotent(self):
        make_job(self.tmp)
        m = Manifest(self.manifest_path)
        count1, _ = m.rebuild(self.tmp)
        count2, _ = m.rebuild(self.tmp)
        self.assertEqual(count1, count2)
        self.assertEqual(len(m.all_jobs()), 1)

    def test_rebuild_persists_to_disk(self):
        make_job(self.tmp, title="Rebuild test")
        m = Manifest(self.manifest_path)
        m.rebuild(self.tmp)
        m2 = Manifest(self.manifest_path)
        self.assertEqual(len(m2.all_jobs()), 1)
        self.assertEqual(m2.all_jobs()[0]["title"], "Rebuild test")


class TestManifestCounts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmp / "MANIFEST.yaml"
        self.m = Manifest(self.manifest_path)

    def test_total_matches_number_appended(self):
        for i in range(4):
            self.m.append(make_job(self.tmp, title=f"J{i}"))
        self.assertEqual(self.m.counts()["total"], 4)

    def test_by_status_counts_are_accurate(self):
        j1 = make_job(self.tmp, title="A", tags=["maintenance"])
        j2 = make_job(self.tmp, title="B", tags=["data"])
        j3 = make_job(self.tmp, title="C")
        self.m.append(j1)
        self.m.append(j2)
        self.m.append(j3)
        self.m.update_status(j1.id, "done")
        self.m.update_status(j2.id, "failed")
        counts = self.m.counts()
        self.assertEqual(counts["by_status"].get("done"), 1)
        self.assertEqual(counts["by_status"].get("failed"), 1)
        self.assertEqual(counts["by_status"].get("pending"), 1)

    def test_by_tag_counts_are_accurate(self):
        self.m.append(make_job(self.tmp, title="A", tags=["maintenance", "memctl"]))
        self.m.append(make_job(self.tmp, title="B", tags=["maintenance"]))
        self.m.append(make_job(self.tmp, title="C", tags=["data"]))
        counts = self.m.counts()
        self.assertEqual(counts["by_tag"].get("maintenance"), 2)
        self.assertEqual(counts["by_tag"].get("memctl"), 1)
        self.assertEqual(counts["by_tag"].get("data"), 1)
        self.assertIsNone(counts["by_tag"].get("infra"))

    def test_by_schedule_counts_are_accurate(self):
        j1, _ = Job.create(self.tmp, CFG_JOB, title="A", command="echo", schedule="overnight")
        j2, _ = Job.create(self.tmp, CFG_JOB, title="B", command="echo", schedule="immediate")
        self.m.append(j1)
        self.m.append(j2)
        counts = self.m.counts()
        self.assertEqual(counts["by_schedule"].get("overnight"), 1)
        self.assertEqual(counts["by_schedule"].get("immediate"), 1)

    def test_empty_manifest_has_zero_counts(self):
        counts = self.m.counts()
        self.assertEqual(counts["total"], 0)
        self.assertEqual(counts["by_status"], {})
        self.assertEqual(counts["by_tag"], {})


if __name__ == "__main__":
    unittest.main()
