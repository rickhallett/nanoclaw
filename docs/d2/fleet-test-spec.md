---
title: "Fleet Integration & Chaos Test Suite"
category: spec
status: active
created: 2026-04-06
---

# Fleet Integration & Chaos Test Suite

Proves the Halostream does what we intend. Not just when the sun is shining — when agents are actively trying to kill it.

## Design Principles

- **No mocking where reality is available.** These tests exist to catch what mocks hide.
- **Mock only where cost or rate limits make reality impractical.** LLM synthesis and Telegram delivery get mocks. NATS, NFS, and pod lifecycle do not.
- **In-cluster execution.** The test runner is a pod, not a laptop command. It has RBAC access to read pod state, exec into containers, and kill pods. No port-forwarding, no KUBECONFIG leakage.
- **Cryptographic verification over string matching.** When testing data flow, write a unique hash and verify the exact hash arrives. No "contains" assertions on mutable data.
- **The test suite is the deployment gate.** If it doesn't pass, it doesn't ship.

## Test Tiers

### Tier 1: Heavy Iron Diagnostics (Plumbing)

Fast (<60s). Run after every deployment. Proves the machine is assembled correctly.

| Test | What it proves | Kill signal if missing |
|------|---------------|----------------------|
| `test_pod_roster` | All expected pods Running 1/1, no CrashLoop/Error/Pending | Deployment is broken |
| `test_nfs_hash_propagation` | Authority writes unique SHA-256 → all 7 advisors read exact hash within 2s | NFS mount is broken or stale |
| `test_nfs_read_only` | Advisors cannot write to `/memory/` | Security boundary violated |
| `test_nfs_corpus_integrity` | INDEX.md exists, parseable, >100 notes, notes dir matches index count | Corpus corrupted or incomplete |
| `test_nats_stream_exists` | HALO stream present with correct config (subjects, retention) | Event bus is broken |
| `test_nats_consumers_registered` | One consumer per advisor, all caught up (pending=0) | Event consumer sidecar failed to start |
| `test_advisor_identity` | Each pod's ADVISOR_NAME env matches its deployment name | Manifest copy-paste error |
| `test_advisor_fleet_context` | Each advisor's system-prompt contains Fleet Context preamble | Prompt not updated |
| `test_memctl_authority_write` | Authority can `memctl stats` and reports >0 notes | Authority pod misconfigured |
| `test_argocd_git_sha` | Running deployment specs match the HEAD git SHA of the tracked branch | Argo drift — cluster != git |
| `test_argocd_health` | Argo app status is Synced + Healthy, zero degraded resources | GitOps is broken |
| `test_namespace_security` | halo-fleet is `baseline`, halo-infra is `privileged` | PodSecurity misconfigured |

### Tier 2: Halostream Event Flow (CQRS Verification)

Proves data moves through the system. Requires NATS. ~2min.

| Test | What it proves | Kill signal if missing |
|------|---------------|----------------------|
| `test_event_publish_ack` | Publish `halo.test.ping` → all consumers ack within 10s | NATS delivery broken |
| `test_track_event_projection` | Publish `track.movement.logged` → appears in advisor projection.db within 5s | Projection handler broken |
| `test_journal_event_projection` | Publish `journal.entry.added` → appears in projection.db | Journal handler broken |
| `test_cross_advisor_visibility` | Event from Musashi's consumer visible in Draper's projection | Cross-pod data flow broken |
| `test_amnesia_recovery` | Wipe an advisor's projection.db → consumer replays from seq 0 → projection rebuilt perfectly | CQRS rebuild broken (system not immortal) |
| `test_duplicate_event_idempotency` | Publish same event ID twice → projection has exactly one entry | Idempotency guard broken |

### Tier 3: Chaos Engineering (Dodging Bullets)

Proves the system recovers from failure. Destructive. ~5min.

| Test | What it proves | Kill signal if missing |
|------|---------------|----------------------|
| `test_nats_pod_murder` | Kill NATS pod during event publish → K8s restarts → consumers reconnect → no message loss | Single point of failure |
| `test_advisor_pod_murder` | Kill an advisor mid-conversation → pod restarts → consumer replays unacked messages | Data loss on pod restart |
| `test_nfs_server_restart` | Kill NFS server pod → K8s restarts → memory reads resume → no corruption | NFS is fragile |
| `test_memctl_authority_restart` | Kill authority pod → restarts → NFS corpus intact → writes resume | Authority state loss |
| `test_concurrent_nats_publish` | 7 advisors publish simultaneously → no message interleaving or loss | Race condition in event bus |

### Tier 4: Mock Pipeline (Cost-Free Integration)

Tests the full pipeline without burning API tokens or hitting rate limits.

| Test | What it proves | Kill signal if missing |
|------|---------------|----------------------|
| `test_briefing_gather_from_projections` | Briefing gather reads from cluster projection data, not local SQLite | Briefing reads stale/wrong data |
| `test_briefing_synthesis_mock` | Full gather → mock LLM → formatted output | Synthesis pipeline broken |
| `test_telegram_roundtrip_mock` | Mock Telegram receives a message → advisor processes → reply sent to mock | End-to-end message flow broken |

### Tier 5: Telegram Liveness (Live, Careful)

Validates bots actually respond. Rate-limit aware. ~3min.

| Test | What it proves | Kill signal if missing |
|------|---------------|----------------------|
| `test_bot_get_me` | Each bot's `getMe` API returns valid bot info | Bot token invalid or revoked |
| `test_bot_responds` | Send a message → receive a non-empty reply within 120s | Hermes pipeline broken |

## Architecture

### Test Runner Pod

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: fleet-test-runner
  namespace: halo-fleet
spec:
  template:
    spec:
      serviceAccountName: fleet-test-runner
      containers:
        - name: runner
          image: lhr.vultrcr.com/jeany/halo:fleet-latest
          command: ["pytest", "tests/fleet/", "-v", "--tb=short"]
          env:
            - name: KUBECONFIG
              value: /dev/null  # Uses in-cluster config
            - name: NATS_URL
              value: nats://nats.halo-fleet.svc.cluster.local:4222
      restartPolicy: Never
  backoffLimit: 0
```

### RBAC

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: fleet-test-runner
  namespace: halo-fleet
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/exec", "pods/log", "services", "configmaps", "persistentvolumeclaims"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/exec"]
    verbs: ["create"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["delete"]  # For chaos tests only
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]
  - apiGroups: ["argoproj.io"]
    resources: ["applications"]
    verbs: ["get", "list"]
```

### Mock LLM Pod (Tier 4)

Lightweight FastAPI server returning static responses. Deployed only during test runs.

```python
@app.post("/v1/messages")
async def mock_anthropic(request: Request):
    return {"content": [{"type": "text", "text": "*HAL* No errors. All quiet.\n🔴"}]}
```

Advisor pods get `ANTHROPIC_API_URL` overridden to point at the mock during test runs. No real API calls.

### Mock Telegram Server (Tier 4)

Records sent messages instead of delivering them. Exposes `/assert` endpoint for test verification.

## Run Commands

```bash
# Deploy and run (from laptop)
kubectl apply -f tests/fleet/manifests/
kubectl wait --for=condition=complete job/fleet-test-runner -n halo-fleet --timeout=300s
kubectl logs job/fleet-test-runner -n halo-fleet

# Or from CI
just fleet-test

# Selective tiers
kubectl ... -- pytest tests/fleet/ -m "tier1" -v
kubectl ... -- pytest tests/fleet/ -m "tier1 or tier2" -v
kubectl ... -- pytest tests/fleet/ -m "chaos" -v
```

## Marker Taxonomy

| Marker | Meaning | Default |
|--------|---------|---------|
| `tier1` | Plumbing smoke | Always run |
| `tier2` | NATS event flow | Always run |
| `tier3` / `chaos` | Destructive tests | On-demand only |
| `tier4` | Mock pipeline | Always run |
| `tier5` / `telegram` | Live Telegram | On-demand only |
| `slow` | >30s | Excluded from `-m "not slow"` |

## Success Criteria

The fleet is deployable when:
- Tier 1: 100% green (no exceptions)
- Tier 2: 100% green (no exceptions)
- Tier 3: 100% green (run before any production-affecting change)
- Tier 4: 100% green (when briefing pipeline changes)
- Tier 5: >80% green (Telegram rate limits may cause transient failures)
