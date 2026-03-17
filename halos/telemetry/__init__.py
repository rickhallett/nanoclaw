"""BATHW telemetry — structured event emission for halos modules.

Usage:
    from halos.telemetry import emit
    emit("agentctl", "session_ended", {"session_id": "...", "tokens": 1234})

Events are written to:
  1. ClickHouse via HTTP insert (if BATHW_CLICKHOUSE_URL is set)
  2. Structured JSON log line via hlog (always, as fallback)

Never blocks the caller. Never fails loudly.
"""

from .emitter import emit, configure

__all__ = ["emit", "configure"]
