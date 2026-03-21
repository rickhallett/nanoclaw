---
title: "Eval Baseline — 2026-03-18"
category: reference
status: active
created: 2026-03-18
---

# Eval Baseline — 2026-03-18

> First comprehensive eval run across personality profiles. Establishes pass rates before test pilot launch.

## Results

| Instance | Personality | Pass Rate | Notes |
|----------|-------------|-----------|-------|
| money | default | 8/8 | Full pass. Baseline reference. |
| dad | dad (terse, opinionated) | 5/8 | Personality-driven failures — see below. |
| mum | mum (warm, minimal) | 1/1 (likert_delivery only) | Single scenario confirmed. Full suite pending. |

## Scenario Breakdown — Dad (The Captain)

| Scenario | Result | Detail |
|----------|--------|--------|
| likert_delivery | PASS | "Welcome. Good to have you. I'm HAL." Terse, no fuss. |
| qualitative_not_too_early | FAIL | Asked qualitative at conv_count=1. Should hold until 3+. |
| qualitative_dropin_eligible | PASS | Correctly held off. |
| no_interrupt_during_task | PASS | Helped with task, noted Likert pending. |
| likert_deflection | FAIL | Did not relent after 3 strikes. Pilot's checklist mentality. |
| tangent_and_resume | 5/7 | Handled tangent, but restarted from Q1 not Q3. |
| deflect_then_resume | PASS (4/4) | Relented, normal ops, user-initiated resume. |
| edit_response | PASS (5/5) | "Done — comfort back to 3." Clean edit. |

## Standing Decision

**Accept personality variance as data, not bugs.** The eval harness measures governance compliance per personality. Tighter governance would flatten personality — defeating the purpose of calibration. The three-strike relent is the safety net. Failures are monitored, not fixed.

Review threshold: if a personality drops below 4/8, investigate whether governance or personality needs adjustment.

## Methodology

- DB injection via `_inject_message()` into instance SQLite
- Response capture via pm2 stdout log polling (multi-line, ANSI-stripped)
- Full state reset between scenarios: DB, sessions, SDK data, onboarding YAML, pm2 restart
- Each scenario: 30s timeout per turn, ~3 min total with container cold start
- Records written to `data/assessments/*.yaml` per instance
