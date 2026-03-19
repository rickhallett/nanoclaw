"""Nightctl overnight activity summary.

Generates an exec summary of agent-job execution for delivery
15 minutes before the morning briefing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .config import Config


@dataclass
class NightctlSummary:
    """Summary of nightctl overnight activity."""

    timestamp: str = ""
    window_start: str = ""
    window_end: str = ""

    # Agent-jobs
    agent_jobs_run: int = 0
    agent_jobs_done: list[dict] = field(default_factory=list)
    agent_jobs_failed: list[dict] = field(default_factory=list)
    agent_jobs_pending: list[dict] = field(default_factory=list)

    # Regular jobs
    jobs_run: int = 0
    jobs_done: int = 0
    jobs_failed: int = 0

    # Run records
    runs: list[dict] = field(default_factory=list)


def gather_nightctl_summary(cfg: Config) -> NightctlSummary:
    """Gather nightctl activity from the overnight window.

    Looks at:
    - queue/items/*.yaml for agent-job status
    - queue/runs/*.yaml for execution records since overnight window start
    - queue/MANIFEST.yaml for legacy job status
    """
    now = datetime.now(timezone.utc)

    # Overnight window is 02:00-05:00 local, but we look back ~4 hours
    # to catch everything from the window
    since = now - timedelta(hours=4)

    summary = NightctlSummary(
        timestamp=now.isoformat(),
        window_start=(now - timedelta(hours=4)).strftime("%H:%M"),
        window_end=now.strftime("%H:%M"),
    )

    # Resolve paths from nightctl config
    nightctl_config = cfg.nightctl_config
    if not nightctl_config.exists():
        return summary

    with open(nightctl_config) as f:
        ncfg = yaml.safe_load(f) or {}

    base_dir = nightctl_config.parent
    items_dir = _resolve(base_dir, ncfg.get("items_dir", "./queue/items"))
    runs_dir = _resolve(base_dir, ncfg.get("runs_dir", "./queue/runs"))

    # Collect agent-job items
    if items_dir.exists():
        for f in items_dir.glob("*.yaml"):
            try:
                with open(f) as fh:
                    data = yaml.safe_load(fh) or {}

                kind = data.get("kind", "task")
                if kind != "agent-job":
                    continue

                status = data.get("status", "open")
                item_info = {
                    "id": data.get("id", f.stem),
                    "title": data.get("title", "untitled"),
                    "status": status,
                    "priority": data.get("priority", 3),
                }

                if status == "done":
                    # Check if completed recently
                    modified = data.get("modified", "")
                    if modified and _is_recent(modified, since):
                        summary.agent_jobs_done.append(item_info)
                        summary.agent_jobs_run += 1
                elif status == "failed":
                    modified = data.get("modified", "")
                    if modified and _is_recent(modified, since):
                        summary.agent_jobs_failed.append(item_info)
                        summary.agent_jobs_run += 1
                elif status == "in-progress":
                    summary.agent_jobs_pending.append(item_info)

            except Exception:
                pass

    # Collect recent run records
    if runs_dir.exists():
        for f in sorted(runs_dir.glob("*.yaml"), reverse=True):
            try:
                with open(f) as fh:
                    run = yaml.safe_load(fh) or {}

                started = run.get("started", "")
                if started and _is_recent(started, since):
                    summary.runs.append(
                        {
                            "id": run.get("id", f.stem),
                            "outcome": run.get("outcome", "unknown"),
                            "duration_secs": run.get("duration_secs", 0),
                            "started": started,
                        }
                    )

                    if run.get("outcome") == "done":
                        summary.jobs_done += 1
                    elif run.get("outcome") in ("failed", "timeout"):
                        summary.jobs_failed += 1
                    summary.jobs_run += 1

            except Exception:
                pass

    return summary


def format_nightctl_summary(summary: NightctlSummary) -> str:
    """Format the summary as a Telegram message."""
    lines = ["🌙 *Overnight Activity Summary*\n"]

    # Agent-jobs section
    total_agent = len(summary.agent_jobs_done) + len(summary.agent_jobs_failed)
    if total_agent > 0 or summary.agent_jobs_pending:
        lines.append("*Agent Jobs*")

        if summary.agent_jobs_done:
            lines.append(f"✅ Completed: {len(summary.agent_jobs_done)}")
            for job in summary.agent_jobs_done:
                lines.append(f"   • {job['title']}")

        if summary.agent_jobs_failed:
            lines.append(f"❌ Failed: {len(summary.agent_jobs_failed)}")
            for job in summary.agent_jobs_failed:
                lines.append(f"   • {job['title']}")

        if summary.agent_jobs_pending:
            lines.append(f"⏳ Still pending: {len(summary.agent_jobs_pending)}")
            for job in summary.agent_jobs_pending:
                lines.append(f"   • {job['title']}")

        lines.append("")

    # Run records section (if any non-agent runs)
    if summary.runs:
        total_duration = sum(r.get("duration_secs", 0) for r in summary.runs)
        lines.append(f"*Execution Stats*")
        lines.append(f"Total runs: {summary.jobs_run}")
        lines.append(f"Duration: {total_duration // 60}m {total_duration % 60}s")
        lines.append("")

    # Summary line
    if total_agent == 0 and not summary.runs:
        lines.append("_No overnight activity recorded._")
    else:
        success_rate = 0
        if summary.agent_jobs_run > 0:
            success_rate = len(summary.agent_jobs_done) / summary.agent_jobs_run * 100
        lines.append(f"_Window: {summary.window_start} – {summary.window_end} UTC_")
        if summary.agent_jobs_run > 0:
            lines.append(f"_Success rate: {success_rate:.0f}%_")

    return "\n".join(lines)


def _resolve(base: Path, path_str: str) -> Path:
    """Resolve a path relative to base if not absolute."""
    p = Path(path_str)
    return p if p.is_absolute() else (base / p).resolve()


def _is_recent(timestamp: str, since: datetime) -> bool:
    """Check if a timestamp is more recent than 'since'."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt >= since
    except (ValueError, AttributeError):
        return False
