"""halctl CLI — microHAL fleet management.

Provision, monitor, and control independent HAL instances.
"""

import argparse
import sys

from halos.common.log import hlog


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_create(args):
    """Provision a new microHAL instance."""
    from .provision import create_instance

    try:
        entry = create_instance(
            name=args.name,
            personality=args.personality,
        )
    except FileExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"created  {entry['name']}  {entry['path']}")
    print(f"personality: {entry['personality']}")
    print(f"token env:   {entry['telegram_bot_token_env']}")
    print()
    print("Next steps:")
    print("  1. Open Telegram, message @BotFather")
    print("  2. Send /newbot and follow the prompts")
    print(f"  3. Set the bot token as {entry['telegram_bot_token_env']} in your environment")
    print(f"  4. Start the instance: cd {entry['path']}/.. && npx pm2 start ecosystem.config.cjs")
    return 0


def cmd_list(args):
    """List fleet instances with live audit data."""
    from .config import load_fleet_manifest
    from pathlib import Path
    import re
    import sqlite3 as sqlite

    manifest = load_fleet_manifest()
    instances = manifest.get("instances", [])

    if not instances:
        print("no instances")
        return 0

    rows = []
    for inst in instances:
        name = inst["name"]
        deploy = Path(inst.get("path", ""))
        status = inst.get("status", "unknown")
        personality = inst.get("personality", "")

        bot_username = ""
        tg_group = ""
        notes = 0
        host_path = str(deploy).replace(str(Path.home()), "~")

        if deploy.exists():
            # Bot username from ecosystem config
            eco = deploy.parent / "ecosystem.config.cjs"
            if eco.exists():
                content = eco.read_text()
                m = re.search(r'TELEGRAM_BOT_TOKEN:\s*["\'](\d+):', content)
                if m:
                    # Get username from DB chats or fall back to token prefix
                    bot_username = m.group(1)

            # Telegram group from registered_groups
            db_path = deploy / "store" / "messages.db"
            if db_path.exists():
                try:
                    conn = sqlite.connect(str(db_path))
                    cur = conn.execute("SELECT jid, name FROM registered_groups LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        tg_group = f"{row[0]} ({row[1]})"
                    conn.close()
                except Exception:
                    tg_group = "?"

            # Notes count
            notes_dir = deploy / "memory" / "notes"
            if notes_dir.exists():
                notes = len(list(notes_dir.glob("*.md")))

        rows.append((name, status, personality, bot_username, tg_group, notes, host_path))

    # Print table
    fmt = "{:<10} {:<8} {:<16} {:<14} {:<28} {:<6} {}"
    print(fmt.format("NAME", "STATUS", "PERSONALITY", "BOT ID", "TG GROUP", "NOTES", "HOST PATH"))
    print("─" * 120)
    for r in rows:
        print(fmt.format(r[0], r[1], r[2], r[3], r[4], r[5], r[6]))

    # Container perspective (footer)
    print()
    print("Container mounts: /workspace/project (ro) · /workspace/group (rw) · /workspace/ipc (rw)")
    return 0


def cmd_status(args):
    """Show details of a specific instance."""
    from .config import load_fleet_manifest
    from pathlib import Path

    manifest = load_fleet_manifest()
    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == args.name:
            instance = inst
            break

    if instance is None:
        print(f"ERROR: instance '{args.name}' not found", file=sys.stderr)
        sys.exit(1)

    deploy = Path(instance["path"])
    print(f"Name:        {instance['name']}")
    print(f"Status:      {instance.get('status', 'unknown')}")
    print(f"Personality: {instance.get('personality', '')}")
    print(f"Path:        {instance['path']}")
    print(f"Token env:   {instance.get('telegram_bot_token_env', '')}")
    print(f"Services:    {', '.join(instance.get('services', []))}")
    print(f"Created:     {instance.get('created', '')}")

    # Disk usage (if path exists)
    if deploy.exists():
        import subprocess
        try:
            result = subprocess.run(
                ["du", "-sh", str(deploy)],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                print(f"Disk:        {result.stdout.split()[0]}")
        except Exception:
            pass

        # Memory notes count
        mem_dir = deploy / "memory" / "notes"
        if mem_dir.exists():
            notes = list(mem_dir.glob("*.md"))
            print(f"Notes:       {len(notes)}")
    else:
        print(f"Disk:        (path not found)")

    return 0


def cmd_freeze(args):
    """Freeze an instance (stop process, preserve everything)."""
    from .provision import freeze_instance
    try:
        freeze_instance(args.name)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return 0


def cmd_fold(args):
    """Fold an instance (stop + archive)."""
    from .provision import fold_instance
    try:
        fold_instance(args.name)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return 0


def cmd_fry(args):
    """Fry an instance (stop + wipe). Nuclear."""
    from .provision import fry_instance
    try:
        fry_instance(args.name, confirm=args.confirm)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    return 0


def cmd_reset(args):
    """Nuclear reset: kill container, clear all state, fresh start."""
    from .config import load_fleet_manifest
    from pathlib import Path
    import subprocess
    import shutil

    manifest = load_fleet_manifest()
    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == args.name:
            instance = inst
            break

    if instance is None:
        print(f"ERROR: instance '{args.name}' not found", file=sys.stderr)
        sys.exit(1)

    deploy = Path(instance["path"])
    print(f"Resetting {args.name}...")

    # 1. Kill any running containers for this instance
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=nanoclaw-telegram-main", "-q"],
            capture_output=True, text=True, timeout=5,
        )
        for cid in result.stdout.strip().split("\n"):
            if cid:
                subprocess.run(["docker", "kill", cid], capture_output=True, timeout=5)
                print(f"  killed container {cid[:12]}")
    except Exception:
        pass

    # 2. Clear database
    db_path = deploy / "store" / "messages.db"
    if db_path.exists():
        try:
            subprocess.run(
                ["sqlite3", str(db_path), "DELETE FROM messages; DELETE FROM chats; DELETE FROM sessions;"],
                capture_output=True, timeout=5,
            )
            print("  cleared messages, chats, sessions")
        except Exception as e:
            print(f"  WARN: db clear failed: {e}", file=sys.stderr)

    # 3. Wipe session files
    sessions_dir = deploy / "data" / "sessions"
    if sessions_dir.exists():
        shutil.rmtree(sessions_dir)
        print("  wiped session files")

    # 4. Restart pm2
    try:
        subprocess.run(["npx", "pm2", "delete", f"microhal-{args.name}"],
                        capture_output=True, timeout=10)
    except Exception:
        pass

    eco_path = deploy.parent / "ecosystem.config.cjs"
    if eco_path.exists():
        result = subprocess.run(
            ["npx", "pm2", "start", str(eco_path)],
            capture_output=True, text=True, timeout=15, cwd=str(deploy.parent),
        )
        if result.returncode == 0:
            print(f"  restarted pm2 process")
        else:
            print(f"  WARN: pm2 start failed: {result.stderr[:100]}", file=sys.stderr)
    else:
        print(f"  WARN: no ecosystem config at {eco_path}", file=sys.stderr)

    hlog("halctl", "info", "instance_reset", {"name": args.name})
    print(f"\nreset complete — {args.name} is fresh")
    return 0


def cmd_push(args):
    """Push code updates from prime to microHAL instance(s)."""
    if args.all:
        from .provision import push_all
        pushed = push_all()
        if not pushed:
            print("no active instances to push")
        else:
            for name in pushed:
                print(f"pushed  {name}")
    else:
        if not args.name:
            print("ERROR: specify --name or --all", file=sys.stderr)
            sys.exit(1)
        from .provision import push_instance
        try:
            push_instance(args.name)
            print(f"pushed  {args.name}")
        except (ValueError, FileNotFoundError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="halctl",
        description="halctl — microHAL fleet management.",
    )

    sub = parser.add_subparsers(dest="subcommand")

    # create
    cr = sub.add_parser("create", help="Provision a new microHAL instance")
    cr.add_argument("--name", required=True, help="Instance name")
    cr.add_argument("--personality", default=None, help="Personality template name")

    # list
    sub.add_parser("list", help="List fleet instances")

    # status
    st = sub.add_parser("status", help="Instance details")
    st.add_argument("name", help="Instance name")

    # freeze
    fr = sub.add_parser("freeze", help="Stop process, preserve everything")
    fr.add_argument("name", help="Instance name")

    # fold
    fo = sub.add_parser("fold", help="Stop + archive data")
    fo.add_argument("name", help="Instance name")

    # fry
    fy = sub.add_parser("fry", help="Stop + wipe (nuclear)")
    fy.add_argument("name", help="Instance name")
    fy.add_argument("--confirm", action="store_true", help="Required for destructive operation")

    # reset
    rs = sub.add_parser("reset", help="Nuclear reset: kill container, clear state, restart")
    rs.add_argument("name", help="Instance name")

    # push
    pu = sub.add_parser("push", help="Push code updates from prime")
    pu.add_argument("name", nargs="?", default=None, help="Instance name")
    pu.add_argument("--all", action="store_true", help="Push to all active instances")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "create": cmd_create,
        "list": cmd_list,
        "status": cmd_status,
        "freeze": cmd_freeze,
        "fold": cmd_fold,
        "fry": cmd_fry,
        "reset": cmd_reset,
        "push": cmd_push,
    }

    if args.subcommand in dispatch:
        sys.exit(dispatch[args.subcommand](args) or 0)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
