# halos Capability Map

Analysis of current modules, infrastructure overlap, candidate modules, and design boundaries.

## 1. What Exists Now

### memctl — Structured memory governance
**Status: Production. The most mature module.**

Fully implemented: `new`, `get`, `search`, `index rebuild`, `index verify`, `link`, `prune`, `stats`, `enrich`. 59 notes, 18 backlinks, 12 entities, 5 semantic clusters. The enrichment rubric (five-dimension scoring with human approval loop) is genuinely novel and working.

Gaps:
- `export` is in the spec but not yet implemented in `halos/memctl/cli.py`
- The spec says Go binary but the implementation is Python. This is fine — the spec predates the consolidation into the `halos` Python package. The spec is now historical, the Python implementation is canonical.
- No `unlink` command yet (spec mentions it in the architecture overview as surgical intervention, but no CLI command exists)

### nightctl — Overnight batch processing
**Status: Production. Well-specified, complete implementation.**

Fully implemented: `enqueue`, `list`, `status`, `run`, `cancel`, `manifest rebuild`, `manifest verify`, `archive`, `hatch`, `stats`. Notification on failure via halos messaging layer. Serial/parallel execution modes. Dependency resolution between jobs.

Gaps:
- `hatch` (permanent deletion) exists but requires double safety (--execute AND config flag). This is correct, not a gap.
- No test coverage visible in the halos/ tree. True for all modules.

### cronctl — Cron job definitions
**Status: Production. Lean and complete for its scope.**

Implemented: `add`, `list`, `enable`, `disable`, `install`, `uninstall`, `status`, `run`. Generates crontab from YAML job files, supports user-crontab or file-only install methods.

Gaps:
- No archive/history. Jobs are just YAML files that get enabled/disabled. This is probably fine for cron definitions — they're configuration, not events. Adding archive-not-delete here would be over-engineering.
- No `--dry-run` on `add` (it writes immediately). Minor.
- The cron schedule regex is more restrictive than real crontab (no named days, no ranges with steps like `1-5/2`). This will bite eventually.

### todoctl — Backlog tracking
**Status: Production. Functional but the thinnest module.**

Implemented: `add`, `list`, `done`, `defer`, `block`, `start`, `stats`, `graph`. The `graph` command (ASCII tree by priority) is a nice touch for the agent's context window.

Gaps:
- No archive. Done items stay in the items directory forever. This violates the shared design principle of archive-not-delete. Should archive completed items after a retention period.
- No `edit` or `update` command. If a title or priority needs changing, there's no CLI path — you'd have to edit the YAML directly, which violates "CLI-driven writes, never direct file edits."
- No `delete`/`cancel` status. Items can only be done or deferred, never abandoned.
- No entities field. memctl and nightctl have entities; todoctl items don't. This means you can't cross-reference backlog items with memory notes by entity.
- No hash/manifest. Unlike memctl and nightctl, there's no derived index to verify. Probably fine at current scale.

### Cross-module assessment

The four modules share a clean design language. The Python `halos` package with `uv sync` console_scripts is the right call — one install, four commands. The shared dependency on pyyaml and nothing else is admirable.

What's missing across all of them: **tests**. There are no test files in `halos/`. For CLIs that enforce schema validation, pruning thresholds, and hash verification, this is a liability. The "defensive coding mandate" standing order (SD in memory) explicitly states LLMs are probabilistic and unhappy paths are inevitable. The modules should practice what they preach.

## 2. What NanoClaw Already Provides

halos modules do not operate in a vacuum. NanoClaw's infrastructure handles several things that a naive module design would try to rebuild:

### Messaging (src/router.ts, src/channels/)
Multi-channel outbound messaging. WhatsApp, Telegram, Slack, Discord, Gmail. nightctl already uses this for failure notifications via the halos messaging layer. Any new module that needs to notify the operator can use the same path.

### Scheduling (src/task-scheduler.ts, src/db.ts)
NanoClaw has a full task scheduler with cron expressions, interval-based scheduling, and one-shot tasks. Tasks run in containers with group isolation. This is the *runtime* scheduler. cronctl is the *definition* layer (YAML files that generate crontab). nightctl is the *batch* layer (deferred jobs with dependency chains). These three layers are complementary, not overlapping:
- NanoClaw scheduler: "run this prompt in this container at this time"
- cronctl: "these system commands should run on this cron schedule"
- nightctl: "these jobs are queued for the overnight window"

### IPC (src/ipc.ts)
File-based IPC with per-group namespaces. Containers write JSON files to `data/ipc/{group}/messages/` or `data/ipc/{group}/tasks/`. The host process polls and dispatches. Authorization model: main group can send anywhere; non-main groups can only send to themselves. Any new module that needs container-to-host communication should use this existing IPC mechanism rather than inventing its own.

### Container isolation (src/container-runner.ts)
Containers get volume mounts (read-only project root for main, read-write group folder), credential proxy access, and IPC directories. The halos tools are installed inside the container via `uv sync`. Modules run inside the container as CLI commands the agent invokes.

### SQLite (src/db.ts)
NanoClaw uses SQLite for task state, run logs, and group metadata. halos modules deliberately avoid this — they're filesystem-first. This is a design choice, not an oversight. The filesystem approach means the agent's tools are auditable with `cat` and `ls`, diffable with git, and don't require a database client to inspect. But it means halos modules cannot leverage NanoClaw's existing task/run tables. This is the correct tradeoff.

### What this means for new modules

A new halos module gets for free:
- Outbound messaging to any channel (via IPC message files)
- Scheduled execution (via NanoClaw tasks or cronctl definitions)
- Container sandboxing with filesystem isolation
- The `halos` Python package structure and `uv sync` installation

A new halos module must provide:
- Its own YAML file format and schema validation
- Its own CLI with the standard flags (--json, --dry-run, --verbose, --config)
- Its own config file at repo root ({module}.yaml)
- A `console_scripts` entry in pyproject.toml

## 3. Candidate Modules

### Tier 1: Immediate (fills a gap the existing modules expose)

#### testctl
**One-line:** Test runner and gate for halos modules.

**Why:** The defensive coding mandate is a standing order. There are no tests. Every module does schema validation, hash computation, file I/O, and pruning logic that should be tested. The modules enforce discipline on the agent but have no enforcement on themselves.

**What it looks like:**
```
testctl run                    # run all module tests
testctl run --module memctl    # run tests for one module
testctl gate                   # lint + typecheck + test (the local gate)
testctl coverage               # show coverage by module
```

File format: Not YAML files — this is a runner, not a data store. A `testctl.yaml` config pointing to test directories per module. Tests themselves are pytest files in `halos/{module}/tests/`.

**Priority: Immediate.** This is infrastructure debt. The halos principles document says "every meaningful change must pass through a local gate." halos itself has no gate.

**Dependencies:** None. It tests existing modules.

**Counterargument:** This might not be a halos module at all. It might just be `pytest` with a `Makefile` target. Don't over-engineer a test runner into a YAML-schema CLI. The right move is probably: add `halos/{module}/tests/` directories, add a `make gate` target, and move on. If it needs more than that, revisit.

---

#### logctl
**One-line:** Structured log viewer and query interface for halos operations.

**Why:** nightctl writes run records. cronctl runs commands. memctl does pruning. All of these produce output that currently goes to stdout or individual log files. There's no unified way to ask "what happened overnight?" or "show me all failed operations this week."

**What it looks like:**
```
logctl query --since yesterday --status failed
logctl query --module nightctl --tags maintenance
logctl tail                    # live tail of all halos operations
logctl summary --period 7d     # weekly digest
```

Storage: `logs/halos/` directory with one YAML file per operation (following the atomic file pattern). Each module writes a log entry via a shared `halos.log` library function.

**Priority: Soon.** Not blocking anything today, but as halos grows, the operational visibility gap will compound. The overnight run produces useful data that currently requires reading individual nightctl run records.

**Dependencies:** All modules would need to emit structured log entries. This means a shared logging convention, not just logctl reading existing files.

---

### Tier 2: Soon (clear use case, not urgent)

#### vaultctl
**One-line:** Secret reference management — pointers to secrets, never the secrets themselves.

**Why:** NanoClaw has a credential proxy that injects secrets into containers. But there's no halos-layer tracking of *which* secrets exist, *which* modules need them, *when* they were last rotated, or *when* they expire. The agent can't answer "which API keys are about to expire?" because that information isn't in the knowledge graph.

**What it looks like:**
```
vaultctl add --name anthropic-api --provider anthropic --expires 2026-06-01 --tags api,llm
vaultctl list
vaultctl expiring --within 30d
vaultctl rotate --name anthropic-api   # triggers rotation workflow, does NOT handle the secret itself
```

Storage: `vault/` directory with YAML files. Each file contains metadata about a secret (name, provider, tags, expiry, last rotated) but NEVER the secret value. The actual secrets stay in the credential proxy / environment variables / wherever they already live.

**Priority: Soon.** Kai has API keys, OAuth tokens, and service credentials scattered across NanoClaw channels. Tracking rotation and expiry is the kind of thing that bites you at 2am.

**Dependencies:** None, but should integrate with memctl (expiring secrets could generate memory notes) and nightctl (rotation checks as overnight jobs).

---

#### reportctl
**One-line:** Periodic digest generation from halos module state.

**Why:** The memory graph has patterns. The backlog has priorities. The overnight queue has results. A daily or weekly digest that synthesizes these into a "state of the system" report would be genuinely useful. Currently the agent has to be asked to do this manually each time.

**What it looks like:**
```
reportctl generate --period daily       # generates a report from all module state
reportctl generate --period weekly
reportctl templates list                # available report templates
reportctl templates add --name standup --modules memctl,todoctl,nightctl
```

Storage: `reports/` directory. Templates in `reports/templates/`. Generated reports as markdown files.

**Priority: Soon.** The pieces exist (memctl stats, todoctl graph, nightctl stats). reportctl would compose them into a coherent narrative. The overnight window is the natural execution time.

**Dependencies:** All existing modules (reads their state). nightctl (scheduled generation).

---

### Tier 3: Eventually (real need, not yet acute)

#### watchctl
**One-line:** File and URL change monitoring with configurable alerting.

**Why:** Kai tracks multiple projects, job postings, and external resources. "Tell me when this page changes" or "alert me when this file is modified" is a recurring need that currently requires manual cron jobs or ad-hoc scripts.

**What it looks like:**
```
watchctl add --url https://example.com/jobs --interval 6h --tags job-search
watchctl add --file /path/to/config.yaml --on-change "nightctl enqueue --title 'Config changed'"
watchctl list
watchctl check --all              # run all watches now
watchctl history --name example-jobs
```

Storage: `watches/` directory. Each watch is a YAML file. Check results stored as timestamped YAML files in `watches/results/`.

**Priority: Eventually.** Useful but not critical. Could be approximated with cronctl + a shell script for now.

**Dependencies:** cronctl (scheduling), nightctl (deferred actions on change), messaging (alerts).

---

#### syncctl
**One-line:** Bidirectional sync definitions between local state and external services.

**Why:** Kai's workflow spans NanoClaw (messaging), GitHub (code), job boards (applications), and various web services. Keeping state synchronized between these is manual and error-prone. syncctl would define sync pairs and run them on schedule.

**What it looks like:**
```
syncctl add --name github-issues --source github:qwibitai/thepit --target todoctl --interval 1h
syncctl run --name github-issues
syncctl list
syncctl status --name github-issues
```

**Priority: Eventually.** The integration surface is large and each sync pair needs custom logic. This is probably better as individual nightctl jobs until patterns emerge.

**Dependencies:** nightctl (execution), todoctl (sync target), external service APIs.

---

### Tier 4: Speculative (interesting but may never be needed)

#### agentctl
**One-line:** Agent session metadata and performance tracking.

**Why:** Each container invocation is an agent session. How long did it take? How many tokens did it use? What was the outcome? NanoClaw logs some of this but not in a halos-accessible way.

**What it looks like:** Session records as YAML files. Query by group, date, outcome. Token usage tracking over time.

**Priority: Speculative.** NanoClaw's SQLite already tracks task runs. Duplicating this in the filesystem would violate the "don't rebuild what NanoClaw provides" principle. Only makes sense if there's agent-side metadata (self-assessment, difficulty rating, tool usage patterns) that doesn't belong in the host's SQLite.

**Dependencies:** Would need container-side instrumentation to write session metadata.

---

#### rulectl
**One-line:** Standing order and governance rule management.

**Why:** The memory graph contains 7+ standing orders (SD-134, SD-266, SD-315, SD-319, SD-325, SD-268, SD-327). These are currently stored as memctl notes with type=decision and tag=standing-order. They work, but they're mixed in with regular decisions. A dedicated module could enforce rule precedence, track amendments (SD-319 has one), and provide quick lookup.

**What it looks like:**
```
rulectl list                           # all active standing orders
rulectl get SD-319                     # full text + amendments
rulectl amend SD-319 --text "..."      # create amendment record
rulectl check --text "output"          # check text against active rules
```

**Priority: Speculative.** The current approach (memctl notes with a tag filter) works. Standing orders are immutable decisions — memctl handles immutable decisions. A separate module adds complexity without clear benefit until the rule corpus grows past ~20 items.

**Dependencies:** memctl (current storage), would need migration path.

---

#### flowctl
**One-line:** Multi-step workflow definitions and execution tracking.

**Why:** Some operations are multi-step: "pull PR comments, fix issues, push, wait for CI, report back." Currently these are ad-hoc agent instructions. flowctl would define reusable workflow templates.

**What it looks like:** YAML workflow definitions with steps, conditions, and rollback. Execution tracking in `flows/runs/`.

**Priority: Speculative.** This is a workflow engine. Workflow engines are where good intentions go to die. nightctl's dependency chains handle sequential execution. Anything more complex should be a script, not a YAML DSL.

## 4. Anti-patterns to Avoid

### The database-in-YAML trap
Every new module adds YAML files. At some point, someone will want to query across modules: "show me all memory notes linked to backlog items tagged 'architecture'." The temptation will be to build a cross-module query layer, which is a database with extra steps. Resist this. Each module has its own query commands. Cross-module queries are agent reasoning tasks, not infrastructure.

### The notification framework
nightctl already sends failure notifications. reportctl would send digests. watchctl would send alerts. The temptation will be to build a unified notification framework with routing rules, throttling, and channel preferences. This is a premature abstraction. Each module should write an IPC message file when it needs to notify. The format is already defined. Adding a framework between the module and the IPC directory adds a layer that helps nobody.

### configctl — a meta-config manager
"What if there was one module to manage all the other modules' configs?" No. Each module has a `{module}.yaml` at repo root. They're human-readable. `cat cronctl.yaml` is faster than `configctl get cronctl`. Meta-configuration is governance recursion — the exact vulnerability Kai already identified in memory.

### statusctl — a unified dashboard
"What if one command showed the status of all modules?" This sounds useful until you realize it's just calling `memctl stats && nightctl stats && cronctl status && todoctl stats`. A shell alias does this. A module that wraps four other modules' stats commands is not a module, it's a script.

### migrctl — schema migration tooling
The YAML schemas will evolve. The temptation will be to build migration tooling. But the schemas are simple flat YAML. A migration is a `for f in *.yaml; do ...` loop. If you need Alembic for YAML files, your YAML files are too complex.

### Any module that requires a running daemon
halos modules are CLIs. They run, do their thing, exit. nightctl's executor is the closest thing to a daemon and it's invoked by cron, not self-hosting. If a module needs to run continuously, it belongs in NanoClaw's Node.js process, not halos.

## 5. The Naming Question: "halos"

### Arguments for
- **Identity.** HAL is already the personality name in CLAUDE.md. halos as the operating layer for HAL is a natural extension. It gives the tooling suite a name that isn't just "those Python scripts."
- **Scope boundary.** "halos module" immediately communicates "filesystem-first CLI tool following the shared conventions." It's a membership test, not just a label.
- **Cohesion.** Four modules with a shared name feel like a system. Four modules without a name feel like a junk drawer.
- **It already stuck.** The docs, the memory notes, the standing orders — they all reference halos. Renaming would be churn for no gain.

### Arguments against
- **Grandiosity.** Calling four Python CLIs an "operating system" is semantic inflation. It's a toolkit. Kai's own memory notes flag governance recursion and the gap between papers-about-systems and working-systems. halos risks being the former.
- **Scope creep magnet.** An "OS" invites people to think "what else does an OS need?" Networking? Process management? A filesystem abstraction? The name creates expectations the project shouldn't fulfill.
- **Confusion with NanoClaw.** NanoClaw is the actual runtime. halos is the tooling layer. But "OS" implies halos is the runtime, which it's not.

### Alternatives
- **hal-tools** — Accurate but generic. Doesn't convey the design discipline.
- **halkit** — Short, implies toolkit. Less pretentious than OS. Loses the identity.
- **halos** (reframed) — Keep the name but define "OS" as "Operational Scripts" or "Operational Surface" rather than "Operating System." This preserves the name while deflating the grandiosity.

### Verdict
Keep halos. The name works. The grandiosity concern is real but manageable — the standing orders and memory notes already demonstrate that Kai is aware of governance recursion and actively guards against it. The name will stick because it already has. If it starts attracting scope creep, the design principles (filesystem-first, no daemons, no databases, archive-not-delete) are the guardrails, not the name.

## Summary Table

| Module | Purpose | Priority | Exists |
|--------|---------|----------|--------|
| memctl | Structured memory governance | - | Yes |
| nightctl | Overnight batch processing | - | Yes |
| cronctl | Cron job definitions | - | Yes |
| todoctl | Backlog tracking | - | Yes |
| testctl* | Module test gate | Immediate | No |
| logctl | Structured operation logs | Soon | No |
| vaultctl | Secret reference tracking | Soon | No |
| reportctl | Periodic digest generation | Soon | No |
| watchctl | File/URL change monitoring | Eventually | No |
| syncctl | External service sync | Eventually | No |
| agentctl | Session metadata tracking | Speculative | No |
| rulectl | Standing order management | Speculative | No |
| flowctl | Multi-step workflows | Speculative | No |

\* testctl may be better as a `make gate` target than a halos module. See analysis above.

---

Generated: 2026-03-16. This is a point-in-time analysis, not a roadmap.
