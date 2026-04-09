"""drillctl CLI — spaced repetition for Python stdlib mastery.

Usage:
    drillctl today                        # what's due
    drillctl run                          # interactive drill session
    drillctl review <slug> --pass/--fail  # log a single review
    drillctl log <day> --hit a,b --miss c # batch log from curriculum session
    drillctl cards                        # list all cards
    drillctl stats                        # overall statistics
    drillctl load <file>                  # bulk load cards from YAML/JSON
    drillctl add <slug> --domain d --prompt p --answer a
"""

import argparse
import json
import sys

from . import store
from halos.common.log import hlog


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="drillctl",
        description="drillctl — spaced repetition for Python stdlib mastery",
    )
    sub = parser.add_subparsers(dest="command")

    # --- today ---
    p_today = sub.add_parser("today", help="Show cards due for review")
    p_today.add_argument("--json", action="store_true", dest="json_out")
    p_today.add_argument("--new", action="store_true", help="Include unseen cards")
    p_today.add_argument("--domain", default=None, help="Filter by domain")

    # --- run ---
    p_run = sub.add_parser("run", help="Interactive drill session")
    p_run.add_argument("--limit", type=int, default=None, help="Max cards to drill")
    p_run.add_argument("--domain", default=None, help="Filter by domain")
    p_run.add_argument("--new", action="store_true", help="Include unseen cards")

    # --- review ---
    p_review = sub.add_parser("review", help="Log a single card review")
    p_review.add_argument("slug", help="Card slug")
    grp = p_review.add_mutually_exclusive_group(required=True)
    grp.add_argument("--pass", action="store_true", dest="passed")
    grp.add_argument("--fail", action="store_true", dest="failed")

    # --- log ---
    p_log = sub.add_parser("log", help="Batch log from a curriculum session")
    p_log.add_argument("session", help="Session name (e.g. day01)")
    p_log.add_argument("--hit", default="", help="Comma-separated slugs you got right")
    p_log.add_argument("--miss", default="", help="Comma-separated slugs you got wrong")

    # --- cards ---
    p_cards = sub.add_parser("cards", help="List all cards")
    p_cards.add_argument("--domain", default=None, help="Filter by domain")
    p_cards.add_argument("--json", action="store_true", dest="json_out")

    # --- add ---
    p_add = sub.add_parser("add", help="Add a single card")
    p_add.add_argument("slug", help="Unique slug (e.g. defaultdict_factory)")
    p_add.add_argument("--domain", default="python", help="Domain/category")
    p_add.add_argument("--prompt", default="", help="The question")
    p_add.add_argument("--answer", default="", help="The answer")

    # --- remove ---
    p_rm = sub.add_parser("remove", help="Remove a card")
    p_rm.add_argument("slug", help="Card slug")

    # --- stats ---
    p_stats = sub.add_parser("stats", help="Overall drill statistics")
    p_stats.add_argument("--json", action="store_true", dest="json_out")

    # --- load ---
    p_load = sub.add_parser("load", help="Bulk load cards from a JSON file")
    p_load.add_argument("file", help="Path to JSON file with card definitions")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "today": cmd_today,
        "run": cmd_run,
        "review": cmd_review,
        "log": cmd_log,
        "cards": cmd_cards,
        "add": cmd_add,
        "remove": cmd_remove,
        "stats": cmd_stats,
        "load": cmd_load,
    }
    sys.exit(dispatch[args.command](args) or 0)


def cmd_today(args) -> int:
    due = store.due_cards(include_new=args.new)
    if args.domain:
        due = [c for c in due if c.get("domain") == args.domain]
    if args.json_out:
        print(json.dumps(due, indent=2))
        return 0

    if not due:
        print("Nothing due today. All caught up.")
        return 0

    print(f"DUE ({len(due)} cards):\n")
    for s in due:
        if s["last_review"] is None:
            status = "NEW"
            detail = ""
        else:
            ago = _time_ago(s["last_review"])
            status = f"streak={s['streak']}"
            detail = f"last: {ago}, interval: {s['interval_days']:.0f}d"
        print(f"  {s['slug']:<40} [{status}] {detail}")
        if s.get("prompt"):
            print(f"    {s['prompt'][:70]}")
        print()

    print(f"Run: drillctl run")
    return 0


def cmd_run(args) -> int:
    due = store.due_cards(include_new=args.new)
    if args.domain:
        due = [c for c in due if c.get("domain") == args.domain]
    if args.limit:
        due = due[:args.limit]

    if not due:
        print("Nothing due. All caught up.")
        return 0

    print(f"Drilling {len(due)} cards. Type 'p' for pass, 'f' for fail, 'q' to quit.\n")

    reviewed = 0
    for i, card in enumerate(due, 1):
        print(f"── [{i}/{len(due)}] {card['slug']} ──")
        if card.get("prompt"):
            print(f"\n  {card['prompt']}\n")
        else:
            print(f"\n  (no prompt — review this concept)\n")

        # Wait for user to think
        try:
            inp = input("  Ready to see answer? [enter] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if inp.lower() == 'q':
            print("Session ended.")
            break

        if card.get("answer"):
            print(f"\n  ANSWER: {card['answer']}\n")

        while True:
            try:
                result = input("  (p)ass / (f)ail / (q)uit? ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nSession ended.")
                return 0

            if result in ('p', 'pass'):
                state = store.log_review(card["slug"], passed=True)
                print(f"  ✓ Next review in {state['interval_days']:.0f} days\n")
                reviewed += 1
                break
            elif result in ('f', 'fail'):
                state = store.log_review(card["slug"], passed=False)
                print(f"  ✗ Review again tomorrow\n")
                reviewed += 1
                break
            elif result in ('q', 'quit'):
                print("Session ended.")
                return 0
            else:
                print("  Type 'p', 'f', or 'q'")

    print(f"\nReviewed {reviewed} cards.")
    st = store.stats()
    print(f"Pass rate: {st['pass_rate']}% | Due: {st['due_today']} | Graduated: {st['graduated']}")
    return 0


def cmd_review(args) -> int:
    state = store.get_card_state(args.slug)
    if not state:
        print(f"Card not found: {args.slug}", file=sys.stderr)
        return 1

    passed = args.passed
    result = store.log_review(args.slug, passed=passed)

    hlog("drillctl", "info", "review", {
        "slug": args.slug,
        "result": result["result"],
        "interval": result["interval_days"],
        "streak": result["streak"],
    })

    label = "pass" if passed else "fail"
    print(f"{args.slug}: {label} → interval={result['interval_days']:.0f}d, streak={result['streak']}, next={result['next_due']}")
    return 0


def cmd_log(args) -> int:
    hits = [s.strip() for s in args.hit.split(",") if s.strip()]
    misses = [s.strip() for s in args.miss.split(",") if s.strip()]

    for slug in hits:
        # Ensure card exists
        if not store.get_card_state(slug):
            store.add_card(slug, domain="python")
        result = store.log_review(slug, passed=True)
        print(f"  pass: {slug} → interval={result['interval_days']:.0f}d")

    for slug in misses:
        if not store.get_card_state(slug):
            store.add_card(slug, domain="python")
        result = store.log_review(slug, passed=False)
        print(f"  fail: {slug} → review tomorrow")

    hlog("drillctl", "info", "batch_log", {
        "session": args.session,
        "hits": len(hits),
        "misses": len(misses),
    })

    total = len(hits) + len(misses)
    print(f"\nLogged {total} reviews from {args.session} ({len(hits)} pass, {len(misses)} fail)")
    return 0


def cmd_cards(args) -> int:
    cards = store.list_cards(domain=args.domain)

    if args.json_out:
        print(json.dumps(cards, indent=2))
        return 0

    if not cards:
        print("No cards. Load some with: drillctl load <file>")
        return 0

    for c in cards:
        state = store.get_card_state(c["slug"])
        if state and state["last_review"]:
            info = f"streak={state['streak']}, interval={state['interval_days']:.0f}d"
            if state["graduated"]:
                info += " [GRADUATED]"
        else:
            info = "NEW"
        print(f"  {c['slug']:<40} [{c['domain']}] {info}")
    print(f"\n{len(cards)} cards total.")
    return 0


def cmd_add(args) -> int:
    card = store.add_card(
        slug=args.slug,
        domain=args.domain,
        prompt=args.prompt,
        answer=args.answer,
    )
    print(f"Added: {card['slug']} [{card['domain']}]")
    return 0


def cmd_remove(args) -> int:
    if store.remove_card(args.slug):
        print(f"Removed: {args.slug}")
    else:
        print(f"Not found: {args.slug}", file=sys.stderr)
        return 1
    return 0


def cmd_stats(args) -> int:
    st = store.stats()
    if args.json_out:
        print(json.dumps(st, indent=2))
        return 0

    print(f"Cards:      {st['total_cards']}")
    print(f"Reviews:    {st['total_reviews']} ({st['passes']} pass, {st['fails']} fail)")
    print(f"Pass rate:  {st['pass_rate']}%")
    print(f"Graduated:  {st['graduated']}")
    print(f"Due today:  {st['due_today']}")
    print(f"New/unseen: {st['new_unseen']}")
    return 0


def cmd_load(args) -> int:
    from pathlib import Path
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    data = json.loads(path.read_text())
    if isinstance(data, dict):
        cards = data.get("cards", [])
    elif isinstance(data, list):
        cards = data
    else:
        print("Expected a JSON list or object with 'cards' key.", file=sys.stderr)
        return 1

    loaded = 0
    for c in cards:
        store.add_card(
            slug=c["slug"],
            domain=c.get("domain", "python"),
            prompt=c.get("prompt", ""),
            answer=c.get("answer", ""),
        )
        loaded += 1

    print(f"Loaded {loaded} cards from {path.name}")
    return 0


def _time_ago(ts_str: str) -> str:
    from datetime import datetime, timezone
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return ts_str
    diff = datetime.now(timezone.utc) - ts
    days = diff.days
    if days == 0:
        hours = diff.seconds // 3600
        return f"{hours}h ago" if hours else "just now"
    return f"{days}d ago"


if __name__ == "__main__":
    main()
