"""jobctl status — summary counts by status."""

import click
from rich.console import Console
from rich.table import Table
from rich import box

from jobctl.db import get_conn, init_db

console = Console()

STATUS_ORDER = ["pending_review", "accepted", "applied", "interviewing", "offered", "rejected", "dismissed"]
STATUS_COLORS = {
    "pending_review": "yellow",
    "accepted": "green",
    "applied": "blue",
    "interviewing": "cyan",
    "offered": "bold green",
    "rejected": "red",
    "dismissed": "dim",
}


@click.command("status")
def status_cmd():
    """Show summary counts by status."""
    init_db()
    conn = get_conn()

    rows = conn.execute(
        "SELECT status, COUNT(*) as count FROM listings GROUP BY status"
    ).fetchall()

    counts = {row["status"]: row["count"] for row in rows}
    total = sum(counts.values())

    conn.close()

    if not counts:
        click.echo("No listings in database. Run `jobctl seed` to import vacancies.")
        return

    table = Table(title="Job Listings by Status", box=box.ROUNDED, show_footer=True)
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    for status in STATUS_ORDER:
        count = counts.get(status, 0)
        if count == 0 and status not in counts:
            continue
        color = STATUS_COLORS.get(status, "white")
        table.add_row(
            f"[{color}]{status}[/{color}]",
            f"[{color}]{count}[/{color}]",
        )

    # Add any statuses not in our expected order
    for status, count in counts.items():
        if status not in STATUS_ORDER:
            table.add_row(status, str(count))

    table.columns[1].footer = f"[bold]{total}[/bold]"
    table.columns[0].footer = "[bold]Total[/bold]"

    console.print(table)
