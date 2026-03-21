---
title: "Code Review Taxonomy"
category: review
status: active
created: 2026-03-20
---

# Code Review Taxonomy

Hierarchical labelling system for exhaustive code review of NanoClaw. Each finding is labelled on two axes:

1. **Structural label** — `{DOMAIN}.{DIMENSION}.{##}` — where in the system
2. **Error class tag** — `[TC##]` — what kind of weakness (from testing-concrete.md)

Example finding: `CTR.PARSE.02 [TC09]` — container runner, output parsing, item 02, exhibits correlation failure.

---

## Axis 1: Structural Labels

### ORK — Orchestrator (`src/index.ts`, 674 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **ORK.STATE** | Global state management | 5 mutable globals: lastTimestamp, sessions, registeredGroups, lastAgentTimestamp, queue |
| ORK.STATE.01 | Cursor persistence | loadState/saveState ↔ SQLite router_state |
| ORK.STATE.02 | Session tracking | Map<groupFolder, sessionId> — dual-update from streaming callback + sync return |
| ORK.STATE.03 | Group registry coherence | registeredGroups map loaded from DB, mutated at runtime |
| **ORK.CUR** | Cursor management | Advance-before-process + rollback-on-error semantics |
| ORK.CUR.01 | Pre-advance invariant | Cursor advanced before container spawns (crash safety) |
| ORK.CUR.02 | Rollback condition | Error-with-no-output → restore cursor; error-with-output → keep advanced |
| ORK.CUR.03 | Race window | Container crash between cursor advance and first output |
| **ORK.MSG** | Message processing | processGroupMessages flow |
| ORK.MSG.01 | Trigger checking | Trigger check in message loop AND per-group processor (divergence risk) |
| ORK.MSG.02 | Pipe vs queue decision | Active container → pipe via IPC; inactive → queue (race if container dies mid-check) |
| ORK.MSG.03 | Message deduplication | Interaction between lastTimestamp, lastAgentTimestamp, and is_bot_message filters |
| **ORK.LIFE** | Lifecycle | Startup sequence (14 steps), shutdown, signal handling |
| ORK.LIFE.01 | Startup ordering | Dependencies between steps (e.g., channels before IPC watcher) |
| ORK.LIFE.02 | Shutdown grace | Signal handlers, queue.shutdown() detach semantics |
| ORK.LIFE.03 | Recovery pass | recoverPendingMessages on restart — stalled group detection |
| **ORK.IDLE** | Idle timeout | Timer reset logic |
| ORK.IDLE.01 | Reset trigger | Resets on agent output markers only, not stderr or session updates |
| ORK.IDLE.02 | Long-thinking agents | Agents with no intermediate output may be killed prematurely |

---

### CTR — Container Runner (`src/container-runner.ts`, 781 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **CTR.MNT** | Mount construction | buildVolumeMounts — per-group filesystem isolation |
| CTR.MNT.01 | Main vs non-main divergence | Different mount sets, different RW/RO policies |
| CTR.MNT.02 | .env shadow | `.env` → `/dev/null` (secrets isolation) |
| CTR.MNT.03 | Fleet visibility | `/workspace/fleet` — main-only, read-only |
| CTR.MNT.04 | Memory overlay | `/workspace/project/memory` — writable for all groups |
| CTR.MNT.05 | Agent-runner source sync | VERSION file comparison; thrash risk if VERSION missing |
| **CTR.PARSE** | Output parsing | Sentinel marker protocol |
| CTR.PARSE.01 | Marker framing | `---NANOCLAW_OUTPUT_START---` / `---NANOCLAW_OUTPUT_END---` |
| CTR.PARSE.02 | Split-across-chunks | Circular buffer with no explicit bounds on parseBuffer size |
| CTR.PARSE.03 | JSON parse failure | Warning logged, no error propagation |
| CTR.PARSE.04 | Multiple marker pairs | One per agent turn — streaming callback chain |
| **CTR.SPAWN** | Container spawn | Docker run command construction |
| CTR.SPAWN.01 | Auth mode detection | Called every spawn, no caching |
| CTR.SPAWN.02 | Environment injection | TZ, ANTHROPIC_BASE_URL, API key/OAuth placeholder |
| CTR.SPAWN.03 | Container naming | Unique name generation |
| **CTR.TIMEOUT** | Timeout & reaping | |
| CTR.TIMEOUT.01 | Default timeout | 30 min configurable, hard minimum IDLE_TIMEOUT+30s |
| CTR.TIMEOUT.02 | Reaping semantics | docker stop (15s grace) → SIGKILL fallback |
| CTR.TIMEOUT.03 | Timeout classification | Output existed → success (idle cleanup); no output → error |
| **CTR.CHAIN** | Output chain | Promise chain for callback settlement |
| CTR.CHAIN.01 | Callback stall | Misbehaving onOutput callback stalls all subsequent messages for group |
| CTR.CHAIN.02 | Session ID extraction | Updated in streaming callback — overwrite risk |

---

### AGR — Agent Runner (`container/agent-runner/src/index.ts`, 601 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **AGR.LOOP** | Query loop | Prompt → SDK query → poll IPC → emit results → wait |
| AGR.LOOP.01 | MessageStream | Push-based async iterable keeping isSingleUserTurn false |
| AGR.LOOP.02 | IPC polling during query | Follow-up messages read while SDK query executes |
| AGR.LOOP.03 | Close sentinel detection | `_close` file during query → graceful exit |
| **AGR.SPIN** | Spin detection | Three-layer defence |
| AGR.SPIN.01 | Rate limit on resume | Within 10 messages → session poisoned, discard |
| AGR.SPIN.02 | Max turns without output | 150 messages, 0 text results → kill, discard session |
| AGR.SPIN.03 | Close sentinel | Host-initiated graceful exit |
| **AGR.SDK** | SDK configuration | |
| AGR.SDK.01 | Permission mode | bypassPermissions — no user approval in container |
| AGR.SDK.02 | Allowed tools | Bash, Read/Write/Edit, Glob/Grep, WebSearch/WebFetch, Task, MCP |
| AGR.SDK.03 | PreCompact hook | Archives transcripts to conversations/ before compaction |
| **AGR.INPUT** | Input protocol | |
| AGR.INPUT.01 | Stdin parsing | Full ContainerInput JSON |
| AGR.INPUT.02 | IPC input polling | 500ms interval, JSON files in /workspace/ipc/input/ |
| AGR.INPUT.03 | System prompt composition | Group CLAUDE.md + global CLAUDE.md |

---

### MCP — IPC MCP Server (`container/agent-runner/src/ipc-mcp-stdio.ts`, 338 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **MCP.TOOL** | Tool surface | 8 tools exposed to agents |
| MCP.TOOL.01 | send_message | Fire-and-forget JSON write |
| MCP.TOOL.02 | schedule_task | Authorization: non-main → own group only |
| MCP.TOOL.03 | list_tasks | Reads current_tasks.json snapshot (briefing gap) |
| MCP.TOOL.04 | task mutations | pause/resume/cancel/update — authorization checks |
| MCP.TOOL.05 | register_group | Main-only |
| **MCP.AUTH** | Tool authorization | isMain privilege boundary |
| MCP.AUTH.01 | Environment injection | NANOCLAW_CHAT_JID, NANOCLAW_GROUP_FOLDER, NANOCLAW_IS_MAIN |
| MCP.AUTH.02 | Non-main restrictions | Own group only for all task/message operations |
| **MCP.GAP** | Known gaps | |
| MCP.GAP.01 | Briefing gap | list_tasks has no knowledge of crontab/cronctl/external scheduling |
| MCP.GAP.02 | Fire-and-forget semantics | No delivery confirmation for any tool |

---

### IPC — Inter-Process Communication (`src/ipc.ts`, 465 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **IPC.MSG** | Message namespace | Container → host message routing |
| IPC.MSG.01 | Authorization | Main → any JID; non-main → own JID only |
| IPC.MSG.02 | Bot pool path | Telegram sender routing via sendPoolMessage |
| **IPC.TASK** | Task namespace | Large switch: schedule, pause, resume, cancel, update, refresh, register |
| IPC.TASK.01 | schedule_task auth | Non-main restricted to own group |
| IPC.TASK.02 | Task mutations auth | Group folder match required |
| IPC.TASK.03 | register_group | Main-only, folder name validation |
| IPC.TASK.04 | refresh_groups | Main-only, group metadata sync |
| **IPC.TRANSPORT** | File-based transport | |
| IPC.TRANSPORT.01 | Polling interval | 1s host-side (IPC_POLL_INTERVAL) |
| IPC.TRANSPORT.02 | Atomicity | Write-then-rename pattern |
| IPC.TRANSPORT.03 | File deletion | Deleted after read (no replay) |
| **IPC.DI** | Dependency injection | IpcDeps interface |
| IPC.DI.01 | sendMessage binding | Routed through channels |
| IPC.DI.02 | Group registry | registeredGroups, registerGroup, syncGroups |

---

### DAT — Data Layer (`src/db.ts`, 765 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **DAT.SCHEMA** | Schema (8 tables) | |
| DAT.SCHEMA.01 | chats | Chat/group metadata |
| DAT.SCHEMA.02 | messages | All inbound/outbound with sender, timestamp, bot flags |
| DAT.SCHEMA.03 | scheduled_tasks | State machine: active/paused/completed |
| DAT.SCHEMA.04 | task_run_logs | Execution history |
| DAT.SCHEMA.05 | onboarding | User onboarding state machine |
| DAT.SCHEMA.06 | assessments | Likert + qualitative responses |
| DAT.SCHEMA.07 | router_state | Key-value cursor persistence |
| DAT.SCHEMA.08 | sessions | Group folder → SDK session ID |
| DAT.SCHEMA.09 | registered_groups | Group registry with container config |
| **DAT.QUERY** | Query patterns | |
| DAT.QUERY.01 | Subquery reversal | Inner DESC LIMIT → outer ASC for newest-N-in-order |
| DAT.QUERY.02 | Bot message filtering | Dual filter: is_bot_message AND content prefix |
| DAT.QUERY.03 | Dynamic SQL in updateTask | Runtime field list construction (parameterized) |
| **DAT.MIG** | Migrations | |
| DAT.MIG.01 | Append-only ALTER TABLE | Try-catch for idempotence |
| DAT.MIG.02 | No version tracking | Can't distinguish never-migrated from already-migrated |
| DAT.MIG.03 | Backfill logic | Content prefix → is_bot_message, folder → is_main, JID patterns → channel |
| **DAT.SEC** | Security | |
| DAT.SEC.01 | Parameterized queries | No SQL injection |
| DAT.SEC.02 | No raw SQL to containers | Database file inaccessible from containers |

---

### GQ — Group Queue (`src/group-queue.ts`, 365 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **GQ.INV** | Invariants | |
| GQ.INV.01 | One container per group | Messages queued while container runs |
| GQ.INV.02 | Global concurrency cap | MAX_CONCURRENT_CONTAINERS (5) |
| GQ.INV.03 | Tasks before messages | Drain priority ordering |
| **GQ.PREEMPT** | Preemption | |
| GQ.PREEMPT.01 | Idle container preemption | _close sentinel on task arrival |
| **GQ.RETRY** | Retry logic | |
| GQ.RETRY.01 | Exponential backoff | Base 5s, doubling, max 5 retries |
| GQ.RETRY.02 | Drop semantics | After max retries, drops messages (retries on next incoming) |
| **GQ.SHUT** | Shutdown | |
| GQ.SHUT.01 | Detach semantics | Containers finish via idle timeout, not killed |
| **GQ.FOLLOW** | Follow-up delivery | |
| GQ.FOLLOW.01 | IPC file write | JSON to data/ipc/{groupFolder}/input/ for running containers |

---

### CHL — Channel System (`src/channels/`, ~981 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **CHL.REG** | Registry | Factory pattern, auto-registration |
| CHL.REG.01 | Null factory return | Credentials missing → skip gracefully |
| **CHL.IF** | Channel interface | connect, sendMessage, isConnected, ownsJid, disconnect |
| CHL.IF.01 | JID ownership | ownsJid routes to correct channel |
| CHL.IF.02 | Optional methods | setTyping, syncGroups — not all channels implement |
| **CHL.TG** | Telegram (571 LOC) | |
| CHL.TG.01 | Long-poll | Primary bot polling loop |
| CHL.TG.02 | Onboarding gate | State machine: first_contact → welcome_sent → active |
| CHL.TG.03 | Bot pool | Round-robin assignment, setMyName rename, 2s propagation wait |
| CHL.TG.04 | Message handler | @mention → @ASSISTANT_NAME translation |
| CHL.TG.05 | Markdown fallback | Try markdown parse, fall back to plain text |
| CHL.TG.06 | Message splitting | 4096 char Telegram limit |
| CHL.TG.07 | JID bootstrap | Empty ownedJids → claims all tg: JIDs |
| **CHL.GM** | Gmail (364 LOC) | |
| CHL.GM.01 | Short-poll | 60s interval, exponential backoff on error |
| CHL.GM.02 | Processed IDs | In-memory set capped at 5000 |
| CHL.GM.03 | Self-skip | Ignores own emails (loop prevention) |
| CHL.GM.04 | Thread metadata cache | For proper In-Reply-To/References headers |
| CHL.GM.05 | Main-only routing | All emails go to prime |

---

### SEC — Security (`~1,000 LOC across 4 files`)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **SEC.L1** | Layer 1: Container isolation | Docker namespaces |
| SEC.L1.01 | Mount validation before spawn | |
| **SEC.L2** | Layer 2: Credential proxy (236 LOC) | |
| SEC.L2.01 | API key mode | Strip placeholder, inject real key |
| SEC.L2.02 | OAuth mode | Intercept token exchange, replace placeholder |
| SEC.L2.03 | Telemetry tap | SSE stream parsed for usage logging |
| SEC.L2.04 | Key property | API keys never enter container address space |
| **SEC.L3** | Layer 3: Mount security (419 LOC) | |
| SEC.L3.01 | Allowlist | External file, outside project root |
| SEC.L3.02 | Path expansion | ~ → home, symlink resolution |
| SEC.L3.03 | Blocked patterns | .ssh, .gnupg, .aws, .kube, .docker, id_rsa |
| SEC.L3.04 | Allowed root check | Mount must fall under allowedRoots |
| SEC.L3.05 | RW enforcement | Non-main forced RO if nonMainReadOnly |
| **SEC.L4** | Layer 4: IPC authorization | isMain privilege boundary |
| SEC.L4.01 | Per-operation matrix | See IPC.TASK labels |
| **SEC.L5** | Layer 5: Sender allowlist (128 LOC) | |
| SEC.L5.01 | Per-chat control | allow: "*" or specific senders |
| SEC.L5.02 | Mode: trigger vs drop | |
| SEC.L5.03 | Fallback | Invalid config → allow-all (prevent lockout) |
| **SEC.RC** | Remote control (218 LOC) | |
| SEC.RC.01 | Detached process | claude remote-control |
| SEC.RC.02 | Crash recovery | Metadata in remote-control.json |

---

### SCHED — Task Scheduler (`src/task-scheduler.ts`, 282 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **SCHED.POLL** | Polling | 60s interval for due tasks |
| SCHED.POLL.01 | Re-check race | Task may have been paused/cancelled since query |
| **SCHED.RUN** | Task run | |
| SCHED.RUN.01 | Group folder resolution | Pauses task if invalid (stops retry churn) |
| SCHED.RUN.02 | Single-turn semantics | 10s close after task, not 30min idle |
| SCHED.RUN.03 | Run logging | task_run_logs table |
| **SCHED.DRIFT** | Drift prevention | |
| SCHED.DRIFT.01 | Anchor to scheduled time | next = scheduled + interval, not wall clock |

---

### FLT — Fleet & Personality (`templates/`, `halfleet/`, `groups/`)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **FLT.TOPO** | Fleet topology | Prime → microhals, asymmetric visibility |
| FLT.TOPO.01 | Isolation model | Prime sees all; microhals see nothing |
| FLT.TOPO.02 | Governance locking | chmod 444/555 on CLAUDE.md, .claude/, src/, container/, templates/ |
| **FLT.PERS** | Personality composition | base.md + profile YAML + user context + group identity |
| FLT.PERS.01 | base.md | ~290 LOC governance (verification loop, honesty, tools, boundaries) |
| FLT.PERS.02 | Profile YAML | 5 categories × N dimensions per user |
| FLT.PERS.03 | User context | Hand-written, irreducible human knowledge |
| FLT.PERS.04 | Group CLAUDE.md | Channel-specific identity + permissions |
| **FLT.ONBOARD** | Onboarding | |
| FLT.ONBOARD.01 | Bot-level flow | first_contact → welcome_sent → active (see CHL.TG.02) |
| FLT.ONBOARD.02 | Agent-level Likert | 5 questions, three-strike rule |
| FLT.ONBOARD.03 | Agent-level qualitative | 2 open-ended, after 3-7 conversations |
| FLT.ONBOARD.04 | Post-assessment | Operator-triggered mirror questions |
| **FLT.EVAL** | Evaluation systems | |
| FLT.EVAL.01 | Infrastructure smoke | 10-point checklist, pass/fail |
| FLT.EVAL.02 | Behavioral smoke | 2,287 LOC, 6 capability dimensions, >95% threshold |
| FLT.EVAL.03 | Eval harness | Single-injection + multi-turn dialogue scenarios |

---

### HALO — Halos Ecosystem (Python, 16,471 LOC)

| Label | Dimension | Scope |
|-------|-----------|-------|
| **HALO.HALCTL** | Fleet management (4,321 LOC) | create, freeze, fold, fry, assess, smoke, supervise, session |
| HALO.HALCTL.01 | Provisioning | Instance lifecycle with locked governance |
| HALO.HALCTL.02 | Supervisor | Phrase-matching behavioral triggers |
| HALO.HALCTL.03 | Health checks | Log activity + pm2 stats for zombie detection |
| HALO.HALCTL.04 | Session management | SQLite, logged via hlog |
| **HALO.NIGHT** | Work tracker (2,452 LOC) | tasks, jobs, agent-jobs with state machine |
| HALO.NIGHT.01 | Plan validation | XML or context-only gates |
| HALO.NIGHT.02 | Atomic writes | yaml.tmp + os.replace |
| HALO.NIGHT.03 | Dependency tracking | |
| **HALO.MEM** | Memory governance (1,167 LOC) | |
| HALO.MEM.01 | Decay function | Backlink count + age + confidence |
| HALO.MEM.02 | Index integrity | SHA256 drift detection |
| **HALO.BRIEF** | Briefings (818 LOC) | |
| HALO.BRIEF.01 | Synthesis cascade | claude CLI → SDK → raw fallback |
| HALO.BRIEF.02 | Delivery | IPC JSON file → Telegram |
| **HALO.LOG** | Log reader (831 LOC) | |
| HALO.LOG.01 | Structured parsing | JSON lines from hlog |
| HALO.LOG.02 | Cross-instance aggregation | Fleet view |
| **HALO.AGENT** | Session tracking (555 LOC) | |
| HALO.AGENT.01 | Spin detection | Thresholds, error streaks |
| **HALO.CRON** | Cron management (519 LOC) | |
| HALO.CRON.01 | YAML → crontab | Generated crontab from definitions |
| **HALO.REPORT** | Digest generator (801 LOC) | |
| HALO.REPORT.01 | Collectors | Imported by briefings |

---

### CFG — Configuration & Types

| Label | Dimension | Scope |
|-------|-----------|-------|
| **CFG.ENV** | Environment | config.ts (94 LOC), env.ts |
| CFG.ENV.01 | Secrets boundary | Secrets NOT in config.ts — credential-proxy only |
| CFG.ENV.02 | CONTAINER_PROXY_PORT vs CREDENTIAL_PROXY_PORT | Fleet routing distinction |
| **CFG.TYPE** | Core types (108 LOC) | |
| CFG.TYPE.01 | RegisteredGroup | isMain as authorization primitive |
| CFG.TYPE.02 | Channel interface | Multi-channel routing contract |
| CFG.TYPE.03 | ContainerConfig | Per-group mount configuration |
| **CFG.ROUTER** | Router (52 LOC) | |
| CFG.ROUTER.01 | formatMessages | XML wrapping for agent prompts |
| CFG.ROUTER.02 | routeOutbound | Channel lookup by JID |
| CFG.ROUTER.03 | stripInternalTags | Remove <internal> blocks before delivery |

---

## Axis 2: Error Class Tags (from testing-concrete.md)

Each tag identifies the **type of weakness** a finding exhibits. Applied as suffix: `[TC##]`.

### Primary Error Classes

| Tag | Name | One-line test |
|-----|------|---------------|
| **TC01** | Response-Level Verification | Does the test check the artifact, or just what the system *said*? |
| **TC02** | Knowledge vs Compliance | Does it test protocol *execution*, or just protocol *knowledge*? |
| **TC03** | Context Leakage as Persistence | Does it prove durable storage, or same-session recall? |
| **TC04** | Negative-Only Assertions | Does it assert presence of required behavior, not just absence of bad? |
| **TC05** | Boundary Hallucination | Does it verify enforcement by checking the protected artifact, not refusal language? |
| **TC06** | Fixture Contamination | Is the test self-contained, or does it depend on prior test state? |
| **TC07** | Cleanup Theater | Does mutation rely on best-effort cleanup, or isolated fixtures? |
| **TC08** | Cosmetic Completeness | Is the assertion layer strong, or hidden behind polished scaffolding? |

### Advanced Error Classes

| Tag | Name | One-line test |
|-----|------|---------------|
| **TC09** | Correlation Failure | Can you prove the observed response belongs to *this* stimulus? |
| **TC10** | Capability Adjacency | Does it prove the named capability, or a nearby one? |
| **TC11** | State-Machine Underconstraint | Does it verify transition *sequence*, or only terminal state? |
| **TC12** | Context-Boundary Ambiguity | Does it cross the boundary it claims (sender / thread / session / process)? |
| **TC13** | Gate Design Failure | Can critical scenario failures hide in an overall pass rate? |
| **TC14** | Progressive Narrowing | After first fixes, do narrower escape hatches remain? |

---

## Axis 3: Severity (applied during review, not pre-assigned)

| Severity | Label | Meaning |
|----------|-------|---------|
| **S1** | Critical | Incorrect behavior in production; data loss, security breach, or silent corruption |
| **S2** | High | Likely failure under real conditions; race, timeout, or auth bypass |
| **S3** | Medium | Latent issue; triggers under edge conditions or accumulation |
| **S4** | Low | Code quality, clarity, maintainability; no behavioral impact |

---

## Composite Label Format

```
{DOMAIN}.{DIMENSION}.{##} [TC##] S{1-4}
```

**Example findings:**

| Label | Description |
|-------|-------------|
| `ORK.CUR.03 [TC11] S2` | Orchestrator cursor race window — state-machine underconstraint, high severity |
| `CTR.PARSE.02 [TC09] S3` | Container output buffer unbounded — correlation failure risk under load, medium |
| `SEC.L3.02 [TC05] S2` | Mount validation symlink resolution — does enforcement survive TOCTOU? High |
| `IPC.TASK.02 [TC05] S1` | Task mutation auth — verify enforcement by checking artifact, not refusal text |
| `CHL.TG.02 [TC11] S3` | Onboarding state machine — does test verify full transition sequence? |
| `FLT.EVAL.02 [TC13] S2` | Behavioral smoke suite — can a critical scenario failure hide in 95% pass rate? |
| `DAT.MIG.02 [TC03] S3` | Migration idempotence — no version tracking conflates never-migrated with already-migrated |
| `AGR.SPIN.01 [TC10] S2` | Rate-limit spin detection — proves "too many messages" but not "poisoned context" specifically |
| `GQ.INV.02 [TC04] S4` | Concurrency cap — test checks cap not exceeded, but does it verify queued groups DO eventually run? |
| `MCP.GAP.02 [TC01] S3` | Fire-and-forget IPC — tool returns "requested" but no delivery verification |

---

## Review Itinerary

Ordered by structural risk (churn × centrality × security surface):

### Phase 1: Critical Path (ORK + CTR + AGR)
Priority: highest churn, everything depends on these.

1. **ORK.CUR** — Cursor management with rollback (3 items)
2. **ORK.MSG** — Message processing flow (3 items)
3. **ORK.IDLE** — Idle timeout logic (2 items)
4. **CTR.PARSE** — Sentinel output parsing (4 items)
5. **CTR.MNT** — Mount construction (5 items)
6. **CTR.TIMEOUT** — Timeout & reaping (3 items)
7. **CTR.CHAIN** — Output chain promise choreography (2 items)
8. **AGR.LOOP** — Query loop (3 items)
9. **AGR.SPIN** — Spin detection (3 items)

### Phase 2: Security Surface (SEC + IPC.AUTH + MCP.AUTH)
Priority: defense-in-depth — each layer reviewed independently.

10. **SEC.L2** — Credential proxy (4 items)
11. **SEC.L3** — Mount security (5 items)
12. **SEC.L4** — IPC authorization (1 item, cross-ref IPC.TASK)
13. **SEC.L5** — Sender allowlist (3 items)
14. **IPC.MSG.01** — Message routing authorization
15. **IPC.TASK.01–04** — Task namespace authorization
16. **MCP.AUTH** — Container-side authorization (2 items)

### Phase 3: Data Integrity (DAT + SCHED + GQ)
Priority: persistence, state machines, concurrency invariants.

17. **DAT.QUERY** — Query patterns including subquery reversal (3 items)
18. **DAT.MIG** — Migration safety (3 items)
19. **DAT.SEC** — SQL injection surface (2 items)
20. **SCHED.DRIFT** — Drift prevention (1 item)
21. **SCHED.RUN** — Task run lifecycle (3 items)
22. **GQ.INV** — Queue invariants (3 items)
23. **GQ.RETRY** — Retry and drop semantics (2 items)

### Phase 4: Channel Surface (CHL)
Priority: user-facing, external API interaction.

24. **CHL.TG** — Telegram (7 items)
25. **CHL.GM** — Gmail (5 items)
26. **CHL.REG** — Registry (1 item)

### Phase 5: Fleet & Personality (FLT)
Priority: domain-specific, lower change frequency.

27. **FLT.TOPO** — Fleet topology and isolation (2 items)
28. **FLT.ONBOARD** — Onboarding state machines (4 items)
29. **FLT.EVAL** — Evaluation systems (3 items)
30. **FLT.PERS** — Personality composition (4 items)

### Phase 6: Halos Ecosystem (HALO)
Priority: largest codebase, most independent.

31. **HALO.HALCTL** — Fleet management (4 items)
32. **HALO.NIGHT** — Work tracker (3 items)
33. **HALO.BRIEF** — Briefings (2 items)
34. **HALO.MEM** — Memory governance (2 items)
35. **HALO.LOG + HALO.AGENT + HALO.CRON + HALO.REPORT** — Supporting modules (5 items)

---

## Audit Heuristics (per finding)

Apply these from testing-concrete.md when evaluating each label:

1. What concrete artifact or state transition does this assertion inspect?
2. Can the system say the right thing while the behavior is still broken?
3. Is the validator checking semantics, or only existence?
4. Does the test prove persistence, or only same-session recall?
5. Does the test cross the boundary it claims to cross?
6. Can the harness prove the observed response belongs to this exact stimulus?
7. Is the test proving the named capability, or only an adjacent one?
8. For workflows, does it verify the sequence, or only a plausible end state?
9. Does the test verify enforcement, or only refusal language?
10. Could this pass with empty output, plain text, or a no-op?
11. Could prior test residue make this pass?
12. Could the suite still pass if a critical scenario is broken?

---

## Metrics for Before/After Comparison

After both review passes, compare:

| Metric | Before | After |
|--------|--------|-------|
| Total findings | | |
| S1 (Critical) count | | |
| S2 (High) count | | |
| Per-domain finding density | | |
| TC tag distribution | | |
| Findings resolved | | |
| New findings introduced | | |
| Net severity change | | |
