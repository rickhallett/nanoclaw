"""statusctl CLI — fleet health monitoring.

Usage:
    statusctl                   # full health report (Rich)
    statusctl check             # exit 0 if HEALTHY, exit 1 otherwise
    statusctl metrics --json    # host resource snapshot
    statusctl report            # one-liner for briefings
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from halos.common.log import hlog


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="statusctl",
        description="statusctl — fleet health monitoring",
    )
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output as JSON")

    sub = parser.add_subparsers(dest="command")

    # --- check ---
    sub.add_parser("check", help="Exit 0 if HEALTHY, exit 1 otherwise")

    # --- metrics ---
    p_metrics = sub.add_parser("metrics", help="Host resource snapshot")
    p_metrics.add_argument("--json", action="store_true", dest="json_out",
                           help="Output as JSON")

    # --- report ---
    sub.add_parser("report", help="One-liner summary for briefings")

    args = parser.parse_args()

    if args.command is None:
        cmd_default(args)
    elif args.command == "check":
        sys.exit(cmd_check(args))
    elif args.command == "metrics":
        sys.exit(cmd_metrics(args))
    elif args.command == "report":
        sys.exit(cmd_report(args))


def cmd_default(args) -> None:
    """Full health report with Rich formatting."""
    from .engine import health_report

    report = health_report()
    grade = report["grade"]
    checks = report["checks"]
    metrics = report["metrics"]

    if getattr(args, "json_out", False):
        print(json.dumps(report, indent=2))
        return

    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel
    from rich import box

    console = Console()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    content = Text()
    content.append(f"NanoClaw Health — {now}\n\n", style="bold")

    # Service checks
    service_names = {"nanoclaw", "credential-proxy", "docker"}
    for c in checks:
        if c["name"] in service_names:
            icon = _status_icon(c["status"])
            content.append(f"  Service     {c['name']:<20} {icon} {c['message']}\n")

    content.append("\n")

    # Container / session / error summary
    containers_running = metrics.get("running", 0)
    exited_error = metrics.get("exited_error", 0)
    sessions = metrics.get("active", 0)
    spinning = metrics.get("spinning", 0)
    errors_24h = metrics.get("error_count_24h", 0)

    content.append(f"  Containers  {containers_running} running, {exited_error} exited-error\n")
    content.append(f"  Sessions    {sessions} active, {spinning} spinning\n")
    content.append(f"  Errors      {errors_24h} in 24h\n")
    content.append("\n")

    # Host metrics
    cpu_pct = metrics.get("cpu_pct", "?")
    ram_used = metrics.get("used_gb", "?")
    ram_total = metrics.get("total_gb", "?")
    disk_pct = metrics.get("disk_pct", "?")
    content.append(f"  Host        CPU {cpu_pct}% | RAM {ram_used}/{ram_total} GB | Disk {disk_pct}%\n")
    content.append("\n")

    # Grade
    grade_style = {
        "HEALTHY": "bold green",
        "DEGRADED": "bold yellow",
        "DOWN": "bold red",
    }.get(grade, "bold")

    content.append("  Status: ", style="bold")
    content.append(grade, style=grade_style)
    content.append("\n")

    console.print(Panel(content, box=box.ROUNDED, border_style="cyan"))

    hlog("statusctl", "info", "health_check", {"grade": grade})


def cmd_check(args) -> int:
    """Exit 0 if HEALTHY, exit 1 with failures on stderr."""
    from .engine import health_report

    report = health_report()
    grade = report["grade"]

    hlog("statusctl", "info", "gate_check", {"grade": grade})

    if grade == "HEALTHY":
        return 0

    # Output failures to stderr
    failures = [c for c in report["checks"] if c["status"] != "ok"]
    print(json.dumps(failures), file=sys.stderr)
    return 1


def cmd_metrics(args) -> int:
    """Host resource snapshot."""
    from .checks import HostCheck

    results = HostCheck().run()
    metrics: dict = {}
    for r in results:
        metrics[r.name] = {
            "status": r.status,
            "message": r.message,
            **r.metrics,
        }

    if getattr(args, "json_out", False):
        print(json.dumps(metrics, indent=2))
    else:
        for name, data in metrics.items():
            status = data.pop("status", "ok")
            message = data.pop("message", "")
            print(f"  {name:<10} {message}")

    return 0


def cmd_report(args) -> int:
    """One-liner summary (alias for briefing integration)."""
    from .briefing import text_summary
    print(text_summary())
    return 0


def _status_icon(status: str) -> str:
    """Map status to a terminal-safe indicator."""
    return {
        "ok": "[green]OK[/green]",
        "warn": "[yellow]WARN[/yellow]",
        "fail": "[red]FAIL[/red]",
    }.get(status, status)


if __name__ == "__main__":
    main()
