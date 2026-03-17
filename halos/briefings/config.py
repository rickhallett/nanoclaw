"""Configuration for briefings module."""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULTS = {
    "project_root": ".",
    "memctl_config": "./memctl.yaml",
    "nightctl_config": "./nightctl.yaml",
    "todoctl_config": "./todoctl.yaml",
    "logctl_config": "./logctl.yaml",
    "ipc_dir": "./data/ipc",
    "ipc_group": "telegram_main",
    "chat_jid": "",
    "db_path": "./store/messages.db",
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
}


@dataclass
class Config:
    project_root: Path
    memctl_config: Path
    nightctl_config: Path
    todoctl_config: Path
    logctl_config: Path
    ipc_dir: Path
    ipc_group: str
    chat_jid: str
    db_path: Path
    model: str
    max_tokens: int

    def _resolve(self, base: Path, p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else (base / path).resolve()


def load_config(config_path: str | None = None) -> Config:
    if config_path:
        path = Path(config_path).resolve()
    else:
        env_path = os.environ.get("BRIEFINGS_CONFIG")
        if env_path:
            path = Path(env_path).resolve()
        else:
            path = Path("briefings.yaml").resolve()

    raw: dict = {}
    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}

    data = {**DEFAULTS, **raw}
    base = path.parent if path.exists() else Path.cwd()
    project_root = Path(data["project_root"])
    if not project_root.is_absolute():
        project_root = (base / project_root).resolve()

    def resolve(p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else (project_root / pp).resolve()

    # Resolve chat_jid from config or DB
    chat_jid = data.get("chat_jid", "")
    if not chat_jid:
        chat_jid = _resolve_main_jid(resolve(data["db_path"]))

    return Config(
        project_root=project_root,
        memctl_config=resolve(data["memctl_config"]),
        nightctl_config=resolve(data["nightctl_config"]),
        todoctl_config=resolve(data["todoctl_config"]),
        logctl_config=resolve(data["logctl_config"]),
        ipc_dir=resolve(data["ipc_dir"]),
        ipc_group=data["ipc_group"],
        chat_jid=chat_jid,
        db_path=resolve(data["db_path"]),
        model=data["model"],
        max_tokens=int(data["max_tokens"]),
    )


def _resolve_main_jid(db_path: Path) -> str:
    """Look up the main group's JID from the NanoClaw database."""
    if not db_path.exists():
        return ""
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT jid FROM registered_groups WHERE is_main = 1 LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""
