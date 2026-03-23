"""jobctl review — interactive TUI for reviewing pending listings."""

import sys
import uuid
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from jobctl.db import get_conn, init_db

console = Console()


def _get_keypress() -> str:
    """Read a single keypress without requiring Enter."""
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


@click.command("review")
def review_cmd():
    """Interactive review of pending_review listings. Keys: (a)ccept (d)ismiss (s)kip (q)uit."""
    init_db()
    conn = get_conn()

    rows = conn.execute(
        "SELECT * FROM listings WHERE status = 'pending_review' ORDER BY score DESC"
    ).fetchall()

    if not rows:
        click.echo("Nothing to review. All listings have been reviewed.")
        conn.close()
        return

    console.print(f"\n[bold green]Reviewing {len(rows)} pending listings[/bold green] — (a)ccept / (d)ismiss / (s)kip / (q)uit\n")

    reviewed = 0
    for i, row in enumerate(rows):
        short_id = row["id"][:8]
        score_val = f"{row['score']:.2f}" if row["score"] is not None else "—"

        # Build display
        header = f"[{score_val}] {row['title']} — {row['company']}"
        location_str = row["location"] or "location unknown"
        salary_str = row["salary"] or "salary undisclosed"
        subtitle = f"{location_str} | {salary_str}"

        desc = row["description"] or "(no description)"
        desc_preview = desc[:800] + "..." if len(desc) > 800 else desc

        body = Text()
        body.append(f"{subtitle}\n", style="dim")
        body.append(f"\n{desc_preview}\n", style="italic")
        if row["url"]:
            body.append(f"\n{row['url']}", style="blue underline")

        panel = Panel(
            body,
            title=f"[bold]{header}[/bold]",
            subtitle=f"[dim]({i+1}/{len(rows)}) ID: {short_id}[/dim]",
        )
        console.print(panel)

        # Get keypress
        console.print("[bold]Action:[/bold] ", end="")
        try:
            key = _get_keypress().lower()
        except Exception:
            # Fallback for non-TTY
            key = click.prompt("", prompt_suffix="").strip().lower()[:1]

        now = datetime.now(timezone.utc).isoformat()

        if key == "a":
            console.print("[green]✓ Accepted[/green]")
            conn.execute(
                "UPDATE listings SET status='accepted', updated_at=? WHERE id=?",
                (now, row["id"])
            )
            conn.execute(
                "INSERT INTO calibration (id, listing_id, action, created_at) VALUES (?,?,?,?)",
                (str(uuid.uuid4()), row["id"], "accept", now)
            )
            conn.commit()
            reviewed += 1

        elif key == "d":
            console.print("[red]✗ Dismissed[/red]")
            conn.execute(
                "UPDATE listings SET status='dismissed', updated_at=? WHERE id=?",
                (now, row["id"])
            )
            conn.execute(
                "INSERT INTO calibration (id, listing_id, action, created_at) VALUES (?,?,?,?)",
                (str(uuid.uuid4()), row["id"], "dismiss", now)
            )
            conn.commit()
            reviewed += 1

        elif key == "s":
            console.print("[yellow]→ Skipped[/yellow]")

        elif key == "q":
            console.print("[dim]Quit.[/dim]")
            break

        else:
            console.print(f"[dim]Unknown key '{key}' — skipping[/dim]")

        console.print()

    conn.close()
    console.print(f"\n[bold]Done.[/bold] Reviewed {reviewed} listings this session.")
