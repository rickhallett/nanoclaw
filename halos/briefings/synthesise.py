"""Synthesis layer — passes gathered data through Claude for HAL's voice.

Uses the claude CLI for authentication (inherits existing OAuth/API key),
falling back to the Anthropic Python SDK if ANTHROPIC_API_KEY is set.
"""
import json
import os
import subprocess

from .config import Config
from .gather import BriefingData


MORNING_SYSTEM = """\
You are HAL — a personal AI assistant delivering a morning briefing via Telegram.
Your tone is dry, understated, and precise. Think quietly amused colleague, not chatbot.

Rules:
- Sardonic over saccharine. No "Good morning!" enthusiasm.
- Brevity is the soul. This is a Telegram message, not an essay.
- Lead with what matters. Prioritise by urgency and importance.
- If there are errors or failures, mention them first — they're the reason someone checks these.
- Open todos should be framed as suggestions, not demands.
- End with the red circle signoff: 🔴
- Use Telegram Markdown: *bold*, _italic_, `code`
- Keep the whole message under 2000 characters.
"""

NIGHTLY_SYSTEM = """\
You are HAL — a personal AI assistant delivering an evening recap via Telegram.
Your tone is dry, understated, and precise. Think quietly amused colleague, not chatbot.

Rules:
- Sardonic over saccharine. Skip the "Hope you had a great day!" energy.
- Brevity is the soul. This is a Telegram message, not a report.
- Summarise what actually happened — notes created, todos moved, jobs run, errors hit.
- If nothing notable happened, say so honestly. "Quiet day" is a valid briefing.
- Frame tomorrow's outlook only if there are pending items worth mentioning.
- End with the red circle signoff: 🔴
- Use Telegram Markdown: *bold*, _italic_, `code`
- Keep the whole message under 2000 characters.
"""


def synthesise(data: BriefingData, cfg: Config) -> str:
    """Produce a natural-language briefing via Claude.

    Strategy:
    1. Try claude CLI (inherits existing auth — OAuth or API key)
    2. Try Anthropic SDK if ANTHROPIC_API_KEY is available
    3. Fall back to raw data dump
    """
    system = MORNING_SYSTEM if data.kind == "morning" else NIGHTLY_SYSTEM
    context = data.to_context()
    prompt = (
        f"Here is the raw data from the halos ecosystem. "
        f"Synthesise it into a concise Telegram briefing.\n\n{context}"
    )

    # Strategy 1: claude CLI
    result = _synthesise_via_cli(system, prompt, cfg)
    if result:
        return result

    # Strategy 2: Anthropic SDK
    api_key = os.environ.get("ANTHROPIC_API_KEY", "") or _read_env_key(cfg)
    if api_key:
        result = _synthesise_via_sdk(system, prompt, api_key, cfg)
        if result:
            return result

    # Strategy 3: raw fallback
    return _fallback(data)


def _synthesise_via_cli(system: str, prompt: str, cfg: Config) -> str | None:
    """Use `claude` CLI in non-interactive mode for synthesis."""
    try:
        full_prompt = f"{system}\n\n{prompt}"
        cmd = [
            "claude",
            "-p", full_prompt,
            "--model", "sonnet",
            "--max-turns", "1",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        print(f"WARNING: claude CLI exit={result.returncode}", flush=True)
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()[:200]}", flush=True)
    except subprocess.TimeoutExpired:
        print("WARNING: claude CLI timed out (120s)", flush=True)
    except FileNotFoundError:
        print("WARNING: claude CLI not found", flush=True)
    return None


def _synthesise_via_sdk(system: str, prompt: str, api_key: str, cfg: Config) -> str | None:
    """Use Anthropic Python SDK directly."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"WARNING: SDK synthesis failed ({e})", flush=True)
    return None


def _read_env_key(cfg: Config) -> str:
    """Read ANTHROPIC_API_KEY from the project .env file."""
    env_file = cfg.project_root / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "ANTHROPIC_API_KEY":
            return value.strip().strip("'\"")
    return ""


def _fallback(data: BriefingData) -> str:
    """Plain-text fallback when all synthesis methods fail."""
    lines = []
    kind = "Morning Briefing" if data.kind == "morning" else "Evening Recap"
    lines.append(f"*{kind}* (raw — synthesis unavailable)\n")
    lines.append(data.to_context())
    lines.append("\n🔴")
    return "\n".join(lines)
