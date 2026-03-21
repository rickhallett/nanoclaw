"""Bank CSV format definitions.

Each bank module exports:
  COLUMNS: dict mapping semantic fields to CSV header names
  DATE_FORMAT: strptime format string
  DEFAULT_ACCOUNT: hledger account for the bank
"""

import importlib
import pkgutil


_BANKS: dict[str, object] = {}


def load_all() -> None:
    """Import all bank modules to populate the registry."""
    for finder, name, is_pkg in pkgutil.iter_modules(__path__):
        mod = importlib.import_module(f".{name}", package="halos.ledgerctl.banks")
        _BANKS[name] = mod


def get(name: str):
    """Return a bank module by name, or None."""
    if not _BANKS:
        load_all()
    return _BANKS.get(name)


def all_banks() -> list[str]:
    """Return sorted list of registered bank names."""
    if not _BANKS:
        load_all()
    return sorted(_BANKS.keys())
