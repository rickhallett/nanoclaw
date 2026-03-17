# halos Architecture Review — 2026-03-16

## What halos is

Seven Python CLI tools installed as a single package via `uv sync`. They manage the operational state around a NanoClaw agent — memory, jobs, cron, backlog, logs, reports, session tracking. None of them replace NanoClaw's core runtime. They sit alongside it.

NanoClaw handles message routing, container orchestration, credential proxying, and the Claude Agent SDK integration. halos handles everything the agent needs to *know*, *remember*, *schedule*, and *audit* outside of a single conversation turn.

## The architecture

```
NanoClaw (Node.js)                    halos (Python)
─────────────────                     ──────────────
Telegram/WhatsApp ←→ Messages         memctl    — what the agent knows
Container runner  ←→ Agent execution  nightctl  — what the agent deferred
Task scheduler    ←→ Cron triggers    cronctl   — what runs on a clock
IPC watcher       ←→ Agent ↔ host     todoctl   — what needs doing
SQLite            ←→ Message history  logctl    — what happened
Credential proxy  ←→ API auth         reportctl — the digest
                                      agentctl  — how much agent time was spent
```

The boundary is clean: NanoClaw owns the runtime, halos owns the state. They communicate through the filesystem — the same IPC mechanism NanoClaw already uses for container-to-host messaging.

## Established patterns

**Filesystem-first storage.** Every module stores state as YAML or Markdown files in a known directory. No database, no binary format, no opaque state. This is the Unix philosophy applied to agent tooling: data as files, tools as filters, `cat` and `ls` as debuggers.

**Derived indices.** memctl's INDEX.md and nightctl's MANIFEST.yaml are both regenerable from the source files. This is the same principle as a database index or a build cache — if it drifts, rebuild it, no data loss. The source files are ground truth.

**Schema validation at write time, not read time.** This follows the "parse, don't validate" principle from functional programming, adapted for CLI tools. The `new`/`add`/`enqueue` commands enforce schema before writing. The files on disk are assumed valid. (The adversarial review found this assumption is too trusting — validation on load was added in the fix pass.)

**Controlled vocabulary.** Tags and types are defined in config, not invented at write time. This is borrowed from library science — controlled vocabularies prevent the synonym problem where the same concept gets tagged three different ways and search misses two of them.

**Archive not delete.** From the slopodar taxonomy's own design invariant. Pruning moves files, never removes them. Destructive operations require explicit flags and config changes. This is the "append-only log" pattern from event sourcing, applied to memory governance.

**Atomic writes.** Temp file then `os.replace()`. Borrowed from database WAL design and NanoClaw's own IPC file protocol (which uses the same pattern for container-to-host messages). Prevents partial writes on crash.

## Where it innovates

**The enrichment rubric.** Most knowledge graphs either link everything automatically (embedding similarity to hairball) or require manual curation (doesn't scale). `memctl enrich` sits in the middle with a five-dimension heuristic scorer that proposes links for human batch approval. The scoring dimensions (semantic bridge, cross-type novelty, causal direction, cluster value, recall utility) are legible and tunable. The noise tag filter prevents the "kai appears in everything" problem. The muster format enables fast binary decisions. Human approvals change the graph topology, which changes future cluster_value scores. It's a feedback loop that trains itself without ML infrastructure.

**The enforcement loop.** Three layers that make the agent follow the memory protocol without a hook system: L8 (CLAUDE.md system prompt says "not optional"), L7 (memctl stdout prints neighbour summary and "connect the dots?" after every write), and structural context (the neighbour list shows what *could* be linked). This uses the layer model's own insight — tool output occupies high semantic real estate in the attention window.

**The conversation extraction protocol.** A defined rubric for what crosses the threshold from conversational texture to durable knowledge. Five categories that pass (identity insights, anxiety anchors, standing decisions, reference material, valued analogies), five that don't (pleasantries, transient events, decorative metaphors, redundant coaching, emotional texture). This turns an ad-hoc judgment call into a repeatable decision framework.

**The adversarial review structure.** Independent reviewers per module with no shared context, focused mandates (find bugs, not confirm correctness), severity-graded output, and a triage muster. This is the verification fabric from The Pit applied to the tools that manage The Pit's knowledge.

## Why the decisions were made

**Python over Go.** The spec originally called for Go. We built it, used it, and found ourselves reaching for Python every time we needed to do something beyond schema validation. YAML parsing, string manipulation, filesystem walks, graph rendering — all Python's home turf. The rewrite halved the line count and eliminated the compilation step. SD-310 (Python via uv exclusively) sealed it.

**Separate tools over a monolith.** Each module has its own config, its own data directory, its own CLI. They can be used independently. reportctl reads the other modules' data files but doesn't import their code. This keeps coupling low and makes it possible to replace or remove a module without cascading changes.

**YAML over JSON.** YAML is human-readable and human-editable (even though the tools say "never edit directly," humans will). JSON frontmatter in a Markdown file would require custom parsing. YAML frontmatter is a well-established convention (Jekyll, Hugo, Obsidian).

**No LLM in the governance loop.** memctl enrich uses structural heuristics, not embeddings or LLM calls. Pruning uses a mathematical decay function. The agent's role is limited to `memctl new` and reading the index. This is deliberate: the memory store must be trustworthy even when the agent is probabilistic. If the governance layer is also probabilistic, you've built a system that can gaslight itself.

## What it does well

**The design language is consistent.** Seven modules, same conventions. A developer who understands memctl can read any other module. Config at repo root, data in a named directory, CLI as the only write path, `--json` and `--dry-run` on everything.

**The memory graph is genuinely useful.** 59 notes with 18 backlinks, searchable by entity and tag, with a visual graph output. The enrichment proposals were 18/18 approved on first muster — the scoring heuristic found real connections the tag model missed.

**The test suite is real.** 539 tests across 7 modules. The adversarial review found 91 issues and 14 of the most critical were fixed with regression tests. The tests aren't tautological — the adversarial reviewers specifically checked for that.

**The enforcement loop works.** The post-write stdout nudge is the right weight of intervention for the current stage. It doesn't require hook infrastructure, it's visible in the agent's context, and it's cheap to add more modules' post-write behaviour later.

## What could be improved

**The adversarial review pattern should be automated.** We ran it manually and it found 91 issues. A scheduled job that dispatches review agents against each module on a weekly cadence would catch drift as the codebase evolves. Right now it's a one-shot — the paper guardrail problem, again.

**logctl is a reader without a writer.** halos modules don't emit structured logs. They print to stdout/stderr. logctl can parse NanoClaw's pino output but has no halos-native log source to consume. The "halos structured" format is defined in the parser but nothing writes it. logctl is infrastructure waiting for a use case.

**reportctl's cross-module coupling is the most fragile point.** It reads other modules' data files without importing their code (correct design), but the field names are implicit contracts. The `status` vs `outcome` bug proved this. Integration tests between modules would catch these, and we have none.

**todoctl is still the thinnest module.** The adversarial review confirmed: no archive (done items accumulate), no edit command, no cancel status, no entities field. The MEDIUM findings weren't all fixed in this pass.

**The noise tag filter in enrich is hand-tuned.** `NOISE_TAGS` and `NOISE_ENTS` are hardcoded sets that work for the current corpus but will need updating as the graph grows. These should be in config, not code.

**No cross-module integration tests.** Unit tests per module: strong. Workflow simulations: passed. But there's no test that creates a real memctl note, runs reportctl briefing against it, and asserts the output contains the note. The simulated workflows ran against temp directories, not the real data formats. The corrupt file test used `.yaml` instead of `.md` and didn't actually exercise the error path.

**The container image is 2.37 GB.** Chromium and its dependencies are the bulk. If a container only needs CLI tools and no browser, a lighter image would halve startup time. Two-tier images (slim for CLI-only, full for browser) would be a meaningful optimisation.

**agentctl ingests after the fact.** It parses log files that container-runner wrote, which means session data is only available after the container exits and someone runs `agentctl ingest`. A hook that writes the session record at container shutdown would make the data available immediately.

**The "halos" name.** It works. The capability map suggests reframing "OS" as "Operational Surface" to guard against scope creep. The risk is that calling it an OS invites building one. It's a tool suite, not a kernel. The name should reflect that.
