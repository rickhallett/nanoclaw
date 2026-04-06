"""Tier 1: Advisor identity and configuration verification.

Proves each advisor knows who it is, has the right persona loaded,
and has the Fleet Context preamble in its system prompt.
"""

import pytest

from .conftest import EXPECTED_ADVISORS, FLEET_NS

pytestmark = [pytest.mark.fleet, pytest.mark.tier1]


class TestAdvisorIdentity:
    """Each advisor's env and config match its intended identity."""

    @pytest.mark.parametrize("advisor", EXPECTED_ADVISORS)
    def test_advisor_name_env(self, kubectl_exec, advisor, advisor_pod_names):
        if advisor not in advisor_pod_names:
            pytest.skip(f"advisor-{advisor} not running")

        pod = advisor_pod_names[advisor]
        name = kubectl_exec(pod, "echo $ADVISOR_NAME")
        assert name == advisor, (
            f"Pod for {advisor} has ADVISOR_NAME={name}"
        )

    @pytest.mark.parametrize("advisor", EXPECTED_ADVISORS)
    def test_fleet_context_in_prompt(self, kubectl_exec, advisor, advisor_pod_names):
        """Every advisor's system prompt contains the Fleet Context preamble."""
        if advisor not in advisor_pod_names:
            pytest.skip(f"advisor-{advisor} not running")

        pod = advisor_pod_names[advisor]
        # System prompt is loaded via HERMES_EPHEMERAL_SYSTEM_PROMPT env
        # or from /opt/data/system-prompt.md
        prompt = kubectl_exec(pod, "cat /opt/data/system-prompt.md 2>/dev/null || echo MISSING")
        assert "Fleet Context" in prompt, (
            f"advisor-{advisor} system prompt missing Fleet Context preamble"
        )
        assert "Halostream" in prompt, (
            f"advisor-{advisor} system prompt missing Halostream reference"
        )

    @pytest.mark.parametrize("advisor", EXPECTED_ADVISORS)
    def test_memctl_config_present(self, kubectl_exec, advisor, advisor_pod_names):
        """Every advisor has the memctl reader config mounted."""
        if advisor not in advisor_pod_names:
            pytest.skip(f"advisor-{advisor} not running")

        pod = advisor_pod_names[advisor]
        config = kubectl_exec(pod, "cat /opt/config/memctl.yaml 2>/dev/null || echo MISSING")
        assert "memory_dir: /memory" in config, (
            f"advisor-{advisor} memctl config missing or wrong"
        )
        assert "auto_rebuild: false" in config, (
            f"advisor-{advisor} should have auto_rebuild: false (read-only)"
        )
