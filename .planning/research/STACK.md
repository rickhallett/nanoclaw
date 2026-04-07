# Technology Stack

**Project:** Halo for Aura (Client 001) — Content Repurposing + LLM Eval
**Researched:** 2026-04-07

## Recommended Stack

### Transcription

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Deepgram Nova-3 | API (latest) | Primary transcription engine | Native keyword boosting ("keyterm prompting") for custom vocabulary without fine-tuning. Self-serve customization — add UHT terms (Microcosmic Orbit, Chi Nei Tsang, nudan) at API call time, no model retraining. $0.0043-0.0145/min pre-recorded. Python SDK is a thin wrapper, fits the halos pattern. | HIGH |
| deepgram-sdk | >=4.0 | Python SDK | Official SDK, straightforward `client.listen.v1.media.transcribe_file()` pattern. Async support. | HIGH |

**Why not Whisper API:** OpenAI Whisper ($0.006/min) is cheaper but has no native custom vocabulary support. The `initial_prompt` hack is unreliable and size-limited. For Daoist/UHT terminology, Whisper will butcher "Chi Nei Tsang" and "nudan" consistently. Fine-tuning Whisper is possible but overkill for this use case — Deepgram's keyterm prompting solves it at the API level.

**Why not AssemblyAI:** Good custom vocabulary support but more expensive ($0.015/min) and the Python SDK is heavier. Deepgram's Nova-3 matches or beats accuracy on English audio.

**Why not self-hosted Whisper/WhisperX:** Running inference in-cluster adds GPU requirements to Vultr VKE. The cost economics don't work for a pilot at 4-8 recordings/month. Cloud API is the right call at this scale.

### Video Processing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ffmpeg | system binary | Video/audio extraction, clip cutting, format conversion | Already installed in fleet containers. Industry standard. No reason to use anything else for media manipulation. | HIGH |
| ffmpeg-python | >=0.2.0 | Python wrapper for ffmpeg CLI | Programmatic ffmpeg command building. Lighter than MoviePy, no PIL dependency chain. Fits the subprocess-wrapper pattern used elsewhere in halos (himalaya, claude CLI). | MEDIUM |
| yt-dlp | >=2024.0 | Zoom cloud recording download (if URL-based delivery) | Handles authenticated video downloads. May not be needed if Aura uploads directly via Telegram. Include as optional dependency. | LOW |

**Why not MoviePy:** MoviePy pulls in numpy, imageio, PIL — heavyweight for what is essentially "cut video at timestamps and extract audio." ffmpeg-python is a thin command builder, which is the halos way.

**Why not PyAV:** Low-level FFmpeg bindings are overkill. We're cutting clips, not building a video editor.

### LLM Evaluation Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| deepeval | >=2.0 | LLM evaluation framework | **Python-native, pytest-integrated, 50+ built-in metrics, custom G-Eval for arbitrary criteria.** This is the right choice because: (1) existing test infrastructure is pytest, (2) custom metrics via G-Eval let us define "voice fidelity" and "overpromise detection" as natural language criteria evaluated by Claude, (3) native Anthropic support for judge model, (4) runs in CI. | HIGH |

**Why not promptfoo:** Promptfoo is YAML/CLI-first, Node.js-native. It excels at prompt comparison across providers — not what we need. We need pytest-integrated evaluation of specific output qualities (voice fidelity, terminology accuracy, overpromise detection). DeepEval's G-Eval metric maps directly to these custom criteria. Also: promptfoo was acquired by OpenAI in March 2026, which introduces vendor alignment concerns for an Anthropic-primary stack.

**Why not custom eval scripts:** DeepEval provides the scaffolding (test cases, metrics, scoring, reporting) that would take weeks to build from scratch. The G-Eval metric is essentially "LLM-as-judge with CoT" which is exactly what voice fidelity scoring needs, but with proper statistical foundations.

**Why not Braintrust/LangSmith:** SaaS platforms add cost and data residency concerns. DeepEval is open source, runs locally, and the pytest integration means eval results show up in the same test output as everything else.

### Custom Eval Metrics (built on DeepEval)

| Metric | Type | What It Measures | Implementation |
|--------|------|-----------------|----------------|
| Voice Fidelity | G-Eval (custom) | Does output match Aura's communication patterns? Soft, educational, meditative pace, Lao Tzu quotes, never salesy. | G-Eval with rubric from intake session baseline |
| Overpromise Detection | G-Eval (custom) | Does content make claims beyond what Aura actually teaches? | G-Eval with criteria: no healing claims, no medical promises, factual to recording |
| Terminology Accuracy | Deterministic + G-Eval | Are UHT terms spelled correctly and used in proper context? | Regex check for known terms + G-Eval for contextual accuracy |
| Drift Monitor | G-Eval (custom) | Has output style drifted from baseline over time? | Compare recent outputs against baseline corpus, score consistency |
| Content Completeness | G-Eval (custom) | Does the Instagram post capture the key teaching points from the recording segment? | G-Eval comparing transcript segment to generated content |

### Instagram Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Instagram Graph API | v21.0+ | Content publishing (official) | Two-step container model: create media container, then publish. Supports images, carousels, reels. 50 posts/24h limit (more than enough). Requires Instagram Business account. | HIGH |
| httpx | >=0.27.0 (existing) | HTTP client for Graph API calls | Already in the stack. The Graph API is simple REST — create container, poll status, publish. No SDK needed. Write a thin wrapper in halos, same pattern as Telegram bot API calls. | HIGH |

**Why not instagrapi:** Uses Instagram's private/reverse-engineered API. Explicitly "not suited for business applications." Account ban risk. The official Graph API does everything we need for publishing.

**Why not python-facebook-api / Instagram-Python-SDK:** The Graph API publishing flow is 3 HTTP calls. Adding a dependency for 3 calls violates the halos principle of thin wrappers over simple APIs. httpx + a 50-line module is the right abstraction.

**Important constraint:** Instagram Graph API requires a Facebook App, Instagram Business Account, and OAuth token management (60-day long-lived tokens with refresh). This is setup complexity, not code complexity. Budget time for Meta developer account configuration.

### Prompt Management

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Jinja2 | >=3.0 (existing) | Prompt template rendering | Already in the stack. Prompt templates with variable substitution. No new dependency needed. | HIGH |
| YAML config files | -- | Prompt version storage | Same pattern as briefings.yaml, watchctl.yaml. Store prompt versions with metadata (version, eval scores, active flag). File-based, git-tracked, no database needed. | HIGH |

**Why not LangChain/LangSmith:** Massive dependency tree for prompt management that amounts to string interpolation + versioning. Jinja2 + YAML + git gives us versioned, diffable, reviewable prompts with zero new dependencies.

**Why not a prompt database:** At pilot scale (2 agents, <10 prompt templates), a database adds complexity without value. YAML files in git provide version history, diff, and review for free.

### Content Pipeline Orchestration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python modules in halos | -- | Pipeline orchestration | New halos module: `contentctl`. Steps: ingest -> transcribe -> segment -> generate -> eval -> review -> publish. Each step is a function. SQLite for pipeline state (same pattern as nightctl). No workflow engine needed at this scale. | HIGH |
| SQLite | stdlib | Pipeline state tracking | Recording status, transcription results, generated content, eval scores, publish status. Same pattern as every other halos module. | HIGH |

**Why not Celery/Airflow/Temporal:** 4-8 recordings per month. A workflow engine for 4 jobs/month is architectural vanity. A Python module with SQLite state tracking handles this with zero operational overhead. Revisit if/when volume exceeds 50 recordings/month.

### Custom Terminology Dictionary

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| YAML dictionary file | -- | UHT term definitions, correct spellings, context | `aura-dictionary.yaml` at config root. Terms, aliases, phonetic hints (for Deepgram keyterm prompting), definitions, usage context. Loaded by transcription step and eval metrics. | HIGH |
| Deepgram keyterm prompting | API feature | Feed dictionary terms to Deepgram at transcription time | Nova-3's keyterm prompting accepts terms at request time. No model training. Add terms to dictionary, they're automatically included in next transcription. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Transcription | Deepgram Nova-3 | OpenAI Whisper API | No native custom vocabulary; UHT terms will be mangled |
| Transcription | Deepgram Nova-3 | Self-hosted Whisper | GPU requirements on VKE; cost doesn't work at pilot scale |
| Video Processing | ffmpeg-python | MoviePy | Heavy dependency chain (numpy, PIL) for simple clip cutting |
| LLM Eval | DeepEval | Promptfoo | Node.js-native, YAML-config; doesn't fit pytest/Python stack |
| LLM Eval | DeepEval | Custom scripts | Weeks of scaffolding work; G-Eval metric is exactly what we need |
| Instagram | Graph API + httpx | instagrapi | Private API, ban risk, "not for business" |
| Instagram | Graph API + httpx | Python SDK wrappers | 3 HTTP calls don't need a library |
| Orchestration | halos module + SQLite | Celery/Airflow | 4 jobs/month doesn't need a workflow engine |
| Prompts | Jinja2 + YAML + git | LangChain | Massive deps for string interpolation |

## Installation

```bash
# New dependencies (add to pyproject.toml)
# Core
deepgram-sdk>=4.0          # Transcription API client
deepeval>=2.0              # LLM evaluation framework
ffmpeg-python>=0.2.0       # Video processing wrapper

# Optional (if Zoom cloud URL delivery)
yt-dlp>=2024.0             # Video download

# Already in stack (no changes needed)
# httpx>=0.27.0            # Instagram Graph API calls
# jinja2>=3.0              # Prompt templates
# pyyaml>=6.0              # Config files
# anthropic>=0.84.0        # LLM for eval judge + content generation
```

```bash
# System dependency (already in container)
# ffmpeg — already installed in fleet Dockerfile

# Dev dependency
pip install deepeval  # or add to [dev] extras for eval CLI
```

## New Environment Variables

| Variable | Purpose | Where |
|----------|---------|-------|
| `DEEPGRAM_API_KEY` | Transcription API auth | K8s Secret, .env |
| `META_APP_ID` | Facebook App ID for Instagram Graph API | K8s Secret, .env |
| `META_APP_SECRET` | Facebook App Secret | K8s Secret, .env |
| `INSTAGRAM_ACCESS_TOKEN` | Long-lived user token (60-day, needs refresh) | K8s Secret, .env |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Aura's Instagram Business Account ID | K8s ConfigMap |

## New halos Modules

| Module | Command | Purpose |
|--------|---------|---------|
| contentctl | `contentctl` | Content pipeline orchestration: ingest, transcribe, segment, generate, eval, review, publish |
| evalctl | `evalctl` | LLM evaluation runner: baseline capture, drift monitoring, eval suite execution |
| instactl | `instactl` | Instagram Graph API wrapper: create container, publish, token refresh |

## Cost Estimate (Pilot)

| Service | Usage | Monthly Cost |
|---------|-------|-------------|
| Deepgram Nova-3 | ~8 recordings x 90min = 720min @ $0.0043/min | ~$3.10 |
| Anthropic Claude (content gen) | ~40 generations @ ~2K tokens each | ~$2-4 |
| Anthropic Claude (eval judge) | ~200 eval runs @ ~1K tokens each | ~$3-5 |
| Instagram API | Free (Graph API) | $0 |
| **Total incremental** | | **~$8-12/month** |

Within the GBP 50-80/month compute budget with room to spare.

## Sources

- [Deepgram Nova-3 announcement](https://deepgram.com/learn/introducing-nova-3-speech-to-text-api) — keyterm prompting, self-serve customization
- [Deepgram Python SDK](https://github.com/deepgram/deepgram-python-sdk) — official SDK
- [Deepgram keywords docs](https://developers.deepgram.com/docs/keywords) — keyword boosting API
- [Deepgram pricing](https://deepgram.com/pricing) — pay-as-you-go rates
- [DeepEval docs](https://deepeval.com/docs/getting-started) — Python LLM eval framework
- [DeepEval G-Eval](https://deepeval.com/docs/metrics-llm-evals) — custom criteria evaluation
- [DeepEval vs Promptfoo comparison](https://nimbleapproach.com/blog/technical-deep-dive-promptfoo-vs-deepeval-for-automated-ai-evaluation/) — framework comparison
- [Instagram Graph API publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) — official publishing docs
- [Instagram API guide 2026](https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/) — current API state
- [Whisper custom vocabulary limitations](https://github.com/openai/whisper/discussions/1522) — no native custom vocab support
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) — Python ffmpeg wrapper
- [Promptfoo OpenAI acquisition](https://www.promptfoo.dev/docs/intro/) — acquired March 2026, MIT licensed

---

*Stack research: 2026-04-07*
