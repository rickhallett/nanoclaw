"""Parse container log files into session records."""

import glob
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import Config
from .session import Session, filename, marshal


def _parse_log_field(text: str, field: str) -> Optional[str]:
    """Extract a field value from a container log."""
    pattern = rf"^{re.escape(field)}:\s*(.+)$"
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _derive_container_name(log_path: str, log_text: str) -> Optional[str]:
    """Get container name from log content or filename."""
    # Try the Container: line first
    name = _parse_log_field(log_text, "Container")
    if name:
        return name
    # Fall back to deriving from the filename + parent group
    # e.g. groups/telegram_main/logs/container-2026-03-15T23-22-12-313Z.log
    p = Path(log_path)
    # The filename minus extension is the container identifier
    return p.stem


def _derive_group_from_path(log_path: str) -> str:
    """Derive group name from log file path.

    Expected: .../groups/{group_folder}/logs/container-*.log
    """
    parts = Path(log_path).parts
    for i, part in enumerate(parts):
        if part == "groups" and i + 2 < len(parts) and parts[i + 2] == "logs":
            return parts[i + 1]
    return "unknown"


def _determine_status(exit_code: int, log_text: str) -> str:
    """Determine session status from exit code and log content."""
    if "TIMEOUT" in log_text.split("\n")[0]:
        return "timeout"
    if exit_code != 0:
        return "error"
    return "success"


def parse_log(log_path: str) -> Optional[Session]:
    """Parse a single container log file into a Session record."""
    try:
        text = Path(log_path).read_text()
    except (OSError, IOError):
        return None

    if "=== Container Run Log" not in text:
        return None

    timestamp_str = _parse_log_field(text, "Timestamp")
    group_name = _parse_log_field(text, "Group")
    duration_str = _parse_log_field(text, "Duration")
    exit_code_str = _parse_log_field(text, "Exit Code")
    prompt_length_str = _parse_log_field(text, "Prompt length")

    # Required fields
    if not timestamp_str or not duration_str:
        return None

    # Parse duration (in ms from container runner)
    duration_ms = int(duration_str.replace("ms", "").strip())
    duration_secs = duration_ms // 1000

    exit_code = int(exit_code_str) if exit_code_str else 1

    # Parse timestamp
    try:
        started = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError:
        return None

    from datetime import timedelta
    finished = started + timedelta(milliseconds=duration_ms)

    # Derive group from log field or path
    group = group_name or _derive_group_from_path(log_path)
    # Normalize group name to folder-style (spaces -> underscores, lowercase)
    group_folder = group.lower().replace(" ", "_")

    # Container name as session ID
    container_name = _derive_container_name(log_path, text)
    if not container_name:
        return None

    # Use container name as the session ID (includes timestamp, guaranteed unique)
    session_id = container_name

    prompt_length = int(prompt_length_str.replace("chars", "").strip()) if prompt_length_str else 0

    # Estimate result length from log (not always available)
    result_length = 0

    status = _determine_status(exit_code, text)
    source = "container"

    return Session(
        id=session_id,
        group=group_folder,
        started=started.isoformat(),
        finished=finished.isoformat(),
        duration_secs=duration_secs,
        exit_code=exit_code,
        prompt_length=prompt_length,
        result_length=result_length,
        status=status,
        source=source,
    )


def ingest(cfg: Config, verbose: bool = False) -> tuple[int, int, int]:
    """Ingest all container logs. Returns (ingested, skipped, errors)."""
    sessions_dir = Path(cfg.sessions_dir)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Collect existing session IDs to skip duplicates
    existing_ids: set[str] = set()
    for f in sessions_dir.iterdir():
        if f.suffix == ".yaml":
            existing_ids.add(f.stem)

    ingested = 0
    skipped = 0
    errors = 0

    # Expand log_dirs globs
    log_files: list[str] = []
    for pattern in cfg.log_dirs:
        matched = glob.glob(os.path.join(pattern, "container-*.log"))
        log_files.extend(matched)

    for log_path in sorted(log_files):
        session = parse_log(log_path)
        if session is None:
            errors += 1
            if verbose:
                print(f"  SKIP (parse error): {log_path}")
            continue

        if session.id in existing_ids:
            skipped += 1
            if verbose:
                print(f"  SKIP (exists): {session.id}")
            continue

        # Write session record
        out_path = sessions_dir / filename(session)
        data = marshal(session)
        tmp = str(out_path) + ".tmp"
        Path(tmp).write_text(data)
        os.replace(tmp, str(out_path))

        existing_ids.add(session.id)
        ingested += 1
        if verbose:
            print(f"  INGESTED: {session.id} ({session.group}, {session.status})")

    return ingested, skipped, errors
