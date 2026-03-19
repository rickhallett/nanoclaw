# Review Handoff

Prepare a review handoff for an adversarial reviewer.

**Do not claim correctness.**
Do not say "fixed", "resolved", "proved", or "works" unless you are naming a literal artifact checked in code.

Describe only:

1. **Files changed** — list every file modified in this session
2. **Exact code paths touched** — functions, methods, branches added or modified
3. **Claimed behavior delta** — what the code is supposed to do differently now
4. **What evidence exists in code** — tests, assertions, guards that demonstrate the claim
5. **Known limitations** — what this implementation does NOT handle
6. **Where an adversarial reviewer should look first** — highest-risk areas
7. **What nearby capability might be mistaken for the target capability** — similar behaviors that could fool a shallow check
8. **What this change does NOT prove** — explicit non-claims

## Output Format

```markdown
## Change Summary

[Brief description of intent, not outcome]

## Files Changed

- path/to/file.ts — [what was touched]
- ...

## Code Paths Touched

- `functionName()` in file.ts:42 — [what changed]
- ...

## Claimed Behavior Delta

- [specific claim about new/changed behavior]
- ...

## Evidence in Code

- [test name or assertion that supports each claim]
- ...

## Known Limitations

- [what this does NOT handle]
- ...

## Review Hotspots

1. [highest-risk area and why]
2. ...

## Nearby Capabilities (Potential Confusion)

- [similar behavior that could be mistaken for target]
- ...

## Non-Claims

- This change does NOT prove: [explicit list]
- ...

## Residual Risks

- [risks that remain even if implementation is correct]
- ...
```

You are producing a map, not a certificate. The reviewer will verify independently.
