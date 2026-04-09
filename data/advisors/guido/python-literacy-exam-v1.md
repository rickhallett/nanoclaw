# The Python Literacy Exam — v1
**Administered by: Guido van Rossum, BDFL (ret.)**
**Subject: Kai**
**Date: 2026-04-07**

---

*Adjusts glasses. Opens a plain text file. No syntax highlighting.*

Rules:
- Read each snippet. Write what it outputs. If it raises an exception, name the exception.
- No REPL. No interpreter. No looking anything up. Brain only.
- If you are unsure, say so. Guessing teaches nothing.
- Some snippets have a follow-up: "What would you change?" Answer briefly.
- Write your answers in the `> OUTPUT:` block below each snippet.

---

## Domain 1: Data Structures (collections, heapq, bisect)

### Q1
```python
from collections import Counter

words = "the cat sat on the mat the cat".split()
c = Counter(words)
print(c.most_common(2))
```

> OUTPUT: "cat"

---

### Q2
```python
from collections import defaultdict

d = defaultdict(list)
pairs = [("a", 1), ("b", 2), ("a", 3), ("b", 4), ("a", 5)]
for k, v in pairs:
    d[k].append(v)
print(dict(d))
print(d["c"])
```

> OUTPUT: Exception, loop tries to append(v) before d[k] is defined

---

### Q3
```python
from collections import deque

d = deque([1, 2, 3], maxlen=3)
d.append(4)
d.appendleft(0)
print(list(d))
```

> OUTPUT: not familiar with deque; presumably it prevents append(4), unsure if it throws or swallows this

---

### Q4
```python
import heapq

nums = [5, 1, 8, 3, 2, 9]
print(heapq.nsmallest(3, nums))
print(nums)
```

> OUTPUT: unfamiliar with heapq; my best guess is this does not alter nums list in place but returns 3 smallest values

> FOLLOW-UP: Is `nums` modified by `nsmallest`? What if you had called `heapq.heapify(nums)` first?

---

## Domain 2: Iteration & Functional (itertools, functools)

### Q5
```python
from itertools import chain, islice

a = [1, 2, 3]
b = [4, 5, 6]
c = chain(a, b)
print(list(islice(c, 2, 5)))
```

> OUTPUT: unfamilr with itertools, chain, islice. best guess is chain concats the two lists and islice returns slice at 2nd and 5th index, in this case creating a new list of [2,3,4,5]

---

### Q6
```python
from itertools import groupby

data = [1, 1, 2, 3, 3, 3, 2, 2]
result = [(k, list(g)) for k, g in groupby(data)]
print(result)
```

> OUTPUT: unfamiliar with groupby; best guess is that in this case it returns nested list of [[1,1],[2],[3,3],[2,2]]; I wont reason further about value of result as my base assumption is probably incorrect. with a repl I would identify that first.

> FOLLOW-UP: Why does `2` appear twice as a key? What would you do if you wanted all 2s grouped together?

---

### Q7
```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(10))
print(fib.cache_info())
```

> OUTPUT: not sure what this is, memoisation? presumably fib.cache_info() returns object values stored on fib as a result of the lru_cache decorator

---

### Q8
```python
squares = (x**2 for x in range(5))
print(type(squares))
print(sum(squares))
print(sum(squares))
```

> OUTPUT: generator returns type iter?. sum(squares) = 55, second print either raises error (generator exhasted) or None/Null 

> FOLLOW-UP: Why does the second `sum` return what it returns?

---

### Q9
```python
from functools import partial

def power(base, exp):
    return base ** exp

square = partial(power, exp=2)
cube = partial(power, exp=3)
print(square(5))
print(cube(3))
```

> OUTPUT: 25, 3 (partial presumably creates a new function with one named arg already defined)

---

## Domain 3: Text & Patterns (re, string)

### Q10
```python
import re

text = "error: 404, error: 500, info: 200"
matches = re.findall(r"error: (\d+)", text)
print(matches)
```

> OUTPUT: ["404","500","200"]

---

### Q11
```python
import re

pattern = re.compile(r"(\w+)@(\w+)\.(\w+)")
m = pattern.match("kai@oceanheart.ai")
if m:
    print(m.groups())
    print(m.group(2))
```

> OUTPUT: ["kai","oceanheart","ai"], ["ai"]

---

### Q12
```python
name = "kai"
width = 20
print(f"{name:>20}")
print(f"{name:*^20}")
```

> OUTPUT: "kai                    ", "                    kai"

---

## Domain 4: OS & Process (pathlib, subprocess, tempfile)

### Q13
```python
from pathlib import Path

p = Path("/Users/kai/code/halo/data/../data/notes/file.md")
print(p.resolve().parent.name)
print(p.suffix)
print(p.stem)
```

> OUTPUT: "halo", "md", "file"

> FOLLOW-UP: What does `.resolve()` do here that matters? - traverses data dir to find file.md, arbitrary number of ops

---

### Q14
```python
import subprocess

result = subprocess.run(
    ["echo", "hello world"],
    capture_output=True,
    text=True
)
print(repr(result.stdout))
print(result.returncode)
```

> OUTPUT: "hello world"...nope no idea. Dont know type .run() returns, nor what repr does with that.

---

### Q15
```python
import subprocess

try:
    subprocess.run(["false"], check=True)
    print("success")
except subprocess.CalledProcessError as e:
    print(f"failed: {e.returncode}")
```

> OUTPUT: Dont know

---

### Q16
```python
from pathlib import Path

p = Path("somefile.tar.gz")
print(p.suffix)
print(p.suffixes)
print(p.stem)
```

> OUTPUT: "tar.gz", ["tar","gz"], "somefile"

---

## Domain 5: Concurrency (threading, asyncio, concurrent.futures)

### Q17
```python
import threading

counter = 0

def increment():
    global counter
    for _ in range(100000):
        counter += 1

threads = [threading.Thread(target=increment) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(counter == 500000)
```

> OUTPUT: False

> FOLLOW-UP: Why? What would you use to fix it? - global declares counter 5 times. I don't understand the scope behaviour to be honest. I think it would be better if each thread maintained its own count and returned it after execution, at which point we sum each value

---

### Q18
```python
from concurrent.futures import ThreadPoolExecutor

def fetch(url):
    return f"fetched {url}"

urls = ["a.com", "b.com", "c.com"]
with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(fetch, urls))
print(results)
```

> OUTPUT: ["fetched {a,b,c}.com"] (first two workers concurrent, 3rd is after, but all run)

---

### Q19
```python
import asyncio

async def greet(name, delay):
    await asyncio.sleep(delay)
    return f"hello {name}"

async def main():
    results = await asyncio.gather(
        greet("kai", 0.2),
        greet("ben", 0.1),
    )
    print(results)

asyncio.run(main())
```

> OUTPUT: ["hello ben", "hello kai"]

> FOLLOW-UP: In what order do the coroutines *start*? In what order do they *finish*? Does the output reflect start order or finish order? - they start in declared order, but async await reeturns ben before kai

---

## Domain 6: Serialisation & Config (json, csv, struct)

### Q20
```python
import json

data = {"name": "kai", "balance": 5370.82, "active": True}
s = json.dumps(data)
print(type(s))
d = json.loads(s)
print(d["active"])
print(type(d["active"]))
```

> OUTPUT: Str, True, Boolean

---

### Q21
```python
import json
from datetime import datetime

data = {"ts": datetime.now()}
try:
    print(json.dumps(data))
except TypeError as e:
    print(f"error: {type(data['ts']).__name__}")
```

> OUTPUT: initially thought it was something about not being able to deserialise this object but actually I dont know enough about that

> FOLLOW-UP: How do you fix this without removing the datetime? Show the minimal change.

---

### Q22
```python
import csv
from io import StringIO

data = "name,score\nkai,95\nben,87\n"
reader = csv.DictReader(StringIO(data))
rows = list(reader)
print(rows[0]["score"])
print(type(rows[0]["score"]))
```

> OUTPUT: presumably "95", type Str, need to cast in production. Dont know anything about these classes.

> FOLLOW-UP: Why is the type what it is? How would you handle this in production?

---

## Domain 7: Networking & HTTP (socket, urllib)

### Q23
```python
from urllib.parse import urlparse, urlencode

url = "https://api.example.com/v1/search?q=hello&page=2"
parsed = urlparse(url)
print(parsed.scheme)
print(parsed.path)
print(parsed.query)
```

> OUTPUT: "https", "v1/search", "q=hello&page=2", not sure why we are importing urlencode here?

---

### Q24
```python
from urllib.parse import urlencode, quote

params = {"q": "kubernetes pods", "limit": 10}
print(urlencode(params))
```

> OUTPUT: "q=kubernetes%20pods&limit=10"

---

## Domain 8: Testing & Debugging (unittest, logging, pdb)

### Q25
```python
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test")

logger.debug("debug msg")
logger.info("info msg")
logger.warning("warn msg")
logger.error("error msg")
```

> OUTPUT: "test: debug msg", "test: info msg", "test: warn msg"

> FOLLOW-UP: Why are only some messages printed? What level would you set to see everything? - config'd up to warning, would need to set to error to see error messages

---

### Q26
```python
from unittest.mock import patch

def get_hostname():
    import socket
    return socket.gethostname()

with patch("socket.gethostname", return_value="mock-host"):
    print(get_hostname())
```

> OUTPUT: "mock-host"

> FOLLOW-UP: Why does this work even though `get_hostname` imports socket inside the function? - because the 'with' patch has already mocked it? No idea.

---

## Domain 9: The Internals

### Q27
```python
class Celsius:
    def __init__(self, temp=0):
        self._temp = temp

    @property
    def temp(self):
        return self._temp

    @temp.setter
    def temp(self, value):
        if value < -273.15:
            raise ValueError("Below absolute zero")
        self._temp = value

c = Celsius(25)
c.temp = -300
```

> OUTPUT: "ValueError: Below absolute zero"

---

### Q28
```python
class Base:
    def greet(self):
        return "base"

class Left(Base):
    def greet(self):
        return "left"

class Right(Base):
    def greet(self):
        return "right"

class Child(Left, Right):
    pass

print(Child().greet())
print([c.__name__ for c in Child.__mro__])
```

> OUTPUT: "right", ["Child", "Left", "Right", "Base"]

---

### Q29
```python
from contextlib import contextmanager

@contextmanager
def managed(name):
    print(f"entering {name}")
    try:
        yield name.upper()
    finally:
        print(f"exiting {name}")

with managed("session") as s:
    print(f"inside: {s}")
    raise ValueError("boom")
```

> OUTPUT: "entering session", "inside SESSION", "boom"

> FOLLOW-UP: Does the `finally` block run? Does the exception propagate? - No; ValueError is not caught and so program terminates 

---

### Q30
```python
def make_multipliers():
    return [lambda x: x * i for i in range(4)]

fns = make_multipliers()
print([f(2) for f in fns])
```

> OUTPUT: I cant see why this doesnt produce the array below

> FOLLOW-UP: Why? How would you fix it to get `[0, 2, 4, 6]`?

---

### Q31
```python
class Immutable:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y

obj = Immutable(1, 2)
try:
    obj.z = 3
except AttributeError:
    print("no new attributes")

print(hasattr(obj, "__dict__"))
```

> OUTPUT: True

> FOLLOW-UP: What does `__slots__` actually do, and when would you use it? - when you want to define ahead of time properties that cannot be modified after instantiation

---

## Domain 10: The Glue (argparse, sys, datetime, enum, hashlib)

### Q32
```python
from enum import Enum

class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"

s = Status("active")
print(s)
print(s.value)
print(s == "active")
print(s == Status.ACTIVE)
```

> OUTPUT: "active", "active", True, True

---

### Q33
```python
from datetime import datetime, timezone, timedelta

utc_now = datetime.now(timezone.utc)
bst = timezone(timedelta(hours=1))
local = utc_now.astimezone(bst)

print(utc_now.tzinfo)
print(local.tzinfo)

naive = datetime.now()
print(naive.tzinfo)
```

> OUTPUT: No idea

> FOLLOW-UP: Why is the last one what it is? What goes wrong in production when you mix naive and aware datetimes?

---

### Q34
```python
import hashlib

data = "ripperdoc"
h = hashlib.sha256(data.encode()).hexdigest()
print(len(h))
print(type(h))
```

> OUTPUT: dont know

---

### Q35
```python
import sys

print(sys.argv[0])
print(sys.platform)
print(sys.version_info[:2])
```

> OUTPUT: current path of execution maybe, macos?, "14"

> NOTE: For `sys.argv[0]`, just describe what it would be if this were run as `python exam.py`. For `version_info`, give what you think the current Python version tuple would be.

---

## Bonus: The SRE Gauntlet

These test the instinct, not the knowledge.

### Q36
```python
d = {}
d[[1, 2, 3]] = "value"
```

> OUTPUT: attribute error, dictionary propety must be string, use Set instead

> FOLLOW-UP: Why? What would you use instead?

---

### Q37
```python
a = [1, 2, 3]
b = a
b.append(4)
print(a)

c = a[:]
c.append(5)
print(a)
```

> OUTPUT: [1,2,3,4], [1,2,3,4]

> FOLLOW-UP: What is `a[:]` doing? Name two other ways to achieve the same thing. - Creates new list (slice), list(a), copy stdlib? not sure what it is but I there there is one

---

### Q38
```python
def add_item(item, lst=[]):
    lst.append(item)
    return lst

print(add_item("a"))
print(add_item("b"))
print(add_item("c"))
```

> OUTPUT: ["a"], ["a","b"], ["a',"b","c"]

> FOLLOW-UP: This is one of the most famous Python gotchas. Why does it happen? What is the fix? - This was in my initial python exam last week. I believe it is because the default method is instantiated once at run time initiation, if you wanted a new list each time you would have to pass in to add_item on invokation

---

### Q39
```python
x = 256
y = 256
print(x is y)

a = 257
b = 257
print(a is b)
```

> OUTPUT: False, False

> FOLLOW-UP: Why the difference? When does `is` vs `==` matter in production? type equalty vs value equality, 'is' is instance equality and each variable is a primitive instantiation in its own right

---

### Q40
```python
try:
    result = 1 / 0
except ZeroDivisionError:
    print("caught")
else:
    print("clean")
finally:
    print("always")
```

> OUTPUT: Dont know...

> FOLLOW-UP: When does the `else` block run? Why would you use it instead of putting code in the `try`?

---

## Scoring Key
*(To be filled by Guido after review)*

| Domain | Score | Notes |
|--------|-------|-------|
| 1. Data Structures | — | |
| 2. Iteration & Functional | — | |
| 3. Text & Patterns | — | |
| 4. OS & Process | — | |
| 5. Concurrency | — | |
| 6. Serialisation & Config | — | |
| 7. Networking & HTTP | — | |
| 8. Testing & Debugging | — | |
| 9. The Internals | — | |
| 10. The Glue | — | |
| Bonus: SRE Gauntlet | — | |

**Overall Assessment:**

---

*The BDFL sets down the exam paper. Pours coffee. Waits.*
