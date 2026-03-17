# The Crossroads: discovering-ben × nanoclaw × BATHW

2026-03-17

## What I found

`/home/mrkai/code/dormant/clients/project-ben/discovering-ben` is a research project analysing 255 conversations (5,338 messages) between Ben (Rick's brother, autistic, age 37) and Claude over 26 days. It identifies seven "vicious cycles" where well-intentioned LLM behaviour compounds autistic cognitive difficulties.

The central finding: **60-70% of the dysfunction originates from LLM behaviour patterns, not user behaviour.** The four pathological LLM patterns: over-provisioning, over-compliance, over-apology, and task-focus during distress.

## The seven cycles

| Cycle | What happens | How bad |
|-------|-------------|---------|
| Information Overload | User asks for certainty, LLM over-provisions, overwhelm increases | 100% of cases |
| Decision Paralysis | Binary thinker gets 7 options, abandons | 92.2% abandonment |
| Perfectionism Escalation | Impossible standards, LLM complies, endless refinement | 71.9% incompletion |
| Emotional Dysregulation | Frustration, LLM ignores emotion and does the task | 100% no baseline return |
| Mind Reading | Theory of mind gaps, LLM assumes context | Mild, manageable |
| System Building | Barely exists | 0.8% |
| Special Interest Hyperfocus | Actually productive | 60% positive |

## Why this matters for the crossroads

The port function brainfart from this morning — "give my brother HAL, just on Telegram" — is not just a feature request. It's the natural next step of a multi-year research arc.

Rick has already:
1. Quantified the dysfunction (255 conversations, statistical evidence)
2. Identified the LLM-side culpability (60-70%)
3. Built a repeatable analysis pipeline
4. Proposed concrete design principles (scoped defaults, single options, boundary-setting, emotional awareness)

What he hasn't done yet:
5. Built an AI assistant that implements those principles
6. Tested it with Ben
7. Measured the delta

Steps 5-7 are what nanoclaw + the port function would do. HAL's personality instructions (sardonic, not sycophantic, opinions allowed, brevity) already address several of the pathological LLM patterns. The scoped-defaults principle aligns with "brevity is the soul." The anti-sycophancy rule directly counters over-compliance.

## The BATHW angle

This is not portfolio filler. This is:
- Rare empirical data (n=1, but 5,338 messages deep)
- A repeatable methodology with code
- A concrete system redesign derived from data
- A before/after measurement opportunity (give Ben HAL, run the same detectors)

The positioning writes itself: "I analyse how LLM training creates specific dysfunction patterns for specific cognitive profiles — and then I build systems that fix them."

## What's technically portable

1. **Analysis pipeline** — production-ready at `analysis_pipeline/`, could run on HAL-Ben conversations
2. **Vicious cycle detectors** — 7 Python scripts, modular, could become a halos module
3. **Conversation schema** — type-safe dataclasses for Claude export data
4. **MkDocs site** — complete static site, deployment-ready

## The strange intersection

Software engineer + former psychotherapist + Zen practitioner + brother of an autistic power user + builder of agent systems. That's not a CV. That's a Venn diagram with one person in the middle.

## Refs

- Project: `/home/mrkai/code/dormant/clients/project-ben/discovering-ben`
- memctl note: `20260317-104356-413`
- Port function todo: `20260317-102759-948`
- Personality instructions: `CLAUDE.md` Personality section
