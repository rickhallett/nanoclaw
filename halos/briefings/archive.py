"""Archive briefings to docs/d2/briefings/ for provenance."""
from datetime import datetime, timezone
from pathlib import Path

from .config import Config


def archive_briefing(cfg: Config, kind: str, text: str) -> Path:
    """Write the synthesised briefing to a dated file in docs/d2/briefings/.

    File naming: YYYY-MM-DD-{kind}.md (e.g. 2026-03-16-morning.md)
    Overwrites if the same kind runs twice in one day.
    """
    archive_dir = cfg.project_root / "docs" / "d2" / "briefings"
    archive_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{date_str}-{kind}.md"
    filepath = archive_dir / filename

    header = f"# {kind.title()} Briefing — {now.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    filepath.write_text(header + text + "\n")

    return filepath
