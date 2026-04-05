#!/usr/bin/env python3
"""Aura session relay — tails Hermes JSONL and publishes to NATS.

Watches the Aura gateway's sessions directory for new JSONL lines,
converts them to observation events, and publishes to the HALO stream
on subject `halo.observation.aura`.

Runs as a sidecar in the halo-aura namespace.

Environment variables:
    SESSIONS_DIR    - path to Hermes sessions directory (default: /opt/data/sessions)
    NATS_URL        - NATS server URL (default: nats://nats.halo-fleet.svc.cluster.local:4222)
    NATS_USER       - NATS auth user (default: "hq")
    NATS_PASS       - NATS auth password (required)
"""

import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path

import nats
from ulid import ULID


SESSIONS_DIR = Path(os.environ.get("SESSIONS_DIR", "/opt/data/sessions"))
NATS_URL = os.environ.get("NATS_URL", "nats://nats.halo-fleet.svc.cluster.local:4222")
NATS_USER = os.environ.get("NATS_USER", "hq")
NATS_PASS = os.environ.get("NATS_PASS", "")
SUBJECT = "halo.observation.aura"

# Only relay user and assistant messages, skip tool calls and metadata
RELAY_ROLES = {"user", "assistant"}


def make_event(role: str, content: str, session_id: str, timestamp: str) -> dict:
    return {
        "id": str(ULID()),
        "type": f"observation.aura.{role}",
        "version": 1,
        "source": "aura-relay",
        "timestamp": timestamp,
        "correlation_id": session_id,
        "payload": {
            "role": role,
            "content": content,
            "session_id": session_id,
        },
    }


class SessionTailer:
    """Tails a single JSONL session file."""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0
        self.session_id = path.stem

    def read_new_lines(self) -> list[dict]:
        """Read any new lines since last check."""
        try:
            size = self.path.stat().st_size
            if size <= self.offset:
                return []

            lines = []
            with open(self.path, "r") as f:
                f.seek(self.offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("role") in RELAY_ROLES and data.get("content"):
                            lines.append(data)
                    except json.JSONDecodeError:
                        pass
                self.offset = f.tell()
            return lines
        except FileNotFoundError:
            return []


async def run():
    if not NATS_PASS:
        print("[aura-relay] ERROR: NATS_PASS not set", file=sys.stderr)
        sys.exit(1)

    print(f"[aura-relay] Starting — watching {SESSIONS_DIR}", flush=True)
    print(f"[aura-relay] NATS: {NATS_URL} subject={SUBJECT}", flush=True)

    nc = await nats.connect(NATS_URL, user=NATS_USER, password=NATS_PASS)
    js = nc.jetstream()

    tailers: dict[str, SessionTailer] = {}
    running = True
    published = 0

    def shutdown(sig, _frame):
        nonlocal running
        print(f"[aura-relay] Received {signal.Signals(sig).name}, stopping...", flush=True)
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Initialise tailers for existing files, seek to end (don't replay history)
    for f in SESSIONS_DIR.glob("*.jsonl"):
        t = SessionTailer(f)
        t.offset = f.stat().st_size  # skip existing content
        tailers[str(f)] = t
        print(f"[aura-relay] Tracking existing: {f.name} (skipping {t.offset} bytes)", flush=True)

    while running:
        # Discover new session files
        for f in SESSIONS_DIR.glob("*.jsonl"):
            key = str(f)
            if key not in tailers:
                tailers[key] = SessionTailer(f)
                print(f"[aura-relay] New session: {f.name}", flush=True)

        # Tail all active sessions
        for tailer in tailers.values():
            new_lines = tailer.read_new_lines()
            for line in new_lines:
                event = make_event(
                    role=line["role"],
                    content=line["content"],
                    session_id=tailer.session_id,
                    timestamp=line.get("timestamp", ""),
                )
                try:
                    await js.publish(SUBJECT, json.dumps(event).encode())
                    published += 1
                    role = line["role"]
                    preview = line["content"][:60].replace("\n", " ")
                    print(f"[aura-relay] [{role}] {preview}...", flush=True)
                except Exception as e:
                    print(f"[aura-relay] Publish error: {e}", file=sys.stderr, flush=True)

        await asyncio.sleep(2)  # poll interval

    await nc.close()
    print(f"[aura-relay] Stopped. Published {published} events total.", flush=True)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
