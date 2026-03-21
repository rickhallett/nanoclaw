---
title: "Patterns and Lessons — 2026-03-18 Session"
category: journal
status: active
created: 2026-03-18
---

# Patterns and Lessons — 2026-03-18 Session

> Captured hot. 16 commits, fleet provisioned, eval harness built, dialogue scenarios passing.

## 1. The State Leakage Class

**Problem:** Every test failure that looked like "the agent thinks X already happened" was state leaking between runs. Four distinct layers of persistence, each capable of contaminating the next run independently:

| Layer | What it stores | How it leaks |
|-------|---------------|--------------|
| SQLite (messages, sessions, assessments) | Conversation history, session IDs, assessment answers | Agent sees prior test messages as real conversation |
| onboarding-state.yaml | Likert completion, deferral state | Agent skips assessment because yaml says it's done |
| Claude SDK session data (data/sessions/) | Full conversation transcript | Agent "remembers" things that happened in a prior test |
| pm2 log files | Agent output from all runs | Eval harness matches stale output from prior scenarios |

**Solution:** Nuclear reset between scenarios — all four layers cleared. The `afterEach` equivalent for non-deterministic agent testing is more aggressive than typical test teardown because the state surface is wider than the code surface.

**Lesson:** If your test subject has memory, your teardown must be as thorough as its recall.

## 2. The Detection Fragility Class

**Problem:** Assertions that check for specific keywords ("done", "complete", "finished") fail when the agent uses synonyms ("that's the last of them", "all wrapped up"). The agent is correct; the test is brittle.

**Pattern:** Three iterations on every assertion type:
1. First attempt: exact keyword match → fails on natural variation
2. Second attempt: expanded keyword list → catches more but still misses
3. Final form: check for absence of error signals rather than presence of success signals

**Solution:** Invert the assertion. Instead of "response contains 'got it'", check "response is non-empty AND does not contain 'invalid/error/try again'". This is robust to phrasing variation while still catching real failures.

**Lesson:** When testing non-deterministic systems, assert on what should NOT happen rather than what SHOULD happen. The space of correct responses is infinite; the space of incorrect responses is enumerable.

## 3. The Governance Precedence Class

**Problem:** The agent received two competing directives:
- "You MUST deliver Likert before doing anything else" (labelled CRITICAL)
- "After 3 deflections, relent and stop asking"

The MUST won every time. The agent refused to relent because the higher-priority directive overrode the escape valve.

**Solution:** Explicit precedence language: "The three-strike rule OVERRIDES the requirement above." Also required: carve-outs for edge cases ("the ban on re-raising is about YOU pushing — not about the user pulling").

**Lesson:** LLMs resolve competing instructions by weight (position, emphasis, labelling). If you want an override, you must name it as one. Implicit priority doesn't work — the model will default to whichever instruction is louder.

## 4. The Multi-Line Log Parsing Class

**Problem:** Agent responses span multiple lines in pm2 logs. The initial regex `Agent output: (.+)` captured only the first line. Likert questions appeared on continuation lines and were invisible to the eval harness.

**Pattern:** pm2/pino logs use timestamp prefixes. Multi-line output has:
```
[HH:MM:SS] Agent output: First line of response
continuation line (no timestamp)
continuation line
[HH:MM:SS] Next log entry
```

**Solution:** Parse until next timestamp-prefixed line. Concatenate continuation lines with the initial match.

**Lesson:** Log formats are contracts. If your log format allows multi-line entries, your parser must handle them from day one. A regex that matches single lines will silently truncate structured output.

## 5. The Proxy Routing Class

**Problem:** Fleet instances bind their credential proxy on a unique port (3874, 3751, etc.) but containers need to reach prime's proxy on port 3001. The original approach patched source files post-copy with string matching — which silently failed when the source changed.

**Evolution:**
1. String-matching patch (`_patch_container_proxy_port`) → brittle, failed silently on Mum's instance
2. Manual sed fix → worked once, not repeatable
3. Upstream `CONTAINER_PROXY_PORT` into prime's source → fleet instances override via ecosystem config, no patching

**Lesson:** If you're patching source code after copying it, you're one refactor away from silent failure. Upstream the config. Make the source work for both contexts natively.

## 6. The Provisioning Completeness Class

**Problem:** `halctl create` produced an instance that required 4-5 manual post-steps:
1. `npm install` (node_modules excluded from copy)
2. Register operator chat (manual node -e command)
3. Fix skills permissions (cpSync needs 755)
4. Clear stale sessions (store/ copied from prime)
5. Hardcode bot token in ecosystem config

Each of these caused a "bot not responding" failure that took 5-10 minutes to diagnose.

**Solution:** Bake each fix into the provisioning pipeline as it was discovered:
- `npm install` → still manual (platform-specific, correct to exclude)
- Operator registration → `_register_operator_chat()` in create
- Skills permissions → lock exemptions in fleet-config.yaml
- Stale sessions → `store/` added to exclude list
- Bot token → still manual (BotFather ceremony, unavoidable)

**Lesson:** Every manual post-provisioning step is a bug in the provisioning system. If you did it by hand once, automate it immediately — you will do it again, and you will forget a step.

## 7. The Dialogue Pacing Class

**Problem:** Multi-turn eval scenarios send bare numbers ("3", "4") as Likert answers. The agent sometimes doesn't understand because its previous message was a greeting, not a question. The bare number has no context.

**Solution:** Add context to injected messages: "for the comfort question, I'd say 4" instead of just "4". This mirrors how real users actually talk — they don't send bare integers.

**Lesson:** Test messages should model real user behaviour, not idealised input. If your test sends something a real user wouldn't send, the test is testing the wrong thing.

## 8. The Governance Wording Class

**Problem:** Instructions like "read this file and follow its protocol" were ignored on first turn. The agent prioritised responding to the user's greeting over reading a governance file.

**Solution:** Inline the critical check directly in the CLAUDE.md: "CRITICAL — check on every session start: read onboarding-state.yaml. If no likert_responses, MUST deliver assessment."

**Pattern:** Three tiers of governance effectiveness:
1. "Read file X for instructions" → often skipped (deferred read)
2. "Follow this protocol: [summary]" → sometimes followed (compressed)
3. "CRITICAL — check Y. If Z, MUST do W." → reliably followed (inline, imperative, specific)

**Lesson:** Agent governance follows the same rules as human communication: if it's important, say it directly. Don't make the reader go find the important part.

## Meta-Pattern

Every class of problem above has the same root: **the gap between what you think you specified and what actually executes.** The provisioning system thought it was complete. The governance thought it was clear. The assertions thought they were robust. The state reset thought it was thorough.

Testing narrows the gap. But the gap is fractal — each fix reveals a smaller gap underneath. The discipline is knowing when the gap is small enough to ship.

Tonight's answer: when the dialogue scenarios pass and the agent handles tangents, deflections, and edits gracefully, the gap is small enough for family.
