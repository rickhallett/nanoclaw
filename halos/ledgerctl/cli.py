"""ledgerctl CLI — plain-text personal accounting.

Usage:
    ledgerctl add --account expenses:food --amount 42.50 --payee "Countdown"
    ledgerctl import --bank anz --csv statement.csv [--dry-run]
    ledgerctl balance [--period monthly] [--json]
    ledgerctl income [--period monthly] [--json]
    ledgerctl cashflow [--period monthly]
    ledgerctl categories
    ledgerctl search --payee "Countdown"
    ledgerctl summary
    ledgerctl rules list
    ledgerctl rules add --pattern "COUNTDOWN" --account expenses:food
"""

import argparse
import json
import sys
from datetime import date, datetime

from halos.common.log import hlog

from . import journal as jmod
from . import importer
from . import reports
from . import rules as rmod
from . import briefing


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ledgerctl",
        description="ledgerctl — plain-text personal accounting",
    )
    sub = parser.add_subparsers(dest="command")

    # --- add ---
    p_add = sub.add_parser("add", help="Add a journal entry")
    p_add.add_argument("--account", required=True, help="Target account (e.g. expenses:food)")
    p_add.add_argument("--amount", type=float, required=True, help="Amount (positive)")
    p_add.add_argument("--payee", required=True, help="Payee/description")
    p_add.add_argument("--date", default=None, dest="entry_date",
                        help="Entry date (YYYY-MM-DD). Default: today.")
    p_add.add_argument("--from", default=None, dest="from_account",
                        help="Source account. Default: inferred from account type.")
    p_add.add_argument("--currency", default="$", help="Currency symbol. Default: $")
    p_add.add_argument("--comment", default="", help="Optional comment")

    # --- import ---
    p_import = sub.add_parser("import", help="Import bank CSV")
    p_import.add_argument("--bank", required=True, help="Bank name (e.g. anz, wise)")
    p_import.add_argument("--csv", required=True, dest="csv_path", help="Path to CSV file")
    p_import.add_argument("--dry-run", action="store_true", dest="dry_run",
                           help="Preview entries without writing")
    p_import.add_argument("--currency", default="$", help="Currency symbol. Default: $")

    # --- balance ---
    p_balance = sub.add_parser("balance", help="Balance report")
    p_balance.add_argument("--period", default=None,
                            choices=["daily", "weekly", "monthly", "yearly"],
                            help="Filter period")
    p_balance.add_argument("--json", action="store_true", dest="json_out")

    # --- income ---
    p_income = sub.add_parser("income", help="Income report")
    p_income.add_argument("--period", default=None,
                           choices=["daily", "weekly", "monthly", "yearly"])
    p_income.add_argument("--json", action="store_true", dest="json_out")

    # --- cashflow ---
    p_cashflow = sub.add_parser("cashflow", help="Cashflow report (income - expenses)")
    p_cashflow.add_argument("--period", default=None,
                             choices=["daily", "weekly", "monthly", "yearly"])
    p_cashflow.add_argument("--json", action="store_true", dest="json_out")

    # --- categories ---
    p_cats = sub.add_parser("categories", help="List expense categories with totals")
    p_cats.add_argument("--period", default=None,
                         choices=["daily", "weekly", "monthly", "yearly"])
    p_cats.add_argument("--json", action="store_true", dest="json_out")

    # --- search ---
    p_search = sub.add_parser("search", help="Search transactions by payee")
    p_search.add_argument("--payee", required=True, help="Payee pattern (regex)")
    p_search.add_argument("--json", action="store_true", dest="json_out")

    # --- summary ---
    sub.add_parser("summary", help="One-liner summary for briefing")

    # --- rules ---
    p_rules = sub.add_parser("rules", help="Categorisation rule management")
    rules_sub = p_rules.add_subparsers(dest="rules_command")
    rules_sub.add_parser("list", help="List all rules")
    p_rules_add = rules_sub.add_parser("add", help="Add a new rule")
    p_rules_add.add_argument("--pattern", required=True, help="Regex pattern")
    p_rules_add.add_argument("--account", required=True, help="Target account")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "add": cmd_add,
        "import": cmd_import,
        "balance": cmd_balance,
        "income": cmd_income,
        "cashflow": cmd_cashflow,
        "categories": cmd_categories,
        "search": cmd_search,
        "summary": cmd_summary,
        "rules": cmd_rules,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(handler(args) or 0)


def cmd_add(args) -> int:
    """Add a manual journal entry."""
    entry_date = date.today()
    if args.entry_date:
        try:
            entry_date = date.fromisoformat(args.entry_date)
        except ValueError:
            print(f"ERROR: invalid date '{args.entry_date}'. Use YYYY-MM-DD.", file=sys.stderr)
            return 1

    amount = abs(args.amount)
    account = args.account

    # Determine source/balancing account
    if args.from_account:
        from_account = args.from_account
    elif account.startswith("expenses:"):
        from_account = "assets:bank:checking"
    elif account.startswith("income:"):
        from_account = "assets:bank:checking"
    else:
        from_account = "assets:bank:checking"

    if account.startswith("expenses:"):
        postings = [
            jmod.Posting(account=account, amount=amount, currency=args.currency),
            jmod.Posting(account=from_account),
        ]
    elif account.startswith("income:"):
        postings = [
            jmod.Posting(account=from_account, amount=amount, currency=args.currency),
            jmod.Posting(account=account),
        ]
    else:
        postings = [
            jmod.Posting(account=account, amount=amount, currency=args.currency),
            jmod.Posting(account=from_account),
        ]

    entry = jmod.Entry(
        date=entry_date,
        payee=args.payee,
        postings=postings,
        comment=args.comment,
    )

    jmod.append_entries([entry])

    hlog("ledgerctl", "info", "entry_added", {
        "account": account,
        "amount": amount,
        "payee": args.payee,
        "date": entry_date.isoformat(),
    })

    print(f"added  {entry_date}  {args.payee}  {args.currency}{amount:.2f}  -> {account}")
    return 0


def cmd_import(args) -> int:
    """Import a bank CSV file."""
    try:
        entries = importer.import_csv(
            csv_path=args.csv_path,
            bank_name=args.bank,
            dry_run=args.dry_run,
            currency=args.currency,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"--- DRY RUN: {len(entries)} entries would be imported ---\n")
        for entry in entries:
            print(entry.format())
            print()
    else:
        print(f"Imported {len(entries)} entries.")

    return 0


def cmd_balance(args) -> int:
    """Show balance report."""
    if args.json_out:
        result = reports.balance(period=args.period, as_json=True)
        print(json.dumps(result, indent=2))
    else:
        print(reports.balance(period=args.period))
    return 0


def cmd_income(args) -> int:
    """Show income report."""
    if args.json_out:
        result = reports.income(period=args.period, as_json=True)
        print(json.dumps(result, indent=2))
    else:
        print(reports.income(period=args.period))
    return 0


def cmd_cashflow(args) -> int:
    """Show cashflow report."""
    if args.json_out:
        result = reports.cashflow(period=args.period, as_json=True)
        print(json.dumps(result, indent=2))
    else:
        print(reports.cashflow(period=args.period))
    return 0


def cmd_categories(args) -> int:
    """List expense categories with totals."""
    cats = reports.categories(period=args.period)

    if args.json_out:
        print(json.dumps(cats, indent=2))
    else:
        if not cats:
            print("No expense categories found.")
            return 0
        fmt = "  {:<40} ${:>12,.2f}"
        print(f"  {'CATEGORY':<40} {'AMOUNT':>14}")
        print("  " + "-" * 56)
        for account, amount in cats.items():
            print(fmt.format(account, amount))
    return 0


def cmd_search(args) -> int:
    """Search transactions by payee."""
    results = reports.search(args.payee)

    if args.json_out:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print(f"No transactions matching '{args.payee}'.")
            return 0
        for r in results:
            postings_str = ", ".join(
                f"{p['account']}" + (f" {p.get('currency', '$')}{p['amount']:.2f}" if 'amount' in p else "")
                for p in r["postings"]
            )
            print(f"  {r['date']}  {r['payee']:<30}  {postings_str}")
    return 0


def cmd_summary(args) -> int:
    """Print one-liner summary for briefing integration."""
    summary = briefing.text_summary()
    if summary:
        print(summary)
    else:
        print("ledgerctl: no transaction data yet")
    return 0


def cmd_rules(args) -> int:
    """Manage categorisation rules."""
    if not args.rules_command:
        print("Usage: ledgerctl rules {list|add}", file=sys.stderr)
        return 1

    if args.rules_command == "list":
        rules = rmod.load_rules()
        if not rules:
            print("No rules configured. Add rules with: ledgerctl rules add --pattern PATTERN --account ACCOUNT")
            return 0
        fmt = "  {:<3} {:<30} {}"
        print(fmt.format("#", "PATTERN", "ACCOUNT"))
        print("  " + "-" * 60)
        for i, rule in enumerate(rules, 1):
            print(fmt.format(i, rule["pattern"], rule["account"]))
        return 0

    if args.rules_command == "add":
        import re
        # Validate regex
        try:
            re.compile(args.pattern)
        except re.error as e:
            print(f"ERROR: invalid regex pattern: {e}", file=sys.stderr)
            return 1

        rmod.add_rule(args.pattern, args.account)
        hlog("ledgerctl", "info", "rule_added", {
            "pattern": args.pattern,
            "account": args.account,
        })
        print(f"added rule: '{args.pattern}' -> {args.account}")
        return 0

    return 1


if __name__ == "__main__":
    main()
