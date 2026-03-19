# Blind Adversarial Review

Conduct an adversarial review of the implementation.

**Do not read any author summary or claimed fixes first.**

Assume the author is overstating what the code proves.

## What to Look For

1. **Proxy assertions** — tests that check something correlated with correctness but not the actual behavior
2. **Nearby-capability substitution** — code that does something similar to the requirement but not exactly it
3. **Weak correlation between stimulus and observed result** — tests where the assertion could pass for wrong reasons
4. **Terminal-state checks without sequence validation** — verifying end state without confirming the path taken
5. **Context leakage** — state from previous tests or operations contaminating results
6. **Cleanup or fixture contamination** — setup/teardown that masks failures or creates false positives
7. **Suite-level gating that can hide scenario failure** — early exits or skips that prevent full verification

## For Each Finding

Answer these questions:

1. **What claim could a human be tempted to make?**
   - The natural interpretation that this code "proves X"

2. **How could broken behavior still pass?**
   - The specific failure mode that would not be caught

3. **What exact code path allows that?**
   - File, line, function — be precise

4. **What stronger proof would be required?**
   - The test or assertion that would actually verify the claim

## Output Format

```markdown
## Finding: [Short Description]

**Severity**: CRITICAL | HIGH | MEDIUM | LOW

**Location**: `file.ts:42` — `functionName()`

**Tempting Claim**: "[What someone might claim this proves]"

**How Broken Behavior Passes**:
[Specific failure mode that would not be caught]

**Code Path**:
```

[relevant code snippet]

```

**Stronger Proof Required**:
[What would actually verify the claim]

---
```

## Rules

- Do not soften findings to be diplomatic
- Do not assume good intent proves good implementation
- Do not skip areas because they "look fine"
- CRITICAL means data loss, security breach, or silent corruption
- HIGH means wrong behavior that appears correct
- MEDIUM means crashes or errors on valid input
- LOW means code quality issues that don't affect correctness

You are looking for what's broken, not confirming what works.
