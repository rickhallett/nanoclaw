#!/usr/bin/env python3
"""Day 7: itertools — groupby, takewhile, dropwhile, zip_longest.

groupby is the one you got half-right on the exam. Nail it today.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day07_itertools_grouping.py
"""
from IPython import embed
from itertools import groupby, takewhile, dropwhile, zip_longest

# ============================================================================
# LESSON: groupby — consecutive groups only
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: groupby — the most misunderstood function")
print("=" * 60)
print()
print("groupby groups CONSECUTIVE elements with the same key.")
print("It does NOT sort first. If the data isn't sorted by the key,")
print("the same key can appear in multiple groups.")
print()
print("TRY:")
print()
print("  # Consecutive groups")
print("  data = [1, 1, 2, 3, 3, 3, 2, 2]")
print("  result = [(k, list(g)) for k, g in groupby(data)]")
print("  print(result)")
print("  # PREDICT: ? (this was exam Q6)")
print()
print("  # Note: 2 appears TWICE because it's not consecutive")
print("  # To group ALL 2s together: sort first")
print("  data_sorted = sorted(data)")
print("  result = [(k, list(g)) for k, g in groupby(data_sorted)]")
print("  print(result)")
print("  # Now 2 appears only once")
print()
print("CRITICAL: you MUST consume each group g before advancing to the next.")
print("groupby yields lazy iterators. If you advance to the next (k, g),")
print("the previous g is exhausted.")
print()

embed(header="Checkpoint 1: groupby — consecutive groups, sort first for global")

# ============================================================================
# LESSON: groupby with a key function
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: groupby with key functions")
print("=" * 60)
print()
print("groupby(iterable, key=func) — group by the result of func.")
print()
print("TRY:")
print()
print("  # Group strings by first character")
print("  words = sorted(['apple', 'avocado', 'banana', 'blueberry', 'cherry', 'cranberry'])")
print("  for letter, group in groupby(words, key=lambda w: w[0]):")
print("      print(f'  {letter}: {list(group)}')")
print()
print("  # Group pods by status (MUST sort by status first)")
print("  pods = [")
print("      ('musashi', 'Running'), ('medici', 'CrashLoopBackOff'),")
print("      ('bankei', 'Running'), ('gibson', 'OOMKilled'),")
print("      ('draper', 'Running'), ('karpathy', 'Running'),")
print("  ]")
print("  pods_sorted = sorted(pods, key=lambda p: p[1])")
print("  for status, group in groupby(pods_sorted, key=lambda p: p[1]):")
print("      names = [name for name, _ in group]")
print("      print(f'  {status}: {names}')")
print()
print("  # Group numbers by even/odd")
print("  nums = sorted(range(10), key=lambda x: x % 2)")
print("  for is_odd, group in groupby(nums, key=lambda x: x % 2):")
print("      label = 'odd' if is_odd else 'even'")
print("      print(f'  {label}: {list(group)}')")
print()

embed(header="Checkpoint 2: groupby with key — sort first, always")

# ============================================================================
# LESSON: takewhile and dropwhile
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: takewhile and dropwhile")
print("=" * 60)
print()
print("takewhile(pred, it) — yield items WHILE predicate is True, stop at first False")
print("dropwhile(pred, it) — skip items WHILE predicate is True, yield the rest")
print()
print("TRY:")
print()
print("  nums = [2, 4, 6, 1, 3, 5, 8, 10]")
print()
print("  # takewhile: take while even")
print("  print(list(takewhile(lambda x: x % 2 == 0, nums)))")
print("  # PREDICT: ?  (stops at first odd number)")
print()
print("  # dropwhile: skip while even, then yield everything")
print("  print(list(dropwhile(lambda x: x % 2 == 0, nums)))")
print("  # PREDICT: ?  (starts from first odd number)")
print()
print("  # Real use: skip log header lines")
print("  log = [")
print("      '# Log file v2',")
print("      '# Generated 2026-04-08',")
print("      '# Format: level message',")
print("      'INFO Starting up',")
print("      'WARN Memory high',")
print("      'ERROR Disk full',")
print("  ]")
print("  data_lines = list(dropwhile(lambda l: l.startswith('#'), log))")
print("  print(data_lines)")
print()
print("  # Real use: take entries until first error")
print("  entries = ['ok', 'ok', 'ok', 'error', 'ok', 'error']")
print("  before_error = list(takewhile(lambda e: e != 'error', entries))")
print("  print(before_error)")
print()

embed(header="Checkpoint 3: takewhile and dropwhile — prefix operations")

# ============================================================================
# LESSON: zip_longest
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: zip_longest — zip that doesn't truncate")
print("=" * 60)
print()
print("zip() stops at the shortest. zip_longest fills with a default.")
print()
print("TRY:")
print()
print("  a = [1, 2, 3]")
print("  b = ['a', 'b']")
print()
print("  # Regular zip — truncates")
print("  print(list(zip(a, b)))")
print("  # PREDICT: ?")
print()
print("  # zip_longest — fills missing values")
print("  print(list(zip_longest(a, b)))")
print("  # PREDICT: ? (what's the fill value?)")
print()
print("  # Custom fill value")
print("  print(list(zip_longest(a, b, fillvalue='?')))")
print("  # PREDICT: ?")
print()
print("  # Real use: compare two configs side by side")
print("  old_config = ['port=8080', 'debug=false', 'workers=4']")
print("  new_config = ['port=8080', 'debug=true', 'workers=8', 'timeout=30']")
print("  for old, new in zip_longest(old_config, new_config, fillvalue='(missing)'):")
print("      marker = '  ' if old == new else '>>'")
print("      print(f'  {marker} {old:25s} | {new}')")
print()

embed(header="Checkpoint 4: zip_longest — no truncation")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Log stream analyser")
print("=" * 60)
print()
print("'log_stream' is a time-ordered list of (timestamp, level, message).")
print()
print("Tasks:")
print("  1. groupby timestamp prefix (hour) — how many events per hour?")
print("     (sort by hour first, use key=lambda e: e[0][:2])")
print("  2. takewhile — get all events before the first ERROR")
print("  3. dropwhile — skip everything before the first ERROR")
print("  4. Group events by level (sort + groupby)")
print("  5. zip_longest the ERROR events and WARN events side by side")
print()

log_stream = [
    ("09:01", "INFO",  "Server started"),
    ("09:05", "INFO",  "Connected to DB"),
    ("09:12", "WARN",  "Slow query: 2.1s"),
    ("09:15", "INFO",  "Request processed"),
    ("09:22", "WARN",  "Memory at 78%"),
    ("09:30", "ERROR", "NATS connection lost"),
    ("09:31", "ERROR", "Failed to publish event"),
    ("09:35", "INFO",  "NATS reconnected"),
    ("10:01", "INFO",  "Scheduled job started"),
    ("10:05", "WARN",  "Disk at 85%"),
    ("10:15", "ERROR", "OOMKilled: advisor-gibson"),
    ("10:20", "INFO",  "Pod restarted"),
    ("10:30", "WARN",  "Connection pool near capacity"),
    ("11:00", "INFO",  "Health check passed"),
]

embed(header="Checkpoint 5: log stream analysis with groupby + takewhile + dropwhile")

print()
print("DAY 7 COMPLETE.")
print()
print("  groupby(it, key=fn)  — CONSECUTIVE groups. Sort first for global.")
print("  takewhile(pred, it)  — yield while True, stop at first False")
print("  dropwhile(pred, it)  — skip while True, yield the rest")
print("  zip_longest(a, b, fillvalue=X) — zip without truncation")
print()
print("groupby gotcha: ALWAYS sort by key first. ALWAYS consume group before next.")
print("Tomorrow: combinatoric itertools — product, permutations, combinations.")
