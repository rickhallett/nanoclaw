import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    log_dir: str = "./logs"
    data_dir: str = "./data"
    sources: dict[str, str] = field(default_factory=lambda: {
        "nanoclaw": "./logs/nanoclaw.log",
        "nanoclaw_error": "./logs/nanoclaw.error.log",
    })
    format: str = "pino"  # pino | jsonl | plain
    tail_lines: int = 50


def load(path: str = "") -> Config:
    if not path:
        path = os.environ.get("LOGCTL_CONFIG", "logctl.yaml")

    p = Path(path)
    if not p.exists():
        # Unlike memctl, missing config is not fatal — use defaults
        return Config()

    raw = yaml.safe_load(p.read_text())
    if not raw:
        return Config()

    return Config(
        log_dir=raw.get("log_dir", "./logs"),
        data_dir=raw.get("data_dir", "./data"),
        sources=raw.get("sources", {
            "nanoclaw": "./logs/nanoclaw.log",
            "nanoclaw_error": "./logs/nanoclaw.error.log",
        }),
        format=raw.get("format", "pino"),
        tail_lines=raw.get("tail_lines", 50),
    )
