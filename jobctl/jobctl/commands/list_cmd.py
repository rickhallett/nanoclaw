"""jobctl list — list job listings."""

import click
from rich.console import Console
from rich.table import Table

from jobctl.db import get_conn, init_db

console = Console()

VALID_STATUSES = ["pending_review", "accepted", "dismissed", "applied", "interviewing", "rejected", "offered"]


@click.command("list")
@click.option("--status", default=None, help=f"Filter by status: {', '.join(VALID_STATUSES)}")
@click.option("--limit", default=50, help="Max results to show")
def list_cmd(status, limit):
    """List job listings."""
    init_db()
    conn = get_conn()

    if status:
        rows = conn.execute(
            "SELECT id, company, title, status, score, location FROM listings WHERE status = ? ORDER BY score DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, company, title, status, score, location FROM listings ORDER BY score DESC LIMIT ?",
            (limit,)
        ).fetchall()

    conn.close()

    if not rows:
        click.echo("No listings found." + (f" (status={status})" if status else ""))
        return

    table = Table(title=f"Job Listings{f' [{status}]' if status else ''}", show_lines=False)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Company", style="bold cyan", min_width=20)
    table.add_column("Title", min_width=30)
    table.add_column("Status", style="yellow", width=16)
    table.add_column("Score", justify="right", width=6)
    table.add_column("Location", style="dim", min_width=15)

    for row in rows:
        short_id = row["id"][:8]
        score_str = f"{row['score']:.2f}" if row["score"] is not None else "—"
        table.add_row(
            short_id,
            row["company"],
            row["title"],
            row["status"],
            score_str,
            row["location"] or "—",
        )

    console.print(table)
