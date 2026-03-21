# Halos × Agent-Native Software Taxonomy: Gap Analysis & Expansion Roadmap

**Date:** 2026-03-21
**Author:** HAL, dispatched by Operator
**Provenance:** Cross-referenced against `noopit/docs/research/agent-native-software-taxonomy.md` (2026-03-09)
**Status:** DRAFT — first pass for Operator review

---

## Premise

The agent-native software taxonomy identifies 48 categories of software and asks: what remains when you subtract the interface? Halos is a living answer to that question — a growing suite of CLI modules that perform the irreducible computation directly, with no GUI tax. This document maps every taxonomy category to the halos ecosystem: what's already built, what's missing, and what's worth building next.

Each category is assessed on:

- **Halos status**: `COVERED` (existing module), `PARTIAL` (tangentially addressed), `GAP` (no coverage).
- **Existing module**: Which halos module(s) already serve this category, if any.
- **Proposed module**: What a purpose-built halos module would look like.
- **Tier**: `NOW` (buildable on current infra), `NEXT` (needs modest new capability), `LATER` (requires significant new work).
- **Value signal**: Why this matters for the Operator's specific workflow.

---

## Methodology Note

The original taxonomy's category numbering and section ordering are preserved exactly. If you want to grep-map between the two documents, `### 7.` in this file corresponds to `### 7.` in the taxonomy. Categories where halos has nothing interesting to say get a brief entry. Categories where the mapping is rich get the space they need.

---

## I. Productivity

### 1. Word Processing / Document Creation

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** `memctl` handles atomic note creation (Markdown + YAML frontmatter). `briefings` synthesises structured text output. `reportctl` generates periodic digests. The pipeline is: structured data → Markdown → delivery via channel. No document *rendering* exists — and that's correct. The agent writes structure; Pandoc or LaTeX renders when presentation matters.

**Proposed module:** `docctl` — document assembly from templates.

**What it would do:** Maintain a `templates/docs/` directory of Markdown/LaTeX skeletons (letters, reports, invoices, proposals). `docctl render --template letter --vars vars.yaml` fills the template and renders to PDF via Pandoc. `docctl list` shows available templates. Variables come from structured YAML, not interactive form-filling.

**Tier:** NOW. Pandoc is already available. Templates are files. This is a shell script with a nice CLI wrapper.

**Value signal:** Operator already generates reports and briefings. Formalising the template→render pipeline makes it composable with briefings, mailctl, and nightctl outputs.

---

### 2. Spreadsheets / Data Manipulation

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED (implicitly)

**Existing coverage:** Every halos module that touches structured data (trackctl, nightctl, reportctl, logctl) already operates this way — SQLite stores, Python computations, CLI queries. There is no spreadsheet. This is the taxonomy's point: the agent-native form of a spreadsheet is a database + scripts, and halos was built that way from day one.

**Proposed module:** None. The existing pattern (SQLite per domain + CLI) IS the agent-native spreadsheet. If anything, this validates the architecture.

**Tier:** N/A — already the correct form.

---

### 3. Presentations / Slide Decks

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP

**Proposed module:** Not worth building as a dedicated module. If the Operator needs slides, the workflow is: `briefings` or `reportctl` generates content → Marp or reveal.js renders Markdown to slides → human reviews visual output. A `docctl` (§1) with a slides template covers this.

**Tier:** NOW (via docctl template, not a standalone module).

---

### 4. Email / Messaging

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** COVERED

**Existing coverage:** `mailctl` — inbox snapshot, message reading, search, triage rules, send, folder listing, filter management, briefing integration. Channels (Telegram, Gmail, Slack, Discord) handle messaging. The agent reads and sends messages as structured data. No inbox UI needed.

`mailctl` already provides:
- `mailctl inbox [--unread]` — structured inbox view
- `mailctl triage [--dry-run]` — rule-based inbox processing
- `mailctl summary` — one-liner for briefing integration
- `mailctl send` — compose from stdin

**Gap:** Triage rules are currently static. An LLM-assisted triage layer (classify incoming mail by urgency/topic, auto-label, surface only what needs human attention) would close the remaining gap.

**Proposed enhancement:** `mailctl triage --ai` — pass unread messages through a classification prompt, auto-apply labels, surface only messages requiring human judgment.

**Tier:** NEXT. Requires container agent invocation for classification, which means either an MCP tool or a lightweight SDK call from within mailctl.

---

### 5. Calendar / Scheduling

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** Google Calendar API is available inside agent containers via the `google_workspace` MCP server. `cronctl` manages cron schedules for halos tasks. `nightctl` tracks work items with time-awareness (execution windows, scheduling). But there's no unified calendar abstraction that merges personal calendar events with nightctl tasks and cron jobs into a single queryable timeline.

**Proposed module:** `calctl` — unified schedule view.

**What it would do:** Query Google Calendar via MCP, merge with nightctl items that have deadlines, merge with cronctl scheduled jobs. `calctl today` shows everything happening today. `calctl week` shows the week. `calctl conflicts` detects overlapping commitments. `calctl free --duration 60m` finds open slots. Output as structured text for briefing integration.

**Tier:** NOW. All data sources already exist (Google Calendar MCP, nightctl items, cronctl jobs). This is a read-only aggregation layer.

**Value signal:** Morning briefings already pull from nightctl and cronctl. Adding calendar events completes the picture — the agent can say "you have 3 meetings today, 2 nightctl items due, and a briefing at 7pm" in a single view.

---

### 6. Note-Taking / Knowledge Management

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED

**Existing coverage:** `memctl` — structured memory governance with atomic Markdown notes, YAML frontmatter, decay-based pruning, search, entity linking, index rebuilding. `memory/INDEX.md` is the lookup protocol. `memory/reflections/` is the autonomous journal. This is the taxonomy's ideal form: a directory of Markdown files with metadata, queryable via CLI.

`memctl` provides:
- `memctl new` — create atomic notes with type, tags, entities, confidence, expiry
- `memctl search` — full-text and metadata search
- `memctl prune` — decay-based garbage collection
- `memctl rebuild` — index regeneration
- `memctl stats` — corpus health metrics

**Gap:** Graph analysis. The taxonomy notes that agents can "compute graph metrics (centrality, clustering) directly." memctl doesn't do this yet — it has entity links but no graph traversal or cluster detection.

**Proposed enhancement:** `memctl graph --clusters` — compute note clusters by entity co-occurrence. `memctl graph --orphans` — find unlinked notes. `memctl graph --central` — identify high-centrality notes (knowledge hubs).

**Tier:** NOW. Notes already have entity metadata. Graph computation is networkx over the existing index.

---

### 7. Project Management / Task Tracking

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED

**Existing coverage:** `nightctl` — unified work tracker with Eisenhower matrix (q1-q4), state machine (open→active→done→archived), overnight execution, YAML item files, CLI CRUD. This is exactly the taxonomy's "structured data file with a CLI for CRUD." The Kanban board is replaced by `nightctl graph` (Eisenhower-grouped view).

`nightctl` provides:
- Full state machine: `open → active → done → archived` (plus `blocked`, `deferred`)
- Eisenhower quadrants for prioritisation
- Overnight execution (autonomous work while the Operator sleeps)
- `nightctl graph` — grouped view replacing spatial boards
- YAML item files in `queue/items/` — versionable, diffable, greppable

**Gap:** Dependency tracking between items. The taxonomy mentions this as a core operation. nightctl items are currently independent — there's no "blocked by X" relationship.

**Proposed enhancement:** `nightctl edit <ID> --blocked-by <ID>` — add dependency edges. `nightctl graph --deps` — show dependency DAG. `nightctl ready` — list items whose blockers are all resolved.

**Tier:** NOW. YAML items already have extensible fields. Adding a `blocked_by` list and a graph query is straightforward.

---

## II. Development

### 8. IDEs / Code Editors

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** N/A (out of scope)

The agent already operates this way — bash + text editor + compiler + LSP. NanoClaw's container agents read files, make edits, run tests. This is the canonical example from the taxonomy, and halos doesn't need a module for it because the agent runtime IS the IDE.

---

### 9. Version Control (GUI Clients)

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** N/A (out of scope)

Git is used natively throughout. `agentctl` tracks sessions. Commits are atomic. No GUI needed. The existing infrastructure is the agent-native form.

---

### 10. Database Management (GUI Clients)

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED (implicitly)

Every halos module uses SQLite directly via Python. `db.ts` in the Node.js layer manages 9 tables. Schema introspection is `sqlite3` queries. The agent-native form is exactly what's built.

---

### 11. API Testing (Postman, etc.)

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** N/A (out of scope)

Container agents use `curl`/`httpie` directly. No module needed.

---

### 12. CI/CD Dashboards

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** `halctl smoke` runs infrastructure + agent capability checks. `logctl` aggregates logs. But there's no unified "pipeline health" view that shows: last build status, test results, deploy state, service health.

**Proposed module:** `statusctl` — system health dashboard for the NanoClaw fleet.

**What it would do:** `statusctl` queries: container build status (Docker), service uptime (systemd), recent errors (logctl), agent session health (agentctl), cron job outcomes (cronctl). `statusctl check` returns exit 0 if all green, exit 1 with structured failure details. `statusctl report` generates a health summary for briefing integration.

**Tier:** NOW. All data sources exist. This is aggregation + threshold evaluation.

**Value signal:** `halctl smoke` tests capabilities. `statusctl` monitors ongoing health. Together they cover provisioning and operations.

---

### 13. Container Management

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED

**Existing coverage:** `container-runner.ts` manages Docker lifecycle. `container/build.sh` handles image builds. `halctl` manages fleet provisioning. All CLI-native, no Docker Desktop needed.

---

## III. Creative

### 14. Photo Editing / Image Manipulation

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP

**Proposed module:** Not a dedicated module, but a container skill. Agent containers already have ImageMagick available. For batch operations (resize, watermark, format conversion), the agent composes ImageMagick pipelines. For generative tasks, the AI Gateway provides image generation via `google/gemini-3.1-flash-image-preview`.

**Tier:** NOW (batch ops via existing tools), NEXT (generative image via Gateway integration in container).

---

### 15. Video Editing

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP

**Proposed:** Not a priority. If needed, `ffmpeg` pipelines in container agents. The Operator's workflow doesn't currently involve video production.

**Tier:** LATER.

---

### 16. Audio Editing / Music Production

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP (but adjacent to voice transcription)

**Existing coverage:** Voice transcription (Whisper) is a NanoClaw skill for WhatsApp voice notes. Technical audio processing (`sox`, `ffmpeg`) is available in containers.

**Proposed:** No dedicated module. Audio is taste-territory. The existing transcription pipeline covers the agent-relevant slice.

**Tier:** LATER.

---

### 17. Graphic Design / Illustration

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP

**Proposed:** For diagrams, the agent already writes Mermaid and Graphviz (see §46). For templated design (social cards, OG images), a `docctl` template approach works. Original design is taste-territory — outside halos scope.

**Tier:** NOW (diagrams via existing tools), LATER (templated design via docctl).

---

### 18. 3D Modelling

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP

**Proposed:** Out of scope. The Operator's workflow doesn't involve 3D work.

**Tier:** N/A.

---

### 19. UI/UX Design Tools

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP

**Proposed:** Out of scope for halos modules. The agent generates UI by writing code (React/HTML/CSS) directly — which is the taxonomy's recommended agent-native form. No separate design tool module needed.

**Tier:** N/A.

---

## IV. Communication

### 20. Video Conferencing

**Taxonomy verdict:** IRREDUCIBLE
**Halos status:** GAP (correctly)

The core activity is humans talking to humans. Agent facilitation around the edges — scheduling (calctl §5), transcription, action item extraction — is where halos adds value.

**Proposed enhancement:** Post-meeting processing. If meeting recordings land in Google Drive, a container agent could: transcribe (Whisper or API), extract action items, create nightctl items from them.

**Tier:** NEXT. Requires Drive integration (already available via MCP) + transcription pipeline.

---

### 21. Team Chat (Slack, Teams, Discord)

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** COVERED

**Existing coverage:** NanoClaw's channel system is exactly this. Telegram, Slack, Discord, Gmail — all self-registering channels that process messages as structured data via APIs. The agent participates in team communication via API, not GUI.

---

### 22. Social Media Management

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** X/Twitter integration exists as a NanoClaw skill (post, like, reply, retweet, quote). But there's no scheduling, analytics, or content calendar.

**Proposed module:** `socialctl` — social media operations.

**What it would do:** `socialctl schedule --platform x --text "..." --time "2026-03-22T10:00"` — queue a post. `socialctl analytics --platform x --days 7` — engagement metrics. `socialctl calendar` — view scheduled posts. Content calendar as YAML files (like nightctl items).

**Tier:** NEXT. X API is already integrated. Scheduling is cronctl + a post queue. Analytics requires API queries that aren't currently wired.

**Value signal:** The Operator has indicated interest in YouTube channel monitoring and content workflows. A social presence management layer would compose with that.

---

### 23. CRM (Customer Relationship Management)

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** GAP

**Proposed:** Not a priority for a personal assistant system. If the Operator's workflow shifts toward client management, a lightweight `contactctl` (structured contact notes + interaction log) could be built on the existing memctl pattern.

**Tier:** LATER.

---

## V. System / Infrastructure

### 24. File Management

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED (implicitly)

The agent operates on the filesystem directly. `memctl` manages notes. `nightctl` manages YAML items. `trackctl` manages SQLite stores. Every halos module is a structured layer over filesystem operations.

---

### 25. System Monitoring

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** `logctl` aggregates logs with structured search. `agentctl` tracks agent sessions and detects spin. `halctl smoke` checks infrastructure health. But there's no continuous system metrics collection (CPU, memory, disk, container resource usage).

**Proposed enhancement:** Fold into `statusctl` (§12). `statusctl metrics` — snapshot of host resource usage, container stats, disk pressure. `statusctl watch --interval 60` — poll and alert if thresholds breached. Briefing integration: "Host: 45% disk, 12% CPU, 3 containers running."

**Tier:** NOW. `/proc` parsing + `docker stats` + threshold logic.

---

### 26. Network Management

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** GAP (correctly)

Network management is infrastructure work, not personal assistant territory. The agent can run `ss`, `ip`, `tcpdump` when needed. No dedicated module warranted.

**Tier:** N/A.

---

### 27. Cloud Console

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** GAP

**Proposed:** Not a priority unless the Operator's infrastructure grows beyond a single host. If fleet management expands to cloud instances, `halctl` already has the provisioning primitives. Cloud provider CLIs (`gcloud`, `aws`) compose with existing tooling.

**Tier:** LATER.

---

### 28. Backup / Sync

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** GAP

**Proposed module:** `backupctl` — structured backup policy management.

**What it would do:** `backupctl policy list` — show backup targets and schedules. `backupctl run [--target memory|store|config]` — execute backup for a target. `backupctl verify` — check backup integrity. `backupctl restore --target memory --snapshot 2026-03-20` — restore from snapshot.

Targets: `memory/` (notes corpus), `store/` (SQLite databases), `queue/items/` (nightctl items), `groups/` (per-group CLAUDE.md and config).

**Tier:** NOW. `restic` or `rsync` + cron. The module is a policy layer over existing backup tools.

**Value signal:** The memory corpus (`memory/`) and tracking databases (`store/`) are high-value, low-redundancy data. A structured backup policy prevents catastrophic loss. Currently, git covers text files but not SQLite databases.

---

## VI. Data / Analysis

### 29. Data Visualisation

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** PARTIAL

**Existing coverage:** `dashctl` renders trackctl domains as Rich TUI panels with streak bars, progress indicators, and Eisenhower matrix views. This is terminal-native data visualisation — no browser needed.

**Gap:** Chart generation for briefings or reports. The morning briefing could include a trend chart (streak progress over time, session counts by week) rendered as a small image or ASCII art.

**Proposed enhancement:** `dashctl chart --domain zazen --days 30` — render a sparkline or bar chart (ASCII for terminal, PNG via matplotlib for attachment to briefings).

**Tier:** NOW. matplotlib is a pip install away. ASCII sparklines are trivial.

---

### 30. BI Dashboards

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** COVERED

**Existing coverage:** `dashctl` IS the BI dashboard — an RPG character sheet for personal metrics. `reportctl` generates periodic digests. `briefings` synthesises across all data sources. The composition is: trackctl (raw data) → dashctl (visualisation) → briefings (narrative summary) → channel (delivery).

**Proposed enhancement:** `dashctl --html` — render the dashboard as a static HTML page for browser viewing. Useful when the Operator wants to share progress or review on a screen rather than a terminal.

**Tier:** NOW. Rich can export to HTML. Minimal work.

---

### 31. Statistical Analysis

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** `trackctl` computes streaks, totals, daily averages. `agentctl` computes session stats. `logctl` aggregates error rates. But there's no general-purpose statistical analysis module.

**Proposed enhancement:** `trackctl trends --domain zazen --window 30` — compute trend direction (improving/declining/stable), variance, best/worst days. `trackctl compare --domains zazen,movement` — cross-domain correlation. Feed into briefings: "zazen and movement streaks correlate at r=0.72 — days you meditate, you also exercise."

**Tier:** NOW. scipy/numpy are standard. The data is already in SQLite.

---

### 32. Machine Learning Experiment Tracking

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** GAP (correctly)

Not relevant to the current workflow. If the Operator starts ML work, MLflow or W&B compose with existing tooling via CLI/API.

**Tier:** N/A.

---

## VII. Web / Content

### 33. Web Browsing

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** COVERED

**Existing coverage:** Container agents have browser automation via Playwright/Puppeteer (the `agent-browser` container skill). Headless browsing for data retrieval. Screenshot-based visual interaction via Xvfb. This is exactly the taxonomy's agent-native form.

---

### 34. Web Scraping

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED (implicitly)

Container agents can scrape with `curl`, `httpie`, Playwright. No dedicated module needed — scraping is a tool capability, not a domain.

---

### 35. Content Management

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** `memctl` manages structured content (notes). Channel messages are stored in SQLite. But there's no blog/publication workflow — content creation → review → publish.

**Proposed:** Not a priority as a standalone module. If the Operator starts publishing (blog, newsletter), a `pubctl` module could manage drafts as Markdown files with publication state (draft→review→published) — essentially a content-specific nightctl. But this is speculative.

**Tier:** LATER.

---

### 36. SEO Tools

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** GAP

**Proposed:** Out of scope unless the Operator has web properties that need SEO. `lighthouse` CLI is available for ad-hoc audits.

**Tier:** N/A.

---

## VIII. Finance / Business

### 37. Accounting Software

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** GAP

**Proposed module:** `ledgerctl` — plain-text accounting.

**What it would do:** Wrap `hledger` or `beancount` with a halos-native CLI. `ledgerctl add --account expenses:food --amount 42.50 --payee "Countdown"` — record a transaction. `ledgerctl balance` — balance sheet. `ledgerctl income` — P&L for period. `ledgerctl import --bank anz --csv statement.csv` — import bank statements. Briefing integration: "Spending this week: $342 (food $128, transport $67, misc $147)."

**Tier:** NEXT. hledger is available via package manager. The halos wrapper adds structured input, briefing integration, and bank CSV import rules.

**Value signal:** Personal finance tracking composes naturally with the existing dashboard. A `finances` panel in dashctl alongside zazen streaks and study hours gives the Operator a complete personal metrics view.

---

### 38. Invoicing

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** GAP

**Proposed:** Covered by `docctl` (§1) with an invoice template. `docctl render --template invoice --vars invoice-2026-03.yaml` → PDF → `mailctl send`. No standalone module needed.

**Tier:** NOW (via docctl).

---

### 39. Trading Platforms

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** GAP

**Proposed:** Out of scope unless the Operator trades. API-first trading platforms compose with existing tooling if needed.

**Tier:** N/A.

---

### 40. ERP Systems

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** N/A

Enterprise scope. Not relevant to a personal assistant system.

---

## IX. Consumer

### 41. Music / Media Players

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** GAP

**Proposed:** Media management (library, playlists, queue) is reducible but low-value for halos. The agent can control `mpv` or Spotify via API if needed. A `mediactl` for playlist curation or podcast queue management is conceivable but not a priority.

**Tier:** LATER.

---

### 42. PDF Readers

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED (implicitly)

PDF reading is a NanoClaw skill (`add-pdf-reader`). Container agents extract text via `pdftotext`, process attachments from WhatsApp/Telegram. No GUI needed.

---

### 43. Password Managers

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED (implicitly)

`credential-proxy.ts` handles key substitution for container agents. `.env` files + environment variables manage secrets. `1password-cli` or `pass` compose if needed.

---

### 44. Screenshot / Screen Recording

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED

Container agents capture screenshots via `scrot` in the Xvfb virtual framebuffer. The `agent-browser` skill uses screenshot-based interaction. This is already the taxonomy's agent-native form.

---

## X. Additional Categories

### 45. CAD / Engineering Software

**Taxonomy verdict:** TASTE_REQUIRED
**Halos status:** N/A

Out of scope.

---

### 46. Diagramming / Whiteboarding

**Taxonomy verdict:** MOSTLY_REDUCIBLE
**Halos status:** PARTIAL

**Existing coverage:** Agents write Mermaid and Graphviz definitions in documentation. The system schematic in CLAUDE.md is ASCII art. Diagrams-as-code is already the practice.

**Proposed enhancement:** `docctl diagram --type mermaid --input flow.mmd --output flow.svg` — render diagrams from definition files. Compose with briefings for visual architecture summaries.

**Tier:** NOW. Mermaid CLI (`mmdc`) renders to SVG/PNG.

---

### 47. Virtual Machines / Hypervisors

**Taxonomy verdict:** FULLY_REDUCIBLE
**Halos status:** COVERED

`container-runner.ts` manages Docker containers. `halctl provision` manages fleet instances. This is infrastructure-as-code — the agent-native form.

---

### 48. Gaming

**Taxonomy verdict:** IRREDUCIBLE (playing) / TASTE_REQUIRED (development)
**Halos status:** N/A

Out of scope. Games exist for human entertainment.

---

---

## Synthesis

### Coverage Map

| Verdict | Taxonomy Count | Halos Covered | Halos Partial | Halos Gap |
|---------|---------------|---------------|---------------|-----------|
| FULLY_REDUCIBLE | 22 | 14 | 3 | 5 |
| MOSTLY_REDUCIBLE | 14 | 5 | 5 | 4 |
| TASTE_REQUIRED | 10 | 0 | 2 | 8 |
| IRREDUCIBLE | 2 | 0 | 0 | 2 |
| **Total** | **48** | **19** | **10** | **19** |

**60% of categories are covered or partially covered.** The remaining 40% splits cleanly: half are taste-territory or irreducible (correctly out of scope), half are actionable gaps.

### Actionable Gaps — Prioritised

| Priority | Proposed Module/Enhancement | Category | Tier | Effort |
|----------|---------------------------|----------|------|--------|
| 1 | `calctl` — unified schedule view | §5 Calendar | NOW | ~15 agent-min |
| 2 | `statusctl` — fleet health monitoring | §12 CI/CD + §25 Monitoring | NOW | ~20 agent-min |
| 3 | `backupctl` — structured backup policy | §28 Backup | NOW | ~15 agent-min |
| 4 | nightctl `--blocked-by` dependencies | §7 Project Management | NOW | ~10 agent-min |
| 5 | memctl `graph` — cluster/orphan analysis | §6 Knowledge Management | NOW | ~15 agent-min |
| 6 | trackctl `trends` — statistical analysis | §31 Statistics | NOW | ~10 agent-min |
| 7 | `docctl` — template rendering pipeline | §1 Documents + §38 Invoicing + §46 Diagrams | NOW | ~20 agent-min |
| 8 | dashctl `--html` export | §30 BI Dashboards | NOW | ~5 agent-min |
| 9 | dashctl `chart` — trend visualisation | §29 Data Visualisation | NOW | ~10 agent-min |
| 10 | mailctl `triage --ai` | §4 Email | NEXT | ~25 agent-min |
| 11 | `socialctl` — social media ops | §22 Social Media | NEXT | ~30 agent-min |
| 12 | `ledgerctl` — plain-text accounting | §37 Accounting | NEXT | ~30 agent-min |
| 13 | Meeting → nightctl pipeline | §20 Video Conferencing | NEXT | ~20 agent-min |

### The Pattern

Halos is strongest in the taxonomy's FULLY_REDUCIBLE categories — which makes sense. These are the categories where the agent-native form is data + CLI, and halos was designed precisely for that pattern. The gaps cluster in two areas:

1. **Aggregation layers.** Individual modules are strong but cross-module views are weak. `calctl` (merging calendar + nightctl + cronctl), `statusctl` (merging logctl + agentctl + system metrics), and `dashctl --html` (rendering the dashboard for non-terminal consumption) all address this. The data exists; the unified queries don't.

2. **Financial and operational tools.** `ledgerctl` and `backupctl` represent domains where the Operator has real needs but no halos module yet. These are straightforwardly buildable on existing patterns (SQLite + CLI + briefing integration).

The TASTE_REQUIRED gaps are correctly gaps. Halos doesn't try to do graphic design, video editing, or music production — and shouldn't. The agent handles the reducible computation; the human handles taste.

### Architectural Observation

The taxonomy's Principle 7 — "the filesystem is the workspace" — maps exactly to halos' IPC model (write-then-rename atomicity, filesystem-based message passing, YAML item files, Markdown notes). This is not coincidence. The taxonomy describes what agent-native software looks like in theory; halos is what it looks like in practice.

The composition advantage (Synthesis §4 in the taxonomy) is halos' strongest architectural property. `trackctl` feeds `dashctl` feeds `briefings` feeds channels. `nightctl` feeds `briefings`. `logctl` feeds `statusctl`. `memctl` feeds everything. Each module does one thing, communicates through structured text, and composes with the others. This is McIlroy's 1978 principles applied to a personal agent system, forty-eight years later.

### What This Means for noopit

If noopit's thesis is that 75% of software is reducible to CLI/API operations, halos is Exhibit A for the personal computing domain. The modules that exist prove the thesis works in practice. The gaps that remain are either taste-territory (correctly deferred to humans) or aggregation problems (solvable with the existing architecture).

The tiered roadmap above gives noopit a concrete example of how the taxonomy translates to buildable software: 9 NOW items, 4 NEXT items, and zero items that require architectural rethinking. The agent-native form isn't aspirational — it's the current state, with known extensions.

---

## Provenance

This document cross-references two codebases:
- **Taxonomy source:** `noopit/docs/research/agent-native-software-taxonomy.md` (2026-03-09)
- **Halos source:** `nanoclaw/halos/` modules as of 2026-03-21

Category numbering preserves the taxonomy's ordering for grep-mapping. Tier estimates use the convention from CLAUDE.md: agent-minutes of generation, not wall-clock time.
