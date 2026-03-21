"""backupctl CLI — structured backup policy management.

Usage:
    backupctl targets                              # list configured targets
    backupctl run [--target TARGET]                # execute backup
    backupctl list [--target TARGET] [--json]      # list snapshots
    backupctl verify                               # verify repository integrity
    backupctl restore --target T --snapshot S --to PATH  # restore
    backupctl summary                              # one-liner for briefings
"""

import argparse
import json
import sys

from halos.common.log import hlog

from . import engine
from .config import load_config, resolve_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="backupctl",
        description="backupctl — structured backup policy management",
    )
    sub = parser.add_subparsers(dest="command")

    # --- targets ---
    sub.add_parser("targets", help="List configured backup targets")

    # --- run ---
    p_run = sub.add_parser("run", help="Execute backup (all or specific target)")
    p_run.add_argument("--target", default=None, help="Specific target to back up")

    # --- list ---
    p_list = sub.add_parser("list", help="List available snapshots")
    p_list.add_argument("--target", default=None, help="Filter by target")
    p_list.add_argument("--json", action="store_true", dest="json_out")

    # --- verify ---
    p_verify = sub.add_parser("verify", help="Verify backup repository integrity")
    p_verify.add_argument("--target", default=None, help="Filter by target")

    # --- restore ---
    p_restore = sub.add_parser("restore", help="Restore from snapshot")
    p_restore.add_argument("--target", required=True, help="Target name")
    p_restore.add_argument("--snapshot", required=True, help="Snapshot ID")
    p_restore.add_argument("--to", required=True, dest="restore_to",
                           help="Directory to restore into (required)")

    # --- summary ---
    sub.add_parser("summary", help="One-liner summary for briefing integration")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "targets": cmd_targets,
        "run": cmd_run,
        "list": cmd_list,
        "verify": cmd_verify,
        "restore": cmd_restore,
        "summary": cmd_summary,
    }
    sys.exit(dispatch[args.command](args) or 0)


def cmd_targets(args) -> int:
    """List configured backup targets."""
    cfg = load_config()

    if not cfg.targets:
        print("No backup targets configured.")
        return 0

    fmt = "{:<12} {:<45} {}"
    print(fmt.format("TARGET", "PATHS", "RETENTION"))
    print("-" * 80)
    for name, target in sorted(cfg.targets.items()):
        paths_str = ", ".join(target.paths)
        retain_parts = []
        if target.retain.hourly:
            retain_parts.append(f"{target.retain.hourly}h")
        if target.retain.daily:
            retain_parts.append(f"{target.retain.daily}d")
        if target.retain.weekly:
            retain_parts.append(f"{target.retain.weekly}w")
        if target.retain.monthly:
            retain_parts.append(f"{target.retain.monthly}m")
        retain_str = "/".join(retain_parts) if retain_parts else "default"

        resolved = resolve_paths(target, cfg.repo_root)
        exists = "ok" if resolved else "MISSING"
        print(fmt.format(name, paths_str, f"{retain_str}  [{exists}]"))
    return 0


def cmd_run(args) -> int:
    """Execute backup."""
    cfg = load_config()
    target = getattr(args, "target", None)

    hlog("backupctl", "info", "backup_started", {
        "target": target or "all",
    })

    results = engine.run_backup(cfg, target_name=target)

    any_failed = False
    for name, result in results.items():
        status = "ok" if result["success"] else "FAILED"
        print(f"  {name:<12} [{result['backend']}] {status}: {result['detail']}")
        if not result["success"]:
            any_failed = True

    if any_failed:
        return 1
    return 0


def cmd_list(args) -> int:
    """List available snapshots."""
    cfg = load_config()
    target = getattr(args, "target", None)

    snapshots = engine.list_snapshots(cfg, target_name=target)

    if getattr(args, "json_out", False):
        print(json.dumps(snapshots, indent=2))
        return 0

    if not snapshots:
        print("No snapshots found.")
        return 0

    fmt = "{:<20} {:<12} {:<10} {}"
    print(fmt.format("ID", "TARGET", "BACKEND", "TIME"))
    print("-" * 70)
    for s in snapshots:
        print(fmt.format(
            s["id"][:20],
            s["target"],
            s["backend"],
            s["time"][:22] if s["time"] else "?",
        ))
    return 0


def cmd_verify(args) -> int:
    """Verify backup repository integrity."""
    cfg = load_config()
    result = engine.verify_repository(cfg)

    status = "ok" if result["success"] else "FAILED"
    print(f"  [{result['backend']}] {status}: {result['detail']}")
    return 0 if result["success"] else 1


def cmd_restore(args) -> int:
    """Restore from a snapshot."""
    from pathlib import Path

    cfg = load_config()
    restore_to = Path(args.restore_to).resolve()

    hlog("backupctl", "info", "restore_started", {
        "target": args.target,
        "snapshot": args.snapshot,
        "restore_to": str(restore_to),
    })

    result = engine.restore_snapshot(
        cfg,
        target_name=args.target,
        snapshot_id=args.snapshot,
        restore_to=restore_to,
    )

    status = "ok" if result["success"] else "FAILED"
    print(f"  [{result['backend']}] {status}: {result['detail']}")
    return 0 if result["success"] else 1


def cmd_summary(args) -> int:
    """One-liner summary for briefing integration."""
    from .briefing import text_summary
    print(text_summary())
    return 0


if __name__ == "__main__":
    main()
