# Agent-Era Development Principles

Notes distilled from Simon Willison's talk on coding agent workflows (Statig, June 2026). These form core operating principles for NanoClaw development going forward.

Source: Simon Willison (Django co-creator, Datasette maintainer) — interview with Eric (Statig infrastructure/security lead).

---

## The TDD Imperative

Tests are no longer optional. The historical argument against tests — "it's extra work" — is void when agents write them for free.

### Red-Green TDD with Agents

Every coding session starts the same way:

1. Tell the agent how to run the test suite (`uv run pytest`, `npm test`, etc.)
2. Say "use red-green TDD"
3. Let it churn

**Why this works:** TDD constrains agent output to the minimum implementation that passes. Without it, agents over-generate — they build more than needed, introduce unnecessary abstractions, and produce code that's harder to verify.

**The five-token prompt:** `use red green TDD` — all good coding agents know the pattern. This is the highest-leverage instruction you can give.

### Manual Exercise After Tests Pass

Passing tests !== working software. Always:

1. Start the server in the background
2. Use `curl` (or equivalent) to exercise the API/interface
3. This catches integration gaps that unit tests miss

**Applied to NanoClaw:** After any container-runner or orchestrator change, the verification loop should include actually spawning a container and sending a message through the full pipeline, not just running `npm test`.

---

## The Trust Ladder

Simon describes stages of AI adoption for developers:

| Stage | Behaviour | Trust Level |
|-------|-----------|-------------|
| 1. Chat | Ask questions, get snippets | Low — verify everything |
| 2. Code assist | Agent writes some code | Medium — review line by line |
| 3. Majority generation | Agent writes more code than you | High — review structurally |
| 4. No writing | You direct, review, don't type | Higher — TDD + conformance |
| 5. No reading | You don't read the code | Highest — proof-based trust |

**Stage 5 requires:** The agent must *prove* the code works. Tests, manual exercise, conformance suites. Without proof, stage 5 is "wildly irresponsible."

**Where NanoClaw sits:** Stage 3-4 for most work. Stage 5 is aspirational but requires the gate infrastructure to support it (see: Makefile gate, `npm run gate`).

---

## Conformance-Driven Development

When a language-agnostic test suite or specification exists, use it as the oracle:

1. Build a test suite that passes against multiple known-good implementations
2. Use that test suite to drive a new implementation
3. The test suite *is* the spec

**Example:** Simon built multipart file upload tests that passed against Go, Node.js, Django, and Starlette, then used those tests to drive a Datasette implementation.

**Applied to NanoClaw:** For IPC protocol, container output markers, or any cross-boundary contract — write conformance tests that validate the protocol, not just one side of it.

---

## Code Quality Is a Choice

> "Having poor quality code from an agent is a choice that you make."

- If the agent produces 2,000 lines of bad code and you ignore it, that's on you
- If you feed refactoring instructions back, the result can exceed what you'd write by hand
- Agents will do the tedious cleanup you'd skip "because I've run out of time"
- **Small/disposable projects:** quality doesn't matter (800 lines of spaghetti, who cares)
- **Maintained projects:** quality matters, and you choose the level by engaging with the output

**The lazy human advantage:** Agents don't get tired of refactoring. Prompt for the cleanup pass you'd never do yourself.

---

## Pattern Propagation

Agents are "incredibly consistent" — they follow existing codebase patterns almost perfectly.

**Implications:**

1. **First implementation sets the standard.** The first test, the first module, the first API handler — agents will copy its style forever. Get it right.
2. **Template projects matter.** Cookie-cutter / scaffolding that puts files in the right place, sets up CI, includes one or two example tests in your preferred style. Agents propagate from there.
3. **Code quality is self-reinforcing.** High-quality codebase → agent adds high-quality code. Low-quality codebase → agent matches the mess.

> "If you're the first person to use Redis at your company you have to do it perfectly because the next person will copy and paste what you did. It's exactly the same with agents."

**Applied to NanoClaw:** The patterns in `src/index.ts`, `src/container-runner.ts`, and `src/db.ts` are the templates agents will propagate. Any pattern improvement there compounds across all future agent-written code.

---

## Security: The Lethal Trifecta

Three conditions that, combined, create catastrophic risk:

1. **Access to private data** (env vars, API keys, email, databases)
2. **Exposure to malicious instructions** (untrusted repos, user input, documentation)
3. **Exfiltration vector** (network access, ability to send messages out)

**The only guaranteed defence:** Remove one leg entirely.

- No private data access → worst case is lies
- No untrusted input → no injection vector
- No exfiltration → attacker can't extract what they find

### Sandboxing

- **Claude Code for Web / Codex:** Runs in Anthropic's/OpenAI's containers. Worst case: they steal your source code. If it's open source, who cares.
- **Docker / Apple Containers:** Good local isolation. Friction still too high for default adoption.
- **`--dangerously-skip-permissions` on local machine:** Simon does this despite being "the world's foremost expert on why you shouldn't." Convenience wins. Mitigate by not pointing agents at untrusted repos.

**Applied to NanoClaw:** Agents already run in Docker containers — this is architecturally sound. The host orchestrator running without sandboxing is the weaker link. The credential proxy (`SEC.L2`) is the compensating control.

---

## Ambition and Exhaustion

> "You have to operate firing on all cylinders if you're going to keep your trio or quadruple of agents busy solving problems. After 3 hours you're literally going to pass out in a corner."

**Key insight:** The bottleneck is human cognitive bandwidth, not agent throughput.

- Running 3 parallel agent sessions is mentally exhausting
- This is the opposite of "skill atrophy" — it requires *more* engagement, not less
- The exhaustion is what prevents 1 engineer × 1000 projects
- Agent-minutes are cheap; human-minutes of oversight are the scarce resource

**This validates the NanoClaw scope estimation rule:** Always express as `agent-minutes × human-minutes`, never wall-clock time.

---

## Career Implications

- Learn a third (fourth, fifth) programming language — don't study it, just start writing code in it with agent support
- Be more ambitious in project scope
- Invest in weird experiments and side projects — the cost of trying things has collapsed
- The value shifts from "can write code" to "can direct, verify, and compose systems"

---

## Open Source Impact

- Agents love open source — they recommend libraries, stitch ecosystems together
- Agent capability is *built on* the open source corpus
- But: projects are flooded with junk AI-generated contributions
- Component libraries (Tailwind UI, etc.) face demand collapse — agents can generate custom components
- Pull request model under pressure — some maintainers want to disable PRs entirely

---

## Inflection Points (Historical Context)

| Date | Event | Impact |
|------|-------|--------|
| 2022 | GitHub Copilot | Autocomplete, incremental help |
| 2023 Q1 | GPT-4 | First actually useful model |
| 2023 Q2-Q4 | GPT-4 plateau | 9 months of stagnation |
| 2024 Q2 | Claude Code + Sonnet 3.5 | Coding agents become viable |
| 2025 Nov | Opus 4.5 + GPT-5.1 | Code quality crosses the trust threshold |
| 2026 Jun | Opus 4.6 + Codex 5.3 | One-shotting everything; reliability becomes predictable |

> "The reason we can start trusting them is we can predict what they're going to do."

---

## Actionable Principles for NanoClaw

1. **Every agent session starts with TDD.** Include test runner instructions in CLAUDE.md or agent prompts.
2. **Manual exercise is mandatory.** After tests pass, exercise the actual system (spawn container, send message, verify delivery).
3. **Conformance suites for cross-boundary contracts.** IPC protocol, output markers, session lifecycle — test both sides.
4. **First patterns compound.** Any refactoring of core files (`index.ts`, `container-runner.ts`, `db.ts`) improves all future agent output.
5. **Proof over trust.** Don't review code line-by-line; verify through automated evidence (test results, curl output, log inspection).
6. **Sandboxing is non-negotiable for untrusted input.** NanoClaw's container architecture already provides this; maintain it.
7. **Exhaustion is real.** Multi-agent sessions drain cognitive bandwidth fast. Plan for it in scope estimates.
