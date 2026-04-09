"""trackctl CLI — personal metrics tracker.

Usage:
    trackctl domains                           # list registered domains
    trackctl add zazen --duration 25           # log a sit
    trackctl add zazen --duration 120 --notes "morning sit, deep release"
    trackctl list zazen --days 7               # recent entries
    trackctl streak zazen                      # streak stats
    trackctl summary                           # all domains
    trackctl summary --domain zazen --json     # one domain, JSON
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from . import registry
from . import store
from . import engine
from halos.common.log import hlog
from halos.eventsource.publish import fire_event


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="trackctl",
        description="trackctl — personal metrics tracker",
    )
    sub = parser.add_subparsers(dest="command")

    # --- domains ---
    sub.add_parser("domains", help="List registered tracker domains")

    # --- add ---
    p_add = sub.add_parser("add", help="Log a new entry")
    p_add.add_argument("domain", help="Domain name (e.g. zazen)")
    p_add.add_argument("--duration", type=int, required=True, dest="duration_mins",
                        help="Duration in minutes")
    p_add.add_argument("--notes", default="", help="Optional notes")
    p_add.add_argument("--time", default=None, dest="entry_time",
                        help="Override time as HH:MM (today, UTC). Default: now.")
    p_add.add_argument("--date", default=None, dest="entry_date",
                        help="Override date as YYYY-MM-DD. Combines with --time.")
    p_add.add_argument("--json", action="store_true", dest="json_out")

    # --- list ---
    p_list = sub.add_parser("list", help="List entries for a domain")
    p_list.add_argument("domain", help="Domain name")
    p_list.add_argument("--days", type=int, default=None,
                         help="Limit to last N days")
    p_list.add_argument("--json", action="store_true", dest="json_out")

    # --- edit ---
    p_edit = sub.add_parser("edit", help="Edit an existing entry")
    p_edit.add_argument("domain", help="Domain name")
    p_edit.add_argument("id", type=int, help="Entry ID")
    p_edit.add_argument("--duration", type=int, default=None, dest="duration_mins")
    p_edit.add_argument("--notes", default=None)
    p_edit.add_argument("--json", action="store_true", dest="json_out")

    # --- delete ---
    p_del = sub.add_parser("delete", help="Delete an entry")
    p_del.add_argument("domain", help="Domain name")
    p_del.add_argument("id", type=int, help="Entry ID")

    # --- streak ---
    p_streak = sub.add_parser("streak", help="Show streak stats for a domain")
    p_streak.add_argument("domain", help="Domain name")
    p_streak.add_argument("--json", action="store_true", dest="json_out")

    # --- summary ---
    p_summary = sub.add_parser("summary", help="Summary stats (all domains or one)")
    p_summary.add_argument("--domain", default=None, help="Limit to one domain")
    p_summary.add_argument("--json", action="store_true", dest="json_out")

    # --- export ---
    p_export = sub.add_parser("export", help="Full JSON export of a domain")
    p_export.add_argument("domain", help="Domain name")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Load all domain registrations
    registry.load_all()

    dispatch = {
        "domains": cmd_domains,
        "add": cmd_add,
        "list": cmd_list,
        "edit": cmd_edit,
        "delete": cmd_delete,
        "streak": cmd_streak,
        "summary": cmd_summary,
        "export": cmd_export,
    }
    sys.exit(dispatch[args.command](args) or 0)


def _require_domain(name: str) -> registry.DomainInfo:
    """Validate that a domain is registered. Exit with error if not."""
    info = registry.get(name)
    if not info:
        known = [d.name for d in registry.all_domains()]
        print(
            f"ERROR: unknown domain '{name}'. "
            f"Registered domains: {', '.join(known) if known else '(none)'}",
            file=sys.stderr,
        )
        sys.exit(1)
    return info


def cmd_domains(args) -> int:
    """List all registered domains."""
    domains = registry.all_domains()
    if not domains:
        print("No domains registered.")
        return 0

    for d in domains:
        target_str = f"  (target: {d.target} days)" if d.target else ""
        print(f"  {d.name:<16} {d.description}{target_str}")
    return 0


def cmd_add(args) -> int:
    """Log a new entry."""
    info = _require_domain(args.domain)

    # Build timestamp
    ts = None
    if args.entry_date or args.entry_time:
        date_str = args.entry_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        time_str = args.entry_time or "00:00"
        try:
            ts = f"{date_str}T{time_str}:00Z"
            # Validate by parsing
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            print(
                f"ERROR: invalid date/time. Use --date YYYY-MM-DD and --time HH:MM.",
                file=sys.stderr,
            )
            return 1

    entry = store.add_entry(
        domain=args.domain,
        duration_mins=args.duration_mins,
        notes=args.notes,
        timestamp=ts,
    )

    hlog("trackctl", "info", "entry_added", {
        "domain": args.domain,
        "id": entry["id"],
        "duration_mins": args.duration_mins,
    })

    # Publish to NATS for cross-pod visibility
    _domain_event_type = {
        "movement": "track.movement.logged",
        "zazen": "track.zazen.logged",
    }
    fire_event(
        _domain_event_type.get(args.domain, f"track.{args.domain}.logged"),
        {
            "domain": args.domain,
            "entry_id": entry["id"],
            "duration_mins": args.duration_mins,
            "notes": args.notes,
        },
    )

    if getattr(args, "json_out", False):
        print(json.dumps(entry, indent=2))
    else:
        print(f"logged  {args.domain}  {args.duration_mins}min  id={entry['id']}")

    return 0


def cmd_list(args) -> int:
    """List entries for a domain."""
    _require_domain(args.domain)
    entries = store.list_entries(args.domain, days=args.days)

    if args.json_out:
        print(json.dumps(entries, indent=2))
    else:
        if not entries:
            print(f"No entries for {args.domain}.")
            return 0

        fmt = "{:<6} {:<22} {:>8}  {}"
        print(fmt.format("ID", "TIMESTAMP", "MINS", "NOTES"))
        print("-" * 70)
        for e in entries:
            notes = (e["notes"] or "")[:30]
            print(fmt.format(e["id"], e["timestamp"], e["duration_mins"], notes))
    return 0


def cmd_edit(args) -> int:
    """Edit an existing entry."""
    _require_domain(args.domain)
    updated = store.edit_entry(
        domain=args.domain,
        entry_id=args.id,
        duration_mins=args.duration_mins,
        notes=args.notes,
    )
    if not updated:
        print(f"ERROR: entry {args.id} not found in {args.domain}", file=sys.stderr)
        return 1

    hlog("trackctl", "info", "entry_edited", {
        "domain": args.domain, "id": args.id,
    })

    fire_event("track.entry.edited", {
        "domain": args.domain,
        "entry_id": args.id,
        "duration_mins": updated["duration_mins"],
        "notes": updated["notes"],
    })

    if getattr(args, "json_out", False):
        print(json.dumps(updated, indent=2))
    else:
        print(f"edited  {args.domain}  id={args.id}")
    return 0


def cmd_delete(args) -> int:
    """Delete an entry."""
    _require_domain(args.domain)
    deleted = store.delete_entry(args.domain, args.id)
    if not deleted:
        print(f"ERROR: entry {args.id} not found in {args.domain}", file=sys.stderr)
        return 1

    hlog("trackctl", "info", "entry_deleted", {
        "domain": args.domain, "id": args.id,
    })

    fire_event("track.entry.deleted", {
        "domain": args.domain,
        "entry_id": args.id,
    })

    print(f"deleted  {args.domain}  id={args.id}")
    return 0


def cmd_streak(args) -> int:
    """Show streak stats."""
    info = _require_domain(args.domain)
    streak = engine.compute_streak(args.domain)

    if args.json_out:
        data = streak.copy()
        if info.target:
            data["target"] = info.target
            data["target_remaining"] = max(0, info.target - streak["current_streak"])
        print(json.dumps(data, indent=2))
    else:
        print(f"Domain:          {args.domain}")
        print(f"Current streak:  {streak['current_streak']} days")
        print(f"Longest streak:  {streak['longest_streak']} days")
        if streak["last_entry_date"]:
            print(f"Last entry:      {streak['last_entry_date']}")
        if info.target:
            remaining = max(0, info.target - streak["current_streak"])
            if remaining > 0:
                print(f"Target:          {info.target} days ({remaining} to go)")
            else:
                print(f"Target:          {info.target} days (reached)")
    return 0


def cmd_summary(args) -> int:
    """Summary stats for all domains or one."""
    if args.domain:
        info = _require_domain(args.domain)
        summaries = [engine.compute_summary(args.domain, target=info.target)]
    else:
        summaries = []
        for d in registry.all_domains():
            summaries.append(engine.compute_summary(d.name, target=d.target))

    if args.json_out:
        print(json.dumps(summaries if len(summaries) != 1 else summaries[0], indent=2))
    else:
        if not summaries:
            print("No domains registered.")
            return 0
        for s in summaries:
            info = registry.get(s["domain"])
            target = info.target if info else None
            print(engine.text_summary(s["domain"], target=target))
    return 0


def cmd_export(args) -> int:
    """Full JSON export of a domain's data."""
    info = _require_domain(args.domain)
    entries = store.list_entries(args.domain)
    summary = engine.compute_summary(args.domain, target=info.target)

    export = {
        "domain": args.domain,
        "description": info.description,
        "target": info.target,
        "summary": summary,
        "entries": entries,
    }
    print(json.dumps(export, indent=2))
    return 0


if __name__ == "__main__":
    main()
