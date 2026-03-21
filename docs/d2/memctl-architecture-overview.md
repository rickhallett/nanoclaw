---
title: "memctl — Architecture Overview"
category: reference
status: active
created: 2026-03-15
---

# memctl — Architecture Overview

A personal knowledge operating system that treats memory as infrastructure, not a feature.

## One Sentence

memctl is a CLI-driven knowledge graph where every claim is an atomic file, every connection is an auditable decision, and the index is always a derived artifact you can rebuild from scratch.

## For Engineers Who Work with LLMs

The problem with giving an AI agent "memory" is that it will write itself a mess. Free-form notes degrade into a context swamp: duplicates, contradictions, stale claims that never get cleaned up, and no way to know which memories are authoritative vs speculative.

memctl treats this like a database schema problem. Every memory note has a type (decision, fact, person, reference, event), a confidence level, an optional expiry date, and tags from a controlled vocabulary. Decisions are immutable and exempt from pruning. Facts can go stale. The agent writes notes via a CLI that validates schema at write time, so malformed memories are rejected before they enter the corpus.

The index is a YAML block the agent reads on session start. It contains note IDs, types, tags, entities, summaries, and SHA256 hashes. The agent looks up candidates by entity or tag intersection, loads only matching files, and checks hashes to detect drift. If a note was modified outside the system, the hash won't match, and the agent is instructed to flag it before continuing.

Backlinks are where the graph gets interesting. They're proposed by a heuristic scoring engine (`memctl enrich`) that evaluates candidate pairs across five dimensions: semantic bridge, cross-type novelty, causal direction, cluster value, and recall utility. Proposals are presented in muster format for human batch approval. The human is the only layer that can validate whether a semantic connection actually holds. This is deliberate: the machine proposes, the human disposes.

Pruning uses a decay function: `score = backlinks * exp(-age / half_life)`. Notes with backlinks are exempt. Decisions and persons are always exempt. Pruning never deletes — it archives with a tombstone. Dry-run by default, explicit flag required to execute.

The whole thing is about 900 lines of Python, one external dependency (pyyaml), installed via `uv sync` as a single-word CLI command.

## Why Not a Database / Vector Store / RAG?

Three reasons.

**Auditability.** Every note is a markdown file you can read with `cat`. Every backlink is a field in that file's YAML frontmatter. Every index entry has a hash you can verify. There is no opaque embedding space, no similarity threshold you can't inspect, no retrieval pipeline that silently drops relevant results. When the agent says "I found this in memory," you can trace exactly which file, which hash, which lookup path.

**Governance.** The agent cannot edit the index, cannot run pruning, cannot modify notes after creation. Write access is through a schema-validated CLI. This separation of concerns means the agent's probabilistic nature can't corrupt the memory store. It can only append well-formed claims and read an immutable index.

**Composability.** memctl is one module in a pattern. nightctl (batch job queue), cronctl (cron definitions), todoctl (backlog tracking) all follow the same conventions: YAML files, controlled vocabularies, CLI writes, derived indices, archive-not-delete. They're independent but share a design language. Adding a new module means following the pattern, not integrating with a framework.

## What's Actually Novel

The enrichment rubric. Most knowledge graph systems either link everything automatically (hairball) or expect the human to do it manually (doesn't scale). The five-dimension scoring system (`memctl enrich`) sits in the middle: it proposes links using structural heuristics, filters out noise tags and generic entities, and presents candidates in a format designed for fast human binary decisions. The human approvals feed back into the graph topology, which changes the cluster_value scores for future proposals. It's a feedback loop where human judgment trains the heuristic without any ML infrastructure.

The enforcement loop. After every note creation, the CLI prints a neighbour summary and an explicit nudge to run enrichment. The agent's system prompt (CLAUDE.md) marks this as non-optional. Three layers of enforcement — system prompt instruction (L8), tool output nudge (L7), and structural context (neighbour list) — without a single hook or callback. The agent would have to actively ignore its own tool output to skip the step.

The design invariant that makes this work: **the index is always rebuildable from the notes corpus.** The notes are ground truth. The index is derived. If the index drifts (stale hashes, orphans, missing entries), `memctl index rebuild` regenerates it from the source files.

Backlinks, however, live in the note files themselves. A bad link persists until explicitly removed. This is intentional: the graph topology is a set of auditable decisions, not a computed artifact. The tradeoff is that cleaning a noisy graph requires surgical intervention (`memctl unlink`, or editing the note's frontmatter), not a bulk reset. Approve links carefully.

## Current State

59 notes, 18 backlinks, 12 entities, 6 standing decisions exempt from pruning. Slopodar taxonomy is the highest-degree node (3 inbound links). Five semantic clusters have formed: anxiety/deskilling, slopodar/verification, identity/career, learning/post-mortems, and governance/process.

## Relationship to halos

memctl is one of four modules in the halos agent operating layer:

| Module | Purpose |
|--------|---------|
| memctl | Structured memory governance |
| nightctl | Overnight batch job queue |
| cronctl | Cron job definitions and crontab generation |
| todoctl | Backlog tracking and prioritisation |

All share: filesystem-first storage, YAML schemas, CLI-driven writes, derived indices, archive-not-delete, dry-run defaults, --json output.

## References

- Spec: `docs/d2/memctl-spec.md`
- Operations guide: `docs/d1/memctl-operations.md`
- Module registry: `docs/d1/halos-modules.md`
- Source: `halos/memctl/`
- Enrichment rubric: `halos/memctl/enrich.py` (docstring contains the full scoring dimensions)
