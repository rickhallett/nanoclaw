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
    # BATHW telemetry fields (populated from api-usage.jsonl)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_cost_usd: float = 0.0

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
        "model": s.model,
        "input_tokens": s.input_tokens,
        "output_tokens": s.output_tokens,
        "cache_read_tokens": s.cache_read_tokens,
        "cache_write_tokens": s.cache_write_tokens,
        "total_cost_usd": s.total_cost_usd,
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
        model=str(raw.get("model", "")),
        input_tokens=int(raw.get("input_tokens", 0)),
        output_tokens=int(raw.get("output_tokens", 0)),
        cache_read_tokens=int(raw.get("cache_read_tokens", 0)),
        cache_write_tokens=int(raw.get("cache_write_tokens", 0)),
        total_cost_usd=float(raw.get("total_cost_usd", 0.0)),
    )


def filename(session: Session) -> str:
    """Generate a filename for a session record."""
    return f"{session.id}.yaml"
