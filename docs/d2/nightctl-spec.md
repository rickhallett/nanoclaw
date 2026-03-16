================================================================
nightctl — halOS Overnight Batch Processing Module
Implementation Specification v1.0
================================================================

OVERVIEW
--------
nightctl is a Python CLI module of halOS that manages a queue of
deferred jobs for overnight (or windowed) execution. It mirrors
memctl's design philosophy: atomic filesystem units, YAML-first
schema, config-driven thresholds, dry-run by default, agent-driven
job creation.

Jobs are created by the agent at runtime via `nightctl enqueue`.
The executor (`nightctl run`) is a scripted operation, not agent-driven.
Notifications on failure are sent via the halOS messaging layer.

Design invariants:
  - One job = one YAML file in queue/jobs/
  - Jobs are immutable after enqueue (no in-place edits)
  - Execution records are written to queue/runs/ (never modify job files)
  - Serial execution by default (configurable)
  - Dry-run available on all mutating commands
  - Archive not delete — completed/failed jobs move to queue/archive/
  - Config drives all thresholds; no magic numbers in code
  - MANIFEST.yaml is a derived artifact, always rebuildable

================================================================
DIRECTORY STRUCTURE
================================================================

queue/
  jobs/         # pending and claimed job files
  runs/         # execution records (output, timing, exit code)
  archive/      # completed/failed jobs past retention window
  MANIFEST.yaml # derived index, rebuilt by nightctl manifest rebuild

nightctl.yaml   # config
tools/nightctl/
  nightctl      # CLI entrypoint (Python)
  nightctl_lib/
    __init__.py
    cli.py
    job.py      # Job schema, parse, validate, write
    executor.py # run loop, serial/parallel modes
    manifest.py # MANIFEST.yaml read/write/rebuild
    notify.py   # failure notifications via halOS messaging
    archive.py  # archive/tombstone operations
    config.py   # nightctl.yaml loading

================================================================
JOB FILE FORMAT
================================================================

Filename: {ISO8601-compact}-{slug}.yaml
Example:  20260315-220000-rebuild-memctl-index.yaml

Every job MUST be parseable as a flat YAML document.

--- SCHEMA ---

id: "20260315-220000"
title: "Rebuild memctl index"
command: "tools/memctl/memctl index rebuild"
schedule: overnight         # overnight | immediate | once
window: "02:00-05:00"       # local time window (HH:MM-HH:MM)
priority: 1                 # lower number = higher priority
depends_on: []              # list of job IDs that must be done first
retries: 2                  # attempts before marking failed
timeout_secs: 300
tags: [maintenance, memctl]
entities: []                # optional: named things this job relates to
created: "2026-03-15T22:00:00Z"
created_by: "agent"         # agent | manual
status: pending             # pending | claimed | running | done | failed

--- END SCHEMA ---

Valid schedule values:
  overnight  - run within configured overnight window
  immediate  - run at next executor cycle regardless of time
  once       - run once then archive (default for all agent-created jobs)

Valid status values:
  pending    - waiting to be claimed by executor
  claimed    - executor has reserved this job (prevents double-run)
  running    - actively executing
  done       - completed successfully
  failed     - exhausted retries

================================================================
CONFIG FILE: nightctl.yaml
================================================================

queue_dir: ./queue
manifest_file: ./queue/MANIFEST.yaml
archive_dir: ./queue/archive
runs_dir: ./queue/runs

execution:
  mode: serial                   # serial | parallel
  max_workers: 1                 # only relevant if mode=parallel
  overnight_window: "02:00-05:00"  # default window for schedule=overnight
  timezone: "Europe/London"

job:
  default_retries: 2
  default_timeout_secs: 300
  default_schedule: overnight
  valid_schedules:
    - overnight
    - immediate
    - once
  valid_tags:
    - maintenance
    - memctl
    - data
    - sync
    - report
    - cleanup
    - backup
    - infra

notify:
  on_failure: true
  on_success: false              # set true for verbose mode
  channel: main                  # halOS group to notify

manifest:
  hash_algorithm: sha256

archive:
  retention_days: 30             # archive entries older than this are eligible for hatch
  dry_run: true                  # safety: must be set false + --execute to act

================================================================
RUN RECORD FORMAT
================================================================

Filename: {job-id}-run-{attempt}.yaml
Example:  20260315-220000-run-1.yaml

id: "20260315-220000"
attempt: 1
started: "2026-03-16T02:03:11Z"
finished: "2026-03-16T02:03:44Z"
exit_code: 0
stdout: "..."
stderr: ""
duration_secs: 33
outcome: done                    # done | failed | timeout

================================================================
MANIFEST FORMAT
================================================================

File: queue/MANIFEST.yaml

generated: "2026-03-16T02:00:00Z"
job_count: 12
pending: 4
done: 7
failed: 1

jobs:
  - id: "20260315-220000"
    file: "queue/jobs/20260315-220000-rebuild-memctl-index.yaml"
    title: "Rebuild memctl index"
    schedule: overnight
    priority: 1
    status: done
    tags: [maintenance, memctl]
    created: "2026-03-15T22:00:00Z"
    hash: "a3f8c2d1e9b74f..."

================================================================
nightctl CLI SPECIFICATION
================================================================

Binary: tools/nightctl/nightctl
Config: auto-loaded from ./nightctl.yaml, or --config flag
All commands support --json and --dry-run

COMMANDS:
  enqueue     Create a new job (agent-facing)
  list        List jobs by status, tag, schedule
  status      Print a specific job and its run records
  run         Execute pending jobs within the active window
  cancel      Mark a pending job as cancelled (moves to archive)
  manifest    Manifest subcommands
    rebuild   Regenerate MANIFEST.yaml from jobs corpus
    verify    Hash-check manifest entries
  archive     Archive done/failed jobs past retention
  hatch       Permanently eject archived jobs (destructive, explicit only)
  stats       Queue health report

FLAGS (global):
  --config    Path to nightctl.yaml (default: ./nightctl.yaml)
  --json      Output as JSON
  --dry-run   Print what would happen without doing it
  --verbose   Include debug output

EXIT CODES:
  0   Success
  1   Validation error
  2   File I/O error
  3   Manifest drift detected
  4   Config error
  5   Job failed during execution

================================================================
COMMAND SPECIFICATIONS
================================================================

-- nightctl enqueue --

PURPOSE: Create a new job. The agent calls this. Never writes files directly.

FLAGS:
  --title         string    Job title (required)
  --command       string    Shell command to execute (required)
  --schedule      string    overnight | immediate | once (default: overnight)
  --window        string    Override time window HH:MM-HH:MM (optional)
  --priority      int       Execution priority, lower = sooner (default: 5)
  --depends-on    strings   Comma-separated job IDs (optional)
  --retries       int       Override default retry count (optional)
  --timeout       int       Override timeout in seconds (optional)
  --tags          strings   Comma-separated tags (optional)
  --entities      strings   Comma-separated entity names (optional)

BEHAVIOUR:
  1. Validate all fields
  2. Generate ID from current timestamp
  3. Generate filename from ID + slugified title
  4. Write to queue/jobs/
  5. Append entry to MANIFEST.yaml
  6. Print: job ID, filename, scheduled window

EXAMPLE:
  nightctl enqueue \
    --title "Rebuild memctl index" \
    --command "tools/memctl/memctl index rebuild" \
    --schedule overnight \
    --tags maintenance,memctl \
    --priority 1


-- nightctl run --

PURPOSE: Execute pending jobs. Scripted operation, not agent-driven.
         Respects the overnight window unless --force is passed.

FLAGS:
  --force      Ignore window check, run now
  --limit      int   Max jobs to run in this cycle (default: unlimited)
  --dry-run    List what would run without executing

BEHAVIOUR:
  1. Check current time is within overnight_window (skip if not, unless --force)
  2. Load MANIFEST.yaml, filter status=pending, sorted by priority then created
  3. Resolve depends_on — skip jobs whose dependencies are not done
  4. For each job (serial by default):
     a. Mark status=claimed in job file + manifest
     b. Mark status=running
     c. Execute command with timeout
     d. Write run record to queue/runs/
     e. On success: mark status=done
     f. On failure: decrement retries; if retries exhausted mark status=failed,
        trigger notify; else reset to pending for next cycle
  5. Print summary: n done, n failed, n skipped (window/deps)


-- nightctl list --

FLAGS:
  --status    Filter by status (pending|running|done|failed)
  --tags      Filter by tag
  --schedule  Filter by schedule type
  --limit     int (default: 20)

OUTPUT:
  ID                  TITLE                          STATUS    PRI  SCHEDULE
  20260315-220000     Rebuild memctl index           done      1    overnight
  20260315-220001     Sync data exports              pending   5    overnight


-- nightctl status <id> --

PURPOSE: Print job file and all associated run records.

OUTPUT:
  Job:    20260315-220000
  Title:  Rebuild memctl index
  Status: done
  Runs:
    attempt 1 — done — 33s — exit 0


-- nightctl cancel <id> --

PURPOSE: Cancel a pending job. Moves to archive with status=cancelled.
         Cannot cancel a running job.


-- nightctl manifest rebuild --

PURPOSE: Regenerate MANIFEST.yaml from jobs corpus. Idempotent, safe any time.

BEHAVIOUR:
  1. Walk queue/jobs/
  2. Parse each job file
  3. Compute hash
  4. Write fresh MANIFEST.yaml
  5. Print: jobs processed, any parse errors


-- nightctl archive --

PURPOSE: Move done/failed jobs past retention_days to queue/archive/.
         Defaults to dry-run.

FLAGS:
  --execute    Actually move files (requires explicit flag)
  --since      Only consider jobs older than this date


-- nightctl hatch --

PURPOSE: Permanently eject (delete) archived jobs.
         Destructive. Requires --execute AND archive.dry_run=false in config.
         This is the only delete operation in nightctl.

FLAGS:
  --execute    Required. Will not run without it.
  --before     ISO8601 date — only eject archived before this date


-- nightctl stats --

OUTPUT:
  Jobs (queue):    12
    pending:        4
    running:        0
    done:           7
    failed:         1
  Archived:         8

  By schedule:
    overnight      10
    immediate       1
    once            1

  By tag:
    maintenance     5
    memctl          3
    data            4

  Next window:  02:00-05:00 local (4h 17m away)
  Last run:     2026-03-15T02:03:44Z (12 jobs, 0 failed)

================================================================
NOTIFICATION BEHAVIOUR
================================================================

On job failure (after retries exhausted):
  - Call halOS send_message with channel=main (or configured channel)
  - Message includes: job ID, title, command, exit code, last stderr snippet
  - Format follows halOS message formatting rules (no markdown)

On success (if notify.on_success=true):
  - Send brief completion summary at end of run cycle

================================================================
RELATIONSHIP TO memctl
================================================================

nightctl and memctl are peer modules of halOS. They share:
  - Filesystem-first, no database
  - YAML schema with controlled vocabulary
  - Derived manifest/index as single source of truth
  - CLI-driven writes, never direct file edits
  - Archive not delete (except hatch/jettison)
  - Config-driven, dry-run by default

nightctl does NOT use memctl for storage. They are independent.
However, nightctl jobs can invoke memctl commands (e.g. index rebuild).

================================================================
CRON / AUTOMATION
================================================================

# Run overnight jobs at 02:05 local (slight offset from window start)
5 2 * * *    /path/to/nightctl run >> /var/log/nightctl-run.log

# Archive old completed jobs weekly
0 3 * * 0    /path/to/nightctl archive --execute

# Stats report daily
7 9 * * *    /path/to/nightctl stats --json >> /var/log/nightctl-stats.log

# Manifest verify every 6 hours
0 */6 * * *  /path/to/nightctl manifest verify

================================================================
END OF SPEC
================================================================
