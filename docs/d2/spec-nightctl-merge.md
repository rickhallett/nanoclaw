# nightctl Unified Work Tracker — Specification

> "Your best work happens while you sleep."

## Goal

Merge todoctl into nightctl to create a single halos module that tracks all units of work — from vague ideas through planned agent tasks to executed batch jobs — with a validated state machine, execution engine, and audit trail. One system, many schedules.

## Status

**Phase 4: Spec confirmed.** Interview complete 2026-03-17. Ready for implementation planning.

## Scope

### In scope
- Unified item schema covering human tasks, machine jobs, and agent tasks
- Validated state machine (transition enforcement, not just status validation)
- Atomic writes (tmp + os.replace)
- Execution engine: subprocess for jobs, container-runner for agent-jobs
- Dependency resolution between items
- Run records (per-attempt audit trail)
- Manifest with hash verification
- Graph visualisation (ASCII, by priority)
- Archive with configurable delayed garbage collection (30-day wake)
- `kind` field: `task`, `job`, `agent-job`
- Agent-jobs require structured XML plan with mandatory constraints
- Planning workflow with human review gate in state machine
- CLI help reflects philosophy: "your best work happens while you sleep"
- Migration of existing todoctl backlog items into nightctl schema

### Out of scope
- lightctl or any daytime-specific tooling (schedule field handles this)
- UI/dashboard integration
- Plan quality scoring (structural validation only)

## Philosophy

Daylight is for planning, review, triage and queue. Night is for execution.

The `kind` field enables triage and delegation:
- **task**: Human work. May or may not happen. Faithfully recorded because someone barked about it once. No command, no execution. God may or may not know the plan.
- **job**: Machine work. Repeatable pipeline steps, prep work, trustworthy processes that consume CPU/API/bandwidth and shouldn't compete with the main thread. Executed via subprocess.
- **agent-job**: Agent work. Only gets scheduled with a sufficiently detailed plan — inline context or a referenced spec file. Planning is where the human stays in the loop to prevent deskilling, learn by doing, feel their hand at the tiller. This is not prompt territory; it's architectural.

### On planning and deskilling

There is active cogitation with an LLM; there is collaboration theatre. The default is active — the human co-authors the plan through `/spec` or `/decompose`, making real decisions about scope, approach, and constraints. But operational reality requires flexibility: brainfarts must be ingressed as they come in, and the ceremony of speccing occurs as the creature evolves from micro wind disturbance to fully formed wind tunnel.

The planning track in the state machine (open → planning → plan-review → in-progress) is the structural embodiment of this principle. The human review gate at plan-review is not optional for agent-jobs. The plan can come from file edit or agent↔human discussion leading to file edit; either way, the XML must pass validation before the dudes on passport control relax.

### On promotion as declaration

Entry is cheap. Promoting an item is declaring it matters — a downpayment in recognition that what matters will take effort. As the cost of production approaches zero, what matters most is knowing what to build and when. By necessity this excludes 99% of ideas. The discipline to stay the course on what actually matters in a given scenario is a perennial question, borderline koan, representing both the catchment area for opportunity and the most holes for energy leakage.

The promotion gate exists to prevent a specific failure mode: obsessive levels of human-agent interaction and output with nothing to show for it. A creative sycophantic loop that spins into the void. This system helps prevent that by requiring a formed plan as the price of execution — not to slow things down, but to ensure that what runs overnight is worth the electricity.

### On validation layering

XML plans are validated twice (swiss cheese model):
1. **Gate time** (plan-review → in-progress): structural validation before the human approves
2. **Runtime** (before passing to container): re-validation in case the file changed between approval and execution

Two independent checks. If the referenced file was modified after approval, the runtime check catches it.

## Architecture

### Item Schema (merged)

```yaml
# Identity
id: "20260317-082412-a1b2c3d4"    # timestamp-uuid (nightctl style)
title: "Short factual title"
kind: task | job | agent-job        # determines execution path

# Lifecycle
status: open                        # validated state machine
priority: 3                         # 1=critical, 2=high, 3=medium, 4=low
tags: [halos, architecture]
entities: [nightctl, todoctl]

# Human fields
context: "Why this exists"
due: "2026-04-01"                   # nullable
blocked_by: "reason or item ID"     # nullable

# Machine fields (nullable for tasks)
command: "uv run reportctl briefing"
schedule: overnight | immediate | once | null
window: "02:00-05:00"              # override, nullable
depends_on: [item-id-1, item-id-2]
retries: 2
timeout_secs: 300

# Agent fields (nullable for non-agent items)
plan: |                             # inline XML plan, or...
  <plan>...</plan>
plan_ref: "docs/d2/spec-foo.md"     # ...reference to spec file containing plan

# Metadata
created: "2026-03-17T08:24:12Z"
modified: "2026-03-17T08:24:12Z"
created_by: agent | human
```

### Plan Schema (XML)

Plans use XML for format separation from YAML (data vs instructions).

```xml
<plan>
  <goal>One sentence. What does success look like.</goal>

  <context>
    What the agent needs to know before starting.
    References to files, specs, prior decisions.
    Not the kitchen sink — just what's load-bearing.
  </context>

  <steps>
    <step n="1" output="memory/notes/research-*.md">
      Research competing tools using web search.
      Write findings as memctl notes.
    </step>
    <step n="2" depends="1" output="docs/d2/analysis-*.md">
      Synthesise research into a comparative analysis.
    </step>
    <step n="3" depends="2" output="stdout">
      Summarise key findings for human review.
    </step>
  </steps>

  <constraints>
    <constraint>Do not commit to git without explicit instruction</constraint>
    <constraint>Do not modify existing halos module code</constraint>
    <constraint>Stay within the docs/d2/ directory for new files</constraint>
  </constraints>

  <success>
    <criterion>At least 3 competitor tools analysed</criterion>
    <criterion>Analysis doc written to docs/d2/</criterion>
    <criterion>Summary printed to stdout</criterion>
  </success>

  <output>
    Where the final artifact lands. File path, stdout, or IPC target.
  </output>
</plan>
```

**Validation rules** (enforced at `nightctl add --kind agent-job` and at plan-review → in-progress transition):

1. Must parse as valid XML
2. `<goal>` required, non-empty
3. `<steps>` required, at least one `<step>` with `n` attribute
4. Each `<step>` must have an `output` attribute (forces definition of "done" per stage)
5. `<constraints>` required, at least one `<constraint>` (forces the author to think about boundaries)
6. `<success>` required, at least one `<criterion>`

**Not validated:** prose quality, step dependency validity, output path existence.

### State Machine

```
                         ┌───────────────────────────┐
                         │           open             │
                         └─────┬──────┬─────────┬─────┘
                               │      │         │
                               ▼      ▼         ▼
                         deferred  planning   cancelled
                          ▲  │        │
                          │  │        ▼
                          └──┘   plan-review ◄──────────┐
                                    │                   │
                              human approves             │
                                    │                   │
                                    ▼                   │
                              in-progress               │
                               │       │                │
                    ┌──────────┤       ├──────────┐     │
                    ▼          ▼       ▼          ▼     │
                blocked     review  running   cancelled │
                 ▲  │         │       │  │              │
                 │  │         ▼       │  │              │
                 │  └──►  testing     │  └──► failed ───┘
                 │          │         │
                 └──────────┤         │
                            ▼         ▼
                           done      done
```

**Transitions (complete):**

| From | To | Trigger | Notes |
|------|-----|---------|-------|
| open | planning | Start authoring a plan | agent-jobs must pass through here |
| open | in-progress | Human starts work | tasks and jobs can skip planning |
| open | deferred | Explicitly deferred | |
| open | cancelled | Abandoned | |
| planning | plan-review | Plan drafted, ready for review | |
| planning | cancelled | Abandoned during planning | |
| plan-review | in-progress | Human approves (XML validation must pass) | **passport control gate** |
| plan-review | planning | Plan rejected, needs rework | |
| plan-review | cancelled | Abandoned | |
| in-progress | review | Human submits for review | human path |
| in-progress | running | Executor starts command | machine/agent path |
| in-progress | blocked | External dependency | |
| in-progress | cancelled | Abandoned | |
| running | done | Exit 0 | |
| running | failed | Exit non-zero, retries exhausted | |
| failed | plan-review | Plan needs revision | **recovery path (agent-jobs)** |
| failed | in-progress | Retry with fix | **recovery path (jobs)** |
| review | in-progress | Rework needed | |
| review | testing | Approved, needs verification | |
| review | done | Approved, complete | |
| testing | in-progress | Test failed | |
| testing | done | Tests pass | |
| blocked | in-progress | Blocker resolved | |
| blocked | cancelled | Abandoned | |
| deferred | open | Revisited | |
| deferred | cancelled | Abandoned | |

**Terminal states:** done, cancelled

**Non-terminal failure:** `failed` is a holding state, not terminal. For jobs, the operator fixes the command and pushes to in-progress. For agent-jobs, it bounces to plan-review because the plan is the thing that needs fixing.

**Track topology:**
- **Planning track**: open → planning → plan-review → in-progress (agent-jobs)
- **Direct track**: open → in-progress (tasks and jobs)
- **Execution track**: in-progress → running → done/failed (machine/agent path)
- **Review track**: in-progress → review → testing → done (human path)

The `kind` field determines which tracks an item traverses, but the state machine is unified.

### Execution Flow

```
nightctl run [--force] [--limit N] [--dry-run]
  │
  ├─ Check window (skip if outside, unless --force)
  ├─ Load items where status=in-progress AND kind ∈ {job, agent-job}
  ├─ Sort by priority, created
  ├─ For each:
  │   ├─ Check depends_on satisfied
  │   ├─ Transition: in-progress → running
  │   ├─ For job: subprocess.run(command)
  │   ├─ For agent-job: delegate to container-runner with plan
  │   ├─ Write run record
  │   └─ Transition: running → done | failed
  └─ Notify on failure
```

**Agent-job execution:** nightctl delegates to container-runner, passing the validated XML plan. The container agent receives the plan as its instruction set. Run records capture the container's stdout/stderr and exit code.

### Garbage Collection

Cancelled and done items remain in the items directory for N days (configurable, default 30). This leaves a "wake" of decisions visible in the recent record. `nightctl archive --execute` sweeps items past the retention period to the archive directory. `nightctl hatch --execute` permanently ejects from archive.

Three-tier lifecycle: **active** (items/) → **archived** (archive/) → **ejected** (deleted)

### File Structure

```
nightctl.yaml              # config (single file, merged)
queue/
  items/                   # all active work items (was: jobs/ + backlog/items/)
  archive/                 # swept items
  runs/                    # execution records
  MANIFEST.yaml            # hash-verified index
```

### Integration Points

- **cronctl**: Schedules `nightctl run` via crontab
- **logctl**: nightctl logs via hlog (already does)
- **reportctl**: Reads nightctl stats for briefings
- **memctl**: Agent-jobs may write results to memory
- **container-runner**: Agent-job execution delegates to container with XML plan

## Behaviour

### Adding items

```bash
# Human task
nightctl add --title "Write up memctl" --kind task --priority 3

# Machine job
nightctl add --title "Generate weekly report" --kind job \
  --command "uv run reportctl weekly" --schedule overnight

# Agent job with inline plan
nightctl add --title "Research competitor tools" --kind agent-job \
  --plan '<plan><goal>...</goal>...</plan>' --schedule overnight

# Agent job with plan reference
nightctl add --title "Research competitor tools" --kind agent-job \
  --plan-ref docs/d2/spec-research.md --schedule overnight

# Agent job without plan → ERROR
nightctl add --title "Do something vague" --kind agent-job
# ERROR: agent-job requires --plan or --plan-ref

# Agent job with invalid XML plan → ERROR
nightctl add --title "Bad plan" --kind agent-job --plan '<plan><goal>hi</goal></plan>'
# ERROR: plan validation failed: <constraints> required with at least one <constraint>
```

### Planning workflow

```bash
# 1. Capture brainfart as open item
nightctl add --title "Investigate caching strategy" --kind agent-job --priority 2
# → status: open (plan validation deferred until planning → plan-review)

# 2. Enter planning phase
nightctl plan <id>
# → status: planning

# 3. Author plan (human writes XML, or co-authors with agent)
nightctl edit <id> --plan-ref docs/d2/spec-caching.md

# 4. Submit for review
nightctl review <id>
# → status: plan-review (XML validation runs here)
# ERROR if plan doesn't validate

# 5. Human approves
nightctl approve <id>
# → status: in-progress (XML validation runs again as safety check)
# Item is now eligible for nightctl run
```

### Listing

```bash
nightctl list                    # active items, all kinds
nightctl list --kind job         # just machine jobs
nightctl list --kind agent-job   # agent work
nightctl list --status blocked   # just blocked items
nightctl list --schedule overnight  # what's on the night train
nightctl graph                   # ASCII priority tree
```

### State transitions

```bash
nightctl start <id>              # open → in-progress (tasks/jobs)
nightctl plan <id>               # open → planning (agent-jobs)
nightctl review <id>             # planning → plan-review, or in-progress → review
nightctl approve <id>            # plan-review → in-progress
nightctl done <id>               # review|testing → done
nightctl block <id> --by "reason"
nightctl defer <id>
nightctl cancel <id>
nightctl revise <id>             # failed → plan-review (agent-jobs)
nightctl retry <id>              # failed → in-progress (jobs)
```

### Execution

```bash
nightctl run                     # execute in-progress jobs/agent-jobs in window
nightctl run --force             # ignore window
nightctl run --dry-run           # show what would execute
nightctl status <id>             # show item + run history
```

## Migration Plan

1. Create new unified Item model with state machine from todoctl and execution from nightctl
2. Add atomic writes (tmp + os.replace) to Item.save()
3. Implement XML plan validation module
4. Expand nightctl CLI: plan, approve, revise, retry, review, testing, block, defer, edit, graph
5. Wire agent-job execution to container-runner
6. Migrate existing todoctl backlog items to new schema in queue/items/
7. Merge nightctl.yaml and todoctl.yaml into single config
8. Update CLAUDE.md, halos-modules.md, all references
9. Remove todoctl from pyproject.toml console_scripts
10. Archive halos/todoctl/ (provenance, not deletion)
11. Update reportctl/briefings collectors that read todoctl data
12. Hard cut from backlog/items/ and queue/jobs/ to queue/items/

## Acceptance Criteria

1. `nightctl add --kind task` creates an item with null command/schedule/plan fields
2. `nightctl add --kind job` requires --command
3. `nightctl add --kind agent-job` accepts item without plan (deferred to plan-review gate)
4. `nightctl plan <id>` transitions open → planning
5. `nightctl review <id>` on a planning item validates XML plan; rejects if invalid
6. `nightctl approve <id>` transitions plan-review → in-progress with re-validation
7. XML validation enforces: goal, steps with n and output attrs, constraints, success criteria
8. State transitions are validated; invalid transitions produce TransitionError with allowed alternatives
9. `nightctl run` only executes items where status=in-progress AND kind ∈ {job, agent-job}
10. `nightctl run` skips items outside the overnight window unless --force
11. `nightctl run` respects depends_on ordering
12. Agent-job execution delegates to container-runner with XML plan
13. Run records are written for every execution attempt
14. Failed agent-jobs can transition to plan-review via `nightctl revise`
15. Failed jobs can transition to in-progress via `nightctl retry`
16. `nightctl graph` produces ASCII priority tree
17. `nightctl list` shows all active items regardless of kind
18. `nightctl list --kind <kind>` filters correctly
19. All file writes use atomic tmp+rename pattern
20. Cancelled/done items remain in items/ for configurable retention period
21. `nightctl archive --execute` respects retention period
22. Manifest rebuilds correctly from items/ directory
23. Manifest verify detects hash drift
24. Existing todoctl backlog items are migrated with status preserved
25. `todoctl` console_script is removed from pyproject.toml
26. `nightctl --help` includes "your best work happens while you sleep"
27. reportctl and briefings collectors work with new item location

## Definition of Done

- [ ] All 27 acceptance criteria have passing tests
- [ ] State machine transitions tested exhaustively (every valid + every invalid pair)
- [ ] XML plan validation tested: valid plans, missing elements, malformed XML
- [ ] Error paths produce clear, actionable messages
- [ ] Migration script tested on real backlog items
- [ ] Container-runner integration tested with sample agent-job
- [ ] `make gate` passes (or equivalent)
- [ ] Development logbook entry written
- [ ] CLAUDE.md updated (todoctl removed, nightctl description expanded)
- [ ] halos-modules.md updated (todoctl row removed)
- [ ] Code reviewed (adversarial, not confirmatory)

## Resolved Questions

1. **ID format**: timestamp-uuid (nightctl style). Collision-resistant for parallel agent creation.
2. **Agent-job execution**: Delegates to container-runner. This is the container moment.
3. **Plan validation**: Structured XML with mandatory elements. Format separation (XML for instructions, YAML for data) prevents prompt injection confusion.
4. **Config**: Single nightctl.yaml.
5. **Directory**: Hard cut to queue/items/. No symlinks.

## Agent Deployment Strategy

Spec → code → review cycle. Implementation phases:

- **Phase 1** (this document): Spec confirmed via interview
- **Phase 2** (next): Implementation plan — determine agent count, parallelism, and sequencing
- **Phase 3**: Code — likely 2-3 agents in parallel on independent modules (Item model, CLI, migration)
- **Phase 4**: Code review — adversarial-reviewer agent
- **Phase 5**: Integration test and gate

## Provenance

This spec crystallised from a single morning session (2026-03-17) that began as a roadmap/backlog triage and evolved through caffeine-driven architecture into a unified work tracker design. The full narrative is recorded in `memory/reflections/2026-03-17-deliberate-collaboration.md`. The development logbook at `docs/d1/development-logbook.md` contains the individual decision entries.

Δ₁ = this spec. Δ₂ = what ships. The difference is the learning.
