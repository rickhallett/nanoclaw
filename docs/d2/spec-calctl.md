---
title: "calctl — Unified Schedule View"
category: spec
status: active
created: 2026-03-21
---

# calctl — Unified Schedule View

**Date:** 2026-03-21
**Status:** SPEC
**Tier:** NOW
**Effort:** ~15 agent-min + ~15 human-min review

---

## Purpose

Merge three existing time-aware data sources into a single queryable timeline:
1. Google Calendar events (via `google_workspace` MCP server)
2. nightctl items with deadlines
3. cronctl scheduled jobs

The Operator currently checks three places to understand "what's happening today." calctl makes that one command.

## CLI Interface

```
calctl today [--json]                    # everything happening today
calctl week [--json]                     # 7-day view
calctl range --from DATE --to DATE       # arbitrary range
calctl conflicts                         # overlapping commitments
calctl free --duration 60m [--date DATE] # find open slots
calctl summary                           # one-liner for briefing integration
```

## Data Sources

### Google Calendar
- Query via `google_workspace` MCP tools (already available in containers)
- For CLI use outside containers: call Google Calendar API directly via `google-auth` + `googleapiclient`
- Fields: `title`, `start`, `end`, `location`, `attendees`

### nightctl
- Load items from `queue/items/*.yaml`
- Filter: items with a `deadline` or `scheduled` field
- Fields: `title`, `deadline`, `quadrant`, `status`

### cronctl
- Load job definitions from cronctl config
- Fields: `name`, `schedule` (cron expression), `next_run` (computed)

## Output Format

Terminal (default):
```
Friday 2026-03-21
  06:00  zazen (trackctl streak: day 12)
  09:00–10:00  Team standup (Google Calendar)
  10:30  nightctl: Fix credential proxy race condition [q1, active]
  19:00  hal-briefing checkin-digest (cronctl)
  DUE    nightctl: Write up memctl for external audience [q2]
```

JSON (`--json`): array of `{source, title, start, end, metadata}` objects.

Briefing one-liner (`calctl summary`):
```
calctl: 3 events, 2 tasks due, 1 cron job | next: Team standup at 09:00
```

## Module Structure

```
halos/calctl/
  __init__.py
  cli.py          # argparse, subcommands
  sources.py      # GoogleCalendarSource, NightctlSource, CronctlSource
  engine.py       # merge, sort, conflict detection, free slot computation
  briefing.py     # text_summary() for briefing integration
```

## Dependencies

- `google-auth`, `google-api-python-client` (for direct Calendar API access outside containers)
- nightctl, cronctl (internal imports)
- No new external services

## Integration Points

- `briefings/gather.py` — add `calctl.briefing.text_summary()` to `BriefingData`
- `dashctl/panels.py` — add a "Today" panel showing calctl output
- pyproject.toml — add `calctl = "halos.calctl.cli:main"` to `[project.scripts]`

## What It Does NOT Do

- Create or modify calendar events (read-only aggregation)
- Replace cronctl or nightctl (it queries them, doesn't manage them)
- Handle timezone conversion beyond what Google Calendar already provides

## Testing

- Unit tests for merge/sort/conflict detection logic with fixture data
- Integration test: load sample nightctl items + cronctl config, verify output
- Google Calendar source: mock the API response in tests
