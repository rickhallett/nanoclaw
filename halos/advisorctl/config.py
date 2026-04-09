"""Advisor fleet endpoint configuration.

Resolution order for a given advisor:
  1. --url flag (explicit override)
  2. ADVISORCTL_URL env var (single-advisor dev shortcut)
  3. In-cluster convention: http://advisor-{name}:8642
  4. Local fallback: http://localhost:8642 (port-forward assumed)
"""

from __future__ import annotations

import os
from pathlib import Path

# Active fleet advisors — must match infra/k8s/fleet/*-deployment.yaml
FLEET_ADVISORS = [
    "bankei",
    "draper",
    "gibson",
    "hightower",
    "karpathy",
    "machiavelli",
    "medici",
    "musashi",
]

DEFAULT_PORT = 8642
CLUSTER_DOMAIN = "halo-fleet.svc.cluster.local"


def is_in_cluster() -> bool:
    """Detect if running inside a Kubernetes pod."""
    return "KUBERNETES_SERVICE_HOST" in os.environ


def resolve_url(advisor: str, url_override: str | None = None) -> str:
    """Return the HTTP base URL for the given advisor's API server."""
    if url_override:
        return url_override.rstrip("/")

    env_url = os.environ.get("ADVISORCTL_URL")
    if env_url:
        return env_url.rstrip("/")

    if is_in_cluster():
        return f"http://advisor-{advisor}.{CLUSTER_DOMAIN}:{DEFAULT_PORT}"

    return f"http://localhost:{DEFAULT_PORT}"


def advisor_data_dir() -> Path:
    """Return the path to data/advisors/ relative to repo root."""
    return Path(__file__).resolve().parents[2] / "data" / "advisors"


def persona_path(advisor: str) -> Path:
    return advisor_data_dir() / advisor / "persona.md"


def rubric_path(advisor: str) -> Path:
    return advisor_data_dir() / advisor / "rubric.yaml"
