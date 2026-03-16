---
description: Break a complex task into atomic, testable steps with dependencies and acceptance criteria.
---

# Task Decomposition

Break $ARGUMENTS into atomic tasks that can be independently completed and verified.

## Decomposition Principles

1. **One concern per task.** If a task has "and" in it, split it.
2. **Independently testable.** Each task has a verification step that doesn't depend on other tasks being complete.
3. **Clear completion criteria.** "Implement the thing" is not a task. "Function X returns Y for input Z, verified by test T" is a task.
4. **2-8 hour ideal size.** Smaller is better. Larger means you missed a split point.
5. **Dependencies are explicit.** If task B needs task A's output, say so. If they're independent, say so — that means they can be parallelised.

## Process

### Step 1: Understand the Goal
Read the relevant code. Check memory/INDEX.md for prior decisions. Understand what exists before deciding what to build.

### Step 2: Identify the Work Units
List every distinct thing that needs to change. Group by file/module when natural, but don't force it.

### Step 3: Order by Dependency
Which tasks unblock other tasks? What's the critical path? What can run in parallel?

### Step 4: Write the Decomposition

For each task:

```markdown
### Task N: [Title]

**Files:** create/modify/test paths
**Depends on:** Task M (or: none)
**Parallel with:** Task P (or: none)

**What:** [One sentence — what changes]
**Why:** [One sentence — what this enables]
**Acceptance criteria:**
- [ ] [Specific, testable criterion]
- [ ] [Another criterion]

**Verification:** [Exact command to run]
```

### Step 5: Estimate and Flag Risks

At the end, summarise:
- Total tasks
- Critical path length
- Parallelisation opportunities
- Risks (tasks that might be harder than they look, tasks with uncertain scope)

## Output

Write the decomposition to `docs/plans/{date}-{topic}.md` unless told otherwise.

After decomposition, ask: "Ready to execute, or should we refine any tasks?"
