"""Collectors pull data from other halos modules' data files.

These functions do NOT import other halos modules. They read filesystem
artifacts directly: INDEX.md, MANIFEST.yaml, backlog items, run records.

CONTRACT: memctl INDEX.md
  YAML block after "## MEMORY_INDEX\\n```yaml\\n"
  Required fields: note_count, notes[].type, notes[].modified, notes[].entities

CONTRACT: todoctl backlog/items/*.yaml
  Required fields: status, priority, tags, created

CONTRACT: nightctl queue/MANIFEST.yaml
  Required fields: job_count, pending, done, failed, jobs[].status, jobs[].created

CONTRACT: nightctl queue/runs/*.yaml
  Required fields: outcome (NOT status), started
"""
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ── memctl ──────────────────────────────────────────────────────


def _parse_index_yaml(index_path: Path) -> dict:
    """Extract the YAML block from memory/INDEX.md.

    Searches for the specific ``## MEMORY_INDEX`` heading that memctl writes,
    rather than matching any generic ``yaml`` code block.
    """
    if not index_path.exists():
        return {}
    content = index_path.read_text()
    marker = "## MEMORY_INDEX\n```yaml\n"
    start = content.find(marker)
    if start == -1:
        # Fallback: try the old generic pattern for backwards compat
        start = content.find("```yaml\n")
        if start == -1:
            return {}
        start += len("```yaml\n")
    else:
        start += len(marker)
    end = content.find("```", start)
    if end == -1:
        return {}
    return yaml.safe_load(content[start:end]) or {}


def collect_memctl(memctl_config_path: Path) -> dict:
    """Collect memory corpus stats from memctl config and index file."""
    result = {
        "available": False,
        "note_count": 0,
        "entities": 0,
        "tags": 0,
        "types": {},
        "orphans": 0,
        "drift": 0,
    }

    if not memctl_config_path.exists():
        return result

    with open(memctl_config_path) as f:
        cfg = yaml.safe_load(f) or {}

    base_dir = memctl_config_path.parent
    memory_dir = _resolve(base_dir, cfg.get("memory_dir", "./memory"))
    index_file = _resolve(base_dir, cfg.get("index_file", "./memory/INDEX.md"))

    idx = _parse_index_yaml(index_file)
    if not idx:
        if index_file.exists():
            print(f"WARNING: memctl INDEX.md exists at {index_file} but could not "
                  "be parsed — expected '## MEMORY_INDEX\\n```yaml\\n' block",
                  file=sys.stderr)
        return result

    result["available"] = True
    notes = idx.get("notes", [])
    result["note_count"] = idx.get("note_count", len(notes))
    result["entities"] = len(idx.get("entities", []))
    result["tags"] = len(idx.get("tag_vocabulary", []))

    type_counts: dict[str, int] = {}
    drift = 0
    for n in notes:
        t = n.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        # Check for drift: compare stored hash with file hash
        fpath = Path(n.get("file", ""))
        if fpath.exists():
            actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
            if actual != n.get("hash", ""):
                drift += 1

    result["types"] = type_counts
    result["drift"] = drift

    # Orphan check
    notes_dir = memory_dir / "notes"
    if notes_dir.exists():
        from pathlib import Path as _P
        indexed_files = {Path(n.get("file", "")).name for n in notes}
        for f in notes_dir.iterdir():
            if f.suffix == ".md" and f.name not in indexed_files:
                result["orphans"] += 1

    return result


# ── todoctl ─────────────────────────────────────────────────────


def collect_todoctl(todoctl_config_path: Path) -> dict:
    """Collect backlog stats from nightctl unified items (queue/items/).

    Falls back to legacy todoctl items directory if nightctl items not found.
    The todoctl_config_path is used to resolve the project root; items are
    read from queue/items/ (nightctl unified location) first.
    """
    result = {
        "available": False,
        "total": 0,
        "by_status": {},
        "by_priority": {},
    }

    if not todoctl_config_path.exists():
        return result

    with open(todoctl_config_path) as f:
        cfg = yaml.safe_load(f) or {}

    base_dir = todoctl_config_path.parent

    # Try nightctl unified items first (queue/items/)
    nightctl_items_dir = _resolve(base_dir, "./queue/items")
    legacy_items_dir = _resolve(base_dir, cfg.get("items_dir", "./backlog/items"))

    # Use nightctl items if available, fall back to legacy
    items_dir = nightctl_items_dir if nightctl_items_dir.exists() else legacy_items_dir

    if not items_dir.exists():
        result["available"] = True
        return result

    result["available"] = True
    by_status: dict[str, int] = {}
    by_priority: dict[int, int] = {}
    total = 0

    for f in sorted(items_dir.glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            # Only count task-kind items for the todoctl collector
            # (jobs and agent-jobs are counted by collect_nightctl)
            kind = data.get("kind", "task")
            if kind != "task":
                continue
            total += 1
            s = data.get("status", "open")
            by_status[s] = by_status.get(s, 0) + 1
            p = data.get("priority", 3)
            by_priority[p] = by_priority.get(p, 0) + 1
        except Exception as exc:
            print(f"WARNING: item {f} could not be parsed: {exc}",
                  file=sys.stderr)

    result["total"] = total
    result["by_status"] = by_status
    result["by_priority"] = by_priority
    return result


# ── nightctl ────────────────────────────────────────────────────


def collect_nightctl(nightctl_config_path: Path) -> dict:
    """Collect queue stats from nightctl manifest and runs."""
    result = {
        "available": False,
        "total_jobs": 0,
        "by_status": {},
        "pending": 0,
        "recent_failures": 0,
        "oldest_pending_age_hours": None,
    }

    if not nightctl_config_path.exists():
        return result

    with open(nightctl_config_path) as f:
        cfg = yaml.safe_load(f) or {}

    base_dir = nightctl_config_path.parent
    manifest_file = _resolve(base_dir, cfg.get("manifest_file", "./queue/MANIFEST.yaml"))
    runs_dir = _resolve(base_dir, cfg.get("runs_dir", "./queue/runs"))

    if not manifest_file.exists():
        result["available"] = True
        return result

    try:
        with open(manifest_file) as f:
            manifest = yaml.safe_load(f) or {}
    except Exception as exc:
        print(f"WARNING: nightctl MANIFEST.yaml at {manifest_file} exists but "
              f"could not be parsed: {exc}", file=sys.stderr)
        result["available"] = True
        return result

    if not isinstance(manifest.get("jobs"), list):
        print(f"WARNING: nightctl MANIFEST.yaml at {manifest_file} missing or "
              "invalid 'jobs' list", file=sys.stderr)

    result["available"] = True
    jobs = manifest.get("jobs", [])
    result["total_jobs"] = len(jobs)
    result["pending"] = manifest.get("pending", 0)

    by_status: dict[str, int] = {}
    now = datetime.now(timezone.utc)
    oldest_pending_hours = None

    for j in jobs:
        s = j.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

        if s == "pending":
            created = j.get("created", "")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_hours = (now - created_dt).total_seconds() / 3600
                    if oldest_pending_hours is None or age_hours > oldest_pending_hours:
                        oldest_pending_hours = age_hours
                except (ValueError, AttributeError):
                    pass

    result["by_status"] = by_status
    result["oldest_pending_age_hours"] = oldest_pending_hours

    # Count recent failures from run records
    if runs_dir.exists():
        recent_failures = 0
        for f in runs_dir.glob("*.yaml"):
            try:
                with open(f) as fh:
                    run = yaml.safe_load(fh) or {}
                if run.get("outcome") == "failed":
                    recent_failures += 1
            except Exception:
                pass
        result["recent_failures"] = recent_failures

    return result


# ── activity (time-windowed) ────────────────────────────────────


def collect_activity(memctl_config_path: Path, todoctl_config_path: Path,
                     nightctl_config_path: Path, since: datetime) -> dict:
    """Collect activity within a time window for digest/weekly reports."""
    result = {
        "notes_created": 0,
        "notes_modified": 0,
        "todos_created": 0,
        "todos_completed": 0,
        "jobs_created": 0,
        "jobs_completed": 0,
        "jobs_failed": 0,
    }

    # memctl: notes created/modified since
    if memctl_config_path.exists():
        with open(memctl_config_path) as f:
            cfg = yaml.safe_load(f) or {}
        base_dir = memctl_config_path.parent
        index_file = _resolve(base_dir, cfg.get("index_file", "./memory/INDEX.md"))
        idx = _parse_index_yaml(index_file)
        for n in idx.get("notes", []):
            modified = n.get("modified", "")
            if modified:
                try:
                    mod_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                    if mod_dt >= since:
                        result["notes_modified"] += 1
                        # Heuristic: if modified ~= created (within same index entry),
                        # count as created. We use the id timestamp prefix.
                        note_id = n.get("id", "")
                        if _id_after(note_id, since):
                            result["notes_created"] += 1
                except (ValueError, AttributeError):
                    pass

    # todoctl: items created/completed since (reads from nightctl unified items)
    if todoctl_config_path.exists():
        with open(todoctl_config_path) as f:
            cfg = yaml.safe_load(f) or {}
        base_dir = todoctl_config_path.parent
        nightctl_items_dir = _resolve(base_dir, "./queue/items")
        legacy_items_dir = _resolve(base_dir, cfg.get("items_dir", "./backlog/items"))
        items_dir = nightctl_items_dir if nightctl_items_dir.exists() else legacy_items_dir
        if items_dir.exists():
            for f in items_dir.glob("*.yaml"):
                try:
                    with open(f) as fh:
                        data = yaml.safe_load(fh) or {}
                    created = data.get("created", "")
                    if created:
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if created_dt >= since:
                            result["todos_created"] += 1
                    if data.get("status") == "done":
                        # We don't have a "completed_at" field, use file mtime
                        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                        if mtime >= since:
                            result["todos_completed"] += 1
                except Exception:
                    pass

    # nightctl: jobs created/completed/failed since
    if nightctl_config_path.exists():
        with open(nightctl_config_path) as f:
            cfg = yaml.safe_load(f) or {}
        base_dir = nightctl_config_path.parent
        manifest_file = _resolve(base_dir, cfg.get("manifest_file", "./queue/MANIFEST.yaml"))
        if manifest_file.exists():
            with open(manifest_file) as fh:
                manifest = yaml.safe_load(fh) or {}
            for j in manifest.get("jobs", []):
                created = j.get("created", "")
                if created:
                    try:
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        if created_dt >= since:
                            result["jobs_created"] += 1
                            if j.get("status") == "done":
                                result["jobs_completed"] += 1
                            elif j.get("status") == "failed":
                                result["jobs_failed"] += 1
                    except (ValueError, AttributeError):
                        pass

    return result


# ── helpers ─────────────────────────────────────────────────────


def _resolve(base_dir: Path, path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def _id_after(note_id: str, since: datetime) -> bool:
    """Check if a note ID (YYYYMMDD-HHMMSS...) was created after `since`."""
    try:
        # IDs start with YYYYMMDD-HHMMSS
        prefix = note_id[:15]  # "20260316-120000"
        dt = datetime.strptime(prefix, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        return dt >= since
    except (ValueError, IndexError):
        return False
