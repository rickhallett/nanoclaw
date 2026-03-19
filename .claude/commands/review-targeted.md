# Targeted Review (Pass 2)

Now read the implementation handoff and check it against the code.

This is pass 2 — you should have already completed a blind review (`/review-blind`).

## Input

You need the review handoff document (from `/review-handoff`). If not provided, ask for it.

## For Each Claimed Behavior Delta

Evaluate and classify as one of:

| Verdict            | Meaning                                                                       |
| ------------------ | ----------------------------------------------------------------------------- |
| **Confirmed**      | The exact claimed capability is demonstrated in code with sufficient evidence |
| **Partially True** | Some aspect of the claim is supported, but not the full claim                 |
| **Overstated**     | The claim goes beyond what the code actually proves                           |
| **Unsupported**    | No evidence in code supports this claim                                       |

**Prefer "Partially True" over "Confirmed"** unless the exact claimed capability is demonstrated with strong evidence.

## For Each Review Hotspot

Check whether:

- The identified risk is real
- The author's assessment is accurate
- Additional risks exist that weren't mentioned

## For Each Non-Claim

Verify the author is being honest about limitations:

- Are the non-claims actually true?
- Are there additional non-claims that should be listed?
- Is anything claimed elsewhere that contradicts these non-claims?

## Output Format

```markdown
## Handoff Verification

### Claimed Behavior Deltas

| Claim                | Verdict                                         | Evidence         | Notes              |
| -------------------- | ----------------------------------------------- | ---------------- | ------------------ |
| [claim from handoff] | Confirmed/Partially True/Overstated/Unsupported | [code reference] | [why this verdict] |

### Hotspot Assessment

| Hotspot | Author's Risk    | Actual Risk      | Additional Concerns |
| ------- | ---------------- | ---------------- | ------------------- |
| [area]  | [what they said] | [what you found] | [anything missed]   |

### Non-Claims Verification

| Non-Claim                         | Accurate?        | Notes         |
| --------------------------------- | ---------------- | ------------- |
| [what they said it doesn't prove] | Yes/No/Partially | [explanation] |

### Handoff Quality

- **Completeness**: [Did the handoff cover all changed areas?]
- **Honesty**: [Was the author forthright about limitations?]
- **Usefulness**: [Did the handoff help or mislead the review?]

### Discrepancies

[Any findings from blind review (pass 1) that contradict the handoff]

### Final Assessment

[Overall verdict on whether the implementation matches its claims]
```

## Rules

- The handoff tells you where to look, not whether it succeeded
- Trust your blind review findings over the author's framing
- If blind review found something the handoff didn't mention, that's a red flag
- "Confirmed" requires strong evidence, not absence of disproof
