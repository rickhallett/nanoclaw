#!/usr/bin/env python3
"""
MacBook M5 → Arch Linux migration.

Transfers repos, config, and state over Tailscale SSH with full auditability.
Every operation is logged to a manifest with checksums. Dry-run by default.

Usage:
    python scripts/migrate.py                    # dry-run (default)
    python scripts/migrate.py --execute          # live run
    python scripts/migrate.py --execute --phase preflight   # just preflight
    python scripts/migrate.py --execute --phase transfer    # just transfer
    python scripts/migrate.py --verify           # verify a completed transfer
    python scripts/migrate.py --resume           # skip completed items
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARGET_HOST = "carbonx1"  # Tailscale hostname
REMOTE_USER = "kai"
REMOTE_HOME = f"/home/{REMOTE_USER}"
SSH_TARGET = f"{REMOTE_USER}@{TARGET_HOST}"  # user@host for all SSH/rsync

MANIFEST_DIR = Path.home() / ".migration"
MANIFEST_FILE = MANIFEST_DIR / "manifest.json"
LOG_FILE = MANIFEST_DIR / "migrate.log"

# Delay between transfers to avoid sshd rate limiting (seconds)
TRANSFER_DELAY = 3

RSYNC_EXCLUDE = [
    "node_modules",
    ".venv",
    "__pycache__",
    ".next",
    ".turbo",
    "target",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
]

# ---------------------------------------------------------------------------
# Inventory — single source of truth
# ---------------------------------------------------------------------------

CORE_REPOS = ["halo", "thepit", "dotfiles", "maclaw", "jobsworth"]

SECONDARY_REPOS = [
    "sortie-pi",
    "pidgeon",
    "pidgeon-swarm",
    "coldcase",
    "darkfactorio",
    "leash",
    "nine-bells",
    "noopit",
    "runnerboy",
    "superpowers",
]

CONFIG_ITEMS = [
    {"name": "ssh_keys", "src": "~/.ssh", "dst": ".ssh", "sensitive": True},
    {"name": "himalaya_config", "src": "~/.config/himalaya", "dst": ".config/himalaya"},
    {"name": "claude_config", "src": "~/.claude", "dst": ".claude"},
    {"name": "gitconfig", "src": "~/.gitconfig", "dst": ".gitconfig"},
    {"name": "gnupg", "src": "~/.gnupg", "dst": ".gnupg", "sensitive": True},
    {"name": "obsidian_vault", "src": "~/Documents/vault", "dst": "Documents/vault"},
]

HERMES_EXCLUDE = [
    "hermes-agent/venv",
    "checkpoints",
    "browser_screenshots",
    "sandboxes",
]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TransferItem:
    name: str
    source: str
    destination: str
    status: Status = Status.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    bytes_transferred: int = 0
    file_count: int = 0
    checksum: str | None = None
    error: str | None = None
    rsync_stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class Manifest:
    created: str = field(default_factory=lambda: _now())
    hostname: str = field(default_factory=lambda: os.uname().nodename)
    phase: str = "preflight"
    dry_run: bool = True
    items: list[TransferItem] = field(default_factory=list)
    preflight_checks: dict[str, Any] = field(default_factory=dict)

    def save(self) -> None:
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "created": self.created,
            "hostname": self.hostname,
            "phase": self.phase,
            "dry_run": self.dry_run,
            "items": [asdict(i) for i in self.items],
            "preflight_checks": self.preflight_checks,
        }
        # Atomic write
        tmp = MANIFEST_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.rename(MANIFEST_FILE)

    @classmethod
    def load(cls) -> Manifest | None:
        if not MANIFEST_FILE.exists():
            return None
        data = json.loads(MANIFEST_FILE.read_text())
        m = cls(
            created=data["created"],
            hostname=data["hostname"],
            phase=data.get("phase", "unknown"),
            dry_run=data.get("dry_run", True),
            preflight_checks=data.get("preflight_checks", {}),
        )
        for item_data in data.get("items", []):
            item_data["status"] = Status(item_data["status"])
            # Handle the rsync_stats field default
            if "rsync_stats" not in item_data:
                item_data["rsync_stats"] = {}
            m.items.append(TransferItem(**item_data))
        return m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log = logging.getLogger("migrate")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _expand(p: str) -> Path:
    return Path(p).expanduser()


def run(
    cmd: list[str],
    *,
    dry_run: bool = False,
    capture: bool = True,
    check: bool = True,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    """Run a command with full logging. In dry-run mode, log and skip."""
    flat = " ".join(cmd)
    if dry_run:
        log.info(f"[DRY-RUN] would run: {flat}")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    log.info(f"[RUN] {flat}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=check,
            timeout=timeout,
        )
        if result.stdout and result.stdout.strip():
            for line in result.stdout.strip().split("\n")[-5:]:
                log.debug(f"  stdout: {line}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed (exit {e.returncode}): {flat}")
        if e.stderr:
            for line in e.stderr.strip().split("\n")[-10:]:
                log.error(f"  stderr: {line}")
        raise
    except subprocess.TimeoutExpired:
        log.error(f"Command timed out after {timeout}s: {flat}")
        raise


def path_checksum(path: Path) -> str:
    """Quick content fingerprint. Works for both files and directories."""
    if not path.exists():
        return "MISSING"
    if path.is_file():
        stat = path.stat()
        entry = f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}"
        return hashlib.sha256(entry.encode()).hexdigest()[:16]
    entries = []
    for f in sorted(path.rglob("*")):
        if f.is_file():
            stat = f.stat()
            entries.append(f"{f.relative_to(path)}:{stat.st_size}:{int(stat.st_mtime)}")
    h = hashlib.sha256("\n".join(entries).encode()).hexdigest()[:16]
    return h


def path_stats(path: Path) -> tuple[int, int]:
    """Return (file_count, total_bytes) for a file or directory."""
    if not path.exists():
        return (0, 0)
    if path.is_file():
        return (1, path.stat().st_size)
    count = 0
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            count += 1
            total += f.stat().st_size
    return count, total


def parse_rsync_stats(output: str) -> dict[str, str]:
    """Extract key stats from rsync --stats output."""
    stats = {}
    for line in output.split("\n"):
        line = line.strip()
        for key in [
            "Number of files",
            "Number of regular files transferred",
            "Total file size",
            "Total transferred file size",
            "Total bytes sent",
            "Total bytes received",
        ]:
            if line.startswith(key):
                stats[key] = line.split(":", 1)[-1].strip()
    return stats


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def preflight(manifest: Manifest) -> bool:
    """Validate prerequisites. Returns True if safe to proceed."""
    checks: dict[str, Any] = {}
    ok = True

    # 1. Tailscale connectivity
    log.info("Checking Tailscale connectivity...")
    try:
        result = run(["ssh", "-o", "ConnectTimeout=5", SSH_TARGET, "echo ok"], check=True)
        checks["tailscale_ssh"] = "ok"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        checks["tailscale_ssh"] = "FAILED — cannot reach carbonx1 via SSH"
        ok = False

    # 2. rsync available locally and remotely
    for host_label, cmd in [("local", ["rsync", "--version"]), ("remote", ["ssh", SSH_TARGET, "rsync", "--version"])]:
        try:
            result = run(cmd, check=True, timeout=10)
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            checks[f"rsync_{host_label}"] = version_line.strip()
        except Exception as e:
            checks[f"rsync_{host_label}"] = f"FAILED — {e}"
            ok = False

    # 3. Disk space on target
    try:
        result = run(["ssh", SSH_TARGET, "df", "-h", REMOTE_HOME], check=True, timeout=10)
        checks["remote_disk"] = result.stdout.strip().split("\n")[-1] if result.stdout else "unknown"
    except Exception:
        checks["remote_disk"] = "FAILED — could not check"
        ok = False

    # 4. Source inventory exists
    missing = []
    for repo in CORE_REPOS:
        p = Path.home() / "code" / repo
        if not p.exists():
            missing.append(str(p))
    for item in CONFIG_ITEMS:
        p = _expand(item["src"])
        if not p.exists():
            missing.append(str(p))
    if not (Path.home() / ".hermes").exists():
        missing.append("~/.hermes")
    checks["missing_sources"] = missing or "none"
    if missing:
        log.warning(f"Missing sources (will be skipped): {missing}")

    # 5. Unpushed git repos
    log.info("Checking for unpushed commits...")
    unpushed = []
    for repo in CORE_REPOS + SECONDARY_REPOS:
        repo_path = Path.home() / "code" / repo
        if not repo_path.exists():
            continue
        try:
            result = run(
                ["git", "-C", str(repo_path), "status", "--porcelain"],
                check=True,
                timeout=10,
            )
            if result.stdout and result.stdout.strip():
                unpushed.append(f"{repo}: uncommitted changes")

            result = run(
                ["git", "-C", str(repo_path), "log", "--oneline", "@{u}..HEAD"],
                check=False,
                timeout=10,
            )
            if result.stdout and result.stdout.strip():
                unpushed.append(f"{repo}: {len(result.stdout.strip().split(chr(10)))} unpushed commits")
        except Exception:
            pass  # No upstream tracking, that's fine
    checks["unpushed"] = unpushed or "none"
    if unpushed:
        log.warning(f"Unpushed work: {unpushed}")

    # 6. Export reference lists
    log.info("Exporting reference lists...")
    ref_dir = MANIFEST_DIR / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)

    for name, cmd in [
        ("brew-formulas.txt", ["brew", "list", "--formula"]),
        ("brew-casks.txt", ["brew", "list", "--cask"]),
        ("uv-tools.txt", ["uv", "tool", "list"]),
        ("crontab.txt", ["crontab", "-l"]),
    ]:
        try:
            result = run(cmd, check=False, timeout=15)
            (ref_dir / name).write_text(result.stdout or "")
            checks[f"export_{name}"] = "ok"
        except Exception as e:
            checks[f"export_{name}"] = f"failed: {e}"

    manifest.preflight_checks = checks
    manifest.save()

    # Print summary
    print("\n" + "=" * 60)
    print("PREFLIGHT SUMMARY")
    print("=" * 60)
    for k, v in checks.items():
        icon = "+" if v == "ok" or v == "none" else "!"
        print(f"  [{icon}] {k}: {v}")
    print("=" * 60)

    return ok


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------


def build_rsync_cmd(
    source: str | Path,
    dest_path: str,
    *,
    extra_excludes: list[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Build an rsync command with standard options."""
    src_path = Path(source).expanduser()
    is_file = src_path.is_file()

    cmd = [
        "rsync",
        "-avz",
        "--stats",
        "--human-readable",
        "--progress",
    ]
    if dry_run:
        cmd.append("--dry-run")
    if not is_file:
        for exc in RSYNC_EXCLUDE:
            cmd.extend(["--exclude", exc])
        for exc in extra_excludes or []:
            cmd.extend(["--exclude", exc])

    src = str(src_path)
    if not is_file and not src.endswith("/"):
        src += "/"
    cmd.append(src)

    # For files: dest is the full remote path. For dirs: dest ends with /
    if is_file:
        cmd.append(f"{SSH_TARGET}:{dest_path}")
    else:
        cmd.append(f"{SSH_TARGET}:{dest_path}/")
    return cmd


def transfer_item(item: TransferItem, *, dry_run: bool, manifest: Manifest) -> None:
    """Execute a single transfer and update the manifest."""
    src = _expand(item.source)
    if not src.exists():
        item.status = Status.SKIPPED
        item.error = f"source does not exist: {src}"
        log.warning(f"Skipping {item.name}: {item.error}")
        manifest.save()
        return

    item.status = Status.RUNNING
    item.started_at = _now()
    item.checksum = path_checksum(src)
    file_count, byte_count = path_stats(src)
    item.file_count = file_count
    item.bytes_transferred = byte_count
    manifest.save()

    log.info(f"Transferring {item.name}: {src} → {SSH_TARGET}:{item.destination}")
    log.info(f"  Source: {file_count} files, {byte_count / 1_048_576:.1f} MB, checksum={item.checksum}")

    # Ensure remote parent directory exists (macOS openrsync lacks --mkpath)
    remote_parent = str(Path(item.destination).parent) if _expand(item.source).is_file() else item.destination
    try:
        run(["ssh", SSH_TARGET, "mkdir", "-p", remote_parent], check=True, timeout=10)
    except subprocess.CalledProcessError:
        log.warning(f"  mkdir failed for {remote_parent} — rsync may still succeed")

    extra_excludes = HERMES_EXCLUDE if "hermes" in item.name else None
    cmd = build_rsync_cmd(src, item.destination, extra_excludes=extra_excludes, dry_run=dry_run)

    try:
        # rsync with --progress writes to stdout continuously; let it stream
        result = run(cmd, dry_run=False, timeout=1800)  # 30 min max per item
        item.rsync_stats = parse_rsync_stats(result.stdout or "")
        item.status = Status.DONE
        item.finished_at = _now()
        log.info(f"  Completed: {item.name}")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        item.status = Status.FAILED
        item.finished_at = _now()
        item.error = str(e)
        log.error(f"  FAILED: {item.name} — {e}")

    manifest.save()


def build_transfer_items() -> list[TransferItem]:
    """Build the full transfer list from inventory."""
    items: list[TransferItem] = []

    # Core repos
    for repo in CORE_REPOS:
        items.append(TransferItem(
            name=f"repo:{repo}",
            source=f"~/code/{repo}",
            destination=f"{REMOTE_HOME}/code/{repo}",
        ))

    # Secondary repos
    for repo in SECONDARY_REPOS:
        items.append(TransferItem(
            name=f"repo:{repo}",
            source=f"~/code/{repo}",
            destination=f"{REMOTE_HOME}/code/{repo}",
        ))

    # Config items
    for item in CONFIG_ITEMS:
        items.append(TransferItem(
            name=f"config:{item['name']}",
            source=item["src"],
            destination=f"{REMOTE_HOME}/{item['dst']}",
        ))

    # Hermes state
    items.append(TransferItem(
        name="hermes:state",
        source="~/.hermes",
        destination=f"{REMOTE_HOME}/.hermes",
    ))

    # Cookies file (watchctl dependency)
    items.append(TransferItem(
        name="config:cookies",
        source="~/code/halo/cookies.txt",
        destination=f"{REMOTE_HOME}/code/halo/cookies.txt",
    ))

    # Reference files from preflight
    items.append(TransferItem(
        name="meta:references",
        source=str(MANIFEST_DIR / "references"),
        destination=f"{REMOTE_HOME}/.migration/references",
    ))

    return items


def transfer(manifest: Manifest, *, dry_run: bool, resume: bool) -> None:
    """Run the transfer phase."""
    if not manifest.items:
        manifest.items = build_transfer_items()

    total = len(manifest.items)
    for i, item in enumerate(manifest.items, 1):
        if resume and item.status == Status.DONE:
            log.info(f"[{i}/{total}] Skipping (already done): {item.name}")
            continue

        print(f"\n[{i}/{total}] {item.name}")
        print(f"  {item.source} → {item.destination}")

        if dry_run:
            src = _expand(item.source)
            if src.exists():
                fc, bc = path_stats(src)
                print(f"  Would transfer: {fc} files, {bc / 1_048_576:.1f} MB")
                item.status = Status.PENDING
                item.checksum = path_checksum(src)
                item.file_count = fc
                item.bytes_transferred = bc
            else:
                print(f"  Source missing — would skip")
                item.status = Status.SKIPPED
        else:
            transfer_item(item, dry_run=False, manifest=manifest)
            if i < total and TRANSFER_DELAY > 0:
                log.debug(f"  Waiting {TRANSFER_DELAY}s before next transfer...")
                time.sleep(TRANSFER_DELAY)

    manifest.save()
    print_summary(manifest)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify(manifest: Manifest) -> None:
    """Verify a completed transfer by comparing local checksums with manifest."""
    if not manifest.items:
        print("No manifest items found. Run a transfer first.")
        return

    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    issues = []
    for item in manifest.items:
        if item.status != Status.DONE:
            continue
        src = _expand(item.source)
        current = path_checksum(src)
        if item.checksum and current != item.checksum:
            issues.append(f"{item.name}: source changed since transfer (was {item.checksum}, now {current})")
            print(f"  [!] {item.name}: SOURCE CHANGED since transfer")
        else:
            print(f"  [+] {item.name}: checksum matches ({current})")

    # Remote spot-check: verify key directories exist
    print("\nRemote spot-checks:")
    spot_checks = [
        f"{REMOTE_HOME}/code/halo/.git",
        f"{REMOTE_HOME}/.ssh/id_ed25519",
        f"{REMOTE_HOME}/.hermes",
        f"{REMOTE_HOME}/.claude",
    ]
    for path in spot_checks:
        try:
            result = run(["ssh", SSH_TARGET, "test", "-e", path, "&&", "echo", "exists"], check=False, timeout=10)
            exists = "exists" in (result.stdout or "")
            icon = "+" if exists else "!"
            print(f"  [{icon}] {path}: {'exists' if exists else 'MISSING'}")
            if not exists:
                issues.append(f"Remote missing: {path}")
        except Exception as e:
            print(f"  [?] {path}: could not check — {e}")

    print(f"\n{'All clear.' if not issues else f'{len(issues)} issue(s) found.'}")
    for issue in issues:
        print(f"  - {issue}")


# ---------------------------------------------------------------------------
# Post-flight (runs on target via SSH)
# ---------------------------------------------------------------------------

# Commands that require sudo — shown but not auto-run
POSTFLIGHT_SUDO_CMDS = """
# Run these manually on carbonx1:

sudo pacman -S --needed \\
    python python-pip uv \\
    nodejs npm \\
    git github-cli \\
    docker docker-compose \\
    bat eza fzf ripgrep \\
    openssh gnupg \\
    aerc \\
    base-devel

# AUR packages (requires yay or paru):
# yay -S --needed google-chrome-stable claude-code himalaya-git
"""

POSTFLIGHT_STEPS: list[dict[str, str]] = [
    {
        "name": "Fix SSH permissions",
        "cmd": "chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_* && chmod 644 ~/.ssh/*.pub 2>/dev/null; echo done",
    },
    {
        "name": "Verify git identity",
        "cmd": "git config --global user.name && git config --global user.email",
    },
    {
        "name": "Test GitHub SSH",
        "cmd": "ssh -T git@github.com 2>&1 | head -1 || true",
    },
    {
        "name": "uv sync halo",
        "cmd": "cd ~/code/halo && uv sync 2>&1 | tail -3",
    },
    {
        "name": "uv sync thepit",
        "cmd": "cd ~/code/thepit && uv sync 2>&1 | tail -3",
    },
    {
        "name": "uv sync maclaw",
        "cmd": "cd ~/code/maclaw && uv sync 2>&1 | tail -3",
    },
    {
        "name": "uv sync jobsworth",
        "cmd": "cd ~/code/jobsworth && uv sync 2>&1 | tail -3",
    },
    {
        "name": "Reinstall uv tools",
        "cmd": (
            "if [ -f ~/.migration/references/uv-tools.txt ]; then "
            "awk '{print $1}' ~/.migration/references/uv-tools.txt | head -20 | xargs -I{} uv tool install {} 2>&1 | tail -5; "
            "else echo 'no uv-tools.txt found'; fi"
        ),
    },
    {
        "name": "Verify halo tools",
        "cmd": "cd ~/code/halo && uv run memctl stats 2>&1 | head -3",
    },
    {
        "name": "Verify trackctl",
        "cmd": "cd ~/code/halo && uv run trackctl domains 2>&1",
    },
    {
        "name": "Verify nightctl",
        "cmd": "cd ~/code/halo && uv run nightctl graph 2>&1 | head -10",
    },
    {
        "name": "Verify hermes state",
        "cmd": "ls -la ~/.hermes/ | head -10",
    },
    {
        "name": "Tailscale status",
        "cmd": "tailscale status 2>&1 | head -5",
    },
    {
        "name": "Install cronctl crontab",
        "cmd": "cd ~/code/halo && uv run cronctl install --execute 2>&1 | tail -3",
    },
]

POSTFLIGHT_CONFIDENCE = [
    {"name": "hermes responds", "cmd": "which hermes 2>/dev/null && hermes --version 2>&1 || echo 'hermes not on PATH yet'"},
    {"name": "memctl returns notes", "cmd": "cd ~/code/halo && uv run memctl stats 2>&1 | grep -i note"},
    {"name": "git push works", "cmd": "cd ~/code/halo && git remote -v | head -2"},
    {"name": "trackctl streak", "cmd": "cd ~/code/halo && uv run trackctl streak movement 2>&1 || echo 'no movement domain'"},
]


def postflight(*, dry_run: bool) -> None:
    """Run post-flight setup on target via SSH."""
    print("\n" + "=" * 60)
    print("POST-FLIGHT SETUP")
    print("=" * 60)

    # Show sudo commands (never auto-run)
    print("\n--- Manual steps (require sudo on carbonx1) ---")
    print(POSTFLIGHT_SUDO_CMDS)

    # Auto steps
    print("--- Automated steps (via SSH) ---\n")
    results: list[tuple[str, bool, str]] = []

    for step in POSTFLIGHT_STEPS:
        print(f"  [{len(results)+1}/{len(POSTFLIGHT_STEPS)}] {step['name']}...")
        if dry_run:
            print(f"    [DRY-RUN] would run: {step['cmd'][:80]}...")
            results.append((step["name"], True, "dry-run"))
            continue

        try:
            result = run(
                ["ssh", SSH_TARGET, step["cmd"]],
                check=False,
                timeout=120,
            )
            output = (result.stdout or "").strip()
            ok = result.returncode == 0
            icon = "+" if ok else "!"
            print(f"    [{icon}] {output[:200] if output else '(no output)'}")
            results.append((step["name"], ok, output[:200]))
        except Exception as e:
            print(f"    [!] FAILED: {e}")
            results.append((step["name"], False, str(e)))

    # Confidence checks
    print("\n--- Confidence checks ---\n")
    for check in POSTFLIGHT_CONFIDENCE:
        print(f"  {check['name']}...")
        if dry_run:
            print(f"    [DRY-RUN] would run: {check['cmd'][:80]}...")
            continue
        try:
            result = run(["ssh", SSH_TARGET, check["cmd"]], check=False, timeout=30)
            output = (result.stdout or "").strip()
            icon = "+" if result.returncode == 0 and output else "!"
            print(f"    [{icon}] {output[:200] if output else '(no output)'}")
        except Exception as e:
            print(f"    [?] {e}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{'=' * 60}")
    print(f"POST-FLIGHT: {passed} passed, {failed} failed")
    print("=" * 60)
    if failed:
        for name, ok, output in results:
            if not ok:
                print(f"  [!] {name}: {output[:100]}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(manifest: Manifest) -> None:
    done = [i for i in manifest.items if i.status == Status.DONE]
    failed = [i for i in manifest.items if i.status == Status.FAILED]
    skipped = [i for i in manifest.items if i.status == Status.SKIPPED]
    pending = [i for i in manifest.items if i.status == Status.PENDING]

    total_bytes = sum(i.bytes_transferred for i in done)

    print("\n" + "=" * 60)
    print(f"TRANSFER SUMMARY  {'(DRY RUN)' if manifest.dry_run else ''}")
    print("=" * 60)
    print(f"  Done:    {len(done)}")
    print(f"  Failed:  {len(failed)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  Pending: {len(pending)}")
    print(f"  Data:    {total_bytes / 1_048_576:.1f} MB across {sum(i.file_count for i in done)} files")
    print(f"  Manifest: {MANIFEST_FILE}")

    if failed:
        print("\nFailed items:")
        for item in failed:
            print(f"  - {item.name}: {item.error}")

    if skipped:
        print("\nSkipped items:")
        for item in skipped:
            print(f"  - {item.name}: {item.error or 'source not found'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MacBook → Arch Linux migration with full auditability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Phases:
  preflight  — validate connectivity, check for unpushed work, export refs
  transfer   — rsync all inventory items to target
  verify     — compare checksums and spot-check remote

Safety:
  Dry-run by default. Pass --execute to actually transfer.
  Manifest saved to ~/.migration/manifest.json after every item.
  Resume with --resume to skip completed items.
        """,
    )
    parser.add_argument("--execute", action="store_true", help="actually run (default is dry-run)")
    parser.add_argument("--resume", action="store_true", help="skip already-completed items")
    parser.add_argument("--verify", action="store_true", help="verify a completed transfer")
    parser.add_argument("--phase", choices=["preflight", "transfer", "postflight", "all"], default="all")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # Directories
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    # Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, mode="a"),
        ],
    )

    dry_run = not args.execute

    if dry_run and not args.verify:
        log.info("DRY RUN — no data will be transferred. Pass --execute to go live.")

    # Load or create manifest
    manifest = None
    if args.resume or args.verify:
        manifest = Manifest.load()
        if manifest is None:
            log.error("No manifest found. Run a transfer first.")
            sys.exit(1)

    if args.verify:
        assert manifest is not None
        verify(manifest)
        return

    if manifest is None:
        manifest = Manifest(dry_run=dry_run)

    manifest.dry_run = dry_run

    # Preflight
    if args.phase in ("preflight", "all"):
        manifest.phase = "preflight"
        manifest.save()
        ok = preflight(manifest)
        if not ok and args.execute:
            log.error("Preflight failed. Fix issues above before running with --execute.")
            sys.exit(1)
        if args.phase == "preflight":
            return

    # Transfer
    if args.phase in ("transfer", "all"):
        manifest.phase = "transfer"
        manifest.save()
        transfer(manifest, dry_run=dry_run, resume=args.resume)

    # Post-flight
    if args.phase in ("postflight", "all"):
        postflight(dry_run=dry_run)


if __name__ == "__main__":
    main()
