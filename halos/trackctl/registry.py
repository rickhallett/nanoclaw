"""Domain registry for trackctl.

Each domain module calls register() to declare itself.
The registry is the single source of truth for available domains.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DomainInfo:
    """Metadata about a registered tracker domain."""
    name: str
    description: str
    target: Optional[int] = None  # streak target, if any


_DOMAINS: dict[str, DomainInfo] = {}


def register(name: str, description: str, target: Optional[int] = None) -> None:
    """Register a tracker domain.

    Args:
        name: Short domain name (e.g. 'zazen'). Used as DB filename and CLI argument.
        description: Human-readable description.
        target: Optional streak target in days.

    Raises:
        ValueError: If name is empty or already registered.
    """
    if not name:
        raise ValueError("domain name must not be empty")
    if name in _DOMAINS:
        raise ValueError(f"domain '{name}' is already registered")
    _DOMAINS[name] = DomainInfo(name=name, description=description, target=target)


def get(name: str) -> Optional[DomainInfo]:
    """Look up a domain by name. Returns None if not found."""
    return _DOMAINS.get(name)


def all_domains() -> list[DomainInfo]:
    """Return all registered domains, sorted by name."""
    return sorted(_DOMAINS.values(), key=lambda d: d.name)


def load_all() -> None:
    """Import all domain modules to trigger registration.

    This discovers domain modules in the domains/ package and imports them.
    Each module's top-level code calls register().
    """
    import importlib
    import pkgutil
    from . import domains as domains_pkg

    for finder, name, is_pkg in pkgutil.iter_modules(domains_pkg.__path__):
        importlib.import_module(f".domains.{name}", package="halos.trackctl")
