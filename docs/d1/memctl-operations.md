---
title: "memctl Operations Guide"
category: runbook
status: active
created: 2026-03-15
---

# memctl Operations Guide

How to use the memory governance system. This is the operational reference
for any agent or session that needs to read or write structured memory.

Command: `memctl` (installed via `uv sync`, source: `halos/memctl/`)
Config: `memctl.yaml` (repo root)
Index:  `memory/INDEX.md` (auto-maintained, never hand-edit)
Notes:  `memory/notes/*.md` (one claim per file, YAML frontmatter + body)
Spec:   `docs/d2/memctl-spec.md` (canonical, version-controlled)

## Boot Sequence

On session start:

1. Read `memory/INDEX.md`. The MEMORY_INDEX yaml block is your lookup table.
2. For any question that might depend on stored knowledge, scan the index
   by entity intersection, tag intersection, or type filter.
3. Load only matching note files. Do not load the full corpus. Token budget
   matters.
4. If a hash in the index doesn't match the file on disk, run
   `memctl index verify` and report drift before continuing.

## Writing Notes

Always use the CLI. Never write or edit note files directly.

```bash
memctl new \
  --title "Short factual title" \
  --type decision \
  --tags postgres,auth \
  --entities alice,project-alpha \
  --confidence high \
  --body "Single claim. One sentence if possible."
```

Rules:
- One claim per note. Two things to record = two `memctl new` calls.
- Use `--link-to <id>` when the new note references an existing one.
- Unknown tags produce a warning, not an error. Check `memctl.yaml` for
  the controlled vocabulary. Add new tags there if a concept recurs.
- Valid types: `decision`, `fact`, `reference`, `project`, `person`, `event`.
- Valid confidence: `high`, `medium`, `low`.

### When to Write

- A decision was made (type=decision). These are permanent, exempt from pruning.
- A fact was established that matters in future sessions (type=fact).
- A person was introduced with relevant context (type=person). Also prune-exempt.
- A project was scoped or descoped (type=project).
- An external resource needs a durable pointer (type=reference).
- Do NOT write notes for transient conversational context.

### Type Semantics

| Type | Meaning | Pruning |
|------|---------|---------|
| decision | A choice that was made. Immutable, authoritative. | Exempt. |
| fact | Observable state. May become stale over time. | Subject to score. |
| reference | Pointer to external resource. | Subject to score. |
| project | Top-level organisational node. | Subject to score. |
| person | A person entity. | Exempt. |
| event | Something that happened at a point in time. | Subject to score. |

## Reading Notes

When answering questions:
- `type=decision` notes are authoritative. Treat as ground truth.
- `confidence=low` notes should be stated with uncertainty.
- Notes past their `expires` date are stale. State this explicitly.
- If no candidates match, say so. Do not hallucinate memory.

## Commands Reference

```bash
# Write a note
memctl new --title "..." --type fact --tags x,y --body "..."

# Find notes by entity, tag, type, or text
memctl search --entities kai --type decision
memctl search --tags governance,verification
memctl search --text "slopodar"

# Print a specific note
memctl get 20260315-204342

# Verify index integrity (exit code 3 = drift detected)
memctl index verify

# Rebuild index from notes corpus (idempotent, safe any time)
memctl index rebuild

# Add a backlink between notes
memctl link --from <new-id> --to <existing-id>

# Corpus health report
memctl stats

# Visual graph of the memory network
memctl graph

# Identify prune candidates (dry-run by default)
memctl prune
memctl prune --execute   # actually archive (requires dry_run: false in config)
```

## JSON Output

All commands support `--json` as a global flag (must appear before the subcommand):

```bash
memctl --json search --entities kai
memctl --json stats
```

## Index Maintenance

The index at `memory/INDEX.md` is a derived artifact. It is always rebuildable
from the notes corpus via `memctl index rebuild`. The index contains:

- Per-note: id, file path, title, type, tags, entities, summary, SHA256 hash,
  backlink count, modified date, expiry date.
- Corpus-level: entity list, tag vocabulary, note count, generation timestamp.

**Drift** means a note file was modified since the index was last built. The hash
won't match. This is not an error during development (notes are being written),
but should be zero in steady state. Run `memctl index rebuild` to clear drift.

**Orphans** are note files that exist on disk but aren't in the index. Usually
means a note was written outside memctl (which you shouldn't do) or the index
is stale. `memctl index rebuild` fixes this.

## Pruning

Prune score = `backlink_count * exp(-days_since_modified / half_life_days)`.
Notes with 0 backlinks get `recency * 0.5`. Expired notes get score halved.

Exempt from pruning: `type=decision`, `type=person`, notes with backlinks
>= `min_backlinks_to_exempt` (default 1).

Pruning never deletes. It moves notes to `memory/archive/` with a tombstone.
Config defaults to `dry_run: true`. Must be explicitly set to `false` in
`memctl.yaml` AND `--execute` passed on the command line.

## Architecture Notes

- memctl is a Python CLI in the `halos` package (`halos/memctl/`). Install via
  `uv sync`. Single external dependency: pyyaml.
- The agent never edits the index or runs pruning. Those are scripted operations.
- The agent's role: write notes via `memctl new`, read the index, follow the
  lookup protocol.
- All paths in the index are relative to repo root. Run memctl from repo root.
- Config at `memctl.yaml` drives all thresholds. No magic numbers in code.
- Notes are immutable after creation except via `memctl edit` (not yet implemented)
  or direct file modification (which you should not do).
