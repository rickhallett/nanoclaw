import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import config as cfgmod
from . import index as idxmod
from . import note as notemod
from . import prune as prunemod


def main():
    parser = argparse.ArgumentParser(
        prog="memctl",
        description="NanoClaw memory governance CLI",
    )
    parser.add_argument("--config", default="", help="config file (default: ./memctl.yaml)")
    parser.add_argument("--json", action="store_true", dest="json_out", help="output as JSON")
    parser.add_argument("--dry-run", action="store_true", help="print what would happen")
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command")

    # --- new ---
    p_new = sub.add_parser("new", help="write a new atomic note")
    p_new.add_argument("--title", required=True)
    p_new.add_argument("--type", required=True, dest="note_type")
    p_new.add_argument("--tags", required=True, help="comma-separated")
    p_new.add_argument("--entities", default="", help="comma-separated")
    p_new.add_argument("--confidence", default="high")
    p_new.add_argument("--body", required=True)
    p_new.add_argument("--expires", default="")
    p_new.add_argument("--link-to", default="", dest="link_to")

    # --- get ---
    p_get = sub.add_parser("get", help="print a note by ID or filename")
    p_get.add_argument("query")

    # --- search ---
    p_search = sub.add_parser("search", help="search notes")
    p_search.add_argument("--tags", default="")
    p_search.add_argument("--entities", default="")
    p_search.add_argument("--type", default="", dest="search_type")
    p_search.add_argument("--text", default="")
    p_search.add_argument("--limit", type=int, default=20)

    # --- index ---
    p_index = sub.add_parser("index", help="index management")
    idx_sub = p_index.add_subparsers(dest="index_cmd")
    idx_sub.add_parser("rebuild", help="regenerate index from notes")
    idx_sub.add_parser("verify", help="hash-check all entries")

    # --- link ---
    p_link = sub.add_parser("link", help="add a backlink")
    p_link.add_argument("--from", required=True, dest="link_from")
    p_link.add_argument("--to", required=True, dest="link_to")

    # --- prune ---
    p_prune = sub.add_parser("prune", help="identify and archive stale notes")
    p_prune.add_argument("--execute", action="store_true")

    # --- stats ---
    sub.add_parser("stats", help="corpus health report")

    # --- graph ---
    sub.add_parser("graph", help="print the memory graph")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    cfg = cfgmod.load(args.config)

    commands = {
        "new": cmd_new, "get": cmd_get, "search": cmd_search,
        "index": cmd_index, "link": cmd_link, "prune": cmd_prune,
        "stats": cmd_stats, "graph": cmd_graph,
    }
    commands[args.command](cfg, args)


def split_trim(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()] if s else []


# ── new ──────────────────────────────────────────────────────

def cmd_new(cfg, args):
    tags = split_trim(args.tags)
    entities = split_trim(args.entities)
    id = notemod.now_id()
    now = notemod.now_iso()

    n = notemod.Note(
        id=id, title=args.title, type=args.note_type,
        tags=tags, entities=entities, confidence=args.confidence,
        created=now, modified=now, body=args.body,
        expires=args.expires or None,
    )

    errs = notemod.validate(n, cfg.note.valid_types, cfg.note.valid_confidence)
    if errs:
        print(f"Validation failed:\n  " + "\n  ".join(errs), file=sys.stderr)
        sys.exit(1)

    warnings = []
    known = set(cfg.note.tags)
    for t in tags:
        if t not in known:
            warnings.append(f'unknown tag "{t}"')

    notes_dir = Path(cfg.memory_dir) / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    fname = notemod.filename(id, args.title)
    fpath = notes_dir / fname

    if args.dry_run:
        print(f"DRY RUN: would write {fpath}")
        return

    # Guard against filename collision (e.g. rapid successive calls)
    if fpath.exists():
        print(f"File already exists: {fpath}", file=sys.stderr)
        print("This usually means two notes were created in the same millisecond. Retry.", file=sys.stderr)
        sys.exit(2)

    # Atomic write: temp file then rename
    data = notemod.marshal(n)
    tmp = str(fpath) + ".tmp"
    Path(tmp).write_text(data)
    os.replace(tmp, str(fpath))

    if args.link_to:
        _add_backlink(cfg, args.link_to, id)

    # Update index
    rel = str(fpath)
    summary = n.body[:cfg.index.max_summary_chars]
    if len(n.body) > cfg.index.max_summary_chars:
        summary += "..."

    entry = idxmod.Entry(
        id=id, file=rel, title=n.title, type=n.type,
        tags=n.tags, entities=n.entities, summary=summary,
        hash=idxmod.hash_bytes(data.encode()), backlink_count=0,
        modified=now,
    )

    idx = idxmod.read(cfg.index_file)
    idx.notes.append(entry)
    idx.note_count = len(idx.notes)
    idx.entities = idxmod.collect_entities(idx.notes)
    idx.tag_vocabulary = cfg.note.tags
    idxmod.write(cfg.index_file, idx)

    if args.json_out:
        json.dump({"id": id, "file": rel, "warnings": warnings}, sys.stdout, indent=2)
        print()
    else:
        print(f"Created: {rel}")
        print(f"ID:      {id}")
        for w in warnings:
            print(f"WARNING: {w}")


# ── get ──────────────────────────────────────────────────────

def cmd_get(cfg, args):
    notes_dir = Path(cfg.memory_dir) / "notes"
    if not notes_dir.exists():
        print(f"notes directory not found: {notes_dir}", file=sys.stderr)
        sys.exit(2)
    for f in sorted(notes_dir.iterdir()):
        if f.name.startswith(args.query) or f.name == args.query:
            print(f.read_text(), end="")
            return
    print(f"note {args.query!r} not found", file=sys.stderr)
    sys.exit(1)


# ── search ───────────────────────────────────────────────────

def cmd_search(cfg, args):
    idx = idxmod.read(cfg.index_file)
    tag_filter = split_trim(args.tags)
    ent_filter = split_trim(args.entities)
    results = []

    for n in idx.notes:
        if args.search_type and n.type != args.search_type:
            continue
        if tag_filter and not all(t in n.tags for t in tag_filter):
            continue
        if ent_filter and not any(e.lower() in [x.lower() for x in n.entities] for e in ent_filter):
            continue
        if args.text and args.text.lower() not in (n.title + " " + n.summary).lower():
            continue
        results.append(n)

    results = results[:args.limit]

    if args.json_out:
        json.dump([n.to_dict() for n in results], sys.stdout, indent=2)
        print()
    else:
        for r in results:
            print(r.file)
        if not results:
            print("No matches found.")


# ── index ────────────────────────────────────────────────────

def cmd_index(cfg, args):
    if args.index_cmd == "rebuild":
        _index_rebuild(cfg, args)
    elif args.index_cmd == "verify":
        _index_verify(cfg, args)
    else:
        print("Usage: memctl index {rebuild|verify}")


def _index_rebuild(cfg, args):
    notes_dir = os.path.join(cfg.memory_dir, "notes")
    entries, parse_errors = idxmod.rebuild_from_notes(notes_dir, cfg.index.max_summary_chars)

    idx = idxmod.Index(
        note_count=len(entries),
        entities=idxmod.collect_entities(entries),
        tag_vocabulary=cfg.note.tags,
        notes=entries,
    )

    if args.dry_run:
        print(f"DRY RUN: would write {len(entries)} notes to {cfg.index_file}")
        return

    idxmod.write(cfg.index_file, idx)
    print(f"Rebuilt index: {len(entries)} notes, {parse_errors} parse errors")


def _index_verify(cfg, args):
    idx = idxmod.read(cfg.index_file)
    results = idxmod.verify(idx.notes)
    drift = sum(1 for r in results if r.status == "DRIFT")
    missing = sum(1 for r in results if r.status == "MISSING")

    if args.json_out:
        json.dump([{"id": r.id, "file": r.file, "status": r.status} for r in results], sys.stdout, indent=2)
        print()
    else:
        for r in results:
            print(f"{r.status:<8} {r.id}  {os.path.basename(r.file)}")

    # Check orphans
    notes_dir = Path(cfg.memory_dir) / "notes"
    if notes_dir.exists():
        indexed = {os.path.basename(n.file) for n in idx.notes}
        for f in sorted(notes_dir.iterdir()):
            if f.suffix == ".md" and f.name not in indexed:
                print(f"{'ORPHAN':<8} {f.name}")

    if drift or missing:
        print(f"\n{drift} drifted, {missing} missing. Run: memctl index rebuild")
        sys.exit(3)


# ── link ─────────────────────────────────────────────────────

def cmd_link(cfg, args):
    if args.dry_run:
        print(f"DRY RUN: would link {args.link_from} → {args.link_to}")
        return
    _add_backlink(cfg, args.link_to, args.link_from)
    print(f"Linked: {args.link_from} → {args.link_to}")


def _add_backlink(cfg, target_id: str, source_id: str):
    notes_dir = Path(cfg.memory_dir) / "notes"
    if not notes_dir.exists():
        raise SystemExit(f"notes directory not found: {notes_dir}")
    for f in notes_dir.iterdir():
        if f.name.startswith(target_id):
            n = notemod.parse(f.read_text())
            if source_id in n.backlinks:
                return
            n.backlinks.append(source_id)
            n.modified = notemod.now_iso()
            # Atomic write
            tmp = str(f) + ".tmp"
            Path(tmp).write_text(notemod.marshal(n))
            os.replace(tmp, str(f))
            # Backlink changed the file hash — update the index entry
            idx = idxmod.read(cfg.index_file)
            for entry in idx.notes:
                if entry.id == target_id or os.path.basename(entry.file) == f.name:
                    entry.hash = idxmod.hash_file(str(f))
                    entry.backlink_count = len(n.backlinks)
                    entry.modified = n.modified
                    break
            idxmod.write(cfg.index_file, idx)
            return
    raise SystemExit(f"note {target_id!r} not found")


# ── prune ────────────────────────────────────────────────────

def cmd_prune(cfg, args):
    execute = args.execute and not cfg.prune.dry_run
    if os.environ.get("MEMCTL_DRY_RUN") == "true":
        execute = False

    idx = idxmod.read(cfg.index_file)
    now = datetime.now(timezone.utc)
    archived = 0

    for n in idx.notes:
        if prunemod.is_exempt(n.type, n.backlink_count, cfg.prune.min_backlinks_to_exempt):
            if args.verbose or args.json_out:
                print(f"{'EXEMPT':<10} {n.id}  {os.path.basename(n.file)}  type={n.type}")
            continue

        try:
            mod = datetime.fromisoformat(n.modified.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            mod = now
        days = (now - mod).total_seconds() / 86400
        s = prunemod.score(n.backlink_count, days, cfg.prune.half_life_days)

        if n.expires:
            try:
                exp = datetime.fromisoformat(n.expires.replace("Z", "+00:00"))
                if now > exp:
                    s *= 0.5
            except (ValueError, AttributeError):
                pass

        if s < cfg.prune.min_score:
            print(f"{'CANDIDATE':<10} {n.id}  {os.path.basename(n.file)}  score={s:.3f}  (threshold={cfg.prune.min_score})")
            if execute:
                _archive_note(cfg, n)
                archived += 1
        elif args.verbose:
            print(f"{'KEEP':<10} {n.id}  {os.path.basename(n.file)}  score={s:.3f}")

    if execute:
        print(f"\nArchived: {archived} notes")
    else:
        print("\nDRY RUN — pass --execute to archive candidates")


def _archive_note(cfg, entry):
    Path(cfg.archive_dir).mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    dst = os.path.join(cfg.archive_dir, f"{entry.id}-archived-{date}.md")
    shutil.move(entry.file, dst)


# ── stats ────────────────────────────────────────────────────

def cmd_stats(cfg, args):
    idx = idxmod.read(cfg.index_file)
    now = datetime.now(timezone.utc)

    archive_dir = Path(cfg.archive_dir)
    archived = len([f for f in archive_dir.iterdir() if f.suffix == ".md"]) if archive_dir.exists() else 0

    notes_dir = Path(cfg.memory_dir) / "notes"
    orphans = 0
    if notes_dir.exists():
        indexed = {os.path.basename(n.file) for n in idx.notes}
        orphans = sum(1 for f in notes_dir.iterdir() if f.suffix == ".md" and f.name not in indexed)

    type_counts: dict[str, int] = {}
    entity_set: set[str] = set()
    tag_set: set[str] = set()
    healthy = ok = prune_zone = 0

    for n in idx.notes:
        type_counts[n.type] = type_counts.get(n.type, 0) + 1
        entity_set.update(n.entities)
        tag_set.update(n.tags)

        try:
            mod = datetime.fromisoformat(n.modified.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            mod = now
        days = (now - mod).total_seconds() / 86400
        s = prunemod.score(n.backlink_count, days, cfg.prune.half_life_days)

        if s > 0.50:
            healthy += 1
        elif s >= cfg.prune.min_score:
            ok += 1
        else:
            prune_zone += 1

    if args.json_out:
        json.dump({
            "notes": idx.note_count, "archived": archived, "orphaned": orphans,
            "types": type_counts, "entities": len(entity_set), "tags": len(tag_set),
        }, sys.stdout, indent=2)
        print()
        return

    print(f"Notes:          {idx.note_count}")
    print(f"Archived:       {archived}")
    print(f"Orphaned:       {orphans}")
    print()
    print("By type:")
    for t in cfg.note.valid_types:
        if c := type_counts.get(t, 0):
            print(f"  {t:<14} {c}")
    print()
    print("Score distribution:")
    print(f"  > 0.50   (healthy):    {healthy}")
    print(f"  0.15-0.50 (ok):        {ok}")
    print(f"  < 0.15   (prune zone): {prune_zone}")
    print()
    print(f"Entities: {len(entity_set)} unique")
    print(f"Tags:     {len(tag_set)} unique")


# ── graph ────────────────────────────────────────────────────

def cmd_graph(cfg, args):
    idx = idxmod.read(cfg.index_file)

    by_type: dict[str, list[idxmod.Entry]] = {}
    entities: dict[str, list[str]] = {}
    for n in idx.notes:
        by_type.setdefault(n.type, []).append(n)
        for e in n.entities:
            entities.setdefault(e, []).append(n.title)

    bl_total = sum(n.backlink_count for n in idx.notes)

    print(f"{'═' * 64}")
    print(f"  MEMORY GRAPH  ·  {idx.note_count} notes  ·  {len(entities)} entities  ·  {bl_total} backlinks")
    print(f"{'═' * 64}")

    for t in ["person", "project", "decision", "fact", "reference", "event"]:
        items = by_type.get(t, [])
        if not items:
            continue
        print(f"\n  ┌─ {t.upper()} ({len(items)})")
        for i, n in enumerate(items):
            is_last = i == len(items) - 1
            prefix = "  └─" if is_last else "  ├─"
            detail = "    " if is_last else "  │ "
            ents = ", ".join(n.entities) if n.entities else ""
            tags = ", ".join(n.tags)
            print(f"{prefix} {n.title}")
            if ents:
                print(f"{detail}   ⤷ [{ents}]  #{tags}")
            else:
                print(f"{detail}   ⤷ #{tags}")

    print()
    print("  ┌─ ENTITY INDEX")
    sorted_ents = sorted(entities.items())
    for i, (e, titles) in enumerate(sorted_ents):
        is_last = i == len(sorted_ents) - 1
        prefix = "  └─" if is_last else "  ├─"
        print(f"{prefix} {e:22s} ({len(titles)} notes)")

    print()
    print(f"{'═' * 64}")
