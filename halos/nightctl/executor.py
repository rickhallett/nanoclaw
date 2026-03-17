import subprocess
try:
    import yaml
except ImportError:
    from . import yaml_shim as yaml
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .item import Item
from .job import Job
from .manifest import Manifest
from .notify import Notifier
from halos.common.log import hlog


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
    """Execute a single legacy job. Returns outcome: done | failed | timeout."""
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


def execute_item(item: Item, runs_dir: Path, notifier: Notifier, dry_run: bool = False) -> str:
    """Execute a unified Item (job or agent-job). Returns outcome: done | failed | timeout."""
    attempt = _get_attempt_number(runs_dir, item.id)

    if dry_run:
        print(f"  DRY-RUN  {item.id}  {item.title}  [{item.kind}]")
        return "done"

    # Agent-jobs: delegate to container-runner via IPC
    if item.kind == "agent-job":
        from .container import prepare_agent_job, ContainerError
        started = _now_iso()
        print(f"  running  {item.id}  {item.title}  [agent-job]")

        try:
            result_info = prepare_agent_job(item)
            hlog("nightctl", "info", "agent_job_dispatched", {
                "id": item.id,
                "plan_path": str(result_info["plan_path"]),
            })
            finished = _now_iso()
            stdout = f"agent-job dispatched: plan at {result_info['plan_path']}"
            if result_info.get("ipc_path"):
                stdout += f", IPC at {result_info['ipc_path']}"
            record = _run_record(item.id, attempt, started, finished, 0, stdout, "", "done")
            _write_run_record(runs_dir, item.id, record)
            return "done"
        except (ContainerError, Exception) as e:
            finished = _now_iso()
            stderr = str(e)
            hlog("nightctl", "error", "agent_job_failed", {
                "id": item.id,
                "error": stderr,
            })
            record = _run_record(item.id, attempt, started, finished, 1, "", stderr, "failed")
            _write_run_record(runs_dir, item.id, record)
            remaining = item.decrement_retries()
            if remaining <= 0:
                notifier.failure(item.id, item.title, f"agent-job: {item.plan_ref or 'inline'}", 1, stderr)
                return "failed"
            else:
                print(f"  retry    {item.id}  ({remaining} retries remaining)")
                return "retry"

    # Regular job execution via subprocess
    if not item.command:
        print(f"  skipped  {item.id}  (no command)")
        return "skipped"

    started = _now_iso()
    print(f"  running  {item.id}  {item.title}  [{item.kind}]")

    try:
        result = subprocess.run(
            item.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=item.timeout_secs,
        )
        finished = _now_iso()
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        outcome = "done" if exit_code == 0 else "failed"

    except subprocess.TimeoutExpired:
        finished = _now_iso()
        exit_code = -1
        stdout = ""
        stderr = f"timeout after {item.timeout_secs}s"
        outcome = "timeout"

    record = _run_record(item.id, attempt, started, finished, exit_code, stdout, stderr, outcome)
    _write_run_record(runs_dir, item.id, record)

    if outcome != "done":
        remaining = item.decrement_retries()
        if remaining <= 0:
            notifier.failure(item.id, item.title, item.command or "", exit_code, stderr)
            return "failed"
        else:
            print(f"  retry    {item.id}  ({remaining} retries remaining)")
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

    def _item_deps_satisfied(self, item: Item) -> bool:
        """Check if all depends_on items are done."""
        deps = item.depends_on
        if not deps:
            return True
        # Check items dir for done status
        from .cli import _load_all_items
        items_dir = getattr(self.cfg, "items_dir", None)
        all_items = {i.id: i for i in _load_all_items(items_dir)} if items_dir else {}
        for dep_id in deps:
            dep = all_items.get(dep_id)
            if not dep or dep.status != "done":
                return False
        return True

    def run(self, force: bool = False, limit: int = None, dry_run: bool = False) -> dict:
        exec_cfg = self.cfg.execution
        window = exec_cfg.get("overnight_window", "02:00-05:00")
        tz = exec_cfg.get("timezone", "Europe/London")

        if not force and not _in_window(window, tz):
            print(f"outside overnight window ({window} {tz}) -- use --force to override")
            return {"done": 0, "failed": 0, "skipped": 0, "outside_window": True}

        counts = {"done": 0, "failed": 0, "skipped": 0}

        # --- Execute unified Items (in-progress, kind in job/agent-job) ---
        from .cli import _load_all_items
        items_dir = getattr(self.cfg, "items_dir", None)
        items = _load_all_items(items_dir) if items_dir else []
        executable_items = [
            i for i in items
            if i.status == "in-progress" and i.kind in ("job", "agent-job")
        ]
        executable_items.sort(key=lambda i: (i.priority, i.created))

        executed = 0
        for item in executable_items:
            if limit and executed >= limit:
                break

            if not self._item_deps_satisfied(item):
                print(f"  skipped  {item.id}  (dependencies not done)")
                counts["skipped"] += 1
                continue

            # Transition: in-progress -> running
            try:
                item.transition("running")
                item.save()
            except Exception as e:
                print(f"  error    {item.id}  transition to running failed: {e}")
                counts["skipped"] += 1
                continue

            outcome = execute_item(item, self.cfg.runs_dir, self.notifier, dry_run=dry_run)

            if outcome == "done":
                item.transition("done")
                item.save()
                counts["done"] += 1
            elif outcome == "failed":
                item.transition("failed")
                item.save()
                counts["failed"] += 1
            elif outcome == "retry":
                # Back to in-progress for next cycle
                item.data["status"] = "in-progress"
                item.save()
                counts["skipped"] += 1

            executed += 1

        # --- Execute legacy jobs from manifest ---
        remaining_limit = (limit - executed) if limit else None
        if remaining_limit is not None and remaining_limit <= 0:
            self.notifier.success_summary(counts["done"], counts["failed"], counts["skipped"])
            return counts

        pending = self.manifest.pending_jobs()
        pending.sort(key=lambda j: (j.get("priority", 5), j.get("created", "")))

        if remaining_limit:
            pending = pending[:remaining_limit]

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
