"""
Notification stub for nightctl.
In production this hooks into halos send_message.
For the prototype it writes to stderr and a notify log.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Notifier:
    def __init__(self, cfg_notify: dict, log_path: Path = None):
        self.cfg = cfg_notify
        self.log_path = log_path

    def _write_log(self, message: str):
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(f"[{_now_iso()}] {message}\n")

    def failure(self, job_id: str, title: str, command: str, exit_code: int, stderr_snippet: str):
        if not self.cfg.get("on_failure", True):
            return
        lines = [
            f"nightctl FAILURE",
            f"Job:     {job_id}",
            f"Title:   {title}",
            f"Command: {command}",
            f"Exit:    {exit_code}",
        ]
        if stderr_snippet:
            lines.append(f"Stderr:  {stderr_snippet[:300]}")
        message = "\n".join(lines)
        print(message, file=sys.stderr)
        self._write_log(message)
        # TODO: wire to halos send_message when available in this context

    def success_summary(self, done: int, failed: int, skipped: int):
        if not self.cfg.get("on_success", False):
            return
        message = f"nightctl run complete — done: {done}, failed: {failed}, skipped: {skipped}"
        print(message)
        self._write_log(message)
