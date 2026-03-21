# Halo

A personal operating system layer, built for agents.

---

## What This Is

NanoClaw is a suite of composable CLI modules that form a personal operating system — not in the kernel sense, but in the "everything you need to manage a life and its projects" sense. Each module is a focused tool that does one thing. Together, they create an expressive runtime layer where an agent can manage work, track habits, monitor infrastructure, process email, produce reports, and maintain memory — all without a single GUI application.

A single Node.js process connects messaging channels (Telegram, Slack, Discord, Gmail) to Claude agents running in isolated Docker containers. Each agent has its own filesystem, memory, and conversation history. The **halos** Python toolchain wraps everything in structured CLI modules that compose through text, files, and SQLite.

The architectural thesis: if 75% of software is GUI chrome over simple data operations, then a personal system built entirely from composable CLI tools should be more powerful, more automatable, and more coherent than any collection of GUI apps.

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
│   calctl      unified schedule (calendar + tasks + cron)        │
│   ledgerctl   plain-text accounting, bank CSV import            │
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

## Quick Start

```bash
gh repo fork rickhallett/nanoclaw --clone
cd nanoclaw
npm install
cp .env.example .env  # add your ANTHROPIC_API_KEY and TELEGRAM_BOT_TOKEN
npm run build
npm run dev

# Install halos tools
uv sync
```

## Module Reference

### Work & Planning

| Module | Command | What It Does |
|--------|---------|-------------|
| nightctl | `nightctl` | Work tracking with Eisenhower matrix (q1-q4), 13-state machine, overnight execution |
| cronctl | `cronctl` | Cron job definitions as YAML, crontab generation, manual triggering |
| calctl | `calctl` | Unified schedule — Google Calendar + nightctl deadlines + cronctl jobs |

```bash
nightctl add --title "Fix race condition" --quadrant q1
nightctl graph                              # Eisenhower matrix view
calctl today                                # everything happening today
calctl conflicts                            # overlapping commitments
calctl free --duration 60                   # find open 60-min slots
```

### Personal Metrics

| Module | Command | What It Does |
|--------|---------|-------------|
| trackctl | `trackctl` | Habit tracker with pluggable domains, streak engine, daily sums |
| dashctl | `dashctl` | TUI dashboard — RPG character sheet for metrics + Eisenhower view |
| ledgerctl | `ledgerctl` | Plain-text accounting, bank CSV import, categorisation rules |

```bash
trackctl add zazen --duration 25            # log 25 minutes of meditation
trackctl streak zazen                       # current: 12, longest: 47, target: 100
dashctl                                     # full TUI dashboard
dashctl --html --output dashboard.html      # self-contained HTML export
ledgerctl import --bank anz --csv statement.csv
ledgerctl balance                           # P&L by account
```

### Memory & Knowledge

| Module | Command | What It Does |
|--------|---------|-------------|
| memctl | `memctl` | Structured memory — atomic notes, entity linking, decay pruning, graph analysis |

```bash
memctl new --title "..." --type decision --tags "arch,security" --body "..."
memctl search --tags arch --type decision
memctl graph                                # interactive knowledge graph (HTML)
memctl graph --format dot -o graph.svg      # export as SVG via Graphviz
memctl stats                                # corpus health
```

### Communication

| Module | Command | What It Does |
|--------|---------|-------------|
| mailctl | `mailctl` | Gmail via himalaya — inbox, search, triage, filters, send |

```bash
mailctl inbox --unread                      # what needs attention
mailctl triage --execute                    # apply deterministic triage rules
mailctl summary                             # "mailctl: 12 unread (3 from ben) | 247 total"
```

### Observability

| Module | Command | What It Does |
|--------|---------|-------------|
| logctl | `logctl` | Structured log search, fleet aggregation, token usage tracking |
| agentctl | `agentctl` | Session tracking, spin detection, error streaks |
| statusctl | `statusctl` | Fleet health — service, container, agent, and host metrics |

```bash
logctl errors                               # errors in last 24h
logctl usage --since 7d --by model          # token cost breakdown
statusctl                                   # full health report
statusctl check                             # exit 0 if HEALTHY, exit 1 if not
```

### Operations

| Module | Command | What It Does |
|--------|---------|-------------|
| halctl | `halctl` | Fleet provisioning, session lifecycle, eval harness, supervisor |
| backupctl | `backupctl` | Structured backup policy, SQLite-safe snapshots, restic/tar backend |

```bash
halctl create --name ben --personality discovering-ben
halctl session clear telegram_main          # clear poisoned session
backupctl run                               # backup all targets
backupctl verify                            # check integrity
```

### Synthesis

| Module | Command | What It Does |
|--------|---------|-------------|
| briefings | `hal-briefing` | Daily digests — morning, nightly, overnight summary, diary, check-in |
| reportctl | `reportctl` | Periodic data collection — briefing, weekly, health, digest |

```bash
hal-briefing morning                        # 0600 daily briefing
hal-briefing diary                          # autonomous reflection entry
reportctl digest --since 24h               # activity digest
```

## How Modules Compose

The power isn't in any single module. It's in how they compose.

**Morning briefing pipeline:**
```
cronctl (6:00 trigger)
  → hal-briefing morning
    → memctl stats        → "147 notes, 3 orphans"
    → nightctl items      → "4 tasks: 1 q1, 2 q2, 1 q3"
    → calctl today        → "3 events, 2 tasks due"
    → trackctl summary    → "zazen: 12-day streak"
    → mailctl summary     → "8 unread (2 from ben)"
    → statusctl report    → "HEALTHY | CPU 12%"
    → logctl errors       → "2 errors in last 12h"
    → synthesise (LLM)    → narrative briefing
    → deliver (Telegram)  → message to Operator
```

**Habit tracking → dashboard → briefing:**
```
trackctl add zazen --duration 25
  → SQLite entry in store/track_zazen.db
  → dashctl reads → streak bar ████████████░░░░░░░░ 13%
  → briefings gather → "zazen: 13-day streak..."
  → morning briefing includes streak update
```

**Infrastructure monitoring → alert → briefing:**
```
cronctl (periodic statusctl check)
  → statusctl check → if exit 1: degradation logged
  → nightly briefing: "statusctl: DEGRADED — disk at 91%"
```

## The Telemetry Spine

Every module emits structured events via `hlog(source, level, event, data)`. logctl reads them. agentctl detects anomalies. briefings synthesise them. The structured log is the nervous system.

## Data Architecture

```
store/              SQLite databases (per-domain), journal, rules
memory/             Markdown notes (memctl), reflections (diary)
queue/items/        YAML work items (nightctl)
logs/               Structured event stream (hlog → JSONL)
```

**Storage principle:** SQLite for queryable data. YAML for human-readable config and work items. Markdown for prose. JSONL for append-only events.

## Fleet Management

```
~/code/nanoclaw/          HAL-prime (this repo)
~/code/halfleet/
  microhal-ben/           Independent instance (personality: discovering-ben)
  microhal-dad/           Independent instance (personality: The Captain)
  microhal-mum/           Independent instance (personality: warm, minimal)
```

Each fleet instance has its own bot token, personality dimensions, and sandboxed environment. Governance (CLAUDE.md, src/, halos/) is chmod 444/555 — users can't alter their own governance.

## Key Decisions

- **Isolation over convenience.** Agents run in containers, not behind permission checks. Fleet instances can't see prime or each other.
- **Memory is structured.** One claim per note. Backlinks create a graph. Time-decay pruning prevents bloat.
- **No LLM on untrusted input.** Triage rules are deterministic pattern matching. Prompt injection risk rules out LLM classification of external content.
- **The filesystem is the workspace.** IPC is write-then-rename atomicity. State is files, not hidden variables.
- **Assessment before deployment.** Every user gets a Likert pre-assessment. The eval harness tests at machine speed.
- **Scope in agent-minutes.** No wall-clock estimates. "~15 agent-minutes + ~30 human-minutes of review."

## Documentation

```
docs/
├── d1/    Operational — debug checklist, security, diagrams, session patterns
├── d2/    Architecture — specs, requirements, ecosystem digest, research
├── d3/    Deep dives + archive — SDK, Docker, completed plans
```

See [docs/d2/halos-ecosystem-digest.md](docs/d2/halos-ecosystem-digest.md) for the full module API reference and composition patterns.

## Requirements

- Linux or macOS
- Node.js 20+
- Docker
- Python 3.11+ with [uv](https://docs.astral.sh/uv/) (for halos tools)
- [Claude Code](https://claude.ai/download) (for agent SDK)

## License

MIT

## Provenance

Forked from [qwibitai/nanoclaw](https://github.com/qwibitai/nanoclaw). Diverged significantly — fleet management, structured memory, halos toolchain, and the full ecosystem described above are original work.
