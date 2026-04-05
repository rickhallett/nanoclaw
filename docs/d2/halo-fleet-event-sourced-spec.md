---
title: "Halo Fleet: Event-Sourced Multi-Agent Architecture"
category: spec
status: draft
created: 2026-04-05
---

# Halo Fleet: Event-Sourced Multi-Agent Architecture

Technical specification for the Halo advisory fleet as an event-sourced distributed system on Vultr VKE. Supersedes `halo-k8s-advisor-migration-spec.md`.

## Status

Draft. Not yet reviewed. Written against codebase state as of 2026-04-05.

## Scope

Deploy 7 advisors (Musashi, Seneca, Socrates, Sun Tzu, Machiavelli, Medici, Bankei) and 1 dramaturg (Plutarch) as long-running Hermes gateway instances on Vultr VKE. Each advisor is a full Hermes gateway with the complete halos module arsenal. All share state through a NATS JetStream event stream — the stream is the system's nervous system.

**Telegram is the human interface.** Kai interacts with advisors via Telegram. Advisors publish events to the stream from within the cluster. The MacBook has no direct connection to NATS — it is outside the cluster topology.

**Key architectural decisions:** CronJobs are replaced by long-running Deployments. Litestream replication is replaced by event sourcing. Shared PVCs are replaced by disposable local projections rebuilt from the stream. Releases are standard k8s rollouts.

---

## 1. Foundational Concepts

### 1.1 Event Sourcing

Every meaningful action in the system produces an immutable event on the NATS JetStream stream. The stream is the single source of truth. All other state (SQLite databases, YAML files, in-memory caches) is a projection — a disposable read model derived from the event log.

### 1.2 CQRS (Command Query Responsibility Segregation)

- **Write path:** Telegram message → advisor processes → publish event to stream
- **Read path:** Query → read from local projection (SQLite)

Writers don't wait for consumers. Consumers build their own view of the world.

### 1.3 Choreography, Not Orchestration

No central coordinator. Each advisor reacts to events it cares about. The evening council emerges from sequential reactions, not from a conductor.

### 1.4 Disposable Pods

Kill any pod. It restarts, replays from its last checkpoint on the stream, rebuilds its projection, and resumes. Zero manual intervention.

---

## 2. Event Schema Design

### 2.1 Event Envelope

Every event on the stream uses this envelope:

```json
{
  "id": "evt_01J5XKQR7M3FVGS8T92BWHNC4P",
  "type": "track.movement.logged",
  "version": 1,
  "source": "musashi",
  "timestamp": "2026-04-05T07:12:34.567Z",
  "correlation_id": "cor_01J5XKQR7M3FVGS8T92BWHNC4Q",
  "payload": {
    "domain": "movement",
    "duration_mins": 45,
    "notes": "Morning run, 5km",
    "entry_id": 342
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | ULID string | Globally unique, sortable. Prefix `evt_`. |
| `type` | string | Dot-delimited event type. Matches NATS subject suffix. |
| `version` | int | Schema version for this event type. Starts at 1. |
| `source` | string | Identifier of the producer. One of: `hq`, `musashi`, `seneca`, `socrates`, `sun-tzu`, `machiavelli`, `medici`, `bankei`, `plutarch`. |
| `timestamp` | ISO 8601 | When the event occurred (not when it was published). |
| `correlation_id` | ULID string | Groups related events. A user action that triggers multiple events shares one correlation_id. |
| `payload` | object | Event-type-specific data. Schema defined per event type. |

### 2.2 Event Taxonomy

#### Domain Events

| Event Type | Published By | Payload Schema | Description |
|------------|-------------|----------------|-------------|
| `track.movement.logged` | any advisor | `{domain, duration_mins, notes, entry_id}` | Movement session recorded |
| `track.zazen.logged` | any advisor | `{domain, duration_mins, notes, entry_id}` | Zazen session recorded |
| `track.study.logged` | any advisor | `{domain, duration_mins, notes, entry_id, sub_domain}` | Study session recorded (neetcode, crafters, source) |
| `track.entry.deleted` | any advisor | `{domain, entry_id}` | Track entry removed |
| `track.entry.edited` | any advisor | `{domain, entry_id, duration_mins?, notes?}` | Track entry modified |
| `night.item.created` | any advisor | `{item_id, title, quadrant, kind, tags}` | Nightctl item created |
| `night.item.transitioned` | any advisor | `{item_id, from_status, to_status}` | Item state change |
| `night.item.updated` | any advisor | `{item_id, fields_changed}` | Item metadata updated |
| `night.job.completed` | any advisor | `{job_id, result, duration_secs}` | Overnight job finished |
| `night.job.failed` | any advisor | `{job_id, error, duration_secs}` | Overnight job failed |
| `mem.note.created` | any advisor | `{note_id, entity, tags, summary}` | Memory note added |
| `mem.note.deleted` | any advisor | `{note_id, entity}` | Memory note removed |
| `mem.index.rebuilt` | any advisor | `{note_count, entity_count}` | Index rebuilt |
| `journal.entry.added` | any advisor | `{entry_id, tags, source, mood, energy}` | Journal entry recorded |
| `journal.window.synthesised` | any advisor | `{days, hash, summary_length}` | Journal window cache updated |
| `commits.pushed` | any advisor | `{repos: [{name, count, commits}], total, period}` | Git activity aggregated (polled from GitHub API) |
| `advisor.delivered` | any advisor | `{advisor, chat_id, message_length, model, tokens_used}` | Advisor message sent to Telegram |
| `advisor.profile.updated` | any advisor | `{advisor, diff_summary}` | Advisor profile updated |
| `briefing.composed` | any advisor | `{kind, advisor, agents_included}` | Briefing synthesised |
| `cal.event.created` | any advisor | `{event_id, title, start, end}` | Calendar event |
| `cal.event.updated` | any advisor | `{event_id, fields_changed}` | Calendar event changed |
| `ledger.entry.added` | any advisor | `{entry_id, amount, category, description}` | Financial entry |
| `mail.triaged` | any advisor | `{message_id, label, action}` | Email triaged |

#### System Events

| Event Type | Published By | Payload Schema | Description |
|------------|-------------|----------------|-------------|
| `system.advisor.started` | any advisor | `{advisor, version, image_tag}` | Pod started and connected to stream |
| `system.advisor.stopped` | any advisor | `{advisor, reason, uptime_secs}` | Pod shutting down gracefully |
| `system.health.check` | any advisor | `{advisor, status, projection_lag, uptime_secs}` | Periodic health heartbeat |
| `system.stream.checkpoint` | any advisor | `{advisor, stream_seq, projection_rows}` | Stream position saved |
| `system.error` | any | `{source, error_type, message, stack_trace?}` | Error requiring attention |

#### Release Events

| Event Type | Published By | Payload Schema | Description |
|------------|-------------|----------------|-------------|
| `release.published` | hq | `{version, changelog, image_tag}` | New release deployed (informational) |

### 2.3 Event Versioning Strategy

Events are immutable once published. Schema evolution rules:

1. **Additive changes only.** New optional fields can be added to a payload without bumping the version. Consumers ignore unknown fields.
2. **Breaking changes** require a new event type version. Old consumers ignore unknown versions.
3. **On breaking change:** update all consumers (single image, single deploy), then replay from stream if projections need rebuilding.
4. **Tombstoning.** Deprecated event types are documented but never deleted from the stream. Consumers stop subscribing when ready.

---

## 3. NATS JetStream Topology

### 3.1 Stream Configuration

A single stream captures all Halo events:

```yaml
name: HALO
subjects:
  - "halo.>"
retention: limits
storage: file
max_bytes: 5368709120    # 5 GiB
max_age: 7776000000000000  # 90 days in nanoseconds
max_msg_size: 1048576    # 1 MiB per event
num_replicas: 1          # Single node (VKE has 1 worker)
discard: old
duplicate_window: 120000000000  # 2 minutes dedup window
allow_rollup_hdrs: true
```

### 3.2 Subject Hierarchy

```
halo.
  track.{movement,zazen,study}.logged
  track.entry.{deleted,edited}
  night.item.{created,transitioned,updated}
  night.job.{completed,failed}
  mem.{note.created,note.deleted,index.rebuilt}
  journal.{entry.added,window.synthesised}
  commits.pushed
  advisor.{delivered,profile.updated}
  advisor.<name>.delivered
  briefing.composed
  cal.event.{created,updated}
  ledger.entry.added
  mail.triaged
  system.advisor.{started,stopped}
  system.{health.check,stream.checkpoint,error}
  release.published
```

### 3.3 Consumer Configuration

Each advisor gets a durable pull consumer. Example for Musashi:

```yaml
name: musashi
durable_name: musashi
filter_subjects:
  - "halo.track.movement.>"
  - "halo.track.zazen.>"
  - "halo.journal.>"
  - "halo.advisor.musashi.>"
  - "halo.system.>"
  - "halo.release.>"
  - "halo.commits.>"
ack_policy: explicit
ack_wait: 30000000000          # 30 seconds
max_deliver: 3
deliver_policy: last
replay_policy: instant
max_ack_pending: 1000
inactive_threshold: 86400000000000  # 24h
```

**Plutarch** subscribes to `halo.>` (all events) with `max_ack_pending: 5000` and 60s ack wait.

### 3.4 Delivery Guarantees

**At-least-once delivery.** Every consumer must be idempotent. The `id` field (ULID) in the event envelope is the deduplication key.

```python
def handle_event(event: dict, db: sqlite3.Connection) -> None:
    """Idempotent event handler — safe to replay."""
    event_id = event["id"]

    existing = db.execute(
        "SELECT 1 FROM _processed_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()

    if existing:
        return

    _apply_event(event, db)

    db.execute(
        "INSERT INTO _processed_events (event_id, processed_at) VALUES (?, ?)",
        (event_id, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
```

### 3.5 NATS Deployment

```yaml
# k8s/nats/nats-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nats
  namespace: halo-fleet
  labels:
    app.kubernetes.io/name: nats
    app.kubernetes.io/part-of: halo
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: nats
  template:
    metadata:
      labels:
        app.kubernetes.io/name: nats
    spec:
      containers:
        - name: nats
          image: nats:2.10-alpine
          args:
            - "--jetstream"
            - "--store_dir=/data/jetstream"
            - "--config=/etc/nats/nats.conf"
          ports:
            - containerPort: 4222
              name: client
            - containerPort: 8222
              name: monitor
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: nats-data
              mountPath: /data
            - name: nats-config
              mountPath: /etc/nats
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8222
            initialDelaySeconds: 5
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8222
            initialDelaySeconds: 2
            periodSeconds: 10
      volumes:
        - name: nats-data
          persistentVolumeClaim:
            claimName: nats-data
        - name: nats-config
          configMap:
            name: nats-config
---
apiVersion: v1
kind: Service
metadata:
  name: nats
  namespace: halo-fleet
spec:
  selector:
    app.kubernetes.io/name: nats
  ports:
    - name: client
      port: 4222
    - name: monitor
      port: 8222
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: nats-data
  namespace: halo-fleet
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: vultr-block-storage-hdd
  resources:
    requests:
      storage: 10Gi
```

### 3.6 NATS Authentication

Two credential tiers. All traffic is cluster-internal — NATS is not exposed outside VKE.

```
# k8s/nats/nats.conf
listen: 0.0.0.0:4222
http: 0.0.0.0:8222

jetstream {
  store_dir: /data/jetstream
  max_mem: 256M
  max_file: 5G
}

authorization {
  users = [
    {user: "hq",      password: "$HQ_PASS",      permissions: {publish: "halo.>", subscribe: "halo.>"}}
    {user: "advisor",  password: "$ADVISOR_PASS",  permissions: {publish: "halo.>", subscribe: "halo.>"}}
  ]
}
```

Two users: `hq` for monitoring and release events, `advisor` shared by all advisor pods. Per-advisor credentials can be added later if the threat model changes, but all pods run the same image with the same code — scoped permissions add operational cost without meaningful security gain at this scale.

---

## 4. Projection Engine

### 4.1 Architecture

Each advisor maintains a local SQLite database as its projection — a disposable read model. On startup, the advisor replays events from its last checkpoint to rebuild the projection. On steady state, it processes events as they arrive.

```
Stream (NATS JetStream)
    │
    ▼
┌─────────────────────────────────┐
│  EventConsumer                   │
│  (pull from durable consumer)    │
│         │                        │
│         ▼                        │
│  EventRouter                     │
│  (dispatch by event type)        │
│         │                        │
│         ▼                        │
│  ProjectionHandlers              │
│  (per-domain: track, night, etc) │
│         │                        │
│         ▼                        │
│  SQLite (local projection)       │
│  /opt/data/projection.db         │
└─────────────────────────────────┘
```

### 4.2 Core Interfaces

```python
"""halos/eventsource/core.py — Event sourcing primitives."""

from __future__ import annotations
import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
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
        return json.dumps({
            "id": self.id,
            "type": self.type,
            "version": self.version,
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        })

    @classmethod
    def from_json(cls, data: str | bytes, stream_seq: int = 0) -> Event:
        d = json.loads(data)
        return cls(stream_seq=stream_seq, **d)

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

    def __init__(self, nc, stream: str = "HALO", source: str = "unknown"):
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
```

### 4.3 Projection Database

Each advisor's projection is a single SQLite file at `/opt/data/projection.db`. It contains:

1. **Domain tables** — rebuilt from events (track entries, nightctl items, journal entries, etc.)
2. **Checkpoint table** — tracks the last processed stream sequence number
3. **Processed events table** — for idempotency

```python
"""halos/eventsource/projection.py — Projection engine."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .core import Event, ProjectionHandler


class ProjectionEngine:
    """Manages the local projection database and event processing."""

    def __init__(self, db_path: Path, handlers: list[ProjectionHandler]):
        self._db_path = db_path
        self._handlers = handlers
        self._handler_map: dict[str, list[ProjectionHandler]] = {}
        self._db: sqlite3.Connection | None = None

        for handler in handlers:
            for event_type in handler.handles():
                self._handler_map.setdefault(event_type, []).append(handler)

    def open(self) -> None:
        """Open database and initialize schemas."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self._db_path))
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")

        self._db.execute("""
            CREATE TABLE IF NOT EXISTS _checkpoint (
                consumer TEXT PRIMARY KEY,
                stream_seq INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS _processed_events (
                event_id TEXT PRIMARY KEY,
                processed_at TEXT NOT NULL
            )
        """)
        self._db.commit()

        for handler in self._handlers:
            handler.init_schema(self._db)
        self._db.commit()

    def last_checkpoint(self, consumer: str) -> int:
        row = self._db.execute(
            "SELECT stream_seq FROM _checkpoint WHERE consumer = ?",
            (consumer,),
        ).fetchone()
        return row["stream_seq"] if row else 0

    def apply(self, event: Event, consumer: str) -> bool:
        """Apply a single event to the projection. Returns True if processed."""
        existing = self._db.execute(
            "SELECT 1 FROM _processed_events WHERE event_id = ?",
            (event.id,),
        ).fetchone()
        if existing:
            return False

        handlers = self._handler_map.get(event.type, [])
        for handler in handlers:
            handler.apply(event, self._db)

        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO _processed_events (event_id, processed_at) VALUES (?, ?)",
            (event.id, now),
        )
        self._db.execute("""
            INSERT INTO _checkpoint (consumer, stream_seq, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(consumer) DO UPDATE SET
                stream_seq = excluded.stream_seq,
                updated_at = excluded.updated_at
        """, (consumer, event.stream_seq, now))

        self._db.commit()
        return True

    def rebuild(self) -> None:
        """Drop and recreate all projection tables."""
        for handler in self._handlers:
            for table in getattr(handler, "tables", []):
                self._db.execute(f"DROP TABLE IF EXISTS {table}")

        for handler in self._handlers:
            handler.init_schema(self._db)
        self._db.commit()

        self._db.execute("DELETE FROM _processed_events")
        self._db.execute("DELETE FROM _checkpoint")
        self._db.commit()

    def close(self) -> None:
        if self._db:
            self._db.close()
```

### 4.4 Domain Projection Handlers

```python
"""halos/eventsource/handlers/track.py — Track domain projection."""

import sqlite3
from ..core import Event, ProjectionHandler


class TrackProjectionHandler(ProjectionHandler):
    """Handles track.* events → local track_entries table."""

    tables = ["track_entries"]

    def handles(self) -> list[str]:
        return [
            "track.movement.logged",
            "track.zazen.logged",
            "track.study.logged",
            "track.entry.deleted",
            "track.entry.edited",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS track_entries (
                id INTEGER PRIMARY KEY,
                domain TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration_mins INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                source_event_id TEXT NOT NULL,
                UNIQUE(source_event_id)
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_track_domain_ts "
            "ON track_entries(domain, timestamp DESC)"
        )

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload
        if event.type in (
            "track.movement.logged",
            "track.zazen.logged",
            "track.study.logged",
        ):
            db.execute("""
                INSERT OR IGNORE INTO track_entries
                    (id, domain, timestamp, duration_mins, notes, source_event_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                p["entry_id"], p["domain"], event.timestamp,
                p["duration_mins"], p.get("notes", ""), event.id,
            ))

        elif event.type == "track.entry.deleted":
            db.execute(
                "DELETE FROM track_entries WHERE id = ? AND domain = ?",
                (p["entry_id"], p["domain"]),
            )

        elif event.type == "track.entry.edited":
            sets, vals = [], []
            if "duration_mins" in p:
                sets.append("duration_mins = ?")
                vals.append(p["duration_mins"])
            if "notes" in p:
                sets.append("notes = ?")
                vals.append(p["notes"])
            if sets:
                vals.extend([p["entry_id"], p["domain"]])
                db.execute(
                    f"UPDATE track_entries SET {', '.join(sets)} "
                    f"WHERE id = ? AND domain = ?",
                    vals,
                )


class NightProjectionHandler(ProjectionHandler):
    """Handles night.* events → local night_items table."""

    tables = ["night_items", "night_jobs"]

    def handles(self) -> list[str]:
        return [
            "night.item.created",
            "night.item.transitioned",
            "night.item.updated",
            "night.job.completed",
            "night.job.failed",
        ]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS night_items (
                item_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                quadrant TEXT NOT NULL DEFAULT 'q3',
                kind TEXT NOT NULL DEFAULT 'task',
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS night_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                duration_secs REAL,
                completed_at TEXT NOT NULL
            )
        """)

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        p = event.payload
        import json as _json

        if event.type == "night.item.created":
            db.execute("""
                INSERT OR IGNORE INTO night_items
                    (item_id, title, quadrant, kind, tags, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            """, (
                p["item_id"], p["title"], p.get("quadrant", "q3"),
                p.get("kind", "task"), _json.dumps(p.get("tags", [])),
                event.timestamp, event.timestamp,
            ))

        elif event.type == "night.item.transitioned":
            db.execute(
                "UPDATE night_items SET status = ?, updated_at = ? WHERE item_id = ?",
                (p["to_status"], event.timestamp, p["item_id"]),
            )

        elif event.type == "night.item.updated":
            for field_name, value in p.get("fields_changed", {}).items():
                if field_name in ("title", "quadrant", "kind"):
                    db.execute(
                        f"UPDATE night_items SET {field_name} = ?, updated_at = ? "
                        f"WHERE item_id = ?",
                        (value, event.timestamp, p["item_id"]),
                    )

        elif event.type in ("night.job.completed", "night.job.failed"):
            status = "completed" if event.type == "night.job.completed" else "failed"
            db.execute("""
                INSERT OR REPLACE INTO night_jobs
                    (job_id, status, result, error, duration_secs, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                p["job_id"], status, p.get("result"), p.get("error"),
                p.get("duration_secs"), event.timestamp,
            ))


class JournalProjectionHandler(ProjectionHandler):
    """Handles journal.* events → local journal_entries table."""

    tables = ["journal_entries"]

    def handles(self) -> list[str]:
        return ["journal.entry.added"]

    def init_schema(self, db: sqlite3.Connection) -> None:
        db.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id INTEGER PRIMARY KEY,
                raw_text TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL DEFAULT 'text',
                mood TEXT,
                energy TEXT,
                timestamp TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                UNIQUE(source_event_id)
            )
        """)

    def apply(self, event: Event, db: sqlite3.Connection) -> None:
        import json as _json
        p = event.payload
        if event.type == "journal.entry.added":
            db.execute("""
                INSERT OR IGNORE INTO journal_entries
                    (entry_id, tags, source, mood, energy, timestamp, source_event_id, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, '')
            """, (
                p["entry_id"], _json.dumps(p.get("tags", [])),
                p.get("source", "text"), p.get("mood"), p.get("energy"),
                event.timestamp, event.id,
            ))
```

### 4.5 Checkpoint Strategy

- **On every event:** Stream sequence number saved to `_checkpoint` after processing.
- **On startup:** Read last checkpoint, deliver from that sequence + 1.
- **On rebuild:** Clear checkpoint, replay from stream beginning.

### 4.6 Startup Replay Sequence

```python
"""halos/eventsource/consumer.py — Event consumer lifecycle."""

import asyncio
import nats
from pathlib import Path
from .core import Event, EventPublisher
from .projection import ProjectionEngine


class AdvisorEventLoop:
    """Main event consumption loop for an advisor."""

    def __init__(
        self,
        advisor_name: str,
        nats_url: str,
        nats_user: str,
        nats_pass: str,
        projection_path: Path,
        handlers: list,
    ):
        self.advisor_name = advisor_name
        self.nats_url = nats_url
        self.nats_user = nats_user
        self.nats_pass = nats_pass
        self.projection = ProjectionEngine(projection_path, handlers)
        self.publisher: EventPublisher | None = None
        self._nc = None
        self._sub = None

    async def start(self) -> None:
        """Connect to NATS, replay from checkpoint, enter steady state."""
        self.projection.open()
        last_seq = self.projection.last_checkpoint(self.advisor_name)

        self._nc = await nats.connect(
            self.nats_url,
            user=self.nats_user,
            password=self.nats_pass,
        )
        js = self._nc.jetstream()

        self.publisher = EventPublisher(self._nc, source=self.advisor_name)

        self._sub = await js.pull_subscribe(
            "halo.>",
            durable=self.advisor_name,
            config=nats.js.api.ConsumerConfig(
                ack_policy="explicit",
                max_deliver=3,
                ack_wait=30,
            ),
        )

        await self.publisher.emit(
            "system.advisor.started",
            {"advisor": self.advisor_name, "version": self._get_version(),
             "image_tag": self._get_image_tag()},
        )

        await self._consume_loop()

    async def _consume_loop(self) -> None:
        while True:
            try:
                messages = await self._sub.fetch(batch=10, timeout=5)
                for msg in messages:
                    event = Event.from_json(
                        msg.data,
                        stream_seq=msg.metadata.sequence.stream,
                    )
                    self.projection.apply(event, self.advisor_name)
                    await msg.ack()
            except nats.errors.TimeoutError:
                pass
            except Exception as e:
                print(f"ERROR processing event: {e}", flush=True)
                await asyncio.sleep(1)

    async def stop(self) -> None:
        if self.publisher:
            await self.publisher.emit(
                "system.advisor.stopped",
                {"advisor": self.advisor_name, "reason": "shutdown",
                 "uptime_secs": self._uptime()},
            )
        if self._sub:
            await self._sub.unsubscribe()
        if self._nc:
            await self._nc.close()
        self.projection.close()

    def _get_version(self) -> str:
        import os
        return os.environ.get("HALO_VERSION", "0.0.0-dev")

    def _get_image_tag(self) -> str:
        import os
        return os.environ.get("HALO_IMAGE_TAG", "unknown")

    def _uptime(self) -> float:
        return 0.0  # Implemented with start timestamp
```

---

## 5. Write Path: Telegram → Advisor → Stream

### 5.1 How Data Enters the Stream

Telegram is the sole human interface. All writes flow through advisors:

```
Kai sends Telegram message
    │
    ▼
Advisor (Hermes gateway) receives message
    │
    ▼
Advisor executes halos command (e.g. trackctl add)
    │
    ▼
Event published to NATS from within the cluster
    │
    ▼
All consumers receive the event and update projections
```

The advisor both writes and reads from its own projection. The write produces the event; the event updates the projection; the projection serves reads.

### 5.2 Per-Module Event Publishing

When an advisor executes a halos command, it publishes the corresponding event. This happens inside the advisor pod — no external connectivity required.

| Module | Events Published | When |
|--------|-----------------|------|
| **trackctl** | `track.{domain}.logged`, `track.entry.deleted`, `track.entry.edited` | Kai logs activity via Telegram |
| **nightctl** | `night.item.created`, `night.item.transitioned`, `night.item.updated`, `night.job.completed`, `night.job.failed` | Kai manages tasks via Telegram, overnight jobs run |
| **memctl** | `mem.note.created`, `mem.note.deleted`, `mem.index.rebuilt` | Advisor creates/manages memory |
| **journalctl** | `journal.entry.added`, `journal.window.synthesised` | Kai journals via Telegram, advisor synthesises |
| **dashctl** | None (read-only) | Reads from projection |
| **calctl** | `cal.event.created`, `cal.event.updated` | New module, event-native |
| **ledgerctl** | `ledger.entry.added` | New module, event-native |

### 5.3 Git Activity

Commits data enters the stream via an advisor polling the GitHub API on a cron schedule, publishing `commits.pushed` events. No MacBook involvement.

---

## 6. Advisor Container Architecture

### 6.1 Base Image

Each advisor runs the full Hermes gateway image with halos layered on top. Same Dockerfile for all advisors — differentiated by config only.

```dockerfile
FROM debian:13.4

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    nodejs npm \
    ripgrep ffmpeg gcc python3-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 hermes && useradd -u 1000 -g 1000 -m -d /home/hermes hermes

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY vendor/hermes-agent /opt/hermes
WORKDIR /opt/hermes
RUN pip install --no-cache-dir ".[all,messaging,cron]"
RUN npm install --prefer-offline --no-audit

COPY halos/ /opt/halos/halos/
COPY pyproject.toml /opt/halos/
WORKDIR /opt/halos
RUN pip install --no-cache-dir .

COPY data/advisors/ /opt/data/advisors/
COPY briefings.yaml /opt/data/briefings.yaml
COPY docker/entrypoint.sh /opt/entrypoint.sh
COPY docker/defaults/ /opt/defaults/
RUN chmod +x /opt/entrypoint.sh

RUN mkdir -p /opt/data && chown -R hermes:hermes /opt/data

ENV HERMES_HOME=/opt/data
VOLUME ["/opt/data"]
USER hermes
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["gateway"]
```

### 6.2 Per-Advisor Configuration

Each advisor gets a ConfigMap with its persona, bot token, cron schedule, and NATS subscriptions.

```yaml
# k8s/advisors/musashi-config.yaml
gateway:
  name: musashi
  system_prompt_file: /opt/data/advisors/musashi/persona.md

telegram:
  bot_token_env: MUSASHI_BOT_TOKEN
  chat_id: "5967394003"

nats:
  url: nats://nats.halo-fleet.svc.cluster.local:4222
  user_env: NATS_USER
  pass_env: NATS_PASS
  consumer_name: musashi

cron:
  jobs:
    - name: morning-checkin
      schedule: "0 7 * * *"
      timezone: Europe/London
      action: deliver_briefing
      config:
        kind: morning
        domain: body
        gather_modules: [trackctl.movement, trackctl.zazen, journalctl]

halos:
  projection_db: /opt/data/projection.db
  source_name: musashi
  subscriptions:
    - "halo.track.movement.>"
    - "halo.track.zazen.>"
    - "halo.journal.>"
    - "halo.advisor.musashi.>"
    - "halo.system.>"
    - "halo.release.>"
    - "halo.commits.>"

llm:
  model: claude-sonnet-4-20250514
  max_tokens: 1024
  api_key_env: ANTHROPIC_API_KEY
```

### 6.3 Kubernetes Deployment

Each advisor is a **Deployment** with `replicas: 1` and `Recreate` strategy. Internal cron via Hermes handles scheduling.

```yaml
# k8s/advisors/musashi-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: advisor-musashi
  namespace: halo-fleet
  labels:
    app.kubernetes.io/name: advisor-musashi
    app.kubernetes.io/component: advisor
    app.kubernetes.io/part-of: halo
    halo/advisor: musashi
    halo/domain: body
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: advisor-musashi
  template:
    metadata:
      labels:
        app.kubernetes.io/name: advisor-musashi
        app.kubernetes.io/component: advisor
        halo/advisor: musashi
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gateway
          image: ghcr.io/rickhallett/halo:latest
          args: ["gateway"]
          ports:
            - containerPort: 9090
              name: metrics
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          env:
            - name: ADVISOR_NAME
              value: "musashi"
            - name: TZ
              value: "Europe/London"
            - name: NATS_USER
              value: "advisor"
          envFrom:
            - secretRef:
                name: advisor-musashi-secrets
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: advisor-config
              mountPath: /opt/data/config.yaml
              subPath: config.yaml
            - name: projection-data
              mountPath: /opt/data
          livenessProbe:
            httpGet:
              path: /health
              port: 9090
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /ready
              port: 9090
            initialDelaySeconds: 5
            periodSeconds: 10
      volumes:
        - name: advisor-config
          configMap:
            name: advisor-musashi-config
        - name: projection-data
          emptyDir:
            sizeLimit: 500Mi
```

**Key decisions:**

- **emptyDir for projection storage.** Projection rebuilds from the stream on restart. No PVC needed.
- **Recreate strategy.** Only one instance per advisor.
- **Internal cron via Hermes.** K8s just keeps the pod alive.

### 6.4 Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: advisor-musashi-secrets
  namespace: halo-fleet
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "<from-vault>"
  MUSASHI_BOT_TOKEN: "<musashi-specific-telegram-bot-token>"
  NATS_PASS: "<shared-advisor-nats-password>"
```

Each advisor has its own Telegram bot identity (created via @BotFather). NATS credential is shared.

### 6.5 Per-Advisor Schedule Matrix

| Advisor | Cron Schedule | Session Type | NATS Subscriptions |
|---------|--------------|--------------|-------------------|
| Musashi | `0 7 * * *` | Morning body | `track.movement.*`, `track.zazen.*`, `journal.*`, `commits.*` |
| Socrates | `0 9 * * *` | Morning craft | `track.study.*`, `mem.*`, `journal.*`, `commits.*` |
| Seneca | `45 19 * * *` | Evening time | `track.*`, `night.*`, `journal.*`, `commits.*` |
| Medici | `0 20 * * *` | Evening money | `night.*`, `ledger.*`, `journal.*` |
| Machiavelli | `15 20 * * *` | Evening power | `advisor.*.delivered`, `night.*`, `journal.*` |
| Sun Tzu | `30 20 * * *` | Evening strategy | `advisor.*.delivered`, `night.*`, `track.*`, `journal.*` |
| Bankei | On-demand | Rest, rhythm | `track.zazen.*`, `journal.*` |
| Plutarch | `0 21 * * 0` (weekly) | Dramaturg | `halo.>` (all events) |

### 6.6 Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: halo-fleet
  labels:
    app.kubernetes.io/part-of: halo
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## 7. Release Strategy

Standard Kubernetes rollouts. All advisors run the same image.

### 7.1 Pipeline

```
git tag v0.2.0 && git push --tags
    │
    ▼
GitHub Actions: build image → push to GHCR
    │
    ▼
kubectl set image deployment/advisor-musashi gateway=ghcr.io/rickhallett/halo:v0.2.0
kubectl set image deployment/advisor-seneca  gateway=ghcr.io/rickhallett/halo:v0.2.0
...
```

Or update the image tag in manifests and `kubectl apply`. Kustomize image override works too.

### 7.2 Rollback

```bash
kubectl rollout undo deployment/advisor-musashi
```

Kubernetes maintains rollout history. Readiness probes gate traffic — a broken image fails the probe and the old pod stays.

### 7.3 Informational Event

On deploy, publish a single `release.published` event to the stream so advisors (and Plutarch's projection) can record version history:

```json
{
  "type": "release.published",
  "source": "hq",
  "payload": {
    "version": "0.2.0",
    "image_tag": "ghcr.io/rickhallett/halo:v0.2.0",
    "changelog": ["Add ledgerctl module", "Fix projection rebuild"]
  }
}
```

This is informational only. No state machine, no adoption protocol, no self-patching.

---

## 8. Inter-Advisor Communication

### 8.1 Choreography Pattern

Advisors don't communicate directly. All communication flows through the event stream. Each advisor publishes events about its own actions and consumes events relevant to its domain.

### 8.2 Evening Council Sequence

The evening session is a choreography driven by staggered cron schedules:

```
19:45  Seneca's cron fires
       → Gathers today's data from projection
       → Delivers to Telegram
       → Publishes: halo.advisor.seneca.delivered

20:00  Medici's cron fires
       → Reads Seneca's delivery event from projection (if present)
       → Gathers financial data, synthesises
       → Publishes: halo.advisor.medici.delivered

20:15  Machiavelli's cron fires
       → Reads Seneca + Medici delivery events from projection (if present)
       → Synthesises blind spots
       → Publishes: halo.advisor.machiavelli.delivered

20:30  Sun Tzu's cron fires
       → Reads all preceding delivery events from projection (if present)
       → Synthesises strategic layer
       → Publishes: halo.advisor.sun-tzu.delivered
```

If an upstream advisor hasn't delivered by the time a downstream advisor's cron fires, the downstream advisor proceeds with whatever is in its projection. No polling, no waiting. The 15-minute stagger provides enough buffer in practice. If Seneca was down, Medici simply notes "Seneca was unavailable this evening" and moves on.

The `advisor.delivered` event includes a `summary` field for downstream context but NOT the full message text (that stays on Telegram).

### 8.3 Plutarch's Role

Plutarch subscribes to all events. His jobs:

1. **Weekly roundtable synthesis:** Meta-analysis of all advisor deliveries — themes, contradictions, patterns.
2. **System health narrative:** Transform technical metrics into human-readable fleet state.
3. **Cross-advisor pattern detection:** Notice when multiple advisors flag the same issue from different angles.

---

## 9. Observability

The observability stack is already deployed on VKE. See [Halo Observability Runbook](../d1/halo-observability-runbook.md) for access, queries, and upgrade procedures.

**Existing infrastructure** (in `monitoring` namespace):

| Component | Status | Fleet Integration |
|-----------|--------|-------------------|
| Prometheus (kube-prometheus-stack) | Running | Advisor pods use `prometheus.io/scrape: "true"` annotation — scraped automatically |
| Grafana | Running | Build fleet dashboards against advisor metrics once pods are emitting |
| Loki + Promtail | Running | Advisor pod stdout captured automatically via DaemonSet |
| Alertmanager | Running | **Not yet wired to Telegram** — prerequisite for fleet alerting |

### 9.1 Advisor Metrics

Each advisor pod exposes metrics on `:9090/metrics`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `halo_events_published_total` | Counter | advisor, event_type | Events published to NATS |
| `halo_events_consumed_total` | Counter | advisor, event_type | Events consumed from NATS |
| `halo_consumer_lag_messages` | Gauge | advisor | Unprocessed messages |
| `halo_projection_rows_total` | Gauge | advisor, table | Projection database size |
| `halo_delivery_success_total` | Counter | advisor | Successful Telegram deliveries |
| `halo_delivery_failure_total` | Counter | advisor | Failed Telegram deliveries |
| `halo_llm_latency_seconds` | Histogram | advisor, model | LLM API call duration |
| `halo_llm_tokens_total` | Counter | advisor, model, direction | Token usage |
| `halo_llm_cost_usd_total` | Counter | advisor, model | Estimated API cost |
| `halo_advisor_uptime_seconds` | Gauge | advisor | Uptime |
| `halo_advisor_version_info` | Gauge | advisor, version | Version label |

### 9.2 Alert Conditions

| What | Alert When |
|------|------------|
| Consumer lag | > 1000 messages for > 10 minutes |
| Stream storage | > 80% of 5 GiB |
| Advisor down | Any advisor down > 5 minutes |
| Missed delivery | Any advisor hasn't delivered in > 25 hours |
| LLM latency | p95 > 60 seconds for > 5 minutes |

Alert delivery: Alertmanager → Telegram (wiring this is a prerequisite — see runbook "Not Yet Done" section).

### 9.3 Logs

Promtail ships advisor container stdout/stderr to Loki automatically. Query in Grafana:

```logql
{namespace="halo-fleet", container="gateway"}
{namespace="halo-fleet"} |= "ERROR"
{namespace="halo-fleet", pod=~"advisor-musashi.*"}
```

### 9.4 Distributed Tracing

Each event carries a `correlation_id`. Advisors include `triggered_by` in delivery event payloads, linking back to the data events that informed the synthesis.

---

## 10. Security

### 10.1 NATS Authentication

NATS is cluster-internal only — not exposed outside VKE. Two credential tiers (`hq`, `advisor`). See §3.6.

### 10.2 Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: advisor-policy
  namespace: halo-fleet
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: advisor
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              app: prometheus
      ports:
        - protocol: TCP
          port: 9090
  egress:
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: nats
      ports:
        - protocol: TCP
          port: 4222
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

### 10.3 Secret Management

Phase 1: k8s Secrets (manual). Later: external-secrets operator → Vultr Secrets.

### 10.4 Threat Surface

| Vector | Risk | Mitigation |
|--------|------|------------|
| Compromised pod → event injection | Medium | NATS auth. All pods run same image — compromise of one implies compromise of all. Shared credential is honest about this. |
| API key exfiltration via prompt injection | Medium | No tool exposes env vars. Persona instructions prohibit outputting secrets. |
| Stream replay (old events re-published) | Low | NATS dedup window + `_processed_events` table. |
| NATS denial of service | Medium | Rate limiting. `max_ack_pending` bounds backlog. Cluster-internal only. |

---

## 11. Migration Path

Phases are ordered by dependency. No time estimates — scope each phase when starting it.

### Phase 1: NATS on VKE

Deploy NATS to `halo-fleet` namespace. Create HALO stream with subject hierarchy. Create credentials. Verify connectivity within the cluster. Apply network policies and pod security standards from the start.

**Done when:** NATS is running, stream exists, a test pod can publish and consume events.

### Phase 2: Musashi Pilot

Implement the eventsource package (`core.py`, `projection.py`, `consumer.py`, handlers). Deploy Musashi as a full Hermes gateway on VKE with its own Telegram bot. Verify projection rebuilds from stream on startup, cron fires on schedule, Telegram delivery works, metrics are exposed.

Run alongside the existing MacBook-based Musashi until confident, then disable the local one.

**Done when:** Musashi delivers to Telegram on schedule using data from stream projection. No MacBook dependency.

### Phase 3: Full Fleet

Deploy remaining advisors one at a time, monitoring between deploys. Create per-advisor Telegram bots. Verify evening council choreography flows correctly. Deploy Plutarch with wildcard subscription. Set up Prometheus scraping and alerting.

**Done when:** All advisors fire on schedule. Evening council flows. Plutarch weekly synthesis works.

### Phase 4: Telegram as Write Interface

Wire up advisor Telegram handlers to publish domain events when Kai logs activity, manages tasks, or journals. This is the point where the MacBook stops being relevant to the fleet — all data enters through Telegram.

**Done when:** Kai can log movement, manage nightctl items, and add journal entries through Telegram, and the data propagates to all advisors via the stream.

### Phase 5: Hardening

Chaos testing: kill advisor pods, kill NATS, corrupt projections. Verify automatic recovery (pod restart → stream replay → projection rebuild → operational). Measure projection rebuild time at scale — if >2 minutes, add projection snapshots. Document runbooks for failure modes.

**Done when:** Recovery from any component failure is automatic.

---

## 12. Technical Debt & Open Questions

### 12.1 Inherited Debt

| ID | Area | Resolution |
|----|------|------------|
| TD-1 | journalctl uses `claude` CLI subprocess | Replace with Anthropic SDK direct call. In the event-sourced architecture, journal window synthesis becomes an event consumer that publishes `journal.window.synthesised`. |
| TD-4 | Dockerfile uses pip | Hermes Dockerfile uses pip. Advisor pods inherit this. Fix: migrate Hermes to uv, or accept pip in the Hermes layer. |

### 12.2 New Debt

| ID | Area | Severity | Description |
|----|------|----------|-------------|
| TD-ES1 | Event schema | Medium | No automated schema validation on publish. Could publish malformed events. Add JSON Schema validation when event volume warrants it. |
| TD-ES2 | Projection rebuild time | Medium | At scale (90 days × all domains), full rebuild time is unknown. Measure with Musashi pilot. If >2 min, add projection snapshots. |
| TD-ES3 | NATS availability | Low | Single-node NATS is a SPOF. Persistent storage means events survive restart. If the system grows, deploy a 3-node cluster (`num_replicas: 3`). |
| TD-ES4 | Bankei schedule | Low | Bankei has no cron schedule — on-demand only, responds to direct messages. Intentional. |

### 12.3 Open Questions

1. **Projection rebuild time at scale.** After 90 days of events, how long does a full rebuild take? Unknown until measured with Musashi pilot.

2. **NATS cluster for HA.** Single-node is fine for one VKE worker. If the system grows, deploy a 3-node cluster.

3. **Hermes cron integration.** Verify that Hermes gateway supports internal cron scheduling. If not, use APScheduler alongside the gateway process.

---

## 13. Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| VKE worker node (existing) | ~$12-24 (shared) |
| NATS PVC (10Gi block storage) | ~$1 |
| Advisor pods (8 × idle Deployments, shared node) | $0 incremental |
| Anthropic API (8 advisors × 30 days × ~3K tokens) | ~$5-8 |
| Per-advisor Telegram bots | $0 |
| **Total incremental** | **~$6-33/month** |

Memory footprint per advisor: ~200MB. Total for 8 advisors: ~1.6GB. Fits on a 4GB VKE worker node with NATS. If tight, consider a 2-node cluster or image optimisation.

---

## Appendix A: Advisor Subscription Map

```yaml
musashi:
  publishes: [advisor.musashi.delivered, advisor.delivered, advisor.profile.updated, system.*, track.*]
  subscribes: [track.movement.>, track.zazen.>, journal.>, commits.>, system.>, release.>]

seneca:
  publishes: [advisor.seneca.delivered, advisor.delivered, advisor.profile.updated, system.*]
  subscribes: [track.>, night.>, journal.>, commits.>, system.>, release.>]

socrates:
  publishes: [advisor.socrates.delivered, advisor.delivered, advisor.profile.updated, system.*]
  subscribes: [track.study.>, mem.>, journal.>, commits.>, system.>, release.>]

sun-tzu:
  publishes: [advisor.sun-tzu.delivered, advisor.delivered, advisor.profile.updated, system.*]
  subscribes: [advisor.seneca.delivered, advisor.medici.delivered, advisor.machiavelli.delivered, night.>, track.>, journal.>, commits.>, system.>, release.>]

machiavelli:
  publishes: [advisor.machiavelli.delivered, advisor.delivered, advisor.profile.updated, system.*]
  subscribes: [advisor.seneca.delivered, advisor.medici.delivered, night.>, journal.>, system.>, release.>]

medici:
  publishes: [advisor.medici.delivered, advisor.delivered, advisor.profile.updated, system.*]
  subscribes: [advisor.seneca.delivered, night.>, ledger.>, journal.>, system.>, release.>]

bankei:
  publishes: [advisor.bankei.delivered, advisor.delivered, advisor.profile.updated, system.*]
  subscribes: [track.zazen.>, journal.>, system.>, release.>]

plutarch:
  publishes: [advisor.plutarch.delivered, advisor.delivered, briefing.composed, system.*]
  subscribes: [halo.>]  # Everything
```

## Appendix B: Advisor Domain → Data Mapping

| Advisor | trackctl Domains | Other Data Sources | Evening Council Role |
|---------|-----------------|-------------------|---------------------|
| Musashi | movement, zazen | journalctl window, commits | N/A (morning) |
| Socrates | study-neetcode, study-crafters, study-source | memctl corpus, commits | N/A (morning) |
| Seneca | all (productivity audit) | nightctl items, journalctl, commits | Opens evening: "what did you do today" |
| Medici | none directly | nightctl (cost), ledgerctl, journalctl | Costs it: "what did it cost" |
| Machiavelli | none directly | all advisor deliveries, nightctl | Blind spots: "what aren't you seeing" |
| Sun Tzu | project | all advisor deliveries, nightctl | Closes evening: "what's next" |
| Bankei | zazen | journalctl window | N/A (on-demand) |
| Plutarch | all (via wildcard) | all events | Weekly synthesis |
