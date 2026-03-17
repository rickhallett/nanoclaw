---
id: 20260316-065510-445
title: Defensive coding mandate for agent-facing CLIs
type: decision
tags:
- standing-order
- governance
- engineering
- decision
entities:
- kai
backlinks:
- 20260316-133401-679
- 20260316-143309-091
- 20260315-210021
- 20260315-210023
- 20260315-210026
confidence: high
created: '2026-03-16T06:55:10Z'
modified: '2026-03-16T18:02:06Z'
expires: null
---

All halos modules must handle unhappy paths defensively. LLMs are probabilistic; the unhappy path is a question of time. Atomic writes (tmp+rename), collision guards, missing directory handling, accurate error counts, index consistency after mutations. No silent swallowing of errors.
