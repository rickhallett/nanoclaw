#!/usr/bin/env python3
"""Day 2: defaultdict — real patterns.

Run: uv run python data/advisors/guido/curriculum/scripts/day02_defaultdict_patterns.py
"""
from IPython import embed
from collections import defaultdict

# ============================================================================
# PATTERN 1: Inverted index
# ============================================================================

print("=" * 60)
print("CHECKPOINT 1: Inverted index")
print("=" * 60)
print()
print("'tags' is a list of (tag, filename) tuples.")
print("Build an index: tag → [filenames]")
print()
print("TRY:")
print("  index = defaultdict(list)")
print("  for tag, item in tags:")
print("      index[tag].append(item)")
print("  print(dict(index))")
print("  print(index['k8s'])")
print()

tags = [
    ("k8s", "pod.yaml"), ("k8s", "svc.yaml"), ("docker", "Dockerfile"),
    ("k8s", "deploy.yaml"), ("docker", "compose.yaml"), ("ci", "Jenkinsfile"),
    ("k8s", "ingress.yaml"), ("ci", ".gitlab-ci.yml"),
]
index = defaultdict(list)

embed(header="Checkpoint 1: build the inverted index")

# ============================================================================
# PATTERN 2: Pod status grouping (SRE scenario)
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 2: Pod status grouping")
print("=" * 60)
print()
print("'pods' is a list of dicts, like kubectl output.")
print()
print("Task A: group pod names by status → defaultdict(list)")
print("Task B: group pod names by namespace → defaultdict(list)")
print("Task C: unique statuses per namespace → defaultdict(set)")
print()
print("TRY EACH ONE. Type it out.")
print()

pods = [
    {"name": "advisor-musashi", "namespace": "halo-fleet", "status": "Running"},
    {"name": "advisor-medici", "namespace": "halo-fleet", "status": "CrashLoopBackOff"},
    {"name": "nginx", "namespace": "default", "status": "Running"},
    {"name": "advisor-bankei", "namespace": "halo-fleet", "status": "Running"},
    {"name": "redis", "namespace": "default", "status": "Pending"},
    {"name": "advisor-gibson", "namespace": "halo-fleet", "status": "OOMKilled"},
    {"name": "coredns", "namespace": "kube-system", "status": "Running"},
]

by_status = defaultdict(list)
by_namespace = defaultdict(list)
unique_statuses = defaultdict(set)

embed(header="Checkpoint 2: three grouping tasks on pod data")

# ============================================================================
# PATTERN 3: Accumulating statistics
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 3: Accumulating statistics")
print("=" * 60)
print()
print("'metrics' is a stream of (host, response_time_ms) tuples.")
print("Build: host → list of response times")
print("Then compute: host → average response time")
print()
print("TRY:")
print("  times = defaultdict(list)")
print("  for host, ms in metrics:")
print("      times[host].append(ms)")
print("  for host, values in times.items():")
print("      avg = sum(values) / len(values)")
print("      print(f'{host}: avg={avg:.1f}ms, samples={len(values)}')")
print()

metrics = [
    ("web-01", 120), ("web-02", 85), ("web-01", 95),
    ("web-03", 200), ("web-02", 110), ("web-01", 130),
    ("web-03", 180), ("web-02", 90), ("web-01", 105),
    ("web-03", 220), ("web-02", 95), ("web-03", 190),
]

times = defaultdict(list)

embed(header="Checkpoint 3: response time statistics per host")

# ============================================================================
# PATTERN 4: defaultdict vs setdefault vs manual check
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 4: Three ways to do the same thing")
print("=" * 60)
print()
print("All three approaches group items. Compare them.")
print()
print("TRY EACH:")
print()
print("  # Way 1: manual check (ugly, verbose)")
print("  d1 = {}")
print("  for k, v in data:")
print("      if k not in d1:")
print("          d1[k] = []")
print("      d1[k].append(v)")
print()
print("  # Way 2: setdefault (one-liner but reads poorly)")
print("  d2 = {}")
print("  for k, v in data:")
print("      d2.setdefault(k, []).append(v)")
print()
print("  # Way 3: defaultdict (clean, obvious)")
print("  d3 = defaultdict(list)")
print("  for k, v in data:")
print("      d3[k].append(v)")
print()
print("All three produce identical results. defaultdict is the Pythonic way.")
print()

data = [("a", 1), ("b", 2), ("a", 3), ("b", 4), ("c", 5)]

embed(header="Checkpoint 4: compare the three approaches")

# ============================================================================
# SCRIPT CHALLENGE
# ============================================================================

print()
print("=" * 60)
print("CHECKPOINT 5: Script challenge")
print("=" * 60)
print()
print("'access_log' simulates web server access log entries.")
print()
print("Build THREE things:")
print("  1. by_method: HTTP method → list of paths (defaultdict(list))")
print("  2. by_status: status code → set of unique paths (defaultdict(set))")
print("  3. by_path: path → list of response times (defaultdict(list))")
print()
print("Then print:")
print("  - All paths that returned a 500")
print("  - The path with the highest average response time")
print("  - How many unique paths each HTTP method hit")
print()

access_log = [
    ("GET",  "/api/pods",    200, 45),
    ("GET",  "/api/pods",    200, 52),
    ("POST", "/api/deploy",  201, 230),
    ("GET",  "/api/pods",    500, 890),
    ("GET",  "/api/nodes",   200, 38),
    ("POST", "/api/deploy",  500, 1200),
    ("GET",  "/api/health",  200, 12),
    ("GET",  "/api/nodes",   200, 41),
    ("POST", "/api/deploy",  201, 210),
    ("GET",  "/api/health",  200, 15),
    ("DELETE", "/api/pods/old", 204, 180),
    ("GET",  "/api/pods",    200, 48),
]

by_method = defaultdict(list)
by_status = defaultdict(set)
by_path = defaultdict(list)

embed(header="Checkpoint 5: access log analysis")

print()
print("DAY 2 COMPLETE.")
print("defaultdict is now your default tool for grouping. No exceptions.")
