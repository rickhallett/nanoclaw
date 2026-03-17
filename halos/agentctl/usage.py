"""Enrich session records with API usage data from the credential proxy.

The credential proxy writes one JSONL line per API call to data/api-usage.jsonl.
This module reads those lines and matches them to sessions by time window
(usage events that fall between session.started and session.finished).
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .session import Session


# Claude API pricing (USD per million tokens) — updated 2026-03
# https://docs.anthropic.com/en/docs/about-claude/models
PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_write": 18.75},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00, "cache_read": 0.08, "cache_write": 1.00},
    # Fallback for unknown models
    "_default": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
}


@dataclass
class UsageEvent:
    ts: datetime
    path: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


def load_usage_events(usage_log: str) -> list[UsageEvent]:
    """Read all usage events from the JSONL file."""
    p = Path(usage_log)
    if not p.exists():
        return []

    events = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            ts = datetime.fromisoformat(raw["ts"].replace("Z", "+00:00"))
            events.append(UsageEvent(
                ts=ts,
                path=raw.get("path", ""),
                model=raw.get("model", "unknown"),
                input_tokens=int(raw.get("input_tokens", 0)),
                output_tokens=int(raw.get("output_tokens", 0)),
                cache_creation_input_tokens=int(raw.get("cache_creation_input_tokens", 0)),
                cache_read_input_tokens=int(raw.get("cache_read_input_tokens", 0)),
            ))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue

    return sorted(events, key=lambda e: e.ts)


def compute_cost(model: str, input_tokens: int, output_tokens: int,
                 cache_read: int, cache_write: int) -> float:
    """Compute USD cost from token counts and model pricing."""
    # Match model by prefix (e.g. "claude-sonnet-4-6-20260301" → "claude-sonnet-4-6")
    prices = PRICING.get("_default")
    for key in PRICING:
        if key != "_default" and model.startswith(key):
            prices = PRICING[key]
            break

    return (
        input_tokens * prices["input"] / 1_000_000
        + output_tokens * prices["output"] / 1_000_000
        + cache_read * prices["cache_read"] / 1_000_000
        + cache_write * prices["cache_write"] / 1_000_000
    )


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def enrich_session(session: Session, events: list[UsageEvent]) -> Session:
    """Attach usage data to a session by matching events within its time window."""
    started = _parse_dt(session.started)
    finished = _parse_dt(session.finished)

    # Find all usage events that fall within this session's time window
    matched = [e for e in events if started <= e.ts <= finished]

    if not matched:
        return session

    # Aggregate across all API calls in this session
    session.input_tokens = sum(e.input_tokens for e in matched)
    session.output_tokens = sum(e.output_tokens for e in matched)
    session.cache_read_tokens = sum(e.cache_read_input_tokens for e in matched)
    session.cache_write_tokens = sum(e.cache_creation_input_tokens for e in matched)

    # Use the model from the last API call (most likely the primary model)
    session.model = matched[-1].model

    session.total_cost_usd = compute_cost(
        session.model,
        session.input_tokens,
        session.output_tokens,
        session.cache_read_tokens,
        session.cache_write_tokens,
    )

    return session
