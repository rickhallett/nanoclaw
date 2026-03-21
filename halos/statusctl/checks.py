"""Health check implementations for statusctl.

Each check class runs a specific probe and returns a CheckResult.
All checks gracefully handle missing tools (Docker not installed,
systemd not available, /proc not present).
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: str  # "ok", "warn", "fail"
    message: str
    metrics: dict = field(default_factory=dict)


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """Run a subprocess, returning (returncode, stdout, stderr).

    Returns (-1, "", error_message) if the command is not found or times out.
    """
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", f"command timed out: {' '.join(cmd)}"


class ServiceCheck:
    """Check NanoClaw service, credential proxy, and Docker daemon."""

    def run(self) -> list[CheckResult]:
        results = []
        results.append(self._check_nanoclaw())
        results.append(self._check_credential_proxy())
        results.append(self._check_docker())
        return results

    def _check_nanoclaw(self) -> CheckResult:
        rc, stdout, stderr = _run(["systemctl", "--user", "is-active", "nanoclaw"])
        if rc == -1:
            return CheckResult(
                name="nanoclaw",
                status="warn",
                message="systemctl not available",
            )
        state = stdout.strip()
        if state == "active":
            return CheckResult(name="nanoclaw", status="ok", message="running")
        return CheckResult(name="nanoclaw", status="fail", message=f"not running ({state})")

    def _check_credential_proxy(self) -> CheckResult:
        rc, stdout, stderr = _run(["ss", "-tlnp"])
        if rc == -1:
            return CheckResult(
                name="credential-proxy",
                status="warn",
                message="ss not available",
            )
        if ":3001" in stdout:
            return CheckResult(
                name="credential-proxy", status="ok", message="listening :3001",
            )
        return CheckResult(
            name="credential-proxy", status="fail", message="not listening on :3001",
        )

    def _check_docker(self) -> CheckResult:
        rc, stdout, stderr = _run(["docker", "info"], timeout=15)
        if rc == -1:
            return CheckResult(name="docker", status="fail", message="Docker not reachable")
        if rc == 0:
            return CheckResult(name="docker", status="ok", message="running")
        return CheckResult(name="docker", status="fail", message=f"error (exit {rc})")


class ContainerCheck:
    """Check running containers and recent exits."""

    def run(self) -> list[CheckResult]:
        results = []
        results.append(self._check_containers())
        return results

    def _check_containers(self) -> CheckResult:
        # Running containers
        rc, stdout, _ = _run(["docker", "ps", "--format", "{{.Names}}"])
        if rc == -1:
            return CheckResult(
                name="containers",
                status="warn",
                message="docker not available",
                metrics={"running": 0, "exited_error": 0},
            )

        running = [line for line in stdout.strip().splitlines() if line.strip()]
        running_count = len(running)

        # Recent non-zero exits (last hour)
        rc2, stdout2, _ = _run([
            "docker", "ps", "-a",
            "--filter", "status=exited",
            "--format", "{{.Names}}\t{{.Status}}",
        ])
        exited_error = 0
        if rc2 == 0 and stdout2.strip():
            exited_error = len(stdout2.strip().splitlines())

        metrics = {"running": running_count, "exited_error": exited_error}

        if running_count == 0 and exited_error > 0:
            return CheckResult(
                name="containers",
                status="warn",
                message=f"0 running, {exited_error} exited with errors",
                metrics=metrics,
            )

        return CheckResult(
            name="containers",
            status="ok",
            message=f"{running_count} running, {exited_error} exited-error",
            metrics=metrics,
        )


class AgentCheck:
    """Check agent sessions, spin detection, and recent errors."""

    def run(self) -> list[CheckResult]:
        results = []
        results.append(self._check_sessions())
        results.append(self._check_errors())
        return results

    def _check_sessions(self) -> CheckResult:
        rc, stdout, _ = _run(["agentctl", "stats", "--json"])
        metrics: dict = {"active": 0, "spinning": 0}

        if rc == -1:
            return CheckResult(
                name="sessions",
                status="warn",
                message="agentctl not available",
                metrics=metrics,
            )

        if rc == 0 and stdout.strip():
            import json
            try:
                data = json.loads(stdout)
                total = data.get("total", 0)
                errors = data.get("errors", 0)
                timeouts = data.get("timeouts", 0)
                metrics = {
                    "active": total,
                    "spinning": timeouts,
                    "errors": errors,
                }
                if timeouts > 0:
                    return CheckResult(
                        name="sessions",
                        status="warn",
                        message=f"{total} sessions, {timeouts} timeouts",
                        metrics=metrics,
                    )
                return CheckResult(
                    name="sessions",
                    status="ok",
                    message=f"{total} sessions",
                    metrics=metrics,
                )
            except (json.JSONDecodeError, KeyError):
                pass

        return CheckResult(
            name="sessions",
            status="ok",
            message="no session data",
            metrics=metrics,
        )

    def _check_errors(self) -> CheckResult:
        rc, stdout, _ = _run(["logctl", "errors"])
        metrics: dict = {"error_count_24h": 0}

        if rc == -1:
            return CheckResult(
                name="errors",
                status="warn",
                message="logctl not available",
                metrics=metrics,
            )

        if rc == 0 and stdout.strip():
            lines = [l for l in stdout.strip().splitlines() if l.strip()]
            count = len(lines)
            metrics["error_count_24h"] = count
            if count > 50:
                return CheckResult(
                    name="errors",
                    status="warn",
                    message=f"{count} errors in 24h (elevated)",
                    metrics=metrics,
                )
            return CheckResult(
                name="errors",
                status="ok",
                message=f"{count} errors in 24h",
                metrics=metrics,
            )

        return CheckResult(
            name="errors", status="ok", message="0 errors in 24h", metrics=metrics,
        )


class HostCheck:
    """Check host resources: CPU, memory, disk, uptime."""

    def run(self) -> list[CheckResult]:
        results = []
        results.append(self._check_cpu())
        results.append(self._check_memory())
        results.append(self._check_disk())
        results.append(self._check_uptime())
        return results

    def _check_cpu(self) -> CheckResult:
        try:
            text = Path("/proc/loadavg").read_text()
            parts = text.strip().split()
            load_1 = float(parts[0])
            # Estimate CPU count from /proc/cpuinfo
            try:
                cpuinfo = Path("/proc/cpuinfo").read_text()
                cpu_count = cpuinfo.count("processor\t:")
                if cpu_count == 0:
                    cpu_count = 1
            except (OSError, IOError):
                cpu_count = 1

            pct = int((load_1 / cpu_count) * 100)
            metrics = {
                "load_1min": load_1,
                "cpu_count": cpu_count,
                "cpu_pct": min(pct, 999),
            }
            if pct > 90:
                return CheckResult(
                    name="cpu", status="warn",
                    message=f"load {load_1:.1f} ({pct}% of {cpu_count} cores)",
                    metrics=metrics,
                )
            return CheckResult(
                name="cpu", status="ok",
                message=f"{pct}% (load {load_1:.1f}, {cpu_count} cores)",
                metrics=metrics,
            )
        except (OSError, IOError, ValueError, IndexError):
            return CheckResult(
                name="cpu", status="warn",
                message="/proc/loadavg not available",
                metrics={},
            )

    def _check_memory(self) -> CheckResult:
        try:
            text = Path("/proc/meminfo").read_text()
            info: dict[str, int] = {}
            for line in text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    # Values in kB
                    parts = val.strip().split()
                    if parts:
                        try:
                            info[key.strip()] = int(parts[0])
                        except ValueError:
                            pass

            total_kb = info.get("MemTotal", 0)
            avail_kb = info.get("MemAvailable", 0)
            if total_kb == 0:
                return CheckResult(
                    name="memory", status="warn",
                    message="could not parse /proc/meminfo",
                )

            used_kb = total_kb - avail_kb
            pct = int((used_kb / total_kb) * 100)
            total_gb = total_kb / (1024 * 1024)
            used_gb = used_kb / (1024 * 1024)

            metrics = {
                "total_gb": round(total_gb, 1),
                "used_gb": round(used_gb, 1),
                "available_gb": round((total_gb - used_gb), 1),
                "ram_pct": pct,
            }

            if pct > 90:
                return CheckResult(
                    name="memory", status="warn",
                    message=f"{used_gb:.1f}/{total_gb:.1f} GB ({pct}%)",
                    metrics=metrics,
                )
            return CheckResult(
                name="memory", status="ok",
                message=f"{used_gb:.1f}/{total_gb:.1f} GB ({pct}%)",
                metrics=metrics,
            )
        except (OSError, IOError):
            return CheckResult(
                name="memory", status="warn",
                message="/proc/meminfo not available",
            )

    def _check_disk(self) -> CheckResult:
        try:
            usage = shutil.disk_usage(".")
            pct = int((usage.used / usage.total) * 100)
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)

            metrics = {
                "total_gb": round(total_gb, 1),
                "used_gb": round(used_gb, 1),
                "free_gb": round(free_gb, 1),
                "disk_pct": pct,
            }

            if pct > 95:
                return CheckResult(
                    name="disk", status="fail",
                    message=f"{pct}% used ({free_gb:.1f} GB free) — CRITICAL",
                    metrics=metrics,
                )
            if pct > 85:
                return CheckResult(
                    name="disk", status="warn",
                    message=f"{pct}% used ({free_gb:.1f} GB free)",
                    metrics=metrics,
                )
            return CheckResult(
                name="disk", status="ok",
                message=f"{pct}% ({used_gb:.1f}/{total_gb:.1f} GB)",
                metrics=metrics,
            )
        except OSError:
            return CheckResult(
                name="disk", status="warn",
                message="could not read disk usage",
            )

    def _check_uptime(self) -> CheckResult:
        try:
            text = Path("/proc/uptime").read_text()
            secs = float(text.strip().split()[0])
            days = int(secs // 86400)
            hours = int((secs % 86400) // 3600)
            metrics = {"uptime_secs": int(secs), "uptime_days": days}
            return CheckResult(
                name="uptime", status="ok",
                message=f"{days}d {hours}h",
                metrics=metrics,
            )
        except (OSError, IOError, ValueError, IndexError):
            return CheckResult(
                name="uptime", status="warn",
                message="/proc/uptime not available",
            )
