"""secretctl daemon — authenticates once, serves secrets over Unix socket.

Start:
    secretctl daemon                    # foreground
    secretctl daemon --background       # daemonise

Then any process can read secrets without biometric:
    secretctl resolve "op://Personal/eBay/password"   # uses daemon if running
    # or programmatically:
    from halos.secretctl.client import resolve
    secret = await resolve("op://Personal/eBay/password")  # routes through daemon

Protocol (JSON over Unix socket, newline-delimited):

    Request:  {"action": "resolve", "reference": "op://..."}
              {"action": "vaults"}
              {"action": "items", "vault_id": "..."}
              {"action": "get", "vault_id": "...", "item_id": "..."}
              {"action": "ping"}
              {"action": "shutdown"}

    Response: {"ok": true, "data": ...}
              {"ok": false, "error": "..."}
"""

import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from onepassword import Client, DesktopAuth

SOCKET_PATH = Path.home() / ".hermes" / "secretctl.sock"
PID_PATH = Path.home() / ".hermes" / "secretctl.pid"

DEFAULT_ACCOUNT = "my.1password.com"
INTEGRATION_NAME = "halo"
INTEGRATION_VERSION = "v1.0.0"


DEFAULT_TTL_MINUTES = 30


class SecretDaemon:
    def __init__(self, account: str = DEFAULT_ACCOUNT, ttl_minutes: int = DEFAULT_TTL_MINUTES):
        self.account = account
        self.ttl_minutes = ttl_minutes
        self.client: Optional[Client] = None
        self.server: Optional[asyncio.AbstractServer] = None

    async def authenticate(self) -> None:
        print("Authenticating with 1Password (biometric)...")
        auth = DesktopAuth(self.account)
        self.client = await Client.authenticate(
            auth=auth,
            integration_name=INTEGRATION_NAME,
            integration_version=INTEGRATION_VERSION,
        )
        print("Authenticated.")

    async def handle_request(self, data: dict) -> dict:
        action = data.get("action")

        if action == "ping":
            return {"ok": True, "data": "pong"}

        if action == "shutdown":
            print("Shutdown requested.")
            asyncio.get_event_loop().call_soon(self._shutdown)
            return {"ok": True, "data": "shutting down"}

        if self.client is None:
            return {"ok": False, "error": "not authenticated"}

        try:
            if action == "resolve":
                ref = data.get("reference", "")
                if not ref.startswith("op://"):
                    return {"ok": False, "error": f"invalid reference: {ref}"}
                secret = await self.client.secrets.resolve(ref)
                return {"ok": True, "data": secret}

            elif action == "vaults":
                vaults = await self.client.vaults.list()
                result = [{"id": v.id, "title": v.title} for v in vaults]
                return {"ok": True, "data": result}

            elif action == "items":
                vault_id = data.get("vault_id", "")
                items = await self.client.items.list(vault_id)
                result = [{"id": i.id, "title": i.title} for i in items]
                return {"ok": True, "data": result}

            elif action == "get":
                vault_id = data.get("vault_id", "")
                item_id = data.get("item_id", "")
                item = await self.client.items.get(vault_id, item_id)
                fields = []
                if hasattr(item, "fields"):
                    for f in item.fields:
                        label = getattr(f, "title", getattr(f, "label", "?"))
                        value = getattr(f, "value", "")
                        fields.append({"label": label, "value": value})
                return {"ok": True, "data": {
                    "title": item.title,
                    "category": str(item.category),
                    "fields": fields,
                }}

            else:
                return {"ok": False, "error": f"unknown action: {action}"}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    request = json.loads(line.decode().strip())
                except json.JSONDecodeError:
                    response = {"ok": False, "error": "invalid JSON"}
                else:
                    response = await self.handle_request(request)
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            writer.close()

    def _shutdown(self) -> None:
        if self.server:
            self.server.close()
        self._cleanup()
        asyncio.get_event_loop().stop()

    def _cleanup(self) -> None:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        if PID_PATH.exists():
            PID_PATH.unlink()

    async def run(self) -> None:
        # Clean stale socket
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)

        await self.authenticate()

        self.server = await asyncio.start_unix_server(
            self._handle_connection, path=str(SOCKET_PATH)
        )
        # Restrict socket permissions
        os.chmod(SOCKET_PATH, 0o600)

        # Write PID
        PID_PATH.write_text(str(os.getpid()))

        print(f"Daemon listening on {SOCKET_PATH} (pid {os.getpid()}, ttl {self.ttl_minutes}m)")

        # Handle signals
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown)

        # Schedule auto-shutdown
        loop.call_later(self.ttl_minutes * 60, self._expire)

        try:
            await self.server.serve_forever()
        except asyncio.CancelledError:
            pass
        finally:
            self._cleanup()
            print("Daemon stopped.")

    def _expire(self) -> None:
        print(f"TTL expired ({self.ttl_minutes}m). Shutting down.")
        self._shutdown()


def is_running() -> bool:
    """Check if the daemon is already running."""
    if not PID_PATH.exists():
        return False
    try:
        pid = int(PID_PATH.read_text().strip())
        os.kill(pid, 0)  # signal 0 = existence check
        return True
    except (ProcessLookupError, ValueError):
        # Stale PID file
        PID_PATH.unlink(missing_ok=True)
        SOCKET_PATH.unlink(missing_ok=True)
        return False


def start_daemon(background: bool = False, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> None:
    """Start the daemon, optionally in the background."""
    if is_running():
        pid = PID_PATH.read_text().strip()
        print(f"Daemon already running (pid {pid})")
        sys.exit(0)

    if background:
        pid = os.fork()
        if pid > 0:
            # Parent — wait briefly for auth to complete
            print(f"Daemon forked (pid {pid}, ttl {ttl_minutes}m). Authenticate via Touch ID in the prompt.")
            sys.exit(0)
        # Child — detach
        os.setsid()
        # Redirect stdout/stderr to log
        log_path = Path.home() / ".hermes" / "secretctl.log"
        log_fd = open(log_path, "a")
        os.dup2(log_fd.fileno(), sys.stdout.fileno())
        os.dup2(log_fd.fileno(), sys.stderr.fileno())

    daemon = SecretDaemon(ttl_minutes=ttl_minutes)
    asyncio.run(daemon.run())


def stop_daemon() -> None:
    """Stop the running daemon."""
    if not is_running():
        print("Daemon not running.")
        return
    pid = int(PID_PATH.read_text().strip())
    os.kill(pid, signal.SIGTERM)
    print(f"Sent SIGTERM to daemon (pid {pid}).")
