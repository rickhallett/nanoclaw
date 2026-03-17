"""Tests for nightctl expanded CLI — Phase 2 unified work tracker.

Tests the new subcommands: add, plan, approve, revise, retry, start,
review, testing, done, block, defer, cancel, edit, graph.
Also tests --help output and error cases.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PYTHON = sys.executable


def run(*args, cwd=None):
    result = subprocess.run(
        [PYTHON, "-m", "halos.nightctl.cli"] + list(args),
        capture_output=True, text=True, cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


VALID_PLAN_XML = (
    "<plan>"
    "<goal>Test goal</goal>"
    "<steps><step n=\"1\" output=\"stdout\">Do the thing</step></steps>"
    "<constraints><constraint>Don't break things</constraint></constraints>"
    "<success><criterion>It works</criterion></success>"
    "<output>stdout</output>"
    "</plan>"
)


class BaseItemTest(unittest.TestCase):
    """Base class with config that includes items_dir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._write_config()

    def _write_config(self):
        config = f"""queue_dir: {self.tmp}/queue
items_dir: {self.tmp}/queue/items
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
        for d in ["queue/jobs", "queue/items", "queue/runs", "queue/archive"]:
            Path(self.tmp, d).mkdir(parents=True, exist_ok=True)

    def nightctl(self, *args):
        return run("--config", self.config_path, *args)

    def add_json(self, title="Test item", kind="task", **kwargs):
        extra = []
        for k, v in kwargs.items():
            extra += [f"--{k.replace('_', '-')}", str(v)]
        rc, out, err = self.nightctl("--json", "add",
                                      "--title", title, "--kind", kind, *extra)
        self.assertEqual(rc, 0, f"add failed: {err}")
        return json.loads(out)

    def items_dir(self):
        return Path(self.tmp, "queue/items")


# ---------------------------------------------------------------------------
# Add command
# ---------------------------------------------------------------------------

class TestAdd(BaseItemTest):
    def test_add_task_exit_zero(self):
        rc, _, _ = self.nightctl("add", "--title", "Write docs", "--kind", "task")
        self.assertEqual(rc, 0)

    def test_add_task_json_has_id(self):
        data = self.add_json("Write docs", "task")
        self.assertIn("id", data)
        self.assertEqual(data["kind"], "task")

    def test_add_task_creates_file(self):
        data = self.add_json("Write docs", "task")
        self.assertTrue(Path(data["file"]).exists())

    def test_add_job_requires_command(self):
        rc, _, err = self.nightctl("add", "--title", "Run report", "--kind", "job")
        self.assertNotEqual(rc, 0)
        self.assertIn("command", err.lower())

    def test_add_job_with_command(self):
        data = self.add_json("Run report", "job", command="echo hi", schedule="overnight")
        self.assertEqual(data["kind"], "job")

    def test_add_agent_job_without_plan_ok(self):
        """Brainfart ingress: no plan required at creation."""
        data = self.add_json("Research tools", "agent-job")
        self.assertEqual(data["kind"], "agent-job")

    def test_add_agent_job_with_valid_plan(self):
        data = self.add_json("Research tools", "agent-job", plan=VALID_PLAN_XML)
        self.assertEqual(data["kind"], "agent-job")

    def test_add_agent_job_with_invalid_plan_rejects(self):
        rc, _, err = self.nightctl("add", "--title", "Bad",
                                    "--kind", "agent-job",
                                    "--plan", "<plan><goal></goal></plan>")
        self.assertNotEqual(rc, 0)

    def test_add_invalid_kind_rejects(self):
        rc, _, err = self.nightctl("add", "--title", "Nope", "--kind", "unicorn")
        self.assertNotEqual(rc, 0)

    def test_add_with_priority(self):
        data = self.add_json("Urgent", "task", priority=1)
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.priority, 1)

    def test_add_with_tags(self):
        data = self.add_json("Tagged", "task", tags="infra,data")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertIn("infra", item.tags)
        self.assertIn("data", item.tags)

    def test_add_with_context_and_due(self):
        data = self.add_json("Deadline item", "task", context="Important thing", due="2026-04-01")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.context, "Important thing")
        self.assertEqual(item.due, "2026-04-01")

    def test_add_with_schedule(self):
        data = self.add_json("Scheduled", "job", command="echo hi", schedule="immediate")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.schedule, "immediate")

    def test_add_two_items_unique_ids(self):
        d1 = self.add_json("First", "task")
        d2 = self.add_json("Second", "task")
        self.assertNotEqual(d1["id"], d2["id"])


# ---------------------------------------------------------------------------
# Plan command
# ---------------------------------------------------------------------------

class TestPlan(BaseItemTest):
    def test_plan_transitions_to_planning(self):
        data = self.add_json("Research", "agent-job")
        rc, out, _ = self.nightctl("plan", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("planning", out)

    def test_plan_from_non_open_fails(self):
        data = self.add_json("Task", "task")
        # start it first
        self.nightctl("start", data["id"])
        # try to plan it
        rc, _, err = self.nightctl("plan", data["id"])
        self.assertNotEqual(rc, 0)

    def test_plan_nonexistent_id_fails(self):
        rc, _, err = self.nightctl("plan", "does-not-exist")
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Approve command
# ---------------------------------------------------------------------------

class TestApprove(BaseItemTest):
    def test_approve_with_valid_plan(self):
        data = self.add_json("Research", "agent-job")
        self.nightctl("plan", data["id"])
        # Add plan via edit
        self.nightctl("edit", data["id"], "--plan", VALID_PLAN_XML)
        # Submit for review
        self.nightctl("review", data["id"])
        # Approve
        rc, out, _ = self.nightctl("approve", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("approved", out)

    def test_approve_without_plan_fails(self):
        data = self.add_json("Research", "agent-job")
        self.nightctl("plan", data["id"])
        self.nightctl("review", data["id"])
        # No plan was added -> approve should fail validation
        rc, _, err = self.nightctl("approve", data["id"])
        self.assertNotEqual(rc, 0)

    def test_approve_from_wrong_state_fails(self):
        """Approve (plan-review -> in-progress) should fail from review state."""
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        self.nightctl("review", data["id"])
        # Now in 'review' state — approve tries to transition to in-progress
        # which IS valid from review, so use done state instead
        self.nightctl("done", data["id"])
        rc, _, err = self.nightctl("approve", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Revise command
# ---------------------------------------------------------------------------

class TestRevise(BaseItemTest):
    def test_revise_agent_job_from_failed(self):
        """failed -> plan-review for agent-jobs."""
        data = self.add_json("Research", "agent-job")
        # Get to failed state: plan -> review -> approve -> running -> failed
        self.nightctl("plan", data["id"])
        self.nightctl("edit", data["id"], "--plan", VALID_PLAN_XML)
        self.nightctl("review", data["id"])
        self.nightctl("approve", data["id"])
        # Manually set to running then failed (simulating executor)
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        item.transition("running")
        item.save()
        item.transition("failed")
        item.save()

        rc, out, _ = self.nightctl("revise", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("revised", out)

    def test_revise_job_fails(self):
        """Jobs cannot revise (failed -> plan-review not allowed for jobs)."""
        data = self.add_json("Report", "job", command="false")
        # Get to failed
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        item.save()

        rc, _, err = self.nightctl("revise", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Retry command
# ---------------------------------------------------------------------------

class TestRetry(BaseItemTest):
    def test_retry_job_from_failed(self):
        """failed -> in-progress for jobs."""
        data = self.add_json("Report", "job", command="echo hi")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        item.save()

        rc, out, _ = self.nightctl("retry", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("retry", out)

    def test_retry_agent_job_fails(self):
        """Agent-jobs cannot retry directly (must go through plan-review)."""
        data = self.add_json("Research", "agent-job")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        item.save()

        rc, _, err = self.nightctl("retry", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Start command
# ---------------------------------------------------------------------------

class TestStart(BaseItemTest):
    def test_start_task(self):
        data = self.add_json("Write docs", "task")
        rc, out, _ = self.nightctl("start", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("started", out)

    def test_start_job(self):
        data = self.add_json("Report", "job", command="echo hi")
        rc, out, _ = self.nightctl("start", data["id"])
        self.assertEqual(rc, 0)

    def test_start_agent_job_with_context_succeeds(self):
        """Agent-jobs can skip planning if context is sufficient (research jobs)."""
        data = self.add_json("Research task", "agent-job",
                             context="Detailed research context that is long enough to qualify as sufficient for a context-only agent job execution")
        rc, _, err = self.nightctl("start", data["id"])
        self.assertEqual(rc, 0)


# ---------------------------------------------------------------------------
# Review command
# ---------------------------------------------------------------------------

class TestReview(BaseItemTest):
    def test_review_from_planning(self):
        """planning -> plan-review."""
        data = self.add_json("Research", "agent-job")
        self.nightctl("plan", data["id"])
        self.nightctl("edit", data["id"], "--plan", VALID_PLAN_XML)
        rc, out, _ = self.nightctl("review", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("review", out)

    def test_review_from_in_progress(self):
        """in-progress -> review."""
        data = self.add_json("Write docs", "task")
        self.nightctl("start", data["id"])
        rc, out, _ = self.nightctl("review", data["id"])
        self.assertEqual(rc, 0)

    def test_review_from_open_fails(self):
        data = self.add_json("Task", "task")
        rc, _, err = self.nightctl("review", data["id"])
        self.assertNotEqual(rc, 0)

    def test_review_planning_without_plan_fails(self):
        """plan-review gate rejects missing plan for agent-jobs."""
        data = self.add_json("Research", "agent-job")
        self.nightctl("plan", data["id"])
        rc, _, err = self.nightctl("review", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Testing command
# ---------------------------------------------------------------------------

class TestTesting(BaseItemTest):
    def test_testing_from_review(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        self.nightctl("review", data["id"])
        rc, out, _ = self.nightctl("testing", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("testing", out)

    def test_testing_from_wrong_state_fails(self):
        data = self.add_json("Task", "task")
        rc, _, err = self.nightctl("testing", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Done command
# ---------------------------------------------------------------------------

class TestDone(BaseItemTest):
    def test_done_from_review(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        self.nightctl("review", data["id"])
        rc, out, _ = self.nightctl("done", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("done", out)

    def test_done_from_testing(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        self.nightctl("review", data["id"])
        self.nightctl("testing", data["id"])
        rc, out, _ = self.nightctl("done", data["id"])
        self.assertEqual(rc, 0)

    def test_done_from_open_fails(self):
        data = self.add_json("Task", "task")
        rc, _, err = self.nightctl("done", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Block command
# ---------------------------------------------------------------------------

class TestBlock(BaseItemTest):
    def test_block_with_reason(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        rc, out, _ = self.nightctl("block", data["id"], "--by", "waiting on API")
        self.assertEqual(rc, 0)
        self.assertIn("blocked", out)
        self.assertIn("waiting on API", out)

    def test_block_from_open_fails(self):
        data = self.add_json("Task", "task")
        rc, _, err = self.nightctl("block", data["id"], "--by", "reason")
        self.assertNotEqual(rc, 0)

    def test_block_requires_by_flag(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        rc, _, err = self.nightctl("block", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Defer command
# ---------------------------------------------------------------------------

class TestDefer(BaseItemTest):
    def test_defer_from_open(self):
        data = self.add_json("Task", "task")
        rc, out, _ = self.nightctl("defer", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("deferred", out)

    def test_defer_from_in_progress_fails(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        rc, _, err = self.nightctl("defer", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Cancel command (unified items)
# ---------------------------------------------------------------------------

class TestCancelItem(BaseItemTest):
    def test_cancel_from_open(self):
        data = self.add_json("Task", "task")
        rc, out, _ = self.nightctl("cancel", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("cancelled", out)

    def test_cancel_from_in_progress(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        rc, out, _ = self.nightctl("cancel", data["id"])
        self.assertEqual(rc, 0)

    def test_cancel_from_done_fails(self):
        """Terminal state — cannot cancel."""
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        self.nightctl("review", data["id"])
        self.nightctl("done", data["id"])
        rc, _, err = self.nightctl("cancel", data["id"])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# Edit command
# ---------------------------------------------------------------------------

class TestEdit(BaseItemTest):
    def test_edit_title(self):
        data = self.add_json("Original", "task")
        rc, out, _ = self.nightctl("edit", data["id"], "--title", "Updated")
        self.assertEqual(rc, 0)
        self.assertIn("Updated", out)

    def test_edit_priority(self):
        data = self.add_json("Task", "task")
        self.nightctl("edit", data["id"], "--priority", "1")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.priority, 1)

    def test_edit_tags(self):
        data = self.add_json("Task", "task")
        self.nightctl("edit", data["id"], "--tags", "infra,data")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertIn("infra", item.tags)

    def test_edit_plan(self):
        data = self.add_json("Research", "agent-job")
        self.nightctl("edit", data["id"], "--plan", VALID_PLAN_XML)
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertIsNotNone(item.plan)

    def test_edit_plan_ref(self):
        data = self.add_json("Research", "agent-job")
        self.nightctl("edit", data["id"], "--plan-ref", "docs/d2/spec.md")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.plan_ref, "docs/d2/spec.md")

    def test_edit_nonexistent_id_fails(self):
        rc, _, err = self.nightctl("edit", "does-not-exist", "--title", "New")
        self.assertNotEqual(rc, 0)

    def test_edit_context_and_due(self):
        data = self.add_json("Task", "task")
        self.nightctl("edit", data["id"], "--context", "Updated context", "--due", "2026-05-01")
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.context, "Updated context")
        self.assertEqual(item.due, "2026-05-01")


# ---------------------------------------------------------------------------
# Graph command
# ---------------------------------------------------------------------------

class TestGraph(BaseItemTest):
    def test_graph_empty_exits_zero(self):
        rc, out, _ = self.nightctl("graph")
        self.assertEqual(rc, 0)
        self.assertIn("BACKLOG", out)

    def test_graph_shows_items(self):
        self.add_json("Critical task", "task", priority=1)
        self.add_json("Low task", "task", priority=4)
        rc, out, _ = self.nightctl("graph")
        self.assertEqual(rc, 0)
        self.assertIn("CRITICAL", out)
        self.assertIn("LOW", out)
        self.assertIn("Critical task", out)

    def test_graph_shows_kind_for_non_tasks(self):
        self.add_json("Agent work", "agent-job")
        rc, out, _ = self.nightctl("graph")
        self.assertIn("[agent-job]", out)

    def test_graph_shows_deferred_section(self):
        data = self.add_json("Maybe later", "task")
        self.nightctl("defer", data["id"])
        rc, out, _ = self.nightctl("graph")
        self.assertIn("DEFERRED", out)
        self.assertIn("Maybe later", out)


# ---------------------------------------------------------------------------
# List with unified items
# ---------------------------------------------------------------------------

class TestListItems(BaseItemTest):
    def test_list_shows_items(self):
        self.add_json("Item A", "task")
        self.add_json("Item B", "job", command="echo hi")
        rc, out, _ = self.nightctl("list")
        self.assertEqual(rc, 0)
        self.assertIn("Item A", out)
        self.assertIn("Item B", out)

    def test_list_filter_by_kind(self):
        self.add_json("Task A", "task")
        self.add_json("Job A", "job", command="echo hi")
        rc, out, _ = self.nightctl("list", "--kind", "task")
        self.assertEqual(rc, 0)
        self.assertIn("Task A", out)
        self.assertNotIn("Job A", out)

    def test_list_filter_by_status(self):
        d1 = self.add_json("Open item", "task")
        d2 = self.add_json("Started item", "task")
        self.nightctl("start", d2["id"])
        rc, out, _ = self.nightctl("list", "--status", "in-progress")
        self.assertIn(d2["id"], out)
        self.assertNotIn(d1["id"], out)

    def test_list_json_mode(self):
        self.add_json("Task", "task")
        rc, out, _ = self.nightctl("--json", "list", "--kind", "task")
        data = json.loads(out)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["kind"], "task")


# ---------------------------------------------------------------------------
# Status with unified items
# ---------------------------------------------------------------------------

class TestStatusItem(BaseItemTest):
    def test_status_shows_item_details(self):
        data = self.add_json("Detail test", "agent-job")
        rc, out, _ = self.nightctl("status", data["id"])
        self.assertEqual(rc, 0)
        self.assertIn("Detail test", out)
        self.assertIn("agent-job", out)
        self.assertIn("open", out)

    def test_status_json_mode(self):
        data = self.add_json("JSON test", "task")
        rc, out, _ = self.nightctl("--json", "status", data["id"])
        self.assertEqual(rc, 0)
        parsed = json.loads(out)
        self.assertIn("item", parsed)
        self.assertEqual(parsed["item"]["id"], data["id"])


# ---------------------------------------------------------------------------
# Full lifecycle: agent-job planning workflow
# ---------------------------------------------------------------------------

class TestAgentJobWorkflow(BaseItemTest):
    def test_full_agent_job_lifecycle(self):
        """open -> planning -> plan-review -> in-progress (approved)."""
        data = self.add_json("Research tools", "agent-job")
        item_id = data["id"]

        # Plan
        rc, _, _ = self.nightctl("plan", item_id)
        self.assertEqual(rc, 0)

        # Edit plan
        rc, _, _ = self.nightctl("edit", item_id, "--plan", VALID_PLAN_XML)
        self.assertEqual(rc, 0)

        # Review
        rc, _, _ = self.nightctl("review", item_id)
        self.assertEqual(rc, 0)

        # Approve
        rc, _, _ = self.nightctl("approve", item_id)
        self.assertEqual(rc, 0)

        # Verify final state
        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.status, "in-progress")

    def test_task_direct_lifecycle(self):
        """open -> in-progress -> review -> done."""
        data = self.add_json("Write docs", "task")
        item_id = data["id"]

        self.nightctl("start", item_id)
        self.nightctl("review", item_id)
        rc, _, _ = self.nightctl("done", item_id)
        self.assertEqual(rc, 0)

        from halos.nightctl.item import Item
        item = Item.from_file(Path(data["file"]))
        self.assertEqual(item.status, "done")

    def test_task_with_testing(self):
        """open -> in-progress -> review -> testing -> done."""
        data = self.add_json("Feature", "task")
        item_id = data["id"]

        self.nightctl("start", item_id)
        self.nightctl("review", item_id)
        self.nightctl("testing", item_id)
        rc, _, _ = self.nightctl("done", item_id)
        self.assertEqual(rc, 0)


# ---------------------------------------------------------------------------
# Help output
# ---------------------------------------------------------------------------

class TestHelp(BaseItemTest):
    def test_help_includes_philosophy(self):
        rc, out, _ = run("--help")
        combined = out
        self.assertIn("your best work happens while you sleep", combined.lower())

    def test_help_shows_subcommands(self):
        rc, out, _ = run("--help")
        for cmd in ["add", "plan", "approve", "start", "review", "done", "graph"]:
            self.assertIn(cmd, out)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrors(BaseItemTest):
    def test_transition_from_terminal_state_error(self):
        data = self.add_json("Task", "task")
        self.nightctl("start", data["id"])
        self.nightctl("review", data["id"])
        self.nightctl("done", data["id"])
        rc, _, err = self.nightctl("start", data["id"])
        self.assertNotEqual(rc, 0)
        self.assertIn("ERROR", err)

    def test_missing_id_arg(self):
        rc, _, err = self.nightctl("start")
        self.assertNotEqual(rc, 0)

    def test_add_missing_title(self):
        rc, _, err = self.nightctl("add", "--kind", "task")
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
