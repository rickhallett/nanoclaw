# Domain Pitfalls

**Domain:** AI content repurposing + LLM eval infrastructure
**Researched:** 2026-04-07

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Voice Drift Without Detection
**What goes wrong:** LLM-generated content gradually drifts from Aura's voice toward generic wellness copywriting. Each individual post looks "fine" but the cumulative effect is a brand that doesn't sound like her.
**Why it happens:** LLMs have strong priors toward popular writing styles. Without continuous measurement, drift is invisible until the client says "this doesn't sound like me anymore."
**Consequences:** Trust destruction. Client stops using the system. Rewrite of all prompts.
**Prevention:** Voice fidelity eval on every generation, not just during development. Drift monitoring comparing recent outputs to intake baseline. Threshold alerts when scores drop below 0.7.
**Detection:** Declining eval scores over time. Aura rejecting more posts in review. Language becoming more generic.

### Pitfall 2: Transcription Garbage In, Content Garbage Out
**What goes wrong:** Deepgram mangles UHT terminology despite keyterm prompting. "Microcosmic Orbit" becomes "microscopic orbit." Generated content propagates the error.
**Why it happens:** Keyterm prompting boosts probability but doesn't guarantee. Zoom audio quality varies. Background noise, accents, overlapping speech.
**Consequences:** Factually incorrect content. Aura loses trust in the system. Every post requires manual correction.
**Prevention:** (1) Comprehensive dictionary with phonetic hints before first transcription. (2) Post-transcription terminology check — regex scan for known terms + fuzzy match for near-misses. (3) Correction step before content generation.
**Detection:** Terminology accuracy metric in eval suite. Manual spot-check of first 5 transcriptions.

### Pitfall 3: Instagram Token Expiry Silent Failure
**What goes wrong:** Instagram long-lived access token expires after 60 days. Publishing silently fails. No error surfaced to Aura or operator.
**Why it happens:** OAuth token lifecycle is easy to forget. No built-in reminder in the Graph API.
**Consequences:** Approved content never gets published. Aura thinks system is broken. Manual intervention needed.
**Prevention:** Token expiry tracking in SQLite. Cron job to check expiry 7 days before. Telegram alert to operator when refresh needed. Token refresh endpoint in instactl.
**Detection:** Failed publish API calls. Token expiry date check in health monitoring.

### Pitfall 4: Eval Metrics That Don't Correlate With Human Judgment
**What goes wrong:** Eval framework reports high scores but Aura rejects the posts. Or: low scores on content Aura likes.
**Why it happens:** G-Eval criteria are written by the developer, not calibrated against Aura's actual preferences. LLM-as-judge has its own biases.
**Consequences:** False confidence in content quality. Eval becomes noise that gets ignored. Defeats the purpose of eval infrastructure.
**Prevention:** (1) Calibration phase: generate 20 posts, have Aura rate them 1-5, compare against eval scores. (2) Adjust rubric criteria until correlation is >0.7. (3) Track approve/reject rates as the ground truth metric.
**Detection:** Low correlation between eval scores and Aura's approve/reject decisions.

## Moderate Pitfalls

### Pitfall 1: Over-Engineering the Pipeline for 4 Recordings/Month
**What goes wrong:** Building Celery queues, retry logic, dead letter queues, monitoring dashboards for a workload that runs 4 times per month.
**Prevention:** State machine in SQLite. Manual retry via CLI command. Dashboard is `contentctl status`. Add infrastructure only when it breaks.

### Pitfall 2: Prompt Template Proliferation
**What goes wrong:** Different prompt templates for different content types, teaching styles, topics. 15 templates that are 90% identical.
**Prevention:** One base template with Jinja2 conditionals. Template inheritance if needed. Version in git, not in database.

### Pitfall 3: Segment Boundaries Wrong
**What goes wrong:** LLM-assisted transcript segmentation cuts in the middle of a teaching concept, or groups unrelated topics.
**Prevention:** Use topic markers from the recording (Aura typically announces what she's teaching). Err on larger segments. Let Aura adjust segment boundaries in review.

### Pitfall 4: Meta Developer Account Setup Friction
**What goes wrong:** Instagram Graph API requires Facebook App review, Business Account verification, and proper permissions. This can take days-weeks if not started early.
**Prevention:** Start Meta developer account setup in phase 1, even if Instagram publishing is phase 2. Decouple account setup from code implementation.

### Pitfall 5: Deepgram Cost Surprises
**What goes wrong:** Deepgram's $200 free credit runs out faster than expected due to development/testing iterations.
**Prevention:** Track API usage from day one. Use short test clips during development, not full 90-minute recordings. Cache transcription results — never re-transcribe the same recording.

## Minor Pitfalls

### Pitfall 1: Instagram Caption Length Limits
**What goes wrong:** Generated captions exceed Instagram's 2200 character limit.
**Prevention:** Character count check in content generation step. Prompt template includes length constraint.

### Pitfall 2: Hashtag Strategy Mismatch
**What goes wrong:** Generic wellness hashtags (#healing #meditation) instead of niche UHT hashtags.
**Prevention:** Hashtag list in dictionary or separate config. Domain-specific: #QiGong #TaoistPractice #ChiNeiTsang #UHT not #wellness #selfcare.

### Pitfall 3: Timezone Issues in Scheduling
**What goes wrong:** Content scheduled for posting uses UTC but Aura thinks in GMT/BST.
**Prevention:** All user-facing times in Europe/London timezone. Internal storage in UTC. Convert at display boundary.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dictionary setup | Incomplete term list — misses terms Aura uses informally | Review first 3 transcriptions with Aura, iterate dictionary |
| Transcription integration | Audio quality variance across Zoom recordings | Test with actual recordings, not clean test audio |
| Eval baseline | Criteria that don't match Aura's actual preferences | Calibration phase with Aura rating real outputs |
| Content generation | Generic wellness tone despite prompt engineering | Voice fidelity eval as hard gate — don't proceed until scores > 0.8 |
| Instagram integration | Meta developer account setup delays | Start account setup immediately, before any code |
| Prompt tuning | Overfitting to eval metrics at the expense of naturalness | Human review remains the ultimate gate; eval is advisory |

## Sources

- [Whisper custom vocabulary limitations](https://github.com/openai/whisper/discussions/1522) — why Deepgram over Whisper
- [Instagram Graph API token lifecycle](https://developers.facebook.com/docs/instagram-platform/content-publishing/) — 60-day tokens
- [DeepEval G-Eval calibration](https://deepeval.com/docs/metrics-llm-evals) — LLM-as-judge considerations
- [Deepgram pricing](https://deepgram.com/pricing) — $200 free credit, pay-as-you-go rates
- PROJECT.md — Aura's voice characteristics, workflow, constraints

---

*Pitfalls research: 2026-04-07*
