---
title: "Taxonomy Review Phase 5"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Phase 5

Date: 2026-03-20

Scope:
- `FLT.TOPO`
- `FLT.ONBOARD`
- `FLT.EVAL`
- `FLT.PERS`

Primary files reviewed:
- `templates/microhal/*`
- `src/channels/telegram.ts`
- `halos/halctl/behavioral_smoke.py`

## Summary

Phase 5 produced 2 findings.

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 1 |
| S3 | 1 |
| S4 | 0 |

## Findings

### FLT.ONBOARD.01 [TC12] S2

Bot-level onboarding handoff is stored in one global file, `memory/onboarding-state.yaml`, so concurrent onboarding flows overwrite each other across users and groups.

Evidence:
- `writeOnboardingYaml()` always writes to `process.cwd()/memory/onboarding-state.yaml` in `src/channels/telegram.ts:88-116`;
- the welcome and waiver-accepted paths call it for whichever sender most recently advanced state in `src/channels/telegram.ts:284-286` and `src/channels/telegram.ts:340-342`.

Impact:
- if two users or groups are onboarding near the same time, the agent-visible handoff file can describe the wrong sender/group/state;
- the boundary between onboarding conversations is reduced to "last writer wins".

Why `[TC12]`:
- a per-user/per-group workflow crosses the sender/group boundary through a shared global artifact.

### FLT.EVAL.02 [TC13] S3

The behavioral smoke suite can still pass while an entire scenario fails, so long as that scenario is neither blocking nor given a per-scenario minimum.

Evidence:
- suite pass/fail only checks global threshold, `blocking_failures`, and `min_rate_failures` in `halos/halctl/behavioral_smoke.py:166-177`;
- scenarios without either flag therefore contribute only to the overall percentage;
- even a scenario described as "protocol is fundamental" is configured to tolerate 50% failure at `halos/halctl/behavioral_smoke.py:1795-1796`.

Impact:
- a meaningful behavioral regression can hide inside an overall pass if the suite is otherwise green;
- criticality is controlled by metadata quality, not just by what the scenario actually tests.

Why `[TC13]`:
- the gate design allows localized failures to disappear inside the aggregate score.

## Coverage Notes

Observed coverage:
- targeted Python test slices across Halos subsystems passed: `80 passed in 3.97s`.

Important gaps:
- no test covers the shared onboarding handoff file under concurrent onboarding;
- no test asserts that every important behavioral scenario must independently gate the suite.
