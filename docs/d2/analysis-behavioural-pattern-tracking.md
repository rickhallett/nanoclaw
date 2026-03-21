# Behavioural Pattern Tracking: Schema & Lookup Design

## 1. Context

The halos ecosystem currently tracks *what happened* (memctl notes, nightctl jobs, logctl events, agentctl sessions) but not *what it means over time*. There is no mechanism for observing that Rick tends to deep-work on Tuesdays, goes quiet on Sundays, or that productivity drops after 3+ days without exercise.

The goal: a structured system that ingests behavioural observations at conversational frequency, stores them efficiently, and enables temporal queries across daily, weekly, and monthly horizons.

### Existing Infrastructure Assessment

**memctl** — Markdown notes with YAML frontmatter. Good for atomic insights, decisions, facts. Bad for time-series data: no numeric fields, no temporal indexing, pruning via half-life scoring would destroy exactly the old data that makes long-horizon patterns visible. The 30-day half-life is the opposite of what behavioural tracking needs.

**reportctl/briefings** — Already gathers cross-module data and synthesises it through Claude. This is the natural *consumer* of pattern data, not the store.

**messages.db** — SQLite, better-sqlite3 on the Node side. Contains chat messages, sessions, tasks. Schema is message-centric, not observation-centric. Adding behavioural tracking here would conflate communication plumbing with analytical data.

**hlog** — Append-only JSON lines. High volume, no indexing, no aggregation. Useful as a raw event source but not queryable at pattern scale.

**reflections/** — HAL's journal. Unstructured markdown. Valuable as narrative context but not machine-queryable for patterns.

### Constraints

- Python CLI ecosystem (halos modules installed via `uv sync`)
- SQLite is the established data store pattern (messages.db)
- Agent writes observations during conversation; agent queries patterns during conversation
- Must not break memctl governance (pruning, scoring, index integrity)
- Data grows linearly with conversation frequency — needs pruning/rollup strategy

---

## 2. Options

### A. Extend memctl with an `observation` note type

Add `observation` to `valid_types`. Use tags like `energy`, `productivity`, `mood`. Body contains structured YAML in the markdown body.

**What it looks like:** `memctl new --type observation --tags energy,wellbeing --body "energy_level: 7\nproductivity: high\ncontext: deep work session on weaver"`

**Cost:** Zero new infrastructure. ~10 agent-minutes to add type + tags.

**Enables:** Immediate use with existing search, graph, enrichment.

**Prevents/Makes Harder:**
- Temporal queries. `memctl search --tags energy --since 30d` doesn't exist. You'd need to post-filter by date from the index YAML, which means loading all observations into memory.
- Numeric aggregation. "Average energy this week" requires parsing markdown bodies.
- Volume. At 3-5 observations/day, you'd add ~100-150 notes/month. The index (already a single YAML block in INDEX.md) would bloat. Pruning would fight pattern retention.
- The half-life scoring model actively penalises old observations, which is the inverse of what this system needs.

### B. Purpose-built SQLite database (`store/patterns.db`)

A new database with a schema designed for time-series behavioural observations, pre-computed aggregations, and temporal queries.

**What it looks like:** New halos module (`patternctl` or `trackctl`) with its own SQLite database, CLI, and collector for reportctl/briefings integration.

**Cost:** ~45 agent-minutes implementation + ~30 human-minutes review. New module, new config, new database file.

**Enables:**
- Native temporal queries with SQL (WHERE observed_at BETWEEN ... GROUP BY strftime)
- Numeric fields with proper types (energy INTEGER, not "energy_level: 7" in markdown)
- Aggregation tables for weekly/monthly rollups without re-scanning raw data
- Efficient pruning: archive raw observations after rollup, keep aggregates forever
- Clean separation: observations are not episodic memory

**Prevents/Makes Harder:**
- No automatic graph/backlink integration with memctl notes
- Another database to back up
- Another module to maintain

### C. Hybrid: SQLite for observations, memctl for insights

SQLite stores the raw time-series data. When patterns crystallise into actionable insights, those get promoted to memctl notes (type `fact` or `decision`) with a backlink to the pattern data.

**What it looks like:** `trackctl` writes observations to `store/patterns.db`. Aggregation jobs produce weekly/monthly summaries. When a pattern is significant enough to inform decision-making, it becomes a memctl note: "Rick's productivity peaks Tuesday-Wednesday; schedule deep work accordingly."

**Cost:** Same as B, plus the promotion pipeline (~10 additional agent-minutes).

**Enables:** Everything in B, plus episodic memory integration. The memctl graph shows *why* a decision was made ("linked to weekly pattern analysis showing consistent Tuesday peaks").

**Prevents/Makes Harder:** Marginally more complexity in the promotion step, but this is a feature, not a cost — it forces the system to distinguish signal from noise.

---

## 3. Tradeoffs

| Criterion                    | A: Extend memctl    | B: SQLite-only       | C: Hybrid            |
|------------------------------|----------------------|----------------------|----------------------|
| Implementation effort        | Minimal              | Moderate             | Moderate+            |
| Temporal query performance   | Poor                 | Excellent            | Excellent            |
| Numeric aggregation          | Manual parsing       | Native SQL           | Native SQL           |
| Volume tolerance (1yr)       | ~1500 notes in index | Millions of rows     | Millions of rows     |
| Pruning compatibility        | Fights half-life     | Independent strategy | Independent strategy |
| memctl graph integration     | Free                 | None                 | Via promotion        |
| Briefings integration        | Custom collector     | reportctl collector  | reportctl collector  |
| Separation of concerns       | Violated             | Clean                | Clean                |
| Insight durability           | Notes persist        | Data only            | Both layers          |

---

## 4. Recommendation

**Option C: Hybrid.** The data has two distinct lifecycles that map cleanly to two storage strategies:

1. **High-frequency observations** (3-10/day) need time-series storage with aggregation and pruning. SQLite.
2. **Crystallised insights** ("this pattern means X for how you work") need episodic memory with backlinks and narrative context. memctl.

Forcing both through memctl would be like storing temperature readings as Post-it notes — technically possible, miserable in practice.

---

## 5. Schema Design

### 5.1 Database: `store/patterns.db`

#### Table: `observations`

The atomic unit. One row per behavioural observation.

```sql
CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at TEXT NOT NULL,          -- ISO 8601, UTC
    source TEXT NOT NULL DEFAULT 'conversation',  -- conversation | briefing | cron | manual
    dimension TEXT NOT NULL,            -- energy | productivity | mood | focus | exercise | sleep | social
    value INTEGER,                      -- numeric score 1-10 (nullable for non-numeric)
    label TEXT,                         -- qualitative: high/medium/low, or free text
    context TEXT,                       -- what was happening (project, activity, location)
    confidence TEXT NOT NULL DEFAULT 'inferred',  -- stated | inferred | observed
    raw_signal TEXT,                    -- the conversational fragment that triggered this observation
    session_id TEXT                     -- links to agentctl session if applicable
);

CREATE INDEX idx_obs_dimension_time ON observations(dimension, observed_at);
CREATE INDEX idx_obs_time ON observations(observed_at);
CREATE INDEX idx_obs_source ON observations(source);
```

**Design rationale:**
- `dimension` is the behavioural axis. Controlled vocabulary, not free tags.
- `value` + `label` — some dimensions are naturally numeric (energy 1-10), others qualitative (mood: "restless"). Both are first-class.
- `confidence` distinguishes "I feel like a 7 today" (stated) from the agent inferring energy from message cadence (inferred) from observable facts like "completed 5 tasks" (observed).
- `raw_signal` is the provenance chain — what conversational evidence prompted this observation.

#### Table: `aggregates`

Pre-computed rollups. Never queried in real-time; populated by a scheduled aggregation job.

```sql
CREATE TABLE aggregates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period TEXT NOT NULL,               -- day | week | month
    period_start TEXT NOT NULL,         -- ISO 8601 date (YYYY-MM-DD or YYYY-Www or YYYY-MM)
    dimension TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    avg_value REAL,                     -- mean of numeric observations
    min_value INTEGER,
    max_value INTEGER,
    stddev_value REAL,                  -- standard deviation (variance signal)
    mode_label TEXT,                    -- most frequent qualitative label
    label_distribution TEXT,            -- JSON: {"high": 3, "medium": 5, "low": 1}
    narrative TEXT,                     -- agent-generated summary of this period+dimension
    computed_at TEXT NOT NULL,

    UNIQUE(period, period_start, dimension)
);

CREATE INDEX idx_agg_lookup ON aggregates(dimension, period, period_start);
```

**Design rationale:**
- `UNIQUE(period, period_start, dimension)` makes aggregation idempotent — re-running overwrites, doesn't duplicate.
- `narrative` is the synthesis output: "Energy averaged 6.2 this week, dipping to 4 on Thursday after the late-night debugging session." Generated by Claude during aggregation.
- `stddev_value` — variance matters more than mean for pattern detection. Consistent 6s vs. volatile 3-9 swings tell different stories.

#### Table: `patterns`

Detected recurring patterns. The analytical layer.

```sql
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TEXT NOT NULL,
    pattern_type TEXT NOT NULL,         -- cycle | trend | correlation | anomaly
    dimensions TEXT NOT NULL,           -- JSON array: ["energy", "productivity"]
    resolution TEXT NOT NULL,           -- daily | weekly | monthly
    description TEXT NOT NULL,          -- human-readable pattern description
    evidence TEXT NOT NULL,             -- JSON: references to aggregates/observations that support this
    strength REAL NOT NULL,             -- 0.0-1.0 confidence in the pattern
    first_seen TEXT NOT NULL,           -- when this pattern was first detected
    last_confirmed TEXT NOT NULL,       -- when it was last still true
    times_confirmed INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',  -- active | weakening | expired | promoted
    memctl_note_id TEXT,               -- set when promoted to episodic memory

    UNIQUE(pattern_type, dimensions, resolution, description)
);

CREATE INDEX idx_patterns_status ON patterns(status, strength);
CREATE INDEX idx_patterns_dims ON patterns(dimensions);
```

**Design rationale:**
- `strength` increases with `times_confirmed`. A pattern detected once is speculative; detected across 8 weeks is structural.
- `status` lifecycle: `active` -> `weakening` (contradicted by recent data) -> `expired`. Or `active` -> `promoted` (written to memctl as durable insight).
- `memctl_note_id` is the bridge to the episodic memory system.
- The UNIQUE constraint on type+dims+resolution+description prevents duplicate pattern entries. When re-detected, `last_confirmed` and `times_confirmed` are updated.

#### Table: `dimension_config`

Controlled vocabulary for dimensions. Avoids schema drift.

```sql
CREATE TABLE dimension_config (
    name TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    value_type TEXT NOT NULL,           -- numeric | qualitative | both
    value_range_min INTEGER,            -- for numeric: valid range
    value_range_max INTEGER,
    valid_labels TEXT,                  -- JSON array of valid qualitative labels
    description TEXT
);

-- Seed data
INSERT INTO dimension_config VALUES
    ('energy', 'Energy Level', 'numeric', 1, 10, NULL, 'Physical and mental energy'),
    ('productivity', 'Productivity', 'both', 1, 10, '["high","medium","low","blocked"]', 'Work output and effectiveness'),
    ('mood', 'Mood', 'qualitative', NULL, NULL, '["positive","neutral","restless","frustrated","calm","anxious"]', 'General emotional state'),
    ('focus', 'Focus', 'both', 1, 10, '["deep","shallow","scattered","flow"]', 'Concentration quality'),
    ('exercise', 'Exercise', 'qualitative', NULL, NULL, '["none","light","moderate","intense"]', 'Physical activity'),
    ('sleep', 'Sleep Quality', 'both', 1, 10, '["good","ok","poor","terrible"]', 'Previous night sleep'),
    ('social', 'Social Contact', 'qualitative', NULL, NULL, '["isolated","light","moderate","heavy"]', 'Human interaction level');
```

### 5.2 Temporal Aggregation Strategy

Three-tier rollup, driven by a cron job (via `cronctl`):

**Daily (runs at 2300 UTC):**
```sql
-- For each dimension with observations today:
INSERT OR REPLACE INTO aggregates (period, period_start, dimension, count, avg_value, min_value, max_value, stddev_value, mode_label, label_distribution, computed_at)
SELECT
    'day',
    date(observed_at) as d,
    dimension,
    count(*),
    avg(value),
    min(value),
    max(value),
    -- SQLite doesn't have native stddev, compute in Python
    NULL,
    NULL, -- mode_label computed in Python
    NULL, -- label_distribution computed in Python
    strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
FROM observations
WHERE date(observed_at) = date('now')
GROUP BY dimension;
```

The Python aggregation code computes stddev, mode, and label distribution, then generates the narrative via Claude (or a template fallback).

**Weekly (runs Sunday 2330 UTC):**
Aggregates from daily aggregates, not raw observations. Computes week-over-week deltas.

**Monthly (runs 1st of month, 0030 UTC):**
Aggregates from weekly aggregates. This is where cross-dimension correlations are analysed: "Weeks with 3+ exercise sessions correlate with productivity scores 1.5 points higher."

**Pattern detection (runs with weekly aggregation):**
Compare the current week's aggregates against the trailing 4/8/12 week baseline. Flag:
- **Cycles**: Does energy follow a weekly pattern? (Compare day-of-week averages)
- **Trends**: Is productivity trending up/down over 4+ weeks?
- **Correlations**: Do two dimensions move together? (Pearson on weekly averages)
- **Anomalies**: Is this week > 2 stddev from the trailing mean?

### 5.3 Agent Interaction Model

#### Writing Observations

The agent writes observations during conversation via a CLI tool:

```bash
# Explicit statement from user: "I'm at like a 6 today energy-wise"
trackctl observe --dimension energy --value 6 --confidence stated \
    --context "morning check-in" --signal "I'm at like a 6 today energy-wise"

# Agent inference from conversational tone
trackctl observe --dimension focus --label scattered --confidence inferred \
    --context "debugging container-runner" --signal "multiple topic switches in 5 messages"

# Observable fact
trackctl observe --dimension exercise --label intense --confidence observed \
    --context "mentioned gym session" --signal "just got back from the gym"
```

This is a Bash tool call from inside the agent container — same pattern as `memctl new`.

#### Querying Patterns

```bash
# What does this week look like?
trackctl week                           # current week summary across all dimensions

# How does energy trend?
trackctl trend --dimension energy --weeks 8

# What patterns are active?
trackctl patterns --status active

# Cross-dimension query
trackctl correlate --dimensions energy,productivity --weeks 12

# Day-of-week analysis
trackctl rhythm --dimension productivity  # shows Mon-Sun averages over trailing 8 weeks

# Raw observations for context
trackctl observations --dimension mood --days 7
```

Output format: structured text by default, `--json` for programmatic use. Same convention as every other halos module.

#### Briefings Integration

New reportctl collector: `collect_patterns(patterns_db_path)` reads active patterns and recent aggregates. The briefings `gather.py` includes this in `BriefingData`. Morning briefing might include:

> Energy trending down over 3 weeks (7.2 -> 6.1 -> 5.4). Exercise frequency also down. These have correlated at r=0.72 over the past 8 weeks.

#### Promotion to memctl

When a pattern's `strength` exceeds a threshold (e.g., 0.8) and `times_confirmed` >= 4:

```bash
trackctl promote --pattern-id 7
# Creates: memctl new --type fact --tags wellbeing,pattern \
#   --body "Consistent pattern: energy correlates with exercise frequency (r=0.72, confirmed 8 weeks). ..."
# Updates: patterns.status = 'promoted', patterns.memctl_note_id = '<new note id>'
```

### 5.4 Pruning / Archival Strategy

| Data tier         | Retention        | Rationale                                                |
|-------------------|------------------|----------------------------------------------------------|
| Raw observations  | 90 days          | After daily aggregation, individual data points add little |
| Daily aggregates  | 1 year           | Weekly rollups preserve the signal; daily detail fades    |
| Weekly aggregates | Indefinite       | This is the core analytical resolution                   |
| Monthly aggregates| Indefinite       | Structural context, tiny volume                          |
| Active patterns   | Until expired     | Expired patterns archived after 6 months                 |
| Promoted patterns | memctl governs   | Once in episodic memory, memctl lifecycle applies         |

Pruning runs as a cron job:

```bash
# Archive raw observations older than 90 days (that have been aggregated)
trackctl prune --observations --older-than 90d

# Archive daily aggregates older than 1 year
trackctl prune --daily --older-than 365d

# Expire patterns not confirmed in 8 weeks
trackctl prune --patterns --stale 8w
```

Archived data goes to `store/patterns-archive.db` (or a dated SQLite file) rather than being deleted. Storage is cheap; losing historical data is not reversible.

### 5.5 Module Structure

```
halos/trackctl/
    __init__.py
    cli.py          # trackctl command: observe, week, trend, patterns, correlate, rhythm, prune, promote
    config.py       # Config dataclass, YAML loader
    db.py           # SQLite schema creation, migrations, query helpers
    aggregation.py  # Daily/weekly/monthly rollup logic
    detection.py    # Pattern detection algorithms (cycles, trends, correlations, anomalies)
    collector.py    # reportctl-compatible collector for briefings integration
```

Config file: `trackctl.yaml`

```yaml
database: ./store/patterns.db
archive_database: ./store/patterns-archive.db

observation:
  max_per_day: 20              # sanity limit
  dimensions:                  # override dimension_config defaults if needed
    - energy
    - productivity
    - mood
    - focus
    - exercise
    - sleep
    - social

aggregation:
  daily_at: "23:00"            # UTC
  weekly_on: "sunday"
  monthly_on: 1
  narrative_model: "sonnet"    # model for narrative generation
  narrative_max_tokens: 300

detection:
  min_weeks_for_trend: 4
  min_weeks_for_cycle: 6
  correlation_threshold: 0.6   # Pearson r
  anomaly_stddev: 2.0
  promotion_strength: 0.8
  promotion_confirmations: 4

prune:
  observation_retention_days: 90
  daily_aggregate_retention_days: 365
  pattern_stale_weeks: 8
```

---

## 6. Open Questions

1. **Observation frequency in practice.** The schema supports 3-10/day. But how aggressively should the agent infer observations vs. only recording explicit statements? Over-inference risks noise; under-inference misses the slow signals. This probably needs a tuning period with the `confidence` field as the dial.

2. **Narrative generation cost.** Weekly aggregation generates narratives via Claude. At ~7 dimensions * 4 weeks/month, that's ~28 synthesis calls/month. Trivial cost, but the aggregation job needs timeout/fallback handling (the briefings module already solved this pattern).

3. **Cross-user applicability.** This design assumes a single user (Rick). If fleet instances need behavioural tracking for their users, the schema needs a `user_id` column. Easy migration, but worth deciding now vs. later.

4. **Bootstrap period.** Pattern detection needs 4-8 weeks of data before it can say anything meaningful. The system will feel inert initially. The agent should set expectations: "I've started tracking. Ask me again in a month."

5. **Privacy boundary.** Some dimensions (mood, social) are sensitive. Should `raw_signal` (the conversational fragment) be stored, or only the derived observation? Storing it provides provenance but creates a queryable log of emotional states tied to timestamps.

6. **Integration with existing reflections.** HAL's diary entries in `memory/reflections/` sometimes contain implicit pattern observations. Should there be a one-time or periodic extraction pass that seeds `observations` from historical reflections?
