import hashlib
try:
    import yaml
except ImportError:
    from nightctl_lib import yaml_shim as yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .job import Job


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Manifest:
    def __init__(self, manifest_file: Path):
        self.manifest_file = manifest_file
        self._data = self._load()

    def _load(self) -> dict:
        if self.manifest_file.exists():
            with open(self.manifest_file) as f:
                return yaml.safe_load(f) or self._empty()
        return self._empty()

    def _empty(self) -> dict:
        return {
            "generated": _now_iso(),
            "job_count": 0,
            "pending": 0,
            "done": 0,
            "failed": 0,
            "jobs": [],
        }

    def _entry_from_job(self, job: Job) -> dict:
        h = _file_hash(job.file_path) if job.file_path and job.file_path.exists() else ""
        return {
            "id": job.id,
            "file": str(job.file_path),
            "title": job.title,
            "schedule": job.schedule,
            "priority": job.priority,
            "status": job.status,
            "tags": job.tags,
            "depends_on": job.depends_on,
            "created": job.created,
            "hash": h,
        }

    def _recount(self):
        jobs = self._data.get("jobs", [])
        self._data["job_count"] = len(jobs)
        self._data["pending"] = sum(1 for j in jobs if j["status"] == "pending")
        self._data["done"] = sum(1 for j in jobs if j["status"] == "done")
        self._data["failed"] = sum(1 for j in jobs if j["status"] == "failed")

    def save(self):
        self._data["generated"] = _now_iso()
        self._recount()
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_file, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, sort_keys=False)

    def append(self, job: Job):
        entry = self._entry_from_job(job)
        jobs = self._data.setdefault("jobs", [])
        # remove stale entry if re-enqueueing same id
        self._data["jobs"] = [j for j in jobs if j["id"] != job.id]
        self._data["jobs"].append(entry)
        self.save()

    def update_status(self, job_id: str, status: str):
        for entry in self._data.get("jobs", []):
            if entry["id"] == job_id:
                entry["status"] = status
                break
        self.save()

    def get_entry(self, job_id: str) -> Optional[dict]:
        for entry in self._data.get("jobs", []):
            if entry["id"] == job_id:
                return entry
        return None

    def all_jobs(self) -> list:
        return list(self._data.get("jobs", []))

    def pending_jobs(self) -> list:
        return [j for j in self.all_jobs() if j["status"] == "pending"]

    def verify(self, jobs_dir: Path) -> list:
        results = []
        indexed_ids = set()

        for entry in self._data.get("jobs", []):
            job_id = entry["id"]
            indexed_ids.add(job_id)
            file_path = Path(entry["file"])

            if not file_path.exists():
                results.append({"status": "MISSING", "id": job_id, "file": str(file_path)})
                continue

            actual_hash = _file_hash(file_path)
            if actual_hash != entry.get("hash", ""):
                results.append({"status": "DRIFT", "id": job_id, "file": str(file_path)})
            else:
                results.append({"status": "MATCH", "id": job_id, "file": str(file_path)})

        # check for orphans — read id field directly (robust to any ID format)
        for yaml_file in jobs_dir.glob("*.yaml"):
            try:
                job = Job.from_file(yaml_file)
                job_id = job.id
            except Exception:
                job_id = yaml_file.stem
            if job_id not in indexed_ids:
                results.append({"status": "ORPHAN", "id": job_id, "file": str(yaml_file)})

        return results

    def rebuild(self, jobs_dir: Path):
        jobs_list = []
        errors = []

        for yaml_file in sorted(jobs_dir.glob("*.yaml")):
            try:
                job = Job.from_file(yaml_file)
                entry = self._entry_from_job(job)
                jobs_list.append(entry)
            except Exception as e:
                errors.append(f"{yaml_file.name}: {e}")

        self._data["jobs"] = jobs_list
        self.save()
        return len(jobs_list), errors

    def counts(self) -> dict:
        jobs = self._data.get("jobs", [])
        by_status = {}
        by_schedule = {}
        by_tag = {}
        for j in jobs:
            s = j.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
            sc = j.get("schedule", "unknown")
            by_schedule[sc] = by_schedule.get(sc, 0) + 1
            for t in (j.get("tags") or []):
                by_tag[t] = by_tag.get(t, 0) + 1
        return {
            "total": len(jobs),
            "by_status": by_status,
            "by_schedule": by_schedule,
            "by_tag": by_tag,
        }
