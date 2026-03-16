import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import load_config
from .job import Job, ValidationError
from .manifest import Manifest
from .notify import Notifier
from .executor import Executor, _in_window, _parse_window
from .archive import run_archive, run_hatch


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


def cmd_enqueue(args, cfg):
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
    except ValidationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    manifest = Manifest(cfg.manifest_file)
    manifest.append(job)

    if args.json:
        out = {"id": job.id, "file": str(job.file_path), "warnings": warnings}
        print(json.dumps(out, indent=2))
    else:
        print(f"enqueued  {job.id}  {job.file_path.name}")
        for w in warnings:
            print(f"  warning: {w}")

    return 0


def cmd_list(args, cfg):
    manifest = Manifest(cfg.manifest_file)
    jobs = manifest.all_jobs()

    if getattr(args, "status", None):
        jobs = [j for j in jobs if j["status"] == args.status]
    if getattr(args, "tags", None):
        filter_tags = [t.strip() for t in args.tags.split(",")]
        jobs = [j for j in jobs if any(t in j.get("tags", []) for t in filter_tags)]
    if getattr(args, "schedule", None):
        jobs = [j for j in jobs if j.get("schedule") == args.schedule]

    limit = getattr(args, "limit", 20) or 20
    jobs = jobs[:limit]

    if args.json:
        print(json.dumps(jobs, indent=2))
    else:
        if not jobs:
            print("no jobs found")
            return 0
        fmt = "{:<22} {:<38} {:<10} {:<4} {}"
        print(fmt.format("ID", "TITLE", "STATUS", "PRI", "SCHEDULE"))
        print("-" * 85)
        for j in jobs:
            title = j["title"][:37]
            print(fmt.format(j["id"], title, j["status"], str(j.get("priority", 5)), j.get("schedule", "")))
    return 0


def cmd_status(args, cfg):
    manifest = Manifest(cfg.manifest_file)
    entry = manifest.get_entry(args.id)

    if not entry:
        print(f"ERROR: job {args.id} not found in manifest", file=sys.stderr)
        sys.exit(1)

    runs = []
    for run_file in sorted(cfg.runs_dir.glob(f"{args.id}-run-*.yaml")):
        try:
            import yaml
        except ImportError:
            from nightctl_lib import yaml_shim as yaml
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
                print(f"  attempt {r['attempt']} — {outcome} — {duration}s — exit {exit_code}")
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


def cmd_cancel(args, cfg):
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

    # move to archive
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
        print("\ndrift detected — run: nightctl manifest rebuild")
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
            "archived": archived_count,
            "by_status": counts["by_status"],
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


def build_parser():
    parser = argparse.ArgumentParser(
        prog="nightctl",
        description="halOS overnight batch processing queue",
    )
    parser.add_argument("--config", default=None, help="Path to nightctl.yaml")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="subcommand")

    # enqueue
    enq = sub.add_parser("enqueue", help="Create a new job")
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

    # list
    lst = sub.add_parser("list", help="List jobs")
    lst.add_argument("--status", default=None)
    lst.add_argument("--tags", default=None)
    lst.add_argument("--schedule", default=None)
    lst.add_argument("--limit", type=int, default=20)

    # status
    sts = sub.add_parser("status", help="Show a specific job")
    sts.add_argument("id")

    # run
    run = sub.add_parser("run", help="Execute pending jobs")
    run.add_argument("--force", action="store_true")
    run.add_argument("--limit", type=int, default=None)

    # cancel
    can = sub.add_parser("cancel", help="Cancel a pending job")
    can.add_argument("id")

    # manifest
    mani = sub.add_parser("manifest", help="Manifest subcommands")
    mani_sub = mani.add_subparsers(dest="manifest_command")
    mani_sub.add_parser("rebuild", help="Regenerate manifest from jobs corpus")
    mani_sub.add_parser("verify", help="Hash-check manifest entries")

    # archive
    arch = sub.add_parser("archive", help="Archive old done/failed jobs")
    arch.add_argument("--execute", action="store_true")
    arch.add_argument("--since", default=None)

    # hatch
    hatch = sub.add_parser("hatch", help="Permanently eject archived jobs")
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
        "enqueue": cmd_enqueue,
        "list": cmd_list,
        "status": cmd_status,
        "run": cmd_run,
        "cancel": cmd_cancel,
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
