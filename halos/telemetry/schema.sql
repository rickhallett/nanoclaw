-- BATHW ClickHouse schema v0.1
-- Run: clickhouse-client < halos/telemetry/schema.sql

CREATE DATABASE IF NOT EXISTS bathw;

-- Raw event catch-all (cronctl, todoctl, briefings, etc)
CREATE TABLE IF NOT EXISTS bathw.raw_events
(
    ts          DateTime64(3),
    source      String,
    event       String,
    data        String  -- JSON blob
)
ENGINE = MergeTree
ORDER BY (ts, source, event);

-- Agent sessions (agentctl)
CREATE TABLE IF NOT EXISTS bathw.agent_sessions
(
    session_id          String,
    started_at          DateTime64(3),
    ended_at            Nullable(DateTime64(3)),
    duration_ms         UInt64,
    group_name          String,
    channel             String,
    trigger_type        String,
    model               String,
    input_tokens        UInt32,
    output_tokens       UInt32,
    cache_read_tokens   UInt32,
    cache_write_tokens  UInt32,
    total_cost_usd      Float64,
    tool_calls          UInt16,
    turns               UInt16,
    outcome             Enum8('success' = 1, 'partial' = 2, 'failure' = 3, 'timeout' = 4, 'cancelled' = 5),
    intervention        Bool,
    intervention_type   Nullable(String),
    error_class         Nullable(String)
)
ENGINE = MergeTree
ORDER BY (started_at, group_name);

-- Tool usage per session
CREATE TABLE IF NOT EXISTS bathw.tool_usage
(
    session_id      String,
    tool_name       String,
    invocation_idx  UInt16,
    started_at      DateTime64(3),
    duration_ms     UInt32,
    success         Bool,
    error_message   Nullable(String),
    input_tokens    UInt32,
    output_tokens   UInt32
)
ENGINE = MergeTree
ORDER BY (started_at, tool_name);

-- Memory governance events
CREATE TABLE IF NOT EXISTS bathw.memory_events
(
    event_id        String,
    ts              DateTime64(3),
    event_type      Enum8(
        'note_created' = 1,
        'note_pruned' = 2,
        'note_archived' = 3,
        'backlink_added' = 4,
        'index_rebuilt' = 5,
        'search_performed' = 6,
        'enrich_proposed' = 7,
        'enrich_accepted' = 8
    ),
    note_id         Nullable(String),
    note_type       Nullable(String),
    tags            Array(String),
    entities        Array(String),
    corpus_size     UInt32,
    search_query    Nullable(String),
    search_results  UInt16
)
ENGINE = MergeTree
ORDER BY (ts, event_type);

-- Evaluation scores
CREATE TABLE IF NOT EXISTS bathw.eval_scores
(
    eval_id             String,
    session_id          String,
    ts                  DateTime64(3),
    eval_type           Enum8(
        'quality' = 1,
        'relevance' = 2,
        'safety' = 3,
        'cost_efficiency' = 4,
        'task_completion' = 5,
        'instruction_adherence' = 6
    ),
    score               Float32,
    judge_model         String,
    judge_prompt_hash   String,
    reasoning           String,
    human_override      Nullable(Float32)
)
ENGINE = MergeTree
ORDER BY (ts, eval_type);

-- Classified incidents
CREATE TABLE IF NOT EXISTS bathw.incidents
(
    incident_id         String,
    ts                  DateTime64(3),
    session_id          Nullable(String),
    severity            Enum8('info' = 1, 'warning' = 2, 'error' = 3, 'critical' = 4),
    failure_class       String,
    title               String,
    description         String,
    root_cause          String,
    resolution          String,
    time_to_resolve_m   UInt32,
    recurrence_count    UInt16,
    tags                Array(String)
)
ENGINE = MergeTree
ORDER BY (ts, failure_class);

-- Daily cost aggregates (materialized)
CREATE TABLE IF NOT EXISTS bathw.daily_costs
(
    date                    Date,
    group_name              String,
    channel                 String,
    session_count           UInt16,
    total_input_tokens      UInt64,
    total_output_tokens     UInt64,
    total_cost_usd          Float64,
    avg_cost_per_session    Float64,
    avg_tokens_per_session  UInt32
)
ENGINE = SummingMergeTree
ORDER BY (date, group_name, channel);

-- Memory scaling snapshots (daily)
CREATE TABLE IF NOT EXISTS bathw.memory_snapshots
(
    snapshot_date   Date,
    corpus_size     UInt32,
    decision_count  UInt16,
    fact_count      UInt16,
    reference_count UInt16,
    backlink_count  UInt32,
    avg_backlinks   Float32,
    orphan_count    UInt16,
    prune_candidates UInt16,
    index_size_bytes UInt32,
    rebuild_time_ms UInt32,
    search_avg_ms   Float32
)
ENGINE = MergeTree
ORDER BY snapshot_date;
