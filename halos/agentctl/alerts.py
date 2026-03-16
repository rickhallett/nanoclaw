"""Spinning-to-infinity detection and alert logic."""

from collections import defaultdict
from pathlib import Path

from .config import Config
from .session import Session, parse


def load_sessions(sessions_dir: str) -> list[Session]:
    """Load all session records from the sessions directory."""
    sessions: list[Session] = []
    d = Path(sessions_dir)
    if not d.exists():
        return sessions
    for f in sorted(d.iterdir()):
        if f.suffix != ".yaml":
            continue
        try:
            sessions.append(parse(f.read_text()))
        except (ValueError, KeyError):
            continue
    return sessions


def detect_long_sessions(sessions: list[Session], threshold_secs: int) -> list[Session]:
    """Find sessions exceeding the spin threshold with no meaningful result."""
    alerts = []
    for s in sessions:
        if s.duration_secs > threshold_secs and s.result_length == 0:
            alerts.append(s)
    return alerts


def detect_error_streaks(sessions: list[Session], streak_threshold: int) -> dict[str, list[Session]]:
    """Find groups with consecutive error sessions at the tail.

    Returns a dict of group -> list of consecutive error sessions (most recent).
    Only returns groups where the streak length >= streak_threshold.
    """
    # Group sessions by group, sorted by start time
    by_group: dict[str, list[Session]] = defaultdict(list)
    for s in sessions:
        by_group[s.group].append(s)

    # Sort each group by started timestamp
    for group in by_group:
        by_group[group].sort(key=lambda s: s.started)

    result: dict[str, list[Session]] = {}
    for group, group_sessions in by_group.items():
        # Count consecutive errors from the end
        streak: list[Session] = []
        for s in reversed(group_sessions):
            if s.status == "error":
                streak.append(s)
            else:
                break

        if len(streak) >= streak_threshold:
            result[group] = list(reversed(streak))

    return result


def check_alerts(cfg: Config) -> list[str]:
    """Run all alert checks and return warning messages."""
    sessions = load_sessions(cfg.sessions_dir)
    if not sessions:
        return []

    warnings: list[str] = []

    # Long sessions (spinning to infinity)
    long = detect_long_sessions(sessions, cfg.spin_threshold_secs)
    for s in long:
        warnings.append(
            f"SPIN: {s.id} ran for {s.duration_secs}s (>{cfg.spin_threshold_secs}s) "
            f"with no result [group={s.group}, status={s.status}]"
        )

    # Error streaks
    streaks = detect_error_streaks(sessions, cfg.error_streak_threshold)
    for group, streak in streaks.items():
        warnings.append(
            f"STREAK: {group} has {len(streak)} consecutive errors "
            f"(threshold={cfg.error_streak_threshold})"
        )

    return warnings
