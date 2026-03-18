<p align="center">
  <img src="assets/nanoclaw-logo.png" alt="NanoClaw" width="400">
</p>

<p align="center">
  Personal AI assistant with containerised agents, fleet management, and structured memory.
</p>

---

## What This Is

NanoClaw is a personal AI infrastructure layer. A single Node.js process connects messaging channels (Telegram, WhatsApp, Slack, Discord) to Claude agents running in isolated Docker containers. Each agent has its own filesystem, memory, and conversation history.

This fork extends the original with:

- **Fleet management** — HAL-prime spawns and maintains independent instances for non-technical users, each with its own bot token, personality, and sandboxed environment
- **Structured memory** — `memctl` governs durable knowledge with atomic notes, backlink graphs, and time-decay pruning
- **Personality engine** — YAML-driven dimension profiles (brevity, warmth, opinion strength) compose into per-user CLAUDE.md governance
- **Assessment system** — Pre/post Likert and qualitative instruments with bot-level onboarding, three-strike relent, and multi-turn dialogue eval harness
- **halos toolchain** — Python CLI modules for memory, work tracking, fleet ops, briefings, and agent telemetry

## Architecture

```
Telegram ──→ Bot (grammY) ──→ Onboarding gate ──→ SQLite ──→ Message loop ──→ Container (Claude SDK) ──→ Response
                                                                                    ↓
                                                                          Credential proxy ──→ Anthropic API
```

Single process. Channels self-register at startup. Agents execute in Docker containers with mount-based isolation. Fleet instances share prime's credential proxy on port 3001 — containers never see raw tokens.

```
~/code/nanoclaw/          HAL-prime (this repo)
~/code/halfleet/
  microhal-ben/           Independent instance (discovering-ben personality)
  microhal-dad/           Independent instance (The Captain — retired 737 pilot)
  microhal-mum/           Independent instance (warm, minimal, overwhelm-aware)
```

See [docs/d1/architecture-diagrams.md](docs/d1/architecture-diagrams.md) for mermaid diagrams of the full system.

## Quick Start

```bash
gh repo fork rickhallett/nanoclaw --clone
cd nanoclaw
npm install
cp .env.example .env  # add your CLAUDE_CODE_OAUTH_TOKEN and TELEGRAM_BOT_TOKEN
npm run build
npm run dev
```

## Fleet Management

```bash
uv sync                                    # install halos tools
halctl create --name ben --personality discovering-ben
halctl list                                # audit table with bot IDs, groups, notes
halctl push --all                          # push governance updates to fleet
halctl smoke money                         # tier 2 smoke test (15 checks)
halctl assess money                        # eval harness (8 scenarios incl. dialogue)
```

## halos Modules

| Module | Command | Purpose |
|--------|---------|---------|
| memctl | `memctl` | Structured memory: notes, backlinks, pruning, graph visualisation |
| nightctl | `nightctl` | Work tracker: tasks, jobs, agent-jobs with 13-state machine |
| halctl | `halctl` | Fleet management: create, push, freeze, fold, fry, smoke, assess |
| cronctl | `cronctl` | Cron job definitions and crontab generation |
| logctl | `logctl` | Structured log reader and search |
| reportctl | `reportctl` | Periodic digests from halos ecosystem |
| agentctl | `agentctl` | LLM session tracking and spin detection |
| briefings | `hal-briefing` | Cron-driven daily Telegram digests |

## Documentation

```
docs/
├── d1/    Operational — debug checklist, security, diagrams, briefings, session patterns
├── d2/    Architecture — specs, requirements, research, capability maps
├── d3/    Deep dives + archive — SDK, Docker, completed plans
```

Run `python3 docs-audit.py` for a repeatable snapshot of docs health.

## Key Decisions

- **Isolation over convenience.** Agents run in containers, not behind permission checks. Fleet instances can't see prime or each other.
- **Governance is filesystem-locked.** CLAUDE.md, .claude/, src/, halos/ are chmod 444/555 on fleet instances. Users can't alter their own governance.
- **Memory is structured.** One claim per note. Backlinks create a graph. Time-decay pruning prevents bloat. The index is the source of truth.
- **Assessment before deployment.** Every user gets a Likert pre-assessment. Qualitative questions drop in after rapport builds. The eval harness tests all of this at machine speed.
- **Scope in agent-minutes.** No wall-clock estimates. "~15 agent-minutes + ~30 human-minutes of review."

## Requirements

- Linux or macOS
- Node.js 20+
- Docker
- Python 3.11+ with uv (for halos tools)
- [Claude Code](https://claude.ai/download) (for agent SDK)

## License

MIT

## Provenance

Forked from [qwibitai/nanoclaw](https://github.com/qwibitai/nanoclaw). Diverged significantly — fleet management, structured memory, personality engine, assessment system, and eval harness are original work.
