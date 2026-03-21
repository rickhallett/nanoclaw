---
title: "Taxonomy Review Phase 1"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Phase 1

Date: 2026-03-20

Scope:
- `ORK.CUR`
- `ORK.MSG`
- `ORK.IDLE`
- `CTR.PARSE`
- `CTR.MNT`
- `CTR.TIMEOUT`
- `CTR.CHAIN`
- `AGR.LOOP`
- `AGR.SPIN`

Files reviewed:
- `src/index.ts`
- `src/container-runner.ts`
- `src/group-queue.ts`
- `container/agent-runner/src/index.ts`
- `src/container-runner.test.ts`
- `src/group-queue.test.ts`

## Summary

Phase 1 produced 5 findings.

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 2 |
| S3 | 3 |
| S4 | 0 |

The highest-risk issues are both commit/ack mismatches:
- piped follow-up messages are marked processed before the active container durably consumes them;
- streaming-mode container completion trusts process exit even after parse failure, so malformed output can be treated as success and the cursor stays advanced.

## Findings

### ORK.MSG.02 [TC11] S2

Follow-up messages piped into an active container are committed in router state before the container has durably accepted them.

Evidence:
- `startMessageLoop()` advances `lastAgentTimestamp` immediately after `queue.sendMessage()` returns true in `src/index.ts:448-455`.
- `queue.sendMessage()` only writes an IPC file; there is no delivery acknowledgement from the container in `src/group-queue.ts:160-175`.
- restart recovery only replays DB messages newer than `lastAgentTimestamp` in `src/index.ts:479-489`.
- the container-side IPC reader deletes files when it drains them in `container/agent-runner/src/index.ts:276-295`.

Impact:
- if the host or container dies after the DB cursor is advanced but before the active container drains the IPC file, the follow-up message is no longer recoverable from the message table on restart;
- the stale IPC file will only be delivered if some later event happens to start another container for that group, so the message can become silently invisible for an unbounded time.

Why `[TC11]`:
- the state machine commits the "message delivered" transition before the consumer has acknowledged receipt.

### CTR.PARSE.03 [TC01] S2

Streaming-mode parse failures are logged and ignored, but a zero-exit container is still treated as success even when no valid output frame was parsed.

Evidence:
- parse errors only emit a warning in `src/container-runner.ts:434-449`;
- on normal close, streaming mode resolves success after `outputChain` settles without checking that any valid marker was parsed in `src/container-runner.ts:639-651`;
- the orchestrator only rolls back the cursor on explicit error in `src/index.ts:254-271`.

Impact:
- malformed, truncated, or otherwise unparsable streamed output can result in a successful completion path with no user-visible response and no retry;
- the message cursor remains advanced, so the original user input is silently dropped.

Why `[TC01]`:
- the host accepts a successful process lifecycle instead of verifying the actual output artifact it needed to receive.

### CTR.CHAIN.01 [TC11] S3

A rejected streaming callback can wedge the group permanently because `outputChain` is never observed with an error path.

Evidence:
- each parsed frame appends `onOutput(parsed)` to `outputChain` in `src/container-runner.ts:442-444`;
- both timeout-success and normal-close success paths wait on `outputChain.then(...)` with no `catch` in `src/container-runner.ts:537-543` and `src/container-runner.ts:641-651`;
- the wrapped callback updates SQLite session state before delegating in `src/index.ts:313-322`, so a DB error is enough to reject the chain.

Impact:
- one callback failure leaves `runContainerAgent()` unresolved even after the container has exited;
- `processGroupMessages()` never returns, which leaves the group queue slot active and blocks further work for that group.

Why `[TC11]`:
- the close path models only the success transition for callback settlement and has no failure transition.

### CTR.PARSE.02 [TC09] S3

`parseBuffer` is unbounded in streaming mode, even though the log copies of stdout and stderr are capped.

Evidence:
- every stdout chunk is appended to `parseBuffer` in `src/container-runner.ts:421-427`;
- the buffer is only sliced after a complete end marker is found in `src/container-runner.ts:425-432`;
- unlike `stdout` and `stderr`, there is no size guard on `parseBuffer`.

Impact:
- a broken runner that emits a start marker without a matching end marker can grow host memory until the process slows or crashes;
- this failure mode bypasses the existing output truncation guard, so the operator gets the appearance of bounded logging while the parser state grows without limit.

Why `[TC09]`:
- the parser assumes partial output still belongs to a valid framed message and keeps correlating future bytes to it forever.

### AGR.SPIN.02 [TC10] S3

Spin detection treats "no text result yet" as equivalent to "poisoned session", which can abort legitimate tool-heavy work.

Evidence:
- `messageCount` increments for every SDK event in `container/agent-runner/src/index.ts:442-458`;
- `textResultCount` only increments for non-empty text `result` messages in `container/agent-runner/src/index.ts:477-487`;
- after 150 total events with zero text results, the runner emits an error and discards the session in `container/agent-runner/src/index.ts:489-501`;
- the same loop explicitly allows task/team/tool-oriented workflows in `container/agent-runner/src/index.ts:407-417`.

Impact:
- long-running tool execution, subagent orchestration, or system-heavy turns can cross the threshold without being stuck;
- the session is discarded and the turn fails even though the agent may still have been making forward progress.

Why `[TC10]`:
- the heuristic proves an adjacent symptom ("no text yet") instead of the claimed capability failure ("session is spinning/poisoned").

## Coverage Notes

Observed coverage:
- `src/group-queue.test.ts` passed in this environment.
- `src/container-runner.test.ts` did not execute because importing `src/container-runtime.ts` hit `os.networkInterfaces()` and failed with `uv_interface_addresses returned Unknown system error 1`.

Gaps that matter for Phase 1:
- no test exercises piped-message crash recovery across `lastAgentTimestamp` plus IPC files;
- no test covers streaming-mode close with malformed JSON or zero valid markers;
- no test covers rejection of `onOutput()` in the streaming close path;
- no test covers the 150-event spin heuristic against tool-heavy but healthy workflows.

## Next Scope

Recommended next step:
- continue with Phase 2 from `docs/d2/review-taxonomy.md` and keep appending findings to the same taxonomy table format.
