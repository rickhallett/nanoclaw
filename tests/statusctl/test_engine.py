"""Unit tests for statusctl engine."""

from unittest.mock import patch

from halos.statusctl.checks import CheckResult
from halos.statusctl.engine import (
    compute_grade,
    aggregate_metrics,
    run_all_checks,
    health_report,
)


class TestComputeGrade:
    def test_all_ok_is_healthy(self):
        results = [
            CheckResult(name="nanoclaw", status="ok", message="running"),
            CheckResult(name="docker", status="ok", message="running"),
            CheckResult(name="cpu", status="ok", message="5%"),
        ]
        assert compute_grade(results) == "HEALTHY"

    def test_non_critical_warn_is_degraded(self):
        results = [
            CheckResult(name="nanoclaw", status="ok", message="running"),
            CheckResult(name="sessions", status="warn", message="high errors"),
            CheckResult(name="cpu", status="ok", message="5%"),
        ]
        assert compute_grade(results) == "DEGRADED"

    def test_non_critical_fail_is_degraded(self):
        results = [
            CheckResult(name="nanoclaw", status="ok", message="running"),
            CheckResult(name="credential-proxy", status="fail", message="not listening"),
            CheckResult(name="cpu", status="ok", message="5%"),
        ]
        assert compute_grade(results) == "DEGRADED"

    def test_critical_fail_is_down(self):
        results = [
            CheckResult(name="nanoclaw", status="fail", message="not running"),
            CheckResult(name="docker", status="ok", message="running"),
        ]
        assert compute_grade(results) == "DOWN"

    def test_docker_fail_is_down(self):
        results = [
            CheckResult(name="nanoclaw", status="ok", message="running"),
            CheckResult(name="docker", status="fail", message="unreachable"),
        ]
        assert compute_grade(results) == "DOWN"

    def test_disk_critical_is_down(self):
        results = [
            CheckResult(name="disk", status="fail", message="96% — CRITICAL"),
        ]
        assert compute_grade(results) == "DOWN"

    def test_empty_results_is_healthy(self):
        assert compute_grade([]) == "HEALTHY"

    def test_mixed_results(self):
        results = [
            CheckResult(name="nanoclaw", status="ok", message="running"),
            CheckResult(name="sessions", status="warn", message="timeout"),
            CheckResult(name="disk", status="ok", message="45%"),
            CheckResult(name="errors", status="ok", message="2 errors"),
        ]
        assert compute_grade(results) == "DEGRADED"


class TestAggregateMetrics:
    def test_merges_all_metrics(self):
        results = [
            CheckResult(name="cpu", status="ok", message="5%",
                        metrics={"cpu_pct": 5, "load_1min": 0.5}),
            CheckResult(name="disk", status="ok", message="45%",
                        metrics={"disk_pct": 45}),
        ]
        merged = aggregate_metrics(results)
        assert merged["cpu_pct"] == 5
        assert merged["disk_pct"] == 45
        assert merged["load_1min"] == 0.5

    def test_empty_results(self):
        assert aggregate_metrics([]) == {}


class TestRunAllChecks:
    def test_returns_results_from_all_checkers(self):
        """Ensure run_all_checks calls all checker classes and returns results."""
        fake_result = CheckResult(name="test", status="ok", message="mocked")

        with patch("halos.statusctl.engine.ServiceCheck") as mock_svc, \
             patch("halos.statusctl.engine.ContainerCheck") as mock_ctr, \
             patch("halos.statusctl.engine.AgentCheck") as mock_agt, \
             patch("halos.statusctl.engine.HostCheck") as mock_host:

            for mock_cls in [mock_svc, mock_ctr, mock_agt, mock_host]:
                mock_cls.return_value.run.return_value = [fake_result]

            results = run_all_checks()

        assert len(results) == 4
        assert all(r.name == "test" for r in results)

    def test_checker_exception_caught(self):
        """If a checker raises, it should be caught and reported as warn."""
        with patch("halos.statusctl.engine.ServiceCheck") as mock_svc, \
             patch("halos.statusctl.engine.ContainerCheck") as mock_ctr, \
             patch("halos.statusctl.engine.AgentCheck") as mock_agt, \
             patch("halos.statusctl.engine.HostCheck") as mock_host:

            mock_svc.return_value.run.side_effect = RuntimeError("boom")
            ok_result = CheckResult(name="ok", status="ok", message="fine")
            mock_ctr.return_value.run.return_value = [ok_result]
            mock_agt.return_value.run.return_value = [ok_result]
            mock_host.return_value.run.return_value = [ok_result]

            results = run_all_checks()

        # Should still have results (3 ok + 1 warn from exception)
        assert len(results) == 4
        warn = [r for r in results if r.status == "warn"]
        assert len(warn) == 1
        assert "boom" in warn[0].message


class TestHealthReport:
    def test_returns_full_structure(self):
        fake_result = CheckResult(
            name="test", status="ok", message="mocked",
            metrics={"cpu_pct": 5},
        )

        with patch("halos.statusctl.engine.ServiceCheck") as mock_svc, \
             patch("halos.statusctl.engine.ContainerCheck") as mock_ctr, \
             patch("halos.statusctl.engine.AgentCheck") as mock_agt, \
             patch("halos.statusctl.engine.HostCheck") as mock_host:

            for mock_cls in [mock_svc, mock_ctr, mock_agt, mock_host]:
                mock_cls.return_value.run.return_value = [fake_result]

            report = health_report()

        assert "grade" in report
        assert "checks" in report
        assert "metrics" in report
        assert report["grade"] == "HEALTHY"
        assert report["metrics"]["cpu_pct"] == 5
