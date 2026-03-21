"""Streak and statistics engine for trackctl.

Streak logic:
- A "day done" is any calendar day (UTC) with >= 1 entry.
- Consecutive days form a streak.
- Missing a calendar day resets the current streak to 0.
- The engine tracks both current streak and longest streak.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from . import store


def _dates_with_entries(domain: str) -> set[date]:
    """Return the set of calendar dates (UTC) that have at least one entry."""
    totals = store.daily_totals(domain)
    dates: set[date] = set()
    for date_str in totals:
        try:
            dates.add(date.fromisoformat(date_str))
        except ValueError:
            continue
    return dates


def compute_streak(domain: str) -> dict:
    """Compute current and longest streak for a domain.

    Returns:
        Dict with keys: current_streak, longest_streak, last_entry_date.
    """
    dates = _dates_with_entries(domain)
    if not dates:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "last_entry_date": None,
        }

    sorted_dates = sorted(dates)
    today = datetime.now(timezone.utc).date()

    # Compute longest streak
    longest = 1
    current_run = 1
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1

    # Compute current streak (must include today or yesterday)
    last_date = sorted_dates[-1]
    if last_date < today - timedelta(days=1):
        # More than one day gap — streak is broken
        current_streak = 0
    else:
        # Walk backward from last_date
        current_streak = 1
        check = last_date - timedelta(days=1)
        while check in dates:
            current_streak += 1
            check -= timedelta(days=1)

    return {
        "current_streak": current_streak,
        "longest_streak": longest,
        "last_entry_date": last_date.isoformat(),
    }


def compute_summary(domain: str, target: Optional[int] = None) -> dict:
    """Full summary stats for a domain.

    Args:
        domain: Domain name.
        target: Optional streak target (e.g. 100 days).

    Returns:
        Dict with streak info, today's total, all-time total, entry count.
    """
    streak = compute_streak(domain)
    totals = store.daily_totals(domain)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    today_mins = totals.get(today_str, 0)
    alltime_mins = sum(totals.values())
    total_days = len(totals)
    total_entries = len(store.list_entries(domain))

    result = {
        "domain": domain,
        "current_streak": streak["current_streak"],
        "longest_streak": streak["longest_streak"],
        "last_entry_date": streak["last_entry_date"],
        "today_mins": today_mins,
        "alltime_mins": alltime_mins,
        "total_days": total_days,
        "total_entries": total_entries,
    }

    if target is not None:
        result["target"] = target
        result["target_remaining"] = max(0, target - streak["current_streak"])

    return result


def text_summary(domain: str, target: Optional[int] = None) -> str:
    """One-line text summary suitable for briefing integration.

    Example: "zazen: 5-day streak (longest: 12) | today: 25min | all-time: 1,240min (48 days)"
    """
    s = compute_summary(domain, target=target)

    parts = [
        f"{domain}: {s['current_streak']}-day streak (longest: {s['longest_streak']})",
    ]

    if target is not None and target > 0:
        remaining = s.get("target_remaining", 0)
        if remaining > 0:
            parts[0] += f" [target: {target}, {remaining} to go]"
        else:
            parts[0] += f" [target: {target} reached]"

    parts.append(f"today: {s['today_mins']}min")
    parts.append(f"all-time: {s['alltime_mins']:,}min ({s['total_days']} days)")

    return " | ".join(parts)
