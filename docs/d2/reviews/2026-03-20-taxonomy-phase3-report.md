---
title: "Taxonomy Review Phase 3"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Phase 3

Date: 2026-03-20

Scope:
- `DAT.QUERY`
- `DAT.MIG`
- `DAT.SEC`
- `SCHED.DRIFT`
- `SCHED.RUN`
- `GQ.INV`
- `GQ.RETRY`

## Summary

Phase 3 produced 4 findings.

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 3 |
| S3 | 1 |
| S4 | 0 |

The dominant pattern in this phase is lossy or self-stalling state progression: message retrieval drops older backlog under load, migration failures are swallowed, and one scheduler failure path never exits the retry surface.

## Findings

### DAT.QUERY.01 [TC11] S2

`getNewMessages()` and `getMessagesSince()` return the most recent `N` unseen rows, not the earliest `N` after the cursor, so older unseen messages are permanently skipped when backlog exceeds the cap.

Evidence:
- both queries select `ORDER BY timestamp DESC LIMIT ?` and then re-sort ascending in `src/db.ts:341-352` and `src/db.ts:375-386`;
- the caller advances the cursor to the newest returned timestamp in `src/db.ts:358-363`;
- the current tests explicitly encode this "most recent in chronological order" behavior at `src/db.test.ts:412` and `src/db.test.ts:428`.

Impact:
- if more than 200 relevant messages accumulate between polls, the oldest unseen messages are never returned before the cursor advances past them;
- backlog truncation becomes silent data loss rather than bounded processing.

Why `[TC11]`:
- the cursor state machine assumes it processed the whole unseen interval, but the query only sampled its tail.

### DAT.MIG.01 [TC01] S2

Schema migration `ALTER TABLE` failures are silently swallowed for every reason, not just "column already exists".

Evidence:
- each append-only migration wraps `ALTER TABLE` in bare `try/catch {}` blocks in `src/db.ts:111-165`;
- the backfill for `is_bot_message`, `is_main`, `channel`, and `is_group` only runs inside those same try blocks.

Impact:
- disk-full, lock, corruption, or syntax failures leave the schema half-migrated with no signal to the caller;
- downstream code then assumes columns and backfills exist, which turns migration failure into latent runtime breakage.

Why `[TC01]`:
- startup treats "migration step executed without throwing outward" as success instead of verifying the schema artifact actually changed.

### SCHED.RUN.01 [TC11] S2

When a due task references a group folder that no longer exists in `registeredGroups`, the scheduler logs an error and returns without changing the task state, so the task is retried forever on every poll.

Evidence:
- the missing-group branch only logs and writes a run log before returning in `src/task-scheduler.ts:111-129`;
- the scheduler loop re-enqueues any task whose DB row is still `active` in `src/task-scheduler.ts:251-267`.

Impact:
- orphaned tasks churn every scheduler interval without any operator-visible pause or completion transition;
- logs fill with repeat failures and the queue spends work on a task that cannot ever run.

Why `[TC11]`:
- the run lifecycle has an error transition for invalid folder syntax, but not for "group row missing", leaving the task state machine incomplete.

### GQ.RETRY.02 [TC04] S3

After retry exhaustion, the queue stops driving the stranded message set until a fresh inbound message arrives or the process restarts.

Evidence:
- exhausted retries log and reset the counter, but do not requeue the group in `src/group-queue.ts:263-272`;
- retries are only scheduled by future incoming events in `src/group-queue.ts:279-283`.

Impact:
- messages that were rolled back for retry can remain unprocessed indefinitely if the conversation goes quiet after the last failure;
- the system preserves the data in SQLite, but no longer guarantees forward progress.

Why `[TC04]`:
- the implementation defends against duplicate retries, but does not positively guarantee that deferred work will eventually run.

## Coverage Notes

Observed coverage:
- `src/db.test.ts` ran, but its limit tests encode the lossy capped-query behavior instead of flagging it.

Important gaps:
- `src/task-scheduler.test.ts` could not run in this environment because importing `src/container-runner.ts` pulled in `src/container-runtime.ts`, which failed at `os.networkInterfaces()`;
- no test covers the missing-group branch in `runTask()`;
- no test proves liveness after `GQ.RETRY.02` retry exhaustion.
