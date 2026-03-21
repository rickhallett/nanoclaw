"""Token usage reader for api-usage.jsonl files."""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Anthropic pricing per million tokens (as of 2025-05)
# https://docs.anthropic.com/en/docs/about-claude/models
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
    # Fallback for unknown models
    "_default": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
}


def _get_pricing(model: str) -> dict:
    """Look up pricing for a model, falling back to default."""
    for key in PRICING:
        if key != "_default" and key in model:
            return PRICING[key]
    # Try prefix matching (e.g. "claude-sonnet-4" matches "claude-sonnet-4-20250514")
    for key in PRICING:
        if key != "_default" and model.startswith(key.rsplit("-", 1)[0]):
            return PRICING[key]
    return PRICING["_default"]


def _cost(event: dict) -> float:
    """Calculate cost in USD for a single usage event."""
    p = _get_pricing(event.get("model", ""))
    return (
        event.get("input_tokens", 0) * p["input"] / 1_000_000
        + event.get("output_tokens", 0) * p["output"] / 1_000_000
        + event.get("cache_read_input_tokens", 0) * p["cache_read"] / 1_000_000
        + event.get("cache_creation_input_tokens", 0) * p["cache_write"] / 1_000_000
    )


def read_usage(usage_path: Path, since: str = "") -> list[dict]:
    """Read and optionally filter usage events from a JSONL file."""
    if not usage_path.exists():
        return []

    cutoff = None
    if since:
        now = datetime.now(timezone.utc)
        if since.endswith("h"):
            cutoff = now - timedelta(hours=int(since[:-1]))
        elif since.endswith("d"):
            cutoff = now - timedelta(days=int(since[:-1]))

    events = []
    for line in usage_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if cutoff:
            ts = event.get("ts", "")
            try:
                event_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if event_time < cutoff:
                    continue
            except (ValueError, AttributeError):
                continue

        event["cost_usd"] = _cost(event)
        events.append(event)

    return events


def summarize(events: list[dict], by: str = "group") -> dict:
    """Aggregate usage events into a summary."""
    totals = defaultdict(lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost_usd": 0.0,
        "requests": 0,
    })

    for e in events:
        key = e.get(by, "unknown")
        t = totals[key]
        t["input_tokens"] += e.get("input_tokens", 0)
        t["output_tokens"] += e.get("output_tokens", 0)
        t["cache_read_tokens"] += e.get("cache_read_input_tokens", 0)
        t["cache_write_tokens"] += e.get("cache_creation_input_tokens", 0)
        t["cost_usd"] += e.get("cost_usd", 0.0)
        t["requests"] += 1

    grand = {
        "input_tokens": sum(t["input_tokens"] for t in totals.values()),
        "output_tokens": sum(t["output_tokens"] for t in totals.values()),
        "cache_read_tokens": sum(t["cache_read_tokens"] for t in totals.values()),
        "cache_write_tokens": sum(t["cache_write_tokens"] for t in totals.values()),
        "cost_usd": sum(t["cost_usd"] for t in totals.values()),
        "requests": sum(t["requests"] for t in totals.values()),
    }

    return {"by": dict(totals), "total": grand}
