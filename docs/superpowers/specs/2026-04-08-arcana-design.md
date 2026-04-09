# Arcana: Multi-Agent Research Analyst Pipeline

> Portfolio demonstration project for AI Engineer (Build & Deployment Focus) roles.
> Domain-neutral, first-principles AI engineering deployed on local Kubernetes.

## Purpose

A multi-agent research analyst that ingests documents (PDF, images, web pages), extracts and indexes their content, then answers research questions with cited, fact-checked briefings.

Demonstrates: multi-agent pipelines, RAG, LangGraph orchestration, multi-provider LLM strategy, NATS JetStream distribution, K8s deployment, LangSmith observability, and production-quality Python engineering.

## Architecture: The Spine

LangGraph is the **orchestration spine** — a `StateGraph` that defines the pipeline DAG. Heavy lifting happens in **worker pods** deployed on K8s. Graph nodes dispatch work to workers via NATS JetStream request/reply, wait for results, and manage state transitions.

### Three Layers

**Layer 1: Gateway (FastAPI)**
- REST API for document upload, job submission, query interface
- SSE endpoint for real-time pipeline progress to the dashboard
- Serves lightweight web dashboard (Jinja2 + HTMX)
- Runs as a single K8s Deployment
- LangGraph orchestrator runs inside the gateway process (orchestration logic, not compute)

**Layer 2: Orchestrator (LangGraph)**
- Two StateGraph definitions:
  - **Ingestion graph:** upload -> extract -> chunk -> embed -> index
  - **Query graph:** question -> retrieve -> analyse -> fact-check -> synthesise -> report
- Graph nodes are thin dispatchers — publish work to NATS subjects and await responses
- Full LangSmith tracing on every graph execution

**JetStream reliability semantics (built-in, not deferred):**
- **Idempotency:** Every work request carries a deterministic idempotency key (`{job_id}:{step_name}:{attempt}`). Workers check the `_processed` table before executing. Duplicate deliveries are acked without side effects.
- **Retries:** Bounded exponential backoff (3 attempts, base 2s, max 16s). Managed by the orchestrator — on timeout or worker NACK, the graph node retries with an incremented attempt counter.
- **Dead letter queue:** After max attempts, failed messages route to `arcana.dlq.{step}` with full context (original payload, error, attempt history). DLQ subjects are durable and monitored via structured logging.
- **Ack policy:** Workers explicitly ack only after successful processing and persistence. No auto-ack. NATS redelivers on timeout (30s).
- **Graph recovery:** If the orchestrator pod restarts mid-pipeline, incomplete jobs are detected on startup (status != `completed` in PostgreSQL) and re-entered at the last successful step.

**Layer 3: Workers (K8s Pods)**
Four worker types, each a separate Deployment:

| Worker | NATS Subject | LLM Provider | Purpose |
|---|---|---|---|
| `extractor` | `arcana.extract` | GPT-4o (vision) | OCR/VLM — PDFs, images, screenshots into structured text |
| `embedder` | `arcana.embed` | OpenAI `text-embedding-3-small` | Chunks text, generates embeddings, writes to vector store |
| `analyst` | `arcana.analyse` | Claude (Sonnet/Opus) | Deep reasoning over retrieved context, produces draft briefing |
| `checker` | `arcana.check` | GPT-4o | Fact-checks claims against source chunks, flags unsupported statements |

### Provider Selection Rationale

- **extractor (GPT-4o vision):** Strongest at document layout understanding (tables, diagrams, scanned docs)
- **embedder (OpenAI text-embedding-3-small):** Cheap, fast, industry default for embeddings
- **analyst (Claude):** Better at nuanced synthesis and long-context reasoning
- **checker (GPT-4o structured output):** JSON schema enforcement for claim verification

Multi-provider is a deliberate engineering decision — demonstrates provider selection based on task characteristics, not allegiance.

## Data Flow

### Document Ingestion

```
User uploads PDF/image/URL
  -> Gateway validates + stores raw file (shared RWX PVC, immutable key + SHA256 checksum)
  -> Publishes job to NATS arcana.jobs.ingest
  -> Orchestrator runs ingestion graph:
      1. extractor worker: raw file -> structured text + metadata
      2. embedder worker: structured text -> chunks (~500 tokens) -> embeddings -> ChromaDB
  -> Job status updated in PostgreSQL
  -> SSE pushes progress to dashboard
```

### Query Flow

```
User submits research question
  -> Gateway creates query job
  -> Orchestrator runs query graph:
      1. Retriever (in gateway process, not a worker): question -> ChromaDB similarity search -> top-k chunks
      2. analyst worker: question + retrieved chunks -> draft briefing with inline citations
      3. checker worker: draft briefing + source chunks -> verified briefing
         (each claim tagged: supported/unsupported/partial)
      4. Synthesiser (in gateway process, not a worker): assembles final report with confidence score
  -> Report persisted to PostgreSQL
  -> SSE pushes final result to dashboard
```

### Storage

| Store | Technology | What it holds | K8s resource |
|---|---|---|---|
| Documents DB | PostgreSQL (prod) / SQLite (local dev) | Jobs, reports, document metadata, pipeline state | StatefulSet + PVC |
| Vector store | ChromaDB | Document chunk embeddings | Deployment + PVC |
| Raw files | Shared RWX PVC (e.g., NFS) | Uploaded PDFs, images | RWX PersistentVolumeClaim mounted by gateway + workers |
| Message bus | NATS JetStream | Work dispatch, inter-agent comms | Existing cluster NATS |

ChromaDB chosen for zero-config Python-native dev experience. Production swap to pgvector/Pinecone is trivial due to clean interface boundary.

### File Handoff Contract

Uploaded files are stored on a **shared RWX PersistentVolumeClaim** (NFS-backed, matching the existing Halo fleet pattern) mounted by both the gateway and all worker pods. The gateway writes files using an immutable key (`{job_id}/{sha256}.{ext}`) and records the checksum in PostgreSQL. Workers receive only the object reference via NATS — never the file content. On receipt, workers verify the checksum before processing. This ensures:
- Files survive gateway pod rescheduling or node loss
- Workers can retry independently of the gateway lifecycle
- No implicit cross-pod file access assumptions

## K8s Deployment Topology

**Namespace:** `arcana` — fully isolated. No cross-namespace dependencies except NATS (consumed as service endpoint from existing cluster).

**NATS:** Creates an `ARCANA` stream (subjects `arcana.>`) alongside the existing `HALO` stream. Separate streams, separate consumers, zero blast radius.

| Resource | Replicas | Image | Resource Limits | Notes |
|---|---|---|---|---|
| `arcana-gateway` | 1 | `arcana:latest` | 256Mi / 0.5 CPU | FastAPI + LangGraph + dashboard |
| `arcana-extractor` | 1-2 | `arcana-worker:latest` | 512Mi / 1 CPU | Heaviest — VLM calls, PDF parsing |
| `arcana-embedder` | 1 | `arcana-worker:latest` | 256Mi / 0.5 CPU | Lightweight API calls |
| `arcana-analyst` | 1 | `arcana-worker:latest` | 256Mi / 0.5 CPU | Claude API calls |
| `arcana-checker` | 1 | `arcana-worker:latest` | 256Mi / 0.5 CPU | GPT-4o structured output |
| `arcana-chromadb` | 1 | `chromadb/chroma` | 512Mi / 0.5 CPU | Vector store, PVC-backed |
| `arcana-db` | 1 | `postgres:16-alpine` | 256Mi / 0.5 CPU | Metadata + reports, PVC-backed |

**Design choices:**
- Single worker image, `WORKER_TYPE` env var selects entrypoint
- Secrets via K8s Secrets — each worker mounts only what it needs
- HPA-ready (resource requests/limits defined) but not configured — documented as production consideration
- Liveness: HTTP `/health` on gateway, TCP on workers (NATS connection alive)
- Readiness: worker reports ready after NATS subscription confirmed

## Dashboard & Observability

### Layer A: FastAPI Dashboard (demo reel)

Server-rendered Jinja2 + HTMX. No React, no JS build tooling. Python engineering role, Python frontend.

| View | What it shows |
|---|---|
| **Documents** | Upload form, ingested doc list with status/metadata |
| **Query** | Text input, streaming result via SSE, briefing with citations + confidence badges |
| **Pipeline** | Live graph execution — active workers, timing per step |

### Layer B: LangSmith Tracing (engineering credibility)

Every LangGraph execution traced end-to-end:
- Graph runs with timing per node, input/output at each step
- LLM calls with prompt, completion, token counts, latency, model used
- Retrieval queries with top-k results and relevance scores
- Fact-checker output as LangSmith feedback scores

### Tracing Data Policy

LangSmith captures prompts, completions, and retrieval results — which includes raw document content and user queries. Controls:

- **Environment gating:** Full prompt/completion tracing enabled only when `ARCANA_TRACE_LEVEL=full` (local dev default). Production default is `ARCANA_TRACE_LEVEL=metadata` — traces capture timing, token counts, model used, and step outcomes, but truncate prompt/completion content to first 200 chars.
- **Redaction:** Document content in retrieval traces is replaced with chunk IDs and relevance scores. Full chunk text is never sent to LangSmith in metadata mode.
- **Retention:** LangSmith project configured with 30-day retention. No long-term storage of traced content.
- **Demo mode:** For the portfolio walkthrough, `full` tracing is intentional — you want to show the interviewer actual prompts and completions. The policy exists to demonstrate you've thought about it, not to hide the demo data.

### Structured Logging

All workers emit JSON logs with correlation IDs (LangGraph run ID propagated via NATS headers). `kubectl logs -n arcana` shows coherent cross-pod traces.

## Project Structure

```
arcana/
├── pyproject.toml
├── Dockerfile
├── k8s/
├── src/
│   └── arcana/
│       ├── gateway/
│       │   ├── app.py              # FastAPI application
│       │   ├── routes.py           # Upload, query, SSE endpoints
│       │   └── templates/          # Jinja2 + HTMX
│       ├── orchestrator/
│       │   ├── ingest.py           # Ingestion StateGraph
│       │   ├── query.py            # Query StateGraph
│       │   └── state.py            # TypedDict state schemas
│       ├── workers/
│       │   ├── base.py             # BaseWorker (NATS subscribe, health, shutdown)
│       │   ├── extractor.py        # VLM/OCR extraction (GPT-4o vision)
│       │   ├── embedder.py         # Chunking + embedding (OpenAI)
│       │   ├── analyst.py          # Deep analysis (Claude)
│       │   └── checker.py          # Fact verification (GPT-4o structured output)
│       ├── store/
│       │   ├── documents.py        # PostgreSQL/SQLite: jobs, metadata, reports
│       │   └── vectors.py          # ChromaDB: chunk storage and retrieval
│       ├── models/
│       │   ├── events.py           # NATS message schemas (Pydantic)
│       │   └── reports.py          # Briefing output schemas (Pydantic)
│       └── config.py               # Settings via pydantic-settings
├── tests/
│   ├── test_orchestrator.py        # Graph execution (mocked workers)
│   ├── test_workers.py             # Worker units (mocked LLM calls)
│   ├── test_store.py               # Storage layer
│   └── test_integration.py         # E2E with real NATS (marked slow)
└── README.md
```

### Key Interfaces

```python
class BaseWorker:
    """All four workers inherit from this."""
    async def start(self, nats_url: str, subject: str) -> None: ...
    async def handle(self, msg: NATSMessage) -> WorkerResult: ...
    async def health(self) -> bool: ...

class ExtractRequest(BaseModel):
    """NATS message contract — Pydantic at every service boundary."""
    job_id: str
    document_url: str
    doc_type: Literal["pdf", "image", "url"]

class ExtractResult(BaseModel):
    job_id: str
    text: str
    metadata: DocumentMetadata
    pages: int
```

**Design principles:**
- Pydantic at all service boundaries. No loose dicts crossing NATS.
- `BaseWorker` is the only abstraction. No framework, no plugin system, no registry.
- Graph definitions readable in 60 seconds.
- Tests mock at the NATS boundary. Integration tests use real NATS, marked separately.

## Tech Stack

```toml
# Core
python = ">=3.11"
langgraph = "*"
langsmith = "*"
langchain-openai = "*"
langchain-anthropic = "*"

# Workers
nats-py = ">=2.9.0"
pydantic = ">=2.0"
pydantic-settings = "*"

# Gateway
fastapi = "*"
uvicorn = "*"
jinja2 = "*"
sse-starlette = "*"
python-multipart = "*"

# Storage
chromadb = "*"
asyncpg = "*"          # PostgreSQL (prod)
aiosqlite = "*"        # SQLite (local dev)

# Document processing
pymupdf = "*"          # PDF text extraction (fast, no Poppler dep)
httpx = "*"            # Async HTTP

# Dev
pytest = ">=9.0"
pytest-asyncio = "*"
ruff = "*"
```

**Notable decisions:**
- `langchain-openai` / `langchain-anthropic` over raw SDKs: native LangSmith tracing for free, seamless LangGraph integration. Right trade for a LangChain shop portfolio piece.
- `pymupdf` for fast local PDF parsing before VLM — don't throw expensive compute at solved problems.
- `ruff` from day one — "production-quality code" starts with a formatted repo.
- `asyncpg` / `aiosqlite` swap via config — dev/prod parity without over-engineering.
- No LangServe, LangFlow, or LangChain Agents. LangGraph is the orchestrator. Everything else is plain Python.

## Demo Walkthrough

Pre-loaded with 3-4 documents (e.g., AI regulation reports, climate tech papers). Vector store already indexed.

| Minute | What you show | What it demonstrates |
|---|---|---|
| 1 | `kubectl get pods -n arcana` — 7 pods, all healthy | K8s deployment, namespace isolation |
| 2 | Dashboard: submit research question, SSE streams progress | Real-time pipeline, user experience |
| 3 | Briefing with citations, confidence badges | RAG output quality, fact-checking |
| 4 | LangSmith trace: timing, tokens, costs per step | Production observability, multi-provider |
| 5 | `kubectl scale deployment arcana-extractor --replicas=3` | Independent scaling, NATS queue groups |
| 6 | Verbal: "Here's what I'd add next" | Architectural judgement, production thinking |

### Production Considerations (discussed, not built)

- HPA on extractor keyed to NATS pending message count
- Swap ChromaDB for pgvector to reduce operational surface
- Cost dashboard per query via LangSmith evaluation datasets
- Rate limiting on gateway for API key cost control

## JD Coverage Matrix

| Requirement | How Arcana covers it |
|---|---|
| Multi-agent pipelines (LLMs, VLMs, OCR) | 4 workers: GPT-4o vision, Claude, OpenAI embeddings |
| End-to-end AI systems (RAG, orchestration, memory) | LangGraph StateGraph + ChromaDB + typed state |
| Deploy, monitor, iterate in cloud | K8s namespace, LangSmith traces, structured logs |
| Scalability, reliability, maintainability | Independent worker scaling, JetStream persistence, health probes |
| LangChain, LangGraph familiarity | Central to the architecture |
| Strong Python engineering | Pydantic models, async workers, ruff-formatted, tested |
| Bias toward practical delivery | Working system, not slides |
| Collaborative team player | Clean README, documented decisions, conventional structure |

## Constraints

- **Standalone repository.** Not inside halo. Clean portfolio piece.
- **NATS reuse.** Connects to existing cluster NATS. Creates `ARCANA` stream, does not touch `HALO` stream.
- **K8s namespace isolation.** `arcana` namespace only. No modification to existing workloads.
- **Timeline.** ~1 month. Quality over speed.
- **Domain neutral.** Research analyst — universally legible, no domain glossary required.
