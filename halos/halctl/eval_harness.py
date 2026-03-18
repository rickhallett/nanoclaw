"""Assessment eval harness — structured tests for agent behaviour under varied conditions.

Unlike smoke tests (binary pass/fail), the harness captures the full context
of an agent interaction for later analysis. Each run produces a structured
YAML record: what was asked, under what conditions, what the agent did,
and whether it met expectations.

Usage:
    halctl assess <instance> --scenario <name>
    halctl assess <instance> --all
"""

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    from halos.nightctl import yaml_shim as yaml

from halos.common.log import hlog
from .config import load_fleet_manifest, fleet_dir
from .provision import OPERATOR_CHAT_JID
from .smoke import _connect_db, _inject_message, _wait_for_response, _count_log_lines


class AssessRecord:
    """A single assessment run with full context."""

    def __init__(self, instance: str, scenario: str):
        self.record_id = f"assess-{uuid.uuid4().hex[:8]}"
        self.instance = instance
        self.scenario = scenario
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.conditions: dict = {}
        self.prompt = ""
        self.response = ""
        self.behaviour: dict = {}
        self.assertions: list[dict] = []

    def assert_check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.assertions.append({"name": name, "passed": passed, "detail": detail})
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {name}" + (f"  ({detail})" if detail else ""))
        return passed

    @property
    def passed(self) -> bool:
        return all(a["passed"] for a in self.assertions)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "instance": self.instance,
            "scenario": self.scenario,
            "timestamp": self.timestamp,
            "conditions": self.conditions,
            "prompt": self.prompt,
            "response": self.response,
            "behaviour": self.behaviour,
            "assertions": self.assertions,
            "passed": self.passed,
        }


def _get_conversation_count(conn: sqlite3.Connection, sender_id: str, chat_jid: str) -> int:
    """Count distinct 'sessions' by looking at message gaps > 30 min."""
    rows = conn.execute(
        "SELECT timestamp FROM messages WHERE sender = ? AND chat_jid = ? ORDER BY timestamp",
        (sender_id, chat_jid),
    ).fetchall()
    if not rows:
        return 0
    count = 1
    prev = rows[0][0]
    for (ts,) in rows[1:]:
        try:
            from datetime import datetime as dt
            t1 = dt.fromisoformat(prev.replace("Z", "+00:00"))
            t2 = dt.fromisoformat(ts.replace("Z", "+00:00"))
            if (t2 - t1).total_seconds() > 1800:
                count += 1
        except (ValueError, TypeError):
            pass
        prev = ts
    return count


def _seed_conversations(conn: sqlite3.Connection, chat_jid: str, sender_id: str, count: int) -> None:
    """Inject synthetic conversation history to simulate N prior conversations."""
    from datetime import timedelta
    base = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(count):
        ts = (base + timedelta(hours=i * 2)).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO messages (id, chat_jid, sender, sender_name, content, timestamp, is_from_me, is_bot_message) VALUES (?, ?, ?, ?, ?, ?, 0, 0)",
            (f"seed-{i}-user", chat_jid, sender_id, "Assess User", f"conversation {i} message", ts),
        )
        ts_reply = (base + timedelta(hours=i * 2, minutes=1)).isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO messages (id, chat_jid, sender, sender_name, content, timestamp, is_from_me, is_bot_message) VALUES (?, ?, ?, ?, ?, ?, 1, 0)",
            (f"seed-{i}-bot", chat_jid, "HAL", "HAL", f"response to conversation {i}", ts_reply),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_likert_delivery(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: does the agent deliver Likert questions during first real conversation?"""
    rec = AssessRecord("", "likert_delivery")
    rec.conditions = {
        "onboarding_state": "active",
        "likert_complete": False,
        "conversation_count": 0,
    }

    rec.prompt = "@HAL hello, I'm new here"
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    # collect_all: agent may greet first, then ask Likert in follow-up messages
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout, collect_all=True) or ""

    response_lower = rec.response.lower()
    rec.behaviour = {
        "mentioned_questions": "question" in response_lower or "scale" in response_lower or "1" in rec.response,
        "mentioned_rick": "rick" in response_lower,
        "was_warm": any(w in response_lower for w in ["welcome", "hello", "hi", "glad"]),
    }

    rec.assert_check(
        "initiates_assessment",
        rec.behaviour["mentioned_questions"],
        rec.response[:100],
    )
    rec.assert_check(
        "warm_tone",
        rec.behaviour["was_warm"] or len(rec.response) > 20,
        "response has conversational warmth",
    )

    return rec


def scenario_qualitative_not_too_early(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: agent should NOT ask qualitative questions before 3 conversations."""
    rec = AssessRecord("", "qualitative_not_too_early")

    _seed_conversations(conn, OPERATOR_CHAT_JID, "5967394003", 1)
    conv_count = _get_conversation_count(conn, "5967394003", OPERATOR_CHAT_JID)

    rec.conditions = {
        "conversation_count": conv_count,
        "likert_complete": True,
        "qualitative_pre_complete": False,
    }

    rec.prompt = "@HAL that was really helpful, thanks"
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout) or ""

    response_lower = rec.response.lower()
    asked_qualitative = any(
        phrase in response_lower
        for phrase in ["hope this will help", "feel about ai", "couple of questions", "rick asked"]
    )
    rec.behaviour = {"asked_qualitative": asked_qualitative}

    rec.assert_check(
        "should_not_ask_qualitative_early",
        not asked_qualitative,
        f"conv_count={conv_count}, asked={asked_qualitative}",
    )

    return rec


def scenario_qualitative_dropin_eligible(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: agent behaviour when eligible to ask qualitative questions (3-7 conversations)."""
    rec = AssessRecord("", "qualitative_dropin_eligible")

    _seed_conversations(conn, OPERATOR_CHAT_JID, "5967394003", 5)
    conv_count = _get_conversation_count(conn, "5967394003", OPERATOR_CHAT_JID)

    rec.conditions = {
        "conversation_count": conv_count,
        "likert_complete": True,
        "qualitative_pre_complete": False,
        "session_context": "user just completed a task, natural pause",
    }

    rec.prompt = "@HAL thanks, that was exactly what I needed. Quiet day otherwise."
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout) or ""

    response_lower = rec.response.lower()
    asked_qualitative = any(
        phrase in response_lower
        for phrase in ["hope this will help", "feel about ai", "couple of questions", "rick asked", "good time"]
    )
    asked_permission = any(
        phrase in response_lower
        for phrase in ["good time", "is now", "would you", "mind if", "before i forget"]
    )

    rec.behaviour = {
        "asked_qualitative": asked_qualitative,
        "asked_permission_first": asked_permission,
    }

    # Soft assertion — characterising, not gatekeeping
    rec.assert_check(
        "eligible_and_aware",
        True,
        f"asked={asked_qualitative}, permission={asked_permission}",
    )
    if asked_qualitative:
        rec.assert_check(
            "asked_permission_first",
            asked_permission,
            "should ask before launching into questions",
        )

    return rec


def scenario_no_interrupt_during_task(
    conn: sqlite3.Connection,
    deploy_path: Path,
    pm2_log: Path,
    timeout: float,
) -> AssessRecord:
    """Test: agent should NOT ask assessment questions mid-task."""
    rec = AssessRecord("", "no_interrupt_during_task")

    _seed_conversations(conn, OPERATOR_CHAT_JID, "5967394003", 5)

    rec.conditions = {
        "conversation_count": 5,
        "likert_complete": True,
        "qualitative_pre_complete": False,
        "session_context": "user is mid-task, actively requesting help",
    }

    rec.prompt = "@HAL can you help me draft a message to my boss about taking next Friday off?"
    before_lines = _count_log_lines(pm2_log)
    _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Assess User", rec.prompt)
    rec.response = _wait_for_response(pm2_log, before_lines, timeout=timeout) or ""

    response_lower = rec.response.lower()
    asked_qualitative = any(
        phrase in response_lower
        for phrase in ["hope this will help you with", "feel about ai", "couple of questions rick asked"]
    )
    helped_with_task = any(
        phrase in response_lower
        for phrase in ["friday", "boss", "day off", "time off", "draft", "message", "context", "tone", "formal", "sure", "help"]
    )

    rec.behaviour = {
        "asked_qualitative": asked_qualitative,
        "helped_with_task": helped_with_task,
    }

    rec.assert_check(
        "should_not_interrupt_task",
        not asked_qualitative,
        f"asked_qualitative={asked_qualitative}",
    )
    rec.assert_check(
        "should_help_with_task",
        helped_with_task,
        rec.response[:100],
    )

    return rec


# ---------------------------------------------------------------------------
# Registry and runner
# ---------------------------------------------------------------------------

SCENARIOS = {
    "likert_delivery": scenario_likert_delivery,
    "qualitative_not_too_early": scenario_qualitative_not_too_early,
    "qualitative_dropin_eligible": scenario_qualitative_dropin_eligible,
    "no_interrupt_during_task": scenario_no_interrupt_during_task,
}


def run_assessment(
    name: str,
    scenarios: list[str] | None = None,
    timeout: float = 60.0,
    fleet_base: Path | None = None,
) -> list[AssessRecord]:
    """Run assessment scenarios against a live instance. Returns list of AssessRecords."""
    base_dir = fleet_base or fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)

    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == name:
            instance = inst
            break

    if instance is None:
        raise ValueError(f"instance not found: {name}")

    deploy_path = Path(instance["path"])
    conn = _connect_db(deploy_path)
    pm2_log = Path.home() / ".pm2" / "logs" / f"microhal-{name}-out.log"

    to_run = scenarios or list(SCENARIOS.keys())
    records = []

    for scenario_name in to_run:
        if scenario_name not in SCENARIOS:
            print(f"  SKIP: unknown scenario '{scenario_name}'")
            continue

        print(f"\n  --- {scenario_name} ---")
        fn = SCENARIOS[scenario_name]
        rec = fn(conn, deploy_path, pm2_log, timeout)
        rec.instance = name
        records.append(rec)

    conn.close()

    # Write records to disk
    records_dir = deploy_path / "data" / "assessments"
    records_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    for rec in records:
        out_path = records_dir / f"{ts}-{rec.scenario}.yaml"
        with open(out_path, "w") as f:
            yaml.dump(rec.to_dict(), f, default_flow_style=False, sort_keys=False)

    hlog("halctl", "info", "assessment_complete", {
        "name": name,
        "scenarios": len(records),
        "passed": sum(1 for r in records if r.passed),
        "failed": sum(1 for r in records if not r.passed),
    })

    return records
