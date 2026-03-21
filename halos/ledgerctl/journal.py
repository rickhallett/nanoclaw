"""Journal reader/writer for hledger-format plain-text accounting.

Journal file lives at store/ledger.journal. Format:

    2026-03-21 Countdown
        expenses:food                       $42.50
        assets:bank:anz:checking

Each entry: date, payee/description, list of postings (account, amount, currency).
The last posting in a group can omit the amount (hledger infers the balancing amount).

All writes use atomic temp-file-then-rename to avoid corruption.
"""

import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional


@dataclass
class Posting:
    """A single posting (line) within a journal entry."""
    account: str
    amount: Optional[float] = None
    currency: str = "$"

    def format(self) -> str:
        if self.amount is not None:
            # Right-align amount at column 48 for readability
            amt_str = f"{self.currency}{abs(self.amount):,.2f}"
            if self.amount < 0:
                amt_str = f"-{amt_str}"
            # Pad account to at least 40 chars for alignment
            return f"    {self.account:<40}{amt_str}"
        return f"    {self.account}"


@dataclass
class Entry:
    """A complete journal entry (transaction)."""
    date: date
    payee: str
    postings: list[Posting] = field(default_factory=list)
    comment: str = ""

    def format(self) -> str:
        lines = []
        header = f"{self.date.isoformat()} {self.payee}"
        if self.comment:
            header += f"  ; {self.comment}"
        lines.append(header)
        for p in self.postings:
            lines.append(p.format())
        return "\n".join(lines)


def _store_dir() -> Path:
    """Resolve the store/ directory relative to the repo root."""
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "store").is_dir():
            return ancestor / "store"
    return Path.cwd() / "store"


def journal_path(store_dir: Optional[Path] = None) -> Path:
    """Return the path to the journal file."""
    d = store_dir or _store_dir()
    return d / "ledger.journal"


def read_journal(path: Optional[Path] = None) -> list[Entry]:
    """Parse an hledger journal file into a list of Entry objects.

    Args:
        path: Journal file path. Defaults to store/ledger.journal.

    Returns:
        List of Entry objects in file order.
    """
    jpath = path or journal_path()
    if not jpath.exists():
        return []

    text = jpath.read_text(encoding="utf-8")
    return parse_journal(text)


def parse_journal(text: str) -> list[Entry]:
    """Parse journal text into Entry objects."""
    entries: list[Entry] = []
    current_entry: Optional[Entry] = None

    for line in text.splitlines():
        # Skip empty lines and pure comment lines
        if not line.strip() or line.strip().startswith(";"):
            if current_entry is not None:
                entries.append(current_entry)
                current_entry = None
            continue

        # Posting line (starts with whitespace)
        if line[0] in (" ", "\t"):
            if current_entry is None:
                continue
            posting = _parse_posting(line)
            if posting:
                current_entry.postings.append(posting)
            continue

        # Transaction header line: DATE PAYEE [; COMMENT]
        match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(.+)", line)
        if match:
            if current_entry is not None:
                entries.append(current_entry)

            date_str = match.group(1)
            rest = match.group(2)

            comment = ""
            if "  ; " in rest:
                payee_part, comment = rest.split("  ; ", 1)
            elif rest.endswith(";"):
                payee_part = rest[:-1].strip()
            else:
                payee_part = rest

            current_entry = Entry(
                date=date.fromisoformat(date_str),
                payee=payee_part.strip(),
                comment=comment.strip(),
            )

    # Don't forget the last entry
    if current_entry is not None:
        entries.append(current_entry)

    return entries


def _parse_posting(line: str) -> Optional[Posting]:
    """Parse a posting line like '    expenses:food    $42.50'."""
    stripped = line.strip()
    if not stripped:
        return None

    # Try to match account + amount pattern
    # Amount can be: $1,234.56 or -$1,234.56 or NZD 42.50 etc.
    match = re.match(
        r"([\w:]+(?:\s[\w:]+)*)\s{2,}(-?)([A-Z]{2,3}|\$|€|£)?([\d,]+\.\d{2})",
        stripped,
    )
    if match:
        account = match.group(1)
        sign = match.group(2)
        currency = match.group(3) or "$"
        amount = float(match.group(4).replace(",", ""))
        if sign == "-":
            amount = -amount
        return Posting(account=account, amount=amount, currency=currency)

    # Account only (balancing posting, no amount)
    if re.match(r"^[\w:]+$", stripped):
        return Posting(account=stripped)

    # Account with spaces but no amount
    account_match = re.match(r"^([\w:]+(?:\s[\w:]+)*)$", stripped)
    if account_match:
        return Posting(account=account_match.group(1))

    return None


def append_entries(
    entries: list[Entry],
    path: Optional[Path] = None,
    store_dir: Optional[Path] = None,
) -> None:
    """Append entries to the journal file atomically.

    Args:
        entries: List of Entry objects to append.
        path: Journal file path. Defaults to store/ledger.journal.
        store_dir: Store directory (used if path is None).
    """
    if not entries:
        return

    jpath = path or journal_path(store_dir)
    jpath.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content
    existing = ""
    if jpath.exists():
        existing = jpath.read_text(encoding="utf-8")

    # Build new content
    new_parts = []
    for entry in entries:
        new_parts.append(entry.format())

    new_block = "\n\n".join(new_parts)

    if existing:
        # Ensure separation from existing content
        if not existing.endswith("\n\n"):
            if existing.endswith("\n"):
                existing += "\n"
            else:
                existing += "\n\n"
        content = existing + new_block + "\n"
    else:
        content = new_block + "\n"

    # Atomic write: temp file then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(jpath.parent), prefix=".ledger_", suffix=".tmp"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.rename(tmp_path, str(jpath))
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def entry_exists(
    entries: list[Entry], check_date: date, amount: float, payee: str
) -> bool:
    """Check if a matching entry already exists (for duplicate detection).

    Matches on (date, amount, payee) — the same triple used by importers.
    """
    for e in entries:
        if e.date != check_date:
            continue
        if e.payee.strip().lower() != payee.strip().lower():
            continue
        # Check if any posting has the matching amount
        for p in e.postings:
            if p.amount is not None and abs(p.amount - amount) < 0.005:
                return True
    return False
