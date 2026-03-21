---
title: "MEMCTL — NanoClaw Memory Governance System"
category: spec
status: active
created: 2026-03-15
---

================================================================
MEMCTL — NanoClaw Memory Governance System
Implementation Specification v1.0
================================================================

OVERVIEW
--------
memctl is a Go CLI binary that manages atomic memory notes for a
NanoClaw agent. It maintains a CLAUDE.md index for fast agent
lookup, enforces note schema at write time, detects and reports
index drift via hash verification, and runs scripted pruning/
archival of orphaned or stale notes.

All operations that modify state are scripted (no LLM involvement).
The agent's role is limited to: writing new notes via `memctl new`,
reading the index, and following the lookup protocol defined in
CLAUDE.md. The agent never directly edits the index or runs pruning.

Design invariants:
  - Notes are immutable after creation except via `memctl edit`
  - The index is always derivable from the notes corpus (rebuild is lossless)
  - Pruning never deletes — it archives with a tombstone
  - Config drives all thresholds; no magic numbers in code
  - Every command is safe to run as --dry-run first

================================================================
DIRECTORY STRUCTURE
================================================================

memory/
  notes/          # atomic note files (one claim per file)
  archive/        # pruned notes (tombstoned, not deleted)
  backlinks/      # auto-generated backlink graph (JSON, one per entity)

CLAUDE.md         # agent-facing index (auto-maintained by memctl)
memctl.yaml       # config file
memctl            # compiled binary

================================================================
NOTE FILE FORMAT
================================================================

Filename: {ISO8601-compact}-{slug}.md
Example:  20260315-143022-postgres-chosen-for-auth.md

Every note MUST be parseable as YAML frontmatter + plaintext body.
If it cannot be expressed in this schema, it is not a valid note.

--- SCHEMA ---

---
id: "20260315-143022"          # timestamp, set at creation, immutable
title: "Postgres chosen over MongoDB for auth surface"
type: decision                  # decision | fact | reference | project | person | event
tags:
  - postgres
  - mongodb
  - auth
  - database
entities:                       # named things this note is about
  - alice
  - project-alpha
backlinks:                      # IDs of notes that reference this one (auto-maintained)
  - "20260314-091500"
confidence: high                # high | medium | low
created: "2026-03-15T14:30:22Z"
modified: "2026-03-15T14:30:22Z"
expires: null                   # optional: ISO8601 date after which note is stale
---

Single plaintext sentence or short paragraph stating the claim.
No sub-headings. No lists. If you need a list, it's multiple notes.

--- END SCHEMA ---

Enforcement: `memctl new` validates schema before writing.
Invalid notes are rejected with a descriptive error. The agent
is told exactly what field is missing or malformed.

Valid types and their semantics:
  decision  - a choice that was made (immutable once true)
  fact      - an observable state (may become stale)
  reference - a pointer to an external resource
  project   - a project entity (top-level organisational node)
  person    - a person entity
  event     - something that happened at a point in time

================================================================
CONFIG FILE: memctl.yaml
================================================================

memory_dir: ./memory
index_file: ./CLAUDE.md
archive_dir: ./memory/archive
backlink_dir: ./memory/backlinks

note:
  # Controlled vocabulary for tags — agent must use these.
  # Add new tags here; unknown tags cause a warning, not an error.
  tags:
    - postgres
    - mongodb
    - auth
    - database
    - decision
    - architecture
    - security
    - deadline
    - blocker
    - resolved
    # extend as needed

  valid_types:
    - decision
    - fact
    - reference
    - project
    - person
    - event

  valid_confidence:
    - high
    - medium
    - low

index:
  max_summary_chars: 120        # summary field in CLAUDE.md index entry
  hash_algorithm: sha256        # for drift detection

prune:
  half_life_days: 30            # recency decay half-life
  min_score: 0.15               # notes below this score are archive candidates
  min_backlinks_to_exempt: 1    # notes with >= this many backlinks are never pruned
  dry_run: true                 # SAFETY: must be explicitly set false to execute
  tombstone_retention_days: 90  # how long tombstones stay in archive before deletion

================================================================
CLAUDE.md INDEX FORMAT
================================================================

The CLAUDE.md file has two sections:
  1. LOOKUP PROTOCOL — instructions for the agent (human-readable)
  2. MEMORY_INDEX — machine-parseable YAML block

The agent reads this file on every session start.
The index is updated by memctl, never by the agent directly.

--- CLAUDE.md TEMPLATE ---

# MEMORY INDEX
<!-- AUTO-MAINTAINED BY memctl — DO NOT HAND-EDIT THE YAML BLOCK -->
<!-- Run: memctl index verify   to check for drift              -->
<!-- Run: memctl index rebuild  to regenerate from notes corpus -->

## LOOKUP PROTOCOL

When answering a question that may depend on stored memory:

1. Parse MEMORY_INDEX below. Identify candidate notes by:
   a. entity intersection (does the query mention a known entity?)
   b. tag intersection (does the query map to known tags?)
   c. type filter (decisions? facts? people?)

2. For each candidate, check: does the hash in the index match
   the file? If not, flag drift and re-read the file directly.
   Run `memctl index verify` to surface all drift.

3. Load only the matching note files. Do not load the full corpus.

4. If no candidates match, say so. Do not hallucinate memory.

5. To write a new note: call `memctl new` with structured args.
   Do not write to memory files directly.

6. A note with type=decision is treated as authoritative.
   A note with confidence=low should be stated with uncertainty.
   A note with an expires date in the past should be treated as stale.

## MEMORY_INDEX
```yaml
generated: "2026-03-15T14:30:22Z"
note_count: 47
entities:
  - alice
  - bob
  - project-alpha
  - project-beta
tag_vocabulary:
  - postgres
  - auth
  - database
  - deadline
  # ... full controlled vocab

notes:
  - id: "20260315-143022"
    file: "memory/notes/20260315-143022-postgres-chosen-for-auth.md"
    title: "Postgres chosen over MongoDB for auth surface"
    type: decision
    tags: [postgres, mongodb, auth, database]
    entities: [alice, project-alpha]
    summary: "Chose Postgres. Alice owns auth. JWT expiry 24h."
    hash: "a3f8c2d1e9b74f..."
    backlink_count: 3
    modified: "2026-03-15T14:30:22Z"
    expires: null
```
---

================================================================
memctl CLI SPECIFICATION
================================================================

Binary: memctl
Config: auto-loaded from ./memctl.yaml, or --config flag
All commands print structured output (default: human-readable)
Pass --json for machine-readable output in any command

--- main.go comment block template ---

/*
memctl — NanoClaw memory governance CLI

USAGE
  memctl <command> [flags]

COMMANDS
  new         Write a new atomic note (validates schema)
  get         Print a note by ID or filename
  search      Search notes by tag, entity, type, or text
  index       Index management subcommands
    rebuild   Regenerate CLAUDE.md index from notes corpus
    verify    Hash-check all index entries; report drift
    diff      Show what has changed since last index build
  link        Add a backlink between two notes
  prune       Identify and archive stale/orphaned notes
  stats       Corpus health report
  export      Export notes to JSON or CSV

FLAGS (global)
  --config    Path to memctl.yaml (default: ./memctl.yaml)
  --json      Output as JSON
  --dry-run   Print what would happen without doing it
  --verbose   Include debug output

ENVIRONMENT
  MEMCTL_CONFIG   Override config file path
  MEMCTL_DRY_RUN  Set to "true" to force dry-run globally

CONFIG
  See memctl.yaml. All thresholds are config-driven.
  No magic numbers in binary.

EXIT CODES
  0   Success
  1   Validation error (bad schema, unknown tag, etc.)
  2   File I/O error
  3   Index drift detected (use: memctl index rebuild)
  4   Config error
*/

================================================================
COMMAND SPECIFICATIONS
================================================================

-- memctl new --

PURPOSE: Write a validated atomic note. The agent calls this.
         Never writes files directly.

FLAGS:
  --title         string   Note title (required)
  --type          string   Note type from valid_types (required)
  --tags          strings  Comma-separated tags (required, min 1)
  --entities      strings  Comma-separated entity names (optional)
  --confidence    string   high|medium|low (default: high)
  --body          string   Single-claim body text (required)
  --expires       string   ISO8601 expiry date (optional)
  --link-to       string   ID of note this links back to (optional)

BEHAVIOUR:
  1. Validate all fields against schema and controlled vocabulary
  2. Warn (not error) on unknown tags — suggest nearest match
  3. Generate ID from current timestamp
  4. Generate filename from ID + slugified title
  5. Write file to memory/notes/
  6. Update backlinks: if --link-to provided, append this note's
     ID to the target note's backlinks field
  7. Update MEMORY_INDEX entry in CLAUDE.md (append only)
  8. Print: note ID, filename, any tag warnings

OUTPUT (--json):
  {
    "id": "20260315-143022",
    "file": "memory/notes/20260315-143022-postgres-chosen-for-auth.md",
    "warnings": ["unknown tag 'foobar' — nearest: 'database'"]
  }

EXAMPLE:
  memctl new \
    --title "Postgres chosen over MongoDB for auth surface" \
    --type decision \
    --tags postgres,mongodb,auth,database \
    --entities alice,project-alpha \
    --confidence high \
    --body "Chose Postgres for auth. Alice owns this surface. JWT expiry set to 24h."


-- memctl search --

PURPOSE: Search notes by tag, entity, type, or full-text.
         Returns file paths — agent then reads files directly.
         Does NOT load file content. Stays token-efficient.

FLAGS:
  --tags        strings   Match notes containing ALL of these tags
  --entities    strings   Match notes referencing ANY of these entities
  --type        string    Filter by note type
  --text        string    Full-text search in title and body
  --since       string    ISO8601 — only notes modified after this date
  --expired                Include notes past their expires date
  --limit       int        Max results (default: 20)

OUTPUT:
  List of matching file paths, one per line.
  With --json: array of index entries (no file body).

EXAMPLE:
  memctl search --entities alice --type decision
  # Returns paths to all decision notes about alice


-- memctl index rebuild --

PURPOSE: Regenerate CLAUDE.md MEMORY_INDEX from scratch.
         Safe to run any time. Idempotent.

BEHAVIOUR:
  1. Walk memory/notes/
  2. Parse each note's frontmatter
  3. Compute SHA256 hash of file content
  4. Truncate note body to max_summary_chars for summary field
  5. Write fresh MEMORY_INDEX block to CLAUDE.md
  6. Preserve LOOKUP PROTOCOL section (never overwrites it)
  7. Print: notes processed, time taken, any parse errors

FLAGS:
  --dry-run    Show what would be written without writing


-- memctl index verify --

PURPOSE: Hash-check all index entries against current file content.
         Reports drift. Non-zero exit if any drift found.

BEHAVIOUR:
  1. For each entry in MEMORY_INDEX, compute hash of current file
  2. Compare against stored hash
  3. Report: MATCH | DRIFT | MISSING (file deleted) | ORPHAN (file exists, not in index)
  4. Suggest remediation: `memctl index rebuild` or `memctl new`

OUTPUT:
  MATCH   20260315-143022  postgres-chosen-for-auth.md
  DRIFT   20260314-091500  alice-owns-auth.md  (file modified since index)
  ORPHAN  20260316-120000  new-unindexed-note.md

Exit code 3 if any DRIFT or MISSING found.
Exit code 0 if all MATCH (ORPHAN is a warning, not an error).


-- memctl link --

PURPOSE: Add a backlink between two notes.
         The agent calls this when it creates a note that
         references an existing one.

FLAGS:
  --from    string   ID of the note doing the referencing (required)
  --to      string   ID of the note being referenced (required)

BEHAVIOUR:
  1. Append --from ID to the backlinks field of --to note
  2. Recompute hash, update index entry
  3. Print confirmation

EXAMPLE:
  memctl link --from 20260315-143022 --to 20260314-091500


-- memctl prune --

PURPOSE: Identify and archive notes below the prune score threshold.
         ALWAYS defaults to --dry-run. Explicit --execute required.
         Never deletes — moves to archive/ with tombstone.

PRUNE SCORE ALGORITHM:
  recency = exp(-days_since_modified / half_life_days)
  score   = backlink_count * recency

  If backlink_count >= min_backlinks_to_exempt: exempt (never pruned)
  If score < min_score: archive candidate

  Special cases:
    type=decision: exempt regardless of score (decisions are permanent)
    type=person:   exempt regardless of score
    expired=true:  score halved (faster path to archival)

FLAGS:
  --dry-run    Print candidates without acting (DEFAULT)
  --execute    Actually archive candidates (requires explicit flag)
  --since      Only consider notes older than this date
  --min-score  Override config threshold for this run

BEHAVIOUR (--execute):
  1. For each archive candidate:
     a. Move file to memory/archive/{id}-archived-{date}.md
     b. Write tombstone entry to MEMORY_INDEX:
        status: archived
        archived_at: ISO8601
        reason: score={n} below threshold={n}
     c. Remove full index entry; replace with tombstone
  2. Print: n notes archived, n exempt, n below threshold

OUTPUT (--dry-run):
  CANDIDATE  20260301-100000  old-mongodb-note.md  score=0.04  (threshold=0.15)
  EXEMPT     20260315-143022  postgres-decision.md  type=decision
  CANDIDATE  20260228-090000  stale-fact.md  score=0.09  expired=true


-- memctl stats --

PURPOSE: Corpus health report. Run periodically or before pruning.

OUTPUT:
  Notes:          47
  Archived:       12
  Orphaned:        2  (not in index — run: memctl index rebuild)
  Drifted:         1  (modified since index — run: memctl index verify)

  By type:
    decision        18
    fact            14
    reference        7
    project          4
    person           3
    event            1

  Score distribution:
    > 0.50   (healthy):   31
    0.15–0.50 (ok):       10
    < 0.15   (prune zone): 6

  Entities: 14 unique
  Tags:     23 unique (3 outside controlled vocabulary)

  Oldest note:   20260201-080000 (43 days)
  Last modified: 20260315-143022 (today)

================================================================
CRON / AUTOMATION
================================================================

Suggested crontab entries (adjust paths):

# Verify index every 6 hours — exit code 3 triggers notification
0 */6 * * *  /path/to/memctl index verify --json >> /var/log/memctl-verify.log

# Stats report daily
0 9 * * *    /path/to/memctl stats --json >> /var/log/memctl-stats.log

# Prune dry-run weekly — review output before running --execute
0 10 * * 1   /path/to/memctl prune --dry-run --json >> /var/log/memctl-prune.log

# Full rebuild weekly as belt-and-braces
0 2 * * 0    /path/to/memctl index rebuild

================================================================
CLAUDE.md AGENT INSTRUCTIONS (complete section)
================================================================

Paste this as the LOOKUP PROTOCOL section of CLAUDE.md:

---

## HOW TO USE MEMORY

### Writing a note
Always use memctl. Never write to memory files directly.

  memctl new \
    --title "Short factual title" \
    --type [decision|fact|reference|project|person|event] \
    --tags tag1,tag2 \
    --entities entity1,entity2 \
    --confidence [high|medium|low] \
    --body "Single claim. One sentence if possible."

One claim per note. If you need to record two things, run memctl new twice.

Use --link-to <id> if the new note references an existing one.
After writing, run: memctl index verify

### Reading memory
1. Scan MEMORY_INDEX below for candidates by entity + tag intersection
2. Load only matching files — do not load the full corpus
3. Check: does the hash in the index match the file?
   If not: run `memctl index verify` and report drift before continuing
4. type=decision notes are authoritative
5. confidence=low notes should be stated with uncertainty
6. Notes past their expires date are stale — state this explicitly

### What you must not do
- Do not hand-edit CLAUDE.md or any note file
- Do not invent backlinks — use memctl link
- Do not prune or archive notes — that is a scripted job
- Do not write notes with multiple claims

### When to write a note
- A decision was made → type=decision
- A fact was established that will matter in future sessions → type=fact
- A person was introduced with relevant context → type=person
- A project was scoped or descoped → type=project
- Do not write notes for transient conversational context

---

================================================================
IMPLEMENTATION NOTES FOR GO BINARY
================================================================

Package structure:

  cmd/
    root.go         cobra root command, global flags
    new.go          memctl new
    get.go          memctl get
    search.go       memctl search
    index.go        index subcommand group
    link.go         memctl link
    prune.go        memctl prune
    stats.go        memctl stats
    export.go       memctl export

  internal/
    note/
      note.go       Note struct, parse/validate/write
      schema.go     schema validation
      slug.go       title → filename slug
    index/
      index.go      CLAUDE.md index read/write
      hash.go       SHA256 helpers
      drift.go      drift detection logic
    prune/
      score.go      prune score algorithm
      archive.go    archive/tombstone operations
    config/
      config.go     memctl.yaml loading and validation
    output/
      output.go     human-readable and --json output helpers

Dependencies (keep minimal):
  github.com/spf13/cobra       CLI framework
  github.com/spf13/viper       Config loading
  gopkg.in/yaml.v3             YAML parsing
  crypto/sha256                stdlib, no external dep needed

Build:
  go build -o memctl ./cmd/
  CGO_ENABLED=0 for static binary (important for container contexts)

================================================================
END OF SPEC
================================================================
