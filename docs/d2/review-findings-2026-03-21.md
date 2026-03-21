---
title: "Adversarial Review Findings — 24h Halos Expansion"
category: review
status: active
created: 2026-03-21
---

# Adversarial Review Findings

**Reviewer:** adversarial-reviewer agent
**Scope:** commits 35a79ee..6d787b1 (~17,000 lines across calctl, statusctl, backupctl, ledgerctl, dashctl, mailctl)
**Tests:** 281 passed, 0 failed (71% line coverage across reviewed modules)

## Summary
- Total findings: 14
- Critical: 1
- High: 5
- Medium: 5
- Low: 3

---

## Critical Findings

### C-1. ledgerctl journal.py: error handler crashes on double-close

**File:** `halos/ledgerctl/journal.py:228`

**What:** The except block in `append_entries()` uses `os.get_inheritable(fd)` to decide whether to close the file descriptor. After the try block calls `os.close(fd)` at line 225, `fd` is invalid. Calling `os.get_inheritable()` on a closed fd raises `OSError: [Errno 9] Bad file descriptor`, which replaces the original exception. The original error is swallowed.

```python
# Line 228: THIS CRASHES if fd was already closed at line 225
os.close(fd) if not os.get_inheritable(fd) else None
```

Confirmed by test: `os.get_inheritable(fd)` raises `OSError` on a closed fd.

**Impact:** If any error occurs after `os.close(fd)` but before `os.rename()` (e.g., permission error on rename), the error handler itself raises `OSError`, masking the real error. The temp file is not cleaned up because `os.unlink` (line 230) is never reached. Repeated failures accumulate orphan `.ledger_*.tmp` files.

**Fix:** Replace lines 227-231 with the standard pattern used in 18 other locations in this codebase:
```python
except Exception:
    try:
        os.close(fd)
    except OSError:
        pass
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    raise
```

---

## High Findings

### H-1. ledgerctl uses os.rename instead of os.replace (non-atomic on cross-filesystem, not idempotent on Windows)

**File:** `halos/ledgerctl/journal.py:226`, `halos/ledgerctl/rules.py:68`

**What:** `os.rename()` is used for atomic writes. Every other halos module (18 call sites) uses `os.replace()`. `os.rename()` fails with `EXDEV` if source and destination are on different filesystems. On Windows (unlikely but), it fails if the destination exists. `os.replace()` handles both cases correctly and is the project's established convention.

**Impact:** Journal writes fail if `/tmp` and the store directory are on different filesystems (e.g., containerised environments, bind mounts). Since this is the accounting data path, the failure is silent — users may believe entries were saved when they weren't (the exception propagates but the intent was atomicity).

**Fix:** Change `os.rename` to `os.replace` in both files.

### H-2. mailctl cmd_triage: inconsistent unread detection vs cmd_inbox (will miss unread messages)

**File:** `halos/mailctl/cli.py:131` vs `halos/mailctl/cli.py:70`

**What:** `cmd_inbox` filters unread messages using `"Seen" not in m.get("flags", [])` (checking list membership). `cmd_triage` filters using `not m.get("flags", {}).get("seen", False)` (checking dict key with lowercase). These are mutually exclusive data shape assumptions — if himalaya returns flags as a list (the cmd_inbox assumption), then cmd_triage's `.get("seen")` always returns `None`/`False`, meaning ALL messages look unread. If himalaya returns flags as a dict, cmd_inbox breaks instead.

**Impact:** Triage will either process all messages (including already-read ones) or miss all unread messages, depending on himalaya's actual output format. Either way, one of the two code paths is wrong.

**Fix:** Determine himalaya's actual flag format and standardise both paths. Based on the briefing module (line 24) also using `"Seen" not in m.get("flags", [])`, the list form is likely correct. Change line 131 to match.

### H-3. mailctl has zero test coverage

**File:** `halos/mailctl/` (entire module)

**What:** No test directory exists at `tests/mailctl/`. The review guide explicitly flags this as a gap. The module contains subprocess calls to himalaya, SQLite operations, triage logic, and an email send function — all untested.

**Impact:** Any regression in the triage rules, store layer, or CLI dispatch goes undetected. The flag inconsistency in H-2 would have been caught by even basic unit tests.

**Fix:** Create `tests/mailctl/` with tests for at minimum: `triage.py` (rule evaluation), `store.py` (CRUD operations), and `cli.py` (dispatch routing). The himalaya engine can be tested with subprocess mocking.

### H-4. backupctl _list_tar_snapshots: filename parsing breaks for hyphenated target names

**File:** `halos/backupctl/engine.py:328`

**What:** `stem.split("-", 2)` splits the filename `backup-{target}-{timestamp}` into at most 3 parts. If the target name contains hyphens (e.g., `my-target`), the split yields `["backup", "my", "target-20260321-100000"]`, misidentifying the target as `"my"` and the timestamp as `"target-20260321-100000"`.

The default targets (`store`, `memory`, `queue`, `config`) don't contain hyphens, so this works today. But the config file supports arbitrary target names, and nothing validates against hyphens.

**Impact:** Listing or restoring backups for hyphenated targets returns wrong metadata. `get_last_backup_age()` fails to parse the timestamp, returning `None` (no backups found) even when backups exist. The briefing then reports "no backups found" — masking successful backup operations.

**Fix:** Use a more robust filename format. Either: (a) replace hyphens in target names with underscores before writing, or (b) use a different separator (e.g., `backup__{target}__{timestamp}.tar.gz`), or (c) validate target names to reject hyphens in `config.py`.

### H-5. ledgerctl search and rules accept user-supplied regex with no timeout or complexity limit (ReDoS)

**File:** `halos/ledgerctl/reports.py:270`, `halos/ledgerctl/rules.py:109`

**What:** Both `reports.search()` and `rules.categorise()` pass user-supplied regex patterns directly to `re.search()`. The CLI validates that the pattern compiles (`cli.py:303`) but does not limit its complexity. A pathological pattern like `(a+)+$` against a long string will hang the process.

For the CLI this is a minor concern (user is attacking themselves). But if these functions are called programmatically from briefing or import flows with data-derived patterns, the risk increases.

**Impact:** A catastrophic backtracking regex in the rules file will hang every CSV import and every briefing summary that touches categorisation.

**Fix:** Wrap `re.search()` calls with a timeout (Python 3.11+ supports `re.search(..., timeout=)` parameter, or use `signal.alarm` on Unix). At minimum, add a max pattern length check.

---

## Medium Findings

### M-1. dashctl html_export: no atomic write — partial HTML files on crash

**File:** `halos/dashctl/html_export.py:62`

**What:** `path.write_text(html)` writes directly to the target path. If the process is interrupted mid-write (Ctrl-C, OOM kill, disk full), the output file contains a truncated, invalid HTML document. All other file-writing halos modules use tmp+rename for atomicity.

**Impact:** A cron-triggered dashboard export that fails mid-write leaves a broken HTML file. The next successful run overwrites it, but in the meantime any monitoring that reads the HTML sees garbage.

**Fix:** Use the standard tmp+os.replace pattern.

### M-2. backupctl: default password "nanoclaw-local-backup" hardcoded in source

**File:** `halos/backupctl/engine.py:36`

**What:** When no password file or `RESTIC_PASSWORD` env var is set, the engine falls back to the hardcoded string `"nanoclaw-local-backup"`. This is documented as being for "local-only repos" but is visible in the source code.

**Impact:** Low for local-only deployments. If the backup repository is ever moved to remote storage (S3, SFTP), the password is already known. Not a credential leak per se (it's not a secret), but it's the wrong pattern — default passwords tend to persist.

**Fix:** Either require explicit password configuration (fail loudly if neither password_file nor RESTIC_PASSWORD is set), or generate a random password on first `init` and store it in a dotfile.

### M-3. statusctl cmd_metrics mutates dict during iteration (cosmetic corruption)

**File:** `halos/statusctl/cli.py:155-156`

**What:** In the non-JSON branch of `cmd_metrics`, `data.pop("status")` and `data.pop("message")` mutate the dict while it's being iterated. Python allows this because iteration is over `metrics.items()` (the outer dict), not over `data` itself. However, this means the `--json` and non-JSON branches display different data structures (JSON includes status/message, text does not). If a caller invokes `cmd_metrics` twice in the same process, the second call would crash because `status` and `message` have already been popped.

**Impact:** Minor — CLI commands run once per process invocation. But it breaks the principle that `--json` and text output show the same data.

**Fix:** Don't mutate `data`. Read `status` and `message` with `.get()` instead of `.pop()`.

### M-4. calctl CronctlSource: max_daily_runs filter uses per-query count, not per-day count

**File:** `halos/calctl/sources.py:194`

**What:** `if self._max_daily_runs and len(runs) > self._max_daily_runs` filters based on the total number of runs in the entire query window, not per-day. A `calctl week` query (7-day window) would produce 7x more runs than `calctl today` for the same cron job. A cron job running every 2 hours (`0 */2 * * *`) produces 12 runs/day, which passes the filter for `today` but gets filtered out for `week` (84 runs).

**Impact:** The same cron job appears in `calctl today` but disappears from `calctl week`. Inconsistent behaviour that will confuse users.

**Fix:** Compute runs per day and filter based on max runs per day, or document that the filter applies to the total query window.

### M-5. backupctl _safe_copy_sqlite: no timeout, no WAL handling

**File:** `halos/backupctl/engine.py:84-97`

**What:** `sqlite3.connect()` and `src_conn.backup(dst_conn)` have no timeout. If the source database is locked by a long-running write transaction, `backup()` will block indefinitely. Additionally, if the source database uses WAL mode, the backup may not capture WAL-pending transactions (though sqlite3.backup() generally handles this correctly for same-machine copies).

**Impact:** A backup triggered while nightctl or trackctl is writing to their SQLite databases could hang the backup process indefinitely, blocking subsequent backups in the chain.

**Fix:** Set `timeout=30` on `sqlite3.connect()` for the source connection, and wrap the backup call in a `try` with a process-level timeout.

---

## Low Findings

### L-1. calctl cli.py: `main()` exits with 0 when no subcommand given (should be 1 or show help+error)

**File:** `halos/calctl/cli.py:247`

**What:** `sys.exit(0)` when no command is provided. Convention in other halos modules (ledgerctl, etc.) varies, but a successful exit code for "did nothing" is misleading in automation contexts.

**Impact:** A script checking `calctl` exit code will believe it succeeded when no operation was performed.

**Fix:** Exit with 1 or 2 (usage error) when no subcommand is given, matching POSIX convention.

### L-2. mailctl engine.py: search() splits query on whitespace, breaking quoted IMAP searches

**File:** `halos/mailctl/engine.py:91`

**What:** `*query.split()` splits the search query on whitespace before passing as separate arguments to himalaya. IMAP search queries can contain quoted strings (e.g., `FROM "John Doe"`), which this splitting breaks into `["FROM", "\"John", "Doe\""]`.

**Impact:** Multi-word search queries will produce unexpected results or errors from himalaya.

**Fix:** Pass `query` as a single argument rather than splitting it: `["envelope", "list", "--folder", folder, query]`. Or use `shlex.split()` to respect quoting.

### L-3. ledgerctl posting regex doesn't handle all currency formats

**File:** `halos/ledgerctl/journal.py:153-154`

**What:** The regex `([A-Z]{2,3}|\$|€|£)` only handles 2-3 letter currency codes and three specific symbols. Currency codes like `NZ$` (as used in ANZ NZ context) are not matched. The regex also requires `{2,}` minimum spaces between account and amount, which may not match all valid hledger formats.

**Impact:** Journal entries with `NZ$` or other multi-char symbols will fail to parse, losing the currency on round-trip.

**Fix:** Expand the currency regex to handle common compound symbols: `([A-Z]{2,3}\$?|\$|€|£|¥)`.

---

## Test Coverage Report

```
281 passed, 0 failed, 71% aggregate line coverage

Module                              Stmts   Miss   Cover
---------------------------------------------------------
halos/calctl/engine.py                65      0    100%
halos/calctl/briefing.py              28      0    100%
halos/calctl/sources.py              248     71     71%
halos/calctl/cli.py                  150     69     54%   <-- CLI untested
halos/statusctl/engine.py             38      0    100%
halos/statusctl/briefing.py           12      0    100%
halos/statusctl/checks.py            181     11     94%
halos/statusctl/cli.py                97     20     79%
halos/backupctl/config.py             66      2     97%
halos/backupctl/engine.py            238     72     70%
halos/backupctl/cli.py               103     18     83%
halos/backupctl/briefing.py           36     11     69%
halos/ledgerctl/journal.py           136     21     85%
halos/ledgerctl/importer.py           60      9     85%
halos/ledgerctl/reports.py           155     32     79%
halos/ledgerctl/rules.py              59     15     75%
halos/ledgerctl/cli.py               175     58     67%
halos/dashctl/html_export.py          15      0    100%
halos/dashctl/panels.py              124    124      0%  <-- zero coverage
halos/dashctl/cli.py                  83     83      0%  <-- zero coverage
halos/mailctl/ (entire module)         -      -      0%  <-- NO TESTS EXIST
```

**Key gaps:**
- mailctl: entire module untested (H-3)
- dashctl/panels.py: 0% coverage (the core rendering logic)
- dashctl/cli.py: 0% coverage (mode dispatch)
- calctl/cli.py: 54% (most subcommands untested)
- backupctl/engine.py: restic and restore paths untested (mocking needed)

---

## Recommendations

**Priority 1 (fix before next deploy):**
1. **C-1:** Fix the crash-in-error-handler in journal.py (data loss path)
2. **H-1:** Replace `os.rename` with `os.replace` in ledgerctl (2 lines)
3. **H-2:** Fix the inconsistent flag checking in mailctl triage

**Priority 2 (this week):**
4. **H-3:** Create basic test suite for mailctl
5. **H-4:** Fix tar filename parsing for hyphenated target names
6. **H-5:** Add regex timeout or complexity limit to ledgerctl

**Priority 3 (backlog):**
7. **M-1 through M-5:** Address medium findings
8. Add tests for dashctl/panels.py and dashctl/cli.py
9. Expand calctl CLI test coverage

---

*Report generated 2026-03-21 by adversarial-reviewer agent.*
