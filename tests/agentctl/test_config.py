"""Tests for config loading."""

from pathlib import Path

from halos.agentctl.config import Config, load


def test_defaults():
    cfg = Config()
    assert cfg.sessions_dir == "./data/agent-sessions"
    assert cfg.spin_threshold_secs == 600
    assert cfg.error_streak_threshold == 3
    assert len(cfg.log_dirs) == 1


def test_load_missing_file_returns_defaults():
    cfg = load("/nonexistent/agentctl.yaml")
    assert cfg.sessions_dir == "./data/agent-sessions"
    assert cfg.spin_threshold_secs == 600


def test_load_valid_config(tmp_path):
    config_file = tmp_path / "agentctl.yaml"
    config_file.write_text(
        "sessions_dir: /tmp/sessions\n"
        "spin_threshold_secs: 300\n"
        "error_streak_threshold: 5\n"
        "log_dirs:\n"
        "  - /var/log/containers/\n"
    )
    cfg = load(str(config_file))
    assert cfg.sessions_dir == "/tmp/sessions"
    assert cfg.spin_threshold_secs == 300
    assert cfg.error_streak_threshold == 5
    assert cfg.log_dirs == ["/var/log/containers/"]


def test_load_empty_config(tmp_path):
    config_file = tmp_path / "agentctl.yaml"
    config_file.write_text("")
    cfg = load(str(config_file))
    # Should return defaults for empty file
    assert cfg.sessions_dir == "./data/agent-sessions"


def test_load_partial_config(tmp_path):
    config_file = tmp_path / "agentctl.yaml"
    config_file.write_text("spin_threshold_secs: 120\n")
    cfg = load(str(config_file))
    assert cfg.spin_threshold_secs == 120
    # Other fields should be defaults
    assert cfg.sessions_dir == "./data/agent-sessions"
    assert cfg.error_streak_threshold == 3
