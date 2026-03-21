"""Unit tests for backupctl engine."""

import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from halos.backupctl.config import BackupConfig, BackupTarget, RetentionPolicy
from halos.backupctl.engine import (
    _safe_copy_sqlite,
    _prepare_backup_paths,
    _backup_tar,
    _list_tar_snapshots,
    _verify_tar,
    _restore_tar,
    _list_restic_snapshots,
    run_backup,
    list_snapshots,
    verify_repository,
    get_last_backup_age,
    get_target_stats,
)


def _make_config(tmp_path: Path) -> BackupConfig:
    """Create a test config pointing at tmp_path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return BackupConfig(
        repository=repo,
        targets={
            "test": BackupTarget(
                name="test",
                paths=["testdata/"],
                retain=RetentionPolicy(daily=7),
            ),
        },
        repo_root=tmp_path,
    )


class TestSqliteBackup:
    """Tests for sqlite3.backup() safety."""

    def test_creates_valid_backup(self, tmp_path):
        """sqlite3.backup() produces a readable, consistent copy."""
        db_path = tmp_path / "source.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO items VALUES (1, 'alpha')")
        conn.execute("INSERT INTO items VALUES (2, 'beta')")
        conn.commit()
        conn.close()

        dest_dir = tmp_path / "backup"
        dest_dir.mkdir()
        backup_path = _safe_copy_sqlite(db_path, dest_dir)

        # Verify the backup is valid and has the data
        backup_conn = sqlite3.connect(str(backup_path))
        rows = backup_conn.execute("SELECT * FROM items ORDER BY id").fetchall()
        backup_conn.close()

        assert len(rows) == 2
        assert rows[0] == (1, "alpha")
        assert rows[1] == (2, "beta")

    def test_backup_is_independent(self, tmp_path):
        """Changes to source after backup don't affect the backup."""
        db_path = tmp_path / "source.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (val TEXT)")
        conn.execute("INSERT INTO t VALUES ('before')")
        conn.commit()

        dest_dir = tmp_path / "backup"
        dest_dir.mkdir()
        backup_path = _safe_copy_sqlite(db_path, dest_dir)

        # Modify source
        conn.execute("INSERT INTO t VALUES ('after')")
        conn.commit()
        conn.close()

        # Backup should only have 'before'
        backup_conn = sqlite3.connect(str(backup_path))
        rows = backup_conn.execute("SELECT val FROM t").fetchall()
        backup_conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "before"


class TestPrepareBackupPaths:
    """Tests for path preparation with SQLite safety."""

    def test_directory_with_db_gets_safe_copy(self, tmp_path):
        """Directories containing .db files get copied with safe SQLite backup."""
        data_dir = tmp_path / "testdata"
        data_dir.mkdir()

        # Create a real SQLite db
        db_path = data_dir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (42)")
        conn.commit()
        conn.close()

        # Create a non-db file too
        (data_dir / "notes.txt").write_text("hello")

        target = BackupTarget(name="test", paths=["testdata/"])
        tmp_dir = tmp_path / "staging"
        tmp_dir.mkdir()

        paths = _prepare_backup_paths(target, tmp_path, tmp_dir)
        assert len(paths) == 1
        # Should be the temp copy, not the original
        assert paths[0] != data_dir
        # Should contain the db and the txt
        assert (paths[0] / "test.db").exists()
        assert (paths[0] / "notes.txt").exists()

        # Verify the db copy is valid
        backup_conn = sqlite3.connect(str(paths[0] / "test.db"))
        rows = backup_conn.execute("SELECT x FROM t").fetchall()
        backup_conn.close()
        assert rows[0][0] == 42

    def test_directory_without_db_used_directly(self, tmp_path):
        """Directories without .db files are used directly (no copy)."""
        data_dir = tmp_path / "testdata"
        data_dir.mkdir()
        (data_dir / "file.txt").write_text("content")

        target = BackupTarget(name="test", paths=["testdata/"])
        tmp_dir = tmp_path / "staging"
        tmp_dir.mkdir()

        paths = _prepare_backup_paths(target, tmp_path, tmp_dir)
        assert len(paths) == 1
        assert paths[0] == data_dir.resolve()

    def test_single_db_file(self, tmp_path):
        """A single .db file path gets safe copy."""
        db_path = tmp_path / "single.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t (v TEXT)")
        conn.commit()
        conn.close()

        target = BackupTarget(name="test", paths=["single.db"])
        tmp_dir = tmp_path / "staging"
        tmp_dir.mkdir()

        paths = _prepare_backup_paths(target, tmp_path, tmp_dir)
        assert len(paths) == 1
        assert paths[0].name == "single.db"
        assert paths[0].parent == tmp_dir


class TestTarBackup:
    """Tests for tar fallback backend."""

    def test_creates_tar_file(self, tmp_path):
        """Tar backup creates a valid archive."""
        cfg = _make_config(tmp_path)
        data_dir = tmp_path / "testdata"
        data_dir.mkdir()
        (data_dir / "file.txt").write_text("backup this")

        paths = [data_dir]
        result = _backup_tar(cfg, "test", paths)

        assert result["success"] is True
        assert result["backend"] == "tar"
        assert "bytes" in result["detail"]

        # Verify tar file exists
        tar_dir = cfg.repository / "tar"
        tar_files = list(tar_dir.glob("backup-test-*.tar.gz"))
        assert len(tar_files) == 1
        assert tar_files[0].stat().st_size > 0

    def test_tar_directory_created(self, tmp_path):
        """Tar backup creates the tar subdirectory if missing."""
        cfg = _make_config(tmp_path)
        data_dir = tmp_path / "testdata"
        data_dir.mkdir()
        (data_dir / "x.txt").write_text("x")

        _backup_tar(cfg, "test", [data_dir])
        assert (cfg.repository / "tar").is_dir()


class TestListTarSnapshots:
    """Tests for listing tar snapshots."""

    def test_empty_when_no_backups(self, tmp_path):
        cfg = _make_config(tmp_path)
        snapshots = _list_tar_snapshots(cfg)
        assert snapshots == []

    def test_lists_existing_tar_files(self, tmp_path):
        cfg = _make_config(tmp_path)
        tar_dir = cfg.repository / "tar"
        tar_dir.mkdir(parents=True)

        # Create dummy tar files
        (tar_dir / "backup-store-20260321-100000.tar.gz").write_bytes(b"\x1f\x8b" + b"\x00" * 20)
        (tar_dir / "backup-memory-20260321-110000.tar.gz").write_bytes(b"\x1f\x8b" + b"\x00" * 20)

        snapshots = _list_tar_snapshots(cfg)
        assert len(snapshots) == 2

    def test_filter_by_target(self, tmp_path):
        cfg = _make_config(tmp_path)
        tar_dir = cfg.repository / "tar"
        tar_dir.mkdir(parents=True)

        (tar_dir / "backup-store-20260321-100000.tar.gz").write_bytes(b"\x1f\x8b" + b"\x00" * 20)
        (tar_dir / "backup-memory-20260321-110000.tar.gz").write_bytes(b"\x1f\x8b" + b"\x00" * 20)

        snapshots = _list_tar_snapshots(cfg, target_name="store")
        assert len(snapshots) == 1
        assert snapshots[0]["target"] == "store"


class TestVerifyTar:
    """Tests for tar verification."""

    def test_no_tar_dir(self, tmp_path):
        cfg = _make_config(tmp_path)
        result = _verify_tar(cfg)
        assert result["success"] is False

    def test_empty_tar_dir(self, tmp_path):
        cfg = _make_config(tmp_path)
        (cfg.repository / "tar").mkdir(parents=True)
        result = _verify_tar(cfg)
        assert result["success"] is True  # nothing to verify


class TestResticMocking:
    """Tests for restic backend with mocked subprocess."""

    @patch("halos.backupctl.engine._has_restic", return_value=True)
    @patch("subprocess.run")
    def test_list_restic_snapshots_parses_json(self, mock_run, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "id": "abc123def456",
                "short_id": "abc123de",
                "time": "2026-03-21T10:00:00Z",
                "tags": ["store"],
                "paths": ["/data/store"],
            },
            {
                "id": "xyz789ghi012",
                "short_id": "xyz789gh",
                "time": "2026-03-21T11:00:00Z",
                "tags": ["memory"],
                "paths": ["/data/memory"],
            },
        ])
        mock_run.return_value = mock_result

        snapshots = _list_restic_snapshots(cfg)
        assert len(snapshots) == 2
        assert snapshots[0]["id"] == "abc123de"
        assert snapshots[0]["target"] == "store"
        assert snapshots[1]["target"] == "memory"

    @patch("halos.backupctl.engine._has_restic", return_value=True)
    @patch("subprocess.run")
    def test_list_restic_snapshots_filter(self, mock_run, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([{
            "id": "abc123",
            "short_id": "abc123",
            "time": "2026-03-21T10:00:00Z",
            "tags": ["store"],
            "paths": [],
        }])
        mock_run.return_value = mock_result

        snapshots = _list_restic_snapshots(cfg, target_name="store")
        # Verify --tag was passed
        call_args = mock_run.call_args[0][0]
        assert "--tag" in call_args
        assert "store" in call_args

    @patch("halos.backupctl.engine._has_restic", return_value=True)
    @patch("subprocess.run")
    def test_verify_restic_success(self, mock_run, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "no errors found"
        mock_run.return_value = mock_result

        result = verify_repository(cfg)
        assert result["success"] is True
        assert result["backend"] == "restic"

    @patch("halos.backupctl.engine._has_restic", return_value=True)
    @patch("subprocess.run")
    def test_verify_restic_failure(self, mock_run, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "repository corrupted"
        mock_run.return_value = mock_result

        result = verify_repository(cfg)
        assert result["success"] is False


class TestRunBackup:
    """Tests for the run_backup orchestration."""

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_unknown_target_returns_error(self, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)
        results = run_backup(cfg, target_name="nonexistent")
        assert results["nonexistent"]["success"] is False
        assert "unknown target" in results["nonexistent"]["detail"]

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_tar_fallback_used_when_no_restic(self, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)
        data_dir = tmp_path / "testdata"
        data_dir.mkdir()
        (data_dir / "x.txt").write_text("data")

        results = run_backup(cfg, target_name="test")
        assert results["test"]["success"] is True
        assert results["test"]["backend"] == "tar"

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_missing_paths_report_error(self, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)
        # Don't create testdata/ — paths won't resolve
        results = run_backup(cfg, target_name="test")
        assert results["test"]["success"] is False
        assert "no paths" in results["test"]["detail"]


class TestGetLastBackupAge:
    """Tests for backup age calculation."""

    @patch("halos.backupctl.engine._has_restic", return_value=False)
    def test_none_when_no_backups(self, mock_restic, tmp_path):
        cfg = _make_config(tmp_path)
        assert get_last_backup_age(cfg) is None

    @patch("halos.backupctl.engine.list_snapshots")
    def test_parses_tar_timestamp(self, mock_list, tmp_path):
        cfg = _make_config(tmp_path)
        mock_list.return_value = [
            {"time": "20260321-100000", "target": "store"},
        ]
        age = get_last_backup_age(cfg)
        # Should return a number (hours)
        assert age is not None
        assert isinstance(age, float)


class TestGetTargetStats:
    """Tests for target statistics."""

    @patch("halos.backupctl.engine.list_snapshots")
    def test_counts_snapshots(self, mock_list, tmp_path):
        cfg = _make_config(tmp_path)
        mock_list.return_value = [
            {"target": "store", "size_bytes": 1000},
            {"target": "store", "size_bytes": 2000},
        ]
        stats = get_target_stats(cfg, "store")
        assert stats["snapshot_count"] == 2
        assert stats["total_size_bytes"] == 3000
