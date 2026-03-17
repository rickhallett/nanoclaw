# Competitive Landscape: LLM Agent Operational Telemetry

**Date:** 2026-03-16
**Analyst:** strategic-analyst
**Claim under test:** "Almost nobody is publishing operational telemetry from running LLM agent systems long-term."

---

## Verdict: The claim is MOSTLY TRUE, with important nuance.

There is a growing body of work on agent *evaluation frameworks*, *failure taxonomies*, and *tooling*. But the specific thing — raw operational telemetry from a real agent system running over weeks/months, published transparently — remains extremely rare. The space is full of "how to monitor" and nearly empty of "here is what we monitored."

---

## 1. Agent Failure Taxonomies

**Crowdedness: MODERATE (academic) / SPARSE (production)**

This is the area closest to being well-covered, but almost entirely from an academic angle using benchmark traces, not production systems.

### What exists:

- **MAST (Multi-Agent System Failure Taxonomy)** — 14 failure modes across 3 categories, validated on 1,600+ annotated traces from 7 MAS frameworks. High inter-annotator agreement (kappa = 0.88). Published at NeurIPS 2025.
  - Paper: [arxiv.org/abs/2503.13657](https://arxiv.org/abs/2503.13657)
  - This is the strongest work in the space. But the traces come from benchmark frameworks (AutoGen, CrewAI, etc.), not long-running production deployments.

- **TRAIL (Trace Reasoning and Agentic Issue Localization)** — 841 annotated errors across traces from the GAIA benchmark, averaging 5.68 errors per trace. Four expert annotators.
  - Paper: [arxiv.org/html/2505.08638v1](https://arxiv.org/html/2505.08638v1)

- **System-Level LLM Failure Taxonomy** — 15 hidden failure modes including multi-step reasoning drift, context-boundary degradation, tool invocation errors, and cost-driven performance collapse.
  - Paper: [arxiv.org/abs/2511.19933](https://arxiv.org/abs/2511.19933)

- **Microsoft Agentic AI Failure Modes** — Whitepaper from Microsoft on taxonomy of failure modes in agentic AI systems.
  - PDF: [Microsoft CDN](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf)

- **AGENTRX** — Full execution trace annotations with failure categories for why runs ultimately fail.
  - Paper: [arxiv.org/pdf/2602.02475](https://arxiv.org/pdf/2602.02475)

### Gap:
All of these classify failure *types*. None publish **frequency distributions from production systems over time** — e.g., "in month 3, tool invocation errors dropped from 12% to 4% after we changed X." The taxonomies exist; the longitudinal operational data does not.

---

## 2. Agent Operational Telemetry Dashboards

**Crowdedness: EMPTY (public dashboards) / CROWDED (tooling to build your own)**

This is the starkest gap. There is an entire ecosystem of observability *tooling* and zero public instances of anyone sharing what the dashboards actually show.

### Tooling that exists (but shows nothing publicly):

| Tool | Type | Notes |
|------|------|-------|
| [Langfuse](https://github.com/langfuse/langfuse) | Open source LLM observability | Traces, cost tracking, evals. 18k+ GitHub stars. |
| [OpenLLMetry](https://github.com/traceloop/openllmetry) | OpenTelemetry extensions for LLMs | Standard instrumentation. |
| [OpenLIT](https://github.com/openlit/openlit) | OpenTelemetry-native platform | One-line setup, GPU monitoring included. |
| [Langtrace](https://github.com/Scale3-Labs/langtrace) | Open source observability | Traces, evaluations, metrics. |
| [Helicone](https://www.helicone.ai) | Proxy-based monitoring | Lightweight, auto-logs requests. |
| [Datadog LLM Observability](https://www.datadoghq.com/blog/monitor-openai-cost-datadog-cloud-cost-management-llm-observability/) | Enterprise | Per-call cost breakdown in traces. |
| [Portkey](https://portkey.ai) | AI gateway + control plane | Routing, caching, monitoring. |

Anthropic's Claude Code itself exports telemetry via OpenTelemetry (metrics as time series, events via logs/events protocol) — but this is instrumentation, not published data.

### What does NOT exist (as far as I can find):
- No public Grafana dashboard showing real agent system metrics over time
- No "here are our token costs per week for the last 6 months" blog post with actual numbers
- No open dataset of operational telemetry from a running agent system

### The one near-miss:
**Agent-O-Rama** (redplanetlabs) — tracks agent-level metrics including success rates, end-to-end latency, token counts, time-to-first-token. But it's a benchmarking arena, not a production system sharing its telemetry.

---

## 3. Memory/RAG Scaling Studies

**Crowdedness: MODERATE (theoretical/architectural) / SPARSE (empirical with real scaling curves)**

### What exists:

- **"Your RAG system works on 10,000 documents. Here's why it dies at 30 million"** — A Medium post by Daniel Manzke arguing that enterprise RAG at scale is a partitioning problem, not a retrieval problem. Practical architectural advice but no published latency curves or precision/recall data at each scale point.
  - [Medium article](https://medium.com/@danielmanzke/your-rag-system-works-on-10-000-documents-heres-why-it-dies-at-30-million-529171cd30c0)

- **RAGO (ISCA 2025)** — Systematic performance optimization for RAG serving from MIT CSAIL. Addresses scheduling and resource allocation at scale. This is the most rigorous systems-level work.
  - [Paper](https://people.csail.mit.edu/suvinay/pubs/2025.rago.isca.pdf)

- **Sparse RAG (ICLR 2025)** — Balances generation quality and compute efficiency through selective document processing. Shows degradation curves as context scales from 100K to 10M tokens.
  - [Paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/5df5b1f121c915d8bdd00db6aac20827-Paper-Conference.pdf)

- **Small LM + RAG empirical study** — Shows adding retrieval context can *destroy* 42-100% of answers the model previously got right below 7B parameters (distraction effect).
  - [arxiv.org/abs/2603.11513](https://arxiv.org/abs/2603.11513)

### Gap:
Nobody has published the simple study everyone wants: "We built a RAG system. At 100 docs, retrieval precision was X and latency was Y. At 1,000 docs... at 10,000 docs... at 100,000 docs..." with actual numbers from a real system. The academic work uses synthetic benchmarks. The practitioners write architectural advice without data.

---

## 4. Intervention Rate / Human-in-the-Loop Metrics

**Crowdedness: VERY SPARSE**

This might be the single emptiest area. Almost nobody is publishing how often humans have to correct agent output, and there is no standard metric.

### What exists:

- **MAP Study ("Measuring Agents in Production")** — The most relevant work. 20 case studies via interviews + survey of 306 practitioners across 26 domains. Key finding: **68% of production agents execute at most 10 steps before human intervention, 74% depend primarily on human evaluation.** This is the closest thing to real production data on intervention rates.
  - [arxiv.org/abs/2512.04123](https://arxiv.org/abs/2512.04123)

- **Intercom's Fin AI Agent** — Resolves "up to 65%" end-to-end, implying ~35% intervention rate. But this is a marketing number, not a published study.

- **Cox Automotive circuit breakers** — Stops agents at P95 cost thresholds or ~20 turns, auto-handing off to humans. Real production pattern, but no published intervention frequency data.

- **Speed at Cost of Quality study** — Longitudinal finding that velocity gains from LLM agent assistants concentrate in the first 1-2 months before returning to baseline. This is intervention-adjacent but doesn't track intervention rate directly.
  - [Paper PDF](https://courtney-e-miller.github.io/papers/SpeedAtTheCostofQuality_TheImpactofLLMAgentAssistantonSoftwareDevelopment.pdf)

- **ZenML 1,200 deployment analysis** — Catalogued 1,200+ production LLM deployments. Six key patterns identified. But the analysis focuses on architectural patterns, not intervention metrics.
  - [ZenML blog](https://www.zenml.io/blog/what-1200-production-deployments-reveal-about-llmops-in-2025)

### Gap:
No standard metric exists. Nobody publishes "our intervention rate was X% in week 1 and Y% in week 12." The MAP study is the closest, and it's survey-based, not telemetry-based. This is wide open territory.

---

## 5. LLM Agent Cost Analysis (Real Usage Data)

**Crowdedness: MODERATE (pricing guides) / VERY SPARSE (actual production cost data)**

### What exists (mostly useless):

Dozens of "LLM Pricing Comparison 2025" articles comparing per-token rates across providers. These are theoretical, not operational.

### What exists (somewhat useful):

- **AI coding agent cost comparison** — One developer measured ~$2 for three tasks on Cursor vs ~$8 on Claude Code. Claude Code used 5.5x fewer tokens (33K vs 188K for identical tasks). Self-described as "super imperfect."
  - [Apidog analysis](https://apidog.com/blog/claude-code-cursor-cost-analysis/)
  - [Morph LLM comparison](https://www.morphllm.com/ai-coding-agent)

- **BudgetMLAgent** — Academic paper on cost-effective multi-agent systems for ML tasks. Published at AIMLSystems conference.
  - [ACM paper](https://dl.acm.org/doi/10.1145/3703412.3703416)

- **General production cost ranges** — Industry estimates of $3,200-$13,000/month for production agent systems (tokens + vector DB + monitoring + security). Not per-task.
  - [Agentive AIQ](https://agentiveaiq.com/blog/how-much-does-ai-cost-per-month-real-pricing-revealed)

### Gap:
Nobody has published "here is what our agent system costs per task type, measured over N months." No cost-per-coding-task, cost-per-research-task, cost-per-customer-support-resolution from real production data with enough detail to be useful. The one coding agent comparison is a single developer's rough estimate.

---

## 6. LLM-as-Judge Evaluation Pipelines

**Crowdedness: WELL-COVERED (this space is active and maturing)**

This is the one area where the claim does not hold. LLM-as-judge is extensively documented.

### What exists:

- **Comprehensive survey paper** with 6 versions — [arxiv.org/html/2411.15594v6](https://arxiv.org/html/2411.15594v6)
- **Agent-as-a-Judge** (multi-agent eval frameworks) — [arxiv.org/html/2508.02994v1](https://arxiv.org/html/2508.02994v1)
- **EvalPlanner** — Decouples planning from execution, 93.9 on RewardBench
- **Anthropic's Bloom** — Open source agentic framework for automated behavioral evaluations, tested across 16 frontier models with 100 rollouts each
  - [Anthropic research](https://www.anthropic.com/research/bloom)
- **Evidently AI guide** — Practical implementation guide: [evidentlyai.com/llm-guide/llm-as-a-judge](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)
- **Arize primer** with pre-built evaluators: [arize.com/llm-as-a-judge](https://arize.com/llm-as-a-judge/)
- **Training pipeline paper** with practical lessons: [arxiv.org/html/2502.02988v1](https://arxiv.org/html/2502.02988v1)

### Known limitations (well-documented):
- 80% agreement with human preferences (matching human-to-human consistency)
- Vulnerable to adversarial attacks
- Poor cross-language consistency (Fleiss' Kappa ~0.3 across 25 languages)
- Expert domain agreement only 60-68% (dietetics, mental health)
- 500x-5000x cost savings over human review

### Assessment:
This is genuinely well-covered territory. The methodology is documented, the limitations are known, the tooling exists. Publishing more here would need a specific angle (e.g., LLM-as-judge applied to agent telemetry specifically, or longitudinal calibration drift data).

---

## 7. "Building X the Hard Way" Style Publications

**Crowdedness: MODERATE (blog posts) / EMPTY (systematic, long-form, telemetry-backed)**

### What exists:

- **"What We Learned from a Year of Building with LLMs" (O'Reilly, 2024)** — The canonical "lessons learned" post. Widely cited. Covers tactical, operational, and strategic lessons. But it's advice, not telemetry.
  - [O'Reilly Radar](https://www.oreilly.com/radar/what-we-learned-from-a-year-of-building-with-llms-part-i/)

- **AWS DevOps Agent: From Prototype to Product (Jan 2026)** — Five mechanisms for continuous agent quality improvement. Real production lessons.
  - [AWS Blog](https://aws.amazon.com/blogs/devops/from-ai-agent-prototype-to-product-lessons-from-building-aws-devops-agent/)

- **AWS/Amazon: Evaluating AI Agents (2025)** — Real-world lessons from building agentic systems at Amazon.
  - [AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/evaluating-ai-agents-real-world-lessons-from-building-agentic-systems-at-amazon/)

- **Microsoft Azure SRE Agent (Jan 2026)** — "We were building a context engineering system that happens to do SRE." Key insight: trusting the model to reason vs. building brittle workflows.
  - [Microsoft Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/context-engineering-lessons-from-building-azure-sre-agent/4481200/)

- **Google Cloud: Lessons from 2025 on Agents and Trust (Dec 2025)** — Three takeaways: agents got jobs, evaluation became architecture, trust is the bottleneck. Introduces concept of "agent undo stacks."
  - [Google Cloud Blog](https://cloud.google.com/transform/ai-grew-up-and-got-a-job-lessons-from-2025-on-agents-and-trust)

- **Thoughtworks AIOps: What We Learned in 2025 (Jan 2026)** — 20 PoCs across 16+ clients, 11 reaching production. AI agents must be treated as production workloads.
  - [Thoughtworks](https://www.thoughtworks.com/en-ca/insights/blog/generative-ai/aiops-what-we-learned-in-2025)

- **Composio: Why AI Pilots Fail in Production** — Three traps: Dumb RAG, Brittle Connectors, the Polling Tax.
  - [Composio blog](https://composio.dev/blog/why-ai-agent-pilots-fail-2026-integration-roadmap)

- **LangChain: State of Agent Engineering** — Industry survey on agent patterns.
  - [LangChain](https://www.langchain.com/state-of-agent-engineering)

- **Anthropic: Demystifying Evals for AI Agents** — Field-tested evaluation methods from customer work.
  - [Anthropic engineering](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

### Gap:
All of these are either (a) architectural advice without telemetry, (b) single-point-in-time lessons learned, or (c) marketing-adjacent thought leadership. None of them are "here is a system, here is what it did over 6 months, here are the numbers." The BATHW format — systematic, from-scratch, showing the operational reality with data — does not exist for agent systems.

---

## Summary Matrix

| Area | Academic Coverage | Production Data Published | Tooling Available | Open for Original Work? |
|------|:-:|:-:|:-:|:-:|
| Failure taxonomies | Strong | None | Moderate | Yes (production frequency data) |
| Operational telemetry | Weak | None | Crowded | Wide open |
| RAG scaling curves | Moderate | None | N/A | Wide open |
| Intervention rates | Very weak | Almost none | None | Wide open |
| Cost per task | None | Almost none | Moderate | Wide open |
| LLM-as-judge | Strong | Moderate | Strong | Narrow angles only |
| BATHW-style publications | N/A | None | N/A | Wide open |

---

## Positioning Recommendation

The claim is substantively correct. The landscape has:
1. **Plenty of taxonomies and frameworks** (how to think about agent failure)
2. **Plenty of tooling** (how to instrument agent systems)
3. **Almost no published operational data** (what actually happens when you run one)

The gap is not in knowledge of *what to measure* — it's in anyone *showing their measurements*. This is likely because:
- Companies treat operational data as competitive intelligence
- Solo builders don't have the instrumentation habit
- Academic benchmarks are easier to publish than production telemetry

A publication strategy that publishes real numbers from a real system — even a small personal one — would be genuinely novel. The closest competition is the MAP study (survey of 306 practitioners) and the O'Reilly "Year of Building with LLMs" post (qualitative lessons). Neither shows telemetry from an actual running system.

The strongest positioning would combine areas 1, 2, 4, and 5: a failure taxonomy with frequency data, backed by operational telemetry, showing intervention rates and costs over time, from a system you actually run. That specific combination does not exist anywhere I can find.
