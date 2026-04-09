"""advisorctl CLI — agent-native interface to the advisor fleet.

Usage:
    hal advisor ask musashi "What does today's practice look like?"
    hal advisor ask karpathy "Review this" --stdin
    hal advisor ask draper --session pitch-v2 "Sharpen the hook"
    hal advisor query --advisor musashi --days 7
    hal advisor query --summary
    hal advisor audit --advisor draper --days 1
    hal advisor audit --all --auto-execute
    hal advisor list
    hal advisor forward musashi
"""

import argparse
import os
import subprocess
import sys

from .config import FLEET_ADVISORS, DEFAULT_PORT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="advisorctl",
        description="Agent-native CLI for the advisor fleet",
    )
    sub = parser.add_subparsers(dest="command")

    # --- ask ---
    ask_p = sub.add_parser("ask", help="Live query an advisor")
    ask_p.add_argument("advisor", choices=FLEET_ADVISORS, help="Advisor name")
    ask_p.add_argument("prompt", nargs="?", help="The prompt (or use --stdin)")
    ask_p.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    ask_p.add_argument("--session", help="Session ID for conversation continuity")
    ask_p.add_argument("--system", help="Ephemeral system prompt overlay")
    ask_p.add_argument("--no-stream", action="store_true", help="Disable streaming")
    ask_p.add_argument("--url", help="Override advisor API URL")
    ask_p.add_argument("--timeout", type=float, default=120.0, help="Request timeout (seconds)")

    # --- query ---
    query_p = sub.add_parser("query", help="Search historical advisor messages")
    query_p.add_argument("--advisor", choices=FLEET_ADVISORS, help="Filter to advisor")
    query_p.add_argument("--direction", choices=["inbound", "outbound"])
    query_p.add_argument("--days", type=int, default=1)
    query_p.add_argument("--limit", type=int, default=50)
    query_p.add_argument("--summary", action="store_true")
    query_p.add_argument("--json", action="store_true", dest="json_out")

    # --- audit ---
    audit_p = sub.add_parser("audit", help="LLM-as-judge policy enforcement")
    audit_p.add_argument("--advisor", choices=FLEET_ADVISORS, help="Audit one advisor")
    audit_p.add_argument("--all", action="store_true", help="Audit all advisors")
    audit_p.add_argument("--days", type=int, default=1)
    audit_p.add_argument("--limit", type=int, default=20)
    audit_p.add_argument("--auto-execute", action="store_true", help="Execute policy on violations")
    audit_p.add_argument("--json", action="store_true", dest="json_out")

    # --- list ---
    sub.add_parser("list", help="List fleet advisors")

    # --- forward ---
    fwd_p = sub.add_parser("forward", help="Port-forward to an advisor pod")
    fwd_p.add_argument("advisor", choices=FLEET_ADVISORS)
    fwd_p.add_argument("--local-port", type=int, default=DEFAULT_PORT)
    fwd_p.add_argument("--namespace", default="halo-fleet")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "ask":
        return _cmd_ask(args)
    elif args.command == "query":
        return _cmd_query(args)
    elif args.command == "audit":
        return _cmd_audit(args)
    elif args.command == "list":
        return _cmd_list()
    elif args.command == "forward":
        return _cmd_forward(args)

    return 0


def _cmd_ask(args) -> int:
    from .ask import ask

    prompt = args.prompt
    if args.stdin or not prompt:
        stdin_data = sys.stdin.read().strip()
        if prompt:
            prompt = f"{prompt}\n\n{stdin_data}"
        else:
            prompt = stdin_data

    if not prompt:
        print("ERROR: no prompt provided", file=sys.stderr)
        return 1

    try:
        ask(
            args.advisor,
            prompt,
            url_override=args.url,
            session_id=args.session,
            system=args.system,
            stream=not args.no_stream,
            timeout=args.timeout,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    return 0


def _cmd_query(args) -> int:
    from .query import list_messages, summary, print_messages, print_summary

    if args.summary:
        rows = summary(advisor=args.advisor, days=args.days)
        print_summary(rows, json_out=args.json_out)
    else:
        messages = list_messages(
            advisor=args.advisor,
            direction=args.direction,
            days=args.days,
            limit=args.limit,
        )
        print_messages(messages, json_out=args.json_out)
    return 0


def _cmd_audit(args) -> int:
    from .audit import audit, print_report

    if not args.advisor and not args.all:
        print("ERROR: specify --advisor <name> or --all", file=sys.stderr)
        return 1

    reports = audit(
        advisor=args.advisor,
        days=args.days,
        limit=args.limit,
        auto_execute=args.auto_execute,
        json_out=args.json_out,
    )
    print_report(reports, json_out=args.json_out)
    return 0


def _cmd_list() -> int:
    print(f"{'ADVISOR':<16} {'DOMAIN'}")
    print("-" * 30)
    # Domain mapping from fleet labels
    domains = {
        "bankei": "rest",
        "draper": "pitch",
        "gibson": "futures",
        "hightower": "heavy-iron",
        "karpathy": "craft",
        "machiavelli": "power",
        "medici": "money",
        "musashi": "body",
    }
    for adv in FLEET_ADVISORS:
        print(f"{adv:<16} {domains.get(adv, '?')}")
    return 0


def _cmd_forward(args) -> int:
    """Start kubectl port-forward to the advisor pod."""
    label = f"app.kubernetes.io/name=advisor-{args.advisor}"
    cmd = [
        "kubectl", "port-forward",
        "-n", args.namespace,
        f"deployment/advisor-{args.advisor}",
        f"{args.local_port}:{DEFAULT_PORT}",
    ]
    print(f"Forwarding localhost:{args.local_port} -> advisor-{args.advisor}:{DEFAULT_PORT}")
    print(f"  {' '.join(cmd)}")
    try:
        os.execvp("kubectl", cmd)
    except FileNotFoundError:
        print("ERROR: kubectl not found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
