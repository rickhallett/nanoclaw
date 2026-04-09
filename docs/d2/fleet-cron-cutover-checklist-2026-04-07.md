---
title: "Fleet CronJob Cutover Checklist"
category: runbook
status: superseded
created: 2026-04-07
---

# Fleet CronJob Cutover Checklist

## Decision Update (2026-04-07)

This runbook is superseded by the adopted operating model:

- Keep advisor services as always-on Hermes gateway Deployments.
- Use Hermes-native cron scheduling created/managed from Telegram interactions.
- Do not proceed with Kubernetes CronJob cutover at this time.

Rationale: this preserves direct functional equivalence with current operator workflow and avoids runner-path ambiguity introduced by one-shot CronJob execution.

## Objective

Cut over advisor scheduling from always-on Deployment gateway pods to Kubernetes CronJobs, while preserving delivery reliability and keeping rollback under 5 minutes.

## Current Reality (Verified)

- Advisors are currently `Deployment` workloads in `infra/k8s/fleet/*-deployment.yaml`.
- Local host cron is still active via `cron/jobs/*.yaml` and `cron/crontab.generated`.
- Briefing delivery still targets `ipc_group: telegram_main` and `chat_id: 5967394003` in `briefings.yaml`.
- Draft CronJob manifests now exist under `infra/k8s/fleet/cronjobs/` and are suspended.

## Critical Gate Before Enabling CronJobs

A deterministic one-shot advisor runner must be confirmed. Current CronJob draft uses Hermes `chat --query` as a provisional path, which must pass canary validation before unsuspending broadly.

## Phase 0: Preflight

1. Export cluster context and verify namespace health.
2. Confirm all advisor ConfigMaps, prompts, and secrets exist.
3. Verify NATS and memory dependencies are healthy (`nats`, `memctl-authority`, NFS).
4. Snapshot existing Deployment YAML and pod logs for rollback evidence.

## Phase 1: Install Draft CronJobs (Still Suspended)

1. Apply draft manifests:
   - `kubectl apply -k infra/k8s/fleet/cronjobs`
2. Verify resources exist and are suspended:
   - `kubectl get cronjobs -n halo-fleet`

## Phase 2: Canary (Single Advisor)

1. Pick canary advisor: `musashi`.
2. Unsuspend only canary:
   - `kubectl patch cronjob advisor-musashi -n halo-fleet -p '{"spec":{"suspend":false}}'`
3. Trigger manual run:
   - `kubectl create job --from=cronjob/advisor-musashi musashi-manual-$(date +%s) -n halo-fleet`
4. Validate:
   - Job completion status
   - Delivery observed in operator channel
   - No crash loops or stuck jobs
   - Expected profile/store side effects
5. Run for 7 consecutive scheduled executions.

Success gate: 7/7 successful runs with verified delivery and no data corruption.

## Phase 3: Progressive Rollout

1. Unsuspend in this order (one per day minimum):
   - `karpathy`, `draper`, `medici`, `machiavelli`, `gibson`, `hightower`
2. Keep `bankei` suspended unless weekly/on-demand behavior is explicitly approved.
3. Continue per-advisor acceptance checks:
   - Success ratio >= 95%
   - Delivery latency within expected window
   - No concurrent write hazards observed

## Phase 4: Decommission Legacy Scheduling

1. Disable local advisor/briefing cron entries on host.
2. Archive legacy cron job definitions or mark deprecated.
3. Remove/retire old Deployment manifests only after 7 stable days post-cutover.
4. Keep one-command rollback script ready for an additional 14 days.

## Rollback Plan (Immediate)

If any advisor fails repeatedly or delivery degrades:

1. Suspend failing CronJob:
   - `kubectl patch cronjob advisor-<name> -n halo-fleet -p '{"spec":{"suspend":true}}'`
2. Restart corresponding legacy Deployment:
   - `kubectl rollout restart deployment/advisor-<name> -n halo-fleet`
3. Collect logs and preserve failed Job YAML for forensic review.

## Observability Checklist

- `kubectl get cronjobs,jobs,pods -n halo-fleet`
- `kubectl logs job/<job-name> -n halo-fleet`
- Message delivery confirmation in operator Telegram path
- NATS consumer health unchanged
- Memory mount readable in job pod

## Open Risks

1. One-shot runner semantics are not yet a dedicated module; current draft relies on prompt-driven `chat --query` behavior.
2. Delivery tool availability in non-gateway one-shot sessions must be confirmed.
3. `bankei` schedule semantics are business-defined, not purely technical.
