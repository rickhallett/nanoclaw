#!/usr/bin/env python3
"""Day 3: Counter — counting things properly.

Run: uv run python data/advisors/guido/curriculum/scripts/day03_counter.py
"""
from IPython import embed
from collections import Counter

# ============================================================================
# LESSON: Counter basics
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: Creating Counters")
print("=" * 60)
print()
print("Counter is a dict subclass for counting hashable objects.")
print("Three ways to create one:")
print()
print("TRY EACH:")
print("  c1 = Counter('abracadabra')        — from iterable")
print("  c2 = Counter(['a','b','a','c'])     — from list")
print("  c3 = Counter(errors=5, warnings=2)  — from kwargs")
print()
print("Then try:")
print("  print(c1)")
print("  print(c1['a'])      — count of 'a'")
print("  print(c1['z'])      — count of missing element (what happens?)")
print("  print(dict(c1))     — as a plain dict")
print()
print("KEY: Counter returns 0 for missing keys. Never raises KeyError.")
print()

embed(header="Checkpoint 1: create Counters three ways")

# ============================================================================
# LESSON: most_common
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: most_common()")
print("=" * 60)
print()
print("'status_codes' is a list of HTTP status codes from a log.")
print("'c' is a Counter of those codes.")
print()
print("TRY:")
print("  c = Counter(status_codes)")
print("  print(c)")
print("  print(c.most_common(2))   — top 2, as list of (element, count) tuples")
print("  print(c.most_common())    — ALL, sorted by frequency")
print("  print(c.most_common(1)[0])  — just the top one tuple")
print("  print(c.most_common(1)[0][0])  — just the element")
print()
print("RETURN TYPE: list of (element, count) tuples. Not a dict. Not just elements.")
print("This is what you got wrong on Q1 of the exam.")
print()

status_codes = [200, 200, 404, 500, 200, 404, 200, 500, 500, 200, 301, 200, 404]

embed(header="Checkpoint 2: most_common — returns list of tuples")

# ============================================================================
# LESSON: Counter arithmetic
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Counter arithmetic")
print("=" * 60)
print()
print("Two pod snapshots: 'before' and 'after'.")
print()
print("TRY:")
print("  print(before + after)    — combined counts")
print("  print(after - before)    — only POSITIVE differences (what increased)")
print("  print(before - after)    — only POSITIVE differences (what decreased)")
print("  print(before & after)    — minimum of each (intersection)")
print("  print(before | after)    — maximum of each (union)")
print()
print("KEY: subtraction drops zero and negative counts.")
print("This means (after - before) shows only what GREW.")
print("And (before - after) shows only what SHRANK.")
print()

before = Counter(Running=8, Pending=2, Failed=1)
after  = Counter(Running=6, Pending=1, Failed=3, CrashLoopBackOff=2)

embed(header="Checkpoint 3: Counter arithmetic — before/after pod status")

# ============================================================================
# LESSON: update and subtract
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: update() and subtract()")
print("=" * 60)
print()
print("'c' starts as Counter(errors=5, warnings=2).")
print()
print("TRY:")
print("  c.update({'errors': 3, 'info': 10})   — ADDS counts")
print("  print(c)")
print("  c.subtract({'errors': 20})             — SUBTRACTS counts")
print("  print(c)")
print("  print(c['errors'])     — can counts go NEGATIVE? Try it.")
print()
print("KEY DIFFERENCE:")
print("  update()   adds counts (like Counter + Counter)")
print("  subtract() subtracts counts (CAN go negative, unlike - operator)")
print("  The - operator drops negatives. subtract() keeps them.")
print()

c = Counter(errors=5, warnings=2)

embed(header="Checkpoint 4: update vs subtract vs minus operator")

# ============================================================================
# LESSON: Counter tricks
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Useful tricks")
print("=" * 60)
print()
print("TRY EACH:")
print()
print("  c = Counter('mississippi')")
print("  print(c)")
print()
print("  # Elements that appear exactly once:")
print("  unique = [item for item, count in c.items() if count == 1]")
print("  print(unique)")
print()
print("  # Unary plus strips zero and negative counts:")
print("  c['z'] = 0")
print("  c['q'] = -1")
print("  print(c)       — has z and q")
print("  print(+c)      — z and q are gone")
print()
print("  # Total count (Python 3.10+):")
print("  print(c.total())")
print()
print("  # list(c.elements()) — each element repeated by its count:")
print("  small = Counter(a=2, b=1)")
print("  print(list(small.elements()))")
print()

embed(header="Checkpoint 5: Counter tricks — unique, unary plus, elements")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: Log level analysis")
print("=" * 60)
print()
print("'log_lines' is a simulated log. Each line starts with a level.")
print()
print("Tasks:")
print("  1. Extract the level from each line (first word)")
print("  2. Count levels using Counter")
print("  3. Print most_common(3)")
print("  4. Print any level that appears only once")
print("  5. What percentage of lines are ERROR or CRITICAL?")
print()

log_lines = [
    "INFO  Server started on port 8080",
    "INFO  Connected to database",
    "WARN  Slow query: 2.3s on /api/pods",
    "INFO  Request: GET /api/health",
    "ERROR Failed to connect to NATS",
    "INFO  Request: GET /api/pods",
    "WARN  Memory usage above 80%",
    "ERROR Timeout waiting for response from advisor-medici",
    "INFO  Request: POST /api/deploy",
    "CRITICAL Out of disk space on /data",
    "ERROR Failed to write to NFS mount",
    "INFO  Request: GET /api/health",
    "WARN  Connection pool near capacity",
    "INFO  Graceful shutdown initiated",
    "ERROR NATS consumer lag exceeding threshold",
]

embed(header="Checkpoint 6: log level analysis")

print()
print("DAY 3 COMPLETE.")
print()
print("You should now know:")
print("  - Counter('iterable') counts elements")
print("  - c.most_common(n) returns LIST OF TUPLES: [(elem, count), ...]")
print("  - c['missing'] returns 0, never KeyError")
print("  - c1 - c2 drops negatives. c.subtract() keeps them.")
print("  - +c strips zero and negative counts")
