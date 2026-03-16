import hashlib
import re
import uuid
try:
    import yaml
except ImportError:
    from nightctl_lib import yaml_shim as yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


VALID_STATUSES = ["pending", "claimed", "running", "done", "failed", "cancelled"]
VALID_SCHEDULES = ["overnight", "immediate", "once"]


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:60]


def _now_id() -> str:
    """Generate a unique ID: YYYYMMDD-HHMMSS-xxxxxxxx (8 random hex chars)."""
    now = datetime.now(timezone.utc)
    rnd = uuid.uuid4().hex[:8]
    return now.strftime("%Y%m%d-%H%M%S") + f"-{rnd}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ValidationError(Exception):
    pass


class Job:
    def __init__(self, data: dict, file_path: Optional[Path] = None):
        self.data = data
        self.file_path = file_path

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def title(self) -> str:
        return self.data["title"]

    @property
    def command(self) -> str:
        return self.data["command"]

    @property
    def status(self) -> str:
        return self.data["status"]

    @property
    def priority(self) -> int:
        return self.data.get("priority", 5)

    @property
    def schedule(self) -> str:
        return self.data.get("schedule", "overnight")

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
    def tags(self) -> list:
        return self.data.get("tags", [])

    @property
    def created(self) -> str:
        return self.data.get("created", "")

    def file_hash(self) -> str:
        if not self.file_path or not self.file_path.exists():
            return ""
        content = self.file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def set_status(self, status: str):
        if status not in VALID_STATUSES:
            raise ValidationError(f"Invalid status: {status}")
        self.data["status"] = status

    def decrement_retries(self):
        remaining = self.retries_remaining - 1
        self.data["retries_remaining"] = remaining
        return remaining

    def to_yaml(self) -> str:
        return yaml.dump(self.data, default_flow_style=False, sort_keys=False)

    def save(self):
        if not self.file_path:
            raise RuntimeError("No file path set")
        self.file_path.write_text(self.to_yaml())

    @classmethod
    def from_file(cls, path: Path) -> "Job":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(data, file_path=path)

    @classmethod
    def create(cls, jobs_dir: Path, cfg_job: dict, **kwargs) -> "Job":
        title = kwargs.get("title", "").strip()
        command = kwargs.get("command", "").strip()

        if not title:
            raise ValidationError("--title is required")
        if not command:
            raise ValidationError("--command is required")

        schedule = kwargs.get("schedule", cfg_job.get("default_schedule", "overnight"))
        if schedule not in VALID_SCHEDULES:
            raise ValidationError(f"Invalid schedule '{schedule}'. Valid: {VALID_SCHEDULES}")

        tags = kwargs.get("tags", [])
        valid_tags = cfg_job.get("valid_tags", [])
        warnings = []
        for tag in tags:
            if tag not in valid_tags:
                warnings.append(f"unknown tag '{tag}' — not in controlled vocabulary")

        job_id = _now_id()
        slug = _slugify(title)
        filename = f"{job_id}-{slug}.yaml"
        file_path = jobs_dir / filename

        retries = kwargs.get("retries", cfg_job.get("default_retries", 2))
        timeout_secs = kwargs.get("timeout_secs", cfg_job.get("default_timeout_secs", 300))
        priority = kwargs.get("priority", 5)
        depends_on = kwargs.get("depends_on", [])
        entities = kwargs.get("entities", [])
        window = kwargs.get("window", None)

        data = {
            "id": job_id,
            "title": title,
            "command": command,
            "schedule": schedule,
            "priority": priority,
            "depends_on": depends_on,
            "retries": retries,
            "retries_remaining": retries,
            "timeout_secs": timeout_secs,
            "tags": tags,
            "entities": entities,
            "created": _now_iso(),
            "created_by": "agent",
            "status": "pending",
        }

        if window:
            data["window"] = window

        job = cls(data, file_path=file_path)
        job.save()
        return job, warnings
