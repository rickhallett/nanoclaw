---
title: "Halo Observability Runbook"
category: runbook
status: active
created: 2026-04-05
---

# Halo Observability Runbook

## What's Deployed

Full observability stack on the Halo k3s cluster (ryzen32, homelab). All components run in the `monitoring` namespace. Access via `ssh ryzen32`; all kubectl commands require `sudo`.

| Component | Helm Chart | Version | Purpose |
|-----------|-----------|---------|---------|
| **Prometheus** | `prometheus-community/kube-prometheus-stack` | Latest | Metrics collection, alerting rules |
| **Grafana** | (bundled with kube-prometheus-stack) | Latest | Dashboards, log exploration |
| **Alertmanager** | (bundled with kube-prometheus-stack) | Latest | Alert routing (not yet wired to Telegram/email) |
| **Loki** | `grafana/loki` | Latest | Log aggregation (single-binary mode) |
| **Promtail** | `grafana/promtail` | Latest | DaemonSet shipping container stdout → Loki |

## Access

All access is via `kubectl port-forward` over SSH. Nothing is exposed publicly.

```bash
# SSH to ryzen32, then run kubectl with sudo
ssh ryzen32

# Grafana (dashboards + log exploration)
sudo kubectl port-forward -n monitoring svc/prometheus-grafana 3001:80
# → http://localhost:3001  admin / halo-grafana-2026

# Prometheus (raw metrics, PromQL)
sudo kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
# → http://localhost:9090

# Alertmanager (alert status, silences)
sudo kubectl port-forward -n monitoring svc/alertmanager-operated 9093:9093
# → http://localhost:9093
```

Use port 3001 for Grafana -- 3000 is typically in use locally.

## Grafana Datasources

| Name | Type | URL (in-cluster) |
|------|------|-------------------|
| Prometheus | prometheus | `http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090` |
| Loki | loki | `http://loki.monitoring.svc.cluster.local:3100` |

Both are provisioned automatically by Grafana sidecar containers from ConfigMaps.

## Querying Logs

In Grafana: **Explore** (compass icon) → select **Loki** datasource.

Useful queries:

```logql
# All halo-fleet namespace logs
{namespace="halo-fleet"}

# A specific advisor container
{namespace="halo-fleet", pod=~"advisor-musashi.*"}

# Filter for errors
{namespace="halo-fleet"} |= "ERROR"

# Filter for Telegram activity (excludes polling noise)
{namespace="halo-fleet"} |= "telegram" != "getUpdates"

# Monitoring namespace (Prometheus, Grafana, Loki itself)
{namespace="monitoring"}
```

### What Goes to Loki

Promtail ships **container stdout/stderr** to Loki. The Hermes gateway writes most operational logs to `/opt/data/logs/gateway.log` (a file inside the container), not stdout. What reaches Loki:

- Entrypoint output (skill sync, env generation, WAL enforcement)
- Agent tool execution output (the kaomoji lines, tool results)
- Python warnings/errors that hit stderr
- Advisor startup/shutdown messages

The detailed `gateway.log` (HTTP poll results, message routing, API calls) stays inside the pod. To read it:

```bash
ssh ryzen32
sudo kubectl exec -n halo-fleet deployment/advisor-musashi -- cat /opt/data/logs/gateway.log | tail -50
```

## Dashboards

The kube-prometheus-stack ships ~20 pre-built dashboards:

- **Kubernetes / Compute Resources / Namespace (Pods)** — CPU/memory per pod in halo-fleet
- **Kubernetes / Compute Resources / Node** — overall node utilisation
- **Node Exporter / USE Method / Node** — disk, network, CPU saturation
- **Alertmanager Overview** — firing alerts, notification status

## Helm Values

All values files live in `infra/k8s/monitoring/`:

| File | What it configures |
|------|--------------------|
| `prometheus-values.yaml` | kube-prometheus-stack: Grafana, Prometheus, Alertmanager, node-exporter |
| `loki-values.yaml` | Loki single-binary mode, filesystem storage, no caching |
| `promtail-values.yaml` | Promtail client config (Loki endpoint) |

### Key Design Decisions

- **No persistent storage for Prometheus.** 15-day retention in emptyDir. Pod restart = metrics reset. Acceptable at current scale.
- **Loki single-binary mode.** No read/write/backend split. One replica, filesystem storage. Scales to ~100GB/day of logs, which is orders of magnitude beyond current needs.
- **Control plane exporters.** k3s exposes control plane metrics natively -- `kubeEtcd`, `kubeControllerManager`, `kubeScheduler`, `kubeProxy` may be available depending on k3s configuration.
- **Grafana sidecar TLS.** Verify sidecar TLS settings match the k3s cluster CA. Previous VKE deployment required `skipTlsVerify: true` due to Vultr CA issues -- k3s may not need this.

## Upgrading

```bash
# SSH to ryzen32 first
ssh ryzen32

# Update Helm repos
sudo helm repo update

# Upgrade Prometheus stack
sudo helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  -f infra/k8s/monitoring/prometheus-values.yaml \
  --wait --timeout 5m

# Upgrade Loki
sudo helm upgrade loki grafana/loki \
  -n monitoring \
  -f infra/k8s/monitoring/loki-values.yaml \
  --wait --timeout 5m

# Upgrade Promtail
sudo helm upgrade promtail grafana/promtail \
  -n monitoring \
  -f infra/k8s/monitoring/promtail-values.yaml \
  --wait --timeout 3m
```

## Not Yet Done

| Item | Status | Notes |
|------|--------|-------|
| Alertmanager → Telegram | Not wired | Needs webhook or bot integration |
| Alertmanager → Email | Not wired | Secondary channel per spec |
| Cost tracking dashboard | Not built | LLM spend per client — needs gateway to emit structured cost logs |
| PVC usage alerts | Not configured | Alert when PVC usage > 80% |
| Pod restart alerts | Not configured | Alert after 3 restarts in 10 minutes |
| Gateway heartbeat stale alert | Not configured | PrometheusRule for heartbeat file age |
