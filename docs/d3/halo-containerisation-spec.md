---
title: "Halo Containerisation & Multi-Tenant Deployment Spec"
category: spec
status: archived
created: 2026-04-04
---

# Halo Containerisation & Multi-Tenant Deployment

## 1. Problem Statement

Halo is a personal agentic system running as a bare-metal process on macOS (`~/.hermes/`). To offer personalised Halo instances to clients (starting with Aura), we need:

1. A container image that packages the full Hermes gateway + halos ecosystem
2. Per-client configuration that customises the image without code changes
3. Infrastructure automation (Terraform + ArgoCD) for repeatable deployment
4. Cost isolation and observability per client

The design must survive the transition from "second process on Kai's Mac" to "isolated K8s deployment per client" without architectural rewrites.

## 2. Current State

### 2.1 Hermes Gateway

- **Source**: `~/.hermes/hermes-agent/` (Nous Research, MIT-licensed)
- **Runtime state**: `~/.hermes/` (config.yaml, .env, sessions/, memories/, state.db, logs/)
- **Entry point**: `hermes --gateway` (runs `gateway/run.py` → `GatewayRunner`)
- **Existing Dockerfile**: `~/.hermes/hermes-agent/Dockerfile` — Debian 13.4, installs hermes-agent[all], npm deps, Playwright/Chromium
- **Existing entrypoint**: `docker/entrypoint.sh` — bootstraps `$HERMES_HOME` volume with .env, config.yaml, SOUL.md, syncs skills
- **Config injection**: `HERMES_HOME` env var points to the data volume. All config loaded from `$HERMES_HOME/config.yaml` and `$HERMES_HOME/.env`
- **System prompt**: `HERMES_EPHEMERAL_SYSTEM_PROMPT` env var or `agent.system_prompt` in config.yaml
- **User restriction**: `TELEGRAM_ALLOWED_USERS` env var (comma-separated Telegram user IDs)
- **Image size**: ~2GB+ (Debian + Python + Node + Chromium)

### 2.2 Halos Ecosystem

- **Source**: `/Users/mrkai/code/halo/halos/` (Python package, uv-managed)
- **Modules**: memctl, nightctl, trackctl, briefings, cronctl, mailctl, dashctl, watchctl, journalctl, etc.
- **Data**: `store/` directory (SQLite databases per module)
- **Memory**: `memory/` directory (markdown notes, INDEX.md)
- **Config**: Various YAML files in repo root (memctl.yaml, watchctl.yaml, etc.)

### 2.3 Jeany Infrastructure (reusable patterns)

- **Terraform**: Vultr VKE cluster provisioning (`infra/terraform/`)
- **Kustomize**: Base + overlay pattern (`infra/k8s/base/`, `infra/k8s/overlays/`)
- **ArgoCD**: GitOps deployment with ingress
- **Observability**: Prometheus, Grafana, Loki, Tempo (docker-compose profiles)
- **Provider**: Vultr, London region, `vc2-2c-4gb` plan (~$24/mo per node)

## 3. Architecture

### 3.1 Image Strategy: Fat Image, Thin Config

One container image contains the entire stack. Client repos contain only configuration.

```
┌─────────────────────────────────────────────┐
│  ghcr.io/rickhallett/halo:v1.0.0            │
│                                             │
│  Layer 1: Debian 13 + Python 3.11 + Node    │
│  Layer 2: hermes-agent[all,messaging,cron]  │
│  Layer 3: halos package (all modules)       │
│  Layer 4: Playwright + Chromium             │
│  Layer 5: Entrypoint + defaults             │
└─────────────────────────────────────────────┘
```

### 3.2 Repo Topology

```
halo/                          (this repo — product source)
├── Dockerfile                 Build the halo image
├── docker/
│   ├── entrypoint.sh          Container bootstrap
│   └── defaults/              Default config templates
│       ├── config.yaml
│       └── .env.example
├── halos/                     Python package (all modules)
├── infra/
│   └── base/                  Shared K8s base manifests
└── ...

halo-deploy/                   (thin client template — github.com/rickhallett/halo-deploy)
├── config/
│   ├── .env.example           Template — copy to .env, never commit .env
│   ├── config.yaml            Model, session reset, personality config
│   ├── system-prompt.md       Ephemeral system prompt
│   └── SOUL.md                Agent personality (persistent)
├── infra/
│   ├── terraform/
│   │   ├── main.tf            Vultr VKE (or shared cluster)
│   │   └── terraform.tfvars.example
│   └── k8s/
│       ├── kustomization.yaml References halo/infra/k8s/base (remote)
│       ├── namespace.yaml
│       ├── configmap.yaml     ConfigMaps from config/
│       └── sealed-secret.yaml Bitnami Sealed Secrets (safe to commit)
├── argocd-app.yaml            ArgoCD Application manifest
└── README.md
```

### 3.3 Configuration Injection

The container expects `$HERMES_HOME` to contain all runtime state and config. In K8s, this is assembled from multiple sources:

| Source | Mount point | Mode | Contains |
|---|---|---|---|
| ConfigMap `halo-config` | `$HERMES_HOME/config.yaml` | read-only (subPath) | Model, session policy, personality |
| ConfigMap `halo-prompt` | `$HERMES_HOME/system-prompt.md` | read-only (subPath) | Ephemeral system prompt (read by entrypoint into env var) |
| ConfigMap `halo-soul` | `$HERMES_HOME/SOUL.md` | read-only (subPath) | Persistent agent personality |
| Secret `halo-secrets` | `$HERMES_HOME/.env` | read-only (subPath, 0400) | Bot token, API keys, allowed users. **File mount, not envFrom** — env vars are accessible to any child process via `os.environ`/`/proc/self/environ`. File mount with restrictive permissions is the narrower exposure surface. |
| PersistentVolumeClaim `halo-data` | `$HERMES_HOME/sessions/`, `memories/`, `store/`, `logs/` | read-write | Mutable runtime state |
| ConfigMap `halo-module-config` | `$HERMES_HOME/memctl.yaml`, `$HERMES_HOME/watchctl.yaml`, etc. | read-only (subPath, optional) | Halos module configuration (per-client). Not all clients use all modules. |

The entrypoint reads `system-prompt.md` via a Python subprocess (not shell expansion — see §5) and exports it as `HERMES_EPHEMERAL_SYSTEM_PROMPT` before launching the gateway.

**trackctl domains**: Domain definitions are Python files (`domains/<name>.py`) that must be importable. These are **baked into the image** in a `domains/` directory under the halos package. Per-client activation is controlled by `config.yaml` (list of enabled domains), not by mounting Python files via ConfigMap. New domains require an image rebuild. This is acceptable at current scale — domain definitions change rarely and are product code, not client config.

### 3.4 What Varies Per Client

| Parameter | Where configured | Example (Aura) |
|---|---|---|
| Telegram bot token | `.env` → Secret | `BOT_TOKEN=7123456:AAF...` |
| Allowed Telegram users | `.env` → Secret | `TELEGRAM_ALLOWED_USERS=987654321` |
| System prompt | `system-prompt.md` → ConfigMap | Aura's onboarding-derived prompt |
| SOUL.md | ConfigMap | Her agent's persistent personality |
| Model + provider | `config.yaml` → ConfigMap | `claude-sonnet-4-20250514` (cost-conscious) |
| Session reset policy | `config.yaml` → ConfigMap | idle: 120 min, daily reset at 03:00 |
| Briefing schedule | `config.yaml` → ConfigMap | Morning 08:00, no nightly |
| trackctl domains | `config.yaml` → ConfigMap (activation list); domain code baked into image | `practice-hours`, `content-creation` |
| Advisor personas | `advisors/` → ConfigMap (markdown files, not executable) | Her roundtable (Dao-aligned, not Musashi) |
| API keys | `.env` → Secret | Her Anthropic key (or yours, billed to her) |
| Resource limits | `deployment.yaml` | 512Mi RAM, 0.5 CPU (lighter than yours) |
| Cost ceiling | `.env` → Secret | `COST_CEILING_USD=50` per month |

### 3.5 What Does NOT Vary

- Container image (same tag across all clients)
- Module code (memctl, nightctl, trackctl, etc.)
- Gateway code (run.py, config.py, session.py)
- Memory system mechanics (memctl governance, note format)
- Entrypoint script

## 4. Dockerfile

```dockerfile
# Pin base image by digest for reproducibility. Update digest when upgrading Debian.
# To find current digest: docker pull debian:13.4 && docker inspect --format='{{index .RepoDigests 0}}' debian:13.4
FROM debian:13.4@sha256:<PIN_DIGEST_HERE>

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    nodejs npm \
    ripgrep ffmpeg gcc python3-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with explicit UID/GID 1000 to match K8s securityContext.
# K8s deployment sets runAsUser: 1000, runAsGroup: 1000, fsGroup: 1000.
RUN groupadd -g 1000 hermes && useradd -u 1000 -g 1000 -m -d /home/hermes hermes

# Create venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Validate vendor directory is populated (fail fast if submodule not checked out)
COPY vendor/hermes-agent /opt/hermes
RUN test -f /opt/hermes/pyproject.toml || { echo "ERROR: vendor/hermes-agent is empty — check git submodule init" >&2; exit 1; }
WORKDIR /opt/hermes
RUN pip install ".[all,messaging,cron]"
RUN npm install

# Install halos modules into the same venv (non-editable for production)
COPY halos/ /opt/halos/halos/
COPY pyproject.toml /opt/halos/
WORKDIR /opt/halos
RUN pip install .

# Playwright (optional — skip for lightweight client deploys)
ARG INSTALL_BROWSER=false
RUN if [ "$INSTALL_BROWSER" = "true" ]; then \
      cd /opt/hermes && npx playwright install --with-deps chromium; \
    fi

# Entrypoint and permissions
WORKDIR /opt/hermes
COPY docker/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

# Pre-create data directory with correct ownership
RUN mkdir -p /opt/data && chown -R hermes:hermes /opt/data

ENV HERMES_HOME=/opt/data
VOLUME ["/opt/data"]
USER hermes
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["hermes", "--gateway"]
```

**Design notes:**

- **Single-stage build.** Previous multi-stage was broken (Stage 1 output unused by Stage 2). Single stage is simpler and correct. Build deps (gcc, python3-dev, libffi-dev) remain in the image — acceptable at current scale; revisit multi-stage when image size matters.
- **Non-root user.** `hermes` user created with explicit UID/GID 1000, matching the K8s `securityContext` values. `USER hermes` set before entrypoint.
- **Pinned base image.** Digest-pinned for reproducibility per §9.4. Tag retained for readability.
- **Non-editable install.** `pip install .` (not `-e .`) — production images must not have mutable source paths.
- **Submodule validation.** Build fails fast if `vendor/hermes-agent` is empty (stale submodule, GitHub unavailable during CI).
- **Vendoring.** Hermes source vendored at `vendor/hermes-agent/` (git submodule pointing at `rickhallett/hermes-agent` fork). Halos source copied directly from repo.
- **INSTALL_BROWSER defaults to false.** Chromium stripped from standard client image.

## 5. Entrypoint

```bash
#!/bin/bash
set -e

HERMES_HOME="${HERMES_HOME:-/opt/data}"

# Create mutable directories if not present (PVC may be empty on first run)
mkdir -p "$HERMES_HOME"/{sessions,memories,logs,skills,store,cron,hooks}

# Detect empty PVC (first run or data loss). Attempt restore from S3 backup
# before bootstrapping fresh defaults. If restore fails, proceed with defaults.
if [ ! -f "$HERMES_HOME/state.db" ] && [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    echo "Empty PVC detected. Attempting restore from backup..." >&2
    python3 /opt/hermes/docker/restore-from-s3.py "$BACKUP_S3_BUCKET" "$HERMES_HOME" \
        && echo "Restore successful." >&2 \
        || echo "WARNING: Restore failed. Bootstrapping fresh instance." >&2
fi

# Bootstrap defaults if ConfigMap mounts are absent (local Docker dev only).
# In K8s, ConfigMaps mount config.yaml/system-prompt.md/SOUL.md directly —
# these conditionals will never trigger because the files already exist.
# If a ConfigMap is missing, the pod fails at mount time before this script runs.
[ ! -f "$HERMES_HOME/config.yaml" ] && cp /opt/hermes/docker/defaults/config.yaml "$HERMES_HOME/config.yaml"
[ ! -f "$HERMES_HOME/.env" ] && cp /opt/hermes/docker/defaults/.env.example "$HERMES_HOME/.env"

# Load system prompt safely via Python to avoid shell injection.
# system-prompt.md is client-authored content — it MUST NOT be interpreted by
# the shell. Previous version used $(cat ...) which allows arbitrary code
# execution if the prompt contains backticks, $(), or unbalanced quotes.
if [ -f "$HERMES_HOME/system-prompt.md" ]; then
    HERMES_EPHEMERAL_SYSTEM_PROMPT="$(python3 -c "
import sys, os
with open(os.path.join(os.environ.get('HERMES_HOME', '/opt/data'), 'system-prompt.md'), 'rb') as f:
    sys.stdout.buffer.write(f.read())
")"
    export HERMES_EPHEMERAL_SYSTEM_PROMPT
fi

# Halos modules expect store/ and memory/ relative to cwd.
# Set working directory to HERMES_HOME so all relative paths resolve.
cd "$HERMES_HOME"

# Sync bundled skills from image into data volume (local file copy, no network).
# This copies skill definitions bundled in the image; it does NOT fetch from
# GitHub/PyPI. NetworkPolicy does not need to allow additional egress for this.
if [ -d "/opt/hermes/skills" ]; then
    python3 /opt/hermes/tools/skills_sync.py || echo "WARNING: skills_sync failed — bot will run without bundled skill updates" >&2
fi

# Heartbeat is NOT written by the entrypoint. It MUST be written by the Hermes
# Python process itself (async background task in the event loop). A shell-based
# heartbeat would keep touching the file even if Hermes deadlocks, defeating
# the purpose of the liveness probe.
#
# The gateway must call: Path(os.environ['HERMES_HOME'] / 'heartbeat').touch()
# every 60 seconds from within its asyncio loop. If the loop is blocked, the
# file goes stale, and K8s kills the pod. That's the point.
#
# The startup probe allows up to 5 minutes (initialDelaySeconds=10,
# periodSeconds=10, failureThreshold=30) for the gateway to start and write
# its first heartbeat. No entrypoint touch is needed or wanted — the startup
# probe tolerates the file's absence during init.

exec "$@"
```

## 6. Infrastructure

### 6.1 Shared vs Dedicated Cluster

**Phase 1 (1-3 clients)**: Shared Vultr VKE cluster. Each client gets a namespace. Cost-efficient (~$24/mo for the node, split across clients).

**Phase 2 (4+ clients or isolation requirement)**: Dedicated clusters via Terraform. Each client's `terraform.tfvars` provisions their own VKE. More expensive but eliminates noisy-neighbour risk.

### 6.2 Terraform (shared cluster variant)

```hcl
# infra/terraform/main.tf — in halo repo (shared infra)
resource "vultr_kubernetes" "halo" {
  region          = var.region
  label           = "halo-shared"
  version         = var.k8s_version
  enable_firewall = true

  node_pools {
    label         = "halo-workers"
    plan          = var.node_plan      # vc2-2c-4gb
    node_quantity = var.node_count     # start at 1
    auto_scaler   = true
    min_nodes     = 1
    max_nodes     = 3
  }
}
```

### 6.3 Kustomize Base (in halo repo)

```yaml
# infra/k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - deployment.yaml
  - pvc.yaml
  # No service.yaml — gateway polls Telegram, exposes no HTTP endpoints.
  # If a health-check endpoint is added later, add a Service then.
```

```yaml
# infra/k8s/base/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: halo-data
  annotations:
    # Protect against accidental deletion via ArgoCD prune or kubectl delete.
    # The finalizer prevents the PVC from being deleted until manually removed.
    helm.sh/resource-policy: keep
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: vultr-block-storage-hdd   # Explicit — don't rely on cluster default
  resources:
    requests:
      storage: 5Gi   # SQLite DBs + memories + logs. Monitor via PVC usage alert.
```

```yaml
# infra/k8s/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: halo-gateway
spec:
  replicas: 1
  selector:
    matchLabels:
      app: halo-gateway
  template:
    metadata:
      labels:
        app: halo-gateway
      annotations:
        # Force pod restart when ConfigMap/Secret content changes.
        # Client overlay must set this to a hash of the config content.
        # Example: kustomize configMapGenerator with behavior=merge, or
        # manually: checksum/config: <sha256 of configmap.yaml>
        checksum/config: "MUST_BE_SET_BY_OVERLAY"
    spec:
      securityContext:
        runAsUser: 1000         # Matches Dockerfile: useradd -u 1000
        runAsGroup: 1000        # Matches Dockerfile: groupadd -g 1000
        fsGroup: 1000           # K8s chowns PVC to hermes GID before container starts
      containers:
        - name: gateway
          # Base uses a placeholder tag. Client overlays MUST patch to a pinned
          # version (e.g. ghcr.io/rickhallett/halo:v1.0.0). ArgoCD will reject
          # sync if the image pull fails, but :latest must never reach production.
          image: ghcr.io/rickhallett/halo:MUST_BE_PATCHED_BY_OVERLAY
          # Secrets mounted as a read-only file at $HERMES_HOME/.env.
          # NOT injected via envFrom — env vars are readable by any process
          # (os.environ, /proc/self/environ, subprocess env dumps). File mount
          # with restrictive permissions is the narrower exposure surface.
          # Hermes reads .env from $HERMES_HOME/.env at startup (dotenv loader).
          volumeMounts:
            - name: data
              mountPath: /opt/data
            - name: config
              mountPath: /opt/data/config.yaml
              subPath: config.yaml
            - name: prompt
              mountPath: /opt/data/system-prompt.md
              subPath: system-prompt.md
            - name: soul
              mountPath: /opt/data/SOUL.md
              subPath: SOUL.md
            - name: secrets
              mountPath: /opt/data/.env
              subPath: .env
              readOnly: true
            - name: module-config
              mountPath: /opt/data/memctl.yaml
              subPath: memctl.yaml
            - name: module-config
              mountPath: /opt/data/watchctl.yaml
              subPath: watchctl.yaml
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          startupProbe:
            exec:
              command: ["python3", "-c", "import os; exit(0 if os.path.exists('/opt/data/heartbeat') else 1)"]
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 30   # 10 + (10 * 30) = 5 min max startup time
          livenessProbe:
            exec:
              command: ["python3", "-c", "import os,time; f='/opt/data/heartbeat'; exit(0 if os.path.exists(f) and time.time()-os.path.getmtime(f)<120 else 1)"]
            periodSeconds: 60
          readinessProbe:
            exec:
              command: ["python3", "-c", "import os,time; f='/opt/data/heartbeat'; exit(0 if os.path.exists(f) and time.time()-os.path.getmtime(f)<120 else 1)"]
            periodSeconds: 30
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: halo-data
        - name: config
          configMap:
            name: halo-config
        - name: prompt
          configMap:
            name: halo-prompt
        - name: soul
          configMap:
            name: halo-soul
        - name: secrets
          secret:
            secretName: halo-secrets
            defaultMode: 0400      # Owner-read only (hermes user)
        - name: module-config
          configMap:
            name: halo-module-config
            optional: true         # Not all clients use all modules
```

### 6.4 Client Overlay (in client repo)

```yaml
# halo-deploy-aura/infra/k8s/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: halo-aura
resources:
  - github.com/rickhallett/halo//infra/k8s/base?ref=v1.0.0
  - namespace.yaml
  - configmap.yaml
  - secrets.yaml
patches:
  - target:
      kind: Deployment
      name: halo-gateway
    patch: |
      - op: replace
        path: /spec/template/spec/containers/0/image
        value: ghcr.io/rickhallett/halo:v1.0.0
      - op: replace
        path: /spec/template/spec/containers/0/resources/limits/memory
        value: "512Mi"
```

### 6.5 ArgoCD Application (in client repo)

```yaml
# halo-deploy-aura/argocd-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: halo-aura
  namespace: argocd
spec:
  project: default
  source:
    # NOTE: If the halo repo (referenced by Kustomize remote base) is private,
    # ArgoCD needs repository credentials configured:
    #   argocd repo add https://github.com/rickhallett/halo --username <user> --password <PAT>
    # Without this, Kustomize remote base resolution fails silently.
    repoURL: https://github.com/rickhallett/halo-deploy-aura
    targetRevision: main
    path: infra/k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: halo-aura
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      # Prevent ArgoCD from deleting PVCs during prune.
      # PVC deletion = irrecoverable data loss. PVCs are protected by the
      # helm.sh/resource-policy: keep annotation on the manifest AND this
      # exclusion. Belt and braces.
      - RespectIgnoreDifferences=true
  ignoreDifferences:
    - group: ""
      kind: PersistentVolumeClaim
      jsonPointers:
        - /spec
```

## 7. Storage

### 7.1 SQLite in Containers

Hermes uses SQLite for sessions (`state.db`) and halos modules use per-domain SQLite files (`store/track_*.db`, `store/journal.db`, etc.). This works fine for single-instance deployments:

- Each client runs exactly one gateway replica (no concurrent writes)
- PVC provides durable storage across pod restarts
- **WAL mode required**: All SQLite connections MUST set `PRAGMA journal_mode=WAL` at connection time. WAL is more resilient on block storage (survives unclean shutdown without corruption). Implementation: halos modules set this in their `_connect()` functions. Hermes `SessionDB` must be patched to set WAL mode if not already doing so. Verify both at image build time via a simple test.
- **Schema forward-compatibility policy**: New columns added with `ALTER TABLE ... ADD COLUMN ... DEFAULT ...` so that old code ignores them (SQLite is lenient with unknown columns on SELECT). Destructive schema changes (column renames, drops, type changes) require a migration script AND a minimum-version gate in the entrypoint. Until migration tooling exists, rollbacks to a previous image version are safe as long as only additive schema changes are made.

### 7.2 Backup Strategy

- **Phase 1**: Sidecar container in the same Pod runs `sqlite3 .backup` on a cron schedule (daily). Writes to a shared emptyDir volume, then uploads to Vultr Object Storage (S3-compatible). Must be a sidecar, not a separate CronJob — cloud PVCs are ReadWriteOnce and cannot be mounted by a second Pod.
  - **Retry policy**: Upload failures retry 3x with exponential backoff (10s, 60s, 300s). If all retries fail, the sidecar writes a failure marker to stdout (picked up by Loki) and exits non-zero. K8s restartPolicy ensures the sidecar restarts.
  - **Backup verification**: Weekly scheduled job downloads the latest backup, runs `sqlite3 <file> "PRAGMA integrity_check"` and `SELECT count(*) FROM <key_table>`, and logs the result. Untested backups are not backups.
  - **Backup destination**: Off-region Vultr Object Storage bucket (not same region as VKE). Region failure must not take both live data and backups.
- **Restore**: Entrypoint detects empty PVC (no `state.db`) and attempts restore from S3 before bootstrapping fresh defaults. Controlled by `BACKUP_S3_BUCKET` env var. Restore script: `docker/restore-from-s3.py`. Without this, a PVC loss results in ArgoCD spinning up a blank instance that immediately overwrites the next backup cycle with empty data.
- **RTO/RPO targets**: RPO = 24 hours (daily backup cycle). RTO = 1 hour (Terraform rebuild + restore from S3). These are best-effort targets at current scale, not SLA commitments.
- **Phase 2**: Litestream for continuous WAL replication to S3 if durability requirements increase. Reduces RPO to near-zero.

### 7.3 Future: Postgres Migration

If/when multi-instance or cross-region becomes necessary:
- Hermes already uses a `SessionDB` class — swap backend behind the interface
- halos modules use simple `sqlite3` calls — abstract to a store interface
- Not needed at the 1-5 client scale. Flag it and move on.

## 8. Observability

### 8.1 Per-Client Cost Tracking

Each client namespace gets labels:

```yaml
metadata:
  labels:
    halo.client: aura
    halo.tier: standard
```

**Label injection path**: The `halo.client` label value is passed to the gateway via `config.yaml` (`client_id: aura`). The gateway includes this in structured log output for every LLM API call (model, input tokens, output tokens, cost estimate, client_id). Loki ingests these logs; Grafana queries filter by `client_id` label. This does NOT rely on K8s namespace labels reaching the application — it's an app-level config value.

**Implementation owner**: Hermes gateway must emit structured JSON logs with the `client_id` field. If Hermes doesn't support this natively, a logging wrapper in the entrypoint or a halos shim module handles it. This is code that needs writing.

### 8.2 Shared Observability Stack

Deploy Prometheus + Grafana + Loki once in a `monitoring` namespace (reuse Jeany's docker-compose configs as Helm values). All client namespaces emit to the shared stack.

**Log routing**: The gateway MUST log to stdout/stderr (structured JSON). Loki ingests via Promtail DaemonSet scraping container stdout. The entrypoint creates `$HERMES_HOME/logs/` for any file-based logging Hermes does natively, but the primary observability path is stdout → Promtail → Loki. If Hermes writes to log files instead of stdout, add a Promtail sidecar or configure Hermes to log to stdout (preferred).

### 8.3 Alerting

- **Hard circuit breaker**: When LLM spend exceeds `COST_CEILING_USD`, the gateway must refuse to process further messages and enter a suspended state. Resume requires manual unblock (env var flip or API call). Alerts are not controls — agentic loops can burn through budgets faster than humans can respond.
  - **Tracking semantics**: Per-calendar-month. Counter resets at midnight UTC on the 1st. Tracked by the gateway in a local SQLite table (`cost_tracking`): each API call logs model, token counts, and estimated cost. The breaker checks the running monthly total before each API call.
  - **Implementation owner**: This is a Hermes patch (or halos wrapper around the Anthropic client). Code does not exist yet. Must be implemented before any client deployment with client-owned API keys.
  - **In-flight handling**: If the ceiling is reached mid-conversation, the current response completes (sunk cost), then the breaker activates. Next user message receives a friendly "monthly limit reached" response.
  - **Bypass**: Operator can temporarily raise the ceiling via ConfigMap update + pod restart. No hot-reload path — intentionally requires a deliberate action.
- Gateway process crashes → K8s restarts pod, alert after 3 restarts in 10 minutes
- PVC usage > 80% → alert (memories and logs grow unbounded without pruning)
- **Alert channels**: Primary: Kai via Telegram (Hermes bot on Kai's own instance). Secondary: email via mailctl. If the Telegram gateway itself is down, the K8s-level alerts (Prometheus Alertmanager) route to email. Two independent channels ensure alerts arrive even when the product is the thing that's broken.
- Heartbeat file (`/opt/data/heartbeat`) written every 60s by the gateway's **Python asyncio loop** (not a shell background process). If the event loop blocks, the file goes stale, and K8s kills the pod. This is the only mechanism that detects deadlocks — a shell-based heartbeat would keep writing regardless of application state. Requires a small patch to Hermes: an `asyncio.create_task` that calls `Path(heartbeat).touch()` on a 60s interval.

## 9. Security

### 9.1 Secret Management

- **Phase 1**: K8s Secrets (base64-encoded, not encrypted at rest unless Vultr supports etcd encryption)
- **Phase 2**: Sealed Secrets (Bitnami) — encrypt secrets in the client repo, decrypt only in-cluster

### 9.2 Agentic Code Execution

- Container runs as non-root user (`USER hermes`, UID 1000) matching K8s securityContext
- `$HERMES_HOME/.env` is mounted from K8s Secret as a **read-only file** with mode 0400 (owner-read only). The agent process (running as `hermes`) can read it at startup (Hermes dotenv loader), but agent tools that operate via subprocesses do not inherit file descriptors to it. This is narrower than `envFrom` (which exposes all secrets via `os.environ` to every child process, `/proc/self/environ`, and `env`/`printenv` commands).
- **Residual risk**: The gateway process itself has the secret values in memory after loading `.env`. A tool that can execute `python3 -c "import os; print(os.environ)"` within the gateway process (not a subprocess) could still read them. Mitigation: secrets are loaded into a dedicated config object, not left in `os.environ`. This requires a Hermes patch to `del os.environ[key]` after loading.
- Hermes `HERMES_EXEC_ASK` is enabled (gateway/run.py sets this by default) — dangerous commands require explicit approval
- Terminal sandbox (`TERMINAL_ENV`) should use Docker-in-Docker or gVisor for clients with code execution enabled. For Aura (non-technical, no code execution use case): disable terminal tools entirely via `enabled_toolsets` in config.yaml.
- **Toolset enforcement**: Disabling terminal tools is a config.yaml setting. There is no admission webhook or policy-as-code that prevents re-enabling. At current scale (1-3 clients, Kai is sole operator), config review is manual. If client count grows, add an OPA/Gatekeeper policy that rejects deployments with terminal tools enabled unless a `security-reviewed: "true"` annotation is present.

### 9.3 Network Isolation

- Each namespace gets a NetworkPolicy: egress allowed to Telegram API, Anthropic API, and DNS only. Anthropic IP ranges change — use FQDN-based egress policies (Cilium/Calico support this) rather than IP allowlists where the CNI supports it. Fallback: egress to `0.0.0.0/0` on port 443 with explicit deny for inter-namespace and private ranges.
- No inter-namespace communication
- No ingress (gateway polls Telegram, doesn't expose HTTP). Base Kustomize does not include a Service manifest.

### 9.5 Namespace RBAC

- Each client namespace gets a `Role` and `RoleBinding` scoped to that namespace only. No `ClusterRole` or `ClusterRoleBinding` for client workloads.
- The gateway pod's ServiceAccount has minimal permissions: read ConfigMaps and Secrets in its own namespace, nothing else.
- Verify: `kubectl auth can-i --list --as=system:serviceaccount:halo-aura:default -n halo-kai` must return empty (no cross-namespace access).

### 9.4 Image Security

- Pin base image digests, not just tags (enforced in Dockerfile — see §4)
- Scan with Trivy in CI before pushing to GHCR
- **Periodic re-scan**: Weekly GitHub Actions scheduled workflow runs Trivy against the currently-deployed image tags (read from client repo manifests). New CVEs discovered after build time are caught within 7 days.
- Read-only root filesystem where possible (HERMES_HOME volume is the only writable mount)
- **Future (Phase 2+)**: SBOM generation (Syft) and image signing (cosign) to mitigate supply-chain risk across shared images. At 1-3 clients this is overhead; at 5+ it's necessary.

## 10. Upgrade Path

1. Kai merges changes to `halo` repo → CI builds new image → pushes `ghcr.io/rickhallett/halo:v1.1.0`
2. Kai tests on own instance (bare-metal or own K8s namespace) for ≥24h
3. Bump image tag in `halo-deploy-aura/infra/k8s/kustomization.yaml`
4. Push to client repo → ArgoCD syncs → Aura's pod restarts with new image
5. Rollback: revert the tag bump, ArgoCD syncs back

Canary deployment with N=1: Kai is always the canary.

## 10a. CI/CD Pipeline

Image builds are triggered by GitHub Actions on the `halo` repo.

```yaml
# .github/workflows/build-image.yml
name: Build Halo Image
on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          scan-ref: .
          exit-code: 1
          severity: CRITICAL,HIGH

      # Validate submodule is populated before building
      - name: Validate vendor directory
        run: test -f vendor/hermes-agent/pyproject.toml || { echo "::error::vendor/hermes-agent is empty — submodule not checked out"; exit 1; }

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/rickhallett/halo:${{ github.ref_name }}
          # NOTE: No :latest tag pushed. Mutable tags in production registries
          # allow silent image replacement. All manifests must reference a
          # pinned version tag. Base deployment.yaml uses a placeholder that
          # client overlays MUST patch.
          build-args: |
            INSTALL_BROWSER=false
```

**Trigger**: Push a git tag (`v1.0.0`) → CI builds, validates submodule, scans with Trivy, pushes to GHCR with immutable version tag only.
**Manual**: `workflow_dispatch` for ad-hoc builds.
**Browser variant**: Separate workflow or matrix build with `INSTALL_BROWSER=true` → tagged as `halo:v1.0.0-browser`.
**Tag immutability**: GHCR supports immutable tags via repository settings. Enable this to prevent overwriting existing tags.

## 11. Implementation Phases

### Phase 0: Aura Onboarding (now → 3 days)

- Second Hermes process on Mac with Aura's bot token
- Gather requirements via the onboarding prompt
- No infrastructure work — just conversations
- **Output**: Halo specification document for Aura

### Phase 1: Containerisation (parallel, ~2 days agent work)

- [ ] Vendor hermes-agent into halo repo (git submodule or snapshot)
- [ ] Write Dockerfile (extending upstream's, adding halos)
- [ ] Write entrypoint.sh with system-prompt.md → env var bridge
- [ ] Test locally: `docker build` + `docker run` with Kai's config
- [ ] Test with Aura's bot token + system prompt (local Docker, not K8s)
- **Gate**: Gateway starts, connects to Telegram, responds to a message

### Phase 2: Client Repo Template (after Phase 1, ~1 day)

- [ ] Create `halo-deploy-aura/` repo with structure from §3.2
- [ ] Populate config/ from Aura's spec
- [ ] Write Kustomize base (in halo) + overlay (in client repo)
- [ ] Test: `kustomize build` produces valid manifests
- **Gate**: `kubectl apply --dry-run=server` succeeds

### Phase 3: Infrastructure (after Phase 2, ~1 day)

- [ ] Terraform shared VKE cluster (clone Jeany pattern)
  - [ ] Remote backend for Terraform state (Vultr Object Storage or Terraform Cloud). **Not local file** — state lost with machine = irrecoverable cluster drift.
  - [ ] State locking enabled (S3 backend + DynamoDB, or Terraform Cloud native locking)
- [ ] Install ArgoCD + ingress-nginx
  - [ ] Configure ArgoCD repo credentials for private halo repo (Kustomize remote base)
- [ ] Deploy monitoring namespace (Prometheus/Grafana/Loki)
  - [ ] Configure Alertmanager with dual channel: Telegram (primary) + email (secondary)
- [ ] Apply ArgoCD Application for Aura
- [ ] **Runbook for client onboarding** (document every step from Phase 1-3 as a repeatable checklist — don't defer to Phase 4, do it now while the steps are fresh)
- **Gate**: Aura's bot responds on Telegram from K8s

### Phase 4: Hardening (after Phase 3, ongoing)

- [ ] NetworkPolicy per namespace
- [ ] Sealed Secrets
- [ ] Backup sidecar for SQLite files (with retry logic and off-region destination)
- [ ] Backup verification job (weekly integrity check)
- [ ] Cost alerting dashboard + circuit breaker implementation
- [ ] Trivy periodic re-scan workflow (weekly)
- [ ] Client offboarding/data export script (fix glob issue — see §15)
- [ ] SLA documentation for client-facing contracts
- [ ] OPA/Gatekeeper policy for toolset enforcement (when client count > 3)

## 12. Cost Estimate (Per Client, Phase 1)

| Item | Monthly cost | Notes |
|---|---|---|
| Vultr VKE node (shared, 1/N) | ~$8-24 | $24 node / 1-3 clients |
| LLM API (Anthropic) | $20-100 | Depends on usage + model choice |
| Container registry | $0 | Vultr free tier (10GB) |
| Object storage (backups) | ~$5 | Vultr Object Storage |
| **Total infra per client** | **~$13-29** | Kai's hard cost |

With client-owned API keys, Kai's hard cost is infrastructure only. The £49/month infra fee covers this with healthy margin for operational overhead. See §14 for full pricing model.

## 13. Resolved Decisions

1. **Hermes vendoring**: Git submodule at `vendor/hermes-agent` pointing directly at `NousResearch/hermes-agent` (upstream). No fork — we wrap, don't patch. All Halo-specific behaviour lives in the entrypoint and halos layer. Upstream sync via `git submodule update --remote vendor/hermes-agent`.

2. **Halos integration depth**: Full halos ecosystem in the image. All modules available. Per-client config determines which are active (e.g. Aura may not use mailctl initially, but the capability is there for upsell).

3. **API key ownership**: Client owns their own Anthropic API key (Phase 1). Eliminates float risk. Kai charges for infrastructure + customisation, not API pass-through. Weekly/monthly usage reports delivered via a client-facing briefing module so the client has visibility on their own spend.
   - **IP exposure note**: Client-owned keys mean the client can view raw API call details on the Anthropic dashboard, including `system` message content (SOUL.md, ephemeral prompt). This exposes Kai's prompt engineering IP. Accepted trade-off at founding client stage — Aura's prompts are co-created. For future clients where prompt IP is valuable, consider Kai-owned keys with cost pass-through billing, or Anthropic's upcoming prompt caching which may obscure system messages.

4. **Browser in container**: Disabled by default (`INSTALL_BROWSER=false`). Saves ~1GB. Build arg available for clients who need web browsing.

5. **Voice**: STT (faster-whisper) included — voice note transcription is a core Telegram UX. TTS deferred — ElevenLabs integration adds cost complexity (per-character billing, voice cloning licensing). Revisit when a client specifically requests it.

6. **Monitoring access**: TBD — depends on pricing tier. At minimum, clients receive a weekly usage summary (token spend, session count, active modules) via their bot. Grafana access is a potential premium tier feature.

## 14. Pricing Model (GBP)

### Structure: Setup Fee + Monthly Retainer + Client-Owned API Keys

| Item | Amount | Notes |
|---|---|---|
| Setup & customisation (founding client) | £800-1,200 (fixed) | Onboarding interviews, spec, deployment, initial advisor/prompt design. Discounted — Aura is helping validate the product. |
| Setup & customisation (standard) | £1,500-2,500 (fixed) | Full rate once the deployment process is proven. |
| Monthly service | £200/month | Infrastructure + 4 hrs hands-on support (bug fixes, tuning, new features) |
| Additional time | £85/hr | Beyond the included 4 hrs. Rate reflects current experience level — revisit after 2-3 deployments. |
| LLM API costs | Client pays directly | Client creates own Anthropic account. Model choice (Opus vs Sonnet) discussed during onboarding. |
| Usage reporting | Included | Weekly summary of token spend + session activity delivered via bot |

**Typical monthly cost for client**: £200 (service) + £30-80 (API, model-dependent) = **£230-280/month** after setup.

### Rationale

- Client-owned keys eliminate float risk and align incentives (client self-regulates usage).
- Founding client rate acknowledges this is a prototype — honest positioning, not undervaluing.
- £75-100/hr is defensible as a skilled freelancer building something novel. Not agency rates, not junior rates. Revisit upward after proven deployments.
- £200/month covers infra (~£20 hard cost) + 4 hrs support (~£50/hr effective). Realistic for early months where tuning and bug fixing will be heavier. Margin improves as the system stabilises.
- 4 included hours prevent nickel-and-diming while capping open-ended scope.

### Open Pricing Questions

- ElevenLabs TTS: if added, per-character costs need separate billing or inclusion in a higher tier
- At what client count does the infrastructure fee need to increase (dedicated cluster threshold)?
- When to raise the hourly rate: after client #2? After 3 months of stable operation? After a referral?

## 15. Client Data & Offboarding

### Data Ownership

All data generated by a client's instance belongs to the client. This includes:
- Memory notes (`memories/`)
- Session transcripts (`sessions/`)
- Tracked metrics (`store/track_*.db`)
- Journal entries (`store/journal.db`)
- Any files created by the agent

Kai has operational access for maintenance and debugging. Client data is never shared across namespaces or used for other clients.

### Data Export

On request or at offboarding, a full export is provided:

```bash
#!/bin/bash
# Export script (run from sidecar or kubectl exec)
set -e
mkdir -p export

# Core databases
sqlite3 "$HERMES_HOME/state.db" .dump > export/state.sql
sqlite3 "$HERMES_HOME/store/journal.db" .dump > export/journal.sql

# trackctl databases — sqlite3 doesn't accept shell globs.
# Iterate over each file individually.
for db in "$HERMES_HOME"/store/track_*.db; do
    [ -f "$db" ] || continue
    name=$(basename "$db" .db)
    sqlite3 "$db" .dump > "export/${name}.sql"
done

# Memory notes and session transcripts
cp -r "$HERMES_HOME/memories/" export/memories/
cp -r "$HERMES_HOME/sessions/" export/sessions/

tar czf "client-export-$(date +%Y%m%d).tar.gz" export/
echo "Export complete: client-export-$(date +%Y%m%d).tar.gz"
```

Delivered as a tar archive containing SQL dumps (machine-readable, restorable) plus raw markdown/session files (human-readable). GDPR right of access and portability covered.

### Offboarding

1. Final data export delivered to client
2. ArgoCD Application deleted
3. Namespace deleted (PVC and all data destroyed)
4. Terraform resources cleaned up (if dedicated cluster)
5. Bot token revoked via BotFather
6. Client repo archived on GitHub

## 16. Support & Availability

### Service Level (informal, Phase 1)

This is not an enterprise SLA. It's an honest statement of what to expect:

| Aspect | Commitment |
|---|---|
| Uptime target | Best effort. K8s auto-restarts crashed pods. Typical availability >99% for a single-replica deployment. |
| Response to outage | Within 24 hours on weekdays. Weekend issues addressed next business day unless critical (total data loss, security breach). |
| Planned maintenance | Notified 24 hours in advance via the bot. Typically <5 min downtime (pod restart). |
| Included support | 4 hrs/month of tuning, bug fixes, feature additions. Tracked honestly. |
| Escalation | Message Kai directly on Telegram. No ticket system. |

This is a one-person operation serving a small number of clients. The advantage is direct access to the person who built the system. The trade-off is no 24/7 NOC. For £200/month, that's the honest deal.

### Formalisation Path

If the client base grows beyond 3-5 clients, a proper SLA document with defined response times, uptime percentages, and credit mechanisms will replace this section.
