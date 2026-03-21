---
title: "NanoClaw/halos Portfolio Showcase — Specification"
category: spec
status: active
created: 2026-03-17
---

# NanoClaw/halos Portfolio Showcase — Specification

## Goal

Transform the NanoClaw + halos codebase into an irresistible public portfolio piece that demonstrates every skill demanded by the "AI Automation Engineer / Internal AI Tools Specialist" role archetype.

## Strategic Framing

The hiring managers for these roles want to see one thing: **someone who has already built the thing they're hiring for**. Not tutorials, not certificates, not "I used ChatGPT" — production-grade AI automation infrastructure with real cross-system integration.

NanoClaw + halos already demonstrates:
- AI agent orchestration (Claude Agent SDK, container isolation)
- Multi-channel messaging (Telegram, WhatsApp, Slack, Discord)
- Python CLI ecosystem (8 modules with structured data, YAML schemas, filesystem-first design)
- Cron-driven automation with LLM synthesis (hal-briefing)
- Structured memory governance (memctl)
- IPC between systems (filesystem-based, cross-language)
- API integration patterns (Telegram Bot API, credential proxy)

What's missing is **explicit demonstration of business-facing automation patterns** — the CRM syncs, pipeline dashboards, email workflows, and cross-tool integrations that these roles build daily.

## Scope

### In Scope
- Extensions to existing halos/NanoClaw architecture
- Business automation demo modules
- Architecture documentation and diagrams
- Public README rewrite for portfolio context
- Sanitization of private data (memory store, credentials)
- Demo mode for running without live credentials

### Out of Scope
- Rewriting NanoClaw core (it's upstream; we fork)
- Building a web frontend
- Production deployment for others to use
- Fake data that looks fake

---

## The Showcase Layers

### Layer 1: What Already Exists (Document & Diagram)

These features already ship. They just need proper documentation for a portfolio audience.

1. **Architecture diagram** — Mermaid or D2 diagram showing: Channels → Orchestrator → Container Agent → IPC → halos modules → Cron → Telegram. This is the centrepiece. Hiring managers scan visuals before reading code.

2. **halos module registry** — Already exists at `docs/d1/halos-modules.md`. Needs a portfolio-facing summary: "8 CLI tools, ~3000 lines of Python, all composable, all tested."

3. **Briefing system** — Already shipped today. Morning/nightly briefings with cron → Python data gathering → Claude synthesis → IPC → Telegram delivery. This is exactly the kind of end-to-end automation these roles build.

4. **Memory governance** — memctl with atomic notes, YAML schemas, hash-verified indices, pruning algorithms, enrichment scoring. This demonstrates structured data management at a level most portfolio projects don't reach.

### Layer 2: Business Automation Demos (Build New)

These are new modules that demonstrate the *business-facing* patterns hiring managers want to see. Each should be a real, functional halos module — not a mock.

#### A. `pipelinectl` — CRM/Pipeline Integration Demo

**What it demonstrates:** API integration with a CRM-like system, data transformation, LLM-powered analysis.

**Implementation:**
- Read from a CSV/JSON "pipeline" data source (or connect to HubSpot/Pipedrive free tier API)
- Track deal stages, amounts, close dates
- Generate weekly pipeline summary via Claude synthesis
- Detect stale deals (no activity in N days) and flag them
- Output: Telegram notification + archived report

**Skills demonstrated:** REST API integration, data pipeline, LLM analysis, cron automation, business metrics.

#### B. `campaignctl` — Marketing Campaign Orchestrator

**What it demonstrates:** Multi-step workflow automation, event-driven triggers, cross-system coordination.

**Implementation:**
- Define campaigns as YAML (audience, content template, schedule, channel)
- Track campaign lifecycle (draft → scheduled → live → completed → analysed)
- Generate campaign performance summary from mock/real analytics data
- LLM-powered content suggestion based on past performance
- Integration point: could connect to Mailchimp/SendGrid free tier

**Skills demonstrated:** Workflow orchestration, YAML-driven configuration, lifecycle state machines, marketing automation.

#### C. `healthctl` — Customer Success Health Scoring

**What it demonstrates:** Data aggregation from multiple sources, scoring algorithms, automated alerting.

**Implementation:**
- Aggregate signals: support ticket frequency, feature usage, billing status, NPS scores
- Compute health score per customer (weighted algorithm)
- Flag at-risk accounts with LLM-generated context
- Daily digest of accounts needing attention
- Escalation workflow via Telegram notification

**Skills demonstrated:** Data aggregation, scoring algorithms, cross-functional alerting, customer success patterns.

#### D. `onboardctl` — Automated Onboarding Workflow

**What it demonstrates:** Multi-step process automation, checklist management, cross-system provisioning.

**Implementation:**
- Define onboarding playbook as YAML (steps, owners, deadlines, dependencies)
- Track progress per new hire/customer
- Automated reminders for overdue steps
- LLM-generated welcome messages customised to role/context
- Integration with task tracking (todoctl)

**Skills demonstrated:** Process automation, checklist/workflow engines, cross-system orchestration.

### Layer 3: Integration Patterns Library

A `patterns/` directory demonstrating common integration patterns as standalone, documented examples:

1. **Webhook receiver** — Simple Flask/FastAPI endpoint that receives webhooks and routes to halos modules
2. **n8n-equivalent workflow** — A Python workflow engine that chains steps (fetch → transform → enrich → notify) — demonstrating you can build what n8n does, not just use it
3. **Rate-limited API client** — Reusable pattern for calling external APIs with retry, backoff, and circuit breaker
4. **Event bus** — Simple pub/sub between halos modules (filesystem-based, consistent with existing IPC philosophy)
5. **Data sync** — Bidirectional sync pattern between two data sources with conflict resolution

### Layer 4: Presentation & Documentation

#### Public README Rewrite

The current README is NanoClaw's upstream README (for general users). The portfolio fork needs a different framing:

```
# NanoClaw + halos — AI Automation Infrastructure

A personal AI assistant platform with a Python CLI ecosystem for automated
briefings, memory governance, job scheduling, and business process automation.

Built as a practical demonstration of:
- AI agent orchestration with Claude Agent SDK
- Multi-channel messaging (Telegram, WhatsApp, Slack)
- Cron-driven automation with LLM synthesis
- Structured data management (YAML schemas, hash-verified indices)
- Cross-system integration via IPC
- Python CLI tooling (8 modules, ~4000 lines)

## Architecture
[diagram]

## Modules
[table]

## Live Examples
- Morning briefing: data gathering → Claude synthesis → Telegram delivery
- Nightly recap: activity aggregation → contextual summary → archival
- Memory governance: atomic notes → enrichment scoring → pruning lifecycle
```

#### Architecture Diagram

Mermaid diagram covering the full system:

```
Channels (Telegram/WhatsApp/Slack)
  ↓
NanoClaw Orchestrator (Node.js)
  ↓ message queue
Container Agent (Claude SDK)
  ↓ IPC (filesystem JSON)
halos Python Modules
  ├── memctl (memory governance)
  ├── nightctl (batch jobs)
  ├── cronctl (scheduling)
  ├── todoctl (backlog)
  ├── logctl (structured logs)
  ├── reportctl (digests)
  ├── agentctl (session tracking)
  ├── hal-briefing (daily briefings)
  ├── pipelinectl (CRM demo)
  ├── campaignctl (marketing demo)
  ├── healthctl (CS scoring demo)
  └── onboardctl (workflow demo)
  ↓
Cron → Synthesis (Claude) → IPC → Telegram
```

#### Demo Mode

A `--demo` flag across halos modules that uses bundled sample data instead of live data. This lets someone clone the repo and see it work without credentials.

---

## Sanitization Plan

### Must be gitignored/redacted:
- `memory/notes/` — all note files (personal data)
- `memory/reflections/` — diary entries (keep INDEX.md structure, remove content)
- `memory/INDEX.md` — the YAML block contains note metadata
- `.env` — credentials
- `store/` — SQLite databases with message history
- `data/` — IPC files, session data
- `groups/*/` — group-specific memory and context

### Keep public:
- `memory/reflections/INDEX.md` — structure only (shows the concept)
- All code (`src/`, `halos/`, `container/`)
- All docs (`docs/`)
- Config files (`memctl.yaml`, `nightctl.yaml`, etc.) — no secrets
- Cron job definitions (`cron/jobs/`)
- Architecture docs and diagrams
- Test suites

### Approach:
Add to `.gitignore`:
```
memory/notes/
memory/reflections/*.md
!memory/reflections/INDEX.md
memory/archive/
memory/backlinks/
store/
data/
groups/*/
.env
```

Create `memory/notes/.gitkeep` and `memory/reflections/SAMPLE.md` with a sanitized example entry showing the format.

---

## Priority & Sequencing

### Phase 1: MVP Showcase (1-2 days)
1. Sanitize `.gitignore`
2. Architecture diagram (Mermaid in README)
3. Portfolio-facing README rewrite
4. Document existing modules with portfolio framing
5. Push public

### Phase 2: Business Demos (3-5 days)
6. `pipelinectl` — CRM pipeline demo
7. `healthctl` — customer health scoring
8. `--demo` mode for sample data
9. Integration patterns library (2-3 patterns)

### Phase 3: Full Showcase (1-2 weeks)
10. `campaignctl` — marketing automation
11. `onboardctl` — workflow engine
12. Video walkthrough / Loom recording
13. Remaining integration patterns
14. Blog post / writeup

---

## Differentiation — What Makes This Stand Out

1. **It's real.** Not a tutorial project. Not a TODO app with AI bolted on. This is a running system that sends actual messages to an actual phone at 0600 and 2100 every day.

2. **It's composable.** 8 modules that talk to each other via filesystem IPC, not tightly coupled. This is the Unix philosophy applied to AI tooling.

3. **It shows taste.** The personality layer (HAL), the reflections workspace, the briefing synthesis — these show someone who thinks about UX, not just functionality.

4. **It demonstrates the full stack.** Node.js orchestrator + Python CLI ecosystem + Container isolation + Cron scheduling + LLM synthesis + Multi-channel delivery. One person built this.

5. **The commit history tells a story.** 392 commits over 45 days. The git archaeology is visible — someone can trace the evolution from fork to fully personalized system.

6. **It has its own memory.** memctl with hash-verified indices, enrichment scoring, and pruning lifecycle. Most portfolio projects store nothing. This one remembers.

7. **Self-documenting AI agent.** HAL writes its own diary entries. The reflections workspace is both a feature and a portfolio talking point — "I built an AI system that maintains its own phenomenological record."

---

## Open Questions

1. **Should pipelinectl use a real CRM API (HubSpot free tier) or simulated data?** Real API is more impressive but adds setup complexity for reviewers.

2. **How much of the NanoClaw upstream README should be preserved vs replaced?** The portfolio README needs to serve a different audience than the original.

3. **Should the repo be a fork or a standalone?** Fork preserves the provenance (392 commits). Standalone is cleaner but loses history.

4. **Video walkthrough — Loom, YouTube, or embedded in README?** A 3-minute video showing the briefing system in action would be high-impact.

5. **Should the halos modules be extracted into a separate repo?** The Python ecosystem is impressive enough to stand alone, but the integration with NanoClaw is part of the story.
