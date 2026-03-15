---
id: 20260315-210053
title: Technical preferences - tools and conventions
type: decision
tags:
- engineering
- stack
- decision
entities:
- kai
confidence: high
created: '2026-03-15T21:00:53Z'
modified: '2026-03-15T21:00:53Z'
expires: null
---

TypeScript primary, Next.js for web. Python via uv exclusively (SD-310, no exceptions). Drizzle ORM, Neon Postgres. 2-space indentation. JSDoc for behaviour, header comments for purpose. Squash merge to keep main clean. Git worktree over git stash. YAML over prose for structured data (SD-258).
