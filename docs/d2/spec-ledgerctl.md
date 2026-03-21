# ledgerctl — Personal Finance Aggregation

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NEXT
**Effort:** ~30 agent-min + ~45 human-min (bank rules, category decisions)

---

## Purpose

Aggregate personal finances into one structured, queryable place. Plain-text accounting (hledger/beancount) as the engine, with a halos-native CLI wrapper that adds: bank CSV import, briefing integration, and a foundation for AI-assisted financial analysis.

The dream: a personalised financial advisor built on structured financial data. This spec covers the data foundation — the advisory layer comes later, once the data is clean and queryable.

## CLI Interface

```
ledgerctl add --account expenses:food --amount 42.50 --payee "Countdown"
ledgerctl add --account income:salary --amount 5000 --date 2026-03-15

ledgerctl import --bank anz --csv statement.csv [--dry-run]
ledgerctl import --bank wise --csv wise-statement.csv

ledgerctl balance [--period monthly] [--json]
ledgerctl income [--period monthly] [--json]
ledgerctl cashflow [--period monthly]

ledgerctl categories                     # list expense categories + recent spend
ledgerctl search --payee "Countdown"     # find transactions
ledgerctl summary                        # one-liner for briefing integration

ledgerctl rules list                     # show import categorisation rules
ledgerctl rules add --pattern "COUNTDOWN" --account expenses:food
```

## Architecture

### Data Layer

hledger journal file at `store/ledger.journal` (plain text, git-trackable):

```
2026-03-21 Countdown
    expenses:food                       $42.50
    assets:bank:anz:checking

2026-03-15 Employer
    assets:bank:anz:checking           $5,000.00
    income:salary
```

### Bank Import Engine

Each bank gets a rules file at `halos/ledgerctl/banks/<bank>.py`:

```python
# banks/anz.py
COLUMNS = {
    "date": "Date",
    "amount": "Amount",
    "payee": "Particulars",
    "reference": "Reference",
}
DATE_FORMAT = "%d/%m/%Y"
DEFAULT_ACCOUNT = "assets:bank:anz:checking"
```

Import flow:
1. Parse CSV with bank-specific column mapping
2. Apply categorisation rules (pattern → account mapping)
3. Generate hledger journal entries
4. `--dry-run` shows entries without writing
5. Append to `store/ledger.journal`

### Categorisation Rules

Stored in `store/ledger-rules.yaml`:

```yaml
rules:
  - pattern: "COUNTDOWN|NEW WORLD|PAKNSAVE"
    account: expenses:food
  - pattern: "VODAFONE|SPARK"
    account: expenses:phone
  - pattern: "SALARY|EMPLOYER"
    account: income:salary
```

Rules are deterministic pattern matching — no LLM classification (per feedback memory: no LLM on untrusted input). Uncategorised transactions go to `expenses:uncategorised` for human review.

## Module Structure

```
halos/ledgerctl/
  __init__.py
  cli.py          # argparse, subcommands
  journal.py      # read/write/append hledger journal entries
  importer.py     # bank CSV import engine
  rules.py        # categorisation rule management
  reports.py      # balance, income, cashflow (wraps hledger CLI)
  briefing.py     # text_summary() for briefing integration
  banks/
    __init__.py
    anz.py         # ANZ CSV format
    wise.py        # Wise CSV format
```

## Briefing Integration

One-liner:
```
ledgerctl: spent $1,240 this week (food $380, transport $210, misc $650) | income: $5,000 | savings rate: 62%
```

## Human Decision Points

This module has more human-input requirements than typical halos modules:

1. **Bank CSV column mapping** — each bank has a different CSV format. The Operator must configure the first import for each bank.
2. **Category taxonomy** — what expense categories to use. Start minimal (food, transport, housing, utilities, entertainment, misc) and let the Operator expand.
3. **Categorisation rules** — pattern → category mappings. The Operator reviews uncategorised transactions and adds rules iteratively.
4. **Account structure** — assets, liabilities, income, expense account hierarchy.

## Dependencies

- `hledger` (system package, `apt install hledger` or `brew install hledger`)
- No Python dependencies beyond stdlib (CSV parsing, YAML for rules)

## Integration Points

- pyproject.toml — add `ledgerctl = "halos.ledgerctl.cli:main"`
- briefings — spending summary in morning/nightly briefings
- dashctl — finance panel (monthly spend trend, savings rate, top categories)
- calctl — could correlate spending with calendar events (stretch goal)

## Future: Advisory Layer

Once the data foundation is solid (3+ months of clean, categorised transactions), the advisory layer can:
- Compute spending trends (increasing/decreasing by category)
- Flag anomalies ("you spent 3x your usual food budget this week")
- Project cash flow ("at current rate, you'll have $X in savings by June")
- Suggest optimisations ("your phone plan costs $X/month — here are cheaper options")

This advisory layer operates on structured financial data, not raw bank input — so it avoids the prompt injection concern. The LLM analyses your own categorised numbers, not untrusted external text.

## What It Does NOT Do

- Connect to bank APIs directly (CSV import is the interface — simpler, more portable, no OAuth complexity)
- Provide actual financial advice (disclaimer: not financial advice)
- Auto-categorise via LLM (deterministic rules only)
- Handle investment tracking (separate concern, possibly future `investctl`)

## Testing

- Unit tests for CSV parsing with sample bank statements
- Unit tests for categorisation rule application
- Integration test: import CSV → verify journal entries → run balance report
- Edge cases: duplicate detection, partial imports, currency handling
