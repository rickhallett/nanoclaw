"""Configuration loader for backupctl.

Loads from backupctl.yaml at repo root. Falls back to sensible defaults
if the config file doesn't exist.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class RetentionPolicy:
    """How many snapshots to keep per time bucket."""
    hourly: int = 0
    daily: int = 30
    weekly: int = 12
    monthly: int = 0


@dataclass
class BackupTarget:
    """A named backup target with paths and retention policy."""
    name: str
    paths: list[str]
    retain: RetentionPolicy = field(default_factory=RetentionPolicy)
    schedule: str = ""  # cron expression (informational)


@dataclass
class BackupConfig:
    """Top-level backup configuration."""
    repository: Path
    password_file: Optional[Path] = None
    targets: dict[str, BackupTarget] = field(default_factory=dict)
    repo_root: Path = field(default_factory=lambda: Path.cwd())


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (where pyproject.toml lives)."""
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "pyproject.toml").is_file():
            return ancestor
    return Path.cwd()


def _default_targets() -> dict[str, BackupTarget]:
    """Sensible defaults when no config file exists."""
    return {
        "store": BackupTarget(
            name="store",
            paths=["store/"],
            retain=RetentionPolicy(daily=30, weekly=12),
        ),
        "memory": BackupTarget(
            name="memory",
            paths=["memory/"],
            retain=RetentionPolicy(daily=30, weekly=12),
        ),
        "queue": BackupTarget(
            name="queue",
            paths=["queue/items/"],
            retain=RetentionPolicy(daily=30),
        ),
        "config": BackupTarget(
            name="config",
            paths=[".env", "memctl.yaml", "cronctl.yaml"],
            retain=RetentionPolicy(weekly=12),
        ),
    }


def _default_repository() -> Path:
    """Default backup repository path."""
    return Path.home() / "backups" / "nanoclaw"


def _parse_retention(raw: dict) -> RetentionPolicy:
    """Parse a retention dict from YAML."""
    return RetentionPolicy(
        hourly=raw.get("hourly", 0),
        daily=raw.get("daily", 30),
        weekly=raw.get("weekly", 12),
        monthly=raw.get("monthly", 0),
    )


def _parse_target(name: str, raw: dict) -> BackupTarget:
    """Parse a single target definition from YAML."""
    paths = raw.get("paths", [])
    if isinstance(paths, str):
        paths = [paths]
    retain_raw = raw.get("retain", {})
    retain = _parse_retention(retain_raw) if retain_raw else RetentionPolicy()
    schedule = raw.get("schedule", "")
    return BackupTarget(name=name, paths=paths, retain=retain, schedule=schedule)


def load_config(config_path: Optional[Path] = None) -> BackupConfig:
    """Load backup configuration.

    Args:
        config_path: Explicit path to backupctl.yaml. If None, looks at repo root.

    Returns:
        BackupConfig with targets, repository path, and repo root.
    """
    repo_root = _find_repo_root()

    if config_path is None:
        config_path = repo_root / "backupctl.yaml"

    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

        repository = Path(raw.get("repository", str(_default_repository())))
        password_file = None
        if raw.get("password_file"):
            password_file = Path(raw["password_file"])

        targets: dict[str, BackupTarget] = {}
        for name, target_raw in raw.get("targets", {}).items():
            if not isinstance(target_raw, dict):
                continue
            targets[name] = _parse_target(name, target_raw)

        if not targets:
            targets = _default_targets()

        return BackupConfig(
            repository=repository,
            password_file=password_file,
            targets=targets,
            repo_root=repo_root,
        )

    # No config file — use defaults
    return BackupConfig(
        repository=_default_repository(),
        targets=_default_targets(),
        repo_root=repo_root,
    )


def resolve_paths(target: BackupTarget, repo_root: Path) -> list[Path]:
    """Resolve target paths relative to repo root. Returns only paths that exist."""
    resolved = []
    for p in target.paths:
        full = (repo_root / p).resolve()
        if full.exists():
            resolved.append(full)
    return resolved
