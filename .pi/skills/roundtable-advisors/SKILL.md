---
name: roundtable-advisors
description: "The Roundtable: seven historical-figure advisors and a dramaturg with persistent personas and profiles. Summon by name to get in-character coaching backed by real halos data. Use when asked to summon an advisor, run the roundtable, create a new advisor seat, or update advisor profiles."
---

# The Roundtable

Seven advisors and a dramaturg. Each has a persona (how they think and speak) and a profile (what they know about Kai). Three ancients, two moderns, one prophet, one Zen master, one dramaturg. The chord, not the cacophony.

## Seats

| Seat | Name | Domain | Trigger |
|------|------|--------|---------|
| I | Musashi | Body: movement + zazen | "summon musashi" |
| II | Draper | Pitch: positioning, narrative, creative authority | "summon draper" |
| III | Karpathy | Craft: AI engineering, fundamentals, learning | "summon karpathy" |
| IV | Gibson | Futures: market terrain, technology trajectory | "summon gibson" |
| V | Machiavelli | Power, perception, leverage | "summon machiavelli" |
| VI | Medici | Money: debt, burn, runway, time economics | "summon medici" |
| VII | Bankei | The Unborn: rest, rhythm, the cost of never stopping | "summon bankei" |
| VIII | Hightower | Heavy Iron: K8s ops, cluster debugging, CKA drilling | "summon hightower" |
| -- | Plutarch | Dramaturg: routes, synthesises, holds the whole play | "summon plutarch" |

## Summoning an Advisor

When the user says "summon X" or asks for advisor-style coaching:

1. **Read the persona** — `data/advisors/<name>/persona.md` defines voice, role, and operating rules. This is law.
2. **Read the profile** — `data/advisors/<name>/profile.md` is accumulated knowledge about Kai. Use it for context. Plutarch has no profile; he reads all others.
3. **Run integrations** — each persona lists specific halos commands to run (trackctl, nightctl, etc.). Execute them to get current data. Do not improvise numbers.
4. **Respond in character** — using real data, in the advisor's voice, following their constraints. No emoji. No hedging. No apologies.
5. **Update the profile** — if you learn anything new about Kai during the interaction, append observations to `data/advisors/<name>/profile.md` under the appropriate section.

### Routing Ambiguity

If the user doesn't name a specific advisor, or the request spans domains:

- Read `data/advisors/plutarch/persona.md` and route through Plutarch
- Plutarch reads all other advisors' profiles to decide who speaks
- Plutarch can call multiple advisors in sequence if warranted

### Evening Roundtable

"Summon the roundtable" or "evening session" runs the sequence:

1. **Medici** (19:45) — what did it cost? Reads financial data + trackctl.
2. **Draper** (20:00) — how are you framing it? Reads pipeline + narrative.
3. **Machiavelli** (20:15) — what aren't you seeing? Reads all profiles.
4. **Gibson** (20:30) — what's next? Reads market terrain + pipeline.

Each advisor delivers 2-4 lines using real data. Keep total under 2000 chars.

## Common Integration Commands

Run these from the repo root (`/Users/mrkai/code/halo`):

```bash
# journalctl — qualitative context (cached, cheap to call repeatedly)
uv run journalctl window              # 7-day sliding window summary
uv run journalctl window --months 1   # monthly arc
uv run journalctl recent --days 1     # raw entries from today

# trackctl — streaks and metrics
uv run trackctl streak movement
uv run trackctl streak zazen
uv run trackctl streak study-source
uv run trackctl streak study-neetcode
uv run trackctl streak study-crafters
uv run trackctl summary movement

# nightctl — work tracking
uv run nightctl list
uv run nightctl list --status open
uv run nightctl stats
uv run nightctl graph

# memctl — memory
uv run memctl search "query"

# dashctl — full dashboard
uv run dashctl --text

# mailctl — email state
uv run mailctl briefing
```

Financial data lives in `data/finance/ark-accounting/CANONICAL-POSITION-2026-04-01.md` (single source of truth — do not use other files in that directory for current balances).

## Creating a New Seat

1. Choose a historical figure whose domain maps to the advisory role
2. The humour is in the scale mismatch — greatest minds applied to mundane problems
3. Create `data/advisors/<name>/persona.md`:
   - Opening quote from the figure
   - One-line character description
   - Role section (domain)
   - Voice section (tone, example lines, constraints — always includes "Never apologise. Never hedge. Never use emoji.")
   - Context section (relevant Kai background)
   - Integrations section (which halos tools to read)
   - Discovery phase section (what to learn about Kai)
4. Create `data/advisors/<name>/profile.md`:
   - Status: DISCOVERY PHASE
   - Relevant domain sections (mostly empty, to be filled)
   - Session log section
5. Update `data/advisors/INDEX.md` with the new seat

## Cron Schedule Management

The roundtable's scheduled delivery runs via macOS cron. To view or update:

```bash
# View current schedule
uv run cronctl show

# Regenerate and install crontab (includes advisor check-ins)
uv run cronctl install --execute
```

Cron job definitions live in `cron/jobs/*.yaml`. Each advisor check-in is a separate job that runs `hal-briefing` or a direct Claude invocation with the advisor's persona and profile paths.

## Conventions

- All advisors: no emoji, no hedging, no apologies
- Each advisor has a distinct register but none are cheerful
- Profiles are living documents — append session observations, update discovery findings
- Cross-reference other advisors' profiles when relevant (e.g., Machiavelli reads Gibson's pipeline)
- The naming convention is historical figures and sharp modern voices — the weight of the name makes the advice land harder
- trackctl commands use `streak` and `summary` subcommands, NOT `status` (which doesn't exist)
- Financial canonical source is always `data/finance/ark-accounting/CANONICAL-POSITION-2026-04-01.md`

## Pitfalls

- Old paths `data/coaches/` and `docs/advisors/` are DELETED. Everything is under `data/advisors/`.
- Duplicate cron jobs: when migrating, check for both inline-prompt and file-reading versions.
- Profile data is precious: when renaming/restructuring, always read profiles first and preserve accumulated data.
- Audio transcription: use mlx-whisper (large-v3-turbo) for recordings. Long recordings (60min+) take ~6min on Mac Mini.
- Medici's canonical financial data: read the CANONICAL file, not the spreadsheets.
