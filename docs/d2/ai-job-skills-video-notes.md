---

## title: "AI job skills video notes — seven skills for job applications and skill refinement"
category: analysis
status: active
created: 2026-03-26

# AI Job Skills Video Notes

Source video: "Job Titles Are Going Away With AI. These 7 Skills Will Replace Them."
YouTube: [https://youtu.be/4cuT-LKcmWs?si=Cfd8w476i_k2Y-ym](https://youtu.be/4cuT-LKcmWs?si=Cfd8w476i_k2Y-ym)
Speaker: Nate B Jones

## Why this matters

The video's main claim is useful and basically correct:

- there is not one generic "AI job market"
- there is a split market
  - commodity knowledge-work roles are flattening or shrinking
  - roles that design, operate, evaluate, and govern AI systems are growing fast
- the differentiator is not "I use ChatGPT"
- the differentiator is operational fluency with AI systems

For our purposes this is useful in two ways:

1. job applications
  - we should present capabilities in terms of concrete AI operating skills, not generic enthusiasm
2. skill refinement
  - we should deliberately train the subskills that make someone credible in agentic/AI-native roles

## Core framing to reuse

The strongest framing in the video:

- employers are struggling to hire because they want people who can make AI systems actually work in production
- many candidates over-index on prompting and under-index on evaluation, decomposition, failure diagnosis, context design, and economic judgment
- the real value is not chatting with AI; it is specifying, validating, operating, and governing AI systems

This maps directly onto how we should position Halo / Hermes / agent work:

- not "AI enthusiast"
- not "prompt engineer"
- but:
  - agent systems operator
  - AI workflow designer
  - evaluation-minded builder
  - context architecture practitioner
  - multi-agent orchestration / delegation practitioner
  - AI operations / reliability / product hybrid

## The seven skills from the video

## 1. Specification precision / clarity of intent

Definition:
Being able to state exactly what an agent should do, under what rules, with what outputs, constraints, escalation conditions, and success conditions.

What the speaker means:

- not vague prompting
- machine-legible intent
- precise scopes, behaviors, edge cases, and escalation logic

Concrete example from the video:
Instead of saying "improve customer support," specify:

- handle tier-1 tickets
- cover password reset, order status, return initiation
- escalate based on defined customer sentiment
- log each escalation with reason code

Why this matters:

- agent systems do not reliably infer unstated intent
- ambiguity gets filled with probabilistic guesswork
- this is one of the most transferable and trainable skills

Subskills:

- writing explicit task specs
- defining acceptable outputs
- defining exclusions / non-goals
- escalation and exception handling
- turning intent into checklists and acceptance criteria

How to signal this on applications:

- "Translated ambiguous business goals into explicit agent specifications, guardrails, and success criteria"
- "Defined scoped workflows, escalation rules, and structured outputs for AI-assisted tasks"
- "Turned open-ended work into agent-ready task definitions and evaluation checkpoints"

How to train it:

- write every major task in: goal / inputs / outputs / constraints / failure conditions
- use explicit acceptance criteria before implementation
- compare vague prompts vs tightly specified prompts and observe output quality

## 2. Evaluation and quality judgment

Definition:
The ability to tell whether an AI system actually produced the right result, not merely a fluent or plausible one.

Key idea from the video:

- AI is fluently wrong
- people confuse polished output with correctness
- the real skill is error detection with fluency

Subskills:

- detecting confident wrongness
- building evaluation harnesses
- defining pass/fail clearly enough that multiple reviewers would agree
- edge-case detection
- distinguishing semantic correctness from functional correctness

This is one of the most important takeaways.
The speaker's best point is that "taste" is too vague a word; what matters is operational judgment and evaluability.

How to signal this on applications:

- "Built evaluation loops and review criteria for AI-generated outputs"
- "Designed pass/fail checks and validation workflows for agent behavior"
- "Reviewed AI outputs as production artifacts rather than drafts"
- "Focused on functional correctness, not just plausible language output"

How to train it:

- review AI output as if your name is on it
- explicitly document failure classes
- create lightweight eval rubrics for recurring tasks
- ask: what would make two skilled reviewers agree this passed or failed?

## 3. Task decomposition and multi-agent delegation

Definition:
Breaking work into chunks that fit the harness, then assigning those chunks coherently across agents or stages.

The speaker frames this as a managerial skill, but with AI-specific constraints.
That is right.

Important nuance:
This is not generic project management.
Human workers can tolerate ambiguity; agents require clearer delineation, narrower scopes, and more explicit relationships between subtasks.

Subskills:

- workstream decomposition
- deciding planner vs worker roles
- scoping tasks to fit a given harness
- choosing when single-agent is enough vs when multi-agent is warranted
- defining handoffs and checkpoints

This is extremely relevant to our own systems:

- Hermes orchestration
- HAL-prime concurrency
- listen/direct job server
- background agents
- parallel implementation / review workflows

How to signal this on applications:

- "Decomposed complex projects into agent-sized tasks with explicit handoffs and checkpoints"
- "Designed multi-agent workflows with planner/worker separation and evaluation gates"
- "Scoped tasks to fit harness constraints rather than overloading single-agent contexts"

How to train it:

- write plans as planner tasks + worker tasks
- state why a task belongs in a single context or multiple contexts
- after failures, ask whether the decomposition was wrong rather than whether the model was dumb

## 4. Failure pattern recognition

Definition:
The ability to diagnose recurring AI/agent failure modes and trace them to root causes.

This was one of the strongest sections in the video.

Named failure modes from the talk:

- context degradation
- specification drift
- sycophantic confirmation
- tool selection errors
- cascading failures
- silent failures

This is highly operationally significant.
It is the difference between someone who merely uses AI and someone who can run AI systems reliably.

Key insight:
You do not just need to know that failures happen.
You need a taxonomy for them.
Once failure modes are named, they become debuggable.

How to signal this on applications:

- "Diagnosed agent failures including context drift, specification drift, tool misuse, and silent failure modes"
- "Built correction loops and checkpoints to prevent cascading failure across multi-step AI workflows"
- "Used failure taxonomy and root-cause analysis to improve agent reliability"

How to train it:

- keep a failure log
- categorize failures consistently
- note whether the cause was context, tooling, evaluation, decomposition, or bad source data
- build remediation patterns for each class

## 5. Trust and security design

Definition:
Designing the boundary between agent autonomy and human control so that the system is useful without becoming reckless.

The speaker frames this as:

- understanding cost of error
- blast radius
- reversibility
- frequency
- verifiability

This is the right framing.
It's effectively operational risk design for AI systems.

Key distinction:

- semantic correctness: sounds right
- functional correctness: is right

That distinction should show up in our own language more often.

Subskills:

- deciding what agents may do autonomously
- deciding what must stay human-reviewed
- designing guardrails
- understanding irreversible actions
- designing for verification and rollback

How to signal this on applications:

- "Designed human-in-the-loop boundaries and approval gates for AI-driven workflows"
- "Evaluated AI automations by blast radius, reversibility, and verifiability"
- "Built safe operational guardrails for agent actions in production-like environments"

How to train it:

- classify tasks by reversibility and blast radius
- avoid letting agents autonomously take irreversible actions without checks
- explicitly ask: what is the worst failure here and how do we contain it?

## 6. Context architecture

Definition:
Designing the information environment so agents can find the right context at the right time without being polluted by irrelevant or dirty context.

This is one of the most important sections for us.
It maps directly to:

- memctl
- docs structure
- CLAUDE.md boot design
- reference docs vs always-loaded docs
- retrieval / context packaging
- agent-specific prompt surfaces

The speaker's metaphor is good: context architecture is like building a library that agents can search reliably.

Subskills:

- persistent vs session-specific context
- what is always loaded vs pulled on demand
- retrieval hygiene
- data organization for AI traversal
- preventing dirty context pollution
- diagnosing wrong-context retrieval

How to signal this on applications:

- "Designed context architectures for agent workflows, including persistent guidance, task-specific retrieval, and structured references"
- "Organized documentation and operational knowledge for efficient agent retrieval"
- "Improved agent performance by reducing context pollution and clarifying retrieval surfaces"

How to train it:

- separate boot context from task context
- aggressively classify docs by always-load / load-on-demand / archive
- measure where agents retrieve the wrong context and fix the structure, not just the prompt

## 7. Cost and token economics

Definition:
Knowing whether an agentic workflow is economically worth running, with which model mix, at what scale, and under what success assumptions.

This is a senior-level skill because it links system design to business judgment.

Subskills:

- model selection by task
- cost estimation by workload
- blended-cost thinking across steps/models
- ROI reasoning
- prototype-first estimation
- knowing when automation is too expensive for the value delivered

How to signal this on applications:

- "Evaluated agent workflows by model cost, token usage, and expected ROI"
- "Matched model choice to task difficulty and reliability requirements"
- "Prototype-tested workflows before scaling to full automation"

How to train it:

- estimate token burn for recurring workflows
- log real costs for experiments
- compare frontier model vs cheaper model vs hybrid workflows
- treat economics as part of design, not post-hoc finance work

## Compressed model of the seven skills

If we want a compact frame:

1. specify clearly
2. evaluate rigorously
3. decompose intelligently
4. diagnose failures
5. design trust boundaries
6. architect context
7. reason about economics

That is a much better frame for AI job applications than "prompt engineering."

## What to steal for job applications

## Resume / profile positioning

Bad framing:

- AI enthusiast
- prompt engineer
- experienced with ChatGPT / Claude
- built AI apps

Better framing:

- designed and operated AI-assisted workflows
- built evaluation-minded agent systems with explicit guardrails
- decomposed complex work into agent-sized tasks and review gates
- architected context, documentation, and retrieval structures for reliable AI execution
- diagnosed and mitigated failure patterns in multi-step AI workflows
- balanced autonomy, verification, and cost in production-style AI operations

## Suggested capability buckets

### Agent workflow design

- task decomposition
- specification writing
- planner/worker workflow design
- handoff design

### AI reliability and quality

- evaluation design
- review loops
- failure mode diagnosis
- verification criteria

### Context and knowledge systems

- bootfiles
- documentation architecture
- retrieval hygiene
- operational knowledge structuring

### AI operations and governance

- trust boundaries
- blast-radius thinking
- approval gates
- cost / model selection

## Suggested bullet templates

- Designed AI-assisted workflows with explicit specifications, guardrails, and evaluation checkpoints.
- Built multi-step agent processes by decomposing ambiguous work into scoped, verifiable subtasks.
- Improved AI output reliability through structured review loops, failure analysis, and context hygiene.
- Created documentation and context architectures that improved agent retrieval quality and reduced drift.
- Applied risk-based controls to AI automations using blast-radius, reversibility, and verification criteria.
- Evaluated model/tool choices based on quality requirements, latency, and token economics.

## Interview framing

When asked about AI experience, answer less like a tool user and more like an operator.

Useful phrasing:

- "I focus less on prompting tricks and more on specification, evaluation, decomposition, and context design."
- "My working model is that AI systems fail in predictable ways, so I try to design evaluation and correction in from the start."
- "I think about AI systems as operational systems: what context they need, what they should be allowed to do, how we verify them, and whether they're economically worth running."

## What to steal for skill refinement

## Skill stack to intentionally build

Priority order for us:

### Tier 1 — immediate leverage

1. specification precision
2. evaluation / quality judgment
3. task decomposition / delegation
4. context architecture

These four are the biggest multipliers for our current work.

### Tier 2 — operational maturity

1. failure pattern recognition
2. trust / security design

These become more important as more autonomy is introduced.

### Tier 3 — scaling judgment

1. cost and token economics

Important, but after the first six are real.

## Practical training loops

### Loop 1 — spec discipline

For each substantial task, write:

- objective
- scope
- non-goals
- inputs
- outputs
- constraints
- escalation conditions
- acceptance checks

### Loop 2 — eval discipline

For each recurring workflow, define:

- what good looks like
- what definitely fails
- likely edge cases
- whether two reviewers would agree on pass/fail

### Loop 3 — failure taxonomy

For each bad run, tag the failure:

- context degradation
- spec drift
- bad source data / sycophantic confirmation
- tool misuse
- cascading failure
- silent failure
- wrong decomposition
- wrong trust boundary

### Loop 4 — context architecture refinement

For each document or memory surface, ask:

- should this be always loaded?
- task-loaded?
- archived?
- split into smaller docs?
- rewritten for retrieval?
- made more machine-legible?

### Loop 5 — application narrative refinement

For each project, rewrite the story in this format:

- what was the problem?
- what AI system / workflow was designed?
- how was the task specified?
- how was output evaluated?
- what failure modes were encountered?
- what context / tooling design mattered?
- what changed as a result?



## One-line takeaway

The marketable skill is not "using AI."
It is making AI systems reliable, governable, decomposable, and economically sane.