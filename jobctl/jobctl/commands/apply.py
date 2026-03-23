"""jobctl apply — generate tailored application materials for a listing."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from jobctl.db import get_conn, init_db
from jobctl.generator import generate_cover_letter
from jobctl.commands.show import find_listing

CV_PATH = Path.home() / "code/nanoclaw/docs/job-applications/thinking-machines-devprod/cv.md"
APPS_DIR = Path.home() / "code/nanoclaw/store/applications"

console = Console()


@click.command("apply")
@click.argument("id")
@click.option("--no-materials", is_flag=True, default=False, help="Skip generation, just log application")
def apply_cmd(id, no_materials):
    """Generate tailored cover letter and CV for a listing."""
    init_db()
    conn = get_conn()

    row = find_listing(conn, id)
    if not row:
        click.echo(f"No listing found with ID: {id}", err=True)
        conn.close()
        return

    if row["status"] == "applied":
        click.echo(
            f"Already applied to {row['company']} — {row['title']} on {row['updated_at'][:10]}. "
            "Use `jobctl update` to change status."
        )
        conn.close()
        return

    now = datetime.now(timezone.utc).isoformat()
    listing_id = row["id"]

    app_dir = APPS_DIR / listing_id
    app_dir.mkdir(parents=True, exist_ok=True)

    if not no_materials:
        console.print(f"[bold]Generating materials for:[/bold] {row['company']} — {row['title']}")

        # Generate cover letter
        with console.status("[bold green]Calling Anthropic API..."):
            try:
                cover_letter = generate_cover_letter(
                    company=row["company"],
                    title=row["title"],
                    description=row["description"],
                )
            except RuntimeError as e:
                click.echo(f"Error generating cover letter: {e}", err=True)
                conn.close()
                return

        # Save cover letter to file
        cl_path = app_dir / "cover-letter.md"
        cl_path.write_text(cover_letter)

        # Copy canonical CV
        cv_dest = app_dir / "cv.md"
        if CV_PATH.exists():
            cv_dest.write_text(CV_PATH.read_text())

        # Store in materials table
        conn.execute(
            "INSERT INTO materials (id, listing_id, type, content, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), listing_id, "cover_letter", cover_letter, now)
        )
        conn.execute(
            "INSERT INTO materials (id, listing_id, type, content, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), listing_id, "cv", CV_PATH.read_text() if CV_PATH.exists() else "", now)
        )

        console.print(Panel(
            cover_letter,
            title=f"[bold green]Cover Letter — {row['company']}[/bold green]",
        ))
        console.print(f"\n[dim]Saved to: {app_dir}/[/dim]")

    # Update listing status
    conn.execute(
        "UPDATE listings SET status='applied', updated_at=? WHERE id=?",
        (now, listing_id)
    )
    conn.commit()
    conn.close()

    console.print(f"\n[bold green]✓[/bold green] Marked as [bold]applied[/bold]. Application files in: [blue]{app_dir}[/blue]")
    if row["url"]:
        console.print(f"[dim]Apply at: {row['url']}[/dim]")
