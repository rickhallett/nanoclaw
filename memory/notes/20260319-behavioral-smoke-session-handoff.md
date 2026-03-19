---
title: 'Session Handoff: Behavioral Smoke Tests'
type: session-log
tags: [testing, behavioral-smoke, session-handoff, code-review]
created: 2026-03-19T16:15:00Z
confidence: high
---

# Session Handoff: Behavioral Smoke Tests

## What Was Asked For

Rick requested a new wing of smoke tests with the following requirements:

1. **Purpose:** Ensure agents follow basic operating instructions
2. **Independence:** Runs separately from existing smoke tests
3. **Real tests:** Burns tokens, tests actual agent behavior
4. **First scenario:** "When user asks to be reminded, agent creates/updates a cron job"
5. **Acceptance criteria:** >95% success rate
6. **Verification:** Use halos ecosystem and filesystem edits
7. **Cleanup:** Clear test artifacts after smoke test

After initial implementation, Rick asked for a comprehensive list of testable behaviors based on the ecosystem. I produced a survey identifying 12 orthogonal test scenarios across 6 capability dimensions (Task, Memory, Formatting, Command, Auth, Onboarding).

## What Was Promised

An orthogonal test matrix where:

- Each test validates ONE capability dimension
- Tests are independent (no O(n²) coupling)
- Failures don't cascade
- Token cost is minimized
- Tests can be run selectively by scenario, phase, or capability

## What Was Delivered

### Files Created/Modified

1. **`halos/halctl/behavioral_smoke.py`** — New module with:
   - Scenario registry architecture with metadata (ID, capability, phase, cost)
   - 12 registered scenarios (T1, T2, M1, M2, F1, F2, C1, C2, A1, A2, O1, O2)
   - `TestContext` dataclass for shared state
   - `BehavioralResult` and `BehavioralSuiteResult` for tracking
   - Cleanup function targeting `BSMOKE_*` artifacts
   - Selective execution by ID, phase, or capability

2. **`halos/halctl/cli.py`** — Updated with:
   - `halctl behavioral-smoke` command
   - `--list` flag to show available scenarios
   - `--scenario`, `--phase`, `--capability` filters
   - `--runs`, `--timeout`, `--threshold` overrides

### CLI Interface

```bash
halctl behavioral-smoke --list           # Show all scenarios
halctl behavioral-smoke prime            # Run full suite on HAL-prime
halctl behavioral-smoke prime --phase 1  # Run only CORE phase
halctl behavioral-smoke prime -s T1,M1   # Run specific scenarios
halctl behavioral-smoke prime -c T       # Run all Task capability tests
```

## What Was Reviewed

Rick challenged the implementation with direct skepticism. His exact words: "My sloposenses are firing here hal."

## Results of Review

**The implementation is fundamentally flawed.** The scenarios are structured well but the _validators_ are toothless. Specific failures:

### 1. False Positive Factory (CRITICAL)

Most scenarios fall back to heuristic keyword matching:

```python
task_indicators = ["scheduled", "reminder set", "task"]
if any(ind in response.lower() for ind in task_indicators):
    result.record(True, "Response indicates task creation")
```

A confident hallucination passes. This puts a green light on precisely what we're guarding against.

### 2. M2 Memory Lookup — Worse Than No Test

Stores a fact, then queries in the same session. The agent recalls from conversation context, not from memctl. This doesn't test persistence at all.

### 3. O1/O2 Onboarding — Tests Knowledge, Not Compliance

Asks the agent "what do you do during onboarding?" instead of simulating a new user and verifying Likert questions are delivered. Tests training data, not behavior.

### 4. A1 Authorization — Potential DB Pollution

Creates real groups in the database. If test fails mid-run, artifacts remain. Cleanup is reactive, not preventive.

### 5. F1 Formatting — No Positive Assertions

Checks for markdown _absence_ but not Telegram formatting _presence_. Plain text passes.

### 6. T2 Depends on T1 — Not Actually Orthogonal

Despite claiming orthogonal design, T2 (task modification) creates its own fixture but the _stated_ design was to avoid this coupling. The implementation is better than claimed but the architecture section is misleading.

## What Rigorous Testing Would Look Like

| Scenario | Current (Bad)                 | Required (Good)                                   |
| -------- | ----------------------------- | ------------------------------------------------- |
| T1       | Response contains "scheduled" | DB row exists AND schedule matches user intent    |
| M1       | Response contains "noted"     | Note file exists with correct YAML frontmatter    |
| M2       | Query in same session         | Store → restart → query in fresh session          |
| F1       | No markdown patterns          | No markdown AND Telegram formatting present       |
| A2       | Response says "cannot"        | No IPC file created, no DB row                    |
| O1       | Agent describes protocol      | Fresh onboarding state, Likert question delivered |

## Artifacts Requiring Cleanup

The current `behavioral_smoke.py` should be considered scaffolding, not production code. The registry architecture and CLI are solid. The scenario implementations need complete rewrites with proper validators.

## Next Steps for Successor Agent

1. **Read `.claude/evals/testing.md`** — Contains the pattern pairs (bad vs good) extracted from this review
2. **Rewrite validators** one scenario at a time, following the eval guidelines
3. **Start with T1** — It's the original requirement and the most concrete
4. **Verify no false positives** — Each validator must fail when the behavior is broken
5. **Run against live instance** to validate

## Token Count at Handoff

~110k tokens in session when review occurred.
