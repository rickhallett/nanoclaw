"""Tests for nightctl unified Item model."""

import pytest
from pathlib import Path

from halos.nightctl.item import (
    Item,
    ValidationError,
    TransitionError,
    SaveError,
    valid_transitions,
    VALID_KINDS,
    VALID_STATUSES,
    TERMINAL_STATUSES,
)
from halos.nightctl.plan import PlanValidationError


VALID_PLAN_XML = """\
<plan>
  <goal>Test goal</goal>
  <steps><step n="1" output="stdout">Do the thing</step></steps>
  <constraints><constraint>Don't break things</constraint></constraints>
  <success><criterion>It works</criterion></success>
  <output>stdout</output>
</plan>"""


# ---------------------------------------------------------------------------
# State machine: valid_transitions()
# ---------------------------------------------------------------------------

class TestValidTransitions:
    """Exhaustive state machine tests."""

    def test_agent_job_can_skip_planning_with_context(self):
        """Agent-jobs can go open → in-progress (context-only mode for research jobs)."""
        trans = valid_transitions("open", "agent-job")
        assert "in-progress" in trans
        assert "planning" in trans

    def test_task_can_skip_planning(self):
        trans = valid_transitions("open", "task")
        assert "in-progress" in trans

    def test_job_can_skip_planning(self):
        trans = valid_transitions("open", "job")
        assert "in-progress" in trans

    def test_task_cannot_enter_running(self):
        trans = valid_transitions("in-progress", "task")
        assert "running" not in trans

    def test_job_can_enter_running(self):
        trans = valid_transitions("in-progress", "job")
        assert "running" in trans

    def test_agent_job_can_enter_running(self):
        trans = valid_transitions("in-progress", "agent-job")
        assert "running" in trans

    def test_failed_agent_job_recovers_via_plan_review(self):
        trans = valid_transitions("failed", "agent-job")
        assert "plan-review" in trans
        assert "in-progress" not in trans

    def test_failed_job_recovers_via_in_progress(self):
        trans = valid_transitions("failed", "job")
        assert "in-progress" in trans
        assert "plan-review" not in trans

    def test_failed_task_recovers_via_in_progress(self):
        trans = valid_transitions("failed", "task")
        assert "in-progress" in trans
        assert "plan-review" not in trans

    def test_terminal_states_have_no_transitions(self):
        for kind in VALID_KINDS:
            for terminal in TERMINAL_STATUSES:
                assert valid_transitions(terminal, kind) == []

    def test_all_statuses_have_entries(self):
        """Every status in VALID_STATUSES is covered in the transition table."""
        for kind in VALID_KINDS:
            for status in VALID_STATUSES:
                # Should not raise — even terminal states return []
                result = valid_transitions(status, kind)
                assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Item creation
# ---------------------------------------------------------------------------

class TestItemCreate:
    def test_create_task(self, tmp_path):
        item = Item.create(tmp_path, title="Write docs", kind="task")
        assert item.kind == "task"
        assert item.status == "open"
        assert item.command is None
        assert item.file_path.exists()

    def test_create_job_requires_command(self, tmp_path):
        with pytest.raises(ValidationError, match="command is required"):
            Item.create(tmp_path, title="Run report", kind="job")

    def test_create_job_with_command(self, tmp_path):
        item = Item.create(tmp_path, title="Run report", kind="job", command="echo hi", schedule="overnight")
        assert item.kind == "job"
        assert item.command == "echo hi"
        assert item.schedule == "overnight"

    def test_create_agent_job_without_plan_ok(self, tmp_path):
        """Brainfart ingress: agent-jobs don't need plan at creation."""
        item = Item.create(tmp_path, title="Research tools", kind="agent-job")
        assert item.kind == "agent-job"
        assert item.plan is None

    def test_create_agent_job_with_valid_plan(self, tmp_path):
        item = Item.create(tmp_path, title="Research tools", kind="agent-job", plan=VALID_PLAN_XML)
        assert item.plan is not None

    def test_create_agent_job_with_invalid_plan_rejects(self, tmp_path):
        with pytest.raises(PlanValidationError):
            Item.create(tmp_path, title="Bad plan", kind="agent-job", plan="<plan><goal></goal></plan>")

    def test_create_invalid_kind_rejects(self, tmp_path):
        with pytest.raises(ValidationError, match="invalid kind"):
            Item.create(tmp_path, title="Nope", kind="unicorn")

    def test_create_empty_title_rejects(self, tmp_path):
        with pytest.raises(ValidationError, match="title is required"):
            Item.create(tmp_path, title="  ", kind="task")

    def test_create_invalid_schedule_rejects(self, tmp_path):
        with pytest.raises(ValidationError, match="invalid schedule"):
            Item.create(tmp_path, title="Bad schedule", kind="job", command="echo", schedule="biweekly")

    def test_id_is_unique(self, tmp_path):
        a = Item.create(tmp_path, title="First", kind="task")
        b = Item.create(tmp_path, title="Second", kind="task")
        assert a.id != b.id


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

class TestItemTransition:
    def test_valid_transition(self, tmp_path):
        item = Item.create(tmp_path, title="Test", kind="task")
        item.transition("in-progress")
        assert item.status == "in-progress"

    def test_invalid_transition_raises(self, tmp_path):
        item = Item.create(tmp_path, title="Test", kind="task")
        with pytest.raises(TransitionError) as exc_info:
            item.transition("done")
        assert "open" in str(exc_info.value)
        assert exc_info.value.current == "open"
        assert exc_info.value.attempted == "done"
        assert len(exc_info.value.allowed) > 0

    def test_transition_updates_modified(self, tmp_path):
        item = Item.create(tmp_path, title="Test", kind="task")
        original = item.modified
        item.transition("in-progress")
        assert item.modified >= original

    def test_terminal_state_rejects_all(self, tmp_path):
        item = Item.create(tmp_path, title="Test", kind="job", command="echo hi")
        item.transition("in-progress")
        item.transition("running")
        item.transition("done")
        for status in VALID_STATUSES:
            if status == "done":
                continue
            with pytest.raises(TransitionError):
                item.transition(status)


# ---------------------------------------------------------------------------
# Plan validation gates
# ---------------------------------------------------------------------------

class TestPlanGates:
    def test_agent_job_plan_review_requires_plan(self, tmp_path):
        item = Item.create(tmp_path, title="Research", kind="agent-job")
        item.transition("planning")
        with pytest.raises(PlanValidationError, match="requires a plan"):
            item.transition("plan-review")

    def test_agent_job_plan_review_with_inline_plan(self, tmp_path):
        item = Item.create(tmp_path, title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        assert item.status == "plan-review"

    def test_agent_job_approval_revalidates(self, tmp_path):
        """Swiss cheese: plan-review → in-progress re-validates."""
        item = Item.create(tmp_path, title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        # Corrupt the plan after review
        item.data["plan"] = "<plan><goal></goal></plan>"
        with pytest.raises(PlanValidationError):
            item.transition("in-progress")

    def test_agent_job_plan_ref_validated(self, tmp_path):
        plan_file = tmp_path / "spec.md"
        plan_file.write_text(f"# Spec\n\n{VALID_PLAN_XML}\n")

        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Research", kind="agent-job", plan_ref=str(plan_file))
        item.transition("planning")
        item.transition("plan-review")
        assert item.status == "plan-review"

    def test_job_skips_plan_gate(self, tmp_path):
        """Jobs don't trigger plan validation even when transitioning."""
        item = Item.create(tmp_path, title="Report", kind="job", command="echo hi")
        item.transition("in-progress")
        assert item.status == "in-progress"


# ---------------------------------------------------------------------------
# Full lifecycle tests
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_task_lifecycle(self, tmp_path):
        """open → in-progress → review → done"""
        item = Item.create(tmp_path, title="Write docs", kind="task")
        item.transition("in-progress")
        item.transition("review")
        item.transition("done")
        assert item.status == "done"

    def test_job_lifecycle(self, tmp_path):
        """open → in-progress → running → done"""
        item = Item.create(tmp_path, title="Run report", kind="job", command="echo hi")
        item.transition("in-progress")
        item.transition("running")
        item.transition("done")
        assert item.status == "done"

    def test_agent_job_lifecycle(self, tmp_path):
        """open → planning → plan-review → in-progress → running → done"""
        item = Item.create(tmp_path, title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        item.transition("in-progress")
        item.transition("running")
        item.transition("done")
        assert item.status == "done"

    def test_agent_job_failure_recovery(self, tmp_path):
        """open → planning → plan-review → in-progress → running → failed → plan-review"""
        item = Item.create(tmp_path, title="Research", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")
        # Recovery: revise the plan
        item.data["plan"] = VALID_PLAN_XML
        item.transition("plan-review")
        assert item.status == "plan-review"

    def test_deferred_and_back(self, tmp_path):
        """open → deferred → open → in-progress"""
        item = Item.create(tmp_path, title="Maybe later", kind="task")
        item.transition("deferred")
        item.transition("open")
        item.transition("in-progress")
        assert item.status == "in-progress"

    def test_blocked_and_unblocked(self, tmp_path):
        """open → in-progress → blocked → in-progress → review → done"""
        item = Item.create(tmp_path, title="Blocked work", kind="task")
        item.transition("in-progress")
        item.transition("blocked")
        item.data["blocked_by"] = "waiting on API access"
        item.transition("in-progress")
        item.transition("review")
        item.transition("done")
        assert item.status == "done"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_reload(self, tmp_path):
        item = Item.create(tmp_path, title="Persist me", kind="task")
        item.transition("in-progress")
        item.save()
        reloaded = Item.from_file(item.file_path)
        assert reloaded.id == item.id
        assert reloaded.status == "in-progress"
        assert reloaded.kind == "task"

    def test_no_stale_tmp_files(self, tmp_path):
        item = Item.create(tmp_path, title="Clean save", kind="task")
        item.save()
        tmps = list(tmp_path.glob("*.tmp"))
        assert not tmps

    def test_save_without_filepath_raises_runtime_error(self):
        item = Item({"id": "test", "title": "test", "kind": "task"})
        with pytest.raises(RuntimeError, match="No file path"):
            item.save()

    def test_file_hash(self, tmp_path):
        item = Item.create(tmp_path, title="Hash me", kind="task")
        h = item.file_hash()
        assert len(h) == 64  # sha256 hex

    def test_archive(self, tmp_path):
        items_dir = tmp_path / "items"
        archive_dir = tmp_path / "archive"
        item = Item.create(items_dir, title="Archive me", kind="task")
        original = item.file_path
        item.archive(archive_dir)
        assert not original.exists()
        assert item.file_path.parent == archive_dir
        assert item.file_path.exists()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_validate_missing_id(self):
        item = Item({"title": "no id", "kind": "task"})
        with pytest.raises(ValidationError, match="id is required"):
            item.validate()

    def test_validate_missing_title(self):
        item = Item({"id": "x", "kind": "task"})
        with pytest.raises(ValidationError, match="title is required"):
            item.validate()

    def test_validate_invalid_kind(self):
        item = Item({"id": "x", "title": "t", "kind": "unicorn"})
        with pytest.raises(ValidationError, match="invalid kind"):
            item.validate()

    def test_validate_invalid_status(self):
        item = Item({"id": "x", "title": "t", "kind": "task", "status": "vibing"})
        with pytest.raises(ValidationError, match="invalid status"):
            item.validate()

    def test_validate_priority_not_int(self):
        item = Item({"id": "x", "title": "t", "kind": "task", "priority": "high"})
        with pytest.raises(ValidationError, match="priority must be int"):
            item.validate()

    def test_validate_priority_bool_rejected(self):
        item = Item({"id": "x", "title": "t", "kind": "task", "priority": True})
        with pytest.raises(ValidationError, match="priority must be int"):
            item.validate()
