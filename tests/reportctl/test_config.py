"""Tests for reportctl config loading."""
import pytest
from pathlib import Path

from halos.reportctl.config import load_config, DEFAULTS


@pytest.fixture
def config_file(tmp_path):
    cfg = tmp_path / "reportctl.yaml"
    cfg.write_text(
        "reports_dir: ./my-reports\n"
        "memctl_config: ./custom-memctl.yaml\n"
    )
    return cfg


@pytest.fixture
def minimal_config(tmp_path):
    cfg = tmp_path / "reportctl.yaml"
    cfg.write_text("{}\n")
    return cfg


def test_load_config(config_file):
    cfg = load_config(str(config_file))
    assert cfg.reports_dir == (config_file.parent / "my-reports").resolve()
    assert cfg.memctl_config == (config_file.parent / "custom-memctl.yaml").resolve()
    # Defaults for unspecified fields
    assert cfg.nightctl_config == (config_file.parent / "./nightctl.yaml").resolve()
    assert cfg.todoctl_config == (config_file.parent / "./todoctl.yaml").resolve()


def test_load_config_defaults(minimal_config):
    cfg = load_config(str(minimal_config))
    assert cfg.reports_dir == (minimal_config.parent / "./reports").resolve()
    assert cfg.memctl_config == (minimal_config.parent / "./memctl.yaml").resolve()


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/reportctl.yaml")


def test_load_config_env_var(tmp_path, monkeypatch):
    cfg = tmp_path / "env-reportctl.yaml"
    cfg.write_text("reports_dir: ./env-reports\n")
    monkeypatch.setenv("REPORTCTL_CONFIG", str(cfg))
    monkeypatch.chdir(tmp_path)
    result = load_config()
    assert result.reports_dir == (tmp_path / "env-reports").resolve()


def test_config_absolute_paths(tmp_path):
    cfg_file = tmp_path / "reportctl.yaml"
    cfg_file.write_text(f"reports_dir: /tmp/absolute-reports\n")
    cfg = load_config(str(cfg_file))
    assert cfg.reports_dir == Path("/tmp/absolute-reports")
