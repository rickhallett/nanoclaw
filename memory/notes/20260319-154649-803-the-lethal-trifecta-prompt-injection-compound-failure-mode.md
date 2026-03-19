---
id: 20260319-154649-803
title: The Lethal Trifecta — prompt injection compound failure mode
type: fact
tags:
- ai-failure-modes
- security
- prompt-injection
- taxonomy
entities:
- Simon Willison
confidence: high
created: '2026-03-19T15:46:49Z'
modified: '2026-03-19T15:46:49Z'
expires: null
---

Simon Willison's named failure mode: when an AI agent combines private data access + exposure to malicious instructions + an exfiltration vector, prompt injection becomes catastrophic. LLMs are 'incredibly gullible by design.' All three conditions must be present; removing any one breaks the trifecta. Source: Pragmatic Summit 2026 fireside chat.
