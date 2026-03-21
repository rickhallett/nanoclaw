"""Briefing integration for ledgerctl.

Provides text_summary() for inclusion in morning/nightly briefings.
Format: "ledgerctl: spent $1,240 this week (food $380, transport $210) | income: $5,000 | savings rate: 62%"
"""

from pathlib import Path
from typing import Optional

from .reports import cashflow, categories


def text_summary(
    journal: Optional[Path] = None,
    period: str = "weekly",
) -> str:
    """One-line text summary for briefing integration.

    Args:
        journal: Journal file path. Defaults to store/ledger.journal.
        period: Reporting period. Default: weekly.

    Returns:
        Formatted one-liner, or empty string if no data.
    """
    try:
        cf = cashflow(journal=journal, period=period, as_json=True)
        cats = categories(journal=journal, period=period)
    except Exception:
        return ""

    income_total = cf.get("income", 0)
    expense_total = cf.get("expenses", 0)

    if income_total == 0 and expense_total == 0:
        return ""

    # Top expense categories (up to 3)
    cat_parts = []
    for account, amount in list(cats.items())[:3]:
        # Shorten account name: expenses:food -> food
        short = account.split(":")[-1] if ":" in account else account
        cat_parts.append(f"{short} ${amount:,.0f}")

    parts = []
    if expense_total > 0:
        spent_str = f"spent ${expense_total:,.0f} this {'week' if period == 'weekly' else period}"
        if cat_parts:
            spent_str += f" ({', '.join(cat_parts)})"
        parts.append(spent_str)

    if income_total > 0:
        parts.append(f"income: ${income_total:,.0f}")

    if income_total > 0:
        savings_rate = ((income_total - expense_total) / income_total) * 100
        parts.append(f"savings rate: {savings_rate:.0f}%")

    if not parts:
        return ""

    return "ledgerctl: " + " | ".join(parts)
