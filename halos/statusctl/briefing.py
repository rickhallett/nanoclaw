"""Briefing integration for statusctl.

Provides a one-liner suitable for inclusion in morning/nightly briefings.
"""

from .engine import health_report


def text_summary() -> str:
    """One-line health summary for briefing integration.

    Example:
        "statusctl: HEALTHY | 2 containers, 3 sessions, 2 errors/24h | CPU 12%, RAM 26%, Disk 45%"
    """
    report = health_report()
    grade = report["grade"]
    m = report["metrics"]

    containers = m.get("running", 0)
    sessions = m.get("active", 0)
    errors = m.get("error_count_24h", 0)

    cpu = m.get("cpu_pct", "?")
    ram = m.get("ram_pct", "?")
    disk = m.get("disk_pct", "?")

    return (
        f"statusctl: {grade} | "
        f"{containers} containers, {sessions} sessions, {errors} errors/24h | "
        f"CPU {cpu}%, RAM {ram}%, Disk {disk}%"
    )
