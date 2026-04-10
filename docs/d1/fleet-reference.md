---
title: "Fleet Reference — Ryzen Bare Metal (k3s)"
category: reference
status: active
created: 2026-04-10
---

# Fleet Reference — Ryzen Bare Metal (k3s)

Canonical reference for the Halo advisor fleet running on the Ryzen homelab. Verified against live cluster state on 2026-04-10. This document supersedes any VKE-era references.

## Hardware

| Spec | Value |
|------|-------|
| Host | ryzen32 (via Tailscale) |
| OS | Arch Linux, kernel 6.19.6-arch1-1 |
| CPU | 16 cores |
| RAM | 30Gi total, ~23Gi available |
| Disk | 475G root, 77G used (17%) |
| Swap | 45Gi |
| IP (LAN) | 192.168.1.128 |

## Cluster

| Component | Version |
|-----------|---------|
| k3s | v1.34.6+k3s1 |
| containerd | 2.2.2 |
| Docker | 29.3.1 (builds only; k3s uses containerd) |
| Container registry | localhost:5000 (Docker registry, local to Ryzen) |

All `kubectl` commands require `sudo` — k3s kubeconfig is root-only at `/etc/rancher/k3s/k3s.yaml`.

## Namespace

| Property | Value |
|----------|-------|
| Name | halo-fleet |
| PodSecurity enforce | baseline |
| PodSecurity audit | baseline |
| PodSecurity warn | restricted |

## Fleet Roster

9 advisors + NATS. All advisors run `localhost:5000/halo:dev`.

| Seat | Name | Domain | Touchbase Schedule | Status |
|------|------|--------|-------------------|--------|
| I | musashi | Body (movement + zazen) | 07:00 daily | Running |
| II | draper | Pitch (positioning, narrative) | 07:10 daily | Running |
| III | karpathy | Craft (AI engineering, learning) | 07:05 daily | Running |
| IV | gibson | Futures (market terrain, tech trajectory) | 07:25 daily | Running |
| V | machiavelli | Power, perception, leverage | 07:20 daily | Running |
| VI | medici | Money (debt, burn, runway) | 07:15 daily | Running |
| VII | bankei | Rest (rhythm, the cost of never stopping) | 07:35 daily | Running |
| VIII | hightower | Heavy Iron (K8s ops, CKA) | 07:30 daily | Running |
| X | turing | Imitation Game (agentic engineering) | 10:00 daily | Running |

All touchbase messages go to Telegram chat ID `5967394003`.

## Image

Single image: `localhost:5000/halo:dev`. Everything baked in — Hermes gateway, halos Python tooling, system dependencies. No init containers, no halos overlay, no Vultr registry.

Build chain:
```
Mac (source) → Mutagen sync → Ryzen (local disk) → docker build → localhost:5000 → kubectl rollout restart
```

**Mutagen permission stripping (discovered 2026-04-10):** Mutagen syncs files from Mac to Ryzen with `600`/`700` permissions (owner-only), stripping the group/world read bits. Docker COPY preserves these permissions into the image. Since the container runs as UID 1000 (hermes) but files are owned by root, all source files become unreadable. The Dockerfile fixes this with `chmod -R a+rX` on all runtime directories after COPY steps. This is permanent — if Mutagen's permission behavior changes, the chmod is a no-op.

## Per-Advisor Resources

Each advisor gets 4 Kubernetes resources:

| Resource | Naming | Purpose |
|----------|--------|---------|
| Deployment | `advisor-{name}` | Pod spec, env, probes |
| ConfigMap (config) | `advisor-{name}-config` | `config.yaml` — provider, model, gateway, halos modules |
| ConfigMap (prompt) | `advisor-{name}-prompt` | `system-prompt.md` — persona, integrations, tools |
| Secret | `advisor-{name}-secrets` | `.env` — `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `TELEGRAM_ALLOWED_USERS` |
| PVC | `advisor-{name}-data` | 1Gi local-path — state.db, store/, sessions/, logs/ |

### Shared Resources

| Resource | Name | Purpose |
|----------|------|---------|
| Secret | nats-auth | `ADVISOR_PASS` — shared NATS credentials |
| ConfigMap | nats-config | NATS server configuration |
| ConfigMap | memctl-reader-config | Shared memctl config (read-only memory access) |
| PVC | nats-data | 10Gi local-path — NATS JetStream persistence |

## Deployment Pattern

Every advisor deployment follows this structure (verified from live `last-applied-configuration`):

- **No `imagePullSecrets`** — image is from localhost registry
- **No `initContainers`** — everything in single image
- **Container args**: `echo 'export PATH="/opt/venv/bin:$PATH"' >> ~/.bashrc && exec /opt/entrypoint.sh gateway`
- **Security context**: `runAsNonRoot: true`, UID/GID 1000, `seccompProfile: RuntimeDefault`, all capabilities dropped
- **Resources**: 50m/192Mi request, 500m/384Mi limit
- **Startup probe**: heartbeat file check, 10s initial delay, 30 retries
- **Liveness probe**: heartbeat file freshness < 120s, 60s interval
- **Strategy**: Recreate (not RollingUpdate — advisors hold session state)

### Environment Variables (all advisors)

| Variable | Value | Notes |
|----------|-------|-------|
| ADVISOR_NAME | `{name}` | Per-advisor |
| ADVISOR_TOUCHBASE_SCHEDULE | cron expression | Per-advisor |
| ADVISOR_TOUCHBASE_CHAT_ID | 5967394003 | Kai's Telegram ID |
| ADVISOR_TOUCHBASE_PLATFORM | telegram | |
| TZ | Europe/London | |
| PATH | /opt/venv/bin:... | venv first |
| NATS_URL | nats://nats.halo-fleet.svc.cluster.local:4222 | Cluster-internal |
| NATS_USER | advisor | |
| NATS_PASS | (from secret nats-auth) | |

### Volume Mounts

| Mount | Source | Path |
|-------|--------|------|
| Config | ConfigMap `advisor-{name}-config` | `/opt/defaults/config.yaml` |
| Prompt | ConfigMap `advisor-{name}-prompt` | `/opt/defaults/system-prompt.md` |
| Secrets | Secret `advisor-{name}-secrets` | `/opt/data/.env` (read-only) |
| Data | PVC `advisor-{name}-data` | `/opt/data` |

## NATS JetStream

| Property | Value |
|----------|-------|
| Image | nats:2.10-alpine |
| ClusterIP | 10.43.86.239 |
| Client port | 4222 |
| Monitor port | 8222 |
| PVC | nats-data, 10Gi, local-path |
| Stream name | HALO |
| Auth | username `advisor`, password from `nats-auth` secret |

### Accessing NATS from Mac

NATS is ClusterIP only. SSH tunnel required:
```bash
ssh -L 4222:10.43.86.239:4222 mrkai@ryzen32 -fN
# Kill after use:
pkill -f "ssh.*4222.*ryzen32"
```

## Event Sourcing (Halostream)

Each advisor runs a NATS consumer sidecar process (`python3 -m halos.eventsource.run_consumer`) started by `entrypoint.sh` when `NATS_PASS` is set.

### Projection Database

Location: `/opt/data/store/projection.db` (inside each advisor's PVC).

Tables (verified on medici, 2026-04-10):

| Table | Rows | Purpose |
|-------|------|---------|
| _checkpoint | 1 | Consumer position (stream_seq, updated_at) |
| _processed_events | 241 | Idempotency — prevents double-processing |
| track_entries | 0 | trackctl metrics |
| journal_entries | 0 | journalctl entries |
| night_items | 0 | nightctl work items |
| night_jobs | 0 | nightctl background jobs |
| observation_messages | 0 | Observation ingest |
| advisor_messages | 41 | Cross-advisor comms |
| dev_commits | 0 | Git commit events |
| mail_triage | 0 | Email triage events |
| system_events | 19 | System lifecycle events |

Checkpoint at stream sequence 242, last updated 2026-04-10T06:26:31Z.

### Projection Rebuild

The projection is disposable. Delete `projection.db`, restart the pod, and the consumer replays from the beginning of the NATS stream. The stream is truth.

## Allowed Telegram Users

Configured per-advisor in `infra/k8s/fleet/{name}-secrets.yaml` as `TELEGRAM_ALLOWED_USERS` (comma-separated).

| User | Telegram ID | Access |
|------|-------------|--------|
| Kai | 5967394003 | All advisors |
| Kai's father | 6039583689 | Medici only (added 2026-04-10) |

## Storage

All PVCs use `local-path` storage class (k3s default). Data lives on Ryzen's local disk under `/var/lib/rancher/k3s/storage/`.

| PVC | Size | Advisor |
|-----|------|---------|
| advisor-musashi-data | 1Gi | musashi |
| advisor-karpathy-data | 1Gi | karpathy |
| advisor-draper-data | 1Gi | draper |
| advisor-medici-data | 1Gi | medici |
| advisor-machiavelli-data | 1Gi | machiavelli |
| advisor-gibson-data | 1Gi | gibson |
| advisor-hightower-data | 1Gi | hightower |
| advisor-bankei-data | 1Gi | bankei |
| advisor-turing-data | 1Gi | turing |
| nats-data | 10Gi | NATS JetStream |

**No NFS.** VKE used NFS for shared memory corpus and advisor state. Ryzen uses per-advisor local-path PVCs. Each advisor gets its own isolated storage with its own projection rebuilt from the halostream.

## Deploy Pipeline

### Mutagen Sync

One-way file sync from Mac to Ryzen. Session name: `halo`.

| Property | Value |
|----------|-------|
| Alpha | /Users/mrkai/code/halo (Mac) |
| Beta | ryzen32:~/code/halo (Ryzen) |
| Sync contents | 519 dirs, 2326 files, 126 MB |
| Excludes | `.git`, `store/` (track DBs synced separately) |

### Commands (justfile)

| Command | What it does |
|---------|-------------|
| `just deploy` | Full pipeline: sync flush, build, push, kubectl apply, rollout restart |
| `just build` | Sync flush + docker build on Ryzen |
| `just build-push` | Build + push to localhost:5000 |
| `just restart` | Rollout restart only (no build) |
| `just pods` | Show pod status |
| `just watch` | Live pod watch |
| `just logs {advisor}` | Tail logs for an advisor (uses `-l halo/advisor={name}`) |
| `just sync-status` | Mutagen sync status |
| `just sync-flush` | Block until Ryzen is up to date |
| `just sync-trackdbs` | SCP track DBs to Ryzen (excluded from Mutagen) |
| `just ssh` | SSH to Ryzen |
| `just remote {cmd}` | Run a command on Ryzen |
| `just registry-list` | Show what's in the local registry |
| `just build-push-halos` | Build halos overlay image (not used in standard deploy) |

### Deploy Sequence

```bash
# Standard deploy (everything)
just deploy

# Track DBs changed
just sync-trackdbs

# ConfigMap/Secret only (no image rebuild)
just sync-flush
ssh ryzen32 "cd ~/code/halo && sudo kubectl apply -f infra/k8s/fleet/"
just restart

# Single advisor restart
ssh ryzen32 "sudo kubectl rollout restart deploy/advisor-medici -n halo-fleet"
```

### Submodule (vendor/hermes-agent)

Mutagen excludes `.git` metadata. Submodule updates need manual tar+scp:
```bash
tar czf /tmp/hermes-agent.tar.gz -C vendor hermes-agent
scp /tmp/hermes-agent.tar.gz mrkai@ryzen32:/tmp/
ssh mrkai@ryzen32 "cd ~/code/halo && rm -rf vendor/hermes-agent && tar xzf /tmp/hermes-agent.tar.gz -C vendor/"
```

## Session Management

### Clearing advisor sessions

Session state lives in `state.db` on the PVC. Pod restarts do NOT clear it.

```bash
# Full session wipe for an advisor
sudo kubectl exec -n halo-fleet deploy/advisor-{name} -- \
  sh -c 'rm -f /opt/data/state.db /opt/data/state.db-wal /opt/data/state.db-shm /opt/data/gateway_state.json'
sudo kubectl delete pod -n halo-fleet -l halo/advisor={name}
```

### Process model inside a pod

Verified via `/proc` inspection (no `ps` binary in container):

| Process | Command |
|---------|---------|
| PID 1 | `/bin/bash /opt/entrypoint.sh gateway` |
| Entrypoint child | `hermes gateway` (Python, the Telegram bot) |
| Consumer sidecar | `python3 -m halos.eventsource.run_consumer` |
| Heartbeat | `sleep 30` loop (writes `/opt/data/heartbeat` for liveness probe) |

## Manifest Files (git)

| Path | Purpose |
|------|---------|
| `infra/k8s/fleet/{name}-deployment.yaml` | Deployment spec |
| `infra/k8s/fleet/{name}-config.yaml` | ConfigMap — config.yaml |
| `infra/k8s/fleet/{name}-prompt.yaml` | ConfigMap — system-prompt.md |
| `infra/k8s/fleet/{name}-secrets.yaml` | Secret — .env (bot token, API key, allowed users) |
| `infra/k8s/fleet/advisor-pvcs.yaml` | All 9 advisor PVCs |
| `infra/k8s/fleet/nats-deployment.yaml` | NATS StatefulSet/Deployment |
| `infra/k8s/fleet/nats-config.yaml` | NATS server config |
| `infra/k8s/fleet/nats-secrets.yaml` | NATS auth credentials |
| `infra/k8s/fleet/namespace.yaml` | Namespace with PodSecurity labels |

### VKE-era artifacts (dead, retained for archaeology)

| Path | Status |
|------|--------|
| `infra/k8s/fleet/nfs-server.yaml` | Dead — NFS server was VKE-only |
| `infra/k8s/fleet/memory-pvc.yaml` | Dead — Vultr block storage PVC for NFS |

## Label Selectors

| Selector | Matches |
|----------|---------|
| `halo/advisor={name}` | Single advisor pod (preferred for logs, exec) |
| `app.kubernetes.io/name=advisor-{name}` | Single advisor (used by Deployment selector) |
| `app.kubernetes.io/component=advisor` | All advisor pods |

**Do not use** `-l app={name}` — this label does not exist on any pod.

## Key Differences from VKE

| Aspect | VKE (dead) | Ryzen (live) |
|--------|------------|--------------|
| Registry | lhr.vultrcr.com/jeany/ | localhost:5000 |
| Image | halo:fleet-latest + halo-halos:latest | halo:dev (single) |
| Init containers | halos-sync + state-init | None |
| Storage | NFS (shared, VKE block storage) | local-path PVCs (per-advisor) |
| Memory corpus | Shared NFS mount (read-only) | Not mounted (TODO or removed) |
| GitOps | Argo CD (self-heal, auto-sync) | Manual (`just deploy`) |
| Deploy | git push → Argo polls → sync | Mutagen sync → build on Ryzen → kubectl apply |
| PodSecurity | Varied per namespace | baseline (enforce) on halo-fleet |
| Node | Vultr VKE managed nodes | Single Ryzen bare metal |

## Troubleshooting Quick Reference

| Symptom | Cause | Fix |
|---------|-------|-----|
| Pod stuck in Init | NFS volume mount — stale VKE IP | Update deployment to use PVC |
| Advisor ignores new prompt | ConfigMap not applied | `kubectl apply -f infra/k8s/fleet/` then restart |
| Old sessions bleed into new conversations | state.db on PVC survives restarts | Delete state.db + gateway_state.json, delete pod |
| Logs command returns nothing | Wrong label selector | Use `-l halo/advisor={name}` |
| Image pull fails | Vultr registry ref in manifest | Update image to `localhost:5000/halo:dev` |
| kubectl permission denied | k3s kubeconfig is root-only | Prefix with `sudo` |
