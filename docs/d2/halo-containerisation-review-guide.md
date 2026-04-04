---
title: "Halo Containerisation Spec — Adversarial Review Guide"
category: review
status: active
created: 2026-04-04
---

# Adversarial Review Guide: Halo Containerisation Spec

Target document: `docs/d2/halo-containerisation-spec.md`

This guide provides a systematic framework for adversarial review of the Halo multi-tenant deployment specification. The reviewer should assume the roles of: hostile red-teamer, cynical SRE, strict cloud architect, and paranoid billing analyst.

---

## Labelling System

Every finding must carry a composite label:

```
{DOMAIN}.{DIMENSION}.{##} [{FC##}] S{1-4}
```

### Axis 1: Structural Domains

| Domain | Code | Scope | Spec sections |
|--------|------|-------|---------------|
| Container Image | **IMG** | Dockerfile, layers, build pipeline, vendoring | §4, §10a, §13.1 |
| Entrypoint & Bootstrap | **BOOT** | Startup sequence, env bridging, first-run logic | §5 |
| Configuration Injection | **CFG** | ConfigMaps, Secrets, env vars, mount strategy | §3.3, §3.4 |
| Storage & Persistence | **STO** | PVC, SQLite, backup, migration, data lifecycle | §7, §15 |
| Networking & Routing | **NET** | Egress, ingress, inter-namespace, Telegram polling | §9.3 |
| Orchestration | **ORCH** | K8s manifests, Kustomize, ArgoCD, Terraform | §6, §10 |
| Security | **SEC** | Secrets, RBAC, code execution, image scanning | §9 |
| Observability | **OBS** | Metrics, alerting, cost tracking, heartbeat | §8 |
| Cost & Billing | **COST** | Circuit breaker, client billing, infra cost model | §8.3, §12, §14 |
| Ops & Lifecycle | **OPS** | Upgrades, rollback, offboarding, SLA | §10, §15, §16 |
| Client Isolation | **ISO** | Namespace separation, data boundaries, config bleed | §3, §9 |

### Axis 2: Failure Class Tags

Infrastructure specs fail differently from code. These classes are tuned for deployment review.

| Tag | Name | One-line test |
|-----|------|---------------|
| **FC01** | Spec–Reality Gap | Does the spec describe what will actually happen, or what the author hopes will happen? |
| **FC02** | Single-Point-of-Failure | If this component dies, does the system recover automatically or require human intervention? |
| **FC03** | State Divergence | Can the declared state (git, ArgoCD, Terraform) drift from the actual state (running cluster)? |
| **FC04** | Blast Radius Underestimate | Does the spec correctly bound the impact of this failure to one client, or could it cascade? |
| **FC05** | Cost Runaway | Can this component generate unbounded cost without human action? |
| **FC06** | Secret Exposure | Can credentials be read, logged, or exfiltrated through this path? |
| **FC07** | Data Loss Window | Between the last backup and a failure, how much data is lost? Is that acceptable? |
| **FC08** | Rollback Incompatibility | Does rolling back this component leave other components in an inconsistent state? |
| **FC09** | Config Bleed | Can one client's configuration, data, or behaviour leak into another client's namespace? |
| **FC10** | Implicit Dependency | Does this component depend on something the spec doesn't mention (DNS, NTP, registry availability, upstream API)? |
| **FC11** | Operational Blindness | If this fails silently, how long before anyone notices? |
| **FC12** | Privilege Escalation | Can an unprivileged actor (agent, client, container process) reach a privileged resource? |
| **FC13** | Toil Accumulation | Does this design choice create recurring manual work that scales with client count? |
| **FC14** | Premature Abstraction | Is this component over-engineered for the current scale (1-3 clients)? |
| **FC15** | Missing Specification | Is something required for production that the spec simply doesn't address? |

### Axis 3: Severity

| Level | Label | Meaning |
|-------|-------|---------|
| **S1** | Critical | Will cause downtime, data loss, security breach, or financial harm in production |
| **S2** | High | Will cause operational pain, client-visible degradation, or uncontrolled cost |
| **S3** | Medium | Latent issue; triggers under growth, edge conditions, or accumulation |
| **S4** | Low | Clarity, maintainability, or minor inefficiency; no production impact |

---

## Structural Dimensions per Domain

### IMG — Container Image

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **IMG.BUILD** | Build pipeline | Reproducibility, layer caching, build time, CI trigger |
| IMG.BUILD.01 | | Is the build fully reproducible? Pinned base image digest or floating tag? |
| IMG.BUILD.02 | | Does the multi-stage build actually produce the correct artefact? (halos-builder output used correctly?) |
| IMG.BUILD.03 | | What happens if the submodule ref is stale or GitHub is down during CI? |
| **IMG.SIZE** | Image footprint | Size, unnecessary deps, attack surface |
| IMG.SIZE.01 | | What's in the image that shouldn't be? Dev deps, test fixtures, build tools? |
| IMG.SIZE.02 | | Is ffmpeg actually needed for all clients? |
| **IMG.VENDOR** | Hermes vendoring | Submodule strategy, upstream tracking, patch management |
| IMG.VENDOR.01 | | What's the process for applying security patches from upstream Hermes? |
| IMG.VENDOR.02 | | Can the image build without network access to the submodule remote? |
| **IMG.TAG** | Tagging & registry | Version strategy, tag immutability, cleanup |
| IMG.TAG.01 | | Is `latest` tag used in any production manifest? (It shouldn't be.) |
| IMG.TAG.02 | | What prevents pushing a different image over an existing tag? |

### BOOT — Entrypoint & Bootstrap

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **BOOT.INIT** | First-run logic | Default config bootstrap, directory creation |
| BOOT.INIT.01 | | If ConfigMap mounts config.yaml AND the PVC already has one, which wins? Mount order matters. |
| BOOT.INIT.02 | | Can a malformed system-prompt.md crash the entrypoint? (e.g. contains backticks that break the shell `$(cat ...)`) |
| **BOOT.HEART** | Heartbeat writer | Background process lifecycle |
| BOOT.HEART.01 | | The heartbeat is a background shell loop. If it dies (killed by OOM), the liveness probe will kill the pod even though the gateway is fine. |
| BOOT.HEART.02 | | The heartbeat loop is a child of PID 1 (bash). When `exec` replaces bash with the gateway, what happens to the background loop? It becomes an orphan. Does the container runtime reap it? |
| **BOOT.ENV** | Environment bridging | system-prompt.md → env var, working directory |
| BOOT.ENV.01 | | `HERMES_EPHEMERAL_SYSTEM_PROMPT` loaded via `$(cat file)` — shell expansion issues if prompt contains `$`, backticks, or null bytes? |
| BOOT.ENV.02 | | `cd $HERMES_HOME` sets cwd for the gateway. Does Hermes respect cwd or resolve paths from its own `__file__`? |

### CFG — Configuration Injection

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **CFG.MOUNT** | Volume mount conflicts | ConfigMap subPath vs PVC mount ordering |
| CFG.MOUNT.01 | | ConfigMap mounts config.yaml at `/opt/data/config.yaml` as subPath. PVC mounts at `/opt/data/`. Does the PVC mount shadow the ConfigMap? Mount order in the pod spec matters. |
| CFG.MOUNT.02 | | ConfigMap `halo-module-config` mounts memctl.yaml etc. Are these read-only? Can the gateway process write to them (e.g. memctl index rebuild)? |
| **CFG.UPDATE** | Config change propagation | How changes reach the running pod |
| CFG.UPDATE.01 | | ConfigMap/Secret updates do NOT trigger pod restart. How does the operator know to restart? |
| CFG.UPDATE.02 | | If config.yaml is malformed, the pod restarts with broken config in a CrashLoopBackOff. Is there validation before apply? |
| **CFG.SCOPE** | Per-client config completeness | Everything that varies per client accounted for? |
| CFG.SCOPE.01 | | Are cronctl schedules per-client? Where do they live? |
| CFG.SCOPE.02 | | trackctl domains are listed as ConfigMap but they're Python files (`domains/<name>.py`). ConfigMap can't mount executable Python that gets imported. How does this actually work? |

### STO — Storage & Persistence

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **STO.PVC** | PersistentVolumeClaim | Sizing, class, reclaim policy |
| STO.PVC.01 | | What storage class? What reclaim policy? If the namespace is deleted, is the PVC deleted too? (ReclaimPolicy: Delete is the default.) |
| STO.PVC.02 | | Initial PVC size? SQLite grows unbounded without vacuuming. What's the growth rate? |
| **STO.BACKUP** | Backup sidecar | Schedule, verification, restore testing |
| STO.BACKUP.01 | | Sidecar writes to emptyDir then uploads. If the upload fails, the emptyDir is lost on pod restart. Is there retry logic? |
| STO.BACKUP.02 | | Has a restore from backup ever been tested? Untested backups are not backups. |
| **STO.SQLITE** | SQLite on block storage | WAL mode, locking, corruption risk |
| STO.SQLITE.01 | | Is WAL mode explicitly enabled, or default (journal mode)? WAL is more resilient on network storage. |
| STO.SQLITE.02 | | `PRAGMA journal_mode=WAL` must be set at connection time. Who sets it? Hermes? Halos modules? Both? Neither? |
| **STO.MIGRATE** | Schema evolution | Forward/backward compatibility |
| STO.MIGRATE.01 | | Image v1.1.0 adds a column. Rollback to v1.0.0. Does the old code crash? (Deferred, but what's the mitigation for now?) |

### NET — Networking & Routing

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **NET.EGRESS** | Outbound traffic | Telegram API, Anthropic API, DNS |
| NET.EGRESS.01 | | NetworkPolicy allows Telegram + Anthropic + DNS. Anthropic uses multiple IP ranges that change. How is the policy maintained? |
| NET.EGRESS.02 | | Does the gateway need egress to PyPI, npm, or GitHub at runtime? (skills_sync, pip install?) |
| **NET.INGRESS** | Inbound traffic | "No ingress" claim |
| NET.INGRESS.01 | | Is that actually true? Does Hermes expose any HTTP endpoint (API server, webhook platform, health check)? Check the Platform enum. |
| **NET.DNS** | DNS resolution | External service discovery |
| NET.DNS.01 | | If Vultr DNS is down, the gateway can't resolve api.telegram.org. Is there a fallback? (Hermes has `TELEGRAM_FALLBACK_IPS`.) |

### ORCH — Orchestration

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **ORCH.KUSTOMIZE** | Kustomize base + overlay | Remote base reference, version pinning |
| ORCH.KUSTOMIZE.01 | | Client overlay references `github.com/rickhallett/halo//infra/k8s/base?ref=v1.0.0`. If the halo repo is private, ArgoCD needs credentials to fetch the base. Is that configured? |
| ORCH.KUSTOMIZE.02 | | What if the base changes in a breaking way and a client overlay hasn't been updated? |
| **ORCH.ARGOCD** | ArgoCD sync | Automated sync, prune, self-heal |
| ORCH.ARGOCD.01 | | `prune: true` means ArgoCD deletes resources removed from git. Accidental deletion of a manifest = ArgoCD deletes the running resource. |
| ORCH.ARGOCD.02 | | ArgoCD itself is a single point of failure. If ArgoCD goes down, no syncs happen. Is ArgoCD HA? |
| **ORCH.TF** | Terraform state | State storage, locking |
| ORCH.TF.01 | | Where is Terraform state stored? Local file? Remote backend? If local, it's lost with the machine. |
| ORCH.TF.02 | | Is there state locking? Without it, concurrent applies corrupt state. |
| **ORCH.UPGRADE** | Upgrade path | Canary, rollback, blue-green |
| ORCH.UPGRADE.01 | | Rollback is "revert the tag bump." But PVC state has advanced. See STO.MIGRATE. |

### SEC — Security

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **SEC.USER** | Non-root container | USER directive, file permissions |
| SEC.USER.01 | | Dockerfile says `USER hermes` but doesn't show the `RUN useradd` or `chown` commands. Does the user exist? Can it write to $HERMES_HOME? |
| **SEC.SECRETS** | Secret lifecycle | Creation, rotation, exposure |
| SEC.SECRETS.01 | | Secrets are in the client git repo (even if sealed). Is the repo private? Who has access? |
| SEC.SECRETS.02 | | Secret rotation: if Aura's Anthropic key is compromised, what's the process? Update Secret → restart pod? How fast? |
| **SEC.AGENT** | Agentic attack surface | Prompt injection, tool abuse |
| SEC.AGENT.01 | | System prompt is in a ConfigMap. Can the agent read the ConfigMap via kubectl (if somehow kubectl is in the image)? |
| SEC.AGENT.02 | | Terminal tools disabled for Aura. What prevents re-enabling via config change without reviewing the security implications? |
| **SEC.SCAN** | Image scanning | Trivy, CVE management |
| SEC.SCAN.01 | | CI scans on build. But the running image ages. Is there periodic re-scanning of deployed images? |

### OBS — Observability

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **OBS.HEART** | Heartbeat & probes | Liveness, readiness, startup |
| OBS.HEART.01 | | No startup probe defined. Gateway may take >60s to connect to Telegram on first boot. Liveness probe could kill it before it's ready. |
| **OBS.LOG** | Logging | Structured logs, aggregation, retention |
| OBS.LOG.01 | | Where do gateway logs go? Stdout (picked up by Loki via Promtail)? Or files in $HERMES_HOME/logs/? If files, Loki can't see them without a sidecar. |
| **OBS.COST** | Cost tracking | Per-client attribution, dashboard |
| OBS.COST.01 | | "LLM API calls logged with client label." Who logs them? Hermes doesn't know about K8s namespace labels. How does the label get injected? |
| **OBS.ALERT** | Alerting | Alert routing, on-call, escalation |
| OBS.ALERT.01 | | Alerts go to "Kai via Telegram." If the Telegram gateway is what's broken, alerts don't arrive. Secondary alert channel? |

### COST — Cost & Billing

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **COST.CIRCUIT** | Hard circuit breaker | Implementation, bypass, recovery |
| COST.CIRCUIT.01 | | The spec says the gateway "must refuse to process further messages." Who implements this? Hermes? A sidecar? A wrapper? Is this code that exists or code that needs writing? |
| COST.CIRCUIT.02 | | How is the ceiling tracked? Per-calendar-month? Rolling 30 days? Per-session? |
| **COST.MODEL** | Pricing model | Margin, sustainability |
| COST.MODEL.01 | | £200/month at 4 hrs support = £50/hr effective. If early months need 6-8 hrs, you're working for £25-33/hr. Is there a cap on "included" hours? |
| COST.MODEL.02 | | Client-owned API keys mean client can see raw API calls on Anthropic dashboard. Is the system prompt visible in the API request? |

### OPS — Operations & Lifecycle

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **OPS.ONBOARD** | Client onboarding | Repeatable process, checklist |
| OPS.ONBOARD.01 | | How long does onboarding client #2 take? Is the process documented as a runbook, or only in Kai's head? |
| **OPS.OFFBOARD** | Client offboarding | Data export, cleanup, billing stop |
| OPS.OFFBOARD.01 | | Export script uses `sqlite3 .dump`. Does the client get the raw SQL, or something human-readable? |
| **OPS.DISASTER** | Disaster recovery | Full cluster loss, region outage |
| OPS.DISASTER.01 | | If the Vultr London region goes down, what's the recovery plan? Terraform can rebuild, but PVC data is gone unless backed up off-region. |
| **OPS.DEPEND** | External dependencies | Upstream Hermes, Anthropic, Vultr, Telegram |
| OPS.DEPEND.01 | | If Nous Research changes the Hermes license from MIT, what's the fallback? |

### ISO — Client Isolation

| Label | Dimension | What to probe |
|-------|-----------|---------------|
| **ISO.NS** | Namespace boundaries | Network, storage, RBAC |
| ISO.NS.01 | | Are there RBAC policies preventing pods in namespace A from reading Secrets in namespace B? (K8s default: yes, but only if no cluster-wide bindings exist.) |
| **ISO.IMAGE** | Shared image risk | Same image, different clients |
| ISO.IMAGE.01 | | If a malicious payload is baked into the image, all clients are affected simultaneously. Mitigation? |
| **ISO.OPS** | Operational isolation | Can maintenance on client A affect client B? |
| ISO.OPS.01 | | Shared node. If client A's pod OOMs and the kernel OOM-killer fires, it may kill client B's pod instead. Resource limits are requests, not guarantees, unless you use Guaranteed QoS class. |

---

## Review Itinerary

Ordered by risk (blast radius × likelihood × detectability):

### Phase 1: Will It Actually Boot? (BOOT + CFG + IMG)

Start here. If the container doesn't start correctly, nothing else matters.

1. **BOOT.INIT** — First-run logic, mount conflicts (2 items)
2. **BOOT.HEART** — Heartbeat process lifecycle (2 items)
3. **BOOT.ENV** — Shell expansion in env bridging (2 items)
4. **CFG.MOUNT** — ConfigMap vs PVC mount ordering (2 items)
5. **CFG.SCOPE** — Completeness of per-client config (2 items)
6. **IMG.BUILD** — Build reproducibility and correctness (3 items)

### Phase 2: Will It Stay Running? (STO + OBS + NET)

The system booted. Now: will it survive a week?

7. **STO.PVC** — Storage sizing and reclaim policy (2 items)
8. **STO.SQLITE** — WAL mode, corruption resilience (2 items)
9. **STO.BACKUP** — Backup sidecar reliability (2 items)
10. **OBS.HEART** — Startup probe gap (1 item)
11. **OBS.LOG** — Log routing to Loki (1 item)
12. **OBS.ALERT** — Alert channel reliability (1 item)
13. **NET.EGRESS** — NetworkPolicy maintenance burden (2 items)
14. **NET.INGRESS** — Verify "no ingress" claim (1 item)

### Phase 3: Will It Stay Secure? (SEC + ISO)

Running and observable. Now: is the trust model sound?

15. **SEC.USER** — Non-root user actually works (1 item)
16. **SEC.SECRETS** — Secret lifecycle and rotation (2 items)
17. **SEC.AGENT** — Agentic attack surface (2 items)
18. **SEC.SCAN** — Ongoing vulnerability management (1 item)
19. **ISO.NS** — Namespace RBAC boundaries (1 item)
20. **ISO.OPS** — Shared node OOM risk (1 item)

### Phase 4: Will It Scale and Pay? (COST + ORCH + OPS)

Secure and running. Now: does the business model survive contact with reality?

21. **COST.CIRCUIT** — Circuit breaker implementation gap (2 items)
22. **COST.MODEL** — Margin erosion under support load (2 items)
23. **ORCH.TF** — Terraform state management (2 items)
24. **ORCH.ARGOCD** — ArgoCD as SPOF (2 items)
25. **ORCH.KUSTOMIZE** — Remote base dependency (2 items)
26. **OPS.ONBOARD** — Repeatability for client #2 (1 item)
27. **OPS.DISASTER** — Regional failure recovery (1 item)
28. **OPS.DEPEND** — Upstream dependency risk (1 item)

---

## Audit Heuristics

Apply to every finding:

1. **Does this exist yet?** The spec describes intended state. Has any of it been built? Label aspirational claims.
2. **Who fixes this at 3am?** If the answer is "nobody, it waits until Monday" — is that acceptable for this severity?
3. **Does this scale linearly with clients?** If adding client #5 requires the same manual effort as client #1, it's toil.
4. **What's the blast radius?** One client? All clients? The operator?
5. **Is the mitigation tested?** An untested backup is not a backup. An untested rollback is not a rollback.
6. **Does the spec say "must" without saying "how"?** Every "must" needs an implementation owner and a verification method.
7. **What happens if the operator is unavailable for 48 hours?** Does the system self-heal, degrade gracefully, or fail silently?
8. **Is this finding premature for the current scale?** Mark with [FC14] if so. Not every risk needs solving at 1-3 clients, but it must be acknowledged.

---

## Scoring Template

After review, summarise:

| Metric | Count |
|--------|-------|
| Total findings | |
| S1 (Critical) | |
| S2 (High) | |
| S3 (Medium) | |
| S4 (Low) | |
| Findings with [FC15] (missing spec) | |
| Findings with [FC14] (premature) | |
| Findings requiring code that doesn't exist yet | |

### Per-Domain Heatmap

| Domain | S1 | S2 | S3 | S4 | Total |
|--------|----|----|----|----|-------|
| IMG | | | | | |
| BOOT | | | | | |
| CFG | | | | | |
| STO | | | | | |
| NET | | | | | |
| ORCH | | | | | |
| SEC | | | | | |
| OBS | | | | | |
| COST | | | | | |
| OPS | | | | | |
| ISO | | | | | |
