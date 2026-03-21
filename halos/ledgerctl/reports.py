"""Reporting engine for ledgerctl.

If hledger is installed, shells out for balance/income/cashflow reports.
Otherwise, pure Python fallback that parses the journal directly.

All reports support --period (daily, weekly, monthly, yearly) and --json output.
"""

import json
import shutil
import subprocess
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .journal import Entry, read_journal, journal_path


def _has_hledger() -> bool:
    """Check if hledger is installed and accessible."""
    return shutil.which("hledger") is not None


def _hledger_report(
    report_type: str,
    journal: Optional[Path] = None,
    period: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
) -> str:
    """Run an hledger report command and return stdout."""
    jpath = journal or journal_path()
    cmd = ["hledger", "-f", str(jpath), report_type]
    if period:
        cmd.extend(["--period", period])
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"hledger error: {result.stderr.strip()}")
    return result.stdout


def _period_start(period: Optional[str] = None) -> Optional[date]:
    """Convert a period name to a start date."""
    if not period:
        return None
    today = datetime.now(timezone.utc).date()
    if period == "daily":
        return today
    elif period == "weekly":
        return today - timedelta(days=today.weekday())  # Monday
    elif period == "monthly":
        return today.replace(day=1)
    elif period == "yearly":
        return today.replace(month=1, day=1)
    return None


def _filter_by_period(entries: list[Entry], period: Optional[str] = None) -> list[Entry]:
    """Filter entries to those within the given period."""
    start = _period_start(period)
    if start is None:
        return entries
    return [e for e in entries if e.date >= start]


def balance(
    journal: Optional[Path] = None,
    period: Optional[str] = None,
    as_json: bool = False,
) -> str | dict:
    """Balance report: sum of postings by account.

    Args:
        journal: Journal file path.
        period: Filter period (daily, weekly, monthly, yearly).
        as_json: Return dict instead of formatted string.

    Returns:
        Formatted balance string or dict of {account: amount}.
    """
    if _has_hledger() and not as_json:
        try:
            return _hledger_report("balance", journal, period)
        except (RuntimeError, subprocess.TimeoutExpired):
            pass  # Fall through to Python

    entries = read_journal(journal)
    entries = _filter_by_period(entries, period)

    balances: dict[str, float] = defaultdict(float)
    for entry in entries:
        for posting in entry.postings:
            if posting.amount is not None:
                balances[posting.account] += posting.amount

    if as_json:
        return dict(sorted(balances.items()))

    if not balances:
        return "No transactions found."

    lines = []
    for account in sorted(balances.keys()):
        amt = balances[account]
        lines.append(f"  ${amt:>12,.2f}  {account}")
    return "\n".join(lines)


def income(
    journal: Optional[Path] = None,
    period: Optional[str] = None,
    as_json: bool = False,
) -> str | dict:
    """Income report: sum of income:* accounts.

    Returns positive numbers for income received.
    """
    if _has_hledger() and not as_json:
        try:
            return _hledger_report("income", journal, period)
        except (RuntimeError, subprocess.TimeoutExpired):
            pass

    entries = read_journal(journal)
    entries = _filter_by_period(entries, period)

    totals: dict[str, float] = defaultdict(float)
    for entry in entries:
        for posting in entry.postings:
            if posting.amount is not None and posting.account.startswith("income:"):
                # Income postings are typically negative in double-entry;
                # we report as positive
                totals[posting.account] += abs(posting.amount)

    # Also infer income from balancing postings
    for entry in entries:
        has_income_explicit = any(
            p.account.startswith("income:") and p.amount is not None
            for p in entry.postings
        )
        if has_income_explicit:
            continue
        # Check if any posting without amount is income
        for posting in entry.postings:
            if posting.amount is None and posting.account.startswith("income:"):
                # Infer amount from other postings
                explicit_sum = sum(
                    p.amount for p in entry.postings if p.amount is not None
                )
                totals[posting.account] += abs(explicit_sum)

    if as_json:
        return dict(sorted(totals.items()))

    if not totals:
        return "No income found."

    lines = []
    total = 0.0
    for account in sorted(totals.keys()):
        amt = totals[account]
        total += amt
        lines.append(f"  ${amt:>12,.2f}  {account}")
    lines.append(f"  ${total:>12,.2f}  total")
    return "\n".join(lines)


def cashflow(
    journal: Optional[Path] = None,
    period: Optional[str] = None,
    as_json: bool = False,
) -> str | dict:
    """Cashflow report: income minus expenses for the period."""
    if _has_hledger() and not as_json:
        try:
            return _hledger_report("cashflow", journal, period)
        except (RuntimeError, subprocess.TimeoutExpired):
            pass

    entries = read_journal(journal)
    entries = _filter_by_period(entries, period)

    income_total = 0.0
    expense_total = 0.0

    for entry in entries:
        for posting in entry.postings:
            if posting.amount is None:
                continue
            if posting.account.startswith("income:"):
                income_total += abs(posting.amount)
            elif posting.account.startswith("expenses:"):
                expense_total += posting.amount

    # Infer amounts for balancing postings
    for entry in entries:
        for posting in entry.postings:
            if posting.amount is not None:
                continue
            explicit_sum = sum(
                p.amount for p in entry.postings if p.amount is not None
            )
            if posting.account.startswith("income:"):
                income_total += abs(explicit_sum)
            elif posting.account.startswith("expenses:"):
                expense_total += abs(explicit_sum)

    net = income_total - expense_total

    if as_json:
        return {
            "income": round(income_total, 2),
            "expenses": round(expense_total, 2),
            "net": round(net, 2),
        }

    lines = [
        f"  Income:   ${income_total:>12,.2f}",
        f"  Expenses: ${expense_total:>12,.2f}",
        f"  Net:      ${net:>12,.2f}",
    ]
    return "\n".join(lines)


def categories(
    journal: Optional[Path] = None,
    period: Optional[str] = None,
) -> dict[str, float]:
    """List expense categories with total spend.

    Returns dict of {category: total_amount} sorted by amount descending.
    """
    entries = read_journal(journal)
    entries = _filter_by_period(entries, period)

    cats: dict[str, float] = defaultdict(float)
    for entry in entries:
        for posting in entry.postings:
            if posting.amount is not None and posting.account.startswith("expenses:"):
                cats[posting.account] += posting.amount

    # Also infer from balancing postings
    for entry in entries:
        for posting in entry.postings:
            if posting.amount is None and posting.account.startswith("expenses:"):
                explicit_sum = sum(
                    p.amount for p in entry.postings if p.amount is not None
                )
                cats[posting.account] += abs(explicit_sum)

    return dict(sorted(cats.items(), key=lambda x: x[1], reverse=True))


def search(
    payee_pattern: str,
    journal: Optional[Path] = None,
) -> list[dict]:
    """Search journal entries by payee pattern.

    Returns list of dicts with date, payee, postings.
    """
    import re
    entries = read_journal(journal)
    results = []

    for entry in entries:
        if re.search(payee_pattern, entry.payee, re.IGNORECASE):
            postings = []
            for p in entry.postings:
                pd = {"account": p.account}
                if p.amount is not None:
                    pd["amount"] = p.amount
                    pd["currency"] = p.currency
                postings.append(pd)
            results.append({
                "date": entry.date.isoformat(),
                "payee": entry.payee,
                "postings": postings,
            })

    return results
