#!/usr/bin/env python3
"""Day 4: deque — the double-ended queue.

Run: uv run python data/advisors/guido/curriculum/scripts/day04_deque.py
"""
from IPython import embed
from collections import deque

# ============================================================================
# LESSON: deque basics
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: Basic operations")
print("=" * 60)
print()
print("'d' is a deque([1, 2, 3]).")
print()
print("TRY EACH and predict the result BEFORE you hit enter:")
print("  d.append(4)       — adds to RIGHT end")
print("  print(list(d))")
print("  d.appendleft(0)   — adds to LEFT end")
print("  print(list(d))")
print("  d.pop()           — removes from RIGHT, returns it")
print("  d.popleft()       — removes from LEFT, returns it")
print("  print(list(d))")
print()
print("PERFORMANCE:")
print("  list.insert(0, x) → O(n) — shifts every element")
print("  deque.appendleft(x) → O(1) — constant time")
print("  For 1M items: list is seconds, deque is milliseconds.")
print()

d = deque([1, 2, 3])

embed(header="Checkpoint 1: deque basic operations")

# ============================================================================
# LESSON: maxlen — the bounded buffer
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: maxlen (this was exam Q3)")
print("=" * 60)
print()
print("'d' is a deque([1, 2, 3], maxlen=3).")
print()
print("TRY (predict BEFORE each one):")
print("  d.append(4)        — what gets dropped? From which end?")
print("  print(list(d))     — predict this FIRST")
print("  d.appendleft(0)    — what gets dropped now?")
print("  print(list(d))     — predict this FIRST")
print()
print("RULE: append pushes RIGHT, drops from LEFT.")
print("      appendleft pushes LEFT, drops from RIGHT.")
print("      NEVER raises. SILENTLY drops from the opposite end.")
print()
print("This is how you build bounded buffers and rolling windows.")
print()

d = deque([1, 2, 3], maxlen=3)

embed(header="Checkpoint 2: maxlen behaviour — the exam question")

# ============================================================================
# PATTERN: Rolling window
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Rolling window")
print("=" * 60)
print()
print("'window' is a deque(maxlen=5). 'data' is a stream of numbers.")
print()
print("TRY:")
print("  for value in data:")
print("      window.append(value)")
print("      if len(window) == 5:")
print("          avg = sum(window) / len(window)")
print("          print(f'window: {list(window)}, avg: {avg:.1f}')")
print()
print("This is exactly how you'd monitor rolling average response times,")
print("CPU usage, or error rates in an SRE dashboard.")
print()

window = deque(maxlen=5)
data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

embed(header="Checkpoint 3: rolling window average")

# ============================================================================
# PATTERN: FIFO queue
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: FIFO queue")
print("=" * 60)
print()
print("deque as a job queue: append to add, popleft to process.")
print()
print("TRY:")
print("  q = deque()")
print("  q.append('deploy-web')     — enqueue")
print("  q.append('restart-nats')")
print("  q.append('backup-etcd')")
print("  print(f'queue: {list(q)}')")
print("  job = q.popleft()          — dequeue (FIFO: first in, first out)")
print("  print(f'processing: {job}')")
print("  print(f'remaining: {list(q)}')")
print()
print("Compare: list.pop(0) is O(n). deque.popleft() is O(1).")
print()

q = deque()

embed(header="Checkpoint 4: FIFO job queue")

# ============================================================================
# LESSON: rotate
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: rotate")
print("=" * 60)
print()
print("'d' is deque([1, 2, 3, 4, 5]).")
print()
print("TRY (predict first):")
print("  d.rotate(2)       — positive: rotate RIGHT")
print("  print(list(d))    — last 2 items moved to front")
print("  d.rotate(-2)      — negative: rotate LEFT (undo)")
print("  print(list(d))    — back to original")
print("  d.rotate(-1)      — shift left by 1")
print("  print(list(d))    — first item goes to end")
print()

d = deque([1, 2, 3, 4, 5])

embed(header="Checkpoint 5: rotate")

# ============================================================================
# PATTERN: tail -f simulator
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 6: tail -f simulator")
print("=" * 60)
print()
print("Build a log tail: keep the last 10 lines of a simulated log stream.")
print("'tail' is deque(maxlen=10).")
print()
print("TRY:")
print("  for i in range(50):")
print("      line = f'[{i:03d}] Log entry: event_{i}'")
print("      tail.append(line)")
print()
print("  print('--- Last 10 lines ---')")
print("  for line in tail:")
print("      print(line)")
print()
print("Notice: you never had to check length or manually evict old entries.")
print("maxlen handles it silently. This is the deque advantage.")
print()

tail = deque(maxlen=10)

embed(header="Checkpoint 6: tail -f with deque(maxlen=10)")

# ============================================================================
# EXERCISE: SRE alert buffer
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 7: SRE alert buffer")
print("=" * 60)
print()
print("'alerts' is a stream of (timestamp, severity, message) tuples.")
print("Build TWO things:")
print("  1. 'recent' — deque(maxlen=5) of all alerts (rolling window)")
print("  2. 'critical_history' — deque(maxlen=3) of CRITICAL alerts only")
print()
print("After processing, print both buffers.")
print("This pattern: separate bounded buffers for different severity levels.")
print()

alerts = [
    ("09:01", "INFO", "Pod advisor-musashi started"),
    ("09:02", "WARN", "Memory usage 82%"),
    ("09:03", "CRITICAL", "NFS mount failed"),
    ("09:04", "INFO", "Health check passed"),
    ("09:05", "ERROR", "NATS consumer lag 500"),
    ("09:06", "CRITICAL", "etcd leader lost"),
    ("09:07", "INFO", "Pod advisor-medici restarted"),
    ("09:08", "WARN", "Disk usage 91%"),
    ("09:09", "CRITICAL", "OOMKilled: advisor-gibson"),
    ("09:10", "INFO", "Argo sync completed"),
]

recent = deque(maxlen=5)
critical_history = deque(maxlen=3)

embed(header="Checkpoint 7: alert buffer — two deques, different filters")

print()
print("DAY 4 COMPLETE.")
print()
print("You should now know:")
print("  - deque: O(1) append/pop from both ends")
print("  - maxlen silently drops from the OPPOSITE end. Never raises.")
print("  - append → drops left. appendleft → drops right.")
print("  - FIFO queue: append + popleft")
print("  - Rolling window: deque(maxlen=N)")
print("  - rotate(n): positive=right, negative=left")
