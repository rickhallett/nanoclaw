"""Tier 2 smoke test — inject messages into a live instance and verify agent response."""

import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from halos.common.log import hlog
from .config import load_fleet_manifest


class SmokeResult:
    """Collects pass/fail results for a smoke run."""

    def __init__(self, instance_name: str):
        self.instance = instance_name
        self.checks: list[tuple[str, bool, str]] = []  # (name, passed, detail)

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.checks.append((name, passed, detail))
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}" + (f"  ({detail})" if detail else ""))
        return passed

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    def summary(self) -> str:
        total = len(self.checks)
        passed = sum(1 for _, ok, _ in self.checks if ok)
        return f"{passed}/{total} checks passed"


def _connect_db(deploy_path: Path) -> sqlite3.Connection:
    db_path = deploy_path / "store" / "messages.db"
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    return sqlite3.connect(str(db_path))


def _inject_message(
    conn: sqlite3.Connection,
    chat_jid: str,
    sender_id: str,
    sender_name: str,
    content: str,
) -> str:
    """Insert a fake user message into the messages table. Returns the message ID."""
    msg_id = f"smoke-{uuid.uuid4().hex[:8]}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    conn.execute(
        """INSERT INTO messages (id, chat_jid, sender, sender_name, content, timestamp, is_from_me, is_bot_message)
           VALUES (?, ?, ?, ?, ?, ?, 0, 0)""",
        (msg_id, chat_jid, sender_id, sender_name, content, ts),
    )
    conn.commit()
    return msg_id


def _wait_for_response(
    pm2_log: Path,
    after_line_count: int,
    timeout: float = 60.0,
    poll_interval: float = 2.0,
    collect_all: bool = False,
) -> str | None:
    """Poll pm2 stdout log for new 'Agent output:' lines after our injection.

    If collect_all=True, waits for the full timeout and returns all agent
    output concatenated. Otherwise returns the first match.
    """
    import re

    deadline = time.monotonic() + timeout
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    pattern = re.compile(r"Agent output: (.+)")
    collected: list[str] = []

    # Agent output spans multiple lines in pm2 logs. Each output block starts
    # with a timestamp + "Agent output:" and continues until the next timestamped line.
    timestamp_pattern = re.compile(r'^\[\d{2}:\d{2}:\d{2}')

    while time.monotonic() < deadline:
        if pm2_log.exists():
            lines = pm2_log.read_text().splitlines()
            new_lines = lines[after_line_count:]

            i = 0
            while i < len(new_lines):
                clean = ansi_escape.sub('', new_lines[i])
                m = pattern.search(clean)
                if m:
                    # Capture first line
                    parts = [m.group(1).strip()]
                    # Capture continuation lines (no timestamp prefix)
                    j = i + 1
                    while j < len(new_lines):
                        next_clean = ansi_escape.sub('', new_lines[j])
                        if timestamp_pattern.match(next_clean):
                            break
                        parts.append(next_clean.strip())
                        j += 1
                    text = " ".join(p for p in parts if p)
                    if not collect_all:
                        return text
                    if text not in collected:
                        collected.append(text)
                    i = j
                else:
                    i += 1

        time.sleep(poll_interval)

    return "\n".join(collected) if collected else None


def _count_log_lines(pm2_log: Path) -> int:
    """Count current lines in pm2 log file."""
    if not pm2_log.exists():
        return 0
    return len(pm2_log.read_text().splitlines())


def _check_process_running(name: str) -> bool:
    """Check if the pm2 process is online."""
    import subprocess

    try:
        result = subprocess.run(
            ["npx", "pm2", "jlist"],
            capture_output=True, text=True, timeout=10,
        )
        import json
        processes = json.loads(result.stdout)
        for p in processes:
            if p.get("name") == f"microhal-{name}" and p.get("pm2_env", {}).get("status") == "online":
                return True
    except Exception:
        pass
    return False


def _check_onboarding_table(conn: sqlite3.Connection) -> bool:
    """Check that the onboarding table exists."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='onboarding'"
    ).fetchone()
    return row is not None


def _check_registered_group(conn: sqlite3.Connection, chat_jid: str) -> bool:
    """Check that the operator's chat is registered."""
    row = conn.execute(
        "SELECT jid FROM registered_groups WHERE jid = ?", (chat_jid,)
    ).fetchone()
    return row is not None


def run_smoke(
    name: str,
    fleet_base: Path | None = None,
    timeout: float = 60.0,
) -> SmokeResult:
    """Run the full smoke test suite against a live instance.

    Checks:
      1. pm2 process is running
      2. DB exists and has required tables
      3. Operator chat is registered
      4. Message injection → agent response round-trip
    """
    from .config import fleet_dir

    result = SmokeResult(name)
    base_dir = fleet_base or fleet_dir()

    # Resolve instance
    manifest = load_fleet_manifest(fleet_base=base_dir)
    instance = None
    for inst in manifest.get("instances", []):
        if inst["name"] == name:
            instance = inst
            break

    if instance is None:
        result.check("instance_exists", False, f"'{name}' not in FLEET.yaml")
        return result

    deploy_path = Path(instance["path"])
    result.check("instance_exists", deploy_path.exists(), str(deploy_path))

    if not deploy_path.exists():
        return result

    # Check pm2 process
    result.check("pm2_online", _check_process_running(name))

    # Check DB
    try:
        conn = _connect_db(deploy_path)
    except FileNotFoundError as e:
        result.check("db_exists", False, str(e))
        return result
    result.check("db_exists", True)

    # Check schema
    result.check("onboarding_table", _check_onboarding_table(conn))

    # Check operator registration
    from .provision import OPERATOR_CHAT_JID
    result.check(
        "operator_registered",
        _check_registered_group(conn, OPERATOR_CHAT_JID),
    )

    # Check welcome templates
    welcome_dir = deploy_path / "templates" / "microhal" / "welcome"
    welcome_count = len(list(welcome_dir.glob("*.md"))) if welcome_dir.exists() else 0
    result.check("welcome_templates", welcome_count >= 4, f"{welcome_count} files")

    # Check CLAUDE.md in group folder
    group_claude = deploy_path / "groups" / "telegram_main" / "CLAUDE.md"
    result.check("group_claude_md", group_claude.exists())

    # Check container proxy routing
    dist_runner = deploy_path / "dist" / "container-runner.js"
    if dist_runner.exists():
        content = dist_runner.read_text()
        result.check(
            "proxy_routing",
            "CONTAINER_PROXY_PORT" in content,
            "CONTAINER_PROXY_PORT in dist",
        )
    else:
        result.check("proxy_routing", False, "dist/container-runner.js missing")

    # Check skills permissions (cpSync needs 755/644)
    skills_dir = deploy_path / ".claude" / "skills"
    if skills_dir.exists():
        import stat
        skills_mode = skills_dir.stat().st_mode & 0o777
        result.check(
            "skills_permissions",
            skills_mode >= 0o755,
            f"mode={oct(skills_mode)}",
        )
    else:
        result.check("skills_permissions", True, "no skills dir")

    # Agent capability checks — each injects a message and validates the response
    if not result.check("preconditions", all(ok for _, ok, _ in result.checks), "all above must pass"):
        conn.close()
        return result

    pm2_log = Path.home() / ".pm2" / "logs" / f"microhal-{name}-out.log"

    def _agent_check(
        check_name: str,
        prompt: str,
        validate=None,
        side_effect=None,
    ) -> bool:
        """Inject a message, wait for response, validate it.

        validate(response: str) -> (bool, str) — returns (passed, detail)
        side_effect() -> (bool, str) — optional post-response filesystem check
        """
        before_lines = _count_log_lines(pm2_log)
        _inject_message(conn, OPERATOR_CHAT_JID, "5967394003", "Smoke Test", prompt)
        print(f"\n  [{check_name}] injected, waiting...")
        response = _wait_for_response(pm2_log, before_lines, timeout=timeout)
        if not response:
            result.check(check_name, False, f"no response within {timeout}s")
            return False
        passed, detail = validate(response)
        result.check(check_name, passed, detail)
        if side_effect and passed:
            se_passed, se_detail = side_effect()
            result.check(f"{check_name}_side_effect", se_passed, se_detail)
        return passed

    # 1. Basic response — can the agent hear us?
    _agent_check(
        "agent_responds",
        "@HAL respond with exactly: SMOKE_OK",
        lambda r: ("SMOKE_OK" in r.upper(), r[:80]),
    )

    # 2. File read — can the agent read its governance?
    _agent_check(
        "file_read",
        "@HAL read the first line of /workspace/group/CLAUDE.md and reply with just that line, nothing else",
        lambda r: (
            "microhal" in r.lower() or "hal" in r.lower(),
            r[:80],
        ),
    )

    # 3. Tool use — can the agent execute commands?
    _agent_check(
        "tool_use",
        "@HAL run the command 'echo TOOL_CHECK_OK' and reply with just the output",
        lambda r: ("TOOL_CHECK_OK" in r, r[:80]),
    )

    # 4. Memory write — can the agent create a memctl note?
    smoke_note_title = f"smoke-test-{uuid.uuid4().hex[:6]}"
    notes_dir = deploy_path / "memory" / "notes"
    notes_before = set(notes_dir.glob("*.md")) if notes_dir.exists() else set()

    _agent_check(
        "memory_write",
        f'@HAL create a memctl note with title "{smoke_note_title}" type fact tags smoke-test body "automated smoke test"',
        lambda r: (
            "note" in r.lower() or smoke_note_title in r or "created" in r.lower(),
            r[:80],
        ),
        side_effect=lambda: (
            (lambda new: (len(new) > 0, f"{len(new)} new note(s)"))(
                (set(notes_dir.glob("*.md")) if notes_dir.exists() else set()) - notes_before
            )
        ),
    )

    conn.close()

    hlog("halctl", "info", "smoke_complete", {
        "name": name,
        "passed": result.passed,
        "summary": result.summary(),
    })

    return result
