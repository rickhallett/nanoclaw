import os
from pathlib import Path

import yaml


DEFAULTS = {
    "reports_dir": "./reports",
    "memctl_config": "./memctl.yaml",
    "nightctl_config": "./nightctl.yaml",
    "todoctl_config": "./todoctl.yaml",
}


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
    def reports_dir(self) -> Path:
        return self._resolve(self._data["reports_dir"])

    @property
    def memctl_config(self) -> Path:
        return self._resolve(self._data["memctl_config"])

    @property
    def nightctl_config(self) -> Path:
        return self._resolve(self._data["nightctl_config"])

    @property
    def todoctl_config(self) -> Path:
        return self._resolve(self._data["todoctl_config"])


def load_config(config_path: str = None) -> Config:
    if config_path:
        path = Path(config_path).resolve()
    else:
        env_path = os.environ.get("REPORTCTL_CONFIG")
        if env_path:
            path = Path(env_path).resolve()
        else:
            path = Path("reportctl.yaml").resolve()

    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    data = {**DEFAULTS, **raw}
    return Config(data, path)
