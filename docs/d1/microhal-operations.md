---
title: "microHAL Operations Guide"
category: runbook
status: active
created: 2026-03-17
---

# microHAL Operations Guide

Lessons learned the hard way. 2026-03-17.

## pm2 Cheat Sheet

```bash
npx pm2 list                              # all processes
npx pm2 logs microhal-ben --lines 20      # recent logs
npx pm2 logs microhal-ben                 # live tail (ctrl+c to exit)
npx pm2 delete microhal-ben && \
  cd /home/mrkai/code/halfleet/microhal-ben && \
  npx pm2 start ecosystem.config.cjs      # full restart (clears cached env)
npx pm2 stop microhal-ben                 # freeze (preserves process entry)
npx pm2 start microhal-ben                # thaw
```

**Critical:** `pm2 restart` does NOT reload env vars. You must `pm2 delete` then `pm2 start` to pick up .env or ecosystem config changes.

## Nuclear Reset (clean slate for a microHAL)

When things are weird and you need a fresh start:

```bash
# 1. Kill everything
docker kill $(docker ps --filter "name=nanoclaw-telegram-main" -q) 2>/dev/null
npx pm2 delete microhal-ben

# 2. Clear ALL state
sqlite3 /path/to/microhal/store/messages.db "DELETE FROM messages; DELETE FROM chats; DELETE FROM sessions;"
rm -rf /path/to/microhal/data/sessions/

# 3. Fresh start
cd /path/to/halfleet/microhal-ben
npx pm2 start ecosystem.config.cjs
```

All three steps are required. Missing any one leaves stale state:
- Skip docker kill → old container has cached Claude session
- Skip DB clear → old session ID gets reused
- Skip sessions dir → old `.claude/projects/` context lingers

## Where Things Live

```
halfleet/
  microhal-ben/
    ecosystem.config.cjs          # pm2 config (env vars, startup command)
    nanoclaw/
      CLAUDE.md                   # ROOT — read by humans, NOT by agent
      groups/telegram_main/
        CLAUDE.md                 # GROUP — THIS is what the agent reads
        logs/                     # container logs (one per invocation)
      store/messages.db           # message history, sessions, chats
      data/sessions/              # Claude Code session files (.claude/ mirror)
      memory/                     # memctl notes
      workspace/                  # user's playground
      projects/                   # user's coding projects
```

## The CLAUDE.md Trap

**The agent's CWD is `/workspace/group`, not `/workspace/project`.**

Claude Code reads CLAUDE.md from the current working directory. The container mounts:
- `/workspace/project` → the nanoclaw repo root (read-only)
- `/workspace/group` → the group folder (read-write)

The agent runs from `/workspace/group`. So CLAUDE.md MUST be in `groups/telegram_main/CLAUDE.md`. The root CLAUDE.md is only read if the agent explicitly traverses up, which it doesn't reliably do.

**Rule:** Always copy CLAUDE.md to the group folder. The halctl provisioning script must do this.

## Credential Proxy (Fleet Sharing)

All microHAL containers route API calls through HAL-prime's credential proxy on port 3001.

```
microHAL process → binds own proxy on port 3002+ (unused by containers)
microHAL container → calls host.docker.internal:3001 (prime's proxy)
```

This works because:
- Docker bridge can reach port 3001 (prime's proxy, already open)
- Docker bridge CANNOT reach arbitrary new ports without iptables/sudo
- The `CONTAINER_PROXY_PORT` env var in ecosystem config controls what containers use

If a container gets "Request timed out", check that prime is running (port 3001 must be listening).

## Permission Model

```
LOCKED (444/555, owned by rick):
  CLAUDE.md, .claude/agents/, .claude/commands/
  halos/, src/, container/ (except container/skills → 755/644)

EXEMPT (755/644 — needed by cpSync):
  .claude/skills/, .claude/hooks/, container/skills/

OPEN (full rwx):
  workspace/, projects/, groups/, memory/, data/
```

**Why the exemptions:** container-runner uses `cpSync` to copy skills into session dirs. `cpSync` preserves source permissions. If the source is 444, the destination copy is 444, and the next cpSync call fails trying to overwrite its own read-only copy. Force flag doesn't help with directory permissions.

## Container Lifecycle

1. User sends Telegram message
2. Bot stores message in SQLite
3. Polling loop picks it up, spawns container
4. Container boots, reads CLAUDE.md from `/workspace/group/`
5. Agent SDK calls Claude API via credential proxy (host:3001)
6. Response sent back via IPC → Telegram
7. Container stays alive for 30min idle timeout
8. Subsequent messages reuse warm container (fast)
9. After 30min idle, container dies. Next message = cold start again.

**First message is always slow** (container cold start + npm install check + SDK init). Subsequent messages on warm container are seconds.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No response at all | pm2 process down | `npx pm2 list`, restart if needed |
| "Request timed out" | Proxy unreachable | Check prime is running (`ss -tlnp \| grep 3001`) |
| "No conversation found with session ID" | Stale session | Nuclear reset (see above) |
| EACCES on skills copy | Locked permissions on source | Check container/skills is 755/644 |
| Agent ignores CLAUDE.md | CLAUDE.md not in group folder | Copy to `groups/telegram_main/CLAUDE.md` |
| Agent calls user wrong name | Old messages in DB | Clear messages table |
| Port EADDRINUSE | Two processes on same port | Check ecosystem config proxy port is unique |
