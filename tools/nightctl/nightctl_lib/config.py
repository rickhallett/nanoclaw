import os
try:
    import yaml
except ImportError:
    from nightctl_lib import yaml_shim as yaml
from pathlib import Path


DEFAULTS = {
    "queue_dir": "./queue",
    "manifest_file": "./queue/MANIFEST.yaml",
    "archive_dir": "./queue/archive",
    "runs_dir": "./queue/runs",
    "execution": {
        "mode": "serial",
        "max_workers": 1,
        "overnight_window": "02:00-05:00",
        "timezone": "Europe/London",
    },
    "job": {
        "default_retries": 2,
        "default_timeout_secs": 300,
        "default_schedule": "overnight",
        "valid_schedules": ["overnight", "immediate", "once"],
        "valid_tags": ["maintenance", "memctl", "data", "sync", "report", "cleanup", "backup", "infra"],
    },
    "notify": {
        "on_failure": True,
        "on_success": False,
        "channel": "main",
    },
    "manifest": {
        "hash_algorithm": "sha256",
    },
    "archive": {
        "retention_days": 30,
        "dry_run": True,
    },
}


def _deep_merge(base, override):
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class Config:
    def __init__(self, data: dict, config_path: Path):
        self._data = data
        self.config_path = config_path
        self.base_dir = config_path.parent

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute():
            return p
        return (self.base_dir / p).resolve()

    @property
    def queue_dir(self) -> Path:
        return self._resolve(self._data["queue_dir"])

    @property
    def jobs_dir(self) -> Path:
        return self.queue_dir / "jobs"

    @property
    def manifest_file(self) -> Path:
        return self._resolve(self._data["manifest_file"])

    @property
    def archive_dir(self) -> Path:
        return self._resolve(self._data["archive_dir"])

    @property
    def runs_dir(self) -> Path:
        return self._resolve(self._data["runs_dir"])

    @property
    def execution(self) -> dict:
        return self._data["execution"]

    @property
    def job(self) -> dict:
        return self._data["job"]

    @property
    def notify(self) -> dict:
        return self._data["notify"]

    @property
    def manifest(self) -> dict:
        return self._data["manifest"]

    @property
    def archive(self) -> dict:
        return self._data["archive"]

    def ensure_dirs(self):
        for d in [self.jobs_dir, self.archive_dir, self.runs_dir]:
            d.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str = None) -> Config:
    if config_path:
        path = Path(config_path).resolve()
    else:
        env_path = os.environ.get("NIGHTCTL_CONFIG")
        if env_path:
            path = Path(env_path).resolve()
        else:
            path = Path("nightctl.yaml").resolve()

    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    data = _deep_merge(DEFAULTS, raw)
    cfg = Config(data, path)
    cfg.ensure_dirs()
    return cfg
