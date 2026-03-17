---
id: 20260316-152220-968
title: Daily briefings module shipped
type: decision
tags:
- briefings
- halos
- cron
- telegram
entities:
- hal
- telegram
confidence: high
created: '2026-03-16T15:22:20Z'
modified: '2026-03-16T15:22:20Z'
expires: null
---

Hybrid Python+Claude briefings: gather data via reportctl collectors, synthesise via claude CLI (inherits OAuth), deliver via IPC to Telegram. Morning at 0600, nightly at 2100. cronctl manages the schedule.
