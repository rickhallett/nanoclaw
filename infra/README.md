---
title: "Infrastructure Directory Map"
category: reference
status: active
created: 2026-04-06
---

# Infrastructure

All infrastructure code for the Halo ecosystem. Target: k3s on Ryzen homelab (ryzen32 via Tailscale).

## Directory Layout

```
infra/
├── k8s/
│   ├── fleet/              ← Source of truth for halo-fleet namespace (manual kubectl apply)
│   │   ├── namespace.yaml          Namespace definition (PodSecurity: baseline)
│   │   ├── README.md               Fleet deployment runbook (gotchas, procedures)
│   │   │
│   │   ├── *-deployment.yaml       Advisor pod deployments (7 advisors)
│   │   ├── *-config.yaml           Advisor ConfigMaps (config.yaml)
│   │   ├── *-prompt.yaml           Advisor ConfigMaps (system-prompt.md)
│   │   ├── *-secrets.yaml          Advisor Secrets (gitignored — tokens, API keys)
│   │   ├── *-secrets.yaml.example  Secret templates (committed)
│   │   │
│   │   ├── memctl-authority.yaml        Memory governance pod (single writer)
│   │   ├── memctl-authority-config.yaml ConfigMap for authority (memory_dir: /memory)
│   │   ├── memctl-reader-config.yaml    ConfigMap for advisors (read-only memctl)
│   │   ├── memory-pvc.yaml             PVC for NFS-backed memory corpus (in halo-infra)
│   │   ├── nfs-server.yaml             NFS server + Service (in halo-infra)
│   │   │
│   │   ├── nats.yaml               NATS server deployment + service
│   │   ├── nats-config.yaml        NATS server configuration
│   │   ├── nats-secrets.yaml       NATS auth credentials (gitignored)
│   │   ├── nats-secrets.yaml.example
│   │   ├── nats-init-stream.yaml   Job: creates HALO JetStream stream on startup
│   │   │
│   │   ├── musashi-secrets.yaml.example  Template for advisor secrets
│   │   └── kaniko-build.yaml       Kaniko in-cluster build (unused — blocked by PodSecurity)
│   │
│   ├── archived-fleet/     ← Replaced advisor manifests (Socrates → Karpathy, etc.)
│   ├── base/               ← Kustomize base (legacy, pre-fleet)
│   ├── aura/               ← Aura relay patch
│   └── monitoring/         ← Helm values for Prometheus, Loki, Promtail (not yet deployed)
│
├── terraform/              ← VKE cluster provisioning (Vultr provider)
│   ├── main.tf             Cluster, node pool, firewall
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
│
└── gemini-bridge/          ← Experimental Gemini CLI ↔ Telegram bridge (local only)
    ├── bridge.py           Polling bridge (150 LOC)
    ├── GEMINI.md           Chango persona
    ├── pyproject.toml
    └── .gemini/settings.json  API key auth (no keyring)
```

## Namespaces

| Namespace | PodSecurity | What's in it |
|-----------|------------|-------------|
| `halo-fleet` | baseline | 8 advisor pods, memctl-authority, NATS, init jobs |
| `halo-infra` | privileged | NFS server (requires privileged container) |

## Deploy Pipeline

No GitOps controller. Manual SSH pipeline from Mac to ryzen32:

```bash
git push
ssh mrkai@ryzen32 "cd ~/code/halo && git pull"
ssh mrkai@ryzen32 "cd ~/code/halo && docker build -t localhost:5000/halo:dev . && docker push localhost:5000/halo:dev && sudo kubectl rollout restart deploy -n halo-fleet"
sudo kubectl get pods -n halo-fleet  # verify (~45s)
```

All `kubectl` on ryzen32 requires `sudo` (k3s kubeconfig is root-only).

## Shared Storage

### Memory Corpus (NFS)

Single-writer architecture. `memctl-authority` pod writes to NFS. All advisors mount read-only.

```
NFS Server (halo-infra)
  └── PVC: halo-memory (40Gi, vultr-block-storage-hdd-retain)
       └── /exports/ (chown 1000:1000)
            ├── INDEX.md (88KB)
            ├── notes/ (157 .md files)
            └── reflections/ (13 .md files)

Mounted in all advisor pods at /memory (read-only, NFS ClusterIP: 10.100.54.223)
Mounted in memctl-authority at /memory (read-write)
```

**Gotcha:** Kubelet mounts NFS from the host network. ClusterIP must be hardcoded in volume specs — `.svc.cluster.local` DNS doesn't resolve from the host. See `docs/d2/k8s-fleet-lessons-learned.md` for details.

### NATS JetStream (Halostream)

Event bus connecting all advisors. Stream: `HALO`, subjects: `halo.>`.

Each advisor pod runs an event consumer sidecar (`halos.eventsource.run_consumer`) that projects events into a local `projection.db` (SQLite).

## Per-Advisor Manifest Pattern

Each advisor has 3-4 manifests:

| File | Content | Secret? |
|------|---------|---------|
| `<name>-deployment.yaml` | Pod spec, env, volumes, probes | No |
| `<name>-config.yaml` | ConfigMap: `config.yaml` (model, modules, domains) | No |
| `<name>-prompt.yaml` | ConfigMap: `system-prompt.md` (persona) | No |
| `<name>-secrets.yaml` | Secret: `.env` (bot token, API key, allowed users) | **Yes — gitignored** |

### Adding a New Advisor

See `infra/k8s/fleet/README.md` for the full procedure. Summary:

1. Create bot via @BotFather
2. Copy manifests from an existing advisor
3. Update: `ADVISOR_NAME`, bot token, persona, ConfigMap names, trackctl domains
4. `kubectl apply` the secret (not in git), then `kubectl apply` the rest + rollout restart

## Terraform

VKE cluster provisioning. Single node pool (`vc2-2c-4gb`), London region.

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

KUBECONFIG at `~/.kube/vultr-halo.yaml`.

## Lessons Learned

See `docs/d2/k8s-fleet-lessons-learned.md` — hard-won items covering NFS, PodSecurity, deploy pipeline, and platform-specific gotchas.
