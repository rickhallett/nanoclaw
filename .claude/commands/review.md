# Adversarial Review (Orchestrated)

Run a full adversarial review cycle using three isolated subagents.

## Process

You are the orchestrator. You will spawn three subagents sequentially, controlling what context each receives. **Do not run these yourself** — dispatch to subagents via the Task tool.

### Round 1: Blind Review

Spawn a subagent with:

- The files/code to review (list them explicitly)
- The `/review-blind` instructions
- **Nothing else** — no implementation context, no author claims

Wait for completion. Save the output as `blind_findings`.

### Round 2: Handoff Generation

Spawn a second subagent with:

- The files/code changed
- The `/review-handoff` instructions
- **Do not include the blind findings** — this subagent doesn't know what the reviewer found

Wait for completion. Save the output as `handoff`.

### Round 3: Targeted Verification

Spawn a third subagent with:

- The files/code
- The `/review-targeted` instructions
- The `blind_findings` from Round 1
- The `handoff` from Round 2

This subagent compares the handoff claims against the blind findings and the actual code.

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

1. **Sequential dispatch.** Round 1 must complete before Round 2 starts. Round 2 must complete before Round 3 starts.

2. **Context isolation.** Each subagent gets only what's listed above. The blind reviewer never sees the handoff. The handoff author never sees the blind findings.

3. **You are the orchestrator, not the reviewer.** Do not perform the review yourself. Dispatch to subagents.

4. **Collect and synthesize.** After Round 3, combine all outputs into the final report.

## When to Use

- After significant implementation work
- Before merging to main
- When claims about behavior need verification
- When you suspect the implementation model is pattern-matching rather than reasoning

## Why Subagents

Each subagent starts with fresh context. The blind reviewer cannot be contaminated by the handoff because it doesn't exist in their context. The handoff author cannot defensively address blind findings because they don't know what was found.

This is true isolation, not "try not to think about it."
