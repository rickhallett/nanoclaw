"""Fleet health checks — active ping that catches zombies.

A process can be pid-alive but event-loop-dead (the microhal-dad scenario).
We check last log activity to detect this.
"""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from halos.common.log import hlog


STALE_THRESHOLD_MINUTES = 30  # no log output for this long = zombie
# Startup lines are expected to be the last entry when idle — not zombie signals
STARTUP_EVENTS = {"NanoClaw running", "Telegram bot connected", "Scheduler loop started",
                  "IPC watcher started", "Database initialized", "Credential proxy started",
                  "State loaded"}
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class HealthResult:
    instance: str
    pid: int | None = None
    pid_alive: bool = False
    pm2_status: str = ""
    uptime: str = ""
    restarts: int = 0
    memory_mb: float = 0.0
    last_log_ts: str = ""
    minutes_silent: float = -1
    zombie: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.pid_alive and not self.zombie and not self.errors

    def summary_line(self) -> str:
        status = "OK" if self.healthy else "ZOMBIE" if self.zombie else "DOWN"
        parts = [f"{self.instance:<12} {status:<8}"]
        if self.pid:
            parts.append(f"pid={self.pid}")
        if self.uptime:
            parts.append(f"up={self.uptime}")
        if self.restarts:
            parts.append(f"restarts={self.restarts}")
        if self.memory_mb:
            parts.append(f"mem={self.memory_mb:.0f}MB")
        if self.minutes_silent >= 0:
            parts.append(f"silent={self.minutes_silent:.0f}m")
        if self.errors:
            parts.append(f"errors={self.errors}")
        return "  ".join(parts)


def _pm2_jlist() -> list[dict]:
    """Get pm2 process list as structured data."""
    try:
        result = subprocess.run(
            ["npx", "pm2", "jlist"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
    except Exception:
        pass
    return []


def _last_log_info(pm2_log: Path) -> tuple[str | None, bool]:
    """Extract timestamp and startup-status from the last substantive log line.

    Returns (timestamp, is_startup_line).
    is_startup_line=True means the last log entry is a startup event,
    which is normal for idle bots — not a zombie signal.
    """
    if not pm2_log.exists():
        return None, False
    try:
        # Read last 4KB — enough for several log lines
        size = pm2_log.stat().st_size
        offset = max(0, size - 4096)
        with open(pm2_log) as f:
            f.seek(offset)
            tail = f.read()

        ts_re = re.compile(r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\]")
        last_ts = None
        last_line = ""
        for line in tail.splitlines():
            clean = ANSI_RE.sub("", line)
            m = ts_re.match(clean)
            if m:
                last_ts = m.group(1)
                last_line = clean

        is_startup = any(event in last_line for event in STARTUP_EVENTS)
        return last_ts, is_startup
    except Exception:
        return None, False


def _minutes_since(time_str: str) -> float:
    """Minutes between HH:MM:SS.mmm and now (assumes today, UTC)."""
    try:
        now = datetime.now(timezone.utc)
        t = datetime.strptime(time_str, "%H:%M:%S.%f").time()
        dt = datetime.combine(now.date(), t, tzinfo=timezone.utc)
        delta = (now - dt).total_seconds() / 60
        # Handle day boundary — if result is very negative, it was yesterday
        if delta < -60:
            delta += 1440
        return delta
    except Exception:
        return -1


def check_instance(name: str, pm2_processes: list[dict] | None = None) -> HealthResult:
    """Run health check against a single fleet instance."""
    result = HealthResult(instance=name)
    pm2_name = f"microhal-{name}" if not name.startswith("microhal-") else name
    short_name = name.removeprefix("microhal-")

    # Find in pm2 process list
    if pm2_processes is None:
        pm2_processes = _pm2_jlist()

    proc = None
    for p in pm2_processes:
        if p.get("name") == pm2_name:
            proc = p
            break

    if proc is None:
        result.errors.append("not in pm2")
        return result

    result.pid = proc.get("pid")
    result.pm2_status = proc.get("pm2_env", {}).get("status", "unknown")
    result.uptime = _format_uptime(proc.get("pm2_env", {}).get("pm_uptime"))
    result.restarts = proc.get("pm2_env", {}).get("restart_time", 0)
    monit = proc.get("monit", {})
    result.memory_mb = monit.get("memory", 0) / (1024 * 1024)

    # pid alive?
    if result.pid:
        try:
            import os
            os.kill(result.pid, 0)
            result.pid_alive = True
        except (ProcessLookupError, PermissionError):
            result.pid_alive = False
            result.errors.append("pid dead")

    # Last log activity — the zombie detector
    pm2_log = Path.home() / ".pm2" / "logs" / f"{pm2_name}-out.log"
    last_ts, is_startup = _last_log_info(pm2_log)
    if last_ts:
        result.last_log_ts = last_ts
        result.minutes_silent = _minutes_since(last_ts)
        # If the last line is a startup event, the bot may just be idle.
        # Only flag as zombie if silent for a long time AND last line
        # was mid-operation (not startup), or silent for an extreme duration.
        if result.minutes_silent > STALE_THRESHOLD_MINUTES:
            if is_startup and result.minutes_silent < 120:
                # Recently started, no messages yet — probably just idle
                pass
            else:
                result.zombie = True
                result.errors.append(f"event loop silent for {result.minutes_silent:.0f}m")

    return result


def check_all() -> list[HealthResult]:
    """Health check all active fleet instances."""
    from .config import load_fleet_manifest

    manifest = load_fleet_manifest()
    instances = [i for i in manifest.get("instances", []) if i.get("status") == "active"]

    if not instances:
        return []

    pm2_procs = _pm2_jlist()
    results = []
    for inst in instances:
        name = inst["name"]
        r = check_instance(name, pm2_procs)
        results.append(r)

    return results


def restart_instance(name: str) -> bool:
    """Restart a fleet instance via pm2. Returns True on success."""
    pm2_name = f"microhal-{name}" if not name.startswith("microhal-") else name
    try:
        result = subprocess.run(
            ["npx", "pm2", "restart", pm2_name],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


def auto_heal(results: list[HealthResult]) -> list[str]:
    """Restart any unhealthy instances. Returns list of restarted names."""
    restarted = []
    for r in results:
        if not r.healthy:
            name = r.instance
            if restart_instance(name):
                restarted.append(name)
                hlog("halctl", "info", "auto_healed", {
                    "instance": name,
                    "was_zombie": r.zombie,
                    "minutes_silent": r.minutes_silent,
                    "errors": r.errors,
                })
            else:
                hlog("halctl", "error", "auto_heal_failed", {"instance": name})
    return restarted


def _format_uptime(pm_uptime: int | None) -> str:
    """Format pm2 uptime (epoch ms) as human-readable."""
    if not pm_uptime:
        return ""
    try:
        now_ms = datetime.now(timezone.utc).timestamp() * 1000
        diff_s = (now_ms - pm_uptime) / 1000
        if diff_s < 60:
            return f"{diff_s:.0f}s"
        elif diff_s < 3600:
            return f"{diff_s / 60:.0f}m"
        else:
            return f"{diff_s / 3600:.1f}h"
    except Exception:
        return ""
