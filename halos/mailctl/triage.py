"""triage — inbox triage rules for mailctl.

Each rule is a function that takes a message dict and returns a TriageAction.
Rules run in priority order; first match wins.

TODO(kai): Define your triage rules here. The structure is ready —
the interesting question is: what's your signal-to-noise boundary?

Consider:
  - VIP senders (always surface)
  - Automated notifications (archive or label)
  - Newsletter patterns (batch for weekly review)
  - Time-sensitive keywords (urgent, deploy, incident)
  - Thread depth (long threads you're CC'd on → lower priority)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Action(Enum):
    SURFACE = "surface"       # show in briefing, keep unread
    ARCHIVE = "archive"       # mark read, move to archive
    LABEL = "label"           # apply label, keep in inbox
    SKIP = "skip"             # no action, next rule


@dataclass
class TriageResult:
    action: Action
    reason: str
    label: Optional[str] = None


# --- Rules (evaluated in order, first match wins) ---

def _rule_vip(msg: dict) -> Optional[TriageResult]:
    """Surface messages from VIP senders."""
    # TODO: your VIP list
    vips: set[str] = set()
    sender = msg.get("from", {}).get("addr", "").lower()
    if sender in vips:
        return TriageResult(Action.SURFACE, f"VIP sender: {sender}")
    return None


def _rule_automated(msg: dict) -> Optional[TriageResult]:
    """Archive known automated senders."""
    # TODO: your noise list
    noise_patterns: list[str] = []
    sender = msg.get("from", {}).get("addr", "").lower()
    for pattern in noise_patterns:
        if pattern in sender:
            return TriageResult(Action.ARCHIVE, f"Automated: {pattern}")
    return None


# Rule registry — order matters
RULES = [
    _rule_vip,
    _rule_automated,
]


def triage(msg: dict) -> TriageResult:
    """Run triage rules against a message. Default: SURFACE."""
    for rule in RULES:
        result = rule(msg)
        if result is not None and result.action != Action.SKIP:
            return result
    return TriageResult(Action.SURFACE, "no rule matched — default surface")


def run_triage(messages: list[dict], dry_run: bool = True) -> list[dict]:
    """Triage a batch of messages. Returns list of {message, result} dicts."""
    results = []
    for msg in messages:
        result = triage(msg)
        results.append({
            "message_id": msg.get("id"),
            "from": msg.get("from", {}).get("addr", "unknown"),
            "subject": msg.get("subject", "(no subject)"),
            "action": result.action.value,
            "reason": result.reason,
        })
    return results
