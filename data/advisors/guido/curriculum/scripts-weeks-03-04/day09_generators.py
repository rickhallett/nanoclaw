#!/usr/bin/env python3
"""Day 9: Generators — yield, generator expressions, and the pipeline pattern.

This is where Python becomes a stream processing language.

Run: uv run python data/advisors/guido/curriculum/scripts-weeks-03-04/day09_generators.py
"""
from IPython import embed

# ============================================================================
# LESSON: yield makes a generator
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: yield basics")
print("=" * 60)
print()
print("A function with yield is a generator function.")
print("Calling it returns a generator object (an iterator).")
print("It pauses at each yield and resumes when next() is called.")
print()
print("TRY:")
print()
print("  def count_up(n):")
print("      i = 0")
print("      while i < n:")
print("          yield i")
print("          i += 1")
print()
print("  # Call it — does NOT execute the body")
print("  gen = count_up(5)")
print("  print(type(gen))  — generator object, not a list")
print()
print("  # Pull values one at a time")
print("  print(next(gen))  — 0")
print("  print(next(gen))  — 1")
print("  print(next(gen))  — 2")
print()
print("  # Get the rest as a list")
print("  print(list(gen))  — [3, 4] (only what's left)")
print()
print("  # Iterate normally")
print("  for x in count_up(3):")
print("      print(x)")
print()

embed(header="Checkpoint 1: yield — lazy, one-at-a-time production")

# ============================================================================
# LESSON: Generator expressions vs list comprehensions
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Generator expressions (exam Q8)")
print("=" * 60)
print()
print("List comprehension: [expr for x in it]  — builds entire list in memory")
print("Generator expression: (expr for x in it) — lazy, one item at a time")
print()
print("TRY:")
print()
print("  # List comprehension — all in memory")
print("  squares_list = [x**2 for x in range(5)]")
print("  print(type(squares_list))   — list")
print("  print(squares_list)         — [0, 1, 4, 9, 16]")
print()
print("  # Generator expression — lazy")
print("  squares_gen = (x**2 for x in range(5))")
print("  print(type(squares_gen))    — generator")
print("  print(sum(squares_gen))     — 30 (not 55! range(5) = 0,1,2,3,4)")
print("  print(sum(squares_gen))     — 0 (exhausted! this was exam Q8)")
print()
print("  # Memory difference:")
print("  import sys")
print("  big_list = [x for x in range(1000000)]")
print("  big_gen = (x for x in range(1000000))")
print("  print(f'list: {sys.getsizeof(big_list):,} bytes')")
print("  print(f'gen:  {sys.getsizeof(big_gen):,} bytes')")
print()
print("  # Generators can be passed directly to functions:")
print("  total = sum(x**2 for x in range(5))  # no extra parentheses needed")
print("  print(total)")
print()

import sys
embed(header="Checkpoint 2: generator expressions — lazy, exhaustible, memory-light")

# ============================================================================
# LESSON: yield from
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: yield from — delegation")
print("=" * 60)
print()
print("yield from delegates to another iterable or generator.")
print()
print("TRY:")
print()
print("  # Without yield from (verbose):")
print("  def chain_manual(*iterables):")
print("      for it in iterables:")
print("          for item in it:")
print("              yield item")
print()
print("  # With yield from (clean):")
print("  def chain_clean(*iterables):")
print("      for it in iterables:")
print("          yield from it")
print()
print("  print(list(chain_manual([1,2], [3,4], [5,6])))")
print("  print(list(chain_clean([1,2], [3,4], [5,6])))")
print()
print("  # Recursive generator: flatten arbitrarily nested lists")
print("  def flatten(lst):")
print("      for item in lst:")
print("          if isinstance(item, list):")
print("              yield from flatten(item)")
print("          else:")
print("              yield item")
print()
print("  nested = [1, [2, 3], [4, [5, 6]], 7]")
print("  print(list(flatten(nested)))")
print("  # PREDICT: ?")
print()

embed(header="Checkpoint 3: yield from — delegation and recursion")

# ============================================================================
# PATTERN: Generator pipelines
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: The pipeline pattern (this is the real power)")
print("=" * 60)
print()
print("Chain generators together like Unix pipes.")
print("Each stage transforms the stream lazily.")
print()
print("TRY — TYPE ALL OF THIS OUT:")
print()
print("  # Stage 1: read lines from data")
print("  def read_lines(data):")
print("      for line in data.strip().split('\\n'):")
print("          yield line")
print()
print("  # Stage 2: filter non-empty, non-comment lines")
print("  def filter_lines(lines):")
print("      for line in lines:")
print("          stripped = line.strip()")
print("          if stripped and not stripped.startswith('#'):")
print("              yield stripped")
print()
print("  # Stage 3: parse into fields")
print("  def parse_fields(lines):")
print("      for line in lines:")
print("          parts = line.split()")
print("          if len(parts) >= 3:")
print("              yield {'ts': parts[0], 'level': parts[1], 'msg': ' '.join(parts[2:])}")
print()
print("  # Stage 4: filter by level")
print("  def errors_only(records):")
print("      for record in records:")
print("          if record['level'] in ('ERROR', 'CRITICAL'):")
print("              yield record")
print()
print("  # The pipeline:")
print("  raw = '''")
print("  # Log file")
print("  09:01 INFO Server started")
print("  09:05 WARN Memory high")
print("  09:10 ERROR NATS down")
print("  09:12 INFO Reconnecting")
print("  09:15 ERROR Timeout on etcd")
print("  09:20 CRITICAL Disk full")
print("  '''")
print()
print("  pipeline = errors_only(parse_fields(filter_lines(read_lines(raw))))")
print("  for record in pipeline:")
print("      print(record)")
print()
print("NOTHING executes until you iterate. The entire pipeline is lazy.")
print("For a 10GB log file, memory usage stays constant.")
print()

embed(header="Checkpoint 4: generator pipeline — type it all out")

# ============================================================================
# PATTERN: Generator as coroutine (send)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: send() — two-way generators (advanced)")
print("=" * 60)
print()
print("Generators can RECEIVE values via send(). Rarely used but")
print("important to understand for async Python and some frameworks.")
print()
print("TRY:")
print()
print("  def accumulator():")
print("      total = 0")
print("      while True:")
print("          value = yield total")
print("          if value is None:")
print("              break")
print("          total += value")
print()
print("  acc = accumulator()")
print("  next(acc)           # prime the generator (advance to first yield)")
print("  print(acc.send(10)) # send 10, get total=10")
print("  print(acc.send(20)) # send 20, get total=30")
print("  print(acc.send(5))  # send 5, get total=35")
print()
print("Pattern: next(gen) primes it. send(value) both sends and receives.")
print("This is the basis of Python's async/await under the hood.")
print()

embed(header="Checkpoint 5: send — two-way generators")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: Build a log processing pipeline")
print("=" * 60)
print()
print("Build a 5-stage generator pipeline for processing log data:")
print()
print("  Stage 1: read_log(path) — yield lines from a file (or string)")
print("  Stage 2: parse_log(lines) — yield {ts, level, message} dicts")
print("  Stage 3: filter_level(records, min_level) — yield records at or above level")
print("  Stage 4: add_context(records) — yield records with extra fields")
print("           (e.g., line_number, is_error)")
print("  Stage 5: format_output(records) — yield formatted strings")
print()
print("Chain them: format_output(add_context(filter_level(parse_log(read_log(data)), 'WARN')))")
print()
print("'log_data' is ready for you to use.")
print()

log_data = """09:01:15 INFO Server started on port 8080
09:01:16 INFO Connected to PostgreSQL
09:02:30 DEBUG Health check passed
09:05:12 WARN Slow query: SELECT * FROM pods (2.3s)
09:06:00 INFO Request: GET /api/pods (200, 45ms)
09:08:45 WARN Memory usage at 82%
09:10:00 ERROR Failed to connect to NATS: connection refused
09:10:05 ERROR Retry 1/3: NATS connection
09:10:10 ERROR Retry 2/3: NATS connection
09:10:15 INFO NATS reconnected
09:12:00 WARN Disk usage at 88%
09:15:30 CRITICAL etcd leader election failed
09:15:31 CRITICAL Cluster entering read-only mode
09:16:00 ERROR kubectl apply failed: etcd timeout
09:20:00 INFO Recovery: etcd leader elected
09:20:01 INFO Cluster back to read-write mode"""

embed(header="Checkpoint 6: build the full 5-stage pipeline")

print()
print("DAY 9 COMPLETE.")
print()
print("  yield          — makes a generator function")
print("  yield from     — delegates to another iterable")
print("  (expr for x)   — generator expression (lazy)")
print("  next(gen)      — advance one step")
print("  Pipeline       — chain generators: stage3(stage2(stage1(data)))")
print("  send(value)    — two-way communication (advanced)")
print()
print("Generators are how Python does stream processing without eating RAM.")
print("Tomorrow: the capstone — a full log analyser using everything.")
