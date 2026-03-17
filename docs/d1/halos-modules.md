# halos Module Registry

Operational modules that comprise the HAL agent operating layer.

| Module | Command | Source | Purpose | Status |
|--------|---------|--------|---------|--------|
| memctl | `memctl` | halos/memctl/ | Structured memory: atomic notes, YAML schema, hash-verified index, pruning | Active |
| nightctl | `nightctl` | halos/nightctl/ | Overnight batch jobs: deferred execution, windowed scheduling, run records | Active |
| cronctl | `cronctl` | halos/cronctl/ | Cron management: YAML job definitions, crontab generation, enable/disable | Active |
| todoctl | `todoctl` | halos/todoctl/ | Backlog tracking: prioritised YAML items, status workflow, blocking | Active |
| logctl | `logctl` | halos/logctl/ | Structured log reader: pino parser, search, filters, error summary | Active |
| reportctl | `reportctl` | halos/reportctl/ | Periodic digests: briefing, weekly, health from memctl/todoctl/nightctl | Active |
| agentctl | `agentctl` | halos/agentctl/ | LLM session tracking: usage stats, spinning-to-infinity detection | Active |
| briefings | `hal-briefing` | halos/briefings/ | Cron-driven daily digests: morning briefing (0600) and nightly recap (2100) via Telegram, with Claude synthesis for HAL's voice | Active |

## Shared Design Principles

All modules follow the same conventions:
- Filesystem-first, no database
- YAML schema with controlled vocabulary
- CLI-driven writes, never direct file edits
- Config at repo root ({module}.yaml)
- Derived manifests/indices are rebuildable
- Archive not delete
- --dry-run available on all mutating commands
- --json for machine-readable output
