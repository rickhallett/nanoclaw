---
title: "microHAL PoC — Specification"
category: spec
status: active
created: 2026-03-17
---

# microHAL PoC — Specification

> "It just works." — the entire UX requirement.
> "All data belongs to me." — the entire legal requirement.

## Goal

HAL-prime spawns and maintains fully independent HAL instances for non-technical users, delivered via Telegram. Each microHAL is a separate nanoclaw deployment with its own repo clone, bot token, and process — completely unable to touch prime soil. Fleet management and code updates flow one-way from HAL-prime. Research instrumentation from day one.

## Architecture Decision

**REVISED: Fully independent deployments.** Not per-user groups in a shared process.

```
/home/mrkai/code/
  nanoclaw/                          # HAL-prime (this repo)
  halfleet/
    microhal-ben/
      nanoclaw/                      # Full repo clone
        CLAUDE.md                    # Modified, read-only governance
        groups/telegram_main/        # Ben's main (and only) group
        memory/                      # Ben's memory, isolated
        halos/                       # Subset of halos tools
    microhal-mum/
      nanoclaw/                      # Separate clone
        ...
```

**Why separate deployments, not shared process:**
- Ben has "an almost magical ability to make machines do mad shit." Shared process = shared filesystem = unacceptable risk.
- Code execution in agent containers must be provably unable to reach prime.
- Independent process means independent crash domain. Ben's agent going haywire doesn't affect prime or other microHALs.
- Each instance gets its own Telegram bot token — unique identity per user.

**HAL-prime retains:**
- Read access to `~/code/halfleet/` (can see all microHAL repos)
- Write access for code pushes (1-way: prime → microHAL)
- Kill switch capability
- Fleet monitoring via log/memory inspection

## PoC Success Criteria

1. Working Telegram bot with unique token per instance
2. Real code execution proving inability to touch prime soil (verified test)
3. 1-way code modification from HAL-prime to microHAL (demonstrated commit)
4. Kill switch operational from prime repo and remote via Telegram
5. Onboarding state machine: ToC → waiver → pre-flight assessment → tutorial
6. Shared service access (gh, vercel, neonctl) without exposing credentials directly

## Isolation Model

```
HAL-prime (~/code/nanoclaw/)
  ├── Can read: ~/code/halfleet/microhal-*/
  ├── Can write: push code updates to microHAL deployments
  ├── Can kill: halctl kill <microhal-id>
  └── Cannot: be reached from any microHAL

microHAL-ben (~/code/halfleet/microhal-ben/nanoclaw/)
  ├── LOCKED (read-only, owned by rick):
  │     CLAUDE.md, .claude/, halos/, src/, container/
  │     — governance BIOS, immutable at runtime
  ├── OPEN (read-write, service user):
  │     workspace/, projects/, groups/, memory/
  │     — user's playground, unrestricted
  ├── Can access: gh, vercel, neonctl (shared services via credential proxy)
  ├── Cannot: see ~/code/nanoclaw/ (prime)
  └── Cannot: see other microHAL instances
```

**Lockdown is surgical, not blanket.** The governance layer (CLAUDE.md, agents, halos, engine) is filesystem-permission locked (chmod 444/555, owned by rick). The workspace is theirs. Between bash and curl they'll find the edges — that's data, not a bug.

## Provisioning Model

**Scripted file copy from prime's working tree, driven by config manifest.** Not a git clone — nanoclaw source is infrastructure fossil record, not active development for microHAL users. No setup scripts, no origin tracking. Direct provisioning.

```yaml
# halfleet/fleet-config.yaml
base:
  source: ~/code/nanoclaw
  exclude:
    - memory/              # prime's memory
    - .claude/projects/    # prime's project memory
    - data/                # fleet data (prime only)
    - queue/               # prime's work queue
    - backlog/             # legacy
    - docs/d2/             # internal specs
    - nanoclaw.db          # prime's database
    - groups/              # prime's groups
    - .env*                # prime's secrets
  lock:                    # read-only after copy (chmod 444/555, owned by rick)
    - CLAUDE.md
    - .claude/
    - halos/
    - src/
    - container/
  open:                    # read-write (owned by service user)
    - workspace/
    - projects/
    - groups/
    - memory/

profiles:
  ben:
    personality: discovering-ben
    services: [gh, vercel, neonctl]
    telegram_bot_name: HALBen_bot
  mum:
    personality: gentle
    services: []
    telegram_bot_name: HALMum_bot
  dad:
    personality: default
    services: [gh]
    telegram_bot_name: HALDad_bot
```

Different configs for different people from day one. New test pilot = new profile entry + re-run. When the fleet moves to its own Linux box with bare-metal containers, the config travels with it.

## Onboarding State Machine

First-contact flow, enforced by the agent's CLAUDE.md instructions:

```
[first_message] → terms_of_service
  │
  ▼
terms_of_service → waiver_acceptance
  │  "All data belongs to the operator. This is a pilot, not a product."
  │  User must reply with explicit acceptance.
  ▼
waiver_acceptance → pre_flight_assessment
  │  Likert scale: AI attitudes (5-7 questions)
  │  Stored as baseline data in fleet/
  ▼
pre_flight_assessment → tutorial
  │  1-3 messages: high-level description + examples
  │  "I can help with X, Y, Z. Here's how people typically use me."
  ▼
tutorial → active
  │  Normal operation begins.
  ▼
active → [ongoing]
```

The state is tracked in the microHAL's memory. The agent refuses normal operation until onboarding is complete. Re-onboarding can be triggered by the operator.

## Shared Services

Each microHAL gets access to operator-controlled services via credential proxy:

| Service | Access | What it enables |
|---------|--------|-----------------|
| `gh` (GitHub CLI) | Rick's GitHub account | Background coding projects, PR creation |
| `vercel` | Rick's Vercel account | Deploy custom apps/workflows |
| `neonctl` | Rick's Neon account | Database provisioning for user projects |

These give microHAL users raw materials for custom projects while abstracting infrastructure details. The credential proxy controls what's exposed — microHALs never see raw tokens.

**Risk:** Ben deploys something unhinged to Vercel. Mitigation: Vercel project-level isolation, spend limits, and the kill switch. Operator responsibility, documented in ToC.

## CLAUDE.md Governance

Each microHAL gets a modified CLAUDE.md containing:
- Compressed agentic governance wisdom (from prime's standing decisions)
- Personality layer (per-user, from discovering-ben research for Ben)
- Onboarding state machine instructions
- Tool access boundaries
- **Read-only mount** — the agent cannot modify its own governance

Users can create custom agents, skills, and commands on top of this base. The base is immutable.

## Kill Switch

```bash
# From HAL-prime repo
halctl kill microhal-ben              # Stop process, disable bot

# From Telegram (Rick's main channel, authenticated)
@HAL kill microhal-ben                # Remote kill via IPC
```

Kill has three modes — freeze, fold, fry:

```bash
halctl freeze microhal-ben    # Stop process, preserve everything. Reversible.
halctl fold microhal-ben      # Stop + revoke token + archive data to fleet/
halctl fry microhal-ben       # Stop + revoke + wipe. Nuclear. Requires --confirm.
```

All modes:
1. Stop the pm2 process
2. Log the event with timestamp and reason
3. Notify Rick via prime's Telegram channel

Fold additionally: revoke bot token, move data to `data/fleet/ben/archive/`
Fry additionally: revoke bot token, delete the deployment directory

## Fleet Code Management

**1-way push: prime → microHAL**

```bash
# From HAL-prime
halctl push microhal-ben              # Push latest code changes
halctl push --all                     # Fleet-wide update
halctl push --dry-run microhal-ben    # Preview what would change
```

Implementation: cherry-pick from prime for now. Templates come from proof of concept delivery, not upfront. `halctl push` copies updated locked files from prime and re-applies permissions.

**Per-instance vs per-fleet changes:**
- Fleet changes: governance updates, security patches, halos upgrades → `halctl push --all`
- Instance changes: personality tuning, user-specific config → `halctl push microhal-ben`

## Setup Script

```bash
halctl create --name ben --personality discovering-ben
```

Steps:
1. Read `halfleet/fleet-config.yaml` for profile and base config
2. Copy prime working tree to `~/code/halfleet/microhal-ben/nanoclaw/`, excluding items in `base.exclude`
3. Apply personality template to CLAUDE.md (compose from base + personality + user layers)
4. Create `workspace/`, `projects/`, `groups/telegram_main/`, `memory/` directories
5. Lock governance layer: chown rick + chmod 444/555 on items in `base.lock`
6. Set open directories to service user ownership
7. Create new Telegram bot via BotFather (manual step, script prints BotFather deep link + instructions)
8. Configure environment: bot token, credential proxy endpoints for profile's services list
9. Set up pm2 process: `pm2 start ecosystem.config.js --only microhal-ben`
10. Register in fleet manifest: `~/code/halfleet/FLEET.yaml`
11. Run isolation verification: assert microHAL process cannot read prime filesystem
12. Print onboarding instructions for the user

## Implementation Phases

### Phase 0: Data Baseline (no code)
Run discovering-ben detectors on existing 255 conversations. Document baseline. ~1 session.

### Phase 1: Fleet Infrastructure
- `halctl` CLI tool (create, kill, push, list, status)
- Repo cloning + stripping script
- systemd service template
- Fleet manifest (FLEET.yaml)
- Isolation verification test
- ~2-3 sessions

### Phase 2: Ben Deployment
- BotFather: create @HALBen_bot (manual)
- Ben-specific personality from research
- Onboarding state machine in CLAUDE.md
- Credential proxy configuration
- CLAUDE.md as read-only
- Ben starts chatting
- ~1-2 sessions + observation period

### Phase 3: Instrumentation
- `halos/cycledet/` module (ported detectors)
- `halctl assess` and `halctl note` subcommands
- Weekly cron job for cycle detection
- Pre/post Likert comparison tooling
- ~2-3 sessions

### Phase 4: Fleet Operations
- `halctl logs`, `halctl report`
- Rolling updates via `halctl push`
- Integration with HAL-prime's briefings
- ~1-2 sessions

**Minimum viable: Phase 0 + Phase 1 + Phase 2.**

## Resolved Ambiguities

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| A1 | Bot creation | Semi-auto: script prints BotFather deep link, waits for token paste | 60-second ceremony, unavoidable, reduce tab-switching |
| A2 | Service management | pm2 | Less ceremony than systemd for multi-process. Footgun: `pm2 delete && start` for env changes, not `pm2 restart`. Acceptable. |
| A3 | Credential proxy | Shared on prime, microHALs call over localhost | Single point of monitoring/revocation. Natural control plane. Prime must be running. |
| A4 | Fleet template | Cherry-pick from prime | Templates come from PoC delivery, not upfront. Don't know what we're doing yet. |
| A5 | Governance lockdown | Filesystem permissions (chmod 444/555, owned by rick) | Surgical: governance BIOS locked, workspace open. |
| A6 | Onboarding state | memctl notes (type=state) | Allows memories to build on top. Risk: users less skilled than memctl creator. Accepted — we measure this. |
| A7 | Kill switch | Three modes: freeze (stop), fold (stop+archive), fry (stop+wipe) | All three needed for different situations. Fry requires --confirm. |
| A8 | Shared services | All-access per profile config, no runtime ACL | Monitoring outweighs control at this stage. We don't know the control case yet. OOTB nanoclaw IS the baseline — alignment-as-a-service needs real data on what happens without it. Bug-laden ACL is worse than no ACL as first point of friction. |

## Provenance

Architecture revised from single-process model to independent deployments (2026-03-17) after considering the Ben factor: agents must be provably unable to touch prime soil. The security model is structural, not policy. Steel girders, not paper guardrails.

Science, not vibes.
