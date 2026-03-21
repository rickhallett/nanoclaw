"""mailctl CLI — Gmail operations, inbox triage, and filter management.

Usage:
    mailctl inbox [--unread] [--json]     Inbox snapshot
    mailctl read <id>                     Read a message
    mailctl search <query>                Search messages (IMAP syntax)
    mailctl triage [--dry-run]            Run triage rules on unread inbox
    mailctl send --to X --subject Y       Send (body from stdin)
    mailctl folders                       List Gmail folders/labels
    mailctl filters                       List managed Gmail filters
    mailctl actions [--limit N]           Show recent action log
    mailctl summary                       One-line summary for briefings
"""

import argparse
import json
import sys

from . import store


# --- Existing commands ---


def cmd_filters(args: argparse.Namespace) -> int:
    """List all managed filters."""
    filters = store.list_filters()
    if not filters:
        print("No managed filters.")
        return 0
    for f in filters:
        reason = f.get("reason") or ""
        print(f"  {f['sender']:<45} {f['gmail_filter_id'][:20]}...  {reason}")
    print(f"\n{len(filters)} filter(s) managed by mailctl")
    return 0


def cmd_actions(args: argparse.Namespace) -> int:
    """Show recent action log."""
    actions = store.list_actions(limit=args.limit)
    if not actions:
        print("No actions recorded.")
        return 0
    for a in actions:
        sender = a.get("sender") or ""
        details = a.get("details") or ""
        print(f"  {a['timestamp'][:19]}  {a['action']:<20} {sender:<35} {details}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """One-line summary for briefing integration."""
    from .briefing import text_summary

    print(text_summary())
    return 0


# --- New himalaya-backed commands ---


def cmd_inbox(args: argparse.Namespace) -> int:
    """Inbox snapshot."""
    from . import engine

    messages = engine.list_messages(folder="INBOX", page_size=50)
    if args.unread:
        messages = [m for m in messages if "Seen" not in m.get("flags", [])]

    if args.json:
        print(json.dumps(messages, indent=2))
        return 0

    if not messages:
        print("Inbox empty." if not args.unread else "No unread messages.")
        return 0

    for m in messages:
        seen = " " if "Seen" in m.get("flags", []) else "*"
        sender = m.get("from", {}).get("name") or m.get("from", {}).get("addr", "?")
        subject = m.get("subject", "(no subject)")
        date = m.get("date", "")[:16]
        print(f"  {seen} {m.get('id', '?'):<8} {date}  {sender:<25} {subject:.60}")

    print(f"\n{len(messages)} message(s)")
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    """Read a message."""
    from . import engine

    msg = engine.read_message(args.message_id)
    if isinstance(msg, dict):
        print(json.dumps(msg, indent=2) if args.json else msg.get("body", ""))
    else:
        print(msg)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search messages."""
    from . import engine

    results = engine.search(args.query)
    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    if not results:
        print("No results.")
        return 0

    for m in results:
        sender = m.get("from", {}).get("name") or m.get("from", {}).get("addr", "?")
        subject = m.get("subject", "(no subject)")
        print(f"  {m.get('id', '?'):<8} {sender:<25} {subject:.60}")

    print(f"\n{len(results)} result(s)")
    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    """Run triage rules on unread inbox."""
    from . import engine
    from .triage import run_triage

    messages = engine.list_messages(folder="INBOX", page_size=100)
    unread = [m for m in messages if not m.get("flags", {}).get("seen", False)]

    if not unread:
        print("No unread messages to triage.")
        return 0

    results = run_triage(unread, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for r in results:
        action = r["action"].upper()
        print(f"  [{action:<8}] {r['from']:<30} {r['subject']:.50}")
        print(f"             {r['reason']}")

    label = "DRY RUN — " if args.dry_run else ""
    print(f"\n{label}{len(results)} message(s) triaged")
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    """Send a message (body from stdin)."""
    from . import engine

    body = sys.stdin.read()
    engine.send(to=args.to, subject=args.subject, body=body, cc=args.cc)
    print(f"Sent to {args.to}")
    return 0


def cmd_folders(args: argparse.Namespace) -> int:
    """List folders/labels."""
    from . import engine

    folder_list = engine.folders()
    if args.json:
        print(json.dumps(folder_list, indent=2))
        return 0

    for f in folder_list:
        name = f.get("name", "?") if isinstance(f, dict) else str(f)
        print(f"  {name}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mailctl",
        description="Gmail operations, inbox triage, and filter management",
    )
    sub = parser.add_subparsers(dest="command")

    # inbox
    inbox_p = sub.add_parser("inbox", help="Inbox snapshot")
    inbox_p.add_argument("--unread", action="store_true", help="Unread only")
    inbox_p.add_argument("--json", action="store_true", help="JSON output")

    # read
    read_p = sub.add_parser("read", help="Read a message")
    read_p.add_argument("message_id", help="Message ID")
    read_p.add_argument("--json", action="store_true", help="JSON output")

    # search
    search_p = sub.add_parser("search", help="Search messages")
    search_p.add_argument("query", help="Search query (IMAP syntax)")
    search_p.add_argument("--json", action="store_true", help="JSON output")

    # triage
    triage_p = sub.add_parser("triage", help="Run triage rules on unread inbox")
    triage_p.add_argument("--dry-run", action="store_true", default=True,
                          help="Preview without executing (default)")
    triage_p.add_argument("--execute", action="store_true", help="Execute triage actions")
    triage_p.add_argument("--json", action="store_true", help="JSON output")

    # send
    send_p = sub.add_parser("send", help="Send a message (body from stdin)")
    send_p.add_argument("--to", required=True, help="Recipient address")
    send_p.add_argument("--subject", required=True, help="Subject line")
    send_p.add_argument("--cc", default=None, help="CC address")

    # folders
    folders_p = sub.add_parser("folders", help="List Gmail folders/labels")
    folders_p.add_argument("--json", action="store_true", help="JSON output")

    # existing
    sub.add_parser("filters", help="List managed Gmail filters")

    actions_p = sub.add_parser("actions", help="Show recent action log")
    actions_p.add_argument("--limit", type=int, default=50, help="Max actions to show")

    sub.add_parser("summary", help="One-line briefing summary")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "inbox": cmd_inbox,
        "read": cmd_read,
        "search": cmd_search,
        "triage": cmd_triage,
        "send": cmd_send,
        "folders": cmd_folders,
        "filters": cmd_filters,
        "actions": cmd_actions,
        "summary": cmd_summary,
    }
    sys.exit(dispatch[args.command](args) or 0)
