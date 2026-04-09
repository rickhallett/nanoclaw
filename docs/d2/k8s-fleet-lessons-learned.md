---
title: "K8s Fleet Deployment Lessons Learned"
category: analysis
status: active
created: 2026-04-06
---

# K8s Fleet Deployment Lessons Learned

Hard-won knowledge from deploying the Halo advisor fleet, NFS-backed memory corpus, and Argo CD on VKE (Vultr Kubernetes Engine). Every item below caused at least one failed deployment or debug cycle.

## NFS in Kubernetes

### 1. NFS kernel server requires privileged containers

**Problem:** The `itsthenetwork/nfs-server-alpine` image needs `privileged: true` and `CAP_SYS_ADMIN`. The `restricted` PodSecurity standard rejects it outright.

**Fix:** Run the NFS server in a separate namespace (`halo-infra`) with `privileged` PodSecurity enforcement. Keep the main fleet namespace at `baseline` or `restricted`.

**Gotcha:** Even `baseline` enforcement blocks NFS *volume types* in pods. Only `baseline` enforcement (not `restricted`) allows pods to mount NFS volumes. If your namespace uses `restricted`, pods mounting NFS will fail with `restricted volume types (volume "X" uses restricted volume type "nfs")`.

### 2. Kubelet mounts NFS from the host network, not pod network

**Problem:** NFS volume mounts in pod specs use `server: <hostname>`. The kubelet resolves this DNS name from the **host's** `/etc/resolv.conf`, not from cluster DNS. Headless services (ClusterIP: None) and `.svc.cluster.local` names are invisible to the kubelet.

**Fix:** Use the Service's ClusterIP directly in the NFS volume spec. A ClusterIP service (not headless) gets a stable IP that the kubelet can route to via kube-proxy. Hardcode it.

**Downside:** If the NFS service is recreated, the ClusterIP changes and all volume specs need updating. Document the IP and accept the coupling, or use a static ClusterIP in the Service spec.

```yaml
# Works — kubelet can reach ClusterIP via kube-proxy
volumes:
  - name: memory-nfs
    nfs:
      server: 10.100.54.223  # ClusterIP of nfs-server service
      path: /

# Fails — kubelet can't resolve cluster DNS
volumes:
  - name: memory-nfs
    nfs:
      server: nfs-server.halo-infra.svc.cluster.local
      path: /
```

### 3. NFS export root permissions

**Problem:** A fresh ext4 filesystem on the PVC has `root:root` ownership on `/`. The NFS server runs privileged but the client pods run as UID 1000 (`runAsNonRoot: true`). Writes fail with `Permission denied`.

**Fix:** `chown 1000:1000 /exports/` on the NFS server pod after first mount. This persists on the PVC. Only needed once.

## PodSecurity Standards

### 4. Argo CD selfHeal reverts namespace labels

**Problem:** Manually changing namespace labels (e.g., `pod-security.kubernetes.io/enforce: restricted` → `baseline`) via `kubectl label` gets reverted within seconds if Argo CD has selfHeal enabled and the namespace manifest is tracked.

**Fix:** Change the label in the committed `namespace.yaml` manifest, push to git, and let Argo apply it. Never rely on imperative label changes when Argo is watching.

### 5. The restricted → baseline escalation path

The three PodSecurity levels and what they actually block for NFS use:

| Level | Privileged containers | NFS volume type | NFS server | NFS client |
|-------|----------------------|-----------------|------------|------------|
| `restricted` | ❌ | ❌ | ❌ | ❌ |
| `baseline` | ❌ | ✅ | ❌ | ✅ |
| `privileged` | ✅ | ✅ | ✅ | ✅ |

For a fleet with NFS: server namespace needs `privileged`, client namespace needs at least `baseline`.

## Argo CD

### 6. Argo exclude globs don't work on subdirectories in non-recursive mode

**Problem:** Setting `directory.exclude: "{archived/*}"` with `recurse: false` does not prevent Argo from finding manifests in `archived/` if that directory contains valid YAML with Kubernetes resource definitions.

**Fix:** Move archived manifests completely out of the Argo-tracked directory. Don't rely on exclude patterns for subdirectories.

### 7. `git mv` doesn't stage deletions automatically in all contexts

**Problem:** Running `mv dir/file newdir/file` then `git add -A newdir/` stages the new file but may not stage the deletion of the old path if the old path was previously tracked. This leaves ghost files in git that Argo will deploy.

**Fix:** Always use `git rm` explicitly for the old paths, or use `git mv` (not shell `mv`) which handles both sides atomically.

### 8. Argo prune:false means orphans live forever

**Problem:** With `syncPolicy.automated.prune: false` (the default safe setting), resources deployed by a previous sync but no longer in git are never deleted. They become "Synced" ghosts that Argo actively maintains.

**Fix:** Either set `prune: true` in the sync policy (risky — accidental git deletions kill resources), or run `argocd app sync <app> --prune` manually after removing resources from git. We chose to enable auto-prune after gaining confidence.

### 9. Argo repo-server caches aggressively

**Problem:** After pushing to git, Argo may not see the new commit for up to 3 minutes (default poll interval). The repo-server caches the git tree and doesn't refresh on every sync attempt.

**Fix:** `argocd app get <app> --hard-refresh` forces a fresh git fetch. For faster feedback during development, reduce `timeout.reconciliation` in Argo's ConfigMap, or use a webhook.

### 10. Self-referencing Argo Application manifests

**Problem:** Putting `argocd-app.yaml` (the Application CR) inside the directory that the Application tracks creates a self-referencing loop. Argo tries to manage itself.

**Fix:** Exclude the Application manifest from the directory scan: `directory.exclude: "{argocd-app.yaml}"`. Or store Application CRs in a separate directory/repo.

### 11. Operations in progress block sync

**Problem:** `argocd app sync` returns `another operation is already in progress` when Argo is retrying a failed sync or selfHeal is running.

**Fix:** Wait for the operation to finish, or terminate it with `kubectl patch application <app> -n argocd --type merge -p '{"operation": null}'`. Disabling auto-sync temporarily (`argocd app set <app> --sync-policy none`) also stops the interference.

## Vultr-Specific

### 12. Minimum PVC size is 40Gi

Documented in the fleet README but worth repeating: Vultr block storage requests under 40Gi fail silently or with unhelpful errors. Always request `storage: 40Gi` even if you need 1Gi.

### 13. Use `vultr-block-storage-hdd-retain` for persistent data

The default storage class uses `Delete` reclaim policy — the PV is destroyed when the PVC is deleted. For data that must survive (memory corpus, NATS journal), always specify `vultr-block-storage-hdd-retain`.

## Architecture Decisions

### 14. Memory corpus: shared NFS PVC, single-writer authority

**Decision:** One `memctl-authority` pod has read-write access to the NFS-backed memory corpus. All advisor pods mount it read-only. No event sourcing for memory, no sync logic, no drift.

**Rationale:** Memory is a governance system with graph mutations (link, prune, score, merge). These operations are non-commutative — applying them in different orders produces different results. A single writer serialises the invariants. The write volume is low (~5-10 notes/day). Reads are the hot path, and NFS gives real-time read consistency.

**Alternative rejected:** Event-sourcing notes through NATS. Would require conflict resolution for concurrent edits, index rebuild ordering guarantees, and 7 copies of 157 notes that could diverge.

### 15. memctl-authority is infrastructure, not an advisor

The authority pod is not tied to any advisor persona. It's a governance process that outlives individual advisor seats. If Draper gets the axe, the memory corpus continues unchanged.

### 16. NFS server in separate namespace from fleet

Security boundary: the NFS server needs `privileged`, advisors don't. Separate namespace means the privilege escalation is contained. The fleet namespace stays at `baseline`.

## Ryzen Bare Metal (k3s) — Migrated from VKE 2026-04-09

### 17. No Argo CD — deploy is manual

The Ryzen k3s cluster has no GitOps controller. The deploy chain is: `git pull` on Ryzen, `docker build`, `docker push localhost:5000/halo:dev`, `kubectl rollout restart`. Document every step because the agent won't have Argo to fall back on.

### 18. Live deployments diverge from git manifests

The committed manifests reference `lhr.vultrcr.com/jeany/halo:fleet-latest` (dead Vultr registry). Live pods run `localhost:5000/halo:dev` (patched via `kubectl set image` or `kubectl edit`). Until manifests are updated in git, there's a permanent drift between what's committed and what's running. Treat `kubectl get deploy -o yaml` as truth, not the git manifests.

### 19. Single image, no halos overlay

VKE used a two-image pattern: base `halo:fleet-latest` + init container `halo-halos:latest` for hot-reloading halos Python code. Ryzen uses a single `localhost:5000/halo:dev` image with everything baked in. The init container (`halos-sync`) still runs but copies from a stale image. To update halos code, rebuild the full image.

### 20. Submodule pin references unpushed commit

`vendor/hermes-agent` is pinned to commit `d48b108` which exists only on the Mac (local commit, never force-pushed). Fresh clones fail `git submodule update --init`. Workaround: tar the submodule from the Mac and extract on Ryzen. Proper fix: push the fork commit or repin to a published commit.

### 21. `.dockerignore` excludes `store/` but Dockerfile needs track DBs

The Dockerfile `COPY store/track_*.db` fails because `.dockerignore` blanket-excludes `store/`. Fixed by adding `!store/track_*.db` exception. If new files from `store/` are needed in the image, add similar exceptions.

### 22. NATS is only reachable via SSH tunnel from Mac

NATS runs as a ClusterIP service (`10.43.86.239:4222`) inside k3s. Not exposed on Tailscale. To publish events from the Mac: `ssh -L 4222:10.43.86.239:4222 mrkai@ryzen32 -fN`. Kill after use: `pkill -f "ssh.*4222.*ryzen32"`. The ClusterIP may change if the NATS service is recreated.

### 23. k3s kubeconfig is root-only

`/etc/rancher/k3s/k3s.yaml` has `0600 root:root` permissions. All kubectl commands from the `mrkai` user need `sudo`. Fix: `sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config && sudo chown mrkai:mrkai ~/.kube/config` on the Ryzen, or add `--write-kubeconfig-mode 0644` to k3s server args.

### 24. Full deploy runbook (Mac → Ryzen)

```bash
# 1. Push code
git push

# 2. Pull on Ryzen
ssh mrkai@ryzen32 "cd ~/code/halo && git pull"

# 3. If submodule changed: tar and ship from Mac
tar czf /tmp/hermes-agent.tar.gz -C vendor hermes-agent
scp /tmp/hermes-agent.tar.gz mrkai@ryzen32:/tmp/
ssh mrkai@ryzen32 "cd ~/code/halo && rm -rf vendor/hermes-agent && tar xzf /tmp/hermes-agent.tar.gz -C vendor/"

# 4. If track DBs changed: ship them
scp store/track_*.db mrkai@ryzen32:~/code/halo/store/

# 5. Build and push
ssh mrkai@ryzen32 "cd ~/code/halo && docker build -t localhost:5000/halo:dev . && docker push localhost:5000/halo:dev"

# 6. Restart fleet
ssh mrkai@ryzen32 "sudo kubectl rollout restart deploy -n halo-fleet"

# 7. Verify
ssh mrkai@ryzen32 "sudo kubectl get pods -n halo-fleet --no-headers | grep -v Terminating"
```
