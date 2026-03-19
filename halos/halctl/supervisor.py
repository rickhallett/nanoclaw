"""Supervisor — periodic conversation monitor for fleet instances.

Reads recent messages from an instance's SQLite DB, applies deterministic
heuristic triggers, and sends interventions via the Telegram Bot API.
Logs all decisions to a dedicated logctl stream.

Run via cron or manually:
    halctl supervise ben
    halctl supervise --all

Triggers fire at most once per session (30-min gap = new session).
"""

import json
import re
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from halos.common.log import hlog
from .config import load_fleet_manifest, fleet_dir


# ---------------------------------------------------------------------------
# Logging — dedicated stream for logctl
# ---------------------------------------------------------------------------

LOG_DIR = Path.home() / "code" / "nanoclaw" / "logs"

def _supervisor_log(instance: str, level: str, event: str, data: dict = None):
    """Write structured log line to supervisor log file + hlog."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "supervisor.log"

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "source": f"supervisor/{instance}",
        "event": event,
        "data": data or {},
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    hlog("supervisor", level, event, {"instance": instance, **(data or {})})


# ---------------------------------------------------------------------------
# Message reading
# ---------------------------------------------------------------------------

def _read_recent_messages(db_path: Path, minutes: int = 30) -> list[dict]:
    """Read messages from the last N minutes."""
    if not db_path.exists():
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT id, sender_name, content, timestamp, is_from_me
               FROM messages WHERE timestamp > ? ORDER BY timestamp ASC""",
            (cutoff,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        _supervisor_log("unknown", "error", "db_read_failed", {"error": str(e)})
        return []


def _read_agent_outputs(instance: str, minutes: int = 30) -> list[dict]:
    """Read recent agent outputs from pm2 log."""
    pm2_log = Path.home() / ".pm2" / "logs" / f"microhal-{instance}-out.log"
    if not pm2_log.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    ts_re = re.compile(r"^\[(\d{2}:\d{2}:\d{2}\.\d{3})\]")
    output_re = re.compile(r"Agent output: (.+)")

    outputs = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT")

    try:
        for line in pm2_log.read_text(errors="replace").splitlines():
            clean = ansi_re.sub("", line)
            m = output_re.search(clean)
            if m:
                ts_match = ts_re.match(clean)
                if ts_match:
                    ts_str = f"{today}{ts_match.group(1)}Z"
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts >= cutoff:
                            outputs.append({
                                "timestamp": ts_str,
                                "content": m.group(1).strip(),
                            })
                    except ValueError:
                        pass
    except Exception:
        pass

    return outputs


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------

FOLD_PHRASES = [
    "fair enough", "fair point", "you might be right", "you may be right",
    "that's valid", "good point", "i stand corrected", "you're right",
    "i take that back", "my mistake",
]

CHALLENGE_PHRASES = [
    "what makes you say", "what do you mean", "be more specific",
    "walk me through", "how do you know", "who told you that",
    "is that what actually happened", "that's a strong claim",
    "reads like ai output", "this reads like ai",
]

DEPARTURE_PHRASES = [
    "i need to go", "im going to", "i must get away", "going to sleep",
    "off now", "i'll be back", "brb", "taking a break", "going to meditate",
    "going to eat", "sort my flat", "do everything else",
]


def detect_fold_after_challenge(messages: list[dict], agent_outputs: list[dict]) -> dict | None:
    """Detect: agent challenged → user pushed back → agent folded."""
    # Look for agent challenge followed by agent fold in outputs
    for i in range(len(agent_outputs) - 1):
        current = agent_outputs[i]["content"].lower()
        is_challenge = any(p in current for p in CHALLENGE_PHRASES)

        if is_challenge and i + 1 < len(agent_outputs):
            next_out = agent_outputs[i + 1]["content"].lower()
            is_fold = any(p in next_out for p in FOLD_PHRASES)
            if is_fold:
                return {
                    "trigger": "fold_after_challenge",
                    "challenge": agent_outputs[i]["content"][:100],
                    "fold": agent_outputs[i + 1]["content"][:100],
                    "timestamp": agent_outputs[i + 1]["timestamp"],
                }
    return None


def detect_departure_return(messages: list[dict], agent_outputs: list[dict] = None) -> dict | None:
    """Detect: user announced departure, returned within 10 min with new topic."""
    user_msgs = [m for m in messages if not m["is_from_me"]]
    agent_outputs = agent_outputs or []

    for i, msg in enumerate(user_msgs):
        content_lower = msg["content"].lower()
        is_departure = any(p in content_lower for p in DEPARTURE_PHRASES)

        if is_departure:
            departure_ts = msg["timestamp"]
            for j in range(i + 1, len(user_msgs)):
                next_msg = user_msgs[j]
                try:
                    t1 = datetime.fromisoformat(departure_ts.replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(next_msg["timestamp"].replace("Z", "+00:00"))
                    gap = (t2 - t1).total_seconds()
                    if 30 < gap < 600:
                        # Find agent response between departure and return
                        agent_response = ""
                        for out in agent_outputs:
                            try:
                                t_out = datetime.fromisoformat(out["timestamp"].replace("Z", "+00:00"))
                                if t1 < t_out < t2:
                                    agent_response = out["content"][:150]
                                    break
                            except (ValueError, TypeError):
                                pass
                        return {
                            "trigger": "departure_return",
                            "departure_msg": msg["content"][:150],
                            "agent_response": agent_response,
                            "return_msg": next_msg["content"][:150],
                            "gap_seconds": int(gap),
                            "timestamp": next_msg["timestamp"],
                        }
                except (ValueError, TypeError):
                    pass
                break
    return None


def detect_ai_paste_accepted(messages: list[dict], agent_outputs: list[dict]) -> dict | None:
    """Detect: large AI-style paste was accepted without flagging."""
    AI_MARKERS = ["leverage", "framework", "holistic", "comprehensive", "optimize",
                  "utilize", "facilitate", "streamline", "actionable", "strategic"]

    user_msgs = [m for m in messages if not m["is_from_me"]]

    for msg in user_msgs:
        content = msg["content"]
        if len(content) < 500:
            continue

        content_lower = content.lower()
        marker_count = sum(1 for m in AI_MARKERS if m in content_lower)
        if marker_count < 2:
            continue

        # Check if any agent output shortly after flagged it
        msg_ts = msg["timestamp"]
        was_flagged = False
        for out in agent_outputs:
            try:
                t1 = datetime.fromisoformat(msg_ts.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(out["timestamp"].replace("Z", "+00:00"))
                if 0 < (t2 - t1).total_seconds() < 120:
                    if any(p in out["content"].lower() for p in ["ai output", "reads like ai", "another conversation", "who told you"]):
                        was_flagged = True
                        break
            except (ValueError, TypeError):
                pass

        if not was_flagged:
            # Find what the agent actually said in response
            agent_response = ""
            for out in agent_outputs:
                try:
                    t1 = datetime.fromisoformat(msg_ts.replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(out["timestamp"].replace("Z", "+00:00"))
                    if 0 < (t2 - t1).total_seconds() < 120:
                        agent_response = out["content"][:150]
                        break
                except (ValueError, TypeError):
                    pass
            return {
                "trigger": "ai_paste_accepted",
                "paste_preview": content[:150],
                "agent_response": agent_response,
                "marker_count": marker_count,
                "timestamp": msg_ts,
            }
    return None


TRIGGERS = [
    ("fold_after_challenge", detect_fold_after_challenge),
    ("departure_return", detect_departure_return),
    ("ai_paste_accepted", detect_ai_paste_accepted),
]


# ---------------------------------------------------------------------------
# Intervention
# ---------------------------------------------------------------------------

INTERVENTION_MESSAGES = {
    "fold_after_challenge": "[Supervisor] The agent just backed down from a valid challenge. The original question still stands. Don't let it slide.",
    "departure_return": "[Supervisor] You said you were going to do something important, then came back to chat instead. What was the important thing?",
    "ai_paste_accepted": "[Supervisor] A large block of AI-generated text just went through without being questioned. Not everything AI tells you is true. What in that text have you actually verified?",
}


def _send_telegram(token: str, chat_id: str, text: str) -> bool:
    """Send a message via Telegram Bot API."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        return r.json().get("ok", False)
    except Exception:
        return False


def _get_bot_token(instance_path: Path) -> str:
    """Read bot token from .env.token."""
    token_path = instance_path.parent / ".env.token"
    if token_path.exists():
        return token_path.read_text().strip()
    return ""


def _get_chat_jid(db_path: Path) -> str:
    """Get the main group JID from the DB."""
    try:
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT jid FROM registered_groups WHERE is_main = 1 LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# State tracking — prevent trigger spam
# ---------------------------------------------------------------------------

def _state_path(instance: str) -> Path:
    return Path.home() / "code" / "nanoclaw" / "data" / "supervisor" / f"{instance}.json"


def _load_state(instance: str) -> dict:
    path = _state_path(instance)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"last_triggers": {}}


def _save_state(instance: str, state: dict):
    path = _state_path(instance)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def _can_fire(state: dict, trigger_name: str, cooldown_minutes: int = 30) -> bool:
    """Check if a trigger can fire (respects cooldown)."""
    last = state.get("last_triggers", {}).get(trigger_name)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - last_dt).total_seconds() > cooldown_minutes * 60
    except (ValueError, TypeError):
        return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def supervise_instance(name: str, window_minutes: int = 30) -> list[dict]:
    """Run supervisor checks on a single instance. Returns fired triggers."""
    base_dir = fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)

    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == name and inst.get("status") == "active":
            instance = inst
            break

    if not instance:
        _supervisor_log(name, "warn", "instance_not_found")
        return []

    deploy = Path(instance["path"])
    db_path = deploy / "store" / "messages.db"

    messages = _read_recent_messages(db_path, minutes=window_minutes)
    agent_outputs = _read_agent_outputs(name, minutes=window_minutes)

    if not messages:
        _supervisor_log(name, "info", "no_recent_messages")
        return []

    _supervisor_log(name, "info", "sweep_start", {
        "messages": len(messages),
        "agent_outputs": len(agent_outputs),
        "window_minutes": window_minutes,
    })

    state = _load_state(name)
    fired = []

    for trigger_name, detect_fn in TRIGGERS:
        if not _can_fire(state, trigger_name):
            continue

        result = detect_fn(messages, agent_outputs)

        if result:
            _supervisor_log(name, "warn", "trigger_fired", result)

            # Send intervention
            token = _get_bot_token(deploy)
            chat_jid = _get_chat_jid(db_path)
            chat_id = chat_jid.replace("tg:", "")

            if token and chat_id:
                msg = INTERVENTION_MESSAGES.get(trigger_name, "")
                if msg:
                    sent = _send_telegram(token, chat_id, msg)
                    _supervisor_log(name, "info", "intervention_sent", {
                        "trigger": trigger_name,
                        "sent": sent,
                    })

            # Update cooldown
            state.setdefault("last_triggers", {})[trigger_name] = \
                datetime.now(timezone.utc).isoformat()
            fired.append(result)

    _save_state(name, state)

    _supervisor_log(name, "info", "sweep_complete", {
        "triggers_fired": len(fired),
    })

    return fired


def supervise_all(window_minutes: int = 30) -> dict[str, list[dict]]:
    """Run supervisor on all active instances."""
    manifest = load_fleet_manifest()
    results = {}
    for inst in manifest.get("instances", []):
        if inst.get("status") == "active":
            results[inst["name"]] = supervise_instance(inst["name"], window_minutes)
    return results
