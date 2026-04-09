#!/usr/bin/env python3
"""Day 1: defaultdict — the automatic factory.

Run: uv run python data/advisors/guido/curriculum/scripts/day01_defaultdict_basics.py

Each checkpoint drops you into IPython with everything loaded.
Explore, experiment, break things. Ctrl-D to continue.
"""
from ptpython.ipython import embed

# ============================================================================
# LESSON: What is defaultdict?
# ============================================================================
# A normal dict raises KeyError on missing keys.
# defaultdict calls a factory function instead — the factory takes NO args.

from collections import defaultdict

# The factory argument determines what missing keys become:
# defaultdict(list)    → missing key returns []
# defaultdict(int)     → missing key returns 0
# defaultdict(set)     → missing key returns set()
# defaultdict(str)     → missing key returns ""
# defaultdict(lambda: "unknown") → missing key returns "unknown"

print("=" * 60)
print("CHECKPOINT 1: The basics")
print("=" * 60)
print()
print("A defaultdict(list) has been created as 'd'.")
print()
print("TRY THESE (type them out, predict first):")
print("  1. d['missing']           — what do you get?")
print("  2. dict(d)                — what keys exist now?")
print("  3. d.get('also_missing')  — same or different?")
print("  4. dict(d)                — did 'also_missing' appear?")
print()
print("KEY INSIGHT: d[key] triggers __missing__. d.get(key) does NOT.")
print()

d = defaultdict(list)

embed(header="Checkpoint 1: explore d — a defaultdict(list)")

# ============================================================================
# EXERCISE: Grouping with defaultdict
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Grouping")
print("=" * 60)
print()
print("Server logs have been loaded as 'logs' — a list of (host, level) tuples.")
print("'by_host' is a defaultdict(list).")
print()
print("TRY THESE:")
print("  1. Group logs by host:")
print("     for host, level in logs:")
print("         by_host[host].append(level)")
print("  2. print(dict(by_host))")
print("  3. Predict: what happens with by_host['web-99']?")
print()

logs = [
    ("web-01", "error"), ("web-02", "warn"), ("web-01", "error"),
    ("web-03", "info"), ("web-02", "error"), ("web-01", "warn"),
]

by_host = defaultdict(list)

embed(header="Checkpoint 2: group logs by host using by_host")

# ============================================================================
# EXERCISE: Counting with defaultdict(int)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Counting")
print("=" * 60)
print()
print("Same logs. Now count occurrences of each level.")
print("'counts' is a defaultdict(int) — missing keys start at 0.")
print()
print("TRY THESE:")
print("  1. for host, level in logs:")
print("         counts[level] += 1")
print("  2. print(dict(counts))")
print("  3. Why does += 1 work? Because int() returns 0, and 0 + 1 = 1.")
print()

counts = defaultdict(int)

embed(header="Checkpoint 3: count log levels using counts")

# ============================================================================
# EXERCISE: Unique values per key with defaultdict(set)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: Unique values per key")
print("=" * 60)
print()
print("'events' contains (host, status_code) tuples.")
print("'unique_codes' is a defaultdict(set).")
print()
print("TRY THESE:")
print("  1. for host, code in events:")
print("         unique_codes[host].add(code)")
print("  2. print(dict(unique_codes))")
print("  3. Note: web-01 had TWO 404s but the set only keeps one.")
print()

events = [("web-01", 404), ("web-01", 500), ("web-01", 404), ("web-02", 500)]
unique_codes = defaultdict(set)

embed(header="Checkpoint 4: unique status codes per host")

# ============================================================================
# EXERCISE: Nested defaultdict
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Nested defaultdict")
print("=" * 60)
print()
print("A defaultdict of defaultdict(int) — two levels deep.")
print("'nested' is ready to go.")
print()
print("TRY THESE:")
print("  1. nested['web-01']['errors'] += 1")
print("  2. nested['web-01']['errors'] += 1")
print("  3. nested['web-01']['warns'] += 1")
print("  4. nested['web-02']['errors'] += 1")
print("  5. print(dict(nested['web-01']))")
print("  6. print(dict(nested['web-02']))")
print("  7. print(dict(nested['web-99']))  — what happens?")
print()

nested = defaultdict(lambda: defaultdict(int))

embed(header="Checkpoint 5: nested defaultdict — host → level → count")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: Script challenge")
print("=" * 60)
print()
print("'files' is a list of filenames.")
print("Group them by extension using defaultdict(list).")
print("Files with no extension go under key ''.")
print()
print("Hint: use str.rsplit('.', 1) or just check if '.' is in the name.")
print()
print("TRY IT:")
print("  by_ext = defaultdict(list)")
print("  for f in files:")
print("      ext = f.rsplit('.', 1)[1] if '.' in f else ''")
print("      by_ext[ext].append(f)")
print("  for ext, names in sorted(by_ext.items()):")
print("      print(f'  .{ext}: {names}' if ext else f'  (none): {names}')")
print()

files = ["main.py", "utils.py", "Dockerfile", "deploy.yaml", "svc.yaml",
         "README.md", "Makefile", "test_main.py", "config.toml"]
by_ext = defaultdict(list)

embed(header="Checkpoint 6: group files by extension")

print()
print("=" * 60)
print("DAY 1 COMPLETE")
print("=" * 60)
print()
print("You should now know:")
print("  - defaultdict(list)  → missing key returns []")
print("  - defaultdict(int)   → missing key returns 0")
print("  - defaultdict(set)   → missing key returns set()")
print("  - d[key] triggers the factory. d.get(key) does NOT.")
print("  - Nested: defaultdict(lambda: defaultdict(int))")
print()
print("Tomorrow: more defaultdict patterns, then Counter.")
