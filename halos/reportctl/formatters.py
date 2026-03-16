"""Format collected data as human-readable text or JSON."""
import json
from datetime import datetime, timezone


def format_briefing(memctl: dict, todoctl: dict, nightctl: dict,
                    *, json_out: bool = False) -> str:
    """Morning briefing: corpus stats, open todos, pending jobs, recent errors."""
    data = {
        "report": "briefing",
        "generated": _now_iso(),
        "memory": memctl,
        "backlog": todoctl,
        "queue": nightctl,
    }

    if json_out:
        return json.dumps(data, indent=2, default=str)

    lines = []
    lines.append("=" * 60)
    lines.append("  MORNING BRIEFING")
    lines.append("=" * 60)

    # Memory
    lines.append("")
    lines.append("  MEMORY")
    if memctl["available"]:
        lines.append(f"    Notes:      {memctl['note_count']}")
        lines.append(f"    Entities:   {memctl['entities']}")
        lines.append(f"    Tags:       {memctl['tags']}")
        if memctl["types"]:
            lines.append("    By type:")
            for t, c in sorted(memctl["types"].items()):
                lines.append(f"      {t:<14} {c}")
        if memctl["drift"]:
            lines.append(f"    WARNING: {memctl['drift']} notes with index drift")
        if memctl["orphans"]:
            lines.append(f"    WARNING: {memctl['orphans']} orphaned notes")
    else:
        lines.append("    (not configured)")

    # Backlog
    lines.append("")
    lines.append("  BACKLOG")
    if todoctl["available"]:
        lines.append(f"    Items:      {todoctl['total']}")
        if todoctl["by_status"]:
            for s, c in sorted(todoctl["by_status"].items()):
                lines.append(f"      {s:<14} {c}")
    else:
        lines.append("    (not configured)")

    # Queue
    lines.append("")
    lines.append("  QUEUE")
    if nightctl["available"]:
        lines.append(f"    Jobs:       {nightctl['total_jobs']}")
        lines.append(f"    Pending:    {nightctl['pending']}")
        if nightctl["recent_failures"]:
            lines.append(f"    Failures:   {nightctl['recent_failures']}")
        if nightctl["oldest_pending_age_hours"] is not None:
            lines.append(f"    Oldest pending: {nightctl['oldest_pending_age_hours']:.1f}h ago")
        if nightctl["by_status"]:
            for s, c in sorted(nightctl["by_status"].items()):
                lines.append(f"      {s:<14} {c}")
    else:
        lines.append("    (not configured)")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_weekly(activity: dict, memctl: dict, todoctl: dict, nightctl: dict,
                  *, json_out: bool = False) -> str:
    """Weekly summary: notes created, todos completed, jobs run."""
    data = {
        "report": "weekly",
        "generated": _now_iso(),
        "activity": activity,
        "memory": memctl,
        "backlog": todoctl,
        "queue": nightctl,
    }

    if json_out:
        return json.dumps(data, indent=2, default=str)

    lines = []
    lines.append("=" * 60)
    lines.append("  WEEKLY SUMMARY")
    lines.append("=" * 60)

    lines.append("")
    lines.append("  ACTIVITY THIS WEEK")
    lines.append(f"    Notes created:    {activity['notes_created']}")
    lines.append(f"    Notes modified:   {activity['notes_modified']}")
    lines.append(f"    Todos created:    {activity['todos_created']}")
    lines.append(f"    Todos completed:  {activity['todos_completed']}")
    lines.append(f"    Jobs created:     {activity['jobs_created']}")
    lines.append(f"    Jobs completed:   {activity['jobs_completed']}")
    lines.append(f"    Jobs failed:      {activity['jobs_failed']}")

    # Current state snapshot
    lines.append("")
    lines.append("  CURRENT STATE")
    if memctl["available"]:
        lines.append(f"    Memory:  {memctl['note_count']} notes, {memctl['entities']} entities")
    if todoctl["available"]:
        open_count = todoctl["by_status"].get("open", 0) + todoctl["by_status"].get("in-progress", 0)
        lines.append(f"    Backlog: {todoctl['total']} items, {open_count} active")
    if nightctl["available"]:
        lines.append(f"    Queue:   {nightctl['total_jobs']} jobs, {nightctl['pending']} pending")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_health(memctl: dict, todoctl: dict, nightctl: dict,
                  *, json_out: bool = False) -> str:
    """System health: index drift, orphans, queue status, backlog age."""
    issues = []

    if memctl["available"]:
        if memctl["drift"]:
            issues.append(f"memctl: {memctl['drift']} notes with index drift")
        if memctl["orphans"]:
            issues.append(f"memctl: {memctl['orphans']} orphaned notes (not in index)")

    if nightctl["available"]:
        if nightctl["recent_failures"]:
            issues.append(f"nightctl: {nightctl['recent_failures']} failed run records")
        if nightctl["oldest_pending_age_hours"] is not None and nightctl["oldest_pending_age_hours"] > 48:
            issues.append(f"nightctl: oldest pending job is {nightctl['oldest_pending_age_hours']:.0f}h old")

    if todoctl["available"]:
        blocked = todoctl["by_status"].get("blocked", 0)
        if blocked:
            issues.append(f"todoctl: {blocked} blocked items")

    status = "HEALTHY" if not issues else "DEGRADED"

    data = {
        "report": "health",
        "generated": _now_iso(),
        "status": status,
        "issues": issues,
        "memory": memctl,
        "backlog": todoctl,
        "queue": nightctl,
    }

    if json_out:
        return json.dumps(data, indent=2, default=str)

    lines = []
    lines.append("=" * 60)
    lines.append(f"  SYSTEM HEALTH: {status}")
    lines.append("=" * 60)

    if issues:
        lines.append("")
        lines.append("  ISSUES")
        for issue in issues:
            lines.append(f"    - {issue}")

    lines.append("")
    lines.append("  MEMORY")
    if memctl["available"]:
        lines.append(f"    Notes:    {memctl['note_count']}")
        lines.append(f"    Drift:    {memctl['drift']}")
        lines.append(f"    Orphans:  {memctl['orphans']}")
    else:
        lines.append("    (not configured)")

    lines.append("")
    lines.append("  QUEUE")
    if nightctl["available"]:
        lines.append(f"    Jobs:     {nightctl['total_jobs']}")
        lines.append(f"    Pending:  {nightctl['pending']}")
        lines.append(f"    Failures: {nightctl['recent_failures']}")
        if nightctl["oldest_pending_age_hours"] is not None:
            lines.append(f"    Backlog:  {nightctl['oldest_pending_age_hours']:.1f}h oldest pending")
    else:
        lines.append("    (not configured)")

    lines.append("")
    lines.append("  BACKLOG")
    if todoctl["available"]:
        lines.append(f"    Items:    {todoctl['total']}")
        if todoctl["by_status"]:
            for s, c in sorted(todoctl["by_status"].items()):
                lines.append(f"      {s:<14} {c}")
    else:
        lines.append("    (not configured)")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_digest(activity: dict, since_label: str,
                  *, json_out: bool = False) -> str:
    """Activity digest for a time window."""
    data = {
        "report": "digest",
        "generated": _now_iso(),
        "since": since_label,
        "activity": activity,
    }

    if json_out:
        return json.dumps(data, indent=2, default=str)

    lines = []
    lines.append("=" * 60)
    lines.append(f"  ACTIVITY DIGEST (since {since_label})")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"    Notes created:    {activity['notes_created']}")
    lines.append(f"    Notes modified:   {activity['notes_modified']}")
    lines.append(f"    Todos created:    {activity['todos_created']}")
    lines.append(f"    Todos completed:  {activity['todos_completed']}")
    lines.append(f"    Jobs created:     {activity['jobs_created']}")
    lines.append(f"    Jobs completed:   {activity['jobs_completed']}")
    lines.append(f"    Jobs failed:      {activity['jobs_failed']}")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
