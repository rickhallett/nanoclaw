---
title: "Taxonomy Review Phase 6"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Phase 6

Date: 2026-03-20

Scope:
- `HALO.HALCTL`
- `HALO.NIGHT`
- `HALO.BRIEF`
- `HALO.MEM`
- `HALO.LOG`
- `HALO.AGENT`
- `HALO.CRON`
- `HALO.REPORT`

Primary files reviewed:
- `halos/halctl/session.py`
- `halos/halctl/cli.py`
- `halos/nightctl/executor.py`
- `halos/briefings/synthesise.py`
- `halos/cronctl/cli.py`
- `halos/cronctl/cron.py`

## Summary

Phase 6 produced 2 findings.

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 1 |
| S3 | 1 |
| S4 | 0 |

Reviewed areas with no material findings in this pass:
- `HALO.BRIEF` fallback ordering itself
- `HALO.CRON` generated crontab atomic writes
- `HALO.MEM` and `HALO.LOG` sampled critical paths

## Findings

### HALO.HALCTL.04 [TC12] S2

`halctl session clear` mutates only the SQLite `sessions` table; it does not coordinate with the live NanoClaw process, its in-memory session map, or any still-running containers.

Evidence:
- `session_clear()` and `session_clear_all()` only delete rows from SQLite in `halos/halctl/session.py:64-121`;
- NanoClaw loads sessions into memory at startup and then reads/writes its in-memory map independently in `src/index.ts:70-71`, `src/index.ts:87`, `src/index.ts:284`, and `src/index.ts:313-359`.

Impact:
- an operator can believe a session was cleared while a live process still resumes or rewrites the old session ID;
- the administrative boundary crosses from Halos into NanoClaw without a coherence mechanism.

Why `[TC12]`:
- the operation claims to clear a cross-process session boundary but actually mutates only one side of that boundary.

### HALO.NIGHT.02 [TC11] S3

Nightctl run records are written directly, not atomically, despite the broader subsystem relying on tmp-plus-replace semantics elsewhere.

Evidence:
- `_write_run_record()` writes YAML straight to the final path in `halos/nightctl/executor.py:70-77`;
- nearby container-preparation writes use atomic `os.replace()` semantics in `halos/nightctl/container.py:81-99` and `halos/nightctl/container.py:147-150`.

Impact:
- a crash or interruption while writing a run record can leave a truncated YAML artifact;
- downstream reporting and audit tools then read corrupted execution history.

Why `[TC11]`:
- execution history transitions from "running" to "recorded" without an atomic commit boundary.

## Coverage Notes

Observed coverage:
- targeted Python slices passed, including `tests/nightctl/test_executor.py`, `tests/cronctl/test_adversarial_fixes.py`, and `tests/reportctl/test_formatters.py`.

Important gaps:
- no targeted test covers `halctl session clear` interacting with a live NanoClaw process;
- no test asserts atomicity for `_write_run_record()`.
