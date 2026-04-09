#!/usr/bin/env python3
"""Day 7: regex — re.match/search/findall, groups, compile (exam Q10-Q11).

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-05-06/day07_regex_fundamentals.py
"""
from IPython import embed
import re

# ============================================================================
# LESSON: The three functions
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: match vs search vs findall")
print("=" * 60)
print()
print("  re.match(pattern, string)   — match at START of string only")
print("  re.search(pattern, string)  — find FIRST match anywhere")
print("  re.findall(pattern, string) — find ALL matches, return list")
print()
print("TRY:")
print()
print("  text = 'error: 404, error: 500, info: 200'")
print()
print("  # match — only looks at the start")
print("  m = re.match(r'error', text)")
print("  print(m)  — Match object (found 'error' at start)")
print()
print("  m = re.match(r'info', text)")
print("  print(m)  — None (info is not at the start)")
print()
print("  # search — finds first occurrence anywhere")
print("  m = re.search(r'info', text)")
print("  print(m)  — Match object")
print("  print(m.group())  — 'info'")
print("  print(m.start(), m.end())  — position in string")
print()
print("  # findall — finds all occurrences")
print("  matches = re.findall(r'\\d+', text)")
print("  print(matches)  — ['404', '500', '200']")
print()
print("  # EXAM Q10: findall with capture group")
print("  matches = re.findall(r'error: (\\d+)', text)")
print("  print(matches)  — PREDICT: ?")
print("  # When findall has a capture group, it returns the GROUP content,")
print("  # not the full match. 'info: 200' doesn't match 'error: (\\d+)'.")
print()

embed(header="Checkpoint 1: match (start) vs search (first) vs findall (all)")

# ============================================================================
# LESSON: Groups — capture parts of the match
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Groups (exam Q11)")
print("=" * 60)
print()
print("Parentheses create capture groups. group(0) is the whole match.")
print("group(1) is the first group. group(2) is the second. Etc.")
print()
print("TRY:")
print()
print("  pattern = re.compile(r'(\\w+)@(\\w+)\\.(\\w+)')")
print("  m = pattern.match('kai@oceanheart.ai')")
print()
print("  print(m.group(0))  — full match")
print("  print(m.group(1))  — first group")
print("  print(m.group(2))  — second group")
print("  print(m.group(3))  — third group")
print("  print(m.groups())  — tuple of ALL groups")
print()
print("  # EXAM Q11 correction:")
print("  # .groups() returns a TUPLE, not a list")
print("  # .group(2) is 'oceanheart', NOT 'ai'")
print("  # Groups are 1-indexed. group(0) = whole match.")
print()
print("  # PREDICT each one before running:")
print("  m = re.match(r'(\\d{4})-(\\d{2})-(\\d{2})', '2026-04-08')")
print("  print(m.group(0))   — ?")
print("  print(m.group(1))   — ?")
print("  print(m.group(2))   — ?")
print("  print(m.groups())   — ?")
print()

embed(header="Checkpoint 2: groups — 0=full, 1=first, .groups()=tuple")

# ============================================================================
# LESSON: Named groups
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Named groups — (?P<name>...)")
print("=" * 60)
print()
print("Named groups are more readable and accessible by name.")
print()
print("TRY:")
print()
print("  # Named group syntax: (?P<name>pattern)")
print("  pattern = re.compile(r'(?P<year>\\d{4})-(?P<month>\\d{2})-(?P<day>\\d{2})')")
print("  m = pattern.match('2026-04-08')")
print()
print("  print(m.group('year'))    — '2026'")
print("  print(m.group('month'))   — '04'")
print("  print(m.group('day'))     — '08'")
print("  print(m.groupdict())      — {'year': '2026', 'month': '04', 'day': '08'}")
print()
print("  # Real use: parse log lines")
print("  log_pattern = re.compile(")
print("      r'(?P<ts>[\\d:]+) (?P<level>\\w+) (?P<message>.*)'")
print("  )")
print("  m = log_pattern.match('09:15:30 ERROR Failed to connect to NATS')")
print("  if m:")
print("      print(m.groupdict())")
print()
print("  # Named groups work with findall too (returns list of tuples):")
print("  # Actually, findall with groups returns tuples of group values.")
print("  # Use finditer for named access:")
print("  for m in log_pattern.finditer('''09:01 INFO Started")
print("09:05 WARN Slow query")
print("09:10 ERROR NATS down'''):")
print("      print(m.groupdict())")
print()

embed(header="Checkpoint 3: named groups — groupdict() for structured parsing")

# ============================================================================
# LESSON: re.compile — compile once, use many times
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: compile, flags, and finditer")
print("=" * 60)
print()
print("re.compile(pattern) creates a reusable regex object.")
print("Faster when the same pattern is used many times.")
print()
print("TRY:")
print()
print("  # Compile once")
print("  EMAIL = re.compile(r'[\\w.+-]+@[\\w-]+\\.[\\w.]+')")
print()
print("  # Use many times")
print("  texts = [")
print("      'Contact kai@oceanheart.ai for support',")
print("      'No email here',")
print("      'Send to admin@example.com or dev@example.co.uk',")
print("  ]")
print("  for text in texts:")
print("      found = EMAIL.findall(text)")
print("      print(f'  {found}')")
print()
print("  # Flags")
print("  # re.IGNORECASE (re.I) — case-insensitive")
print("  p = re.compile(r'error', re.IGNORECASE)")
print("  print(p.findall('Error ERROR error'))  — all three match")
print()
print("  # re.MULTILINE (re.M) — ^ and $ match line boundaries")
print("  text = 'line1\\nline2\\nline3'")
print("  print(re.findall(r'^line', text))           — ['line'] (just start)")
print("  print(re.findall(r'^line', text, re.M))     — ['line', 'line', 'line']")
print()
print("  # finditer — iterator of Match objects (memory efficient)")
print("  for m in EMAIL.finditer('kai@a.com and ben@b.com'):")
print("      print(f'  {m.group()} at position {m.start()}-{m.end()}')")
print()

embed(header="Checkpoint 4: compile, IGNORECASE, MULTILINE, finditer")

# ============================================================================
# LESSON: Character classes and quantifiers
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: The regex cheat sheet")
print("=" * 60)
print()
print("CHARACTERS:")
print("  .        any character (except newline)")
print("  \\d       digit [0-9]")
print("  \\D       non-digit")
print("  \\w       word char [a-zA-Z0-9_]")
print("  \\W       non-word char")
print("  \\s       whitespace [ \\t\\n\\r\\f\\v]")
print("  \\S       non-whitespace")
print("  [abc]    character set")
print("  [^abc]   negated set")
print()
print("QUANTIFIERS:")
print("  *        0 or more (greedy)")
print("  +        1 or more (greedy)")
print("  ?        0 or 1")
print("  {n}      exactly n")
print("  {n,m}    between n and m")
print("  *? +? ?? non-greedy (minimal match)")
print()
print("ANCHORS:")
print("  ^        start of string (or line with re.M)")
print("  $        end of string (or line with re.M)")
print("  \\b       word boundary")
print()
print("TRY:")
print("  text = 'server-01 has 16GB RAM and 8 CPUs at 192.168.1.100'")
print("  print(re.findall(r'\\d+', text))        — all numbers")
print("  print(re.findall(r'\\b\\d+\\b', text))    — whole-word numbers only")
print("  print(re.findall(r'\\d+\\.\\d+\\.\\d+\\.\\d+', text))  — IP addresses")
print("  print(re.findall(r'\\d+GB', text))       — GB values")
print()

embed(header="Checkpoint 5: character classes and quantifiers — try the examples")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: Parse kubectl-style output with regex")
print("=" * 60)
print()
print("'kubectl_output' simulates 'kubectl get pods' text output.")
print()
print("Tasks:")
print("  1. Write a regex to parse each line into: name, ready, status, restarts, age")
print("  2. Use named groups")
print("  3. findall or finditer to process all lines")
print("  4. Group by status using defaultdict")
print("  5. Find pods with restarts > 0")
print()

kubectl_output = """NAME                          READY   STATUS             RESTARTS   AGE
advisor-musashi-7b4d5f6-x9k   1/1     Running            0          5d
advisor-medici-8c3e6g7-m2p    0/1     CrashLoopBackOff   7          5d
advisor-bankei-5a2b3c4-n8q    1/1     Running            0          5d
advisor-gibson-9d8e7f6-k4r    0/1     OOMKilled          3          2d
advisor-draper-1f2g3h4-j7s    1/1     Running            1          5d
nginx-deployment-6b7c8d-p5t   1/1     Running            0          12d
redis-master-0                1/1     Running            0          30d
advisor-karpathy-2g3h4i-w6u   1/1     Running            0          3d"""

from collections import defaultdict

embed(header="Checkpoint 6: parse kubectl output with regex + collections")

print()
print("DAY 7 COMPLETE.")
print()
print("  re.match   — start of string only")
print("  re.search  — first match anywhere")
print("  re.findall — all matches (returns group content if groups exist)")
print("  re.finditer — all matches as Match objects (memory efficient)")
print("  group(0) = full match, group(1) = first capture")
print("  .groups() = tuple, .groupdict() = dict")
print("  (?P<name>...) for named groups")
print("  re.compile() for reuse. re.I for case-insensitive.")
print()
print("Tomorrow: advanced regex — lookahead, substitution, SRE patterns.")
