"""Template composition for microHAL CLAUDE.md files."""

from pathlib import Path


def _templates_dir() -> Path:
    """Return the templates/microhal directory."""
    return Path(__file__).resolve().parents[2] / "templates" / "microhal"


def _read_template(path: Path) -> str:
    """Read a template file, returning empty string if missing."""
    if path.exists():
        return path.read_text()
    return ""


def compose_claude_md(personality: str, user_name: str) -> str:
    """Compose CLAUDE.md from base + personality + user layers.

    Tries YAML profile-based rendering first (profiles/{user_name}.yaml +
    block library). Falls back to legacy .md personality files if no YAML
    profile exists. Zero migration pressure.

    Layers:
      1. templates/microhal/base.md — shared instructions
      2. Personality (YAML profile OR legacy .md file)
      3. templates/microhal/user/<user_name>.md — user-specific context

    Missing layers are silently skipped.
    """
    tdir = _templates_dir()
    base = _read_template(tdir / "base.md")

    # Try YAML profile first
    profile_path = tdir / "profiles" / f"{user_name}.yaml"
    schema_path = tdir / "personality-schema.yaml"

    if profile_path.exists() and schema_path.exists():
        from .renderer import render_personality
        pers = render_personality(
            profile_name=user_name,
            schema_path=schema_path,
            profiles_dir=tdir / "profiles",
            blocks_dir=tdir / "blocks",
        )
    else:
        # Legacy fallback: personality .md file
        pers = _read_template(tdir / "personality" / f"{personality}.md")

    user = _read_template(tdir / "user" / f"{user_name}.md")

    sections = [s for s in [base, pers, user] if s.strip()]
    return "\n\n".join(sections) + "\n"
