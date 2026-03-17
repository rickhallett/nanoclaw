"""Migrate todoctl backlog items to nightctl unified items.

Reads YAML files from backlog/items/, converts to the nightctl Item schema
(adding kind=task and null machine/agent fields), and writes to queue/items/
using atomic writes.

Usage:
    uv run python -m halos.nightctl.migrate_todoctl
    uv run python -m halos.nightctl.migrate_todoctl --dry-run
    uv run python -m halos.nightctl.migrate_todoctl --source ./backlog/items --dest ./queue/items
"""

import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    from . import yaml_shim as yaml

from .item import Item, _slugify


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically via tmp + os.replace."""
    tmp = path.with_suffix(".yaml.tmp")
    try:
        tmp.write_text(content)
        os.replace(str(tmp), str(path))
    except OSError as e:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(f"Failed to write {path.name}: {e}") from e


def migrate_item(data: dict, dest_dir: Path, dry_run: bool = False) -> dict:
    """Convert a single todoctl item to nightctl Item schema.

    Returns a summary dict with id, title, status, and outcome.
    """
    item_id = data.get("id", "unknown")
    title = data.get("title", "untitled")

    # Build the unified Item data, preserving all existing fields
    # and adding the new nightctl-specific fields with sensible defaults.
    now_iso = data.get("created", "")
    modified = data.get("modified", now_iso)

    unified = {
        # Identity
        "id": item_id,
        "title": title,
        "kind": "task",

        # Lifecycle (preserved from todoctl)
        "status": data.get("status", "open"),
        "priority": data.get("priority", 3),
        "tags": data.get("tags", []),
        "entities": data.get("entities", []),

        # Human fields (preserved from todoctl)
        "context": data.get("context", ""),
        "due": data.get("due"),
        "blocked_by": data.get("blocked_by"),

        # Machine fields (null for tasks)
        "command": None,
        "schedule": None,
        "window": None,
        "depends_on": [],
        "retries": 2,
        "retries_remaining": 2,
        "timeout_secs": 300,

        # Agent fields (null for tasks)
        "plan": None,
        "plan_ref": None,

        # Metadata
        "created": now_iso,
        "modified": modified,
        "created_by": "human",
    }

    # Generate filename matching nightctl convention
    slug = _slugify(title)
    filename = f"{item_id}-{slug}.yaml"
    dest_path = dest_dir / filename

    result = {
        "id": item_id,
        "title": title,
        "status": unified["status"],
        "file": filename,
        "outcome": "ok",
    }

    if dry_run:
        result["outcome"] = "dry-run"
        return result

    # Validate before writing
    item = Item(unified, file_path=dest_path)
    try:
        item.validate()
    except Exception as e:
        result["outcome"] = f"validation error: {e}"
        return result

    # Write using atomic pattern
    content = yaml.dump(unified, default_flow_style=False, sort_keys=False)
    _atomic_write(dest_path, content)

    return result


def run_migration(
    source_dir: Path,
    dest_dir: Path,
    dry_run: bool = False,
) -> list[dict]:
    """Migrate all todoctl items from source_dir to dest_dir.

    Returns a list of result dicts (one per item).
    """
    if not source_dir.exists():
        print(f"ERROR: source directory does not exist: {source_dir}", file=sys.stderr)
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)

    results = []
    source_files = sorted(source_dir.glob("*.yaml"))

    if not source_files:
        print("No YAML files found in source directory.")
        return []

    for f in source_files:
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as e:
            results.append({
                "id": f.stem,
                "title": f.stem,
                "status": "unknown",
                "file": f.name,
                "outcome": f"parse error: {e}",
            })
            continue

        result = migrate_item(data, dest_dir, dry_run=dry_run)
        results.append(result)

    return results


def print_summary(results: list[dict], dry_run: bool = False) -> None:
    """Print a human-readable migration summary."""
    if not results:
        print("Nothing to migrate.")
        return

    prefix = "[DRY-RUN] " if dry_run else ""
    ok = [r for r in results if r["outcome"] in ("ok", "dry-run")]
    errors = [r for r in results if r["outcome"] not in ("ok", "dry-run")]

    print(f"\n{prefix}Migration summary: {len(ok)} migrated, {len(errors)} errors")
    print("-" * 60)

    for r in ok:
        print(f"  {r['id']:<24} {r['status']:<12} {r['title'][:40]}")

    if errors:
        print(f"\nErrors:")
        for r in errors:
            print(f"  {r['id']}: {r['outcome']}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate todoctl backlog items to nightctl unified items."
    )
    parser.add_argument(
        "--source", default="./backlog/items",
        help="Source directory (todoctl items)"
    )
    parser.add_argument(
        "--dest", default="./queue/items",
        help="Destination directory (nightctl items)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be migrated without writing"
    )

    args = parser.parse_args()

    source = Path(args.source).resolve()
    dest = Path(args.dest).resolve()

    print(f"Source:  {source}")
    print(f"Dest:    {dest}")
    if args.dry_run:
        print("Mode:    DRY-RUN")

    results = run_migration(source, dest, dry_run=args.dry_run)
    print_summary(results, dry_run=args.dry_run)

    errors = [r for r in results if r["outcome"] not in ("ok", "dry-run")]
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
