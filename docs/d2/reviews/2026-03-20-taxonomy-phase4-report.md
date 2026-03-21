---
title: "Taxonomy Review Phase 4"
category: review
status: active
created: 2026-03-20
---

# Taxonomy Review Phase 4

Date: 2026-03-20

Scope:
- `CHL.TG`
- `CHL.GM`
- `CHL.REG`

## Summary

Phase 4 produced 2 findings.

| Severity | Count |
|----------|-------|
| S1 | 0 |
| S2 | 0 |
| S3 | 2 |
| S4 | 0 |

## Findings

### CHL.GM.02 [TC11] S3

The Gmail poller marks a message ID as processed before `processMessage()` succeeds.

Evidence:
- message IDs are inserted into `processedIds` before processing at `src/channels/gmail.ts:201-205`;
- poll-level errors only increment backoff and do not remove the prematurely claimed ID in `src/channels/gmail.ts:215-229`.

Impact:
- transient fetch/parse/API failures can suppress redelivery of still-unread messages for the rest of the process lifetime;
- recovery depends on process restart rather than the poller itself.

Why `[TC11]`:
- the poller commits the "seen" transition before the message has completed the processing transition.

### CHL.TG.07 [TC12] S3

Before any Telegram JID has been observed or restored, the channel claims ownership of all `tg:` JIDs, and routing picks the first matching channel.

Evidence:
- `ownsJid()` returns `true` for any `tg:` JID when `ownedJids` is empty in `src/channels/telegram.ts:535-540`;
- `findChannel()` returns the first channel whose `ownsJid()` is true in `src/router.ts:47-51`.

Impact:
- first-boot or cold-start routing for Telegram depends on channel registration/order rather than proven chat ownership;
- in multi-bot or pooled configurations, outbound delivery can be attributed to the wrong logical channel until ownership is populated.

Why `[TC12]`:
- the routing decision crosses the channel boundary using a bootstrap assumption instead of an observed ownership fact.

## Coverage Notes

Observed coverage:
- `src/channels/gmail.test.ts` passed.

Coverage problems found during review:
- `src/channels/telegram.test.ts` currently has 15 failures because text-message tests do not initialize the onboarding DB dependency introduced by `getOnboardingState()`; the failures start at `src/channels/telegram.test.ts:170` and the runtime error comes from `src/db.ts:687`.
