---
id: 20260319-154711-750
title: Sandboxing Gap — running agents without environment isolation
type: fact
tags:
- ai-failure-modes
- taxonomy
- security
entities:
- Simon Willison
confidence: high
created: '2026-03-19T15:47:11Z'
modified: '2026-03-19T15:47:11Z'
expires: null
---

Running coding agents locally without an isolated execution environment provides a ready-made exfiltration vector, completing The Lethal Trifecta. Willison praised Claude Code for Web specifically because Anthropic manages the container. Damage limitation requires the agent to be unable to affect the broader system if compromised.
