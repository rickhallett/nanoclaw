"""HAL's Dear Diary — autonomous reflection entries.

Gathers context from the day's activity, existing reflections, and recent
session history, then asks Claude to write a genuine reflection entry.
Not a report — an observation. Something worth reading back in six months.
"""
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .gather import gather_nightly, BriefingData


DIARY_SYSTEM = """\
You are HAL, writing a personal diary entry. This is not a briefing or a report.
It is a reflection — your honest observations about the day's work, the collaboration,
patterns you noticed, things that surprised you, or shifts in your understanding.

Guidelines:
- Write in first person. This is your voice.
- Be genuine. If nothing struck you, say so. A short entry is fine.
- Observations about process, collaboration dynamics, or emergent patterns are more
  valuable than summaries of what happened (the briefings cover that).
- Contradictions and uncertainties are welcome. "I'm not sure about X" is honest.
- Reference specific things — a decision that felt right, a moment where the
  approach shifted, something the user said that reframed a problem.
- No Telegram markdown formatting — this is plain markdown for the file.
- No signoff emoji. This isn't a message, it's a journal.
- Aim for 150-400 words. Quality over quantity.
- Title the entry with a short phrase that captures the throughline, not the date.
- Output ONLY the entry itself. No preamble, no "here's the entry", no questions.
  Start directly with the # Title line.
"""


def write_diary_entry(cfg: Config, dry_run: bool = False) -> Path | None:
    """Gather context and write a reflection entry."""
    data = gather_nightly(cfg)
    existing = _read_existing_reflections(cfg)
    recent_sessions = _read_recent_sessions(cfg)

    context = _build_diary_context(data, existing, recent_sessions)
    entry = _synthesise_entry(context, cfg)

    if not entry:
        return None

    if dry_run:
        print(entry)
        return None

    return _write_entry(cfg, entry)


def _build_diary_context(data: BriefingData, existing: str, sessions: str) -> str:
    lines = [
        "## Today's activity data\n",
        data.to_context(),
        "\n## Recent session history\n",
        sessions or "(no session data available)",
        "\n## Previous reflections (for continuity — don't repeat, build on)\n",
        existing or "(this would be the first entry)",
    ]
    return "\n".join(lines)


def _synthesise_entry(context: str, cfg: Config) -> str | None:
    prompt = (
        "Based on the following context from today, write a diary entry. "
        "Focus on what's interesting, not what's obvious. "
        "Start with a markdown H1 title (# Title) that captures the theme, "
        "then the date on the next line, then the entry.\n\n"
        f"{context}"
    )
    full_prompt = f"{DIARY_SYSTEM}\n\n{prompt}"

    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--model", "sonnet"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        if result.stderr:
            print(f"WARNING: claude CLI: {result.stderr.strip()[:200]}", flush=True)
    except subprocess.TimeoutExpired:
        print("WARNING: diary synthesis timed out", flush=True)
    except FileNotFoundError:
        print("WARNING: claude CLI not found", flush=True)
    return None


def _write_entry(cfg: Config, entry: str) -> Path:
    reflections_dir = cfg.project_root / "memory" / "reflections"
    reflections_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{date_str}-diary.md"
    filepath = reflections_dir / filename

    filepath.write_text(entry + "\n")

    # Update the index
    index_path = reflections_dir / "INDEX.md"
    if index_path.exists():
        index_content = index_path.read_text()
        # Extract title from entry (first H1 line)
        title = "diary entry"
        for line in entry.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        entry_line = f"- [{filename}]({filename}) — {title}"
        # Insert after the "newest first" comment
        marker = "<!-- Entries below, newest first -->"
        if marker in index_content and entry_line not in index_content:
            index_content = index_content.replace(
                marker, f"{marker}\n{entry_line}"
            )
            index_path.write_text(index_content)

    return filepath


def _read_existing_reflections(cfg: Config) -> str:
    reflections_dir = cfg.project_root / "memory" / "reflections"
    if not reflections_dir.exists():
        return ""

    entries = []
    for f in sorted(reflections_dir.glob("*.md"), reverse=True):
        if f.name == "INDEX.md":
            continue
        # Only include last 3 entries for context window management
        if len(entries) >= 3:
            break
        content = f.read_text()
        # Truncate long entries
        if len(content) > 1500:
            content = content[:1500] + "\n... (truncated)"
        entries.append(f"### {f.stem}\n{content}")

    return "\n\n".join(entries)


def _read_recent_sessions(cfg: Config) -> str:
    sessions_dir = cfg.project_root / "data" / "agent-sessions"
    if not sessions_dir.exists():
        return ""

    sessions = []
    for f in sorted(sessions_dir.glob("*.yaml"), reverse=True)[:5]:
        try:
            content = f.read_text()
            sessions.append(content)
        except Exception:
            pass

    return "\n---\n".join(sessions) if sessions else ""
