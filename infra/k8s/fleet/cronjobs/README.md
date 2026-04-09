# Fleet CronJob Draft Pack

First-pass Kubernetes CronJob manifests for advisor schedule migration.

## Decision Update (2026-04-07)

This directory is currently parked.

Adopted model is Path 1:

- Always-on advisor `Deployment` gateway pods remain primary.
- Cron scheduling remains Hermes-native (created/managed through Telegram sessions).
- These CronJob manifests are retained only as reference drafts and should remain suspended.

## Status

- `DRAFT`: manifests are intentionally created with `spec.suspend: true`.
- They are safe to commit and review, but not production-active until unsuspended.

## Why Suspended

The repo currently does not contain a dedicated one-shot advisor runner module (for example, `python -m halos.advisors.run`).
These CronJobs use Hermes `chat --query` via `/opt/entrypoint.sh` as a provisional execution path.

Before enabling:

1. Validate one-shot advisor behavior in-cluster (tool access, delivery, profile writes).
2. Confirm deterministic message delivery semantics (Telegram vs IPC fallback).
3. Run one advisor in canary for 7 days before broad unsuspend.

## Schedule Matrix (Draft)

- Musashi: `0 7 * * *`
- Karpathy: `0 9 * * *`
- Draper: `45 19 * * *`
- Medici: `0 20 * * *`
- Machiavelli: `15 20 * * *`
- Gibson: `30 20 * * *`
- Hightower: `45 20 * * *`
- Bankei: `0 12 * * 0` (weekly placeholder; on-demand model still preferred)

## Files

- `advisor-*-cronjob.yaml`: advisor cron resources
- `kustomization.yaml`: batch apply entrypoint

## Apply (draft review environment)

```bash
kubectl apply -k infra/k8s/fleet/cronjobs
kubectl get cronjobs -n halo-fleet
```

No jobs execute while suspended.

## Deploy Note

Apply manually via `kubectl apply -k infra/k8s/fleet/cronjobs` on ryzen32 (sudo required).
