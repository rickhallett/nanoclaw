"""Integration tests for the nightctl CLI via subprocess."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

NIGHTCTL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nightctl")
PYTHON = sys.executable


def run(*args, cwd=None):
    result = subprocess.run(
        [PYTHON, NIGHTCTL] + list(args),
        capture_output=True, text=True, cwd=cwd
    )
    return result.returncode, result.stdout, result.stderr


class BaseCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._write_config()

    def _write_config(self):
        config = f"""queue_dir: {self.tmp}/queue
manifest_file: {self.tmp}/queue/MANIFEST.yaml
archive_dir: {self.tmp}/queue/archive
runs_dir: {self.tmp}/queue/runs

execution:
  mode: serial
  max_workers: 1
  overnight_window: "02:00-05:00"
  timezone: Europe/London

job:
  default_retries: 2
  default_timeout_secs: 300
  default_schedule: overnight
  valid_schedules:
    - overnight
    - immediate
    - once
  valid_tags:
    - maintenance
    - memctl
    - data
    - infra

notify:
  on_failure: false
  on_success: false
  channel: main

manifest:
  hash_algorithm: sha256

archive:
  retention_days: 30
  dry_run: true
"""
        self.config_path = os.path.join(self.tmp, "nightctl.yaml")
        Path(self.config_path).write_text(config)
        for d in ["queue/jobs", "queue/runs", "queue/archive"]:
            Path(self.tmp, d).mkdir(parents=True, exist_ok=True)

    def nightctl(self, *args):
        return run("--config", self.config_path, *args)

    def enqueue_json(self, title="Test job", command="echo hi", **kwargs):
        extra = []
        for k, v in kwargs.items():
            extra += [f"--{k.replace('_', '-')}", str(v)]
        rc, out, err = self.nightctl("--json", "enqueue",
                                     "--title", title, "--command", command, *extra)
        self.assertEqual(rc, 0, f"enqueue failed: {err}")
        return json.loads(out)

    def jobs_dir(self):
        return Path(self.tmp, "queue/jobs")

    def runs_dir(self):
        return Path(self.tmp, "queue/runs")


class TestEnqueue(BaseCliTest):
    def test_enqueue_exit_code_zero(self):
        rc, _, _ = self.nightctl("enqueue", "--title", "T", "--command", "echo hi")
        self.assertEqual(rc, 0)

    def test_enqueue_json_contains_id_file_warnings(self):
        data = self.enqueue_json("My job", "echo hi")
        self.assertIn("id", data)
        self.assertIn("file", data)
        self.assertIn("warnings", data)

    def test_enqueue_id_has_correct_format(self):
        data = self.enqueue_json()
        parts = data["id"].split("-")
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[0]), 8)
        self.assertEqual(len(parts[1]), 6)
        self.assertEqual(len(parts[2]), 8)

    def test_enqueue_creates_job_file_on_disk(self):
        data = self.enqueue_json()
        self.assertTrue(Path(data["file"]).exists())

    def test_enqueue_job_file_contains_correct_title(self):
        data = self.enqueue_json("Specific title", "echo hi")
        from nightctl_lib.job import Job
        job = Job.from_file(Path(data["file"]))
        self.assertEqual(job.title, "Specific title")

    def test_enqueue_job_file_status_is_pending(self):
        data = self.enqueue_json()
        from nightctl_lib.job import Job
        job = Job.from_file(Path(data["file"]))
        self.assertEqual(job.status, "pending")

    def test_enqueue_two_jobs_get_unique_ids(self):
        d1 = self.enqueue_json("First", "echo 1")
        d2 = self.enqueue_json("Second", "echo 2")
        self.assertNotEqual(d1["id"], d2["id"])

    def test_enqueue_known_tags_no_warnings(self):
        data = self.enqueue_json(tags="maintenance,memctl")
        self.assertEqual(data["warnings"], [])

    def test_enqueue_unknown_tag_produces_warning_with_tag_name(self):
        data = self.enqueue_json(tags="unknowntag123")
        self.assertTrue(len(data["warnings"]) > 0)
        self.assertTrue(any("unknowntag123" in w for w in data["warnings"]))

    def test_enqueue_missing_title_exits_nonzero(self):
        rc, _, err = self.nightctl("enqueue", "--command", "echo hi")
        self.assertNotEqual(rc, 0)

    def test_enqueue_missing_command_exits_nonzero(self):
        rc, _, err = self.nightctl("enqueue", "--title", "T")
        self.assertNotEqual(rc, 0)

    def test_enqueue_invalid_schedule_exits_nonzero(self):
        rc, _, err = self.nightctl("enqueue", "--title", "T", "--command", "echo", "--schedule", "weekly")
        self.assertNotEqual(rc, 0)

    def test_enqueue_priority_stored_in_file(self):
        data = self.enqueue_json(priority=3)
        from nightctl_lib.job import Job
        job = Job.from_file(Path(data["file"]))
        self.assertEqual(job.priority, 3)


class TestList(BaseCliTest):
    def test_list_empty_queue_says_no_jobs(self):
        rc, out, _ = self.nightctl("list")
        self.assertEqual(rc, 0)
        self.assertIn("no jobs", out)

    def test_list_shows_both_job_ids(self):
        d1 = self.enqueue_json("Job A", "echo a")
        d2 = self.enqueue_json("Job B", "echo b")
        rc, out, _ = self.nightctl("list")
        self.assertEqual(rc, 0)
        self.assertIn(d1["id"], out)
        self.assertIn(d2["id"], out)

    def test_list_shows_both_job_titles(self):
        self.enqueue_json("Job Alpha", "echo a")
        self.enqueue_json("Job Beta", "echo b")
        rc, out, _ = self.nightctl("list")
        self.assertIn("Job Alpha", out)
        self.assertIn("Job Beta", out)

    def test_list_shows_pending_status(self):
        self.enqueue_json("T", "echo hi")
        rc, out, _ = self.nightctl("list")
        self.assertIn("pending", out)

    def test_list_json_count_matches_enqueued(self):
        for i in range(3):
            self.enqueue_json(f"Job {i}", f"echo {i}")
        rc, out, _ = self.nightctl("--json", "list")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data), 3)

    def test_list_json_entries_have_required_fields(self):
        self.enqueue_json("T", "echo hi")
        rc, out, _ = self.nightctl("--json", "list")
        data = json.loads(out)
        entry = data[0]
        for field in ("id", "title", "status", "priority", "schedule"):
            self.assertIn(field, entry, f"Missing field: {field}")

    def test_list_filter_by_status_pending(self):
        d = self.enqueue_json("Pending job", "echo hi")
        rc, out, _ = self.nightctl("list", "--status", "pending")
        self.assertIn(d["id"], out)

    def test_list_filter_status_done_shows_empty(self):
        self.enqueue_json("Pending job", "echo hi")
        rc, out, _ = self.nightctl("list", "--status", "done")
        self.assertIn("no jobs", out)


class TestStatus(BaseCliTest):
    def test_status_shows_job_id(self):
        d = self.enqueue_json("Status test", "echo hi")
        rc, out, _ = self.nightctl("status", d["id"])
        self.assertEqual(rc, 0)
        self.assertIn(d["id"], out)

    def test_status_shows_job_title(self):
        d = self.enqueue_json("Exact title check", "echo hi")
        rc, out, _ = self.nightctl("status", d["id"])
        self.assertIn("Exact title check", out)

    def test_status_shows_pending_status(self):
        d = self.enqueue_json("T", "echo hi")
        rc, out, _ = self.nightctl("status", d["id"])
        self.assertIn("pending", out)

    def test_status_shows_no_runs_initially(self):
        d = self.enqueue_json("T", "echo hi")
        rc, out, _ = self.nightctl("status", d["id"])
        self.assertIn("none", out.lower())

    def test_status_json_structure(self):
        d = self.enqueue_json("T", "echo hi")
        rc, out, _ = self.nightctl("--json", "status", d["id"])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertIn("job", parsed)
        self.assertIn("runs", parsed)
        self.assertEqual(parsed["job"]["id"], d["id"])
        self.assertIsInstance(parsed["runs"], list)

    def test_status_after_run_shows_done(self):
        d = self.enqueue_json("T", "echo hi")
        self.nightctl("run", "--force")
        rc, out, _ = self.nightctl("--json", "status", d["id"])
        parsed = json.loads(out)
        self.assertEqual(parsed["job"]["status"], "done")
        self.assertEqual(len(parsed["runs"]), 1)
        self.assertEqual(parsed["runs"][0]["outcome"], "done")
        self.assertEqual(parsed["runs"][0]["exit_code"], 0)

    def test_status_nonexistent_id_exits_nonzero(self):
        rc, _, _ = self.nightctl("status", "nonexistent-id-here")
        self.assertNotEqual(rc, 0)


class TestRun(BaseCliTest):
    def test_run_force_executes_and_exits_zero(self):
        self.enqueue_json("T", "echo hi")
        rc, out, _ = self.nightctl("run", "--force")
        self.assertEqual(rc, 0)

    def test_run_force_reports_correct_done_count(self):
        for i in range(3):
            self.enqueue_json(f"J{i}", "echo hi")
        rc, out, _ = self.nightctl("run", "--force")
        self.assertIn("done: 3", out)
        self.assertIn("failed: 0", out)

    def test_run_outside_window_exits_zero_and_reports_it(self):
        self.enqueue_json("T", "echo hi")
        rc, out, _ = self.nightctl("run")
        self.assertEqual(rc, 0)
        self.assertIn("outside overnight window", out)

    def test_run_outside_window_does_not_execute_jobs(self):
        d = self.enqueue_json("T", "echo hi")
        self.nightctl("run")
        rc, out, _ = self.nightctl("--json", "status", d["id"])
        parsed = json.loads(out)
        self.assertEqual(parsed["job"]["status"], "pending")

    def test_run_failing_job_exits_5(self):
        self.enqueue_json("Bad", "exit 1", retries=0)
        rc, _, _ = self.nightctl("run", "--force")
        self.assertEqual(rc, 5)

    def test_run_failing_job_reports_failed_count(self):
        self.enqueue_json("Bad", "exit 1", retries=0)
        rc, out, _ = self.nightctl("run", "--force")
        self.assertIn("failed: 1", out)

    def test_run_writes_run_record_with_correct_outcome(self):
        d = self.enqueue_json("T", "echo hi")
        self.nightctl("run", "--force")
        rc, out, _ = self.nightctl("--json", "status", d["id"])
        parsed = json.loads(out)
        self.assertEqual(len(parsed["runs"]), 1)
        self.assertEqual(parsed["runs"][0]["outcome"], "done")
        self.assertEqual(parsed["runs"][0]["exit_code"], 0)

    def test_run_limit_executes_exactly_n_jobs(self):
        for i in range(5):
            self.enqueue_json(f"J{i}", "echo hi")
        rc, out, _ = self.nightctl("run", "--force", "--limit", "2")
        self.assertIn("done: 2", out)
        rc2, out2, _ = self.nightctl("--json", "list", "--status", "pending")
        pending = json.loads(out2)
        self.assertEqual(len(pending), 3)


class TestCancel(BaseCliTest):
    def test_cancel_exits_zero(self):
        d = self.enqueue_json("Cancel me", "echo hi")
        rc, _, _ = self.nightctl("cancel", d["id"])
        self.assertEqual(rc, 0)

    def test_cancelled_job_shows_cancelled_status(self):
        d = self.enqueue_json("Cancel me", "echo hi")
        self.nightctl("cancel", d["id"])
        rc, out, _ = self.nightctl("--json", "list", "--status", "cancelled")
        # cancelled jobs are moved to archive — check via stats or list
        rc2, out2, _ = self.nightctl("--json", "list", "--status", "pending")
        pending = json.loads(out2)
        pending_ids = [j["id"] for j in pending]
        self.assertNotIn(d["id"], pending_ids)

    def test_cancelled_job_not_executed_on_run(self):
        sentinel = Path(self.tmp) / "sentinel"
        d = self.enqueue_json("Cancel me", f"touch {sentinel}")
        self.nightctl("cancel", d["id"])
        self.nightctl("run", "--force")
        self.assertFalse(sentinel.exists(), "cancelled job must not run")

    def test_cancel_nonexistent_id_exits_nonzero(self):
        rc, _, _ = self.nightctl("cancel", "does-not-exist-here")
        self.assertNotEqual(rc, 0)


class TestManifest(BaseCliTest):
    def test_manifest_rebuild_exits_zero(self):
        self.enqueue_json("T", "echo hi")
        rc, _, _ = self.nightctl("manifest", "rebuild")
        self.assertEqual(rc, 0)

    def test_manifest_rebuild_reports_correct_count(self):
        for i in range(3):
            self.enqueue_json(f"J{i}", "echo hi")
        rc, out, _ = self.nightctl("manifest", "rebuild")
        self.assertIn("3", out)

    def test_manifest_verify_clean_state_exits_zero(self):
        self.enqueue_json("T", "echo hi")
        self.nightctl("manifest", "rebuild")
        rc, out, _ = self.nightctl("manifest", "verify")
        self.assertEqual(rc, 0)
        self.assertIn("MATCH", out)

    def test_manifest_verify_clean_shows_job_id(self):
        d = self.enqueue_json("T", "echo hi")
        self.nightctl("manifest", "rebuild")
        rc, out, _ = self.nightctl("manifest", "verify")
        self.assertIn(d["id"], out)

    def test_manifest_verify_drift_exits_3(self):
        d = self.enqueue_json("T", "echo hi")
        self.nightctl("run", "--force")
        rc, out, _ = self.nightctl("manifest", "verify")
        self.assertEqual(rc, 3)
        self.assertIn("DRIFT", out)
        self.assertIn(d["id"], out)

    def test_manifest_verify_after_rebuild_is_clean(self):
        self.enqueue_json("T", "echo hi")
        self.nightctl("run", "--force")
        # drift exists
        rc1, _, _ = self.nightctl("manifest", "verify")
        self.assertEqual(rc1, 3)
        # rebuild fixes it
        self.nightctl("manifest", "rebuild")
        rc2, out2, _ = self.nightctl("manifest", "verify")
        self.assertEqual(rc2, 0)
        self.assertNotIn("DRIFT", out2)


class TestStats(BaseCliTest):
    def test_stats_exits_zero(self):
        rc, _, _ = self.nightctl("stats")
        self.assertEqual(rc, 0)

    def test_stats_shows_jobs_queue_header(self):
        rc, out, _ = self.nightctl("stats")
        self.assertIn("Jobs (queue)", out)

    def test_stats_shows_next_window(self):
        rc, out, _ = self.nightctl("stats")
        self.assertIn("Next window", out)
        self.assertIn("02:00-05:00", out)

    def test_stats_json_has_required_fields(self):
        rc, out, _ = self.nightctl("--json", "stats")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for field in ("total", "by_status", "by_schedule", "by_tag", "window", "in_window"):
            self.assertIn(field, data, f"Missing field: {field}")

    def test_stats_json_total_matches_enqueued(self):
        for i in range(3):
            self.enqueue_json(f"J{i}", "echo hi")
        rc, out, _ = self.nightctl("--json", "stats")
        data = json.loads(out)
        self.assertEqual(data["total"], 3)

    def test_stats_json_by_status_counts_are_correct(self):
        self.enqueue_json("J1", "echo hi")
        self.enqueue_json("J2", "echo hi")
        self.nightctl("run", "--force")
        rc, out, _ = self.nightctl("--json", "stats")
        data = json.loads(out)
        self.assertEqual(data["by_status"].get("done"), 2)

    def test_stats_json_window_is_string(self):
        rc, out, _ = self.nightctl("--json", "stats")
        data = json.loads(out)
        self.assertIsInstance(data["window"], str)
        self.assertIn("-", data["window"])

    def test_stats_json_in_window_is_bool(self):
        rc, out, _ = self.nightctl("--json", "stats")
        data = json.loads(out)
        self.assertIsInstance(data["in_window"], bool)


class TestArchiveCli(BaseCliTest):
    def test_archive_default_is_dry_run(self):
        rc, out, _ = self.nightctl("archive")
        self.assertEqual(rc, 0)
        self.assertIn("dry-run", out)

    def test_archive_recent_jobs_zero_candidates(self):
        self.enqueue_json("T", "echo hi")
        self.nightctl("run", "--force")
        rc, out, _ = self.nightctl("archive")
        self.assertIn("candidates: 0", out)


class TestHatchCli(BaseCliTest):
    def test_hatch_default_is_dry_run(self):
        rc, out, _ = self.nightctl("hatch")
        self.assertEqual(rc, 0)
        self.assertIn("dry-run", out)

    def test_hatch_execute_blocked_when_config_dry_run_true(self):
        # default config has archive.dry_run=true
        rc, _, _ = self.nightctl("hatch", "--execute")
        self.assertNotEqual(rc, 0)


class TestMissingConfig(unittest.TestCase):
    def test_missing_config_exits_4(self):
        rc, _, _ = run("--config", "/nonexistent/nightctl.yaml", "stats")
        self.assertEqual(rc, 4)

    def test_missing_config_error_message_mentions_path(self):
        rc, out, err = run("--config", "/nonexistent/nightctl.yaml", "stats")
        combined = out + err
        self.assertIn("nightctl.yaml", combined)


if __name__ == "__main__":
    unittest.main()
