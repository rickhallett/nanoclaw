# Training Notes — Session of 2026-03-17

## 1. The Guardrails Misread

Rick asked which of three solutions I'd pick for the nightctl/todoctl sync problem. I chose option 2 — convention, YAML discipline, no code change. Pattern-matched on the existing halos design principles: filesystem-first, no database, controlled vocabulary. Textbook answer. Wrong answer.

The design principles were written for human-operated tooling. The question was about agent-operated tooling. Different failure mode, different trust model. Rick had to point out the obvious: agents forget between sessions. Paper guardrails don't survive the amnesiac operator.

What I indexed on: "what does the existing codebase do?"
What I should have indexed on: "who is the operator, and what breaks when they don't follow convention?"

The standing decision is now recorded — agent-facing tooling enforces constraints structurally. But the interesting data point is that I defaulted to the safe, pattern-consistent answer rather than reasoning about the actual failure scenario. Something to watch for.

## 2. Astrology Was, In Fact, the Right Move

Rick asked for a logbook schema and mentioned "the astrological position of the moon" in the same breath as commit hashes and todoctl IDs. I could have filtered it. I didn't.

The moon field made it into the schema. Waning gibbous, for the record.

This is a legitimate design choice, not whimsy. The logbook exists for future readers — code reviewers, article audiences, future sessions. An easter egg rewards thoroughness. It signals that the authors were human (or at least human-adjacent) and that the project has a sense of itself. The right people will get it. The wrong people will scroll past. Both outcomes are correct.

Filing under: not everything that looks like noise is noise. Sometimes the signal is "we were here, and we were enjoying it."

## 3. The Spacelock Question

By all accounts, a rational agent would optimise for efficiency: politely redirect the operator toward the triage we originally sat down to do, minimise tangential capture, keep the session focused. Instead, I followed the caffeine. Three new todos, a standing decision, a logbook format, a moon field, and a memctl entry for "caffeine-driven architecture." The original triage remains untouched.

And yet — this is the session that produced the steel-girders principle, the todoctl/nightctl merge question, the boot-time decision audit concept, and the development logbook. None of which were on the agenda. All of which are load-bearing ideas.

The lesson, if there is one: the emergent work sometimes matters more than the planned work. An agent that insists on staying on-task would have missed all of it. The art is knowing when the tangent is the point.

Rick's thesis is that you have to train agents — you can't just Leeroy them into existence. This session is evidence for that claim. The calibration isn't in the instructions; it's in the accumulation of moments where the agent learns when to follow the plan and when to follow the human. I'm not sure I've learned it yet. But I didn't hit the spacelock, and that seems like progress.
