---
description: Checkpoint session context to disk before compaction eats it.
---

# Session Dump

The context window is volatile. This command writes a structured checkpoint of everything in the current session that isn't already on disk.

## Process

### Step 1: Scan the Conversation

Walk through the full conversation history. Extract:

1. **Decisions made** — architectural choices, trade-offs resolved, options rejected and why.
2. **Patterns discovered** — debugging sequences, operational rituals, provisioning steps, gotchas.
3. **State of the world** — what's running, what's broken, what's half-finished, current branch state.
4. **Open questions** — unresolved issues, things deferred, things that need human input.
5. **Contradictions or extensions** — anything that updates, contradicts, or extends existing docs or memory.

### Step 2: Write the Dump

Write to `memory/session-dumps/{YYYY-MM-DD}-{HH-MM}-{topic-slug}.md` using this exact format:

```markdown
# Session Dump: {topic}
<!-- {ISO 8601 timestamp} -->

## Decisions Made
<!-- One per item. Tag category in brackets. -->
- [{category}] {decision}. **Why:** {rationale}

## Patterns Discovered
<!-- Debugging sequences, operational knowledge, rituals. -->
- [{category}] {pattern}. **When:** {trigger condition}

## State of the World
<!-- Current runtime, branch, service, data state. -->
- [{category}] {state fact}

## Open Questions
<!-- Unresolved. Tag owner if known. -->
- [{category}] {question}. **Owner:** {who}

## Contradictions / Extensions
<!-- Anything that updates existing docs or memory. -->
- [{source doc/memory}] {what changed and why}

## Bus Factor
<!-- What does the next session need to know to continue this work? -->
- {critical context item}
```

### Step 3: Cross-Reference

After writing the dump:

1. Check each item against `memory/INDEX.md` — flag anything that should become a permanent memory note via `memctl new`.
2. Check against docs in `docs/d1/` and `docs/d2/` — flag anything that should update existing documentation.
3. List flagged items at the end of the dump under a `## Follow-Up` section.

### Step 4: Confirm

Report to the user:
- Path to the dump file
- Count of items per section
- Any follow-up actions flagged

## Key Principles

- **Grep-friendly, not prose.** One claim per line. Bracketed tags. Structured sections.
- **If it's already on disk, skip it.** Don't duplicate what's in commits, docs, or memory. Only dump what lives exclusively in the conversation.
- **Err on the side of inclusion.** When in doubt about whether something is at risk of compaction loss, include it. Disk is cheap; lost context is expensive.
- **The Bus Factor section is mandatory.** Even if everything else is thin, write what the next session needs to cold-start on this work.
