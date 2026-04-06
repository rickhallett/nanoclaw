---
title: "Halo Containerisation — Technical Walkthrough & Diagrams"
category: analysis
status: active
created: 2026-04-04
---

# Halo Containerisation — Technical Walkthrough & Diagrams

Companion to [halo-containerisation-spec.md](halo-containerisation-spec.md). This document provides layered visual explanations of how Halo ships from a single-user macOS process to isolated, per-client Kubernetes deployments. Use it to generate materials at any level of detail — from investor pitch to DevOps runbook.

---

## Table of Contents

1. [System Overview (30,000ft)](#1-system-overview)
2. [What a Client Gets](#2-what-a-client-gets)
3. [Image Architecture](#3-image-architecture)
4. [Configuration Injection — The Thin Config Model](#4-configuration-injection)
5. [Kubernetes Deployment Topology](#5-kubernetes-deployment-topology)
6. [Data Flow: Message Lifecycle](#6-data-flow-message-lifecycle)
7. [Storage & Backup Architecture](#7-storage--backup-architecture)
8. [Security Model](#8-security-model)
9. [CI/CD & Upgrade Pipeline](#9-cicd--upgrade-pipeline)
10. [Multi-Tenancy & Isolation](#10-multi-tenancy--isolation)
11. [Observability Stack](#11-observability-stack)
12. [Cost Structure](#12-cost-structure)
13. [Phased Rollout](#13-phased-rollout)
14. [Glossary](#14-glossary)

---

## 1. System Overview

### What Halo Is

Halo is a personal AI assistant platform. Each client gets their own instance — a private Telegram bot backed by Claude (Anthropic), with a suite of life-management tools: memory, task tracking, journaling, metrics, email triage, daily briefings, and a cast of AI advisor personas.

### The Transition

```
    BEFORE (single user)                    AFTER (multi-tenant)
    ════════════════════                    ════════════════════

    ┌──────────────────┐                    ┌─────────────────────────┐
    │   Kai's MacBook  │                    │   Vultr VKE Cluster     │
    │                  │                    │                         │
    │  hermes-agent ─┐ │                    │  ┌───────────────────┐  │
    │  halos modules  │ │                    │  │ ns: halo-kai      │  │
    │  ~/.hermes/     │ │                    │  │  [Kai's Halo]     │  │
    │  store/, memory/│ │                    │  └───────────────────┘  │
    │                  │                    │                         │
    └────────┬─────────┘                    │  ┌───────────────────┐  │
             │                              │  │ ns: halo-aura     │  │
             ▼                              │  │  [Aura's Halo]    │  │
        Telegram API                        │  └───────────────────┘  │
                                            │                         │
                                            │  ┌───────────────────┐  │
                                            │  │ ns: halo-client-n │  │
                                            │  │  [Client N's Halo]│  │
                                            │  └───────────────────┘  │
                                            │                         │
                                            │  ┌───────────────────┐  │
                                            │  │ ns: monitoring    │  │
                                            │  │  Prometheus/Loki  │  │
                                            │  └───────────────────┘  │
                                            └─────────────────────────┘
```

Key insight: every client gets the **same container image** with **different configuration**. No code forks, no per-client branches. One product, many instances.

---

## 2. What a Client Gets

### The Client Experience

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT'S TELEGRAM                           │
│                                                                 │
│  💬 "Good morning"                                              │
│                                                                 │
│  🤖 Good morning. Here's your briefing:                         │
│     • 3 tasks in your Q1 (urgent+important)                    │
│     • Zazen: 4-day streak, 22 min yesterday                    │
│     • Journal: last entry was 2 days ago                        │
│     • 📧 2 VIP emails need attention                            │
│     • Musashi says: "The body is the sword's home."             │
│                                                                 │
│  💬 "Log 30 minutes zazen"                                      │
│  🤖 Logged. 5-day streak now. Musashi approves.                 │
│                                                                 │
│  💬 "What did I decide about the Bristol contract?"             │
│  🤖 [searches structured memory] On March 3rd you decided...    │
│                                                                 │
│  🔒 Only the client's Telegram ID can talk to their bot.       │
│  🔒 No other client can see their data.                         │
│  🔒 Each bot runs in its own Kubernetes namespace.              │
└─────────────────────────────────────────────────────────────────┘
```

### Capability Stack (what's inside)

```
┌──────────────────────────────────────────────────────────────┐
│                    HALO INSTANCE                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  GATEWAY LAYER (Hermes)                                │  │
│  │  Telegram polling ← → Claude API ← → Tool dispatch    │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼───────────────────────────────────┐  │
│  │  HALOS MODULE LAYER                                    │  │
│  │                                                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ memctl   │ │ nightctl │ │ trackctl │ │briefings │  │  │
│  │  │ memory   │ │ tasks    │ │ metrics  │ │ digests  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │                                                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │journalctl│ │ mailctl  │ │ watchctl │ │ dashctl  │  │  │
│  │  │ journal  │ │ email    │ │ youtube  │ │ TUI dash │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │                                                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐               │  │
│  │  │ cronctl  │ │ agentctl │ │ halctl   │               │  │
│  │  │ schedule │ │ sessions │ │lifecycle │               │  │
│  │  └──────────┘ └──────────┘ └──────────┘               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  PERSONALITY LAYER                                     │  │
│  │  SOUL.md (persistent persona) + system-prompt.md       │  │
│  │  + Roundtable Advisors (Musashi, Seneca, Socrates...) │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  DATA LAYER                                            │  │
│  │  SQLite databases │ Markdown notes │ Session logs      │  │
│  │  (all on PVC — durable, backed up, exportable)        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Image Architecture

### Fat Image, Thin Config

The entire stack ships as a single Docker image. Nothing is installed at runtime. Client-specific behaviour comes entirely from mounted configuration files.

```
┌──────────────────────────────────────────────────────────────────┐
│  ghcr.io/rickhallett/halo:v1.2.0                     ~2 GB     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  LAYER 5: Entrypoint + defaults                    ~1 KB  │  │
│  │  /opt/entrypoint.sh, /opt/hermes/docker/defaults/          │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  LAYER 4: Playwright + Chromium (optional)       ~800 MB  │  │
│  │  Only built when INSTALL_BROWSER=true                      │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  LAYER 3: halos package (all modules)             ~15 MB  │  │
│  │  pip install . from /opt/halos/                            │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  LAYER 2: hermes-agent[all,messaging,cron]       ~400 MB  │  │
│  │  pip install from /opt/hermes/ + npm install               │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  LAYER 1: Debian 13 + Python 3.11 + Node.js     ~700 MB  │  │
│  │  Base image pinned by SHA256 digest                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Runs as: hermes (UID 1000, GID 1000) — non-root               │
│  Writable: /opt/data (HERMES_HOME) only                         │
│  Entrypoint: /opt/entrypoint.sh → exec hermes --gateway         │
└──────────────────────────────────────────────────────────────────┘
```

### Why "fat image, thin config"?

| Alternative | Problem |
|---|---|
| Per-client image builds | Drift, N build pipelines, slow rollouts |
| Runtime `pip install` | Non-reproducible, network dependency at boot |
| Sidecar per module | Over-engineering for a single-process app |

One image. Many configs. Ship it.

---

## 4. Configuration Injection

### The Assembly: How a Running Instance Is Composed

At deploy time, Kubernetes assembles a running Halo instance from four sources:

```
 CONTAINER IMAGE                CONFIG (per-client)           SECRETS (per-client)
 (immutable, shared)            (ConfigMaps)                  (K8s Secrets)
 ══════════════════             ══════════════                ═════════════════
                                                              
 ┌──────────────────┐  ┌─────────────────────────┐  ┌──────────────────────┐
 │ Gateway code     │  │ config.yaml             │  │ .env                 │
 │ Halos modules    │  │  - model choice         │  │  - BOT_TOKEN         │
 │ Python/Node      │  │  - session policy       │  │  - ANTHROPIC_API_KEY │
 │ Entrypoint       │  │  - enabled modules      │  │  - ALLOWED_USERS     │
 │                  │  │  - briefing schedule    │  │  - COST_CEILING_USD  │
 │                  │  │                         │  │                      │
 │                  │  │ system-prompt.md        │  └──────────┬───────────┘
 │                  │  │  - ephemeral personality│             │
 │                  │  │                         │             │
 │                  │  │ SOUL.md                 │             │
 │                  │  │  - persistent persona   │             │
 │                  │  │                         │             │
 │                  │  │ memctl.yaml (optional)  │             │
 │                  │  │ watchctl.yaml (optional)│             │
 └────────┬─────────┘  └────────────┬────────────┘             │
          │                         │                          │
          ▼                         ▼                          ▼
 ┌────────────────────────────────────────────────────────────────┐
 │                    KUBERNETES POD                               │
 │                                                                │
 │  /opt/hermes/          ← image (read-only root FS)            │
 │  /opt/halos/           ← image (read-only root FS)            │
 │  /opt/data/            ← PVC (read-write, persistent)         │
 │  /opt/data/config.yaml ← ConfigMap (read-only, subPath)       │
 │  /opt/data/SOUL.md     ← ConfigMap (read-only, subPath)       │
 │  /opt/data/.env        ← Secret (read-only, mode 0400)        │
 │  /opt/data/store/      ← PVC subdirectory                     │
 │  /opt/data/memories/   ← PVC subdirectory                     │
 │  /opt/data/sessions/   ← PVC subdirectory                     │
 └────────────────────────────────────────────────────────────────┘
```

### Mount Map Detail

```
$HERMES_HOME (/opt/data/)
├── .env                    ← Secret mount (0400, read-only)
├── config.yaml             ← ConfigMap: halo-config
├── system-prompt.md        ← ConfigMap: halo-prompt
├── SOUL.md                 ← ConfigMap: halo-soul
├── memctl.yaml             ← ConfigMap: halo-module-config (optional)
├── watchctl.yaml           ← ConfigMap: halo-module-config (optional)
├── state.db                ← PVC (Hermes session DB)
├── heartbeat               ← PVC (written by gateway asyncio loop)
├── sessions/               ← PVC (conversation transcripts)
├── memories/               ← PVC (memctl markdown notes + INDEX.md)
├── store/                  ← PVC (SQLite: journal.db, track_*.db, ...)
├── logs/                   ← PVC (gateway file logs, secondary to stdout)
├── skills/                 ← PVC (synced from image on boot)
├── cron/                   ← PVC (cron state)
└── hooks/                  ← PVC (event hooks)
```

### What Varies vs What Doesn't

```
        SHARED (image)                    PER-CLIENT (config + secrets)
        ══════════════                    ════════════════════════════

   ┌─ Gateway code (run.py)         ┌─ Telegram bot token
   ├─ All halos modules             ├─ Allowed Telegram user IDs
   ├─ Python/Node runtime           ├─ Anthropic API key
   ├─ Entrypoint script             ├─ System prompt (personality)
   ├─ Memory system mechanics       ├─ SOUL.md (persistent persona)
   ├─ Note format / governance      ├─ Model choice (Opus/Sonnet)
   └─ Module code                   ├─ Session reset policy
                                    ├─ Briefing schedule
                                    ├─ Active modules list
                                    ├─ Advisor personas
                                    ├─ trackctl domains (activation)
                                    ├─ Resource limits (CPU/RAM)
                                    └─ Cost ceiling
```

---

## 5. Kubernetes Deployment Topology

### Cluster Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  VULTR VKE CLUSTER (London, shared Phase 1)                        │
│  Managed by: Terraform (halo repo, remote state)                   │
│  Deployed by: ArgoCD (GitOps, auto-sync)                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  NAMESPACE: argocd                                          │   │
│  │  ArgoCD server + repo-server + application-controller       │   │
│  │  Watches: halo-deploy-{client} repos on GitHub              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  NAMESPACE: monitoring                                      │   │
│  │  Prometheus │ Grafana │ Loki │ Promtail (DaemonSet)         │   │
│  │  Alertmanager → Telegram (primary) + email (secondary)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────┐  ┌──────────────────────────┐       │
│  │  NAMESPACE: halo-kai     │  │  NAMESPACE: halo-aura    │       │
│  │                          │  │                          │       │
│  │  ┌────────────────────┐  │  │  ┌────────────────────┐  │       │
│  │  │ Pod: halo-gateway  │  │  │  │ Pod: halo-gateway  │  │       │
│  │  │ ┌────────────────┐ │  │  │  │ ┌────────────────┐ │  │       │
│  │  │ │ gateway (main) │ │  │  │  │ │ gateway (main) │ │  │       │
│  │  │ └────────────────┘ │  │  │  │ └────────────────┘ │  │       │
│  │  │ ┌────────────────┐ │  │  │  │ ┌────────────────┐ │  │       │
│  │  │ │ backup sidecar │ │  │  │  │ │ backup sidecar │ │  │       │
│  │  │ └────────────────┘ │  │  │  │ └────────────────┘ │  │       │
│  │  └─────────┬──────────┘  │  │  └─────────┬──────────┘  │       │
│  │            │              │  │            │              │       │
│  │  ┌─────────▼──────────┐  │  │  ┌─────────▼──────────┐  │       │
│  │  │  PVC: halo-data    │  │  │  │  PVC: halo-data    │  │       │
│  │  │  5Gi block storage │  │  │  │  5Gi block storage │  │       │
│  │  └────────────────────┘  │  │  └────────────────────┘  │       │
│  │                          │  │                          │       │
│  │  ConfigMaps + Secrets    │  │  ConfigMaps + Secrets    │       │
│  │  NetworkPolicy (egress)  │  │  NetworkPolicy (egress)  │       │
│  │  RBAC (namespace-scoped) │  │  RBAC (namespace-scoped) │       │
│  └──────────────────────────┘  └──────────────────────────┘       │
│                                                                     │
│  ┌──────────────────────────┐                                      │
│  │  NAMESPACE: halo-client-n│  (future clients)                    │
│  │  (same structure)        │                                      │
│  └──────────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Pod Detail

```
┌──────────────────────────────────────────────────────────────────┐
│  POD: halo-gateway                                               │
│  securityContext: runAsUser=1000, runAsGroup=1000, fsGroup=1000  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  CONTAINER: gateway (main)                                 │  │
│  │  Image: ghcr.io/rickhallett/halo:v1.2.0                   │  │
│  │  Command: /opt/entrypoint.sh → hermes --gateway            │  │
│  │                                                            │  │
│  │  Resources:                                                │  │
│  │    requests: 256Mi RAM, 250m CPU                           │  │
│  │    limits:   1Gi RAM, 1000m CPU                            │  │
│  │                                                            │  │
│  │  Probes:                                                   │  │
│  │    startup:  checks /opt/data/heartbeat exists             │  │
│  │              (allows 5 min for init)                        │  │
│  │    liveness: checks heartbeat file < 120s old              │  │
│  │              (detects deadlocks — shell can't fake this)   │  │
│  │    readiness: same as liveness                             │  │
│  │                                                            │  │
│  │  Volumes:                                                  │  │
│  │    /opt/data          → PVC halo-data                      │  │
│  │    /opt/data/.env     → Secret halo-secrets (0400)         │  │
│  │    /opt/data/*.yaml   → ConfigMaps                         │  │
│  │    /opt/data/SOUL.md  → ConfigMap halo-soul                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  CONTAINER: backup (sidecar)                               │  │
│  │  Runs: daily sqlite3 .backup → S3 upload                  │  │
│  │  Shares: PVC halo-data (ReadWriteOnce, same Pod)          │  │
│  │  Retry: 3x exponential backoff (10s, 60s, 300s)           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Data Flow: Message Lifecycle

### Happy Path: User Sends a Telegram Message

```
 ┌──────────┐         ┌──────────────┐         ┌──────────────┐
 │ Telegram  │         │   Hermes     │         │  Anthropic   │
 │   User    │         │   Gateway    │         │  Claude API  │
 └─────┬────┘         └──────┬───────┘         └──────┬───────┘
       │                     │                        │
       │  1. Send message    │                        │
       │ ──────────────────► │                        │
       │   (Telegram API)    │                        │
       │                     │                        │
       │                     │  2. Poll receives msg  │
       │                     │  ──── (long-polling) ──│
       │                     │                        │
       │                     │  3. Auth check:        │
       │                     │     TELEGRAM_ALLOWED   │
       │                     │     _USERS contains    │
       │                     │     sender's ID?       │
       │                     │                        │
       │                     │  4. Build context:     │
       │                     │     SOUL.md +          │
       │                     │     system-prompt.md + │
       │                     │     session history    │
       │                     │                        │
       │                     │  5. API call ──────────►
       │                     │     (with tools)       │
       │                     │                        │
       │                     │  6. Claude responds    │
       │                     │  ◄──────────────────── │
       │                     │     (may include       │
       │                     │      tool calls)       │
       │                     │                        │
       │                     │  7. Execute tools:     │
       │                     │     ┌──────────────┐   │
       │                     │     │ memctl search│   │
       │                     │     │ nightctl add │   │
       │                     │     │ trackctl log │   │
       │                     │     │ mailctl read │   │
       │                     │     └──────────────┘   │
       │                     │                        │
       │                     │  8. Tool results back  │
       │                     │  ────────────────────► │
       │                     │                        │
       │                     │  9. Final response     │
       │                     │  ◄──────────────────── │
       │                     │                        │
       │  10. Reply          │                        │
       │ ◄────────────────── │                        │
       │   (Telegram API)    │                        │
       │                     │                        │
       │                     │  11. Log to stdout     │
       │                     │      (JSON: client_id, │
       │                     │       tokens, cost)    │
       │                     │                        │
       │                     │  12. Touch heartbeat   │
       │                     │      (asyncio task,    │
       │                     │       every 60s)       │
       │                     │                        │
```

### Tool Dispatch Detail

```
USER: "Log 30 minutes zazen and show my streak"

     Gateway receives message
           │
           ▼
     Claude API call (with tool definitions)
           │
           ▼
     Claude returns tool_use:
       ┌─ trackctl.add_entry("zazen", 30, "logged via chat")
       └─ trackctl.compute_streak("zazen")
           │
           ▼
     Gateway executes tools against halos modules
       │
       ├── trackctl writes to store/track_zazen.db (on PVC)
       └── trackctl reads streak from same DB
           │
           ▼
     Tool results sent back to Claude
           │
           ▼
     Claude synthesises: "Logged 30 min zazen. 5-day streak 🔥"
           │
           ▼
     Gateway sends reply to Telegram
```

### No Inbound Networking Required

```
    IMPORTANT: The gateway has NO inbound HTTP endpoints.

    ┌─────────┐                    ┌──────────────────┐
    │Telegram  │ ◄──── polling ────│  Halo Gateway    │
    │  API     │ ────── reply ────►│  (outbound only) │
    └─────────┘                    └──────────────────┘

    No Service, no Ingress, no LoadBalancer.
    The gateway reaches OUT to Telegram and Anthropic.
    Nothing reaches in. This simplifies security enormously.
```

---

## 7. Storage & Backup Architecture

### Data Layout on PVC

```
PVC: halo-data (5Gi, Vultr Block Storage HDD)
│
├── state.db              Hermes: sessions, message history
├── heartbeat             Written by asyncio loop every 60s
│
├── store/
│   ├── journal.db        journalctl entries + LLM synthesis cache
│   ├── track_zazen.db    trackctl: zazen metrics
│   ├── track_movement.db trackctl: movement metrics
│   ├── track_*.db        trackctl: other domains
│   ├── nightctl.db       nightctl: tasks, Eisenhower matrix
│   ├── mail.db           mailctl: filter audit log
│   └── journal-cache/    journalctl: sliding window cache
│
├── memories/
│   ├── INDEX.md          memctl: auto-maintained lookup index
│   └── notes/
│       ├── 20260315-*.md memctl: individual memory notes
│       └── ...
│
├── sessions/             Hermes: conversation transcripts
├── logs/                 Hermes: file-based logs (secondary)
├── skills/               Hermes: synced skill definitions
├── cron/                 cronctl: schedule state
└── hooks/                Hermes: event hook scripts
```

### SQLite Safety Model

```
    WHY SQLITE IS FINE HERE:

    ┌──────────────────────────────────────────────┐
    │  1 client = 1 pod = 1 process = 1 writer     │
    │                                              │
    │  No concurrent writes. No shared-nothing.    │
    │  SQLite is the correct choice at this scale. │
    └──────────────────────────────────────────────┘

    PRAGMA journal_mode=WAL;    ← Set on every connection
    │
    ├── Survives unclean shutdown (pod kill, node failure)
    ├── Readers don't block writers
    └── Block storage compatible (no NFS locking issues)

    Schema evolution:
    ├── Additive only: ALTER TABLE ... ADD COLUMN ... DEFAULT ...
    ├── Old code ignores new columns (SQLite is lenient)
    └── Destructive changes require migration script + version gate
```

### Backup Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  DAILY BACKUP FLOW                                              │
│                                                                 │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────┐  │
│  │ Gateway Pod   │     │ Backup Sidecar   │     │ Vultr S3   │  │
│  │ (main)        │     │ (same pod)       │     │ (off-region│  │
│  │               │     │                  │     │  bucket)   │  │
│  │  state.db ────┼────►│ sqlite3 .backup  │     │            │  │
│  │  store/*.db ──┼────►│ (safe hot copy)  │     │            │  │
│  │               │     │       │          │     │            │  │
│  │               │     │       ▼          │     │            │  │
│  │               │     │  /tmp/backup/    │     │            │  │
│  │               │     │  (emptyDir vol)  │     │            │  │
│  │               │     │       │          │     │            │  │
│  │               │     │       ▼          │     │            │  │
│  │               │     │  S3 upload ──────┼────►│ stored     │  │
│  │               │     │  (3x retry,      │     │            │  │
│  │               │     │   exp backoff)   │     │            │  │
│  └───────────────┘     └──────────────────┘     └────────────┘  │
│                                                                 │
│  WHY SIDECAR, NOT CRONJOB?                                      │
│  Cloud PVCs are ReadWriteOnce — only one Pod can mount them.   │
│  A CronJob would be a second Pod. It can't access the PVC.     │
│                                                                 │
│  WHY OFF-REGION?                                                 │
│  If London burns, backups in London burn too.                   │
│  Backup bucket is in a different Vultr region.                  │
│                                                                 │
│  WEEKLY VERIFICATION:                                            │
│  Download latest backup → PRAGMA integrity_check →              │
│  SELECT count(*) FROM key tables → log result.                  │
│  Untested backups are not backups.                               │
│                                                                 │
│  RPO: 24 hours (daily cycle)                                     │
│  RTO: ~1 hour (Terraform rebuild + S3 restore)                  │
└─────────────────────────────────────────────────────────────────┘
```

### Restore Flow (Empty PVC Detection)

```
    Pod starts → entrypoint.sh runs
         │
         ▼
    state.db exists?
    ┌─── YES ──── Normal boot. Skip restore.
    │
    └─── NO ───── Empty PVC detected (first run or data loss)
                    │
                    ▼
              BACKUP_S3_BUCKET set?
              ┌─── NO ──── Bootstrap fresh defaults (dev/local only)
              │
              └─── YES ─── python3 restore-from-s3.py
                              │
                              ├── Success → "Restore complete" → normal boot
                              └── Failure → "WARNING: Restore failed" →
                                            bootstrap fresh defaults
                                            (prevents blank instance from
                                             overwriting next backup cycle)
```

---

## 8. Security Model

### Defence in Depth

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: NETWORK                                               │
│                                                                 │
│  NetworkPolicy per namespace:                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  EGRESS ALLOWED:                                        │   │
│  │    ✅ api.telegram.org (FQDN-based, Cilium/Calico)     │   │
│  │    ✅ api.anthropic.com                                 │   │
│  │    ✅ DNS (kube-dns)                                    │   │
│  │    ✅ Vultr S3 endpoint (for backups)                   │   │
│  │                                                         │   │
│  │  EGRESS DENIED:                                         │   │
│  │    ❌ Inter-namespace (no cross-client communication)   │   │
│  │    ❌ Private IP ranges (10.0.0.0/8, 172.16.0.0/12)    │   │
│  │    ❌ Everything else on non-443 ports                  │   │
│  │                                                         │   │
│  │  INGRESS:                                               │   │
│  │    ❌ None. No Service, no Ingress. Gateway polls out.  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  LAYER 2: IDENTITY & ACCESS                                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Telegram: TELEGRAM_ALLOWED_USERS whitelist             │   │
│  │  K8s RBAC: namespace-scoped Role only                   │   │
│  │  ServiceAccount: read own ConfigMaps/Secrets, nothing   │   │
│  │  else. No ClusterRole for client workloads.             │   │
│  │                                                         │   │
│  │  Verify: kubectl auth can-i --list                      │   │
│  │    --as=system:serviceaccount:halo-aura:default         │   │
│  │    -n halo-kai → must return empty                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  LAYER 3: CONTAINER RUNTIME                                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Non-root: UID 1000 / GID 1000 (hermes user)           │   │
│  │  Read-only root FS (only /opt/data is writable)         │   │
│  │  No privileged containers                               │   │
│  │  Hermes HERMES_EXEC_ASK: dangerous cmds need approval   │   │
│  │  Terminal tools: DISABLED for non-technical clients      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  LAYER 4: SECRET HANDLING                                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  .env mounted as FILE (mode 0400), NOT envFrom          │   │
│  │                                                         │   │
│  │  Why file mount > envFrom:                              │   │
│  │  ┌───────────────────┬────────────────────────────┐    │   │
│  │  │ envFrom           │ File mount (0400)          │    │   │
│  │  ├───────────────────┼────────────────────────────┤    │   │
│  │  │ os.environ access │ File read only at startup  │    │   │
│  │  │ /proc/self/environ│ Not in process environment │    │   │
│  │  │ Child processes   │ Not inherited by children  │    │   │
│  │  │ `env` command     │ Not visible via env/printenv│   │   │
│  │  └───────────────────┴────────────────────────────┘    │   │
│  │                                                         │   │
│  │  After loading: del os.environ[key] (Hermes patch)     │   │
│  │  Phase 2: Sealed Secrets (encrypted in git, decrypted  │   │
│  │  only in-cluster)                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  LAYER 5: IMAGE SUPPLY CHAIN                                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Base image: digest-pinned (not just tag)               │   │
│  │  CI: Trivy scan before push (CRITICAL + HIGH = fail)    │   │
│  │  Weekly: re-scan deployed images for new CVEs           │   │
│  │  Registry: GHCR with immutable tags enabled             │   │
│  │  Future: SBOM (Syft) + signing (cosign) at 5+ clients  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Cost Circuit Breaker (Agentic Safety)

```
    LLM API call requested
           │
           ▼
    ┌──────────────────────────┐
    │ Check: monthly spend     │
    │ < COST_CEILING_USD?      │
    │ (local SQLite counter)   │
    └──────────┬───────────────┘
               │
       ┌───────┴────────┐
       │                │
      YES              NO
       │                │
       ▼                ▼
    Proceed          ┌───────────────────────────┐
    with call        │ BREAKER ACTIVATED          │
                     │                           │
                     │ • Current response        │
                     │   completes (sunk cost)   │
                     │ • Next message gets:      │
                     │   "Monthly limit reached" │
                     │ • Resume: operator raises │
                     │   ceiling via ConfigMap   │
                     │   update + pod restart    │
                     │ • No hot-reload — forces  │
                     │   deliberate action       │
                     └───────────────────────────┘

    Counter resets: midnight UTC, 1st of each month.
    This is a CONTROL, not an alert. Alerts arrive after
    humans can't act. Agentic loops burn money faster than
    humans can respond to notifications.
```

---

## 9. CI/CD & Upgrade Pipeline

### Image Build & Deploy Flow

```
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  HALO REPO (product source)           CLIENT REPO (config only)      │
│  github.com/rickhallett/halo          github.com/rickhallett/         │
│                                       halo-deploy-aura               │
│  1. Kai pushes code change                                           │
│     │                                                                │
│  2. Kai tags: git tag v1.2.0                                         │
│     │                                                                │
│  3. GitHub Actions triggers ──────────────────────────────┐          │
│     │                                                     │          │
│     ▼                                                     │          │
│  ┌───────────────────────────────────────┐                │          │
│  │ CI Pipeline                           │                │          │
│  │                                       │                │          │
│  │ a. Checkout (with submodules)         │                │          │
│  │ b. Validate vendor/ populated         │                │          │
│  │ c. Trivy scan (CRITICAL/HIGH = fail)  │                │          │
│  │ d. docker build                       │                │          │
│  │ e. docker push                        │                │          │
│  │    ghcr.io/rickhallett/halo:v1.2.0    │                │          │
│  │    (immutable tag, no :latest)        │                │          │
│  └───────────────────┬───────────────────┘                │          │
│                      │                                     │          │
│  4. Kai tests on own instance (≥24h canary) ◄─────────────┘          │
│     │                                                                │
│  5. If good: bump tag in client repo                                 │
│     │                                                                │
│     ▼                                                                │
│                                       ┌────────────────────────────┐ │
│                                       │ kustomization.yaml         │ │
│                                       │ image: halo:v1.1.0        │ │
│                                       │        ──────────         │ │
│                                       │ image: halo:v1.2.0  ✏️    │ │
│                                       └────────────┬───────────────┘ │
│                                                    │                 │
│  6. Push to client repo                            │                 │
│     │                                              │                 │
│     ▼                                              ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  ArgoCD detects change (auto-sync enabled)                  │    │
│  │  │                                                          │    │
│  │  ├── Resolves Kustomize (base from halo repo + overlay)     │    │
│  │  ├── Applies manifests to halo-aura namespace               │    │
│  │  ├── Pod restarts with new image                            │    │
│  │  └── PVC preserved (data survives restart)                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  7. ROLLBACK: revert tag bump in client repo → ArgoCD syncs back     │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Canary Strategy

```
    Kai is ALWAYS the canary.

    v1.2.0 built
        │
        ▼
    Deploy to halo-kai namespace
        │
        ├── Run for ≥ 24 hours
        ├── Monitor: logs, cost, heartbeat, tool execution
        │
        ▼
    Stable? ──── NO ──── Fix, rebuild, re-tag
        │
       YES
        │
        ▼
    Bump tag in halo-deploy-aura
        │
        ▼
    ArgoCD deploys to Aura
```

---

## 10. Multi-Tenancy & Isolation

### Repo Topology: Product vs Client

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  halo/  (PRODUCT REPO — one copy, shared by all)                      │
│  │                                                                     │
│  ├── Dockerfile            ← builds the universal image               │
│  ├── docker/                                                           │
│  │   ├── entrypoint.sh     ← container bootstrap                      │
│  │   └── defaults/         ← fallback config for local dev            │
│  ├── halos/                ← all Python modules                        │
│  ├── vendor/hermes-agent/  ← gateway (git submodule of fork)          │
│  ├── infra/k8s/base/      ← shared K8s manifests                      │
│  └── .github/workflows/   ← CI: build, scan, push image              │
│                                                                        │
│  halo-deploy-aura/  (CLIENT REPO — one per client, config only)       │
│  │                                                                     │
│  ├── config/                                                           │
│  │   ├── .env              ← bot token, API keys (encrypted)          │
│  │   ├── config.yaml       ← model, schedule, modules                 │
│  │   ├── system-prompt.md  ← her bot's personality (ephemeral)        │
│  │   ├── SOUL.md           ← her bot's personality (persistent)       │
│  │   └── advisors/         ← her roundtable personas (markdown)       │
│  ├── infra/k8s/                                                        │
│  │   ├── kustomization.yaml ← references halo/infra/k8s/base         │
│  │   ├── namespace.yaml                                                │
│  │   ├── configmap.yaml    ← wraps config/ files as ConfigMaps        │
│  │   ├── secrets.yaml      ← sealed secrets for .env                  │
│  │   └── deployment.yaml   ← image tag pin, resource limits           │
│  └── argocd-app.yaml       ← ArgoCD Application definition           │
│                                                                        │
│  halo-deploy-clientN/  (same structure, different config)              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Isolation Guarantees

```
    CLIENT A (halo-aura)              CLIENT B (halo-kai)
    ════════════════════              ════════════════════

    ┌──────────────────┐              ┌──────────────────┐
    │ Namespace:       │              │ Namespace:       │
    │   halo-aura      │              │   halo-kai       │
    │                  │              │                  │
    │ Own PVC          │     ╳ ╳ ╳    │ Own PVC          │
    │ Own ConfigMaps   │  No cross-   │ Own ConfigMaps   │
    │ Own Secrets      │  namespace   │ Own Secrets      │
    │ Own RBAC Role    │  traffic     │ Own RBAC Role    │
    │ Own NetworkPolicy│              │ Own NetworkPolicy│
    │ Own ServiceAcct  │              │ Own ServiceAcct  │
    └──────────────────┘              └──────────────────┘

    WHAT A CAN'T DO:
    ❌ Read B's secrets
    ❌ Access B's PVC
    ❌ Send network traffic to B's pod
    ❌ Query B's metrics (no cross-namespace in Grafana)
    ❌ See B's memory notes, journal, tasks

    WHAT THEY SHARE:
    ✅ Same container image (identical code)
    ✅ Same K8s cluster (Phase 1 cost efficiency)
    ✅ Same monitoring stack (Kai sees all; clients see only their own)
```

---

## 11. Observability Stack

### Monitoring Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  NAMESPACE: monitoring                                               │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │
│  │  Prometheus     │  │  Loki          │  │  Grafana               │ │
│  │  (metrics)      │  │  (logs)        │  │  (dashboards)          │ │
│  │                 │  │                │  │                        │ │
│  │ Scrapes:        │  │ Ingests:       │  │ Queries:               │ │
│  │  - pod metrics  │  │  - stdout/err  │  │  - Per-client cost     │ │
│  │  - node metrics │  │    from all    │  │  - Token usage/day     │ │
│  │  - PVC usage    │  │    pods via    │  │  - Session count       │ │
│  │  - restarts     │  │    Promtail    │  │  - Error rate          │ │
│  │                 │  │    DaemonSet   │  │  - PVC usage %         │ │
│  └────────┬────────┘  └────────┬───────┘  │  - Restart count      │ │
│           │                    │          │  - Heartbeat freshness │ │
│           ▼                    ▼          └────────────────────────┘ │
│  ┌──────────────────────────────────┐                                │
│  │  Alertmanager                    │                                │
│  │                                  │                                │
│  │  Rules:                          │     Alert Channels:            │
│  │  • Pod restart > 3x / 10min     │     ┌───────────────────┐     │
│  │  • PVC usage > 80%              │────►│ Telegram (Kai's   │     │
│  │  • Heartbeat stale > 5min       │     │ own Hermes bot)   │     │
│  │  • Monthly cost > ceiling       │     └───────────────────┘     │
│  │  • Backup upload failed         │     ┌───────────────────┐     │
│  │                                  │────►│ Email (mailctl)   │     │
│  │                                  │     │ (backup channel)  │     │
│  └──────────────────────────────────┘     └───────────────────┘     │
│                                                                      │
│  Two independent alert channels: if Telegram is the thing that's    │
│  broken, email still arrives.                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Structured Log Flow

```
    Gateway process
         │
         │  Every LLM API call emits JSON to stdout:
         │  {
         │    "event": "llm_call",
         │    "client_id": "aura",
         │    "model": "claude-sonnet-4-20250514",
         │    "input_tokens": 2340,
         │    "output_tokens": 891,
         │    "cost_estimate_usd": 0.023,
         │    "tool_calls": ["trackctl.add_entry", "memctl.search"],
         │    "duration_ms": 3200,
         │    "timestamp": "2026-04-04T10:23:45Z"
         │  }
         │
         ▼
    Promtail (DaemonSet, scrapes container stdout)
         │
         ▼
    Loki (indexed by namespace, pod, client_id label)
         │
         ▼
    Grafana (query: sum cost_estimate_usd by client_id, month)
         │
         ▼
    Weekly client report (delivered via their bot):
    "This week: 142 messages, 84k tokens, ~$12.40 API cost"
```

---

## 12. Cost Structure

### Per-Client Monthly Breakdown

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENT COST MODEL                                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  KAI'S HARD COSTS (per client)                       │   │
│  │                                                      │   │
│  │  VKE node share (1/N of $24)    £8-20/mo            │   │
│  │  Object storage (backups)        ~£4/mo              │   │
│  │  Container registry              £0 (free tier)      │   │
│  │  ──────────────────────────────────────              │   │
│  │  Total hard cost:                ~£12-24/mo          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CLIENT PAYS                                         │   │
│  │                                                      │   │
│  │  Monthly service (Kai)           £200/mo             │   │
│  │    includes: infra + 4 hrs support                   │   │
│  │  LLM API (client's own key)      £25-65/mo          │   │
│  │    varies by model + usage                           │   │
│  │  ──────────────────────────────────────              │   │
│  │  Total client outlay:            ~£225-265/mo        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  KAI'S MARGIN                                        │   │
│  │                                                      │   │
│  │  Revenue:     £200/mo                                │   │
│  │  Hard costs:  £12-24/mo                              │   │
│  │  Net:         £176-188/mo (before labour)            │   │
│  │                                                      │   │
│  │  4 included hours @ ~£44-47/hr effective             │   │
│  │  Additional hours @ £85/hr                           │   │
│  │                                                      │   │
│  │  Margin improves as system stabilises (fewer support │   │
│  │  hours consumed). At 3 clients: ~£525-565/mo net.   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Setup: £800-1,200 (founding) / £1,500-2,500 (standard)    │
└──────────────────────────────────────────────────────────────┘
```

---

## 13. Phased Rollout

### Implementation Timeline

```
PHASE 0: ONBOARDING (now → 3 days)
═══════════════════════════════════
  • Second Hermes process on Kai's Mac with Aura's bot token
  • Gather requirements via onboarding conversations
  • Output: Halo specification document for Aura
  • Gate: Aura's spec approved

         │
         ▼

PHASE 1: CONTAINERISATION (~2 days agent work)
═══════════════════════════════════════════════
  • Vendor hermes-agent as git submodule
  • Write Dockerfile + entrypoint.sh
  • Build image, test locally with Kai's config
  • Test with Aura's bot token (local Docker)
  • Gate: Gateway starts, connects to Telegram, responds to a message

         │
         ▼

PHASE 2: CLIENT REPO TEMPLATE (~1 day)
═══════════════════════════════════════
  • Create halo-deploy-aura/ repo
  • Populate config/ from Aura's spec
  • Write Kustomize base + overlay
  • Gate: `kustomize build` produces valid manifests
         `kubectl apply --dry-run=server` succeeds

         │
         ▼

PHASE 3: INFRASTRUCTURE (~1 day)
════════════════════════════════
  • Terraform: VKE cluster (remote state, state locking)
  • Install ArgoCD + monitoring stack
  • Deploy Aura's namespace
  • Write onboarding runbook (while steps are fresh)
  • Gate: Aura's bot responds on Telegram FROM K8s

         │
         ▼

PHASE 4: HARDENING (ongoing)
═════════════════════════════
  • NetworkPolicy per namespace
  • Sealed Secrets
  • Backup sidecar + verification job
  • Cost circuit breaker implementation
  • Trivy weekly re-scan
  • Data export / offboarding script
  • OPA/Gatekeeper (when client count > 3)
```

### What Exists vs What Needs Building

```
    EXISTS TODAY                          NEEDS BUILDING
    ════════════                          ══════════════

    ✅ Hermes gateway (upstream)          🔨 Dockerfile
    ✅ Halos modules (all of them)        🔨 entrypoint.sh
    ✅ Memory system (memctl)             🔨 Vendor submodule setup
    ✅ Task tracking (nightctl)           🔨 K8s base manifests
    ✅ Metrics (trackctl)                 🔨 Client repo template
    ✅ Briefings pipeline                 🔨 Terraform for VKE
    ✅ Journal (journalctl)               🔨 ArgoCD setup
    ✅ Email (mailctl)                    🔨 Backup sidecar
    ✅ Advisors (roundtable)              🔨 Cost circuit breaker
    ✅ Cron scheduling (cronctl)          🔨 Heartbeat asyncio patch
    ✅ Jeany infra patterns               🔨 Structured JSON logging
    ✅ Upstream Dockerfile (base)         🔨 Secret cleanup patch
                                          🔨 WAL mode verification
                                          🔨 Restore-from-S3 script
                                          🔨 Onboarding runbook
```

---

## 14. Glossary

| Term | Meaning |
|---|---|
| **Halo** | The product: a personalised AI assistant platform |
| **Hermes** | The gateway engine (open-source, Nous Research). Handles Telegram ↔ Claude communication |
| **Halos** | The Python module ecosystem (memctl, nightctl, trackctl, etc.) — Halo's tools |
| **SOUL.md** | Persistent agent personality file. Defines who the bot *is* across sessions |
| **System prompt** | Ephemeral instructions loaded at session start. Can change without restarting |
| **Roundtable** | Historical-figure AI advisor personas (Musashi, Seneca, etc.) |
| **Fat image** | Docker image containing all code. Client config is external |
| **Thin config** | Per-client configuration files mounted into the container at deploy time |
| **PVC** | Persistent Volume Claim — durable storage in K8s that survives pod restarts |
| **ConfigMap** | K8s resource for non-secret configuration data |
| **Sealed Secret** | Encrypted secret that's safe to commit to git (decrypted only in-cluster) |
| **ArgoCD** | GitOps tool: watches a git repo, auto-deploys changes to K8s |
| **Kustomize** | K8s manifest templating: base manifests + per-environment overlays |
| **Circuit breaker** | Hard spending limit that stops API calls, not just alerts |
| **Canary** | Kai's own instance — always upgraded first, runs for 24h before client rollout |
| **WAL mode** | SQLite Write-Ahead Logging — crash-safe, reader-friendly journal mode |
| **RPO/RTO** | Recovery Point Objective (max data loss) / Recovery Time Objective (max downtime) |

---

*Generated from [halo-containerisation-spec.md](halo-containerisation-spec.md). For implementation details, refer to the spec. For the client-facing proposal, see [halo-client-proposal-aura.md](halo-client-proposal-aura.md).*
