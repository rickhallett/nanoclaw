"""Data gathering from halos modules.

Imports reportctl collectors directly for structured data.
Adds logctl errors, agentctl session stats, and todoctl items.
"""
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from halos.reportctl.collectors import (
    collect_activity,
    collect_memctl,
    collect_nightctl,
    collect_todoctl,
)

from .config import Config


@dataclass
class BriefingData:
    """All gathered data for a briefing, ready for synthesis."""
    timestamp: str = ""
    kind: str = ""  # "morning" or "nightly"

    # From reportctl collectors
    memctl: dict = field(default_factory=dict)
    todoctl: dict = field(default_factory=dict)
    nightctl: dict = field(default_factory=dict)
    activity: dict = field(default_factory=dict)

    # Additional context
    recent_errors: list[str] = field(default_factory=list)
    session_stats: dict = field(default_factory=dict)
    open_todos: list[dict] = field(default_factory=list)

    # Personal metrics (trackctl + dashctl)
    tracker_summary: str = ""
    eisenhower_summary: str = ""

    def to_context(self) -> str:
        """Format gathered data as a context block for the synthesis prompt."""
        lines = [f"Data gathered at {self.timestamp} for {self.kind} briefing:\n"]

        lines.append("## Memory Corpus")
        if self.memctl.get("available"):
            lines.append(f"  Notes: {self.memctl['note_count']}")
            lines.append(f"  Entities: {self.memctl['entities']}")
            lines.append(f"  Types: {self.memctl['types']}")
            if self.memctl.get("drift"):
                lines.append(f"  Index drift: {self.memctl['drift']} notes")
            if self.memctl.get("orphans"):
                lines.append(f"  Orphaned notes: {self.memctl['orphans']}")
        else:
            lines.append("  memctl: unavailable")

        lines.append("\n## Backlog")
        if self.todoctl.get("available"):
            lines.append(f"  Total items: {self.todoctl['total']}")
            lines.append(f"  By status: {self.todoctl['by_status']}")
        if self.open_todos:
            lines.append("  Open items:")
            for t in self.open_todos:
                q = t.get("quadrant", "q3")
                lines.append(f"    [{q}] {t.get('title', 'untitled')}")
                if t.get("tags"):
                    lines.append(f"        tags: {', '.join(t['tags'])}")

        lines.append("\n## Job Queue")
        if self.nightctl.get("available"):
            lines.append(f"  Total jobs: {self.nightctl['total_jobs']}")
            lines.append(f"  By status: {self.nightctl['by_status']}")
            lines.append(f"  Pending: {self.nightctl['pending']}")
            if self.nightctl.get("recent_failures"):
                lines.append(f"  Recent failures: {self.nightctl['recent_failures']}")
            if self.nightctl.get("oldest_pending_age_hours"):
                lines.append(f"  Oldest pending: {self.nightctl['oldest_pending_age_hours']:.1f}h ago")

        lines.append("\n## Activity (last 24h)")
        if self.activity:
            lines.append(f"  Notes created: {self.activity.get('notes_created', 0)}")
            lines.append(f"  Notes modified: {self.activity.get('notes_modified', 0)}")
            lines.append(f"  Todos created: {self.activity.get('todos_created', 0)}")
            lines.append(f"  Todos completed: {self.activity.get('todos_completed', 0)}")
            lines.append(f"  Jobs created: {self.activity.get('jobs_created', 0)}")
            lines.append(f"  Jobs completed: {self.activity.get('jobs_completed', 0)}")
            if self.activity.get("jobs_failed"):
                lines.append(f"  Jobs failed: {self.activity['jobs_failed']}")

        if self.recent_errors:
            lines.append(f"\n## Errors (last 24h): {len(self.recent_errors)}")
            for err in self.recent_errors[:10]:
                lines.append(f"  - {err}")
            if len(self.recent_errors) > 10:
                lines.append(f"  ... and {len(self.recent_errors) - 10} more")

        if self.session_stats:
            lines.append("\n## Agent Sessions")
            for k, v in self.session_stats.items():
                lines.append(f"  {k}: {v}")

        if self.tracker_summary:
            lines.append("\n## Personal Metrics (trackctl)")
            lines.append(self.tracker_summary)

        if self.eisenhower_summary:
            lines.append("\n## Task Board (Eisenhower)")
            lines.append(self.eisenhower_summary)

        return "\n".join(lines)


def gather_morning(cfg: Config) -> BriefingData:
    """Gather data for the 0600 morning briefing."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    data = BriefingData(
        timestamp=now.isoformat(),
        kind="morning",
        memctl=collect_memctl(cfg.memctl_config),
        todoctl=collect_todoctl(cfg.todoctl_config),
        nightctl=collect_nightctl(cfg.nightctl_config),
        activity=collect_activity(
            cfg.memctl_config, cfg.todoctl_config, cfg.nightctl_config, since
        ),
        open_todos=_get_open_todos(cfg.todoctl_config),
        recent_errors=_get_recent_errors(cfg),
        session_stats=_get_session_stats(cfg),
        tracker_summary=_get_tracker_summary(),
        eisenhower_summary=_get_eisenhower_summary(),
    )
    return data


def gather_nightly(cfg: Config) -> BriefingData:
    """Gather data for the 2100 nightly recap."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=15)  # Since ~0600 this morning

    data = BriefingData(
        timestamp=now.isoformat(),
        kind="nightly",
        memctl=collect_memctl(cfg.memctl_config),
        todoctl=collect_todoctl(cfg.todoctl_config),
        nightctl=collect_nightctl(cfg.nightctl_config),
        activity=collect_activity(
            cfg.memctl_config, cfg.todoctl_config, cfg.nightctl_config, since
        ),
        open_todos=_get_open_todos(cfg.todoctl_config),
        recent_errors=_get_recent_errors(cfg),
        session_stats=_get_session_stats(cfg),
        tracker_summary=_get_tracker_summary(),
        eisenhower_summary=_get_eisenhower_summary(),
    )
    return data


def _get_open_todos(todoctl_config_path: Path) -> list[dict]:
    """Read open todo items with their details.

    Reads from nightctl unified items (queue/items/) first,
    falls back to legacy todoctl directory.
    """
    import yaml

    if not todoctl_config_path.exists():
        return []

    with open(todoctl_config_path) as f:
        cfg = yaml.safe_load(f) or {}

    base_dir = todoctl_config_path.parent

    # Try nightctl unified items first
    nightctl_items_dir = (base_dir / "queue" / "items").resolve()
    legacy_items_dir_str = cfg.get("items_dir", "./backlog/items")
    legacy_items_dir = Path(legacy_items_dir_str)
    if not legacy_items_dir.is_absolute():
        legacy_items_dir = (base_dir / legacy_items_dir).resolve()

    items_dir = nightctl_items_dir if nightctl_items_dir.exists() else legacy_items_dir

    if not items_dir.exists():
        return []

    todos = []
    for f in sorted(items_dir.glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            # Only include task-kind items (not jobs or agent-jobs)
            kind = data.get("kind", "task")
            if kind != "task":
                continue
            if data.get("status", "open") == "open":
                quadrant = data.get("quadrant", data.get("priority", "q3"))
                if isinstance(quadrant, int):
                    quadrant = f"q{min(max(quadrant, 1), 4)}"
                todos.append({
                    "title": data.get("title", f.stem),
                    "quadrant": quadrant,
                    "tags": data.get("tags", []),
                    "created": data.get("created", ""),
                })
        except Exception:
            pass

    # Sort by quadrant (q1 first)
    todos.sort(key=lambda t: t.get("quadrant", "q3"))
    return todos


def _get_tracker_summary() -> str:
    """Collect trackctl summaries via dashctl --text."""
    try:
        result = subprocess.run(
            ["dashctl", "--text"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def _get_eisenhower_summary() -> str:
    """Compact Eisenhower matrix summary for briefing."""
    try:
        from halos.nightctl.item import load_all_items
        from halos.nightctl.config import load_config
        cfg = load_config()
        items = load_all_items(cfg.items_dir)

        active = [i for i in items if i.status in (
            "open", "planning", "plan-review", "in-progress",
            "review", "testing", "blocked",
        )]

        q_labels = {"q1": "DO FIRST", "q2": "SCHEDULE", "q3": "DELEGATE", "q4": "ELIMINATE"}
        lines = []
        for q in ("q1", "q2", "q3", "q4"):
            group = [i for i in active if i.quadrant == q]
            if not group:
                continue
            lines.append(f"  {q.upper()} · {q_labels[q]} ({len(group)})")
            for item in group[:5]:
                marker = "*" if item.status == "in-progress" else " "
                lines.append(f"    [{marker}] {item.title[:60]}")
            if len(group) > 5:
                lines.append(f"        ... +{len(group) - 5} more")

        done_count = len([i for i in items if i.status == "done"])
        lines.append(f"  Total: {len(active)} active, {done_count} done")
        return "\n".join(lines)
    except Exception:
        return ""


def _get_recent_errors(cfg: Config) -> list[str]:
    """Get recent error-level log entries via logctl."""
    try:
        result = subprocess.run(
            ["logctl", "--config", str(cfg.logctl_config), "errors"],
            capture_output=True, text=True, timeout=10,
            cwd=str(cfg.project_root),
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            if lines == ["No errors in the last 24 hours."]:
                return []
            return lines[:20]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


def _get_session_stats(cfg: Config) -> dict:
    """Get agent session stats via agentctl."""
    try:
        result = subprocess.run(
            ["agentctl", "stats", "--json"],
            capture_output=True, text=True, timeout=10,
            cwd=str(cfg.project_root),
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return {}
