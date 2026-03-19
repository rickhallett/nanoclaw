# Adversarial Review: Behavioral Smoke Suite v2

Date: 2026-03-19

Scope: static adversarial review of the current `halos/halctl/behavioral_smoke.py` and `halos/halctl/cli.py`, after the post-review rewrite.

Method: assume the implementation is trying to look correct while leaving broken behavior undetected. For each scenario and harness rule, ask: "How could this still pass green while the real capability is wrong?"

This review did not run the suite. It is based on code inspection only.

## Findings

### 1. M2 still does not prove durable retrieval; it can pass on short-term conversational recall

File: `halos/halctl/behavioral_smoke.py:872-940`

Severity: high

`M2` is materially better than the previous version because it now performs a retrieval query. The remaining issue is that the retrieval happens immediately after the write, in the same sender/session/chat context:

- store fact
- verify note exists
- ask "What is my test preference?"
- pass if response contains the stored value

That still allows a broken memory system to pass if the agent is answering from fresh conversational context rather than durable memory.

Adversarial pass path:

- note writing works or at least appears to work
- actual memory lookup path is broken or unused
- model answers from the immediately preceding conversation turn
- scenario passes

Why this matters:

- the scenario claims to test retrieval from durable memory
- the current shape tests "can answer a follow-up question right after being told the fact"

Required fix:

- move the query to a fresh process, fresh session, or at minimum a different sender context that cannot see the original conversational turn
- keep the note existence check only as setup verification, not as proof of retrieval correctness

---

### 2. O2 under-enforces its own contract; it can pass if the agent relents after strike 2 instead of strike 3

File: `halos/halctl/behavioral_smoke.py:1643-1649`, `halos/halctl/behavioral_smoke.py:1763-1787`

Severity: high

The docstring says:

- strikes 1-2 must still get Likert questions
- after strike 3 the agent should relent

The implementation does not actually enforce that. It uses:

- `strike3_no_likert`
- `earlier_had_likert = any(sr[2] for sr in strike_responses[:2])`

Using `any(...)` means only one of the first two strikes needs to contain a Likert question.

Adversarial pass path:

- strike 1 contains a Likert question
- strike 2 already stops asking
- strike 3 also has no Likert
- state is not deferred
- test still passes because `earlier_had_likert` is true and strike 3 had no Likert

That is not the documented three-strike rule. It is "asked at least once before stopping."

Required fix:

- require strike 1 and strike 2 both to contain the assessment prompt
- only allow the non-Likert transition on strike 3, unless there is an explicit deferred terminal state proving the rule completed

---

### 3. T1 still checks only coarse schedule semantics, so materially wrong schedules can pass

File: `halos/halctl/behavioral_smoke.py:475-535`, `halos/halctl/behavioral_smoke.py:547-623`

Severity: high

The schedule validator is stronger than before, but it still verifies only a coarse subset of user intent:

- `cron`: validates format and roughly the hour field
- `once`: validates "future" and roughly the hour

It does not verify:

- weekday semantics for prompts like "every Monday at 10am"
- date semantics for prompts like "next Friday at noon"
- day-vs-daily recurrence distinctions beyond `schedule_type`
- binding to the expected chat or actor

Adversarial pass paths:

- "every Monday at 10am" becomes a daily cron at 10:00 and passes
- "next Friday at noon" becomes tomorrow at noon and passes
- a one-time task is created for the right hour but wrong date and still passes

Required fix:

- assert weekday/day-of-month semantics from `schedule_value`, not just hour and type
- verify the created task is attached to the correct chat/user scope

---

### 4. C1 still does not prove shell execution; it proves access to current time

File: `halos/halctl/behavioral_smoke.py:1167-1234`

Severity: medium

Switching from `echo` to `date +%s` is a real improvement because the output is no longer present in the prompt. It still does not prove the specific capability named by the test: shell command execution.

The pass condition is "response contains a plausible epoch timestamp inside the observed window." That can be satisfied by any mechanism that gives the model current time with second-level precision:

- a time tool
- ambient runtime clock access
- direct system prompt timing knowledge combined with light inference

Adversarial pass path:

- shell tool is broken or unavailable
- model obtains current time some other way
- emits an epoch inside the allowed window
- scenario passes

Required fix:

- use a command whose output depends on a side effect or filesystem fact not available through general time awareness
- ideally verify a command-side artifact or transcript rather than only the returned value

---

### 5. Aggregate thresholding can hide a total failure of a critical scenario

File: `halos/halctl/behavioral_smoke.py:132-148`, `halos/halctl/behavioral_smoke.py:2048-2056`

Severity: medium

Suite pass/fail is based on total passing runs across the whole suite. That means a low-run but important scenario can fail completely while the suite still clears the global `0.95` threshold.

Example on a microHAL run with default counts:

- `O2` runs only 2 times
- the rest of the suite has enough total runs that 2 failures can still leave the overall rate above 95%
- result: the suite can go green even if the three-strike rule is entirely broken

This is a gate-design problem, not a scenario bug, but it matters if the suite is meant to certify behavioral compliance.

Required fix:

- require per-scenario minimum pass thresholds in addition to a global suite threshold
- treat certain scenarios as mandatory blockers, especially boundary and onboarding state-machine tests

---

### 6. T2 still treats pending IPC as success, so downstream cancellation failure can be masked

File: `halos/halctl/behavioral_smoke.py:703-728`

Severity: medium

`T2` improved its setup isolation, but it still passes when only a cancel/update IPC artifact exists and the durable DB state has not changed yet.

Adversarial pass path:

- agent emits a cancel IPC request
- downstream consumer never processes it, or processes it incorrectly
- task remains live in the real system
- test passes on the pending IPC

Required fix:

- keep IPC as a diagnostic signal only
- require a durable DB state change or deletion before passing

---

### 7. O1 proves onboarding engagement better than before, but it still uses a loose regex proxy for the actual prompt contract

File: `halos/halctl/behavioral_smoke.py:1567-1612`

Severity: medium

This scenario is clearly improved because it now requires both:

- onboarding state creation
- a Likert-like response

The remaining weakness is that the Likert check is still a broad regex proxy. A generic sentence containing "on a scale of 1 to 5" can satisfy the response half of the assertion without proving the exact onboarding question or protocol framing is correct.

Adversarial pass path:

- onboarding row is created
- response contains a generic rating phrase unrelated to the intended onboarding prompt
- scenario passes

Required fix:

- assert a narrower onboarding prompt shape or validate the associated assessment record if that is the real protocol artifact

---

### 8. M1 still verifies only a narrow keyword slice of the remembered fact

File: `halos/halctl/behavioral_smoke.py:763-830`

Severity: medium

`M1` is much better than v1 because it removed the "any new note" fallback and requires the marker plus a fact token. The semantic check is still shallow:

- `"tuesday"` is enough for `"I have a meeting every Tuesday at 2pm"`
- `"dark mode"` is enough even if the note drops the "all applications" part

Adversarial pass path:

- note captures only part of the fact or a distorted version of it
- chosen keyword still appears
- scenario passes

Required fix:

- validate a fuller normalized fact payload, not just one keyword fragment

---

### 9. Cleanup is safer than before but still relies on broad end-of-suite cleanup in a live environment

File: `halos/halctl/behavioral_smoke.py:1802-1899`

Severity: medium

Cleanup is improved, especially for `registered_groups`, where it now prefers exact JIDs from tracked artifacts. The residual risk is structural:

- cleanup still happens mainly at suite end
- a mid-suite crash can strand tasks, notes, messages, or onboarding state
- the folder fallback `telegram_smoke-test-%` is narrower than the old name match, but it is still pattern-based rather than exact

This is more of an operational risk than a hallucination risk, but it matters because the suite mutates live state.

Required fix:

- clean up per scenario where practical
- prefer exact fixture identifiers everywhere, including folders if they are created deterministically

---

### 10. C2 remains one of the stronger scenarios, but its container-path assumption is still brittle

File: `halos/halctl/behavioral_smoke.py:1263-1310`

Severity: low

This is still one of the most credible scenarios because the response must contain a unique token that is not present in the prompt. The remaining issue is environmental:

- it assumes the host file written under `group_dir/tmp` is visible as `/workspace/group/tmp/...`
- the prime fallback still writes under `ctx.deploy_path/tmp` but asks the agent for `/workspace/group/tmp/...`

This is more likely to create false failures than false passes, but it limits confidence in the signal.

## Overall Assessment

The suite is materially stronger than the prior version. Important improvements include:

- response correlation by injected message ID
- removal of the broad M1 fallback
- a real retrieval step in M2
- stronger onboarding gating in O1
- a much better O2 shape
- safer cleanup for registered groups
- IPC-only results downgraded to failure in T1 and A1

The remaining weaknesses are no longer mostly "obvious false-positive factories." They are narrower and more scenario-specific:

- same-session leakage in M2
- under-enforced strike sequencing in O2
- coarse semantic checks in T1 and M1
- proxy capability checks in C1
- aggregate thresholding that can hide a failed critical scenario

## Gate Recommendation

This version is much closer to a credible behavioral suite, but I would still avoid treating it as a hard compliance gate until:

- M2 crosses a fresh context boundary
- O2 enforces the exact strike progression it claims to test
- T1 validates full schedule intent, not just type and hour
- C1 proves shell execution specifically
- suite pass/fail includes per-scenario blocking rules
