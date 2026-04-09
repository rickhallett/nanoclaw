#!/usr/bin/env python3
"""Day 5: collections integration — combining all three.

Run: uv run python data/advisors/guido/curriculum/scripts/day05_collections_integration.py
"""
from IPython import embed
from collections import defaultdict, Counter, deque

# ============================================================================
# REVIEW: Mental model
# ============================================================================

print("=" * 60)
print("COLLECTIONS CHEAT SHEET")
print("=" * 60)
print()
print("  defaultdict(list)  → group items by key    → 'if k not in d' is dead")
print("  defaultdict(int)   → simple counting        → replaced by Counter")
print("  defaultdict(set)   → unique items per key   → dedup per group")
print("  Counter(iterable)  → count + top-N + math   → log analysis, metrics")
print("  deque(maxlen=N)    → bounded buffer/queue   → rolling windows, FIFO")
print()
print("=" * 60)

# ============================================================================
# SCENARIO: Parsing kubectl-style output
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 1: Parse and analyse pod data")
print("=" * 60)
print()
print("'raw' is multiline text like kubectl get pods output.")
print("'entries' has been parsed into (name, status, restarts) tuples.")
print()
print("Tasks (use the right tool for each):")
print("  1. Counter: count how many pods in each status")
print("  2. Counter: what is the most common status? (most_common(1))")
print("  3. defaultdict(list): group pod names by status")
print("  4. defaultdict(set): unique statuses per namespace prefix")
print("     (namespace = name.split('-')[0] if '-' in name else 'other')")
print("  5. deque(maxlen=3): track last 3 restart counts for medici")
print()

raw = """advisor-musashi Running 0
advisor-medici CrashLoopBackOff 5
advisor-bankei Running 0
advisor-draper Running 1
advisor-gibson OOMKilled 3
advisor-medici CrashLoopBackOff 6
nginx Running 0
advisor-medici CrashLoopBackOff 7
coredns Running 0
redis Pending 0""".strip().split("\n")

entries = []
for line in raw:
    parts = line.split()
    entries.append((parts[0], parts[1], int(parts[2])))

embed(header="Checkpoint 1: five tasks on pod data — use the right collection for each")

# ============================================================================
# SCENARIO: Access log analysis
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Web server access log")
print("=" * 60)
print()
print("'access_log' is a list of (method, path, status, response_ms) tuples.")
print()
print("Build ALL of these:")
print("  status_counts = Counter(...)           — count of each status code")
print("  method_paths = defaultdict(set)        — unique paths per HTTP method")
print("  path_times = defaultdict(list)         — response times per path")
print("  error_window = deque(maxlen=5)         — last 5 errors (status >= 400)")
print()
print("Then answer:")
print("  a) What is the most common status code?")
print("  b) How many unique paths does GET hit?")
print("  c) Which path has the highest average response time?")
print("  d) What are the last 5 errors?")
print()

access_log = [
    ("GET",  "/api/pods",       200,  45),
    ("GET",  "/api/pods",       200,  52),
    ("POST", "/api/deploy",     201, 230),
    ("GET",  "/api/pods",       500, 890),
    ("GET",  "/api/nodes",      200,  38),
    ("POST", "/api/deploy",     500,1200),
    ("GET",  "/api/health",     200,  12),
    ("GET",  "/api/nodes",      200,  41),
    ("POST", "/api/deploy",     201, 210),
    ("GET",  "/api/health",     200,  15),
    ("DELETE","/api/pods/old",  204, 180),
    ("GET",  "/api/pods",       200,  48),
    ("GET",  "/api/pods",       404, 320),
    ("POST", "/api/rollback",   500, 950),
    ("GET",  "/api/health",     200,  11),
]

status_counts = Counter()
method_paths = defaultdict(set)
path_times = defaultdict(list)
error_window = deque(maxlen=5)

embed(header="Checkpoint 2: access log — Counter + defaultdict + deque together")

# ============================================================================
# SCENARIO: Event stream processing
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Event stream — the full pattern")
print("=" * 60)
print()
print("'events' is a time-ordered stream of cluster events.")
print()
print("Build a monitoring dashboard:")
print("  1. event_counts: Counter of event types")
print("  2. by_pod: defaultdict(list) — events per pod")
print("  3. severity_pods: defaultdict(set) — which pods hit each severity")
print("  4. recent_critical: deque(maxlen=3) — last 3 critical events")
print("  5. pod_event_window: defaultdict(lambda: deque(maxlen=3))")
print("     — last 3 events PER POD (nested: defaultdict of deques)")
print()
print("The last one is the advanced pattern. A defaultdict whose factory")
print("produces deques. Each pod gets its own rolling window.")
print()

events = [
    {"ts": "09:01", "pod": "musashi",  "type": "Started",        "severity": "info"},
    {"ts": "09:02", "pod": "medici",   "type": "Pulled",         "severity": "info"},
    {"ts": "09:03", "pod": "medici",   "type": "CrashLoopBackOff","severity": "error"},
    {"ts": "09:04", "pod": "musashi",  "type": "HealthCheck",    "severity": "info"},
    {"ts": "09:05", "pod": "gibson",   "type": "OOMKilled",      "severity": "critical"},
    {"ts": "09:06", "pod": "medici",   "type": "BackOff",        "severity": "warn"},
    {"ts": "09:07", "pod": "medici",   "type": "CrashLoopBackOff","severity": "error"},
    {"ts": "09:08", "pod": "bankei",   "type": "Started",        "severity": "info"},
    {"ts": "09:09", "pod": "gibson",   "type": "OOMKilled",      "severity": "critical"},
    {"ts": "09:10", "pod": "medici",   "type": "Pulled",         "severity": "info"},
    {"ts": "09:11", "pod": "medici",   "type": "CrashLoopBackOff","severity": "error"},
    {"ts": "09:12", "pod": "draper",   "type": "HealthCheck",    "severity": "info"},
]

event_counts = Counter()
by_pod = defaultdict(list)
severity_pods = defaultdict(set)
recent_critical = deque(maxlen=3)
pod_event_window = defaultdict(lambda: deque(maxlen=3))

embed(header="Checkpoint 3: cluster event dashboard — all collections together")

# ============================================================================
# CHECKPOINT QUIZ
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: Self-test (answer in your head, then verify)")
print("=" * 60)
print()
print("Answer these WITHOUT running code:")
print()
print("  1. defaultdict(list)['missing'] returns what?")
print("  2. Counter('aab').most_common(1) returns what type? What value?")
print("  3. deque([1,2,3], maxlen=3) — after .append(4), what is the list?")
print("  4. Counter(a=3) - Counter(a=5) — what is the result?")
print("  5. defaultdict(int)['x'] += 1 — what is d['x'] now? Why?")
print("  6. deque(maxlen=5) with 10 appends — how many items at the end?")
print("  7. Counter('hello')['z'] — does it raise KeyError?")
print("  8. What is the difference between Counter.subtract() and the - operator?")
print()

embed(header="Checkpoint 4: verify your answers in the REPL")

print()
print("=" * 60)
print("DAY 5 COMPLETE — COLLECTIONS MODULE FINISHED")
print("=" * 60)
print()
print("If you can build the Checkpoint 3 dashboard from memory,")
print("you own the collections module. Not FLUENT yet — that comes")
print("with repetition. But FUNCTIONAL. Which is where you need to be.")
print()
print("Tomorrow: subprocess.run — the SRE's most important function.")
