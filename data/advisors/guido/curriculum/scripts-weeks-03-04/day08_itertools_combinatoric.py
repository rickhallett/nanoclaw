#!/usr/bin/env python3
"""Day 8: itertools — product, permutations, combinations, starmap.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day08_itertools_combinatoric.py
"""
from IPython import embed
from itertools import product, permutations, combinations, combinations_with_replacement, starmap
from functools import reduce

# ============================================================================
# LESSON: product — cartesian product
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: product — every combination of inputs")
print("=" * 60)
print()
print("product(A, B) yields every (a, b) pair. Like nested for-loops.")
print()
print("TRY:")
print()
print("  # Basic: all pairs")
print("  colors = ['red', 'blue']")
print("  sizes = ['S', 'M', 'L']")
print("  print(list(product(colors, sizes)))")
print("  # PREDICT: ? (how many items?)")
print()
print("  # Three iterables")
print("  envs = ['dev', 'prod']")
print("  regions = ['us', 'eu']")
print("  tiers = ['web', 'db']")
print("  for env, region, tier in product(envs, regions, tiers):")
print("      print(f'  {env}-{region}-{tier}')")
print("  # How many? 2 * 2 * 2 = 8")
print()
print("  # product with repeat — like nested loops of same iterable")
print("  print(list(product([0, 1], repeat=3)))")
print("  # All 3-bit binary numbers: 000, 001, 010, ..., 111")
print()
print("  # Real use: test matrix")
print("  py_versions = ['3.10', '3.11', '3.12']")
print("  os_list = ['ubuntu', 'alpine']")
print("  for py, os_name in product(py_versions, os_list):")
print("      print(f'  test: python {py} on {os_name}')")
print()

embed(header="Checkpoint 1: product — cartesian product, test matrices")

# ============================================================================
# LESSON: permutations and combinations
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: permutations and combinations")
print("=" * 60)
print()
print("permutations(it, r)  — all orderings of r items (order matters)")
print("combinations(it, r)  — all selections of r items (order doesn't matter)")
print()
print("TRY:")
print()
print("  items = ['A', 'B', 'C']")
print()
print("  # Permutations of 2: all orderings of 2 items")
print("  perms = list(permutations(items, 2))")
print("  print(f'permutations(3,2) = {len(perms)}: {perms}')")
print("  # PREDICT count: ? (includes both AB and BA)")
print()
print("  # Combinations of 2: all selections of 2 items")
print("  combs = list(combinations(items, 2))")
print("  print(f'combinations(3,2) = {len(combs)}: {combs}')")
print("  # PREDICT count: ? (AB only, no BA)")
print()
print("  # Full permutations (all items)")
print("  full = list(permutations(items))")
print("  print(f'permutations(3) = {len(full)}: {full}')")
print("  # 3! = 6")
print()
print("  # combinations_with_replacement — can pick same item twice")
print("  cwr = list(combinations_with_replacement(items, 2))")
print("  print(f'combinations_with_replacement(3,2) = {len(cwr)}: {cwr}')")
print()
print("  # Real use: find all pairs of pods that might conflict")
print("  pods = ['musashi', 'medici', 'bankei', 'gibson']")
print("  print('Possible conflicts:')")
print("  for p1, p2 in combinations(pods, 2):")
print("      print(f'  {p1} <-> {p2}')")
print()

embed(header="Checkpoint 2: permutations vs combinations — order matters or not")

# ============================================================================
# LESSON: starmap
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: starmap — map with unpacking")
print("=" * 60)
print()
print("map(func, iterable) calls func(item) for each item.")
print("starmap(func, iterable) calls func(*item) — unpacks tuples as args.")
print()
print("TRY:")
print()
print("  # Regular map")
print("  print(list(map(str.upper, ['hello', 'world'])))")
print()
print("  # starmap: each item is a tuple of args")
print("  pairs = [(2, 3), (4, 5), (6, 7)]")
print("  print(list(starmap(pow, pairs)))")
print("  # PREDICT: ? (pow(2,3), pow(4,5), pow(6,7))")
print()
print("  # Real use: apply operations to name-value pairs")
print("  configs = [('port', 8080), ('workers', 4), ('timeout', 30)]")
print("  formatted = list(starmap(lambda k, v: f'{k}={v}', configs))")
print("  print(formatted)")
print()
print("  # starmap with max")
print("  data = [(3, 5, 1), (8, 2, 4), (6, 9, 3)]")
print("  print(list(starmap(max, data)))")
print("  # PREDICT: ?")
print()

embed(header="Checkpoint 3: starmap — function(*args) for each tuple")

# ============================================================================
# LESSON: accumulate (bonus)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: accumulate — running totals")
print("=" * 60)
print()
print("accumulate(it, func) — running accumulation (default: addition).")
print()
print("TRY:")
print()
print("  from itertools import accumulate")
print("  import operator")
print()
print("  # Running sum")
print("  nums = [1, 2, 3, 4, 5]")
print("  print(list(accumulate(nums)))")
print("  # PREDICT: ?")
print()
print("  # Running max")
print("  temps = [20, 22, 19, 25, 23, 28, 21]")
print("  print(list(accumulate(temps, max)))")
print("  # PREDICT: ? (running maximum temperature)")
print()
print("  # Running product")
print("  print(list(accumulate([1, 2, 3, 4], operator.mul)))")
print("  # PREDICT: ? (1, 1*2, 1*2*3, 1*2*3*4)")
print()
print("  # Real use: cumulative error count")
print("  errors_per_hour = [0, 1, 0, 3, 2, 0, 5, 1]")
print("  cumulative = list(accumulate(errors_per_hour))")
print("  for hour, (count, total) in enumerate(zip(errors_per_hour, cumulative)):")
print("      bar = '#' * total")
print("      print(f'  hour {hour}: {count} errors (total: {total}) {bar}')")
print()

from itertools import accumulate
import operator
embed(header="Checkpoint 4: accumulate — running totals and running max")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Infrastructure test matrix generator")
print("=" * 60)
print()
print("Build a test matrix generator for a CI/CD pipeline.")
print()
print("Given:")
print("  python_versions = ['3.10', '3.11', '3.12']")
print("  os_list = ['ubuntu-22.04', 'alpine-3.18']")
print("  db_backends = ['postgres', 'sqlite']")
print()
print("Tasks:")
print("  1. product: generate all test combinations (how many?)")
print("  2. combinations: find all pairs of Python versions for cross-testing")
print("  3. starmap: format each test as 'py3.11-ubuntu-22.04-postgres'")
print("  4. accumulate: if each test takes ~2 min, show running total time")
print("  5. Print the full matrix and estimated total CI time")
print()

python_versions = ['3.10', '3.11', '3.12']
os_list = ['ubuntu-22.04', 'alpine-3.18']
db_backends = ['postgres', 'sqlite']

embed(header="Checkpoint 5: CI test matrix — product + combinations + starmap")

print()
print("DAY 8 COMPLETE.")
print()
print("  product(A, B)          — cartesian product (nested loops)")
print("  permutations(it, r)    — all orderings (AB ≠ BA)")
print("  combinations(it, r)    — all selections (AB = BA)")
print("  starmap(fn, tuples)    — map with argument unpacking")
print("  accumulate(it, fn)     — running totals")
print()
print("Tomorrow: generators — yield, send, and the pipeline pattern.")
