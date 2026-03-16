"""Tests for spinning-to-infinity detection and alert logic."""

from halos.agentctl.alerts import detect_long_sessions, detect_error_streaks, check_alerts
from halos.agentctl.config import Config
from halos.agentctl.session import Session, marshal

from pathlib import Path
import pytest


def _session(id: str, group: str = "test_group", duration: int = 60,
             status: str = "success", result_length: int = 100,
             started: str = "2026-03-16T09:00:00+00:00") -> Session:
    return Session(
        id=id, group=group, started=started,
        finished="2026-03-16T09:01:00+00:00",
        duration_secs=duration, exit_code=0 if status == "success" else 1,
        prompt_length=100, result_length=result_length,
        status=status, source="container",
    )


def test_detect_long_sessions_finds_spinners():
    sessions = [
        _session("s1", duration=60, result_length=100),
        _session("s2", duration=700, result_length=0),   # spinner
        _session("s3", duration=1200, result_length=0),  # spinner
        _session("s4", duration=800, result_length=50),   # long but has result
    ]
    alerts = detect_long_sessions(sessions, threshold_secs=600)
    assert len(alerts) == 2
    assert {a.id for a in alerts} == {"s2", "s3"}


def test_detect_long_sessions_none_found():
    sessions = [
        _session("s1", duration=60),
        _session("s2", duration=300),
    ]
    alerts = detect_long_sessions(sessions, threshold_secs=600)
    assert len(alerts) == 0


def test_detect_error_streaks():
    sessions = [
        _session("s1", status="success", started="2026-03-16T09:00:00+00:00"),
        _session("s2", status="error", started="2026-03-16T09:01:00+00:00"),
        _session("s3", status="error", started="2026-03-16T09:02:00+00:00"),
        _session("s4", status="error", started="2026-03-16T09:03:00+00:00"),
    ]
    streaks = detect_error_streaks(sessions, streak_threshold=3)
    assert "test_group" in streaks
    assert len(streaks["test_group"]) == 3


def test_detect_error_streaks_broken_by_success():
    sessions = [
        _session("s1", status="error", started="2026-03-16T09:00:00+00:00"),
        _session("s2", status="error", started="2026-03-16T09:01:00+00:00"),
        _session("s3", status="success", started="2026-03-16T09:02:00+00:00"),
        _session("s4", status="error", started="2026-03-16T09:03:00+00:00"),
    ]
    streaks = detect_error_streaks(sessions, streak_threshold=3)
    assert len(streaks) == 0


def test_detect_error_streaks_multiple_groups():
    sessions = [
        _session("s1", group="g1", status="error", started="2026-03-16T09:00:00+00:00"),
        _session("s2", group="g1", status="error", started="2026-03-16T09:01:00+00:00"),
        _session("s3", group="g1", status="error", started="2026-03-16T09:02:00+00:00"),
        _session("s4", group="g2", status="success", started="2026-03-16T09:00:00+00:00"),
        _session("s5", group="g2", status="error", started="2026-03-16T09:01:00+00:00"),
    ]
    streaks = detect_error_streaks(sessions, streak_threshold=3)
    assert "g1" in streaks
    assert "g2" not in streaks


def test_no_alerts_on_healthy_data(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    # Write healthy sessions
    for i in range(5):
        s = _session(f"s{i}", duration=60, status="success")
        (sessions_dir / f"s{i}.yaml").write_text(marshal(s))

    cfg = Config(
        sessions_dir=str(sessions_dir),
        spin_threshold_secs=600,
        error_streak_threshold=3,
    )
    warnings = check_alerts(cfg)
    assert len(warnings) == 0


def test_alerts_on_bad_data(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    # Write a spinner
    s = _session("spinner", duration=1200, result_length=0)
    (sessions_dir / "spinner.yaml").write_text(marshal(s))

    # Write an error streak
    for i in range(4):
        s = _session(f"err{i}", status="error", result_length=0,
                     started=f"2026-03-16T09:0{i}:00+00:00")
        (sessions_dir / f"err{i}.yaml").write_text(marshal(s))

    cfg = Config(
        sessions_dir=str(sessions_dir),
        spin_threshold_secs=600,
        error_streak_threshold=3,
    )
    warnings = check_alerts(cfg)
    assert len(warnings) >= 2  # At least one SPIN and one STREAK
    assert any("SPIN" in w for w in warnings)
    assert any("STREAK" in w for w in warnings)


def test_empty_sessions_dir(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    cfg = Config(sessions_dir=str(sessions_dir))
    warnings = check_alerts(cfg)
    assert warnings == []
