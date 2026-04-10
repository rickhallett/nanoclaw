---
title: "Halo Roundtable Advisor Migration to Kubernetes"
category: spec
status: archived
created: 2026-04-05
---

# Halo Roundtable Advisor Migration to Kubernetes

Technical specification for migrating the roundtable advisor system from Mac Mini cron jobs to dedicated Kubernetes pods on Vultr VKE.

## Status

Draft. Not yet reviewed. Written against codebase state as of 2026-04-05.

## Scope

Migrate 7 advisors (Musashi, Seneca, Socrates, Sun Tzu, Machiavelli, Medici, Bankei) and 1 dramaturg (Plutarch) from locally-executed Hermes cronjobs to containerised workloads on Vultr VKE. Each advisor becomes an independently deployable, observable unit.

Out of scope: the Hermes gateway itself (already containerised), HAL-prime, the agent spawner.

---

## 1. Current Architecture

### 1.1 Advisor Execution Model

Each advisor is a scheduled invocation of the Hermes agent framework. The Hermes cronjob:
1. Loads persona from `data/advisors/<name>/persona.md`
2. Loads living profile from `data/advisors/<name>/profile.md`
3. Runs halos CLI tools (`trackctl`, `nightctl`, `dashctl`, `journalctl`, `memctl`) to gather domain-specific data
4. Passes gathered data + persona through LLM synthesis (Claude Sonnet via CLI, OAuth, or API key)
5. Delivers the result to Telegram via bot API (`HERMES_BOT_TOKEN`)
6. Updates `profile.md` with new learnings

### 1.2 Schedule (from INDEX.md)

| Time  | Advisor     | Session Type |
|-------|-------------|-------------|
| 07:00 | Musashi     | Morning — body (movement + zazen) |
| 09:00 | Socrates    | Morning — craft (CPD, learning) |
| 19:45 | Seneca      | Evening — time (what did you do today) |
| 20:00 | Medici      | Evening — money (what did it cost) |
| 20:15 | Machiavelli | Evening — power (what aren't you seeing) |
| 20:30 | Sun Tzu     | Evening — strategy (what's next) |
| TBD   | Bankei      | On-demand — rest, rhythm |
| --    | Plutarch    | Dramaturg — reads all others, synthesises |

The morning briefing (separate from advisors) is a roundtable composition at 06:00 gathering from HAL/NIGHTCTL/RUBBER_DUCK/GAINZ_ROSHI agents — this is the `hal-briefing morning` command.

### 1.3 Data Dependencies

All data lives on the Mac Mini filesystem:

| Data | Path | Format | Size |
|------|------|--------|------|
| trackctl databases | `store/track_*.db` (6 files) | SQLite | Small (<10MB each) |
| nightctl job queue | `queue/items/*.yaml` | YAML files | Small |
| nightctl jobs DB | `store/jobs.db` | SQLite | Small |
| memctl corpus | `memory/` + `memctl.yaml` | Markdown + YAML | Medium |
| journal | `store/journal.db` | SQLite | Small |
| messages DB | `store/messages.db` | SQLite | Medium |
| mail DB | `store/mail.db` | SQLite | Small |
| advisor personas | `data/advisors/*/persona.md` | Markdown | Tiny |
| advisor profiles | `data/advisors/*/profile.md` | Markdown | Tiny, mutable |
| git repos | `~/code/*/` | Git repos | N/A — local only |
| briefing config | `briefings.yaml` + `*.yaml` configs | YAML | Tiny |

### 1.4 Auth Cascade (from synthesise.py)

LLM synthesis tries four strategies in order:
1. `claude` CLI (inherits OAuth — works when token is fresh)
2. OAuth token refresh via `~/.claude/.credentials.json`
3. Anthropic SDK with `ANTHROPIC_API_KEY` from `.env`
4. Raw data fallback (no LLM)

In containers, strategies 1-2 are unavailable (no Claude CLI, no OAuth credentials file). Strategy 3 is the primary path. This is a simplification, not a regression.

### 1.5 Delivery (from deliver.py)

Direct Telegram Bot API call via `httpx.post`. Token from `HERMES_BOT_TOKEN` env var (resolved via `telegram_bot_token_env` in `briefings.yaml`). Chat ID hardcoded in config: `5967394003`. Falls back to IPC file write for gateway pickup.

---

## 2. Container Architecture

### 2.1 Base Image Strategy

The existing Dockerfile uses `debian:13.4` with system Python + pip. This violates the repo's uv-only policy (TD-4 in CLAUDE.md). The advisor image should diverge from the gateway image.

```dockerfile
# Dockerfile.advisor
FROM python:3.12-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System deps (minimal — advisors don't need Node.js, ffmpeg, or Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -g 1000 advisor && useradd -u 1000 -g 1000 -m -d /home/advisor advisor

WORKDIR /opt/halo

# Copy project files for uv sync
COPY pyproject.toml uv.lock ./
COPY halos/ halos/
COPY scripts/ scripts/

# Install with uv (respects uv-only policy)
RUN uv sync --frozen --no-dev

# Advisor data (persona files baked in, profiles mounted)
COPY data/advisors/ /opt/halo/data/advisors/
COPY briefings.yaml /opt/halo/briefings.yaml

# Config files (will be overridden by ConfigMaps in k8s)
COPY memctl.yaml nightctl.yaml todoctl.yaml logctl.yaml ./

USER advisor
ENTRYPOINT ["uv", "run"]
```

**Key differences from gateway Dockerfile:**
- No Node.js, npm, Playwright, ffmpeg
- uv instead of pip
- No Hermes submodule dependency
- ~200MB image vs ~1.2GB for gateway

### 2.2 Pod Design: CronJobs, Not Long-Running Pods

Each advisor runs as a Kubernetes CronJob. Rationale:

- Advisors fire once or twice daily. A long-running pod with internal scheduling wastes resources 99.9% of the time.
- CronJobs give native k8s scheduling, retry logic, job history, and failure alerting.
- Each CronJob invocation is a fresh pod — no state corruption between runs.
- Profile updates (the only mutable state) go to a PVC.

The alternative (long-running pods with internal `schedule` library) adds complexity for no benefit. The "dedicated pod per advisor" mental model maps naturally to "dedicated CronJob per advisor."

**Exception:** Plutarch (the dramaturg) may need a different pattern if it reads advisor outputs in sequence. See section 3.

### 2.3 Resource Definitions

```yaml
# k8s/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: halo-advisors
  labels:
    app.kubernetes.io/part-of: halo
```

```yaml
# k8s/base/cronjob-musashi.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: advisor-musashi
  namespace: halo-advisors
  labels:
    app.kubernetes.io/name: advisor-musashi
    app.kubernetes.io/component: advisor
    halo/advisor: musashi
    halo/domain: body
    halo/session: morning
spec:
  schedule: "0 7 * * *"          # 07:00 daily (cluster TZ or use TZ field)
  timeZone: "Europe/London"
  concurrencyPolicy: Forbid       # Never overlap
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  startingDeadlineSeconds: 300     # 5min grace — if scheduler misses, still fire
  jobTemplate:
    spec:
      backoffLimit: 2              # Retry twice on failure
      activeDeadlineSeconds: 300   # Kill after 5min (LLM timeout safety)
      template:
        metadata:
          labels:
            halo/advisor: musashi
          annotations:
            prometheus.io/scrape: "true"
            prometheus.io/port: "9090"
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
          containers:
            - name: advisor
              image: ghcr.io/rickhallett/halo-advisor:v0.1.0
              command: ["uv", "run", "python", "-m", "halos.advisors.run"]
              args: ["--advisor", "musashi"]
              resources:
                requests:
                  cpu: 100m
                  memory: 256Mi
                limits:
                  cpu: 500m
                  memory: 512Mi
              env:
                - name: ADVISOR_NAME
                  value: "musashi"
                - name: BRIEFINGS_CONFIG
                  value: "/opt/halo/briefings.yaml"
                - name: TZ
                  value: "Europe/London"
              envFrom:
                - secretRef:
                    name: halo-api-keys
              volumeMounts:
                - name: advisor-profiles
                  mountPath: /opt/halo/data/advisors/musashi/profile.md
                  subPath: musashi-profile.md
                - name: halo-store
                  mountPath: /opt/halo/store
                  readOnly: true
                - name: advisor-config
                  mountPath: /opt/halo/briefings.yaml
                  subPath: briefings.yaml
                - name: advisor-output
                  mountPath: /opt/halo/output
          volumes:
            - name: advisor-profiles
              persistentVolumeClaim:
                claimName: advisor-profiles
            - name: halo-store
              persistentVolumeClaim:
                claimName: halo-store
            - name: advisor-config
              configMap:
                name: advisor-config
            - name: advisor-output
              emptyDir: {}
```

### 2.4 ConfigMaps and Secrets

```yaml
# k8s/base/configmap-advisors.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: advisor-config
  namespace: halo-advisors
data:
  briefings.yaml: |
    project_root: "/opt/halo"
    memctl_config: "/opt/halo/memctl.yaml"
    nightctl_config: "/opt/halo/nightctl.yaml"
    todoctl_config: "/opt/halo/todoctl.yaml"
    logctl_config: "/opt/halo/logctl.yaml"
    ipc_dir: "/opt/halo/data/ipc"
    ipc_group: "telegram_main"
    db_path: "/opt/halo/store/messages.db"
    model: "claude-sonnet-4-20250514"
    max_tokens: 1024
    chat_id: "5967394003"
    telegram_bot_token_env: "HERMES_BOT_TOKEN"
```

```yaml
# k8s/base/secret-api-keys.yaml
apiVersion: v1
kind: Secret
metadata:
  name: halo-api-keys
  namespace: halo-advisors
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "<from-vault>"
  HERMES_BOT_TOKEN: "<from-vault>"
  # Per-advisor tokens if needed in future
```

Persona files are baked into the image (they change rarely). Profiles are on a PVC (they're living documents updated by advisors).

### 2.5 Persistent Volume Claims

```yaml
# k8s/base/pvc-profiles.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: advisor-profiles
  namespace: halo-advisors
spec:
  accessModes:
    - ReadWriteMany          # Multiple CronJobs may run concurrently (evening session)
  storageClassName: vultr-block-storage-hdd
  resources:
    requests:
      storage: 1Gi           # Profiles are tiny — this is minimum Vultr allows
---
# k8s/base/pvc-store.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: halo-store
  namespace: halo-advisors
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: vultr-block-storage-hdd
  resources:
    requests:
      storage: 5Gi
```

**Trade-off: ReadWriteMany.** Vultr block storage is ReadWriteOnce. ReadWriteMany requires either:
- NFS provisioner (e.g., nfs-subdir-external-provisioner on a dedicated PV)
- Switching to Vultr Object Storage with s3fs-fuse (latency penalty)
- Accepting that evening advisors run sequentially (Forbid concurrency at the Job level, stagger schedules by 15min as currently done)

**Recommendation for Phase 1:** Use ReadWriteOnce. The existing 15-minute stagger between evening advisors means CronJobs don't overlap. Add `concurrencyPolicy: Forbid` and rely on the schedule gap. This is already the current behavior.

---

## 3. Scheduling & Orchestration

### 3.1 CronJob Schedule Matrix

```yaml
# All times Europe/London
advisor-musashi:     "0 7 * * *"     # 07:00
advisor-socrates:    "0 9 * * *"     # 09:00
advisor-seneca:      "45 19 * * *"   # 19:45
advisor-medici:      "0 20 * * *"    # 20:00
advisor-machiavelli: "15 20 * * *"   # 20:15
advisor-sun-tzu:     "30 20 * * *"   # 20:30
```

Each CronJob runs the same image with a different `ADVISOR_NAME` env var.

### 3.2 Morning Briefing Roundtable

The morning briefing (`hal-briefing morning`) is separate from advisor sessions. It runs at 06:00 and gathers data from all halos modules, then synthesises a composite message. This should be its own CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: briefing-morning
  namespace: halo-advisors
spec:
  schedule: "0 6 * * *"
  timeZone: "Europe/London"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: briefing
              image: ghcr.io/rickhallett/halo-advisor:v0.1.0
              command: ["uv", "run", "hal-briefing", "morning"]
              envFrom:
                - secretRef:
                    name: halo-api-keys
              volumeMounts:
                - name: halo-store
                  mountPath: /opt/halo/store
                  readOnly: true
                - name: advisor-config
                  mountPath: /opt/halo/briefings.yaml
                  subPath: briefings.yaml
          volumes:
            - name: halo-store
              persistentVolumeClaim:
                claimName: halo-store
            - name: advisor-config
              configMap:
                name: advisor-config
          restartPolicy: OnFailure
```

### 3.3 Evening Council Sequence

The evening session (19:45-20:30) is intentionally sequential: Seneca assesses the day, Medici costs it, Machiavelli finds blind spots, Sun Tzu plans tomorrow. They don't read each other's output — the sequence is for Kai's benefit, not inter-advisor communication.

No orchestration beyond cron staggering is needed. The 15-minute gaps are sufficient.

### 3.4 Plutarch (Dramaturg)

Plutarch reads all other advisors' profiles. It doesn't have its own profile — it synthesises. Plutarch should run as a periodic CronJob (e.g., weekly) or on-demand via a manual Job trigger. It needs ReadOnly access to all advisor profiles on the PVC.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: advisor-plutarch
  namespace: halo-advisors
spec:
  schedule: "0 21 * * 0"  # Sunday 21:00 — weekly roundtable synthesis
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: plutarch
              image: ghcr.io/rickhallett/halo-advisor:v0.1.0
              command: ["uv", "run", "python", "-m", "halos.advisors.run"]
              args: ["--advisor", "plutarch"]
              volumeMounts:
                - name: advisor-profiles
                  mountPath: /opt/halo/data/advisors
                  readOnly: true
```

---

## 4. Data Layer

### 4.1 trackctl SQLite

Six SQLite databases in `store/track_*.db`. Advisors read these for context (Musashi reads `track_movement.db` and `track_zazen.db`; Socrates reads `track_study-*.db`).

**Problem:** Data is written by the Mac Mini (Kai logs via `trackctl add` locally). Pods only read.

**Options:**
| Option | Pros | Cons |
|--------|------|------|
| Rsync to PVC | Simple, unidirectional | Stale data (up to sync interval) |
| Litestream replication | Real-time, WAL-based | Another daemon on Mac Mini |
| PostgreSQL migration | Proper multi-reader, no sync | Large refactor of trackctl |
| SQLite over NFS | No sync needed | NFS + SQLite = corruption risk |

**Recommendation:** Litestream for Phase 1. It replicates SQLite WAL to S3-compatible storage (Vultr Object Storage). A sidecar or init container in each pod restores from Litestream before the advisor runs. Latency: seconds. Complexity: low. No code changes to trackctl.

```yaml
# Litestream sidecar pattern (init container restores, advisor reads)
initContainers:
  - name: restore-store
    image: litestream/litestream:0.3
    command: ["litestream", "restore", "-if-db-not-exists", "-if-replica-exists",
              "-o", "/opt/halo/store/track_movement.db",
              "s3://halo-litestream/track_movement.db"]
    env:
      - name: LITESTREAM_ACCESS_KEY_ID
        valueFrom:
          secretKeyRef:
            name: litestream-s3
            key: access-key
      - name: LITESTREAM_SECRET_ACCESS_KEY
        valueFrom:
          secretKeyRef:
            name: litestream-s3
            key: secret-key
    volumeMounts:
      - name: halo-store
        mountPath: /opt/halo/store
```

On the Mac Mini side, run Litestream as a background process replicating all `store/*.db` files to Vultr Object Storage.

**Phase 2 option:** If write-back is needed (advisors updating profiles via trackctl), migrate to PostgreSQL. But for now, advisors are read-only consumers of trackctl data.

### 4.2 memctl Data

`memory/` directory with markdown notes + `memory/INDEX.md`. Read-only for advisors. Same Litestream/rsync pattern. Or: bake `memory/` into the image and rebuild on changes (it changes infrequently).

### 4.3 nightctl Queue/Items

`queue/items/*.yaml` files and `store/jobs.db`. Read by the briefing system for backlog context. Same sync pattern as trackctl.

### 4.4 git-pulse

`scripts/git-pulse.sh` walks `~/code/*/` directories on the Mac Mini counting commits. This cannot run in a cluster pod — there are no repos there.

**Options:**
1. **Cron on Mac Mini → API endpoint.** Mac Mini runs git-pulse on schedule, writes result to a known location. Pod fetches it.
2. **Cron on Mac Mini → S3/ConfigMap.** Write git-pulse output to Vultr Object Storage. Pod reads it.
3. **Git-pulse as a separate CronJob on Mac Mini** that pushes results to a lightweight API or Redis.
4. **Accept empty git-pulse in cluster.** The briefing still works — git-pulse returns empty string gracefully.

**Recommendation for Phase 1:** Option 4. git-pulse is informational, not critical. The gather function already handles `""` gracefully. For Phase 2, Option 2 — a Mac Mini cron writes `git-pulse.json` to Vultr Object Storage, advisor pods read it.

### 4.5 Journal and Mail

`store/journal.db` — read by advisors for qualitative context. Same Litestream replication.
`store/mail.db` — not currently used by advisors. Skip.

---

## 5. Networking & Delivery

### 5.1 Telegram Bot Token Management

Single token: `HERMES_BOT_TOKEN`. Stored in `halo-api-keys` Secret. All advisors share the same bot identity (Hermes, @maclaw00_bot).

**Future consideration:** Per-advisor bot identities. Each advisor gets its own Telegram bot (e.g., @musashi_halo_bot). This creates visual separation in the chat. Not for Phase 1.

### 5.2 Advisor → Telegram Delivery Path

Direct HTTPS to `api.telegram.org`. No ingress needed. No service mesh. Each pod makes an outbound HTTPS call. Vultr VKE provides egress by default.

The IPC fallback path (writing JSON files for gateway pickup) is irrelevant in k8s — there's no gateway watching the filesystem. Remove IPC fallback from the containerised code path or leave it as a no-op.

### 5.3 Inter-Advisor Communication

Currently none. Advisors don't read each other's outputs. Plutarch reads all profiles but doesn't write. The evening sequence is temporal, not causal — Seneca doesn't feed Medici.

If inter-advisor communication is desired in future: a shared Redis or NATS instance for event pub/sub. Not needed for Phase 1.

### 5.4 Mac Mini ↔ Cluster Data Sync

Unidirectional: Mac Mini → Cluster. Data flows:

```
Mac Mini                          Vultr VKE
┌─────────────┐                   ┌──────────────────┐
│ store/*.db  │──Litestream──────▶│ Vultr Obj Storage │
│ queue/items │──rsync/cron──────▶│                    │
│ memory/     │──rsync/cron──────▶│                    │
│ git-pulse   │──(Phase 2)───────▶│                    │
└─────────────┘                   └──────┬───────────┘
                                         │ init containers
                                         ▼
                                  ┌──────────────────┐
                                  │  Advisor Pods     │
                                  │  (read-only)      │
                                  └──────────────────┘
```

Profile write-back (advisor updating its own profile.md):

```
Advisor Pod ──writes──▶ PVC (advisor-profiles)
                           │
                           ▼
Mac Mini ◀──rsync/cron── (manual or automated pull)
```

Profile updates are the only write path from cluster to Mac Mini. For Phase 1, this can be a manual `kubectl cp` or rsync pull. For Phase 2, bidirectional Syncthing or a git-based workflow (advisor commits to a branch, Mac Mini pulls).

---

## 6. Advisor Runner Module

The current briefing system (`halos/briefings/`) handles the roundtable morning/evening briefings. Individual advisor sessions are run by Hermes (external). For k8s, we need a lightweight advisor runner that:

1. Loads persona + profile
2. Gathers domain-specific data (reusing halos tooling)
3. Constructs advisor-specific prompt
4. Calls Anthropic API
5. Delivers to Telegram
6. Updates profile if needed

This is a new module: `halos/advisors/run.py`.

```python
# halos/advisors/run.py (sketch — not production code)
"""Advisor session runner for containerised execution."""
import os
import sys
from pathlib import Path

import anthropic
import httpx

def run_advisor(name: str):
    base = Path(os.environ.get("HALO_ROOT", "/opt/halo"))
    persona = (base / "data" / "advisors" / name / "persona.md").read_text()
    profile_path = base / "data" / "advisors" / name / "profile.md"
    profile = profile_path.read_text() if profile_path.exists() else ""

    # Gather domain data using existing halos tooling
    context = gather_for_advisor(name, base)

    # Synthesise via Anthropic API (strategy 3 only — no CLI, no OAuth)
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    response = client.messages.create(
        model=os.environ.get("ADVISOR_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=1024,
        system=persona,
        messages=[{
            "role": "user",
            "content": f"## Profile\n{profile}\n\n## Current Data\n{context}\n\n"
                       f"Deliver your daily message."
        }],
    )
    text = response.content[0].text

    # Deliver to Telegram
    token = os.environ["HERMES_BOT_TOKEN"]
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "5967394003")
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=15,
    )
    if not r.json().get("ok"):
        print(f"DELIVERY FAILED: {r.text}", file=sys.stderr)
        sys.exit(1)

    # Emit metrics
    emit_metrics(name, response.usage, success=True)
```

**Unknown:** How do current Hermes advisor sessions work exactly? The cronjob invocation command, prompt construction, and profile update logic need to be extracted from Hermes configuration. This spec assumes we can replicate it in a standalone module. If Hermes provides features (conversation memory, tool use, multi-turn) that the standalone runner can't, we may need to run Hermes inside the advisor pod instead.

---

## 7. Observability

### 7.1 Health Checks

CronJobs don't have liveness/readiness probes (they run to completion). Health is measured by:
- Job completion status (succeeded/failed)
- Job duration
- Time since last successful run

For the briefing morning CronJob (most critical), add a separate watchdog:

```yaml
# k8s/monitoring/cronjob-watchdog.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: advisor-watchdog
  namespace: halo-advisors
spec:
  schedule: "30 7 * * *"  # 30min after Musashi should have fired
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: watchdog
              image: bitnami/kubectl:latest
              command: ["/bin/sh", "-c"]
              args:
                - |
                  # Check if Musashi's last job succeeded
                  LAST=$(kubectl get jobs -n halo-advisors \
                    -l halo/advisor=musashi \
                    --sort-by=.status.startTime \
                    -o jsonpath='{.items[-1].status.succeeded}')
                  if [ "$LAST" != "1" ]; then
                    # Alert via Telegram
                    curl -s -X POST \
                      "https://api.telegram.org/bot${HERMES_BOT_TOKEN}/sendMessage" \
                      -d "chat_id=${CHAT_ID}&text=⚠️ Musashi failed to deliver this morning."
                  fi
```

### 7.2 Prometheus Metrics

Each advisor pod should expose metrics before exiting. Since CronJobs are short-lived, use the Pushgateway pattern:

```yaml
# k8s/monitoring/pushgateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus-pushgateway
  namespace: halo-advisors
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pushgateway
  template:
    spec:
      containers:
        - name: pushgateway
          image: prom/pushgateway:v1.9.0
          ports:
            - containerPort: 9091
---
apiVersion: v1
kind: Service
metadata:
  name: pushgateway
  namespace: halo-advisors
spec:
  selector:
    app: pushgateway
  ports:
    - port: 9091
```

Metrics pushed by each advisor run:

```
# HELP halo_advisor_run_duration_seconds Time taken for advisor session
# TYPE halo_advisor_run_duration_seconds gauge
halo_advisor_run_duration_seconds{advisor="musashi"} 12.3

# HELP halo_advisor_delivery_success Whether Telegram delivery succeeded
# TYPE halo_advisor_delivery_success gauge
halo_advisor_delivery_success{advisor="musashi"} 1

# HELP halo_advisor_llm_tokens_used Total tokens used in synthesis
# TYPE halo_advisor_llm_tokens_used gauge
halo_advisor_llm_tokens_used{advisor="musashi",type="input"} 2340
halo_advisor_llm_tokens_used{advisor="musashi",type="output"} 450

# HELP halo_advisor_llm_latency_seconds LLM API call duration
# TYPE halo_advisor_llm_latency_seconds gauge
halo_advisor_llm_latency_seconds{advisor="musashi"} 8.7

# HELP halo_advisor_last_success_timestamp Unix timestamp of last successful run
# TYPE halo_advisor_last_success_timestamp gauge
halo_advisor_last_success_timestamp{advisor="musashi"} 1743850800
```

### 7.3 Grafana Dashboard

A single "Halo Advisors" dashboard with:
- **Row 1:** Advisor status grid — green/red per advisor, based on `halo_advisor_last_success_timestamp` staleness
- **Row 2:** Delivery success rate over 7 days (per advisor)
- **Row 3:** LLM token usage by advisor (bar chart, daily)
- **Row 4:** LLM latency p50/p95 by advisor
- **Row 5:** Job duration trends

This is standard Grafana JSON model, provisioned via ConfigMap or Grafana operator.

### 7.4 Alerting

```yaml
# k8s/monitoring/alerting-rules.yaml (PrometheusRule CRD)
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: halo-advisor-alerts
  namespace: halo-advisors
spec:
  groups:
    - name: halo-advisors
      rules:
        - alert: AdvisorMissedSchedule
          expr: |
            time() - halo_advisor_last_success_timestamp > 90000
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Advisor {{ $labels.advisor }} hasn't run in 25+ hours"

        - alert: AdvisorDeliveryFailure
          expr: |
            halo_advisor_delivery_success == 0
          for: 0m
          labels:
            severity: critical
          annotations:
            summary: "Advisor {{ $labels.advisor }} failed to deliver to Telegram"

        - alert: AdvisorHighLatency
          expr: |
            halo_advisor_llm_latency_seconds > 60
          for: 0m
          labels:
            severity: warning
          annotations:
            summary: "Advisor {{ $labels.advisor }} LLM call took >60s"
```

Alert delivery: Alertmanager → Telegram webhook (same bot, same chat). Dogfooding.

---

## 8. CI/CD

### 8.1 Image Build

Extend existing `build-image.yml` workflow:

```yaml
# .github/workflows/build-advisor-image.yml
name: Build Advisor Image
on:
  push:
    tags: ['advisor-v*']
    paths:
      - 'halos/**'
      - 'data/advisors/**'
      - 'Dockerfile.advisor'
      - 'pyproject.toml'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          exit-code: 1
          severity: CRITICAL

      - uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.advisor
          push: true
          tags: ghcr.io/rickhallett/halo-advisor:${{ github.ref_name }}
```

### 8.2 Deployment

Kustomize-based with overlays:

```
k8s/
  base/
    kustomization.yaml
    namespace.yaml
    configmap-advisors.yaml
    secret-api-keys.yaml      # sealed-secrets or external-secrets
    pvc-profiles.yaml
    pvc-store.yaml
    cronjob-musashi.yaml
    cronjob-seneca.yaml
    cronjob-socrates.yaml
    cronjob-sun-tzu.yaml
    cronjob-machiavelli.yaml
    cronjob-medici.yaml
    cronjob-briefing-morning.yaml
    cronjob-briefing-nightly.yaml
  overlays/
    dev/
      kustomization.yaml      # dry-run mode, --no-send
    prod/
      kustomization.yaml      # real delivery
```

Deploy via:
```bash
kubectl apply -k k8s/overlays/prod
```

Or via GitHub Actions:
```yaml
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure kubectl
        run: |
          echo "${{ secrets.VULTR_KUBECONFIG }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
      - run: |
          cd k8s/overlays/prod
          kustomize edit set image ghcr.io/rickhallett/halo-advisor:${{ github.ref_name }}
          kubectl apply -k .
```

### 8.3 Rolling Updates for Persona/Prompt Changes

Persona files are baked into the image. To update a persona without a full rebuild:

1. **ConfigMap overlay (preferred for iteration):** Mount persona files via ConfigMap. Override the baked-in version.
2. **Image rebuild (preferred for releases):** Change persona, tag, build, deploy.

For canary testing a prompt change: run the advisor CronJob manually with `--no-send`, inspect output, then promote.

```bash
# Test a persona change
kubectl create job musashi-test --from=cronjob/advisor-musashi \
  -n halo-advisors -- uv run python -m halos.advisors.run --advisor musashi --no-send
kubectl logs job/musashi-test -n halo-advisors
```

### 8.4 Integration Test

```yaml
# .github/workflows/advisor-integration.yml
name: Advisor Integration Test
on:
  workflow_dispatch:
  schedule:
    - cron: '0 12 * * 1'  # Weekly Monday noon

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3

      - name: Run advisor in dry-run mode
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          uv sync
          uv run python -m halos.advisors.run --advisor musashi --no-send > output.txt

      - name: Validate output
        run: |
          # Output should be non-empty, contain no error markers, be under 2000 chars
          test -s output.txt
          ! grep -qi "error\|failed\|traceback" output.txt
          CHARS=$(wc -c < output.txt)
          test "$CHARS" -lt 2500
```

---

## 9. Security & Red Team Resilience

### 9.1 Network Policies

Advisor pods need exactly one egress path: HTTPS to `api.telegram.org` and `api.anthropic.com`. Lock everything else down.

```yaml
# k8s/base/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: advisor-egress
  namespace: halo-advisors
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: advisor
  policyTypes:
    - Egress
    - Ingress
  ingress: []  # No inbound traffic
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
    - to:                    # DNS resolution
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

**Note:** Locking egress to specific IP ranges for Telegram/Anthropic is fragile (CDN IPs change). Allow port 443 egress broadly, rely on application-level controls.

### 9.2 Pod Security Standards

```yaml
# Applied via namespace label
apiVersion: v1
kind: Namespace
metadata:
  name: halo-advisors
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

All pods run as non-root (UID 1000), with read-only root filesystem where possible, no privilege escalation.

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop: ["ALL"]
```

### 9.3 Secret Rotation

- `ANTHROPIC_API_KEY`: Rotate quarterly. Use external-secrets operator synced from Vultr/AWS Secrets Manager.
- `HERMES_BOT_TOKEN`: Telegram bot tokens don't expire, but can be revoked via @BotFather. Store in external-secrets.
- Litestream S3 credentials: Rotate via IAM policy.

For Phase 1: plain Kubernetes Secrets with `kubectl create secret`. For Phase 2: sealed-secrets or external-secrets-operator.

### 9.4 Attack Surface Analysis

| Vector | Risk | Mitigation |
|--------|------|------------|
| Compromised advisor pod → API key exfiltration | High | Network policies limit egress; per-advisor API keys (future) limit blast radius |
| Prompt injection via profile.md | Medium | Profiles are written by the advisor itself (LLM output). An attacker with PVC write access could inject instructions. Mitigation: read-only profiles in production, write via controlled pipeline |
| Supply chain (base image, uv deps) | Medium | Trivy scan in CI, pinned image digests, `uv.lock` for reproducible installs |
| Telegram token leak | High | Token in k8s Secret, not in image. Rotation procedure documented |
| SQLite corruption on shared PVC | Medium | WAL mode enforced; CronJobs don't overlap (Forbid policy) |
| Cluster-level compromise | Critical | Standard k8s hardening: RBAC, network policies, pod security standards, audit logging |
| Model hallucination / persona drift | Low | Persona files are immutable (baked or ConfigMap). Profile drift is by design — monitor via git-diff on profile pulls |

---

## 10. Migration Path

### Phase 1: Musashi as Pilot (Week 1-2)

**Goal:** Single advisor running in VKE, delivering to Telegram, alongside Mac Mini execution.

Steps:
1. Create `Dockerfile.advisor` (section 2.1)
2. Create `halos/advisors/run.py` runner module
3. Build and push image to GHCR
4. Deploy to VKE: namespace, Secret, ConfigMap, PVC, CronJob for Musashi
5. Run manually (`kubectl create job`) and validate output
6. Enable cron schedule
7. Disable Musashi's Mac Mini cronjob
8. Monitor for 1 week

**Success criteria:** Musashi delivers to Telegram on schedule for 7 consecutive days. LLM synthesis works. Delivery confirmed. No Mac Mini dependency.

**Known gap:** trackctl data won't be available unless Litestream is set up. Accept degraded data for Phase 1 (advisors work without trackctl — they just lose quantitative context).

### Phase 2: All Advisors Deployed (Week 3-4)

**Goal:** All 7 advisors + morning briefing running in VKE. Mac Mini remains primary for data collection.

Steps:
1. Deploy remaining CronJobs (Seneca, Socrates, Sun Tzu, Machiavelli, Medici, Bankei)
2. Deploy morning briefing CronJob
3. Set up Litestream replication from Mac Mini → Vultr Object Storage
4. Add init containers for store restoration
5. Disable Mac Mini advisor cronjobs one at a time
6. Deploy Pushgateway + Prometheus scrape config
7. Build Grafana dashboard

**Success criteria:** All advisors fire on schedule from VKE. Grafana shows green. Mac Mini cronjobs disabled.

### Phase 3: Cluster Primary (Week 5-6)

**Goal:** VKE is the primary execution environment. Mac Mini is data source only.

Steps:
1. Set up profile write-back pipeline (PVC → git → Mac Mini)
2. Deploy watchdog alerting
3. Set up git-pulse sync (Mac Mini → Object Storage)
4. Add network policies
5. Formal cutover: Mac Mini advisor cronjobs removed, not just disabled

### Phase 4: Full Independence + Hardening (Week 7-8)

**Goal:** System is production-grade. Red team tested.

Steps:
1. External-secrets operator for secret management
2. Pod security standards enforced
3. Integration test suite in CI
4. Chaos testing: kill advisor pods, corrupt PVC, revoke API key, network partition
5. Document runbooks for common failure modes
6. Profile update cycle fully automated
7. Plutarch weekly synthesis deployed

---

## 11. Technical Debt Inventory

### 11.1 Existing Debt (from CLAUDE.md)

| ID | Area | Impact on Migration |
|----|------|-------------------|
| TD-1 | journalctl uses `claude` CLI subprocess | **Blocks containerisation.** Must be replaced with Anthropic SDK direct call before advisors that use journalctl window synthesis can run in containers. |
| TD-3 | No HTTP health check sidecar | Irrelevant for CronJobs (they exit). Relevant if we ever move to long-running pods. |
| TD-4 | Dockerfile uses pip, violates uv-only policy | **Fixed by this migration** — `Dockerfile.advisor` uses uv exclusively. |
| TD-5 | No automated integration test for container build | Addressed in section 8.4. |

### 11.2 New Debt Created by This Migration

| ID | Area | Severity | Description |
|----|------|----------|-------------|
| TD-K1 | Auth | Medium | OAuth cascade (strategies 1-2 in synthesise.py) is dead code in containers. The advisor runner should use Anthropic SDK directly, not inherit the multi-strategy cascade. Leaving the cascade in means confusing failure modes when OAuth refresh code runs and fails in a container. |
| TD-K2 | Data sync | Medium | Litestream replication is unidirectional. Profile write-back has no automated pipeline in Phase 1-2. Manual `kubectl cp` is the gap. |
| TD-K3 | git-pulse | Low | git-pulse is unavailable in cluster. Advisors lose commit activity context. Not critical but lossy. |
| TD-K4 | Model staleness | Medium | `model: "claude-sonnet-4-20250514"` is hardcoded in briefings.yaml and baked into ConfigMap. Model ID rotation requires ConfigMap update + CronJob restart. Should be an env var. |
| TD-K5 | Advisor runner | High | `halos/advisors/run.py` doesn't exist yet. This spec assumes it can be built by extracting logic from Hermes advisor invocation. If Hermes provides irreplaceable features (multi-turn conversation memory, tool use during session), the runner becomes much more complex. **This is the biggest unknown.** |
| TD-K6 | Profile concurrency | Low | If two advisors run simultaneously and both write to the profiles PVC, there's no locking mechanism. Currently prevented by schedule stagger, but fragile. |
| TD-K7 | IPC fallback | Low | `deliver.py` still writes IPC files on Telegram failure. In a container with emptyDir, these files vanish when the pod exits. Should be replaced with a proper dead letter queue or at minimum logged. |

### 11.3 Open Questions

1. **How does Hermes invoke advisors?** The cron command, prompt structure, and tool-use capabilities during a session need to be documented. The advisor runner is the critical path.
2. **Vultr VKE timezone support.** CronJob `timeZone` field requires the `CronJobTimeZone` feature gate (GA since k8s 1.27). Verify Vultr VKE version.
3. **Vultr block storage RWX.** Confirm whether Vultr supports ReadWriteMany PVCs or if we need NFS.
4. **Claude Max subscription in containers.** If the current auth relies on Claude Max (subscription, not API key), containers can't use it. API key billing is separate. Confirm which billing path applies.
5. **Bankei's schedule.** INDEX.md doesn't include Bankei in the cron schedule. Is it on-demand only?

---

## 12. Cost Estimate

| Resource | Monthly Cost (Vultr) |
|----------|---------------------|
| VKE worker node (1x, already exists) | ~$12-24 (shared with gateway) |
| Block storage PVC (5Gi + 1Gi) | ~$1 |
| Object storage (Litestream) | ~$5 |
| Anthropic API (7 advisors × 30 days × ~3K tokens) | ~$3-5 |
| **Total incremental** | **~$10-30/month** |

The advisors are cheap. They're short CronJobs using minimal compute. The LLM cost is the dominant factor, and it's modest at current token volumes.

---

## Appendix A: Full CronJob Template (Kustomize Base)

```yaml
# k8s/base/cronjob-template.yaml
# Use with kustomize namePrefix or patches per advisor
apiVersion: batch/v1
kind: CronJob
metadata:
  name: advisor-TEMPLATE
  namespace: halo-advisors
  labels:
    app.kubernetes.io/name: advisor-TEMPLATE
    app.kubernetes.io/component: advisor
    app.kubernetes.io/part-of: halo
spec:
  schedule: "REPLACE"
  timeZone: "Europe/London"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  startingDeadlineSeconds: 300
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 300
      template:
        metadata:
          labels:
            app.kubernetes.io/component: advisor
            halo/advisor: TEMPLATE
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          initContainers:
            - name: restore-store
              image: litestream/litestream:0.3
              command: ["sh", "-c"]
              args:
                - |
                  for db in track_movement track_zazen track_project track_study-neetcode track_study-crafters track_study-source journal jobs messages; do
                    litestream restore -if-db-not-exists -if-replica-exists \
                      -o /opt/halo/store/${db}.db \
                      s3://halo-litestream/${db}.db 2>/dev/null || true
                  done
              envFrom:
                - secretRef:
                    name: litestream-s3
              volumeMounts:
                - name: halo-store
                  mountPath: /opt/halo/store
          containers:
            - name: advisor
              image: ghcr.io/rickhallett/halo-advisor:latest
              command: ["uv", "run", "python", "-m", "halos.advisors.run"]
              args: ["--advisor", "TEMPLATE"]
              resources:
                requests:
                  cpu: 100m
                  memory: 256Mi
                limits:
                  cpu: 500m
                  memory: 512Mi
              env:
                - name: ADVISOR_NAME
                  value: "TEMPLATE"
                - name: PUSHGATEWAY_URL
                  value: "http://pushgateway.halo-advisors:9091"
                - name: TZ
                  value: "Europe/London"
              envFrom:
                - secretRef:
                    name: halo-api-keys
              securityContext:
                allowPrivilegeEscalation: false
                readOnlyRootFilesystem: false  # uv needs to write .venv cache
                capabilities:
                  drop: ["ALL"]
              volumeMounts:
                - name: advisor-profiles
                  mountPath: /opt/halo/data/advisors
                - name: halo-store
                  mountPath: /opt/halo/store
                  readOnly: true
                - name: advisor-config
                  mountPath: /opt/halo/briefings.yaml
                  subPath: briefings.yaml
          volumes:
            - name: advisor-profiles
              persistentVolumeClaim:
                claimName: advisor-profiles
            - name: halo-store
              persistentVolumeClaim:
                claimName: halo-store
            - name: advisor-config
              configMap:
                name: advisor-config
```

---

## Appendix B: Advisor Domain → Data Mapping

| Advisor | trackctl domains read | Other data |
|---------|----------------------|------------|
| Musashi | movement, zazen | journalctl window |
| Seneca | all (productivity audit) | nightctl items, activity |
| Socrates | study-neetcode, study-crafters, study-source | memctl corpus |
| Sun Tzu | project | nightctl items (strategy) |
| Machiavelli | none directly | all profiles (reads others) |
| Medici | none directly | nightctl (cost), activity |
| Bankei | zazen | journalctl window |
| Plutarch | none | all advisor profiles |
