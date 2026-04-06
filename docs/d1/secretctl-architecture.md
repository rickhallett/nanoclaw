# secretctl Architecture

> Verified: 2026-03-28
> Source: `halos/secretctl/` (client.py, daemon.py, cli.py)

secretctl gives halos modules and agents access to 1Password secrets without repeated biometric prompts. A long-running daemon authenticates once via Touch ID, then serves secrets to any local process over a Unix socket for the duration of its TTL.

---

## Daemon Lifecycle

The daemon moves through a linear sequence: authenticate, listen, shut down. There are no restart or reconnect states — if it dies, the next client that needs a secret either starts a new daemon or falls back to direct SDK auth.

```mermaid
stateDiagram-v2
    [*] --> Starting: secretctl daemon --ttl 60
    
    Starting --> Authenticating: Clean stale socket
    Authenticating --> TouchID: DesktopAuth(account)
    TouchID --> Authenticated: Biometric approved
    Authenticated --> Listening: Unix socket opened\n~/.hermes/secretctl.sock
    
    Listening --> Listening: Handle requests
    Listening --> Expired: TTL timer fires
    Listening --> Stopped: SIGTERM / SIGINT
    Listening --> Stopped: {"action": "shutdown"}
    
    Expired --> Cleanup: _expire()
    Stopped --> Cleanup: _shutdown()
    Cleanup --> [*]: Unlink socket + PID
```

**Starting:** Removes any stale socket file left by a previous crash. Without this, `asyncio.start_unix_server()` would fail with "address already in use."

**Authenticating:** The 1Password Python SDK's `DesktopAuth` communicates with the 1Password desktop app over IPC. The desktop app handles the biometric challenge. The SDK receives an authenticated session object — no tokens are written to disk.

**Listening:** The daemon enters `serve_forever()`, an asyncio coroutine that blocks until the server is explicitly closed. Three things can trigger shutdown: the TTL timer (registered via `loop.call_later`), a Unix signal, or a `{"action": "shutdown"}` request from a client.

**Cleanup:** Unlinks both `secretctl.sock` and `secretctl.pid`. The `finally` block in `run()` calls `_cleanup()` as a safety net in case `_shutdown()` was interrupted.

---

## Request Flow

Every CLI invocation (e.g. `secretctl vaults`) is a new short-lived process. `client.py` checks whether the daemon is reachable before deciding how to authenticate.

```mermaid
sequenceDiagram
    participant CLI as secretctl vaults<br/>(new process)
    participant Client as client.py
    participant Socket as Unix Socket<br/>secretctl.sock
    participant Daemon as SecretDaemon<br/>(long-running)
    participant SDK as 1Password SDK<br/>(authenticated)

    CLI->>Client: list_vaults()
    Client->>Client: Socket exists?
    
    alt Daemon running
        Client->>Socket: {"action": "vaults"}\n
        Socket->>Daemon: readline()
        Daemon->>SDK: client.vaults.list()
        Note over SDK: No biometric—<br/>reuses auth from startup
        SDK-->>Daemon: [vault objects]
        Daemon-->>Socket: {"ok": true, "data": [...]}\n
        Socket-->>Client: JSON response
        Client-->>CLI: Print vault list
    else Daemon not running
        Client->>Client: Socket missing or refused
        Client->>SDK: Client.authenticate()
        Note over SDK: Touch ID prompt
        SDK-->>Client: Authenticated client
        Client->>SDK: client.vaults.list()
        SDK-->>Client: [vault objects]
        Client-->>CLI: Print vault list
    end
```

**Protocol:** Newline-delimited JSON over a Unix domain socket. One JSON object per line, request and response. No HTTP, no framing, no overhead. The connection supports multiple request/response cycles (the daemon reads in a `while True` loop), but in practice each client sends one request and disconnects.

**Fallback:** `_daemon_request()` checks three things: does the socket file exist, can we connect, does the response arrive within 10 seconds. Any failure returns `None`, and the caller falls through to direct SDK authentication. This means the daemon is always optional — secretctl works without it, just with more fingerprint prompts.

**Why the SDK doesn't re-prompt:** The `Client` object holds the authenticated session as an in-memory state machine. Every `.secrets.resolve()` or `.vaults.list()` call is a method invocation on that live object, routed through the SDK's internal IPC to the 1Password desktop app. The desktop app remembers that this process was already authorised. No re-authentication until the process dies.

---

## Background Daemon (fork)

With `--background`, the daemon detaches from the terminal so it survives shell exits. This uses the classic Unix double-fork pattern (simplified to a single fork since we call `os.setsid()`).

```mermaid
flowchart TD
    A["secretctl daemon --background --ttl 60"] --> B["os.fork()"]
    
    B --> C["Parent process"]
    B --> D["Child process"]
    
    C --> C1["Print: Daemon forked (pid N)"]
    C1 --> C2["sys.exit(0)"]
    
    D --> D1["os.setsid() — detach from terminal"]
    D1 --> D2["Redirect stdout/stderr → secretctl.log"]
    D2 --> D3["Touch ID prompt"]
    D3 --> D4["Open Unix socket :0600"]
    D4 --> D5["Write PID file"]
    D5 --> D6["Schedule TTL callback"]
    D6 --> D7["serve_forever()"]
    
    D7 -->|"TTL expires"| D8["_expire() → _shutdown()"]
    D7 -->|"SIGTERM"| D8
    D8 --> D9["Unlink socket + PID"]
    D9 --> D10["Process exits"]
```

**`os.fork()`:** Creates an identical copy of the process. The parent gets the child's PID (positive integer); the child gets 0. Both continue executing from the same point.

**`os.setsid()`:** The child becomes a session leader — it's no longer associated with the terminal that started it. Closing that terminal won't send SIGHUP to the daemon.

**Stdout/stderr redirect:** Since there's no terminal, output goes to `~/.hermes/secretctl.log`. The `open()` + `os.dup2()` pattern replaces file descriptors 1 (stdout) and 2 (stderr) at the OS level, so even C libraries writing to stderr end up in the log file.

**Touch ID timing:** The biometric prompt appears *after* the parent has exited and returned you to the shell. This can be slightly confusing — your terminal prompt is back, but Touch ID is waiting. The daemon won't start serving until you approve.

---

## What's on Disk

Nothing sensitive is persisted. The authenticated session exists only in the daemon process's memory. Kill the process and the auth is gone.

```mermaid
flowchart LR
    subgraph "~/.hermes/"
        SOCK["secretctl.sock<br/><i>Unix domain socket</i><br/>srw------- (0600)"]
        PID["secretctl.pid<br/><i>Text: process ID</i>"]
        LOG["secretctl.log<br/><i>Only if --background</i>"]
    end
    
    subgraph "In memory only"
        AUTH["1Password Client<br/><i>Authenticated session</i><br/>Dies with process"]
    end
    
    SOCK -.-|"Clients connect here"| AUTH
    PID -.-|"Used by status/stop"| AUTH
```

| File | Purpose | Lifecycle |
|---|---|---|
| `secretctl.sock` | Unix domain socket. Clients connect here to send JSON requests. | Created on startup, unlinked on shutdown. Permission `0600` — only the owning user can connect. |
| `secretctl.pid` | Contains the daemon's process ID as plain text. | Created on startup, unlinked on shutdown. Used by `is_running()` to check liveness via `os.kill(pid, 0)`. |
| `secretctl.log` | Daemon stdout/stderr when running with `--background`. | Appended to, never truncated automatically. Only exists if you've used `--background`. |

**Stale file recovery:** If the daemon crashes without cleaning up, the next `start_daemon()` call detects the stale PID (process no longer exists), removes both files, and starts fresh. `is_running()` handles this transparently.

---

## hal Dispatcher

`hal` is a thin router that replaces itself with the target command via `os.execvp()`. After the exec call, the hal process no longer exists — the kernel has replaced its entire memory image with the target binary. No subprocess overhead, no parent process lingering.

```mermaid
flowchart TD
    A["hal secrets vaults"] --> B{"Module lookup"}
    
    B -->|"Found in MODULES"| C["os.execvp(secretctl, args)"]
    B -->|"Found in AGENT_MODULES"| D{"Command type?"}
    B -->|"Not found"| E["Fuzzy match full cmd name"]
    E -->|"No match"| F["Error: unknown module"]
    
    D -->|"steer"| G["os.execvp(steer, args)"]
    D -->|"drive"| H["chdir agent/drive/<br/>os.execvp(uv run python main.py, args)"]
    D -->|"just *"| I["chdir agent/<br/>os.execvp(just, subcmd + args)"]
    
    C --> J["Process replaced —<br/>hal is gone,<br/>secretctl is running"]
    G --> J
    H --> J
    I --> J
```

**`os.execvp` vs `subprocess.run`:** `execvp` replaces the current process. There's no parent waiting for a child — hal becomes secretctl. This means exit codes, signals, and stdio all pass through natively. `subprocess.run` would create a child process and require hal to forward everything, adding complexity for no benefit.

**Agent tool dispatch:** Commands prefixed with `just` need to run from the `agent/` directory (the justfile lives there). `os.chdir()` before `execvp` handles this. `drive` similarly needs to run from `agent/drive/` since it's a separate uv project with its own `pyproject.toml`.

**Fuzzy matching:** If someone types `hal nightctl add` instead of `hal night add`, the fuzzy matcher strips the `ctl` suffix and finds the alias. This catches the common case of using the full command name as the module identifier.

---

## CLI Quick Reference

```bash
# Daemon management
secretctl daemon                        # foreground, 30 min TTL
secretctl daemon --background --ttl 60  # background, 1 hour
secretctl status                        # check if running
secretctl stop                          # graceful shutdown

# Secret access (routes through daemon if running)
secretctl vaults                        # list vaults
secretctl items <vault_id>              # list items
secretctl get <vault_id> <item_id>      # full item with fields
secretctl resolve "op://Vault/Item/field"              # single secret
secretctl resolve ref1 ref2 ref3 --json                # batch, JSON

# Via hal
hal secrets daemon --ttl 120
hal secrets resolve "op://Personal/eBay/password"

# Programmatic (from other halos modules)
from halos.secretctl.client import resolve
password = await resolve("op://Personal/eBay/password")
```

## Security Notes

- The Unix socket is `0600` — only the owning user can connect. No network exposure.
- No secrets are cached on disk. The authenticated session lives in process memory only.
- The TTL guarantees the daemon won't run indefinitely if forgotten.
- The 1Password desktop app's own security model still applies — the SDK session is scoped to what the desktop app permits.
- The daemon logs (`secretctl.log`) contain status messages, not secret values. Responses containing secrets are only written to the socket, never to the log.
