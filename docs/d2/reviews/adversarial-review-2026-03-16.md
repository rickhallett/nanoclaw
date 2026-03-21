---
title: "Adversarial Code Review — 2026-03-16"
category: reference
status: active
created: 2026-03-16
---

# Adversarial Code Review — 2026-03-16

5 independent reviewers, one per target. 91 total findings.

## Triage Summary

| Severity | memctl | logctl | reportctl | agentctl | cronctl+todoctl | Total |
|----------|--------|--------|-----------|----------|-----------------|-------|
| CRITICAL | 3 | 1 | 0 | 0 | 0 | 4 |
| HIGH | 6 | 4 | 5 | 5 | 9 | 29 |
| MEDIUM | 5 | 5 | 5 | 6 | 8 | 29 |
| LOW | 6 | 6 | 6 | 6 | 5 | 29 |
| **Total** | **20** | **16** | **16** | **17** | **22** | **91** |

## CRITICAL (fix now — data loss or corruption)

| # | Module | Finding | Root Cause |
|---|--------|---------|------------|
| C1 | memctl | now_id() TOCTOU race — two processes can overwrite each other | File existence check is not atomic with write |
| C2 | memctl | Crash between note write and index write creates orphan | Two-step non-transactional write |
| C3 | memctl | _atomic_write leaves .tmp on crash before os.replace | No cleanup of partial temp files |
| C4 | logctl | read_log_file loads entire file into memory — OOM on large logs | No streaming/lazy read |

## HIGH (fix soon — silent wrong behaviour)

**Cross-cutting (affects multiple modules):**

| # | Modules | Finding |
|---|---------|---------|
| H1 | todoctl, cronctl | Non-atomic writes (memctl solved this, siblings didn't copy) |
| H2 | todoctl, cronctl | No validation on load — corrupt YAML accepted silently |
| H3 | todoctl | ID collision on rapid creation (second-precision, no ms) |
| H4 | cronctl | ID collision by design (slugify-only, no uniqueness guard) |
| H5 | cronctl | Crontab % not escaped (cron interprets % as newline) |
| H6 | cronctl | Schedule regex rejects valid cron expressions (MON-FRI, ranges) |

**Per-module:**

| # | Module | Finding |
|---|--------|---------|
| H7 | memctl | No schema enforcement on unknown frontmatter fields |
| H8 | memctl | marshal() always emits expires: null |
| H9 | memctl | Config values not type-validated (bool is subclass of int) |
| H10 | memctl | hash_file reads file twice in rebuild (TOCTOU between parse and hash) |
| H11 | memctl | _add_backlink index match uses OR when it should use AND |
| H12 | memctl | Uniqueness test is tautological (asserts len >= 1) |
| H13 | logctl | matches_since silently includes entries it can't filter |
| H14 | logctl | HH:MM:SS timestamps wrong for multi-day windows |
| H15 | logctl | cmd_errors misses fatal-level entries |
| H16 | logctl | parse_halos_structured accepts any YAML with "event" key |
| H17 | reportctl | collect_nightctl checks "status" but executor writes "outcome" |
| H18 | reportctl | Naive timezone comparison crashes on naive datetime |
| H19 | reportctl | notes_created heuristic conflates modification with creation |
| H20 | reportctl | _id_after relies on implicit UTC assumption |
| H21 | reportctl | collect_activity counts by creation date, misses old completions |
| H22 | agentctl | Normal logs missing Container field — inconsistent session IDs |
| H23 | agentctl | TIMEOUT detection too loose — string match in first line |
| H24 | agentctl | "Had Streaming Output" ignored — idle cleanup = false alarm |
| H25 | agentctl | Unguarded int() on duration/exit_code — crashes on malformed |
| H26 | todoctl | No archive command — done items accumulate forever |
| H27 | todoctl | No edit/update command |
| H28 | cronctl | Crontab cd path not quoted (breaks on spaces) |
| H29 | cronctl | Crontab install write not atomic |

## Patterns Observed

**1. memctl's defensive fixes didn't propagate.** Atomic writes, millisecond IDs, collision guards — all solved in memctl, absent from todoctl and cronctl. The standing order was recorded but the code wasn't audited against it.

**2. No validation on load.** Every module validates on *create* but trusts files on *read*. An LLM hand-editing a YAML file (which the instructions say not to do, but they will) can inject any data.

**3. No CLI integration tests.** All modules test the model layer. None test the CLI layer where the integration logic lives (atomic coordination, argument parsing, output formatting).

**4. reportctl's cross-module coupling is fragile.** Field name mismatch (status vs outcome) would be caught by an integration test but wasn't. Fixtures don't match real data formats.

**5. Time handling is inconsistent.** Some modules use UTC, some assume local, some don't handle timezone-aware vs naive comparison. No shared utility.

## Recommended Fix Order

1. **Atomic writes for todoctl + cronctl** (H1) — copy memctl's pattern, 30 min
2. **Millisecond IDs for todoctl** (H3) — copy memctl's now_id(), 5 min
3. **ID collision guard for cronctl** (H4) — check exists before write, 5 min
4. **reportctl status vs outcome** (H17) — one-line fix, 1 min
5. **logctl streaming read** (C4) — replace read_text with line iterator, 30 min
6. **Crontab % escaping** (H5) — one-line fix, 1 min
7. **Validation on load for todoctl + cronctl** (H2) — add validate() calls, 20 min
8. **agentctl int() guards** (H25) — try/except ValueError, 5 min
9. **agentctl Had Streaming Output** (H24) — parse field, adjust status, 15 min
10. **memctl TOCTOU** (C1) — append random suffix to ID, 5 min (already done with ms, but needs random component for true safety)
