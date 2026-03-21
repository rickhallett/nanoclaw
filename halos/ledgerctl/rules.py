"""Categorisation rules for ledgerctl.

Rules are stored in store/ledger-rules.yaml. Each rule:
  - pattern: regex pattern to match against payee/description
  - account: hledger account name (e.g. expenses:food)

Rules evaluate in order, first match wins.
Unmatched transactions map to expenses:uncategorised.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Optional

import yaml


DEFAULT_ACCOUNT = "expenses:uncategorised"


def _store_dir() -> Path:
    """Resolve the store/ directory relative to the repo root."""
    p = Path(__file__).resolve()
    for ancestor in p.parents:
        if (ancestor / "store").is_dir():
            return ancestor / "store"
    return Path.cwd() / "store"


def rules_path(store_dir: Optional[Path] = None) -> Path:
    """Return path to the rules YAML file."""
    d = store_dir or _store_dir()
    return d / "ledger-rules.yaml"


def load_rules(path: Optional[Path] = None) -> list[dict]:
    """Load categorisation rules from YAML.

    Returns:
        List of dicts with 'pattern' and 'account' keys, in order.
    """
    rpath = path or rules_path()
    if not rpath.exists():
        return []

    with open(rpath, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("rules", [])


def save_rules(rules: list[dict], path: Optional[Path] = None) -> None:
    """Save rules to YAML atomically."""
    rpath = path or rules_path()
    rpath.parent.mkdir(parents=True, exist_ok=True)

    data = {"rules": rules}
    content = yaml.dump(data, default_flow_style=False, sort_keys=False)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(rpath.parent), prefix=".rules_", suffix=".tmp"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.rename(tmp_path, str(rpath))
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def add_rule(
    pattern: str,
    account: str,
    path: Optional[Path] = None,
) -> list[dict]:
    """Append a new rule. Returns the updated rules list."""
    rules = load_rules(path)
    rules.append({"pattern": pattern, "account": account})
    save_rules(rules, path)
    return rules


def categorise(payee: str, rules: Optional[list[dict]] = None) -> str:
    """Match a payee against rules and return the target account.

    Args:
        payee: Transaction payee/description text.
        rules: Optional pre-loaded rules list. Loads from file if None.

    Returns:
        The matched account, or 'expenses:uncategorised' if no match.
    """
    if rules is None:
        rules = load_rules()

    for rule in rules:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        try:
            if re.search(pattern, payee, re.IGNORECASE):
                return rule["account"]
        except re.error:
            # Invalid regex — skip this rule
            continue

    return DEFAULT_ACCOUNT
