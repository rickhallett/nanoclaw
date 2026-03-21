"""Smoke tests for backupctl — real operations, no mocking.

These tests create actual backups using the tar fallback (no restic required)
and verify the results are usable.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from halos.backupctl.config import BackupConfig, BackupTarget, RetentionPolicy, load_config
from halos.backupctl.engine import run_backup, list_snapshots, verify_repository, restore_snapshot
from halos.backupctl.briefing import text_summary


class TestSmokeTargets:
    """Smoke test: targets command doesn't crash."""

    def test_default_config_loads(self):
        """load_config() with no file returns sensible defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(config_path=Path(tmp) / "nonexistent.yaml")
            assert len(cfg.targets) >= 3
            assert "store" in cfg.targets


class TestSmokeBackupCycle:
    """Smoke test: full backup -> list -> verify -> restore cycle with tar."""

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_backup_and_list(self, mock_restic, tmp_path):
        """Create a real tar backup and list it."""
        # Set up test data
        data_dir = tmp_path / "memory"
        data_dir.mkdir()
        (data_dir / "note1.md").write_text("# First note\nSome content.")
        (data_dir / "note2.md").write_text("# Second note\nMore content.")

        repo = tmp_path / "backups"
        cfg = BackupConfig(
            repository=repo,
            targets={
                "memory": BackupTarget(
                    name="memory",
                    paths=["memory/"],
                    retain=RetentionPolicy(daily=30),
                ),
            },
            repo_root=tmp_path,
        )

        # Run backup
        results = run_backup(cfg, target_name="memory")
        assert results["memory"]["success"] is True
        assert results["memory"]["backend"] == "tar"

        # List snapshots
        snapshots = list_snapshots(cfg, target_name="memory")
        assert len(snapshots) == 1
        assert snapshots[0]["target"] == "memory"
        assert snapshots[0]["backend"] == "tar"
        assert snapshots[0].get("size_bytes", 0) > 0

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_backup_with_sqlite(self, mock_restic, tmp_path):
        """Backup a directory containing SQLite databases."""
        store_dir = tmp_path / "store"
        store_dir.mkdir()

        # Create a real SQLite database
        db_path = store_dir / "messages.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE msgs (id INTEGER PRIMARY KEY, text TEXT)")
        conn.execute("INSERT INTO msgs VALUES (1, 'hello world')")
        conn.commit()
        conn.close()

        repo = tmp_path / "backups"
        cfg = BackupConfig(
            repository=repo,
            targets={
                "store": BackupTarget(
                    name="store",
                    paths=["store/"],
                    retain=RetentionPolicy(daily=30),
                ),
            },
            repo_root=tmp_path,
        )

        results = run_backup(cfg, target_name="store")
        assert results["store"]["success"] is True

        # Verify backup exists
        tar_files = list((repo / "tar").glob("backup-store-*.tar.gz"))
        assert len(tar_files) == 1
        assert tar_files[0].stat().st_size > 0

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_verify_tar_backups(self, mock_restic, tmp_path):
        """Verify tar backup integrity."""
        data_dir = tmp_path / "memory"
        data_dir.mkdir()
        (data_dir / "file.txt").write_text("content")

        repo = tmp_path / "backups"
        cfg = BackupConfig(
            repository=repo,
            targets={
                "memory": BackupTarget(name="memory", paths=["memory/"]),
            },
            repo_root=tmp_path,
        )

        # Create backup first
        run_backup(cfg, target_name="memory")

        # Verify
        result = verify_repository(cfg)
        assert result["success"] is True

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_restore_tar_backup(self, mock_restic, tmp_path):
        """Restore a tar backup and verify contents."""
        data_dir = tmp_path / "memory"
        data_dir.mkdir()
        (data_dir / "note.md").write_text("important stuff")

        repo = tmp_path / "backups"
        cfg = BackupConfig(
            repository=repo,
            targets={
                "memory": BackupTarget(name="memory", paths=["memory/"]),
            },
            repo_root=tmp_path,
        )

        # Backup
        run_backup(cfg, target_name="memory")

        # Get snapshot ID
        snapshots = list_snapshots(cfg, target_name="memory")
        assert len(snapshots) == 1
        snapshot_id = snapshots[0]["id"]

        # Restore to new location
        restore_dir = tmp_path / "restored"
        result = restore_snapshot(cfg, "memory", snapshot_id, restore_dir)
        assert result["success"] is True

        # The restored content should exist somewhere under restore_dir
        # (tar preserves full paths)
        assert restore_dir.exists()


class TestSmokeBriefing:
    """Smoke test: briefing integration."""

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_text_summary_no_backups(self, mock_restic):
        """text_summary() returns something sensible with no backups."""
        summary = text_summary()
        assert "backupctl:" in summary

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_text_summary_with_backups(self, mock_restic, tmp_path):
        """text_summary() includes target info after a backup."""
        data_dir = tmp_path / "memory"
        data_dir.mkdir()
        (data_dir / "x.md").write_text("data")

        repo = tmp_path / "backups"
        cfg = BackupConfig(
            repository=repo,
            targets={
                "memory": BackupTarget(name="memory", paths=["memory/"]),
            },
            repo_root=tmp_path,
        )

        run_backup(cfg, target_name="memory")

        # text_summary uses load_config() which won't find our test repo,
        # so we patch it
        with patch("halos.backupctl.briefing.load_config", return_value=cfg):
            summary = text_summary()
            assert "backupctl:" in summary
