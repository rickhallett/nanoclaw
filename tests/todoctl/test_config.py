"""Tests for halos.todoctl.config — load, defaults."""
from pathlib import Path

import pytest
import yaml

from halos.todoctl.config import Config, DEFAULTS, load_config


class TestLoadValid:
    def test_full_config(self, tmp_path):
        cfg_file = tmp_path / "todoctl.yaml"
        cfg_file.write_text(yaml.dump({
            "backlog_dir": "./custom-backlog",
            "items_dir": "./custom-backlog/items",
            "valid_priorities": [1, 2, 3],
            "valid_tags": ["infra", "dev"],
        }))
        cfg = load_config(str(cfg_file))
        assert cfg.valid_priorities == [1, 2, 3]
        assert cfg.valid_tags == ["infra", "dev"]
        assert "custom-backlog" in str(cfg.backlog_dir)

    def test_defaults_applied(self, tmp_path):
        cfg_file = tmp_path / "todoctl.yaml"
        cfg_file.write_text("")
        cfg = load_config(str(cfg_file))
        assert cfg.valid_priorities == [1, 2, 3, 4]
        assert cfg.valid_tags == []
        assert "items" in str(cfg.items_dir)

    def test_partial_override(self, tmp_path):
        cfg_file = tmp_path / "todoctl.yaml"
        cfg_file.write_text("valid_tags: [ops]\n")
        cfg = load_config(str(cfg_file))
        assert cfg.valid_tags == ["ops"]
        # Other defaults preserved
        assert cfg.valid_priorities == [1, 2, 3, 4]


class TestLoadMissing:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Config not found"):
            load_config(str(tmp_path / "nope.yaml"))


class TestEnsureDirs:
    def test_items_dir_created_on_load(self, tmp_path):
        cfg_file = tmp_path / "todoctl.yaml"
        cfg_file.write_text("")
        cfg = load_config(str(cfg_file))
        assert cfg.items_dir.exists()
