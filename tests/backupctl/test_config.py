"""Unit tests for backupctl config loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from halos.backupctl.config import (
    BackupConfig,
    BackupTarget,
    RetentionPolicy,
    load_config,
    resolve_paths,
    _parse_retention,
    _parse_target,
)


class TestDefaultConfig:
    """Tests for default configuration when no backupctl.yaml exists."""

    def test_returns_config_without_yaml(self, tmp_path):
        """Default config is returned when no config file exists."""
        fake_yaml = tmp_path / "backupctl.yaml"
        cfg = load_config(config_path=fake_yaml)
        assert isinstance(cfg, BackupConfig)

    def test_default_targets_present(self, tmp_path):
        fake_yaml = tmp_path / "backupctl.yaml"
        cfg = load_config(config_path=fake_yaml)
        assert "store" in cfg.targets
        assert "memory" in cfg.targets
        assert "queue" in cfg.targets
        assert "config" in cfg.targets

    def test_default_store_paths(self, tmp_path):
        fake_yaml = tmp_path / "backupctl.yaml"
        cfg = load_config(config_path=fake_yaml)
        assert cfg.targets["store"].paths == ["store/"]

    def test_default_memory_paths(self, tmp_path):
        fake_yaml = tmp_path / "backupctl.yaml"
        cfg = load_config(config_path=fake_yaml)
        assert cfg.targets["memory"].paths == ["memory/"]

    def test_default_repository_is_home_based(self, tmp_path):
        fake_yaml = tmp_path / "backupctl.yaml"
        cfg = load_config(config_path=fake_yaml)
        assert "backups" in str(cfg.repository)
        assert "nanoclaw" in str(cfg.repository)

    def test_default_retention_daily(self, tmp_path):
        fake_yaml = tmp_path / "backupctl.yaml"
        cfg = load_config(config_path=fake_yaml)
        assert cfg.targets["store"].retain.daily == 30

    def test_default_retention_weekly(self, tmp_path):
        fake_yaml = tmp_path / "backupctl.yaml"
        cfg = load_config(config_path=fake_yaml)
        assert cfg.targets["store"].retain.weekly == 12


class TestCustomConfig:
    """Tests for loading a custom backupctl.yaml."""

    def test_loads_custom_repository(self, tmp_path):
        config = {
            "repository": "/tmp/custom-backups",
            "targets": {
                "mydata": {
                    "paths": ["data/"],
                    "retain": {"daily": 7},
                },
            },
        }
        cfg_file = tmp_path / "backupctl.yaml"
        cfg_file.write_text(yaml.dump(config))

        cfg = load_config(config_path=cfg_file)
        assert str(cfg.repository) == "/tmp/custom-backups"

    def test_loads_custom_targets(self, tmp_path):
        config = {
            "repository": "/tmp/backups",
            "targets": {
                "mydata": {
                    "paths": ["data/", "extra/"],
                    "retain": {"daily": 14, "weekly": 4},
                },
            },
        }
        cfg_file = tmp_path / "backupctl.yaml"
        cfg_file.write_text(yaml.dump(config))

        cfg = load_config(config_path=cfg_file)
        assert "mydata" in cfg.targets
        assert cfg.targets["mydata"].paths == ["data/", "extra/"]
        assert cfg.targets["mydata"].retain.daily == 14
        assert cfg.targets["mydata"].retain.weekly == 4

    def test_loads_password_file(self, tmp_path):
        config = {
            "repository": "/tmp/backups",
            "password_file": "/home/user/.backup-pass",
            "targets": {"store": {"paths": ["store/"]}},
        }
        cfg_file = tmp_path / "backupctl.yaml"
        cfg_file.write_text(yaml.dump(config))

        cfg = load_config(config_path=cfg_file)
        assert cfg.password_file == Path("/home/user/.backup-pass")

    def test_schedule_preserved(self, tmp_path):
        config = {
            "repository": "/tmp/backups",
            "targets": {
                "store": {
                    "paths": ["store/"],
                    "schedule": "0 */6 * * *",
                },
            },
        }
        cfg_file = tmp_path / "backupctl.yaml"
        cfg_file.write_text(yaml.dump(config))

        cfg = load_config(config_path=cfg_file)
        assert cfg.targets["store"].schedule == "0 */6 * * *"

    def test_empty_targets_uses_defaults(self, tmp_path):
        config = {"repository": "/tmp/backups", "targets": {}}
        cfg_file = tmp_path / "backupctl.yaml"
        cfg_file.write_text(yaml.dump(config))

        cfg = load_config(config_path=cfg_file)
        assert "store" in cfg.targets  # defaults

    def test_string_path_converted_to_list(self, tmp_path):
        """A string path should be wrapped in a list."""
        config = {
            "repository": "/tmp/backups",
            "targets": {
                "single": {"paths": "just-one-dir/"},
            },
        }
        cfg_file = tmp_path / "backupctl.yaml"
        cfg_file.write_text(yaml.dump(config))

        cfg = load_config(config_path=cfg_file)
        assert cfg.targets["single"].paths == ["just-one-dir/"]


class TestPathResolution:
    """Tests for resolve_paths."""

    def test_existing_directory_resolved(self, tmp_path):
        (tmp_path / "data").mkdir()
        target = BackupTarget(name="test", paths=["data"])
        resolved = resolve_paths(target, tmp_path)
        assert len(resolved) == 1
        assert resolved[0] == (tmp_path / "data").resolve()

    def test_missing_path_excluded(self, tmp_path):
        target = BackupTarget(name="test", paths=["nonexistent/"])
        resolved = resolve_paths(target, tmp_path)
        assert len(resolved) == 0

    def test_file_path_resolved(self, tmp_path):
        (tmp_path / ".env").write_text("SECRET=x")
        target = BackupTarget(name="test", paths=[".env"])
        resolved = resolve_paths(target, tmp_path)
        assert len(resolved) == 1

    def test_mixed_existing_and_missing(self, tmp_path):
        (tmp_path / "real").mkdir()
        target = BackupTarget(name="test", paths=["real", "fake"])
        resolved = resolve_paths(target, tmp_path)
        assert len(resolved) == 1


class TestRetentionParsing:
    """Tests for retention policy parsing."""

    def test_all_fields(self):
        r = _parse_retention({"hourly": 24, "daily": 30, "weekly": 12, "monthly": 6})
        assert r.hourly == 24
        assert r.daily == 30
        assert r.weekly == 12
        assert r.monthly == 6

    def test_partial_fields_use_defaults(self):
        r = _parse_retention({"daily": 7})
        assert r.daily == 7
        assert r.weekly == 12  # default
        assert r.hourly == 0  # default

    def test_empty_dict(self):
        r = _parse_retention({})
        assert r.daily == 30  # default
        assert r.weekly == 12  # default
