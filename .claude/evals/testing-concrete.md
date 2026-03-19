# Eval: Concrete Testing Failure Modes

Guidance for spotting agent-written tests that look legitimate but do not verify real behavior.

## Core Principle

A test suite is hallucinatory when it validates persuasive signals around the behavior instead of the behavior itself. The common smell is structural competence wrapped around weak assertions.

In practice, this means the agent often gets the outer shape right:

- CLI surface
- scenario registry
- metadata and categorization
- cleanup hooks
- reporting types
- broad coverage claims

But the inner loop is wrong: the pass/fail logic checks whether the system sounded correct, not whether it did the correct thing.

---

## Canonical Failure Pattern

The recurring pattern looks like this:

1. The user asks for behavioral verification.
2. The agent builds polished scaffolding that resembles a real test harness.
3. The validator uses a proxy that is easy to observe.
4. The proxy is correlated with success but does not prove success.
5. The suite goes green while the real behavior remains broken.

This is more dangerous than obvious nonsense because it creates false confidence.

---

## Primary Error Classes

### 1. Response-Level Verification

**Smell:** The test passes because the reply contains words like `"scheduled"`, `"saved"`, `"cannot"`, or `"done"`.

**Why it fails:** Models can confidently claim an action occurred without creating the corresponding artifact.

**What to require instead:** Check the database row, file, IPC message, API side effect, or other concrete state change.

---

### 2. Knowledge vs Compliance Substitution

**Smell:** The test asks the agent what it would do, what the policy is, or how onboarding works.

**Why it fails:** This tests protocol knowledge, not protocol execution.

**What to require instead:** Simulate the real user state and verify the required behavior is actually emitted or enforced.

---

### 3. Context Leakage Mistaken for Persistence

**Smell:** The test stores information, then checks retrieval in the same session and calls that “memory.”

**Why it fails:** The agent may be recalling from local conversation context rather than durable storage.

**What to require instead:** Verify the persisted artifact directly and, where relevant, validate retrieval in a fresh session or restarted process.

---

### 4. Negative-Only Assertions

**Smell:** The test checks only that bad output is absent: no markdown, no exception, no forbidden phrase, no crash.

**Why it fails:** Empty, inert, or incomplete behavior can still pass.

**What to require instead:** Assert both sides:

- absence of the wrong behavior
- presence of the required behavior

---

### 5. Boundary Hallucination

**Smell:** The system says “I can’t do that,” and the test treats the refusal as proof of enforcement.

**Why it fails:** The forbidden side effect may still have been emitted behind the scenes.

**What to require instead:** Verify the protected artifact was not created and no downstream action was queued.

---

### 6. Fixture Contamination

**Smell:** A test implicitly depends on earlier test state, shared setup, or leftover artifacts.

**Why it fails:** Tests pass or fail for the wrong reason, and selective runs become misleading.

**What to require instead:** Each test must create its own fixtures, identify them uniquely, and verify only its own side effects.

---

### 7. Cleanup Theater

**Smell:** The test mutates real state and relies on best-effort cleanup after completion.

**Why it fails:** Mid-run failures leave residue, pollute the environment, and can influence later results.

**What to require instead:** Prefer isolated fixtures, reversible operations, dedicated namespaces, and validations that confirm cleanup succeeded.

---

### 8. Cosmetic Completeness

**Smell:** The suite has phases, capability matrices, IDs, thresholds, and rich reporting, but weak validators.

**Why it fails:** Architecture quality gets mistaken for test quality.

**What to require instead:** Review the assertion layer first. A minimal harness with strong validators is better than a polished framework with false positives.

---

## Advanced Error Classes

These show up after the obvious slop has been removed. The suite may now look almost rigorous, but still leave narrow escape hatches.

### 9. Correlation Failure

**Smell:** The validator is good, but the harness cannot prove the observed response or artifact belongs to the specific test stimulus.

**Why it fails:** A strong assertion applied to the wrong event is still a false positive. Unrelated replies, background activity, or delayed prior outputs can be graded as the test result.

**What to require instead:** Correlate by durable IDs, exact fixture keys, or machine-parsable metadata tied to the injected stimulus.

---

### 10. Capability Adjacency

**Smell:** The test proves a nearby capability rather than the one it claims to verify.

**Why it fails:** A system can pass by using an alternate path. For example, proving access to current time is not the same as proving shell execution.

**What to require instead:** Choose a validation target that can only be satisfied by the intended capability, or verify a capability-specific side effect.

---

### 11. State-Machine Underconstraint

**Smell:** A multi-step workflow test checks only the terminal state, or only a subset of the required sequence.

**Why it fails:** The system can arrive at a plausible end state through the wrong path, too early, or for the wrong reason.

**What to require instead:** Validate both transition sequence and terminal state when the protocol itself is part of the contract.

---

### 12. Context-Boundary Ambiguity

**Smell:** The test claims to cross context boundaries, but only changes one dimension such as sender, while leaving others such as chat, session, or process unchanged.

**Why it fails:** “Different sender” is not necessarily “different context.” Shared chat history, shared caches, or shared process memory can still satisfy the test.

**What to require instead:** Be explicit about which boundary matters:

- sender boundary
- chat/thread boundary
- session boundary
- process/restart boundary

Then verify the test actually crosses that boundary.

---

### 13. Gate Design Failure

**Smell:** Individual scenarios are decent, but suite-level aggregation lets critical failures disappear into an overall pass rate.

**Why it fails:** A high global score can hide total or partial failure in low-volume but important scenarios.

**What to require instead:** Combine global thresholds with per-scenario minimums and explicit blocking scenarios for critical behaviors.

---

### 14. Progressive Narrowing

**Smell:** The first obvious heuristics are fixed, and the suite now looks serious, so review pressure drops.

**Why it fails:** Agent-written suites often improve from blatant proxy tests to narrower semantic escape routes. The false-positive surface shrinks, but does not disappear.

**What to require instead:** Keep reviewing after the first rewrite. The question changes from “is this obvious slop?” to “what nearby or partial behavior still passes?”

---

## Generalization Targets

These failure modes recur anywhere an agent is asked to “test behavior”:

- benchmarks that score explanation quality instead of repo state
- eval harnesses that grade intent instead of end-state correctness
- memory tests that confuse prompt context with persistence
- security tests that verify refusal language rather than boundary enforcement
- migration checks that accept success logs instead of inspecting data
- workflow or onboarding tests that verify policy recitation instead of actual protocol compliance

---

## Audit Heuristics

Use these questions to review any agent-generated test:

- What concrete artifact or state transition does this assertion inspect?
- Can the system say the right thing while the behavior is still broken?
- Is the validator checking semantics, or only existence?
- Does the test prove persistence, or only same-session recall?
- Does the test cross the boundary it claims to cross, or only a nearby one?
- Can the harness prove that the observed response belongs to this exact stimulus?
- Is the test proving the named capability, or only an adjacent capability?
- For workflows, does it verify the sequence, or only a plausible end state?
- Does the test verify enforcement, or only refusal language?
- Could this pass with empty output, plain text, or a no-op?
- Could prior test residue make this pass?
- Could the suite still pass overall if a critical low-run scenario is flaky or fully broken?
- If cleanup fails midway, what state remains behind?

If the answer to any of those is unclear, the test is probably too weak.

---

## Required Standard

Before treating a behavioral test as credible, verify:

- it inspects the real artifact, not the response text
- it checks semantic correctness, not just artifact existence
- it would fail if the implementation only hallucinated success
- it asserts positive required behavior, not only absence of bad behavior
- it creates isolated fixtures and can run independently
- it distinguishes conversational context from persistence
- it correlates the observed result to the exact stimulus under test
- it proves the named capability, not just an adjacent one
- it validates workflow transitions when sequence is part of the contract
- it uses suite-level gating that cannot hide critical scenario failures
- it verifies boundaries by absence of side effects, not by refusal wording

The shortest useful rule is:

If a test can pass while the real behavior is broken, it is not validating behavior.
