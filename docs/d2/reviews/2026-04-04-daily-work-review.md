---
title: "Daily Work Review — 2026-04-04"
category: review
status: active
created: 2026-04-04
---

# Daily Work Review — 2026-04-04

**Commits:** 5 · **Files:** 36 · **Delta:** +3,482 / −338 · **Window:** 13:34–20:06 BST

## Scope & Cadence

Two substantial features and three quick-follow fixes in ~6.5 hours of active work. High output after a quiet preceding week (zero commits 2nd–3rd). Burst pattern, not sustained rhythm.

## Feature 1: journalctl — Qualitative Journal Module

**Commit:** `268d5f31` · 21 files · +1,841 / −338

New halos module: store, CLI, LLM-synthesised sliding window summaries, 21 passing tests, 250-line spec, advisor integration across all 8 roundtable seats.

### Strengths

- **Content-hash caching** in `window.py` — no TTL to tune, invalidates only when underlying data changes. Multiple consumers (advisors, briefings) pay zero LLM cost after the first synthesis. Compound interest design.
- **Clean separation of concerns.** Store does CRUD. Window does synthesis. CLI wires them. Config is 20 lines.
- **Test coverage is real.** 21 tests in 213 lines, 50ms runtime. Tests-as-documentation.
- **Advisor integration is the high-leverage move.** journalctl feeding into 8 advisor personas with trackctl metrics creates a qualitative-quantitative feedback loop. Musashi's prototype training week (138 lines from Apple Notes) shows context designed for usefulness, not presence.
- **Graceful degradation.** Claude CLI unavailable → raw entries. Empty entries → "Silence is data." Window prompt flags sparse entries as signal.

### Technical Debt

- **TD-1: Subprocess shell-out to `claude` CLI for synthesis.** No retry, no rate limiting, 120s hard timeout. `FileNotFoundError` caught as warning print only. In unattended cron/briefing context, flaky CLI means silently degraded window. Fallback to raw entries is fine for now; wants a proper client eventually.
- **TD-2: CLAUDE.md cleanup bundled with feature commit.** Two concerns in one commit — reverting one means reverting both. Cosmetic but worth noting for future commit hygiene.

## Feature 2: Containerisation Scaffolding

**Commits:** `2ef3ea27`, `d8b3f33f`, `d87567ce`, `2616ad8b` · 19 files · +1,656 / −13

Dockerfile, entrypoint, Kustomize base manifests, CI pipeline, 854-line spec, 328-line review guide. Three follow-up fixes from first real smoke test.

### Strengths

- **Entrypoint is well-considered.** Safe prompt loading via Python (no shell injection from client-authored `system-prompt.md`). WAL mode enforcement on all SQLite databases at startup. Heartbeat wrapper without patching Hermes source. S3 restore on empty PVC.
- **"Fat image, thin config" is correct** for this stage. One image, client repos contain only configuration.
- **K8s manifests are production-grade.** File-mounted secrets (not envFrom), `MUST_BE_PATCHED_BY_OVERLAY` sentinels, config checksum annotation, PVC protection, non-root security context, three-tier probes.
- **Commit sequence tells the right story.** Scaffolding → submodule correction → spec update → connectivity fix after real testing. The fix commit documents exactly what broke and why.
- **Adversarial review taken seriously.** 33 findings, 6 S1 critical, all addressed before merge.

### Technical Debt

- **TD-3: Heartbeat detects process death but not asyncio deadlocks.** Comment acknowledges "revisit with an HTTP health check sidecar." If gateway hangs (not crashes), K8s won't know for up to 120s. Acceptable for single-user; gap for multi-tenant.
- **TD-4: `pip install` in Dockerfile instead of `uv`.** Standing order says "Python uses uv exclusively." Likely practical (Debian base image, upstream Hermes compatibility) but deviation is undocumented. Should be documented as intentional or fixed.
- **TD-5: No automated integration test.** Smoke test was manual (`docker build + run`). CI has Trivy + submodule validation but no end-to-end test. First-pass acceptable; next commit's obvious gap.

## Cross-Cutting Observations

- **Documentation ratio is high and appropriate.** 1,432 lines of specs/review guides for 1,625 lines of infra code. For containerisation work this ratio makes sense.
- **Advisor persona files (687 lines, 8 seats)** now consume both trackctl metrics and journalctl windows — genuine context, not just vibes.
- **Clear daily arc:** qualitative data layer (morning) → packaging/deployment (afternoon) → debugging real connectivity (evening). No context-switching waste.

## Open Questions

1. **journalctl in production cron.** Window synthesis via subprocess — is it wired into briefings? Caching design untested under real multi-consumer load.
2. **Heartbeat upgrade path.** When does the HTTP health check sidecar become blocking — before or after first client deployment?
3. **Cadence sustainability.** Two zero-commit days followed by a 3,500-line burst. Clearing a backlog or normal variance?

## Technical Debt Summary

| ID | Area | Severity | Description |
|----|------|----------|-------------|
| TD-1 | journalctl | Medium | Subprocess shell-out for LLM synthesis — no retry/rate-limit, silent degradation |
| TD-2 | git hygiene | Low | CLAUDE.md cleanup bundled with journalctl feature commit |
| TD-3 | infra | Medium | Heartbeat doesn't detect asyncio deadlocks — needs HTTP health sidecar before multi-tenant |
| TD-4 | infra | Low | `pip` in Dockerfile violates `uv`-only standing order — document or fix |
| TD-5 | infra | Medium | No automated integration test for container — manual smoke only |
