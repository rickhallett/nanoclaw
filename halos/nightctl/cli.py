"""nightctl CLI — unified work tracker.

Your best work happens while you sleep.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import yaml
except ImportError:
    from . import yaml_shim as yaml

from .config import load_config
from .item import Item, ValidationError, TransitionError, VALID_KINDS, load_all_items, find_item
from .job import Job, ValidationError as JobValidationError
from .manifest import Manifest
from .notify import Notifier
from .executor import Executor, _in_window, _parse_window
from .archive import run_archive, run_hatch
from halos.common.log import hlog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_local(tz_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(timezone.utc)


def _next_window_info(window_str: str, tz_name: str) -> str:
    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        sh, sm, eh, em = _parse_window(window_str)
        start_mins = sh * 60 + sm
        now_mins = now.hour * 60 + now.minute
        if now_mins < start_mins:
            diff = start_mins - now_mins
        else:
            diff = (24 * 60 - now_mins) + start_mins
        hours, mins = divmod(diff, 60)
        return f"{window_str} {tz_name} ({hours}h {mins}m away)"
    except Exception:
        return window_str


# Aliases for backward compatibility (shared helpers now in item.py)
_load_all_items = load_all_items
_find_item = find_item


def _transition_item(cfg, item_id: str, new_status: str, label: str, extra_cb=None):
    """Find an item, transition it, save, log, and print."""
    item = _find_item(cfg.items_dir, item_id)
    if not item:
        print(f"ERROR: item '{item_id}' not found", file=sys.stderr)
        sys.exit(1)
    try:
        item.transition(new_status)
    except TransitionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    if extra_cb:
        extra_cb(item)
    item.save()
    hlog("nightctl", "info", "status_changed", {"id": item.id, "status": new_status})
    print(f"{label}  {item.id}  {item.title}")
    return 0


# ---------------------------------------------------------------------------
# Item-based commands (new unified model)
# ---------------------------------------------------------------------------

def cmd_add(args, cfg):
    """Create a new work item (task, job, or agent-job)."""
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    entities = [e.strip() for e in args.entities.split(",")] if getattr(args, "entities", None) else []
    depends_on = [d.strip() for d in args.depends_on.split(",")] if getattr(args, "depends_on", None) else []

    kind = getattr(args, "kind", "task") or "task"
    command = getattr(args, "command", None)
    schedule = getattr(args, "schedule", None)
    window = getattr(args, "window", None)
    priority = getattr(args, "priority", 3)
    retries = getattr(args, "retries", 2)
    timeout = getattr(args, "timeout", 300)
    plan = getattr(args, "plan", None)
    plan_ref = getattr(args, "plan_ref", None)
    context = getattr(args, "context", None) or ""
    due = getattr(args, "due", None)

    try:
        item = Item.create(
            items_dir=cfg.items_dir,
            title=args.title,
            kind=kind,
            priority=priority,
            tags=tags,
            entities=entities,
            context=context,
            due=due,
            command=command,
            schedule=schedule,
            window=window,
            depends_on=depends_on if depends_on else None,
            retries=retries,
            timeout_secs=timeout,
            plan=plan,
            plan_ref=plan_ref,
            created_by="human",
        )
    except (ValidationError, Exception) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    hlog("nightctl", "info", "item_created", {"id": item.id, "title": args.title, "kind": kind})

    if args.json:
        out = {"id": item.id, "file": str(item.file_path), "kind": kind}
        print(json.dumps(out, indent=2))
    else:
        print(f"created  {item.id}  {item.file_path.name}")

    return 0


def cmd_plan(args, cfg):
    """Transition an item from open to planning."""
    return _transition_item(cfg, args.id, "planning", "planning")


def cmd_approve(args, cfg):
    """Approve a plan: plan-review -> in-progress."""
    return _transition_item(cfg, args.id, "in-progress", "approved")


def cmd_revise(args, cfg):
    """Send a failed agent-job back to plan-review."""
    return _transition_item(cfg, args.id, "plan-review", "revised")


def cmd_retry(args, cfg):
    """Retry a failed job: failed -> in-progress."""
    return _transition_item(cfg, args.id, "in-progress", "retry")


def cmd_start(args, cfg):
    """Start work: open -> in-progress."""
    return _transition_item(cfg, args.id, "in-progress", "started")


def cmd_review(args, cfg):
    """Submit for review: planning -> plan-review, or in-progress -> review."""
    item = _find_item(cfg.items_dir, args.id)
    if not item:
        print(f"ERROR: item '{args.id}' not found", file=sys.stderr)
        sys.exit(1)

    # Determine the target status based on current state
    if item.status == "planning":
        target = "plan-review"
    elif item.status == "in-progress":
        target = "review"
    else:
        # Let the state machine produce the right error
        # Try plan-review first (more specific), fall back to review
        from .item import valid_transitions
        allowed = valid_transitions(item.status, item.kind)
        if "plan-review" in allowed:
            target = "plan-review"
        elif "review" in allowed:
            target = "review"
        else:
            # Neither is valid — let transition() produce the error
            target = "review"

    try:
        item.transition(target)
    except TransitionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    item.save()
    hlog("nightctl", "info", "status_changed", {"id": item.id, "status": target})
    print(f"review  {item.id}  {item.title}")
    return 0


def cmd_testing(args, cfg):
    """Move to testing: review -> testing."""
    return _transition_item(cfg, args.id, "testing", "testing")


def cmd_done(args, cfg):
    """Mark as done: review|testing -> done."""
    return _transition_item(cfg, args.id, "done", "done")


def cmd_block(args, cfg):
    """Block an item with a reason."""
    item = _find_item(cfg.items_dir, args.id)
    if not item:
        print(f"ERROR: item '{args.id}' not found", file=sys.stderr)
        sys.exit(1)
    try:
        item.transition("blocked")
    except TransitionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    item.data["blocked_by"] = args.by
    item.save()
    hlog("nightctl", "info", "status_changed", {"id": item.id, "status": "blocked"})
    print(f"blocked  {item.id}  {item.title}  by: {args.by}")
    return 0


def cmd_defer(args, cfg):
    """Defer an item: open -> deferred."""
    return _transition_item(cfg, args.id, "deferred", "deferred")


def cmd_cancel_item(args, cfg):
    """Cancel an item via the unified state machine."""
    item = _find_item(cfg.items_dir, args.id)
    if not item:
        # Fall back to legacy job cancel
        return cmd_cancel_legacy(args, cfg)
    try:
        item.transition("cancelled")
    except TransitionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    item.save()
    hlog("nightctl", "info", "item_cancelled", {"id": item.id})
    print(f"cancelled  {item.id}  {item.title}")
    return 0


def cmd_edit(args, cfg):
    """Edit fields on an existing item."""
    item = _find_item(cfg.items_dir, args.id)
    if not item:
        print(f"ERROR: item '{args.id}' not found", file=sys.stderr)
        sys.exit(1)

    if args.title is not None:
        item.data["title"] = args.title
    if args.priority is not None:
        item.data["priority"] = args.priority
    if args.tags is not None:
        item.data["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.context is not None:
        item.data["context"] = args.context
    if args.due is not None:
        item.data["due"] = args.due
    if args.entities is not None:
        item.data["entities"] = [e.strip() for e in args.entities.split(",")]
    if getattr(args, "plan", None) is not None:
        # Validate plan XML before accepting the edit
        from halos.nightctl.plan import validate_plan_xml, PlanValidationError
        try:
            validate_plan_xml(args.plan)
        except PlanValidationError as e:
            print(f"ERROR: invalid plan XML: {'; '.join(e.errors)}", file=sys.stderr)
            sys.exit(1)
        item.data["plan"] = args.plan
    if getattr(args, "plan_ref", None) is not None:
        item.data["plan_ref"] = args.plan_ref

    item.data["modified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    item.save()
    hlog("nightctl", "info", "item_edited", {"id": item.id})
    print(f"edited  {item.id}  {item.title}")
    return 0


def cmd_graph(args, cfg):
    """ASCII priority tree of active items."""
    items = _load_all_items(cfg.items_dir)
    items.sort(key=lambda i: (i.priority, i.created))

    active = [i for i in items if i.status in (
        "open", "planning", "plan-review", "in-progress",
        "review", "testing", "blocked",
    )]
    done = [i for i in items if i.status == "done"]
    deferred = [i for i in items if i.status == "deferred"]

    width = 64
    print(f"{'=' * width}")
    print(f"  BACKLOG  ·  {len(items)} items  ·  {len(active)} active  ·  {len(done)} done")
    print(f"{'=' * width}")

    priority_labels = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}

    status_marker = {
        "open": " ",
        "planning": "P",
        "plan-review": "?",
        "in-progress": "*",
        "review": "R",
        "testing": "T",
        "blocked": "!",
    }

    for pri in sorted(priority_labels):
        group = [i for i in active if i.priority == pri]
        if not group:
            continue
        print(f"\n  \u250c\u2500 {priority_labels[pri]} ({len(group)})")
        for idx, i in enumerate(group):
            is_last = idx == len(group) - 1
            prefix = "  \u2514\u2500" if is_last else "  \u251c\u2500"
            marker = status_marker.get(i.status, "?")
            kind_tag = f" [{i.kind}]" if i.kind != "task" else ""
            print(f"{prefix} [{marker}] {i.title}{kind_tag}")
            if i.tags:
                detail = "    " if is_last else "  \u2502 "
                print(f"{detail}   #{', '.join(i.tags)}")

    if deferred:
        print(f"\n  \u250c\u2500 DEFERRED ({len(deferred)})")
        for idx, i in enumerate(deferred):
            is_last = idx == len(deferred) - 1
            prefix = "  \u2514\u2500" if is_last else "  \u251c\u2500"
            print(f"{prefix} {i.title}")

    print()
    print(f"{'=' * width}")
    return 0


# ---------------------------------------------------------------------------
# Legacy job-based commands (preserved for backward compatibility)
# ---------------------------------------------------------------------------

def cmd_enqueue(args, cfg):
    """Create a legacy job (backward compatible)."""
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    entities = [e.strip() for e in args.entities.split(",")] if getattr(args, "entities", None) else []
    depends_on = [d.strip() for d in args.depends_on.split(",")] if getattr(args, "depends_on", None) else []

    try:
        job, warnings = Job.create(
            jobs_dir=cfg.jobs_dir,
            cfg_job=cfg.job,
            title=args.title,
            command=args.command,
            schedule=getattr(args, "schedule", None) or cfg.job["default_schedule"],
            window=getattr(args, "window", None),
            priority=getattr(args, "priority", 5),
            depends_on=depends_on,
            retries=getattr(args, "retries", None),
            timeout_secs=getattr(args, "timeout", None),
            tags=tags,
            entities=entities,
        )
    except JobValidationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    manifest = Manifest(cfg.manifest_file)
    manifest.append(job)

    hlog("nightctl", "info", "job_enqueued", {"id": job.id, "title": args.title})

    if args.json:
        out = {"id": job.id, "file": str(job.file_path), "warnings": warnings}
        print(json.dumps(out, indent=2))
    else:
        print(f"enqueued  {job.id}  {job.file_path.name}")
        for w in warnings:
            print(f"  warning: {w}")

    return 0


def cmd_list(args, cfg):
    """List items from both legacy jobs (manifest) and unified items."""
    # Check if we have a --kind filter that means items-only
    kind_filter = getattr(args, "kind", None)

    # Load unified items
    items = _load_all_items(cfg.items_dir)

    if kind_filter:
        items = [i for i in items if i.kind == kind_filter]

    if getattr(args, "status", None):
        items = [i for i in items if i.status == args.status]
    if getattr(args, "tags", None):
        filter_tags = [t.strip() for t in args.tags.split(",")]
        items = [i for i in items if any(t in i.tags for t in filter_tags)]
    if getattr(args, "schedule", None):
        items = [i for i in items if i.schedule == args.schedule]

    # If no kind filter, also load legacy jobs from manifest
    if not kind_filter:
        manifest = Manifest(cfg.manifest_file)
        legacy_jobs = manifest.all_jobs()
        if getattr(args, "status", None):
            legacy_jobs = [j for j in legacy_jobs if j["status"] == args.status]
        if getattr(args, "tags", None):
            filter_tags = [t.strip() for t in args.tags.split(",")]
            legacy_jobs = [j for j in legacy_jobs if any(t in j.get("tags", []) for t in filter_tags)]
        if getattr(args, "schedule", None):
            legacy_jobs = [j for j in legacy_jobs if j.get("schedule") == args.schedule]
    else:
        legacy_jobs = []

    limit = getattr(args, "limit", 20) or 20

    if args.json:
        combined = [i.data for i in items] + legacy_jobs
        combined = combined[:limit]
        print(json.dumps(combined, indent=2))
    else:
        if not items and not legacy_jobs:
            print("no jobs found")
            return 0
        fmt = "{:<22} {:<35} {:<12} {:<4} {:<10} {}"
        print(fmt.format("ID", "TITLE", "STATUS", "PRI", "KIND", "SCHEDULE"))
        print("-" * 95)

        # Print unified items first
        count = 0
        for i in sorted(items, key=lambda x: (x.priority, x.created)):
            if count >= limit:
                break
            title = i.title[:34]
            kind = i.kind
            sched = i.schedule or ""
            print(fmt.format(i.id, title, i.status, str(i.priority), kind, sched))
            count += 1

        # Then legacy jobs
        for j in legacy_jobs:
            if count >= limit:
                break
            title = j["title"][:34]
            print(fmt.format(
                j["id"], title, j["status"],
                str(j.get("priority", 5)), "job",
                j.get("schedule", ""),
            ))
            count += 1

    return 0


def cmd_status(args, cfg):
    """Show status of an item or legacy job."""
    # Try unified items first
    item = _find_item(cfg.items_dir, args.id)
    if item:
        runs = []
        for run_file in sorted(cfg.runs_dir.glob(f"{args.id}-run-*.yaml")):
            with open(run_file) as f:
                runs.append(yaml.safe_load(f))

        if args.json:
            print(json.dumps({"item": item.data, "runs": runs}, indent=2))
        else:
            print(f"Item:     {item.id}")
            print(f"Title:    {item.title}")
            print(f"Kind:     {item.kind}")
            print(f"Status:   {item.status}")
            print(f"Priority: {item.priority}")
            if item.schedule:
                print(f"Schedule: {item.schedule}")
            if item.tags:
                print(f"Tags:     {', '.join(item.tags)}")
            if item.context:
                print(f"Context:  {item.context}")
            if item.due:
                print(f"Due:      {item.due}")
            if item.blocked_by:
                print(f"Blocked:  {item.blocked_by}")
            if item.plan_ref:
                print(f"Plan ref: {item.plan_ref}")
            if item.plan:
                print(f"Plan:     (inline, {len(item.plan)} chars)")
            if runs:
                print("Runs:")
                for r in runs:
                    outcome = r.get("outcome", "?")
                    duration = r.get("duration_secs", 0)
                    exit_code = r.get("exit_code", "?")
                    print(f"  attempt {r['attempt']} -- {outcome} -- {duration}s -- exit {exit_code}")
            else:
                print("Runs:     none")
        return 0

    # Fall back to legacy manifest
    manifest = Manifest(cfg.manifest_file)
    entry = manifest.get_entry(args.id)

    if not entry:
        print(f"ERROR: item {args.id} not found", file=sys.stderr)
        sys.exit(1)

    runs = []
    for run_file in sorted(cfg.runs_dir.glob(f"{args.id}-run-*.yaml")):
        with open(run_file) as f:
            runs.append(yaml.safe_load(f))

    if args.json:
        print(json.dumps({"job": entry, "runs": runs}, indent=2))
    else:
        print(f"Job:    {entry['id']}")
        print(f"Title:  {entry['title']}")
        print(f"Status: {entry['status']}")
        print(f"Schedule: {entry.get('schedule', '')}  Priority: {entry.get('priority', 5)}")
        if entry.get("tags"):
            print(f"Tags:   {', '.join(entry['tags'])}")
        if runs:
            print("Runs:")
            for r in runs:
                outcome = r.get("outcome", "?")
                duration = r.get("duration_secs", 0)
                exit_code = r.get("exit_code", "?")
                print(f"  attempt {r['attempt']} -- {outcome} -- {duration}s -- exit {exit_code}")
        else:
            print("Runs:   none")
    return 0


def cmd_run(args, cfg):
    manifest = Manifest(cfg.manifest_file)
    notifier = Notifier(cfg.notify)
    executor = Executor(cfg, manifest, notifier)

    counts = executor.run(
        force=getattr(args, "force", False),
        limit=getattr(args, "limit", None),
        dry_run=getattr(args, "dry_run", False),
    )

    if counts.get("outside_window"):
        sys.exit(0)

    print(f"\ndone: {counts['done']}  failed: {counts['failed']}  skipped: {counts['skipped']}")

    if counts["failed"] > 0:
        sys.exit(5)
    return 0


def cmd_cancel_legacy(args, cfg):
    """Cancel a legacy job via manifest."""
    manifest = Manifest(cfg.manifest_file)
    entry = manifest.get_entry(args.id)

    if not entry:
        print(f"ERROR: job {args.id} not found", file=sys.stderr)
        sys.exit(1)

    if entry["status"] == "running":
        print(f"ERROR: cannot cancel a running job", file=sys.stderr)
        sys.exit(1)

    file_path = Path(entry["file"])
    if file_path.exists():
        job = Job.from_file(file_path)
        job.set_status("cancelled")
        job.save()

    manifest.update_status(args.id, "cancelled")
    hlog("nightctl", "info", "job_cancelled", {"id": args.id})

    archive_dir = cfg.archive_dir
    archive_dir.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        import shutil
        dest = archive_dir / file_path.name
        shutil.move(str(file_path), str(dest))

    print(f"cancelled  {args.id}")
    return 0


def cmd_manifest_rebuild(args, cfg):
    manifest = Manifest(cfg.manifest_file)
    count, errors = manifest.rebuild(cfg.jobs_dir)
    if args.json:
        print(json.dumps({"processed": count, "errors": errors}))
    else:
        print(f"rebuilt manifest: {count} jobs processed")
        for e in errors:
            print(f"  error: {e}")
    return 0


def cmd_manifest_verify(args, cfg):
    manifest = Manifest(cfg.manifest_file)
    results = manifest.verify(cfg.jobs_dir)

    drift = [r for r in results if r["status"] in ("DRIFT", "MISSING")]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"  {r['status']:<8} {r['id']}  {Path(r['file']).name}")

    if drift:
        print("\ndrift detected -- run: nightctl manifest rebuild")
        sys.exit(3)
    return 0


def cmd_archive(args, cfg):
    manifest = Manifest(cfg.manifest_file)
    execute = getattr(args, "execute", False)
    since = getattr(args, "since", None)

    if not execute:
        print("dry-run (pass --execute to act)")

    results = run_archive(cfg, manifest, execute=execute, since=since)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if execute:
            print(f"archived: {results['archived']} of {results['candidates']} candidates")
        else:
            print(f"candidates: {results['candidates']} (dry-run)")
    return 0


def cmd_hatch(args, cfg):
    execute = getattr(args, "execute", False)
    before = getattr(args, "before", None)

    if not execute:
        print("dry-run (pass --execute to permanently eject)")

    results = run_hatch(cfg, execute=execute, before=before)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if results.get("error"):
            print(f"ERROR: {results['error']}", file=sys.stderr)
            sys.exit(1)
        if execute:
            print(f"ejected: {results['ejected']} of {results['candidates']} candidates")
        else:
            print(f"candidates: {results['candidates']} (dry-run)")
    return 0


def cmd_stats(args, cfg):
    manifest = Manifest(cfg.manifest_file)
    counts = manifest.counts()

    # Also count unified items
    items = _load_all_items(cfg.items_dir)
    item_by_status = {}
    item_by_kind = {}
    for i in items:
        item_by_status[i.status] = item_by_status.get(i.status, 0) + 1
        item_by_kind[i.kind] = item_by_kind.get(i.kind, 0) + 1

    exec_cfg = cfg.execution
    window = exec_cfg.get("overnight_window", "02:00-05:00")
    tz = exec_cfg.get("timezone", "Europe/London")
    in_window = _in_window(window, tz)
    next_info = "NOW (in window)" if in_window else _next_window_info(window, tz)

    archive_dir = cfg.archive_dir
    archived_count = len(list(archive_dir.glob("*-archived-*.yaml"))) if archive_dir.exists() else 0

    if args.json:
        out = {
            "total": counts["total"],
            "items": len(items),
            "archived": archived_count,
            "by_status": counts["by_status"],
            "items_by_status": item_by_status,
            "items_by_kind": item_by_kind,
            "by_schedule": counts["by_schedule"],
            "by_tag": counts["by_tag"],
            "window": window,
            "in_window": in_window,
        }
        print(json.dumps(out, indent=2))
    else:
        by_status = counts["by_status"]
        print(f"Jobs (queue):  {counts['total']}")
        for status in ["pending", "running", "claimed", "done", "failed"]:
            n = by_status.get(status, 0)
            if n or status in ("pending", "done", "failed"):
                print(f"  {status:<10} {n}")
        if items:
            print(f"\nItems (unified):  {len(items)}")
            for status, n in sorted(item_by_status.items()):
                print(f"  {status:<14} {n}")
            print(f"\nBy kind:")
            for kind, n in sorted(item_by_kind.items()):
                print(f"  {kind:<12} {n}")
        print(f"Archived:      {archived_count}")
        print()
        if counts["by_schedule"]:
            print("By schedule:")
            for k, v in counts["by_schedule"].items():
                print(f"  {k:<12} {v}")
            print()
        if counts["by_tag"]:
            print("By tag:")
            for k, v in sorted(counts["by_tag"].items(), key=lambda x: -x[1]):
                print(f"  {k:<16} {v}")
            print()
        print(f"Next window:  {next_info}")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="nightctl",
        description="nightctl — unified work tracker. Your best work happens while you sleep.",
    )
    parser.add_argument("--config", default=None, help="Path to nightctl.yaml")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="subcommand")

    # add (unified Item)
    add = sub.add_parser("add", help="Create a new work item")
    add.add_argument("--title", required=True)
    add.add_argument("--kind", default="task", choices=list(VALID_KINDS),
                      help="Item kind: task, job, or agent-job")
    add.add_argument("--command", default=None, help="Command to execute (required for jobs)")
    add.add_argument("--plan", default=None, help="Inline XML plan (agent-jobs)")
    add.add_argument("--plan-ref", default=None, dest="plan_ref",
                      help="Path to file containing XML plan (agent-jobs)")
    add.add_argument("--schedule", default=None)
    add.add_argument("--window", default=None)
    add.add_argument("--priority", type=int, default=3)
    add.add_argument("--depends-on", default=None, dest="depends_on")
    add.add_argument("--retries", type=int, default=2)
    add.add_argument("--timeout", type=int, default=300)
    add.add_argument("--tags", default=None)
    add.add_argument("--entities", default=None)
    add.add_argument("--context", default=None)
    add.add_argument("--due", default=None)

    # enqueue (legacy, backward compat)
    enq = sub.add_parser("enqueue", help="Create a new job (legacy)")
    enq.add_argument("--title", required=True)
    enq.add_argument("--command", required=True)
    enq.add_argument("--schedule", default=None)
    enq.add_argument("--window", default=None)
    enq.add_argument("--priority", type=int, default=5)
    enq.add_argument("--depends-on", default=None, dest="depends_on")
    enq.add_argument("--retries", type=int, default=None)
    enq.add_argument("--timeout", type=int, default=None)
    enq.add_argument("--tags", default=None)
    enq.add_argument("--entities", default=None)

    # plan
    pl = sub.add_parser("plan", help="Start planning: open -> planning")
    pl.add_argument("id")

    # approve
    ap = sub.add_parser("approve", help="Approve plan: plan-review -> in-progress")
    ap.add_argument("id")

    # revise
    rv = sub.add_parser("revise", help="Revise failed agent-job: failed -> plan-review")
    rv.add_argument("id")

    # retry
    rt = sub.add_parser("retry", help="Retry failed job: failed -> in-progress")
    rt.add_argument("id")

    # start
    st = sub.add_parser("start", help="Start work: open -> in-progress")
    st.add_argument("id")

    # review
    rev = sub.add_parser("review", help="Submit for review: planning -> plan-review, or in-progress -> review")
    rev.add_argument("id")

    # testing
    ts = sub.add_parser("testing", help="Move to testing: review -> testing")
    ts.add_argument("id")

    # done
    dn = sub.add_parser("done", help="Mark as done: review|testing -> done")
    dn.add_argument("id")

    # block
    bl = sub.add_parser("block", help="Block an item")
    bl.add_argument("id")
    bl.add_argument("--by", required=True, help="Reason for blocking")

    # defer
    df = sub.add_parser("defer", help="Defer an item: open -> deferred")
    df.add_argument("id")

    # cancel
    can = sub.add_parser("cancel", help="Cancel an item or job")
    can.add_argument("id")

    # edit
    ed = sub.add_parser("edit", help="Edit an existing item")
    ed.add_argument("id")
    ed.add_argument("--title", default=None)
    ed.add_argument("--priority", type=int, default=None)
    ed.add_argument("--tags", default=None)
    ed.add_argument("--context", default=None)
    ed.add_argument("--due", default=None)
    ed.add_argument("--entities", default=None)
    ed.add_argument("--plan", default=None)
    ed.add_argument("--plan-ref", default=None, dest="plan_ref")

    # graph
    sub.add_parser("graph", help="ASCII priority tree of active items")

    # list
    lst = sub.add_parser("list", help="List items")
    lst.add_argument("--status", default=None)
    lst.add_argument("--tags", default=None)
    lst.add_argument("--schedule", default=None)
    lst.add_argument("--kind", default=None, choices=list(VALID_KINDS))
    lst.add_argument("--limit", type=int, default=20)

    # status
    sts = sub.add_parser("status", help="Show item or job details")
    sts.add_argument("id")

    # run
    run = sub.add_parser("run", help="Execute in-progress jobs/agent-jobs")
    run.add_argument("--force", action="store_true")
    run.add_argument("--limit", type=int, default=None)

    # manifest
    mani = sub.add_parser("manifest", help="Manifest subcommands")
    mani_sub = mani.add_subparsers(dest="manifest_command")
    mani_sub.add_parser("rebuild", help="Regenerate manifest from jobs corpus")
    mani_sub.add_parser("verify", help="Hash-check manifest entries")

    # archive
    arch = sub.add_parser("archive", help="Archive old done/failed items")
    arch.add_argument("--execute", action="store_true")
    arch.add_argument("--since", default=None)

    # hatch
    hatch = sub.add_parser("hatch", help="Permanently eject archived items")
    hatch.add_argument("--execute", action="store_true")
    hatch.add_argument("--before", default=None)

    # stats
    sub.add_parser("stats", help="Queue health report")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(4)

    dispatch = {
        "add": cmd_add,
        "enqueue": cmd_enqueue,
        "list": cmd_list,
        "status": cmd_status,
        "run": cmd_run,
        "cancel": cmd_cancel_item,
        "plan": cmd_plan,
        "approve": cmd_approve,
        "revise": cmd_revise,
        "retry": cmd_retry,
        "start": cmd_start,
        "review": cmd_review,
        "testing": cmd_testing,
        "done": cmd_done,
        "block": cmd_block,
        "defer": cmd_defer,
        "edit": cmd_edit,
        "graph": cmd_graph,
        "archive": cmd_archive,
        "hatch": cmd_hatch,
        "stats": cmd_stats,
    }

    if args.subcommand == "manifest":
        if not getattr(args, "manifest_command", None):
            print("usage: nightctl manifest [rebuild|verify]")
            sys.exit(0)
        if args.manifest_command == "rebuild":
            sys.exit(cmd_manifest_rebuild(args, cfg))
        elif args.manifest_command == "verify":
            sys.exit(cmd_manifest_verify(args, cfg))
    elif args.subcommand in dispatch:
        sys.exit(dispatch[args.subcommand](args, cfg) or 0)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
