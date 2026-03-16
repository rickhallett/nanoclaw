"""Session record model: parse, validate, marshal."""

from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class Session:
    id: str
    group: str
    started: str
    finished: str
    duration_secs: int
    exit_code: int
    prompt_length: int
    result_length: int
    status: str  # success | error | timeout
    source: str  # container | scheduled-task

    def validate(self) -> list[str]:
        errors = []
        if not self.id:
            errors.append("id is required")
        if not self.group:
            errors.append("group is required")
        if self.status not in ("success", "error", "timeout"):
            errors.append(f"invalid status: {self.status}")
        if self.source not in ("container", "scheduled-task"):
            errors.append(f"invalid source: {self.source}")
        if self.duration_secs < 0:
            errors.append("duration_secs must be non-negative")
        return errors


def marshal(s: Session) -> str:
    """Serialize a session to YAML."""
    data = {
        "id": s.id,
        "group": s.group,
        "started": s.started,
        "finished": s.finished,
        "duration_secs": s.duration_secs,
        "exit_code": s.exit_code,
        "prompt_length": s.prompt_length,
        "result_length": s.result_length,
        "status": s.status,
        "source": s.source,
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def parse(text: str) -> Session:
    """Deserialize a session from YAML."""
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("session YAML must be a mapping")
    return Session(
        id=str(raw.get("id", "")),
        group=str(raw.get("group", "")),
        started=str(raw.get("started", "")),
        finished=str(raw.get("finished", "")),
        duration_secs=int(raw.get("duration_secs", 0)),
        exit_code=int(raw.get("exit_code", 0)),
        prompt_length=int(raw.get("prompt_length", 0)),
        result_length=int(raw.get("result_length", 0)),
        status=str(raw.get("status", "error")),
        source=str(raw.get("source", "container")),
    )


def filename(session: Session) -> str:
    """Generate a filename for a session record."""
    return f"{session.id}.yaml"
