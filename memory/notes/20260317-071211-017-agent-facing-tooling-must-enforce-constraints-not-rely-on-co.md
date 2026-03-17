---
id: 20260317-071211-017
title: Agent-facing tooling must enforce constraints, not rely on convention
type: decision
tags:
- halos
- architecture
- agents
entities:
- nightctl
- todoctl
- agentctl
confidence: high
created: '2026-03-17T07:12:11Z'
modified: '2026-03-17T07:12:11Z'
expires: null
---

When tooling is operated by agents (not just humans), validation must be structural — required flags, foreign key checks, tool-level enforcement. Convention-based approaches (optional YAML fields, naming discipline) are insufficient because agents forget between sessions. Steel girders over paper guardrails.
