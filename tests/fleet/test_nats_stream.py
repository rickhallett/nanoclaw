"""Tier 1: NATS JetStream health and consumer registration.

Proves the Halostream event bus is operational and all advisors
are connected as consumers.
"""

import json

import pytest

from .conftest import EXPECTED_ADVISORS, FLEET_NS

pytestmark = [pytest.mark.fleet, pytest.mark.tier1]


def _get_jsz(kubectl_exec, advisor_pod_names) -> dict:
    """Query NATS monitoring endpoint via an advisor pod.

    The NATS container is minimal Alpine (no bash). We reach the
    monitoring endpoint from an advisor pod over the cluster network.
    """
    pod = list(advisor_pod_names.values())[0]
    raw = kubectl_exec(
        pod,
        "python3 -c \"import urllib.request, json; "
        "r = urllib.request.urlopen('http://nats.halo-fleet.svc.cluster.local:8222/jsz?streams=true&consumers=true'); "
        "print(r.read().decode())\"",
    )
    return json.loads(raw)


class TestNATSStream:
    """HALO stream exists with correct configuration."""

    def test_stream_exists(self, kubectl_exec, advisor_pod_names):
        jsz = _get_jsz(kubectl_exec, advisor_pod_names)
        assert jsz["streams"] >= 1, "No JetStream streams found"

        # Find HALO stream
        halo = None
        for acct in jsz.get("account_details", []):
            for s in acct.get("stream_detail", []):
                if s["name"] == "HALO":
                    halo = s
                    break
        assert halo is not None, "HALO stream not found"

    def test_stream_has_messages(self, kubectl_exec, advisor_pod_names):
        jsz = _get_jsz(kubectl_exec, advisor_pod_names)
        assert jsz["messages"] > 0, "HALO stream has zero messages"

    def test_stream_has_subjects(self, kubectl_exec, advisor_pod_names):
        jsz = _get_jsz(kubectl_exec, advisor_pod_names)
        for acct in jsz.get("account_details", []):
            for s in acct.get("stream_detail", []):
                if s["name"] == "HALO":
                    num_subjects = s["state"]["num_subjects"]
                    assert num_subjects > 0, "HALO stream has zero subjects"
                    return
        pytest.fail("HALO stream not found")


class TestNATSConsumers:
    """Every advisor has a registered, caught-up consumer."""

    def test_consumer_count(self, kubectl_exec, advisor_pod_names):
        jsz = _get_jsz(kubectl_exec, advisor_pod_names)
        for acct in jsz.get("account_details", []):
            for s in acct.get("stream_detail", []):
                if s["name"] == "HALO":
                    count = s["state"]["consumer_count"]
                    assert count >= len(EXPECTED_ADVISORS), (
                        f"Expected >= {len(EXPECTED_ADVISORS)} consumers, found {count}"
                    )
                    return
        pytest.fail("HALO stream not found")

    def test_each_advisor_has_consumer(self, kubectl_exec, advisor_pod_names):
        jsz = _get_jsz(kubectl_exec, advisor_pod_names)
        consumer_names = set()
        for acct in jsz.get("account_details", []):
            for s in acct.get("stream_detail", []):
                if s["name"] == "HALO":
                    for c in s.get("consumer_detail", []):
                        consumer_names.add(c["name"])

        for advisor in EXPECTED_ADVISORS:
            assert advisor in consumer_names, (
                f"No NATS consumer for advisor '{advisor}'. "
                f"Registered consumers: {sorted(consumer_names)}"
            )

    def test_consumers_caught_up(self, kubectl_exec, advisor_pod_names):
        """All *expected* consumers should have zero pending messages."""
        jsz = _get_jsz(kubectl_exec, advisor_pod_names)
        behind = {}
        for acct in jsz.get("account_details", []):
            for s in acct.get("stream_detail", []):
                if s["name"] == "HALO":
                    for c in s.get("consumer_detail", []):
                        name = c["name"]
                        # Only check consumers for active advisors
                        if name not in EXPECTED_ADVISORS:
                            continue
                        pending = c.get("num_pending", 0)
                        if pending > 0:
                            behind[name] = pending

        assert not behind, f"Consumers behind: {behind}"

    def test_no_orphaned_consumers(self, kubectl_exec, advisor_pod_names):
        """No NATS consumers for advisors that no longer exist."""
        jsz = _get_jsz(kubectl_exec, advisor_pod_names)
        orphans = []
        for acct in jsz.get("account_details", []):
            for s in acct.get("stream_detail", []):
                if s["name"] == "HALO":
                    for c in s.get("consumer_detail", []):
                        name = c["name"]
                        # Skip system consumers
                        if name.startswith("system"):
                            continue
                        if name not in EXPECTED_ADVISORS:
                            orphans.append(name)

        assert not orphans, (
            f"Orphaned NATS consumers (no matching advisor pod): {orphans}. "
            f"Clean up with: nats consumer rm HALO <name>"
        )
