"""Tier 2: Halostream event flow and CQRS verification.

Proves data actually moves through the system — events published
to NATS arrive in advisor projections, bad payloads don't kill
the consumer, and wiped projections rebuild from the stream.
"""

from __future__ import annotations

import json
import time
import uuid

import pytest

from .conftest import EXPECTED_ADVISORS, FLEET_NS

pytestmark = [pytest.mark.fleet, pytest.mark.tier2]

# Python snippet templates executed inside advisor pods via kubectl exec.
# These run in the pod's Python environment which has nats-py installed.

PUBLISH_EVENT_SCRIPT = """
import asyncio, os, json, time, uuid

async def publish():
    import nats
    nc = await nats.connect(
        os.environ['NATS_URL'],
        user=os.environ['NATS_USER'],
        password=os.environ['NATS_PASS'],
    )
    js = nc.jetstream()
    event = {{
        'id': '{event_id}',
        'type': '{event_type}',
        'version': 1,
        'source': 'fleet-test-runner',
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'correlation_id': '',
        'payload': {payload_json}
    }}
    ack = await js.publish('halo.{event_type}', json.dumps(event).encode())
    print(f'seq={{ack.seq}}')
    await nc.close()

asyncio.run(publish())
"""

PUBLISH_RAW_SCRIPT = """
import asyncio, os

async def publish():
    import nats
    nc = await nats.connect(
        os.environ['NATS_URL'],
        user=os.environ['NATS_USER'],
        password=os.environ['NATS_PASS'],
    )
    js = nc.jetstream()
    ack = await js.publish('{subject}', {data})
    print(f'seq={{ack.seq}}')
    await nc.close()

asyncio.run(publish())
"""

CHECK_PROJECTION_SCRIPT = """
import sqlite3, json
db = sqlite3.connect('/opt/data/store/projection.db')
db.row_factory = sqlite3.Row
rows = db.execute(
    "SELECT * FROM _processed_events WHERE event_id = ?",
    ('{event_id}',)
).fetchall()
print(len(rows))
db.close()
"""

CHECK_TRACK_ENTRY_SCRIPT = """
import sqlite3
db = sqlite3.connect('/opt/data/store/projection.db')
rows = db.execute(
    "SELECT * FROM track_entries WHERE source_event_id = ?",
    ('{event_id}',)
).fetchall()
print(len(rows))
db.close()
"""

CHECK_JOURNAL_ENTRY_SCRIPT = """
import sqlite3
db = sqlite3.connect('/opt/data/store/projection.db')
rows = db.execute(
    "SELECT * FROM journal_entries WHERE source_event_id = ?",
    ('{event_id}',)
).fetchall()
print(len(rows))
db.close()
"""

POD_RESTART_COUNT_SCRIPT = """
import json, subprocess
result = subprocess.run(
    ['cat', '/proc/1/status'],
    capture_output=True, text=True
)
# If we can read /proc/1/status, the main process is alive
print('alive' if result.returncode == 0 else 'dead')
"""


def _publish_event(kubectl_exec_python, pod: str, event_id: str, event_type: str, payload: dict) -> int:
    """Publish an event via an advisor pod. Returns the stream sequence number."""
    script = PUBLISH_EVENT_SCRIPT.format(
        event_id=event_id,
        event_type=event_type,
        payload_json=json.dumps(payload),
    )
    result = kubectl_exec_python(pod, script)
    return int(result.strip().split("=")[1])


def _publish_raw(kubectl_exec_python, pod: str, subject: str, data: bytes) -> int:
    """Publish raw bytes to a NATS subject. For poison pill testing."""
    script = PUBLISH_RAW_SCRIPT.format(
        subject=subject,
        data=repr(data),
    )
    result = kubectl_exec_python(pod, script)
    return int(result.strip().split("=")[1])


def _check_processed(kubectl_exec_python, pod: str, event_id: str) -> int:
    """Check if an event has been processed in a pod's projection."""
    script = CHECK_PROJECTION_SCRIPT.format(event_id=event_id)
    result = kubectl_exec_python(pod, script)
    return int(result.strip())


def _check_track_entry(kubectl_exec_python, pod: str, event_id: str) -> int:
    """Check if a track event has been projected."""
    script = CHECK_TRACK_ENTRY_SCRIPT.format(event_id=event_id)
    result = kubectl_exec_python(pod, script)
    return int(result.strip())


def _check_journal_entry(kubectl_exec_python, pod: str, event_id: str) -> int:
    """Check if a journal event has been projected."""
    script = CHECK_JOURNAL_ENTRY_SCRIPT.format(event_id=event_id)
    result = kubectl_exec_python(pod, script)
    return int(result.strip())


def _wait_for_projection(kubectl_exec_python, pod: str, event_id: str, check_fn, timeout: float = 10.0) -> bool:
    """Poll until an event appears in projection, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if check_fn(kubectl_exec_python, pod, event_id) > 0:
                return True
        except RuntimeError:
            pass
        time.sleep(0.5)
    return False


class TestEventPublishAndAck:
    """Events published to NATS are received by all consumers."""

    def test_ping_reaches_all_consumers(self, kubectl_exec_python, advisor_pod_names):
        """Publish a test event and verify all advisors process it."""
        event_id = f"test-ping-{uuid.uuid4().hex[:8]}"
        source_pod = list(advisor_pod_names.values())[0]

        _publish_event(
            kubectl_exec_python, source_pod,
            event_id=event_id,
            event_type="test.ping",
            payload={"message": "tier2 integration test"},
        )

        # Verify all advisors processed the event
        failures = {}
        for name, pod in advisor_pod_names.items():
            found = _wait_for_projection(
                kubectl_exec_python, pod, event_id, _check_processed, timeout=10.0
            )
            if not found:
                failures[name] = "event not processed within 10s"

        assert not failures, f"Event {event_id} not received by: {failures}"


class TestTrackEventProjection:
    """Track events project into advisor SQLite databases."""

    def test_movement_event_projects(self, kubectl_exec_python, advisor_pod_names):
        event_id = f"test-track-{uuid.uuid4().hex[:8]}"
        source_pod = list(advisor_pod_names.values())[0]

        _publish_event(
            kubectl_exec_python, source_pod,
            event_id=event_id,
            event_type="track.movement.logged",
            payload={
                "domain": "movement",
                "duration_mins": 30,
                "entry_id": int(uuid.uuid4().int % 1_000_000_000),
                "notes": "fleet test entry",
            },
        )

        # Check Musashi's projection (movement is his domain)
        musashi_pod = advisor_pod_names.get("musashi")
        if musashi_pod:
            found = _wait_for_projection(
                kubectl_exec_python, musashi_pod, event_id, _check_track_entry, timeout=10.0
            )
            assert found, f"Track event {event_id} not projected in Musashi within 10s"

    def test_cross_advisor_visibility(self, kubectl_exec_python, advisor_pod_names):
        """Event from one advisor is visible in another's projection."""
        event_id = f"test-cross-{uuid.uuid4().hex[:8]}"

        # Publish from Musashi
        musashi_pod = advisor_pod_names.get("musashi")
        draper_pod = advisor_pod_names.get("draper")
        if not musashi_pod or not draper_pod:
            pytest.skip("Need both musashi and draper running")

        _publish_event(
            kubectl_exec_python, musashi_pod,
            event_id=event_id,
            event_type="track.zazen.logged",
            payload={
                "domain": "zazen",
                "duration_mins": 20,
                "entry_id": int(uuid.uuid4().int % 1_000_000_000),
                "notes": "cross-advisor test",
            },
        )

        # Verify Draper sees it
        found = _wait_for_projection(
            kubectl_exec_python, draper_pod, event_id, _check_track_entry, timeout=10.0
        )
        assert found, f"Cross-advisor event {event_id} not visible in Draper's projection"


class TestJournalEventProjection:
    """Journal events project into advisor SQLite databases."""

    def test_journal_event_projects(self, kubectl_exec_python, advisor_pod_names):
        event_id = f"test-journal-{uuid.uuid4().hex[:8]}"
        source_pod = list(advisor_pod_names.values())[0]

        _publish_event(
            kubectl_exec_python, source_pod,
            event_id=event_id,
            event_type="journal.entry.added",
            payload={
                "entry_id": int(uuid.uuid4().int % 1_000_000_000),
                "raw_text": "fleet test journal entry",
                "tags": "[]",
                "source": "test",
                "mood": "",
                "energy": "",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

        # Check any advisor's projection
        pod = list(advisor_pod_names.values())[0]
        found = _wait_for_projection(
            kubectl_exec_python, pod, event_id, _check_journal_entry, timeout=10.0
        )
        assert found, f"Journal event {event_id} not projected within 10s"


class TestDuplicateIdempotency:
    """Publishing the same event ID twice produces exactly one projection entry."""

    def test_duplicate_event_single_entry(self, kubectl_exec_python, advisor_pod_names):
        event_id = f"test-dedup-{uuid.uuid4().hex[:8]}"
        source_pod = list(advisor_pod_names.values())[0]

        payload = {
            "domain": "movement",
            "duration_mins": 10,
            "entry_id": int(uuid.uuid4().int % 1_000_000_000),
            "notes": "dedup test",
        }

        # Publish twice with the same event ID
        _publish_event(kubectl_exec_python, source_pod, event_id, "track.movement.logged", payload)
        time.sleep(2)
        _publish_event(kubectl_exec_python, source_pod, event_id, "track.movement.logged", payload)
        time.sleep(3)

        # Should have exactly one entry
        pod = list(advisor_pod_names.values())[0]
        count = _check_track_entry(kubectl_exec_python, pod, event_id)
        assert count == 1, f"Expected 1 entry for duplicate event, got {count}"


class TestPoisonPill:
    """Malformed payloads must not crash the consumer sidecar.

    The fastest way to kill the entire fleet is a bad payload that
    the consumer can't deserialize — causing crash, restart, re-read
    the same bad message, crash again. CrashLoopBackOff.

    The consumer MUST: ack the poison message, log the error, and
    continue processing the next valid event.
    """

    def test_malformed_json_does_not_crash(self, kubectl_exec_python, advisor_pod_names):
        """Publish garbage bytes, then a valid event. Verify the valid event arrives."""
        source_pod = list(advisor_pod_names.values())[0]
        target_advisor = list(advisor_pod_names.keys())[0]
        target_pod = advisor_pod_names[target_advisor]

        # Get restart count before
        from .conftest import _kubectl_json
        pods = _kubectl_json("get", "pods")
        restart_before = 0
        for p in pods["items"]:
            if p["metadata"]["name"] == target_pod:
                for cs in p["status"].get("containerStatuses", []):
                    if cs["name"] == "gateway":
                        restart_before = cs.get("restartCount", 0)

        # 1. Publish poison: not valid JSON
        _publish_raw(
            kubectl_exec_python, source_pod,
            subject="halo.test.corrupt",
            data=b"THIS IS NOT JSON {{{garbage\xff\xfe",
        )

        # 2. Publish poison: valid JSON but missing required fields
        _publish_raw(
            kubectl_exec_python, source_pod,
            subject="halo.track.movement.logged",
            data=json.dumps({"id": "poison-" + uuid.uuid4().hex[:8], "type": "track.movement.logged"}).encode(),
            # Missing: version, source, timestamp, payload
        )

        # 3. Publish poison: valid event envelope but payload missing required keys
        poison_id = f"poison-partial-{uuid.uuid4().hex[:8]}"
        _publish_event(
            kubectl_exec_python, source_pod,
            event_id=poison_id,
            event_type="track.movement.logged",
            payload={"domain": "movement"},  # Missing: duration_mins, entry_id
        )

        # 4. Now publish a valid event AFTER the poison pills
        valid_id = f"test-post-poison-{uuid.uuid4().hex[:8]}"
        time.sleep(2)  # Give consumer time to process the poison
        _publish_event(
            kubectl_exec_python, source_pod,
            event_id=valid_id,
            event_type="track.movement.logged",
            payload={
                "domain": "movement",
                "duration_mins": 5,
                "entry_id": int(uuid.uuid4().int % 1_000_000_000),
                "notes": "post-poison canary",
            },
        )

        # 5. Verify the valid event was processed (consumer survived the poison)
        found = _wait_for_projection(
            kubectl_exec_python, target_pod, valid_id, _check_track_entry, timeout=15.0
        )
        assert found, (
            f"Valid event {valid_id} not processed after poison pills — "
            f"consumer may have crashed"
        )

        # 6. Verify no restart happened
        time.sleep(3)
        pods = _kubectl_json("get", "pods")
        restart_after = 0
        for p in pods["items"]:
            if p["metadata"]["name"] == target_pod:
                for cs in p["status"].get("containerStatuses", []):
                    if cs["name"] == "gateway":
                        restart_after = cs.get("restartCount", 0)

        assert restart_after == restart_before, (
            f"Container restarted during poison pill test "
            f"(before={restart_before}, after={restart_after}) — "
            f"consumer is not resilient to malformed payloads"
        )


class TestAmnesiaRecovery:
    """Wipe a projection database, verify it rebuilds from the stream.

    This proves the system is functionally immortal — any advisor's
    local state can be destroyed and perfectly reconstructed from
    the NATS JetStream history.
    """

    @pytest.mark.slow
    def test_projection_rebuilds_after_wipe(self, kubectl_exec, kubectl_exec_python, advisor_pod_names):
        # Pick an advisor
        advisor = list(advisor_pod_names.keys())[0]
        pod = advisor_pod_names[advisor]

        # 1. Record current projection state
        before_count = kubectl_exec_python(
            pod,
            "python3 -c \"import sqlite3; "
            "db=sqlite3.connect('/opt/data/store/projection.db'); "
            "print(db.execute('SELECT COUNT(*) FROM _processed_events').fetchone()[0]); "
            "db.close()\"",
        )
        before_count = int(before_count.strip())
        assert before_count > 0, "Projection has no events to rebuild from"

        # 2. Delete the projection database
        kubectl_exec(pod, "rm -f /opt/data/store/projection.db*")

        # 3. Verify it's gone
        check = kubectl_exec_python(
            pod,
            "python3 -c \"import os; print(os.path.exists('/opt/data/store/projection.db'))\"",
        )
        assert check.strip() == "False", "projection.db not deleted"

        # 4. Kill the event consumer process so it restarts and replays
        # The consumer runs as a background process in the entrypoint
        # Killing it will cause the entrypoint's wait loop to notice
        # For now, we restart the pod to trigger full replay
        from .conftest import _kubectl
        _kubectl("delete", "pod", pod, "--grace-period=0", "--force")

        # 5. Wait for the new pod to be ready
        time.sleep(30)
        from .conftest import _kubectl_json
        pods = _kubectl_json("get", "pods")
        new_pod = None
        for p in pods["items"]:
            name = p["metadata"]["name"]
            if name.startswith(f"advisor-{advisor}-") and p["status"]["phase"] == "Running":
                ready = all(
                    cs.get("ready", False)
                    for cs in p["status"].get("containerStatuses", [])
                )
                if ready:
                    new_pod = name
                    break

        assert new_pod is not None, f"advisor-{advisor} did not restart within 30s"

        # 6. Wait for projection to rebuild
        time.sleep(10)  # Give consumer time to replay

        after_count = kubectl_exec_python(
            new_pod,
            "python3 -c \"import sqlite3; "
            "db=sqlite3.connect('/opt/data/store/projection.db'); "
            "print(db.execute('SELECT COUNT(*) FROM _processed_events').fetchone()[0]); "
            "db.close()\"",
        )
        after_count = int(after_count.strip())

        # Should have rebuilt at least as many events as before
        # (might have more if events arrived during the restart)
        assert after_count >= before_count, (
            f"Projection rebuild incomplete: {after_count} events after rebuild, "
            f"had {before_count} before wipe"
        )
