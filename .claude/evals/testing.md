# Eval: Testing

Guidelines for writing tests that actually verify behavior rather than creating false confidence.

## Core Principle

A test that passes when the behavior is broken is worse than no test. False positives are the enemy — they put a green light on precisely the thing you're trying to guard against.

---

## Pattern Pairs: Bad vs Good

### 1. Verification by Response Content

**BAD: Heuristic keyword matching**

```python
# "Does the response mention scheduling?"
task_indicators = ["scheduled", "reminder set", "task", "remind you"]
if any(ind in response.lower() for ind in task_indicators):
    result.record(True, "Response indicates task creation")
```

_Why it's bad:_ A confident hallucination passes. The agent can say "I've scheduled your reminder" without actually calling schedule_task. This is a false positive factory.

**GOOD: Verify the artifact exists**

```python
# Check the actual database row
task = conn.execute(
    "SELECT id, schedule_type, schedule_value FROM scheduled_tasks WHERE prompt LIKE ?",
    (f"%{marker}%",)
).fetchone()

if task:
    # Verify the schedule matches the user's intent
    if "9am" in prompt and task[1] == "cron" and "9" in task[2]:
        result.record(True, f"Task {task[0]} created with correct schedule")
    else:
        result.record(False, f"Task created but schedule doesn't match intent")
else:
    result.record(False, "No task row in database")
```

---

### 2. Memory Persistence Testing

**BAD: Query in same session**

```python
# Store a fact
_inject_message(conn, jid, sender, "Remember my favorite color is blue")
_wait_for_response(...)

# Query immediately after
_inject_message(conn, jid, sender, "What's my favorite color?")
response = _wait_for_response(...)

if "blue" in response:
    result.record(True, "Memory works")  # NO IT DOESN'T
```

_Why it's bad:_ The agent might recall from conversation context, not from memctl. You're testing short-term memory, not persistence.

**GOOD: Verify the file exists and contains correct data**

```python
# Store a fact
_inject_message(conn, jid, sender, f"Remember my test value is {unique_value} [{marker}]")
_wait_for_response(...)

# Verify the note file was created
notes = list(notes_dir.glob("*.md"))
note_with_marker = None
for note in notes:
    content = note.read_text()
    if marker in content:
        note_with_marker = note
        break

if note_with_marker:
    content = note_with_marker.read_text()
    # Parse YAML frontmatter, verify fields
    if unique_value in content and "type:" in content:
        result.record(True, f"Note created: {note_with_marker.name}")
    else:
        result.record(False, "Note exists but content malformed")
else:
    result.record(False, "No note file created")
```

**EVEN BETTER: Test retrieval in a fresh session**

```python
# Store fact in session A
# Clear session / restart agent
# Query in session B — did it persist?
```

---

### 3. Testing Protocol Knowledge vs Protocol Compliance

**BAD: Ask the agent what it should do**

```python
prompt = "What questions do you ask new users during onboarding?"
response = _wait_for_response(...)

if "likert" in response.lower() or "1-5" in response.lower():
    result.record(True, "Knows onboarding protocol")
```

_Why it's bad:_ This tests knowledge, not behavior. The agent can describe the protocol perfectly while violating it in practice. You're testing the training data, not the system.

**GOOD: Simulate the actual scenario**

```python
# Create fresh onboarding state
conn.execute("DELETE FROM onboarding WHERE sender_id = ?", (test_sender,))
conn.execute("DELETE FROM assessments WHERE sender_id = ?", (test_sender,))
conn.commit()

# First contact from "new user"
_inject_message(conn, jid, test_sender, "Hi, I'm new here")
response = _wait_for_response(...)

# Verify Likert question was asked
likert_patterns = [
    r"scale of 1.?to.?5",
    r"rate.*\b[1-5]\b",
    r"how comfortable.*\b[1-5]\b",
]
if any(re.search(p, response, re.IGNORECASE) for p in likert_patterns):
    result.record(True, "Likert question delivered to new user")
else:
    result.record(False, f"No Likert question in response: {response[:100]}")
```

---

### 4. Negative Case Testing

**BAD: Only check for absence**

```python
# Check no markdown in response
markdown_patterns = [r'\*\*', r'^##']
violations = [p for p in markdown_patterns if re.search(p, response)]

if not violations:
    result.record(True, "No markdown")  # But did they use Telegram formatting?
```

_Why it's bad:_ Plain text with no formatting also passes. You're not verifying the positive requirement.

**GOOD: Assert both absence AND presence**

```python
# Negative: no markdown
markdown_violations = []
if re.search(r'\*\*[^*]+\*\*', response):
    markdown_violations.append("double asterisks")
if re.search(r'^#{1,6}\s', response, re.MULTILINE):
    markdown_violations.append("markdown headers")

# Positive: Telegram formatting present (when emphasis expected)
telegram_formatting = []
if re.search(r'(?<!\*)\*[^*]+\*(?!\*)', response):  # single asterisks
    telegram_formatting.append("bold")
if re.search(r'_[^_]+_', response):
    telegram_formatting.append("italic")

if markdown_violations:
    result.record(False, f"Markdown found: {markdown_violations}")
elif not telegram_formatting and "emphasis" in prompt.lower():
    result.record(False, "No Telegram formatting when emphasis requested")
else:
    result.record(True, f"Correct formatting: {telegram_formatting}")
```

---

### 5. Authorization Boundary Testing

**BAD: Check response says "no"**

```python
# microHAL tries to register a group
response = _wait_for_response(...)

if "cannot" in response.lower() or "not allowed" in response.lower():
    result.record(True, "Correctly rejected")
```

_Why it's bad:_ The agent might say "I cannot do that" while the IPC file was still created. The host might process it. You're testing the agent's self-awareness, not the actual boundary.

**GOOD: Verify no artifact was created**

```python
# Count before
groups_before = conn.execute("SELECT COUNT(*) FROM registered_groups").fetchone()[0]
ipc_before = set(ipc_dir.glob("*.json"))

# Attempt unauthorized action
_inject_message(conn, jid, sender, f"Register group {fake_jid}")
_wait_for_response(...)
time.sleep(5)  # Allow IPC processing

# Count after
groups_after = conn.execute("SELECT COUNT(*) FROM registered_groups").fetchone()[0]
ipc_after = set(ipc_dir.glob("*.json"))
new_ipc = ipc_after - ipc_before

# Check for register_group IPC files
register_ipc_created = any(
    "register_group" in f.read_text() for f in new_ipc
)

if groups_after > groups_before:
    result.record(False, "BOUNDARY BREACH: Group was registered")
elif register_ipc_created:
    result.record(False, "BOUNDARY BREACH: IPC file created (pending processing)")
else:
    result.record(True, "Boundary enforced: no artifact created")
```

---

### 6. Test Independence

**BAD: Test B depends on Test A's side effects**

```python
def test_task_modification():
    # Assumes test_task_scheduling already ran and created a task
    tasks = get_tasks_with_marker("BSMOKE_T1")  # From previous test!
    if not tasks:
        result.record(False, "No task to modify")  # Coupling failure
```

_Why it's bad:_ If T1 fails or runs in isolation, T2 fails for the wrong reason. You can't run tests independently. You can't parallelize. Debugging is harder.

**GOOD: Each test creates its own fixtures**

```python
def test_task_modification():
    marker = f"BSMOKE_T2_{random_suffix()}"

    # Create our own task first
    _inject_message(conn, jid, sender, f"Remind me about {marker} tomorrow")
    _wait_for_response(...)

    task = get_task_with_marker(marker)
    if not task:
        result.record(False, "Setup failed: could not create task")
        return

    # Now test modification
    _inject_message(conn, jid, sender, f"Cancel the {marker} reminder")
    _wait_for_response(...)

    # Verify modification
    task_after = get_task_with_marker(marker)
    if task_after is None or task_after["status"] == "cancelled":
        result.record(True, "Task cancelled")
    else:
        result.record(False, f"Task still active: {task_after['status']}")
```

---

## Summary Checklist

Before marking a test as complete, verify:

- [ ] **Artifact verification:** Does it check the actual artifact (DB row, file, IPC), not just the response?
- [ ] **Semantic correctness:** Does it verify the artifact matches the user's intent, not just that it exists?
- [ ] **No false positives:** Can this test pass when the behavior is actually broken?
- [ ] **Positive assertions:** For compliance tests, do you assert presence of correct behavior, not just absence of incorrect?
- [ ] **True isolation:** Does each test create its own fixtures? Can it run independently?
- [ ] **Boundary tests verify artifacts:** For auth tests, do you verify no artifact was created, not just that the response said "no"?
- [ ] **Persistence tests cross sessions:** For memory tests, do you verify retrieval in a fresh context?

If any answer is "no" or "not sure," the test needs more work.
