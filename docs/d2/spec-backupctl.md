# backupctl — Structured Backup Policy

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NOW
**Effort:** ~15 agent-min + ~15 human-min review

---

## Purpose

Structured backup policy for high-value, low-redundancy data. Git covers text files (memory notes, YAML items, source code), but SQLite databases and binary state aren't version-controlled.

## Backup Targets

| Target | Path | Why |
|--------|------|-----|
| `memory` | `memory/` | Note corpus — git-tracked but backup adds safety |
| `store` | `store/*.db` | SQLite databases (messages, sessions, tracking) — NOT git-tracked |
| `queue` | `queue/items/` | nightctl items — git-tracked but backup adds safety |
| `groups` | `groups/*/` | Per-group CLAUDE.md and config — git-tracked |
| `config` | `.env`, `memctl.yaml`, `cronctl.yaml` | Runtime configuration |

**Critical targets:** `store` (SQLite databases are the only data that's not in git and not recoverable).

## CLI Interface

```
backupctl targets                        # list backup targets and policies
backupctl run [--target TARGET]          # run backup (all targets or specific)
backupctl list [--target TARGET]         # list available snapshots
backupctl verify [--target TARGET]       # verify backup integrity
backupctl restore --target T --snapshot S # restore from snapshot
backupctl summary                        # one-liner for briefing integration
```

## Backup Engine

Use `restic` as the backend:
- Deduplication, compression, encryption at rest
- Supports local, S3, SFTP, rclone backends
- Snapshot-based with efficient incremental backups
- Built-in integrity verification

Fallback: if restic isn't installed, use `sqlite3 .backup` for databases + `tar` for directories.

## Configuration

`backupctl.yaml`:
```yaml
repository: /home/mrkai/backups/nanoclaw  # restic repo path
password_file: /home/mrkai/.backupctl-password

targets:
  store:
    paths: ["store/"]
    schedule: "0 */6 * * *"   # every 6 hours
    retain: { hourly: 24, daily: 30, weekly: 12 }
  memory:
    paths: ["memory/"]
    schedule: "0 0 * * *"     # daily
    retain: { daily: 30, weekly: 12, monthly: 12 }
  config:
    paths: [".env", "memctl.yaml", "cronctl.yaml", "backupctl.yaml"]
    schedule: "0 0 * * 0"     # weekly
    retain: { weekly: 12, monthly: 12 }
```

## SQLite Safety

SQLite databases must be backed up safely (not just copied while the process has a write lock):

```python
import sqlite3
conn = sqlite3.connect(db_path)
backup_conn = sqlite3.connect(backup_path)
conn.backup(backup_conn)  # atomic, consistent backup
```

`backupctl` uses `sqlite3.backup()` before handing the consistent copy to restic.

## Module Structure

```
halos/backupctl/
  __init__.py
  cli.py          # argparse, subcommands
  config.py       # load backupctl.yaml, target definitions
  engine.py       # restic wrapper, sqlite backup, tar fallback
  briefing.py     # text_summary() for briefing integration
```

## Integration Points

- pyproject.toml — add `backupctl = "halos.backupctl.cli:main"`
- cronctl — register backup schedules
- briefings — "backupctl: last backup 2h ago, 3 snapshots, 1.2 GB total"
- statusctl — include "last backup age" in health checks

## What It Does NOT Do

- Cloud sync (that's a configuration choice for the restic repository backend)
- Backup the Docker image or container state (rebuild via `container/build.sh`)
- Backup the Node.js source code (that's git)

## Testing

- Unit tests for config loading and target resolution
- Integration test: backup + verify + restore cycle with a test SQLite database
- Edge case: restic not installed → graceful fallback to sqlite3.backup + tar
