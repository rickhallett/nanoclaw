import subprocess
from pathlib import Path

from halos.briefings.config import Config
from halos.briefings.gather import _get_recent_errors


def make_config(tmp_path: Path) -> Config:
    return Config(
        project_root=tmp_path,
        memctl_config=tmp_path / "memctl.yaml",
        nightctl_config=tmp_path / "nightctl.yaml",
        todoctl_config=tmp_path / "todoctl.yaml",
        logctl_config=tmp_path / "logctl.yaml",
        ipc_dir=tmp_path / "data" / "ipc",
        ipc_group="telegram_main",
        chat_jid="tg:123",
        db_path=tmp_path / "store" / "messages.db",
        model="test-model",
        max_tokens=256,
    )


def test_get_recent_errors_ignores_logctl_empty_sentinel(monkeypatch, tmp_path):
    cfg = make_config(tmp_path)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout="No errors in the last 24 hours.\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _get_recent_errors(cfg) == []


def test_get_recent_errors_preserves_actual_error_lines(monkeypatch, tmp_path):
    cfg = make_config(tmp_path)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout="[2026-03-26T12:00:00Z] [error] [briefings] thing broke\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _get_recent_errors(cfg) == ["[2026-03-26T12:00:00Z] [error] [briefings] thing broke"]
