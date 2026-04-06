"""Tier 1: Pod roster and health.

Proves the machine is assembled correctly — right number of pods,
all Running, no ghosts.
"""

import pytest

from .conftest import EXPECTED_ADVISORS, EXPECTED_INFRA_PODS, FLEET_NS, INFRA_NS

pytestmark = [pytest.mark.fleet, pytest.mark.tier1]


class TestPodRoster:
    """Every expected pod exists and is healthy."""

    def test_all_advisors_present(self, advisor_pods):
        missing = set(EXPECTED_ADVISORS) - set(advisor_pods.keys())
        assert not missing, f"Missing advisor pods: {missing}"

    def test_all_advisors_running(self, advisor_pods):
        for name, pod in advisor_pods.items():
            phase = pod["status"]["phase"]
            assert phase == "Running", f"advisor-{name} is {phase}, expected Running"

    def test_all_advisors_ready(self, advisor_pods):
        for name, pod in advisor_pods.items():
            containers = pod["status"].get("containerStatuses", [])
            for c in containers:
                assert c["ready"], (
                    f"advisor-{name} container {c['name']} not ready"
                )

    def test_memctl_authority_running(self, fleet_pods):
        authority = [
            p for p in fleet_pods
            if p["metadata"]["name"].startswith("memctl-authority-")
        ]
        assert len(authority) == 1, f"Expected 1 memctl-authority, found {len(authority)}"
        assert authority[0]["status"]["phase"] == "Running"

    def test_nats_running(self, fleet_pods):
        nats = [
            p for p in fleet_pods
            if p["metadata"]["name"].startswith("nats-")
            and "init" not in p["metadata"]["name"]
        ]
        assert len(nats) == 1, f"Expected 1 NATS pod, found {len(nats)}"
        assert nats[0]["status"]["phase"] == "Running"

    def test_nfs_server_running(self, kubectl_json):
        data = kubectl_json("get", "pods", namespace=INFRA_NS)
        nfs = [
            p for p in data["items"]
            if p["metadata"]["name"].startswith("nfs-server-")
        ]
        assert len(nfs) == 1, f"Expected 1 NFS server, found {len(nfs)}"
        assert nfs[0]["status"]["phase"] == "Running"

    def test_no_ghost_pods(self, fleet_pods):
        """No pods that aren't in our expected roster."""
        expected_prefixes = (
            [f"advisor-{a}-" for a in EXPECTED_ADVISORS]
            + ["memctl-authority-", "nats-"]
        )
        for pod in fleet_pods:
            name = pod["metadata"]["name"]
            phase = pod["status"]["phase"]
            # Skip completed jobs (nats-init-stream)
            if phase in ("Succeeded",):
                continue
            matches = any(name.startswith(prefix) for prefix in expected_prefixes)
            assert matches, f"Ghost pod detected: {name} (phase={phase})"

    def test_no_crashloop(self, fleet_pods):
        for pod in fleet_pods:
            name = pod["metadata"]["name"]
            for cs in pod["status"].get("containerStatuses", []):
                restart_count = cs.get("restartCount", 0)
                waiting = cs.get("state", {}).get("waiting", {})
                reason = waiting.get("reason", "")
                assert reason != "CrashLoopBackOff", (
                    f"{name} is in CrashLoopBackOff (restarts={restart_count})"
                )
