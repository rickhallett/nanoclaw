# NanoClaw Migration Cutover Guide

Target: `100.83.133.110` (Tailscale)
Source: current machine
Date prepared: 2026-03-21

Everything is pre-staged on the target. Follow these steps in order.

## 1. Stop Source (this machine)

```bash
# Stop nanoclaw service
systemctl --user stop nanoclaw

# Stop fleet instances (if running)
pm2 stop all

# Verify nothing is running
systemctl --user status nanoclaw
docker ps  # should show no nanoclaw containers
```

## 2. Final Sync (catch any changes since initial transfer)

```bash
# From this machine — sync any state changes since the transfer
rsync -avz --exclude node_modules --exclude dist --exclude .venv \
  --exclude '*.pyc' --exclude __pycache__ \
  /home/mrkai/code/nanoclaw/ \
  mrkai@100.83.133.110:/home/mrkai/code/nanoclaw/

# Fleet (if applicable)
rsync -avz --exclude node_modules --exclude dist --exclude .venv \
  /home/mrkai/code/halfleet/ \
  mrkai@100.83.133.110:/home/mrkai/code/halfleet/
```

## 3. Start Target

SSH into the target or run from here:

```bash
ssh mrkai@100.83.133.110

# Ensure logs directory exists
mkdir -p /home/mrkai/code/nanoclaw/logs

# Start nanoclaw
systemctl --user start nanoclaw

# Verify it's running
systemctl --user status nanoclaw
# Look for "Active: active (running)"

# Check logs for startup
tail -f /home/mrkai/code/nanoclaw/logs/nanoclaw.log
# Wait for "Connected to Telegram" or similar
```

## 4. Start Fleet (if using multi-agent)

```bash
export PATH=$HOME/.npm-global/bin:$PATH

# Start each fleet instance
cd /home/mrkai/code/halfleet
pm2 start microhal-ben/ecosystem.config.cjs
pm2 start microhal-dad/ecosystem.config.cjs
pm2 start microhal-mum/ecosystem.config.cjs
pm2 start microhal-gains/ecosystem.config.cjs
pm2 start microhal-money/ecosystem.config.cjs

# Verify
pm2 list
```

Note: Fleet instances need `npm install && npm run build` in each
`microhal-*/nanoclaw/` directory first if not already built:

```bash
for inst in microhal-*/nanoclaw; do
  npm --prefix "$inst" install && npm --prefix "$inst" run build
done
```

## 5. Verify

```bash
# Send a test message to @HAL via Telegram
# Check it responds

# Verify cron is running
crontab -l | grep hal-briefing

# Verify Docker can spawn containers
docker run --rm nanoclaw-agent:latest echo "container OK"
```

## 6. Post-Cutover Cleanup (optional)

On the source machine, disable the service so it doesn't auto-start:

```bash
systemctl --user disable nanoclaw
```

## What's Where on Target

| Component | Location |
|---|---|
| Service | `systemctl --user {start,stop,status} nanoclaw` |
| Logs | `/home/mrkai/code/nanoclaw/logs/nanoclaw.log` |
| .env (tokens) | `/home/mrkai/code/nanoclaw/.env` |
| SQLite | `/home/mrkai/code/nanoclaw/store/*.db` |
| Memory | `/home/mrkai/code/nanoclaw/memory/` |
| Fleet | `/home/mrkai/code/halfleet/microhal-*` |
| Crontab | `crontab -l` (5 jobs) |
| Docker image | `nanoclaw-agent:latest` (2.98GB) |
| PM2 | `$HOME/.npm-global/bin/pm2` |
| Config | `~/.config/nanoclaw/` |
| Gmail OAuth | `~/.gmail-mcp/` |
| Claude creds | `~/.claude/.credentials.json` |

## Rollback

If something goes wrong, stop the target and restart the source:

```bash
# On target
ssh mrkai@100.83.133.110 "systemctl --user stop nanoclaw"

# On source (this machine)
systemctl --user start nanoclaw
```
