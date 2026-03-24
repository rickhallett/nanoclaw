# Halo

A personal operating system layer, built for agents.

---

## What This Is

Halo is a monorepo containing three systems that compose into a single personal infrastructure:

```
halo/
├── gateway/     Message gateway — routes Telegram, Gmail to Claude agents in containers
├── halos/       Life-management CLIs — 17 tools for work, finance, health, memory
├── agent/       macOS computer-use — GUI automation, terminal control, job server
```

A single Node.js process connects messaging channels to Claude agents running in isolated Docker containers. Each agent has its own filesystem, memory, and conversation history. The **halos** Python toolchain provides structured CLI modules that compose through text, files, and SQLite. The **agent** toolkit gives those agents eyes and hands on macOS.

The architectural thesis: if 75% of software is GUI chrome over simple data operations, then a personal system built entirely from composable CLI tools should be more powerful, more automatable, and more coherent than any collection of GUI apps.

## The Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        Human Interface                          │
│   Telegram · Gmail · Slack · Discord · Hermes CLI               │
├─────────────────────────────────────────────────────────────────┤
│                     gateway/ (TypeScript)                        │
│   Channel routing · Container orchestration · Credential proxy  │
│   Group isolation · Session management · Fleet provisioning     │
│   Containers get: halos CLIs, Claude agent, sandboxed filesystem│
├─────────────────────────────────────────────────────────────────┤
│                     agent/ (Swift + Python) ⚠ macOS host only   │
│   steer: GUI automation (screenshot, OCR, click, type, hotkey)  │
│   drive: terminal control (tmux sessions, parallel execution)   │
│   listen: job server (HTTP → agent on host) · direct: CLI client│
├─────────────────────────────────────────────────────────────────┤
│                     halos/ (Python) — available everywhere       │
│   nightctl · calctl · trackctl · ledgerctl · mailctl · memctl   │
│   cronctl · halctl · dashctl · statusctl · logctl · reportctl   │
│   briefings · agentctl · backupctl · blogctl · carnivorectl     │
├─────────────────────────────────────────────────────────────────┤
│                     Foundation                                   │
│   SQLite (per-domain) · YAML (config + work items) · Markdown   │
│   hlog telemetry · filesystem-as-IPC                            │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone
gh repo fork rickhallett/halo --clone
cd halo

# Gateway (TypeScript — message routing + containers)
cd gateway && npm install && npm run build && cd ..

# Halos (Python — CLI tools)
uv sync

# Configure
cp .env.example .env   # add TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY, etc.

# Run
cd gateway && npm run dev        # start gateway
uv run dashctl                   # halos dashboard
uv run nightctl add --title "Ship it" --quadrant q1
```

## Module Overview

### gateway/ — Message Gateway

TypeScript · ~10,700 LOC · [README →](gateway/README.md)

Routes messages from Telegram, Gmail (and Slack, Discord, WhatsApp via plugins) to Claude agents running in Docker containers. Handles credential proxying, group isolation, session management, and fleet provisioning.

### halos/ — Life-Management CLIs

Python · 17 CLI tools · [README →](halos/README.md)

| Category | Modules | Purpose |
|----------|---------|---------|
| Work & Planning | nightctl, cronctl, calctl | Task tracking, scheduling, unified calendar |
| Personal Metrics | trackctl, dashctl, ledgerctl | Habits, dashboard, finances |
| Memory & Knowledge | memctl | Structured notes, entity linking, graph analysis |
| Communication | mailctl | Gmail triage, filters, send |
| Observability | logctl, agentctl, statusctl | Logs, sessions, fleet health |
| Operations | halctl, backupctl | Fleet provisioning, backups |
| Synthesis | hal-briefing, reportctl | Daily briefings, periodic digests |

### agent/ — macOS Computer-Use

Swift + Python · [README →](agent/README.md)

Gives AI agents full control of macOS — clicking buttons, reading screens via OCR, typing into apps, and orchestrating terminals via tmux. **Requires direct macOS host access** — these tools run on the Mac Mini via the Listen job server, not inside gateway containers.

| Tool | Language | Purpose |
|------|----------|---------|
| steer | Swift | 14 GUI commands (see, click, type, hotkey, OCR, scroll, drag, find...) |
| drive | Python | 6 tmux commands (session, run, send, logs, poll, fanout) |
| listen | Python | FastAPI job server — accepts prompts, spawns Claude agents on the host |
| direct | Python | CLI client for listen |

## How Modules Compose

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
    → synthesise (LLM)    → narrative briefing
    → deliver (Telegram)  → message to Operator
```

**Telegram → containerised agent:**
```
Telegram message → gateway routes → container spawns Claude agent
  → agent reads CLAUDE.md (knows about halos tools)
  → agent runs: nightctl add --title "Found bug in header"
  → agent runs: memctl search --tags arch
  → agent responds via Telegram
```

**Mac Mini computer-use (via Listen server, not containers):**
```
POST /job "Open Safari and screenshot HN"
  → Listen spawns Claude agent on the Mac Mini
  → agent runs: steer see --app Safari (screenshot — requires macOS)
  → agent runs: steer ocr --app Safari (read text — requires macOS)
  → agent runs: drive run --session dev "npm test" (tmux — requires host)
  → job result returned via GET /job/{id}
```

Note: steer and drive require direct macOS access (Accessibility, Screen
Recording, tmux). They are not available inside gateway containers — only
on the Mac Mini host via the Listen job server.

## Data Architecture

```
store/              SQLite databases (per-domain)
memory/             Markdown notes (memctl), reflections
queue/items/        YAML work items (nightctl)
cron/jobs/          YAML cron definitions
logs/               Structured event stream (hlog → JSONL)
templates/          Personality templates for fleet instances
```

Storage principle: SQLite for queryable data. YAML for human-readable config. Markdown for prose. JSONL for append-only events.

## Key Decisions

- **Isolation over convenience.** Agents run in containers. Fleet instances can't see each other.
- **The filesystem is the API.** Gateway (TS) and halos (Python) share no imports — YAML files and directory conventions are the interface.
- **Memory is structured.** One claim per note. Backlinks form a graph. Time-decay pruning prevents bloat.
- **No LLM on untrusted input.** Triage rules are deterministic pattern matching.
- **Assessment before deployment.** Fleet users get Likert pre-assessment. Eval harness tests at machine speed.

## Requirements

- Linux or macOS (agent/ requires macOS)
- Node.js 20+ (gateway)
- Docker (container runtime)
- Python 3.11+ with [uv](https://docs.astral.sh/uv/) (halos)
- [Claude Code](https://claude.ai/download) (agent SDK)

## License

MIT

## Provenance

Forked from [qwibitai/nanoclaw](https://github.com/qwibitai/nanoclaw). Diverged significantly — the monorepo structure, fleet management, halos toolchain, agent computer-use integration, and full ecosystem are original work.
