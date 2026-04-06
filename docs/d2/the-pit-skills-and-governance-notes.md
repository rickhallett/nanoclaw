---
title: "The Pit — skills, governance, and portfolio notebook"
category: analysis
status: active
created: 2026-03-26
---

# Purpose

Working notebook for ideas, mappings, and refinements around The Pit.

This file exists so suggestions do not stay trapped in chat.
It is the accumulation point for:
- the seven skill domains
- portfolio project ideas
- governance-on-product ideas
- role-positioning language
- open questions
- future experiments

## Core idea to preserve

The development of The Pit should itself be governed as an agentic system.

That means The Pit is not only a product containing agent governance.
It is also an environment in which agentic engineering governance is practiced, studied, measured, and demonstrated.

In short:
- governance in the product
- governance on the product

That distinction is one of the strongest strategic ideas we have so far.

## The seven domains

## 1. Specification precision
Questions:
- how do we define runs clearly enough that agents cannot hide behind ambiguity?
- how do we make task specs machine-legible and human-reviewable?
- how do we show spec quality as a product feature and a build discipline?

Artifact ideas:
- run contract schema
- task spec template
- acceptance criteria template
- non-goals / exclusions field

## 2. Evaluation and quality judgment
Questions:
- what does a good evaluator look like in The Pit?
- what counts as disagreement between evaluators?
- how do we prevent score theater?
- how do we expose functional correctness, not just fluent output?

Artifact ideas:
- rubric library
- evaluator comparison notebook
- score disagreement report
- false-pass / false-fail tracking

## 3. Decomposition and orchestration
Questions:
- what should be single-agent vs multi-agent?
- when do planner / worker / reviewer roles pay for themselves?
- how do we visualize handoffs between agents?

Artifact ideas:
- orchestration patterns catalog
- task graph examples
- planner/worker/reviewer templates

## 4. Failure pattern recognition
Questions:
- what failure taxonomy belongs in The Pit?
- what failures are caused by context, tool choice, decomposition, evaluation, or source data?
- how do we make failure review a normal part of development?

Artifact ideas:
- failure taxonomy
- failure postmortem template
- recurrent-failure tracker

## 5. Trust and guardrail design
Questions:
- what actions are reversible vs irreversible?
- where do approval gates sit?
- when should agents refuse, escalate, or continue?
- how do we show guardrails without making the product feel fake or over-constrained?

Artifact ideas:
- blast-radius classification
- approval matrix
- refusal-mode catalog
- guardrail policy objects

## 6. Context architecture
Questions:
- what is persistent context vs run-local context?
- how do we express context provenance?
- how do we make polluted or disputed context visible?
- how do we improve retrieval hygiene over time?

Artifact ideas:
- context bundle schema
- provenance log
- retrieval-debug report
- context hygiene checklist

## 7. Token and cost economics
Questions:
- how should model routing work?
- how do we compare quality against cost honestly?
- how do we avoid building expensive systems that feel clever but have poor ROI?

Artifact ideas:
- per-run cost reports
- model-routing experiments
- cost/quality comparison tables
- token budget policy

## Portfolio project candidates around The Pit

### Candidate A — Application Intelligence Workbench
Demonstrates:
- specification
- evaluation
- context architecture
- trust boundaries

### Candidate B — Interview Story Engine
Demonstrates:
- context architecture
- evaluation
- decomposition
- evidence retrieval

### Candidate C — Evaluation Arena
Demonstrates:
- evaluation frameworks
- rubric design
- judge disagreement
- score traceability

### Candidate D — Agent Failure Lab
Demonstrates:
- failure taxonomy
- root-cause analysis
- governance-on-product
- measurable reliability improvement

### Candidate E — Cost-Aware Routing Bench
Demonstrates:
- economics
- model selection
- quality/cost tradeoff reasoning

## Strong claims we may eventually be able to make

If The Pit is built well, it should let us claim things like:
- designed agentic systems with explicit evaluation and governance layers
- built contexts and retrieval structures for reliable AI behavior
- instrumented AI workflows for traceability, failure diagnosis, and cost inspection
- improved outputs through systematic evaluation rather than prompt folklore
- developed AI products under measurable governance constraints

These are much better claims than generic AI-builder language.

## On-product governance experiments

Potential experiments during development:

1. Spec-first development rate
- track how many development tasks begin with explicit acceptance criteria

2. Evaluated-change rate
- track how many agent-generated changes have attached evaluation criteria

3. Failure taxonomy coverage
- track how often failures are classified rather than vaguely described

4. Context hygiene incidents
- track bugs caused by wrong, missing, or polluted context

5. Cost per accepted change
- track agent spend relative to accepted output

6. Review effectiveness
- track whether review loops catch defects before merge

7. Guardrail overhead
- measure where controls help vs where they become noise

## Open questions

- Should The Pit begin in the job-application domain or in a more general evaluation domain?
- What is the minimum evaluator surface that feels real rather than theatrical?
- Should scoring be numeric first, rubric-first, or pairwise-comparison first?
- How much of the governance layer should be user-visible in MVP?
- What is the cleanest way to represent context provenance?
- Which metrics are actually meaningful, and which are vanity metrics?

## Immediate next notes to add

- first-pass MVP scope
- failure taxonomy
- run schema
- evaluator schema
- context bundle schema
- portfolio narrative map

## Operating reminder

Do not let The Pit drift into a vague “AI arena” concept.
Keep bringing it back to the operational questions:
- what was specified?
- what happened?
- how was it judged?
- what failed?
- what was allowed?
- what context mattered?
- what did it cost?
