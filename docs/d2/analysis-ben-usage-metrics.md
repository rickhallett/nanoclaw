---
title: "Analysis: Ben Usage Metrics"
category: analysis
status: active
created: 2026-03-21
---

# Analysis: Ben Usage Metrics

**Date:** 2026-03-21
**Status:** Research complete, no files modified

## 1. Context

Ben's microhal instance (microhal-ben) has been active since 2026-03-17. He is the first and most active fleet user. The question is: what quantified metrics can we track to understand how his usage evolves, and what data already exists to support them?

Ben's instance runs as a separate NanoClaw process (pm2: microhal-ben) with its own SQLite database at `/home/mrkai/code/halfleet/microhal-ben/nanoclaw/store/messages.db`. He interacts via Telegram through `@HALBen_bot`. Two senders are present: Ben (sender_id `8660755707`) and Rick (sender_id `5967394003`).

### Current data state (snapshot as of 2026-03-21)

| Metric | Value |
|--------|-------|
| Total messages | 537 |
| User messages (Ben + Rick) | 518 |
| Bot messages | 19 |
| Date range | 2026-03-17 to 2026-03-21 (4 days) |
| Container logs | 62 |
| Memory notes | 26 |
| Scheduled tasks | 2 (1 recurring cron, 1 one-shot) |
| Assessment responses | 5 (all pre-assessment, Likert) |
| pm2 log | 11,433 lines |
| API usage log | Does not exist for Ben |
| Agent session records (agentctl) | 0 (agentctl ingest not configured for fleet) |

---

## 2. Proposed Metrics

### A. Engagement

#### A1. Daily message volume (user messages)

- **Source:** `messages` table, Ben's DB
- **Capturable now:** Yes
- **Query:**
```sql
SELECT date(timestamp) AS day,
       COUNT(*) AS total,
       SUM(CASE WHEN sender = '8660755707' THEN 1 ELSE 0 END) AS ben,
       SUM(CASE WHEN sender = '5967394003' THEN 1 ELSE 0 END) AS rick
FROM messages
WHERE is_from_me = 0 AND is_bot_message = 0
GROUP BY day ORDER BY day;
```
- **Current values:** Mar 17: 12, Mar 18: 96, Mar 19: 306, Mar 20: 2, Mar 21: 102
- **Note:** The Mar 19 spike (306 messages) reflects heavy SAR-related work. Mar 20 was near-zero. Patterns are bursty, not steady.

#### A2. Session frequency (container invocations per day)

- **Source:** Container log files in `groups/telegram_main/logs/`
- **Capturable now:** Yes (file timestamps)
- **Query:** Filesystem count:
```bash
ls groups/telegram_main/logs/container-*.log | \
  sed 's/.*container-\([0-9-]*\)T.*/\1/' | sort | uniq -c
```
- **Current values:** 62 container runs across 4 days (~15.5/day average)

#### A3. Messages per session (conversation depth)

- **Source:** Requires correlating message timestamps with container log start/end times
- **Capturable now:** Partially. Container logs have Timestamp and Duration fields. Messages have timestamps. A join-by-time-window is feasible but not built.
- **Query (approximate):**
```sql
-- Requires: a sessions table populated by agentctl ingest for Ben's instance
-- Then join messages WHERE timestamp BETWEEN session.started AND session.finished
-- Currently blocked by: agentctl not configured for fleet paths
```
- **New instrumentation needed:** Run `agentctl ingest` with `log_dirs` pointing to Ben's container logs. This would populate `data/agent-sessions/` with per-session YAML records, enabling the join.

#### A4. Time-of-day distribution

- **Source:** `messages` table
- **Capturable now:** Yes
- **Query:**
```sql
SELECT strftime('%H', timestamp) AS hour, COUNT(*)
FROM messages WHERE is_from_me = 0 AND is_bot_message = 0
GROUP BY hour ORDER BY hour;
```
- **Current pattern:** Primary activity 05:00-18:00 UTC. Peak hours: 15:00 (61), 05:00 (50), 11:00 (48), 12:00 (42). Almost no activity 20:00-03:00. This suggests a morning-through-afternoon user, likely UK timezone (BST = UTC+1, so 06:00-19:00 local).

#### A5. Active days ratio

- **Source:** `messages` table
- **Capturable now:** Yes
- **Query:**
```sql
SELECT COUNT(DISTINCT date(timestamp)) AS active_days
FROM messages WHERE is_from_me = 0 AND is_bot_message = 0
  AND sender = '8660755707';
```
- **Current value:** 4 out of 4 possible days (skipping Mar 20 which had 2 messages from Rick only). Need more data before this metric is meaningful.

---

### B. Sophistication

#### B1. Average message length (chars)

- **Source:** `messages` table
- **Capturable now:** Yes
- **Query:**
```sql
SELECT date(timestamp) AS day,
       AVG(LENGTH(content)) AS avg_len,
       MAX(LENGTH(content)) AS max_len
FROM messages WHERE is_from_me = 0 AND is_bot_message = 0
GROUP BY day ORDER BY day;
```
- **Current values:** Overall avg: 511 chars, max: 4086 chars. The high average reflects that Ben sends substantive messages -- many are multi-paragraph requests involving legal correspondence, SAR documents, and detailed instructions. This is unusually high for a chat interface.

#### B2. Scheduled task adoption

- **Source:** `scheduled_tasks` table
- **Capturable now:** Yes
- **Query:**
```sql
SELECT id, schedule_type, status, created_at, last_run
FROM scheduled_tasks;
```
- **Current values:** 2 tasks created. 1 recurring cron (daily AI rules reminder, running successfully since Mar 19). 1 one-shot (headphones delivery reminder, scheduled for Mar 23). Task run logs show 3 successful executions with durations of 28-49 seconds.
- **Growth signal:** Track `COUNT(*)` from `scheduled_tasks` over time. Increasing count indicates the user is delegating proactive work to the agent.

#### B3. Memory note accumulation

- **Source:** Filesystem count in `memory/notes/`
- **Capturable now:** Yes
- **Query:**
```bash
ls memory/notes/ | wc -l
# And by date:
ls memory/notes/ | sed 's/^\([0-9]*\)-.*/\1/' | sort | uniq -c
```
- **Current value:** 26 notes. The topics span legal case management, device inventories, daily routines, media preferences, and SAR documentation. This is high density for 4 days.
- **Growth signal:** Notes created per day. A slowing rate might indicate the agent has captured the user's core context; an increasing rate indicates expanding use cases.

#### B4. Multi-turn conversation depth

- **Source:** `messages` table, gap analysis
- **Capturable now:** Partially. Define a "conversation" as messages separated by <30 minutes of silence, then count messages per conversation.
- **Query:**
```sql
-- Sessionize by 30-minute gaps
WITH ordered AS (
  SELECT timestamp,
         LAG(timestamp) OVER (ORDER BY timestamp) AS prev_ts
  FROM messages
  WHERE is_from_me = 0 AND is_bot_message = 0
),
gaps AS (
  SELECT timestamp,
         CASE WHEN (julianday(timestamp) - julianday(prev_ts)) * 86400 > 1800
              THEN 1 ELSE 0 END AS new_session
  FROM ordered
),
sessions AS (
  SELECT timestamp,
         SUM(new_session) OVER (ORDER BY timestamp) AS session_num
  FROM gaps
)
SELECT session_num, COUNT(*) AS messages_in_session
FROM sessions GROUP BY session_num ORDER BY session_num;
```
- **Interpretation:** Longer conversations suggest the user is engaging in complex multi-step tasks rather than one-shot queries. Track median conversation length over time.

#### B5. Content complexity indicator

- **Source:** `messages` table, content analysis
- **Capturable now:** Partially (requires text analysis, not pure SQL)
- **Proxy metrics available now:**
  - Messages containing URLs (forwarded emails, links)
  - Messages > 1000 chars (detailed instructions)
  - Messages containing structured data (file paths, email headers)
- **Query:**
```sql
SELECT date(timestamp) AS day,
       SUM(CASE WHEN LENGTH(content) > 1000 THEN 1 ELSE 0 END) AS long_msgs,
       SUM(CASE WHEN content LIKE '%http%' THEN 1 ELSE 0 END) AS url_msgs
FROM messages WHERE is_from_me = 0 AND is_bot_message = 0
GROUP BY day ORDER BY day;
```

---

### C. Quality Signals

#### C1. Container success rate

- **Source:** Container log files (Exit Code field)
- **Capturable now:** Yes (parse logs)
- **Query:**
```bash
grep -h "^Exit Code:" groups/telegram_main/logs/container-*.log | sort | uniq -c
```
- **Current observation:** The sample logs show exit codes of 0 (success) and 137 (SIGKILL/OOM, likely timeout). A 137 with "Had Streaming Output: true" is counted as success by agentctl.

#### C2. Container duration distribution

- **Source:** Container log files (Duration field)
- **Capturable now:** Yes
- **Query:**
```bash
grep -h "^Duration:" groups/telegram_main/logs/container-*.log | \
  sed 's/Duration: //' | sed 's/ms//'
```
- **Current observation:** Durations range from ~28 seconds (scheduled task) to ~5,509 seconds (long interactive session). The distribution indicates two modes: short automated tasks and long interactive conversations.
- **Growth signal:** If median duration increases over time, the user is engaging in longer, more complex interactions.

#### C3. Session clears (problem indicator)

- **Source:** hlog events (JSON lines from halos modules)
- **Capturable now:** Yes, if HALOS_LOG_FILE is configured for Ben's instance. The `halctl session clear` command emits an hlog entry with event `session_clear`.
- **Query:**
```bash
grep '"event":"session_clear"' "$HALOS_LOG_FILE" | \
  jq -r 'select(.data.instance == "ben")'
```
- **Alternative:** Check the `sessions` table. A changed `session_id` between observations indicates a session clear occurred. Currently: 1 session (`7b7e6955-e95e-4d21-ae98-2aeb39bfb73d`).
- **New instrumentation needed:** Snapshot session IDs periodically to detect changes.

#### C4. Response latency (message-to-container-start)

- **Source:** Correlation between message timestamps and container log timestamps
- **Capturable now:** Partially. The NanoClaw polling interval determines the baseline delay. Container start time minus the triggering message's timestamp gives perceived latency.
- **New instrumentation needed:** The current data model does not link a specific container run to a specific triggering message. This mapping would require either:
  1. Adding `triggering_message_id` to container logs, or
  2. Inferring the link by finding the last user message before each container start timestamp.

#### C5. Error rate from pm2 logs

- **Source:** `~/.pm2/logs/microhal-ben-error.log` (52KB, non-trivial)
- **Capturable now:** Yes
- **Query:**
```bash
wc -l ~/.pm2/logs/microhal-ben-error.log
# Errors per day:
grep -oP '\d{4}-\d{2}-\d{2}' ~/.pm2/logs/microhal-ben-error.log | sort | uniq -c
```

---

### D. Growth Trajectory

#### D1. Week-over-week message volume

- **Source:** `messages` table
- **Capturable now:** Yes (need 2+ weeks of data; currently only 4 days)
- **Query:**
```sql
SELECT strftime('%Y-W%W', timestamp) AS week, COUNT(*) AS msgs
FROM messages WHERE is_from_me = 0 AND is_bot_message = 0
GROUP BY week ORDER BY week;
```
- **Minimum data:** 3 weeks before trends are meaningful.

#### D2. New capability adoption timeline

- **Source:** Composite of multiple tables
- **Capturable now:** Yes
- **Milestones to track:**
  - First message (Mar 17) -- initial contact
  - Onboarding completed (Mar 18) -- waiver accepted
  - First assessment (Mar 18) -- pre-assessment Likert
  - First scheduled task created (Mar 18) -- delegation begins
  - First memory note created (Mar 17, smoke test; first real note Mar 18)
  - First multi-thousand-char message (Mar 19) -- using agent for complex drafting
  - First cron task execution (Mar 19) -- automated proactive contact
- **Growth signal:** Time between capability milestones. A user who discovers scheduling on day 1 vs day 30 tells you something about adoption velocity.

#### D3. Assessment score evolution

- **Source:** `assessments` table
- **Capturable now:** Yes, but only pre-assessment data exists
- **Current baseline (Ben, pre-assessment):**
  - ai_comfort: 5/5 (high)
  - ai_trust: 2/5 (low)
  - ai_frequency: 5/5 (high)
  - ai_evaluation: 2/5 (low confidence in evaluating AI output)
  - ai_attitude: 5/5 (positive)
- **Growth signal:** Run post-assessment at defined intervals (e.g., 2 weeks, 1 month). Delta between pre and post scores is the direct measurement of attitude change.
- **Observation:** The asymmetry is striking -- high comfort and frequency, but low trust and evaluation confidence. This is a user who uses AI a lot but does not fully trust it. Watching these two dimensions converge or diverge is the single most interesting metric.

#### D4. Cost trajectory

- **Source:** API usage log (does not exist for Ben's instance) or container log durations as proxy
- **Capturable now:** Partially (duration only, no token counts)
- **New instrumentation needed:** Enable the credential proxy's `api-usage.jsonl` for Ben's instance, or configure `agentctl ingest` to parse Ben's container logs and enrich with usage data.

---

## 3. Instrumentation Gaps

| Gap | Impact | Effort to close |
|-----|--------|-----------------|
| **agentctl not configured for fleet** | Cannot compute per-session token costs, success rates, or spin detection for Ben | ~5 agent-minutes. Add fleet-aware config to agentctl or run with `--config` pointing to Ben's paths |
| **No api-usage.jsonl for Ben** | Cannot compute actual cost per session | ~10 agent-minutes. Ensure Ben's credential proxy writes to the JSONL. May require container-runner config change |
| **No triggering-message linkage** | Cannot measure true response latency | ~15 agent-minutes. Add message ID to container log header in container-runner |
| **No periodic assessment runner** | Cannot track attitude change longitudinally | ~10 agent-minutes. Add a scheduled assessment trigger (e.g., every 2 weeks) to the eval harness |
| **BATHW ClickHouse not deployed** | The telemetry schema exists but the pipeline is not ingesting. All telemetry goes to stderr only | Variable. The schema is ready; deployment is the blocker |
| **hlog not configured for Ben's instance** | Session clears and other halctl events may not be captured | ~2 agent-minutes. Set HALOS_LOG_FILE in Ben's pm2 ecosystem config |

---

## 4. Recommended Dashboard (priority order)

If building a Ben usage dashboard, instrument these first:

1. **Daily message volume by sender** (A1) -- already capturable, no work needed
2. **Assessment score deltas** (D3) -- highest signal, needs periodic re-assessment
3. **Container success rate** (C1) -- already capturable via log parsing
4. **Memory note growth** (B3) -- filesystem count, trivial
5. **Scheduled task count** (B2) -- already in DB
6. **Session duration distribution** (C2) -- already in container logs
7. **Message length trend** (B1) -- already in DB, proxy for sophistication
8. **Time-of-day heatmap** (A4) -- already capturable, useful for understanding habits

Items 1-8 require zero new instrumentation. They can be built today from existing data.

---

## 5. Open Questions

1. **What is the target audience for these metrics?** If Rick (operator), a CLI report via `reportctl` suffices. If Ben himself, the metrics need to be presented differently (a weekly Telegram digest, perhaps).

2. **What constitutes "good" for each metric?** Without a comparison cohort, we are measuring change, not quality. The pre-assessment baseline is the anchor.

3. **Should Ben's message content be included in reports?** Some messages contain sensitive legal correspondence. Any metric that surfaces content (not just counts) needs to respect this.

4. **When should post-assessment run?** The eval harness exists. The question is timing -- too early and you measure novelty, too late and you miss the adoption curve.

5. **Fleet-wide agentctl:** Should agentctl be extended with a `--instance` flag (like halctl and logctl already have), or should each instance run its own agentctl ingest? The former is cleaner.
