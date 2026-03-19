---
id: 20260319-151037-776
title: Telegram polling watchdog — fix zombie root cause
type: decision
tags:
- fleet
- telegram
- bug
confidence: high
created: '2026-03-19T15:10:37Z'
modified: '2026-03-19T15:10:37Z'
expires: null
---

Root cause identified 2026-03-19: grammY long-poll connections silently stall on Linux. dns.setDefaultResultOrder('ipv4first') in telegram.ts is insufficient. Idle bots die, active ones survive. Fix: Option A — add internal watchdog timer in TelegramChannel that tracks last poll response and forces reconnect if stale. Option B (safety net) — auto-restart in health cron. Option B is being implemented now. Option A is HIGH PRIORITY for when Rick is back at terminal — he wants to write the watchdog logic himself as part of daily src reading. Files to modify: src/channels/telegram.ts (watchdog), halos/halctl/health.py (auto-restart).
