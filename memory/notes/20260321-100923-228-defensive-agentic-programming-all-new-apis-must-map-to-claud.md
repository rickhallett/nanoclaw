---
id: 20260321-100923-228
title: 'Defensive agentic programming: all new APIs must map to CLAUDE.md'
type: decision
tags:
- architecture
- governance
- defensive-programming
entities:
- nanoclaw
- hal
- claude-md
confidence: high
created: '2026-03-21T10:09:23Z'
modified: '2026-03-21T10:09:23Z'
expires: null
---

All new surface-layer API development must be explicitly documented in CLAUDE.md so it is in the agent boot sequence. Agents should not have to discover how things work — discovery leads to non-deterministic behaviour, aberrant patterns, and compounding errors. Defensive agentic programming assumes future operators are non-deterministic and codes accordingly. This applies to every new halos module, CLI tool, and trackctl domain.
