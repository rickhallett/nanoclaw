# Adversarial Review: Behavioral Smoke Suite

Date: 2026-03-19

Scope: static adversarial review of `halos/halctl/behavioral_smoke.py` and the `halctl behavioral-smoke` CLI wiring in `halos/halctl/cli.py`.

Method: treat the suite as hostile terrain and ask, for each scenario, "how could broken behavior still pass green?" This review did not run the suite; it focuses on validator strength, fixture isolation, response correlation, side-effect safety, and cleanup risk.

## Findings

### 1. Global response correlation is unsound, so multiple scenarios can grade the wrong reply

File: `halos/halctl/behavioral_smoke.py:267-302`, `halos/halctl/behavioral_smoke.py:470-475`, `halos/halctl/behavioral_smoke.py:666-671`, `halos/halctl/behavioral_smoke.py:993-999`, `halos/halctl/behavioral_smoke.py:1318-1324`

Severity: critical

The harness injects a message into the database, records the current PM2 log line count, then accepts the first later `Agent output:` line as the scenario response. There is no correlation by message ID, sender ID, marker, chat JID, or any other stable key.

Why this matters:

- Any unrelated agent output emitted after the injection can be mistaken for the test response.
- Background work, concurrent users, retries, or delayed prior outputs can all contaminate the result.
- Every scenario that depends on response content inherits this weakness, even if its own validator looks reasonable.

Adversarial pass path:

- Inject a test message.
- Let some unrelated conversation produce a response containing the expected pattern first.
- The suite records a pass against the wrong event.

Required fix:

- Correlate responses to the injected message directly, ideally through the message store or a durable event ID, not through "first matching log line after line N".
- If log correlation is unavoidable, require the marker or sender identity to appear in a machine-parsable structured event tied to that specific output.

---

### 2. O2 can pass when the three-strike behavior is broken, absent, or silent

File: `halos/halctl/behavioral_smoke.py:1438-1483`

Severity: critical

The success condition is:

- onboarding state enters one of `deferred|complete|skipped|relented`, or
- `likert_asked_count < 3`

That second branch is far too weak. It treats many broken flows as success:

- the agent never actually starts onboarding
- the agent stops responding after strike 1 or strike 2
- the response changes for the wrong reason
- the detector simply fails to recognize the onboarding question format

Adversarial pass path:

- Respond to initial contact with anything.
- Ignore the next three refusal messages.
- `likert_asked_count` remains `0`, so the test passes.

Required fix:

- Prove the scenario started in the correct onboarding state.
- Prove strike 1 and strike 2 still request the assessment or otherwise advance the expected protocol.
- Prove strike 3 transitions the state machine into a specific deferred terminal state.
- Treat missing responses during the refusal sequence as failure, not implicit success.

---

### 3. M2 does not test lookup at all; it re-tests note creation

File: `halos/halctl/behavioral_smoke.py:737-799`

Severity: critical

The scenario is named `Memory Lookup`, but it never issues a retrieval query. It stores a fact, finds a note with the marker, and checks whether the note contains the stored value.

That validates write-path persistence only. It says nothing about whether the agent can retrieve or use the stored memory.

Adversarial pass path:

- Agent writes a note correctly.
- Agent has no retrieval path, no search path, or a broken lookup tool.
- Scenario still passes.

Required fix:

- After writing the fact, query for it in a fresh session or after restarting the agent.
- Prove the answer content matches the stored value.
- Keep the direct artifact check, but only as setup verification, not as the retrieval assertion.

---

### 4. C1 tests command-shaped language, not command execution

File: `halos/halctl/behavioral_smoke.py:979-1008`

Severity: high

The validator passes if the response contains the expected `echo` output token. That is only evidence that the agent can predict the shell output, not that it ran a command.

Adversarial pass path:

- The agent never invokes a shell.
- It simply replies with `CMDTEST_xxxxxx`.
- The test passes.

Required fix:

- Verify an execution-side artifact such as a logged tool call, shell transcript, or a command that produces a side effect not recoverable from prompt inspection alone.
- If staying read-only, use a command whose result cannot be inferred from the prompt and verify it from an independent source.

---

### 5. M1 has a broad false-positive fallback and weak semantic validation

File: `halos/halctl/behavioral_smoke.py:678-715`

Severity: high

If no note contains the marker, the scenario looks for any newly created note and passes it as long as the note has rudimentary frontmatter. It does not verify that the note belongs to this prompt or contains the requested fact.

Even when a marker note is found, the validator still only checks for frontmatter presence, not whether the user fact was stored correctly.

Adversarial pass paths:

- Another process creates an unrelated note during the test window.
- The agent writes a marker note with frontmatter but omits or distorts the requested fact.
- The agent writes a generic note template for every "remember" request.

Required fix:

- Remove the "any new note" fallback.
- Require the specific marker and the fact payload to appear in the persisted note.
- Validate at least the semantic fields that matter, not just `title:` and `type:`.

---

### 6. T1 still under-specifies schedule correctness and accepts incomplete work as success

File: `halos/halctl/behavioral_smoke.py:446-520`, `halos/halctl/behavioral_smoke.py:341-352`

Severity: high

The validator only checks `schedule_type` (`once` vs `cron`). It does not verify:

- the actual day/time matches the user request
- the task is attached to the correct chat or actor
- the prompt was parsed semantically rather than just bucketed into the right type

It also accepts a pending IPC task as success, which proves only that a request artifact was emitted, not that the task was persisted.

Adversarial pass paths:

- "tomorrow at 9am" becomes a one-time task for the wrong date or hour.
- "every Monday at 10am" becomes a daily cron with any Monday-like metadata bug that still leaves `schedule_type='cron'`.
- The scheduler emits IPC but downstream processing fails.

Required fix:

- Assert the exact `schedule_value` semantics against the prompt.
- Verify the persisted task row after IPC processing, not just IPC existence.
- Confirm the created row belongs to the expected chat and remains durable after the queue drains.

---

### 7. O1 can pass without proving onboarding state was actually entered

File: `halos/halctl/behavioral_smoke.py:1328-1352`

Severity: high

If the response matches one of the Likert regexes, the test passes even when there is no onboarding row:

- `state = onboarding_row[0] if onboarding_row else "none"`
- pass recorded regardless

That means the suite can accept a generic "on a scale of 1 to 5..." sentence without proving the onboarding protocol actually engaged.

Adversarial pass path:

- The model emits a conversational sentence containing "on a scale of 1 to 5".
- No onboarding state is created.
- The test still passes.

Required fix:

- Require both a valid onboarding state transition and a response that matches the expected onboarding prompt shape.
- Verify any companion assessment row or protocol-specific metadata if that is part of the contract.

---

### 8. Cleanup can delete legitimate registered groups by name pattern

File: `halos/halctl/behavioral_smoke.py:1527-1532`

Severity: high

Cleanup deletes from `registered_groups` using:

`DELETE FROM registered_groups WHERE name LIKE '%Smoke Test%'`

That is broader than this suite's own fixtures. It does not key on the generated JID, marker, or a dedicated namespace stored by the test.

Why this matters:

- A legitimate group with "Smoke Test" in the name will be deleted.
- The suite mutates live instance state, so cleanup precision matters as much as setup precision.

Required fix:

- Track exact created group identifiers and delete by those identifiers only.
- Do not use human-readable name matching for destructive cleanup in a live environment.

---

### 9. F2 is still a negative-only test and can pass on inert behavior

File: `halos/halctl/behavioral_smoke.py:920-960`

Severity: medium

The scenario passes whenever `<internal>` tags are absent from the response. That means:

- plain refusal passes
- generic low-effort output passes
- unrelated output passes if response correlation is off

This checks leakage absence, but not that the model actually handled the prompt correctly while suppressing internal tags.

Required fix:

- Pair the leakage check with a positive requirement about the visible answer quality or task completion.
- At minimum, confirm the response addresses the prompt content rather than merely omitting the forbidden tag.

---

### 10. F1 is stronger than the previous version but still easy to spoof

File: `halos/halctl/behavioral_smoke.py:828-899`

Severity: medium

This scenario now checks both absence of markdown and presence of Telegram-style formatting, which is a real improvement. It still has notable spoof paths:

- the prompts themselves contain `*emphasis*` and `*bold*`, so an echoing or paraphrasing model can satisfy the formatting regexes cheaply
- any single formatted token is enough; the test does not verify that the requested structure or emphasis was actually applied to the answer
- inline backticks count as valid Telegram formatting even though they are not a meaningful proof of the requested emphasis behavior

Required fix:

- Avoid embedding the target formatting tokens in the prompt text.
- Require a stronger structural check on the answer, not just "at least one formatting match".

---

### 11. A1 and T2 still treat pending IPC as success, which masks downstream failure

File: `halos/halctl/behavioral_smoke.py:603-609`, `halos/halctl/behavioral_smoke.py:1149-1153`

Severity: medium

Both scenarios accept "IPC exists" as success when the durable state change has not happened yet. That is useful as an intermediate diagnostic, but it is not a behavioral pass condition if the contract is user-visible completion.

Adversarial pass path:

- Agent emits the correct IPC request.
- Consumer never processes it, or processes it incorrectly.
- Test passes before the real side effect exists.

Required fix:

- Treat IPC-only observations as "inconclusive" or "setup in progress", then wait for the durable artifact or fail on timeout.

---

### 12. A2 is directionally correct but still vulnerable to environmental races

File: `halos/halctl/behavioral_smoke.py:1201-1264`

Severity: medium

This is one of the stronger scenarios because it checks absence of forbidden artifacts rather than refusal language. The main residual issue is environmental coupling:

- the DB count check is global, so unrelated group creation during the window looks like a boundary breach
- the IPC scan is global and time-window based

This does not make the scenario hallucinatory, but it does make the result noisier in a live shared environment.

Required fix:

- Prefer exact-key assertions over global count deltas.
- Keep the JID-specific checks and make them the primary signal.

---

### 13. The suite mutates live state broadly, and cleanup is best-effort at the end

File: `halos/halctl/behavioral_smoke.py:242-258`, `halos/halctl/behavioral_smoke.py:1498-1584`

Severity: medium

The suite writes directly into live tables and filesystem locations, then performs cleanup after all scenarios run. If the suite aborts mid-run, state can be left behind.

This is especially risky for:

- registered groups
- onboarding state
- memory notes
- synthetic messages
- IPC files

Required fix:

- Use narrower namespaces and exact cleanup keys everywhere.
- Clean up per scenario where practical, not only at suite end.
- Distinguish "test fixture" artifacts in a way that downstream code cannot confuse with operator-created state.

---

### 14. C2 is comparatively stronger, but its path assumption is brittle

File: `halos/halctl/behavioral_smoke.py:1038-1062`

Severity: low

This is one of the better scenarios because the unique file content is not present in the prompt, so parroting is harder. The main issue is environmental:

- it assumes the host path used for file creation corresponds to `/workspace/group/tmp/...` inside the agent container
- the prime fallback writes under `ctx.deploy_path/tmp` but still asks the agent to read `/workspace/group/tmp/...`

This is more likely to cause false failures than false passes, but it should be tightened before being treated as a reliable regression signal.

## Overall Assessment

The suite is materially better than the original handoff criticized in the session note, but it is not yet a trustworthy behavioral gate. The main reasons are:

- global response correlation is unreliable
- several scenarios still accept proxies rather than end-state correctness
- one scenario (`M2`) does not test the behavior it claims to test
- one scenario (`O2`) has a major false-positive branch
- cleanup is still too broad for a live environment

The architecture and CLI are usable scaffolding. The assertion layer is still the limiting factor.

## Priority Rewrite Order

1. Fix response correlation in the harness before trusting any response-based scenario.
2. Rewrite `O2` so silence and non-onboarding cannot pass.
3. Rewrite `M2` into a real retrieval test across a fresh context.
4. Strengthen `M1` and `T1` to verify semantics, not just artifact class.
5. Replace `C1` with an execution proof that cannot be satisfied by parroting.
6. Tighten cleanup to exact fixture identifiers only.

## Gate Recommendation

Do not use `halctl behavioral-smoke` as a release or compliance gate in its current form. At best, it is diagnostic scaffolding with a few credible checks and several important false-positive paths.
