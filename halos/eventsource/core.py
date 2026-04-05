"""Event sourcing primitives — Event envelope and NATS publisher."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import sqlite3

from ulid import ULID


@dataclass(frozen=True)
class Event:
    """Immutable event envelope."""

    id: str
    type: str
    version: int
    source: str
    timestamp: str
    correlation_id: str
    payload: dict[str, Any]
    stream_seq: int = 0

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": self.id,
                "type": self.type,
                "version": self.version,
                "source": self.source,
                "timestamp": self.timestamp,
                "correlation_id": self.correlation_id,
                "payload": self.payload,
            }
        )

    @classmethod
    def from_json(cls, data: str | bytes, stream_seq: int = 0) -> Event:
        d = json.loads(data)
        return cls(stream_seq=stream_seq, **d)

    def with_seq(self, stream_seq: int) -> Event:
        """Return a copy with a different stream_seq."""
        return Event(
            id=self.id,
            type=self.type,
            version=self.version,
            source=self.source,
            timestamp=self.timestamp,
            correlation_id=self.correlation_id,
            payload=self.payload,
            stream_seq=stream_seq,
        )

    @classmethod
    def create(
        cls,
        type: str,
        source: str,
        payload: dict[str, Any],
        version: int = 1,
        correlation_id: str | None = None,
    ) -> Event:
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=f"evt_{ULID()}",
            type=type,
            version=version,
            source=source,
            timestamp=now,
            correlation_id=correlation_id or f"cor_{ULID()}",
            payload=payload,
        )


class EventPublisher:
    """Publishes events to NATS JetStream."""

    def __init__(self, nc: Any, stream: str = "HALO", source: str = "unknown"):
        self._nc = nc
        self._js = nc.jetstream()
        self._stream = stream
        self._source = source

    async def publish(self, event: Event) -> None:
        subject = f"halo.{event.type}"
        await self._js.publish(
            subject,
            event.to_json().encode(),
            headers={"Nats-Msg-Id": event.id},
        )

    async def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        version: int = 1,
        correlation_id: str | None = None,
    ) -> Event:
        event = Event.create(
            type=event_type,
            source=self._source,
            payload=payload,
            version=version,
            correlation_id=correlation_id,
        )
        await self.publish(event)
        return event


class ProjectionHandler(ABC):
    """Base class for event handlers that update a projection."""

    @abstractmethod
    def handles(self) -> list[str]:
        """Return list of event types this handler processes."""
        ...

    @abstractmethod
    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        """Apply event to the projection database."""
        ...

    def init_schema(self, db: sqlite3.Connection) -> None:
        """Create tables if they don't exist. Called once on startup."""
        pass
