---
title: "halos in brief"
category: guide
status: active
created: 2026-03-15
---

# halos in brief

NanoClaw runs agents. halos is what they remember, schedule, and audit.

Seven CLI tools, one `uv sync`. Files as state, YAML as schema, `cat` as debugger.

## The tools

```
memctl     what the agent knows         (notes, backlinks, hash-verified index)
nightctl   what the agent deferred      (batch jobs, overnight window, run records)
cronctl    what runs on a clock         (YAML job defs → crontab generation)
todoctl    what needs doing             (prioritised backlog, status workflow)
logctl     what happened                (log reader, not a log framework)
reportctl  the digest                   (briefings from all modules, no imports)
agentctl   how much agent time was spent (session tracking, spin detection)
```

## Design in three sentences

Every module writes validated YAML files through a CLI. Indices are derived and rebuildable. The agent proposes, the human disposes.

## What's novel

**Enrichment rubric.** `memctl enrich` scores candidate backlinks across five dimensions and presents them for batch human approval. The graph trains itself through the approval loop without ML.

**Enforcement loop.** Three layers make the agent follow the memory protocol: system prompt instruction (L8), tool stdout nudge (L7), neighbour context. No hooks needed.

**No LLM in governance.** The memory store must be trustworthy even when the agent is probabilistic. If the governance layer is also probabilistic, the system can gaslight itself.

## Current state

59 notes, 18 backlinks, 539 tests, 91 adversarial findings (14 critical/high fixed).

## Known gaps

- logctl has no writer (nothing emits halos structured logs yet)
- todoctl needs archive, edit, cancel, entities
- reportctl reads other modules' files via implicit contracts (fragile)
- No cross-module integration tests
- Noise tags in enrich are hardcoded, should be config
