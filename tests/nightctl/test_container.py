"""Tests for nightctl container integration module."""

import json
import pytest
from pathlib import Path

from halos.nightctl.container import (
    ContainerError,
    resolve_plan,
    write_plan_file,
    create_ipc_message,
    prepare_agent_job,
)
from halos.nightctl.item import Item
from halos.nightctl.plan import PlanValidationError


VALID_PLAN = """<plan>
  <goal>Research competing tools</goal>
  <context>We need to understand the landscape.</context>
  <steps>
    <step n="1" output="docs/research.md">Research the tools.</step>
  </steps>
  <constraints>
    <constraint>Do not modify existing code</constraint>
  </constraints>
  <success>
    <criterion>At least 3 tools analysed</criterion>
  </success>
  <output>docs/research.md</output>
</plan>"""

INVALID_PLAN = "<plan><goal>Missing everything else</goal></plan>"


def _make_item(tmp_path, kind="agent-job", plan=None, plan_ref=None, status="in-progress"):
    """Create a test Item."""
    items_dir = tmp_path / "queue" / "items"
    items_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "id": "20260317-120000-abcd1234",
        "title": "Test agent job",
        "kind": kind,
        "status": status,
        "priority": 2,
        "tags": ["test"],
        "entities": [],
        "context": "Test context",
        "due": None,
        "blocked_by": None,
        "command": None,
        "schedule": "overnight",
        "window": None,
        "depends_on": [],
        "retries": 2,
        "retries_remaining": 2,
        "timeout_secs": 300,
        "plan": plan,
        "plan_ref": plan_ref,
        "created": "2026-03-17T12:00:00Z",
        "modified": "2026-03-17T12:00:00Z",
        "created_by": "human",
    }

    file_path = items_dir / "20260317-120000-abcd1234-test-agent-job.yaml"

    import yaml
    file_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    return Item(data, file_path=file_path)


class TestResolvePlan:
    def test_inline_plan(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        result = resolve_plan(item)
        assert "<goal>Research competing tools</goal>" in result

    def test_no_plan_raises(self, tmp_path):
        item = _make_item(tmp_path)
        with pytest.raises(ContainerError, match="has no plan"):
            resolve_plan(item)

    def test_invalid_inline_plan_raises(self, tmp_path):
        item = _make_item(tmp_path, plan=INVALID_PLAN)
        with pytest.raises(PlanValidationError):
            resolve_plan(item)

    def test_plan_ref(self, tmp_path):
        # Create a plan ref file
        plan_file = tmp_path / "docs" / "plan.md"
        plan_file.parent.mkdir(parents=True)
        plan_file.write_text(f"# Plan\n\n{VALID_PLAN}\n")

        item = _make_item(tmp_path, plan_ref=str(plan_file))
        result = resolve_plan(item)
        assert "<goal>Research competing tools</goal>" in result

    def test_plan_ref_missing_file(self, tmp_path):
        item = _make_item(tmp_path, plan_ref="nonexistent/plan.md")
        with pytest.raises(ContainerError, match="not found"):
            resolve_plan(item)

    def test_plan_ref_path_traversal_rejected(self, tmp_path):
        item = _make_item(tmp_path, plan_ref="../../../../etc/passwd")
        with pytest.raises(ContainerError, match="escapes project root"):
            resolve_plan(item)


class TestWritePlanFile:
    def test_writes_plan(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"

        result = write_plan_file(VALID_PLAN, item, plans_dir=plans_dir)

        assert result.exists()
        assert result.suffix == ".xml"
        assert "Research competing tools" in result.read_text()
        assert item.id in result.name

    def test_atomic_write(self, tmp_path):
        """No .tmp files left behind on success."""
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"

        write_plan_file(VALID_PLAN, item, plans_dir=plans_dir)

        tmp_files = list(plans_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_creates_plans_dir(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "new" / "plans"

        write_plan_file(VALID_PLAN, item, plans_dir=plans_dir)
        assert plans_dir.exists()


class TestCreateIpcMessage:
    def test_creates_message(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"
        plan_path = write_plan_file(VALID_PLAN, item, plans_dir=plans_dir)

        ipc_dir = tmp_path / "ipc" / "main"
        result = create_ipc_message(item, plan_path, ipc_dir)

        assert result.exists()
        assert result.suffix == ".json"

        data = json.loads(result.read_text())
        assert data["type"] == "schedule_task"
        assert f"nightctl-{item.id}" == data["taskId"]
        assert "schedule_type" in data
        assert data["schedule_type"] == "once"

    def test_message_contains_plan(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"
        plan_path = write_plan_file(VALID_PLAN, item, plans_dir=plans_dir)

        ipc_dir = tmp_path / "ipc" / "main"
        result = create_ipc_message(item, plan_path, ipc_dir)

        data = json.loads(result.read_text())
        assert "Research competing tools" in data["prompt"]

    def test_creates_tasks_subdir(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"
        plan_path = write_plan_file(VALID_PLAN, item, plans_dir=plans_dir)

        ipc_dir = tmp_path / "ipc" / "main"
        create_ipc_message(item, plan_path, ipc_dir)

        assert (ipc_dir / "tasks").exists()


class TestPrepareAgentJob:
    def test_full_pipeline(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"

        result = prepare_agent_job(item, plans_dir=plans_dir)

        assert "plan_xml" in result
        assert "plan_path" in result
        assert result["plan_path"].exists()
        assert "<goal>" in result["plan_xml"]

    def test_full_pipeline_with_ipc(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"
        ipc_dir = tmp_path / "ipc" / "main"

        result = prepare_agent_job(item, ipc_dir=ipc_dir, plans_dir=plans_dir)

        assert result["ipc_path"] is not None
        assert result["ipc_path"].exists()

    def test_wrong_kind_raises(self, tmp_path):
        item = _make_item(tmp_path, kind="task", plan=VALID_PLAN)
        with pytest.raises(ContainerError, match="not agent-job"):
            prepare_agent_job(item)

    def test_no_plan_raises(self, tmp_path):
        item = _make_item(tmp_path)
        with pytest.raises(ContainerError, match="has no plan"):
            prepare_agent_job(item)

    def test_invalid_plan_raises(self, tmp_path):
        item = _make_item(tmp_path, plan=INVALID_PLAN)
        with pytest.raises(PlanValidationError):
            prepare_agent_job(item)

    def test_no_ipc_dir_skips_ipc(self, tmp_path):
        item = _make_item(tmp_path, plan=VALID_PLAN)
        plans_dir = tmp_path / "plans"

        result = prepare_agent_job(item, plans_dir=plans_dir)
        assert result["ipc_path"] is None
