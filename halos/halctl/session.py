"""halctl session — session lifecycle management for prime and fleet.

List, inspect, and clear Claude SDK sessions. Every mutation is logged
via hlog so logctl picks it up automatically.

Usage:
    halctl session list [--instance <name>]
    halctl session clear <group_folder> [--instance <name>]
    halctl session clear-all [--instance <name>]
"""

import sqlite3
import sys
from pathlib import Path

from halos.common.log import hlog


def _resolve_db(instance: str | None) -> Path:
    """Return the messages.db path for prime or a fleet instance."""
    if instance is None or instance == "prime":
        # Prime: project root is parent of halos/
        project_root = Path(__file__).resolve().parents[2]
        db = project_root / "store" / "messages.db"
    else:
        from .config import load_fleet_manifest

        manifest = load_fleet_manifest()
        entry = next(
            (i for i in manifest.get("instances", []) if i["name"] == instance),
            None,
        )
        if entry is None:
            print(f"ERROR: instance '{instance}' not found", file=sys.stderr)
            sys.exit(1)
        db = Path(entry["path"]) / "store" / "messages.db"

    if not db.exists():
        print(f"ERROR: no database at {db}", file=sys.stderr)
        sys.exit(1)
    return db


def session_list(instance: str | None) -> int:
    """List all active sessions."""
    db = _resolve_db(instance)
    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT group_folder, session_id FROM sessions").fetchall()
    conn.close()

    target = instance or "prime"
    if not rows:
        print(f"{target}: no active sessions")
        return 0

    print(f"{target}: {len(rows)} session(s)")
    print(f"{'GROUP FOLDER':<30} SESSION ID")
    print("─" * 70)
    for folder, sid in rows:
        print(f"{folder:<30} {sid}")
    return 0


def session_clear(group_folder: str, instance: str | None) -> int:
    """Clear session for a specific group folder."""
    db = _resolve_db(instance)
    target = instance or "prime"

    conn = sqlite3.connect(str(db))
    cur = conn.execute(
        "SELECT session_id FROM sessions WHERE group_folder = ?",
        (group_folder,),
    )
    row = cur.fetchone()
    if not row:
        print(f"{target}: no session for '{group_folder}'")
        conn.close()
        return 1

    old_sid = row[0]
    conn.execute("DELETE FROM sessions WHERE group_folder = ?", (group_folder,))
    conn.commit()
    conn.close()

    hlog("halctl", "info", "session_clear", {
        "instance": target,
        "group_folder": group_folder,
        "cleared_session_id": old_sid,
    })
    print(f"{target}: cleared session for '{group_folder}'")
    print(f"  was: {old_sid}")
    # HALO.HALCTL.04: Warn that the live process has an in-memory session map
    # that is not coordinated with this SQLite mutation. The clear only takes
    # full effect after a service restart.
    print(f"  WARNING: the live process may still hold the old session in memory")
    print(f"  restart the service for the clear to take full effect")
    return 0


def session_clear_all(instance: str | None) -> int:
    """Clear all sessions."""
    db = _resolve_db(instance)
    target = instance or "prime"

    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT group_folder, session_id FROM sessions").fetchall()
    if not rows:
        print(f"{target}: no sessions to clear")
        conn.close()
        return 0

    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()

    cleared = {folder: sid for folder, sid in rows}
    hlog("halctl", "info", "session_clear_all", {
        "instance": target,
        "count": len(cleared),
        "cleared": cleared,
    })
    print(f"{target}: cleared {len(cleared)} session(s)")
    for folder, sid in rows:
        print(f"  {folder}: {sid[:16]}...")
    # HALO.HALCTL.04: Same in-memory coherence warning as session_clear
    print(f"  WARNING: the live process may still hold old sessions in memory")
    print(f"  restart the service for clears to take full effect")
    return 0
