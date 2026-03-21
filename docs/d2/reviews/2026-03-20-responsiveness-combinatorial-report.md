---
title: "Responsiveness Combinatorial Pass"
category: review
status: active
created: 2026-03-20
---

# Responsiveness Combinatorial Pass

Date: 2026-03-20

Input findings:
- `OBS.LOG.01`
- `OBS.LOG.02`
- `RESP.IPC.01`
- `CTR.PARSE.01`
- `SVC.SHUT.01`
- `RESP.BOUNDARY.01`

Input table:
- `docs/d2/reviews/2026-03-20-responsiveness-review-findings-table.md`

## Summary

This pass found 5 interaction risks that are materially worse than the individual findings alone.

| Metric | Value |
|--------|-------|
| Total COMB findings | 5 |
| Escalated findings | 5 |
| Net severity delta | +5 |

Top connected findings:
- `OBS.LOG.02` appears in 3 COMB findings.
- `RESP.IPC.01` appears in 2 COMB findings.
- `CTR.PARSE.01` and `SVC.SHUT.01` each appear in 2 COMB findings.

The dominant pattern is not a single broken component. It is that the system commits work early, abandons work during shutdown, and lacks a durable response record. In combination, those properties turn recoverable failures into silent message loss.

## COMB Findings

### COMB.RACE.01 <- RESP.IPC.01 x SVC.SHUT.01 S1

Interaction:
- `RESP.IPC.01` already commits a follow-up message at IPC-file creation time rather than container-consumption time.
- `SVC.SHUT.01` exits the host process without draining or stopping active containers, then startup cleanup kills whatever is still running.

Why this is worse than either finding alone:
- the vulnerable window in `RESP.IPC.01` is normally "host crashes before container drains the file";
- `SVC.SHUT.01` turns that window into a routine operational path during any restart.

Escalation:
- both constituent findings are `S2`;
- per `COMB.RACE`, shared timing window plus state corruption risk escalates one level above the worse finding;
- result: `S1`.

User-visible effect:
- a follow-up message sent to an already-active container can disappear during restart churn without retry and without any visible response.

### COMB.SILENT.01 <- OBS.LOG.02 x CTR.PARSE.01 S1

Interaction:
- `CTR.PARSE.01` allows a zero-exit container to resolve success even when no valid streamed output frame was parsed.
- `OBS.LOG.02` means there is no canonical outbound message record in SQLite to disprove that false success.

Why this is worse than either finding alone:
- parse-failure-as-success is already a dropped-response bug;
- the missing outbound DB record removes the only durable audit trail that could prove what happened after the fact.

Escalation:
- the combined failure is silent and involves dropped user-visible output;
- per `COMB.SILENT`, silent data-loss failures escalate to `S1`.

User-visible effect:
- the user sees no reply, the orchestrator keeps the cursor advanced, and the database still looks as though nothing definitive went wrong.

### COMB.SILENT.02 <- OBS.LOG.01 x OBS.LOG.02 S1

Interaction:
- `OBS.LOG.01` makes fleet conversation pairing unreliable by fabricating pm2 dates and collapsing multi-part responses.
- `OBS.LOG.02` removes any authoritative SQLite response record that could compensate for broken log pairing.

Why this is worse than either finding alone:
- broken log pairing would be survivable if SQLite held outbound truth;
- missing outbound SQLite would be survivable if pm2 pairing were trustworthy enough for reconstruction;
- together, they leave operators unable to distinguish "no response generated" from "response generated but not reconstructed".

Escalation:
- this is a silent observability failure that destroys the response audit trail;
- per `COMB.SILENT`, silent audit-trail loss escalates to `S1`.

Operator effect:
- incident review can misclassify real outages as log artefacts and log artefacts as real outages.

### COMB.BOUNDARY.01 <- RESP.IPC.01 x CTR.PARSE.01 S1

Interaction:
- `RESP.IPC.01` commits piped follow-up input on the host side before container-side consumption is acknowledged.
- `CTR.PARSE.01` accepts container process exit as success even when host-side parsing never produced a valid output frame.

Why this is worse than either finding alone:
- the host/container boundary has no end-to-end acknowledgement for either "input consumed" or "output delivered";
- one side commits the input early and the other side accepts output success too loosely.

Escalation:
- this is a cross-boundary composition with no compensating control on either side;
- the combined failure can lose user-visible work;
- per `COMB.BOUNDARY`, cross-boundary data-loss interactions escalate to `S1`.

User-visible effect:
- a follow-up message can be considered handled end to end even when the host never observed a valid response payload.

### COMB.CASCADE.01 <- RESP.BOUNDARY.01 x SVC.SHUT.01 x OBS.LOG.02 S1

Interaction chain:
1. `RESP.BOUNDARY.01` allows an SDK/proxy stall to hold a turn open until the outer container timeout budget is exhausted.
2. `SVC.SHUT.01` means a restart during that stall abandons the host callback path and kills surviving containers on the next startup.
3. `OBS.LOG.02` means there is still no outbound SQLite record to show whether any partial response was ever produced.

Why this is worse than the individual findings:
- the stall itself is only latency until a restart intersects it;
- the restart turns latency into a dropped turn;
- the missing outbound record makes that dropped turn hard to diagnose and easy to misclassify.

Escalation:
- this is a 3-link failure chain;
- per `COMB.CASCADE`, 3+ link chains escalate to `S1`.

User-visible effect:
- prolonged silence degrades into a hard non-response during service churn, with weak postmortem evidence.

## Patterns Checked With No New COMB Finding

- `COMB.AUTH`: no new composition from the confirmed responsiveness findings. The reviewed set did not contain a primary authorization-layer defect.
- `COMB.STATE`: no clean two-writer divergence pair among the confirmed findings. The earlier guide concerns about router cursor persistence were stale in current code.

## Recommended Fix Order After The Combinatorial Pass

1. Fix `OBS.LOG.02` first. It is the most connected finding and amplifies three separate interaction risks.
2. Fix `RESP.IPC.01` next. Early commit of piped follow-up messages is the main bridge from transient failures to permanent message loss.
3. Fix `SVC.SHUT.01` next. Restart churn currently converts recoverable in-flight work into dropped turns.
4. Fix `CTR.PARSE.01` after that so output framing becomes a real contract rather than best-effort parsing.
5. Fix `OBS.LOG.01` once outbound persistence exists, so fleet review can trust both the primary store and the fallback logs.
6. Add request-level timeouts and cancellation for `RESP.BOUNDARY.01` to keep hung turns from feeding the restart-loss path.

## Notes

This pass was performed against the completed primary findings table. I did not perform a fresh code review beyond checking that the proposed interactions were structurally possible in the already-reviewed paths.
