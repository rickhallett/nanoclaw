---
title: "Responsiveness Review Report"
category: review
status: active
created: 2026-03-20
---

# Responsiveness Review Report

Date: 2026-03-20

Scope:
- `OBS.LOG.01`
- `OBS.LOG.02`
- `ORCH.02`
- `CTR.02`
- `AGR.01`
- `FLEET.01`
- `SVC.01`
- adjacent lifecycle paths that affect message-to-response durability

Files reviewed:
- `docs/d2/review-responsiveness.md`
- `halos/logctl/fleet.py`
- `src/index.ts`
- `src/db.ts`
- `src/group-queue.ts`
- `src/container-runner.ts`
- `src/container-runtime.ts`
- `src/credential-proxy.ts`
- `src/channels/telegram.ts`
- `container/agent-runner/src/index.ts`
- `~/.config/systemd/user/nanoclaw.service`

## Summary

This pass confirmed 6 live responsiveness issues.

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 5 |
| S3 | 1 |
| S4 | 0 |

The highest-risk failures are all commit/visibility mismatches:
- fleet conversation review is still materially blind because pm2 timestamps are coerced onto today's date and only the first response per user turn is retained;
- outbound agent responses are still not persisted to SQLite anywhere in the main send paths;
- follow-up messages piped into an active container are committed before the container has actually consumed them;
- streamed container completion still trusts process exit more than framed output delivery.

The guide is also partly stale. Several items that were framed as missing are now partially addressed:
- `ORCH.03` / `ORCH.04`: `saveState()` now runs immediately after cursor advancement in both the initial-processing path and the piped-follow-up path (`src/index.ts:190-192`, `src/index.ts:453-455`);
- `ROUTE.01` / `ROUTE.03`: Telegram send now falls back from Markdown to plain text and logs failures instead of throwing (`src/channels/telegram.ts:40-55`, `src/channels/telegram.ts:503-528`);
- `CTR.05`: startup orphan cleanup exists (`src/container-runtime.ts:103-127`), but shutdown still drops active work by design, so the underlying responsiveness risk remains in a different form.

## Findings

### OBS.LOG.01 S2

Fleet conversation pairing is still broken across day boundaries, and even same-day multi-part responses are truncated to the first response per user turn.

Evidence:
- pm2 timestamps are converted to ISO by prepending the current UTC date in `halos/logctl/fleet.py:177-182`;
- timestamp normalization uses the same current-date assumption for non-ISO values in `halos/logctl/fleet.py:184-188`;
- only the first matched agent response is retained for a user message because later matches are blocked by `best_idx not in response_for` in `halos/logctl/fleet.py:196-207`.

Impact:
- any pm2 response not emitted on the current UTC day can be paired to the wrong user message or to no user message at all;
- if the agent emits multiple visible outputs for one user turn, fleet conversation view silently drops all but the first.

Guide status:
- confirmed;
- the guide understates the bug by treating it as date inference only.

### OBS.LOG.02 S2

Outbound agent responses are still not persisted to SQLite, so the system has no durable first-class record of what was actually delivered.

Evidence:
- `storeMessage()` exists and supports `is_from_me` writes in `src/db.ts:287-326`;
- inbound channel messages are stored via `storeMessage(msg)` in `src/index.ts:571-597`;
- the main agent response path sends to the channel directly without storing the outbound message in `src/index.ts:217-249`;
- scheduler and IPC send paths also send directly without any DB write in `src/index.ts:637-658`;
- Telegram delivery itself only logs send success/failure in `src/channels/telegram.ts:503-528`.

Impact:
- postmortems cannot distinguish "agent generated output but routing lost it" from "agent never generated output";
- fleet conversation tooling is forced to reconstruct responses from timestamp-adjacent logs instead of querying canonical message history.

Guide status:
- confirmed.

### RESP.IPC.01 [Additional] S2

Follow-up messages piped into an already-active container are marked processed before the container has durably consumed them.

Evidence:
- when a container is already active, `startMessageLoop()` advances `lastAgentTimestamp` immediately after `queue.sendMessage()` returns true in `src/index.ts:437-455`;
- `queue.sendMessage()` only writes an IPC file and returns success once the file is renamed into place in `src/group-queue.ts:160-175`;
- the container consumes and deletes those files later in `container/agent-runner/src/index.ts:276-297`;
- restart recovery only replays DB messages newer than the persisted `lastAgentTimestamp` in `src/index.ts:479-489`.

Impact:
- if the process or container dies after the router cursor is advanced but before the active runner drains the IPC file, the follow-up user message is no longer recoverable from normal restart logic;
- this produces the exact user symptom the guide is worried about: a real inbound message can disappear with no visible response and no automatic retry.

Guide status:
- not called out explicitly in `review-responsiveness.md`;
- this is a confirmed additional risk.

### CTR.PARSE.01 S2

Streaming-mode container completion still resolves as success on zero exit even if no valid framed output was ever parsed.

Evidence:
- streaming parse failures only emit a warning in `src/container-runner.ts:421-449`;
- on normal close, streaming mode resolves success after `outputChain` settles, with no requirement that any valid frame was parsed in `src/container-runner.ts:639-651`;
- the orchestrator only rolls back the cursor on explicit error in `src/index.ts:254-271`.

Impact:
- malformed, truncated, or otherwise unparsable streamed output can leave the turn marked successful with no user-visible response;
- because the cursor was already advanced, the original message is not retried automatically.

Guide status:
- partially covered by `CTR.02`, but the current defect is wider than "output without markers";
- the real failure is that parse failure does not propagate into container failure.

### SVC.SHUT.01 S2

Shutdown still abandons active conversations: the process exits without draining or stopping active containers, and startup cleanup then kills whatever survived.

Evidence:
- the main process handles `SIGTERM`/`SIGINT` and then calls `queue.shutdown(...)` followed by `process.exit(0)` in `src/index.ts:511-520`;
- `GroupQueue.shutdown()` explicitly does not kill or await active containers and only logs them as detached in `src/group-queue.ts:347-363`;
- startup recovery stops all matching orphaned containers in `src/container-runtime.ts:103-127`;
- the systemd unit still restarts the service automatically and has no `TimeoutStopSec` override in `~/.config/systemd/user/nanoclaw.service:5-14`.

Impact:
- any response still in flight when the service shuts down loses its host-side callback chain immediately;
- if the container survives the parent exit, the next startup kills it anyway before that response can be relayed.

Guide status:
- `CTR.05` is only partially stale;
- there is now startup cleanup, but the user-visible failure mode remains because shutdown intentionally detaches active work instead of completing or cancelling it deterministically.

### RESP.BOUNDARY.01 S3

There is still no local timeout or cancellation path for a stalled SDK turn crossing the credential-proxy boundary, so hung upstream calls degrade into long silences until the host kills the whole container.

Evidence:
- `runQuery()` awaits `query(...)` directly with no local timer or abort signal in `container/agent-runner/src/index.ts:332-507`;
- `_close` only ends the local message stream; it does not cancel the in-flight SDK request in `container/agent-runner/src/index.ts:343-362`;
- the credential proxy forwards requests upstream with `http(s).request(...)` but does not set any request timeout in `src/credential-proxy.ts:186-205`;
- host-side timeout recovery only happens at the container boundary in `src/container-runner.ts:477-556`.

Impact:
- if the proxy or upstream API stalls instead of erroring, the user gets no response and no intermediate failure for up to the container hard timeout window;
- this matches the guide's "hung server" symptom more closely than several of the stale routing hypotheses.

Guide status:
- confirmed in substance across `AGR.01` and `FLEET.01`;
- the code still relies on outer container death rather than bounded request-level timeouts.

## Invalidated Or Stale Guide Items

- `ORCH.03` and `ORCH.04` are stale as written. The code now persists router state immediately after cursor advancement on both the initial turn and the piped follow-up path (`src/index.ts:190-192`, `src/index.ts:453-455`).
- `ROUTE.01` and `ROUTE.03` are stale for Telegram. The send path falls back from Markdown to plain text and catches/logs send failures without propagating them up the response pipeline (`src/channels/telegram.ts:40-55`, `src/channels/telegram.ts:503-528`).
- `SVC.01` is only partially current. The unit still lacks `TimeoutStopSec`, but the larger current problem is not slow graceful shutdown; it is that shutdown exits immediately and abandons active work.
- `CTR.05` is partially fixed on startup via orphan cleanup, but not fixed end to end because shutdown still permits orphan creation.

## Config-Dependent Items Not Verifiable From Static Review

- `INGEST.02` sender allowlist membership for ben's specific Telegram ID.
- `INGEST.03` whether ben's group is configured as `isMain: true`.
- `GQ.01` / `GQ.02` live fleet saturation at incident times.
- `AGR.04` / `SESS.03` ben's actual session size and whether resume latency correlates with incidents.

## Recommended Next Fix Order

1. Fix `OBS.LOG.01` in `halos/logctl/fleet.py` so fleet review stops fabricating timestamps and truncating multi-part responses.
2. Persist outbound responses in the orchestrator send paths (`processGroupMessages`, scheduler sends, IPC sends) so response history is queryable from SQLite.
3. Add a delivery/ack boundary for piped follow-up messages instead of advancing `lastAgentTimestamp` on IPC file creation.
4. Make streaming parse failure fatal in `runContainerAgent()` when no valid output frame was observed.
5. Replace shutdown detachment with deterministic container cancellation or drain semantics.
6. Add request-level timeouts at the SDK/proxy boundary so upstream stalls fail fast instead of consuming the full container timeout budget.

## Coverage Notes

This was a static review pass only.

I did not run the app or replay incident logs in this pass, so:
- config-dependent findings remain unverified without the affected fleet instance state;
- timing-sensitive behavior is inferred from current code paths rather than reproduced live.
