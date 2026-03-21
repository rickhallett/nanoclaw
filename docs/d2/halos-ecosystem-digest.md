---
title: "The Halos Ecosystem"
category: analysis
status: active
created: 2026-03-21
---

# The Halos Ecosystem

**A personal operating system layer, built for agents.**

---

## What This Is

Halos is a suite of CLI modules that compose into something resembling a personal operating system — not in the kernel sense, but in the "everything you need to manage a life and its projects" sense. Each module is a focused tool that does one thing. Together, they form an expressive runtime layer where an agent can manage work, track habits, monitor infrastructure, process email, produce reports, and maintain memory — all without opening a single GUI application.

The architectural thesis: if 75% of software is GUI chrome over simple data operations, then a personal system built entirely from composable CLI tools should be more powerful, more automatable, and more coherent than any collection of GUI apps could be.

This document is the map.

---

## The Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        Human Interface                          │
│   Telegram · Gmail · Slack · Discord                            │
│   (channels — messages in, responses out)                       │
├─────────────────────────────────────────────────────────────────┤
│                     Briefings & Reports                         │
│   hal-briefing morning/nightly · reportctl digest               │
│   (synthesis layer — pulls from everything below)               │
├─────────────────────────────────────────────────────────────────┤
│                      Dashboard & Views                          │
│   dashctl (TUI/HTML/JSON/text) · nightctl graph                 │
│   (presentation layer — renders data for consumption)           │
├─────────────────────────────────────────────────────────────────┤
│                    Domain Modules                               │
│   nightctl    work tracking, Eisenhower matrix, state machine   │
│   trackctl    personal metrics (zazen, movement, study)         │
│   memctl      structured memory, decay pruning, graph analysis  │
│   mailctl     Gmail operations, triage rules, filter mgmt       │
│   cronctl     cron definitions, crontab generation              │
├─────────────────────────────────────────────────────────────────┤
│                   Observability                                 │
│   logctl      structured log search, fleet aggregation          │
│   agentctl    session tracking, spin detection                  │
│   statusctl   fleet health: service/container/host metrics      │
├─────────────────────────────────────────────────────────────────┤
│                   Operations                                    │
│   halctl      fleet provisioning, session lifecycle, eval       │
│   backupctl   SQLite-safe backup policy, restic/tar backend     │
├─────────────────────────────────────────────────────────────────┤
│                   Foundation                                    │
│   hlog        structured telemetry (all modules emit here)      │
│   SQLite      per-domain data stores (store/*.db)               │
│   YAML        configuration + work items (queue/items/*.yaml)   │
│   Markdown    notes + templates (memory/*.md)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Reference

### Work & Planning

#### nightctl — Unified Work Tracker

The task engine. Items flow through a state machine with Eisenhower quadrant prioritisation.

```bash
nightctl add --title "..." --quadrant q2    # create item
nightctl start <ID>                         # open → in-progress
nightctl review <ID>                        # in-progress → review
nightctl done <ID>                          # review → done
nightctl graph                              # Eisenhower matrix view
nightctl edit <ID> --quadrant q1            # reclassify urgency
```

**States:** open → planning → plan-review → in-progress → review → testing → done
**Branches:** blocked, deferred, cancelled, failed (with transitions back)
**Storage:** YAML files in `queue/items/` — versionable, diffable, greppable.

**Programmatic:** `Item.create()`, `item.transition(status)`, `load_all_items()`, `find_item()`

---

#### cronctl — Scheduled Jobs

Cron job definitions as YAML, with crontab generation.

```bash
cronctl add --title "Morning briefing" --schedule "0 6 * * *" --command "hal-briefing morning"
cronctl list                                # all defined jobs
cronctl enable <ID> / disable <ID>          # toggle
cronctl install --execute                   # write to system crontab
cronctl status                              # job health overview
```

**Programmatic:** `CronJob.create()`, `job.to_crontab_line()`, `_load_all_jobs()`

---

### Personal Metrics

#### trackctl — Habit & Activity Tracker

Pluggable domain tracker. Each domain gets its own SQLite database. Streak logic: any calendar day with >= 1 entry counts. Miss a day, streak resets.

```bash
trackctl domains                            # list: zazen, movement, study-source, study-neetcode, study-crafters
trackctl add zazen --duration 25            # log 25 minutes
trackctl add movement --duration 45 --notes "morning run, 5km"
trackctl streak zazen                       # current: 12, longest: 47, target: 100
trackctl summary                            # all domains at a glance
trackctl list zazen --days 7                # recent entries
```

**Adding a domain:** Create `halos/trackctl/domains/<name>.py`, call `register(name, desc, target)`. Auto-discovers at import.

**Programmatic:** `store.add_entry()`, `engine.compute_streak()`, `engine.text_summary()` → "zazen: 12-day streak (longest: 47) [target: 100, 88 to go] | today: 25min"

---

#### dashctl — TUI Dashboard

RPG character sheet for personal metrics. Renders trackctl domains + nightctl Eisenhower matrix as Rich panels.

```bash
dashctl                                     # single render (Rich TUI)
dashctl --live --interval 10                # auto-refresh
dashctl --json                              # machine-readable export
dashctl --text                              # plain text for agents
dashctl --html --output dashboard.html      # self-contained HTML page
```

**Programmatic:** `panels.full_dashboard()` → list of Rich renderables.

---

### Memory & Knowledge

#### memctl — Structured Memory Governance

Atomic Markdown notes with YAML frontmatter. Decay-based pruning. Entity linking. Graph analysis.

```bash
memctl new --title "..." --type decision --tags "arch,security" --body "..."
memctl search --tags arch --type decision   # find relevant notes
memctl stats                                # corpus health (147 notes, 12 entities, 3 orphans)
memctl prune --execute                      # decay-based garbage collection
memctl graph --clusters                     # knowledge cluster detection
memctl graph --orphans                      # isolated notes needing links
memctl graph --central --top 5              # knowledge hub identification
memctl graph --suggest-links                # proposed cross-references
```

**Note types:** decision, fact, reference, project, person, event
**Confidence levels:** high, medium, low (affects decay rate)
**Storage:** Markdown files in `memory/notes/`, index at `memory/INDEX.md`

**Programmatic:** `notemod.parse()`, `idxmod.rebuild_from_notes()`, `prunemod.score()`, `graph.find_clusters()`

---

### Communication

#### mailctl — Gmail Operations

Gmail operations powered by himalaya (Rust CLI). Deterministic triage rules — no LLM classification.

```bash
mailctl inbox --unread                      # what needs attention
mailctl read <ID>                           # read a message
mailctl search "from:ben subject:project"   # IMAP query syntax
mailctl triage --dry-run                    # preview triage actions
mailctl triage --execute                    # apply triage rules
mailctl send --to kai@example.com --subject "Update" < body.md
mailctl summary                             # "mailctl: 12 unread (3 from ben) | 247 total"
```

**Triage rules:** VIP senders (SURFACE), noise patterns (ARCHIVE), label rules (LABEL). First match wins. All deterministic — no LLM involved (prompt injection risk).

**Filter taxonomy:** jobs, infra, newsletters, commerce, noise → auto-labeled, skip inbox. Unlisted senders stay in inbox.

**Programmatic:** `engine.list_messages()`, `engine.search()`, `triage.run_triage()`, `briefing.text_summary()`

---

#### Channels (NanoClaw core, not halos)

Telegram, Gmail, Slack, Discord — self-registering at startup. Messages route through the orchestrator to container agents. Channels are the human interface; halos modules are the computation layer beneath.

---

### Observability

#### logctl — Structured Log Search

Every halos module emits structured logs via `hlog()`. logctl reads and queries them.

```bash
logctl tail --source nightctl -n 20         # recent nightctl events
logctl errors                               # errors in last 24h
logctl search --text "session" --since 1h   # full-text search
logctl stats                                # volume by source and level
logctl fleet --instance ben --conversations # cross-instance view
logctl usage --since 7d --by model          # token cost breakdown
logctl trace "2026-03-21T14:30:00" --window 60  # correlate events
```

**Programmatic:** `search.read_log_tail()`, `search.filter_entries()`, `fleet.read_fleet_entries()`, `usage.summarize()`

---

#### agentctl — Session Tracking

Tracks container agent sessions. Detects spin (agent stuck in loops), error streaks, and anomalous behavior.

```bash
agentctl ingest                             # parse container logs → session records
agentctl list --group telegram_main         # recent sessions for a group
agentctl stats --since 7d                   # success rate, avg duration, by-group
agentctl alert                              # check for spinning/error patterns
```

**Programmatic:** `ingest()`, `load_sessions()`, `check_alerts()`

---

#### statusctl — Fleet Health Monitor

Unified health check across all subsystems. One command to know if everything's working.

```bash
statusctl                                   # full Rich health report
statusctl check                             # exit 0 if HEALTHY, exit 1 if not
statusctl metrics --json                    # host resource snapshot
statusctl report                            # briefing one-liner
```

**Checks:** systemd service, credential proxy, Docker daemon, container state, agent sessions, error rates, CPU/RAM/disk.
**Grades:** HEALTHY → DEGRADED → DOWN. Critical checks (service, Docker, disk) trigger DOWN; others trigger DEGRADED.

**Programmatic:** `engine.run_all_checks()`, `engine.compute_grade()`, `briefing.text_summary()`

---

### Operations

#### halctl — Fleet Management

Provisions, monitors, and manages microHAL fleet instances.

```bash
halctl create --name ben --personality friendly    # new instance
halctl list                                        # fleet overview
halctl status ben                                  # instance details
halctl freeze ben                                  # preserve state, stop process
halctl fry ben --confirm                           # nuclear delete

halctl session list                                # SDK sessions
halctl session clear telegram_main                 # clear poisoned session
halctl session clear-all --instance ben            # nuclear session reset

halctl assess ben --scenario greeting              # run eval scenario
halctl supervise all --window 30                   # health sweep
```

**Programmatic:** `provision.create_instance()`, `session.clear_session()`, `supervisor.supervise_all()`

---

#### backupctl — Backup Policy

Structured backups for high-value data. SQLite databases are copied via `sqlite3.backup()` (not raw file copy) for consistency.

```bash
backupctl targets                           # list what gets backed up
backupctl run                               # backup all targets
backupctl run --target store                # backup just SQLite databases
backupctl list --target store               # available snapshots
backupctl verify                            # check backup integrity
backupctl restore --target store --snapshot 2026-03-20 --to /tmp/restore
backupctl summary                           # briefing one-liner
```

**Targets:** store (SQLite DBs), memory (note corpus), queue (nightctl items), config (.env, YAML configs).
**Backend:** restic (primary, with dedup/encryption) → tar (fallback).

**Programmatic:** `engine.run_backup()`, `engine.list_snapshots()`, `engine.restore()`

---

### Synthesis

#### briefings — Daily Digests

The synthesis layer. Pulls data from every module, passes to an LLM for narrative synthesis, delivers via channel.

```bash
hal-briefing morning                        # 0600 daily briefing
hal-briefing nightly                        # 2100 evening recap
hal-briefing nightctl                       # 0545 overnight job summary
hal-briefing diary                          # autonomous reflection
hal-briefing checkin-digest                 # Ben's check-in → exec summary
```

**Data sources pulled:** memctl stats, nightctl items, cronctl schedules, logctl errors, agentctl sessions, trackctl summaries, mailctl inbox, calctl schedule, statusctl health.

**Programmatic:** `gather_morning()`, `synthesise()`, `deliver_message()`, `archive_briefing()`

---

#### reportctl — Periodic Reports

Structured data collection without LLM synthesis. Feeds briefings and standalone reports.

```bash
reportctl briefing                          # corpus stats + open work
reportctl weekly                            # 7-day activity summary
reportctl health                            # system health snapshot
reportctl digest --since 24h               # activity digest
```

**Programmatic:** `collectors.collect_memctl()`, `collectors.collect_nightctl()`, `collectors.collect_activity()`

---

## Composition Patterns

The power isn't in any single module. It's in how they compose.

### Morning Briefing Pipeline

```
cronctl (6:00 trigger)
  → hal-briefing morning
    → gather:
        memctl stats          → "147 notes, 3 orphans"
        nightctl items        → "4 tasks: 1 q1, 2 q2, 1 q3"
        calctl today          → "3 events, 2 tasks due"
        trackctl summary      → "zazen: 12-day streak"
        mailctl summary       → "8 unread (2 from ben)"
        statusctl report      → "HEALTHY | CPU 12%"
        logctl errors         → "2 errors in last 12h"
    → synthesise (LLM)        → narrative briefing
    → deliver (Telegram)      → message to Operator
```

### Work Tracking → Dashboard → Briefing

```
nightctl add --title "Fix race condition" --quadrant q1
  → YAML file in queue/items/
  → dashctl reads → Eisenhower panel shows q1 item
  → briefings gather → "1 urgent task"
  → morning briefing → "You have an urgent item: Fix race condition"
```

### Habit Tracking → Dashboard → Briefing

```
trackctl add zazen --duration 25
  → SQLite entry in store/track_zazen.db
  → engine.compute_streak() → {current: 13, longest: 47}
  → dashctl domain_panel → streak bar ████████████░░░░░░░░ 13%
  → engine.text_summary() → "zazen: 13-day streak..."
  → morning briefing includes streak update
```

### Email → Triage → Briefing

```
mailctl triage --execute
  → scan unread inbox
  → apply rules: VIP → SURFACE, noise → ARCHIVE
  → log actions via hlog
  → mailctl summary → "mailctl: 3 unread after triage"
  → morning briefing includes inbox state
```

### Infrastructure Monitoring → Alert → Briefing

```
cronctl (periodic statusctl check)
  → statusctl check
  → if exit 1: logctl records degradation
  → nightly briefing: "statusctl: DEGRADED — disk at 91%"
  → Operator sees it in evening recap
```

### Backup → Verify → Report

```
cronctl (nightly backupctl run)
  → backupctl run
    → sqlite3.backup() for each .db file
    → restic backup for all targets
  → backupctl summary → "last backup: 2h ago, 30 snapshots"
  → morning briefing includes backup status
```

---

## The Telemetry Spine

Every module emits structured events via `hlog(source, level, event, data)`:

```python
hlog("nightctl", "info", "item_created", {"id": "abc123", "title": "Fix bug", "quadrant": "q1"})
hlog("trackctl", "info", "entry_added", {"domain": "zazen", "duration_mins": 25})
hlog("mailctl", "info", "triage_complete", {"archived": 5, "surfaced": 3})
hlog("backupctl", "info", "backup_complete", {"target": "store", "size_bytes": 1234567})
```

logctl reads these events. agentctl detects anomalies in them. briefings synthesise them. The structured log is the nervous system — every action is observable.

---

## Data Architecture

```
store/
  messages.db          # NanoClaw core: messages, sessions, groups
  mail.db              # mailctl: filters, audit log
  track_zazen.db       # trackctl: zazen entries
  track_movement.db    # trackctl: movement entries
  track_study-*.db     # trackctl: study domain entries
  ledger.journal       # ledgerctl: plain-text accounting
  ledger-rules.yaml    # ledgerctl: categorisation rules
  dashboard.html       # dashctl: last HTML export

memory/
  INDEX.md             # memctl: lookup protocol + index
  notes/               # memctl: atomic Markdown notes
  reflections/         # HAL's autonomous journal

queue/
  items/               # nightctl: YAML work items

logs/
  halos.jsonl          # hlog: structured event stream
```

**Storage principle:** SQLite for structured data that needs querying. YAML for configuration and work items that need human readability and git tracking. Markdown for prose content. JSONL for append-only event streams.

---

## What This Adds Up To

Halos isn't a single application. It's a composition of focused tools that, together, give an agent the ability to:

- **Manage work** — create, prioritise, track, and complete tasks (nightctl)
- **Track habits** — log activities, compute streaks, visualise progress (trackctl, dashctl)
- **Remember things** — structured notes with decay, search, and graph analysis (memctl)
- **Process email** — triage, search, send, with deterministic rules (mailctl)
- **See the schedule** — unified view of calendar, tasks, and cron jobs (calctl)
- **Monitor health** — system, container, and agent health at a glance (statusctl, logctl, agentctl)
- **Manage infrastructure** — provision, freeze, evaluate fleet instances (halctl)
- **Protect data** — structured backups with SQLite safety (backupctl)
- **Produce reports** — daily briefings that synthesise everything above (briefings, reportctl)
- **Display it all** — TUI dashboard, HTML export, JSON for programmatic access (dashctl)

Each module is ~500-2500 lines of Python. Each has a CLI entry point, a programmatic API, and (where relevant) a briefing integration one-liner. The total is around 17,000 lines of Python that replace what would otherwise be a dozen GUI applications, none of which talk to each other.

The Unix philosophy — small tools, text interfaces, composable pipelines — turns out to be exactly what agent-native software looks like. Not because anyone planned it that way forty years ago, but because the constraints are the same: when your user operates at the data layer, the data layer is all you need.

---

## Quick Reference

| Module | Command | One-Liner |
|--------|---------|-----------|
| nightctl | `nightctl` | Work tracking + Eisenhower matrix |
| trackctl | `trackctl` | Personal metrics + streak engine |
| memctl | `memctl` | Structured memory + graph analysis |
| cronctl | `cronctl` | Cron definitions + crontab gen |
| mailctl | `mailctl` | Gmail ops + deterministic triage |
| calctl | `calctl` | Unified schedule view |
| logctl | `logctl` | Structured log search + fleet aggregation |
| agentctl | `agentctl` | Session tracking + spin detection |
| statusctl | `statusctl` | Fleet health monitoring |
| halctl | `halctl` | Fleet provisioning + lifecycle |
| backupctl | `backupctl` | Backup policy + SQLite safety |
| dashctl | `dashctl` | TUI/HTML dashboard |
| briefings | `hal-briefing` | Daily digest synthesis |
| reportctl | `reportctl` | Periodic data collection |

**Install:** `uv sync`
**Run all CLIs:** Each is a console_scripts entry point in pyproject.toml.
**Add a domain:** `halos/trackctl/domains/<name>.py` — auto-discovers.
**Add a module:** Copy trackctl pattern: cli.py + engine.py + store.py + briefing.py.
