---
title: "Combinatorial Risk Pass"
category: review
status: active
created: 2026-03-20
---

# Combinatorial Risk Pass

Separate review step, executed **after** the primary taxonomy-labelled review is complete. Takes the full findings table as input and looks for interactions between findings that elevate risk beyond what any single label captures.

This is not a re-review. It is a second-order analysis: given N findings, which subsets combine into something worse than the sum?

---

## When to Run

After the primary review (all 6 phases of `review-taxonomy.md`) has produced a labelled findings table. The combinatorial pass reads that table — it does not re-read source code unless a specific interaction needs verification.

**Input:** Completed findings table with `{DOMAIN}.{DIMENSION}.{##} [TC##] S{1-4}` labels.
**Output:** Interaction findings labelled `COMB.{PATTERN}.{##}` with escalated severity where warranted.

---

## Interaction Patterns

### COMB.RACE — Temporal Interactions

Findings in different domains that share a time window where both are vulnerable simultaneously.

**Where to look:**
- `ORK.CUR` × `CTR.TIMEOUT` — cursor advanced, container killed by timeout before first output. Does rollback fire? What if the timeout fires during the rollback?
- `ORK.MSG.02` × `GQ.PREEMPT.01` — pipe-vs-queue decision races with idle preemption. Message piped to a container that's being closed.
- `IPC.TRANSPORT.01` × `AGR.LOOP.02` — host polls at 1s, container polls at 500ms. Messages can arrive in the gap between container query completion and next IPC poll.
- `SCHED.POLL.01` × `IPC.TASK` — task paused between getDueTasks() and enqueue. Re-check catches this, but what about cancel?

**Escalation rule:** If two findings share a time window and either can corrupt state, escalate the pair to max(S_a, S_b) - 1 (i.e., one level above the worse of the two).

---

### COMB.AUTH — Authorization Chain Interactions

Findings across the security layers where a weakness in one layer is only safe because another layer compensates. If both are weak, the composition fails.

**Where to look:**
- `SEC.L3` × `CTR.MNT` — mount security validates paths, container runner constructs them. If construction bypasses validation (e.g., late-added mount), the security layer is decorative.
- `SEC.L2.04` × `CTR.SPAWN.02` — credential proxy keeps keys out of containers, but environment injection puts the proxy URL in. If proxy URL is predictable and proxy has no container identity check, any process on the Docker network can use it.
- `MCP.AUTH.01` × `IPC.MSG.01` — container-side authorization reads environment variables set by the host. If a container can modify its own environment (unlikely in Docker, but worth verifying), the authorization is self-asserted.
- `SEC.L5.03` × `CHL.TG.07` — sender allowlist falls back to allow-all on invalid config; Telegram JID bootstrap claims all tg: JIDs. Combined: misconfigured allowlist + first-boot Telegram = no filtering.

**Escalation rule:** If the compensating layer has any finding rated S3 or above, escalate the dependent finding by one severity level.

---

### COMB.STATE — State Coherence Interactions

Findings where two components hold views of the same state that can diverge.

**Where to look:**
- `ORK.STATE.02` × `CTR.CHAIN.02` — session ID updated in both streaming callback and synchronous return. If both fire for different values, which wins? Does the DB end up with the older one?
- `ORK.STATE.03` × `IPC.TASK.03` — group registry in memory vs. registered_groups in SQLite. register_group writes to DB and mutates the in-memory map. What if the DB write succeeds but the map mutation throws?
- `DAT.SCHEMA.08` × `HALO.HALCTL.04` — sessions table written by both the orchestrator (via db.ts) and halctl (via sqlite3 CLI). No locking between the two. halctl session clear during an active container could orphan the session.
- `ORK.CUR.01` × `DAT.SCHEMA.07` — cursor persisted in router_state, but lastAgentTimestamp is in-memory only. Process crash between cursor advance and saveState() means the in-memory cursor is lost but the DB cursor is stale.

**Escalation rule:** If both components can write and neither checks the other's version, escalate to S2 minimum regardless of individual findings.

---

### COMB.BOUNDARY — Cross-Boundary Interactions

Findings where a weakness spans the host/container boundary, the TypeScript/Python boundary, or the channel/orchestrator boundary.

**Where to look:**
- `CTR.PARSE.02` × `AGR.LOOP.01` — host-side parseBuffer has no bounds check; container-side MessageStream keeps isSingleUserTurn false indefinitely. A spinning agent that emits partial markers without completing them grows the buffer without limit.
- `MCP.GAP.01` × `HALO.CRON.01` — agent's list_tasks sees only nanoclaw-internal tasks; cronctl manages external cron jobs. Agent confidently answers "no tasks scheduled" while cron jobs exist. This is a known gap but the combinatorial question is: does any other finding make it worse? (e.g., if briefings also query list_tasks instead of cronctl)
- `CHL.TG.03` × `FLT.TOPO.01` — bot pool assigns personas per group:sender pair, fleet topology isolates instances. If a fleet instance somehow shares a bot pool slot with prime (misconfigured TELEGRAM_BOT_POOL), persona identity leaks across the isolation boundary.
- `IPC.TRANSPORT.03` × `SCHED.RUN.03` — IPC files deleted after read, task run logged to DB. If the IPC file is read and deleted but the task_run_logs write fails, the execution happened but left no audit trail.

**Escalation rule:** Cross-boundary interactions where both sides lack compensating controls escalate to S1 if either side involves security (SEC/MCP.AUTH) or data loss (DAT).

---

### COMB.CASCADE — Failure Cascade Interactions

Findings where one failure triggers or worsens another in a chain.

**Where to look:**
- `GQ.RETRY.02` × `ORK.CUR.02` — max retries exhausted → messages dropped. But cursor was already advanced (ORK.CUR.01). Dropped messages are invisible — no cursor rollback because the container did run (just failed).
- `CTR.TIMEOUT.02` × `GQ.SHUT.01` — timeout reaps container via docker stop; shutdown detaches. If both fire simultaneously (SIGTERM during idle timeout), does the container get stopped twice? Does the group-queue state become inconsistent?
- `AGR.SPIN.01` × `ORK.STATE.02` — spin detection discards session (returns without newSessionId). Orchestrator receives no session update. But the old session ID is still in the sessions table. Next message resumes the poisoned session.
- `DAT.MIG.02` × `DAT.MIG.03` — no version tracking + backfill logic. If a backfill partially completes and the process crashes, the next startup tries the ALTER (caught), skips the backfill (already ran the ALTER), and leaves data half-backfilled with no way to detect it.

**Escalation rule:** If a chain has 3+ links, escalate the terminal finding to S1 regardless of individual severities. Two-link chains escalate the terminal finding by one level.

---

### COMB.SILENT — Silent Failure Interactions

Findings where error handling in one component hides a failure that another component needs to see.

**Where to look:**
- `CTR.PARSE.03` × `ORK.CUR.02` — JSON parse failure in container output logs a warning but doesn't propagate. Orchestrator sees "had streaming output" (because markers were detected) and keeps cursor advanced. But the actual content was garbage.
- `DAT.MIG.01` × `DAT.MIG.02` — ALTER TABLE wrapped in try-catch. If the ALTER fails for a reason *other than* "column already exists" (e.g., disk full, table locked), the error is silently swallowed. Downstream code assumes the column exists.
- `MCP.GAP.02` × `IPC.TRANSPORT.03` — fire-and-forget IPC tool returns "requested". Host reads and deletes the file. If the host-side dispatch fails after file deletion, the message is lost with no error visible to the agent or the user.
- `HALO.BRIEF.01` × `HALO.REPORT.01` — briefings cascade through 3 synthesis strategies. If claude CLI fails silently (exit 0, empty output), the briefing is "delivered" but content-free. Does the raw fallback detect this?

**Escalation rule:** If the silent failure involves data loss or security (message dropped, credential leaked, audit trail lost), escalate to S1. Otherwise escalate by one level.

---

## Composite Label Format

```
COMB.{PATTERN}.{##} ← {FINDING_A} × {FINDING_B} [× {FINDING_C}] S{1-4}
```

**Examples:**

| Label | Interaction | Escalated From |
|-------|-------------|----------------|
| `COMB.RACE.01 ← ORK.CUR.03 × CTR.TIMEOUT.02` S2 | Cursor advanced, container killed before output | ORK.CUR.03 was S3 |
| `COMB.AUTH.01 ← SEC.L5.03 × CHL.TG.07` S2 | Allow-all fallback + JID bootstrap = no filtering | SEC.L5.03 was S3 |
| `COMB.STATE.01 ← ORK.STATE.02 × CTR.CHAIN.02` S2 | Session ID dual-write race | Both were S3 |
| `COMB.CASCADE.01 ← AGR.SPIN.01 × ORK.STATE.02` S1 | Spin discard doesn't clear DB session → poisoned resume | AGR.SPIN.01 was S2 |
| `COMB.SILENT.01 ← CTR.PARSE.03 × ORK.CUR.02` S2 | Garbage parse + cursor kept → lost messages | CTR.PARSE.03 was S4 |

---

## Procedure

1. **Collect** the completed findings table from the primary review.
2. **For each interaction pattern** (RACE, AUTH, STATE, BOUNDARY, CASCADE, SILENT):
   - Walk the "where to look" checklist.
   - For each pair/chain that has findings on both sides, evaluate whether the interaction creates a new risk.
   - If yes, create a `COMB.*` finding with the constituent labels and apply the escalation rule.
3. **De-duplicate** — if the same pair appears in multiple patterns, keep the higher-severity classification.
4. **Produce a summary table** with:
   - Total COMB findings
   - Escalation count (how many findings changed severity)
   - Net severity delta (sum of all escalations)
   - Top 3 most connected findings (findings that appear in the most COMB pairs)

---

## Review of the Review

This document itself should be reviewed for:

- **Completeness** — are there interaction patterns not covered by these six categories? (Likely candidates: resource exhaustion interactions, timing-dependent data corruption, configuration drift between environments.)
- **False positives** — do any "where to look" items describe interactions that are structurally impossible given the architecture? (e.g., if Docker guarantees make a container environment mutation impossible, COMB.AUTH.01's MCP.AUTH concern is moot.)
- **Escalation calibration** — are the escalation rules too aggressive (everything becomes S1) or too conservative (real risks stay at S3)?

After the combinatorial pass, append findings to the same comparison table used by the primary review. The before/after diff now captures both individual and interaction risks.
