"""Critical tests for SQLite backup safety.

Verifies that sqlite3.backup() produces consistent, queryable copies
even when the source database is under simulated load.
"""

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from halos.backupctl.engine import _safe_copy_sqlite


class TestSqliteSafety:
    """Ensure sqlite3.backup() produces consistent copies under all conditions."""

    def test_backup_while_writing(self, tmp_path):
        """Backup taken during concurrent writes is still consistent."""
        db_path = tmp_path / "busy.db"
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.execute("CREATE TABLE data (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()

        # Insert initial data
        for i in range(100):
            conn.execute("INSERT INTO data (value) VALUES (?)", (f"row-{i}",))
        conn.commit()

        # Simulate concurrent writes during backup
        stop_event = threading.Event()
        write_count = [0]

        def writer():
            while not stop_event.is_set():
                try:
                    conn.execute(
                        "INSERT INTO data (value) VALUES (?)",
                        (f"concurrent-{write_count[0]}",),
                    )
                    conn.commit()
                    write_count[0] += 1
                    time.sleep(0.001)
                except sqlite3.OperationalError:
                    # Database locked — expected during backup
                    time.sleep(0.01)

        t = threading.Thread(target=writer)
        t.start()

        # Take backup while writer is active
        time.sleep(0.01)  # Let writer get a few inserts in
        dest_dir = tmp_path / "backup"
        dest_dir.mkdir()
        backup_path = _safe_copy_sqlite(db_path, dest_dir)

        stop_event.set()
        t.join()
        conn.close()

        # Verify backup is consistent and queryable
        backup_conn = sqlite3.connect(str(backup_path))
        rows = backup_conn.execute("SELECT COUNT(*) FROM data").fetchone()
        backup_conn.close()

        # Should have at least the initial 100 rows
        assert rows[0] >= 100

    def test_backup_preserves_schema(self, tmp_path):
        """Backup preserves the full schema including indexes."""
        db_path = tmp_path / "schema.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        conn.execute("CREATE INDEX idx_email ON users (email)")
        conn.execute("INSERT INTO users VALUES (1, 'Kai', 'kai@example.com')")
        conn.commit()
        conn.close()

        dest_dir = tmp_path / "backup"
        dest_dir.mkdir()
        backup_path = _safe_copy_sqlite(db_path, dest_dir)

        backup_conn = sqlite3.connect(str(backup_path))

        # Check data
        row = backup_conn.execute("SELECT * FROM users WHERE id = 1").fetchone()
        assert row == (1, "Kai", "kai@example.com")

        # Check index exists
        indexes = backup_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='users'"
        ).fetchall()
        backup_conn.close()
        index_names = [i[0] for i in indexes]
        assert "idx_email" in index_names

    def test_backup_multiple_tables(self, tmp_path):
        """Backup works correctly with multiple tables."""
        db_path = tmp_path / "multi.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE t1 (a TEXT)")
        conn.execute("CREATE TABLE t2 (b INTEGER)")
        conn.execute("CREATE TABLE t3 (c REAL)")
        conn.execute("INSERT INTO t1 VALUES ('hello')")
        conn.execute("INSERT INTO t2 VALUES (42)")
        conn.execute("INSERT INTO t3 VALUES (3.14)")
        conn.commit()
        conn.close()

        dest_dir = tmp_path / "backup"
        dest_dir.mkdir()
        backup_path = _safe_copy_sqlite(db_path, dest_dir)

        backup_conn = sqlite3.connect(str(backup_path))
        assert backup_conn.execute("SELECT a FROM t1").fetchone()[0] == "hello"
        assert backup_conn.execute("SELECT b FROM t2").fetchone()[0] == 42
        assert abs(backup_conn.execute("SELECT c FROM t3").fetchone()[0] - 3.14) < 0.001
        backup_conn.close()

    def test_backup_empty_database(self, tmp_path):
        """Backup of an empty database (schema only) works."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, ts TEXT)")
        conn.commit()
        conn.close()

        dest_dir = tmp_path / "backup"
        dest_dir.mkdir()
        backup_path = _safe_copy_sqlite(db_path, dest_dir)

        backup_conn = sqlite3.connect(str(backup_path))
        rows = backup_conn.execute("SELECT COUNT(*) FROM events").fetchone()
        backup_conn.close()
        assert rows[0] == 0

    def test_backup_large_database(self, tmp_path):
        """Backup handles larger databases correctly."""
        db_path = tmp_path / "large.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE log (id INTEGER PRIMARY KEY, msg TEXT)")

        # Insert 10k rows
        conn.executemany(
            "INSERT INTO log (msg) VALUES (?)",
            [(f"message-{i}",) for i in range(10_000)],
        )
        conn.commit()
        conn.close()

        dest_dir = tmp_path / "backup"
        dest_dir.mkdir()
        backup_path = _safe_copy_sqlite(db_path, dest_dir)

        backup_conn = sqlite3.connect(str(backup_path))
        count = backup_conn.execute("SELECT COUNT(*) FROM log").fetchone()[0]
        backup_conn.close()
        assert count == 10_000
