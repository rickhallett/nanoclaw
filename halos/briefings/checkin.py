"""Ben check-in system — structured agent questions + exec summary to Kai.

Two-part system:
1. Scheduled task in Ben's microhal initiates check-in conversation daily
2. This module gathers check-in responses and synthesises an exec summary

The check-in prompt runs inside Ben's microhal container. Responses are
stored in the assessments table (phase="checkin"). This module reads them
and delivers a summary to Kai via IPC.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import Config
from .deliver import deliver_message
from .synthesise import _synthesise_via_cli, _synthesise_via_sdk, _read_env_key


# Check-in questions — kept simple, rotated over the week
CHECKIN_QUESTIONS = [
    "How are you finding the agent experience today? Anything particularly useful or frustrating?",
    "What did you use me for today? Was the result what you expected?",
    "Is there anything you wanted to ask me but didn't? What stopped you?",
    "On a scale of 1-5, how helpful was I today? What would make it a 4 or 5?",
    "What's one thing I could do differently that would make your day easier?",
    "Did anything surprise you about how I responded today?",
    "Is there a task you're doing manually that you think I could help with?",
]

# The prompt that runs in Ben's microhal container
CHECKIN_PROMPT = """\
It's time for the daily check-in. This is a brief, structured conversation
to understand how Ben is finding his agent experience. Be natural and
conversational — not clinical. If he doesn't want to do it today, respect
that completely and note it in your response.

Ask him ONE of these questions (rotate, don't repeat the same one two days
in a row):

{questions}

Listen to his answer. If he engages, ask one brief follow-up. Then thank
him and close out.

IMPORTANT: After the conversation, write a brief summary of his response
as a note to memory. Tag it with "checkin" and "ben". Include his sentiment
(positive/neutral/negative) and any specific feedback about the agent experience.
"""

# Synthesis prompt for the exec summary
DIGEST_SYSTEM = """\
You are summarising Ben's daily check-in responses for Kai (his brother,
the system operator). Be concise — this is a Telegram message, not a report.

Rules:
- Lead with sentiment: is Ben finding the agent helpful, frustrating, or neutral?
- Note any specific feedback or feature requests
- Flag any patterns if you notice them across multiple days
- If no check-in happened (Ben declined or was unavailable), say so
- Keep under 500 characters
- Use Telegram Markdown: *bold*, _italic_
- End with 🔴
"""


def gather_checkin_responses(cfg: Config, days: int = 1) -> list[dict]:
    """Read recent check-in responses from Ben's assessments.

    Looks for notes tagged "checkin" in the memory system,
    or assessment entries with phase="checkin" in the DB.
    """
    if not cfg.db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(cfg.db_path))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Check assessments table for check-in entries
        rows = conn.execute(
            """SELECT * FROM assessments
               WHERE phase = 'checkin'
               AND answered_at >= ?
               ORDER BY answered_at DESC""",
            (cutoff,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        pass

    return []


def gather_checkin_from_logs(cfg: Config, days: int = 1) -> str:
    """Fallback: search container logs for check-in conversation output.

    Ben's microhal writes task output to container logs. If assessments
    table doesn't have structured data, we can grep the logs.
    """
    import subprocess

    try:
        # Search for recent check-in outputs in fleet logs
        result = subprocess.run(
            ["logctl", "--config", str(cfg.logctl_config),
             "search", "--source", "microhal-ben", "--event", "checkin",
             "--since", f"{days}d"],
            capture_output=True, text=True, timeout=10,
            cwd=str(cfg.project_root),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return ""


def synthesise_digest(responses: list[dict], log_output: str, cfg: Config) -> str:
    """Produce an exec summary of Ben's check-in for Kai."""
    if not responses and not log_output:
        return "*Ben check-in*: no response recorded today\n\n🔴"

    context_parts = []
    if responses:
        for r in responses:
            context_parts.append(
                f"Q: {r.get('question_text', '?')}\n"
                f"A: {r.get('response', '?')}\n"
                f"Time: {r.get('answered_at', '?')}"
            )
    if log_output:
        context_parts.append(f"Container log output:\n{log_output[:2000]}")

    context = "\n\n".join(context_parts)
    prompt = f"Here are Ben's check-in responses from today:\n\n{context}"

    # Try synthesis
    result = _synthesise_via_cli(DIGEST_SYSTEM, prompt, cfg)
    if result:
        return result

    api_key = _read_env_key(cfg)
    if api_key:
        result = _synthesise_via_sdk(DIGEST_SYSTEM, prompt, api_key, cfg)
        if result:
            return result

    # Fallback: raw summary
    return f"*Ben check-in summary*\n\n{context[:800]}\n\n🔴"


def setup_checkin_task(cfg: Config, cron_expr: str = "0 19 * * *") -> Path:
    """Write an IPC task file to schedule the daily check-in in Ben's microhal.

    This creates a scheduled_task IPC message that the host picks up and
    registers in the task scheduler. Runs in Ben's microhal container.

    Args:
        cfg: Briefing config (for IPC paths).
        cron_expr: Cron expression for when to trigger (default: 7pm daily).

    Returns:
        Path of the written IPC file.
    """
    import os
    import time

    questions_text = "\n".join(f"- {q}" for q in CHECKIN_QUESTIONS)
    prompt = CHECKIN_PROMPT.format(questions=questions_text)

    tasks_dir = cfg.ipc_dir / cfg.ipc_group / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "type": "schedule_task",
        "prompt": prompt,
        "schedule_type": "cron",
        "schedule_value": cron_expr,
        "context_mode": "group",
    }

    filename = f"checkin-setup-{int(time.time() * 1000)}.json"
    filepath = tasks_dir / filename

    tmp = filepath.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(str(tmp), str(filepath))

    return filepath
