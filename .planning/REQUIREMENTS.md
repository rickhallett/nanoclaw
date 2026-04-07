# Requirements: Halo for Aura (Client 001)

**Defined:** 2026-04-07
**Core Value:** The Content Alchemist turns Aura's 80-90min Zoom practice recordings into Instagram-ready content that sounds exactly like her

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [ ] **DICT-01**: Custom UHT terminology dictionary exists as YAML registry with canonical spellings, common mistranscriptions, and context definitions (50+ terms)
- [ ] **DICT-02**: Dictionary is used by transcription correction and generation quality checks
- [ ] **DICT-03**: Aura can add/update terms via Telegram command
- [ ] **LINE-01**: System prompt encodes Master Chia/UHT lineage attribution rules — references lineage correctly when relevant, never claims outside certified scope

### Transcription

- [ ] **TRANS-01**: Zoom recording ingestion accepts recordings via at least one delivery path (Telegram upload, Zoom cloud link, or Google Drive)
- [ ] **TRANS-02**: Audio extracted from recording and transcribed with UHT dictionary correction applied
- [ ] **TRANS-03**: Transcription handles 80-90min recordings (chunking with overlap for files exceeding API limits)
- [ ] **TRANS-04**: Transcript segmented by topic/practice into chapters with timestamps (LLM classification)

### Content Generation

- [ ] **GEN-01**: Text Instagram posts generated from transcript segments in Aura's voice (soft, educational, meditative, with touch of wit)
- [ ] **GEN-02**: Two caption modes available per segment: verbatim extract with light editing, or full LLM paraphrase
- [ ] **GEN-03**: Posts formatted for Instagram: 150-300 words, visual rhythm, hook in first line, 5-8 curated hashtags, no hard CTA
- [ ] **GEN-04**: Lao Tzu quotes woven naturally when appropriate (not forced into every post)
- [ ] **GEN-05**: Engagement pattern learning: approve/reject/edit decisions logged and fed back into generation after 20+ decisions

### Evaluation

- [ ] **EVAL-01**: Voice fidelity eval rubric scores generated content via LLM-as-judge before it reaches Aura (extends existing watchctl/rubric.py)
- [ ] **EVAL-02**: Overpromise detection gates all output — deterministic deny-list for action+condition combinations, plus LLM-as-judge criterion at highest weight
- [ ] **EVAL-03**: Eval baseline established from Aura's intake session conversation — reference for all future scoring
- [ ] **EVAL-04**: Prompt tuning pipeline: eval scores identify weak dimensions, suggest prompt changes, track prompt versions against score trajectories
- [ ] **EVAL-05**: Content below REVIEW threshold (3.0) flagged with eval notes; content below REJECT threshold blocked and logged

### Review & Distribution

- [ ] **REV-01**: Telegram review flow: Aura sees content preview with eval score, can approve/edit/reject via inline keyboard
- [ ] **REV-02**: Human-in-the-loop always — no content published without Aura's explicit approval
- [ ] **REV-03**: Content queue: approved content scheduled across the week (Monday AM / Wednesday PM / Friday AM slots or custom)
- [ ] **REV-04**: Instagram Graph API integration for direct publishing of approved content (requires Meta developer account and app review)

### Programme Structure

- [ ] **PROG-01**: Multi-session transcript accumulation — Dao Assistant tracks topics across recordings to identify curriculum structure
- [ ] **PROG-02**: Programme outline generation: prerequisites, progression paths, session breakdowns (4x20min from 80min sessions)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Content

- **VID-01**: Video clip extraction from Zoom recordings — highlight detection, vertical reframing, caption overlay
- **VID-02**: Video stills extraction for Instagram carousel posts

### Monitoring

- **DRIFT-01**: Long-term voice drift detection dashboard — score trajectory visualisation across weeks/months
- **DRIFT-02**: Automated drift alerts when rolling average drops below threshold

### Growth

- **GROW-01**: Council advisors customised for Aura's domain (Lao Tzu archetype, UHT system archetype)
- **GROW-02**: Website structure recommendations from Dao Assistant (aureliana-therapies.com)
- **GROW-03**: Email list integration — Sunday summaries formatted and delivered via mail

## Out of Scope

| Feature | Reason |
|---------|--------|
| Autonomous posting without review | Aura explicitly requires human approval. Wellness content = reputational risk |
| Multi-platform auto-formatting | Instagram-first. Single platform mastery before expansion |
| Real-time transcription during live sessions | Different product. Post-session processing matches Aura's Sunday workflow |
| AI-generated images | Off-brand for practitioner whose credibility is embodied practice |
| Competitor content analysis | Leads to homogenised content. Aura's differentiation IS her unique voice |
| AI hashtag optimisation | Algorithm-chasing contradicts "nothing forced, slowness creates transformation" |
| Multi-tenant architecture | Separate namespace per client. Defer shared infrastructure |
| Web UI | Telegram is the interface |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DICT-01 | Phase 1 | Pending |
| DICT-02 | Phase 1 | Pending |
| DICT-03 | Phase 4 | Pending |
| LINE-01 | Phase 1 | Pending |
| TRANS-01 | Phase 2 | Pending |
| TRANS-02 | Phase 2 | Pending |
| TRANS-03 | Phase 2 | Pending |
| TRANS-04 | Phase 2 | Pending |
| GEN-01 | Phase 3 | Pending |
| GEN-02 | Phase 3 | Pending |
| GEN-03 | Phase 3 | Pending |
| GEN-04 | Phase 3 | Pending |
| GEN-05 | Phase 5 | Pending |
| EVAL-01 | Phase 1 | Pending |
| EVAL-02 | Phase 1 | Pending |
| EVAL-03 | Phase 1 | Pending |
| EVAL-04 | Phase 5 | Pending |
| EVAL-05 | Phase 1 | Pending |
| REV-01 | Phase 3 | Pending |
| REV-02 | Phase 3 | Pending |
| REV-03 | Phase 4 | Pending |
| REV-04 | Phase 4 | Pending |
| PROG-01 | Phase 5 | Pending |
| PROG-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 after roadmap creation*
