import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    sessions_dir: str = "./data/agent-sessions"
    log_dirs: list[str] = field(default_factory=lambda: ["./groups/*/logs/"])
    spin_threshold_secs: int = 600
    error_streak_threshold: int = 3


def load(path: str = "") -> Config:
    if not path:
        path = os.environ.get("AGENTCTL_CONFIG", "agentctl.yaml")

    p = Path(path)
    if not p.exists():
        return Config()

    raw = yaml.safe_load(p.read_text())
    if not raw:
        return Config()

    return Config(
        sessions_dir=raw.get("sessions_dir", "./data/agent-sessions"),
        log_dirs=raw.get("log_dirs", ["./groups/*/logs/"]),
        spin_threshold_secs=raw.get("spin_threshold_secs", 600),
        error_streak_threshold=raw.get("error_streak_threshold", 3),
    )
