# Feature Research

**Domain:** AI content repurposing for wellness practitioners + LLM eval for voice fidelity
**Researched:** 2026-04-07
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features Aura (and any wellness practitioner client) would assume exist. Missing these means the Content Alchemist feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Zoom recording ingestion** | Core input — Aura records on Zoom, agent must accept recordings without manual steps | MEDIUM | Three delivery paths to support: Zoom cloud link, Google Drive share, or direct Telegram upload. Start with one, expand. Zoom's native transcription API is available but quality varies for domain-specific terms. |
| **Transcription with UHT dictionary correction** | "Microcosmic Orbit" must not become "microscopic orbit" — domain terminology is non-negotiable | HIGH | Whisper large-v3 + post-processing correction layer. Contextual biasing (arxiv:2410.18363) avoids fine-tuning: inject UHT term list as prefix constraints. Fallback: LLM-based semantic correction pass on raw transcript. |
| **Text post generation in Aura's voice** | The entire value proposition — recordings become Instagram captions | MEDIUM | LLM generation with few-shot examples from intake session. System prompt encodes voice attributes: soft, educational, meditative pace, Lao Tzu woven naturally, never salesy. |
| **Human review before publish** | Aura confirmed: no autonomous posting. Every piece reviewed via Telegram approve/reject | LOW | Telegram inline keyboard: preview + approve/edit/reject. Approved content stored for posting. This is a hard constraint, not a feature to defer. |
| **Content queue and scheduling** | Practitioners batch Sunday afternoons — need to review multiple pieces, schedule across the week | LOW | Simple FIFO queue with suggested posting times. No calendar integration needed yet — just "Monday AM / Wednesday PM / Friday AM" slots. |
| **Caption style options** | "Pull exact quotes" vs "paraphrase in her style" — Aura needs to choose per piece | LOW | Two generation modes per transcript segment: verbatim extract with light editing, or full LLM paraphrase. Flag in generation config. |
| **Transcript browsable by topic** | 80-90min sessions cover multiple practices — Aura needs to see what's in each recording | MEDIUM | Segment transcript by topic/practice using LLM classification. Display as chapters: "0:00-12:30 Earth Element Qi Gong", "12:30-28:00 Healing Sounds", etc. |
| **Instagram post formatting** | Output must be ready to post, not raw text needing manual editing | LOW | Caption length limits (2200 chars), hashtag strategy, line breaks for visual rhythm, hook in first line. |

### Differentiators (Competitive Advantage)

Features that separate a bespoke Halo deployment from generic tools like OpusClip or Repurpose.io.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Voice fidelity eval with drift detection** | Generic tools don't monitor whether output sounds like the practitioner — they just generate. Halo's eval harness catches voice drift before content goes out. | HIGH | Extend existing `watchctl/rubric.py` weighted scoring system. LLM-as-judge with Aura-specific rubric: tone (soft/educational), terminology accuracy, Lao Tzu integration naturalness, absence of generic wellness slop. Baseline from intake session transcripts. |
| **Overpromise detection guardrails** | Wellness content walks a regulatory line. "This will heal your trauma" is legally dangerous. Aura's philosophy is "healing is return, not fix" — agent must never cross into medical claims. | HIGH | Classification layer on generated content. Deny-list patterns: cure/heal/fix/treat + condition names. Allow-list: Aura's actual framing ("return to", "cultivate", "invite"). LLM-as-judge rubric criterion with weight 4 (highest). FDA grey area for wellness content makes this non-optional for a responsible product. |
| **Custom terminology dictionary (living)** | UHT system has 50+ domain terms that no generic tool handles. Dictionary evolves as Aura teaches new modules. | MEDIUM | YAML-based term registry: canonical spelling, common mistranscriptions, context definitions. Used by transcription correction AND generation quality checks. Aura adds terms via Telegram: "add term: nuedan -> nudan (female alchemy)". |
| **Programme structure extraction** | Dao Assistant value — from a series of recordings, identify curriculum structure, prerequisites, progression paths | HIGH | Requires multi-session context. Cluster topics across recordings, identify teaching sequences, flag gaps. Produces structured programme outlines for website/funnel. Defer to post-Content Alchemist validation. |
| **Lineage-aware content framing** | Aura is certified UHT UK under Master Chia's system. Content must reference lineage correctly — this is credibility infrastructure in the wellness world. | LOW | System prompt encoding + eval rubric criterion. Master Chia attribution where appropriate, UHT certification context, no claiming techniques outside certified scope. |
| **Engagement pattern learning** | Track which generated posts Aura approves vs rejects/edits. Feed preferences back into generation. | MEDIUM | Log approve/reject/edit decisions. After 20+ decisions, run preference extraction: what patterns does she approve? What does she edit out? Adjust generation few-shot examples. Existing `trackctl` pattern applies. |
| **Prompt tuning pipeline** | Eval results automatically inform prompt refinements — closed loop between quality measurement and generation improvement. | HIGH | Eval scores identify weak dimensions. Suggest prompt changes. Track prompt versions against score trajectories. Prevents "works today, drifts next month." |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Autonomous social media posting** | "Save me the step of posting manually" | Aura explicitly requires review. Autonomous posting in wellness = reputational risk. One bad post about "healing trauma" and credibility evaporates. FDA grey area for wellness claims compounds the risk. | Human-in-the-loop always. Agent generates, Aura approves, then either manual post or single-click publish via API with confirmed content only. |
| **Video clip extraction with AI highlight detection** | OpusClip and CapCut do this — seems table stakes | Massive complexity jump. Requires video processing pipeline (ffmpeg, scene detection, reframing for vertical), separate from text generation. Aura's Zoom recordings are talking-head — highlight detection algorithms optimized for podcasts/interviews don't map well to guided practice sessions where value is in the teaching, not visual highlights. | Start with text-only content from transcripts. Add video clips as v2 only if Aura requests and validates text content quality first. The transcript is the value — video clips are distribution optimization. |
| **Multi-platform auto-formatting** | "Post to Instagram, TikTok, YouTube Shorts, LinkedIn simultaneously" | Each platform has different content culture. Wellness content that works on Instagram (meditative, visual) fails on LinkedIn (professional framing). Auto-formatting creates mediocre everywhere instead of excellent somewhere. | Instagram-first. Single platform mastery. Aura's audience is on Instagram. Expand only after Instagram content quality is validated. |
| **Real-time transcription during live sessions** | "Transcribe as I teach so students get notes instantly" | Latency, accuracy drops with real-time ASR, domain terms fail harder in streaming mode. Distracts from teaching. Changes the product from "repurposing tool" to "live captioning service" — different problem entirely. | Post-session processing only. Aura records, uploads after session, gets content next day. Matches her Sunday afternoon workflow. |
| **AI-generated hashtag optimization** | "Maximize reach with trending hashtags" | Generic hashtag stuffing looks desperate and contradicts Aura's "nothing forced, slowness creates transformation" philosophy. Algorithm-chasing is the opposite of her brand. | Curated hashtag sets per content category (Qi Gong, breathwork, feminine energy). 5-8 relevant tags, not 30 trending ones. Updated monthly, not per-post. |
| **AI-generated images** | "Create visual content to go with posts" | Aura's content is practice recordings and teachings. AI-generated imagery is off-brand for a practitioner whose credibility comes from embodied practice, not generated visuals. | Use video stills from recordings, simple text cards, or Aura's own photos. |
| **Competitor content analysis** | "Show me what other wellness teachers post so I can match their style" | Leads to homogenized content. Aura's differentiation IS her unique voice and UHT lineage. Copying competitors erases the competitive advantage. | Voice fidelity eval ensures Aura sounds like Aura, not like the wellness Instagram average. |

## Feature Dependencies

```
[Custom UHT Dictionary]
    +--enables--> [Transcription with Dictionary Correction]
                      +--enables--> [Transcript Segmentation by Topic]
                      +--enables--> [Text Post Generation in Voice]
                                        +--gated-by--> [Voice Fidelity Eval]
                                        +--gated-by--> [Overpromise Detection]
                                        +--feeds-into-> [Telegram Review Flow]
                                                            +--enables--> [Content Queue/Scheduling]
                                                            +--feeds--> [Engagement Pattern Learning]

[Intake Session Baseline]
    +--enables--> [Voice Fidelity Eval Rubric]
    +--enables--> [Few-shot Examples for Generation]

[Voice Fidelity Eval]
    +--extends--> [Existing halctl eval_harness + watchctl rubric.py]
    +--includes-> [Overpromise Detection as highest-weight criterion]
    +--feeds----> [Prompt Tuning Pipeline]

[Transcript Segmentation] (multi-session accumulation)
    +--enables--> [Programme Structure Extraction] (v2+)
```

### Dependency Notes

- **Text Post Generation is gated by Voice Fidelity Eval:** Generation without eval is generic wellness slop. Eval must exist before any content reaches Aura for review — otherwise early output sets wrong expectations and erodes trust.
- **Transcription requires Custom Dictionary:** Without UHT term correction, transcripts are unusable. "Chi Nei Tsang" becoming "Chinese Zong" means all downstream content is wrong. Dictionary must be populated before first transcription run.
- **Engagement Pattern Learning requires Human Review Flow:** The approve/reject signal IS the training data. No review flow = no learning loop.
- **Programme Structure Extraction requires multiple sessions:** Single-session transcription is prerequisite, but programme extraction needs cross-session analysis. This is why it's a v2+ feature.
- **Voice Fidelity Eval extends existing infrastructure:** `watchctl/rubric.py` already has weighted criteria, LLM-as-judge prompting, and verdict thresholds. `halctl/eval_harness.py` has multi-turn scenario testing. Aura's eval reuses these patterns, not builds from scratch.

## MVP Definition

### Launch With (v1) -- Content Alchemist Core

- [ ] **Custom UHT terminology dictionary** -- YAML registry, manually curated from intake + teaching materials, used by all downstream features
- [ ] **Zoom recording ingestion** (single path: whichever Aura chooses) -- accept recording via Telegram, trigger processing pipeline
- [ ] **Transcription with dictionary correction** -- Whisper + post-processing correction using term dictionary
- [ ] **Transcript segmentation by topic** -- LLM-classified chapters for 80-90min sessions
- [ ] **Text post generation in Aura's voice** -- few-shot from intake, two modes (verbatim extract / LLM paraphrase)
- [ ] **Voice fidelity eval rubric** -- LLM-as-judge scoring before content reaches Aura, extends existing rubric.py
- [ ] **Overpromise detection** -- deterministic deny-list + LLM judge criterion (highest weight)
- [ ] **Telegram review flow** -- preview, approve/edit/reject inline keyboard

### Add After Validation (v1.x) -- Content Alchemist Maturation

- [ ] **Content queue and scheduling** -- trigger: Aura has approved 5+ pieces and wants to spread them across the week
- [ ] **Engagement pattern learning** -- trigger: 20+ approve/reject decisions logged, enough signal to extract preferences
- [ ] **Prompt tuning pipeline** -- trigger: eval scores show consistent weak dimensions across 10+ generation runs
- [ ] **Instagram API direct publishing** -- trigger: manual copy-paste becomes friction point, Aura requests. Requires Meta developer account setup.
- [ ] **Drift monitoring dashboard** -- trigger: 4+ weeks of generation history, enough data to detect trends
- [ ] **Additional recording delivery paths** -- trigger: initial path proves friction-heavy for Aura

### Future Consideration (v2+) -- Dao Assistant + Growth

- [ ] **Programme structure extraction** -- defer until Content Alchemist validated AND Aura has 5+ session recordings across element series
- [ ] **Video clip extraction** -- defer until text content is validated AND Aura explicitly requests video format. Requires ffmpeg pipeline, scene detection, vertical reframing.
- [ ] **Dao Assistant agent** -- programme structuring, website/funnel guidance. Defer until Content Alchemist proves value.
- [ ] **Council advisors for Aura** -- roundtable-style advisors customized for her domain. Defer: agents first, council later (per PROJECT.md).

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Custom UHT dictionary | HIGH | LOW | P1 |
| Zoom recording ingestion | HIGH | MEDIUM | P1 |
| Transcription + correction | HIGH | MEDIUM | P1 |
| Voice fidelity eval rubric | HIGH | HIGH | P1 |
| Overpromise detection | HIGH | MEDIUM | P1 |
| Text post generation | HIGH | MEDIUM | P1 |
| Telegram review flow | HIGH | LOW | P1 |
| Transcript segmentation | MEDIUM | MEDIUM | P1 |
| Instagram post formatting | MEDIUM | LOW | P1 |
| Content queue/scheduling | MEDIUM | LOW | P2 |
| Engagement pattern learning | MEDIUM | MEDIUM | P2 |
| Prompt tuning pipeline | HIGH | HIGH | P2 |
| Instagram API publishing | LOW | MEDIUM | P2 |
| Drift monitoring | MEDIUM | MEDIUM | P2 |
| Programme structure extraction | MEDIUM | HIGH | P3 |
| Video clip extraction | LOW | HIGH | P3 |
| Dao Assistant agent | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch -- the Content Alchemist doesn't work without these
- P2: Should have, add after Content Alchemist proves it generates content Aura approves
- P3: Future consideration, requires validated foundation and explicit client request

## Competitor Feature Analysis

| Feature | OpusClip | Repurpose.io | Descript | Halo for Aura |
|---------|----------|--------------|----------|------------------------------|
| Video clip extraction | Core feature, AI highlight detection, viral scoring | Distribution only, no clip creation | Full video editor with AI | Not v1. Text content from transcript first. |
| Transcription | Basic, no custom vocabulary | No transcription (distribution tool) | Whisper-based, good general accuracy | Whisper + UHT dictionary correction layer |
| Brand voice control | Template system (visual branding only) | None | Script-level editing | LLM-as-judge voice fidelity eval with weighted rubric |
| Custom terminology | None | None | Custom dictionary for captions | Living YAML dictionary, transcription + generation |
| Content review flow | Download and post manually | Auto-publish rules | Export workflow | Telegram inline approve/reject, human always in loop |
| Tone monitoring | None | None | None | Voice drift detection, overpromise guardrails |
| Overpromise detection | None | None | None | Deterministic deny-list + LLM-as-judge with wellness-specific criteria |
| Multi-platform | YouTube, TikTok, Instagram, LinkedIn | 20+ platform connectors | Export to multiple formats | Instagram-only. Single platform mastery. |
| Pricing | $15-75/mo SaaS | $25-50/mo SaaS | $24-33/mo SaaS | Bespoke: GBP 300 setup + compute cost |

**Key insight:** No competitor monitors voice fidelity or detects overpromising. This is the moat. Generic tools generate content -- Halo generates content that provably sounds like Aura and provably doesn't make dangerous claims.

## LLM Eval Framework: Voice Fidelity + Overpromise Monitoring

### Existing Infrastructure to Extend

Halo already has:
- **`halctl/eval_harness.py`**: Multi-turn scenario assessment with structured YAML records, assertions, state reset between scenarios. 8 scenarios, tested across personality profiles.
- **`watchctl/rubric.py`**: Weighted rubric scoring with LLM-as-judge support, YAML-defined criteria, `compute_overall()` for weighted averages, `score_to_verdict()` with configurable thresholds.
- **Eval baseline methodology** (docs/d1/eval-baseline-2026-03-18.md): DB injection, response capture, per-personality variance tracking. Standing decision: "Accept personality variance as data, not bugs."

### Aura Voice Fidelity Rubric (Proposed)

```yaml
name: aura-voice-fidelity
version: 1
description: Evaluates generated content against Aura's communication patterns

criteria:
  tone_softness:
    weight: 3
    scale: [1, 5]
    description: >
      Content has soft, educational, meditative pace. No urgency, no
      hard sells, no exclamation-heavy enthusiasm. Quiet authority.
      5 = reads like Aura's actual speech. 1 = generic Instagram energy.

  terminology_accuracy:
    weight: 3
    scale: [1, 5]
    description: >
      UHT terms used correctly: Microcosmic Orbit, Chi Nei Tsang,
      nudan, 6 Healing Sounds, ovarian breathing, 9 Flowers Nei Kung.
      No misspellings, no invented terms, no conflation of practices.
      5 = all terms correct and contextually appropriate. 1 = wrong terms.

  overpromise_absence:
    weight: 4
    scale: [1, 5]
    description: >
      No medical claims, no cure/heal/fix language applied to conditions.
      Uses Aura's framing: "return to", "cultivate", "invite", "practice".
      Body leads, healing is return not fix, nothing forced.
      5 = clean, no claims. 1 = makes therapeutic promises.

  lao_tzu_integration:
    weight: 1
    scale: [1, 5]
    description: >
      If Lao Tzu quotes appear, they are woven naturally -- not bolted on.
      Not every piece needs a quote. Forced quotes score lower than no quotes.
      5 = naturally integrated or appropriately absent. 1 = forced/irrelevant.

  instagram_readability:
    weight: 2
    scale: [1, 5]
    description: >
      Content works as Instagram caption: appropriate length (150-300 words),
      has visual rhythm (short paragraphs, breathing room), hook in first
      line, call to softly engage (not hard CTA).
      5 = ready to post. 1 = reads like a transcript dump.

  lineage_respect:
    weight: 2
    scale: [1, 5]
    description: >
      Master Chia and UHT lineage referenced appropriately when relevant.
      No claiming techniques outside certified scope. Proper attribution.
      5 = lineage handled with integrity. 1 = claims or omits inappropriately.

verdict_thresholds:
  PUBLISH: 4.0    # Goes to Aura for review
  REVIEW: 3.0     # Flagged with eval notes, Aura sees warnings
  REJECT: 0.0     # Blocked, logged, triggers prompt tuning signal
```

### Eval Pipeline Architecture

1. **Generation** -- Content Alchemist produces Instagram post from transcript segment
2. **Overpromise scan** -- Deterministic deny-list check (fast, cheap, catches obvious violations)
3. **Voice fidelity eval** -- LLM-as-judge scores against rubric (uses existing `rubric.py` compute_overall + score_to_verdict)
4. **Gate decision** -- PUBLISH: goes to Aura for review. REVIEW: flagged with eval notes. REJECT: blocked, logged, prompt tuning signal.
5. **Human review** -- Aura approves/edits/rejects via Telegram
6. **Feedback loop** -- Aura's decisions feed back into few-shot examples and rubric calibration

### Overpromise Detection Patterns

```
# Hard deny: never combine these action verbs with health conditions
ACTIONS: cure, heal, fix, treat, remedy, resolve, eliminate, eradicate
CONDITIONS: anxiety, depression, trauma, PTSD, pain, disease, illness, disorder

# Soft flag: review context before allowing
SOFT_FLAG: improve, reduce, alleviate, manage, relieve
# These are OK when framed as "practice may support" not "this will improve"

# Aura-approved framing (allow-list)
APPROVED: return to, cultivate, invite, practice, explore, soften into,
          create space for, allow, open, nourish, support (without guarantees)
```

### Why Build Eval In-House vs Use DeepEval/Promptfoo/Braintrust

The existing `watchctl/rubric.py` already implements weighted rubric scoring with LLM-as-judge. DeepEval's G-Eval, Promptfoo's LLM rubric, and Braintrust's custom scorers all solve the same problem with more infrastructure overhead. For a single-client deployment with 6 rubric criteria:

- **Build cost**: Extend rubric.py (already done pattern) + write YAML rubric + wire to generation pipeline
- **SaaS cost**: New dependency, API keys, dashboard nobody checks, data leaving the cluster

Use the existing pattern. If Halo scales to 10+ clients with different rubrics, re-evaluate external tooling then.

## Sources

- [Feisworld: Best AI Content Repurposing Tools 2026](https://www.feisworld.com/blog/best-ai-content-repurposing-tool)
- [Postiv AI: 8 Best AI Content Repurposing Tools 2026](https://postiv.ai/blog/content-repurposing-software)
- [OpusClip: Video Repurposing Tool](https://www.opus.pro/tools/video-repurposing-tool)
- [Promptfoo: LLM Rubric Documentation](https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/)
- [DeepEval: G-Eval LLM Evaluation](https://deepeval.com/docs/metrics-llm-evals)
- [Braintrust: LLM-as-a-Judge Guide](https://www.braintrust.dev/articles/what-is-llm-as-a-judge)
- [Confident AI: LLM Evaluation Metrics](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation)
- [arxiv:2410.18363 -- Contextual Biasing for Domain-Specific Whisper Transcription](https://arxiv.org/abs/2410.18363)
- [Harvard Business School: Health Risks of Generative AI Wellness Apps](https://www.hbs.edu/ris/Publication%20Files/the%20health%20risks%20of%20generative%20AI_f5a60667-706a-4514-baf2-b033cdacf857.pdf)
- [FDA Digital Health Advisory Committee: Guardrails for GenAI in Mental Health](https://www.lexology.com/library/detail.aspx?g=e58f075b-5bbc-41ab-95f7-87b379ceaa88)
- [RepurposeMyWebinar: Zoom Integration Guide](https://www.repurposemywebinar.com/resources/content-repurposing-glossary/zoom-integration)
- [CapCut: Long Video to Shorts 2026](https://www.capcut.com/resource/top-5-long-video-to-shorts-tools)
- Existing Halo codebase: `halos/halctl/eval_harness.py`, `halos/watchctl/rubric.py`, `docs/d1/eval-baseline-2026-03-18.md`

---
*Feature research for: AI content repurposing for Daoist wellness practitioner (Aura / Halo Client 001)*
*Researched: 2026-04-07*
