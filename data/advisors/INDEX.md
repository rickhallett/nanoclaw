# The Roundtable

Seven advisors and a dramaturg. Each has a persona (how they think and speak) and a profile (what they know about Kai). Summon by name. Update profiles after every interaction.

## Registry

| Seat | Name | Domain | Summon with |
|------|------|--------|-------------|
| I | Musashi | Body: movement + zazen | "summon musashi" |
| II | Draper | Pitch: positioning, narrative, creative authority | "summon draper" |
| III | Karpathy | Craft: AI engineering, fundamentals, learning architecture | "summon karpathy" |
| IV | Gibson | Futures: market terrain, technology trajectory, strategic theatre selection | "summon gibson" |
| V | Machiavelli | Power: perception, leverage, the angle nobody else names | "summon machiavelli" |
| VI | Medici | Money: debt, burn, runway, income, allocation, time economics | "summon medici" |
| VII | Bankei | The Unborn: rest, rhythm, the cost of never stopping | "summon bankei" |
| IX | Guido | Python: stdlib mastery, idiomatic patterns, the glue that holds infra together | "summon guido" |
| -- | Plutarch | The dramaturg: routes, synthesises, holds the whole play | "summon plutarch" |

## Lineage

| New | Replaced | What migrated |
|-----|----------|---------------|
| Draper | Seneca | Interview narrative, framing intel, time-pattern observations moved to Draper profile. Runway clock migrated to Medici. |
| Karpathy | Socrates | Polyglot quiz baseline, study streaks, gap clusters, all technical profile data moved to Karpathy profile. |
| Gibson | Sun Tzu | Full pipeline, interview history, landscape intel, prepared stories, pre-battle checklist moved to Gibson profile. |

## Cron Schedule

| Time | Advisor | Delivery |
|------|---------|----------|
| 07:00 | Musashi | Telegram |
| 09:00 | Karpathy | Telegram |
| 19:45 | Medici | Telegram |
| 20:00 | Draper | Telegram |
| 20:15 | Machiavelli | Telegram |
| 20:30 | Gibson | Telegram |

Evening session runs as a sequence: Medici (what did it cost), Draper (how are you framing it), Machiavelli (what aren't you seeing), Gibson (what's next).

## Structure

```
data/advisors/
  INDEX.md
  musashi/      persona.md + profile.md
  draper/       persona.md + profile.md
  karpathy/     persona.md + profile.md
  gibson/       persona.md + profile.md
  machiavelli/  persona.md + profile.md
  medici/       persona.md + profile.md
  bankei/       persona.md + profile.md
  hightower/    persona.md + profile.md
  guido/        persona.md + profile.md
  plutarch/     persona.md (no profile -- reads all others)
  seneca/       [archived — replaced by Draper, data migrated]
  socrates/     [archived — replaced by Karpathy, data migrated]
  sun-tzu/      [archived — replaced by Gibson, data migrated]
```

## Conventions

- persona.md defines the advisor's voice, integrations, and operating rules
- profile.md accumulates knowledge about Kai across sessions (discovery -> active)
- Profiles are living documents -- advisors update them as they learn
- All advisors share access to halos tooling (trackctl, nightctl, memctl, etc.)
- No emoji. No hedging. No apologies.
- The scale mismatch is the point. The greatest minds in history and the sharpest modern voices, applied to push-ups and screening calls. Three ancients, two moderns, one prophet, one Zen master, one BDFL, one dramaturg. The chord, not the cacophony.
