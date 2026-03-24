# gateway/

Message gateway — routes Telegram, Gmail, and other channels to Claude agents in isolated containers.

## What It Does

A single Node.js process that:

1. **Receives messages** from Telegram, Gmail (extensible to Slack, Discord, WhatsApp)
2. **Routes them** to the correct group queue (per-chat isolation)
3. **Spawns Claude agents** in Docker containers with mounted filesystem, memory, and tools
4. **Delivers responses** back through the originating channel
5. **Manages credentials** via an OAuth proxy (Claude Max subscription, no separate API billing)

## Architecture

```
┌──────────┐   ┌──────────┐
│ Telegram  │   │  Gmail   │     Channels self-register via registry.ts
└────┬──┬──┘   └────┬──┬──┘
     │  ▲           │  ▲
     ▼  │           ▼  │
┌───────┴───────────┴──────────────────────────────┐
│ Orchestrator (index.ts)                           │
│  startup → store msg → trigger check → enqueue    │
└──────┬───────────────────────────┬───────────────┘
       │                           │
       ▼                           ▼
┌──────────────┐           ┌───────────────┐
│ group-queue   │           │ task-scheduler │
│ max 5 concur  │           │ 60s poll       │
│ per-group     │           │ drift-resist   │
│ mutex         │           └───────┬───────┘
└──────┬───────┘                   │
       ▼                           ▼
┌──────────────────────────────────────────────────┐
│ container-runner                                  │
│  Docker container per invocation                  │
│  Mounted: group folder, halos CLIs, credentials   │
│  Claude Agent SDK conversation                    │
│  ⚠ No macOS access — steer/drive not available    │
└──────────────────────────────────────────────────┘
```

## Structure

```
gateway/
├── src/
│   ├── index.ts              Main orchestrator (~755 lines)
│   ├── channels/
│   │   ├── registry.ts       Channel plugin system
│   │   ├── telegram.ts       Telegram via grammy
│   │   └── gmail.ts          Gmail via googleapis
│   ├── container-runner.ts   Spawns Docker containers for Claude agents
│   ├── container-runtime.ts  Docker lifecycle management
│   ├── credential-proxy.ts   OAuth token proxy for Claude API
│   ├── group-queue.ts        Per-group concurrency control
│   ├── group-folder.ts       Filesystem isolation per chat
│   ├── db.ts                 SQLite — messages, sessions, groups
│   ├── ipc.ts                Inter-process communication
│   ├── task-scheduler.ts     Cron-like scheduled tasks
│   ├── sender-allowlist.ts   Access control
│   ├── router.ts             Message routing logic
│   └── remote-control.ts     Admin commands
├── container/
│   ├── Dockerfile            Agent container image
│   └── agent-runner/         Node.js agent process inside container
├── setup/                    Interactive setup wizard
├── halfleet/                 Fleet provisioning config
├── launchd/                  macOS service management (com.halo)
├── dist/                     Compiled JS output
├── package.json
└── tsconfig.json
```

## Usage

```bash
# Install
npm install

# Build
npm run build

# Development (live reload)
npm run dev

# Production
npm start

# Type check
npx tsc --noEmit

# Tests
npm test
```

## Configuration

All configuration via environment variables in the root `.env`:

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_ALLOWED_USERS` | Comma-separated user IDs |
| `ANTHROPIC_API_KEY` | Leave empty for OAuth mode (recommended) |
| `CONTAINER_IMAGE` | Docker image name (default: `halo-agent:latest`) |

## Fleet

The gateway supports provisioning independent instances for other users (family, clients). Each gets their own bot token, personality, and sandboxed environment.

```bash
halctl create --name ben --personality discovering-ben
halctl push ben
halctl smoke ben
```

Fleet config: `halfleet/fleet-config.yaml`

## Service Management

```bash
# macOS launchd
launchctl load gateway/launchd/com.halo.plist
launchctl start com.halo
launchctl stop com.halo
```
