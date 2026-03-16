"""Tests for halos.memctl.config — load, defaults, missing file."""
import os
from pathlib import Path

import pytest

from halos.memctl.config import Config, IndexConfig, NoteConfig, PruneConfig, load


# ---------------------------------------------------------------------------
# load() — valid config
# ---------------------------------------------------------------------------

class TestLoadValid:
    def test_full_config(self, tmp_path):
        cfg_file = tmp_path / "memctl.yaml"
        cfg_file.write_text("""\
memory_dir: ./mem
index_file: ./mem/IDX.md
archive_dir: ./mem/arch
backlink_dir: ./mem/bl
note:
  tags: [ops, dev]
  valid_types: [decision, fact]
  valid_confidence: [high, low]
index:
  max_summary_chars: 200
  hash_algorithm: sha256
prune:
  half_life_days: 60
  min_score: 0.2
  min_backlinks_to_exempt: 2
  dry_run: false
  tombstone_retention_days: 30
""")
        cfg = load(str(cfg_file))
        assert cfg.memory_dir == "./mem"
        assert cfg.index_file == "./mem/IDX.md"
        assert cfg.archive_dir == "./mem/arch"
        assert cfg.backlink_dir == "./mem/bl"
        assert cfg.note.tags == ["ops", "dev"]
        assert cfg.note.valid_types == ["decision", "fact"]
        assert cfg.note.valid_confidence == ["high", "low"]
        assert cfg.index.max_summary_chars == 200
        assert cfg.prune.half_life_days == 60
        assert cfg.prune.dry_run is False

    def test_empty_yaml_returns_defaults(self, tmp_path):
        cfg_file = tmp_path / "memctl.yaml"
        cfg_file.write_text("")
        cfg = load(str(cfg_file))
        assert cfg.memory_dir == "./memory"
        assert cfg.note.valid_types == ["decision", "fact", "reference", "project", "person", "event"]
        assert cfg.note.valid_confidence == ["high", "medium", "low"]
        assert cfg.index.max_summary_chars == 120
        assert cfg.prune.half_life_days == 30


# ---------------------------------------------------------------------------
# load() — missing config
# ---------------------------------------------------------------------------

class TestLoadMissing:
    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit, match="config not found"):
            load(str(tmp_path / "nonexistent.yaml"))


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_archive_dir_defaults_from_memory_dir(self):
        cfg = Config(memory_dir="/data/mem")
        assert cfg.archive_dir == "/data/mem/archive"

    def test_backlink_dir_defaults_from_memory_dir(self):
        cfg = Config(memory_dir="/data/mem")
        assert cfg.backlink_dir == "/data/mem/backlinks"

    def test_explicit_archive_dir_not_overridden(self):
        cfg = Config(memory_dir="/data/mem", archive_dir="/custom/arch")
        assert cfg.archive_dir == "/custom/arch"

    def test_fields_missing_in_yaml_get_defaults(self, tmp_path):
        cfg_file = tmp_path / "memctl.yaml"
        cfg_file.write_text("memory_dir: ./custom\n")
        cfg = load(str(cfg_file))
        assert cfg.memory_dir == "./custom"
        # Everything else should be default
        assert cfg.index.max_summary_chars == 120
        assert cfg.prune.min_score == 0.15
