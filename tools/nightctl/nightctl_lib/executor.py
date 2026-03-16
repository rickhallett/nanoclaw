import subprocess
try:
    import yaml
except ImportError:
    from nightctl_lib import yaml_shim as yaml
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .job import Job
from .manifest import Manifest
from .notify import Notifier


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_window(window_str: str):
    """Parse 'HH:MM-HH:MM' into (start_hour, start_min, end_hour, end_min)."""
    start_s, end_s = window_str.split("-")
    sh, sm = map(int, start_s.split(":"))
    eh, em = map(int, end_s.split(":"))
    return sh, sm, eh, em


def _in_window(window_str: str, tz_name: str) -> bool:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    now = datetime.now(tz)
    sh, sm, eh, em = _parse_window(window_str)
    start_mins = sh * 60 + sm
    end_mins = eh * 60 + em
    now_mins = now.hour * 60 + now.minute
    if start_mins <= end_mins:
        return start_mins <= now_mins < end_mins
    # overnight window crosses midnight
    return now_mins >= start_mins or now_mins < end_mins


def _run_record(job_id: str, attempt: int, started: str, finished: str,
                exit_code: int, stdout: str, stderr: str, outcome: str) -> dict:
    started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
    finished_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
    duration = int((finished_dt - started_dt).total_seconds())
    return {
        "id": job_id,
        "attempt": attempt,
        "started": started,
        "finished": finished,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "duration_secs": duration,
        "outcome": outcome,
    }


def _write_run_record(runs_dir: Path, job_id: str, record: dict):
    runs_dir.mkdir(parents=True, exist_ok=True)
    attempt = record["attempt"]
    filename = f"{job_id}-run-{attempt}.yaml"
    path = runs_dir / filename
    with open(path, "w") as f:
        yaml.dump(record, f, default_flow_style=False, sort_keys=False)
    return path


def _get_attempt_number(runs_dir: Path, job_id: str) -> int:
    existing = list(runs_dir.glob(f"{job_id}-run-*.yaml"))
    return len(existing) + 1


def execute_job(job: Job, runs_dir: Path, notifier: Notifier, dry_run: bool = False) -> str:
    """Execute a single job. Returns outcome: done | failed | timeout."""
    attempt = _get_attempt_number(runs_dir, job.id)

    if dry_run:
        print(f"  DRY-RUN  {job.id}  {job.title}")
        return "done"

    started = _now_iso()
    print(f"  running  {job.id}  {job.title}")

    try:
        result = subprocess.run(
            job.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=job.timeout_secs,
        )
        finished = _now_iso()
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        outcome = "done" if exit_code == 0 else "failed"

    except subprocess.TimeoutExpired as e:
        finished = _now_iso()
        exit_code = -1
        stdout = ""
        stderr = f"timeout after {job.timeout_secs}s"
        outcome = "timeout"

    record = _run_record(job.id, attempt, started, finished, exit_code, stdout, stderr, outcome)
    _write_run_record(runs_dir, job.id, record)

    if outcome != "done":
        remaining = job.decrement_retries()
        if remaining <= 0:
            notifier.failure(job.id, job.title, job.command, exit_code, stderr)
            return "failed"
        else:
            print(f"  retry    {job.id}  ({remaining} retries remaining)")
            return "retry"

    return "done"


class Executor:
    def __init__(self, cfg, manifest: Manifest, notifier: Notifier):
        self.cfg = cfg
        self.manifest = manifest
        self.notifier = notifier

    def _deps_satisfied(self, job_entry: dict) -> bool:
        deps = job_entry.get("depends_on", [])
        if not deps:
            return True
        for dep_id in deps:
            entry = self.manifest.get_entry(dep_id)
            if not entry or entry["status"] != "done":
                return False
        return True

    def run(self, force: bool = False, limit: int = None, dry_run: bool = False) -> dict:
        exec_cfg = self.cfg.execution
        window = exec_cfg.get("overnight_window", "02:00-05:00")
        tz = exec_cfg.get("timezone", "Europe/London")

        if not force and not _in_window(window, tz):
            print(f"outside overnight window ({window} {tz}) — use --force to override")
            return {"done": 0, "failed": 0, "skipped": 0, "outside_window": True}

        pending = self.manifest.pending_jobs()
        pending.sort(key=lambda j: (j.get("priority", 5), j.get("created", "")))

        if limit:
            pending = pending[:limit]

        counts = {"done": 0, "failed": 0, "skipped": 0}

        for entry in pending:
            if not self._deps_satisfied(entry):
                print(f"  skipped  {entry['id']}  (dependencies not done)")
                counts["skipped"] += 1
                continue

            job = Job.from_file(Path(entry["file"]))

            # claim
            job.set_status("claimed")
            job.save()
            self.manifest.update_status(job.id, "claimed")

            # running
            job.set_status("running")
            job.save()
            self.manifest.update_status(job.id, "running")

            outcome = execute_job(job, self.cfg.runs_dir, self.notifier, dry_run=dry_run)

            if outcome == "done":
                job.set_status("done")
                job.save()
                self.manifest.update_status(job.id, "done")
                counts["done"] += 1
            elif outcome == "failed":
                job.set_status("failed")
                job.save()
                self.manifest.update_status(job.id, "failed")
                counts["failed"] += 1
            elif outcome == "retry":
                job.set_status("pending")
                job.save()
                self.manifest.update_status(job.id, "pending")
                counts["skipped"] += 1

        self.notifier.success_summary(counts["done"], counts["failed"], counts["skipped"])
        return counts
