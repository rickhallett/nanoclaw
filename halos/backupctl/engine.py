"""Backup engine — restic backend with tar fallback.

SQLite safety: before backing up directories containing .db files,
uses sqlite3.backup() to create consistent copies in a temp directory.
"""

import glob as globmod
import json
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from halos.common.log import hlog

from .config import BackupConfig, BackupTarget, resolve_paths


def _has_restic() -> bool:
    """Check if restic is installed and accessible."""
    return shutil.which("restic") is not None


def _restic_env(cfg: BackupConfig) -> dict[str, str]:
    """Build environment variables for restic commands."""
    import os
    env = dict(os.environ)
    env["RESTIC_REPOSITORY"] = str(cfg.repository)
    if cfg.password_file and cfg.password_file.exists():
        env["RESTIC_PASSWORD_FILE"] = str(cfg.password_file)
    elif not env.get("RESTIC_PASSWORD"):
        # Use a default password for local-only repos without explicit config
        env["RESTIC_PASSWORD"] = "nanoclaw-local-backup"
    return env


def _init_restic_repo(cfg: BackupConfig) -> bool:
    """Initialize restic repository if it doesn't exist."""
    env = _restic_env(cfg)
    try:
        result = subprocess.run(
            ["restic", "snapshots", "--json"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return True  # Already initialized
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

    # Initialize
    cfg.repository.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["restic", "init"],
            env=env, capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            hlog("backupctl", "info", "repo_initialized", {
                "repository": str(cfg.repository),
            })
            return True
        hlog("backupctl", "error", "repo_init_failed", {
            "stderr": result.stderr[:500],
        })
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _safe_copy_sqlite(db_path: Path, dest_dir: Path) -> Path:
    """Create a consistent copy of a SQLite database using sqlite3.backup().

    Args:
        db_path: Path to the source .db file.
        dest_dir: Directory to write the backup copy into.

    Returns:
        Path to the backup copy.
    """
    dest = dest_dir / db_path.name
    src_conn = sqlite3.connect(str(db_path))
    dst_conn = sqlite3.connect(str(dest))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    hlog("backupctl", "info", "sqlite_backup", {
        "source": str(db_path),
        "dest": str(dest),
        "size_bytes": dest.stat().st_size,
    })
    return dest


def _prepare_backup_paths(
    target: BackupTarget, repo_root: Path, tmp_dir: Path,
) -> list[Path]:
    """Prepare paths for backup, handling SQLite files safely.

    For directories containing .db files, creates safe copies in tmp_dir
    and returns the tmp path instead. For other paths, returns them directly.
    """
    resolved = resolve_paths(target, repo_root)
    result_paths: list[Path] = []

    for p in resolved:
        if p.is_dir():
            db_files = list(p.glob("*.db"))
            if db_files:
                # Copy the whole directory, replacing .db files with safe copies
                target_tmp = tmp_dir / p.name
                shutil.copytree(p, target_tmp, ignore=shutil.ignore_patterns("*.db"))
                for db_file in db_files:
                    _safe_copy_sqlite(db_file, target_tmp)
                result_paths.append(target_tmp)
            else:
                result_paths.append(p)
        elif p.is_file():
            if p.suffix == ".db":
                _safe_copy_sqlite(p, tmp_dir)
                result_paths.append(tmp_dir / p.name)
            else:
                result_paths.append(p)

    return result_paths


def run_backup(
    cfg: BackupConfig,
    target_name: Optional[str] = None,
) -> dict[str, dict]:
    """Execute backup for one or all targets.

    Args:
        cfg: Backup configuration.
        target_name: Specific target to back up, or None for all.

    Returns:
        Dict mapping target name to result dict with keys:
        success (bool), backend (str), detail (str).
    """
    if target_name:
        if target_name not in cfg.targets:
            return {target_name: {
                "success": False,
                "backend": "none",
                "detail": f"unknown target: {target_name}",
            }}
        targets = {target_name: cfg.targets[target_name]}
    else:
        targets = cfg.targets

    use_restic = _has_restic()
    results: dict[str, dict] = {}

    for name, target in targets.items():
        with tempfile.TemporaryDirectory(prefix=f"backupctl-{name}-") as tmp:
            tmp_dir = Path(tmp)
            paths = _prepare_backup_paths(target, cfg.repo_root, tmp_dir)

            if not paths:
                results[name] = {
                    "success": False,
                    "backend": "none",
                    "detail": "no paths resolved (files may not exist)",
                }
                continue

            if use_restic:
                results[name] = _backup_restic(cfg, name, paths)
            else:
                results[name] = _backup_tar(cfg, name, paths)

    return results


def _backup_restic(
    cfg: BackupConfig, target_name: str, paths: list[Path],
) -> dict:
    """Back up using restic."""
    if not _init_restic_repo(cfg):
        return {
            "success": False,
            "backend": "restic",
            "detail": "failed to initialize restic repository",
        }

    env = _restic_env(cfg)
    cmd = ["restic", "backup", "--tag", target_name]
    cmd.extend(str(p) for p in paths)

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            hlog("backupctl", "info", "backup_completed", {
                "target": target_name,
                "backend": "restic",
            })
            return {
                "success": True,
                "backend": "restic",
                "detail": result.stdout.strip().split("\n")[-1] if result.stdout else "ok",
            }
        return {
            "success": False,
            "backend": "restic",
            "detail": result.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "backend": "restic",
            "detail": "backup timed out (5 min limit)",
        }


def _backup_tar(
    cfg: BackupConfig, target_name: str, paths: list[Path],
) -> dict:
    """Back up using tar (fallback when restic is unavailable)."""
    tar_dir = cfg.repository / "tar"
    tar_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tar_path = tar_dir / f"backup-{target_name}-{timestamp}.tar.gz"

    cmd = ["tar", "czf", str(tar_path)]
    cmd.extend(str(p) for p in paths)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            size = tar_path.stat().st_size
            hlog("backupctl", "info", "backup_completed", {
                "target": target_name,
                "backend": "tar",
                "path": str(tar_path),
                "size_bytes": size,
            })
            return {
                "success": True,
                "backend": "tar",
                "detail": f"{tar_path.name} ({size:,} bytes)",
            }
        return {
            "success": False,
            "backend": "tar",
            "detail": result.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "backend": "tar",
            "detail": "tar timed out (5 min limit)",
        }


def list_snapshots(
    cfg: BackupConfig,
    target_name: Optional[str] = None,
) -> list[dict]:
    """List available backup snapshots.

    Returns list of dicts with keys: id, time, target, backend, paths.
    """
    if _has_restic():
        return _list_restic_snapshots(cfg, target_name)
    return _list_tar_snapshots(cfg, target_name)


def _list_restic_snapshots(
    cfg: BackupConfig, target_name: Optional[str] = None,
) -> list[dict]:
    """List snapshots from restic repository."""
    env = _restic_env(cfg)
    cmd = ["restic", "snapshots", "--json"]
    if target_name:
        cmd.extend(["--tag", target_name])

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []

        raw = json.loads(result.stdout) if result.stdout.strip() else []
        snapshots = []
        for s in raw:
            tags = s.get("tags", [])
            snapshots.append({
                "id": s.get("short_id", s.get("id", "?")[:8]),
                "time": s.get("time", ""),
                "target": tags[0] if tags else "unknown",
                "backend": "restic",
                "paths": s.get("paths", []),
            })
        return snapshots
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return []


def _list_tar_snapshots(
    cfg: BackupConfig, target_name: Optional[str] = None,
) -> list[dict]:
    """List tar backup files."""
    tar_dir = cfg.repository / "tar"
    if not tar_dir.exists():
        return []

    pattern = f"backup-{target_name}-*.tar.gz" if target_name else "backup-*.tar.gz"
    files = sorted(tar_dir.glob(pattern), reverse=True)

    snapshots = []
    for f in files:
        # Parse target name and timestamp from filename
        # Format: backup-{target}-{YYYYMMDD-HHMMSS}.tar.gz
        stem = f.stem.replace(".tar", "")  # remove .tar from .tar.gz
        parts = stem.split("-", 2)  # ["backup", target, timestamp]
        target = parts[1] if len(parts) > 1 else "unknown"
        ts_raw = parts[2] if len(parts) > 2 else ""

        snapshots.append({
            "id": f.name,
            "time": ts_raw,
            "target": target,
            "backend": "tar",
            "paths": [str(f)],
            "size_bytes": f.stat().st_size,
        })

    return snapshots


def verify_repository(cfg: BackupConfig) -> dict:
    """Verify backup repository integrity.

    Returns dict with keys: success (bool), backend (str), detail (str).
    """
    if _has_restic():
        return _verify_restic(cfg)
    return _verify_tar(cfg)


def _verify_restic(cfg: BackupConfig) -> dict:
    """Verify restic repository."""
    env = _restic_env(cfg)
    try:
        result = subprocess.run(
            ["restic", "check"],
            env=env, capture_output=True, text=True, timeout=120,
        )
        success = result.returncode == 0
        return {
            "success": success,
            "backend": "restic",
            "detail": result.stdout.strip() if success else result.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "backend": "restic",
            "detail": "verification timed out",
        }


def _verify_tar(cfg: BackupConfig) -> dict:
    """Verify tar backups by testing integrity of each archive."""
    tar_dir = cfg.repository / "tar"
    if not tar_dir.exists():
        return {
            "success": False,
            "backend": "tar",
            "detail": "no tar backup directory found",
        }

    files = list(tar_dir.glob("backup-*.tar.gz"))
    if not files:
        return {
            "success": True,
            "backend": "tar",
            "detail": "no backups to verify",
        }

    bad = []
    for f in files:
        try:
            result = subprocess.run(
                ["tar", "tzf", str(f)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                bad.append(f.name)
        except subprocess.TimeoutExpired:
            bad.append(f"{f.name} (timeout)")

    if bad:
        return {
            "success": False,
            "backend": "tar",
            "detail": f"corrupt archives: {', '.join(bad)}",
        }
    return {
        "success": True,
        "backend": "tar",
        "detail": f"all {len(files)} archives verified",
    }


def restore_snapshot(
    cfg: BackupConfig,
    target_name: str,
    snapshot_id: str,
    restore_to: Path,
) -> dict:
    """Restore a specific snapshot.

    Args:
        cfg: Backup configuration.
        target_name: Target name (used for tar lookups).
        snapshot_id: Snapshot ID (restic short_id) or tar filename.
        restore_to: Directory to restore into (must be explicit).

    Returns:
        Dict with keys: success (bool), backend (str), detail (str).
    """
    restore_to.mkdir(parents=True, exist_ok=True)

    if _has_restic() and not snapshot_id.endswith(".tar.gz"):
        return _restore_restic(cfg, snapshot_id, restore_to)
    return _restore_tar(cfg, snapshot_id, restore_to)


def _restore_restic(
    cfg: BackupConfig, snapshot_id: str, restore_to: Path,
) -> dict:
    """Restore from restic."""
    env = _restic_env(cfg)
    try:
        result = subprocess.run(
            ["restic", "restore", snapshot_id, "--target", str(restore_to)],
            env=env, capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            hlog("backupctl", "info", "restore_completed", {
                "snapshot": snapshot_id,
                "target": str(restore_to),
                "backend": "restic",
            })
            return {
                "success": True,
                "backend": "restic",
                "detail": f"restored {snapshot_id} to {restore_to}",
            }
        return {
            "success": False,
            "backend": "restic",
            "detail": result.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "backend": "restic",
            "detail": "restore timed out",
        }


def _restore_tar(
    cfg: BackupConfig, snapshot_id: str, restore_to: Path,
) -> dict:
    """Restore from tar backup."""
    tar_dir = cfg.repository / "tar"
    tar_path = tar_dir / snapshot_id

    if not tar_path.exists():
        # Try matching by prefix
        matches = list(tar_dir.glob(f"*{snapshot_id}*"))
        if len(matches) == 1:
            tar_path = matches[0]
        elif len(matches) > 1:
            return {
                "success": False,
                "backend": "tar",
                "detail": f"ambiguous snapshot ID, matches: {[m.name for m in matches]}",
            }
        else:
            return {
                "success": False,
                "backend": "tar",
                "detail": f"snapshot not found: {snapshot_id}",
            }

    try:
        result = subprocess.run(
            ["tar", "xzf", str(tar_path), "-C", str(restore_to)],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            hlog("backupctl", "info", "restore_completed", {
                "snapshot": snapshot_id,
                "target": str(restore_to),
                "backend": "tar",
            })
            return {
                "success": True,
                "backend": "tar",
                "detail": f"restored {tar_path.name} to {restore_to}",
            }
        return {
            "success": False,
            "backend": "tar",
            "detail": result.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "backend": "tar",
            "detail": "restore timed out",
        }


def get_last_backup_age(cfg: BackupConfig) -> Optional[float]:
    """Return hours since the most recent backup, or None if no backups exist."""
    snapshots = list_snapshots(cfg)
    if not snapshots:
        return None

    now = datetime.now(timezone.utc)

    # Try parsing timestamps
    for s in snapshots:
        time_str = s.get("time", "")
        if not time_str:
            continue
        # restic format: 2026-03-21T10:30:00.123456Z
        # tar format: YYYYMMDD-HHMMSS
        try:
            if "T" in time_str:
                ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            else:
                ts = datetime.strptime(time_str, "%Y%m%d-%H%M%S").replace(
                    tzinfo=timezone.utc
                )
            age_hours = (now - ts).total_seconds() / 3600
            return age_hours
        except (ValueError, TypeError):
            continue

    return None


def get_target_stats(
    cfg: BackupConfig, target_name: str,
) -> dict:
    """Get stats for a specific target.

    Returns dict with: snapshot_count, total_size_bytes (tar only).
    """
    snapshots = list_snapshots(cfg, target_name)
    total_size = sum(s.get("size_bytes", 0) for s in snapshots)
    return {
        "snapshot_count": len(snapshots),
        "total_size_bytes": total_size,
    }
