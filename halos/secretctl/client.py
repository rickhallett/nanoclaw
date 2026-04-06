"""1Password client — routes through daemon if running, else direct SDK.

Usage from other halos modules:

    from halos.secretctl.client import resolve, list_vaults

    # Resolves via daemon (no biometric) or falls back to direct SDK (one prompt)
    password = await resolve("op://Personal/eBay/password")
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from onepassword import Client, DesktopAuth

SOCKET_PATH = Path.home() / ".hermes" / "secretctl.sock"

# Direct SDK singleton (fallback when daemon isn't running)
_client: Optional[Client] = None
_lock = asyncio.Lock()

DEFAULT_ACCOUNT = "my.1password.com"
INTEGRATION_NAME = "halo"
INTEGRATION_VERSION = "v1.0.0"


async def _daemon_request(data: dict) -> Optional[dict]:
    """Send a request to the daemon. Returns response dict or None if unavailable."""
    if not SOCKET_PATH.exists():
        return None
    try:
        reader, writer = await asyncio.open_unix_connection(str(SOCKET_PATH))
        writer.write(json.dumps(data).encode() + b"\n")
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout=10)
        writer.close()
        if line:
            return json.loads(line.decode().strip())
        return None
    except (ConnectionRefusedError, FileNotFoundError, asyncio.TimeoutError, OSError):
        return None


async def _get_direct_client() -> Client:
    """Authenticate directly via SDK (triggers biometric)."""
    global _client
    async with _lock:
        if _client is None:
            auth = DesktopAuth(DEFAULT_ACCOUNT)
            _client = await Client.authenticate(
                auth=auth,
                integration_name=INTEGRATION_NAME,
                integration_version=INTEGRATION_VERSION,
            )
        return _client


async def resolve(reference: str) -> str:
    """Resolve a 1Password secret reference URI.

    Routes through daemon if running, else direct SDK auth.
    """
    # Try daemon first
    resp = await _daemon_request({"action": "resolve", "reference": reference})
    if resp and resp.get("ok"):
        return resp["data"]

    # Fallback to direct SDK
    client = await _get_direct_client()
    return await client.secrets.resolve(reference)


async def list_vaults() -> list:
    """List accessible vaults."""
    resp = await _daemon_request({"action": "vaults"})
    if resp and resp.get("ok"):
        return resp["data"]

    client = await _get_direct_client()
    return await client.vaults.list()


async def list_items(vault_id: str) -> list:
    """List items in a vault."""
    resp = await _daemon_request({"action": "items", "vault_id": vault_id})
    if resp and resp.get("ok"):
        return resp["data"]

    client = await _get_direct_client()
    return await client.items.list(vault_id)


async def get_item(vault_id: str, item_id: str):
    """Get a full item."""
    resp = await _daemon_request({"action": "get", "vault_id": vault_id, "item_id": item_id})
    if resp and resp.get("ok"):
        return resp["data"]

    client = await _get_direct_client()
    return await client.items.get(vault_id, item_id)


def resolve_sync(reference: str) -> str:
    """Synchronous wrapper for resolve()."""
    return asyncio.run(resolve(reference))
