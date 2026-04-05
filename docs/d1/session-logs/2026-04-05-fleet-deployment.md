---
title: "Session Log: Fleet Deployment Day"
category: journal
status: active
created: 2026-04-05
---

# 2026-04-05 — Fleet Deployment Day

**Duration:** ~06:00–19:45 BST (~13 hours, breaks included)
**Branch:** `feat/containerisation`
**Commits:** 28
**Diff:** +5,533 / -57 across 57 files

## Context

Day 2 of Kubernetes. Yesterday: got VKE running, Prometheus/Grafana deployed, Halo gateway (Aura) serving on Telegram. Today's goal: deploy the advisory fleet as event-sourced pods connected via NATS.

## Morning — Foundation (06:00–12:00)

Started with the observability stack. Grafana's sidecar had a TLS issue on VKE — fixed, wrote the observability runbook. Then moved to architecture: wrote the event-sourced fleet spec (1,559 lines — the spec that survived simplification from a much larger original that included release state machines, per-advisor NATS auth, upcasters, and date estimates. All cut.)

Built the eventsource package from scratch:
- `core.py` — Event envelope, EventPublisher (NATS JetStream)
- `projection.py` — ProjectionEngine (SQLite, checkpoints, transactional apply)
- `handlers/` — Track, Night, Journal domain projections
- `consumer.py` — AdvisorEventLoop (pull subscribe, replay from checkpoint, poison event handling)

Adversarial review caught three issues: non-atomic projection apply, entry_id collisions across track domains (movement#1 vs zazen#1), and consumer not replaying from start on empty projection. All fixed. Composite PK `(domain, id)` for track_entries.

35 tests written including 2 real NATS Docker integration tests. Suite: 1,364 passing.

## Afternoon — NATS + First Advisor (12:00–16:00)

Deployed NATS JetStream to `halo-fleet` namespace. HALO stream: `halo.>` subjects, 5GB, 90-day retention. Auth: shared `hq` + `advisor` users (subject scoping doesn't work with JetStream API calls — needs `_INBOX.>` and `$JS.API.>` access).

CI pipeline was a saga. Kaniko choked on submodule flags. Local push timed out (4GB image, residential internet). Settled on GitHub Actions → Vultr CR. Same datacenter as VKE, instant pulls.

Musashi deployed as first advisor. Three bugs found in rapid succession:

1. **Store path resolution.** All halos modules walked up from `__file__` to find `store/`. In containers, Python installs to `/opt/venv/lib/...` — walk never finds `store/`. Created `halos.common.paths` with HERMES_HOME-aware resolution. Updated all six affected modules.

2. **ConfigMap writability.** Mounted `config.yaml` via ConfigMap subPath directly to `/opt/data/config.yaml`. Read-only. Hermes's `/sethome` command crashed with `Device or resource busy`. Fix: mount to `/opt/defaults/`, copy to `/opt/data/` on startup.

3. **Login shell PATH.** Hermes runs tools via `bash -lic`. Debian's `/etc/profile` resets PATH to system defaults, stripping `/opt/venv/bin`. Every halos CLI tool: `exit 127 — command not found`. Fix: write `export PATH="/opt/venv/bin:$PATH"` to `~/.bashrc` in the pod startup command.

All three would have hit every advisor. Fixed once in the template.

## Late Afternoon — Fleet Expansion (16:00–18:00)

Deployed Socrates, Medici, and Machiavelli from the Musashi template. Copy-paste with persona swap. All four 1/1 Running within minutes.

More bugs:
- Medici couldn't find financial data — file existed in repo but wasn't in the container. Mounted canonical position as ConfigMap.
- All advisors used relative paths in prompts (`data/finance/...`) — Hermes file tools couldn't resolve them. Switched to absolute `/opt/data/...` paths.
- All prompts had `uv run trackctl` — should be just `trackctl` in the container. Stripped prefix.
- `imagePullPolicy` defaulted to `IfNotPresent` for the `fleet-latest` tag (Kubernetes only defaults to `Always` for the exact tag `latest`). Pods were running stale images. Added explicit `imagePullPolicy: Always`.

Seeded NATS stream with 22 events from local trackctl/journalctl data. All four advisors consuming and projecting correctly. Musashi confirmed live on Telegram, reading real movement/zazen data.

## Evening — Infrastructure + Observation (18:00–19:45)

Wired AdvisorEventLoop into the gateway entrypoint — runs as background process alongside Hermes. Starts if NATS_PASS is set, shuts down on SIGTERM.

Hit Vultr CR storage limit (10GB free tier, 5 old image tags accumulating). Vultr's tag deletion API is broken — every endpoint returns 500. Upgraded to Business plan ($5/mo, 20GB). Trimmed CI to push single tag only (`fleet-latest`).

Installed metrics-server. Actual resource usage vs requests:
- Advisors at idle: 1-2m CPU, 60-90Mi memory (requested: 50m, 192Mi)
- Node total: 9% CPU, 53% memory

Built Aura session relay — sidecar in halo-aura that tails Hermes JSONL session files and publishes user/assistant messages to `halo.observation.aura` on the NATS stream. Live and publishing within minutes of Aura's first conversation.

Added Aura (Telegram ID 7946268837) to allowed users on @aura_halo_01_bot.

Final infrastructure work: Dockerfile restructured for layer caching (dependency layers cached, source layers rebuild fast). GHA build cache enabled. Created `Dockerfile.halos` — tiny Alpine image (~5MB) containing only halos Python source, used as init container to overlay into pods. Halos-only updates: ~30 second build + pod restart, no full image rebuild needed.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Shared NATS credentials (hq + advisor) | Subject scoping breaks JetStream API. Auth boundary is the credential, not subject filtering. |
| GitHub Actions over Kaniko/local push | VKE nodes have no SSH, Kaniko choked on submodules, local push timed out. |
| Vultr CR over GHCR | Same datacenter as VKE. GHCR push was hanging. |
| emptyDir for projection storage | Projections rebuild from stream on restart. No PVC needed per advisor. |
| ConfigMaps to /opt/defaults/ | Mounted ConfigMaps are read-only. Copy to writable location on startup. |
| .bashrc PATH injection | Login shells reset PATH. Only reliable way to persist venv PATH for subprocesses. |
| Init container for halos overlay | Decouples halos iteration speed from base image rebuild. 30s vs 10min. |
| imagePullPolicy: Always | Mutable tags require explicit pull policy. Kubernetes default is wrong for this use case. |
| Vultr CR Business plan | Free tier (10GB) fills up, deletion API is broken. $5/mo for headroom. |

## Bugs Found: 13

All documented in `infra/k8s/fleet/README.md`. Every one was a container deployment gotcha that doesn't exist in local development. The pattern: things that work when cwd is the repo root and Python runs from source break when the code is pip-installed into a venv in a different filesystem, run by a different user, in a read-only mount, from a login shell that resets the environment.

## State at End of Day

- 4 advisors live: Musashi, Socrates, Medici, Machiavelli
- NATS stream: 27 events (22 seeded + 5 runtime)
- Aura relay: live, publishing observation events
- Bot tokens pending: Seneca, Sun Tzu (BotFather cooldown ~2h)
- Deferred: Bankei, Plutarch (luxury seats — not urgent)
- Node capacity: room for 3-4 more advisors at current resource profile
- Test suite: 1,364 passing
