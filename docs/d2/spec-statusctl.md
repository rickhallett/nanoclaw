---
title: "statusctl — Fleet Health Monitoring"
category: spec
status: active
created: 2026-03-21
---

# statusctl — Fleet Health Monitoring

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NOW
**Effort:** ~20 agent-min + ~15 human-min review

---

## Purpose

Unified health check across all NanoClaw subsystems. Replaces the current pattern of manually running `halctl smoke` + `logctl` + `docker ps` + `systemctl status` to diagnose issues.

`statusctl check` returns exit 0 if everything's green, exit 1 with structured failure details.

## CLI Interface

```
statusctl [--json]                       # full health report
statusctl check                          # exit 0/1 gate (for cron/scripts)
statusctl metrics [--json]               # host resource snapshot
statusctl report                         # one-liner for briefing integration
```

## Health Checks

### Service Layer
- `systemctl --user is-active nanoclaw` — main process running?
- Credential proxy listening on port 3001? (`ss -tlnp | grep 3001`)
- Docker daemon reachable? (`docker info`)

### Container Layer
- Running containers: `docker ps --format json`
- Container resource usage: `docker stats --no-stream --format json`
- Recent container exits with non-zero codes: `docker ps -a --filter "exited!=0"`

### Agent Layer
- Active sessions from agentctl: count, age, spin detection flags
- Recent errors from logctl: error count in last hour, last 24h
- Queue depth: pending items in group queues

### Host Layer
- CPU: `/proc/loadavg`
- Memory: `/proc/meminfo` (used/total/available)
- Disk: `df` for store/, memory/, and Docker volumes
- Uptime: `/proc/uptime`

## Output Format

Terminal (default):
```
NanoClaw Health — 2026-03-21 14:30 UTC

  Service     nanoclaw          ● running (uptime: 3d 12h)
  Service     credential-proxy  ● listening :3001
  Service     docker            ● running

  Containers  2 running, 0 exited-error
  Sessions    3 active, 0 spinning
  Errors      2 in last hour, 14 in 24h

  Host        CPU 12% | RAM 4.2/16 GB | Disk 45% (store: 1.2 GB)

  Status: HEALTHY
```

`statusctl check` exit codes:
- 0: all checks pass
- 1: one or more checks failed (failures on stderr as JSON)

Briefing one-liner:
```
statusctl: HEALTHY | 2 containers, 3 sessions, 2 errors/hr | CPU 12%, RAM 26%, Disk 45%
```

## Module Structure

```
halos/statusctl/
  __init__.py
  cli.py          # argparse, subcommands
  checks.py       # ServiceCheck, ContainerCheck, AgentCheck, HostCheck
  engine.py       # run all checks, aggregate, determine HEALTHY/DEGRADED/DOWN
  briefing.py     # text_summary() for briefing integration
```

## Health Grades

- `HEALTHY` — all checks pass
- `DEGRADED` — non-critical failures (high error rate, elevated resource usage)
- `DOWN` — critical failures (service not running, Docker unreachable, disk >95%)

Thresholds are configurable via a `statusctl.yaml` config file (optional, sensible defaults).

## Dependencies

- `psutil` (for cross-platform resource metrics, fallback to /proc parsing)
- logctl, agentctl (internal imports)
- No new external services

## Integration Points

- `briefings/gather.py` — add `statusctl.briefing.text_summary()` to `BriefingData`
- `dashctl/panels.py` — add a health status panel
- pyproject.toml — add `statusctl = "halos.statusctl.cli:main"`
- cronctl — optional: `statusctl check` as a periodic health probe

## What It Does NOT Do

- Fix problems (it reports, doesn't remediate)
- Replace halctl smoke (smoke tests capabilities; statusctl monitors ongoing health)
- Send alerts directly (briefings handle delivery)

## Testing

- Unit tests for each check with mocked subprocess output
- Integration test: verify aggregation logic and grade computation
- Edge cases: Docker not installed, systemd not available (graceful degradation)
