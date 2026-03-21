---
title: "Responsiveness Combinatorial Findings Table"
category: review
status: active
created: 2026-03-20
---

# Responsiveness Combinatorial Findings Table

Date: 2026-03-20

| Label | Severity | Interaction | Escalated From |
|-------|----------|-------------|----------------|
| `COMB.RACE.01` | `S1` | `RESP.IPC.01` x `SVC.SHUT.01`: piped follow-up messages become routinely lossy during restart windows. | `S2` + `S2` |
| `COMB.SILENT.01` | `S1` | `OBS.LOG.02` x `CTR.PARSE.01`: parse-failure-as-success plus no outbound DB record creates a dropped response with no durable audit trail. | `S2` + `S2` |
| `COMB.SILENT.02` | `S1` | `OBS.LOG.01` x `OBS.LOG.02`: broken fleet pairing plus no outbound SQLite record makes response absence fundamentally ambiguous in postmortems. | `S2` + `S2` |
| `COMB.BOUNDARY.01` | `S1` | `RESP.IPC.01` x `CTR.PARSE.01`: host commits input early and accepts output too loosely across the host/container boundary. | `S2` + `S2` |
| `COMB.CASCADE.01` | `S1` | `RESP.BOUNDARY.01` x `SVC.SHUT.01` x `OBS.LOG.02`: stalled upstream turn plus restart abandonment plus no outbound record collapses into a silent hard non-response. | `S3` + `S2` + `S2` |

## Metrics

| Metric | Value |
|--------|-------|
| Total COMB findings | 5 |
| Escalated findings | 5 |
| Net severity delta | +5 |
| Most connected finding | `OBS.LOG.02` (3) |
