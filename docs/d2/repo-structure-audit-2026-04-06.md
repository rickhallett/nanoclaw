---
title: "Repo Structure Audit"
category: analysis
status: archived
created: 2026-04-06
---

# Repo Structure Audit — 2026-04-06

## Context

The Halo repo has evolved from housing personal infrastructure tooling to describing a full K8s fleet with NATS JetStream event sourcing, six roundtable advisor pods, Argo CD, observability stack, and chaos engineering. This audit maps what's here, what's stale, what's dangerous, and what to do about it.

## 0. Execution Status

Option A + heritage deletion executed in commits `ada9e67` and `c70c8ca`. 144 files removed, −24,590 LOC. `gateway/`, `agent/steer/`, `agent/drive/` burned. Argo auto-sync disabled. See [migration-manifest-2026-04-06.md](migration-manifest-2026-04-06.md) section 0 for full log.

---

## 1. Vital Statistics

| Metric | Count |
|--------|-------|
| Total files (excl .git/.venv/node_modules) | ~3,500 |
| Top-level directories | 26 |
| Dot-directories (config) | 8 |
| Python LOC (halos/) | 28,230 |
| Python LOC (jobctl/) | 2,013 |
| Infra manifests (k8s) | 52 files |
| Docs | 172 files |
| Memory notes | 174 files |

## 2. Directory Health Map

```
halo/
├── .claude/          (64 files)  HEALTHY — agents, commands, skills, evals
├── .pi/              (8 files)   OK — Pi/Copilot skill adapters
├── .opencode/        (1 file)    VESTIGIAL — single agent file
├── .hermes/          (1 file)    MINIMAL — one plan file
├── .github/          (10 files)  HEALTHY — CI workflows
│
├── halos/            (169 files) CORE — Python tooling package, 28K LOC
├── tests/            (122 files) HEALTHY — test suite
├── infra/            (70 files)  GROWING FAST — k8s fleet, terraform, gemini-bridge
│   ├── k8s/fleet/    (44 files)  HOT — all advisor pod manifests, NATS, Argo
│   ├── k8s/archived-fleet/ (3)   OK — retired Socrates manifests
│   ├── k8s/aura/     (1 file)    THIN — just a relay patch
│   ├── k8s/monitoring/ (3 files) OK
│   ├── k8s/base/     (4 files)   OK
│   ├── terraform/    (7+lock)    STABLE — Vultr provisioning
│   └── gemini-bridge/ (6 files)  NEW — experimental Gemini CLI bridge
│
├── agent/            (138 files) SPRAWLING — 4 sub-tools, each with own venv
│   ├── listen/       (41 files)  ACTIVE — job server, 32 job YAMLs in queue
│   ├── drive/        (18 files)  STALE — last commit unclear
│   ├── direct/       (4 files)   MINIMAL
│   ├── steer/        (29 files)  STALE — Swift binary + .build artifacts committed
│   ├── specs/        (21 files)  ACCUMULATING — eBay/WTTJ specs, no cleanup cycle
│   ├── logs/         (12 files)  EPHEMERAL — should not be tracked
│   └── scripts/      (1 file)    ORPHAN — linkedin-auto-apply.py
│
├── gateway/          (6,055 files) PROBLEM — full Node.js app WITH node_modules
│   ├── src/          EXISTS      CONTRADICTS CLAUDE.md ("not in this checkout")
│   ├── node_modules/ COMMITTED   Should be gitignored
│   ├── dist/         COMMITTED   Build output
│   └── halfleet/     (unknown)
│
├── data/             (4,506 files) BLOATED — mostly quiz-app node_modules
│   ├── advisors/     personas + quiz-app with full node_modules tree
│   ├── clients/aura/ system prompt
│   └── nanoclaw.db   ORPHAN — old name
│
├── memory/           (174 files) HEALTHY — memctl-governed
├── store/            (112 files) MIXED — DBs + caches + misc state
├── groups/           (90 files)  BLOATED — 80+ committed container logs
├── docs/             (172 files) WELL-ORGANIZED — d1/d2/d3 hierarchy
├── vendor/           (1,323 files) LARGE — hermes-agent vendored
├── templates/        (61 files)  OK — microHAL personality blocks
├── queue/            (65 files)  STALE — archived nightctl plans/items
├── jobctl/           (28 files)  ACTIVE — job application tooling
├── cron/             (8 files)   OK
├── config-examples/  (4 files)   OK
├── docker/           (4 files)   SMALL — defaults + entrypoint
├── scripts/          (6 files)   MIXED — some useful, some one-off
├── backlog/          (14 files)  STALE — old todoctl items (todoctl retired)
├── notebooklm-sources/ (10 files) ONE-OFF — 350K+ markdown exports
├── logs/             (4 files)   EPHEMERAL — nanoclaw.log still referenced
├── rubrics/          (1 file)    OK
├── media/            (1 file)    OK
└── [root files]      27 files    CLUTTERED
```

## 3. Security Findings

### CRITICAL: Committed container logs (groups/telegram_main/logs/)

80+ container log files from March committed to git. Container logs can contain:
- API keys and tokens passed as environment variables
- User message content (PII)
- Internal hostnames and network topology
- Error traces with credential fragments

These are **in git history permanently** even after deletion. If this repo ever goes public or is shared, this is a data breach.

**Action**: Remove from tracking, add to `.gitignore`. Use BFG Repo-Cleaner (`bfg`) to scrub from git history if any secrets are confirmed in the logs. (`git-filter-repo` is banned in this repo; BFG only.)

### HIGH: cookies.txt at repo root

113KB auth cookie file at repo root. Contains browser session tokens. Not gitignored.

**Action**: Remove immediately, add `cookies.txt` to `.gitignore`.

### HIGH: Committed .venv directories

Five Python virtual environments committed to git:
- `agent/direct/.venv/`
- `agent/listen/.venv/`
- `agent/drive/.venv/`
- `infra/gemini-bridge/.venv/`
- `jobctl/.venv/`

These contain site-packages which may include cached credentials, platform-specific binaries, and inflate repo size significantly.

**Action**: Remove from tracking, ensure `.gitignore` covers `**/.venv/`.

### MEDIUM: Terraform state and provider binaries

`infra/terraform/.terraform/` contains provider binaries and `terraform.tfstate`. State files can contain secrets (API keys, resource IDs).

**Action**: Verify `.terraform/` is gitignored. If `terraform.tfvars` contains secrets, gitignore that too.

## 4. Root-Level Debris

| File | Size | Verdict |
|------|------|---------|
| `kent-beck-test-driven-development-by-example.pdf` | 3.5 MB | **REMOVE** — binary blob, not repo content |
| `repomix-output.xml` | 5.6 MB | **REMOVE** — one-off repo export |
| `pi-session-2026-04-04*.html` | 924 KB | **REMOVE** — ephemeral session dump |
| `cookies.txt` | 113 KB | **REMOVE + GITIGNORE** — sensitive auth cookies |
| `boot-review-codex-20260326-091700.md` | 8.4 KB | **ARCHIVE** to docs/d3/ or remove |
| `CLAUDE.template.md` | 26 KB | **CLARIFY** — 377 lines vs 361 in active CLAUDE.md. Drift? |
| `todoctl.yaml` | small | **REMOVE** — todoctl retired for nightctl |
| `halyt` | 182 B | **CLARIFY** — Python shim, purpose unknown |
| 7 root YAML configs | small | **CONSIDER** consolidating to `config/` |

## 5. Staleness Analysis

### Definitely Stale

| Path | Evidence | Files | Action |
|------|----------|-------|--------|
| `backlog/` | todoctl retired, items from March 16-17 | 14 | Archive to d3/ or delete |
| `queue/archive/` | Archived nightctl plans from March 27 | 65 | Archive to d3/ or delete |
| `agent/steer/.build/` | Swift build cache, committed | 29 | Gitignore + remove |
| `agent/specs/` (drafts) | eBay listing drafts v1-v4, WTTJ specs | ~15 | Prune old versions |
| `agent/listen/jobs/` | 32 job YAMLs sitting in queue | 32 | Clear completed, archive rest |
| `agent/logs/` | Ephemeral job logs | 12 | Gitignore |
| `logs/nanoclaw.*` | Pre-rename name | 3 | Delete |
| `data/nanoclaw.db` | Pre-rename name | 1 | Delete |
| `store/nanoclaw.db` | Pre-rename name | 1 | Delete |
| `store/blogctl.db` | blogctl not in CLAUDE.md modules | 1 | Verify dead, delete |
| `gateway/nanoclaw.db` | Pre-rename, empty file | 1 | Delete |
| `groups/telegram_main/logs/` | March container logs | 80+ | Security issue — see above |

### Probably Stale

| Path | Evidence | Action |
|------|----------|--------|
| `gateway/` (6,055 files) | CLAUDE.md says src/ not in checkout, but it is. Committed node_modules + dist. | Decide: archive or recommit. Fix CLAUDE.md either way. |
| `data/advisors/quiz-app/` | Full Node.js app with ~4,400 node_modules files | Remove node_modules at minimum |
| `notebooklm-sources/` | 10 files, 350K+ of curated markdown for one-off export | Archive or remove |
| `.opencode/` | Single agent file | Verify still used |
| `store/x-accounts.yaml` | X integration config | Verify active |
| `store/wellfound_metrics.jsonl` | Job metrics, 14K | Verify active |

### Actively Growing (watch for sprawl)

| Path | Trajectory | Mitigation |
|------|-----------|------------|
| `infra/k8s/fleet/` | +3-4 files per advisor, 44 now | Consider Kustomize overlays before advisor #10 |
| `docs/d2/` | 101 files, specs and analyses accumulate | Need d2/ → d3/ archive cycle |
| `agent/specs/` | Task specs pile up with version suffixes | Prune completed specs |

## 6. Committed Artifacts That Should Not Be in Git

| Path | Type | Impact |
|------|------|--------|
| `gateway/node_modules/` | npm dependencies | Thousands of files, massive repo bloat |
| `gateway/dist/` | Build output | Reproducible from source |
| `data/advisors/quiz-app/node_modules/` | npm dependencies | ~4,400 files |
| `agent/steer/.build/` | Swift build cache | 29 files of platform-specific artifacts |
| `agent/direct/.venv/` | Python venv | Should never be committed |
| `agent/listen/.venv/` | Python venv | Should never be committed |
| `agent/drive/.venv/` | Python venv | Should never be committed |
| `infra/gemini-bridge/.venv/` | Python venv | Should never be committed |
| `jobctl/.venv/` | Python venv | Should never be committed |
| `infra/terraform/.terraform/` | Provider binaries + state | Binaries + potential secrets |

**Estimated waste**: 10,000+ files, likely 50MB+ of git objects that serve no purpose.

## 7. Naming / Identity Ghosts

The `nanoclaw` → `halo` rename (commit `ca52f1a`, 2026-03-24) left traces:

- `store/nanoclaw.db`
- `data/nanoclaw.db`
- `gateway/nanoclaw.db`
- `logs/nanoclaw.log`
- `logs/nanoclaw.error.log`

All should be removed or renamed.

## 8. Structural Contradictions

| Issue | Detail |
|-------|--------|
| **gateway/ existence** | CLAUDE.md says "src/ is not present in this checkout" — but `gateway/src/` exists with full source. Either the doc is wrong or the directory is vestigial from the nanoclaw era. |
| **Container concerns split 3 ways** | `docker/` (entrypoint + defaults), root `Dockerfile` + `Dockerfile.halos`, `infra/k8s/` (manifests). Three places to look for containerisation context. |
| **Two Dockerfiles at root** | `Dockerfile` and `Dockerfile.halos` — which is canonical for what? |
| **Config file scatter** | 7 YAML configs at root (`agentctl.yaml`, `briefings.yaml`, `cronctl.yaml`, `logctl.yaml`, `memctl.yaml`, `nightctl.yaml`, `reportctl.yaml`) instead of a `config/` directory. |
| **store/ as catch-all** | SQLite DBs, JSONL metrics, YAML configs, eval results, journal caches, application data — all flat in one directory with no schema or README. |

## 9. Reorganisation Options

### Option A: Surgical Cleanup (Low risk)

Remove obvious waste without restructuring. Minimal disruption.

1. Gitignore + remove: all `.venv/`, `.build/`, `node_modules/`, `dist/`, `cookies.txt`
2. Delete root debris: PDF, repomix XML, pi-session HTML, todoctl.yaml
3. Archive stale: `backlog/` → `docs/d3/`, `queue/archive/` → `docs/d3/`
4. Fix nanoclaw ghosts: rename or delete orphan `.db` files
5. Purge `groups/telegram_main/logs/` — security risk
6. Update CLAUDE.md: resolve gateway contradiction

**Pros**: Safe, quick, immediate size reduction. Addresses all security findings.
**Cons**: Doesn't address structural sprawl.

### Option B: Directory Consolidation (Medium risk)

Restructure to match the repo's three-concern model: **tooling**, **infra**, **data**.

```
halo/
├── halos/              # Python tooling (unchanged)
├── infra/
│   ├── k8s/            # All k8s manifests
│   ├── terraform/      # Vultr provisioning
│   ├── docker/         # Merge docker/ + root Dockerfiles + container/
│   ├── gemini-bridge/  # Experimental bridge
│   └── ci/             # GHA workflow reference
├── agent/              # Local agent spawner (clean up sub-venvs)
├── gateway/            # Decide: archive wholesale or fix gitignore
├── data/
│   ├── advisors/       # Personas only (drop quiz-app)
│   ├── clients/        # Client prompts
│   └── templates/      # microHAL blocks (moved from templates/)
├── config/             # All YAML configs (moved from root)
├── store/              # Runtime state (gitignore DBs, add README)
├── docs/               # Unchanged (d1/d2/d3 is solid)
├── tests/              # Unchanged
├── memory/             # Unchanged (memctl-governed)
├── jobctl/             # Unchanged
└── scripts/            # Consolidate useful scripts
```

**Pros**: Clear mental model, halos/ import paths unaffected, config discoverable.
**Cons**: Some CI/cron path references break. Needs a sweep pass.

### Option C: Monorepo Formalisation (Higher risk)

Treat as a proper monorepo with `packages/` workspace boundaries.

**Pros**: Clean workspace isolation, each package independently testable.
**Cons**: Maximum disruption. Import paths change. CI rewritten. Overkill unless planning multi-team or open-source split.

## 10. Recommended Sequence

1. **Immediate** — Option A (surgical cleanup + security fixes)
2. **Next session** — Decide gateway fate (archive vs. recommit with proper gitignore)
3. **When fleet hits 8+ advisors** — Evaluate Kustomize overlays for k8s manifests
4. **Optional** — Cherry-pick Option B consolidation moves (config/, docker/ merge)
