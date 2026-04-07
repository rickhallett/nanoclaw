# Architecture Research

**Domain:** Video content repurposing + LLM eval for K8s AI agent platform
**Researched:** 2026-04-07
**Confidence:** MEDIUM (transcription pipeline: HIGH, eval infrastructure: MEDIUM, prompt tuning loop: MEDIUM)

## System Overview

```
                        halo-aura namespace (Vultr VKE)
 ┌──────────────────────────────────────────────────────────────────────┐
 │                                                                      │
 │  ┌────────────┐   ┌─────────────┐   ┌──────────────┐                │
 │  │  Aura GW   │   │  Content    │   │  Eval        │                │
 │  │  (Hermes)  │   │  Pipeline   │   │  Runner      │                │
 │  │  + relay   │   │  (Job)      │   │  (CronJob)   │                │
 │  └─────┬──────┘   └──────┬──────┘   └──────┬───────┘                │
 │        │                 │                  │                        │
 │        │    ┌────────────┴──────────────────┘                        │
 │        │    │                                                        │
 │  ┌─────┴────┴─────────────────────────────────────────────┐          │
 │  │                  Shared NFS Volume                      │          │
 │  │  /recordings  /transcripts  /content  /evals  /dict    │          │
 │  └────────────────────────────────────────────────────────┘          │
 │                                                                      │
 └──────────────────────────────────────────────────────────────────────┘
          │
          │ NATS (cross-namespace)
          ▼
 ┌──────────────────┐
 │  halo-fleet      │
 │  NATS JetStream  │
 │  (event log)     │
 └──────────────────┘
```

### Component Responsibilities

| Component | Responsibility | K8s Resource | Communicates With |
|-----------|----------------|--------------|-------------------|
| **Aura Gateway** | Telegram interface, Content Alchemist + Dao Assistant personas, recording intake via Telegram file upload | Deployment (existing) | NFS, NATS, Anthropic API |
| **Ingestion Worker** | Download recording, extract audio (ffmpeg), run transcription, apply dictionary corrections | K8s Job (on-demand) | NFS (read recording, write transcript), Transcription API |
| **Content Generator** | Transform transcript into Instagram posts/captions in Aura's voice | K8s Job (triggered after transcription) | NFS (read transcript, write drafts), Anthropic API |
| **Review Relay** | Present generated content to Aura in Telegram for approve/reject/edit | Part of Gateway (skill/command) | NFS (read drafts), Telegram API |
| **Eval Runner** | Score conversation logs and content output against voice fidelity, terminology, overpromise criteria | CronJob (nightly) or Job (post-generation) | NFS (read logs + content), Anthropic API, eval store |
| **UHT Dictionary** | Custom terminology file for transcription correction and eval grading | ConfigMap or NFS file | Read by Ingestion Worker, Content Generator, Eval Runner |
| **Prompt Tuner** | Analyse eval trends, propose system prompt revisions, gate deployment | Manual trigger (CLI or Telegram command) | Eval store, Gateway ConfigMap |

## Recommended Project Structure

```
halos/
├── contentctl/              # Content pipeline orchestration
│   ├── cli.py               # CLI: contentctl ingest, contentctl generate, contentctl review
│   ├── ingest.py            # Recording download + audio extraction + transcription
│   ├── transcribe.py        # Transcription API wrapper + dictionary post-processing
│   ├── generate.py          # Transcript -> content drafts (LLM)
│   ├── dictionary.py        # UHT terminology loader, correction rules
│   ├── store.py             # Pipeline state in SQLite (store/content.db)
│   └── config.py            # contentctl.yaml loader
├── evalctl/                 # LLM eval infrastructure
│   ├── cli.py               # CLI: evalctl run, evalctl report, evalctl baseline
│   ├── runner.py            # Execute eval suite against conversation logs
│   ├── scorers/             # Pluggable scoring functions
│   │   ├── voice_fidelity.py    # Does output match Aura's communication patterns?
│   │   ├── terminology.py       # Are UHT terms used correctly?
│   │   ├── overpromise.py       # Does content make claims beyond Aura's scope?
│   │   └── tone.py              # Soft, educational, meditative -- not generic wellness
│   ├── store.py             # Eval results in SQLite (store/eval.db)
│   ├── baseline.py          # Generate baseline scores from intake session
│   └── config.py            # evalctl.yaml loader
infra/k8s/aura/              # K8s manifests for halo-aura namespace
├── ingestion-job.yaml        # On-demand Job template for recording processing
├── content-job.yaml          # On-demand Job template for content generation
├── eval-cronjob.yaml         # Nightly eval runner
├── dictionary-configmap.yaml # UHT terminology
└── kustomization.yaml
```

### Structure Rationale

- **contentctl/:** Follows the established halos module pattern (cli.py + engine/store). Keeps video pipeline logic in one place with a clean CLI surface. Reusable by both K8s Jobs and interactive Telegram commands.
- **evalctl/:** Separate from contentctl because eval applies to ALL agent output (conversations, content, briefings), not just the content pipeline. Pluggable scorers directory mirrors trackctl's pluggable domains pattern.
- **infra/k8s/aura/:** Mirrors `infra/k8s/fleet/` structure but scoped to the aura namespace. Managed separately from fleet manifests since Aura has her own Argo CD app.

## Architectural Patterns

### Pattern 1: Job-per-Recording (not long-running worker)

**What:** Each recording triggers a K8s Job that processes one file end-to-end (download -> extract audio -> transcribe -> correct terminology -> write transcript). Job completes and pod is reclaimed.

**When to use:** Low-volume batch processing (Aura has ~1 recording/week on Sunday afternoons).

**Trade-offs:**
- Pro: Zero idle compute cost. No worker to keep alive. Failure isolation per recording.
- Pro: Natural retry semantics via K8s Job `backoffLimit`.
- Con: Cold start latency (~30s for pod scheduling + image pull). Irrelevant at 1 recording/week.

**Why not a CronJob that polls:** Recordings arrive on-demand (Sunday afternoon, but timing varies). A polling CronJob adds unnecessary infrastructure. Better: Gateway receives recording notification -> creates Job via K8s API.

### Pattern 2: LLM-as-Judge Eval (not heuristic scoring)

**What:** Use Claude as the primary scorer for voice fidelity, tone, and overpromise detection. The intake session transcript serves as the reference corpus. Each eval run scores agent output against criteria defined in YAML rubrics.

**When to use:** When the quality dimension is subjective (voice fidelity, tone) and cannot be reduced to regex or keyword matching.

**Trade-offs:**
- Pro: Can evaluate nuanced qualities ("does this sound like Aura?") that heuristics miss.
- Pro: Mirrors the existing `watchctl` pattern (LLM-as-judge with rubric YAML).
- Con: LLM eval cost (~$0.01-0.05 per eval run). Acceptable at current volume.
- Con: Non-deterministic -- same input may get different scores. Mitigate with multi-run averaging.

**Existing precedent:** `halos/watchctl/evaluate.py` already implements LLM-as-judge with configurable rubrics. evalctl should follow the same pattern, not introduce a new eval framework.

### Pattern 3: Dictionary-Augmented Transcription (not fine-tuning)

**What:** Use a hosted transcription API (Deepgram Nova-3) with keyword boosting for UHT terms, followed by a deterministic post-processing step that applies regex corrections from the UHT dictionary ConfigMap.

**When to use:** When domain vocabulary is specialised but finite (~50-100 terms), and fine-tuning a speech model is overkill.

**Trade-offs:**
- Pro: No GPU infrastructure needed. No model training pipeline. Dictionary is a YAML file Aura can review.
- Pro: Deepgram keyword boosting handles most terms at the API level.
- Con: Rare terms may still mis-transcribe even with boosting. Post-processing catches these.
- Alternative considered: Self-hosted faster-whisper with initial_prompt injection. Works but requires GPU node or slow CPU inference. Deepgram at ~$0.006/min is cheaper than running a GPU node at current volume.

### Pattern 4: File-Based Pipeline Handoff (not message queue)

**What:** Pipeline stages communicate via files on the shared NFS volume. Ingestion writes `/transcripts/{recording_id}.json`. Content generator reads transcript, writes `/content/{recording_id}/`. Eval reads from `/content/` and conversation logs.

**When to use:** Low-volume, sequential pipeline where stages run as separate Jobs.

**Trade-offs:**
- Pro: Debuggable -- every intermediate artifact is a file you can inspect.
- Pro: No additional infrastructure (NATS is available but adds complexity for a linear pipeline).
- Pro: Idempotent -- re-run any stage by deleting its output and re-triggering.
- Con: No real-time notification when a stage completes. Acceptable: Gateway triggers next stage explicitly.

### Pattern 5: Pipeline State Machine (same as nightctl)

**What:** Each recording has a state tracked in SQLite: `pending -> ingested -> transcribed -> generated -> evaluated -> reviewing -> approved`. State transitions are logged with timestamps. Same pattern as nightctl's `open -> active -> testing -> done`.

**When to use:** Any multi-step workflow that needs observability and retry capability.

**Trade-offs:**
- Pro: Can query "what's stuck?" and "what's pending review?" from CLI or Telegram.
- Pro: Each step is independently retryable.
- Pro: Natural fit for the existing halos module pattern.

## Data Flow

### Recording -> Content Pipeline

```
1. Aura sends recording link/file via Telegram
        |
        v
2. Gateway (Content Alchemist skill) receives recording
   - Validates format (mp4/webm/m4a/mp3)
   - Stores to NFS: /recordings/{date}_{title}.{ext}
   - Creates K8s Job: ingestion-{recording_id}
        |
        v
3. Ingestion Job runs in halo-aura namespace
   - ffmpeg: extract audio -> /recordings/{id}_audio.wav
   - Deepgram API: transcribe with UHT keyword boosting
   - Dictionary post-processor: regex corrections for known mis-transcriptions
   - Write: /transcripts/{id}.json (timestamped segments + full text)
   - Update state: pending -> transcribed
   - Publish NATS event: halo.content.aura.transcribed
   - Job completes (pod reclaimed)
        |
        v
4. Gateway notifies Aura: "Transcription ready. Generate content?"
   Aura confirms via Telegram
        |
        v
5. Content Generation Job runs
   - Reads: /transcripts/{id}.json + UHT dictionary + prompt templates
   - Claude API: generate Instagram posts (3-5 variations per teaching point)
   - Claude API: generate video caption candidates
   - Claude API: extract quotable moments with timestamps
   - Write: /content/{id}/ (posts.json, captions.json, quotes.json)
   - Update state: transcribed -> generated
   - Publish NATS event: halo.content.aura.generated
   - Job completes
        |
        v
6. Gateway presents content to Aura in Telegram
   - Shows each post/caption as a message
   - Aura: approve / reject / edit (inline)
   - Approved content marked in /content/{id}/approved.json
   - Update state: generated -> reviewing -> approved
        |
        v
7. (Future) Publish approved content or export for manual posting
```

### Eval Data Flow (Conversation Logs -> Eval Pipeline -> Prompt Updates)

```
1. Data sources accumulate continuously:
   - Conversation logs: /opt/data/sessions/*.jsonl (from existing aura-relay sidecar)
   - Generated content: /content/*/posts.json (from content pipeline)
   - Reference corpus: /evals/baseline/ (from intake session, created once)
        |
        v
2. Eval CronJob runs nightly (or triggered post-generation):
   a. Collect corpus (new conversations + content since last run)
   b. Run scorer suite (LLM-as-judge via Claude):
      - Voice Fidelity: "Does this sound like Aura?" (compare to baseline)
      - Terminology: "Are UHT terms used correctly?" (dictionary + LLM check)
      - Overpromise: "Does this make medical/health claims?" (safety scorer)
      - Tone: "Soft, educational, meditative?" (rubric-based)
   c. Store results in store/eval.db
        |
        v
3. Eval reporting:
   - Per-conversation scores, per-content-piece scores
   - Trend data (rolling 7-day, 30-day averages)
   - Drift alerts when scores drop below threshold
   - Daily summary in nightly briefing via Telegram
   - Alert if voice fidelity drops below configurable threshold
        |
        v
4. Prompt tuning (manual trigger, NOT automated):
   - Analyse low-scoring outputs via evalctl CLI
   - Propose system prompt edits based on failure patterns
   - Human reviews and approves changes
   - Update Gateway ConfigMap with new system prompt
   - Re-run eval against recent outputs to confirm improvement
   - Compare before/after scores to validate the change
```

### Eval Data Model

```sql
-- eval_runs: one row per eval execution
eval_runs (
    id          TEXT PRIMARY KEY,  -- ULID
    timestamp   TEXT,
    corpus_type TEXT,              -- 'conversation' | 'content'
    corpus_id   TEXT,              -- session_id or content_id
    model       TEXT,              -- judge model used
    rubric_ver  TEXT               -- rubric version hash
)

-- eval_scores: one row per scorer per run
eval_scores (
    run_id      TEXT,              -- FK to eval_runs
    scorer      TEXT,              -- 'voice_fidelity' | 'terminology' | 'overpromise' | 'tone'
    score       REAL,              -- 0.0 - 1.0
    explanation TEXT,              -- LLM reasoning
    samples     TEXT               -- JSON: specific examples cited
)
```

## Where New Components Fit in Existing K8s Topology

| Component | Namespace | Resource Type | Image | Notes |
|-----------|-----------|---------------|-------|-------|
| Aura Gateway | `halo-aura` | Deployment (exists) | `halo:fleet-latest` | Add contentctl skill for recording intake + content review |
| Aura Relay | `halo-aura` | Sidecar (exists) | Same pod | Already publishes conversation events to NATS |
| Ingestion Job | `halo-aura` | Job (new) | `halo-halos:latest` + ffmpeg | Needs ffmpeg added to image. Uses halos contentctl module |
| Content Job | `halo-aura` | Job (new) | `halo-halos:latest` | Uses halos contentctl + Anthropic API |
| Eval CronJob | `halo-aura` | CronJob (new) | `halo-halos:latest` | Uses halos evalctl. Nightly or post-generation schedule |
| NFS subpaths | `halo-aura` | PVC (extend existing) | N/A | Add /recordings, /transcripts, /content, /evals subdirectories |
| UHT Dictionary | `halo-aura` | ConfigMap (new) | N/A | Mounted read-only into Ingestion, Content, and Eval pods |

**Image strategy:** The `halo-halos:latest` init-container image already contains all halos Python tooling. Add `ffmpeg` to this image (single `apt-get install ffmpeg` in Dockerfile) or create a `halo-content:latest` variant. The existing Kaniko build pipeline handles in-cluster image builds. Prefer adding ffmpeg to the base image -- it is ~80MB and avoids managing a second image.

**ServiceAccount:** Gateway Deployment needs a ServiceAccount with permission to create/watch Jobs in `halo-aura` namespace. This is a new RBAC resource.

## Build Order (Dependencies Between Components)

```
Phase 1: Foundation (no external dependencies)
├── UHT Dictionary (ConfigMap YAML)         -- unblocks transcription + eval
├── evalctl module (scorers + store)        -- establishes quality baseline
├── Eval baseline from intake session       -- needs evalctl + intake transcript
└── contentctl.dictionary module            -- loads and applies dictionary

Phase 2: Content Pipeline (needs Deepgram API key)
├── contentctl.transcribe                   -- needs dictionary, Deepgram key
├── contentctl.ingest (ffmpeg + transcribe) -- needs transcribe working
├── Ingestion Job manifest                  -- needs contentctl.ingest
├── contentctl.generate                     -- needs transcript output format
└── Content Job manifest                    -- needs contentctl.generate

Phase 3: Integration (needs pipeline + gateway changes)
├── Gateway skill: recording intake         -- needs Ingestion Job template
├── Gateway skill: content review           -- needs Content Job output format
├── RBAC: Gateway ServiceAccount + Role     -- needs Job creation permissions
├── Eval CronJob manifest                   -- needs evalctl module complete
└── Eval reporting in briefings             -- needs eval store with data

Phase 4: Feedback Loop (needs weeks of eval data)
├── Prompt tuning analysis (evalctl CLI)    -- needs 2-4 weeks of eval scores
├── ConfigMap update workflow                -- needs tuning recommendations
└── Before/after eval comparison            -- needs eval runner + two prompt versions
```

**Critical path:** Dictionary -> Transcription -> Content Generation -> Review flow.

**Parallel track:** Eval infrastructure can be built alongside Phase 1-2, but only becomes useful for prompt tuning after enough data accumulates (2-4 weeks of conversations + content).

## Scaling Considerations

| Concern | 1 client, 1 rec/week | 5 clients, 5 rec/week | 20+ clients |
|---------|----------------------|------------------------|-------------|
| Pipeline compute | On-demand Jobs, zero idle | Same, per-namespace | Shared pipeline service, queue-based |
| Transcription cost | ~$0.50/week (Deepgram) | ~$2.50/week | Volume pricing ($4K/yr Growth tier) |
| Eval LLM cost | ~$0.50/week | ~$2.50/week | Haiku for screening, Sonnet for flagged |
| Dictionary mgmt | One YAML file | Per-client YAML | Shared base + client overlay |
| NFS storage | Negligible | ~1GB/month | Consider object storage (S3) |

### First Bottleneck

Not compute or API costs. It is **prompt quality** -- getting the voice right in content generation. This is why eval infrastructure ships in Phase 1, not Phase 3.

### Second Bottleneck

Recording delivery friction. If Aura has to manually share Zoom links via Telegram every Sunday, the workflow has a human bottleneck. Future optimisation: Zoom webhook or Google Drive watch for automatic ingestion.

## Anti-Patterns

### Anti-Pattern 1: Real-time Streaming Transcription

**What people do:** Build a live transcription pipeline that processes audio during Zoom sessions.
**Why it is wrong:** Aura's workflow is batch (Sunday afternoon post-session). Real-time adds WebSocket infrastructure, partial transcript merging, and failure modes for zero benefit.
**Do this instead:** Post-session batch transcription of the complete recording.

### Anti-Pattern 2: Self-Hosted Whisper for Cost Savings

**What people do:** Run faster-whisper on a GPU node to avoid API costs.
**Why it is wrong:** At 80-90 minutes/week, Deepgram costs ~$0.50/week. A GPU node costs $50-200/month. Break-even is ~100 hours/month. Aura will not hit that for years.
**Do this instead:** Use Deepgram Nova-3 API with keyword boosting. Revisit self-hosted only if volume exceeds 20+ hours/month.

### Anti-Pattern 3: Automated Prompt Tuning Without Human Gate

**What people do:** Close the eval -> prompt update loop automatically.
**Why it is wrong:** Prompt changes affect voice fidelity -- the core value proposition. Automated loops can drift the voice based on metrics that do not capture everything. PROJECT.md specifies "Aura reviews before publish" -- same principle for prompts.
**Do this instead:** Eval flags issues, analysis proposes changes, human approves before ConfigMap update.

### Anti-Pattern 4: Fine-Grained Microservices for the Pipeline

**What people do:** Separate Deployments for audio extraction, transcription, post-processing, content generation.
**Why it is wrong:** At 1 recording/week, maintaining 4-5 always-on services for a pipeline that runs 10 minutes once a week.
**Do this instead:** Single halos module (contentctl) with functions for each stage, invoked by K8s Jobs. Share the image, share the NFS volume.

### Anti-Pattern 5: Introducing a New Eval Framework (DeepEval/Promptfoo) When watchctl Already Has the Pattern

**What people do:** Adopt DeepEval or Promptfoo as a dependency for eval infrastructure.
**Why it is wrong:** The repo already has an LLM-as-judge pattern in `watchctl/evaluate.py` with configurable rubrics. Adding a third-party eval framework introduces new dependencies, new config formats, and a learning curve for a pattern that is already solved in the codebase. Promptfoo's self-hosting uses SQLite and is "not recommended for production." DeepEval adds ~50 transitive dependencies.
**Do this instead:** Build evalctl following the watchctl pattern. YAML rubrics, Claude-as-judge, SQLite store. Same patterns, same team knowledge, zero new dependencies.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Deepgram Nova-3 | REST API via httpx in contentctl.transcribe | `DEEPGRAM_API_KEY` in K8s Secret. Keyword boosting via request params. ~$0.006/min |
| Anthropic Claude | SDK via `anthropic` (already a dependency) in contentctl.generate + evalctl | Existing `ANTHROPIC_API_KEY`. Sonnet for content gen, Haiku for bulk eval |
| Zoom Cloud | Recording download URL provided by Aura via Telegram | No Zoom API integration initially. Aura pastes the share link |
| Telegram | File upload (recordings in), content preview (drafts out) | Existing Hermes gateway handles this. Add skills for content workflow |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Gateway <-> Ingestion Job | Gateway creates Job via K8s API, reads output from NFS | Gateway needs ServiceAccount with Job create/watch permissions |
| Ingestion <-> Content Generation | File handoff on NFS (/transcripts/{id}.json) | Content Job reads transcript written by Ingestion Job |
| Content Generation <-> Review | Files on NFS + Telegram messages from Gateway | Gateway reads /content/{id}/ and presents to user |
| Eval Runner <-> Gateway | Eval reads session logs from NFS, reports via Telegram | Eval CronJob has read access to session and content directories |
| Eval Runner <-> Prompt Tuner | Eval store (SQLite) provides trend data for manual analysis | Human-gated process, not automated handoff |
| Dictionary <-> All Pipeline Components | ConfigMap mounted as read-only volume in all Jobs and Gateway | Single source of truth for UHT terminology |

## Sources

- [Deepgram: Best Speech-to-Text APIs 2026](https://deepgram.com/learn/best-speech-to-text-apis-2026) -- API comparison and pricing (HIGH confidence)
- [Deepgram: Whisper vs Deepgram 2025](https://deepgram.com/learn/whisper-vs-deepgram) -- keyword boosting, custom vocabulary (HIGH confidence)
- [Promptfoo: Self-hosting docs](https://www.promptfoo.dev/docs/usage/self-hosting/) -- self-hosted limitations documented (HIGH confidence)
- [Braintrust: Best Promptfoo Alternatives 2026](https://www.braintrust.dev/articles/best-promptfoo-alternatives-2026) -- eval landscape overview (MEDIUM confidence)
- [Outerbounds: Whisper with Metaflow on Kubernetes](https://outerbounds.com/blog/whisper-kubernetes) -- K8s transcription patterns (MEDIUM confidence)
- [GitHub: faster-whisper](https://github.com/SYSTRAN/faster-whisper) -- self-hosted alternative analysis (HIGH confidence)
- [Recall.ai: Zoom Cloud Recording API](https://www.recall.ai/blog/zoom-transcript-api) -- Zoom integration options (MEDIUM confidence)
- Existing codebase: `halos/watchctl/evaluate.py` (LLM-as-judge precedent), `halos/eventsource/aura_relay.py` (NATS integration), `halos/nightctl/` (state machine pattern) -- verified in repo

---
*Architecture research for: Video content repurposing + LLM eval on K8s AI agent platform*
*Researched: 2026-04-07*
