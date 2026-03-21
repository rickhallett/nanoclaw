"""Health aggregation engine for statusctl.

Runs all check classes, collects results, and computes an overall
health grade: HEALTHY, DEGRADED, or DOWN.
"""

from .checks import (
    CheckResult,
    ServiceCheck,
    ContainerCheck,
    AgentCheck,
    HostCheck,
)


# Checks whose failure means DOWN (not just DEGRADED)
_CRITICAL_CHECKS = {"nanoclaw", "docker", "disk"}


def run_all_checks() -> list[CheckResult]:
    """Run every registered check and return flat list of results."""
    results: list[CheckResult] = []
    for checker in [ServiceCheck(), ContainerCheck(), AgentCheck(), HostCheck()]:
        try:
            results.extend(checker.run())
        except Exception as exc:
            results.append(CheckResult(
                name=type(checker).__name__,
                status="warn",
                message=f"check raised: {exc}",
            ))
    return results


def compute_grade(results: list[CheckResult]) -> str:
    """Determine overall health grade from check results.

    Returns:
        "HEALTHY" — all checks ok
        "DEGRADED" — non-critical failures or warnings
        "DOWN" — critical check failed
    """
    if not results:
        return "HEALTHY"

    has_fail = False
    has_warn = False
    critical_fail = False

    for r in results:
        if r.status == "fail":
            has_fail = True
            if r.name in _CRITICAL_CHECKS:
                critical_fail = True
        elif r.status == "warn":
            has_warn = True

    if critical_fail:
        return "DOWN"
    if has_fail or has_warn:
        return "DEGRADED"
    return "HEALTHY"


def aggregate_metrics(results: list[CheckResult]) -> dict:
    """Flatten all check metrics into a single dict."""
    merged: dict = {}
    for r in results:
        merged.update(r.metrics)
    return merged


def health_report() -> dict:
    """Full health report: results, grade, metrics."""
    results = run_all_checks()
    grade = compute_grade(results)
    metrics = aggregate_metrics(results)
    return {
        "grade": grade,
        "checks": [
            {
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "metrics": r.metrics,
            }
            for r in results
        ],
        "metrics": metrics,
    }
