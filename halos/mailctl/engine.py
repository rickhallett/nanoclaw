"""engine — himalaya subprocess wrapper for mailctl.

Provides structured access to Gmail via the himalaya CLI.
All methods return parsed Python objects (dicts/lists), never raw strings.

Requires: himalaya binary on PATH, configured account in ~/.config/himalaya/config.toml
"""

import json
import subprocess
from dataclasses import dataclass
from typing import Optional


ACCOUNT = "gmail"
HIMALAYA = "himalaya"


class HimalayaError(Exception):
    """Raised when himalaya exits non-zero."""

    def __init__(self, message: str, returncode: int, stderr: str):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def _run(args: list[str], stdin: Optional[str] = None) -> str:
    """Run himalaya with args, return stdout."""
    cmd = [HIMALAYA, *args, "-o", "json"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=stdin,
        timeout=30,
    )
    if result.returncode != 0:
        raise HimalayaError(
            f"himalaya {' '.join(args)} failed: {result.stderr.strip()}",
            result.returncode,
            result.stderr,
        )
    return result.stdout


def _parse(raw: str) -> list[dict] | dict:
    """Parse JSON output from himalaya."""
    if not raw.strip():
        return []
    return json.loads(raw)


def list_messages(
    folder: str = "INBOX",
    page: int = 1,
    page_size: int = 25,
) -> list[dict]:
    """List messages in a folder."""
    raw = _run([
        "envelope", "list",
        "--folder", folder,
        "-p", str(page),
        "-s", str(page_size),
    ])
    return _parse(raw)


def read_message(message_id: str, folder: str = "INBOX") -> dict:
    """Read a single message by ID."""
    raw = _run(["message", "read", "--folder", folder, message_id])
    return _parse(raw)


def search(query: str, folder: str = "INBOX") -> list[dict]:
    """Search messages. Query uses IMAP search syntax."""
    raw = _run(["envelope", "list", "--folder", folder, *query.split()])
    return _parse(raw)


def send(to: str, subject: str, body: str, cc: Optional[str] = None) -> None:
    """Compose and send a message."""
    # himalaya expects an RFC 2822-ish message on stdin
    headers = f"To: {to}\nSubject: {subject}\n"
    if cc:
        headers += f"Cc: {cc}\n"
    headers += f"\n{body}"
    _run(["message", "send"], stdin=headers)


def move(message_id: str, dest: str, folder: str = "INBOX") -> None:
    """Move a message to another folder."""
    _run(["message", "move", "--folder", folder, message_id, dest])


def flag(message_id: str, flag: str = "seen", folder: str = "INBOX") -> None:
    """Add a flag to a message."""
    _run(["flag", "add", "--folder", folder, message_id, flag])


def folders() -> list[dict]:
    """List all folders/labels."""
    raw = _run(["folder", "list"])
    return _parse(raw)
