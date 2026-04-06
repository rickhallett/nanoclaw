---
title: "Migration Manifest — Path Dependency Map"
category: reference
status: active
created: 2026-04-06
---

# Migration Manifest — Path Dependency Map

Companion to [repo-structure-audit-2026-04-06.md](repo-structure-audit-2026-04-06.md). This document maps every file that references a path that would change under reorganisation, what breaks if it moves, and in what order to execute.

History rewriting tool: **BFG Repo-Cleaner only**. `git-filter-repo` is banned.

---

## 0. Execution Log

| Phase | Commit | What happened |
|-------|--------|---------------|
| Option A sweep | `ada9e67` | Gitignore hardened, tracked debris removed (boot-review, nanoclaw.db), CI nanoclaw ghost fixed, CLAUDE.md gateway contradiction resolved |
| Heritage deletion | `c70c8ca` | `gateway/` (97 files), `agent/steer/` (28 files), `agent/drive/` (18 files) removed. −24,590 LOC. Makefile, README, CLAUDE.md, CI updated. |
| Argo auto-sync | disabled | `kubectl patch application halo-fleet -n argocd --type=merge -p '{"spec":{"syncPolicy":null}}'` — confirmed empty syncPolicy |
| Pre-cleanup rollback | `1755ba1` | Full rollback point (before any cleanup) |

### Directories removed in heritage deletion

| Directory | Files | LOC | Why |
|-----------|-------|-----|-----|
| `gateway/` | 97 | ~10,600 | Nanoclaw-era Node.js gateway. Superseded by Hermes + K8s fleet. |
| `agent/steer/` | 28 | ~2,800 | Swift OCR browser automation. Superseded by CDP. |
| `agent/drive/` | 18 | ~1,200 | tmux process orchestrator. Superseded by `agent/listen`. |
| `.github/workflows/bump-version.yml` | 1 | 42 | Gateway-era package.json bumper. Dead without gateway. |

### References cleaned

| File | What changed |
|------|-------------|
| `CLAUDE.md` | Removed gateway file map, HAL-prime from topology, updated to 2-surface model |
| `README.md` | Updated architecture (K8s fleet replaces gateway), repo structure, requirements |
| `Makefile` | Removed `gateway-*` targets and `test-todoctl` |
| `update-tokens.yml` | Retargeted from `src/**/*.ts` to `halos/**/*.py` + `infra/**` |

### Still outstanding (wave 2 candidates)

- 22 `.claude/skills/` files reference `src/` paths — upstream Halo skills, now dormant
- `groups/telegram_main/CLAUDE.md` references container mounts rooted in gateway architecture
- `groups/global/CLAUDE.md` references gateway mount paths
- BFG scrub assessment: check `gateway/` git history for any committed secrets before the gitignore era

---

## 1. Critical Path: Argo CD Sync

The single most dangerous path reference in the repo.

| File | Reference | Value | Impact |
|------|-----------|-------|--------|
| `infra/k8s/fleet/argocd-app.yaml` | `spec.source.path` | `infra/k8s/fleet` | **FLEET GOES DARK** if moved |
| `infra/k8s/fleet/argocd-app.yaml` | `spec.source.repoURL` | `https://github.com/rickhallett/halo.git` | Repo rename breaks sync |
| `infra/k8s/fleet/argocd-app.yaml` | `spec.source.targetRevision` | `feat/containerisation` | Branch rename breaks sync |

**Migration rule**: Update Argo CD app BEFORE moving manifests, or fleet desync.

---

## 2. Container Image Paths (Baked into Docker layers)

These paths are hardcoded in Docker images. Changing them requires a full image rebuild + fleet redeploy.

### Root Dockerfile (fleet image)

| Path | Purpose | Consumers |
|------|---------|-----------|
| `/opt/hermes` | Hermes agent install dir | entrypoint.sh, all pods |
| `/opt/venv` | Python venv | PATH in all pods |
| `/opt/venv/bin` | venv binaries | PATH env var |
| `/opt/halos/` | Halos package install | PYTHONPATH in all pods |
| `/opt/entrypoint.sh` | Container entrypoint | All pod specs |
| `/opt/data` | Data volume mount point | HERMES_HOME, all pods |
| `/opt/defaults/config.yaml` | Default config | entrypoint.sh fallback |
| `/opt/defaults/system-prompt.md` | Default prompt | entrypoint.sh fallback |

### Dockerfile.halos (init container image)

| Path | Purpose | Consumers |
|------|---------|-----------|
| `/halos/` | Halos package | Init container COPY source |
| `/target/` | Overlay target | Init container mount point |

### Dockerfile COPY sources (repo-relative)

| COPY Source | Dockerfile | Would Break If Moved |
|-------------|-----------|---------------------|
| `vendor/hermes-agent/pyproject.toml` | Root | YES |
| `vendor/hermes-agent/package.json` | Root | YES |
| `vendor/hermes-agent/` | Root | YES |
| `pyproject.toml` | Root, Dockerfile.halos | YES |
| `halos/` | Root, Dockerfile.halos | YES |
| `docker/entrypoint.sh` | Root | YES |
| `docker/defaults/` | Root | YES |

### Gateway Dockerfile (gateway/container/Dockerfile)

| COPY Source | Purpose |
|-------------|---------|
| `container/agent-runner/package*.json` | Agent runner deps |
| `container/agent-runner/` | Agent runner source |
| `pyproject.toml` | Halos install |
| `halos/` | Halos package |
| `container/himalaya-config.toml` | Email config |

---

## 3. K8s Pod Mount Points (All 7 Advisors)

Every advisor deployment uses an identical mount pattern. Changing any of these requires updating all 7 deployments + the base template.

| Container Path | Source | Used By |
|----------------|--------|---------|
| `/opt/defaults/config.yaml` | ConfigMap | All 7 advisors |
| `/opt/defaults/system-prompt.md` | ConfigMap | All 7 advisors |
| `/opt/data/.env` | Secret | All 7 advisors |
| `/opt/halos-overlay/halos` | Init container (Dockerfile.halos) | All 7 advisors |
| `/opt/data/store` | NFS subPath | All 7 advisors |
| `/opt/data/sessions` | NFS subPath | All 7 advisors |
| `/opt/data/logs` | NFS subPath | All 7 advisors |
| `/opt/config/memctl.yaml` | ConfigMap | All 7 advisors |
| `/memory` | NFS mount | All 7 advisors (memctl) |
| `/opt/data/heartbeat` | Liveness probe | All 7 advisors |
| `/opt/data/data/observations/aura` | NFS subPath | Musashi, Machiavelli |
| `/opt/data/data/advisors/` | ConfigMap | Machiavelli, Medici |
| `/opt/data/data/finance/ark-accounting/` | NFS subPath | Medici only |

**Migration rule**: These are container-internal paths. They only change if you restructure the Docker image layout. Repo moves don't affect them unless Dockerfile COPY sources change.

---

## 4. CI Workflow Path References

### .github/workflows/build-fleet.yaml

| Trigger/Path | Value |
|-------------|-------|
| paths trigger | `Dockerfile`, `halos/**`, `pyproject.toml`, `docker/**`, `data/advisors/**` |
| build context | `.` (repo root) |

### .github/workflows/build-halos.yml

| Reference | Value |
|-----------|-------|
| build context | `.` |
| Dockerfile | `Dockerfile.halos` |

### .github/workflows/build-image.yml

| Reference | Value |
|-----------|-------|
| validation | `vendor/hermes-agent/pyproject.toml` |
| build context | `.` |
| trivy ignore | `.trivyignore` |

### .github/workflows/bump-version.yml

| Trigger | Value |
|---------|-------|
| paths | `src/**`, `container/**` |
| files | `package.json`, `package-lock.json` |

### .github/workflows/update-tokens.yml

| Trigger/Include | Value |
|----------------|-------|
| paths | `src/**`, `container/**`, `launchd/**`, `CLAUDE.md` |
| token count includes | `src/**/*.ts`, `container/agent-runner/src/**/*.ts`, `container/Dockerfile`, `container/build.sh`, `launchd/com.nanoclaw.plist`, `CLAUDE.md` |
| output | `repo-tokens/badge.svg`, `README.md` |

**Note**: `launchd/com.nanoclaw.plist` — nanoclaw ghost in CI.

---

## 5. Python Package Paths

### Entry Points (pyproject.toml — 23 console_scripts)

All resolve via `halos.{module}.cli:main`. These survive any repo directory move as long as:
1. `halos/` package stays at the same relative path to `pyproject.toml`
2. `uv sync` is re-run after moves

```
memctl, nightctl, cronctl, logctl, reportctl, agentctl,
hal-briefing, halctl, observe, trackctl, dashctl, mailctl,
calctl, statusctl, backupctl, blogctl, ledgerctl, docctl,
watchctl, secretctl, journalctl, hal
```

### Path Resolution Hub: `halos/common/paths.py`

**This is the single most important file for Option B/C migrations.**

```
store_dir() priority:
  1. HALO_STORE_DIR env var
  2. HERMES_HOME/store (container mode)
  3. cwd/store (local mode)

repo_root() priority:
  1. HERMES_HOME (if store/ exists under it)
  2. cwd
```

Modules using `store_dir()`: mailctl, ledgerctl, trackctl, eventsource, journalctl.
Modules using `repo_root()`: journalctl (for cache dir).

### Hardcoded Absolute Path

| File | Path | Impact |
|------|------|--------|
| `cron/crontab.generated` | `/Users/mrkai/code/halo` | All cron jobs break if repo moves |

**Migration rule**: Run `cronctl install --execute` after any repo move to regenerate.

---

## 6. YAML Config Path Web

All configs use relative paths resolved from `config_path.parent` (the directory containing the YAML file). Currently all configs sit at repo root, so all `./` paths resolve from repo root.

```
briefings.yaml ──→ ./memctl.yaml
                ──→ ./nightctl.yaml
                ──→ ./todoctl.yaml (DEAD — todoctl retired)
                ──→ ./logctl.yaml
                ──→ ./data/ipc
                ──→ ./store/messages.db

reportctl.yaml ──→ ./memctl.yaml
               ──→ ./nightctl.yaml
               ──→ ./todoctl.yaml (DEAD — todoctl retired)

cronctl.yaml   ──→ ./cron, ./cron/jobs, ./cron/crontab.generated, ./logs/cron

nightctl.yaml  ──→ ./queue, ./queue/items, ./queue/MANIFEST.yaml
               ──→ ./queue/archive, ./queue/runs, ./queue/plans
               ──→ ./data/ipc

memctl.yaml    ──→ ./memory, ./memory/INDEX.md, ./memory/archive, ./memory/backlinks

logctl.yaml    ──→ ./logs, ./logs/halo.log, ./logs/halo.error.log
               ──→ ./logs/halos.log, ./logs/supervisor.log, ./data

agentctl.yaml  ──→ ./data/agent-sessions, ./groups/*/logs/, ./data/api-usage.jsonl

watchctl.yaml  ──→ ./store/watch.db, ./rubrics/watchctl-triage.yaml

todoctl.yaml   ──→ ./backlog, ./backlog/items (DEAD — todoctl retired)
```

**Migration rule for Option B (move configs to `config/`)**: All `./` paths become `../` paths, OR update `base_dir` logic in each module's `config.py` to resolve from repo root instead of config file parent. The second approach is cleaner.

---

## 7. Documentation Path References

### CLAUDE.md (highest impact — loaded every session)

58 internal path references. Key clusters:

| Cluster | Paths Referenced | Count |
|---------|-----------------|-------|
| Module locations | `halos/memctl/`, `halos/nightctl/`, etc. | 12 |
| Doc links | `docs/d1/*`, `docs/d2/*` | 22 |
| Store/data | `store/*.db`, `data/advisors/`, `memory/` | 8 |
| Agent defs | `.claude/agents/*.md`, `.claude/commands/*.md` | 14 |
| Gateway | `src/`, `gateway/` (NOTE: contradicts "not in checkout") | 2 |

### Group CLAUDE.md files (container context)

| File | Key Paths |
|------|-----------|
| `groups/global/CLAUDE.md` | `/workspace/project/memory/INDEX.md`, `halos/halctl/`, `templates/microhal/profiles/` |
| `groups/telegram_main/CLAUDE.md` | `/workspace/project`, `/workspace/group`, `/workspace/ipc`, `/workspace/fleet`, `groups/telegram_main/`, `~/code/halfleet/` |
| `groups/main/CLAUDE.md` | Similar container mount references |

### Agent/Command definitions

| File | References |
|------|-----------|
| `.claude/agents/agent-organizer.md` | `CLAUDE.md`, `memory/INDEX.md`, `docs/d1/halos-modules.md`, `.claude/agents/`, `.claude/commands/` |
| `.claude/agents/documentation-expert.md` | `docs/d1/`, `docs/d2/`, `docs/d3/`, `CLAUDE.md`, `groups/*/CLAUDE.md`, 6 specific doc files |
| `.claude/agents/debugger.md` | `logs/halo.log`, `logs/halos.log`, `groups/{name}/logs/container-*.log` |
| `.claude/agents/strategic-analyst.md` | `docs/d2/analysis-{topic}.md`, `memory/INDEX.md` |
| `.claude/agents/claude-md-mirror.md` | `templates/microhal/base.md`, `templates/microhal/profiles/*.yaml`, `store/messages.db` |

### Skills (Halo upstream skills)

17 skill files reference `src/` paths (gateway TypeScript). These only matter if gateway is active.

---

## 8. Monitoring Paths

| File | Reference | Purpose |
|------|-----------|---------|
| `infra/k8s/monitoring/promtail-values.yaml` | `http://loki.monitoring.svc.cluster.local:3100/loki/api/v1/push` | Log shipping |
| `infra/k8s/monitoring/prometheus-values.yaml` | `http://loki.monitoring.svc.cluster.local:3100` | Grafana datasource |

These are cluster-internal DNS. Not affected by repo moves.

---

## 9. Makefile Targets

| Target | Path Reference |
|--------|---------------|
| `test` | `tests/` |
| `coverage` | `halos` (package name) |
| `test-gateway` | `gateway` (cd) |
| `test-memctl` | `tests/memctl/` |
| `test-nightctl` | `tests/nightctl/` |
| `test-cronctl` | `tests/cronctl/` |
| `test-todoctl` | `tests/todoctl/` |

---

## 10. Missed in First Pass (Added After Review)

References discovered on second sweep that the initial four traces missed.

### 10a. Git Submodule

| File | Reference | Impact |
|------|-----------|--------|
| `.gitmodules` | `vendor/hermes-agent` | Submodule path — build breaks if vendor/ moves |

### 10b. UV Workspace Member

| File | Reference | Impact |
|------|-----------|--------|
| `pyproject.toml` | `[tool.uv.workspace] members = ["data/finance/ark-accounting"]` | `uv sync` fails if data/ moves |

### 10c. LaunchD Service Config

| File | Reference | Impact |
|------|-----------|--------|
| `gateway/launchd/com.halo.plist` | `{{PROJECT_ROOT}}/dist/index.js` | Service won't start |
| `gateway/launchd/com.halo.plist` | `{{PROJECT_ROOT}}/logs/halo.log` | Stdout lost |
| `gateway/launchd/com.halo.plist` | `{{PROJECT_ROOT}}/logs/halo.error.log` | Stderr lost |
| `gateway/setup/service.ts` | `${projectRoot}/logs/halo.log` | Bootstrap log paths |
| `gateway/setup.sh` | `$PROJECT_ROOT/logs/setup.log` | Setup fails silently |

### 10d. Gemini Bridge

| File | Reference | Impact |
|------|-----------|--------|
| `infra/gemini-bridge/bridge.py` | `./GEMINI.md` (relative) | Persona prompt lost |
| `infra/gemini-bridge/bridge.py` | `REPO_ROOT / ".venv" / "bin"` | Halos tools unavailable |
| `infra/gemini-bridge/bridge.py` | `REPO_ROOT / "store"` | State tracking fails |

### 10e. Container Agent Runner (workspace mounts)

Hardcoded paths inside the container agent runtime — not affected by repo moves but critical for container layout changes.

| File | Reference | Impact |
|------|-----------|--------|
| `gateway/container/agent-runner/src/index.ts` | `/workspace/global/CLAUDE.md` | Agent context missing |
| `gateway/container/agent-runner/src/index.ts` | `/workspace/ipc/input` | IPC queue breaks |
| `gateway/container/agent-runner/src/index.ts` | `/workspace/group/conversations` | Conversation history lost |
| `gateway/container/Dockerfile` | `container/agent-runner/` | COPY source |
| `gateway/container/Dockerfile` | `container/himalaya-config.toml` | Email config COPY |

### 10f. Fleet Provisioning

| File | Reference | Impact |
|------|-----------|--------|
| `halos/halctl/provision.py` | `container/skills` (symlink target) | Fleet skills unavailable |
| `gateway/halfleet/fleet-config.yaml` | `~/code/halo` (hardcoded) | Fleet provisioning fails |

### 10g. Agent Listen Server

| File | Reference | Impact |
|------|-----------|--------|
| `agent/listen/main.py` | `Path(__file__).parent / "jobs"` | Job state directory |
| `agent/listen/justfile` | `../../.claude/skills` | Relative path to skills |
| `agent/listen/justfile` | `../../.claude/commands/listen-drive-and-steer-user-prompt.md` | Relative path to command |
| `agent/listen/justfile` | `../../.claude/agents/listen-drive-and-steer-system-prompt.md` | Relative path to agent |

### 10h. Rubrics

| File | Reference | Impact |
|------|-----------|--------|
| `watchctl.yaml` | `./rubrics/watchctl-triage.yaml` | Triage rules not found |
| `halos/watchctl/config.py` | `./rubrics/watchctl-triage.yaml` (default) | Same |

### 10i. Miscellaneous

| File | Reference | Impact |
|------|-----------|--------|
| `halyt` (root) | `halos.halyt.cli` import | Shim CLI breaks |
| `scripts/git-pulse.sh` | `${HOME}/code` | Hardcoded scan root |

---

## 11. Nanoclaw Ghost References

| File | Reference | Action |
|------|-----------|--------|
| `store/nanoclaw.db` | Dead database | Delete |
| `data/nanoclaw.db` | Dead database | Delete |
| `gateway/nanoclaw.db` | Empty file | Delete |
| `logs/nanoclaw.log` | Dead log | Delete |
| `logs/nanoclaw.error.log` | Dead log | Delete |
| `.github/workflows/update-tokens.yml` | `launchd/com.nanoclaw.plist` | Update reference |
| `briefings.yaml` | `./todoctl.yaml` | Remove dead ref |
| `reportctl.yaml` | `./todoctl.yaml` | Remove dead ref |

---

## 12. Migration Execution Order

### Option A (Surgical Cleanup) — Safe order

```
Phase 1: Gitignore additions (no file deletions yet)
  1. Update .gitignore with: **/.venv/, **/.build/, **/node_modules/,
     **/dist/, cookies.txt, *.pdf, repomix-output.xml, **/*.html (root only)
  2. git rm --cached (remove from tracking, keep on disk):
     - agent/direct/.venv/
     - agent/listen/.venv/
     - agent/drive/.venv/
     - infra/gemini-bridge/.venv/
     - jobctl/.venv/
     - agent/steer/.build/
     - gateway/node_modules/
     - gateway/dist/
     - data/advisors/quiz-app/node_modules/
     - infra/terraform/.terraform/
  3. Verify: pytest passes, cron still works

Phase 2: Security items
  4. git rm groups/telegram_main/logs/container-*.log
  5. git rm cookies.txt
  6. Audit logs for secrets → if found, BFG scrub

Phase 3: Debris removal
  7. git rm kent-beck-test-driven-development-by-example.pdf
  8. git rm repomix-output.xml
  9. git rm pi-session-*.html
  10. git rm todoctl.yaml
  11. git rm store/nanoclaw.db data/nanoclaw.db gateway/nanoclaw.db
  12. git rm logs/nanoclaw.log logs/nanoclaw.error.log

Phase 4: Dead reference cleanup
  13. Remove todoctl.yaml refs from briefings.yaml and reportctl.yaml
  14. Update nanoclaw plist ref in update-tokens.yml
  15. Resolve CLAUDE.md gateway contradiction (update "not in this checkout" line)

Phase 5: Stale directory archival
  16. git rm -r backlog/ (todoctl retired)
  17. Decide: archive queue/archive/ to docs/d3/ or delete
  18. Clear completed agent/listen/jobs/
  19. Prune agent/specs/ old versions

Phase 6: Verification
  20. pytest
  21. make test
  22. cronctl install --execute (regenerate crontab)
  23. Verify .gitignore covers all new patterns
```

### Option B additions (if pursued later)

```
Phase 7: Config consolidation
  24. Create config/ directory
  25. Move 7 root YAMLs to config/
  26. Update base_dir resolution in each module's config.py to use repo_root()
  27. Update briefings.yaml and reportctl.yaml cross-references
  28. cronctl install --execute

Phase 8: Docker consolidation
  29. Move docker/ contents into infra/docker/
  30. Move root Dockerfile and Dockerfile.halos into infra/docker/
  31. Update .github/workflows/ build contexts and file references
  32. Update container/build.sh references
  33. Test image build

Phase 9: Data consolidation
  34. Move templates/ to data/templates/
  35. Update groups/global/CLAUDE.md template refs
  36. Update .claude/agents/claude-md-mirror.md template refs
  37. pytest
```

### Option C additions (if pursued later)

```
Phase 10: Package workspace
  38. Create packages/ directory
  39. Move halos/ to packages/halos/
  40. Move jobctl/ to packages/jobctl/
  41. Update pyproject.toml package paths
  42. Update all Dockerfile COPY sources
  43. Update all CI workflow paths
  44. uv sync
  45. cronctl install --execute
  46. Update Argo CD app source path
  47. Full fleet redeploy
  48. pytest
  49. Verify all cron jobs
  50. Update CLAUDE.md (all 58 path references)
  51. Update all agent/command/skill definitions
```
