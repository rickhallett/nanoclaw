"""dashctl CLI — TUI dashboard for personal metrics.

Usage:
    dashctl              # single render
    dashctl --live       # auto-refresh every 30s
    dashctl --json       # JSON export of all domain summaries
    dashctl --text       # plain-text summary for agent/briefing consumption
    dashctl --html       # export as self-contained HTML file
"""

import argparse
import json
import sys
import time

from halos.trackctl import registry, engine


def cmd_render(args):
    """Render the full dashboard once."""
    from rich.console import Console
    from .panels import full_dashboard

    console = Console()
    for panel in full_dashboard():
        console.print(panel)


def cmd_live(args):
    """Live auto-refreshing dashboard."""
    from rich.live import Live
    from rich.console import Group
    from .panels import full_dashboard

    interval = getattr(args, "interval", 30) or 30

    def render():
        return Group(*full_dashboard())

    with Live(render(), refresh_per_second=0.1, screen=True) as live:
        try:
            while True:
                time.sleep(interval)
                live.update(render())
        except KeyboardInterrupt:
            pass


def cmd_json(args):
    """Export all domain summaries as JSON."""
    registry.load_all()
    domains = registry.all_domains()
    output = {}
    for d in domains:
        output[d.name] = engine.compute_summary(d.name, target=d.target)
    print(json.dumps(output, indent=2))


def cmd_html(args):
    """Export dashboard as a self-contained HTML file."""
    from .panels import full_dashboard
    from .html_export import render_html

    panels = full_dashboard()
    output_path = args.output or "store/dashboard.html"
    written = render_html(panels, output_path)
    print(f"Dashboard written to {written}")

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{written}")


def cmd_text(args):
    """Plain-text summary for agent/briefing consumption."""
    registry.load_all()
    domains = registry.all_domains()
    lines = []
    for d in domains:
        lines.append(engine.text_summary(d.name, target=d.target))

    # Add nightctl task counts
    try:
        from halos.nightctl.item import load_all_items
        from halos.nightctl.config import load_config
        cfg = load_config()
        items = load_all_items(cfg.items_dir)
        active = [i for i in items if i.status in (
            "open", "planning", "plan-review", "in-progress",
            "review", "testing", "blocked",
        )]
        q_counts = {}
        for i in active:
            q_counts[i.quadrant] = q_counts.get(i.quadrant, 0) + 1
        parts = [f"{q}: {n}" for q, n in sorted(q_counts.items())]
        lines.append(f"tasks: {len(active)} active ({', '.join(parts)})")
    except Exception:
        pass

    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(
        prog="dashctl",
        description="dashctl — TUI dashboard for personal metrics",
    )
    parser.add_argument("--live", action="store_true", help="Auto-refresh mode")
    parser.add_argument("--interval", type=int, default=30,
                        help="Refresh interval in seconds (with --live)")
    parser.add_argument("--json", action="store_true", help="JSON export")
    parser.add_argument("--text", action="store_true", help="Plain-text for agents")
    parser.add_argument("--html", action="store_true", help="Export as HTML file")
    parser.add_argument("--output", type=str, default=None,
                        help="Output path for --html (default: store/dashboard.html)")
    parser.add_argument("--open", action="store_true",
                        help="Open HTML in browser after writing (with --html)")

    args = parser.parse_args()

    if args.html:
        cmd_html(args)
    elif args.json:
        cmd_json(args)
    elif args.text:
        cmd_text(args)
    elif args.live:
        cmd_live(args)
    else:
        cmd_render(args)


if __name__ == "__main__":
    main()
