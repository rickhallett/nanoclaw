# Development Logbook

Architectural decisions, design tensions, and the reasoning behind them. Written as they happen so future readers (human, agent, or article audience) don't have to reverse-engineer intent from code.

## Entry Schema

```yaml
- date: '2026-03-17'              # when the decision crystallised
  title: Short factual title
  summary: |
    What happened, what we decided, and why.
  refs:
    todo: 20260317-071834-331      # todoctl ID, if applicable
    commit: abc1234                 # commit hash, if applicable
    note: 20260317-071211-017      # memctl note ID, if applicable
    session: null                  # agentctl session ID, if applicable
    url: null                      # external link, if applicable
  tags: [halos, architecture]
  moon: null                       # for the astrologically inclined
```

All fields optional except `date`, `title`, and `summary`. Refs exist so you can trace the decision back to the work that produced it.

## Entries

- date: '2026-03-17'
  title: Agent-facing tooling must enforce constraints, not rely on convention
  summary: |
    nightctl and todoctl drifted within 24 hours of coexistence. 7 jobs
    queued, all cancelled, with only partial overlap to the 5 open todos.
    The dual-ledger problem: two systems tracking overlapping state with
    no foreign key between them.

    Initial instinct was option 2 (convention — add a todo_id field to
    job YAML). Rejected: convention is a paper guardrail. Agent-operated
    tooling needs structural enforcement because agents forget between
    sessions. Steel girders, not paper guardrails.

    Decision: option 3 — nightctl add requires --todo-id or explicit
    --no-todo. Deterministic, auditable, structurally impossible to drift.
  refs:
    todo: null
    note: 20260317-071211-017
    commit: null
  tags: [halos, architecture, nightctl, todoctl]
  moon: waning gibbous

- date: '2026-03-17'
  title: todoctl and nightctl may be one module wearing two hats
  summary: |
    Follow-on from the enforcement decision. If nightctl must call todoctl
    at creation time and todoctl must call nightctl for batch scheduling,
    that's a distributed transaction between two participants maintaining
    the fiction of independence. They share the same entity: a unit of work.

    A todo with schedule: overnight and a run_history: field *is* both
    modules. Scheduling becomes a property, not a parallel system.

    Not yet decided — logged as evaluation todo. The refactor is real work
    and the current separation isn't blocking anything immediately.
  refs:
    todo: 20260317-071834-331
    note: null
    commit: null
  tags: [halos, architecture, nightctl, todoctl]
  moon: waning gibbous

- date: '2026-03-17'
  title: Boot-time decision audit — agents must prove they read the rules
  summary: |
    Standing decisions (memctl type=decision) should be programmatically
    presented to agents at boot via a CLI command. logctl records the
    presentation timestamp. This closes the open loop in most agent
    systems: you can write governance, but without an audit trail proving
    the agent saw it, you can't distinguish "ignored" from "never loaded."

    TBD: whether the agent also signs a read-receipt (second timestamp).
    The presentation + logging is confirmed scope.
  refs:
    todo: 20260317-070508-080
    note: null
    commit: null
  tags: [halos, memctl, agentctl, observability]
  moon: waning gibbous

- date: '2026-03-17'
  title: "halOS" is now "halos" — lowercase energy, case-sensitive
  summary: |
    The naming question (todoctl item 20260316-030927) resolved itself
    through usage. The Python package was always `halos/`. The docs and
    CLI descriptions used "halOS" as a stylised form. Two casings for
    one thing is a bug report waiting to happen on release day.

    Calling it an operating system, even as a stylistic joke, doesn't
    make sense — it's a toolkit. Lowercase "halos" everywhere, including
    sentence starts. Proper noun like git or npm. 26 files updated, zero
    occurrences of "halOS" remain. The todo "Name the halos meta-system"
    was marked done — the name stuck, the casing didn't.
  refs:
    todo: 20260316-030927
    note: null
    commit: null
  tags: [halos, naming, release-readiness]
  moon: waning gibbous

- date: '2026-03-17'
  title: nightctl unified work tracker — spec crystallised from brainfart pipeline
  summary: |
    todoctl and nightctl merge confirmed. nightctl becomes the SSOT for all
    work: human tasks, machine jobs, and agent jobs. Three kinds, one state
    machine, one CLI.

    Key design decisions reached through conversation:
    - kind field (task/job/agent-job) determines execution path and delegation
    - Agent-jobs require XML plans with mandatory constraints (anti-deskilling)
    - XML for plans, YAML for data — format separation signals intent
    - 12-state machine with two tracks: planning (human loop) and execution
      (machine loop), converging at in-progress
    - failed agent-jobs transition to plan-review, not retry (the plan is
      what needs fixing)
    - plan-review is the passport control gate: human must approve, XML
      must validate
    - Cancelled items leave a wake (30-day retention before archive sweep)

    Full session documented as a canonical example of brainfart-to-spec
    process in reflections/2026-03-17-deliberate-collaboration.md.
  refs:
    todo: 20260317-075446-291
    note: 20260317-082412-436
    commit: null
    reflection: memory/reflections/2026-03-17-deliberate-collaboration.md
  tags: [halos, architecture, nightctl, todoctl, process]
  moon: waning gibbous

- date: '2026-03-17'
  title: Cross-model adversarial review — 6 findings, 2 critical pre-existing
  summary: |
    External model review (not Claude) of the full codebase identified:
    (1) yaml_shim.py is unnecessary slop — PyYAML is already a dependency,
    the shim can't handle multiline strings (our own gauntlet confirmed this).
    Delete it. (2) Cursor pre-advancement in index.ts marks messages as seen
    before agent processes them — data loss on container crash. Move saveState
    to success path. (3) IDLE_TIMEOUT == CONTAINER_TIMEOUT races graceful
    shutdown against hard kill. (4) Main group mounts project root read-only
    including SQLite — cross-group data visible. Already mitigated for
    microHALs via disableProjectMemory. (5) memctl enrich scores based on
    metadata overlap, not semantic content — "Analytical Lullaby" creates
    false confidence. (6) reportctl dual ledger between manifest and run
    files — same pattern we killed in todoctl/nightctl.

    The review validated our architectural direction (nightctl merge,
    microHAL isolation model) while surfacing pre-existing bugs in the
    Node.js orchestrator layer that today's Python-focused work didn't touch.

    Round 2 (same reviewer, deeper): 7 more findings. Two genuinely
    critical: (a) non-main group agents have rw mount on shared memory,
    can rm -rf decision notes — the guard is CLAUDE.md instructions not
    filesystem permissions. (b) executor.py uses shell=True with
    subprocess.run on the host, enabling command injection if an agent
    enqueues a user-influenced command. Also flagged: memctl index rebuild
    race condition (no file locking), INDEX.md scaling wall at ~1000 notes
    (~75k tokens on every boot), nightctl approve callable by agents
    (sycophantic self-approval). The "passport control" finding is
    architecturally valid — the human gate is policy not structure.
  refs:
    todo: null
    note: null
    commit: null
  tags: [halos, architecture, security, review]
  moon: waning gibbous
