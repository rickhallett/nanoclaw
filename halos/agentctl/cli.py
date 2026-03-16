"""agentctl CLI — agent session tracking and alerts."""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import config as cfgmod
from .alerts import check_alerts, load_sessions
from .ingest import ingest
from .session import Session


def main():
    parser = argparse.ArgumentParser(
        prog="agentctl",
        description="LLM agent session tracking and spinning-to-infinity detection",
    )
    parser.add_argument("--config", default="", help="config file (default: ./agentctl.yaml)")
    parser.add_argument("--json", action="store_true", dest="json_out", help="output as JSON")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command")

    # --- ingest ---
    sub.add_parser("ingest", help="parse container logs into session records")

    # --- list ---
    p_list = sub.add_parser("list", help="list recent sessions")
    p_list.add_argument("--group", default="", help="filter by group")
    p_list.add_argument("--status", default="", help="filter by status")
    p_list.add_argument("--limit", type=int, default=20)

    # --- stats ---
    p_stats = sub.add_parser("stats", help="session statistics summary")
    p_stats.add_argument("--since", default="", help="time window (e.g. 24h, 7d)")

    # --- alert ---
    sub.add_parser("alert", help="check for spinning-to-infinity and error streaks")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    cfg = cfgmod.load(args.config)

    commands = {
        "ingest": cmd_ingest,
        "list": cmd_list,
        "stats": cmd_stats,
        "alert": cmd_alert,
    }
    commands[args.command](cfg, args)


def cmd_ingest(cfg, args):
    ingested, skipped, errors = ingest(cfg, verbose=args.verbose)

    if args.json_out:
        json.dump({"ingested": ingested, "skipped": skipped, "errors": errors}, sys.stdout, indent=2)
        print()
    else:
        print(f"Ingested: {ingested}")
        print(f"Skipped:  {skipped} (already exist)")
        print(f"Errors:   {errors} (unparseable logs)")


def cmd_list(cfg, args):
    sessions = load_sessions(cfg.sessions_dir)

    # Filter
    if args.group:
        sessions = [s for s in sessions if s.group == args.group]
    if args.status:
        sessions = [s for s in sessions if s.status == args.status]

    # Sort by most recent first
    sessions.sort(key=lambda s: s.started, reverse=True)
    sessions = sessions[:args.limit]

    if args.json_out:
        import yaml
        json.dump([yaml.safe_load(s.__dict__.__repr__()) if False else {
            "id": s.id, "group": s.group, "started": s.started,
            "duration_secs": s.duration_secs, "status": s.status,
            "exit_code": s.exit_code,
        } for s in sessions], sys.stdout, indent=2)
        print()
    else:
        if not sessions:
            print("No sessions found.")
            return
        # Table header
        print(f"{'STATUS':<10} {'DURATION':>8} {'GROUP':<25} {'STARTED':<25} {'ID'}")
        print("-" * 100)
        for s in sessions:
            dur = f"{s.duration_secs}s"
            started = s.started[:19] if len(s.started) > 19 else s.started
            print(f"{s.status:<10} {dur:>8} {s.group:<25} {started:<25} {s.id}")


def _parse_since(since: str) -> datetime:
    """Parse a relative time string like '24h' or '7d' into a datetime."""
    now = datetime.now(timezone.utc)
    if not since:
        return datetime.min.replace(tzinfo=timezone.utc)

    m = None
    import re
    m = re.match(r"^(\d+)([hdwm])$", since)
    if not m:
        raise ValueError(f"invalid --since format: {since} (use e.g. 24h, 7d)")

    val = int(m.group(1))
    unit = m.group(2)
    if unit == "h":
        return now - timedelta(hours=val)
    elif unit == "d":
        return now - timedelta(days=val)
    elif unit == "w":
        return now - timedelta(weeks=val)
    elif unit == "m":
        return now - timedelta(days=val * 30)
    return now


def cmd_stats(cfg, args):
    sessions = load_sessions(cfg.sessions_dir)

    # Time filter
    if args.since:
        cutoff = _parse_since(args.since)
        sessions = [s for s in sessions if _parse_dt(s.started) >= cutoff]

    if not sessions:
        print("No sessions found.")
        return

    total = len(sessions)
    success = sum(1 for s in sessions if s.status == "success")
    errors = sum(1 for s in sessions if s.status == "error")
    timeouts = sum(1 for s in sessions if s.status == "timeout")
    success_rate = (success / total * 100) if total else 0

    durations = [s.duration_secs for s in sessions]
    avg_duration = sum(durations) / len(durations) if durations else 0
    total_duration = sum(durations)

    # By group
    by_group: dict[str, list[Session]] = defaultdict(list)
    for s in sessions:
        by_group[s.group].append(s)

    if args.json_out:
        group_stats = {}
        for g, gs in sorted(by_group.items()):
            g_dur = sum(s.duration_secs for s in gs)
            group_stats[g] = {
                "count": len(gs),
                "total_duration_secs": g_dur,
                "success": sum(1 for s in gs if s.status == "success"),
                "errors": sum(1 for s in gs if s.status == "error"),
            }
        json.dump({
            "total": total, "success": success, "errors": errors, "timeouts": timeouts,
            "success_rate": round(success_rate, 1),
            "avg_duration_secs": round(avg_duration),
            "total_duration_secs": total_duration,
            "by_group": group_stats,
        }, sys.stdout, indent=2)
        print()
    else:
        print(f"Total sessions:   {total}")
        print(f"Success:          {success} ({success_rate:.1f}%)")
        print(f"Errors:           {errors}")
        print(f"Timeouts:         {timeouts}")
        print(f"Avg duration:     {avg_duration:.0f}s")
        print(f"Total duration:   {total_duration}s ({total_duration // 3600}h {(total_duration % 3600) // 60}m)")
        print()
        print("By group:")
        for g, gs in sorted(by_group.items()):
            g_dur = sum(s.duration_secs for s in gs)
            g_succ = sum(1 for s in gs if s.status == "success")
            print(f"  {g:<25} {len(gs):>4} sessions  {g_dur:>6}s  {g_succ}/{len(gs)} ok")


def _parse_dt(s: str) -> datetime:
    """Parse an ISO datetime string."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def cmd_alert(cfg, args):
    warnings = check_alerts(cfg)

    if args.json_out:
        json.dump({"alerts": warnings, "count": len(warnings)}, sys.stdout, indent=2)
        print()
    else:
        if not warnings:
            print("No alerts. All clear.")
        else:
            for w in warnings:
                print(f"  WARNING: {w}")
            print(f"\n{len(warnings)} alert(s) found.")


if __name__ == "__main__":
    main()
