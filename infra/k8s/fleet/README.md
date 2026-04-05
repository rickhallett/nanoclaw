---
title: "Fleet Deployment Guide"
category: runbook
status: active
created: 2026-04-05
---

# Fleet Deployment Guide

Operational runbook for deploying advisors to `halo-fleet` on VKE.

## Known Gotchas

These were found deploying Musashi. They apply to every advisor pod.

### 1. Store path resolution (CRITICAL)

**Problem:** All halos modules (`trackctl`, `journalctl`, `mailctl`, `ledgerctl`) walk up from `__file__` to find `store/`. In containers, Python is installed at `/opt/venv/lib/...` — walking up never finds `store/`. Falls back to `cwd/store` which is wrong if a subprocess changes cwd.

**Fix:** `halos.common.paths.store_dir()` checks `HALO_STORE_DIR` env → `HERMES_HOME/store` → `cwd/store`. All modules now use this shared helper.

**If you add a new module with store access:** Import `from halos.common.paths import store_dir`. Do NOT walk from `__file__`.

### 2. ConfigMap mounts are read-only (CRITICAL)

**Problem:** Mounting a ConfigMap with `subPath` directly to `/opt/data/config.yaml` makes it immutable. Hermes commands like `/sethome` crash with `Device or resource busy` when trying to write.

**Fix:** Mount ConfigMaps to `/opt/defaults/` (read-only). The entrypoint copies them to `/opt/data/` on startup as writable files. System prompt needs an explicit copy step in the Deployment command since the entrypoint only handles `config.yaml` natively.

**Template:**
```yaml
volumeMounts:
  - name: advisor-config
    mountPath: /opt/defaults/config.yaml
    subPath: config.yaml
  - name: advisor-prompt
    mountPath: /opt/defaults/system-prompt.md
    subPath: system-prompt.md
```

### 3. Login shell PATH reset (CRITICAL)

**Problem:** Hermes runs tools via `bash -lic` (login interactive shell). Debian's `/etc/profile` resets PATH to system defaults, stripping `/opt/venv/bin`. All halos CLI tools (`trackctl`, `journalctl`, etc.) return `exit 127 — command not found`.

**Fix:** Write venv PATH to `~/.bashrc` before starting the gateway:
```yaml
args:
  - |
    echo 'export PATH="/opt/venv/bin:$PATH"' >> ~/.bashrc
    exec /opt/entrypoint.sh gateway
```

### 4. Vultr block storage minimum is 40GB

**Problem:** PVC requests under 40Gi fail with `Invalid size — Must be between 40GB and 40000GB`.

**Fix:** Always request `storage: 40Gi` minimum for Vultr PVCs.

### 5. NATS auth needs full subscribe permissions

**Problem:** Restricting NATS subscribe to `halo.>` blocks JetStream API operations. NATS needs `_INBOX.>` for request-reply and `$JS.API.>` for stream management.

**Fix:** Use `permissions: {publish: ">", subscribe: ">"}` for both `hq` and `advisor` users. The auth boundary is the credential, not subject scoping.

### 6. NATS config vs CLI arg conflict

**Problem:** Passing `--store_dir` as a CLI arg AND having `store_dir` in `nats.conf` causes `Duplicate 'store_dir' configuration` error.

**Fix:** Put all config in `nats.conf`. Use only `--config=/etc/nats/nats.conf` as CLI arg.

### 7. JetStream max_file must exceed stream max_bytes

**Problem:** `max_file: 5G` in JetStream config with `max_bytes: 5368709120` (5GB) on the stream → `insufficient storage resources available`.

**Fix:** Set `max_file` to at least 2× the largest stream's `max_bytes`.

### 8. VKE node pool plans cannot be resized in-place

**Problem:** Terraform `apply` for a plan change (e.g. `vc2-2c-4gb` → `vc2-4c-8gb`) succeeds silently but does nothing. The Vultr provider accepts the API call but the node pool is unchanged.

**Fix:** Must create a new node pool with the desired plan, drain the old one, then delete it. Or accept the current plan.

### 9. Docker image push from residential connection

**Problem:** 4GB+ images time out pushing to GHCR from residential internet.

**Fix:** GitHub Actions builds and pushes from GitHub's network. CI workflow: `.github/workflows/build-image.yml`. Push to Vultr CR (`lhr.vultrcr.com/jeany/halo`) — same datacenter as VKE, instant pull.

### 10. imagePullPolicy defaults to IfNotPresent

**Problem:** Tag `fleet-latest` doesn't trigger automatic image pulls. Kubernetes only defaults to `Always` for the exact tag `latest`, not tags containing "latest".

**Fix:** Explicit `imagePullPolicy: Always` on every advisor container.

### 11. Vultr CR tag/repo deletion API is broken (as of 2026-04-05)

**Problem:** `DELETE /registry/{id}/repository/{name}/tag/{tag}` returns 500 (`deleteRepositoryTag is not resolvable`). Repository deletion also 500s. CLI wraps the same broken endpoint.

**Fix:** No fix. Upgrade the registry plan if you hit the storage limit. Business plan is $5/mo for 20GB.

### 12. Vultr CR free tier is 10GB — halo image is ~1.5GB

**Problem:** Each image push adds ~1.5GB. With 5 old tags, the 10GB free tier fills up. Since deletion is broken, old tags accumulate.

**Fix:** Upgraded to Business plan (20GB). Single-tag strategy (`fleet-latest` only) to minimise accumulation.

### 13. Pod security standards block Kaniko

**Problem:** Kaniko needs root to build images. The `restricted` pod security standard blocks it.

**Fix:** Don't use Kaniko. Use GitHub Actions for builds instead.

## Deploying a New Advisor

1. **Create Telegram bot** via @BotFather. Note the token.

2. **Create manifests** (copy from Musashi and modify):
   - `<name>-config.yaml` — ConfigMap with `config.yaml`
   - `<name>-prompt.yaml` — ConfigMap with `system-prompt.md` (from `data/advisors/<name>/persona.md`)
   - `<name>-deployment.yaml` — Deployment
   - `<name>-secrets.yaml` — Secret (gitignored)

3. **Key template values to change:**
   - `ADVISOR_NAME` env var
   - Bot token in secret
   - ConfigMap names
   - Persona content
   - trackctl domains in config

4. **Apply:**
   ```bash
   export KUBECONFIG=~/.kube/vultr-halo.yaml
   kubectl apply -f infra/k8s/fleet/<name>-config.yaml
   kubectl apply -f infra/k8s/fleet/<name>-prompt.yaml
   kubectl apply -f infra/k8s/fleet/<name>-secrets.yaml  # not in git
   kubectl apply -f infra/k8s/fleet/<name>-deployment.yaml
   ```

5. **Verify:**
   ```bash
   kubectl get pods -n halo-fleet -l halo/advisor=<name>
   kubectl logs -n halo-fleet -l halo/advisor=<name> --tail=10
   # Then message the bot on Telegram
   ```

## Image Build

```bash
# Trigger build from any branch
gh workflow run build-image.yml --ref <branch>

# Watch progress
gh run watch <run-id> --exit-status

# Restart advisor to pick up new image
kubectl rollout restart deployment/advisor-<name> -n halo-fleet
```

Image tag `fleet-latest` is mutable and always points to the latest build. Advisors use `imagePullPolicy: Always` implicitly via the `latest` suffix.

## Cluster Access

```bash
export KUBECONFIG=~/.kube/vultr-halo.yaml
kubectl get pods -n halo-fleet
kubectl logs -n halo-fleet -l halo/advisor=<name> --tail=50
kubectl exec -n halo-fleet deployment/advisor-<name> -- sh -c 'cd /opt/data && trackctl streak movement'
```
