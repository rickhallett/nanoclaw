<p align="center">
  <h1 align="center">Halo</h1>
  <p align="center">
    Autonomous event-sourced AI fleet
    <br />
    <em>27 modules. 735 tests. Choreographed advisory council on Kubernetes.</em>
  </p>
</p>

<p align="center">
  <a href="https://github.com/rickhallett/halo/actions"><img src="https://github.com/rickhallett/halo/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/rickhallett/halo/blob/main/LICENSE"><img src="https://img.shields.io/github/license/rickhallett/halo" alt="License" /></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/k3s-local%20cluster-326CE5?logo=kubernetes&logoColor=white" alt="k3s" />
  <img src="https://img.shields.io/badge/NATS-JetStream-27aae1?logo=nats.io&logoColor=white" alt="NATS" />
  <img src="https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/k3s-homelab-326CE5?logo=k3s&logoColor=white" alt="Homelab" />
</p>

---

## What is Halo?

Halo is a personal AI agent system. 27 Python modules cover structured memory, work tracking, email triage, YouTube monitoring, daily briefing synthesis, spaced repetition, finance, journaling, and fleet management. Each module has its own CLI, its own SQLite store, and its own test suite.

The modules run locally on macOS for daily use. When deployed to Kubernetes (k3s), they gain distribution and a choreographed advisory council — multiple advisor instances communicating through a NATS JetStream event stream.

`hal` is the unified CLI entry point. `hal night add`, `hal track add zazen`, `hal mail inbox`, `hal secrets vaults`. One command, every module.

## Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │                       LOCAL (macOS)                         │
  │                                                             │
  │   ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
  │   │ nightctl │  │ trackctl │  │ briefings│   ...27 modules  │
  │   └────┬─────┘  └────┬─────┘  └────┬─────┘                 │
  │        └──────────────┼──────────────┘                      │
  │                       │                                     │
  │              ┌────────┴────────┐                            │
  │              │    hal CLI      │                            │
  │              └────────┬────────┘                            │
  │                       │                                     │
  │              ┌────────┴────────┐                            │
  │              │  pytest (735)   │                            │
  │              └────────┬────────┘                            │
  │                       │                                     │
  │              ┌────────┴────────┐                            │
  │              │  SQLite stores  │                            │
  │              └─────────────────┘                            │
  └─────────────────────────────────────────────────────────────┘
                          │
                     git push
                          │
  ┌─────────────────────────────────────────────────────────────┐
  │                    K3S CLUSTER                              │
  │                                                             │
  │   ┌──────────────────────────────────────────────────────┐  │
  │   │              NATS JetStream                          │  │
  │   │         (event stream / nervous system)              │  │
  │   └──────┬────────┬────────┬────────┬────────────────────┘  │
  │          │        │        │        │                       │
  │   ┌──────┴──┐ ┌───┴───┐ ┌──┴────┐ ┌─┴────────┐            │
  │   │Musashi  │ │Draper │ │Gibson │ │Karpathy  │   ...x8+    │
  │   │(Hermes) │ │(Hermes│ │(Hermes│ │(Hermes)  │            │
  │   └─────────┘ └───────┘ └───────┘ └──────────┘            │
  │                                                             │
  │   ┌─────────────────────────────────────────────────────┐  │
  │   │           Grafana / Prometheus                      │  │
  │   └─────────────────────────────────────────────────────┘  │
  │                                                             │
  │   ┌───────────────────────────────────┐                     │
  │   │  Manual deploy (SSH + kubectl)  │                     │
  │   └───────────────────────────────────┘                     │
  └─────────────────────────────────────────────────────────────┘
```

Every module works locally without a network connection, without Docker, without Kubernetes. The cluster adds distribution and the advisory council. The code does not change. The topology changes.

## The Halostream (Event Sourcing)

All advisors communicate through a NATS JetStream event stream. The stream is the single source of truth. Every pod's SQLite database is a disposable projection rebuilt from the event log on restart.

```
  WRITE: Telegram → Advisor pod → process → publish event to stream
  READ:  Consumer pod → subscribe → update local projection → query locally
```

There is no central coordinator. The evening council emerges from sequential reactions: each advisor watches for the previous advisor's submission event, contributes its perspective, and publishes its own. Plutarch (the dramaturg) synthesises the council's output.

Kill any pod. It restarts, replays from its last checkpoint on the stream, rebuilds its projection, and resumes. No data loss. No manual intervention.

## The Roundtable

| Seat | Name | Domain |
|------|------|--------|
| I | Musashi | Physical state and discipline |
| II | Draper | Copywriting, positioning, and pitch |
| III | Karpathy | Engineering craft and logic |
| IV | Gibson | Market terrain and futures |
| V | Machiavelli | Power dynamics and strategy |
| VI | Medici | Financial runway and economics |
| VII | Bankei | Rest, rhythm, and burnout detection |
| VIII | Hightower | Heavy Iron / K8s Operations |
| — | Plutarch | Dramaturg / council synthesis |

Additional advisors (Seneca, Socrates, Sun Tzu, Guido) are available in `data/advisors/`.

## Modules

The `halos/` package is the centre of gravity. Python CLIs for structured work across domains.

| Module | Command | Purpose |
|--------|---------|---------|
| memctl | `memctl` | Structured memory governance |
| nightctl | `nightctl` | Work tracker with Eisenhower matrix |
| cronctl | `cronctl` | Cron job definitions and crontab generation |
| logctl | `logctl` | Structured log reading and search |
| reportctl | `reportctl` | Periodic digests |
| agentctl | `agentctl` | LLM session tracking and spin detection |
| briefings | `hal-briefing` | Morning / nightly digests via Telegram |
| trackctl | `trackctl` | Personal metrics (zazen, movement, study) |
| dashctl | `dashctl` | TUI dashboard |
| halctl | `halctl` | Fleet management and health checks |
| mailctl | `mailctl` | Gmail operations via himalaya |
| watchctl | `watchctl` | YouTube channel monitor with LLM-as-judge triage |
| journalctl | `journalctl` | Qualitative journal with sliding-window synthesis |
| secretctl | `secretctl` | 1Password secret access |
| ledgerctl | `ledgerctl` | Finance ledger |
| drillctl | `drillctl` | Spaced repetition drill cards |
| eventsource | — | NATS JetStream event sourcing core |
| telemetry | — | Observability |

## Repository Structure

```
halo/
├── halos/              27 Python CLI modules
├── infra/              K8s manifests, NATS, deploy pipeline
├── agent/              macOS agent server (listen/direct/drive/steer)
├── docker/             Fleet container entrypoint
├── data/               Advisor personas, client prompts
├── docs/               Specs, analyses, runbooks
├── memory/             Structured notes and reflections
├── tests/              pytest suite (735 tests)
├── store/              SQLite databases
├── cron/               Cron job definitions
├── jobctl/             Job search automation (CV, applications, tracking)
└── templates/          MicroHAL personality blocks
```

## Storage Model

- SQLite for queryable domain state
- YAML for human-readable config and work items
- Markdown for prose, specs, and context
- JSONL for append-only operational events

## Getting Started

```bash
git clone https://github.com/rickhallett/halo.git
cd halo
uv sync
uv tool install -e .

# Use any module
hal night items
hal track summary
hal mail inbox
```

## License

[MIT](LICENSE)
