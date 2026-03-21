---
title: "Taxonomy Review Phase 1 Findings Table"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Phase 1 Findings Table

Date: 2026-03-20

| Label | Severity | Summary | Evidence |
|-------|----------|---------|----------|
| `ORK.MSG.02 [TC11]` | `S2` | Piped follow-up messages are marked processed before the active container durably consumes them. | `src/index.ts:448-455`, `src/group-queue.ts:160-175`, `src/index.ts:479-489`, `container/agent-runner/src/index.ts:276-295` |
| `CTR.PARSE.03 [TC01]` | `S2` | Malformed or missing streamed frames can still resolve as success on zero exit, leaving the cursor advanced with no retry. | `src/container-runner.ts:434-449`, `src/container-runner.ts:639-651`, `src/index.ts:254-271` |
| `CTR.CHAIN.01 [TC11]` | `S3` | A rejected `onOutput()` callback leaves `outputChain` unresolved and can wedge the group queue. | `src/container-runner.ts:442-444`, `src/container-runner.ts:537-543`, `src/container-runner.ts:641-651`, `src/index.ts:313-322` |
| `CTR.PARSE.02 [TC09]` | `S3` | `parseBuffer` can grow without bound if an end marker never arrives. | `src/container-runner.ts:421-432` |
| `AGR.SPIN.02 [TC10]` | `S3` | The 150-event spin heuristic can kill legitimate tool-heavy turns that have not produced text yet. | `container/agent-runner/src/index.ts:407-417`, `container/agent-runner/src/index.ts:442-458`, `container/agent-runner/src/index.ts:477-501` |

## Metrics

| Metric | Value |
|--------|-------|
| Total findings | 5 |
| S1 count | 0 |
| S2 count | 2 |
| S3 count | 3 |
| S4 count | 0 |
