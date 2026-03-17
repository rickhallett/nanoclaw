"""Container integration for nightctl agent-job execution.

Bridge between Python nightctl and TypeScript container-runner.
Prepares agent-job Items for container execution by:
1. Extracting and validating the XML plan
2. Writing the plan to a temp file the container can mount
3. Creating an IPC message for src/ipc.ts to pick up

The TypeScript side (src/container-runner.ts) spawns the actual container.
nightctl delegates to it via the IPC filesystem protocol.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    from . import yaml_shim as yaml

from .item import Item
from .plan import validate_plan_xml, validate_plan_ref, PlanValidationError
from halos.common.log import hlog


class ContainerError(Exception):
    """Raised when container preparation or IPC dispatch fails."""


def resolve_plan(item: Item) -> str:
    """Extract the XML plan from an Item (inline or from plan_ref).

    Validates the plan before returning it.
    Raises PlanValidationError if the plan is invalid.
    Raises ContainerError if no plan is available.
    """
    if item.plan:
        validate_plan_xml(item.plan)
        return item.plan

    if item.plan_ref:
        # Resolve plan_ref relative to the item's file location
        base_dir = item.file_path.parent if item.file_path else Path.cwd()
        # Go up to project root (queue/items/ -> project root)
        project_root = base_dir
        for _ in range(3):  # queue/items/ -> queue/ -> project root
            parent = project_root.parent
            if parent == project_root:
                break
            project_root = parent

        ref_path = Path(item.plan_ref)
        if not ref_path.is_absolute():
            ref_path = (project_root / ref_path).resolve()

        # Path traversal protection: resolved path must stay within project
        if not ref_path.is_relative_to(project_root):
            raise ContainerError(
                f"Plan ref escapes project root: {item.plan_ref} (resolved to {ref_path})"
            )

        if not ref_path.exists():
            raise ContainerError(
                f"Plan ref file not found: {item.plan_ref} (resolved to {ref_path})"
            )

        plan_text = ref_path.read_text()
        # Use the same extraction logic as plan.py (handles <plan> with attributes)
        from .plan import extract_plan_from_file, PlanValidationError
        try:
            plan_xml = extract_plan_from_file(plan_text)
            validate_plan_xml(plan_xml)
            return plan_xml
        except PlanValidationError as e:
            raise ContainerError(
                f"Plan ref validation failed for {item.plan_ref}: {e}"
            ) from e

    raise ContainerError(
        f"Item {item.id} has no plan (inline or plan_ref) — cannot execute as agent-job"
    )


def write_plan_file(plan_xml: str, item: Item, plans_dir: Path | None = None) -> Path:
    """Write the XML plan to a file that can be mounted into a container.

    Returns the path to the written plan file.
    Uses atomic writes (tmp + os.replace).
    """
    if plans_dir is None:
        plans_dir = Path(tempfile.gettempdir()) / "nightctl-plans"

    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plans_dir / f"{item.id}-plan.xml"

    tmp = plan_path.with_suffix(".xml.tmp")
    try:
        tmp.write_text(plan_xml)
        os.replace(str(tmp), str(plan_path))
    except OSError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ContainerError(f"Failed to write plan file: {e}") from e

    return plan_path


def create_ipc_message(item: Item, plan_path: Path, ipc_dir: Path) -> Path:
    """Create an IPC task message for the TypeScript container-runner.

    Writes a JSON file to the IPC tasks directory that src/ipc.ts will
    pick up and process. The message instructs the container-runner to
    spawn a container with the agent-job's plan.

    The IPC message format follows the existing protocol in src/ipc.ts:
    - type: "schedule_task" for creating a one-shot task
    - prompt: the XML plan as the agent's instruction set
    - schedule_type: "once" for immediate execution
    - schedule_value: now (execute immediately)

    Returns the path to the written IPC message file.
    """
    messages_dir = ipc_dir / "tasks"
    messages_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")

    message = {
        "type": "schedule_task",
        "taskId": f"nightctl-{item.id}",
        "prompt": (
            f"Execute the following agent-job plan. "
            f"The plan XML is at: {plan_path}\n\n"
            f"Plan contents:\n{plan_path.read_text()}"
        ),
        "schedule_type": "once",
        "schedule_value": now.isoformat(),
        "context_mode": "group",
        "targetJid": "",  # Must be set by caller or config
    }

    filename = f"nightctl-{item.id}-{timestamp}.json"
    msg_path = messages_dir / filename

    tmp = msg_path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(message, indent=2))
        os.replace(str(tmp), str(msg_path))
    except OSError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ContainerError(f"Failed to write IPC message: {e}") from e

    return msg_path


def prepare_agent_job(
    item: Item,
    ipc_dir: Path | None = None,
    plans_dir: Path | None = None,
) -> dict:
    """Full preparation pipeline for an agent-job Item.

    1. Resolves and validates the XML plan
    2. Writes the plan to a mountable file
    3. Creates an IPC message for container-runner

    Returns a dict with plan_path, ipc_path, and plan_xml.
    Raises ContainerError or PlanValidationError on failure.
    """
    if item.kind != "agent-job":
        raise ContainerError(f"Item {item.id} is kind={item.kind}, not agent-job")

    hlog("nightctl", "info", "agent_job_prepare", {
        "id": item.id,
        "title": item.title,
        "has_plan": bool(item.plan),
        "has_plan_ref": bool(item.plan_ref),
    })

    # Step 1: Resolve and validate plan
    plan_xml = resolve_plan(item)

    # Step 2: Write plan file
    plan_path = write_plan_file(plan_xml, item, plans_dir=plans_dir)

    # Step 3: Create IPC message (if ipc_dir provided)
    ipc_path = None
    if ipc_dir:
        ipc_path = create_ipc_message(item, plan_path, ipc_dir)

    hlog("nightctl", "info", "agent_job_prepared", {
        "id": item.id,
        "plan_path": str(plan_path),
        "ipc_path": str(ipc_path) if ipc_path else None,
    })

    return {
        "plan_xml": plan_xml,
        "plan_path": plan_path,
        "ipc_path": ipc_path,
    }
