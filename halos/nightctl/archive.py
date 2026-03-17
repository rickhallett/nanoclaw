import shutil
try:
    import yaml
except ImportError:
    from . import yaml_shim as yaml
from datetime import datetime, timezone
from pathlib import Path

from .job import Job
from .manifest import Manifest


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _days_old(created_str: str) -> float:
    try:
        dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return delta.total_seconds() / 86400
    except Exception:
        return 0.0


ARCHIVABLE_STATUSES = {"done", "failed", "cancelled"}


def run_archive(cfg, manifest: Manifest, execute: bool = False, since: str = None) -> dict:
    retention_days = cfg.archive.get("retention_days", 30)
    archive_dir = cfg.archive_dir
    archive_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for entry in manifest.all_jobs():
        if entry["status"] not in ARCHIVABLE_STATUSES:
            continue
        age = _days_old(entry.get("created", ""))
        if age < retention_days:
            continue
        if since:
            # only jobs created before 'since'
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                job_dt = datetime.fromisoformat(entry.get("created", "").replace("Z", "+00:00"))
                if job_dt >= since_dt:
                    continue
            except Exception:
                pass
        candidates.append(entry)

    results = {"candidates": len(candidates), "archived": 0, "dry_run": not execute}

    for entry in candidates:
        file_path = Path(entry["file"])
        job_id = entry["id"]
        archived_name = f"{job_id}-archived-{datetime.now(timezone.utc).strftime('%Y%m%d')}.yaml"
        dest = archive_dir / archived_name

        if not execute:
            print(f"  CANDIDATE  {job_id}  {entry['title']}  age={_days_old(entry.get('created','')):.1f}d")
            continue

        if file_path.exists():
            shutil.move(str(file_path), str(dest))

        # write tombstone as separate file (preserves original data in dest)
        tombstone_name = f"{job_id}-tombstone-{datetime.now(timezone.utc).strftime('%Y%m%d')}.yaml"
        tombstone_path = archive_dir / tombstone_name
        tombstone = {
            "id": job_id,
            "title": entry["title"],
            "status": "archived",
            "archived_at": _now_iso(),
            "reason": f"age={_days_old(entry.get('created','')):.1f}d >= retention={retention_days}d",
            "original_file": str(file_path),
            "archive_file": str(dest),
        }
        with open(tombstone_path, "w") as f:
            yaml.dump(tombstone, f, default_flow_style=False, sort_keys=False)

        manifest.update_status(job_id, "archived")
        results["archived"] += 1
        print(f"  ARCHIVED   {job_id}  {entry['title']}")

    return results


def run_hatch(cfg, execute: bool = False, before: str = None) -> dict:
    """Permanently eject archived jobs. Destructive. Requires explicit --execute."""
    if cfg.archive.get("dry_run", True) and execute:
        print("ERROR: archive.dry_run is true in config. Set to false to enable hatch --execute.")
        return {"ejected": 0, "error": "dry_run=true in config"}

    archive_dir = cfg.archive_dir
    if not archive_dir.exists():
        return {"ejected": 0, "candidates": 0}

    candidates = []
    for yaml_file in archive_dir.glob("*-archived-*.yaml"):
        if before:
            try:
                before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
                mtime = datetime.fromtimestamp(yaml_file.stat().st_mtime, tz=timezone.utc)
                if mtime >= before_dt:
                    continue
            except Exception:
                pass
        candidates.append(yaml_file)

    results = {"candidates": len(candidates), "ejected": 0, "dry_run": not execute}

    for f in candidates:
        if not execute:
            print(f"  CANDIDATE  {f.name}")
            continue
        f.unlink()
        results["ejected"] += 1
        print(f"  EJECTED    {f.name}")

    return results
