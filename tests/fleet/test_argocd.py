"""Tier 1: Argo CD sync and drift verification.

Proves GitOps is working — the cluster matches git, not somebody's
last kubectl apply.
"""

import json
import subprocess

import pytest

from .conftest import FLEET_NS, INFRA_NS

pytestmark = [pytest.mark.fleet, pytest.mark.tier1]


def _argocd_app() -> dict | None:
    """Get the halo-fleet Argo CD Application status."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "application", "halo-fleet",
             "-n", "argocd", "-o", "json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return None


class TestArgoCDHealth:
    """Argo CD Application is synced and healthy."""

    def test_app_exists(self):
        app = _argocd_app()
        assert app is not None, "halo-fleet Application not found in argocd namespace"

    def test_sync_status(self):
        app = _argocd_app()
        if app is None:
            pytest.skip("Argo CD not available")
        sync = app.get("status", {}).get("sync", {}).get("status", "Unknown")
        assert sync == "Synced", f"Argo sync status: {sync} (expected Synced)"

    def test_health_status(self):
        app = _argocd_app()
        if app is None:
            pytest.skip("Argo CD not available")
        health = app.get("status", {}).get("health", {}).get("status", "Unknown")
        assert health == "Healthy", f"Argo health status: {health} (expected Healthy)"

    def test_no_degraded_resources(self):
        app = _argocd_app()
        if app is None:
            pytest.skip("Argo CD not available")
        resources = app.get("status", {}).get("resources", [])
        degraded = [
            r for r in resources
            if r.get("health", {}).get("status") == "Degraded"
        ]
        assert not degraded, (
            f"Degraded resources: {[r['name'] for r in degraded]}"
        )

    def test_git_sha_matches(self):
        """Running cluster spec matches the HEAD of the tracked branch."""
        app = _argocd_app()
        if app is None:
            pytest.skip("Argo CD not available")

        # Get the revision Argo synced to
        synced_rev = (
            app.get("status", {})
            .get("sync", {})
            .get("revision", "unknown")
        )

        # Get the HEAD of the tracked branch from git
        target = (
            app.get("spec", {})
            .get("source", app.get("spec", {}).get("sources", [{}])[0])
            .get("targetRevision", "unknown")
        )

        try:
            result = subprocess.run(
                ["git", "rev-parse", f"origin/{target}"],
                capture_output=True, text=True, timeout=10,
            )
            git_head = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("git not available")
            return

        assert synced_rev == git_head, (
            f"Argo synced to {synced_rev[:12]} but git HEAD is {git_head[:12]}"
        )


class TestNamespaceSecurity:
    """Namespace PodSecurity labels are correct."""

    def test_fleet_namespace_baseline(self):
        result = subprocess.run(
            ["kubectl", "get", "ns", "halo-fleet", "-o",
             "jsonpath={.metadata.labels.pod-security\\.kubernetes\\.io/enforce}"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.stdout.strip() == "baseline", (
            f"halo-fleet enforce level: {result.stdout.strip()} (expected baseline)"
        )

    def test_infra_namespace_privileged(self):
        result = subprocess.run(
            ["kubectl", "get", "ns", "halo-infra", "-o",
             "jsonpath={.metadata.labels.pod-security\\.kubernetes\\.io/enforce}"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.stdout.strip() == "privileged", (
            f"halo-infra enforce level: {result.stdout.strip()} (expected privileged)"
        )
