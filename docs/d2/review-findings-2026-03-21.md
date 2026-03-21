---
title: "Adversarial Review Findings — 24h Halos Expansion"
category: review
status: active
created: 2026-03-21
---

# Adversarial Review Findings

## Summary
- Total findings: 8
- Critical: 0
- High: 4
- Medium: 3
- Low: 1

Structural checks completed:
- `uv run python -m pytest tests/calctl/ tests/statusctl/ tests/backupctl/ tests/ledgerctl/ tests/dashctl/ -v --tb=short` → 281 passed
- Import check for `halos.calctl`, `halos.statusctl`, `halos.backupctl`, `halos.ledgerctl`, `halos.dashctl`, `halos.mailctl` → passed
- CLI entry points for `calctl`, `statusctl`, `backupctl`, `ledgerctl`, `dashctl`, `mailctl` → runnable

## Critical Findings

None.

## High Findings

### 1. `calctl` drops nightctl items that use `deadline`, despite the spec and review guide requiring them
- Severity: High
- Files: `halos/calctl/sources.py:102-108`
- Problem: `NightctlSource.fetch()` only reads `data.get("due")`. The review guide explicitly asks for `due`/`deadline`, and the original spec also calls out deadline-style task data. Any item that only has `deadline` is silently omitted from `today`, `week`, `conflicts`, and briefing summaries.
- Evidence: local repro with a YAML item containing only `deadline: 2026-03-21` returned `events 0`.
- Impact: user-visible data loss in the core schedule view; deadlines can disappear entirely.
- Test gap: the test suite only covers `due`, not `deadline` or `scheduled`.

### 2. `calctl.merge_events()` never deduplicates, so duplicate source data is surfaced as separate events
- Severity: High
- Files: `halos/calctl/engine.py:11-20`
- Problem: `merge_events()` concatenates all source results and sorts them. There is no deduplication pass, even though the review guide explicitly requires dedupe across sources.
- Evidence: local repro with two sources returning the same `CalendarEvent` produced two output rows.
- Impact: duplicate events inflate counts, create misleading summaries, and can generate false conflicts/free-slot calculations.
- Test gap: `tests/calctl/test_engine.py` validates merge + sort but not duplicate suppression.

### 3. `statusctl` treats “docker not installed” as a hard failure, which forces the overall grade to `DOWN`
- Severity: High
- Files: `halos/statusctl/checks.py:79-85`, `halos/statusctl/engine.py:14`, `halos/statusctl/engine.py:44-49`
- Problem: `_check_docker()` returns `status="fail"` when `docker` is missing. Because `docker` is listed in `_CRITICAL_CHECKS`, a host without Docker is graded `DOWN`.
- Why this is wrong: both the spec and review guide require graceful degradation for “tool not installed” cases.
- Evidence: patched repro returned `CheckResult(name='docker', status='fail', message='Docker not reachable', ...)`.
- Impact: false-red health status on machines that simply do not have Docker installed, including supported degraded environments.

### 4. `mailctl` shipped without any dedicated test suite
- Severity: High
- Files: `halos/mailctl/`
- Problem: the guide explicitly flags `mailctl` as lacking dedicated tests. The module wraps live mail operations (`read`, `search`, `send`, `move`, `flag`) and persists audit data, but there is no `tests/mailctl/` coverage at all.
- Impact: regressions in mailbox actions, triage behavior, and subprocess error handling can reach production without automated detection.
- Residual risk: this is the highest testing gap in the reviewed change set because the module operates on external state.

## Medium Findings

### 5. `statusctl` counts all exited containers as “exited-error”, including clean exit `0` containers and old exits
- Severity: Medium
- Files: `halos/statusctl/checks.py:110-118`
- Problem: `_check_containers()` runs `docker ps -a --filter status=exited` and counts every returned line as an error. It does not filter non-zero exit codes, and it does not enforce the “recent exits” behavior described in the spec/review guide.
- Evidence: patched repro with two `Exited (0)` containers reported `exited_error=2`.
- Impact: noisy and misleading health reports; normal one-shot jobs can be misreported as failures.

### 6. `backupctl verify --target` is exposed in the CLI but ignored by the implementation
- Severity: Medium
- Files: `halos/backupctl/cli.py:41-43`, `halos/backupctl/cli.py:152-159`, `halos/backupctl/engine.py:344-351`
- Problem: the CLI accepts `backupctl verify --target TARGET`, but `cmd_verify()` never passes the target through, and `verify_repository()` has no target parameter.
- Impact: operator intent is ignored; a targeted verification command always verifies the entire repository instead.
- Risk: this is a correctness/API contract bug rather than a crash.

### 7. The new runtime dependencies described by the specs are not declared in `pyproject.toml`
- Severity: Medium
- Files: `pyproject.toml:10-19`
- Problem: `pyproject.toml` only declares `pyyaml`, `requests`, and `rich`. The specs/review guide call out `google-auth`, `google-api-python-client`, and `psutil` as required for the new modules’ intended behavior.
- Impact:
  - `calctl` cannot use direct Google Calendar access outside environments that already happen to provide those libs.
  - `statusctl` has no `psutil` path for cross-platform metrics, so macOS falls back to partial `/proc` warnings instead of the promised portability.
- Note: the code does degrade in some cases, but that does not satisfy the guide’s “dependencies are declared” requirement.

## Low Findings

### 8. `ledgerctl` atomic writers use `os.rename()` instead of the project-required `os.replace()`
- Severity: Low
- Files: `halos/ledgerctl/journal.py:219-230`, `halos/ledgerctl/rules.py:62-74`
- Problem: the review guide requires temp-file then `os.replace()` for file writes. These writers use `os.rename()` instead.
- Impact: on Linux this will usually work, but it weakens the intended portability/overwrite guarantee and diverges from the project’s stated atomic-write rule.
- Scope: this is a standards/compliance issue more than an observed Linux data-loss bug.

## Test Coverage Report

Command run:

```bash
uv run python -m pytest tests/calctl/ tests/statusctl/ tests/backupctl/ tests/ledgerctl/ tests/dashctl/ --cov=halos.calctl --cov=halos.statusctl --cov=halos.backupctl --cov=halos.ledgerctl --cov=halos.dashctl --cov-report=term-missing
```

Result:

```text
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.14.3-final-0 ________________

Name                                Stmts   Miss  Cover   Missing
-----------------------------------------------------------------
halos/backupctl/__init__.py             0      0   100%
halos/backupctl/briefing.py            36     11    69%   14-18, 33-36, 50, 56-57
halos/backupctl/cli.py                103     18    83%   60-68, 86, 92, 154-159, 164-184, 195
halos/backupctl/config.py              66      2    97%   47, 128
halos/backupctl/engine.py             238     72    70%   24, 33, 42-70, 128, 156, 175, 186-217, 254-260, 276, 294, 308-309, 368-369, 402-404, 407, 439, 447-470, 486-496, 518-524, 543, 548, 555-558
halos/calctl/__init__.py                0      0   100%
halos/calctl/briefing.py               28      0   100%
halos/calctl/cli.py                   150     69    54%   31, 36-58, 62, 75-85, 102-106, 110-121, 133-138, 159-163, 180-188, 242-259, 263
halos/calctl/engine.py                 65      0   100%
halos/calctl/sources.py               248     71    71%   55, 82-87, 99-100, 109, 158-163, 168, 175-176, 183, 190-191, 241-242, 244-249, 253-301, 305-319, 329, 337-338, 373-377, 380-381, 408-411, 434, 462-464
halos/dashctl/__init__.py               0      0   100%
halos/dashctl/cli.py                   83     83     0%   11-134
halos/dashctl/html_export.py           15      0   100%
halos/dashctl/panels.py               124    124     0%   7-189
halos/ledgerctl/__init__.py             0      0   100%
halos/ledgerctl/banks/__init__.py      15      1    93%   33
halos/ledgerctl/banks/anz.py            3      0   100%
halos/ledgerctl/banks/wise.py           3      0   100%
halos/ledgerctl/briefing.py            31      3    90%   29-30, 60
halos/ledgerctl/cli.py                175     58    67%   100-101, 116-117, 127-129, 136, 142, 155, 182-201, 210, 216-221, 226-231, 239, 242-243, 254-268, 273-278, 284-285, 304-306, 316, 320
halos/ledgerctl/importer.py            60      9    85%   65, 83, 88-92, 98-102, 107
halos/ledgerctl/journal.py            136     21    85%   63-67, 109, 119, 128, 149, 163, 171-175, 214, 227-231, 245
halos/ledgerctl/reports.py            155     32    79%   22, 32-42, 51, 55, 58, 85-88, 122-125, 136, 145, 178-181, 194, 209, 249-252
halos/ledgerctl/rules.py               59     15    75%   25-29, 69-76, 102, 107
halos/statusctl/__init__.py             0      0   100%
halos/statusctl/__main__.py             2      2     0%   2-4
halos/statusctl/briefing.py            12      0   100%
halos/statusctl/checks.py             181     11    94%   33, 184-187, 250-252, 290-291, 296, 352
halos/statusctl/cli.py                 97     20    79%   19-48, 164-166, 179
halos/statusctl/engine.py              38      0   100%
-----------------------------------------------------------------
TOTAL                                2123    622    71%
======================== 281 passed, 1 warning in 3.27s ========================
```

Additional coverage observations:
- `dashctl/cli.py` and `dashctl/panels.py` show 0% under the selected `dashctl` tests, even though the HTML path is exercised. The TUI/default rendering path is still effectively unvalidated here.
- `calctl/cli.py` remains only 54% covered, which aligns with the missing edge-case coverage around range parsing and output branches.
- `mailctl` has no dedicated coverage at all.

## Recommendations

1. Fix `calctl` data correctness first: support `deadline`/`scheduled` ingestion and add real deduplication in `merge_events()`.
2. Fix `statusctl` grading semantics next: missing optional tools should degrade gracefully, and container exit accounting must distinguish clean exits from failures.
3. Close the biggest test gap by adding a dedicated `tests/mailctl/` suite for subprocess failures, deterministic triage, and audit logging.
4. Align packaging with the shipped features by declaring the new dependencies in `pyproject.toml`, or explicitly downgrade the feature claims/docs.
5. Clean up API/contract mismatches such as `backupctl verify --target`.
6. Standardise atomic writes on `os.replace()` everywhere the review guide requires it.
