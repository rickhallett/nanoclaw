---
title: "Taxonomy Review Master Findings Table"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Master Findings Table

Date: 2026-03-20

This table consolidates Phase 1 through Phase 6 for use by the later combinatorial pass.

| Phase | Label | Severity | Summary | Evidence |
|-------|-------|----------|---------|----------|
| 1 | `ORK.MSG.02 [TC11]` | `S2` | Piped follow-up messages are marked processed before the active container durably consumes them. | `src/index.ts:448-455`, `src/group-queue.ts:160-175`, `src/index.ts:479-489`, `container/agent-runner/src/index.ts:276-295` |
| 1 | `CTR.PARSE.03 [TC01]` | `S2` | Malformed or missing streamed frames can still resolve as success on zero exit, leaving the cursor advanced with no retry. | `src/container-runner.ts:434-449`, `src/container-runner.ts:639-651`, `src/index.ts:254-271` |
| 1 | `CTR.CHAIN.01 [TC11]` | `S3` | A rejected `onOutput()` callback leaves `outputChain` unresolved and can wedge the group queue. | `src/container-runner.ts:442-444`, `src/container-runner.ts:537-543`, `src/container-runner.ts:641-651`, `src/index.ts:313-322` |
| 1 | `CTR.PARSE.02 [TC09]` | `S3` | `parseBuffer` can grow without bound if an end marker never arrives. | `src/container-runner.ts:421-432` |
| 1 | `AGR.SPIN.02 [TC10]` | `S3` | The 150-event spin heuristic can kill legitimate tool-heavy turns that have not produced text yet. | `container/agent-runner/src/index.ts:407-417`, `container/agent-runner/src/index.ts:442-458`, `container/agent-runner/src/index.ts:477-501` |
| 2 | `SEC.L2.04 [TC05]` | `S2` | The credential proxy trusts network reachability rather than caller identity. | `src/credential-proxy.ts:152-184`, `src/container-runtime.ts:18-40` |
| 2 | `SEC.L5.03 [TC05]` | `S3` | Sender-allowlist load failures fall back to allow-all. | `src/sender-allowlist.ts:17-21`, `src/sender-allowlist.ts:38-66`, `src/sender-allowlist.test.ts:35`, `src/sender-allowlist.test.ts:82`, `src/sender-allowlist.test.ts:89` |
| 3 | `DAT.QUERY.01 [TC11]` | `S2` | The message queries return the newest capped window, so older unseen backlog is skipped once the cursor advances. | `src/db.ts:341-363`, `src/db.ts:375-389`, `src/db.test.ts:412`, `src/db.test.ts:428` |
| 3 | `DAT.MIG.01 [TC01]` | `S2` | Bare `ALTER TABLE` catches swallow migration failures for reasons other than "already exists". | `src/db.ts:111-165` |
| 3 | `SCHED.RUN.01 [TC11]` | `S2` | Missing task groups log an error and return, but tasks stay active and due forever. | `src/task-scheduler.ts:111-129`, `src/task-scheduler.ts:251-267` |
| 3 | `GQ.RETRY.02 [TC04]` | `S3` | After retry exhaustion, the queue no longer guarantees liveness until another inbound event arrives. | `src/group-queue.ts:263-283` |
| 4 | `CHL.GM.02 [TC11]` | `S3` | Gmail marks message IDs as processed before `processMessage()` succeeds. | `src/channels/gmail.ts:201-205`, `src/channels/gmail.ts:215-229` |
| 4 | `CHL.TG.07 [TC12]` | `S3` | Telegram bootstrap claims all `tg:` JIDs until ownership is learned, and routing takes the first match. | `src/channels/telegram.ts:535-540`, `src/router.ts:47-51` |
| 5 | `FLT.ONBOARD.01 [TC12]` | `S2` | Onboarding handoff is stored in one global YAML file shared across users and groups. | `src/channels/telegram.ts:88-116`, `src/channels/telegram.ts:284-286`, `src/channels/telegram.ts:340-342` |
| 5 | `FLT.EVAL.02 [TC13]` | `S3` | The behavioral smoke suite can pass while an entire scenario fails if it lacks explicit blocking/min-rate metadata. | `halos/halctl/behavioral_smoke.py:166-177`, `halos/halctl/behavioral_smoke.py:1795-1796` |
| 6 | `HALO.HALCTL.04 [TC12]` | `S2` | `halctl session clear` mutates SQLite only and does not coordinate with the live orchestrator session state. | `halos/halctl/session.py:64-121`, `src/index.ts:70-71`, `src/index.ts:87`, `src/index.ts:284`, `src/index.ts:313-359` |
| 6 | `HALO.NIGHT.02 [TC11]` | `S3` | Nightctl run records are written non-atomically. | `halos/nightctl/executor.py:70-77`, `halos/nightctl/container.py:81-99`, `halos/nightctl/container.py:147-150` |

## Metrics

| Metric | Value |
|--------|-------|
| Total findings | 17 |
| S1 count | 0 |
| S2 count | 8 |
| S3 count | 9 |
| S4 count | 0 |
