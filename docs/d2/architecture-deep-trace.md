---
title: "NanoClaw/halos Architecture — Deep Trace"
category: reference
status: active
created: 2026-03-17
---

# NanoClaw/halos Architecture — Deep Trace

> Phase 6 architectural review, 2026-03-17. These diagrams trace the physical and logical boundaries where data is transformed, mounted, or proxied.

## The halos/NanoClaw "Deep Trace"

This diagram traces a single "thought-to-action" cycle.

```text
       USER / EXTERNAL WORLD
          |
          | (1) Message: "@HAL, remember the API key expires in June"
          v
+========================================================================+
| HOST OS (macOS / Linux)                                                |
| [Process: Node.js Orchestrator]                                        |
|                                                                        |
|  +-------------------+      (2) Write      +-----------------------+   |
|  |  Channel Adapter  |-------------------->| SQLite (messages.db)  |   |
|  |  (Telegram/WA)    |      Metadata       +-----------------------+   |
|  +---------^---------+                         |                       |
|            |                                   | (3) Polling Loop      |
|            |                                   v                       |
|            |                        +-----------------------+          |
|            |                        |  Message/Task Router  |          |
|            |                        +-----------+-----------+          |
|            |                                    |                      |
|            |        (4) SPAWN CONTAINER         |                      |
|            |            with MOUNTS             v                      |
|  +---------+---------+               __________________________        |
|  | Credential Proxy  | <~~~~~~~~~~~~/   CONTAINER BOUNDARY     \       |
|  | Port: 3001        |    (6) HTTP  | (Isolation via Hypervisor)|      |
|  +---------^---------+      Proxy   \__________________________/      |
|            :           (Keys hidden)            |                      |
|            :                                    |                      |
|            :            +-----------------------v-------------------+  |
|            :            | GUEST OS (Alpine/Debian Linux)            |  |
|            :            | [Process: Node.js Agent Runner]           |  |
|            :            |                                           |  |
|            :            | (5) BOOTSTRAP:                            |  |
|            :            | Read /workspace/project/memory/INDEX.md   |  |
|            :            |                                           |  |
|            :            |   +-----------------------------------+   |  |
|            :            |   | CLAUDE AGENT SDK (The "Mind")     |   |  |
|            :            |   |   - Generates YAML/Code           |   |  |
|            :            |   |   - Calls Tools via Shell         |   |  |
|            :            |   +-----------------+-----------------+   |  |
|            :            |                     |                     |  |
|            :            |                     | (7) Execute Tool    |  |
|            :            |                     v                     |  |
|            :            |   +-----------------------------------+   |  |
|            :            |   | halos TOOLKIT (Python CLIs)       |   |  |
|            :            |   | [memctl | nightctl | halctl]      |   |  |
|            :            |   +-----------------+-----------------+   |  |
|            :            |                     |                     |  |
+------------:------------+---------------------|---------------------+--+
             :                                  |
             :               (8) FILESYSTEM PERSISTENCE
             :                   (The Shared State)
             :                          |
     [CREDENTIALS]                      v
     ANTHROPIC_KEY ---------> /groups/{name}/notes/*.md  (Note File)
     OAUTH_TOKEN   ---------> /queue/items/*.yaml        (Task File)
             :               /memory/INDEX.md            (Derived Index)
             :                          |
             :                          | (9) Signal Change
             :                          v
+------------:--------------------------+--------------------------------+
|            :            +-----------------------+                      |
|            :            | IPC DIRECTORY         |                      |
|            :~~~~~~~~~~~>| /data/ipc/input/      | (11) Polls Output    |
|   (10) HTTP Response    | /data/ipc/messages/   |-------------------+  |
|      (Usage Data)       +-----------------------+                   |  |
|                                                                     |  |
|  +-------------------+                                              |  |
|  |   agentctl        | <--------------------------------------------+  |
|  | (Usage Ingress)   |        (12) Recalculate cost/spin status        |
|  +-------------------+                                                 |
+------------------------------------------------------------------------+
```

### Felt Sense: 3 Key Observations

#### 1. The "Ghost in the Machine" (Mounts)
When the container spawns, it doesn't "see" your computer. It sees a **carefully curated hallucination** of your filesystem.
*   It thinks `/workspace/group` is its entire universe.
*   It has no idea that when it writes a file there, it is actually punching through the hypervisor wall into your `~/nanoclaw/groups/` folder.
*   **The Sensation:** Working in a room with "One-Way Glass." The agent can see the data you give it, but it can't see the hand that holds the glass.

#### 2. The "Secret Siphon" (Credential Proxy)
Notice the **dotted line ( : )** in the diagram.
*   The Agent SDK makes a standard web request to `api.anthropic.com`.
*   However, the Host has re-routed that request to `localhost:3001`.
*   The Agent thinks it is talking to the cloud; it is actually talking to the Node.js process on your Mac.
*   **The Sensation:** The Agent is like a child playing with a toy phone that is secretly plugged into the parent's real phone. The parent (Node) listens to the conversation and adds the "Real" credentials before letting the message reach the world.

#### 3. The "Slow-Motion Nerve Impulse" (IPC)
Because there is no "live" socket between the Host and the Container's sub-processes (the Python tools):
*   Communication happens by **dropping letters in a mailbox**.
*   `memctl` writes a file; the Host polls the directory; the Host notices the file; the Host acts.
*   **The Sensation:** This creates a distinct "rhythm" to the system. It isn't instantaneous. You can literally watch the "nerves" fire by running `ls -la data/ipc/messages/` and seeing a file appear for a split second before being swallowed by the Host.

---

## The halos Module "Internal Anatomy" Trace

To understand the halos modules, stop thinking of them as a "program" and start thinking of them as a **surgical kit**. Each tool is a sharp, independent instrument that performs one operation on a shared "body" (the Filesystem).

```text
       COMMAND INVOKER
    (Agent via Bash OR Human)
              |
              | (1) $ memctl new --title "Decision: Go" --body "..."
              v
+-----------------------------------------------------------------------+
| HALOS MODULE BOUNDARY (Python CLI)                                    |
| [Example: halos/memctl/cli.py]                                        |
|                                                                       |
|   (2) SCHEMA GATE (halos/module/note.py)                              |
|   - Rejects missing fields / bad types                                |
|   - Prevents "Logic Slop" from entering the disk                      |
|                                                                       |
|   (3) FILENAME FACTORY                                                |
|   - ID generation: 20260317-143022-017                                |
|   - Slugification: ...-decision-go.md                                 |
|                                                                       |
|   (4) THE ATOMIC SWAP (The "Wait-and-Replace")                        |
|   - Write payload to: file.md.tmp  <----------------+                 |
|   - If success: os.replace(.tmp, .md)               | FS LOCK (None)  |
|   - "Atomic Lie": Only the final swap is safe ------>| RISK OF COLLISION
|                                                     +-----------------+
|   (5) TELEMETRY SIPHON (halos/common/log.py)                          |
|   - Emits JSON line: {"event": "note_created", ...}                   |
|   - Siphons to halos.log (The Audit Trail)                            |
|                                                                       |
+-----------------------------------------------------------------------+
              |
              | (6) TRIGGER REBUILD (Derived State)
              v
+-----------------------------------------------------------------------+
| THE FILESYSTEM SPINE (Single Source of Truth)                         |
|                                                                       |
|  /memory/notes/                                                       |
|     ├── 20260315-fact.md                                              |
|     └── 20260317-decision-go.md (NEW) <-------+                       |
|                                               | (7) HASH CALCULATION  |
|  /memory/INDEX.md (The "Map")                 |   & METADATA SYNC     |
|     └── YAML block with SHA256 <--------------+                       |
|                                                                       |
|  /queue/items/                                                        |
|     └── 20260317-task.yaml (The Workflow)                             |
|                                                                       |
+-----------------------------------------------------------------------+
              |
              | (8) AGENT BOOTSTRAP (Next Session)
              v
   "Reading INDEX.md... I recall the decision to 'Go'..."
```

### Felt Sense: The 4 Strategic Boundaries

#### 1. The "Paper Gate" (Validation)
The halos modules act as the **immune system** for the agent's memory.
*   **The Sensation:** If the agent tries to write a note without a `type` or `priority`, the CLI effectively "slaps the hand" of the agent.
*   **The Result:** The filesystem stays "high-quality." You never end up with a folder full of `temp1.txt`, `temp2.txt`. You get a library, not a junk drawer.

#### 2. The "Derived State" (Index vs. Files)
There is a fundamental boundary between the **Notes** (the detailed truth) and the **Index** (the summary map).
*   **The Sensation:** The system is "Double-Buffered." The Index is like a library card catalog. The Notes are the books.
*   **The Risk:** If you edit a Note file with a regular text editor (bypassing the CLI), the **Index becomes a lie**. This is why `memctl index verify` is a "Critical Path" command — it re-scans the spine to see if anyone cheated.

#### 3. The "Temporal Window" (nightctl)
`nightctl` creates a logical boundary around **Time**.
*   **The Sensation:** It turns "Now" into "Later." When the agent enqueues a job, it isn't executing; it is **shifting weight**.
*   **The Feeling:** The system has a "Heartbeat." During the day, it accumulates tension (Pending Tasks). At night (The Window), it releases that tension (Execution).

#### 4. The "Language Bridge" (Standard IO)
Because these are Python CLIs, they communicate with the Node.js orchestrator via **Text over Pipes**.
*   **The Sensation:** The orchestrator and the toolkit are "Co-existing strangers." They don't share memory or variables. They only share a **vocabulary of filenames and JSON strings**.
*   **The Result:** You can delete the entire Node.js orchestrator and replace it with a Go program, and the `halos` kit won't even notice. The Filesystem is the only thing that matters.

---

## Module Archetypes

*   **memctl:** The **Librarian**. Manages the relationship between data and the "Map" (Index).
*   **nightctl:** The **Dispatcher**. Manages the queue and the "Run Records."
*   **cronctl:** The **Metronome**. Synchronizes the toolkit with the System Clock (Crontab).
*   **logctl:** The **Observer**. A read-only lens over the "Nerve impulses" (Log files).
*   **agentctl:** The **Accountant**. Tracks the cost of the "Mind" (Token usage/API calls).
*   **halctl:** The **Fleet Commander**. Spawns, monitors, and retires microHAL instances.

---

## The Verdict

halos is an "Artisanal" Architecture.

It is ideally suited for a Single-User Power-Operator. For a developer who wants an assistant that feels like a shared terminal session, it is arguably the best architecture currently available. It respects the operator's intelligence and provides total transparency.

However, it is unsuitable for Multi-Tenant or Enterprise use in its current form. The reliance on filesystem polling and O(N) index loading means it will hit a performance wall that cannot be solved by "adding more RAM" — it is limited by the "physics" of LLM context windows.

**Final Thought:** The system's greatest innovation isn't the code — it's the Enforcement Loop. Using the agent's own tool-output to "nudge" it toward memory enrichment is a brilliant use of the "Attention" mechanism of Transformers as an architectural control layer.

## Provenance

Written by the human operator (Rick Hallett) as Phase 6 architectural review, 2026-03-17. Produced with assistance from a cross-model analysis pipeline. The "felt sense" annotations bridge engineering and experiential understanding — the therapist-engineer intersection at work.
