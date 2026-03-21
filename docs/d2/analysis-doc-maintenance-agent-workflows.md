---
title: "Analysis: Automated Documentation Maintenance Agent Workflows"
category: analysis
status: active
created: 2026-03-15
---

# Analysis: Automated Documentation Maintenance Agent Workflows

**Date:** 2026-03-21
**Analyst:** Strategic Analyst (HAL)
**Scope:** Drift inventory, proposed agent workflows, architecture sketch, priority ranking

---

## 1. Drift Inventory

A systematic comparison of documentation claims against actual codebase state. Organised by severity.

### 1.1 CLAUDE.md — System Schematic LOC Claims

The schematic embeds line counts as inline annotations (e.g., `container-runner.ts:833`). Most are now stale.

| File | Claimed | Actual | Delta |
|------|---------|--------|-------|
| `container-runner.ts` | :833 | :868 | +35 |
| `container/agent-runner/src/index.ts` | :657 | :668 | +11 |
| `credential-proxy.ts` | :251 | :294 | +43 |
| `config.ts` | :94 | :97 | +3 |
| `registry.ts` | :31 | :30 | -1 |

Files that are currently accurate: `telegram.ts` (:582), `gmail.ts` (:374), `group-queue.ts` (:430), `task-scheduler.ts` (:286), `ipc-mcp-stdio.ts` (:338), `ipc.ts` (:465), `router.ts` (:52), `mount-security.ts` (:419), `sender-allowlist.ts` (:146), `db.ts` (:773), `types.ts` (:107).

### 1.2 CLAUDE.md — Aggregate LOC Claims

| Claim | Actual | Status |
|-------|--------|--------|
| "NanoClaw Runtime (Node.js, src/ ~10,600 LOC)" | src/*.ts = 10,704 (with tests) or ~8,633 (non-test) | Approximately correct if including test files |
| "Halos Python Tooling (halos/, ~17,200 LOC)" | 22,580 LOC across all modules | **Stale.** 31% growth since last update |

### 1.3 CLAUDE.md — Per-Module LOC Claims

| Module | Claimed | Actual | Delta |
|--------|---------|--------|-------|
| halctl | :4321 | 5,977 | +1,656 (38% growth) |
| nightctl | :2452 | 3,172 | +720 (29% growth) |
| memctl | :1167 | 1,502 | +335 (29% growth) |
| briefings | :818 | 1,397 | +579 (71% growth) |
| logctl | :831 | 1,307 | +476 (57% growth) |
| reportctl | :801 | 801 | 0 (exact) |
| agentctl | :555 | 776 | +221 (40% growth) |
| trackctl | :728 | 728 | 0 (exact) |
| cronctl | :519 | 519 | 0 (exact) |
| dashctl | (not claimed) | 388 | N/A — missing from schematic |

### 1.4 CLAUDE.md — Missing Modules

Five modules exist in `pyproject.toml` console_scripts AND have implementations in `halos/` but are **absent from CLAUDE.md's module table**:

| Module | LOC | Has CLI | Has Briefing Integration |
|--------|-----|---------|--------------------------|
| mailctl | 606 | Yes | Yes (briefing.py) |
| calctl | 888 | Yes | Yes (briefing.py) |
| statusctl | 689 | Yes | Yes (briefing.py) |
| backupctl | 982 | Yes | Yes (briefing.py) |
| ledgerctl | 1,254 | Yes | Yes (briefing.py) |

Note: mailctl IS documented in CLAUDE.md (has its own API section), but is missing from the halos module table. The other four are completely undocumented in CLAUDE.md.

### 1.5 CLAUDE.md — Channel Claims

The Quick Context section says: "Channels (WhatsApp, Telegram, Slack, Discord, Gmail) are skills that self-register at startup."

**Actual state:** `src/channels/index.ts` imports only Telegram and Gmail. Slack, Discord, and WhatsApp have placeholder comments but no implementations. The README also lists "Telegram, Slack, Discord, Gmail" in its stack diagram.

### 1.6 CLAUDE.md — Schematic Topology

The schematic shows `dashctl` in the halos module listing but does not include it. It also does not include mailctl, calctl, statusctl, backupctl, or ledgerctl — 5 modules totaling 4,419 LOC.

### 1.7 docs/d1/halos-modules.md — Missing Modules

This "module registry" lists only 8 modules (memctl, nightctl, cronctl, todoctl (retired), logctl, reportctl, agentctl, briefings). Missing: halctl, trackctl, dashctl, mailctl, calctl, statusctl, backupctl, ledgerctl. That is 8 modules missing from an 8-module registry — the registry is documenting less than half the codebase.

### 1.8 docs/d1/halos-in-brief.md — Multiple Stale Claims

| Claim | Actual | Issue |
|-------|--------|-------|
| "Seven CLI tools" | 15 console_scripts in pyproject.toml | Off by 2x |
| Lists todoctl as a current tool | todoctl is deprecated, merged into nightctl | Stale |
| "59 notes, 18 backlinks" | 108 notes (INDEX says 111) | 83% growth since last update |
| "539 tests, 91 adversarial findings" | Unknown current count, but likely stale | Needs recount |
| "logctl has no writer" in Known Gaps | All modules emit via hlog() | Fixed but not updated |
| "todoctl needs archive, edit, cancel" | todoctl is retired | Entire gap section is stale |

### 1.9 docs/d2/halos-ecosystem-digest.md — Aspirational Content

This document describes calctl, ledgerctl, backupctl, statusctl capabilities in detail. These modules DO exist now (post initial writing), so the content may be accurate. However, the document was written as a brainstorm/plan document and the stated capabilities have not been verified against the current implementations.

### 1.10 Dockerfile — Missing Symlinks

The Dockerfile (line 80) creates symlinks for: `memctl nightctl cronctl logctl reportctl agentctl halctl trackctl dashctl todoctl hal-briefing mailctl`.

Missing from symlink list: `calctl`, `statusctl`, `backupctl`, `ledgerctl`. These exist in pyproject.toml but are not linked into container `/usr/local/bin/`.

### 1.11 Container LOC in Schematic

The schematic header says "src/ ~10,600 LOC" but does not clarify whether this includes test files and container code. `src/*.ts` = 10,704 (including 4 test files totaling ~2,071 lines). Without tests: ~8,633. The container TS is another 1,006 lines.

---

## 2. Proposed Agent Workflows

### 2.1 Workflow: LOC Drift Scanner

**Purpose:** Detect when line-count annotations in CLAUDE.md schematic diverge from actual file sizes.

**What it checks:**
- Parse CLAUDE.md for `:NNN` LOC annotations and `~N,NNN LOC` aggregate claims
- Run `wc -l` on the referenced files
- Flag any delta exceeding a threshold (suggest: 10% or 20 lines)
- Also check per-module LOC claims in the schematic footer

**Cron schedule:** Weekly, Sunday 03:00 UTC (`0 3 * * 0`)

**PR workflow:**
1. `git worktree add /tmp/doc-loc-scan doc-maintenance/loc-scan-$(date +%Y%m%d)`
2. Run the scanner script, which edits CLAUDE.md in-place with corrected values
3. `git add CLAUDE.md && git commit -m "docs: update LOC annotations in system schematic"`
4. `gh pr create --title "docs: LOC drift corrections" --body "Automated scan found N files with drifted line counts."`
5. `git worktree remove /tmp/doc-loc-scan`

**Notification:** Telegram message to main group: "LOC drift scan complete. PR #N created with M corrections. [link]"

**halos integration:**
- `hlog("doc-agent", "info", "loc_scan_complete", {"files_checked": N, "drifted": M, "pr_url": url})`
- Briefing: morning briefing gather could pull from hlog events tagged `doc-agent`
- logctl: searchable via `logctl search --source doc-agent`

**Estimated scope:** ~10 agent-minutes to build scanner script, ~5 human-minutes to review first PR

---

### 2.2 Workflow: Module Registry Reconciler

**Purpose:** Keep `docs/d1/halos-modules.md`, the CLAUDE.md module table, and `pyproject.toml` console_scripts in sync.

**What it checks:**
- Parse pyproject.toml `[project.scripts]` for the canonical module list
- Parse CLAUDE.md halos module table
- Parse docs/d1/halos-modules.md
- Diff the three lists. Flag: modules in pyproject.toml but not in docs, modules in docs but not in pyproject.toml, modules with mismatched descriptions

**What it generates:**
- Updated halos-modules.md with any missing modules (auto-generates description from module docstrings)
- Updated CLAUDE.md module table entries
- Flags for human review: new modules that need full API documentation sections in CLAUDE.md

**Cron schedule:** Weekly, Sunday 04:00 UTC (`0 4 * * 0`)

**PR workflow:** Same worktree pattern as 2.1.

**Notification:** Telegram message listing added/removed modules.

**halos integration:**
- `hlog("doc-agent", "info", "registry_reconcile", {"added": [...], "removed": [...]})`

**Estimated scope:** ~15 agent-minutes, ~10 human-minutes review

---

### 2.3 Workflow: Channel Claims Auditor

**Purpose:** Verify that channel references in CLAUDE.md and README.md match the actual `src/channels/index.ts` imports.

**What it checks:**
- Parse `src/channels/index.ts` for active imports (not commented-out placeholders)
- Grep CLAUDE.md and README.md for channel name claims
- Flag claims about channels that are not actually imported/registered

**Cron schedule:** Monthly, 1st of month 03:00 UTC (`0 3 1 * *`)

**PR workflow:** Same worktree pattern. Edits the relevant prose to match reality (e.g., "Channels (Telegram, Gmail) are skills..." instead of listing Slack/Discord/WhatsApp).

**Estimated scope:** ~5 agent-minutes, ~5 human-minutes review

---

### 2.4 Workflow: Halos-in-Brief Freshener

**Purpose:** Regenerate the statistics in `docs/d1/halos-in-brief.md` from live data.

**What it checks/generates:**
- Tool count: count console_scripts in pyproject.toml
- Note count: `ls memory/notes/ | wc -l`
- Test count: run pytest --collect-only and count
- Replace the "Seven CLI tools" line with actual count
- Replace the "59 notes" line with actual count
- Remove references to todoctl as a current tool
- Update Known Gaps section (remove items that are fixed, based on grep for the claimed gap)

**Cron schedule:** Weekly, Sunday 05:00 UTC (`0 5 * * 0`)

**Estimated scope:** ~10 agent-minutes, ~5 human-minutes review

---

### 2.5 Workflow: Dockerfile Symlink Auditor

**Purpose:** Ensure the Dockerfile's symlink loop covers all console_scripts from pyproject.toml.

**What it checks:**
- Parse the `for cmd in ...` line in Dockerfile
- Parse pyproject.toml console_scripts
- Flag any delta

**What it generates:** Updated Dockerfile with corrected symlink list.

**Cron schedule:** On-demand or monthly. Low-frequency drift.

**Estimated scope:** ~5 agent-minutes, ~3 human-minutes review

---

### 2.6 Workflow: Full docs-audit.py Run with PR

**Purpose:** Run the existing `docs-audit.py` tool and surface its findings as a structured PR.

**What it does:**
- `python3 docs-audit.py --full --tree > /tmp/audit-output.txt`
- Parse the output for "Potentially stale" and "Potential misplacement" sections
- Generate a summary PR that either:
  (a) moves misplaced files, or
  (b) creates a `docs/d1/audit-findings-YYYY-MM-DD.md` with the raw output and recommendations

**Cron schedule:** Biweekly, 1st and 15th of month (`0 3 1,15 * *`)

**Estimated scope:** ~5 agent-minutes (already has tooling), ~10 human-minutes review

---

## 3. Architecture Sketch

### How these agents compose with the existing ecosystem

```
                    cronctl (schedule)
                        |
                        v
              +---------+---------+
              |  cron triggers    |
              |  doc-agent job    |
              +---+---+---+------+
                  |   |   |
        +---------+   |   +-----------+
        v             v               v
  LOC Scanner   Registry Reconciler   Audit Runner
        |             |               |
        v             v               v
  [git worktree] [git worktree]  [git worktree]
        |             |               |
        +------+------+------+-------+
               |              |
               v              v
         gh pr create    hlog() events
               |              |
               v              v
         Telegram notify  logctl searchable
               |              |
               v              v
         Human reviews    Morning briefing
         merges or        includes summary
         closes PR
```

### Execution Model

Each workflow runs as a **cron job defined via cronctl**. The command is a Python script or shell script that:

1. Creates a git worktree on a dated branch
2. Runs the specific check/scan
3. If drift found: commits changes, pushes branch, creates PR via `gh`
4. Emits hlog events for observability
5. Sends Telegram notification via the NanoClaw channel layer (either direct API call or by writing an IPC message file)
6. Cleans up the worktree

### Key Design Decisions

**Git worktrees, not direct main edits.** Every change goes through PR review. The agent proposes, the human disposes. This matches the existing halos design principle.

**No container needed.** These scripts run on the host, not in agent containers. They need `git`, `gh`, `wc`, `python3`, and access to the repo. Running them in containers would add complexity for no isolation benefit (they only read the codebase and write PRs).

**Notification via hlog + Telegram.** The simplest path is a direct Telegram API call using the bot token already in `.env`. Alternatively, the scripts could write an IPC message file that the NanoClaw orchestrator picks up, but that couples the doc agent to the runtime being up.

**Briefing integration.** The morning briefing `gather.py` already shells out to various tools. Adding a `_get_doc_agent_summary()` function that reads recent hlog events with `source=doc-agent` would surface doc maintenance activity in the daily briefing.

### What NOT to Automate

- **Full CLAUDE.md rewrites.** The schematic is hand-curated and its structure carries meaning beyond the data. Automated updates should touch only the numeric annotations, not the topology.
- **Moving docs between d1/d2/d3.** docs-audit.py flags potential misplacements, but the BFS hierarchy is a judgment call. Surface the finding; don't auto-move.
- **Deleting deprecated docs.** Flag staleness; don't delete. Archive-not-delete is a halos principle.

---

## 4. Priority Ranking

Ranked by drift-caught-per-effort and frequency of the underlying drift.

### Tier 1 — High Value, Low Effort

1. **Module Registry Reconciler** (Workflow 2.2)
   - Catches: 8 missing modules from halos-modules.md, missing CLAUDE.md entries
   - Why first: The module registry is consulted by every new agent session. Wrong registry = wrong tool selection. This is the single most impactful drift today.
   - Effort: ~15 agent-minutes + ~10 human-minutes

2. **LOC Drift Scanner** (Workflow 2.1)
   - Catches: 5 stale LOC annotations, 2 stale aggregate counts
   - Why second: LOC annotations are read by agents to orient in the codebase. The halos aggregate claim is off by 31% (17,200 vs 22,580).
   - Effort: ~10 agent-minutes + ~5 human-minutes

### Tier 2 — Medium Value, Low Effort

3. **Halos-in-Brief Freshener** (Workflow 2.4)
   - Catches: stale tool count, stale note count, stale gap list, references to retired todoctl
   - Effort: ~10 agent-minutes + ~5 human-minutes

4. **Channel Claims Auditor** (Workflow 2.3)
   - Catches: false claims about Slack/Discord/WhatsApp support
   - Lower frequency: channels change rarely
   - Effort: ~5 agent-minutes + ~5 human-minutes

### Tier 3 — Maintenance

5. **Dockerfile Symlink Auditor** (Workflow 2.5)
   - Low frequency drift but high impact when wrong (container agents can't use missing tools)
   - Effort: ~5 agent-minutes + ~3 human-minutes

6. **Full docs-audit.py Run** (Workflow 2.6)
   - Already exists as a manual tool. Wrapping it in a cron+PR flow is incremental value.
   - Effort: ~5 agent-minutes + ~10 human-minutes

---

## 5. Open Questions

1. **Telegram notification mechanism.** Should doc agents call the Telegram API directly (simpler, decoupled from runtime) or write IPC messages (integrates with existing channel layer, but requires runtime to be up)? The direct API call is more robust for a cron job.

2. **PR merge policy.** Should the human always merge manually, or should some low-risk PRs (e.g., LOC-only changes) auto-merge after a delay? Recommend: always manual for now. Trust is earned.

3. **Worktree cleanup.** If a PR is created but not merged for >7 days, should the agent close it and re-scan next cycle? Recommend yes — stale PRs accumulate.

4. **Scanner scripts location.** Propose `halos/docctl/` as a new module, or simpler standalone scripts in `scripts/doc-maintenance/`? Given the cronctl integration and hlog usage, a halos module (`docctl`) would be more consistent with the ecosystem. Note: `docs/d2/spec-docctl.md` already exists (6.9K) — check if it aligns with this design.

5. **Container Dockerfile drift.** The symlink list in Dockerfile is a build-time artifact. The auditor can flag the drift, but fixing it requires a container rebuild (`./container/build.sh`). The PR should include the Dockerfile change AND a note to rebuild.

6. **Test count in halos-in-brief.** Running `pytest --collect-only` requires the venv to be set up. The cron job needs to either run inside the uv venv or call `uv run pytest --collect-only`.

---

## 6. Immediate Fixes (No Agent Needed)

For reference, here are drift items that could be fixed right now without building any automation:

1. CLAUDE.md schematic: `container-runner.ts:833` should be `:868`, `credential-proxy:251` should be `:294`, `agent-runner/index.ts:657` should be `:668`
2. CLAUDE.md schematic footer: `~17,200 LOC` should be `~22,600 LOC`
3. CLAUDE.md schematic footer: update halctl from `:4321` to `:5977`, nightctl `:2452` to `:3172`, memctl `:1167` to `:1502`, briefings `:818` to `:1397`, logctl `:831` to `:1307`, agentctl `:555` to `:776`
4. CLAUDE.md Quick Context: remove "WhatsApp, Slack, Discord" from channel list
5. CLAUDE.md module table: add calctl, statusctl, backupctl, ledgerctl, dashctl
6. `docs/d1/halos-modules.md`: add all missing modules (halctl, trackctl, dashctl, mailctl, calctl, statusctl, backupctl, ledgerctl)
7. `docs/d1/halos-in-brief.md`: update tool count, note count, remove todoctl references, update known gaps
8. `container/Dockerfile` line 80: add `calctl statusctl backupctl ledgerctl` to symlink loop
