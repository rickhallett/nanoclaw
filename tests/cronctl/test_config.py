"""Tests for halos.cronctl.config — load, defaults."""
from pathlib import Path

import pytest
import yaml

from halos.cronctl.config import Config, DEFAULTS, load_config


class TestLoadValid:
    def test_full_config(self, tmp_path):
        cfg_file = tmp_path / "cronctl.yaml"
        cfg_file.write_text(yaml.dump({
            "cron_dir": "./custom-cron",
            "jobs_dir": "./custom-cron/jobs",
            "output_file": "./custom-cron/out.txt",
            "log_dir": "./logs/custom",
            "install_method": "crontab",
        }))
        cfg = load_config(str(cfg_file))
        assert cfg.install_method == "crontab"
        assert cfg.cron_dir.name == "custom-cron"

    def test_defaults_applied(self, tmp_path):
        cfg_file = tmp_path / "cronctl.yaml"
        cfg_file.write_text("")  # empty config
        cfg = load_config(str(cfg_file))
        assert cfg.install_method == "file"
        # jobs_dir should resolve relative to config dir
        assert "jobs" in str(cfg.jobs_dir)

    def test_partial_override(self, tmp_path):
        cfg_file = tmp_path / "cronctl.yaml"
        cfg_file.write_text("install_method: crontab\n")
        cfg = load_config(str(cfg_file))
        assert cfg.install_method == "crontab"
        # Other defaults preserved
        assert "cron" in str(cfg.cron_dir)


class TestLoadMissing:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Config not found"):
            load_config(str(tmp_path / "nope.yaml"))


class TestEnsureDirs:
    def test_dirs_created_on_load(self, tmp_path):
        cfg_file = tmp_path / "cronctl.yaml"
        cfg_file.write_text("")
        cfg = load_config(str(cfg_file))
        assert cfg.jobs_dir.exists()
        assert cfg.log_dir.exists()
