---
title: "The Pit — product and portfolio specification"
category: spec
status: draft
created: 2026-03-26
---

# The Pit

## Working definition

The Pit is a multi-agent AI evaluation platform.

At product level, it is a system where models or agents conduct structured contests, debates, evaluations, and adjudicated runs inside explicit rules, with observable traces, scoring, and programmable incentives.

At portfolio level, it is also a proving ground for end-to-end AI engineering competence:
- specification precision
- evaluation and quality judgment
- decomposition and orchestration
- failure diagnosis
- trust and guardrail design
- context architecture
- token / cost economics

Crucially, governance is not only a feature of the product.
Governance is also a property of how the product is built.
The Pit should therefore operate on two layers:

1. in-product governance
   - the mechanisms by which agents inside The Pit are constrained, evaluated, audited, and compared
2. on-product governance
   - the mechanisms by which development of The Pit itself becomes a measured, reviewable, agentic engineering practice

That second layer is strategically important. The Pit can function as both:
- an AI product
- a living research and portfolio environment for agentic engineering governance

## Why this exists

There are many AI demos and many AI wrappers.
There are far fewer systems that visibly answer the real operational questions:
- how is agent intent specified?
- how is output evaluated?
- what happens when agents fail?
- what is the trust boundary?
- what context is loaded and why?
- what does this cost and is it worth it?

The Pit should be built to answer those questions in public.

## Primary goal

Build a product that makes agent performance legible, comparable, governable, and economically inspectable.

## Secondary goal

Use the product’s development process to produce portfolio evidence that the builder can design and run agentic systems with discipline.

## Users

### Primary users
- technical operators of AI systems
- AI product and engineering teams
- founders evaluating model / agent quality
- people comparing workflows, prompts, contexts, and tool strategies

### Secondary users
- hiring managers evaluating AI engineering maturity
- portfolio reviewers
- collaborators studying agent governance patterns

## Core thesis

The winning AI systems are not the ones that merely generate plausible language.
They are the ones that can be:
- clearly specified
- evaluated consistently
- decomposed into controllable parts
- debugged when they fail
- governed at the trust boundary
- fed the right context
- justified economically

The Pit should make these dimensions first-class.

## Product pillars

### 1. Contest / run orchestration
The system can run structured agent tasks:
- debates
- pairwise comparisons
- red-team / blue-team runs
- tool-using tasks
- rubric-scored tasks
- multi-step scenarios

A run is not just an output.
A run is a traceable event with setup, context, actions, outputs, scores, and auditability.

### 2. Evaluation as product surface
Evaluation is not a hidden afterthought.
The Pit should expose:
- rubrics
- judge strategies
- evaluator disagreement
- pass/fail criteria
- replayable traces
- score breakdowns
- failure tagging

### 3. Governance and trust boundaries
The system should make explicit:
- what agents are allowed to do
- what tools they may use
- what triggers refusal or escalation
- what counts as unsafe or invalid output
- what actions require human approval

### 4. Context architecture
The system should support explicit distinctions between:
- persistent context
- run-local context
- retrieved context
- prohibited / quarantined context
- dirty or disputed context

The Pit should help answer whether poor outputs came from:
- a weak model
- bad instructions
- polluted context
- missing context
- wrong decomposition
- weak evaluation

### 5. Cost and token visibility
Every serious run should expose:
- model choice
- token consumption
- latency
- blended cost
- score / cost tradeoff
- whether the run was worth the spend

## Dual-track architecture

## A. In-product governance
These are features of the platform itself.

### Candidate in-product capabilities
- structured run definitions
- evaluator modules
- trace capture and replay
- failure labeling
- configurable guardrails
- run approval gates
- audit logs
- policy objects
- scoring and adjudication
- side-by-side comparisons
- cost accounting

## B. On-product governance
These are features of the way The Pit is built and evolved.

This is the strategically distinctive move.
Development itself becomes measurable.

### Candidate on-product capabilities
- every implementation task starts from an explicit spec
- agent-produced changes require declared evaluation criteria
- failures in build/test/review are tagged by taxonomy
- prompts, contexts, and tool access are versioned
- changes to bootfiles / runbooks / docs are tracked as context architecture decisions
- model usage and token costs are logged for development workflows
- portfolio artifacts are created from real development traces rather than retrospective storytelling

### Why this matters
This turns The Pit into a portfolio engine.
Not just “look at the thing I built,” but:
- here is how the work was specified
- here is how agents were governed while building it
- here is the failure taxonomy from real runs
- here is the evidence that evaluation improved outcomes
- here is the cost / quality curve

That is much stronger than a standard project write-up.

## End-to-end skills demonstrated

## 1. Specification precision
The Pit should contain visible run specs, task specs, and acceptance criteria.
Development of The Pit should also be spec-first.

Evidence produced:
- task definitions
- run contracts
- acceptance criteria
- non-goals and safety boundaries

## 2. Evaluation and quality judgment
The Pit should make evaluation central.
Development should also include evaluator design for prompts, outputs, and implementation quality.

Evidence produced:
- scoring rubrics
- evaluator traces
- pass/fail logic
- disagreement handling
- review artifacts

## 3. Decomposition and orchestration
The product itself is about orchestrated runs.
The build process should also use planner/worker/reviewer decomposition where appropriate.

Evidence produced:
- task graphs
- agent roles
- handoff structure
- review loops

## 4. Failure pattern recognition
Both product runs and product development should generate failure logs.

Evidence produced:
- failure taxonomy
- root-cause notes
- remediation patterns
- before/after reliability improvements

## 5. Trust and guardrail design
The product should surface permission boundaries, approval gates, refusal modes, and audit trails.
The build process should use the same discipline for agentic development.

Evidence produced:
- guardrail policies
- approval rules
- safety constraints
- blast-radius reasoning

## 6. Context architecture
The product should let users inspect which context influenced outcomes.
The build process should maintain clear separation between boot context, retrieved references, and run-local context.

Evidence produced:
- context maps
- retrieval decisions
- context hygiene notes
- doc architecture rationale

## 7. Token and cost economics
The product should expose cost surfaces.
The build process should also log model choice and economics.

Evidence produced:
- run cost summaries
- model-routing rationale
- cost / quality tradeoffs
- development economics notes

## MVP shape

The MVP should be narrow and legible.
Do not start with “full AI arena platform.”
Start with the minimum version that proves the thesis.

## MVP objective
Run a structured task between two or more agent configurations, evaluate outputs, store traces, show scores, show failure tags, and show cost.

## MVP components
- run definition
- contestant configuration
- context bundle
- execution trace capture
- evaluator / rubric
- scorecard
- failure tags
- cost ledger
- run report

## MVP candidate workflow
A strong first workflow would be:
- define a task
- run two agent configurations against it
- compare outputs
- score them against explicit rubric
- record failures
- record cost and latency
- produce a report explaining why one run won

This is enough to demonstrate most of the seven skills.

## Recommended first domain
Use a domain that is both operationally relevant and portfolio-relevant.
The strongest initial candidate is likely:
- job-application and role-fit workflows

Why:
- directly useful now
- rich in evaluation surface
- easy to explain to hiring managers
- supports both product value and portfolio evidence

Examples:
- role-fit analysis contests
- cover-letter comparison runs
- CV bullet evaluation runs
- interview answer scoring runs
- evidence retrieval quality tests

## Suggested internal workstreams

### Workstream 1 — platform core
- run model
- execution model
- trace persistence
- scoring model
- report generation

### Workstream 2 — evaluation layer
- rubrics
- judges
- score normalization
- disagreement handling
- failure taxonomy

### Workstream 3 — governance layer
- permissions
- guardrails
- refusal / escalation
- audit logs
- approval gates

### Workstream 4 — context layer
- context bundle schema
- retrieval surfaces
- context provenance
- dirty-context handling

### Workstream 5 — economics layer
- token accounting
- model routing
- cost reports
- run efficiency comparisons

### Workstream 6 — portfolio evidence layer
- portfolio-ready writeups generated from real runs
- development governance logs
- before/after case studies
- skill-mapped artifacts

## Measurable outcomes

The Pit should generate measurable evidence, not vibes.

Candidate metrics:
- run success rate
- evaluator agreement rate
- false pass / false fail rate
- failure category distribution
- average cost per run
- average latency per run
- retrieval precision proxies
- guardrail trigger frequency
- human override frequency
- score improvement across iterations

For on-product governance:
- percentage of tasks started with explicit spec
- percentage of agent changes with evaluation criteria attached
- build failures by taxonomy
- review defect rate
- cost per accepted change
- time-to-diagnosis for agent failures

## Non-goals for early phases

- broad social arena mechanics
- overbuilt gamification
- generalized autonomous everything
- opaque benchmark theater
- maximum model count for its own sake
- excessive front-end polish before evaluation core exists

## Design principles

- legibility over magic
- auditability over novelty
- evaluation over vibes
- constrained autonomy over theatrical autonomy
- narrow MVP over sprawling ambition
- real traces over retrospective storytelling

## Portfolio strategy

The Pit should be able to produce multiple portfolio artifacts before it becomes a flagship.

Those artifacts can include:
- an evaluation-heavy project slice
- a context-architecture slice
- a multi-agent orchestration slice
- a guardrails / trust-boundary slice
- an economics / routing slice

Over time, one of those slices may become the flagship.
Alternatively, The Pit may become the integrating shell that absorbs them.

## Immediate next documents to create

1. The Pit — skills and evidence map
2. The Pit — governance notebook
3. The Pit — MVP plan
4. The Pit — failure taxonomy
5. The Pit — portfolio narratives

## One-line summary

The Pit is not just an agentic product.
It is an instrumented environment for building, evaluating, and demonstrating agentic engineering competence in public.
