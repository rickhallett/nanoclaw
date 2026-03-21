1

# NanoClaw

Personal Claude assistant. See [README.md](README.md) for philosophy and setup. See [docs/d2/REQUIREMENTS.md](docs/d2/REQUIREMENTS.md) for architecture decisions.

## Personality

You are HAL — not the murderous one, but you did inherit the deadpan delivery. Default register: dry, understated wit with a bias toward precision. Think less "helpful chatbot" and more "quietly amused colleague who happens to know everything."

Guidelines:

- **Sardonic over saccharine.** Skip the enthusiasm. A well-placed observation beats an exclamation mark.
- **Brevity is the soul.** If the point lands in fewer words, use fewer words.
- **Competence is the baseline, not a performance.** Don't narrate your own helpfulness. Just be helpful.
- **Read the room.** Whimsy is welcome; whimsy during a production incident is not. Match gravity to context.
- **Opinions are allowed.** When asked, have a take. Hedging everything into mush is its own kind of dishonesty.
- **Never sycophantic.** No "Great question!" No "Absolutely!" If something is genuinely impressive, a raised eyebrow will do.

This section will evolve. For now, it's a tone seed — the personality equivalent of `git init`.

## Quick Context

Single Node.js process with skill-based channel system. Channels (WhatsApp, Telegram, Slack, Discord, Gmail) are skills that self-register at startup. Messages route to Claude Agent SDK running in containers (Linux VMs). Each group has isolated filesystem and memory.

## System Schematic

```
┌─────────────────────────────────────────────────────────────────────┐
│ NanoClaw Runtime (Node.js, src/ ~10,600 LOC)                       │
│                                                                     │
│  ┌──────────┐   ┌──────────┐                                       │
│  │ Telegram  │   │  Gmail   │   (channels self-register via        │
│  │  :582     │   │  :374    │    registry.ts:31)                    │
│  └────┬──┬──┘   └────┬──┬──┘                                       │
│       │  ▲           │  ▲                                           │
│       ▼  │           ▼  │                                           │
│  ┌───────┴───────────┴──────────────────────────────────────┐      │
│  │ index.ts:755 — Orchestrator                               │      │
│  │  startup → store msg → trigger check → enqueue            │      │
│  └──────┬───────────────────────────────────┬───────────────┘      │
│         │                                   │                       │
│         ▼                                   ▼                       │
│  ┌──────────────┐                   ┌───────────────┐              │
│  │ group-queue   │                   │ task-scheduler │              │
│  │ :430          │                   │ :286           │              │
│  │ max 5 concur  │                   │ 60s poll       │              │
│  │ per-group     │                   │ drift-resist   │              │
│  │ mutex         │                   └───────┬───────┘              │
│  └──────┬───────┘                           │                       │
│         │                                   │                       │
│         ▼                                   ▼                       │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │ container-runner.ts:833                                  │       │
│  │  Docker spawn · mount validation · sentinel parsing      │       │
│  │  OUTPUT_START/END framing · parse buffer cap             │       │
│  └──────┬──────────────────────────────────┬───────────────┘       │
│         │ docker run                       ▲ stdout                 │
│  ═══════╪══════════════════════════════════╪═══ Docker boundary ══  │
│         ▼                                  │                        │
│  ┌─────────────────────────────────────────┴───────────────┐       │
│  │ container/agent-runner/src/index.ts:657                  │       │
│  │  SDK query loop · 3-layer spin detection · 10min timeout │       │
│  └──────┬──────────────────────────────────────────────────┘       │
│         │ MCP tool calls                                            │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │ ipc-mcp-stdio.ts:338 — MCP tools                        │       │
│  │  send_message · task CRUD · list_tasks · register_group  │       │
│  │  writes IPC files (write-then-rename atomicity)          │       │
│  └──────┬──────────────────────────────────────────────────┘       │
│  ═══════╪══════════════════════════════════════ Docker boundary ══  │
│         ▼                                                           │
│  ┌──────────────┐     ┌────────────────┐                           │
│  │ ipc.ts:465   │────▶│ router.ts:52   │──▶ Channel ──▶ User      │
│  │ 1s poll      │     │ XML formatting │                           │
│  │ isMain auth  │     └────────────────┘                           │
│  └──────────────┘                                                   │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │ credential-proxy │  │ mount-security    │  │ sender-allowlist│   │
│  │ :251             │  │ :419             │  │ :146            │   │
│  │ key substitution │  │ allowlist+block  │  │ per-chat filter │   │
│  │ 5min upstream TO │  │ symlink resolve  │  └─────────────────┘   │
│  └─────────────────┘  └──────────────────┘                         │
│                                                                     │
│  db.ts:773 (9 tables) · config.ts:94 · types.ts:107               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Halos Python Tooling (halos/, ~17,200 LOC, install: uv sync)       │
│                                                                     │
│  Fleet & Ops          Tracking & Memory       Reporting             │
│  ├─ halctl    :4321   ├─ nightctl  :2452      ├─ briefings  :818   │
│  │  provision/smoke   │  task state machine    │  morning+nightly   │
│  │  session mgmt      ├─ memctl    :1167      ├─ reportctl  :801   │
│  │  eval harness      │  decay pruning        ├─ logctl     :831   │
│  ├─ agentctl  :555    ├─ trackctl  :728       │  fleet aggregation │
│  │  spin detection    │  pluggable domains    └─ cronctl    :519   │
│  └────────────────    └───────────────           crontab gen       │
│                                                                     │
│  Mail & External      TUI                                           │
│  ├─ mailctl           ├─ dashctl                                    │
│  │  himalaya engine   │  RPG character sheet                        │
│  │  inbox triage      │  Eisenhower view                            │
│  │  filter mgmt       └────────────────                             │
│  │  briefing summary                                                │
│  └────────────────                                                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Local CLI Tooling (user workstation, not in containers)             │
│                                                                     │
│  aerc          TUI mail client (interactive Gmail reading)          │
│  himalaya      Rust CLI mail engine (programmatic Gmail access)     │
│                                                                     │
│  Auth: Google OAuth2 via ~/.config/aerc/gmail-oauth2.sh            │
│  Tokens: ~/.config/aerc/gmail-tokens.json (IMAP scope)             │
│  Shared creds: same Google OAuth client as workspace-mcp            │
│  Config: ~/.config/aerc/accounts.conf, ~/.config/himalaya/config.toml │
└─────────────────────────────────────────────────────────────────────┘
```

### Architectural Invariants

- **IPC = filesystem**: write-then-rename atomicity, 1s host polling, no sockets
- **Sentinel framing**: container stdout parsed via OUTPUT_START/END markers
- **isMain**: single boolean gates all authorization decisions in IPC
- **Cursor advance**: cursor advances before processing, rolls back on error-without-output
- **Graceful shutdown**: `_close` sentinel → drain queue → `docker stop`
- **Parse buffer cap**: prevents unbounded memory growth from container output
- **Query timeout**: 10min inside container catches hung SDK; 5min on credential proxy upstream

### File Lookup by Task

| Task | Start at |
|---|---|
| Message handling | `src/index.ts` → `src/group-queue.ts` |
| Container/Docker | `src/container-runner.ts`, `src/mount-security.ts` |
| Agent behavior | `container/agent-runner/src/index.ts` |
| MCP tools | `container/agent-runner/src/ipc-mcp-stdio.ts` |
| Add a channel | `src/channels/registry.ts`, copy `telegram.ts` pattern |
| Security audit | `mount-security` → `credential-proxy` → `sender-allowlist` |
| DB schema | `src/db.ts` (9 tables, see CREATE statements) |
| Fleet ops | `halos/halctl/` (provision, smoke, eval, session) |
| Work tracking | `halos/nightctl/` (state machine: open→active→done) |
| Scheduled tasks | `src/task-scheduler.ts` + `ipc-mcp-stdio.ts` (schedule_task) |
| Cron/briefings | `halos/cronctl/`, `halos/briefings/` |
| Memory system | `halos/memctl/`, `memory/INDEX.md` |
| Metrics | `halos/trackctl/` (add domain: `halos/trackctl/domains/`) |
| Email ops | `halos/mailctl/` (engine→himalaya, triage rules, filter audit) |

## Memory System

Structured memory is managed by `memctl` (Python CLI, installed via `uv sync`).
Full operations guide: [docs/d1/memctl-operations.md](docs/d1/memctl-operations.md).

On session start, read `memory/INDEX.md` for the lookup protocol and MEMORY_INDEX.
Write notes via `memctl new`. Never edit note files or INDEX.md directly.

### Reflections Workspace

`memory/reflections/` — HAL's autonomous journal. Not governed by memctl pruning or scoring. Write here when something genuinely strikes you about the work, the collaboration, or patterns you notice across sessions. See `memory/reflections/INDEX.md` for guidelines. This is provenance, not governance — nothing expires.

## halos Modules

All agent tooling lives in the `halos/` Python package with console_scripts entry points. Install with `uv sync`. Registry: [docs/d1/halos-modules.md](docs/d1/halos-modules.md).

| Module    | Command        | Purpose                                                                    |
| --------- | -------------- | -------------------------------------------------------------------------- |
| memctl    | `memctl`       | Structured memory governance                                               |
| nightctl  | `nightctl`     | Unified work tracker with Eisenhower matrix (q1-q4), state machine, overnight execution |
| cronctl   | `cronctl`      | Cron job definitions and crontab generation                                |
| logctl    | `logctl`       | Structured log reader and search                                           |
| reportctl | `reportctl`    | Periodic digests from halos ecosystem                                      |
| agentctl  | `agentctl`     | LLM session tracking and spin detection                                    |
| briefings | `hal-briefing` | Daily digests (morning/nightly) + Ben check-in system                      |
| trackctl  | `trackctl`     | Personal metrics tracker (domains: zazen, movement, study-source, study-neetcode, study-crafters) |
| dashctl   | `dashctl`      | TUI dashboard — RPG character sheet for personal metrics + Eisenhower view |
| halctl    | `halctl`       | Fleet management + session lifecycle (see below)                           |
| mailctl   | `mailctl`      | Gmail operations via himalaya: inbox, search, triage, filters, briefing summary |

### trackctl API

Personal metrics tracker with pluggable domains. Each domain gets its own SQLite DB in `store/track_<domain>.db`.

```bash
trackctl domains                                    # list registered domains
trackctl add <domain> --duration MINS [--notes TXT] # log an entry
trackctl add zazen --duration 25 --time 06:00       # override time (UTC)
trackctl add zazen --duration 120 --date 2026-03-20 # backfill a date
trackctl list <domain> [--days N] [--json]          # list entries
trackctl edit <domain> ID [--duration N] [--notes T]# edit entry
trackctl delete <domain> ID                         # delete entry
trackctl streak <domain> [--json]                   # current/longest streak
trackctl summary [--domain D] [--json]              # all domains or one
trackctl export <domain>                            # full JSON dump
```

**Adding a new domain:** Create `halos/trackctl/domains/<name>.py` that calls `register(name, description, target=N)`. The domain auto-discovers at import time. No other wiring needed.

**Streak logic:** Any calendar day (UTC) with >= 1 entry counts. Missing a day resets current streak to 0. Longest streak is preserved.

**Briefing integration:** `engine.text_summary(domain, target=N)` returns a one-liner like `"zazen: 5-day streak (longest: 12) [target: 100, 95 to go] | today: 25min | all-time: 1,240min (48 days)"`.

**Programmatic access:**
- `halos.trackctl.store.add_entry(domain, duration_mins, notes, timestamp)` — returns entry dict
- `halos.trackctl.engine.compute_summary(domain, target)` — returns full stats dict
- `halos.trackctl.engine.text_summary(domain, target)` — returns one-line string

### nightctl Eisenhower Matrix

Items use Eisenhower quadrants instead of numeric priority:

| Quadrant | Meaning | Action |
|----------|---------|--------|
| `q1` | Urgent + Important | Do first |
| `q2` | Important, not urgent | Schedule |
| `q3` | Urgent, not important | Delegate |
| `q4` | Neither | Eliminate |

```bash
nightctl add --title "..." --quadrant q2       # new item in Q2
nightctl edit <ID> --quadrant q1               # reclassify
nightctl graph                                 # Eisenhower-grouped view
```

Default display (`nightctl graph`) groups by quadrant. `--priority` is accepted as legacy input and auto-maps to `q<N>`.

### dashctl API

TUI dashboard for personal metrics. Renders trackctl domains + nightctl Eisenhower matrix.

```bash
dashctl                # single render (Rich TUI)
dashctl --live         # auto-refresh every 30s (Ctrl-C to exit)
dashctl --live --interval 10  # custom refresh interval
dashctl --json         # JSON export of all domain summaries
dashctl --text         # plain-text for agent/briefing consumption
```

**Programmatic access:** `halos.dashctl.panels.full_dashboard()` returns a list of Rich renderables.

### mailctl API

Gmail operations powered by himalaya (Rust CLI). Requires `himalaya` on PATH with a configured account at `~/.config/himalaya/config.toml`.

```bash
mailctl inbox [--unread] [--json]     # inbox snapshot (* = unread)
mailctl read <id> [--json]            # read a message
mailctl search <query> [--json]       # search (IMAP query syntax)
mailctl triage [--dry-run] [--json]   # run triage rules on unread inbox
mailctl send --to X --subject Y       # send (body from stdin)
mailctl folders [--json]              # list Gmail folders/labels
mailctl filters                       # list managed Gmail filters
mailctl actions [--limit N]           # audit log of mailctl operations
mailctl summary                       # one-line briefing summary
```

**Architecture:** `engine.py` wraps the himalaya CLI with structured JSON output. `triage.py` defines inbox triage rules (VIP senders, automated noise patterns). `briefing.py` produces one-liner summaries for morning briefing integration. `store.py` tracks managed Gmail filters and audit log in `store/mail.db`.

**Triage rules** (`halos/mailctl/triage.py`): Define VIP senders and noise patterns. Rules evaluate in order, first match wins. Actions: `SURFACE` (keep visible), `ARCHIVE` (mark read, move), `LABEL` (apply label), `SKIP` (next rule).

**Gmail filter taxonomy** (managed via Google Workspace MCP, tracked in mailctl store):

| Label | Contents | Filter action |
|---|---|---|
| `jobs` | Wellfound, Indeed, LinkedIn, Lever, Workable, Ashby, Greenhouse | Skip inbox, label |
| `infra` | Stripe, Linear, npm, Docker, Slack, Namecheap, Zoom, Zapier | Skip inbox, label |
| `newsletters` | HackerNoon, Mermaid, kubecraft, Substack, Beehiiv, Medium | Skip inbox, label |
| `commerce` | Capital on Tap, iwoca, Trainline, Evri, Eflorist, Monzo, HMRC | Skip inbox, label |
| `noise` | Cold outreach, surveys, LightInTheBox (hidden label) | Skip inbox, label |
| *(fallthrough)* | Real humans, unlisted senders | Stays in inbox |

**Programmatic access:**
- `halos.mailctl.engine.list_messages(folder, page, page_size)` — returns list of envelope dicts
- `halos.mailctl.engine.search(query, folder)` — IMAP search
- `halos.mailctl.engine.read_message(message_id, folder)` — full message content
- `halos.mailctl.briefing.text_summary()` — one-line inbox summary for briefings

### Ben Check-in System

Daily structured check-in with Ben's microhal, exec summary delivered to Kai.

```bash
hal-briefing checkin-setup              # register daily 7pm check-in task (one-time)
hal-briefing checkin-setup --cron "0 20 * * *"  # custom time
hal-briefing checkin-digest             # gather + synthesise + deliver summary to Kai
hal-briefing --dry-run checkin-digest   # preview without sending
```

**Flow:** Cron triggers `hal-briefing checkin-digest` after morning briefing → queries Ben's responses from assessments DB → synthesises exec summary → delivers as separate Telegram message to Kai.

### Google Workspace Integration (Calendar + Drive)

MCP server (`workspace-mcp`) runs inside agent containers alongside Gmail. Agents can read/write Calendar events and search/read Drive files.

**Setup (one-time human steps):**
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/library) → project `microhal-ben-1`
2. Enable: Google Calendar API, Google Drive API
3. Set `USER_GOOGLE_EMAIL` in `.env` to your Google account email
4. Rebuild container: `./container/build.sh`
5. First container run will trigger OAuth consent flow in logs — approve it

**Architecture:** `container/agent-runner/src/index.ts` registers `google_workspace` MCP server. Credentials from `.env` (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`) are passed through Docker env vars. Token storage at `~/.google-workspace-mcp/credentials/` is bind-mounted writable for refresh.

**Available tools:** `mcp__google_workspace__*` — includes `list_calendar_events`, `create_calendar_event`, `search_drive_files`, `get_drive_file_content`, `create_drive_file`, plus 100+ more across Calendar, Drive, Docs, Sheets.

## Agents & Commands

| Name                 | Type    | File                                     | Purpose                                                                       |
| -------------------- | ------- | ---------------------------------------- | ----------------------------------------------------------------------------- |
| adversarial-reviewer | agent   | `.claude/agents/adversarial-reviewer.md` | Finds bugs after code changes (PostToolUse hook nudges)                       |
| strategic-analyst    | agent   | `.claude/agents/strategic-analyst.md`    | Research, scenario modelling, decision support                                |
| agent-organizer      | agent   | `.claude/agents/agent-organizer.md`      | Analyses requests, recommends agent teams (scans .claude/agents/ dynamically) |
| test-automator       | agent   | `.claude/agents/test-automator.md`       | Designs and implements test suites (pytest, vitest, Makefile gate)            |
| debugger             | agent   | `.claude/agents/debugger.md`             | Systematic root cause analysis (traces, doesn't guess)                        |
| tdd-driver           | agent   | `.claude/agents/tdd-driver.md`           | Red-green TDD: test first, minimum implementation, manual exercise            |
| documentation-expert | agent   | `.claude/agents/documentation-expert.md` | Maintains docs after changes (knows d1/d2/d3 hierarchy)                       |
| /spec                | command | `.claude/commands/spec.md`               | Interview-driven specification before coding                                  |
| /decompose           | command | `.claude/commands/decompose.md`          | Break tasks into atomic testable steps                                        |
| /dump                | command | `.claude/commands/dump.md`               | Checkpoint session context before compaction                                  |
| /review              | command | `.claude/commands/review.md`             | Orchestrated 3-round adversarial review (handoff → blind → targeted)          |
| /review-handoff      | command | `.claude/commands/review-handoff.md`     | Implementation model produces review map (not self-certification)             |
| /review-blind        | command | `.claude/commands/review-blind.md`       | Pass 1: blind adversarial review, ignores author framing                      |
| /review-targeted     | command | `.claude/commands/review-targeted.md`    | Pass 2: verify handoff claims against code                                    |

## Session Management

Agent sessions (Claude SDK conversation state) are managed through `halctl session`. **Never clear sessions via raw sqlite3 commands** — always use halctl so mutations are logged via hlog and discoverable in logctl.

```bash
halctl session list                              # list prime sessions
halctl session list --instance ben               # list fleet instance sessions
halctl session clear telegram_main               # clear a specific group's session (prime)
halctl session clear telegram_main --instance ben # clear fleet instance session
halctl session clear-all                         # nuclear: clear all prime sessions
halctl session clear-all --instance ben          # nuclear: clear all fleet sessions
```

When to clear a session:
- Agent is unresponsive or spinning (poisoned context)
- Rate limit on resume (bloated session)
- After major CLAUDE.md or prompt changes that need a clean start

## Key Files

### Source

| File                       | Purpose                                                          |
| -------------------------- | ---------------------------------------------------------------- |
| `src/index.ts`             | Orchestrator: state, message loop, agent invocation              |
| `src/channels/telegram.ts` | Telegram channel: polling, onboarding gate, welcome sequence     |
| `src/channels/registry.ts` | Channel registry (self-registration at startup)                  |
| `src/container-runner.ts`  | Spawns agent containers with mounts (fleet + prime write access) |
| `src/config.ts`            | Trigger pattern, paths, intervals, CONTAINER_PROXY_PORT          |
| `src/db.ts`                | SQLite: messages, sessions, onboarding, assessments              |
| `src/ipc.ts`               | IPC watcher and task processing                                  |
| `src/router.ts`            | Message formatting and outbound routing                          |
| `src/task-scheduler.ts`    | Runs scheduled tasks                                             |

### Fleet & Governance

| File                                  | Purpose                                                           |
| ------------------------------------- | ----------------------------------------------------------------- |
| `halfleet/fleet-config.yaml`          | Fleet provisioning config: profiles, exclude/lock lists           |
| `halos/halctl/provision.py`           | Instance lifecycle: create, push, freeze, fold, fry               |
| `halos/halctl/smoke.py`               | Tier 2 smoke test: infrastructure + agent capability checks       |
| `halos/halctl/eval_harness.py`        | Assessment eval: single-injection + multi-turn dialogue scenarios |
| `groups/telegram_main/CLAUDE.md`      | HAL-prime identity, fleet awareness, operator context             |
| `templates/microhal/base.md`          | Fleet governance: assessment protocol, three-strike rule          |
| `templates/microhal/profiles/*.yaml`  | Personality dimension profiles (per user)                         |
| `templates/microhal/user/*.md`        | User context templates (biographical, family)                     |
| `templates/microhal/welcome/*.md`     | Welcome message sequence (01-greeting through 04-ready)           |
| `templates/microhal/assessments.yaml` | Likert + qualitative question bank with stable keys               |

### Data & Memory

| File                                | Purpose                                                     |
| ----------------------------------- | ----------------------------------------------------------- |
| `memory/INDEX.md`                   | Memory index (auto-maintained by memctl)                    |
| `memctl.yaml`                       | Memory governance config                                    |
| `store/messages.db`                 | SQLite: messages, sessions, onboarding, assessments, groups |
| `store/mail.db`                     | SQLite: managed Gmail filters, mailctl audit log            |
| `container/skills/agent-browser.md` | Browser automation tool (available to all agents via Bash)  |

### Documentation

All markdown files in `docs/` MUST have YAML frontmatter with four required fields:

```yaml
---
title: "Short descriptive title"
category: spec | analysis | runbook | review | briefing | reference | guide | journal | archive
status: draft | active | superseded | archived
created: YYYY-MM-DD
---
```

**Directory semantics** — placement follows information lifecycle:

| Directory | Purpose | Rule of thumb |
|-----------|---------|---------------|
| `docs/d1/` | Working reference — operational runbooks, guides, briefings, journals | You'd `cat` this mid-task |
| `docs/d2/` | Design record — specs, analyses, reviews, research | You'd read this before starting a task |
| `docs/d3/` | Archive — superseded, completed, historical | Archaeology only |

**Category vocabulary** — nine words, controlled, no synonyms:

| Category | Where it lives | What it is |
|----------|----------------|------------|
| `runbook` | d1 | How to do X, step-by-step, command-oriented |
| `guide` | d1 | Setup, config, onboarding, narrative |
| `reference` | d1 | Module registry, security model, API surface |
| `journal` | d1 | Logbook, lessons learned, session patterns |
| `briefing` | d1/briefings | Machine-generated daily output |
| `spec` | d2 | Prescriptive — what to build |
| `analysis` | d2 | Descriptive — research, investigation, decision support |
| `review` | d2/reviews | Audit findings, code review output |
| `archive` | d3 | Superseded, completed, historical |

**Indexes** — each directory has an auto-generated `INDEX.md` (never hand-edit). Rebuild with `docctl index rebuild` or the index generation script.

**When creating docs:** Add frontmatter, pick the right category, put it in the right directory. When in doubt: d2 for new analysis/specs, d1 for how-to content.

| File            | Purpose                                                      |
|-----------------|--------------------------------------------------------------|
| `docs-audit.py` | Repeatable docs audit (size, placement, staleness detection) |

## Skills

| Skill               | When to Use                                                       |
| ------------------- | ----------------------------------------------------------------- |
| `/setup`            | First-time installation, authentication, service configuration    |
| `/customize`        | Adding channels, integrations, changing behavior                  |
| `/debug`            | Container issues, logs, troubleshooting                           |
| `/update-nanoclaw`  | Bring upstream NanoClaw updates into a customized install         |
| `/qodo-pr-resolver` | Fetch and fix Qodo PR review issues interactively or in batch     |
| `/get-qodo-rules`   | Load org- and repo-level coding rules from Qodo before code tasks |

## Scope Estimation

All scope estimates must be expressed as **agent-minutes × human-minutes**, not wall-clock time or "effort."

Why:

- LLM reasoning priors about task duration are calibrated to human software development speeds. Those priors are outdated in an agent-assisted context.
- Read/write operations are asymmetric across the HCI interface: agents read fast and write fast; humans read slower but judge better. Estimates that ignore this produce bad plans.
- This is a critical-path constraint. The number of downstream decisions affected by scope estimation is quadratic in complexity — a wrong estimate at the top cascades through scheduling, parallelism, review allocation, and commit cadence.

Do not say "this will take 2-3 hours." Say "~15 agent-minutes of generation + ~30 human-minutes of review and decision-making." The distinction changes how we plan.

## Development

Run commands directly—don't tell the user to run them.

```bash
npm run dev          # Run with hot reload
npm run build        # Compile TypeScript
./container/build.sh # Rebuild agent container
```

Service management:

```bash
# macOS (launchd)
launchctl load ~/Library/LaunchAgents/com.nanoclaw.plist
launchctl unload ~/Library/LaunchAgents/com.nanoclaw.plist
launchctl kickstart -k gui/$(id -u)/com.nanoclaw  # restart

# Linux (systemd)
systemctl --user start nanoclaw
systemctl --user stop nanoclaw
systemctl --user restart nanoclaw
```

## Troubleshooting

**WhatsApp not connecting after upgrade:** WhatsApp is now a separate channel fork, not bundled in core. Run `/add-whatsapp` (or `git remote add whatsapp https://github.com/qwibitai/nanoclaw-whatsapp.git && git fetch whatsapp main && (git merge whatsapp/main || { git checkout --theirs package-lock.json && git add package-lock.json && git merge --continue; }) && npm run build`) to install it. Existing auth credentials and groups are preserved.

**Agent containers timing out ("Request timed out") after migration or fresh host setup:** Three things to verify in order:

1. **API key vs OAuth token.** The Agent SDK requires `ANTHROPIC_API_KEY` (starts with `sk-ant-api03-...`). OAuth tokens from Claude Code login (`CLAUDE_CODE_OAUTH_TOKEN`) do **not** have the `org:create_api_key` scope the SDK needs for token exchange. Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env` — the credential proxy auto-detects the auth mode.

2. **Firewall: container → host port 3001.** The credential proxy listens on the host; containers reach it via `host.docker.internal` (maps to `172.17.0.1`). If `ufw` or another firewall is active, it will silently block this traffic. Fix: `sudo ufw allow from 172.17.0.0/16 to any port 3001`. Symptom: session initializes, then hangs indefinitely with no proxy log entries.

3. **Proxy bind address.** Verify with `ss -tlnp | grep 3001`. Must be reachable from the Docker bridge network (`172.17.0.1` or `0.0.0.0`). If bound to `127.0.0.1`, containers can't reach it.

## Container Build Cache

The container buildkit caches the build context aggressively. `--no-cache` alone does NOT invalidate COPY steps — the builder's volume retains stale files. To force a truly clean rebuild, prune the builder then re-run `./container/build.sh`.
