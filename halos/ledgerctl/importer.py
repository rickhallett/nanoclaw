"""Bank CSV import engine for ledgerctl.

Generic CSV import that delegates to bank-specific modules for column mapping.
Import flow: parse CSV -> apply categorisation rules -> generate journal entries -> append.
Duplicate detection: skip entries where (date, amount, payee) already exist.
"""

import csv
from datetime import datetime, date
from io import StringIO
from pathlib import Path
from typing import Optional

from halos.common.log import hlog

from . import banks
from .journal import Entry, Posting, read_journal, append_entries, entry_exists
from .rules import categorise, load_rules


def import_csv(
    csv_path: str | Path,
    bank_name: str,
    dry_run: bool = False,
    journal_path: Optional[Path] = None,
    rules_path: Optional[Path] = None,
    currency: str = "$",
) -> list[Entry]:
    """Import a bank CSV file into the journal.

    Args:
        csv_path: Path to the CSV file.
        bank_name: Bank module name (e.g. 'anz', 'wise').
        dry_run: If True, generate entries but don't write to journal.
        journal_path: Override journal file path.
        rules_path: Override rules file path.
        currency: Currency symbol. Default: '$'.

    Returns:
        List of Entry objects that were (or would be) appended.

    Raises:
        ValueError: If bank module not found or CSV is invalid.
    """
    bank = banks.get(bank_name)
    if bank is None:
        available = ", ".join(banks.all_banks())
        raise ValueError(
            f"Unknown bank '{bank_name}'. Available: {available}"
        )

    columns = bank.COLUMNS
    date_format = bank.DATE_FORMAT
    default_account = bank.DEFAULT_ACCOUNT

    # Read CSV
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise ValueError(f"CSV file not found: {csv_path}")

    text = csv_file.read_text(encoding="utf-8-sig")  # Handle BOM
    rows = list(csv.DictReader(StringIO(text)))

    if not rows:
        return []

    # Load existing journal for duplicate detection
    existing = read_journal(journal_path)

    # Load rules
    rules = load_rules(rules_path)

    entries: list[Entry] = []
    skipped = 0

    for row in rows:
        # Extract fields using bank column mapping
        date_str = row.get(columns.get("date", ""), "").strip()
        amount_str = row.get(columns.get("amount", ""), "").strip()
        payee_raw = row.get(columns.get("payee", ""), "").strip()

        if not date_str or not amount_str:
            continue

        # Parse date
        try:
            entry_date = datetime.strptime(date_str, date_format).date()
        except ValueError:
            hlog("ledgerctl", "warn", "date_parse_error", {
                "date_str": date_str, "format": date_format,
            })
            continue

        # Parse amount (strip currency symbols, handle commas)
        amount_clean = amount_str.replace(",", "").replace("$", "").replace("€", "").replace("£", "")
        try:
            amount = float(amount_clean)
        except ValueError:
            hlog("ledgerctl", "warn", "amount_parse_error", {
                "amount_str": amount_str,
            })
            continue

        # Build payee — combine available description fields
        payee = payee_raw
        if not payee:
            payee = "Unknown"

        # Duplicate detection
        if entry_exists(existing, entry_date, abs(amount), payee):
            skipped += 1
            continue

        # Categorise
        target_account = categorise(payee, rules)

        # Build entry
        if amount > 0:
            # Money in (income or transfer)
            entry = Entry(
                date=entry_date,
                payee=payee,
                postings=[
                    Posting(account=default_account, amount=amount, currency=currency),
                    Posting(account=target_account),
                ],
            )
        else:
            # Money out (expense)
            entry = Entry(
                date=entry_date,
                payee=payee,
                postings=[
                    Posting(account=target_account, amount=abs(amount), currency=currency),
                    Posting(account=default_account),
                ],
            )

        entries.append(entry)

    if not dry_run and entries:
        append_entries(entries, path=journal_path)

    hlog("ledgerctl", "info", "import_complete", {
        "bank": bank_name,
        "csv": str(csv_path),
        "imported": len(entries),
        "skipped_duplicates": skipped,
        "dry_run": dry_run,
    })

    return entries
