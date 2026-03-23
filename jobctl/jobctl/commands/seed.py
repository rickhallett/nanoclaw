"""jobctl seed — import vacancies from markdown file."""

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import click

from jobctl.db import get_conn, init_db
from jobctl.scorer import score

VACANCIES_PATH = Path.home() / "code/nanoclaw/docs/job-applications/vacancies-march-2026.md"


def parse_vacancies(text: str) -> list[dict]:
    """Parse vacancies-march-2026.md into structured dicts."""
    vacancies = []
    current_tier = ""

    # Split into numbered items
    # Pattern: number + bold company/title line
    entries = re.split(r'\n(?=\d+\.\s+\*\*)', text)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        # Check tier lines before this entry
        tier_match = re.search(r'## (TIER \d+[^#\n]*)', entry)
        if tier_match:
            current_tier = tier_match.group(1).strip()

        # Match numbered listing
        m = re.match(r'\d+\.\s+\*\*([^—*]+?)(?:\s*—\s*([^*]+?))?\*\*', entry)
        if not m:
            continue

        company_raw = m.group(1).strip()
        title_raw = m.group(2).strip() if m.group(2) else ""

        # Split "Company — Title" if title not already extracted
        if not title_raw and "—" in company_raw:
            parts = company_raw.split("—", 1)
            company_raw = parts[0].strip()
            title_raw = parts[1].strip()

        # Extract location/salary line (usually second line)
        lines = entry.split("\n")
        location = None
        salary = None
        url = None
        description_lines = []

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            # URL
            url_match = re.search(r'https?://\S+', line)
            if url_match and not url:
                url = url_match.group(0).rstrip(')')
            # Location + salary line (has | separator or $ or £)
            if re.search(r'[\$£]|\b(remote|hybrid|onsite|on.site)\b', line, re.I) and not location:
                # Parse location and salary
                if '|' in line:
                    loc_part, sal_part = line.split('|', 1)
                    location = loc_part.strip()
                    salary = sal_part.strip()
                elif re.search(r'[\$£]', line):
                    # Try to split at the currency symbol
                    parts = re.split(r'\s+(?=[\$£])', line, maxsplit=1)
                    if len(parts) == 2:
                        location = parts[0].strip()
                        salary = parts[1].strip()
                    else:
                        location = line
                else:
                    location = line
            # Fit/description line
            elif line.startswith("Fit:") or line.startswith("Stack:") or line.startswith("Posted:"):
                description_lines.append(line)

        description = " ".join(description_lines) if description_lines else None

        vacancies.append({
            "company": company_raw,
            "title": title_raw or "Software Engineer",
            "url": url,
            "location": location,
            "salary": salary,
            "description": description,
            "tier": current_tier,
        })

    return vacancies


@click.command("seed")
@click.option("--file", "filepath", default=None, help="Path to vacancies markdown file")
@click.option("--force", is_flag=True, default=False, help="Re-seed even if already seeded")
def seed_cmd(filepath, force):
    """Import vacancies from markdown into the listings table."""
    init_db()
    conn = get_conn()

    path = Path(filepath) if filepath else VACANCIES_PATH
    if not path.exists():
        click.echo(f"Error: vacancies file not found at {path}", err=True)
        return

    text = path.read_text()
    vacancies = parse_vacancies(text)

    if not vacancies:
        click.echo("No vacancies found in file.", err=True)
        return

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    skipped = 0

    for v in vacancies:
        # Dedup by company + title
        existing = conn.execute(
            "SELECT id FROM listings WHERE company = ? AND title = ?",
            (v["company"], v["title"])
        ).fetchone()

        if existing and not force:
            skipped += 1
            continue

        if existing and force:
            conn.execute("DELETE FROM listings WHERE id = ?", (existing["id"],))

        listing_id = str(uuid.uuid4())
        job_score = score(v["title"], v["description"])

        # Add tier info to notes
        notes = v.get("tier", "")

        conn.execute(
            """INSERT INTO listings
               (id, company, title, url, description, location, salary, source, status, score, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,'seed','pending_review',?,?,?,?)""",
            (
                listing_id,
                v["company"],
                v["title"],
                v["url"],
                v["description"],
                v["location"],
                v["salary"],
                job_score,
                notes,
                now,
                now,
            )
        )
        inserted += 1

    conn.commit()
    conn.close()

    click.echo(f"Seeded {inserted} vacancies ({skipped} skipped — already exist). Use --force to re-seed.")
