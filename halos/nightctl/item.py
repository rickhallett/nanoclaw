"""Unified work item model for nightctl.

Merges Job (execution engine) + TodoItem (state machine) into a single
model with kind-aware transition enforcement, atomic writes, and plan
validation gates.

Your best work happens while you sleep.
"""

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    from . import yaml_shim as yaml


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Invalid data on creation or field update."""


class TransitionError(Exception):
    """Invalid state machine transition. Includes allowed alternatives."""

    def __init__(self, current: str, attempted: str, allowed: list[str]):
        self.current = current
        self.attempted = attempted
        self.allowed = allowed
        allowed_str = ", ".join(allowed) if allowed else "(none — terminal state)"
        super().__init__(
            f"Cannot transition from '{current}' to '{attempted}'. "
            f"Valid transitions: {allowed_str}"
        )


class SaveError(Exception):
    """Filesystem failure during atomic write."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_KINDS = ("task", "job", "agent-job")

VALID_STATUSES = (
    "open", "planning", "plan-review", "in-progress",
    "running", "review", "testing",
    "blocked", "deferred",
    "done", "failed", "cancelled",
)

TERMINAL_STATUSES = ("done", "cancelled")

VALID_SCHEDULES = ("overnight", "immediate", "once")

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

_BASE_TRANSITIONS: dict[str, list[str]] = {
    # Entry
    "open":         ["planning", "in-progress", "deferred", "cancelled"],

    # Planning track (agent-jobs)
    "planning":     ["plan-review", "cancelled"],
    "plan-review":  ["in-progress", "planning", "cancelled"],

    # Execution
    "in-progress":  ["review", "running", "blocked", "cancelled"],
    "running":      ["done", "failed", "in-progress"],  # in-progress = retry with remaining attempts

    # Review track (human path)
    "review":       ["in-progress", "testing", "done"],
    "testing":      ["in-progress", "done"],

    # Recovery
    "failed":       ["plan-review", "in-progress"],
    "blocked":      ["in-progress", "cancelled"],
    "deferred":     ["open", "cancelled"],

    # Terminal
    "done":         [],
    "cancelled":    [],
}

# Kind-specific exclusions: (status, kind) → statuses to remove
_KIND_EXCLUSIONS: dict[tuple[str, str], set[str]] = {
    # agent-jobs CAN skip planning if context is sufficient (e.g. research jobs).
    # The executor validates that plan OR context exists before running.
    # Recovery from failure still goes through plan-review for structured jobs.
    ("failed", "agent-job"):    {"in-progress"},

    # tasks cannot enter running state (no execution engine for humans)
    ("in-progress", "task"):    {"running"},
    # tasks don't have plans to revise
    ("failed", "task"):         {"plan-review"},

    # jobs recover via direct retry, not plan-review
    ("failed", "job"):          {"plan-review"},
}


def valid_transitions(status: str, kind: str) -> list[str]:
    """Return allowed next statuses for a given (status, kind) pair.

    Base transitions with kind-specific exclusions applied.
    """
    base = list(_BASE_TRANSITIONS.get(status, []))
    exclusions = _KIND_EXCLUSIONS.get((status, kind), set())
    return [s for s in base if s not in exclusions]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_id() -> str:
    """Generate a unique ID: YYYYMMDD-HHMMSS-xxxxxxxx (8 random hex chars)."""
    now = datetime.now(timezone.utc)
    rnd = uuid.uuid4().hex[:8]
    return now.strftime("%Y%m%d-%H%M%S") + f"-{rnd}"


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:60]


# ---------------------------------------------------------------------------
# Item model
# ---------------------------------------------------------------------------

class Item:
    """A unit of work in nightctl.

    Can be a human task, a machine job, or an agent-job. The kind determines
    which state machine tracks are available and how execution proceeds.
    """

    def __init__(self, data: dict, file_path: Path | None = None):
        self.data = data
        self.file_path = file_path

    # -- Properties (read from self.data) --

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def title(self) -> str:
        return self.data["title"]

    @property
    def kind(self) -> str:
        return self.data.get("kind", "task")

    @property
    def status(self) -> str:
        return self.data.get("status", "open")

    @property
    def priority(self) -> int:
        return self.data.get("priority", 3)

    @property
    def tags(self) -> list:
        return self.data.get("tags", [])

    @property
    def entities(self) -> list:
        return self.data.get("entities", [])

    @property
    def context(self) -> str:
        return self.data.get("context", "")

    @property
    def due(self) -> str | None:
        return self.data.get("due")

    @property
    def blocked_by(self) -> str | None:
        return self.data.get("blocked_by")

    @property
    def command(self) -> str | None:
        return self.data.get("command")

    @property
    def schedule(self) -> str | None:
        return self.data.get("schedule")

    @property
    def window(self) -> str | None:
        return self.data.get("window")

    @property
    def depends_on(self) -> list:
        return self.data.get("depends_on", [])

    @property
    def retries(self) -> int:
        return self.data.get("retries", 2)

    @property
    def retries_remaining(self) -> int:
        return self.data.get("retries_remaining", self.retries)

    @property
    def timeout_secs(self) -> int:
        return self.data.get("timeout_secs", 300)

    @property
    def plan(self) -> str | None:
        return self.data.get("plan")

    @property
    def plan_ref(self) -> str | None:
        return self.data.get("plan_ref")

    @property
    def created(self) -> str:
        return self.data.get("created", "")

    @property
    def modified(self) -> str:
        return self.data.get("modified", "")

    @property
    def created_by(self) -> str:
        return self.data.get("created_by", "agent")

    # -- State machine --

    def transition(self, new_status: str) -> None:
        """Validate and apply a state transition.

        Raises TransitionError if the transition is not allowed for this kind.
        Raises PlanValidationError if a plan gate fails.
        Updates status and modified timestamp.
        """
        allowed = valid_transitions(self.status, self.kind)
        if new_status not in allowed:
            raise TransitionError(self.status, new_status, allowed)

        # Plan validation gates (agent-jobs only)
        # Validate when entering plan-review, or when entering in-progress from
        # planning track OR directly from open (context-only skip).
        # Do NOT validate on retries (running→in-progress) or unblocks (blocked→in-progress).
        if self.kind == "agent-job" and new_status in ("plan-review", "in-progress"):
            if self.status in ("planning", "plan-review", "open"):
                self._validate_plan()

        self.data["status"] = new_status
        self.data["modified"] = _now_iso()

    def _validate_plan(self) -> None:
        """Validate the item's plan. Called at transition gates.

        Agent-jobs need EITHER a structured plan (XML) OR sufficient context.
        Research jobs and simple agent tasks can run on context alone.
        """
        from .plan import validate_plan_xml, validate_plan_ref, PlanValidationError

        if self.plan:
            validate_plan_xml(self.plan)
        elif self.plan_ref:
            base_dir = self.file_path.parent if self.file_path else Path.cwd()
            validate_plan_ref(self.plan_ref, base_dir)
        elif self.context and len(self.context.strip()) >= 50:
            # Context-only mode: sufficient detail can substitute for a plan.
            # 50 chars is a minimal threshold — "research X" is not enough,
            # but a paragraph describing the task is.
            pass
        else:
            raise PlanValidationError(
                ["agent-job requires a plan (inline or plan_ref) or detailed context (50+ chars) before promotion"]
            )

    # -- Execution support --

    def decrement_retries(self) -> int:
        remaining = max(0, self.retries_remaining - 1)
        self.data["retries_remaining"] = remaining
        return remaining

    # -- Persistence --

    def to_yaml(self) -> str:
        return yaml.dump(self.data, default_flow_style=False, sort_keys=False)

    def save(self) -> None:
        """Atomic write: tmp + os.replace.

        Raises RuntimeError if file_path not set (programmer bug).
        Raises SaveError on filesystem failure (runtime condition).
        """
        if not self.file_path:
            raise RuntimeError("No file path set — Item was constructed without a path")

        tmp = self.file_path.with_suffix(".yaml.tmp")
        try:
            tmp.write_text(self.to_yaml())
            os.replace(str(tmp), str(self.file_path))
        except OSError as e:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise SaveError(f"Failed to save {self.file_path.name}: {e}") from e

    def file_hash(self) -> str:
        if not self.file_path or not self.file_path.exists():
            return ""
        return hashlib.sha256(self.file_path.read_bytes()).hexdigest()

    # -- Validation --

    def validate(self) -> None:
        """Structural validation of data fields. Raises ValidationError."""
        if not self.data.get("id"):
            raise ValidationError("id is required")
        if not self.data.get("title"):
            raise ValidationError("title is required")

        kind = self.data.get("kind", "task")
        if kind not in VALID_KINDS:
            raise ValidationError(f"invalid kind: {kind}. Valid: {VALID_KINDS}")

        status = self.data.get("status", "open")
        if status not in VALID_STATUSES:
            raise ValidationError(f"invalid status: {status}. Valid: {VALID_STATUSES}")

        priority = self.data.get("priority", 3)
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise ValidationError(f"priority must be int, got {type(priority).__name__}")

        schedule = self.data.get("schedule")
        if schedule is not None and schedule not in VALID_SCHEDULES:
            raise ValidationError(f"invalid schedule: {schedule}. Valid: {VALID_SCHEDULES}")

        if kind == "job" and not self.data.get("command"):
            raise ValidationError("command is required for kind=job")

    # -- Archive --

    def archive(self, archive_dir: Path) -> None:
        """Move this item's file to the archive directory (atomic)."""
        if not self.file_path:
            raise RuntimeError("No file path set")
        archive_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_dir / self.file_path.name
        os.replace(str(self.file_path), str(dest))
        self.file_path = dest

    # -- Construction --

    @classmethod
    def from_file(cls, path: Path) -> "Item":
        """Load an item from a YAML file. Validates on load."""
        with open(path) as f:
            data = yaml.safe_load(f)
        item = cls(data, file_path=path)
        item.validate()
        return item

    @classmethod
    def create(
        cls,
        items_dir: Path,
        title: str,
        kind: str = "task",
        priority: int = 3,
        tags: list[str] | None = None,
        entities: list[str] | None = None,
        context: str = "",
        due: str | None = None,
        command: str | None = None,
        schedule: str | None = None,
        window: str | None = None,
        depends_on: list[str] | None = None,
        retries: int = 2,
        timeout_secs: int = 300,
        plan: str | None = None,
        plan_ref: str | None = None,
        created_by: str = "agent",
    ) -> "Item":
        """Create a new item. Validates and saves to disk.

        Loose on entry: agent-jobs don't require a plan at creation.
        Strict on promotion: plan required at planning → plan-review gate.
        """
        title = title.strip()
        if not title:
            raise ValidationError("--title is required")
        if kind not in VALID_KINDS:
            raise ValidationError(f"invalid kind: {kind}. Valid: {VALID_KINDS}")
        if kind == "job" and not (command or "").strip():
            raise ValidationError("--command is required for kind=job")
        if schedule is not None and schedule not in VALID_SCHEDULES:
            raise ValidationError(f"invalid schedule: {schedule}. Valid: {VALID_SCHEDULES}")

        # Eager plan validation if provided at creation
        if plan:
            from .plan import validate_plan_xml
            validate_plan_xml(plan)

        item_id = _now_id()
        slug = _slugify(title)
        filename = f"{item_id}-{slug}.yaml"
        file_path = items_dir / filename

        now = _now_iso()
        data = {
            "id": item_id,
            "title": title,
            "kind": kind,
            "status": "open",
            "priority": priority,
            "tags": tags or [],
            "entities": entities or [],
            "context": context or "",
            "due": due,
            "blocked_by": None,
            "command": command,
            "schedule": schedule,
            "window": window,
            "depends_on": depends_on or [],
            "retries": retries,
            "retries_remaining": retries,
            "timeout_secs": timeout_secs,
            "plan": plan,
            "plan_ref": plan_ref,
            "created": now,
            "modified": now,
            "created_by": created_by,
        }

        item = cls(data, file_path=file_path)
        items_dir.mkdir(parents=True, exist_ok=True)
        item.save()
        return item


# ---------------------------------------------------------------------------
# Collection helpers (shared by cli.py and executor.py)
# ---------------------------------------------------------------------------

def load_all_items(items_dir: Path) -> list["Item"]:
    """Load all items from a directory. Skips files that fail validation."""
    import sys
    if not items_dir or not items_dir.exists():
        return []
    items = []
    for f in sorted(items_dir.glob("*.yaml")):
        try:
            items.append(Item.from_file(f))
        except Exception as e:
            print(f"WARN: skipping {f.name}: {e}", file=sys.stderr)
    return items


def find_item(items_dir: Path, item_id: str) -> "Item | None":
    """Find an item by ID. Returns None if not found."""
    for i in load_all_items(items_dir):
        if i.id == item_id:
            return i
    return None
