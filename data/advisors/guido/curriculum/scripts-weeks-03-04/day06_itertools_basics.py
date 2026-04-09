#!/usr/bin/env python3
"""Day 6: itertools — chain, islice, repeat, count, cycle.

These replace nested for-loops and manual list building.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day06_itertools_basics.py
"""
from IPython import embed
from itertools import chain, islice, repeat, count, cycle

# ============================================================================
# KEY CONCEPT: itertools functions return ITERATORS, not lists
# ============================================================================

print("=" * 60)
print("ITERTOOLS — KEY CONCEPT")
print("=" * 60)
print()
print("Every itertools function returns a LAZY ITERATOR.")
print("It does NOT build a list in memory.")
print("To see the result: list(result) or iterate with for.")
print()
print("This means itertools can handle infinite sequences")
print("and million-item datasets without eating your RAM.")
print()

# ============================================================================
# LESSON: chain — concatenate iterables
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: chain — flatten multiple iterables")
print("=" * 60)
print()
print("chain(a, b, c) yields all items from a, then b, then c.")
print("Like + for lists, but lazy and works on any iterable.")
print()
print("TRY:")
print("  a = [1, 2, 3]")
print("  b = [4, 5, 6]")
print("  c = [7, 8, 9]")
print()
print("  # chain them")
print("  result = chain(a, b, c)")
print("  print(type(result))      — not a list!")
print("  print(list(result))      — [1, 2, 3, 4, 5, 6, 7, 8, 9]")
print()
print("  # chain.from_iterable — flatten a list of lists")
print("  nested = [[1, 2], [3, 4], [5, 6]]")
print("  flat = list(chain.from_iterable(nested))")
print("  print(flat)")
print()
print("  # Real use: merge log files")
print("  log1 = ['[web] req 1', '[web] req 2']")
print("  log2 = ['[db] query 1', '[db] query 2']")
print("  all_logs = list(chain(log1, log2))")
print("  print(all_logs)")
print()

embed(header="Checkpoint 1: chain — concatenate iterables")

# ============================================================================
# LESSON: islice — slice any iterable
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: islice — slice without building a list")
print("=" * 60)
print()
print("islice(iterable, stop) or islice(iterable, start, stop[, step])")
print("Like list slicing [start:stop:step] but works on ANY iterable.")
print()
print("TRY:")
print()
print("  # Basic: first 5 items")
print("  print(list(islice(range(100), 5)))")
print("  # PREDICT: ?")
print()
print("  # Start and stop: items at index 2, 3, 4")
print("  print(list(islice(range(100), 2, 5)))")
print("  # PREDICT: ?")
print()
print("  # With step: every 3rd item from index 0 to 20")
print("  print(list(islice(range(100), 0, 20, 3)))")
print("  # PREDICT: ?")
print()
print("  # Real use: first 10 lines of a file (without reading entire file)")
print("  with open('/etc/hosts') as f:")
print("      head = list(islice(f, 10))")
print("      for line in head:")
print("          print(line.rstrip())")
print()
print("  # chain + islice (exam Q5):")
print("  a = [1, 2, 3]")
print("  b = [4, 5, 6]")
print("  c = chain(a, b)")
print("  print(list(islice(c, 2, 5)))  — PREDICT: ?")
print()

embed(header="Checkpoint 2: islice — slice anything lazily")

# ============================================================================
# LESSON: count, cycle, repeat — infinite iterators
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Infinite iterators")
print("=" * 60)
print()
print("These three produce INFINITE sequences. Always use islice or a break.")
print()
print("TRY:")
print()
print("  # count(start, step) — infinite counter")
print("  c = count(10, 2)     # 10, 12, 14, 16, ...")
print("  print(list(islice(c, 5)))  — PREDICT: ?")
print()
print("  # cycle(iterable) — repeat the iterable forever")
print("  colors = cycle(['red', 'green', 'blue'])")
print("  print(list(islice(colors, 7)))  — PREDICT: ?")
print()
print("  # repeat(value, times) — repeat a value")
print("  print(list(repeat('hello', 3)))  — PREDICT: ?")
print()
print("  # repeat without times is INFINITE:")
print("  inf = repeat(0)")
print("  print(list(islice(inf, 5)))  — PREDICT: ?")
print()
print("  # Real use: assign round-robin IDs")
print("  servers = cycle(['web-01', 'web-02', 'web-03'])")
print("  requests = [f'req-{i}' for i in range(7)]")
print("  assignments = list(zip(requests, servers))")
print("  for req, server in assignments:")
print("      print(f'  {req} → {server}')")
print()

embed(header="Checkpoint 3: count, cycle, repeat — always pair with islice")

# ============================================================================
# LESSON: enumerate and zip (not itertools but essential)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: enumerate and zip — the forgotten essentials")
print("=" * 60)
print()
print("Not in itertools but used with them constantly.")
print()
print("TRY:")
print()
print("  # enumerate: index + value")
print("  pods = ['musashi', 'medici', 'bankei']")
print("  for i, pod in enumerate(pods):")
print("      print(f'  {i}: {pod}')")
print()
print("  # enumerate with start:")
print("  for i, pod in enumerate(pods, start=1):")
print("      print(f'  {i}: {pod}')")
print()
print("  # zip: pair up iterables (stops at shortest)")
print("  names = ['kai', 'ben']")
print("  ages = [38, 35, 42]  # extra item")
print("  print(list(zip(names, ages)))  — PREDICT: ?")
print()
print("  # zip with three iterables")
print("  hosts = ['web-01', 'web-02']")
print("  cpus = [2, 4]")
print("  mems = [512, 1024]")
print("  for host, cpu, mem in zip(hosts, cpus, mems):")
print("      print(f'  {host}: {cpu} CPU, {mem}Mi')")
print()
print("  # dict from zip")
print("  keys = ['name', 'role', 'level']")
print("  values = ['kai', 'sre', 'senior']")
print("  d = dict(zip(keys, values))")
print("  print(d)")
print()

embed(header="Checkpoint 4: enumerate + zip — build fluency")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Combine them all")
print("=" * 60)
print()
print("Scenario: you have three log files (simulated as lists).")
print()
print("Tasks:")
print("  1. chain all three into one stream")
print("  2. Use enumerate to add line numbers")
print("  3. Use islice to get lines 5-15 only")
print("  4. Use cycle to assign each line to a processing worker")
print("  5. Print the result: worker, line_no, content")
print()

log_web = [f"[web] request {i}" for i in range(10)]
log_db = [f"[db] query {i}" for i in range(8)]
log_cache = [f"[cache] hit {i}" for i in range(6)]

embed(header="Checkpoint 5: chain + enumerate + islice + cycle together")

print()
print("DAY 6 COMPLETE.")
print()
print("  chain(a, b)        — concatenate iterables lazily")
print("  chain.from_iterable — flatten nested iterables")
print("  islice(it, start, stop) — slice any iterable")
print("  count(start, step)  — infinite counter")
print("  cycle(it)           — infinite repeat of iterable")
print("  repeat(val, n)      — repeat a value n times")
print()
print("ALL return iterators. list() to materialise. islice() to bound.")
print("Tomorrow: groupby, takewhile, dropwhile.")
