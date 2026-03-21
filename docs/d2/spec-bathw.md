---
title: "BATHW — Building Agents the Hard Way"
category: spec
status: active
created: 2026-03-17
---

================================================================
BATHW — Building Agents the Hard Way
Technical Publication — Specification v0.1
================================================================

OVERVIEW
--------
BATHW is an interactive technical publication backed by live
operational telemetry from the NanoClaw agent system. It combines
engineering case studies, live-queried data visualisations, and a
structured failure library documenting what actually happens when
you run an agent system for months.

LANDSCAPE
---------
The tooling for agent observability is maturing (Langfuse, OpenLIT,
Helicone, Datadog LLM Observability). Academic work on agent failure
modes exists — notably MAST (NeurIPS 2025), which annotated 1,600+
traces across 7 frameworks using benchmark tasks.

What is absent is empirical, longitudinal data from production
systems. Specifically:

- No public datasets or dashboards of agent operational telemetry.
- No published failure frequency distributions from real workloads
  (MAST and similar use benchmark traces, not production).
- No longitudinal intervention rate tracking. Best available: the
  MAP study (arxiv 2512.04123), a survey of 306 practitioners
  finding 68% of production agents do ≤10 steps before human
  intervention. No time-series data exists.
- No published cost-per-task breakdowns from sustained agent usage.
- RAG/memory scaling: architectural guidance exists; the empirical
  study (precision and latency at 100/1K/10K/100K documents) does
  not.
- LLM-as-judge methodology is well-documented. Calibration data
  against real workloads is not.

BATHW contributes to these gaps by publishing structured telemetry
from a real agent system operating as a daily-use personal assistant,
with classified failure modes, intervention tracking, cost data,
and memory scaling observations.

Full landscape analysis: docs/d2/analysis-agent-telemetry-landscape.md

================================================================
TIMELINE
================================================================

Hard constraint: 60 days from 2026-03-16 (deadline: 2026-05-15).
Financial constraints require the publication to be generating
value well before that. The build is front-loaded at agentic
velocity. Data accumulation — not coding — is the real bottleneck.

Retroactive data exists: git history of INDEX.md gives memory
scaling time-series. logctl gives incident backfill. agentctl
logs give session history. Weeks of operation precede day 1.

Phase 1 — PIPELINE (days 1-3)
  Ship everything needed for data to flow and a surface to exist.

  - halos/telemetry module (emit() function)
  - ClickHouse on Fly.io, full schema deployed
  - OTLP collector wired to halos modules
  - All modules instrumented: agentctl, memctl, cronctl, todoctl,
    briefings, reportctl
  - Intervention tracking in agentctl
  - Failure taxonomy schema + backfill from existing logs
  - Next.js + MDX scaffold deployed on Vercel
  - Backfilled memory scaling data from git history
  - First live charts: sessions, tokens, cost, memory corpus growth

  Exit criteria: live site with working telemetry pipeline,
  backfilled history, and live data flowing. Linkable from CV.

Phase 2 — FIRST CASE STUDIES (days 4-7)
  Draft the case studies that have enough data to say something.

  - CS-01 draft: "The Intervention Rate" (backfilled + live)
  - CS-02 draft: "Memory at Scale" (backfilled data gives depth)
  - CS-03 draft: "Where the Money Goes" (instrumented cost data)
  - Incident database on site with classified entries
  - Evaluation framework deployed (LLM-as-judge, sampled 20%)

  Exit criteria: three case study drafts live, incident database
  populated, eval pipeline running.

Phase 3 — ACCUMULATION (days 8-60)
  Data takes time to exist. Curves need days to pass. Every day
  that passes makes the site more valuable automatically.

  Day 8-21:  Case studies revised as trendlines emerge.
  Day 21-30: CS-04 "Failure Taxonomy v1" — enough incidents for
             Pareto distribution to be visible.
  Day 30-45: CS-05 eval calibration — manual scoring of 50+
             sessions against LLM-as-judge.
  Day 45-60: Second-order findings. Patterns not hypothesised.
             Publication defensible as a body of work.

  Ongoing: cautious feature-by-feature expansion. Each addition
  earns its place with data justification.

  Roadmap (post-60 if trajectory supports it):
  - Public API (open community resource)
  - Community benchmark datasets
  - Extended case studies as data warrants

================================================================
TELEMETRY SCHEMA — CORE TABLES
================================================================

All timestamps UTC. All IDs ULID or ISO8601-compact as per memctl
convention. ClickHouse MergeTree family for time-series tables.

--- AGENT SESSIONS ---

Table: agent_sessions

  session_id        String        -- ULID
  started_at        DateTime64(3) -- session start
  ended_at          DateTime64(3) -- session end (nullable)
  duration_ms       UInt64        -- wall clock
  group_name        String        -- nanoclaw group context
  channel           String        -- whatsapp|telegram|slack|cron|ipc
  trigger_type      String        -- user_message|scheduled|ipc_task
  model             String        -- claude-sonnet-4-6 etc
  input_tokens      UInt32
  output_tokens     UInt32
  cache_read_tokens UInt32
  cache_write_tokens UInt32
  total_cost_usd    Float64       -- computed from token counts
  tool_calls        UInt16        -- total tool invocations
  turns             UInt16        -- conversation turns
  outcome           Enum8('success','partial','failure','timeout','cancelled')
  intervention      Bool          -- did human correct the agent?
  intervention_type String        -- nullable: 'redirect','correction','abort'
  error_class       String        -- nullable: failure taxonomy code

Engine: MergeTree ORDER BY (started_at, group_name)

--- TOOL USAGE ---

Table: tool_usage

  session_id        String
  tool_name         String        -- Read, Write, Bash, etc
  invocation_idx    UInt16        -- order within session
  started_at        DateTime64(3)
  duration_ms       UInt32
  success           Bool
  error_message     String        -- nullable, truncated to 500 chars
  input_tokens      UInt32        -- tokens in tool input
  output_tokens     UInt32        -- tokens in tool output

Engine: MergeTree ORDER BY (started_at, tool_name)

--- MEMORY EVENTS ---

Table: memory_events

  event_id          String        -- ULID
  timestamp         DateTime64(3)
  event_type        Enum8('note_created','note_pruned','note_archived',
                         'backlink_added','index_rebuilt','search_performed',
                         'enrich_proposed','enrich_accepted')
  note_id           String        -- nullable
  note_type         String        -- nullable: decision, fact, reference, etc
  tags              Array(String)
  entities          Array(String)
  corpus_size       UInt32        -- total notes at time of event
  search_query      String        -- nullable, for search events
  search_results    UInt16        -- nullable

Engine: MergeTree ORDER BY (timestamp, event_type)

--- EVALUATION SCORES ---

Table: eval_scores

  eval_id           String        -- ULID
  session_id        String        -- FK to agent_sessions
  timestamp         DateTime64(3)
  eval_type         Enum8('quality','relevance','safety','cost_efficiency',
                         'task_completion','instruction_adherence')
  score             Float32       -- 0.0 to 1.0 normalised
  judge_model       String        -- which model scored this
  judge_prompt_hash String        -- hash of eval prompt (for versioning)
  reasoning         String        -- judge's reasoning, truncated to 1000 chars
  human_override    Float32       -- nullable, human-provided score for calibration

Engine: MergeTree ORDER BY (timestamp, eval_type)

--- INCIDENTS ---

Table: incidents

  incident_id       String        -- ULID
  timestamp         DateTime64(3)
  session_id        String        -- nullable FK
  severity          Enum8('info','warning','error','critical')
  failure_class     String        -- taxonomy code (see FAILURE TAXONOMY)
  title             String
  description       String
  root_cause        String
  resolution        String
  time_to_resolve_m UInt32        -- minutes
  recurrence_count  UInt16        -- how many times this class has occurred
  tags              Array(String)

Engine: MergeTree ORDER BY (timestamp, failure_class)

--- COST TRACKING ---

Table: daily_costs

  date              Date
  group_name        String
  channel           String
  session_count     UInt16
  total_input_tokens  UInt64
  total_output_tokens UInt64
  total_cost_usd    Float64
  avg_cost_per_session Float64
  avg_tokens_per_session UInt32

Engine: SummingMergeTree ORDER BY (date, group_name, channel)

--- MEMORY SCALING ---

Table: memory_snapshots

  snapshot_date     Date
  corpus_size       UInt32        -- total notes
  decision_count    UInt16
  fact_count        UInt16
  reference_count   UInt16
  backlink_count    UInt32        -- total edges in graph
  avg_backlinks     Float32
  orphan_count      UInt16        -- notes with 0 backlinks
  prune_candidates  UInt16        -- notes below min_score
  index_size_bytes  UInt32
  rebuild_time_ms   UInt32
  search_avg_ms     Float32       -- avg search latency (sampled)

Engine: MergeTree ORDER BY snapshot_date

================================================================
FAILURE TAXONOMY
================================================================

Classification codes for agent failures. Hierarchical.
Prefix indicates category.

  CTX-001  Context overflow — window exceeded mid-task
  CTX-002  Context overflow — compaction lost critical state
  CTX-003  Context pollution — irrelevant context degraded output

  INS-001  Instruction drift — agent deviated from explicit instruction
  INS-002  Instruction conflict — contradictory instructions in context
  INS-003  Sycophantic compliance — agent agreed with incorrect premise

  TOL-001  Tool misuse — wrong tool for the task
  TOL-002  Tool hallucination — fabricated tool arguments
  TOL-003  Tool loop — repeated failed tool calls without adaptation

  MEM-001  Memory miss — relevant note existed but wasn't retrieved
  MEM-002  Memory stale — retrieved note contained outdated information
  MEM-003  Memory overload — too many notes loaded, diluted context

  HAL-001  Factual hallucination — stated false information as fact
  HAL-002  Code hallucination — generated non-functional code confidently
  HAL-003  Reference hallucination — cited non-existent file/function

  COS-001  Cost spike — session cost >3x rolling average
  COS-002  Token waste — excessive output for simple task
  COS-003  Retry storm — repeated API calls on transient failure

  GOV-001  Governance bypass — agent circumvented safety/governance check
  GOV-002  Scope creep — agent did significantly more than requested
  GOV-003  Autonomy failure — agent should have asked but didn't

================================================================
TESTABLE HYPOTHESES
================================================================

These guide data collection priorities. Each must be answerable
from the telemetry schema above.

H1: MEMORY SCALING
  "Memory governance (pruning + backlinks) maintains sub-linear
   search latency as corpus grows from 100 to 10,000 notes."
  Metric: search_avg_ms in memory_snapshots vs corpus_size
  Expected: logarithmic curve, not linear
  Break point: where does it go linear? That's the story.

H2: INTERVENTION RATE DECAY
  "Agent intervention rate decreases over time as memory
   accumulates operational context."
  Metric: intervention rate (intervened sessions / total) by week
  Expected: downward trend, possibly with plateaus
  Counter-hypothesis: intervention rate is constant (memory doesn't help)

H3: CONTEXT WINDOW ECONOMICS
  "Aggressive context management (compaction, selective memory
   loading) reduces per-session cost by >30% vs naive approaches."
  Metric: total_cost_usd and tokens per session, before/after
  Requires: A/B period with different context strategies

H4: FAILURE MODE DISTRIBUTION
  "Agent failures follow a power law — 3-4 failure classes account
   for >80% of incidents."
  Metric: incident counts by failure_class
  Expected: Pareto distribution
  Actionable: focus mitigation on the top 3-4 classes

H5: EVALUATION CALIBRATION
  "LLM-as-judge scores correlate with human scores at r>0.7 after
   calibration on 50+ samples."
  Metric: eval_scores.score vs eval_scores.human_override
  Requires: manual scoring of subset of sessions

H6: COST PREDICTABILITY
  "Daily agent costs are predictable within ±20% after 30 days
   of baseline data."
  Metric: daily_costs.total_cost_usd, forecast vs actual
  Actionable: budget planning for agent operations

H7: TOOL USAGE PATTERNS
  "Tool usage distribution reveals agent 'habits' — some tools
   are over-used relative to task requirements."
  Metric: tool_usage counts by tool_name, normalised by task type
  Actionable: prompt engineering to correct tool selection bias

H8: MEMORY DECAY CURVES
  "Notes without backlinks lose relevance (measured by retrieval
   frequency) exponentially with half-life ~30 days."
  Metric: search result inclusion frequency per note over time
  Validates: the pruning half_life_days=30 config value

================================================================
KEY QUERIES (pre-built views)
================================================================

These are the queries the dashboard needs. Designing them now
ensures the schema supports them.

-- Daily cost trend
SELECT date, sum(total_cost_usd) as cost,
       sum(session_count) as sessions
FROM daily_costs
GROUP BY date ORDER BY date

-- Intervention rate by week
SELECT toMonday(started_at) as week,
       countIf(intervention = true) / count() as intervention_rate,
       count() as total_sessions
FROM agent_sessions
GROUP BY week ORDER BY week

-- Failure class distribution (Pareto)
SELECT failure_class,
       count() as incidents,
       sum(count()) OVER () as total,
       count() / sum(count()) OVER () as pct
FROM incidents
GROUP BY failure_class
ORDER BY incidents DESC

-- Memory corpus growth + search latency
SELECT snapshot_date, corpus_size, search_avg_ms,
       backlink_count, orphan_count
FROM memory_snapshots
ORDER BY snapshot_date

-- Token economics by channel
SELECT channel,
       avg(total_cost_usd) as avg_cost,
       avg(input_tokens + output_tokens) as avg_tokens,
       avg(duration_ms) / 1000 as avg_duration_s
FROM agent_sessions
WHERE started_at > now() - INTERVAL 30 DAY
GROUP BY channel

-- Eval score trends (quality over time)
SELECT toMonday(timestamp) as week,
       eval_type,
       avg(score) as avg_score,
       count() as sample_size
FROM eval_scores
GROUP BY week, eval_type
ORDER BY week

-- Tool usage heatmap (tool × hour of day)
SELECT tool_name,
       toHour(started_at) as hour,
       count() as invocations,
       avg(duration_ms) as avg_duration
FROM tool_usage
GROUP BY tool_name, hour

-- Cost anomaly detection
SELECT session_id, started_at, total_cost_usd,
       avg(total_cost_usd) OVER (
         ORDER BY started_at
         ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
       ) as rolling_avg,
       total_cost_usd / nullIf(avg(total_cost_usd) OVER (
         ORDER BY started_at
         ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
       ), 0) as cost_ratio
FROM agent_sessions
WHERE total_cost_usd > 0
ORDER BY started_at

================================================================
CONTENT PLAN — FIRST CASE STUDIES
================================================================

Written in Phase 2 after 4+ weeks of data. Each is an MDX
document with embedded live-query chart components.

CS-01: "The Intervention Rate"
  The single most important metric for agent reliability.
  Daily/weekly intervention rate over time. Breakdown by task
  type and channel. What triggers human correction? Is the
  agent getting better? This is the headline number.

CS-02: "Memory at Scale — From 82 to 820 Notes"
  How structured memory governance behaves as corpus grows.
  Search latency curves. Backlink density. Pruning effectiveness.
  Where does it flatten? Where does it break? The scaling story.

CS-03: "Where the Money Goes"
  Token economics by channel, task type, time of day. Cost per
  automated task vs estimated manual time. What context management
  strategies actually reduce cost vs what's folklore.

CS-04: "Failure Taxonomy v1"
  The classification system. Frequency counts by class. Pareto
  distribution. Top 3-4 classes with deep-dive analysis. Published
  as a reference others can use.

CS-05: "Eval Without a PhD"
  LLM-as-judge calibration against a real personal-assistant workload.
  Methodology is well-documented elsewhere; the contribution here is
  calibration data — correlation with human scores across task types,
  where judge accuracy breaks down, and sample-size thresholds for
  statistical confidence. Published calibration dataset and code.

================================================================
DATA INTERFACES — HALOS INTEGRATION
================================================================

Each halos module gets a telemetry emitter. Minimal intrusion.
The emitter writes structured events that the OTLP collector
picks up and forwards to ClickHouse.

Module          Events emitted
------          --------------
memctl          note_created, note_pruned, backlink_added,
                index_rebuilt, search_performed, enrich_run
agentctl        session_started, session_ended, token_usage,
                intervention_detected
cronctl         job_scheduled, job_started, job_completed,
                job_failed
todoctl         task_created, task_transitioned, task_completed
logctl          (already structured — tap existing log stream)
briefings       briefing_generated, briefing_delivered
reportctl       digest_generated

Integration pattern:
  from halos.telemetry import emit
  emit("note_created", {note_id: "...", type: "fact", ...})

The emit() function:
  - Writes to OTLP if collector is available
  - Falls back to structured JSON log line (logctl-compatible)
  - Never blocks the calling module
  - Never fails loudly (fire-and-forget with local buffer)

================================================================
INFRASTRUCTURE
================================================================

Phase 1 (local):
  - ClickHouse single-node (Docker or Fly.io free tier)
  - OTLP collector (otel-collector-contrib, Docker)
  - halos modules emit via OTLP gRPC or HTTP

Phase 2 (deployed):
  - ClickHouse on Fly.io or Railway
  - Next.js on Vercel
  - ClickHouse HTTP API for live queries from frontend
  - MDX content in the repo (version-controlled)

Phase 3 (production):
  - Public read-only API over ClickHouse (thin auth layer)
  - Evaluation pipeline (separate cron job)
  - Incident classification (manual + assisted)

================================================================
OPEN QUESTIONS
================================================================

Q1: ClickHouse vs TimescaleDB?
  ClickHouse: better compression, faster analytical queries,
  column-oriented. TimescaleDB: Postgres-compatible, simpler
  if you already run Postgres. Leaning ClickHouse for the
  signal it sends (serious about time-series) and because
  nanoclaw already uses SQLite, not Postgres.

Q2: Evaluation frequency?
  Every session? Sampled? LLM-as-judge has its own cost.
  Suggestion: sample 20% of sessions initially, increase
  for specific failure classes.

Q3: Incident classification — manual or assisted?
  Phase 1: manual (build the taxonomy from real data).
  Phase 2: LLM-assisted classification with human confirmation.
  Phase 3: automated with confidence threshold.

Q4: When is there enough data to publish?
  Minimum: 4 weeks of continuous collection, 200+ sessions,
  50+ manually classified incidents, 30+ eval calibration
  samples. The curves need shape before the story has meaning.

Q5: Privacy / redaction for public dashboard?
  Agent sessions may contain personal data. All public-facing
  queries must aggregate (no individual session content).
  Incident descriptions must be redacted or generalised.
  Memory note content never exposed — only metadata and counts.

================================================================
REVISION HISTORY
================================================================

v0.1  2026-03-16  Initial specification. Schema, hypotheses,
                  phasing, content plan. Pre-instrumentation.
