---
title: "Responsiveness Review Guide"
category: review
status: active
created: 2026-03-20
---

# Responsiveness Review Guide

Systematic code review for the microhal-ben non-response / hung server pattern. Multiple targeted fixes have not resolved the issue — this guide steps back to examine the full message-to-response lifecycle and all the places where a message can enter the system and never produce a visible response.

**Symptom summary (from 24h log survey, 2026-03-19):**

1. Ben explicitly reported HAL not responding at least 8 times during the day
2. Three `Failed with result 'timeout'` events overnight (01:43, 03:34, 06:06 UTC)
3. Final message of the day produced an explicit `Request timed out`
4. The 18:32 spam incident (29 identical messages) suggests prolonged unresponsiveness
5. `logctl fleet --conversations` showed `[no response captured]` on 413/413 entries — **this is a logctl pairing bug, not a response generation bug** (see OBS.LOG.01)

---

## Label Hierarchy

```
INGEST     — Message ingestion (Telegram → SQLite → message loop)
ORCH       — Orchestrator message processing and cursor management
GQ         — Group queue: concurrency, enqueue, drain, retry
CTR        — Container lifecycle: spawn, timeout, shutdown, cleanup
AGR        — Agent runner (container-side): SDK query, IPC, spin detection
STREAM     — Streaming response path: markers, parse, callback chain
SESS       — Session management: resume, poison, clear
IPC        — IPC transport: host↔container file-based messaging
ROUTE      — Outbound routing: format, channel dispatch, delivery
FLEET      — Fleet topology: instance isolation, credential proxy, pm2
OBS        — Observability: logging, logctl, response pairing
SVC        — Service lifecycle: systemd, pm2, restart, shutdown
```

---

## Phase 1: Observability (can we even see the problem?)

### OBS.LOG.01 — logctl fleet conversation pairing is broken

**File:** `halos/logctl/fleet.py:180-208`

**Bug:** `_pm2_to_iso()` at line 180-182 converts pm2's `HH:MM:SS.mmm` timestamps to ISO by prepending **today's date** (`now.strftime("%Y-%m-%dT")`). The pm2 log file spans multiple days (9384 lines for ben). All historical entries get today's date, making the user→agent timestamp pairing fail for every entry not from today.

**Evidence:** pm2 log has 431 `Agent output:` lines and 433 `Telegram message sent` lines — the agent IS responding. logctl just can't pair them.

**Impact:** Complete blindness to agent response content in fleet conversation view. The "no response captured" label is a logging artefact, not evidence of non-response.

**Fix surface:** `fleet.py:180-208` — need date inference from pm2 log context (file mtime, timestamp rollover detection, or cross-referencing SQLite message timestamps).

### OBS.LOG.02 — No structured response logging

**File:** `src/index.ts:226-233`

The only record of what the agent said is `Agent output: ${raw.slice(0, 200)}` in the pm2 log (pino format, no date in timestamp). The response is NOT stored in SQLite `messages` table as an `is_from_me=1` record.

**Impact:** No queryable record of agent responses. Cannot correlate user messages with agent responses except by timestamp proximity in log files. Cannot distinguish "agent responded but logctl missed it" from "agent genuinely didn't respond."

**Review:** Check whether `storeMessage()` is ever called for outbound messages. If not, this is a design gap.

### OBS.LOG.03 — pm2 timestamp has no date component

**File:** pm2 log format: `[HH:MM:SS.mmm] LEVEL (pid): message`

pm2's default log format omits the date. Combined with OBS.LOG.01, this makes cross-day analysis unreliable. The systemd unit redirects stdout to `logs/nanoclaw.log` — check whether this file has the same format or includes dates.

**Review:** `~/.config/systemd/user/nanoclaw.service` — StandardOutput goes to `logs/nanoclaw.log`. Is the pm2 log a different output path? Are both active simultaneously?

---

## Phase 2: Message Ingestion

### INGEST.01 — Telegram polling reliability

**File:** `src/channels/telegram.ts:1-20`

Grammy bot uses long-polling. DNS is forced to IPv4 (line 7) to prevent IPv6 stalls. But long-poll can still fail silently if the Telegram API returns errors that Grammy swallows.

**Review:** Is there error handling on the Grammy `bot.start()` / `bot.on('message')` path? Does a Telegram API timeout cause the bot to stop polling without notification?

### INGEST.02 — Sender allowlist filtering

**File:** `src/index.ts:581-596`

Messages from non-allowlisted senders are dropped before storage. If ben's Telegram user ID isn't in the allowlist for his instance, his messages silently vanish.

**Review:** Verify ben's instance allowlist includes his Telegram sender ID. Check whether allowlist failures are logged.

### INGEST.03 — Trigger pattern gate

**File:** `src/index.ts:175-182`

Non-main groups require a trigger pattern match before processing. If ben's group is misconfigured as non-main, messages without the trigger pattern are ignored.

**Review:** Verify ben's group configuration — is it flagged as `isMain: true`?

---

## Phase 3: Orchestrator / Message Loop

### ORCH.01 — Message loop polling interval

**File:** `src/config.ts:20` — `POLL_INTERVAL = 2000`

The message loop checks for new messages every 2 seconds. This adds 0-2s latency to every response cycle. Not a bug, but contributes to perceived slowness.

**Review:** Check whether the loop has any blocking operations that could extend beyond 2s (e.g., synchronous DB queries, DNS lookups).

### ORCH.02 — Cursor advancement before response

**File:** `src/index.ts:190-196`

`lastAgentTimestamp[chatJid]` is advanced to the latest message timestamp BEFORE the container is spawned. If the container fails to respond, the cursor rollback at line 265 should recover — but only if `outputSentToUser` is false.

**Race condition:** If the agent sends one successful output (setting `outputSentToUser = true`) and then errors on subsequent processing, the cursor is NOT rolled back (line 257-262). Any messages that arrived during that processing window are permanently skipped.

**Review:** Trace the exact sequence: message arrives → cursor advances → container spawns → first output sent → error occurs → cursor NOT rolled back → next poll finds no new messages (cursor already past them).

### ORCH.03 — `saveState()` timing

**File:** `src/index.ts:266`

`saveState()` persists the rolled-back cursor. But if the process crashes between cursor advancement (line 190) and error recovery (line 265), the advanced cursor is persisted to disk and the messages are lost.

**Review:** Where is `saveState()` called on the happy path? Is it called after cursor advancement but before the container starts?

### ORCH.04 — `lastAgentTimestamp` is in-memory only

**File:** `src/index.ts` — `lastAgentTimestamp` map

This is the in-memory cursor for "which messages has the agent seen." It's loaded from `router_state` on startup and saved via `saveState()`. But `saveState()` is not called after every cursor advance.

**Review:** Trace all `saveState()` call sites. Verify that a crash during container execution doesn't leave the cursor in an advanced state that skips messages on restart.

---

## Phase 4: Group Queue / Concurrency

### GQ.01 — Concurrency limit blocking

**File:** `src/group-queue.ts:73` / `src/config.ts:68-70`

`MAX_CONCURRENT_CONTAINERS = 5`. If 5 containers are already running (across all groups), ben's messages queue in `waitingGroups` until a slot opens. With 30-minute idle timeouts, a busy system could delay ben's response by minutes.

**Review:** Check `activeCount` at the time of ben's non-responses. Are other groups consuming all container slots?

### GQ.02 — Retry exhaustion drops messages

**File:** `src/group-queue.ts:263-284`

After 5 exponential backoff retries (5s → 80s), messages are dropped with no user notification. The only recovery is a new incoming message that re-triggers processing.

**Review:** Does the retry counter ever get stuck? Is it reset on success? What happens if the container keeps failing — does ben just get silence until he sends another message?

### GQ.03 — `drainGroup()` ordering

**File:** `src/group-queue.ts:224-231`

After a container finishes, `drainGroup()` checks for pending tasks before pending messages. If there are always pending tasks (e.g., from IPC or scheduler), messages could be indefinitely deprioritised.

**Review:** Are there any recurring tasks that constantly refill the pending task queue?

### GQ.04 — `notifyIdle()` / `closeStdin()` interaction

**File:** `src/group-queue.ts:160-194`

`notifyIdle()` sets `idleWaiting = true`. If `pendingTasks` is non-empty, it immediately calls `closeStdin()`. But if `pendingMessages` arrives between `notifyIdle()` and the next `drainGroup()` cycle, the container is already closing and the message has to wait for a full new container spawn.

**Review:** Trace the timing: agent finishes → `notifyIdle()` → IPC message arrives → `closeStdin()` fires → container exits → new message from ben arrives → has to wait for new spawn.

---

## Phase 5: Container Lifecycle

### CTR.01 — Container spawn failure

**File:** `src/container-runner.ts:395-402`

If `docker run` fails (image not found, Docker daemon down, OOM), the error is caught but the recovery path matters.

**Review:** What happens to the group queue state when spawn fails? Is `state.active` set back to false? Is `activeCount` decremented?

### CTR.02 — Streaming output marker parsing

**File:** `src/container-runner.ts:403-453`

Output is parsed via `---NANOCLAW_OUTPUT_START---` and `---NANOCLAW_OUTPUT_END---` markers. If the agent produces output without markers (e.g., raw stderr, SDK error messages), the output is captured in the log but never triggers `onOutput()`.

**Review:** What happens if the SDK itself crashes with an error message to stdout that doesn't contain markers? The output exists but is invisible to the callback chain.

### CTR.03 — Hard timeout vs. idle timeout race

**File:** `src/container-runner.ts:477-507`

Hard timeout = `max(configTimeout, IDLE_TIMEOUT + 30_000)` = 1830s. Idle timeout = 1800s. The idle timeout sends a `_close` sentinel, then the hard timeout has 30s to kill the container if it doesn't exit gracefully.

**Race:** If the agent is genuinely processing (not idle) but takes >1800s, the idle timeout fires first, sending `_close`. The agent may be mid-response when it receives the close signal. Does it finish the current response or abort?

**Review:** Check agent-runner's `shouldClose()` — does it check the close signal between SDK turns, or can it interrupt a turn in progress?

### CTR.04 — `docker stop` timeout chain

**File:** `src/container-runner.ts:490`

When hard timeout fires: `docker stop` (15s grace) → SIGKILL. But the systemd service has no `TimeoutStopSec` override, defaulting to 90s. If systemd sends SIGTERM to the Node process, which then needs to stop Docker containers, the 15s Docker grace + cleanup may exceed systemd's 90s window.

**Evidence:** Three `Failed with result 'timeout'` events overnight confirm this chain is happening.

**Review:** `~/.config/systemd/user/nanoclaw.service` — add `TimeoutStopSec=120` or implement a SIGTERM handler in `src/index.ts` that aggressively kills containers.

### CTR.05 — Container cleanup on process exit

**File:** `src/index.ts` — process exit handling

When the Node process receives SIGTERM (from systemd restart), what happens to running containers? Are they `docker stop`'d? Are they left orphaned? Do orphaned containers hold open the Docker network, preventing the next process instance from binding?

**Review:** Search for `process.on('SIGTERM'` / `process.on('exit'` handlers. Verify containers are cleaned up.

---

## Phase 6: Agent Runner (Container Side)

### AGR.01 — SDK `query()` hang

**File:** `container/agent-runner/src/index.ts:332-508`

The Claude SDK `query()` call can hang if the API is slow, rate-limited, or the session is corrupted. The agent-runner has spin detection (150 turns, 0 text results) and rate-limit early exit (first 10 messages), but no wall-clock timeout on a single `query()` call.

**Review:** Does `query()` have an internal timeout? If the API hangs indefinitely, does the container just sit there? The hard timeout on the host side would eventually kill it, but that's 1830s of silence.

### AGR.02 — `isSingleUserTurn` and message accumulation

**File:** `container/agent-runner/src/index.ts` — `MessageStream` class

The `MessageStream` accumulates messages from IPC. If `isSingleUserTurn` is false, the SDK keeps waiting for more input. A slow host-side poll (1000ms IPC interval) means the container might be sitting idle waiting for a message that the host hasn't written yet.

**Review:** How does the `MessageStream` determine when to yield messages to the SDK? Is there a timeout on waiting for additional messages?

### AGR.03 — `shouldClose()` check frequency

**File:** `container/agent-runner/src/index.ts` — `shouldClose()`

The close signal (`_close` sentinel file) is only checked between query turns, not during a turn. If a single query takes 10+ minutes, the container doesn't check for close until after the query completes.

**Review:** Does this explain the overnight timeouts? Container is mid-query, idle timeout fires, host writes `_close`, container doesn't see it for 30 minutes, hard timeout kills it, `docker stop` takes 15s, systemd waits 90s, timeout failure logged.

### AGR.04 — Session resume on bloated context

**File:** `container/agent-runner/src/index.ts:464-475`

When resuming a session, if the session has grown large (ben sends hundreds of messages per day, many with large paste blocks), the SDK may need to download/process a large context window. This could cause the first query to take minutes.

**Review:** What's the size of ben's current session? Is the resume time correlated with non-response incidents? Would periodic session clearing prevent context bloat?

---

## Phase 7: Session Management

### SESS.01 — Poisoned session recovery

**File:** `src/index.ts:312-324`

When `status = 'error'` and no `newSessionId` is returned, the session is cleared. But what if the container exits with code 0, status 'success', and a stale `newSessionId`? The session is saved, and the next message resumes into a potentially poisoned context.

**Review:** What exit scenarios produce `status: 'success'` with a stale/corrupt session ID?

### SESS.02 — Dual-write between orchestrator and halctl

**File:** `src/db.ts:540-568` + `halos/halctl/session.py`

Both the orchestrator (via `setSession()`) and halctl (via `sqlite3` CLI) write to the `sessions` table. No locking between them. A `halctl session clear` during an active container run could cause the orchestrator to save a new session ID over the cleared entry, or the clear could race with a write.

**Review:** Is this a practical risk? Does halctl wait for container shutdown before clearing?

### SESS.03 — Session size growth

Ben sends massive message volumes with large paste blocks (full emails, PDF excerpts, Gemini responses). Each message extends the session context. The SDK session file grows without bound until explicitly cleared.

**Review:** What's the current session size for ben's primary group? Is there a mechanism to auto-clear sessions that exceed a size threshold?

---

## Phase 8: IPC Transport

### IPC.01 — Host→container message delivery lag

**File:** `src/ipc.ts` + `container/agent-runner/src/index.ts:59`

Host writes IPC files at 1000ms poll intervals. Container reads them at 500ms intervals. In the worst case, a message has 1500ms latency from host write to container read. This adds up when ben sends rapid-fire messages.

**Review:** Is the IPC file system mounted correctly for ben's instance? Are there permission issues that cause file reads to fail silently?

### IPC.02 — `_close` sentinel delivery

**File:** `src/group-queue.ts:183-194`

The `_close` sentinel is written as an empty file. If the filesystem mount is slow or the container's IPC poll misses it, the close signal is delayed.

**Review:** Verify the IPC mount path for fleet instances. Does ben's instance have the same mount configuration as prime?

### IPC.03 — Fire-and-forget IPC responses

**File:** `src/ipc.ts:40-164`

Container→host IPC messages are written as files, read and deleted by the host. If the host reads the file and then crashes before processing it, the message is lost. No acknowledgment protocol.

**Review:** Can this cause a state where the container thinks it delivered a response but the host never forwarded it to Telegram?

---

## Phase 9: Outbound Routing

### ROUTE.01 — Telegram `sendMessage` failure

**File:** `src/channels/telegram.ts:40-56`

The `sendMessage` function calls the Grammy bot API. If the Telegram API returns an error (rate limit, bot blocked, network issue), how is this handled?

**Review:** Is there retry logic? Is the failure logged? Does a failed send cause the whole `onOutput()` callback to throw, which might prevent subsequent outputs from being delivered?

### ROUTE.02 — `<internal>` tag stripping leaves empty string

**File:** `src/index.ts:225-237`

If the agent's entire response is wrapped in `<internal>` tags, the stripped text is empty and `sendMessage` is not called. The agent "responded" but the user sees nothing.

**Review:** How often does the agent produce internal-only responses? Is there a fallback for empty post-strip text?

### ROUTE.03 — Markdown parse failure fallback

**File:** `src/channels/telegram.ts:40-56`

If the agent's response contains invalid Markdown (e.g., unclosed backticks, unescaped special chars), Grammy may fail to send. Is there a fallback to plain text?

**Review:** Check for try/catch around `sendMessage` with Markdown parse mode.

---

## Phase 10: Fleet Topology

### FLEET.01 — Credential proxy routing

**File:** `src/config.ts:60-65` + `src/credential-proxy.ts`

Ben's containers route API calls through prime's credential proxy. If the proxy is down, restarting, or rate-limited, ben's containers hang waiting for API responses with no visible error to the user.

**Review:** Is the credential proxy health-checked? What's the proxy timeout? Does the proxy have its own retry logic that could add minutes of latency?

### FLEET.02 — pm2 vs systemd dual management

The fleet uses pm2 (`halfleet/ecosystem.config.js`) while prime uses systemd (`nanoclaw.service`). The systemd unit outputs to `logs/nanoclaw.log`, pm2 outputs to `~/.pm2/logs/microhal-ben-out.log`. These are independent processes.

**Review:** When systemd restarts the prime process (which hosts the credential proxy), do pm2 fleet instances detect the proxy outage? Or do they hang?

### FLEET.03 — Container network isolation

Ben's containers spawn on the same Docker network as prime's containers. If prime's containers are consuming Docker resources (network, CPU, memory), ben's containers may be starved.

**Review:** Check Docker resource limits. Are containers constrained by `--memory` or `--cpus` flags? Is the Docker daemon itself healthy during the overnight timeout periods?

---

## Phase 11: Service Lifecycle

### SVC.01 — No `TimeoutStopSec` in systemd unit

**File:** `~/.config/systemd/user/nanoclaw.service`

The unit has `Restart=always` and `RestartSec=5` but no `TimeoutStopSec`. Default is 90s. If the process takes >90s to clean up containers on SIGTERM, systemd force-kills it.

**Evidence:** Three `Failed with result 'timeout'` events overnight. The process is not shutting down within 90s.

**Review:** Add `TimeoutStopSec=180` and/or implement a SIGTERM handler that:
1. Stops accepting new messages
2. Sends `docker stop` to all active containers in parallel
3. Waits for container exits (with 15s grace)
4. Exits cleanly

### SVC.02 — Restart during active conversations

When systemd restarts the process (either from `Restart=always` after a failure or from `systemctl --user restart`), all active containers are orphaned. On restart, the orchestrator loads sessions from DB but containers are gone. The next message spawns a new container, resuming the session — but any in-flight response from the old container is lost.

**Review:** Is there a container cleanup on startup? Does the process check for orphaned Docker containers from previous runs?

### SVC.03 — Overnight restart churn

**Evidence:** Between 01:41 and 06:06, the service restarted 7 times (including 3 timeout failures). This churn means:
- Containers are repeatedly spawned and killed
- Sessions may be corrupted by partial writes
- Any message sent during a restart window is either lost or delayed

**Review:** What triggers these overnight restarts? Are they caused by OOM, unhandled exceptions, or explicit `systemctl restart` from cron/briefings?

---

## Cross-Reference: Combinatorial Risks

Per `docs/d2/review-combinatorial-pass.md`, the following interaction patterns are relevant:

| Pattern | Findings | Risk |
|---------|----------|------|
| `COMB.RACE` | ORCH.02 × CTR.03 | Cursor advanced, container killed by idle timeout before response delivered. Messages skipped. |
| `COMB.STATE` | ORCH.04 × SVC.02 | In-memory cursor lost on restart, DB cursor stale. Messages re-processed or skipped. |
| `COMB.CASCADE` | AGR.01 → CTR.04 → SVC.01 | SDK hangs → hard timeout → docker stop → systemd timeout → force kill → orphaned container |
| `COMB.SILENT` | OBS.LOG.01 × ROUTE.02 | logctl says "no response" + agent sends internal-only text = invisible failure |
| `COMB.BOUNDARY` | FLEET.01 × AGR.04 | Credential proxy down + bloated session resume = container hangs indefinitely at API call |

---

## Priority Order for Investigation

1. **OBS.LOG.01** — Fix logctl pairing first. Without accurate response visibility, every other investigation is guesswork.
2. **OBS.LOG.02** — Store outbound messages in SQLite. This gives a queryable record of what the agent actually said.
3. **SVC.01** — Add `TimeoutStopSec=180` and SIGTERM handler. Stop the overnight restart churn.
4. **CTR.05** — Implement container cleanup on startup. Kill orphaned containers from previous runs.
5. **AGR.04** — Investigate session size for ben. Consider auto-clear threshold.
6. **ORCH.02** — Verify cursor rollback logic for the "partial success then error" case.
7. **FLEET.01** — Add credential proxy health check and timeout.

---

## How to Use This Guide

This document is intended as input to a code review agent (e.g., `adversarial-reviewer`). The agent should:

1. Read each finding's file and line references
2. Verify the described behaviour against current code
3. Flag any findings that are already fixed or no longer applicable
4. Identify additional risks not covered here
5. Propose fixes ordered by impact × effort

The labels (`INGEST.01`, `ORCH.02`, etc.) can be cross-referenced with `review-combinatorial-pass.md` interaction patterns to assess compound risk.
