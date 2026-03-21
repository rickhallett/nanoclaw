"""Panel builders for the dashctl TUI.

Each function returns a Rich renderable (Panel, Table, etc.)
that the layout engine composes into the full dashboard.
"""

from datetime import datetime, timezone

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

from halos.trackctl import registry, engine, store


def _streak_bar(current: int, target: int, width: int = 20) -> Text:
    """Visual progress bar for streak toward target."""
    if target <= 0:
        # No target — just show streak count
        return Text(f"{current}d", style="bold cyan")
    filled = min(int((current / target) * width), width)
    empty = width - filled
    bar = Text()
    bar.append("█" * filled, style="green")
    bar.append("░" * empty, style="dim")
    pct = min(100, int((current / target) * 100))
    bar.append(f" {pct}%", style="bold" if pct >= 100 else "")
    return bar


def _format_mins(mins: int) -> str:
    """Format minutes as 'Xh Ym' or 'Ym'."""
    if mins >= 60:
        h, m = divmod(mins, 60)
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{mins}m"


def header_panel() -> Panel:
    """Top banner with timestamp and overall stats."""
    registry.load_all()
    domains = registry.all_domains()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total_today = 0
    active_streaks = 0
    for d in domains:
        s = engine.compute_summary(d.name, target=d.target)
        total_today += s["today_mins"]
        if s["current_streak"] > 0:
            active_streaks += 1

    header = Text()
    header.append("HAL METRICS", style="bold magenta")
    header.append(f"  ·  {now}\n", style="dim")
    header.append(f"  {len(domains)} domains", style="cyan")
    header.append(f"  ·  {active_streaks} active streaks", style="green")
    header.append(f"  ·  {_format_mins(total_today)} today", style="yellow")

    return Panel(header, border_style="magenta", box=box.HEAVY)


def domain_panel(domain_name: str) -> Panel:
    """Stats panel for a single tracker domain."""
    info = registry.get(domain_name)
    if not info:
        return Panel(f"Unknown domain: {domain_name}", border_style="red")

    s = engine.compute_summary(domain_name, target=info.target)

    content = Text()

    # Streak line with visual bar
    if info.target and info.target > 0:
        content.append("  STREAK  ", style="bold")
        content.append(f"{s['current_streak']}", style="bold green" if s["current_streak"] > 0 else "bold red")
        content.append(f" / {info.target} days\n", style="dim")
        content.append("  ")
        content.append_text(_streak_bar(s["current_streak"], info.target, width=30))
        content.append("\n")
    else:
        content.append("  STREAK  ", style="bold")
        content.append(f"{s['current_streak']}", style="bold green" if s["current_streak"] > 0 else "bold red")
        content.append(" days\n", style="dim")

    content.append(f"  longest: {s['longest_streak']}d", style="dim")
    content.append(f"  ·  entries: {s['total_entries']}", style="dim")
    content.append("\n\n")

    # Today / All-time
    content.append("  TODAY    ", style="bold")
    today_style = "bold green" if s["today_mins"] > 0 else "bold red"
    content.append(f"{_format_mins(s['today_mins'])}\n", style=today_style)
    content.append("  ALL-TIME ", style="bold")
    content.append(f"{_format_mins(s['alltime_mins'])}", style="cyan")
    content.append(f" ({s['total_days']} days)\n", style="dim")

    # Recent entries (last 3)
    entries = store.list_entries(domain_name, days=3)
    if entries:
        content.append("\n  RECENT\n", style="bold")
        for e in entries[:5]:
            ts = e["timestamp"][:16].replace("T", " ")
            content.append(f"  {ts}  ", style="dim")
            content.append(f"{e['duration_mins']}m", style="cyan")
            if e["notes"]:
                note_preview = e["notes"][:40]
                content.append(f"  {note_preview}", style="dim italic")
            content.append("\n")

    # Color based on streak health
    if s["current_streak"] > 0:
        border = "green"
    elif s["total_entries"] > 0:
        border = "yellow"
    else:
        border = "dim"

    title = f" {info.name} "
    if info.description:
        title += f"· {info.description} "

    return Panel(content, title=title, border_style=border, box=box.ROUNDED)


def eisenhower_panel() -> Panel:
    """Compact Eisenhower matrix summary from nightctl."""
    try:
        from halos.nightctl.item import load_all_items
        from halos.nightctl.config import load_config
        cfg = load_config()
        items = load_all_items(cfg.items_dir)
    except Exception:
        return Panel("nightctl unavailable", title=" tasks ", border_style="red")

    active = [i for i in items if i.status in (
        "open", "planning", "plan-review", "in-progress",
        "review", "testing", "blocked",
    )]

    quadrants = {
        "q1": ("DO FIRST", "red"),
        "q2": ("SCHEDULE", "yellow"),
        "q3": ("DELEGATE", "blue"),
        "q4": ("ELIMINATE", "dim"),
    }

    content = Text()
    for q, (label, style) in quadrants.items():
        group = [i for i in active if i.quadrant == q]
        if not group:
            continue
        content.append(f"  {q.upper()} · {label} ", style=f"bold {style}")
        content.append(f"({len(group)})\n", style="dim")
        for item in group[:4]:
            marker = "*" if item.status == "in-progress" else " "
            title = item.title[:55]
            content.append(f"  [{marker}] {title}\n", style=style)
        if len(group) > 4:
            content.append(f"      ... +{len(group) - 4} more\n", style="dim")
        content.append("\n")

    if not active:
        content.append("  No active tasks\n", style="dim")

    total_active = len(active)
    done = len([i for i in items if i.status == "done"])
    content.append(f"  {total_active} active  ·  {done} done", style="dim")

    return Panel(content, title=" nightctl · eisenhower ", border_style="magenta", box=box.ROUNDED)


def full_dashboard() -> list:
    """Return all panels for the full dashboard layout."""
    registry.load_all()
    domains = registry.all_domains()

    renderables = [header_panel()]

    # Domain panels in two columns where possible
    domain_panels = [domain_panel(d.name) for d in domains]
    renderables.extend(domain_panels)

    # Eisenhower matrix
    renderables.append(eisenhower_panel())

    return renderables
