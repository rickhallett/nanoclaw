"""secretctl CLI — 1Password secret access with daemon support.

Usage:
    secretctl vaults                              # list vaults
    secretctl items <vault_id>                    # list items in vault
    secretctl get <vault_id> <item_id>            # get full item
    secretctl resolve "op://Vault/Item/field"     # resolve secret ref
    secretctl daemon                              # start daemon (foreground)
    secretctl daemon --background                 # start daemon (background)
    secretctl stop                                # stop daemon
    secretctl status                              # check daemon status
"""

import argparse
import asyncio
import json
import sys

from . import client
from . import daemon as daemon_mod


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="secretctl",
        description="secretctl — 1Password secret access via SDK with daemon support",
    )
    sub = parser.add_subparsers(dest="command")

    # vaults
    sub.add_parser("vaults", help="List accessible vaults")

    # items
    p_items = sub.add_parser("items", help="List items in a vault")
    p_items.add_argument("vault_id", help="Vault ID")

    # get
    p_get = sub.add_parser("get", help="Get a full item with fields")
    p_get.add_argument("vault_id", help="Vault ID")
    p_get.add_argument("item_id", help="Item ID")

    # resolve
    p_resolve = sub.add_parser("resolve", help="Resolve op:// secret reference(s)")
    p_resolve.add_argument("references", nargs="+", help="op:// URIs")
    p_resolve.add_argument("--json", action="store_true", help="Output as JSON")

    # daemon
    p_daemon = sub.add_parser("daemon", help="Start the secret daemon (one biometric, persistent access)")
    p_daemon.add_argument("--background", action="store_true", help="Run in background")
    p_daemon.add_argument("--ttl", type=int, default=30, metavar="MINS", help="Auto-shutdown after N minutes (default: 30)")

    # stop
    sub.add_parser("stop", help="Stop the daemon")

    # status
    sub.add_parser("status", help="Check daemon status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Non-async commands
    if args.command == "daemon":
        daemon_mod.start_daemon(background=args.background, ttl_minutes=args.ttl)
        return

    if args.command == "stop":
        daemon_mod.stop_daemon()
        return

    if args.command == "status":
        if daemon_mod.is_running():
            pid = daemon_mod.PID_PATH.read_text().strip()
            print(f"Daemon running (pid {pid}, socket {daemon_mod.SOCKET_PATH})")
        else:
            print("Daemon not running")
        return

    asyncio.run(_dispatch(args))


async def _dispatch(args) -> None:
    if args.command == "vaults":
        vaults = await client.list_vaults()
        if isinstance(vaults, list) and vaults and isinstance(vaults[0], dict):
            for v in vaults:
                print(f"{v['id']}  {v['title']}")
        else:
            for v in vaults:
                print(f"{v.id}  {v.title}")

    elif args.command == "items":
        items = await client.list_items(args.vault_id)
        if isinstance(items, list) and items and isinstance(items[0], dict):
            for item in items:
                print(f"{item['id']}  {item['title']}")
        else:
            for item in items:
                print(f"{item.id}  {item.title}")

    elif args.command == "get":
        item = await client.get_item(args.vault_id, args.item_id)
        if isinstance(item, dict):
            print(f"Title: {item['title']}")
            print(f"Category: {item['category']}")
            for f in item.get("fields", []):
                print(f"  {f['label']}: {f['value']}")
        else:
            print(f"Title: {item.title}")
            print(f"Category: {item.category}")
            if hasattr(item, "fields"):
                for f in item.fields:
                    label = getattr(f, "title", getattr(f, "label", "?"))
                    value = getattr(f, "value", "")
                    print(f"  {label}: {value}")

    elif args.command == "resolve":
        results = []
        for ref in args.references:
            secret = await client.resolve(ref)
            results.append({"reference": ref, "value": secret})

        if args.json:
            print(json.dumps(results if len(results) > 1 else results[0]))
        else:
            for r in results:
                if len(results) > 1:
                    print(f"{r['reference']}: {r['value']}")
                else:
                    print(r["value"])
