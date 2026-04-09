# Python Literacy Exam v1 — GRADED
**Subject: Kai**
**Date: 2026-04-07**
**Graded by: Guido van Rossum, BDFL (ret.)**

---

## Grading Scale
- **FLUENT**: Correct output, understands why, could teach it
- **FUNCTIONAL**: Correct or near-correct, understands the concept, minor details off
- **FRAGILE**: Right instinct but wrong output, or correct guess without understanding
- **FOREIGN**: Does not know, fundamentally wrong, or "don't know"

---

## Domain 1: Data Structures — FOREIGN

### Q1 — FRAGILE
```
Kai: "cat"
Correct: [('the', 3), ('cat', 2)]
```
Counter.most_common(n) returns a list of (element, count) tuples, not just the element. You knew Counter counts things — you did not know the API shape.

### Q2 — FOREIGN
```
Kai: Exception, loop tries to append(v) before d[k] is defined
Correct: {'a': [1, 3, 5], 'b': [2, 4]}
         []
```
This is the entire reason defaultdict exists. When you access a missing key, it calls the factory function (here `list`) to create the default value. `d["c"]` returns an empty list, no exception. This is one of the most useful tools in Python for grouping and aggregation scripts. Learn this one first.

### Q3 — FOREIGN
```
Kai: unfamiliar, thinks it prevents append
Correct: [0, 2, 3]
```
deque with maxlen silently drops from the *opposite* end. `append(4)` pushes right, drops 1 from left → [2,3,4]. `appendleft(0)` pushes left, drops 4 from right → [0,2,3]. It never raises. This is how you build bounded buffers and rolling windows.

### Q4 — FRAGILE
```
Kai: correct intuition (doesn't modify, returns smallest)
Correct: [1, 2, 3]
         [5, 1, 8, 3, 2, 9]
```
Good instinct. nsmallest does not modify the list. heapify does (in-place). You got the concept right without knowing the module.

**Domain 1 total: 0 correct, 1 good instinct, 2 unknown. FOREIGN.**

---

## Domain 2: Iteration & Functional — FRAGILE

### Q5 — FRAGILE
```
Kai: [2,3,4,5]
Correct: [3, 4, 5]
```
Your reasoning about chain was correct (concatenates). islice(c, 2, 5) returns items at indices 2, 3, 4 — three items, not four. Same as list slicing: `[2:5]` gives you index 2 up to but not including 5. You were off by one and included the end index.

### Q6 — FRAGILE
```
Kai: [[1,1],[2],[3,3],[2,2]]
Correct: [(1, [1, 1]), (2, [2]), (3, [3, 3, 3]), (2, [2, 2])]
```
Excellent intuition. You correctly identified that groupby works on *consecutive* runs, which is why 2 appears twice. The actual format includes the key as a tuple pair, and you missed the three 3s, but the mental model is right. To group all 2s together: sort first, then groupby.

### Q7 — FRAGILE
```
Kai: recognises memoisation, knows cache_info exists
Correct: 55
         CacheInfo(hits=8, misses=11, maxsize=None, currsize=11)
```
lru_cache is indeed memoisation. fib(10) = 55. cache_info() returns a named tuple with hits, misses, maxsize, currsize. You understood the mechanism but could not produce the output.

### Q8 — FRAGILE
```
Kai: type iter?, sum = 55, second sum raises error or None
Correct: <class 'generator'>
         30
         0
```
Type is `generator`, not `iter`. Sum is 30 (0+1+4+9+16, not 1+2+...+10). Second sum returns 0, not an error — `sum()` of an exhausted generator is `sum([])` which is 0. You understood exhaustion but not the exact behaviour. The arithmetic error: `range(5)` gives 0,1,2,3,4 — the squares are 0,1,4,9,16.

### Q9 — FUNCTIONAL
```
Kai: 25, 3
Correct: 25, 27
```
Understanding of partial is perfect. `cube(3) = 3**3 = 27`, not 3. Arithmetic slip, not a knowledge gap.

**Domain 2 total: 1 near-correct, 3 right instinct, 1 arithmetic error. FRAGILE.**

---

## Domain 3: Text & Patterns — FRAGILE

### Q10 — FRAGILE
```
Kai: ["404","500","200"]
Correct: ['404', '500']
```
The regex is `r"error: (\d+)"` — it only matches lines starting with "error:", not "info:". 200 does not match. When findall has a capture group, it returns the captured text only. You need to read the pattern more carefully.

### Q11 — FRAGILE
```
Kai: ["kai","oceanheart","ai"], ["ai"]
Correct: ('kai', 'oceanheart', 'ai')
         'oceanheart'
```
Two errors. `.groups()` returns a tuple, not a list. `.group(2)` returns the second capture group, which is "oceanheart" — groups are 1-indexed, so group(1)="kai", group(2)="oceanheart", group(3)="ai". group(0) is the entire match.

### Q12 — FRAGILE
```
Kai: "kai                    ", "                    kai"
Correct: "                 kai"
         "********kai*********"
```
Reversed. `>` means right-align (pad left with spaces). `^` means center. `*` before `^` is the fill character. You had the alignment directions backwards and missed the fill character entirely.

**Domain 3 total: 0 correct. All three show familiarity but imprecision. FRAGILE.**

---

## Domain 4: OS & Process — FRAGILE

### Q13 — FRAGILE
```
Kai: "halo", "md", "file"
Correct: "notes", ".md", "file"
```
resolve() collapses `data/../data` to just `data`, giving `/Users/kai/code/halo/data/notes/file.md`. The parent is `.../notes/`, so parent.name is "notes", not "halo". suffix includes the dot: ".md" not "md". stem is correct.

resolve() does not "traverse to find" the file — it normalises the path by resolving `..` and symlinks. It works even if the file does not exist (on most systems).

### Q14 — FOREIGN
```
Kai: "Don't know"
Correct: 'hello world\n'
         0
```
subprocess.run returns a CompletedProcess object. With `capture_output=True, text=True`, stdout is a string. `repr()` shows the escape characters, so you see the `\n`. returncode 0 means success. This is the single most important subprocess pattern for SRE scripting.

### Q15 — FOREIGN
```
Kai: "Don't know"
Correct: "failed: 1"
```
`false` is a Unix command that always returns exit code 1. `check=True` makes subprocess.run raise CalledProcessError on non-zero exit. The except block catches it and prints the returncode. This is how you write safe shell-out code.

### Q16 — FRAGILE
```
Kai: "tar.gz", ["tar","gz"], "somefile"
Correct: ".gz", [".tar", ".gz"], "somefile.tar"
```
suffix returns only the *last* suffix, with the dot. suffixes returns all suffixes, each with their dot. stem strips only the last suffix: "somefile.tar". Pathlib is consistent: suffix always includes the dot.

**Domain 4 total: 0 correct, subprocess completely unknown. FRAGILE (pathlib) / FOREIGN (subprocess).**

---

## Domain 5: Concurrency — FRAGILE

### Q17 — FRAGILE
```
Kai: False — CORRECT answer
Reasoning: "global declares counter 5 times" — WRONG reason
Correct reason: counter += 1 is not atomic (read-modify-write). Multiple threads interleave.
Fix: threading.Lock, or atomic operations.
```
Right answer, wrong explanation. `global` does not declare anything 5 times — it just tells each function to use the module-level variable. The problem is that `+=` is a read-then-write operation and threads interleave between the read and the write. Fix: wrap in a `threading.Lock()`.

### Q18 — FUNCTIONAL
```
Kai: ["fetched {a,b,c}.com"] — correct concept, sloppy format
Correct: ['fetched a.com', 'fetched b.com', 'fetched c.com']
```
pool.map preserves input order. All three run (2 concurrent, then 1). You understood the mechanism.

### Q19 — FRAGILE
```
Kai: ["hello ben", "hello kai"]
Correct: ['hello kai', 'hello ben']
```
gather() preserves *input order*, not completion order. ben finishes first (0.1s < 0.2s), but gather returns results in the order the coroutines were passed. This is a critical detail for production async code — you need to know which result maps to which input.

**Domain 5 total: 1 correct answer (wrong reason), 1 functional, 1 wrong. FRAGILE.**

---

## Domain 6: Serialisation — FUNCTIONAL

### Q20 — FUNCTIONAL
```
Kai: Str, True, Boolean
Correct: <class 'str'>, True, <class 'bool'>
```
All correct in substance. The exact type names are `str` and `bool`, not "Str" and "Boolean". Minor formatting.

### Q21 — FRAGILE
```
Kai: "something about not being able to deserialise... don't know"
Correct: "error: datetime"
```
Your first instinct was right. json.dumps cannot serialise datetime objects — raises TypeError. The except block catches it and prints the type name. You knew the concept but could not commit. Fix: pass `default=str` to json.dumps, or use `.isoformat()`.

### Q22 — FUNCTIONAL
```
Kai: "95", Str, need to cast in production
Correct: '95', <class 'str'>
```
Correct. csv.DictReader returns everything as strings. In production: cast explicitly, or use a schema library. Good instinct.

**Domain 6 total: 2 correct, 1 right instinct. FUNCTIONAL. Your strongest domain.**

---

## Domain 7: Networking — FUNCTIONAL

### Q23 — FUNCTIONAL
```
Kai: "https", "v1/search", "q=hello&page=2"
Correct: 'https', '/v1/search', 'q=hello&page=2'
```
Missing the leading `/` on path. urlparse preserves the path exactly as it appears in the URL. Minor but matters when reconstructing URLs.

### Q24 — FRAGILE
```
Kai: "q=kubernetes%20pods&limit=10"
Correct: 'q=kubernetes+pods&limit=10'
```
urlencode uses `+` for spaces by default (application/x-www-form-urlencoded standard). `%20` is what `quote()` produces. The difference matters for APIs that are strict about encoding.

**Domain 7 total: 1 near-correct, 1 encoding detail wrong. FUNCTIONAL (leaning FRAGILE).**

---

## Domain 8: Testing & Debugging — FRAGILE

### Q25 — FOREIGN
```
Kai: debug, info, warning printed but not error
Correct: WARNING:test:warn msg
         ERROR:test:error msg
```
Completely backwards. `level=WARNING` means "show WARNING and above" — not "show everything up to WARNING." The hierarchy is DEBUG < INFO < WARNING < ERROR < CRITICAL. Setting level to WARNING filters *out* debug and info. To see everything: `level=logging.DEBUG`.

### Q26 — FUNCTIONAL
```
Kai: "mock-host" — CORRECT
Follow-up: "because the with patch has already mocked it" — essentially correct
```
patch replaces the attribute on the `socket` module object in `sys.modules`. When the function imports socket inside, it gets the already-loaded (and now patched) module. The mock is at the module level, not the function level.

**Domain 8 total: 1 correct, 1 completely wrong. FRAGILE. Logging is a critical gap for SRE work.**

---

## Domain 9: The Internals — FRAGILE

### Q27 — FLUENT
```
Kai: "ValueError: Below absolute zero" — CORRECT
```
You understand @property and setter validation. This is the one clean win in the internals domain.

### Q28 — FRAGILE
```
Kai: "right", ["Child", "Left", "Right", "Base"]
Correct: "left", ['Child', 'Left', 'Right', 'Base', 'object']
```
MRO goes left to right in the class definition: `Child(Left, Right)` means Left is checked before Right. So `greet()` returns "left". Your MRO list is correct except you omitted `object` at the end (all classes inherit from object).

### Q29 — FRAGILE
```
Kai: "entering session", "inside SESSION", "boom"
Correct: "entering session"
         "inside: SESSION"
         "exiting session"
         (then ValueError propagates)
```
The `finally` block ALWAYS runs — that is its entire purpose. Even when an exception is raised inside the `with` block, the context manager's finally executes before the exception propagates. You missed "exiting session" and the colon in "inside: SESSION". The exception DOES propagate after finally runs (because the context manager does not suppress it).

### Q30 — FOREIGN
```
Kai: "can't see why this doesn't produce [0,2,4,6]"
Correct: [6, 6, 6, 6]
```
The classic closure trap. All four lambdas capture the *variable* `i`, not its *value* at creation time. By the time you call them, the loop is done and `i = 3`. So every lambda computes `x * 3`. Fix: `lambda x, i=i: x * i` — the default argument captures the value at creation time.

### Q31 — FOREIGN
```
Kai: True
Correct: "no new attributes"
         False
```
`__slots__` does two things: (1) prevents creation of attributes not listed in __slots__ (hence the AttributeError), and (2) eliminates `__dict__` entirely — which is why `hasattr(obj, "__dict__")` returns False. Use it when you have millions of instances and want to save memory. It does NOT make attributes immutable — you can still change x and y.

**Domain 9 total: 1 fluent, 4 wrong. FRAGILE (property decorator is solid, everything else is gaps).**

---

## Domain 10: The Glue — FOREIGN

### Q32 — FRAGILE
```
Kai: "active", "active", True, True
Correct: Status.ACTIVE
         active
         False
         True
```
`print(s)` shows `Status.ACTIVE`, not just "active" — that is the repr of an Enum member. `s.value` gives "active". And critically: `s == "active"` is **False**. Enum members do not compare equal to their values. This is by design — it prevents accidental string comparison bugs. You must compare Enum to Enum.

### Q33 — FOREIGN
```
Kai: "No idea"
Correct: UTC
         UTC+01:00
         None
```
`datetime.now()` without a timezone argument returns a *naive* datetime — `tzinfo` is None. This is one of the most common production bugs in Python. Naive and aware datetimes cannot be compared, subtracted, or mixed — you get a TypeError. Always use `datetime.now(timezone.utc)`.

### Q34 — FOREIGN
```
Kai: "don't know"
Correct: 64
         <class 'str'>
```
SHA-256 produces 32 bytes = 256 bits. hexdigest() converts each byte to 2 hex characters: 32 * 2 = 64 characters. The result is a string. Useful for: file checksums, cache keys, integrity verification.

### Q35 — FRAGILE
```
Kai: "current path of execution maybe", "macos?", "14"
Correct: "exam.py", "darwin", (3, 14)
```
`sys.argv[0]` is the script name as invoked. `sys.platform` on macOS is "darwin" (the kernel name). `version_info[:2]` returns a tuple like `(3, 14)`, not just "14".

**Domain 10 total: 0 correct, 3 foreign, 1 fragile. FOREIGN.**

---

## Bonus: SRE Gauntlet — FRAGILE

### Q36 — FRAGILE
```
Kai: "attribute error, dictionary property must be string, use Set instead"
Correct: TypeError: unhashable type: 'list'
```
Three errors: (1) It is TypeError, not AttributeError. (2) Dict keys must be *hashable*, not specifically strings — ints, tuples, frozensets all work. (3) A set is also unhashable. You would use a **tuple**: `d[(1, 2, 3)] = "value"`. Hashability is a fundamental Python concept for SRE work — you need it for caching, deduplication, and set operations.

### Q37 — FUNCTIONAL
```
Kai: [1,2,3,4], [1,2,3,4] — CORRECT
Follow-up: a[:] creates new list, list(a), copy — all correct
```
You understand reference vs copy. `a[:]`, `list(a)`, `a.copy()`, and `copy.copy(a)` all create shallow copies. Good.

### Q38 — FUNCTIONAL
```
Kai: ['a'], ['a','b'], ['a','b','c'] — CORRECT
Follow-up: knows the gotcha, understands default is instantiated once
```
Correct. The mutable default argument is evaluated once at function definition time. Fix: `def add_item(item, lst=None): lst = lst if lst is not None else []`. You knew this from your recent exam. Good retention.

### Q39 — FRAGILE
```
Kai: False, False
Correct: True, False
```
CPython interns integers from -5 to 256. `x = 256; y = 256` — both point to the same cached object, so `is` returns True. 257 is above the cache range, so `a` and `b` are separate objects. In production: never use `is` for value comparison. Use `==`. Reserve `is` for `None` checks only: `if x is None`.

### Q40 — FOREIGN
```
Kai: "Don't know"
Correct: "caught"
         "always"
```
The `else` block runs ONLY if no exception was raised in `try`. Since 1/0 raises ZeroDivisionError, `except` catches it, `else` is skipped, `finally` always runs. Why use `else`? To keep code that should only run on success *outside* the try block, so it doesn't accidentally catch exceptions from that code too.

**Bonus total: 2 correct, 2 fragile, 1 foreign. FRAGILE.**

---

## HEAT MAP

| # | Domain | Score | Key Gaps |
|---|--------|-------|----------|
| 1 | Data Structures | **FOREIGN** | defaultdict, deque, Counter API, heapq |
| 2 | Iteration & Functional | **FRAGILE** | itertools entirely, functools partially, generator sum behaviour |
| 3 | Text & Patterns | **FRAGILE** | regex group numbering, f-string alignment, pattern reading precision |
| 4 | OS & Process | **FRAGILE** | subprocess completely unknown, pathlib dot/resolve details |
| 5 | Concurrency | **FRAGILE** | threading mechanics (knows race exists, not why), gather order |
| 6 | Serialisation | **FUNCTIONAL** | json datetime, csv types — strongest domain |
| 7 | Networking | **FUNCTIONAL** | urlencode +/% distinction |
| 8 | Testing & Debugging | **FRAGILE** | logging levels completely backwards, mock concept OK |
| 9 | Internals | **FRAGILE** | property OK, MRO/closures/slots/finally all gaps |
| 10 | The Glue | **FOREIGN** | Enum comparison, datetime timezone, hashlib, sys |
| B | SRE Gauntlet | **FRAGILE** | hashability, integer interning, try/else/finally |

## OVERALL: FRAGILE

**Correct answers: 8/40 (20%)**
**Right instinct, wrong output: 12/40 (30%)**
**Foreign / don't know: 11/40 (27.5%)**
**Wrong: 9/40 (22.5%)**

---

## ASSESSMENT

You are not a Python programmer. You are someone who has *used* Python — there is a difference. You have intuition about what things do, which means you have read and written real code. But the stdlib is almost entirely unexplored territory, the internals are opaque, and the details that distinguish working code from correct code are missing.

The good news: your intuition-to-knowledge ratio is high. When you guessed, you guessed in the right direction more often than not. That means the *mental model* is forming — it just has not been tested against reality enough. Thirty minutes a day with a REPL and the stdlib docs will move FRAGILE to FUNCTIONAL within weeks. FOREIGN to FRAGILE takes longer but is achievable in the 6-month window.

**Priority order for study (highest impact first):**

1. **subprocess** — you will use this every day as an SRE. `run()`, `check`, `capture_output`, `text`, `CalledProcessError`. Non-negotiable.
2. **collections** — defaultdict, Counter, deque. Three tools that eliminate 50% of ad-hoc data wrangling.
3. **logging** — the level hierarchy. DEBUG < INFO < WARNING < ERROR < CRITICAL. You had it backwards. SRE lives and dies by logging.
4. **try/except/else/finally** — you use this daily but do not understand the flow. 20 minutes with a REPL.
5. **itertools** — chain, islice, groupby. The tools that replace nested for-loops.
6. **pathlib details** — suffix includes the dot, stem strips only the last suffix, resolve() normalises.
7. **closures and the late binding trap** — Q30. This will bite you in production.
8. **datetime timezone** — naive vs aware. One of the top 5 production bug sources in Python.
9. **Enum comparison semantics** — Enum != string. By design.
10. **hashability** — what can be a dict key and why. Fundamental to Python's data model.
