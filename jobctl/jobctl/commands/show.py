"""jobctl show — show full details of a listing."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from jobctl.db import get_conn, init_db

console = Console()


def find_listing(conn, id_prefix: str):
    """Find a listing by full ID or prefix."""
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (id_prefix,)).fetchone()
    if row:
        return row
    # Try prefix match
    rows = conn.execute("SELECT * FROM listings WHERE id LIKE ?", (id_prefix + "%",)).fetchall()
    if len(rows) == 1:
        return rows[0]
    if len(rows) > 1:
        raise click.UsageError(f"Ambiguous ID prefix '{id_prefix}' — matches {len(rows)} listings. Use more characters.")
    return None


@click.command("show")
@click.argument("id")
def show_cmd(id):
    """Show full details of a listing."""
    init_db()
    conn = get_conn()

    row = find_listing(conn, id)
    if not row:
        click.echo(f"No listing found with ID: {id}", err=True)
        conn.close()
        return

    # Show metadata table
    meta = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    meta.add_column("Field", style="bold dim", width=14)
    meta.add_column("Value")

    meta.add_row("ID", row["id"])
    meta.add_row("Company", row["company"])
    meta.add_row("Title", row["title"])
    meta.add_row("Status", row["status"])
    meta.add_row("Score", f"{row['score']:.3f}" if row["score"] is not None else "—")
    meta.add_row("Location", row["location"] or "—")
    meta.add_row("Salary", row["salary"] or "—")
    meta.add_row("URL", row["url"] or "—")
    meta.add_row("Source", row["source"])
    meta.add_row("Created", row["created_at"])
    meta.add_row("Updated", row["updated_at"])
    if row["notes"]:
        meta.add_row("Notes", row["notes"])

    console.print(Panel(meta, title=f"[bold]{row['company']} — {row['title']}[/bold]", expand=False))

    if row["description"]:
        console.print("\n[bold]Description:[/bold]")
        console.print(row["description"])

    # Show associated materials
    materials = conn.execute(
        "SELECT type, created_at FROM materials WHERE listing_id = ?",
        (row["id"],)
    ).fetchall()

    if materials:
        console.print("\n[bold]Generated Materials:[/bold]")
        for m in materials:
            console.print(f"  • {m['type']} ({m['created_at'][:10]})")

    conn.close()
