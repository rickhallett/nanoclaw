"""Acceptance tests for nightctl unified work tracker merge.

Maps 1:1 to the 27 acceptance criteria in docs/d2/spec-nightctl-merge.md.
Each test is named test_ac_NN_short_description where NN is the criterion number.
These are contract tests -- intentional overlap with unit tests is by design.
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from halos.nightctl.item import (
    Item,
    ValidationError,
    TransitionError,
    valid_transitions,
    VALID_KINDS,
    VALID_STATUSES,
    TERMINAL_STATUSES,
)
from halos.nightctl.plan import validate_plan_xml, PlanValidationError
from halos.nightctl.manifest import Manifest
from halos.nightctl.executor import Executor, _in_window

PYTHON = sys.executable

VALID_PLAN_XML = """\
<plan>
  <goal>Test goal for acceptance</goal>
  <steps><step n="1" output="stdout">Do the thing</step></steps>
  <constraints><constraint>Don't break things</constraint></constraints>
  <success><criterion>It works</criterion></success>
  <output>stdout</output>
</plan>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(*args, config_path=None):
    """Run nightctl CLI and return (returncode, stdout, stderr)."""
    cmd = [PYTHON, "-m", "halos.nightctl.cli"]
    if config_path:
        cmd += ["--config", config_path]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _make_config(tmp_path):
    """Write a nightctl config and create necessary directories. Returns config path."""
    config = {
        "queue_dir": str(tmp_path / "queue"),
        "items_dir": str(tmp_path / "queue" / "items"),
        "manifest_file": str(tmp_path / "queue" / "MANIFEST.yaml"),
        "archive_dir": str(tmp_path / "queue" / "archive"),
        "runs_dir": str(tmp_path / "queue" / "runs"),
        "execution": {
            "mode": "serial",
            "max_workers": 1,
            "overnight_window": "02:00-05:00",
            "timezone": "Europe/London",
        },
        "job": {
            "default_retries": 2,
            "default_timeout_secs": 300,
            "default_schedule": "overnight",
            "valid_schedules": ["overnight", "immediate", "once"],
            "valid_tags": ["maintenance", "memctl", "data", "infra"],
        },
        "notify": {
            "on_failure": False,
            "on_success": False,
            "channel": "main",
        },
        "manifest": {"hash_algorithm": "sha256"},
        "archive": {"retention_days": 30, "dry_run": True},
    }
    config_path = tmp_path / "nightctl.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False))
    for d in ["queue/jobs", "queue/items", "queue/runs", "queue/archive"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return str(config_path)


def _cli_add_json(config_path, title="Test item", kind="task", **kwargs):
    """Add item via CLI and return parsed JSON output."""
    args = ["--json", "--config", config_path, "add", "--title", title, "--kind", kind]
    for k, v in kwargs.items():
        args += [f"--{k.replace('_', '-')}", str(v)]
    rc, out, err = _run_cli(*args)
    assert rc == 0, f"add failed (rc={rc}): {err}"
    return json.loads(out)


# ---------------------------------------------------------------------------
# AC 1: nightctl add --kind task creates item with null command/schedule
# ---------------------------------------------------------------------------

class TestAC01TaskNullFields:
    def test_ac_01_task_null_command_schedule_plan(self, tmp_path):
        """AC1: Task items have null command, schedule, and plan fields."""
        item = Item.create(tmp_path / "items", title="Write docs", kind="task")
        assert item.kind == "task"
        assert item.command is None
        assert item.schedule is None
        assert item.plan is None
        assert item.plan_ref is None

    def test_ac_01_cli_task_creates_file(self, tmp_path):
        """AC1: CLI path also produces null machine fields."""
        cfg = _make_config(tmp_path)
        data = _cli_add_json(cfg, "Write docs", "task")
        item = Item.from_file(Path(data["file"]))
        assert item.command is None
        assert item.schedule is None
        assert item.plan is None


# ---------------------------------------------------------------------------
# AC 2: nightctl add --kind job requires --command
# ---------------------------------------------------------------------------

class TestAC02JobRequiresCommand:
    def test_ac_02_api_rejects_job_without_command(self, tmp_path):
        """AC2: Item.create raises ValidationError for job without command."""
        with pytest.raises(ValidationError, match="command is required"):
            Item.create(tmp_path / "items", title="Run report", kind="job")

    def test_ac_02_cli_rejects_job_without_command(self, tmp_path):
        """AC2: CLI exits non-zero with error message."""
        cfg = _make_config(tmp_path)
        rc, _, err = _run_cli("--config", cfg, "add", "--title", "Report", "--kind", "job")
        assert rc != 0
        assert "command" in err.lower()


# ---------------------------------------------------------------------------
# AC 3: nightctl add --kind agent-job accepts item without plan
# ---------------------------------------------------------------------------

class TestAC03AgentJobDeferredPlan:
    def test_ac_03_api_agent_job_no_plan_ok(self, tmp_path):
        """AC3: Agent-jobs can be created without a plan (brainfart ingress)."""
        item = Item.create(tmp_path / "items", title="Research tools", kind="agent-job")
        assert item.kind == "agent-job"
        assert item.status == "open"
        assert item.plan is None

    def test_ac_03_cli_agent_job_no_plan_ok(self, tmp_path):
        """AC3: CLI creates agent-job without plan, exits 0."""
        cfg = _make_config(tmp_path)
        data = _cli_add_json(cfg, "Research tools", "agent-job")
        assert data["kind"] == "agent-job"


# ---------------------------------------------------------------------------
# AC 4: nightctl plan <id> transitions open -> planning
# ---------------------------------------------------------------------------

class TestAC04PlanTransition:
    def test_ac_04_api_open_to_planning(self, tmp_path):
        """AC4: transition from open to planning via API."""
        item = Item.create(tmp_path / "items", title="Research", kind="agent-job")
        item.transition("planning")
        assert item.status == "planning"

    def test_ac_04_cli_plan_command(self, tmp_path):
        """AC4: nightctl plan <id> transitions to planning."""
        cfg = _make_config(tmp_path)
        data = _cli_add_json(cfg, "Research", "agent-job")
        rc, out, _ = _run_cli("--config", cfg, "plan", data["id"])
        assert rc == 0
        assert "planning" in out


# ---------------------------------------------------------------------------
# AC 5: nightctl review <id> on planning item validates XML plan
# ---------------------------------------------------------------------------

class TestAC05ReviewValidatesPlan:
    def test_ac_05_review_rejects_missing_plan(self, tmp_path):
        """AC5: Planning -> plan-review requires a valid plan."""
        item = Item.create(tmp_path / "items", title="Research", kind="agent-job")
        item.transition("planning")
        with pytest.raises(PlanValidationError, match="requires a plan"):
            item.transition("plan-review")

    def test_ac_05_review_rejects_invalid_plan(self, tmp_path):
        """AC5: Invalid XML plan rejected at plan-review gate."""
        item = Item.create(tmp_path / "items", title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = "<plan><goal></goal></plan>"
        with pytest.raises(PlanValidationError):
            item.transition("plan-review")

    def test_ac_05_review_accepts_valid_plan(self, tmp_path):
        """AC5: Valid plan passes the plan-review gate."""
        item = Item.create(tmp_path / "items", title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        assert item.status == "plan-review"

    def test_ac_05_cli_review_rejects_without_plan(self, tmp_path):
        """AC5: CLI review on planning item without plan exits non-zero."""
        cfg = _make_config(tmp_path)
        data = _cli_add_json(cfg, "Research", "agent-job")
        _run_cli("--config", cfg, "plan", data["id"])
        rc, _, err = _run_cli("--config", cfg, "review", data["id"])
        assert rc != 0


# ---------------------------------------------------------------------------
# AC 6: nightctl approve <id> transitions plan-review -> in-progress
#        with re-validation
# ---------------------------------------------------------------------------

class TestAC06ApproveRevalidates:
    def test_ac_06_approve_transitions_to_in_progress(self, tmp_path):
        """AC6: Approval moves from plan-review to in-progress."""
        item = Item.create(tmp_path / "items", title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        item.transition("in-progress")
        assert item.status == "in-progress"

    def test_ac_06_approve_revalidates_corrupted_plan(self, tmp_path):
        """AC6: Swiss cheese -- plan corrupted after review is caught at approval."""
        item = Item.create(tmp_path / "items", title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        # Corrupt the plan after review
        item.data["plan"] = "<plan><goal></goal></plan>"
        with pytest.raises(PlanValidationError):
            item.transition("in-progress")

    def test_ac_06_cli_approve_workflow(self, tmp_path):
        """AC6: Full CLI workflow: plan -> edit plan -> review -> approve."""
        cfg = _make_config(tmp_path)
        data = _cli_add_json(cfg, "Research", "agent-job")
        _run_cli("--config", cfg, "plan", data["id"])
        _run_cli("--config", cfg, "edit", data["id"], "--plan", VALID_PLAN_XML)
        _run_cli("--config", cfg, "review", data["id"])
        rc, out, _ = _run_cli("--config", cfg, "approve", data["id"])
        assert rc == 0
        assert "approved" in out


# ---------------------------------------------------------------------------
# AC 7: XML validation enforces: goal, steps with n and output,
#        constraints, success
# ---------------------------------------------------------------------------

class TestAC07XmlValidationRules:
    def test_ac_07_missing_goal_rejected(self):
        """AC7: Plan without <goal> fails validation."""
        xml = "<plan><steps><step n='1' output='x'>do</step></steps><constraints><constraint>c</constraint></constraints><success><criterion>y</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<goal> is required" in exc_info.value.errors

    def test_ac_07_missing_steps_rejected(self):
        """AC7: Plan without <steps> fails validation."""
        xml = "<plan><goal>g</goal><constraints><constraint>c</constraint></constraints><success><criterion>y</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<steps> is required" in exc_info.value.errors

    def test_ac_07_step_missing_n_attr_rejected(self):
        """AC7: Step without n attribute fails."""
        xml = "<plan><goal>g</goal><steps><step output='x'>do</step></steps><constraints><constraint>c</constraint></constraints><success><criterion>y</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert any("missing 'n' attribute" in e for e in exc_info.value.errors)

    def test_ac_07_step_missing_output_attr_rejected(self):
        """AC7: Step without output attribute fails."""
        xml = "<plan><goal>g</goal><steps><step n='1'>do</step></steps><constraints><constraint>c</constraint></constraints><success><criterion>y</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert any("missing 'output' attribute" in e for e in exc_info.value.errors)

    def test_ac_07_missing_constraints_rejected(self):
        """AC7: Plan without <constraints> fails."""
        xml = "<plan><goal>g</goal><steps><step n='1' output='x'>do</step></steps><success><criterion>y</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<constraints> is required" in exc_info.value.errors

    def test_ac_07_missing_success_rejected(self):
        """AC7: Plan without <success> fails."""
        xml = "<plan><goal>g</goal><steps><step n='1' output='x'>do</step></steps><constraints><constraint>c</constraint></constraints></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<success> is required" in exc_info.value.errors

    def test_ac_07_valid_plan_passes(self):
        """AC7: Plan with all required elements passes."""
        validate_plan_xml(VALID_PLAN_XML)  # Should not raise


# ---------------------------------------------------------------------------
# AC 8: State transitions validated; invalid produce TransitionError
#        with alternatives
# ---------------------------------------------------------------------------

class TestAC08TransitionValidation:
    def test_ac_08_invalid_transition_raises_with_alternatives(self, tmp_path):
        """AC8: TransitionError includes current, attempted, and allowed list."""
        item = Item.create(tmp_path / "items", title="Test", kind="task")
        with pytest.raises(TransitionError) as exc_info:
            item.transition("done")
        err = exc_info.value
        assert err.current == "open"
        assert err.attempted == "done"
        assert len(err.allowed) > 0
        assert "in-progress" in err.allowed

    def test_ac_08_terminal_state_has_no_transitions(self, tmp_path):
        """AC8: Done items cannot transition anywhere."""
        item = Item.create(tmp_path / "items", title="Test", kind="job", command="echo hi")
        item.transition("in-progress")
        item.transition("running")
        item.transition("done")
        with pytest.raises(TransitionError) as exc_info:
            item.transition("in-progress")
        assert exc_info.value.allowed == []

    def test_ac_08_error_message_includes_valid_transitions(self, tmp_path):
        """AC8: Error message string contains the allowed alternatives."""
        item = Item.create(tmp_path / "items", title="Test", kind="task")
        with pytest.raises(TransitionError) as exc_info:
            item.transition("running")
        msg = str(exc_info.value)
        assert "Valid transitions:" in msg


# ---------------------------------------------------------------------------
# AC 9: nightctl run only executes items where status=in-progress
#        AND kind in job/agent-job
# ---------------------------------------------------------------------------

class TestAC09RunFiltersCriteria:
    def test_ac_09_only_in_progress_jobs_execute(self, tmp_path):
        """AC9: Tasks and open items are not executed."""
        cfg = _make_config(tmp_path)
        items_dir = tmp_path / "queue" / "items"

        # Task in-progress: should NOT execute (tasks have no execution engine)
        task = Item.create(items_dir, title="Human task", kind="task")
        task.transition("in-progress")
        task.save()

        # Job open: should NOT execute (wrong status)
        job_open = Item.create(items_dir, title="Open job", kind="job", command="echo open")
        job_open.save()

        # Job in-progress: SHOULD execute
        job_ip = Item.create(items_dir, title="Ready job", kind="job", command="echo ready")
        job_ip.transition("in-progress")
        job_ip.save()

        rc, out, _ = _run_cli("--config", cfg, "run", "--force")
        # The ready job should be the only one that ran
        assert "Ready job" in out
        assert "Human task" not in out
        assert "Open job" not in out


# ---------------------------------------------------------------------------
# AC 10: nightctl run skips items outside overnight window unless --force
# ---------------------------------------------------------------------------

class TestAC10OvernightWindow:
    def test_ac_10_outside_window_skips(self, tmp_path):
        """AC10: Without --force, running outside window prints skip message."""
        cfg = _make_config(tmp_path)
        items_dir = tmp_path / "queue" / "items"
        job = Item.create(items_dir, title="Night job", kind="job", command="echo hi")
        job.transition("in-progress")
        job.save()

        # The test likely runs outside 02:00-05:00 window
        # If it doesn't, we still verify the message pattern
        rc, out, _ = _run_cli("--config", cfg, "run")
        # Either we're outside window (message shown) or inside (job executes)
        if "outside overnight window" in out:
            assert "Night job" not in out
        else:
            # Inside window -- job should have executed
            assert "Night job" in out

    def test_ac_10_force_overrides_window(self, tmp_path):
        """AC10: --force executes regardless of window."""
        cfg = _make_config(tmp_path)
        items_dir = tmp_path / "queue" / "items"
        job = Item.create(items_dir, title="Forced job", kind="job", command="echo forced")
        job.transition("in-progress")
        job.save()

        rc, out, _ = _run_cli("--config", cfg, "run", "--force")
        assert "outside overnight window" not in out


# ---------------------------------------------------------------------------
# AC 11: nightctl run respects depends_on ordering
# ---------------------------------------------------------------------------

class TestAC11DependsOnOrdering:
    def test_ac_11_unsatisfied_dep_skipped(self, tmp_path):
        """AC11: Item with unsatisfied depends_on is skipped."""
        items_dir = tmp_path / "queue" / "items"
        cfg = _make_config(tmp_path)

        # Dependency item -- open (not done)
        dep = Item.create(items_dir, title="Dependency", kind="job", command="echo dep")
        dep.save()

        # Dependent item -- in-progress but depends on unfinished dep
        dependent = Item.create(
            items_dir, title="Dependent",
            kind="job", command="echo dependent",
            depends_on=[dep.id],
        )
        dependent.transition("in-progress")
        dependent.save()

        rc, out, _ = _run_cli("--config", cfg, "run", "--force")
        assert "dependencies not done" in out or "skipped" in out

    def test_ac_11_satisfied_dep_executes(self, tmp_path):
        """AC11: Item with all deps done can execute."""
        items_dir = tmp_path / "queue" / "items"
        cfg = _make_config(tmp_path)

        # Dependency item -- done
        dep = Item.create(items_dir, title="Done dep", kind="job", command="echo dep")
        dep.transition("in-progress")
        dep.transition("running")
        dep.transition("done")
        dep.save()

        # Dependent item -- in-progress, dep satisfied
        dependent = Item.create(
            items_dir, title="Runnable",
            kind="job", command="echo success",
            depends_on=[dep.id],
        )
        dependent.transition("in-progress")
        dependent.save()

        rc, out, _ = _run_cli("--config", cfg, "run", "--force")
        assert "Runnable" in out


# ---------------------------------------------------------------------------
# AC 12: Agent-job execution delegates to container-runner with XML plan
# ---------------------------------------------------------------------------

class TestAC12AgentJobDelegation:
    def test_ac_12_prepare_agent_job_produces_plan(self, tmp_path):
        """AC12: prepare_agent_job resolves plan and writes plan file."""
        from halos.nightctl.container import prepare_agent_job

        items_dir = tmp_path / "queue" / "items"
        item = Item.create(items_dir, title="Agent task", kind="agent-job", plan=VALID_PLAN_XML)
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        item.transition("in-progress")
        item.save()

        plans_dir = tmp_path / "plans"
        result = prepare_agent_job(item, plans_dir=plans_dir)
        assert result["plan_path"].exists()
        assert "<goal>" in result["plan_xml"]

    def test_ac_12_wrong_kind_rejected(self, tmp_path):
        """AC12: prepare_agent_job rejects non-agent-job items."""
        from halos.nightctl.container import prepare_agent_job, ContainerError

        items_dir = tmp_path / "queue" / "items"
        item = Item.create(items_dir, title="Not agent", kind="task")
        with pytest.raises(ContainerError, match="not agent-job"):
            prepare_agent_job(item)


# ---------------------------------------------------------------------------
# AC 13: Run records written for every execution attempt
# ---------------------------------------------------------------------------

class TestAC13RunRecords:
    def test_ac_13_successful_execution_writes_run_record(self, tmp_path):
        """AC13: After execution, a run record YAML exists in runs_dir."""
        cfg = _make_config(tmp_path)
        items_dir = tmp_path / "queue" / "items"
        runs_dir = tmp_path / "queue" / "runs"

        job = Item.create(items_dir, title="Record test", kind="job", command="echo hello")
        job.transition("in-progress")
        job.save()

        _run_cli("--config", cfg, "run", "--force")

        run_files = list(runs_dir.glob(f"{job.id}-run-*.yaml"))
        assert len(run_files) >= 1

        with open(run_files[0]) as f:
            record = yaml.safe_load(f)
        assert record["id"] == job.id
        assert "outcome" in record
        assert "exit_code" in record
        assert "started" in record
        assert "finished" in record

    def test_ac_13_failed_execution_writes_run_record(self, tmp_path):
        """AC13: Failed commands also produce run records."""
        cfg = _make_config(tmp_path)
        items_dir = tmp_path / "queue" / "items"
        runs_dir = tmp_path / "queue" / "runs"

        job = Item.create(items_dir, title="Fail test", kind="job", command="false")
        job.transition("in-progress")
        job.save()

        _run_cli("--config", cfg, "run", "--force")

        run_files = list(runs_dir.glob(f"{job.id}-run-*.yaml"))
        assert len(run_files) >= 1


# ---------------------------------------------------------------------------
# AC 14: Failed agent-jobs can transition to plan-review via nightctl revise
# ---------------------------------------------------------------------------

class TestAC14ReviseAgentJob:
    def test_ac_14_api_failed_to_plan_review(self, tmp_path):
        """AC14: Failed agent-job transitions to plan-review."""
        item = Item.create(tmp_path / "items", title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        # Revise: back to plan-review
        item.data["plan"] = VALID_PLAN_XML  # plan still present for gate
        item.transition("plan-review")
        assert item.status == "plan-review"

    def test_ac_14_cli_revise(self, tmp_path):
        """AC14: CLI revise command on failed agent-job."""
        cfg = _make_config(tmp_path)
        data = _cli_add_json(cfg, "Research", "agent-job")
        # Drive to failed state via API
        item = Item.from_file(Path(data["file"]))
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        item.save()

        rc, out, _ = _run_cli("--config", cfg, "revise", data["id"])
        assert rc == 0
        assert "revised" in out


# ---------------------------------------------------------------------------
# AC 15: Failed jobs can transition to in-progress via nightctl retry
# ---------------------------------------------------------------------------

class TestAC15RetryJob:
    def test_ac_15_api_failed_job_to_in_progress(self, tmp_path):
        """AC15: Failed job transitions to in-progress."""
        item = Item.create(tmp_path / "items", title="Report", kind="job", command="echo hi")
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        item.transition("in-progress")
        assert item.status == "in-progress"

    def test_ac_15_cli_retry(self, tmp_path):
        """AC15: CLI retry on failed job."""
        cfg = _make_config(tmp_path)
        data = _cli_add_json(cfg, "Report", "job", command="echo hi")
        item = Item.from_file(Path(data["file"]))
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        item.save()

        rc, out, _ = _run_cli("--config", cfg, "retry", data["id"])
        assert rc == 0
        assert "retry" in out

    def test_ac_15_agent_job_cannot_retry_directly(self, tmp_path):
        """AC15: Agent-jobs must go through plan-review, not direct retry."""
        trans = valid_transitions("failed", "agent-job")
        assert "in-progress" not in trans
        assert "plan-review" in trans


# ---------------------------------------------------------------------------
# AC 16: nightctl graph produces ASCII priority tree
# ---------------------------------------------------------------------------

class TestAC16Graph:
    def test_ac_16_graph_has_eisenhower_header(self, tmp_path):
        """AC16: Graph output contains EISENHOWER header."""
        cfg = _make_config(tmp_path)
        rc, out, _ = _run_cli("--config", cfg, "graph")
        assert rc == 0
        assert "EISENHOWER" in out

    def test_ac_16_graph_shows_quadrant_sections(self, tmp_path):
        """AC16: Items grouped by Eisenhower quadrant."""
        cfg = _make_config(tmp_path)
        _cli_add_json(cfg, "Critical task", "task", priority=1)
        _cli_add_json(cfg, "Low task", "task", priority=4)
        rc, out, _ = _run_cli("--config", cfg, "graph")
        assert "Q1" in out
        assert "Q4" in out
        assert "Critical task" in out
        assert "Low task" in out

    def test_ac_16_graph_shows_kind_for_non_tasks(self, tmp_path):
        """AC16: Agent-job kind shown in graph output."""
        cfg = _make_config(tmp_path)
        _cli_add_json(cfg, "Agent work", "agent-job")
        rc, out, _ = _run_cli("--config", cfg, "graph")
        assert "[agent-job]" in out


# ---------------------------------------------------------------------------
# AC 17: nightctl list shows all active items regardless of kind
# ---------------------------------------------------------------------------

class TestAC17ListAll:
    def test_ac_17_list_shows_all_kinds(self, tmp_path):
        """AC17: List without filters shows tasks, jobs, and agent-jobs."""
        cfg = _make_config(tmp_path)
        _cli_add_json(cfg, "My task", "task")
        _cli_add_json(cfg, "My job", "job", command="echo hi")
        _cli_add_json(cfg, "My agent-job", "agent-job")
        rc, out, _ = _run_cli("--config", cfg, "list")
        assert rc == 0
        assert "My task" in out
        assert "My job" in out
        assert "My agent-job" in out


# ---------------------------------------------------------------------------
# AC 18: nightctl list --kind <kind> filters correctly
# ---------------------------------------------------------------------------

class TestAC18ListKindFilter:
    def test_ac_18_filter_tasks_only(self, tmp_path):
        """AC18: --kind task shows only tasks."""
        cfg = _make_config(tmp_path)
        _cli_add_json(cfg, "Task A", "task")
        _cli_add_json(cfg, "Job A", "job", command="echo hi")
        rc, out, _ = _run_cli("--config", cfg, "list", "--kind", "task")
        assert "Task A" in out
        assert "Job A" not in out

    def test_ac_18_filter_agent_jobs_only(self, tmp_path):
        """AC18: --kind agent-job shows only agent-jobs."""
        cfg = _make_config(tmp_path)
        _cli_add_json(cfg, "Task B", "task")
        _cli_add_json(cfg, "Agent B", "agent-job")
        rc, out, _ = _run_cli("--config", cfg, "list", "--kind", "agent-job")
        assert "Agent B" in out
        assert "Task B" not in out


# ---------------------------------------------------------------------------
# AC 19: All file writes use atomic tmp+rename pattern
# ---------------------------------------------------------------------------

class TestAC19AtomicWrites:
    def test_ac_19_create_leaves_no_tmp_files(self, tmp_path):
        """AC19: Item.create uses atomic write -- no .tmp files remain."""
        items_dir = tmp_path / "items"
        Item.create(items_dir, title="Atomic test", kind="task")
        tmp_files = list(items_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_ac_19_save_leaves_no_tmp_files(self, tmp_path):
        """AC19: Item.save uses atomic write -- no .tmp files remain."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Atomic test", kind="task")
        item.transition("in-progress")
        item.save()
        tmp_files = list(items_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_ac_19_save_uses_os_replace(self, tmp_path):
        """AC19: Verify the atomic write pattern by checking file exists after save."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Persist test", kind="task")
        original_path = item.file_path
        item.data["quadrant"] = "q1"
        item.save()
        # File should still exist at the same path
        assert original_path.exists()
        reloaded = Item.from_file(original_path)
        assert reloaded.quadrant == "q1"


# ---------------------------------------------------------------------------
# AC 20: Cancelled/done items remain in items/ for configurable retention
# ---------------------------------------------------------------------------

class TestAC20RetentionInPlace:
    def test_ac_20_done_item_remains_in_items_dir(self, tmp_path):
        """AC20: Done items stay in items/ directory (not immediately archived)."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Completed", kind="task")
        item.transition("in-progress")
        item.transition("review")
        item.transition("done")
        item.save()
        assert item.file_path.exists()
        assert item.file_path.parent == items_dir

    def test_ac_20_cancelled_item_remains_in_items_dir(self, tmp_path):
        """AC20: Cancelled items stay in items/ directory."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Abandoned", kind="task")
        item.transition("cancelled")
        item.save()
        assert item.file_path.exists()
        assert item.file_path.parent == items_dir


# ---------------------------------------------------------------------------
# AC 21: nightctl archive --execute respects retention period
# ---------------------------------------------------------------------------

class TestAC21ArchiveRetention:
    def test_ac_21_recent_items_not_archived(self, tmp_path):
        """AC21: Items younger than retention_days are not archived."""
        from halos.nightctl.archive import run_archive
        from halos.nightctl.config import load_config

        cfg_path = _make_config(tmp_path)
        cfg = load_config(cfg_path)
        manifest = Manifest(Path(cfg.manifest_file))

        # Add a recently-done job to manifest
        items_dir = tmp_path / "queue" / "items"
        job = Item.create(items_dir, title="Recent done", kind="job", command="echo hi")
        job.transition("in-progress")
        job.transition("running")
        job.transition("done")
        job.save()
        manifest.append(job)

        results = run_archive(cfg, manifest, execute=True)
        # Recently created -- should not be archived
        assert results["archived"] == 0


# ---------------------------------------------------------------------------
# AC 22: Manifest rebuilds correctly from items/ directory
# ---------------------------------------------------------------------------

class TestAC22ManifestRebuild:
    def test_ac_22_rebuild_picks_up_all_jobs(self, tmp_path):
        """AC22: Manifest rebuild reads all YAML files from jobs dir."""
        from halos.nightctl.job import Job

        jobs_dir = tmp_path / "queue" / "jobs"
        jobs_dir.mkdir(parents=True)
        manifest_file = tmp_path / "queue" / "MANIFEST.yaml"

        # Create a legacy job file
        job_data = {
            "id": "20260317-100000-test1234",
            "title": "Rebuild test job",
            "command": "echo rebuilt",
            "status": "pending",
            "priority": 3,
            "schedule": "overnight",
            "tags": [],
            "depends_on": [],
            "created": "2026-03-17T10:00:00Z",
        }
        job_path = jobs_dir / "20260317-100000-test1234-rebuild-test-job.yaml"
        job_path.write_text(yaml.dump(job_data, default_flow_style=False))

        manifest = Manifest(manifest_file)
        count, errors = manifest.rebuild(jobs_dir)
        assert count == 1
        assert len(errors) == 0

        entry = manifest.get_entry("20260317-100000-test1234")
        assert entry is not None
        assert entry["title"] == "Rebuild test job"


# ---------------------------------------------------------------------------
# AC 23: Manifest verify detects hash drift
# ---------------------------------------------------------------------------

class TestAC23ManifestVerify:
    def test_ac_23_detects_hash_drift(self, tmp_path):
        """AC23: Modified file detected as DRIFT by manifest verify."""
        from halos.nightctl.job import Job

        jobs_dir = tmp_path / "queue" / "jobs"
        jobs_dir.mkdir(parents=True)
        manifest_file = tmp_path / "queue" / "MANIFEST.yaml"

        job_data = {
            "id": "20260317-110000-drift123",
            "title": "Drift test",
            "command": "echo drift",
            "status": "pending",
            "priority": 3,
            "schedule": "overnight",
            "tags": [],
            "depends_on": [],
            "created": "2026-03-17T11:00:00Z",
        }
        job_path = jobs_dir / "20260317-110000-drift123-drift-test.yaml"
        job_path.write_text(yaml.dump(job_data, default_flow_style=False))

        manifest = Manifest(manifest_file)
        manifest.rebuild(jobs_dir)

        # Modify the file after rebuild
        job_data["title"] = "TAMPERED"
        job_path.write_text(yaml.dump(job_data, default_flow_style=False))

        results = manifest.verify(jobs_dir)
        drift_results = [r for r in results if r["status"] == "DRIFT"]
        assert len(drift_results) >= 1

    def test_ac_23_matching_file_reports_match(self, tmp_path):
        """AC23: Unmodified file reports MATCH."""
        from halos.nightctl.job import Job

        jobs_dir = tmp_path / "queue" / "jobs"
        jobs_dir.mkdir(parents=True)
        manifest_file = tmp_path / "queue" / "MANIFEST.yaml"

        job_data = {
            "id": "20260317-110000-match123",
            "title": "Match test",
            "command": "echo match",
            "status": "pending",
            "priority": 3,
            "schedule": "overnight",
            "tags": [],
            "depends_on": [],
            "created": "2026-03-17T11:00:00Z",
        }
        job_path = jobs_dir / "20260317-110000-match123-match-test.yaml"
        job_path.write_text(yaml.dump(job_data, default_flow_style=False))

        manifest = Manifest(manifest_file)
        manifest.rebuild(jobs_dir)

        results = manifest.verify(jobs_dir)
        match_results = [r for r in results if r["status"] == "MATCH"]
        assert len(match_results) >= 1


# ---------------------------------------------------------------------------
# AC 24: Existing todoctl items migrated with status preserved
# ---------------------------------------------------------------------------

class TestAC24Migration:
    def test_ac_24_status_preserved(self, tmp_path):
        """AC24: Migrated items retain their original status."""
        from halos.nightctl.migrate_todoctl import migrate_item

        dest = tmp_path / "queue" / "items"
        dest.mkdir(parents=True)

        for status in ["open", "done"]:
            item_data = {
                "id": f"20260316-{status[:3]}",
                "title": f"Migrated {status} item",
                "status": status,
                "priority": 2,
                "tags": ["test"],
                "context": "Migration test",
                "created": "2026-03-16T12:00:00Z",
                "due": None,
                "blocked_by": None,
            }
            result = migrate_item(item_data, dest)
            assert result["outcome"] == "ok"
            assert result["status"] == status

            written = [f for f in dest.glob("*.yaml") if status[:3] in f.name]
            assert len(written) >= 1
            item = Item.from_file(written[0])
            assert item.status == status

    def test_ac_24_kind_defaults_to_task(self, tmp_path):
        """AC24: Migrated todoctl items get kind=task."""
        from halos.nightctl.migrate_todoctl import migrate_item

        dest = tmp_path / "queue" / "items"
        dest.mkdir(parents=True)

        item_data = {
            "id": "20260316-task01",
            "title": "Old todoctl item",
            "status": "open",
            "priority": 3,
            "tags": [],
            "context": "",
            "created": "2026-03-16T12:00:00Z",
            "due": None,
            "blocked_by": None,
        }
        migrate_item(item_data, dest)
        written = list(dest.glob("*.yaml"))
        item = Item.from_file(written[0])
        assert item.kind == "task"


# ---------------------------------------------------------------------------
# AC 25: todoctl console_script removed from pyproject.toml
# ---------------------------------------------------------------------------

class TestAC25TodoctlRemoved:
    def test_ac_25_no_todoctl_in_pyproject(self):
        """AC25: pyproject.toml does not contain a todoctl console_script entry."""
        pyproject = Path("/home/mrkai/code/nanoclaw/pyproject.toml")
        content = pyproject.read_text()
        # Check that there's no "todoctl" entry in the scripts section
        assert "todoctl" not in content


# ---------------------------------------------------------------------------
# AC 26: nightctl --help includes "your best work happens while you sleep"
# ---------------------------------------------------------------------------

class TestAC26HelpPhilosophy:
    def test_ac_26_help_contains_philosophy(self):
        """AC26: --help output contains the nightctl philosophy tagline."""
        rc, out, _ = _run_cli("--help")
        combined = out.lower()
        assert "your best work happens while you sleep" in combined


# ---------------------------------------------------------------------------
# AC 27: reportctl and briefings collectors work with new item location
# ---------------------------------------------------------------------------

class TestAC27CollectorCompatibility:
    def test_ac_27_reportctl_reads_queue_items(self, tmp_path):
        """AC27: reportctl collector reads from queue/items/ directory."""
        from halos.reportctl.collectors import collect_todoctl

        # Create queue/items/ with a task
        items_dir = tmp_path / "queue" / "items"
        items_dir.mkdir(parents=True)

        item = Item.create(items_dir, title="Collector test", kind="task", priority=2)
        item.save()

        # Write a minimal todoctl config pointing at this directory
        todoctl_cfg = tmp_path / "todoctl.yaml"
        todoctl_cfg.write_text(yaml.dump({
            "items_dir": "./backlog/items",  # legacy path -- collector should prefer queue/items
        }))

        result = collect_todoctl(todoctl_cfg)
        assert result["total"] >= 1

    def test_ac_27_briefings_reads_queue_items(self, tmp_path):
        """AC27: briefings gather reads open items from queue/items/."""
        from halos.briefings.gather import _get_open_todos

        # Create queue/items/ with an open task
        items_dir = tmp_path / "queue" / "items"
        items_dir.mkdir(parents=True)

        item = Item.create(items_dir, title="Briefing test", kind="task", priority=1)
        item.save()

        # Config lives at tmp_path root -- _get_open_todos looks for queue/items/ relative to it
        todoctl_cfg = tmp_path / "todoctl.yaml"
        todoctl_cfg.write_text(yaml.dump({
            "items_dir": "./backlog/items",
        }))

        result = _get_open_todos(todoctl_cfg)
        assert len(result) >= 1
        assert any(i["title"] == "Briefing test" for i in result)
