"""Integration tests for backupctl CLI."""

import json
import subprocess
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from halos.backupctl.cli import (
    cmd_targets,
    cmd_run,
    cmd_list,
    cmd_summary,
    main,
)
from halos.backupctl.config import BackupConfig, BackupTarget, RetentionPolicy


def _mock_config():
    """Create a mock config for CLI tests."""
    return BackupConfig(
        repository="/tmp/test-backups",
        targets={
            "store": BackupTarget(
                name="store",
                paths=["store/"],
                retain=RetentionPolicy(daily=30, weekly=12),
            ),
            "memory": BackupTarget(
                name="memory",
                paths=["memory/"],
                retain=RetentionPolicy(daily=30, weekly=12),
            ),
        },
    )


class TestCmdTargets:
    """Tests for 'backupctl targets' command."""

    @patch("halos.backupctl.cli.load_config")
    def test_lists_targets(self, mock_load, capsys):
        mock_load.return_value = _mock_config()
        args = MagicMock()
        result = cmd_targets(args)
        assert result == 0

        output = capsys.readouterr().out
        assert "store" in output
        assert "memory" in output

    @patch("halos.backupctl.cli.load_config")
    def test_shows_retention(self, mock_load, capsys):
        mock_load.return_value = _mock_config()
        args = MagicMock()
        cmd_targets(args)

        output = capsys.readouterr().out
        assert "30d" in output
        assert "12w" in output

    @patch("halos.backupctl.cli.load_config")
    def test_empty_targets(self, mock_load, capsys):
        cfg = _mock_config()
        cfg.targets = {}
        mock_load.return_value = cfg
        args = MagicMock()
        result = cmd_targets(args)
        assert result == 0
        assert "No backup targets" in capsys.readouterr().out


class TestCmdRun:
    """Tests for 'backupctl run' command."""

    @patch("halos.backupctl.cli.engine")
    @patch("halos.backupctl.cli.load_config")
    def test_run_specific_target(self, mock_load, mock_engine, capsys):
        mock_load.return_value = _mock_config()
        mock_engine.run_backup.return_value = {
            "store": {
                "success": True,
                "backend": "tar",
                "detail": "backup-store-20260321.tar.gz (1,234 bytes)",
            },
        }
        args = MagicMock(target="store")
        result = cmd_run(args)
        assert result == 0
        mock_engine.run_backup.assert_called_once()

    @patch("halos.backupctl.cli.engine")
    @patch("halos.backupctl.cli.load_config")
    def test_run_failure_returns_1(self, mock_load, mock_engine, capsys):
        mock_load.return_value = _mock_config()
        mock_engine.run_backup.return_value = {
            "store": {
                "success": False,
                "backend": "tar",
                "detail": "permission denied",
            },
        }
        args = MagicMock(target="store")
        result = cmd_run(args)
        assert result == 1


class TestCmdList:
    """Tests for 'backupctl list' command."""

    @patch("halos.backupctl.cli.engine")
    @patch("halos.backupctl.cli.load_config")
    def test_list_json_output(self, mock_load, mock_engine, capsys):
        mock_load.return_value = _mock_config()
        mock_engine.list_snapshots.return_value = [
            {
                "id": "backup-store-20260321-100000.tar.gz",
                "time": "20260321-100000",
                "target": "store",
                "backend": "tar",
                "paths": ["/tmp/backups/tar/backup-store-20260321-100000.tar.gz"],
            },
        ]
        args = MagicMock(target=None, json_out=True)
        result = cmd_list(args)
        assert result == 0

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert len(parsed) == 1
        assert parsed[0]["target"] == "store"

    @patch("halos.backupctl.cli.engine")
    @patch("halos.backupctl.cli.load_config")
    def test_list_table_output(self, mock_load, mock_engine, capsys):
        mock_load.return_value = _mock_config()
        mock_engine.list_snapshots.return_value = [
            {
                "id": "abc123",
                "time": "2026-03-21T10:00:00Z",
                "target": "store",
                "backend": "restic",
                "paths": [],
            },
        ]
        args = MagicMock(target=None, json_out=False)
        result = cmd_list(args)
        assert result == 0

        output = capsys.readouterr().out
        assert "abc123" in output
        assert "store" in output

    @patch("halos.backupctl.cli.engine")
    @patch("halos.backupctl.cli.load_config")
    def test_list_empty(self, mock_load, mock_engine, capsys):
        mock_load.return_value = _mock_config()
        mock_engine.list_snapshots.return_value = []
        args = MagicMock(target=None, json_out=False)
        result = cmd_list(args)
        assert result == 0
        assert "No snapshots" in capsys.readouterr().out


class TestCmdSummary:
    """Tests for 'backupctl summary' command."""

    @patch("halos.backupctl.briefing.text_summary")
    def test_summary_format(self, mock_summary, capsys):
        mock_summary.return_value = "backupctl: last backup 2h ago | store: 5 snapshots (1.2 MB)"
        args = MagicMock()
        result = cmd_summary(args)
        assert result == 0

        output = capsys.readouterr().out
        assert "backupctl:" in output
        assert "store:" in output


class TestMainEntrypoint:
    """Tests for the CLI entrypoint."""

    def test_no_command_prints_help(self, capsys):
        with patch("sys.argv", ["backupctl"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
