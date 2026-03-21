---
title: "Responsiveness Review Findings Table"
category: review
status: active
created: 2026-03-20
---

# Responsiveness Review Findings Table

Date: 2026-03-20

| Label | Severity | Summary | Evidence |
|-------|----------|---------|----------|
| `OBS.LOG.01` | `S2` | Fleet conversation pairing still fabricates pm2 dates and drops later responses for the same user turn. | `halos/logctl/fleet.py:177-188`, `halos/logctl/fleet.py:196-207` |
| `OBS.LOG.02` | `S2` | Outbound agent responses are not persisted to SQLite on any primary send path. | `src/db.ts:287-326`, `src/index.ts:217-249`, `src/index.ts:637-658`, `src/channels/telegram.ts:503-528` |
| `RESP.IPC.01 [Additional]` | `S2` | Piped follow-up messages are marked processed before the active container has consumed the IPC file. | `src/index.ts:437-455`, `src/group-queue.ts:160-175`, `container/agent-runner/src/index.ts:276-297`, `src/index.ts:479-489` |
| `CTR.PARSE.01` | `S2` | Streaming parse failures do not fail the turn, so zero-exit containers can resolve success with no visible response. | `src/container-runner.ts:421-449`, `src/container-runner.ts:639-651`, `src/index.ts:254-271` |
| `SVC.SHUT.01` | `S2` | Shutdown abandons active containers and startup cleanup kills survivors, dropping in-flight responses during restarts. | `src/index.ts:511-520`, `src/group-queue.ts:347-363`, `src/container-runtime.ts:103-127`, `~/.config/systemd/user/nanoclaw.service:5-14` |
| `RESP.BOUNDARY.01` | `S3` | Stalled SDK/proxy calls have no local timeout or cancellation path, so hangs last until the outer container timeout fires. | `container/agent-runner/src/index.ts:332-507`, `container/agent-runner/src/index.ts:343-362`, `src/credential-proxy.ts:186-205`, `src/container-runner.ts:477-556` |

## Metrics

| Metric | Value |
|--------|-------|
| Total findings | 6 |
| S1 count | 0 |
| S2 count | 5 |
| S3 count | 1 |
| S4 count | 0 |
