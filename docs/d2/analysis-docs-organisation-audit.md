---
title: "Documentation Organisation Audit"
category: analysis
status: active
created: 2026-03-15
---

# Documentation Organisation Audit

**Date:** 2026-03-21
**Analyst:** Strategic Analyst (HAL)
**Scope:** Full inventory, pattern analysis, misplacement audit, proposed standard, migration plan

---

## 1. Full Inventory

### 1.1 docs/d1/ — "Operational"

| File | Lines | Bytes | Last Modified | Frontmatter | Category (Actual) |
|------|-------|-------|---------------|-------------|-------------------|
| adversarial-review-2026-03-16.md | 88 | 5,257 | 2026-03-16 | No | Review output |
| architecture-deep-trace.md | 207 | 13,871 | 2026-03-17 | No | Architecture diagram (d2 material) |
| architecture-diagrams.md | 445 | 12,842 | 2026-03-18 | No | Architecture diagram (d2 material) |
| DEBUG_CHECKLIST.md | 143 | 5,085 | 2026-03-15 | No | Operational runbook |
| development-logbook.md | 244 | 11,259 | 2026-03-18 | No | Journal / logbook |
| eval-baseline-2026-03-18.md | 38 | 2,057 | 2026-03-18 | No | Eval results (data) |
| halos-in-brief.md | 41 | 1,875 | 2026-03-16 | No | Overview / primer |
| halos-modules.md | 26 | 1,667 | 2026-03-17 | No | Registry / reference |
| memctl-architecture-overview.md | 66 | 6,268 | 2026-03-17 | No | Architecture overview (d2 material) |
| memctl-operations.md | 156 | 5,757 | 2026-03-16 | No | Operational guide |
| microhal-operations.md | 129 | 5,334 | 2026-03-17 | No | Operational runbook |
| plan-template.xml | 70 | 2,321 | 2026-03-17 | N/A (XML) | Template |
| SECURITY.md | 122 | 6,472 | 2026-03-15 | No | Security reference |
| session-patterns-2026-03-18.md | 119 | 7,814 | 2026-03-18 | No | Lessons learned |
| briefings/2026-03-16-nightly.md | 15 | 834 | 2026-03-18 | No | Briefing |
| briefings/2026-03-17-nightly.md | 17 | 737 | 2026-03-18 | No | Briefing |
| briefings/2026-03-18-morning.md | 26 | 1,169 | 2026-03-18 | No | Briefing |
| walkthrough/index.md | 21 | 1,986 | 2026-03-20 | No | Index |
| walkthrough/001-011 (11 files) | 56-437 | 5K-24K | 2026-03-20/21 | No | Deep walkthrough |
| diagrams/*.svg (9 files) | 0 (binary) | 7K-25K | 2026-03-19 | N/A | SVG diagrams |

**d1 totals:** 27 markdown files + 9 SVG files + 1 XML template = 37 files

### 1.2 docs/d2/ — "Architecture"

| File | Lines | Bytes | Last Modified | Frontmatter | Category (Actual) |
|------|-------|-------|---------------|-------------|-------------------|
| analysis-agent-telemetry-landscape.md | 243 | 16,483 | 2026-03-17 | No | Research |
| analysis-behavioural-pattern-tracking.md | 428 | 21,363 | 2026-03-21 | No | Research/design |
| analysis-ben-usage-metrics.md | 335 | 15,411 | 2026-03-21 | No | Research |
| analysis-cli-email-clients.md | 332 | 15,638 | 2026-03-21 | No | Research |
| analysis-doc-maintenance-agent-workflows.md | 363 | 17,667 | 2026-03-21 | No | Research/design |
| analysis-google-workspace-integration.md | 157 | 10,858 | 2026-03-21 | No | Research |
| analysis-halos-agent-native-taxonomy-mapping.md | 696 | 31,360 | 2026-03-21 | No | Research/design |
| halos-architecture-review.md | 87 | 10,146 | 2026-03-17 | No | Architecture review |
| halos-capability-map.md | 331 | 21,426 | 2026-03-17 | No | Architecture map |
| halos-ecosystem-digest.md | 489 | 21,901 | 2026-03-21 | No | Architecture overview |
| memctl-spec.md | 573 | 19,039 | 2026-03-15 | No | Specification |
| nanoclaw-architecture-final.md | 1,062 | 43,689 | 2026-03-15 | No | Architecture doc (superseded?) |
| nightctl-spec.md | 406 | 13,071 | 2026-03-17 | No | Specification |
| personality-config-plan.md | 220 | 10,146 | 2026-03-17 | No | Design plan |
| principles-agent-tdd.md | 180 | 9,051 | 2026-03-21 | No | Principles doc |
| REQUIREMENTS.md | 196 | 8,464 | 2026-03-15 | No | Requirements |
| research-ai-tools-specialist-roles.md | 154 | 6,980 | 2026-03-17 | No | Research |
| review-combinatorial-pass.md | 146 | 10,819 | 2026-03-20 | No | Review methodology |
| review-responsiveness.md | 429 | 23,127 | 2026-03-20 | No | Review guide |
| review-taxonomy.md | 485 | 25,463 | 2026-03-20 | No | Review methodology |
| skills-as-branches.md | 662 | 27,363 | 2026-03-15 | No | Architecture spec |
| SPEC.md | 785 | 31,707 | 2026-03-15 | No | Core specification |
| spec-backupctl.md | 110 | 3,666 | 2026-03-21 | No | Module spec |
| spec-bathw.md | 537 | 20,921 | 2026-03-17 | No | Publication spec |
| spec-calctl.md | 98 | 3,167 | 2026-03-21 | No | Module spec |
| spec-dashctl-html.md | 83 | 2,145 | 2026-03-21 | No | Module spec |
| spec-docctl.md | 244 | 7,058 | 2026-03-21 | No | Module spec |
| spec-ledgerctl.md | 159 | 5,699 | 2026-03-21 | No | Module spec |
| spec-memctl-graph.md | 236 | 7,496 | 2026-03-21 | No | Module spec |
| spec-microhal.md | 290 | 12,343 | 2026-03-17 | No | Architecture spec |
| spec-nightctl-merge.md | 449 | 20,714 | 2026-03-17 | No | Architecture spec |
| spec-portfolio-showcase.md | 276 | 11,906 | 2026-03-17 | No | Strategy spec |
| spec-statusctl.md | 118 | 3,726 | 2026-03-21 | No | Module spec |
| briefings/6 files | 12-17 | 404-859 | 2026-03-20/21 | No | Briefing |
| reviews/12 files | 20-187 | 1.2K-10.7K | 2026-03-20 | No | Review output |

**d2 totals:** 33 standalone markdown files + 6 briefings + 12 review reports = 51 files

### 1.3 docs/d3/ — "Deep Dives + Archive"

| File | Lines | Bytes | Last Modified | Frontmatter | Category (Actual) |
|------|-------|-------|---------------|-------------|-------------------|
| APPLE-CONTAINER-NETWORKING.md | 90 | 2,992 | 2026-03-15 | No | Operational guide |
| docker-sandboxes.md | 359 | 12,313 | 2026-03-15 | No | Setup guide |
| SDK_DEEP_DIVE.md | 643 | 25,041 | 2026-03-15 | No | Deep dive |
| archive/2026-03-15-memctl.md | 2,294 | 52,972 | 2026-03-18 | No | Superseded plan |
| archive/nanorepo-architecture.md | 167 | 10,178 | 2026-03-18 | No | Superseded architecture |
| archive/db-snapshots-2026-03-18/*.sql (6 files) | 90-140 | 2.8K-44K | 2026-03-18 | N/A | Data snapshot |

**d3 totals:** 5 markdown files + 6 SQL files = 11 files

### 1.4 Aggregate Statistics

| Directory | Markdown Files | Other Files | Total Lines (md) | Total Bytes (md) |
|-----------|---------------|-------------|-------------------|-------------------|
| docs/d1/ | 27 | 10 | ~3,200 | ~180K |
| docs/d2/ | 51 | 0 | ~10,700 | ~520K |
| docs/d3/ | 5 | 6 | ~3,553 | ~103K |
| **Total** | **83** | **16** | **~17,450** | **~803K** |

---

## 2. Pattern Analysis

### 2.1 Naming Conventions

Five distinct naming patterns coexist:

| Pattern | Examples | Count | Notes |
|---------|----------|-------|-------|
| `UPPERCASE.md` | `SPEC.md`, `REQUIREMENTS.md`, `SECURITY.md`, `DEBUG_CHECKLIST.md` | 5 | Foundational/canonical docs |
| `kebab-case.md` | `memctl-operations.md`, `halos-modules.md` | ~20 | Most common pattern |
| `prefix-topic.md` | `analysis-*.md`, `spec-*.md`, `review-*.md` | ~25 | Emergent, useful prefix convention |
| `topic-YYYY-MM-DD.md` | `adversarial-review-2026-03-16.md`, `eval-baseline-2026-03-18.md` | 3 | Date suffix (inconsistent) |
| `YYYY-MM-DD-type.md` | `2026-03-16-nightly.md`, `2026-03-20-morning.md` | 9 | Date prefix (briefings only) |

The `prefix-topic` pattern is the most informative. The newer spec files (`spec-backupctl.md`, `spec-calctl.md`, etc.) all follow it consistently, with inline metadata (Date, Status, Tier, Effort) at the top. The `analysis-*` files similarly have inline Date/Analyst/Status fields. This is an emergent proto-standard, not yet codified.

### 2.2 Structure Conventions

**What exists (ad hoc):**

| Feature | Used By | Notes |
|---------|---------|-------|
| `# Title` as first line | All files | Universal |
| Inline metadata (bold key-value pairs) | Newer specs, analysis docs | `**Date:** 2026-03-21` pattern |
| `> blockquote` subtitle | Several specs | Tagline or context |
| `---` horizontal rules | Many files | Used as section separators, NOT as frontmatter delimiters |
| Table of contents | `SPEC.md` only | Manual TOC |
| Cross-references to other docs | 15+ files | Relative paths, mostly accurate |

**What does NOT exist:**

- YAML frontmatter (zero files have it)
- Standardised status fields
- Standardised category/type declarations
- Any machine-readable metadata
- Per-directory index files (except `walkthrough/index.md`)
- Canonical "last reviewed" or "superseded by" fields

### 2.3 The Emerging Proto-Standard

The newer spec files (2026-03-21 batch) show a convergent pattern:

```markdown
# title — Subtitle

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NOW | NEXT | LATER
**Effort:** ~N agent-min + ~N human-min review

---

## Purpose
...
```

This is the closest thing to a standard. Six files follow it (`spec-backupctl.md`, `spec-calctl.md`, `spec-dashctl-html.md`, `spec-docctl.md`, `spec-ledgerctl.md`, `spec-statusctl.md`, `spec-memctl-graph.md`). The analysis files have a similar but different pattern (Date/Status/Scope instead of Date/Status/Tier/Effort).

---

## 3. Misplacement Audit

### 3.1 Files in Wrong Tier

| File | Current | Should Be | Reason |
|------|---------|-----------|--------|
| `d1/architecture-deep-trace.md` | d1 | d2 | Architecture diagrams, not operational |
| `d1/architecture-diagrams.md` | d1 | d2 | Mermaid architecture diagrams, 445 lines |
| `d1/memctl-architecture-overview.md` | d1 | d2 | Architecture overview, not operations guide |
| `d1/halos-in-brief.md` | d1 | d2 | Overview/primer, not a runbook |
| `d1/adversarial-review-2026-03-16.md` | d1 | d2/reviews | Review output |
| `d1/development-logbook.md` | d1 | d1 (OK) | Operational journal, correctly placed |
| `d1/session-patterns-2026-03-18.md` | d1 | d1 (OK) | Lessons learned, operational |
| `d1/eval-baseline-2026-03-18.md` | d1 | d1 (OK) | Eval results, operational data |
| `d2/nanoclaw-architecture-final.md` | d2 | d3 | 1,062 lines, title says "final" but predates all current architecture docs. Likely superseded. |
| `d2/skills-as-branches.md` | d2 | d3 | 662 lines, describes a previous architecture (manifest-based skills system). The archive version (`d3/archive/nanorepo-architecture.md`) covers related superseded content. |
| `d3/APPLE-CONTAINER-NETWORKING.md` | d3 | d1 | Operational setup guide for macOS networking |
| `d3/docker-sandboxes.md` | d3 | d1 | Setup/operational guide for Docker sandboxes |

### 3.2 Briefings in Both d1 and d2

Briefings are split across `d1/briefings/` (3 files, 2026-03-16 to 2026-03-18) and `d2/briefings/` (6 files, 2026-03-19 to 2026-03-21). This is a migration in progress -- they moved from d1 to d2 around March 19. Neither location is correct per the CLAUDE.md definitions. Briefings are operational output, not architecture.

### 3.3 Reviews Nested in d2

The `d2/reviews/` subdirectory (12 files) contains review output from the responsiveness and taxonomy reviews. These are review artifacts, not architecture documents. They're reasonably placed in d2 as they support architectural decision-making, but they share no naming or structural convention with their parent docs.

### 3.4 docs-audit.py Misplacement Heuristics

The existing `docs-audit.py` checks:
- d1 files >300 lines flagged as "may belong in d2" (line-count heuristic)
- d2 files <50 lines flagged as "may belong in d1"
- Briefings in d2 flagged as "should be d1 or dedicated dir"

These heuristics are rough but directionally correct. The line-count proxy conflates depth with purpose.

---

## 4. Proposed Standard

### 4.1 Design Principles

1. **YAML frontmatter on all markdown docs.** The memctl pattern proves this works: agents already know how to write frontmatter, `memctl new` validates it at write time, and it's grep/parseable.
2. **Filename encodes nothing except topic.** No dates in filenames (dates go in frontmatter). No category prefixes (category goes in frontmatter). Exception: briefings retain date-prefix for chronological browsing.
3. **Auto-generated index per directory.** Like `memory/INDEX.md`, each `docs/d{N}/` gets an `INDEX.md` that's derived from frontmatter, never hand-edited.
4. **Minimal required fields.** More fields = more skipped fields. Keep it to four required, rest optional.

### 4.2 Frontmatter Schema

```yaml
---
title: "Short descriptive title"          # REQUIRED
category: spec | analysis | runbook | review | briefing | reference | guide | journal | archive
                                          # REQUIRED — controlled vocabulary
status: draft | active | superseded | archived
                                          # REQUIRED
created: 2026-03-21                       # REQUIRED
updated: 2026-03-21                       # Optional, set on modification
superseded_by: null                       # Optional — path to replacement doc
related:                                  # Optional — paths to related docs
  - docs/d2/memctl-spec.md
tags:                                     # Optional — free-form, for grep
  - memctl
  - architecture
effort: "~15 agent-min + ~10 human-min"   # Optional — for specs/plans
tier: now | next | later                  # Optional — for specs
---
```

**Four required fields:** `title`, `category`, `status`, `created`. Everything else is optional. This is the minimum viable set that enables:
- Filtering by category: `grep -l "category: spec" docs/d2/*.md`
- Finding active docs: `grep -l "status: active" docs/**/*.md`
- Finding superseded docs: `grep -l "status: superseded" docs/**/*.md`
- Building an index from frontmatter alone

### 4.3 Category Definitions

| Category | Description | Typical Location |
|----------|-------------|------------------|
| `runbook` | How to do X. Step-by-step, command-oriented. | d1 |
| `guide` | Setup, configuration, onboarding. More narrative than runbook. | d1 |
| `reference` | Module registry, security model, API surface. Stable, looked up. | d1 |
| `journal` | Logbook, session patterns, lessons learned. Time-bound. | d1 |
| `briefing` | Daily/nightly briefing output. Machine-generated. | d1/briefings |
| `spec` | Specification for a module, feature, or system. Prescriptive. | d2 |
| `analysis` | Research, investigation, decision support. Descriptive. | d2 |
| `review` | Code review output, audit findings. | d2/reviews |
| `archive` | Superseded, completed, or historical. | d3 |

### 4.4 Directory Semantics (Refined)

The d1/d2/d3 hierarchy maps to **information lifecycle**, not content type:

| Directory | Purpose | When to Place Here |
|-----------|---------|-------------------|
| `d1/` | **Working reference** — docs you reach for during operations | You would `cat` this during a debugging session or onboarding |
| `d2/` | **Design record** — docs that inform or record decisions | You wrote this before building, or to evaluate options |
| `d3/` | **Archive** — completed, superseded, or deep-reference material | This was useful once; now it's provenance |

**Rule of thumb:** If an agent needs it mid-task, it's d1. If an agent needs it before starting a task, it's d2. If nobody needs it unless they're doing archaeology, it's d3.

### 4.5 Index Generation

Each directory gets an auto-generated `INDEX.md`:

```markdown
# docs/d2/ Index
<!-- AUTO-GENERATED by docctl index — do not hand-edit -->

| Title | File | Category | Status | Created | Tags |
|-------|------|----------|--------|---------|------|
| memctl Spec | memctl-spec.md | spec | active | 2026-03-15 | memctl |
| Ben Usage Metrics | analysis-ben-usage-metrics.md | analysis | active | 2026-03-21 | ben, metrics |
...
```

This follows the memctl INDEX.md pattern: auto-generated, never hand-edited, rebuildable from source files. A `docctl index rebuild` command would parse all frontmatter and regenerate.

### 4.6 What This Standard Does NOT Require

- **No mandatory TOC in documents.** Agents can add them; they're not enforced.
- **No mandatory section headings.** A spec and a briefing have different shapes. The frontmatter declares what kind of document it is; the body follows whatever structure fits.
- **No version numbers in frontmatter.** Git provides versioning. Adding `v1.2` to frontmatter creates maintenance burden with zero benefit.
- **No numeric IDs.** memctl uses timestamp IDs because notes need stable machine-addressable references. Docs already have stable addresses: their file paths.

---

## 5. Migration Plan

### 5.1 Phase 1: Add Frontmatter (Non-Breaking)

Add YAML frontmatter to all existing docs. This is additive -- it doesn't change content, move files, or break links.

**Effort:** ~10 agent-minutes. Scripted: read each file, infer category/status from content and location, prepend frontmatter block.

**Inference rules for automated migration:**
- Files in `d1/`: status `active`, category inferred from prefix/content
- Files named `spec-*.md`: category `spec`
- Files named `analysis-*.md`: category `analysis`
- Files in `reviews/`: category `review`
- Files in `briefings/`: category `briefing`
- Files named `*-YYYY-MM-DD.md` or `YYYY-MM-DD-*.md`: extract date for `created`
- Everything else: `created` from git log first commit date

### 5.2 Phase 2: Relocate Misplaced Files

Move files to correct tiers per Section 3.1. Update all cross-references. This requires a link-fixup pass.

**Files to move:**
- `d1/architecture-deep-trace.md` -> `d2/`
- `d1/architecture-diagrams.md` -> `d2/`
- `d1/memctl-architecture-overview.md` -> `d2/`
- `d1/halos-in-brief.md` -> `d2/`
- `d1/adversarial-review-2026-03-16.md` -> `d2/reviews/`
- `d2/nanoclaw-architecture-final.md` -> `d3/archive/` (with `status: superseded`)
- `d3/APPLE-CONTAINER-NETWORKING.md` -> `d1/`
- `d3/docker-sandboxes.md` -> `d1/`

**Briefings:** Consolidate to `d1/briefings/` (all 9 files). Briefings are operational output.

**Effort:** ~5 agent-minutes for moves + ~10 human-minutes for review.

### 5.3 Phase 3: Generate Indexes

Build `docctl index rebuild` (or a standalone script) that parses frontmatter and generates `INDEX.md` for each directory.

**Effort:** ~15 agent-minutes for the script.

### 5.4 Phase 4: Update docs-audit.py

Replace line-count heuristics with frontmatter-aware checks:
- Flag files without frontmatter
- Flag files where `category` doesn't match directory (spec in d1, runbook in d2)
- Flag files with `status: superseded` not in d3
- Flag `related` links that point to nonexistent files

### 5.5 Phase 5: Codify in CLAUDE.md

Update the Documentation section in CLAUDE.md to reference the standard:
- Required frontmatter fields
- Category vocabulary
- `docctl` command for index rebuild
- Rule: agents MUST add frontmatter when creating docs in `docs/`

---

## 6. docctl Integration

The existing `spec-docctl.md` defines docctl as a **document assembly and template rendering** tool (Pandoc-based, PDF/HTML output). That is a different concern from documentation governance.

Two options:

### Option A: Extend docctl

Add `docctl audit` and `docctl index` subcommands to the existing docctl spec. This keeps one module but splits its purpose: assembly + governance.

### Option B: Separate governance into docs-audit.py

Keep `docs-audit.py` as the governance tool, enhanced with frontmatter awareness. docctl stays focused on document rendering.

**Recommendation: Option A.** The existing `docs-audit.py` is a good starting point, but it should evolve into `docctl audit` within the halos module system. Reasons:
- Consistent with halos patterns (CLI module, `uv sync`, console_scripts entry point)
- `docctl index rebuild` mirrors `memctl index rebuild`
- `docctl audit` mirrors `memctl index verify`
- cronctl can schedule periodic audits
- hlog can record audit runs

### docctl Governance Commands (Proposed)

```bash
docctl audit                        # frontmatter validation, misplacement check, broken links
docctl audit --fix                  # auto-add missing frontmatter (interactive confirmation)
docctl index rebuild                # regenerate INDEX.md for each docs/ subdirectory
docctl index verify                 # check INDEX.md matches actual files
docctl lint                         # frontmatter schema validation only
```

These compose with the existing rendering commands in `spec-docctl.md`.

---

## 7. Open Questions

1. **Should the walkthrough be a d1 subdirectory?** The walkthrough is 11 files totalling ~130K. It has its own index. It's operational (onboarding new agents) but also architectural (deep system understanding). Argument for d1: agents reach for it mid-session. Argument for d2: it's a structured analysis of the codebase. Current placement (d1) seems right -- it's a working reference, not a design document.

2. **Diagrams.** The SVG files in `d1/diagrams/` are generated from the mermaid in `d1/architecture-diagrams.md`. Should diagrams live alongside their source doc, or in a separate subdirectory? Current approach (separate `diagrams/` dir) is fine for SVGs since they're binary and clutter `git diff`.

3. **Briefing retention.** Briefings accumulate indefinitely. Should there be a retention policy (e.g., archive briefings older than 30 days to d3)? The memctl pruning pattern could apply here.

4. **Review output retention.** The `d2/reviews/` directory will grow with each review cycle. Same retention question as briefings.

5. **The `nanoclaw-architecture-final.md` question.** At 1,062 lines, this is the largest doc. Its title implies finality but it's from the earliest commit (2026-03-15). Is it the canonical architecture doc, or has it been superseded by the CLAUDE.md schematic + walkthrough? If superseded, it should move to d3 with `status: superseded, superseded_by: CLAUDE.md`.

6. **`skills-as-branches.md` status.** This 662-line doc describes the skills-as-git-branches architecture. The `d3/archive/nanorepo-architecture.md` covers a related superseded design. Is the current skills-as-branches spec still active, or has the architecture moved on? If active, it stays in d2. If superseded, d3.
