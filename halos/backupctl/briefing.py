"""Briefing integration for backupctl.

Provides text_summary() for inclusion in morning/nightly briefings.
"""

from . import engine
from .config import load_config


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def text_summary() -> str:
    """One-line text summary for briefing integration.

    Example: "backupctl: last backup 2h ago | store: 30 snapshots (1.2 GB), memory: 30 snapshots (45 MB)"
    """
    try:
        cfg = load_config()

        age = engine.get_last_backup_age(cfg)
        if age is not None:
            if age < 1:
                age_str = f"{int(age * 60)}min ago"
            elif age < 24:
                age_str = f"{age:.0f}h ago"
            else:
                age_str = f"{age / 24:.0f}d ago"
            parts = [f"backupctl: last backup {age_str}"]
        else:
            parts = ["backupctl: no backups found"]

        target_parts = []
        for name in sorted(cfg.targets):
            stats = engine.get_target_stats(cfg, name)
            count = stats["snapshot_count"]
            if count > 0:
                size_str = _format_size(stats["total_size_bytes"]) if stats["total_size_bytes"] else ""
                if size_str:
                    target_parts.append(f"{name}: {count} snapshots ({size_str})")
                else:
                    target_parts.append(f"{name}: {count} snapshots")

        if target_parts:
            parts.append(", ".join(target_parts))

        return " | ".join(parts)
    except Exception:
        return "backupctl: unavailable"
