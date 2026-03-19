# Adversarial Review (Orchestrated)

Run a full adversarial review cycle: handoff → blind review → targeted verification.

## Process

This review uses three separate passes with strict isolation:

### Round 1: Handoff Generation

First, produce the review handoff document by running `/review-handoff`.

Save the output — you will need it for Round 3, but **do not read it yet**.

### Round 2: Blind Review

Now run `/review-blind`.

**Critical**: Do not reference the handoff document. Approach the code fresh. Assume the author is overstating what the code proves.

Document all findings before proceeding.

### Round 3: Targeted Verification

Now — and only now — read the handoff from Round 1.

Run `/review-targeted` with the handoff as input.

Compare the handoff claims against:

1. What you found in the blind review
2. What the code actually demonstrates

Flag any discrepancies between the author's framing and your blind findings.

## Output

Produce a unified review report:

```markdown
# Adversarial Review Report

## Summary

[One paragraph: overall assessment, key risks, confidence level]

## Blind Review Findings

[Findings from Round 2, unfiltered]

## Handoff Verification

[Table from Round 3: claim verdicts]

## Discrepancies

[Where blind review contradicts or extends the handoff]

## Risk Assessment

| Risk              | Severity                 | Status                  |
| ----------------- | ------------------------ | ----------------------- |
| [identified risk] | CRITICAL/HIGH/MEDIUM/LOW | Open/Mitigated/Accepted |

## Recommendations

1. [Most important action]
2. ...

## Verdict

[ ] PASS — Implementation matches claims, risks acceptable
[ ] CONDITIONAL — Specific issues must be addressed
[ ] FAIL — Claims overstated or critical risks unaddressed
```

## Rules

1. **Isolation is mandatory.** Do not let Round 1 output influence Round 2 thinking. If you cannot maintain this separation, say so.

2. **Blind review comes first.** The handoff exists to help verification, not to frame perception.

3. **Prefer skepticism.** "Partially true" over "confirmed" unless evidence is unambiguous.

4. **Name the non-claims.** What does this change explicitly NOT prove? The author should have said; verify they did.

5. **Discrepancies are signal.** If blind review found something the handoff omitted, that's information about handoff quality.

## When to Use

- After significant implementation work
- Before merging to main
- When claims about behavior need verification
- When you suspect the implementation model is pattern-matching rather than reasoning

## Limitations

This orchestration asks one model to maintain separation between rounds. True adversarial review would use separate model instances. This is a pragmatic approximation — better than no review, worse than true isolation.

If you find yourself unable to "unsee" the handoff during blind review, acknowledge it and note which findings may be contaminated.
