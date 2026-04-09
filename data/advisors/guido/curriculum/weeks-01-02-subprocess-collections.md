# Weeks 1–2: subprocess + collections
**The Foundation Layer**

These are the two modules you will use most as an SRE. `collections` replaces ad-hoc data wrangling. `subprocess` replaces shelling out with `os.system`. Together they cover 60% of real infrastructure scripting.

Each day: 10 min reading, 15 min REPL (in nvim), 5 min write one script.
Predict the output BEFORE you run it. That is where learning happens.

---

## Day 1: defaultdict — the automatic factory

### Read (10 min)

A normal dict raises KeyError on missing keys. defaultdict calls a factory function instead.

```python
from collections import defaultdict

# The factory argument is called with no args when a missing key is accessed
d = defaultdict(list)      # missing key → []
d = defaultdict(int)       # missing key → 0
d = defaultdict(set)       # missing key → set()
d = defaultdict(str)       # missing key → ""
d = defaultdict(lambda: "unknown")  # missing key → "unknown"
```

The factory is called by `__missing__`, which `__getitem__` calls when the key doesn't exist. This means `d[key]` triggers it, but `d.get(key)` does NOT — `.get()` bypasses `__missing__`.

Why this matters for SRE: log aggregation, metric grouping, building indexes from flat data. Every time you write `if key not in d: d[key] = []` you should be using defaultdict.

### REPL (15 min)

Predict each output, then run it.

```python
# Exercise 1: grouping
from collections import defaultdict

logs = [
    ("web-01", "error"), ("web-02", "warn"), ("web-01", "error"),
    ("web-03", "info"), ("web-02", "error"), ("web-01", "warn"),
]

by_host = defaultdict(list)
for host, level in logs:
    by_host[host].append(level)

print(dict(by_host))
# PREDICT: ?

# Exercise 2: counting (before you learn Counter)
counts = defaultdict(int)
for host, level in logs:
    counts[level] += 1

print(dict(counts))
# PREDICT: ?

# Exercise 3: the .get() distinction
d = defaultdict(list)
print(d["missing"])   # what happens?
print(d.get("also_missing"))  # what happens?
print(dict(d))  # what keys exist now?
# PREDICT: ?

# Exercise 4: nested defaultdict
nested = defaultdict(lambda: defaultdict(int))
nested["web-01"]["errors"] += 1
nested["web-01"]["errors"] += 1
nested["web-01"]["warns"] += 1
nested["web-02"]["errors"] += 1
print(dict(nested["web-01"]))
print(dict(nested["web-02"]))
# PREDICT: ?

# Exercise 5: defaultdict vs setdefault
d1 = {}
d1.setdefault("a", []).append(1)
d1.setdefault("a", []).append(2)
print(d1)
# How does this compare to defaultdict(list)?
```

### Script (5 min)

Write a script that reads `/etc/hosts` (or any text file) and builds a defaultdict mapping each first character to the list of lines starting with that character. Print the result.

---

## Day 2: defaultdict — real patterns

### Read (10 min)

Three patterns you will use constantly:

**Pattern 1: Inverted index**
```python
from collections import defaultdict

# Given: list of (tag, item) pairs
# Want: tag → [items]
tags = [("k8s", "pod.yaml"), ("k8s", "svc.yaml"), ("docker", "Dockerfile"), ("k8s", "deploy.yaml")]
index = defaultdict(list)
for tag, item in tags:
    index[tag].append(item)
# index["k8s"] → ["pod.yaml", "svc.yaml", "deploy.yaml"]
```

**Pattern 2: Frequency map (prelude to Counter)**
```python
from collections import defaultdict

words = "the cat sat on the mat".split()
freq = defaultdict(int)
for w in words:
    freq[w] += 1
# freq["the"] → 2
```

**Pattern 3: Unique collection per key**
```python
from collections import defaultdict

events = [("web-01", 404), ("web-01", 500), ("web-01", 404), ("web-02", 500)]
unique_codes = defaultdict(set)
for host, code in events:
    unique_codes[host].add(code)
# unique_codes["web-01"] → {404, 500}
```

### REPL (15 min)

```python
# Exercise 1: build an inverted index from this pod data
from collections import defaultdict

pods = [
    {"name": "advisor-musashi", "namespace": "halo-fleet", "status": "Running"},
    {"name": "advisor-medici", "namespace": "halo-fleet", "status": "CrashLoopBackOff"},
    {"name": "nginx", "namespace": "default", "status": "Running"},
    {"name": "advisor-bankei", "namespace": "halo-fleet", "status": "Running"},
    {"name": "redis", "namespace": "default", "status": "Pending"},
]

# Group pods by status
by_status = defaultdict(list)
for pod in pods:
    by_status[pod["status"]].append(pod["name"])

print(dict(by_status))
# PREDICT: ?

# Group pods by namespace, collecting unique statuses
by_ns = defaultdict(set)
for pod in pods:
    by_ns[pod["namespace"]].add(pod["status"])

print({k: sorted(v) for k, v in by_ns.items()})
# PREDICT: ?

# Exercise 2: What happens here?
d = defaultdict(int)
d["a"]  # just access, no assignment
d["b"] += 0
print(dict(d))
# PREDICT: ? (both keys exist — why?)
```

### Script (5 min)

Write a script that takes a list of file paths and groups them by extension using defaultdict. Example input: `["main.py", "utils.py", "Dockerfile", "deploy.yaml", "svc.yaml", "README.md"]`. Files with no extension go under the key `""`.

---

## Day 3: Counter — counting things properly

### Read (10 min)

Counter is a dict subclass for counting hashable objects. It does what defaultdict(int) does, but with extra methods.

```python
from collections import Counter

# Create from iterable
c = Counter("abracadabra")
# Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})

# Create from keyword args
c = Counter(errors=5, warnings=2, info=10)

# Key methods
c.most_common(2)     # [('info', 10), ('errors', 5)] — list of (elem, count) tuples
c.total()            # 17 (sum of all counts) — Python 3.10+
c.elements()         # iterator: 'errors' × 5, 'warnings' × 2, 'info' × 10
c.subtract(other)    # subtract counts (can go negative)
c.update(more_data)  # add counts from another iterable or Counter

# Arithmetic
c1 = Counter(a=3, b=1)
c2 = Counter(a=1, b=2)
print(c1 + c2)  # Counter({'a': 4, 'b': 3})
print(c1 - c2)  # Counter({'a': 2}) — drops zero and negative
print(c1 & c2)  # Counter({'a': 1, 'b': 1}) — min of each
print(c1 | c2)  # Counter({'a': 3, 'b': 2}) — max of each
```

Why SRE cares: log level counting, status code distribution, error frequency, top-N analysis.

### REPL (15 min)

```python
from collections import Counter

# Exercise 1: basic counting
status_codes = [200, 200, 404, 500, 200, 404, 200, 500, 500, 200]
c = Counter(status_codes)
print(c)
print(c[200])
print(c[302])          # what happens for a code not in the data?
print(c.most_common(2))
# PREDICT all four: ?

# Exercise 2: Counter from a string
c = Counter("mississippi")
print(c)
print(c.most_common())  # no argument — what happens?
# PREDICT: ?

# Exercise 3: arithmetic
before = Counter(running=8, pending=2, failed=1)
after  = Counter(running=6, pending=1, failed=3)
diff = after - before
print(diff)
# PREDICT: ? (what happens to running, which decreased?)

gained = after - before  # only positive
lost = before - after    # only positive
print(f"gained: {gained}")
print(f"lost: {lost}")
# PREDICT: ?

# Exercise 4: update and subtract
c = Counter(errors=5)
c.update({"errors": 3, "warnings": 1})
print(c)
# PREDICT: ?

c.subtract({"errors": 10})
print(c)
print(c["errors"])  # can counts go negative?
# PREDICT: ?

# Exercise 5: most_common returns what type?
c = Counter("hello world")
result = c.most_common(3)
print(result)
print(type(result))
print(type(result[0]))
# PREDICT: ?
```

### Script (5 min)

Write a script that reads a log file (or simulate one as a multiline string) where each line has a log level like `ERROR`, `WARN`, `INFO`. Use Counter to print the top 3 most frequent levels and their counts.

---

## Day 4: deque — the double-ended queue

### Read (10 min)

deque (pronounced "deck") is a double-ended queue. O(1) append and pop from both ends. Lists are O(n) for `insert(0, x)` and `pop(0)`.

```python
from collections import deque

# Basic operations
d = deque([1, 2, 3])
d.append(4)         # right end: [1, 2, 3, 4]
d.appendleft(0)     # left end:  [0, 1, 2, 3, 4]
d.pop()             # from right: returns 4
d.popleft()         # from left:  returns 0
d.rotate(1)         # shift right by 1: [3, 1, 2]
d.rotate(-1)        # shift left by 1:  [1, 2, 3]

# maxlen — the bounded buffer
d = deque(maxlen=3)
d.append(1)  # [1]
d.append(2)  # [1, 2]
d.append(3)  # [1, 2, 3]
d.append(4)  # [2, 3, 4] — silently drops from the LEFT
```

The maxlen behaviour is critical: it never raises, it silently drops from the opposite end. This is how you build:
- Rolling windows (last N log entries)
- Bounded buffers (last N metrics)
- BFS queues (appendleft + pop, or append + popleft)

### REPL (15 min)

```python
from collections import deque

# Exercise 1: maxlen behaviour
d = deque([10, 20, 30], maxlen=3)
d.append(40)
print(list(d))
# PREDICT: ?

d.appendleft(5)
print(list(d))
# PREDICT: ?

# Exercise 2: rolling window
window = deque(maxlen=5)
for i in range(10):
    window.append(i)
    if len(window) == 5:
        print(f"window: {list(window)}, avg: {sum(window)/len(window):.1f}")
# PREDICT first two printed lines: ?

# Exercise 3: using deque as a queue (FIFO)
q = deque()
q.append("job-1")
q.append("job-2")
q.append("job-3")
first = q.popleft()
print(first)
print(list(q))
# PREDICT: ?

# Exercise 4: rotate
d = deque([1, 2, 3, 4, 5])
d.rotate(2)
print(list(d))
# PREDICT: ?
d.rotate(-3)
print(list(d))
# PREDICT: ?

# Exercise 5: deque vs list performance
# Don't run this for timing — just understand WHY
# list.insert(0, x) is O(n) — shifts every element
# deque.appendleft(x) is O(1) — linked list node
# For 1 million items, list insert(0) takes seconds. deque takes milliseconds.
```

### Script (5 min)

Write a "tail -f simulator": create a deque(maxlen=10) and feed it 50 numbered lines. After each line, if the deque is full, print the current window. This simulates keeping the last 10 lines of a log file.

---

## Day 5: collections — integration day

### Read (10 min)

Review all three. The mental model:

| Tool | When to use | Instead of |
|------|-------------|------------|
| defaultdict(list) | Grouping items by key | `if key not in d: d[key] = []` |
| defaultdict(int) | Counting things (simple) | `if key not in d: d[key] = 0` |
| defaultdict(set) | Unique items per key | `if key not in d: d[key] = set()` |
| Counter | Counting + top-N + arithmetic | defaultdict(int) when you need more |
| deque | FIFO queue, rolling window, bounded buffer | list (when you append/pop from left) |

Also know these exist but save for later: `namedtuple`, `OrderedDict` (mostly obsolete since 3.7), `ChainMap`.

### REPL (15 min)

```python
from collections import defaultdict, Counter, deque

# Scenario: you're parsing kubectl output
# Each line is: pod_name status restart_count
raw = """
advisor-musashi Running 0
advisor-medici CrashLoopBackOff 5
advisor-bankei Running 0
advisor-draper Running 1
advisor-gibson OOMKilled 3
advisor-medici CrashLoopBackOff 6
nginx Running 0
advisor-medici CrashLoopBackOff 7
""".strip().split("\n")

# Task 1: parse into list of tuples
entries = []
for line in raw:
    parts = line.split()
    entries.append((parts[0], parts[1], int(parts[2])))

# Task 2: count statuses using Counter
statuses = Counter(status for _, status, _ in entries)
print(statuses)
print(statuses.most_common(1))
# PREDICT: ?

# Task 3: group pod names by status using defaultdict
by_status = defaultdict(list)
for name, status, _ in entries:
    by_status[status].append(name)
print(dict(by_status))
# PREDICT: ?

# Task 4: track last 3 restart counts for medici using deque
medici_restarts = deque(maxlen=3)
for name, _, restarts in entries:
    if name == "advisor-medici":
        medici_restarts.append(restarts)
print(list(medici_restarts))
# PREDICT: ?

# Task 5: unique pods that have been in each status
unique_by_status = defaultdict(set)
for name, status, _ in entries:
    unique_by_status[status].add(name)
print({k: sorted(v) for k, v in unique_by_status.items()})
# PREDICT: ?
```

### Script (5 min)

Combine all three: write a script that processes a simulated stream of `(timestamp, host, status_code)` tuples. Use defaultdict to group by host, Counter to count status codes globally, and deque(maxlen=5) to keep the last 5 events per host.

---

## Day 6: subprocess.run — the basics

### Read (10 min)

`subprocess.run` is the ONE function you need. Forget `os.system`, `os.popen`, `subprocess.call`, `subprocess.Popen` (for now). Just `run`.

```python
import subprocess

# Simplest form — runs command, waits for completion
result = subprocess.run(["ls", "-la"])
# Output goes directly to terminal. result.returncode is the exit code.

# Capture output
result = subprocess.run(["ls", "-la"], capture_output=True, text=True)
# result.stdout — string of stdout
# result.stderr — string of stderr
# result.returncode — int exit code

# Key arguments:
# capture_output=True  → capture stdout/stderr (equiv to stdout=PIPE, stderr=PIPE)
# text=True            → decode bytes to str (equiv to encoding="utf-8")
# check=True           → raise CalledProcessError if returncode != 0
# cwd="/some/path"     → run in this directory
# timeout=10           → kill after 10 seconds, raise TimeoutExpired
# input="data"         → send string to stdin (requires text=True)
# env={"PATH": "..."}  → override environment variables
# shell=True           → run through shell (AVOID — security risk, except for pipes)
```

**The holy trinity for SRE scripting:**
```python
# Pattern 1: run and check
subprocess.run(["kubectl", "apply", "-f", "deploy.yaml"], check=True)

# Pattern 2: run and capture
result = subprocess.run(["kubectl", "get", "pods", "-o", "json"],
                        capture_output=True, text=True, check=True)
pods = json.loads(result.stdout)

# Pattern 3: run with timeout
result = subprocess.run(["curl", "-s", "http://localhost:8080/health"],
                        capture_output=True, text=True, timeout=5)
```

### REPL (15 min)

```python
import subprocess

# Exercise 1: basic run
result = subprocess.run(["echo", "hello from subprocess"], capture_output=True, text=True)
print(repr(result.stdout))
print(result.returncode)
# PREDICT: ? (note: repr shows the \n)

# Exercise 2: multi-word arguments
# WRONG: subprocess.run(["echo", "hello", "world"]) — passes TWO args to echo
# This is actually fine for echo, but be aware:
result = subprocess.run(["echo", "hello", "world"], capture_output=True, text=True)
print(repr(result.stdout))
# PREDICT: ?

# Exercise 3: stderr
result = subprocess.run(["ls", "/nonexistent"], capture_output=True, text=True)
print(f"stdout: {repr(result.stdout)}")
print(f"stderr: {repr(result.stderr)}")
print(f"returncode: {result.returncode}")
# PREDICT: ? (what goes where?)

# Exercise 4: check=True
try:
    subprocess.run(["ls", "/nonexistent"], capture_output=True, text=True, check=True)
except subprocess.CalledProcessError as e:
    print(f"Command failed with code {e.returncode}")
    print(f"stderr: {e.stderr}")
# PREDICT: ?

# Exercise 5: the false command
result = subprocess.run(["false"], capture_output=True, text=True)
print(result.returncode)
# PREDICT: ?

result = subprocess.run(["true"], capture_output=True, text=True)
print(result.returncode)
# PREDICT: ?
```

### Script (5 min)

Write a script that runs `uname -a`, captures the output, and prints each word on its own line with a line number. Use subprocess.run with capture_output and text.

---

## Day 7: subprocess — error handling

### Read (10 min)

Three failure modes you must handle:

```python
import subprocess

# 1. Command fails (non-zero exit)
try:
    result = subprocess.run(["grep", "-r", "pattern", "/nonexistent"],
                           capture_output=True, text=True, check=True)
except subprocess.CalledProcessError as e:
    print(f"Exit code: {e.returncode}")
    print(f"stderr: {e.stderr}")
    # e.stdout also available

# 2. Command not found
try:
    subprocess.run(["nonexistent_command"], capture_output=True, text=True)
except FileNotFoundError:
    print("Command not found")

# 3. Command hangs
try:
    subprocess.run(["sleep", "60"], timeout=5)
except subprocess.TimeoutExpired:
    print("Timed out")
```

The robust pattern:
```python
def run_cmd(cmd, timeout=30):
    """Run a command safely. Return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, check=True
        )
        return result.stdout, result.stderr, 0
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode
    except FileNotFoundError:
        return "", f"Command not found: {cmd[0]}", 127
    except subprocess.TimeoutExpired:
        return "", f"Timeout after {timeout}s", 124
```

Why 127 and 124? Convention from shell: 127 = command not found, 124 = timeout. Not mandatory, but recognisable.

### REPL (15 min)

```python
import subprocess

# Exercise 1: CalledProcessError attributes
try:
    result = subprocess.run(
        ["python3", "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(42)"],
        capture_output=True, text=True, check=True
    )
except subprocess.CalledProcessError as e:
    print(f"returncode: {e.returncode}")
    print(f"stdout: {repr(e.stdout)}")
    print(f"stderr: {repr(e.stderr)}")
    print(f"cmd: {e.cmd}")
# PREDICT: ?

# Exercise 2: FileNotFoundError
try:
    subprocess.run(["kubectl_typo", "get", "pods"])
except FileNotFoundError as e:
    print(f"caught: {e}")
# PREDICT: does this raise FileNotFoundError or something else?

# Exercise 3: timeout
try:
    subprocess.run(["sleep", "10"], timeout=2)
except subprocess.TimeoutExpired as e:
    print(f"timed out after {e.timeout}s")
    print(f"cmd: {e.cmd}")
# PREDICT: ?

# Exercise 4: without check, failure is silent
result = subprocess.run(["false"], capture_output=True, text=True)
print(f"returncode: {result.returncode}")
print(f"This line still runs — no exception without check=True")
# KEY INSIGHT: without check=True you must check returncode yourself

# Exercise 5: input to stdin
result = subprocess.run(
    ["python3", "-c", "x = input(); print(f'got: {x}')"],
    capture_output=True, text=True, input="hello stdin"
)
print(result.stdout)
# PREDICT: ?
```

### Script (5 min)

Write the `run_cmd` helper function from the reading section. Then use it to run three commands: one that succeeds (`echo hello`), one that fails (`ls /nonexistent`), and one that times out (`sleep 60` with timeout=2). Print a clean summary of each.

---

## Day 8: subprocess — real SRE patterns

### Read (10 min)

Patterns you will actually use in infrastructure work:

```python
import subprocess
import json

# Pattern 1: parse JSON output from CLI tools
result = subprocess.run(
    ["kubectl", "get", "pods", "-n", "halo-fleet", "-o", "json"],
    capture_output=True, text=True, check=True
)
data = json.loads(result.stdout)
for pod in data["items"]:
    name = pod["metadata"]["name"]
    phase = pod["status"]["phase"]
    print(f"{name}: {phase}")

# Pattern 2: chain commands (without shell=True)
# Instead of: ps aux | grep python | wc -l
ps = subprocess.run(["ps", "aux"], capture_output=True, text=True)
grep = subprocess.run(["grep", "python"], input=ps.stdout,
                      capture_output=True, text=True)
count = len(grep.stdout.strip().split("\n"))

# Pattern 3: cwd for running in a specific directory
result = subprocess.run(
    ["git", "log", "--oneline", "-5"],
    capture_output=True, text=True, cwd="/path/to/repo"
)

# Pattern 4: environment override
import os
env = os.environ.copy()
env["KUBECONFIG"] = "/etc/rancher/k3s/k3s.yaml"
result = subprocess.run(
    ["kubectl", "get", "nodes"],
    capture_output=True, text=True, env=env
)
```

**When to use shell=True (almost never):**
```python
# Only when you genuinely need shell features (pipes, globbing, variable expansion)
# AND the command is hardcoded (no user input — shell injection risk)
result = subprocess.run("ls *.yaml | wc -l", shell=True, capture_output=True, text=True)
```

### REPL (15 min)

```python
import subprocess
import json

# Exercise 1: capture and parse
result = subprocess.run(["python3", "-c", """
import json
data = {"pods": [{"name": "web", "status": "Running"}, {"name": "db", "status": "Pending"}]}
print(json.dumps(data))
"""], capture_output=True, text=True, check=True)

parsed = json.loads(result.stdout)
for pod in parsed["pods"]:
    print(f"{pod['name']}: {pod['status']}")
# PREDICT: ?

# Exercise 2: piping without shell=True
# Find python processes
ps = subprocess.run(["ps", "aux"], capture_output=True, text=True)
lines = [l for l in ps.stdout.split("\n") if "python" in l.lower()]
print(f"Found {len(lines)} python-related processes")
# Note: this is cleaner than shell piping because you can use Python's
# string methods instead of grep/awk/sed

# Exercise 3: cwd
result = subprocess.run(
    ["pwd"],
    capture_output=True, text=True,
    cwd="/tmp"
)
print(result.stdout.strip())
# PREDICT: ?

# Exercise 4: the input argument
csv_data = "name,age\nkai,38\nben,35\n"
result = subprocess.run(
    ["python3", "-c", "import sys; print(len(sys.stdin.readlines()))"],
    capture_output=True, text=True, input=csv_data
)
print(result.stdout.strip())
# PREDICT: ?
```

### Script (5 min)

Write a script that: (1) runs `uptime` and captures output, (2) runs `df -h /` and captures output, (3) runs `whoami` and captures output. Print a clean system summary using all three results. Handle any command failures gracefully.

---

## Day 9: subprocess — the CompletedProcess object

### Read (10 min)

Every `subprocess.run()` returns a `CompletedProcess` instance. Know its attributes:

```python
import subprocess

result = subprocess.run(["echo", "hello"], capture_output=True, text=True)

result.args          # ['echo', 'hello'] — the command as passed
result.returncode    # 0 — exit code (0 = success)
result.stdout        # 'hello\n' — captured stdout (str if text=True, bytes otherwise)
result.stderr        # '' — captured stderr
```

Without `text=True`:
```python
result = subprocess.run(["echo", "hello"], capture_output=True)
print(type(result.stdout))  # <class 'bytes'>
print(result.stdout)        # b'hello\n'
print(result.stdout.decode("utf-8"))  # 'hello\n'
```

The `text=True` flag (or its alias `encoding="utf-8"`) is almost always what you want. The exception: binary output (e.g., `subprocess.run(["tar", "czf", "-", "dir/"])` where stdout is a tarball).

**repr() vs str():**
```python
s = "hello\n"
print(s)        # hello        (renders the newline)
print(repr(s))  # 'hello\n'   (shows the escape character)
```
This is why the exam used `repr(result.stdout)` — to make the `\n` visible.

### REPL (15 min)

```python
import subprocess

# Exercise 1: text=True vs without
r1 = subprocess.run(["echo", "hello"], capture_output=True, text=True)
r2 = subprocess.run(["echo", "hello"], capture_output=True)
print(type(r1.stdout), repr(r1.stdout))
print(type(r2.stdout), repr(r2.stdout))
# PREDICT: ?

# Exercise 2: args attribute
result = subprocess.run(["ls", "-la", "/tmp"], capture_output=True, text=True)
print(result.args)
print(type(result.args))
# PREDICT: ?

# Exercise 3: multi-line output processing
result = subprocess.run(["ls", "/usr/bin"], capture_output=True, text=True)
lines = result.stdout.strip().split("\n")
print(f"Total binaries: {len(lines)}")
print(f"First 3: {lines[:3]}")
# RUN and observe

# Exercise 4: returncode is ALWAYS available
result = subprocess.run(["ls", "/nonexistent"], capture_output=True, text=True)
print(result.returncode)  # non-zero
print(bool(result.returncode))  # truthy/falsy?
# PREDICT: ?
# KEY: 0 is falsy in Python. Non-zero is truthy.
# So: if result.returncode: means "if command FAILED"

# Exercise 5: checking success idiomatically
result = subprocess.run(["echo", "ok"], capture_output=True, text=True)
if result.returncode == 0:
    print("explicit check: success")
if not result.returncode:
    print("pythonic check: success")
# Both work. The explicit check is clearer for SRE scripts.
```

### Script (5 min)

Write a function `cmd_ok(cmd_list) -> bool` that returns True if the command succeeds (returncode 0) and False otherwise. It should suppress all output. Test it with `["true"]`, `["false"]`, and `["ls", "/nonexistent"]`.

---

## Day 10: subprocess + collections — integration

### Read (10 min)

Now combine them. This is how real SRE scripts work:

```python
import subprocess
import json
from collections import Counter, defaultdict

def get_pod_statuses(namespace="halo-fleet"):
    """Get pod statuses from kubectl."""
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)

    statuses = Counter()
    by_status = defaultdict(list)

    for item in data["items"]:
        name = item["metadata"]["name"]
        phase = item["status"]["phase"]
        statuses[phase] += 1
        by_status[phase].append(name)

    return statuses, dict(by_status)
```

The pattern: subprocess captures raw output → parse it → collections organise it → you make decisions.

### REPL (15 min)

```python
import subprocess
from collections import Counter, defaultdict, deque

# Exercise 1: process listing with Counter
result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
lines = result.stdout.strip().split("\n")[1:]  # skip header

# Count processes per user
users = Counter()
for line in lines:
    user = line.split()[0]
    users[user] += 1

print("Top 5 users by process count:")
for user, count in users.most_common(5):
    print(f"  {user}: {count}")

# Exercise 2: group files by extension
result = subprocess.run(["ls", "/usr/bin"], capture_output=True, text=True)
files = result.stdout.strip().split("\n")

from pathlib import Path
by_suffix = defaultdict(list)
for f in files:
    suffix = Path(f).suffix or "(none)"
    by_suffix[suffix].append(f)

for suffix, fnames in sorted(by_suffix.items()):
    print(f"{suffix}: {len(fnames)} files")

# Exercise 3: rolling command output
history = deque(maxlen=5)
commands = ["date", "whoami", "uptime", "pwd", "hostname", "uname", "arch"]
for cmd in commands:
    result = subprocess.run([cmd], capture_output=True, text=True)
    history.append(f"{cmd}: {result.stdout.strip()}")

print("Last 5 command results:")
for entry in history:
    print(f"  {entry}")
```

### Script (5 min)

Write a script that runs `ls -la` on your home directory, parses the output to extract file sizes and names (skip the header and total lines), and uses Counter to report: total files, total size, and the 3 largest files.

---

## Days 11–14: Consolidation

### Day 11: defaultdict deep cuts

REPL exercises — 30 min, no reading section:

```python
from collections import defaultdict

# Challenge 1: word co-occurrence matrix
# Given sentences, count how often each pair of words appears together
sentences = [
    "the cat sat on the mat",
    "the dog sat on the log",
    "the cat and the dog",
]

cooccurrence = defaultdict(lambda: defaultdict(int))
for sentence in sentences:
    words = sentence.split()
    for i, w1 in enumerate(words):
        for w2 in words[i+1:]:
            cooccurrence[w1][w2] += 1
            cooccurrence[w2][w1] += 1

# Print co-occurrences for "cat"
print(dict(cooccurrence["cat"]))

# Challenge 2: defaultdict with custom factory
# Create a defaultdict where missing keys get the key itself as default
# Hint: you can't do this with defaultdict alone — the factory takes no args
# What would you use instead? (think: __missing__)

class KeyDefaultDict(dict):
    def __missing__(self, key):
        self[key] = key
        return key

d = KeyDefaultDict()
print(d["hello"])
print(d["world"])
print(dict(d))
```

### Day 12: Counter deep cuts

```python
from collections import Counter

# Challenge 1: find elements that appear exactly once
data = [1, 2, 3, 2, 3, 3, 4, 5, 4]
c = Counter(data)
unique = [item for item, count in c.items() if count == 1]
print(unique)  # PREDICT: ?

# Challenge 2: Counter as a multiset
# Remove one occurrence of an element
inventory = Counter(apples=5, bananas=3, oranges=0)
inventory.subtract({"apples": 1})
print(inventory)  # PREDICT: ?

# What happens with +inventory (unary plus)?
print(+inventory)  # strips zero and negative counts

# Challenge 3: find the top N words in a file
import subprocess
result = subprocess.run(["cat", "/usr/share/dict/words"], capture_output=True, text=True)
words = result.stdout.lower().split()
# What are the 5 most common first letters?
first_letters = Counter(w[0] for w in words if w)
print(first_letters.most_common(5))
```

### Day 13: subprocess deep cuts

```python
import subprocess

# Challenge 1: run multiple commands and collect results
commands = {
    "hostname": ["hostname"],
    "kernel": ["uname", "-r"],
    "uptime": ["uptime"],
    "disk": ["df", "-h", "/"],
}

report = {}
for name, cmd in commands.items():
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        report[name] = result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        report[name] = f"FAILED: {e}"

for name, output in report.items():
    print(f"[{name}]\n{output}\n")

# Challenge 2: subprocess with environment manipulation
import os
env = os.environ.copy()
env["GREETING"] = "hello from python"
result = subprocess.run(
    ["python3", "-c", "import os; print(os.environ.get('GREETING', 'not set'))"],
    capture_output=True, text=True, env=env
)
print(result.stdout.strip())
# PREDICT: ?
```

### Day 14: Integration challenge

Write a single script called `sysreport.py` that:

1. Runs 5 system commands (hostname, uptime, df, ps aux, uname -a)
2. Parses ps aux output to count processes per user (Counter)
3. Groups files in /tmp by extension (defaultdict)
4. Keeps a rolling log of the last 3 command execution times (deque)
5. Handles all three failure modes (CalledProcessError, FileNotFoundError, TimeoutExpired)
6. Prints a clean, formatted report

Use ONLY subprocess, collections, json, pathlib, and time from the stdlib. No external packages.

---

## Checkpoint

After Day 14, you should be able to answer these without looking anything up:

1. What does `defaultdict(list)` do when you access a missing key?
2. What does `Counter.most_common(3)` return? What type?
3. What happens when you `append` to a `deque(maxlen=3)` that already has 3 items?
4. What are the three arguments to `subprocess.run` you will use 90% of the time?
5. What exception does `check=True` raise on failure?
6. What exception does a missing command raise?
7. What is `result.returncode` for a successful command?
8. When would you use `text=True` vs leaving it off?

If you can answer all 8 from memory, you are ready for Weeks 3–4.

---

*The BDFL closes the curriculum binder. There is nothing here you cannot learn in 14 days. The only question is whether you will type it out or let the machine type it for you. I already know which one builds the ripperdoc.*
