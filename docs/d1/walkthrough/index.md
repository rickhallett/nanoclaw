---
title: "System Walkthrough"
category: guide
status: active
created: 2026-03-20
---

# System Walkthrough

Structured exploration of the NanoClaw + halos codebase. Each entry is a waypoint — a piece of the system understood well enough to navigate from.

Start with the [Exploration Map](010-exploration-map.md) for recommended routes and time estimates.

## Entries

| # | File | Topic | Date |
|---|------|-------|------|
| 1 | [001-codebase-census.md](001-codebase-census.md) | Codebase size, module breakdown, churn heatmap | 2026-03-20 |
| 2 | [002-connective-tissue.md](002-connective-tissue.md) | Tier 2: IPC, config, group-queue, task-scheduler, router, types, container agent, end-to-end flow | 2026-03-20 |
| 3 | [003-orchestrator.md](003-orchestrator.md) | Deep dive: src/index.ts — startup, message loop, state, complexity hotspots | 2026-03-20 |
| 4 | [004-container-runner.md](004-container-runner.md) | Deep dive: container spawning, mounts, output parsing, timeout/reaping | 2026-03-20 |
| 5 | [005-data-layer.md](005-data-layer.md) | Deep dive: SQLite schema (8 tables), migrations, query patterns | 2026-03-20 |
| 6 | [006-channels.md](006-channels.md) | Channel abstraction, Telegram (bot pool, onboarding), Gmail (OAuth, polling) | 2026-03-20 |
| 7 | [007-security.md](007-security.md) | Five-layer defense: containers, credential proxy, mount security, IPC auth, sender allowlist | 2026-03-20 |
| 8 | [008-fleet-personality.md](008-fleet-personality.md) | Fleet concept, personality composition, onboarding, assessment, evaluation | 2026-03-20 |
| 9 | [009-halos-ecosystem.md](009-halos-ecosystem.md) | All 8 halos modules: halctl, nightctl, memctl, briefings, logctl, agentctl, cronctl, reportctl | 2026-03-20 |
| 10 | [010-exploration-map.md](010-exploration-map.md) | **START HERE** — Full map, time estimates, 4 recommended routes, session planning | 2026-03-20 |
| 11 | [011-complexity-assessment.md](011-complexity-assessment.md) | Complexity rating (58–65/100), comparisons to CI runners, K8s operators, message brokers | 2026-03-20 |
