# Plan: Parameterised Personality Configuration for microHAL Fleet

## Context

The discovering-ben research (619 conversations, 4,456 human messages) proved that personality calibration has measurable impact — 7 identified patterns where default RLHF behaviour amplifies cognitive difficulties. We just deployed research-backed interventions as prose in Ben's CLAUDE.md.

The next question: how to make this **repeatable and measurable** across multiple users. Rick's hypothesis is that iterating with a technical+psychological sidecar converges on alignment faster than solo use. To test that hypothesis, we need structured personality configuration with quantitative dimensions, not just hand-crafted prose.

### Current State

- `templates/microhal/` has three layers: `base.md` (governance) + `personality/{name}.md` (tone) + `user/{name}.md` (context)
- `compose_claude_md(personality, user_name)` concatenates them
- `fleet-config.yaml` maps users to personality names: `ben: { personality: discovering-ben }`
- **Loose end from today:** `personality/discovering-ben.md` (template) is now stale — the deployed CLAUDE.md was edited directly with the new DO/DON'T protocol. This plan subsumes that sync issue.

---

## Architecture: Three Separable Concerns

### 1. Schema — What dimensions exist

`templates/microhal/personality-schema.yaml`

Discrete ordinal levels (not continuous floats — we have N=1, false precision helps no one). Each dimension has named levels that map to prose blocks.

**Categories and dimensions:**

| Category | Dimension | Type | Levels / Range | Default |
|---|---|---|---|---|
| Information Scoping | `brevity` | ordinal | verbose, moderate, terse, minimal | moderate |
| | `summary_default` | boolean | | false |
| | `overwhelm_detection` | boolean | | false |
| Decision Support | `max_options` | integer | 1–5 | 3 |
| | `recommendation_strength` | ordinal | neutral, leaning, directive | leaning |
| | `paralysis_detection` | boolean | | false |
| Task Completion | `completion_signalling` | ordinal | implicit, explicit, firm | implicit |
| | `iteration_cap` | integer | 0–10 (0 = none) | 0 |
| | `scope_creep_detection` | boolean | | false |
| Emotional Calibration | `acknowledgment_mode` | ordinal | skip, brief, contextual | skip |
| | `frustration_response` | ordinal | redirect, pause, channel | redirect |
| | `energy_riding` | boolean | | false |
| Tone | `warmth` | ordinal | clinical, neutral, warm, effusive | neutral |
| | `formality` | ordinal | formal, conversational, casual | conversational |
| | `opinion_strength` | ordinal | hedge, balanced, opinionated | balanced |
| | `apology_suppression` | boolean | | false |

16 dimensions across 5 categories. The discovering-ben research maps cleanly onto these — each of the 7 cycles corresponds to 2-3 dimensions.

### 2. Profiles — Individual set points

`templates/microhal/profiles/{name}.yaml`

```yaml
schema_version: 1
dimensions:
  brevity: minimal
  summary_default: true
  overwhelm_detection: true
  max_options: 1
  recommendation_strength: directive
  # ... etc
provenance:
  brevity: { source: discovering-ben, confidence: high }
  # ... etc
changelog:
  - date: 2026-03-17
    changed: [all]
    reason: "Initial calibration from discovering-ben research"
    source: programmatic
    approved_by: rick
```

- Flat dimension namespace (categories for docs/ordering only)
- Provenance tracks where each setting came from
- Changelog is append-only — combined with git history, full audit trail

### 3. Blocks — Prose fragments, multi-dimension where natural

`templates/microhal/blocks/`

Blocks are self-contained markdown sections. A block **may cover multiple dimensions** when the prose reads more naturally that way — e.g., `completion_and_iteration.md` covers `completion_signalling`, `iteration_cap`, and `scope_creep_detection` together because the DO/DON'T examples interweave them.

**Block naming convention:**
- Single-dimension: `blocks/{dimension}/{level}.md` (e.g., `blocks/brevity/minimal.md`)
- Multi-dimension: `blocks/{primary_dimension}/{level}.md` with a frontmatter `covers:` field listing all dimensions it satisfies
- Boolean: `true.md` / `false.md` (where `false.md` is often empty — no instruction = default LLM behaviour)

**Block frontmatter** (optional, only needed for multi-dimension blocks):
```yaml
---
covers: [completion_signalling, iteration_cap, scope_creep_detection]
activates_when:
  completion_signalling: firm
  iteration_cap: ">0"
---
```

The renderer tracks which dimensions have been satisfied. If a multi-dimension block covers dimensions X, Y, Z, it skips individual blocks for Y and Z.

**Fixed preamble:** `blocks/_preamble.md` is always included first, before any dimension blocks. Contains the "Bounded helpfulness beats unbounded compliance" meta-framing. Not parameterised — every microhal gets this grounding regardless of their dimension settings.

**Why blocks over Jinja2:** No new dependency. Each fragment is independently readable. Rick can audit any block without understanding a template engine. The rendering pipeline is trivially testable.

---

## Rendering Pipeline

New file: `halos/halctl/renderer.py` (~60 lines)

```
load schema → load profile → validate profile against schema →
emit blocks/_preamble.md →
for each category in schema-defined order:
  emit category heading (## Response Discipline, etc.) →
  satisfied = set()
  for each dimension in category:
    if dimension in satisfied: skip
    look up blocks/{dimension}/{value}.md →
    if block has frontmatter `covers:`, add all covered dims to satisfied →
    if block exists and non-empty, include it →
return prose string
```

Modified: `halos/halctl/templates.py` — `compose_claude_md()` tries YAML profile first, falls back to legacy `.md` files. Zero migration pressure.

**Key invariant:** Same profile + same blocks = same output. Deterministic, no LLM in the pipeline.

---

## Data Collection & Feedback Loop

### Channel A: Structured Interview (Phase 2)

`halctl calibrate --name ben --mode interview`

Walks Rick through each dimension: current value → prose it produces → confirm or adjust. Outputs profile diff. Rick approves and commits.

### Channel B: Conversation Analysis (Phase 3)

`halctl calibrate --name ben --mode analyse`

Heuristic pattern detection on conversation logs (not LLM-based initially):
- Option-seeking frequency → `max_options`, `paralysis_detection`
- Response length trends → `brevity`
- Iteration depth per task → `iteration_cap`
- Frustration markers → `frustration_response`

Outputs suggestions as a report. Rick reviews, applies, commits. **Human gate is load-bearing** — no auto-applied changes.

---

## Phased Implementation

### Phase 1: Prove the concept (~15 agent-min + ~20 human-min)

Goal: `halctl create --name ben` produces the same CLAUDE.md it does today, but from parameterised sources.

1. Create `templates/microhal/personality-schema.yaml`
2. Create `templates/microhal/profiles/ben.yaml` (reverse-engineer from today's deployed CLAUDE.md)
3. Create `templates/microhal/profiles/default.yaml` (baseline values)
4. Decompose today's Ben personality sections into `templates/microhal/blocks/` (one file per dimension×level)
5. Write `halos/halctl/renderer.py` — pure function, loads YAML + reads blocks + concatenates
6. Modify `halos/halctl/templates.py` to try YAML profile before legacy fallback
7. Test: render Ben's profile, verify output matches deployed CLAUDE.md
8. **Sync fix:** Update `templates/microhal/personality/discovering-ben.md` with today's changes (or deprecate it entirely since the block library supersedes it)
9. Run gate

### Phase 2: Onboarding interview (~10 agent-min + ~15 human-min)

1. Add `halctl calibrate --name <name> --mode interview` CLI command
2. Wire Likert data from `onboarding.py` into initial profile seeding
3. Test with a new hypothetical user to verify the flow

### Phase 3: Conversation analysis (~20 agent-min + ~30 human-min)

1. Create `halos/microhal/calibrate.py` with heuristic analysers
2. Add `halctl calibrate --name <name> --mode analyse`
3. Test against Ben's conversation history as ground truth

### Phase 4: Hypothesis validation (ongoing, not code)

The tooling from phases 1-3 enables:
- Provision new user with default profile
- Seed via interview
- Monitor and iterate via analysis
- Compare convergence: Rick-calibrated vs self-serve

---

## Files to Create/Modify

| File | Action | Phase |
|---|---|---|
| `templates/microhal/personality-schema.yaml` | Create | 1 |
| `templates/microhal/profiles/ben.yaml` | Create | 1 |
| `templates/microhal/profiles/default.yaml` | Create | 1 |
| `templates/microhal/blocks/` (16+ files) | Create | 1 |
| `halos/halctl/renderer.py` | Create | 1 |
| `halos/halctl/templates.py` | Modify | 1 |
| `templates/microhal/personality/discovering-ben.md` | Update or deprecate | 1 |
| `halos/halctl/cli.py` | Add calibrate command | 2 |
| `halos/microhal/calibrate.py` | Create | 3 |

## Verification

- **Phase 1:** `diff` rendered output against deployed CLAUDE.md — should be equivalent prose
- **Phase 1:** Existing `test_isolation.py` passes (backward compat)
- **Phase 1:** `halctl create --name ben` produces identical CLAUDE.md
- **All phases:** Gate passes (`make gate` or equivalent)

## Design Decisions (Resolved)

| Decision | Choice | Rationale |
|---|---|---|
| Block granularity | Multi-dimension blocks allowed | DO/DON'T prose interweaves dimensions naturally; splitting reads fragmented |
| Core Principle location | Fixed `_preamble.md` | Meta-framing applies to all users regardless of dimension settings |
| Dimension type | Discrete ordinal, not continuous | N=1, false precision helps no one; can increase resolution later |
| Rendering approach | Block library, not Jinja2 | No dependency, auditable fragments, trivially testable |
| Migration strategy | Fallback to legacy `.md` | Zero pressure; new profiles take precedence when YAML exists |
| Human gate on calibration | Always | No auto-applied changes; Rick reviews all dimension adjustments |
