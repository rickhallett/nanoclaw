"""Fleet test fixtures — kubectl helpers, cluster access, advisor registry.

These tests run against a live cluster. They require:
- KUBECONFIG set (or in-cluster config)
- kubectl available on PATH
- The halo-fleet namespace deployed and healthy

All fixtures are session-scoped to avoid repeated cluster queries.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

FLEET_NS = "halo-fleet"
INFRA_NS = "halo-infra"
ARGOCD_NS = "argocd"

EXPECTED_ADVISORS = [
    "musashi",
    "draper",
    "karpathy",
    "gibson",
    "machiavelli",
    "medici",
    "bankei",
]

EXPECTED_INFRA_PODS = [
    "memctl-authority",
    "nats",
]

NFS_CLUSTER_IP = "10.100.54.223"


def _kubectl(*args: str, namespace: str = FLEET_NS, timeout: int = 30) -> subprocess.CompletedResult:
    """Run kubectl and return the result."""
    cmd = ["kubectl", *args, "-n", namespace]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _kubectl_json(*args: str, namespace: str = FLEET_NS) -> dict | list:
    """Run kubectl with -o json and parse the result."""
    result = _kubectl(*args, "-o", "json", namespace=namespace)
    if result.returncode != 0:
        raise RuntimeError(f"kubectl failed: {result.stderr}")
    return json.loads(result.stdout)


def _kubectl_exec(pod: str, command: str, namespace: str = FLEET_NS, container: str | None = None) -> str:
    """Exec a command inside a pod and return stdout."""
    cmd = ["kubectl", "exec", pod, "-n", namespace]
    if container:
        cmd.extend(["-c", container])
    cmd.extend(["--", "bash", "-c", command])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"exec in {pod} failed: {result.stderr}")
    return result.stdout.strip()


def _kubectl_exec_python(pod: str, script: str, namespace: str = FLEET_NS, container: str | None = None) -> str:
    """Write a Python script to the pod's /tmp, execute it, return stdout.

    Avoids shell quoting hell with inline python3 -c.
    """
    import base64
    encoded = base64.b64encode(script.encode()).decode()
    # Write base64 to file, decode, execute
    wrapper = f'echo {encoded} | base64 -d > /tmp/_fleet_test.py && python3 /tmp/_fleet_test.py'
    cmd = ["kubectl", "exec", pod, "-n", namespace]
    if container:
        cmd.extend(["-c", container])
    cmd.extend(["--", "bash", "-c", wrapper])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"exec_python in {pod} failed: {result.stderr}")
    return result.stdout.strip()


def _cluster_available() -> bool:
    """Check if kubectl can reach the cluster."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Skip all fleet tests if cluster is unreachable
pytestmark = pytest.mark.skipif(
    not _cluster_available(),
    reason="Cluster not reachable (KUBECONFIG not set or cluster down)",
)


@pytest.fixture(scope="session")
def kubectl():
    """Returns the _kubectl helper function."""
    return _kubectl


@pytest.fixture(scope="session")
def kubectl_json():
    """Returns the _kubectl_json helper function."""
    return _kubectl_json


@pytest.fixture(scope="session")
def kubectl_exec():
    """Returns the _kubectl_exec helper function."""
    return _kubectl_exec


@pytest.fixture(scope="session")
def kubectl_exec_python():
    """Returns the _kubectl_exec_python helper (for multi-line scripts)."""
    return _kubectl_exec_python


@pytest.fixture(scope="session")
def fleet_pods(kubectl_json) -> list[dict]:
    """All pods in halo-fleet namespace."""
    data = kubectl_json("get", "pods")
    return data.get("items", [])


@pytest.fixture(scope="session")
def advisor_pods(fleet_pods) -> dict[str, dict]:
    """Map of advisor name → pod dict."""
    result = {}
    for pod in fleet_pods:
        name = pod["metadata"]["name"]
        for advisor in EXPECTED_ADVISORS:
            if name.startswith(f"advisor-{advisor}-"):
                result[advisor] = pod
    return result


@pytest.fixture(scope="session")
def advisor_pod_names(advisor_pods) -> dict[str, str]:
    """Map of advisor name → pod name (for kubectl exec)."""
    return {k: v["metadata"]["name"] for k, v in advisor_pods.items()}
