# Halo: Autonomous Event-Sourced AI Fleet

> **"Translating the Dao into YAML files."**

Halo is a bespoke, heavy-iron AI ecosystem designed to automate high-ticket spiritual, wellness, and creator businesses without degrading their authentic human voice.

Built by a psychotherapist turned Kubernetes engineer, Halo rejects the "stateless chatbot" paradigm. Instead, it operates as a **persistent, event-driven hive-mind** deployed on bare-metal cloud infrastructure. It holds context, observes behavior, and executes complex operational pipelines completely invisibly to the end-user.

---

## The Architecture (The Heavy Iron)

Halo is deployed as a fat-code/thin-client architecture on the Vultr Kubernetes Engine (VKE), orchestrated entirely via ArgoCD (GitOps).

- **The Halostream (NATS JetStream):** The nervous system of the fleet. A highly resilient event bus. All agents communicate via pub/sub events. If a pod dies, it simply restarts, replays the JetStream from its last checkpoint, and reconstructs its local reality. Zero message loss.
- **Single-Writer Memory (NFS):** To prevent concurrency locks, state is managed via a single-writer `memctl-authority` pod writing to an NFS Persistent Volume. All advisor pods mount this volume read-only, ensuring total data integrity across the fleet.
- **CQRS Pattern:** Each advisor runs a sidecar event consumer that projects the NATS event stream into a local SQLite database, decoupling read/write workloads and making each pod functionally immortal.
- **Agentic Orchestration:** Written in Python (`uv` managed), wrapping Anthropic and Groq models with strict psychological boundaries to prevent "AI slop" and hallucination.

---

## The Roundtable

The cluster runs 8 distinct, containerised "Advisors." Each is a discrete Kubernetes Deployment with a highly specific system prompt and operational domain:

| Seat | Name | Domain |
|------|------|--------|
| I | Musashi | Physical state and discipline |
| II | Draper | Copywriting, positioning, and pitch |
| III | Karpathy | Engineering craft and logic |
| IV | Gibson | Market terrain and futures |
| V | Machiavelli | Power dynamics and strategy |
| VI | Medici | Financial runway and economics |
| VII | Bankei | Rest, rhythm, and burnout detection |
| VIII | Hightower | Heavy Iron / K8s Operations (Diagnostic) |

For client deployments, this roster is hot-swapped for bespoke archetypes in isolated namespaces.

---

## Chaos Engineering and the Immune System

This system bends bullets. The integration suite executes rigorous Chaos Engineering against the live cluster.

The **66/66 passing integration suite** proves the cluster survives:

- **NATS Pod Murder:** Killing the event broker mid-stream. Consumers reconnect, zero message loss.
- **Advisor Amnesia:** Wiping a pod's local SQLite database. Pod perfectly reconstructs state from JetStream replay.
- **NFS Server Assassination:** Killing the persistent volume host. Full recovery chain verified without stale file handle exceptions.
- **Poison Pill Payloads:** Firing malformed JSON at consumers. Dead-lettered cleanly without crashing the pod.

---

## Why This Exists

There are many AI demos and many AI wrappers. There are far fewer systems that visibly answer the operational questions:

- How is agent intent specified?
- How is output evaluated?
- What happens when agents fail?
- What is the trust boundary?
- What context is loaded and why?
- What does this cost and is it worth it?

Halo exists to answer those questions in a concrete production setting. The winning AI systems are not the ones that merely generate plausible language. They are the ones that can be clearly specified, evaluated consistently, decomposed into controllable parts, debugged when they fail, governed at the trust boundary, and justified economically.

---

## Core Thesis

- Legibility over magic
- Auditability over novelty
- Evaluation over vibes
- Constrained autonomy over theatrical autonomy
- Composable tools over monoliths
- Explicit context over accidental context
- Narrow tools over sprawling abstractions
- Real traces over retrospective storytelling

---

## Repository Structure

```text
halo/
├── halos/              Shared Python CLI tooling
├── infra/              K8s fleet manifests, Terraform, NATS, Argo CD
│   └── k8s/fleet/      ArgoCD GitOps source of truth
├── agent/              macOS job server (listen/direct)
├── docker/             Fleet container entrypoint and defaults
├── vendor/             Hermes agent (git submodule)
├── data/               Advisor personas, client prompts
├── docs/               Specs, analyses, runbooks, reviews, archives
├── memory/             Structured notes and reflections (memctl-governed)
├── tests/              pytest suite
├── cron/               Cron job definitions
├── store/              SQLite databases
├── logs/               Operational logs
├── queue/              Queued work items
└── templates/          microHAL personality blocks
```

---

## halos Modules

The `halos/` package is the centre of gravity. Python CLIs for structured work across domains, installed via `uv sync`.

| Module | Command | Purpose |
|---|---|---|
| memctl | `memctl` | Structured memory governance |
| nightctl | `nightctl` | Work tracker with Eisenhower matrix and state machine |
| cronctl | `cronctl` | Cron job definitions and crontab generation |
| logctl | `logctl` | Structured log reading and search |
| reportctl | `reportctl` | Periodic digests from the ecosystem |
| agentctl | `agentctl` | LLM session tracking and spin detection |
| briefings | `hal-briefing` | Morning / nightly digests via Telegram |
| trackctl | `trackctl` | Personal metrics tracker (zazen, movement, study) |
| dashctl | `dashctl` | TUI dashboard / RPG character sheet |
| halctl | `halctl` | Session lifecycle and health checks |
| mailctl | `mailctl` | Gmail operations via himalaya |
| watchctl | `watchctl` | YouTube channel monitor with LLM-as-judge triage |
| journalctl | `journalctl` | Qualitative journal with sliding-window synthesis |

The point is less the count than the pattern: narrow tools with explicit surfaces, designed to compose.

---

## Example Compositions

### Morning Briefing

```text
cronctl
  -> hal-briefing morning
    -> memctl stats
    -> nightctl items
    -> trackctl summary
    -> mailctl summary
    -> log/status data
    -> synthesis
    -> Telegram delivery
```

### Message-Driven Assistant Workflow

```text
Telegram message
  -> Hermes receives context + tools
  -> runs halos commands
  -> returns result via messaging channel
```

---

## Storage Model

Halo uses a mixed storage model on purpose.

```text
store/         SQLite databases (queryable state)
memory/        Markdown notes and reflections
cron/jobs/     YAML cron definitions
queue/         YAML work items / queues
logs/          JSONL / structured event logs
docs/          Specs, analyses, runbooks, reviews
```

Storage principle:
- SQLite for queryable domain state
- YAML for human-readable config and work items
- Markdown for prose, specs, and context
- JSONL / structured logs for append-only operational events

---

## Documentation

Deeper documentation lives in `docs/`.

| Directory | Purpose |
|-----------|---------|
| `docs/d1/` | Working reference -- runbooks, guides, journals |
| `docs/d2/` | Specs, analyses, design records, reviews |
| `docs/d3/` | Archive |

Design intent starts in `docs/d2/`. Operating procedures start in `docs/d1/`.

---

---

*Built by The Ripperdoc. Magic on the front end. Heavy iron on the back.*

## License

MIT
