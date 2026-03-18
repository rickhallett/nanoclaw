"""Provisioning logic for microHAL instances."""

import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    from halos.nightctl import yaml_shim as yaml

import sqlite3 as sqlite

from halos.common.log import hlog
from .config import load_fleet_config, fleet_dir, load_fleet_manifest, save_fleet_manifest
from .templates import compose_claude_md

# Operator's Telegram chat ID — hardcoded as default main group for all fleet instances.
# Every instance goes through Rick first; the end user's chat is registered later.
OPERATOR_CHAT_JID = "tg:5967394003"
OPERATOR_CHAT_NAME = "Operator"


def _make_ignore_fn(exclude_list: list[str]):
    """Build a shutil.copytree ignore function from the exclude list."""
    def _ignore(directory: str, contents: list[str]) -> set[str]:
        ignored = set()
        for item in contents:
            for pattern in exclude_list:
                pattern_clean = pattern.rstrip("/")
                # Match exact name or directory prefix
                if item == pattern_clean:
                    ignored.add(item)
                elif item.startswith(pattern_clean):
                    ignored.add(item)
                # Handle .env* glob
                elif pattern_clean.endswith("*") and item.startswith(pattern_clean[:-1]):
                    ignored.add(item)
            # Also skip __pycache__ and .git
            if item in ("__pycache__", ".git", "node_modules"):
                ignored.add(item)
        return ignored
    return _ignore


def _apply_lock(path: Path, items: list[str], exempt: list[str] | None = None) -> None:
    """Set locked items to read-only (444 for files, 555 for dirs).

    exempt: list of subpaths within locked dirs that should stay writable
    (e.g., '.claude/skills' needs 755/644 because cpSync preserves permissions
    and the container-runner copies skills into session dirs).
    """
    exempt = exempt or []
    exempt_abs = [str((path / e).resolve()) for e in exempt]

    def _is_exempt(p: str) -> bool:
        rp = str(Path(p).resolve())
        return any(rp.startswith(e) for e in exempt_abs)

    for item in items:
        target = path / item
        if not target.exists():
            continue
        if target.is_dir():
            for root, dirs, files in os.walk(target):
                if _is_exempt(root):
                    # Keep writable: 755 dirs, 644 files
                    os.chmod(root, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                             stat.S_IROTH | stat.S_IXOTH)  # 755
                    for f in files:
                        os.chmod(os.path.join(root, f),
                                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)  # 644
                else:
                    os.chmod(root, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH |
                             stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)  # 555
                    for f in files:
                        os.chmod(os.path.join(root, f),
                                 stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 444
        else:
            os.chmod(target, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 444


def _create_open_dirs(path: Path, items: list[str]) -> None:
    """Create open directories with full rwx."""
    for item in items:
        target = path / item
        target.mkdir(parents=True, exist_ok=True)


def _register_operator_chat(deploy_path: Path, group_name: str) -> None:
    """Initialize the instance DB and register the operator's chat as main group.

    Creates the schema matching nanoclaw's db.ts so the instance starts with
    the operator already registered — no manual post-provision step needed.
    """
    store_dir = deploy_path / "store"
    store_dir.mkdir(parents=True, exist_ok=True)
    db_path = store_dir / "messages.db"

    conn = sqlite.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registered_groups (
            jid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            folder TEXT NOT NULL UNIQUE,
            trigger_pattern TEXT NOT NULL,
            added_at TEXT NOT NULL,
            container_config TEXT,
            requires_trigger INTEGER DEFAULT 1,
            is_main INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS onboarding (
            sender_id TEXT PRIMARY KEY,
            chat_jid TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'first_contact',
            waiver_accepted_at TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT NOT NULL,
            chat_jid TEXT NOT NULL,
            question_key TEXT NOT NULL,
            question_text TEXT NOT NULL,
            phase TEXT NOT NULL,
            response_type TEXT NOT NULL,
            response TEXT NOT NULL,
            asked_at TEXT NOT NULL,
            answered_at TEXT NOT NULL,
            conversation_count INTEGER,
            session_context TEXT,
            UNIQUE(sender_id, question_key)
        )
    """)
    conn.execute(
        """INSERT OR REPLACE INTO registered_groups
           (jid, name, folder, trigger_pattern, added_at, requires_trigger, is_main)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            OPERATOR_CHAT_JID,
            group_name,
            "telegram_main",
            "@HAL",
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            0,  # no trigger required for main
            1,  # is_main
        ),
    )
    conn.commit()
    conn.close()
    hlog("halctl", "info", "operator_registered", {
        "jid": OPERATOR_CHAT_JID,
        "group": group_name,
    })


def _rebuild_typescript(deploy_path: Path) -> None:
    """Rebuild TypeScript after source changes."""
    build_result = os.popen(f"cd {deploy_path} && npm run build 2>&1").read()
    if "error" in build_result.lower() and "warning" not in build_result.lower():
        print(f"  WARN: build may have issues: {build_result[-200:]}", file=__import__('sys').stderr)


def _generate_ecosystem_config(name: str, deploy_path: Path, token_env: str) -> str:
    """Generate pm2 ecosystem config content for an instance."""
    # Each fleet instance gets a unique proxy port (3002+) but containers
    # route through prime's proxy on 3001 (Docker bridge accessible).
    proxy_port = 3002 + abs(hash(name)) % 998  # deterministic, avoids 3001

    return f"""// pm2 ecosystem config for microhal-{name}
// Generated by halctl — do not edit manually.
module.exports = {{
  apps: [{{
    name: "microhal-{name}",
    cwd: "{deploy_path}",
    script: "node",
    args: "dist/index.js",
    env: {{
      NODE_ENV: "production",
      CREDENTIAL_PROXY_PORT: "{proxy_port}",
      CONTAINER_PROXY_PORT: "3001",
      TELEGRAM_BOT_TOKEN: process.env.{token_env} || "",
      CLAUDE_CODE_OAUTH_TOKEN: process.env.CLAUDE_CODE_OAUTH_TOKEN || "",
      ASSISTANT_NAME: "HAL",
      MICROHAL_NAME: "{name}",
    }},
    watch: false,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
  }}],
}};
"""


def create_instance(
    name: str,
    personality: str | None = None,
    config_path: Path | None = None,
    fleet_base: Path | None = None,
) -> dict:
    """Provision a new microHAL instance.

    Returns the instance manifest entry dict.
    """
    cfg = load_fleet_config(config_path)
    base = cfg["base"]
    profiles = cfg.get("profiles", {})

    # Resolve personality from profile or fallback to default
    profile = profiles.get(name, profiles.get("default", {}))
    if personality is None:
        personality = profile.get("personality", "default")
    services = profile.get("services", [])
    bot_name = profile.get("telegram_bot_name")

    source = Path(base["source"])
    if not source.exists():
        raise FileNotFoundError(f"source directory not found: {source}")

    # Determine deployment path
    base_dir = fleet_base or fleet_dir()
    deploy_path = base_dir / f"microhal-{name}" / "nanoclaw"

    if deploy_path.exists():
        raise FileExistsError(f"instance already exists: {deploy_path}")

    # Copy source tree, excluding items in exclude list
    ignore_fn = _make_ignore_fn(base.get("exclude", []))
    shutil.copytree(str(source), str(deploy_path), ignore=ignore_fn)

    hlog("halctl", "info", "files_copied", {"name": name, "path": str(deploy_path)})

    # Create open directories
    open_dirs = base.get("open", [])
    open_dirs = list(set(open_dirs + ["data/"]))  # data/ always open
    _create_open_dirs(deploy_path, open_dirs)

    # Compose and write CLAUDE.md
    claude_md = compose_claude_md(personality, name)
    claude_path = deploy_path / "CLAUDE.md"
    claude_path.write_text(claude_md)

    # Rebuild TypeScript (source copied from prime already has CONTAINER_PROXY_PORT)
    _rebuild_typescript(deploy_path)

    # Apply lock permissions with exemptions for cpSync-copied paths
    # Skills and container/skills must stay 755/644 because container-runner
    # copies them into session dirs and cpSync preserves permissions.
    lock_exemptions = base.get("lock_exemptions", [
        ".claude/skills",
        ".claude/hooks",
        "container/skills",
    ])
    _apply_lock(deploy_path, base.get("lock", []), exempt=lock_exemptions)

    # Copy CLAUDE.md to group folder — the agent reads from /workspace/group,
    # NOT /workspace/project. This is the #1 halogenesis lesson.
    group_dir = deploy_path / "groups" / "telegram_main"
    group_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(claude_path), str(group_dir / "CLAUDE.md"))

    hlog("halctl", "info", "claude_md_copied_to_group", {"name": name})

    # Register operator's Telegram chat as main group (no manual post-provision step)
    _register_operator_chat(deploy_path, name)

    # Generate pm2 ecosystem config
    token_env = f"MICROHAL_{name.upper()}_BOT_TOKEN"
    eco_content = _generate_ecosystem_config(name, deploy_path, token_env)
    eco_path = base_dir / f"microhal-{name}" / "ecosystem.config.cjs"
    eco_path.write_text(eco_content)

    # Register in fleet manifest
    manifest = load_fleet_manifest(fleet_base=base_dir)
    entry = {
        "name": name,
        "path": str(deploy_path),
        "telegram_bot_token_env": token_env,
        "personality": personality,
        "services": services,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "active",
    }
    manifest["instances"].append(entry)
    save_fleet_manifest(manifest, fleet_base=base_dir)

    hlog("halctl", "info", "instance_created", {"name": name, "personality": personality})

    return entry


def push_instance(
    name: str,
    config_path: Path | None = None,
    fleet_base: Path | None = None,
) -> None:
    """Push locked files from prime to an existing microHAL instance."""
    cfg = load_fleet_config(config_path)
    base = cfg["base"]
    source = Path(base["source"])

    base_dir = fleet_base or fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)
    instance = None
    for inst in manifest["instances"]:
        if inst["name"] == name:
            instance = inst
            break

    if instance is None:
        raise ValueError(f"instance not found: {name}")

    deploy_path = Path(instance["path"])
    if not deploy_path.exists():
        raise FileNotFoundError(f"deployment not found: {deploy_path}")

    lock_items = base.get("lock", [])

    # Temporarily unlock, copy, re-lock
    for item in lock_items:
        target = deploy_path / item
        if target.exists():
            if target.is_dir():
                for root, dirs, files in os.walk(target):
                    os.chmod(root, stat.S_IRWXU)
                    for f in files:
                        os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
                shutil.rmtree(target)
            else:
                os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
                target.unlink()

        src = source / item
        if src.is_dir():
            shutil.copytree(str(src), str(target))
        elif src.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(target))

    # Rebuild TypeScript (prime's source now has CONTAINER_PROXY_PORT natively)
    _rebuild_typescript(deploy_path)

    # Recompose CLAUDE.md from templates (push copies prime's raw CLAUDE.md,
    # which lacks personality and user context — recomposition restores them).
    personality = instance.get("personality", "default")
    claude_md = compose_claude_md(personality, name)
    claude_path = deploy_path / "CLAUDE.md"
    os.chmod(claude_path, stat.S_IRUSR | stat.S_IWUSR)
    claude_path.write_text(claude_md)

    # Mirror to group folder (the agent reads from /workspace/group, not /workspace/project)
    group_claude = deploy_path / "groups" / "telegram_main" / "CLAUDE.md"
    if group_claude.exists():
        os.chmod(group_claude, stat.S_IRUSR | stat.S_IWUSR)
    group_claude.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(claude_path), str(group_claude))

    # Re-apply lock (including recomposed CLAUDE.md)
    lock_exemptions = base.get("lock_exemptions", [
        ".claude/skills",
        ".claude/hooks",
        "container/skills",
    ])
    _apply_lock(deploy_path, lock_items, exempt=lock_exemptions)
    hlog("halctl", "info", "instance_pushed", {"name": name})


def push_all(
    config_path: Path | None = None,
    fleet_base: Path | None = None,
) -> list[str]:
    """Push locked files to all active instances. Returns list of pushed names."""
    base_dir = fleet_base or fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)
    pushed = []
    for inst in manifest["instances"]:
        if inst.get("status") == "active":
            push_instance(inst["name"], config_path=config_path, fleet_base=fleet_base)
            pushed.append(inst["name"])
    return pushed


def freeze_instance(name: str, fleet_base: Path | None = None) -> None:
    """Stop process, preserve everything. Reversible."""
    base_dir = fleet_base or fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)
    for inst in manifest["instances"]:
        if inst["name"] == name:
            inst["status"] = "frozen"
            save_fleet_manifest(manifest, fleet_base=base_dir)
            hlog("halctl", "info", "instance_frozen", {"name": name})
            print(f"frozen  {name}")
            print(f"\nManual step: pm2 stop microhal-{name}")
            return
    raise ValueError(f"instance not found: {name}")


def fold_instance(name: str, fleet_base: Path | None = None) -> None:
    """Stop + archive data. Not easily reversible."""
    base_dir = fleet_base or fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)
    for inst in manifest["instances"]:
        if inst["name"] == name:
            inst["status"] = "folded"
            save_fleet_manifest(manifest, fleet_base=base_dir)
            hlog("halctl", "info", "instance_folded", {"name": name})
            print(f"folded  {name}")
            print(f"\nManual steps:")
            print(f"  1. pm2 stop microhal-{name}")
            print(f"  2. Revoke bot token via BotFather")
            print(f"  3. Archive data from {inst['path']}")
            return
    raise ValueError(f"instance not found: {name}")


def fry_instance(name: str, confirm: bool = False, fleet_base: Path | None = None) -> None:
    """Stop + wipe. Nuclear. Requires confirm=True."""
    if not confirm:
        raise ValueError("fry requires --confirm flag (this is destructive)")

    base_dir = fleet_base or fleet_dir()
    manifest = load_fleet_manifest(fleet_base=base_dir)
    for inst in manifest["instances"]:
        if inst["name"] == name:
            deploy_path = Path(inst["path"])
            inst["status"] = "fried"
            save_fleet_manifest(manifest, fleet_base=base_dir)

            # Unlock and delete if path exists
            if deploy_path.exists():
                instance_dir = deploy_path.parent
                # Unlock everything first
                for root, dirs, files in os.walk(instance_dir):
                    os.chmod(root, stat.S_IRWXU)
                    for f in files:
                        os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
                shutil.rmtree(instance_dir)

            hlog("halctl", "info", "instance_fried", {"name": name})
            print(f"fried  {name}  (deployment wiped)")
            print(f"\nManual step: Revoke bot token via BotFather")
            return
    raise ValueError(f"instance not found: {name}")
