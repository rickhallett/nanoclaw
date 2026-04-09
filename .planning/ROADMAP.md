# Roadmap: Halo for Aura (Client 001)

## Overview

Transform Aura's 80-90 minute Zoom practice recordings into Instagram-ready content that sounds exactly like her. The roadmap front-loads the UHT dictionary and eval infrastructure (the two hardest dependencies), then builds the transcription and generation pipeline on solid foundations, and defers feedback loops and programme extraction until real operational data exists. Five phases, strictly ordered by data dependencies: nothing generates content without eval scoring it first, nothing transcribes without the dictionary correcting it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 0.1: Local Cluster Migration** - INSERTED — Migrate K8s fleet from Vultr VKE to local Arch Linux box (Ryzen 7 / 32GB) with Cloudflare Tunnel for public exposure
- [ ] **Phase 1: Dictionary and Eval Baseline** - UHT terminology registry and voice fidelity evaluation infrastructure ship before any content is generated
- [ ] **Phase 2: Transcription Pipeline** - Zoom recordings become dictionary-corrected, chapter-segmented transcripts
- [ ] **Phase 3: Content Generation and Review** - Transcripts become Instagram posts in Aura's voice, gated by eval and human approval
- [ ] **Phase 4: Publishing and Distribution** - Approved content flows to Instagram via API, with scheduling and Telegram dictionary management
- [ ] **Phase 5: Feedback Loop and Programme Structure** - Engagement learning, prompt tuning, and multi-session curriculum extraction from accumulated data

## Phase Details

### Phase 0.1: Local Cluster Migration (INSERTED)
**Goal**: K8s fleet runs on local Arch Linux hardware (Ryzen 7 / 32GB RAM) with Cloudflare Tunnel providing public HTTPS endpoints, eliminating image upload latency and cutting dev iteration cycles from 5-8 min to under 2 min — fully operational before user traffic arrives
**Depends on**: Nothing (infrastructure, parallel-safe with Phase 1)
**Requirements**: None (infrastructure initiative, no REQUIREMENTS.md entries)
**Success Criteria** (what must be TRUE):
  1. k3s cluster running on Arch Linux box with all current advisor pods healthy
  2. Local container builds load directly (no registry push) and deploy in under 60 seconds
  3. Cloudflare Tunnel exposes Telegram webhook endpoints with valid SSL — Aura's bot responds identically to Vultr-hosted version
  4. NATS JetStream data and NFS shared state migrated with zero event loss (replay from checkpoint matches)
  5. Manual deploy pipeline verified (git push → SSH → docker build → kubectl rollout restart)
  6. UPS connected with graceful shutdown hooks on power loss signal
**Migration Scope** (from analysis 2026-04-07):
  - k3s install on Arch: ~1h
  - Local registry or direct import: ~30min
  - Manifest migration (done — manual kubectl apply): ~2-4h
  - Cloudflare Tunnel setup: ~1h
  - NATS + NFS + PVC migration: ~2-3h
  - DNS cutover + Telegram webhook update: ~30min
  - Smoke test all advisors: ~1-2h
  - Risk mitigations: UPS, firewall, Cloudflare proxy hides origin IP
**Plans**: TBD

### Phase 1: Dictionary and Eval Baseline
**Goal**: Every downstream component has access to a canonical UHT terminology registry, and all generated content is scored against a voice fidelity baseline derived from Aura's actual communication patterns
**Depends on**: Nothing (first phase)
**Requirements**: DICT-01, DICT-02, LINE-01, EVAL-01, EVAL-02, EVAL-03, EVAL-05
**Success Criteria** (what must be TRUE):
  1. A YAML dictionary of 50+ UHT terms exists with canonical spellings, common mistranscriptions, and context definitions
  2. The eval rubric scores sample content against Aura's intake session baseline and produces numeric fidelity scores
  3. Overpromise detection flags content containing health claims, cure language, or scope-exceeding assertions
  4. Content scoring below the REJECT threshold (3.0) is blocked and logged; content below REVIEW threshold is flagged with eval notes
  5. The lineage attribution system correctly references Master Chia/UHT when relevant and never claims outside certified scope
**Plans**: TBD

### Phase 2: Transcription Pipeline
**Goal**: Aura's Zoom recordings are ingested, transcribed with UHT dictionary correction, and segmented into topic-based chapters ready for content generation
**Depends on**: Phase 1
**Requirements**: TRANS-01, TRANS-02, TRANS-03, TRANS-04
**Success Criteria** (what must be TRUE):
  1. A Zoom recording delivered via at least one path (Telegram upload, cloud link, or Drive) is accepted and its audio extracted
  2. An 80-90 minute recording is transcribed with UHT terms spelled correctly (dictionary correction applied post-transcription)
  3. Long recordings are chunked with overlap so no content is lost at chunk boundaries
  4. The transcript is segmented into chapters with timestamps, each labelled by topic/practice
**Plans**: TBD

### Phase 3: Content Generation and Review
**Goal**: Transcript segments become Instagram-ready posts in Aura's voice, every post is eval-scored before Aura sees it, and Aura can approve, edit, or reject via Telegram
**Depends on**: Phase 2
**Requirements**: GEN-01, GEN-02, GEN-03, GEN-04, REV-01, REV-02
**Success Criteria** (what must be TRUE):
  1. Text Instagram posts are generated from transcript segments in Aura's voice (soft, educational, meditative, touch of wit)
  2. Both caption modes work: verbatim extract with light editing, and full LLM paraphrase
  3. Posts are formatted for Instagram (150-300 words, hook in first line, 5-8 hashtags, no hard CTA, Lao Tzu quotes when natural)
  4. Aura sees content previews with eval scores in Telegram and can approve, edit, or reject via inline keyboard
  5. No content reaches Aura without passing eval; no content publishes without Aura's explicit approval
**Plans**: TBD
**UI hint**: yes

### Phase 4: Publishing and Distribution
**Goal**: Approved content flows directly to Instagram via Graph API with scheduling across the week, and Aura can manage the UHT dictionary via Telegram
**Depends on**: Phase 3
**Requirements**: REV-03, REV-04, DICT-03
**Success Criteria** (what must be TRUE):
  1. Approved content is queued and scheduled across the week (Monday AM / Wednesday PM / Friday AM or custom slots)
  2. Instagram Graph API integration publishes approved content directly (container create, publish, token refresh tracking)
  3. Aura can add or update UHT dictionary terms via a Telegram command
**Plans**: TBD
**UI hint**: yes

### Phase 5: Feedback Loop and Programme Structure
**Goal**: The system learns from Aura's approve/reject patterns to improve generation quality, eval scores drive prompt refinements, and multi-session transcripts reveal curriculum structure
**Depends on**: Phase 4 (and 2-4 weeks of operational data)
**Requirements**: GEN-05, EVAL-04, PROG-01, PROG-02
**Success Criteria** (what must be TRUE):
  1. After 20+ approve/reject decisions, generation incorporates learned engagement patterns from Aura's feedback
  2. Eval scores identify weak dimensions and the prompt tuning pipeline suggests and tracks prompt version changes against score trajectories
  3. The Dao Assistant accumulates topics across multiple session transcripts and identifies curriculum structure
  4. Programme outlines are generated with prerequisites, progression paths, and session breakdowns (4x20min from 80min sessions)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 (Phase 0.1 runs in parallel, completes before user traffic)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0.1. Local Cluster Migration (INSERTED) | 0/TBD | Not started | - |
| 1. Dictionary and Eval Baseline | 0/TBD | Not started | - |
| 2. Transcription Pipeline | 0/TBD | Not started | - |
| 3. Content Generation and Review | 0/TBD | Not started | - |
| 4. Publishing and Distribution | 0/TBD | Not started | - |
| 5. Feedback Loop and Programme Structure | 0/TBD | Not started | - |
