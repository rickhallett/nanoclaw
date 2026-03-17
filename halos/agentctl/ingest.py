"""Parse container log files into session records."""

import glob
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import Config
from .session import Session, filename, marshal
from .usage import load_usage_events, enrich_session

try:
    from halos.telemetry import emit as telemetry_emit
except ImportError:
    telemetry_emit = None  # type: ignore


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
    if log_text.startswith("=== Container Run Log (TIMEOUT)"):
        # Check if the container had streaming output — if so, it was productive
        streaming = _parse_log_field(log_text, "Had Streaming Output")
        if streaming and streaming.lower() == "true":
            return "success"
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
    try:
        duration_ms = int(duration_str.replace("ms", "").strip())
    except (ValueError, AttributeError):
        duration_ms = 0
    duration_secs = duration_ms // 1000

    try:
        exit_code = int(exit_code_str) if exit_code_str else 1
    except (ValueError, AttributeError):
        exit_code = 1

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

    try:
        prompt_length = int(prompt_length_str.replace("chars", "").strip()) if prompt_length_str else 0
    except (ValueError, AttributeError):
        prompt_length = 0

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

    # Load API usage events for session enrichment
    usage_events = load_usage_events(cfg.usage_log)
    if verbose and usage_events:
        print(f"  Loaded {len(usage_events)} API usage events for enrichment")

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

        # Enrich with API usage data (token counts, cost)
        session = enrich_session(session, usage_events)
        if verbose and session.input_tokens > 0:
            print(f"  ENRICHED: {session.id} ({session.model}, "
                  f"{session.input_tokens}in/{session.output_tokens}out, "
                  f"${session.total_cost_usd:.4f})")

        # Write session record
        out_path = sessions_dir / filename(session)
        data = marshal(session)
        tmp = str(out_path) + ".tmp"
        Path(tmp).write_text(data)
        os.replace(tmp, str(out_path))

        existing_ids.add(session.id)
        ingested += 1

        # Emit telemetry event for BATHW pipeline
        if telemetry_emit:
            telemetry_emit("agentctl", "session_ended", {
                "session_id": session.id,
                "group_name": session.group,
                "started_at": session.started,
                "ended_at": session.finished,
                "duration_ms": session.duration_secs * 1000,
                "model": session.model,
                "input_tokens": session.input_tokens,
                "output_tokens": session.output_tokens,
                "cache_read_tokens": session.cache_read_tokens,
                "cache_write_tokens": session.cache_write_tokens,
                "total_cost_usd": session.total_cost_usd,
                "outcome": session.status,
                "channel": "container",
                "trigger_type": session.source,
            })

        if verbose:
            print(f"  INGESTED: {session.id} ({session.group}, {session.status})")

    return ingested, skipped, errors
