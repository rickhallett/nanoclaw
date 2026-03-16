"""Tests for container log ingestion."""

import os
from pathlib import Path

import pytest

from halos.agentctl.config import Config
from halos.agentctl.ingest import ingest, parse_log


SAMPLE_LOG = """\
=== Container Run Log ===
Timestamp: 2026-03-16T09:00:00.000Z
Group: Rick Hallett
IsMain: true
Duration: 33000ms
Exit Code: 0
Stdout Truncated: false
Stderr Truncated: false

=== Input Summary ===
Prompt length: 166 chars
Session ID: 33768042-3e30-4f37-8e86-1210103a05e5

=== Mounts ===
/workspace/project (ro)
/workspace/group
"""

TIMEOUT_LOG = """\
=== Container Run Log (TIMEOUT) ===
Timestamp: 2026-03-16T10:00:00.000Z
Group: Test Group
Container: nanoclaw-test-group-999
Duration: 900000ms
Exit Code: 137
Had Streaming Output: false
"""

MALFORMED_LOG = """\
This is not a container log.
Just some random text.
"""


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a workspace with logs and sessions directories."""
    logs_dir = tmp_path / "groups" / "telegram_main" / "logs"
    logs_dir.mkdir(parents=True)
    sessions_dir = tmp_path / "data" / "agent-sessions"
    sessions_dir.mkdir(parents=True)
    return tmp_path


def test_parse_normal_log(tmp_workspace):
    log_file = tmp_workspace / "groups" / "telegram_main" / "logs" / "container-2026-03-16T09-00-00-000Z.log"
    log_file.write_text(SAMPLE_LOG)

    session = parse_log(str(log_file))
    assert session is not None
    assert session.group == "rick_hallett"
    assert session.duration_secs == 33
    assert session.exit_code == 0
    assert session.status == "success"
    assert session.prompt_length == 166
    assert session.source == "container"


def test_parse_timeout_log(tmp_workspace):
    log_file = tmp_workspace / "groups" / "test_group" / "logs" / "container-timeout.log"
    log_file.parent.mkdir(parents=True)
    log_file.write_text(TIMEOUT_LOG)

    session = parse_log(str(log_file))
    assert session is not None
    assert session.id == "nanoclaw-test-group-999"
    assert session.status == "timeout"
    assert session.duration_secs == 900
    assert session.exit_code == 137


def test_parse_malformed_log(tmp_workspace):
    log_file = tmp_workspace / "groups" / "telegram_main" / "logs" / "container-bad.log"
    log_file.write_text(MALFORMED_LOG)

    session = parse_log(str(log_file))
    assert session is None


def test_parse_missing_file():
    session = parse_log("/nonexistent/path.log")
    assert session is None


def test_ingest_creates_session_files(tmp_workspace):
    log_file = tmp_workspace / "groups" / "telegram_main" / "logs" / "container-2026-03-16T09-00-00-000Z.log"
    log_file.write_text(SAMPLE_LOG)

    cfg = Config(
        sessions_dir=str(tmp_workspace / "data" / "agent-sessions"),
        log_dirs=[str(tmp_workspace / "groups" / "*" / "logs")],
    )

    ingested, skipped, errors = ingest(cfg)
    assert ingested == 1
    assert skipped == 0
    assert errors == 0

    # Check the file was written
    session_files = list((tmp_workspace / "data" / "agent-sessions").glob("*.yaml"))
    assert len(session_files) == 1


def test_ingest_skips_existing(tmp_workspace):
    log_file = tmp_workspace / "groups" / "telegram_main" / "logs" / "container-2026-03-16T09-00-00-000Z.log"
    log_file.write_text(SAMPLE_LOG)

    cfg = Config(
        sessions_dir=str(tmp_workspace / "data" / "agent-sessions"),
        log_dirs=[str(tmp_workspace / "groups" / "*" / "logs")],
    )

    # First ingest
    ingested1, _, _ = ingest(cfg)
    assert ingested1 == 1

    # Second ingest should skip
    ingested2, skipped2, _ = ingest(cfg)
    assert ingested2 == 0
    assert skipped2 == 1


def test_ingest_handles_malformed(tmp_workspace):
    log_file = tmp_workspace / "groups" / "telegram_main" / "logs" / "container-bad.log"
    log_file.write_text(MALFORMED_LOG)

    cfg = Config(
        sessions_dir=str(tmp_workspace / "data" / "agent-sessions"),
        log_dirs=[str(tmp_workspace / "groups" / "*" / "logs")],
    )

    ingested, skipped, errors = ingest(cfg)
    assert ingested == 0
    assert errors == 1
