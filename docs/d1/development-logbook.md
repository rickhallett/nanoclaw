---
title: "Development Logbook"
category: journal
status: active
created: 2026-03-15
---

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

- date: '2026-03-17'
  title: "Phase 6 verdict: artisanal architecture, the atomic lie, the enforcement loop"
  summary: |
    Human architectural review delivered three key findings:

    1. "Artisanal Architecture" — halos is built for a single-user
       power-operator and this is a feature, not a limitation. O(N) index
       loading and filesystem polling create scaling walls that can't be
       solved by adding RAM. Multi-tenant/enterprise is explicitly out of
       scope. Standing decision: don't apologise for this.

    2. "The Atomic Lie" — tmp-then-rename is atomic for the file but not
       for the operation. Note-then-index two-step has a crash window.
       Acceptable at n=1 with 93 notes. Not acceptable at n=1000 with a
       fleet. Fix: advisory locking or WAL. Conscious tradeoff.

    3. "The Enforcement Loop" — the system's architecture (CLAUDE.md
       personality + memctl boot sequence + enrichment hooks) creates a
       feedback loop that runs through the transformer's attention
       mechanism. This is emergent agent training without fine-tuning.
       The tool-output-as-nudge pattern is the actual innovation.

    Also produced: full system trace diagrams (message flow, container
    boundaries, halos module anatomy) with "felt sense" annotations
    bridging engineering and experiential understanding.
  refs:
    todo: null
    note: null
    commit: null
  tags: [halos, architecture, review, process]
  moon: waning gibbous

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

- date: '2026-03-18'
  title: Fleet provisioned, eval harness built, test-pilot-001 launched
  summary: |
    Overnight session. 23 commits. The fleet went from concept to live
    deployment in one arc: provisioned Dad (@HALCaptain_bot), Mum
    (@HALMum_bot), and two test instances (gains, money). Each instance
    is an independent halo deployment with its own bot token,
    personality profile, memory, and sandboxed filesystem.

    The provisioning pipeline hit every class of integration bug:
    stale session IDs copied from prime, brittle source patching for
    proxy routing, missing node_modules, locked skills permissions,
    and CLAUDE.md personality clobbering on push. Each bug was fixed
    at the root — CONTAINER_PROXY_PORT upstreamed to prime, store/
    excluded from copy, push recomposes CLAUDE.md, operator chat
    pre-registered in halctl create.

    Built a tier 2 smoke test (halctl smoke) that validates 15 checks
    including a live agent round-trip via DB injection + pm2 log polling.
    Then built an assessment eval harness (halctl assess) with 8
    scenarios: 5 single-injection (likert delivery, timing gates,
    task non-interruption, deflection) and 3 multi-turn dialogue
    (tangent-and-resume at 11 turns, deflect-then-resume, edit-response).

    Default personality passes 8/8. Dad's terse/opinionated profile
    passes 5/8. Standing decision: accept personality variance as data.
    Review threshold at 4/8.

    Ben (test-pilot-001) registered at tg:8660755707, accepted waiver,
    mid-Likert assessment as of 10:29 UTC. First real user in flight.

    Key patterns documented in session-patterns-2026-03-18.md:
    state leakage, detection fragility, governance precedence,
    multi-line log parsing, proxy routing, provisioning completeness,
    dialogue pacing, governance wording.
  refs:
    commit: 116544a..952ed19
    note: null
    session: null
  tags: [fleet, provisioning, eval, assessments, testpilot, microhal]
  moon: waning crescent

- date: '2026-03-28'
  title: Credential sync cron installed — two-layer token refresh
  summary: |
    Hermes Telegram bot returned 401. Root cause: ~/.claude/.credentials.json
    was empty/corrupt, so the in-process token refresh had no refresh token
    to work with. Manual fix: ran sync-claude-credentials.sh to restore from
    macOS Keychain.

    Prevention: added cron job (0 */4 * * *) to sync Keychain → credential
    file every 4 hours, logging to ~/.hermes/logs/credential-sync.log.

    Two layers now: cron keeps the file populated, Hermes auto-refreshes
    expired access tokens in-process. If the refresh token itself expires
    (weeks/months), claude /login is still required.
  refs:
    todo: null
    note: null
    commit: null
  tags: [hermes, credentials, cron, ops]
  moon: null

- date: '2026-03-28'
  title: "Job application pipeline: Wellfound automation + pre-application evaluation gate"
  summary: |
    Built an end-to-end job application pipeline: browse Wellfound feed via
    CDP Chrome → score remote UK candidates → inspect JD → generate tailored
    cover text → submit via Playwright → track in jobctl DB + metrics JSONL.

    Trial run applied to Eequ (Senior Backend Engineer, UK Remote, £80-100k).
    Application submitted successfully. Post-mortem revealed a calibration
    failure: the JD opens with "You will have been the primary owner of
    production systems, accountable for their design, deployment, and
    reliability under real-world load." The profile cannot make this claim.
    Enterprise experience is frontend-primary (React at Brandwatch/EDITED);
    backend/infra capabilities exist only in self-built context (halos, The
    Pit) with no external users or production load.

    Built a pre-application evaluation gate (jobctl/jd_evaluator.py) that
    compares JDs against an honest capability profile (jobctl/capability-
    profile.yaml) with evidence tiers: enterprise, self-built, familiar,
    none. Profile explicitly marks gaps: no cloud infra ownership, no
    production backend ownership, no incident response experience.

    Evaluator correctly scores the Eequ role at 0.40 with three dealbreakers.
    Correctly scores a hypothetical React/TS AI tools role at 0.85 with no
    dealbreakers. Gate is now mandatory step 0 in the pipeline skill.

    IMPORTANT CAVEAT: The evaluator, capability profile, AND the three test
    cases were all designed by the same LLM in the same session. This is
    circular validation — the model agreeing with itself is not calibration.
    The test cases are plausible but not independently verified. True
    calibration requires human-labeled training data: bookmarking 20-30 real
    roles into fit buckets (strong/decent/marginal/poor), running them
    through the rubric, and adjusting profile dimensions and thresholds from
    the disagreements. This is tracked as a Q2 nightctl task pending human
    input.

    The automated gate is better than no gate (the Eequ application proves
    that), but its accuracy claims should be held lightly until validated
    against human judgment on a meaningful sample.

    Files created:
    - jobctl/capability-profile.yaml (evidence-tiered capability profile)
    - jobctl/jd_evaluator.py (Claude-powered fit evaluation)
    - store/wellfound_metrics.jsonl (per-application metrics)
    - Skill: wellfound-job-application (full pipeline with selector cache)
  refs:
    todo: 20260328-220513-69bb1e5e
    note: null
    commit: null
    session: null
  tags: [jobctl, wellfound, calibration, pipeline, automation, evaluation]
  moon: null

- date: '2026-04-05'
  title: Fleet image build caching — GHA layer cache + Dockerfile restructure
  summary: |
    Full image rebuilds were taking 10+ minutes even for single-line halos
    changes, because the Dockerfile invalidated Docker's layer cache at
    the `COPY vendor/hermes-agent` step — everything after it rebuilt.

    Two changes:

    1. **Dockerfile restructured** into dependency-then-source layers.
       Hermes pyproject.toml + package.json copied first and deps installed;
       full source copied after. Halos gets the same treatment. When only
       halos Python files change, only the final COPY + pip install runs
       (~30s instead of ~8min for Hermes deps).

    2. **GHA build cache** (`cache-from: type=gha`, `cache-to: type=gha,mode=max`)
       added to both build steps. Docker layers persist across workflow runs
       in GitHub's cache. First build populates the cache; subsequent builds
       reuse unchanged layers.

    Expected halos-only rebuild: ~1-2 minutes (cache hit on system deps,
    Node deps, Python deps; cache miss only on halos source layer).
    Full rebuild (Hermes changes): ~8 minutes (same as before, but cached
    on subsequent runs).
  refs:
    commit: null
    note: null
  tags: [infra, ci, docker, performance]
  moon: null

- date: '2026-04-05'
  title: Fleet deployment — four advisors live on VKE with NATS event sourcing
  summary: |
    Deployed Musashi, Socrates, Medici, and Machiavelli as Hermes gateway
    pods in halo-fleet namespace on VKE. Single image, differentiated by
    ConfigMap (config.yaml, system-prompt.md) and Secret (bot token, API key).

    NATS JetStream deployed in-cluster with HALO stream (halo.> subjects,
    5GB, 90d retention). AdvisorEventLoop runs as background process in
    each pod alongside Hermes — consumes events, maintains local SQLite
    projections. Stream seeded with 22 events from local trackctl/journalctl.

    Aura session relay added as sidecar in halo-aura namespace — tails
    Hermes JSONL session files, publishes user/assistant messages to
    halo.observation.aura on the HALO stream.

    Key bugs found and fixed during deployment:
    - Store path resolution walked from __file__ (fails in venv install)
    - ConfigMap subPath mounts are read-only (breaks /sethome)
    - bash -lic login shell resets PATH (strips /opt/venv/bin)
    - imagePullPolicy defaults to IfNotPresent for non-'latest' tags
    - Vultr CR tag deletion API is broken (500s on all endpoints)
    - Relative paths in prompts don't resolve in container cwd

    All documented in infra/k8s/fleet/README.md (13 numbered gotchas).

    Resource profile: 50m CPU / 192Mi per advisor. Actual usage at idle:
    1-2m CPU / 90Mi. Node at 9% CPU, 53% memory with four advisors +
    NATS + monitoring + old gateway.
  refs:
    commit: null
    note: null
  tags: [fleet, k8s, nats, eventsource, deployment, advisors]
  moon: null
