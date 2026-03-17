import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

from .config import load_config
from .todo import TodoItem, ValidationError, TransitionError, VALID_STATUSES
from halos.common.log import hlog


def cmd_add(args, cfg):
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    entities = [e.strip() for e in args.entities.split(",")] if args.entities else []
    warnings = []
    if cfg.valid_tags:
        for t in tags:
            if t not in cfg.valid_tags:
                warnings.append(f"unknown tag '{t}'")

    priority = args.priority
    if priority not in cfg.valid_priorities:
        print(f"ERROR: invalid priority {priority}. Valid: {cfg.valid_priorities}", file=sys.stderr)
        sys.exit(1)

    try:
        item = TodoItem.create(
            items_dir=cfg.items_dir,
            title=args.title,
            priority=priority,
            tags=tags,
            context=args.context or "",
            due=args.due,
            entities=entities,
        )
    except ValidationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    hlog("todoctl", "info", "item_created", {"id": item.id, "title": args.title})

    if args.json:
        print(json.dumps({"id": item.id, "file": str(item.file_path), "warnings": warnings}, indent=2))
    else:
        print(f"created  {item.id}  {item.file_path.name}")
        for w in warnings:
            print(f"  warning: {w}")
    return 0


def cmd_list(args, cfg):
    items = _load_all_items(cfg.items_dir)

    if not getattr(args, "all", False):
        items = [i for i in items if i.status in ("open", "in-progress", "review", "testing", "blocked")]

    items.sort(key=lambda i: (i.priority, i.created))

    if args.json:
        print(json.dumps([i.data for i in items], indent=2))
    else:
        if not items:
            print("no items found")
            return 0
        fmt = "{:<18} {:<40} {:<14} {:<4} {}"
        print(fmt.format("ID", "TITLE", "STATUS", "PRI", "TAGS"))
        print("-" * 90)
        for i in items:
            title = i.title[:39]
            tags = ", ".join(i.tags)[:20]
            print(fmt.format(i.id, title, i.status, str(i.priority), tags))
    return 0


def _transition_item(cfg, item_id: str, new_status: str, label: str, extra_cb=None):
    """Find an item, transition it, save, log, and print."""
    item = _find_item(cfg.items_dir, item_id)
    if not item:
        print(f"ERROR: item '{item_id}' not found", file=sys.stderr)
        sys.exit(1)
    try:
        item.transition(new_status)
    except TransitionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    if extra_cb:
        extra_cb(item)
    item.save()
    hlog("todoctl", "info", "status_changed", {"id": item.id, "status": new_status})
    print(f"{label}  {item.id}  {item.title}")
    return 0


def cmd_done(args, cfg):
    return _transition_item(cfg, args.id, "done", "done")


def cmd_defer(args, cfg):
    return _transition_item(cfg, args.id, "deferred", "deferred")


def cmd_block(args, cfg):
    def _set_blocked_by(item):
        item.data["blocked_by"] = args.by

    item = _find_item(cfg.items_dir, args.id)
    if not item:
        print(f"ERROR: item '{args.id}' not found", file=sys.stderr)
        sys.exit(1)
    try:
        item.transition("blocked")
    except TransitionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    item.data["blocked_by"] = args.by
    item.save()
    hlog("todoctl", "info", "status_changed", {"id": item.id, "status": "blocked"})
    print(f"blocked  {item.id}  {item.title}  by: {args.by}")
    return 0


def cmd_start(args, cfg):
    return _transition_item(cfg, args.id, "in-progress", "started")


def cmd_cancel(args, cfg):
    return _transition_item(cfg, args.id, "cancelled", "cancelled")


def cmd_review(args, cfg):
    return _transition_item(cfg, args.id, "review", "review")


def cmd_testing(args, cfg):
    return _transition_item(cfg, args.id, "testing", "testing")


def cmd_edit(args, cfg):
    item = _find_item(cfg.items_dir, args.id)
    if not item:
        print(f"ERROR: item '{args.id}' not found", file=sys.stderr)
        sys.exit(1)

    if args.title is not None:
        item.data["title"] = args.title
    if args.priority is not None:
        item.data["priority"] = args.priority
    if args.tags is not None:
        item.data["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.context is not None:
        item.data["context"] = args.context
    if args.due is not None:
        item.data["due"] = args.due
    if args.entities is not None:
        item.data["entities"] = [e.strip() for e in args.entities.split(",")]

    item.save()
    hlog("todoctl", "info", "item_edited", {"id": item.id})
    print(f"edited  {item.id}  {item.title}")
    return 0


def cmd_archive(args, cfg):
    items = _load_all_items(cfg.items_dir)
    archive_dir = cfg.backlog_dir / "archive"
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    candidates = []
    for i in items:
        if i.status not in ("done", "cancelled"):
            continue
        created_str = i.created
        if not created_str:
            continue
        try:
            created_dt = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        if created_dt < cutoff:
            candidates.append(i)

    if not candidates:
        print("nothing to archive")
        return 0

    if not getattr(args, "execute", False):
        # dry-run (default)
        print(f"would archive {len(candidates)} item(s):")
        for i in candidates:
            print(f"  {i.id}  {i.status:<12} {i.title}")
        print("\npass --execute to actually move files")
        return 0

    archive_dir.mkdir(parents=True, exist_ok=True)
    for i in candidates:
        i.archive(archive_dir)
        print(f"archived  {i.id}  {i.title}")
    print(f"\n{len(candidates)} item(s) archived to {archive_dir}")
    return 0


def cmd_stats(args, cfg):
    items = _load_all_items(cfg.items_dir)

    archive_dir = cfg.backlog_dir / "archive"
    archived_count = len(list(archive_dir.glob("*.yaml"))) if archive_dir.exists() else 0

    by_status: dict[str, int] = {}
    by_priority: dict[int, int] = {}
    by_tag: dict[str, int] = {}

    for i in items:
        by_status[i.status] = by_status.get(i.status, 0) + 1
        by_priority[i.priority] = by_priority.get(i.priority, 0) + 1
        for t in i.tags:
            by_tag[t] = by_tag.get(t, 0) + 1

    if args.json:
        print(json.dumps({
            "total": len(items),
            "archived": archived_count,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_tag": by_tag,
        }, indent=2))
    else:
        print(f"Backlog items:  {len(items)}")
        for s in VALID_STATUSES:
            n = by_status.get(s, 0)
            if n or s in ("open", "done"):
                print(f"  {s:<14} {n}")
        if archived_count:
            print(f"  {'archived':<14} {archived_count}")
        print()
        if by_priority:
            print("By priority:")
            for p in sorted(by_priority):
                label = {1: "critical", 2: "high", 3: "medium", 4: "low"}.get(p, str(p))
                print(f"  {p} ({label}):  {by_priority[p]}")
            print()
        if by_tag:
            print("By tag:")
            for k, v in sorted(by_tag.items(), key=lambda x: -x[1]):
                print(f"  {k:<16} {v}")
    return 0


def cmd_graph(args, cfg):
    items = _load_all_items(cfg.items_dir)
    items.sort(key=lambda i: (i.priority, i.created))

    active = [i for i in items if i.status in ("open", "in-progress", "review", "testing", "blocked")]
    done = [i for i in items if i.status == "done"]
    deferred = [i for i in items if i.status == "deferred"]

    width = 64
    print(f"{'=' * width}")
    print(f"  BACKLOG  ·  {len(items)} items  ·  {len(active)} active  ·  {len(done)} done")
    print(f"{'=' * width}")

    priority_labels = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW"}

    for pri in sorted(priority_labels):
        group = [i for i in active if i.priority == pri]
        if not group:
            continue
        print(f"\n  ┌─ {priority_labels[pri]} ({len(group)})")
        for idx, i in enumerate(group):
            is_last = idx == len(group) - 1
            prefix = "  └─" if is_last else "  ├─"
            status_marker = {"open": " ", "in-progress": "*", "review": "R", "testing": "T", "blocked": "!"}
            marker = status_marker.get(i.status, "?")
            print(f"{prefix} [{marker}] {i.title}")
            if i.tags:
                detail = "    " if is_last else "  │ "
                print(f"{detail}   #{', '.join(i.tags)}")

    if deferred:
        print(f"\n  ┌─ DEFERRED ({len(deferred)})")
        for idx, i in enumerate(deferred):
            is_last = idx == len(deferred) - 1
            prefix = "  └─" if is_last else "  ├─"
            print(f"{prefix} {i.title}")

    print()
    print(f"{'=' * width}")
    return 0


def _load_all_items(items_dir: Path) -> list[TodoItem]:
    if not items_dir.exists():
        return []
    items = []
    for f in sorted(items_dir.glob("*.yaml")):
        try:
            items.append(TodoItem.from_file(f))
        except (ValueError, yaml.YAMLError, OSError) as e:
            print(f"WARN: skipping {f.name}: {e}", file=sys.stderr)
    return items


def _find_item(items_dir: Path, item_id: str) -> TodoItem | None:
    for i in _load_all_items(items_dir):
        if i.id == item_id:
            return i
    return None


def build_parser():
    parser = argparse.ArgumentParser(
        prog="todoctl",
        description="halos backlog tracking CLI",
    )
    parser.add_argument("--config", default=None, help="Path to todoctl.yaml")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="subcommand")

    # add
    add = sub.add_parser("add", help="Create a new backlog item")
    add.add_argument("--title", required=True)
    add.add_argument("--priority", type=int, default=3)
    add.add_argument("--tags", default=None)
    add.add_argument("--context", default=None)
    add.add_argument("--due", default=None)
    add.add_argument("--entities", default=None, help="Comma-separated entities")

    # list
    lst = sub.add_parser("list", help="List backlog items")
    lst.add_argument("--all", action="store_true", help="Include done/deferred")

    # done
    dn = sub.add_parser("done", help="Mark item as done")
    dn.add_argument("id")

    # defer
    df = sub.add_parser("defer", help="Mark item as deferred")
    df.add_argument("id")

    # block
    bl = sub.add_parser("block", help="Mark item as blocked")
    bl.add_argument("id")
    bl.add_argument("--by", required=True, help="Reason for blocking")

    # start
    st = sub.add_parser("start", help="Mark item as in-progress")
    st.add_argument("id")

    # cancel
    cn = sub.add_parser("cancel", help="Mark item as cancelled")
    cn.add_argument("id")

    # review
    rv = sub.add_parser("review", help="Mark item as in review")
    rv.add_argument("id")

    # testing
    ts = sub.add_parser("testing", help="Mark item as in testing")
    ts.add_argument("id")

    # edit
    ed = sub.add_parser("edit", help="Edit an existing item")
    ed.add_argument("id")
    ed.add_argument("--title", default=None)
    ed.add_argument("--priority", type=int, default=None)
    ed.add_argument("--tags", default=None)
    ed.add_argument("--context", default=None)
    ed.add_argument("--due", default=None)
    ed.add_argument("--entities", default=None, help="Comma-separated entities")

    # archive
    ar = sub.add_parser("archive", help="Archive done/cancelled items older than 30 days")
    ar.add_argument("--execute", action="store_true", help="Actually move files (default is dry-run)")

    # stats
    sub.add_parser("stats", help="Backlog health report")

    # graph
    sub.add_parser("graph", help="Visual backlog display")

    return parser


def main():
    import warnings
    print(
        "WARNING: todoctl is deprecated. Use nightctl instead.\n"
        "  Items have been migrated to queue/items/.\n"
        "  Run 'nightctl list' to see your backlog.\n",
        file=sys.stderr,
    )

    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(4)

    dispatch = {
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "defer": cmd_defer,
        "block": cmd_block,
        "start": cmd_start,
        "cancel": cmd_cancel,
        "review": cmd_review,
        "testing": cmd_testing,
        "edit": cmd_edit,
        "archive": cmd_archive,
        "stats": cmd_stats,
        "graph": cmd_graph,
    }

    if args.subcommand in dispatch:
        sys.exit(dispatch[args.subcommand](args, cfg) or 0)
    else:
        parser.print_help()
        sys.exit(0)
