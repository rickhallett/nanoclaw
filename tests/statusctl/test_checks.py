"""Unit tests for statusctl check classes."""

from unittest.mock import patch, MagicMock
import pytest

from halos.statusctl.checks import (
    CheckResult,
    ServiceCheck,
    ContainerCheck,
    AgentCheck,
    HostCheck,
    _run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_run_factory(responses: dict):
    """Create a _run mock that returns based on command prefix."""
    def fake_run(cmd, **kwargs):
        # Match on first two args or first arg
        key2 = tuple(cmd[:2]) if len(cmd) >= 2 else tuple(cmd)
        key3 = tuple(cmd[:3]) if len(cmd) >= 3 else key2
        key4 = tuple(cmd[:4]) if len(cmd) >= 4 else key3
        for k in [key4, key3, key2, (cmd[0],)]:
            if k in responses:
                return responses[k]
        return (-1, "", "not mocked")
    return fake_run


# ---------------------------------------------------------------------------
# ServiceCheck
# ---------------------------------------------------------------------------

class TestServiceCheck:
    def test_all_running(self):
        responses = {
            ("systemctl", "--user", "is-active", "nanoclaw"): (0, "active\n", ""),
            ("ss",): (0, "LISTEN  0  128  *:3001  *:*\n", ""),
            ("docker", "info"): (0, "ok\n", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ServiceCheck().run()
        assert len(results) == 3
        assert all(r.status == "ok" for r in results)

    def test_nanoclaw_stopped(self):
        responses = {
            ("systemctl", "--user", "is-active", "nanoclaw"): (3, "inactive\n", ""),
            ("ss",): (0, "LISTEN  0  128  *:3001  *:*\n", ""),
            ("docker", "info"): (0, "ok\n", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ServiceCheck().run()
        nc = [r for r in results if r.name == "nanoclaw"][0]
        assert nc.status == "fail"
        assert "not running" in nc.message

    def test_systemctl_not_installed(self):
        responses = {
            ("systemctl", "--user", "is-active", "nanoclaw"): (-1, "", "command not found: systemctl"),
            ("ss",): (-1, "", "command not found: ss"),
            ("docker", "info"): (-1, "", "command not found: docker"),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ServiceCheck().run()
        nc = [r for r in results if r.name == "nanoclaw"][0]
        assert nc.status == "warn"

    def test_proxy_not_listening(self):
        responses = {
            ("systemctl", "--user", "is-active", "nanoclaw"): (0, "active\n", ""),
            ("ss",): (0, "LISTEN  0  128  *:8080  *:*\n", ""),
            ("docker", "info"): (0, "ok\n", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ServiceCheck().run()
        proxy = [r for r in results if r.name == "credential-proxy"][0]
        assert proxy.status == "fail"

    def test_docker_error(self):
        responses = {
            ("systemctl", "--user", "is-active", "nanoclaw"): (0, "active\n", ""),
            ("ss",): (0, "LISTEN  0  128  *:3001  *:*\n", ""),
            ("docker", "info"): (1, "", "Cannot connect to Docker daemon"),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ServiceCheck().run()
        docker = [r for r in results if r.name == "docker"][0]
        assert docker.status == "fail"


# ---------------------------------------------------------------------------
# ContainerCheck
# ---------------------------------------------------------------------------

class TestContainerCheck:
    def test_running_containers(self):
        responses = {
            ("docker", "ps", "--format"): (0, "agent-1\nagent-2\n", ""),
            ("docker", "ps", "-a"): (0, "", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ContainerCheck().run()
        assert results[0].status == "ok"
        assert results[0].metrics["running"] == 2

    def test_no_containers(self):
        responses = {
            ("docker", "ps", "--format"): (0, "\n", ""),
            ("docker", "ps", "-a"): (0, "", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ContainerCheck().run()
        assert results[0].metrics["running"] == 0

    def test_docker_unavailable(self):
        responses = {
            ("docker", "ps", "--format"): (-1, "", "command not found: docker"),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ContainerCheck().run()
        assert results[0].status == "warn"

    def test_exited_error_containers(self):
        responses = {
            ("docker", "ps", "--format"): (0, "\n", ""),
            ("docker", "ps", "-a"): (0, "old-agent\tExited (1) 5 minutes ago\n", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = ContainerCheck().run()
        assert results[0].status == "warn"
        assert results[0].metrics["exited_error"] == 1


# ---------------------------------------------------------------------------
# AgentCheck
# ---------------------------------------------------------------------------

class TestAgentCheck:
    def test_with_sessions(self):
        import json
        stats_json = json.dumps({
            "total": 5, "success": 4, "errors": 1, "timeouts": 0,
            "success_rate": 80.0,
        })
        responses = {
            ("agentctl", "stats"): (0, stats_json, ""),
            ("logctl",): (0, "error1\nerror2\n", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = AgentCheck().run()
        sess = [r for r in results if r.name == "sessions"][0]
        assert sess.status == "ok"
        assert sess.metrics["active"] == 5

    def test_without_sessions(self):
        responses = {
            ("agentctl", "stats"): (-1, "", "command not found: agentctl"),
            ("logctl",): (-1, "", "command not found: logctl"),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = AgentCheck().run()
        sess = [r for r in results if r.name == "sessions"][0]
        assert sess.status == "warn"

    def test_with_spin_detection(self):
        import json
        stats_json = json.dumps({
            "total": 3, "success": 1, "errors": 0, "timeouts": 2,
        })
        responses = {
            ("agentctl", "stats"): (0, stats_json, ""),
            ("logctl",): (0, "", ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = AgentCheck().run()
        sess = [r for r in results if r.name == "sessions"][0]
        assert sess.status == "warn"
        assert "timeouts" in sess.message

    def test_elevated_errors(self):
        error_lines = "\n".join([f"error line {i}" for i in range(60)])
        responses = {
            ("agentctl", "stats"): (0, '{"total": 1, "success": 1, "errors": 0, "timeouts": 0}', ""),
            ("logctl",): (0, error_lines, ""),
        }
        with patch("halos.statusctl.checks._run", side_effect=mock_run_factory(responses)):
            results = AgentCheck().run()
        errs = [r for r in results if r.name == "errors"][0]
        assert errs.status == "warn"
        assert "elevated" in errs.message


# ---------------------------------------------------------------------------
# HostCheck
# ---------------------------------------------------------------------------

class TestHostCheck:
    def test_normal_values(self):
        loadavg = "0.50 0.60 0.70 1/200 12345"
        cpuinfo = "processor\t: 0\nmodel name\t: x\n\nprocessor\t: 1\nmodel name\t: x\n"
        meminfo = (
            "MemTotal:       16000000 kB\n"
            "MemFree:         4000000 kB\n"
            "MemAvailable:   12000000 kB\n"
        )
        uptime = "259200.50 500000.00"

        def fake_read(self_path, *args, **kwargs):
            s = str(self_path)
            if "loadavg" in s:
                return loadavg
            if "cpuinfo" in s:
                return cpuinfo
            if "meminfo" in s:
                return meminfo
            if "uptime" in s:
                return uptime
            raise OSError("not found")

        with patch("halos.statusctl.checks.Path.read_text", fake_read):
            with patch("halos.statusctl.checks.shutil.disk_usage") as mock_disk:
                mock_disk.return_value = MagicMock(
                    total=100 * 1024**3, used=45 * 1024**3, free=55 * 1024**3,
                )
                results = HostCheck().run()

        cpu = [r for r in results if r.name == "cpu"][0]
        mem = [r for r in results if r.name == "memory"][0]
        disk = [r for r in results if r.name == "disk"][0]
        uptime_r = [r for r in results if r.name == "uptime"][0]

        assert cpu.status == "ok"
        assert mem.status == "ok"
        assert disk.status == "ok"
        assert uptime_r.status == "ok"
        assert disk.metrics["disk_pct"] == 45
        assert "3d" in uptime_r.message

    def test_high_values_trigger_warnings(self):
        loadavg = "4.50 3.60 2.70 1/200 12345"
        cpuinfo = "processor\t: 0\nmodel name\t: x\n"  # 1 core, load 4.5 = 450%
        meminfo = (
            "MemTotal:       16000000 kB\n"
            "MemFree:          500000 kB\n"
            "MemAvailable:    1000000 kB\n"
        )
        uptime = "100.50 200.00"

        def fake_read(self_path, *args, **kwargs):
            s = str(self_path)
            if "loadavg" in s:
                return loadavg
            if "cpuinfo" in s:
                return cpuinfo
            if "meminfo" in s:
                return meminfo
            if "uptime" in s:
                return uptime
            raise OSError("not found")

        with patch("halos.statusctl.checks.Path.read_text", fake_read):
            with patch("halos.statusctl.checks.shutil.disk_usage") as mock_disk:
                mock_disk.return_value = MagicMock(
                    total=100 * 1024**3, used=96 * 1024**3, free=4 * 1024**3,
                )
                results = HostCheck().run()

        cpu = [r for r in results if r.name == "cpu"][0]
        mem = [r for r in results if r.name == "memory"][0]
        disk = [r for r in results if r.name == "disk"][0]

        assert cpu.status == "warn"
        assert mem.status == "warn"
        assert disk.status == "fail"  # >95% is critical

    def test_missing_proc_files(self):
        """Graceful degradation when /proc is not available."""
        def fake_read(self_path, *args, **kwargs):
            raise OSError("not found")

        with patch("halos.statusctl.checks.Path.read_text", fake_read):
            with patch("halos.statusctl.checks.shutil.disk_usage") as mock_disk:
                mock_disk.side_effect = OSError("nope")
                results = HostCheck().run()

        # All should be warn, not crash
        assert all(r.status == "warn" for r in results)
        assert len(results) == 4


# ---------------------------------------------------------------------------
# _run helper
# ---------------------------------------------------------------------------

class TestRunHelper:
    def test_command_not_found(self):
        rc, out, err = _run(["totally_nonexistent_binary_12345"])
        assert rc == -1
        assert "not found" in err

    def test_timeout(self):
        rc, out, err = _run(["sleep", "60"], timeout=1)
        assert rc == -1
        assert "timed out" in err
