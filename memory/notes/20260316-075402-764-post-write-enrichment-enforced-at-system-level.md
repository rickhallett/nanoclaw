---
id: 20260316-075402-764
title: Post-write enrichment enforced at system level
type: decision
tags:
- standing-order
- governance
- decision
entities:
- kai
backlinks:
- 20260316-133401-679
- 20260315-210021
- 20260315-210023
- 20260315-210026
confidence: high
created: '2026-03-16T07:54:02Z'
modified: '2026-03-16T18:02:06Z'
expires: null
---

After every memctl new, the agent must run memctl enrich and present proposals. Enforced via CLAUDE.md system prompt and post-write stdout nudge. The graph only gains edges through this protocol.
