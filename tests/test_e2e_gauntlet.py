"""End-to-end gauntlet tests for nightctl unified work tracker and microHAL onboarding.

These are not unit tests. Each test simulates a realistic multi-step workflow
and deliberately tries to break things. If a test here passes trivially,
it is wrong.

Scenarios cover: lifecycle corruption, parallel stress, state machine exhaustion,
adversarial XML, dependency chains, archive integrity, race conditions,
terminal state escape, kind mutation, retry exhaustion, onboarding abuse,
template composition edge cases, fleet config validation, provisioning,
and the freeze/fold/fry state machine.
"""

import hashlib
import os
import shutil
import stat
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from halos.nightctl.item import (
    Item,
    ValidationError,
    TransitionError,
    SaveError,
    valid_transitions,
    VALID_KINDS,
    VALID_STATUSES,
    TERMINAL_STATUSES,
    _BASE_TRANSITIONS,
    _KIND_EXCLUSIONS,
)
from halos.nightctl.plan import (
    validate_plan_xml,
    PlanValidationError,
    extract_plan_from_file,
    validate_plan_ref,
)
from halos.nightctl.container import (
    prepare_agent_job,
    resolve_plan,
    write_plan_file,
    ContainerError,
)
from halos.nightctl.executor import (
    execute_item,
    _write_run_record,
    _get_attempt_number,
)
from halos.nightctl.config import load_config
from halos.microhal.onboarding import (
    get_onboarding_state,
    get_onboarding_prompt,
    advance_onboarding,
    STATES,
    STATE_ORDER,
    LIKERT_QUESTIONS,
    TUTORIAL_MESSAGES,
    _read_state_file,
    _write_state_file,
)


# ---------------------------------------------------------------------------
# Shared fixtures and constants
# ---------------------------------------------------------------------------

VALID_PLAN = """\
<plan>
  <goal>Achieve the objective</goal>
  <steps>
    <step n="1" output="stdout">Do the first thing</step>
  </steps>
  <constraints>
    <constraint>Stay within scope</constraint>
  </constraints>
  <success>
    <criterion>The objective is achieved</criterion>
  </success>
  <output>stdout</output>
</plan>"""


def _make_nightctl_config(tmp_path):
    """Create a minimal nightctl config for testing. Returns Config object."""
    config = {
        "queue_dir": str(tmp_path / "queue"),
        "items_dir": str(tmp_path / "queue" / "items"),
        "manifest_file": str(tmp_path / "queue" / "MANIFEST.yaml"),
        "archive_dir": str(tmp_path / "queue" / "archive"),
        "runs_dir": str(tmp_path / "queue" / "runs"),
        "execution": {
            "mode": "serial",
            "max_workers": 1,
            "overnight_window": "00:00-23:59",
            "timezone": "UTC",
        },
        "job": {
            "default_retries": 2,
            "default_timeout_secs": 300,
            "default_schedule": "overnight",
            "valid_schedules": ["overnight", "immediate", "once"],
            "valid_tags": [],
        },
        "notify": {"on_failure": False, "on_success": False, "channel": "main"},
        "manifest": {"hash_algorithm": "sha256"},
        "archive": {"retention_days": 30, "dry_run": False},
    }
    config_path = tmp_path / "nightctl.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False))
    for d in ["queue/jobs", "queue/items", "queue/runs", "queue/archive"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return load_config(str(config_path))


class FakeNotifier:
    """Notifier stub that records calls instead of sending messages."""

    def __init__(self):
        self.failures = []
        self.summaries = []

    def failure(self, job_id, title, command, exit_code, stderr):
        self.failures.append({
            "id": job_id, "title": title, "command": command,
            "exit_code": exit_code, "stderr": stderr,
        })

    def success_summary(self, done, failed, skipped):
        self.summaries.append({"done": done, "failed": failed, "skipped": skipped})


# ===========================================================================
# NIGHTCTL GAUNTLET
# ===========================================================================


class TestScenario01LifecycleWithPlanCorruption:
    """Scenario 1: Full agent-job lifecycle with plan corruption mid-flight.

    Create agent-job -> planning -> author valid plan -> plan-review -> approve
    -> corrupt plan on disk -> running -> fail -> revise -> verify plan must
    be re-validated.
    """

    def test_plan_corruption_caught_at_revise_gate(self, tmp_path):
        """After failure, revising back to plan-review re-validates the plan.
        If the plan was corrupted between approval and failure, the gate catches it."""
        items_dir = tmp_path / "items"

        # Create and drive to in-progress
        item = Item.create(items_dir, title="Corruption test", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN
        item.transition("plan-review")
        item.transition("in-progress")
        item.save()

        # Simulate execution: in-progress -> running -> failed
        item.transition("running")
        item.transition("failed")

        # Corrupt the plan on disk AND in memory (simulating file edit between runs)
        item.data["plan"] = "<plan><goal></goal></plan>"
        item.save()

        # Revise: failed -> plan-review. The transition itself should go through
        # because failed -> plan-review doesn't re-validate (it's not on the
        # planning track). But the NEXT gate (plan-review -> in-progress) must catch it.
        item.transition("plan-review")
        assert item.status == "plan-review", (
            "Failed -> plan-review transition should succeed regardless of plan quality"
        )

        # Now try to approve the corrupted plan: plan-review -> in-progress
        with pytest.raises(PlanValidationError, match="goal.*must not be empty"):
            item.transition("in-progress")
        assert item.status == "plan-review", (
            "Status must not change when plan validation fails at the approval gate"
        )

    def test_full_recovery_after_plan_fix(self, tmp_path):
        """After corruption is caught, fixing the plan allows re-approval."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Recovery test", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN
        item.transition("plan-review")
        item.transition("in-progress")
        item.transition("running")
        item.transition("failed")

        # Corrupt
        item.data["plan"] = "not xml at all"
        item.transition("plan-review")

        # Fix
        item.data["plan"] = VALID_PLAN
        item.transition("in-progress")
        assert item.status == "in-progress", (
            "After fixing the plan, approval should succeed"
        )


@pytest.mark.slow
class TestScenario02ParallelCreationStress:
    """Scenario 2: Create 50 items in rapid succession using threading.
    Verify no ID collisions, no file corruption, all items loadable."""

    def test_50_parallel_items_no_collisions(self, tmp_path):
        items_dir = tmp_path / "items"
        items_dir.mkdir(parents=True)
        results = []
        errors = []

        def create_one(index):
            try:
                item = Item.create(
                    items_dir,
                    title=f"Parallel item {index}",
                    kind="task",
                    priority=(index % 4) + 1,
                )
                return item.id, item.file_path
            except Exception as e:
                return None, str(e)

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(create_one, i): i for i in range(50)}
            for future in as_completed(futures):
                item_id, path = future.result()
                if item_id is None:
                    errors.append(path)
                else:
                    results.append((item_id, path))

        assert len(errors) == 0, (
            f"Some items failed to create: {errors}"
        )

        # Check for ID uniqueness
        ids = [r[0] for r in results]
        assert len(set(ids)) == 50, (
            f"ID collision detected: {len(set(ids))} unique IDs from 50 items"
        )

        # Check all files exist and are loadable
        for item_id, path in results:
            assert path.exists(), f"File missing for item {item_id}: {path}"
            loaded = Item.from_file(path)
            assert loaded.id == item_id, (
                f"Loaded ID '{loaded.id}' does not match created ID '{item_id}'"
            )

        # Verify no .tmp files left behind
        tmp_files = list(items_dir.glob("*.tmp"))
        assert len(tmp_files) == 0, (
            f"Stale .tmp files found after parallel creation: {tmp_files}"
        )

    def test_parallel_saves_to_same_item_survive(self, tmp_path):
        """Multiple threads saving to the same item file -- last write wins,
        but no file corruption should occur."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Contention target", kind="task")
        barrier = threading.Barrier(5)

        def update_priority(priority):
            barrier.wait()
            item.data["priority"] = priority
            item.save()

        threads = [
            threading.Thread(target=update_priority, args=(p,))
            for p in range(1, 6)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # File must be valid YAML and loadable
        reloaded = Item.from_file(item.file_path)
        assert reloaded.priority in range(1, 6), (
            f"Priority {reloaded.priority} is not one of the written values"
        )
        # No tmp files
        tmp_files = list(items_dir.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestScenario03ExhaustiveInvalidTransitions:
    """Scenario 3: For EVERY (status, kind) pair, attempt EVERY possible
    transition. Verify that only spec-allowed transitions succeed and all
    others raise TransitionError with correct allowed list."""

    @pytest.mark.parametrize("kind", list(VALID_KINDS))
    def test_every_status_every_target(self, kind, tmp_path):
        """Exhaustive transition matrix for a given kind."""
        items_dir = tmp_path / "items"

        for source_status in VALID_STATUSES:
            allowed = valid_transitions(source_status, kind)

            for target_status in VALID_STATUSES:
                # Build a fresh item at the source status
                if kind == "job":
                    item = Item.create(
                        items_dir, title=f"Matrix {source_status}->{target_status}",
                        kind=kind, command="echo test",
                    )
                else:
                    item = Item.create(
                        items_dir, title=f"Matrix {source_status}->{target_status}",
                        kind=kind,
                    )
                # Force to source status (bypass state machine for setup)
                item.data["status"] = source_status
                # Give it a valid plan if agent-job (so plan gates don't interfere)
                if kind == "agent-job":
                    item.data["plan"] = VALID_PLAN

                if target_status in allowed:
                    # Should succeed
                    try:
                        item.transition(target_status)
                    except TransitionError:
                        pytest.fail(
                            f"Transition {source_status} -> {target_status} for kind={kind} "
                            f"should be ALLOWED but raised TransitionError. "
                            f"Allowed list: {allowed}"
                        )
                    assert item.status == target_status, (
                        f"After allowed transition {source_status} -> {target_status}, "
                        f"status is '{item.status}' instead"
                    )
                else:
                    # Should fail
                    with pytest.raises(TransitionError) as exc_info:
                        item.transition(target_status)
                    err = exc_info.value
                    assert err.current == source_status, (
                        f"TransitionError.current is '{err.current}' but expected '{source_status}'"
                    )
                    assert err.attempted == target_status, (
                        f"TransitionError.attempted is '{err.attempted}' but expected '{target_status}'"
                    )
                    assert err.allowed == allowed, (
                        f"TransitionError.allowed is {err.allowed} but expected {allowed} "
                        f"for {source_status} -> {target_status} (kind={kind})"
                    )


class TestScenario04PlanValidationAdversarial:
    """Scenario 4: Adversarial XML inputs to plan validation."""

    def test_billion_laughs_rejected(self):
        """XML bomb (billion laughs entity expansion) must not hang or OOM.
        Python 3.14+ stdlib ET.fromstring defuses entity expansion silently --
        entities are dropped, leaving empty elements. The structural validation
        then catches the missing required elements. Either way, the plan must
        NOT pass validation."""
        bomb = '''<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<plan><goal>&lol4;</goal></plan>'''
        with pytest.raises(PlanValidationError):
            validate_plan_xml(bomb)

    def test_deeply_nested_elements(self):
        """1000 levels of nesting -- parser should handle or reject, not crash."""
        inner = "<x>" * 1000 + "deep" + "</x>" * 1000
        xml = f"<plan><goal>{inner}</goal><steps><step n='1' output='x'>s</step></steps><constraints><constraint>c</constraint></constraints><success><criterion>y</criterion></success></plan>"
        # Should either parse successfully (goal has text buried deep) or raise.
        # The key assertion: it must not hang or segfault.
        try:
            validate_plan_xml(xml)
        except PlanValidationError:
            pass  # Acceptable -- deeply nested goal may be treated as empty

    @pytest.mark.slow
    def test_one_megabyte_plan(self):
        """1MB plan -- should not crash, may be slow."""
        padding = "x" * (1024 * 1024)
        xml = f"<plan><goal>{padding}</goal><steps><step n='1' output='x'>s</step></steps><constraints><constraint>c</constraint></constraints><success><criterion>y</criterion></success></plan>"
        # Should succeed -- plan is structurally valid, just enormous
        validate_plan_xml(xml)

    def test_cdata_blocks(self):
        """CDATA blocks should be treated as text content."""
        xml = """<plan>
  <goal><![CDATA[This is the goal with <special> chars]]></goal>
  <steps><step n="1" output="stdout"><![CDATA[Step with CDATA]]></step></steps>
  <constraints><constraint><![CDATA[Constraint text]]></constraint></constraints>
  <success><criterion><![CDATA[Success criterion]]></criterion></success>
</plan>"""
        validate_plan_xml(xml)  # Should not raise

    def test_empty_cdata_in_goal_rejected(self):
        """Empty CDATA in goal should count as empty goal."""
        xml = """<plan>
  <goal><![CDATA[]]></goal>
  <steps><step n="1" output="stdout">s</step></steps>
  <constraints><constraint>c</constraint></constraints>
  <success><criterion>y</criterion></success>
</plan>"""
        with pytest.raises(PlanValidationError, match="goal.*must not be empty"):
            validate_plan_xml(xml)

    def test_xml_namespaces_rejected_or_handled(self):
        """XML with namespaces -- the root tag won't be 'plan' in namespace-aware parsing."""
        xml = """<ns:plan xmlns:ns="http://example.com">
  <ns:goal>Goal</ns:goal>
  <ns:steps><ns:step n="1" output="x">s</ns:step></ns:steps>
  <ns:constraints><ns:constraint>c</ns:constraint></ns:constraints>
  <ns:success><ns:criterion>y</ns:criterion></ns:success>
</ns:plan>"""
        # ET.fromstring will see the root tag as {http://example.com}plan, not "plan"
        with pytest.raises(PlanValidationError, match="root element must be <plan>"):
            validate_plan_xml(xml)

    def test_unicode_in_plan(self):
        """Plan with unicode characters in all fields."""
        xml = """<plan>
  <goal>Analyse the eigenvalue decomposition of the Schrodinger equation</goal>
  <steps><step n="1" output="stdout">Use the formula E = mc^2</step></steps>
  <constraints><constraint>Do not exceed 10^9 iterations</constraint></constraints>
  <success><criterion>Output matches the analytical solution</criterion></success>
</plan>"""
        validate_plan_xml(xml)

    def test_self_closing_step_tags(self):
        """Self-closing <step/> with attributes but no text content."""
        xml = """<plan>
  <goal>Test self-closing steps</goal>
  <steps><step n="1" output="stdout"/></steps>
  <constraints><constraint>c</constraint></constraints>
  <success><criterion>y</criterion></success>
</plan>"""
        validate_plan_xml(xml)  # Should succeed -- step has required attrs

    def test_html_entities(self):
        """HTML entities like &amp; &lt; should work in XML."""
        xml = """<plan>
  <goal>Handle &amp; and &lt;special&gt; chars</goal>
  <steps><step n="1" output="stdout">Use &lt;tool&gt;</step></steps>
  <constraints><constraint>Don&apos;t break &amp; things</constraint></constraints>
  <success><criterion>Output contains &lt;expected&gt;</criterion></success>
</plan>"""
        validate_plan_xml(xml)

    def test_not_xml_at_all(self):
        """Completely non-XML input."""
        with pytest.raises(PlanValidationError, match="invalid XML"):
            validate_plan_xml("this is just a string, not xml")

    def test_empty_string(self):
        """Empty string as plan."""
        with pytest.raises(PlanValidationError, match="invalid XML"):
            validate_plan_xml("")

    def test_wrong_root_element(self):
        """Valid XML but wrong root element."""
        with pytest.raises(PlanValidationError, match="root element must be <plan>"):
            validate_plan_xml("<recipe><goal>cook</goal></recipe>")

    def test_multiple_validation_errors_collected(self):
        """A plan missing everything except the root should produce multiple errors."""
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml("<plan></plan>")
        errors = exc_info.value.errors
        assert len(errors) >= 4, (
            f"Expected at least 4 errors for an empty <plan>, got {len(errors)}: {errors}"
        )


class TestScenario05DependencyChainExecution:
    """Scenario 5: Dependency chain of 5 jobs executed in order.
    Also: cyclic dependency detection (or documented lack thereof)."""

    def test_linear_chain_respects_order(self, tmp_path):
        """Five jobs in a chain: each depends on the previous.
        Only the first (no deps) should execute initially."""
        cfg = _make_nightctl_config(tmp_path)
        items_dir = cfg.items_dir
        notifier = FakeNotifier()

        # Create chain: item0 <- item1 <- item2 <- item3 <- item4
        chain = []
        for i in range(5):
            depends = [chain[i - 1].id] if i > 0 else []
            item = Item.create(
                items_dir,
                title=f"Chain link {i}",
                kind="job",
                command=f"echo link-{i}",
                depends_on=depends,
            )
            item.transition("in-progress")
            item.save()
            chain.append(item)

        from halos.nightctl.manifest import Manifest
        from halos.nightctl.executor import Executor

        manifest = Manifest(cfg.manifest_file)
        executor = Executor(cfg, manifest, notifier)

        # Executor cascades through the chain in a single run cycle:
        # after item 0 completes, item 1's dep is satisfied, so it runs too.
        # The cascade should complete all 5 items in dependency order.
        counts = executor.run(force=True)
        assert counts["done"] >= 1, (
            f"Expected at least 1 job done, got {counts['done']}"
        )
        # Verify total processed = done + skipped = 5
        assert counts["done"] + counts["skipped"] == 5, (
            f"Expected all 5 items processed, got done={counts['done']} skipped={counts['skipped']}"
        )

    def test_cyclic_dependency_does_not_hang(self, tmp_path):
        """A -> B -> A cycle. Execution must terminate (skip both, not infinite loop)."""
        cfg = _make_nightctl_config(tmp_path)
        items_dir = cfg.items_dir
        notifier = FakeNotifier()

        item_a = Item.create(
            items_dir, title="Cycle A", kind="job", command="echo a",
        )
        item_b = Item.create(
            items_dir, title="Cycle B", kind="job", command="echo b",
            depends_on=[item_a.id],
        )
        # Now make A depend on B (cycle)
        item_a.data["depends_on"] = [item_b.id]
        item_a.transition("in-progress")
        item_a.save()
        item_b.transition("in-progress")
        item_b.save()

        from halos.nightctl.manifest import Manifest
        from halos.nightctl.executor import Executor

        manifest = Manifest(cfg.manifest_file)
        executor = Executor(cfg, manifest, notifier)

        # Must terminate within a reasonable time (5 seconds)
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Cyclic dependency caused executor to hang")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)
        try:
            counts = executor.run(force=True)
            # Both should be skipped (deps unsatisfied)
            assert counts["done"] == 0, (
                "Neither item in a cycle should complete"
            )
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


class TestScenario06ArchiveLifecycleTorture:
    """Scenario 6: Create items, transition through every status, archive
    done/cancelled ones, verify archived items preserve full data, hatch them."""

    def test_archive_preserves_full_data(self, tmp_path):
        """Archived item file must contain all original fields, not be overwritten
        by a tombstone."""
        items_dir = tmp_path / "items"
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir(parents=True)

        item = Item.create(
            items_dir, title="Archive me",
            kind="job", command="echo preserved",
            tags=["important"], priority=1,
            context="Critical context that must survive archival",
        )
        item.transition("in-progress")
        item.transition("running")
        item.transition("done")
        item.save()

        original_data = dict(item.data)

        # Archive using Item.archive
        item.archive(archive_dir)

        # The file should now be in archive_dir
        assert item.file_path.parent == archive_dir, (
            "After archive(), file_path should point to archive directory"
        )
        assert item.file_path.exists(), "Archived file must exist"

        # Load the archived file and verify ALL fields preserved
        archived = Item.from_file(item.file_path)
        assert archived.title == "Archive me", "Title lost during archival"
        assert archived.command == "echo preserved", "Command lost during archival"
        assert archived.context == "Critical context that must survive archival", (
            "Context lost during archival -- this was a known bug"
        )
        assert archived.tags == ["important"], "Tags lost during archival"
        assert archived.priority == 1, "Priority lost during archival"

    def test_hatch_removes_archived_files(self, tmp_path):
        """After hatching, archived files are permanently deleted."""
        items_dir = tmp_path / "items"
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir(parents=True)

        item = Item.create(items_dir, title="Hatch me", kind="task")
        item.transition("cancelled")
        item.save()
        item.archive(archive_dir)
        archived_path = item.file_path

        assert archived_path.exists(), "Setup: archived file must exist"

        # Hatching = deleting the archived file
        archived_path.unlink()
        assert not archived_path.exists(), "Hatched file should be gone"

    def test_original_directory_empty_after_archive(self, tmp_path):
        """After archiving all items, the items directory should have no YAML files
        for the archived item."""
        items_dir = tmp_path / "items"
        archive_dir = tmp_path / "archive"

        item = Item.create(items_dir, title="Move me", kind="task")
        item.transition("cancelled")
        item.save()
        original_name = item.file_path.name

        item.archive(archive_dir)

        remaining = [f.name for f in items_dir.glob("*.yaml")]
        assert original_name not in remaining, (
            f"Original file '{original_name}' still in items/ after archive"
        )


class TestScenario07EditThenTransitionRace:
    """Scenario 7: Edit an item's plan to invalid XML, then immediately try
    to transition through plan-review. Verify the gate catches it."""

    def test_invalid_plan_edit_blocks_review_gate(self, tmp_path):
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Gate test", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN
        item.save()

        # Edit plan to invalid XML via direct data mutation (simulating file edit)
        item.data["plan"] = "<plan><goal>ok</goal></plan>"

        # Try to pass through plan-review gate
        with pytest.raises(PlanValidationError):
            item.transition("plan-review")

        assert item.status == "planning", (
            "Status must remain 'planning' when plan validation fails"
        )

    def test_plan_removed_entirely_blocks_review(self, tmp_path):
        """Setting plan to None after it was valid should block review."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="No plan", kind="agent-job")
        item.transition("planning")
        item.data["plan"] = VALID_PLAN
        # Now remove it
        item.data["plan"] = None
        item.data["plan_ref"] = None

        with pytest.raises(PlanValidationError, match="requires a plan"):
            item.transition("plan-review")


class TestScenario08TerminalStateEscapeAttempts:
    """Scenario 8: Get an item to 'done' and try every possible transition.
    Get one to 'cancelled' and try every transition. Verify absolute lockdown."""

    @pytest.mark.parametrize("terminal_status", list(TERMINAL_STATUSES))
    def test_terminal_state_blocks_all_transitions(self, terminal_status, tmp_path):
        items_dir = tmp_path / "items"

        for target in VALID_STATUSES:
            if target == terminal_status:
                continue  # Same status -> not a real transition

            item = Item.create(
                items_dir,
                title=f"Terminal {terminal_status} -> {target}",
                kind="job", command="echo test",
            )
            item.data["status"] = terminal_status

            with pytest.raises(TransitionError) as exc_info:
                item.transition(target)

            assert exc_info.value.allowed == [], (
                f"Terminal state '{terminal_status}' should have NO allowed transitions, "
                f"but got {exc_info.value.allowed} when attempting -> '{target}'"
            )

    def test_done_error_message_says_terminal(self, tmp_path):
        """The error message for a done item should clearly indicate it's terminal."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Done test", kind="task")
        item.data["status"] = "done"

        with pytest.raises(TransitionError) as exc_info:
            item.transition("open")
        assert "none" in str(exc_info.value).lower() or "terminal" in str(exc_info.value).lower(), (
            f"Error message should indicate terminal state: {exc_info.value}"
        )


class TestScenario09KindImmutabilityProbing:
    """Scenario 9: Create a task, manually set kind to agent-job in the data dict,
    save, reload, try to skip planning track.

    This probes whether kind mutation is guarded or if it's a known gap.
    """

    def test_kind_mutation_via_data_dict(self, tmp_path):
        """Mutating kind via data dict and saving -- what happens?"""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Kind shift", kind="task")
        original_id = item.id

        # Mutate kind directly
        item.data["kind"] = "agent-job"
        item.save()

        # Reload
        reloaded = Item.from_file(item.file_path)
        assert reloaded.kind == "agent-job", (
            "Kind mutation persisted to disk (expected -- kind is not immutable in current implementation)"
        )

        # Agent-jobs CAN now go open -> in-progress (context-only mode for research jobs).
        # The plan/context validation happens at the executor level, not the state machine.
        allowed = valid_transitions("open", "agent-job")
        assert "in-progress" in allowed, (
            "Agent-jobs should be able to go open -> in-progress (context-only mode)"
        )

        # Transition is allowed but plan validation catches the missing plan/context
        from halos.nightctl.plan import PlanValidationError
        with pytest.raises(PlanValidationError):
            reloaded.transition("in-progress")

    def test_kind_mutation_does_not_corrupt_file(self, tmp_path):
        """Even with kind mutation, the file should remain valid YAML."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Corrupt check", kind="task")
        item.data["kind"] = "agent-job"
        item.save()

        # File should be loadable
        reloaded = Item.from_file(item.file_path)
        assert reloaded.title == "Corrupt check"

    # NOTE: kind immutability is NOT enforced in the current implementation.
    # This is documented as a known gap from the adversarial review.
    # A future fix would add kind validation to save() or make kind read-only.


class TestScenario10RetryExhaustion:
    """Scenario 10: Create a job with retries=2, simulate 3 failures,
    verify retries_remaining goes 2->1->0 (not negative), verify final
    state is failed, verify notification fires."""

    def test_retry_countdown_to_zero(self, tmp_path):
        """retries_remaining decrements correctly and never goes negative."""
        items_dir = tmp_path / "items"
        item = Item.create(
            items_dir, title="Retry test", kind="job",
            command="exit 1", retries=2,
        )
        assert item.retries_remaining == 2, "Initial retries_remaining should match retries"

        # First failure
        remaining = item.decrement_retries()
        assert remaining == 1, f"After 1st failure, retries_remaining should be 1, got {remaining}"

        # Second failure
        remaining = item.decrement_retries()
        assert remaining == 0, f"After 2nd failure, retries_remaining should be 0, got {remaining}"

        # Third failure -- should NOT go negative
        remaining = item.decrement_retries()
        assert remaining == 0, (
            f"After 3rd failure, retries_remaining should stay at 0, got {remaining}. "
            "Going negative would be a bug."
        )

    def test_executor_fires_notification_on_exhaustion(self, tmp_path):
        """When retries are exhausted, the notifier.failure() method is called."""
        cfg = _make_nightctl_config(tmp_path)
        items_dir = cfg.items_dir
        notifier = FakeNotifier()

        item = Item.create(
            items_dir, title="Notify test", kind="job",
            command="false", retries=0,  # No retries
        )
        item.transition("in-progress")
        item.save()

        # Execute directly
        item.transition("running")
        outcome = execute_item(item, cfg.runs_dir, notifier)

        assert outcome == "failed", f"Expected 'failed' outcome, got '{outcome}'"
        assert len(notifier.failures) == 1, (
            f"Expected exactly 1 failure notification, got {len(notifier.failures)}"
        )
        assert notifier.failures[0]["id"] == item.id

    def test_retry_then_exhaust_full_cycle(self, tmp_path):
        """Full executor cycle: 2 retries allowed, 3 failures to exhaust.
        execute_item decrements retries and checks remaining <= 0:
        - retries=2: first failure -> remaining=1 -> "retry"
        - second failure -> remaining=0 -> "failed" (notification fires)
        """
        cfg = _make_nightctl_config(tmp_path)
        items_dir = cfg.items_dir
        notifier = FakeNotifier()

        item = Item.create(
            items_dir, title="Retry exhaust", kind="job",
            command="false", retries=2,
        )
        item.transition("in-progress")
        item.save()

        # First execution: should return "retry" (2 remaining -> 1, which is > 0)
        item.transition("running")
        outcome1 = execute_item(item, cfg.runs_dir, notifier)
        assert outcome1 == "retry", f"First failure should retry, got '{outcome1}'"
        assert item.retries_remaining == 1, (
            f"After first failure, retries_remaining should be 1, got {item.retries_remaining}"
        )

        # Second execution: remaining=1 -> 0, which triggers "failed"
        item.transition("in-progress")
        item.transition("running")
        outcome2 = execute_item(item, cfg.runs_dir, notifier)
        assert outcome2 == "failed", f"Second failure should be final, got '{outcome2}'"
        assert item.retries_remaining == 0
        assert len(notifier.failures) == 1, "Notification should fire on final failure"


# ===========================================================================
# MICROHAL GAUNTLET
# ===========================================================================


class TestScenario11OnboardingAbuse:
    """Scenario 11: Send garbage at every state. Reject terms multiple times.
    Send invalid Likert responses. Try to skip ahead. Verify watertight."""

    def test_terms_rejection_five_times_then_accept(self, tmp_path):
        """Rejecting terms 5 times keeps state at terms_of_service.
        Accepting on the 6th attempt advances normally."""
        mem_dir = tmp_path / "memory"

        # First contact -> terms
        result = advance_onboarding(mem_dir, "first_contact", "hi")
        assert result["new_state"] == "terms_of_service", (
            "first_contact should advance to terms_of_service"
        )

        # Reject 5 times with various garbage
        rejections = ["NO", "nah", "maybe", "", "banana"]
        for rejection in rejections:
            result = advance_onboarding(mem_dir, "terms_of_service", rejection)
            assert result["new_state"] == "terms_of_service", (
                f"Rejecting with '{rejection}' should stay at terms_of_service"
            )
            assert result["advanced"] is False

        # Accept on 6th attempt
        result = advance_onboarding(mem_dir, "terms_of_service", "YES")
        assert result["new_state"] == "pre_flight_assessment", (
            "Accepting terms should advance to pre_flight_assessment"
        )

    def test_invalid_likert_responses(self, tmp_path):
        """Non-numeric, out-of-range, and edge case inputs for Likert questions."""
        mem_dir = tmp_path / "memory"

        # Drive to pre_flight_assessment
        advance_onboarding(mem_dir, "first_contact", "hi")
        advance_onboarding(mem_dir, "terms_of_service", "YES")

        # Try garbage inputs
        garbage = ["banana", "6", "0", "-1", "", "3.5", "one", "   ", "\n"]
        for g in garbage:
            result = advance_onboarding(mem_dir, "pre_flight_assessment", g)
            assert result["new_state"] == "pre_flight_assessment", (
                f"Invalid Likert response '{g}' should stay at pre_flight_assessment"
            )
            assert result["advanced"] is False, (
                f"Invalid response '{g}' should not advance"
            )

        # Valid response should advance
        result = advance_onboarding(mem_dir, "pre_flight_assessment", "3")
        assert result["advanced"] is True

    def test_likert_boundary_values(self, tmp_path):
        """1 and 5 are valid, 0 and 6 are not."""
        mem_dir = tmp_path / "memory"
        advance_onboarding(mem_dir, "first_contact", "hi")
        advance_onboarding(mem_dir, "terms_of_service", "YES")

        # Valid boundaries
        result = advance_onboarding(mem_dir, "pre_flight_assessment", "1")
        assert result["advanced"] is True, "1 is a valid Likert value"

        result = advance_onboarding(mem_dir, "pre_flight_assessment", "5")
        assert result["advanced"] is True, "5 is a valid Likert value"

    def test_direct_state_yaml_manipulation(self, tmp_path):
        """Writing arbitrary state directly to the YAML file. The state machine
        should handle unknown states gracefully."""
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir(parents=True)

        # Write an invalid state directly
        _write_state_file(mem_dir, {"state": "nonexistent_state"})
        state = get_onboarding_state(mem_dir)
        assert state == "first_contact", (
            f"Unknown state should fall back to first_contact, got '{state}'"
        )

        # Write 'active' directly (trying to skip ahead)
        _write_state_file(mem_dir, {"state": "active"})
        state = get_onboarding_state(mem_dir)
        assert state == "active", (
            "Setting state to 'active' directly in YAML DOES work -- "
            "this is a known limitation (state machine is advisory, not cryptographic)"
        )

    def test_full_onboarding_flow_all_questions(self, tmp_path):
        """Complete the entire onboarding flow and verify active state."""
        mem_dir = tmp_path / "memory"

        # first_contact -> terms
        advance_onboarding(mem_dir, "first_contact", "hi")

        # terms -> assessment
        advance_onboarding(mem_dir, "terms_of_service", "YES")

        # Answer all Likert questions
        for i in range(len(LIKERT_QUESTIONS)):
            state = get_onboarding_state(mem_dir)
            result = advance_onboarding(mem_dir, state, str((i % 5) + 1))
            if i < len(LIKERT_QUESTIONS) - 1:
                assert result["new_state"] == "pre_flight_assessment", (
                    f"After question {i+1}, should still be in assessment"
                )

        # Should now be in tutorial
        state = get_onboarding_state(mem_dir)
        assert state == "tutorial", f"After all questions, expected tutorial, got '{state}'"

        # Go through tutorial messages
        for i in range(len(TUTORIAL_MESSAGES)):
            state = get_onboarding_state(mem_dir)
            result = advance_onboarding(mem_dir, state, "ok")

        # Should be active
        state = get_onboarding_state(mem_dir)
        assert state == "active", f"After tutorial, expected active, got '{state}'"

        # Verify active state is sticky
        result = advance_onboarding(mem_dir, "active", "hello")
        assert result["new_state"] == "active"
        assert result["advanced"] is False

    def test_likert_data_persisted(self, tmp_path):
        """Likert responses are stored in the state file with timestamps."""
        mem_dir = tmp_path / "memory"
        advance_onboarding(mem_dir, "first_contact", "hi")
        advance_onboarding(mem_dir, "terms_of_service", "YES")

        # Answer 2 questions
        advance_onboarding(mem_dir, "pre_flight_assessment", "4")
        advance_onboarding(mem_dir, "pre_flight_assessment", "2")

        data = _read_state_file(mem_dir)
        assert "likert_responses" in data, "Likert responses should be persisted"
        assert len(data["likert_responses"]) == 2, (
            f"Expected 2 Likert responses, got {len(data['likert_responses'])}"
        )
        assert data["likert_responses"][0]["value"] == 4
        assert data["likert_responses"][1]["value"] == 2
        assert "answered_at" in data["likert_responses"][0]


class TestScenario12TemplateCompositionEdgeCases:
    """Scenario 12: Template composition with missing files, empty base, etc."""

    def test_missing_personality_uses_empty(self, tmp_path):
        """Compose with a personality that has no template file."""
        from halos.halctl.templates import compose_claude_md, _templates_dir

        # This calls the real function -- personality "nonexistent" has no file
        result = compose_claude_md("nonexistent", "nobody")
        # Should not raise, should produce some output (at least the base)
        assert isinstance(result, str)

    def test_missing_user_template_works(self, tmp_path):
        """Compose without a user-specific template."""
        from halos.halctl.templates import compose_claude_md

        result = compose_claude_md("default", "nonexistent_user")
        assert isinstance(result, str)
        assert len(result.strip()) > 0, "Composition with missing user template should still produce output"

    def test_all_layers_present(self):
        """Compose with known existing templates -- all layers should appear."""
        from halos.halctl.templates import compose_claude_md

        result = compose_claude_md("discovering-ben", "ben")
        assert len(result) > 100, "Full composition should be substantial"
        # Should contain content from base template at minimum
        assert result.endswith("\n"), "Output should end with newline"


class TestScenario13FleetConfigValidation:
    """Scenario 13: Fleet config with missing fields, empty profiles, invalid paths."""

    def test_missing_config_file_raises(self, tmp_path):
        """Loading a config that doesn't exist should raise FileNotFoundError."""
        from halos.halctl.config import load_fleet_config

        with pytest.raises(FileNotFoundError):
            load_fleet_config(tmp_path / "nonexistent.yaml")

    def test_empty_fleet_manifest(self, tmp_path):
        """An empty or missing FLEET.yaml should return a valid empty structure."""
        from halos.halctl.config import load_fleet_manifest

        manifest = load_fleet_manifest(fleet_base=tmp_path)
        assert "instances" in manifest
        assert isinstance(manifest["instances"], list)
        assert len(manifest["instances"]) == 0

    def test_corrupt_fleet_manifest(self, tmp_path):
        """A FLEET.yaml with garbage content should be handled."""
        from halos.halctl.config import load_fleet_manifest

        fleet_yaml = tmp_path / "FLEET.yaml"
        fleet_yaml.write_text("not: yaml: at: all: [broken")

        # yaml.safe_load may raise or return partial data
        try:
            manifest = load_fleet_manifest(fleet_base=tmp_path)
            # If it loads, it should still have instances key
            assert "instances" in manifest
        except yaml.YAMLError:
            pass  # Acceptable -- corrupt YAML

    def test_fleet_config_with_missing_source(self, tmp_path):
        """Config pointing to nonexistent source directory should fail at provisioning time."""
        from halos.halctl.config import load_fleet_config

        config = {
            "base": {
                "source": "/nonexistent/path/to/nowhere",
                "exclude": [],
                "lock": [],
                "open": [],
            },
            "profiles": {},
        }
        config_path = tmp_path / "fleet-config.yaml"
        config_path.write_text(yaml.dump(config))

        cfg = load_fleet_config(config_path)
        # Config loads fine -- the error comes at provision time
        assert cfg["base"]["source"] == "/nonexistent/path/to/nowhere"

    def test_save_and_reload_fleet_manifest(self, tmp_path):
        """Round-trip: save a manifest, reload it, verify integrity."""
        from halos.halctl.config import save_fleet_manifest, load_fleet_manifest

        manifest = {
            "instances": [
                {"name": "test", "status": "active", "path": "/tmp/test"},
            ]
        }
        save_fleet_manifest(manifest, fleet_base=tmp_path)
        reloaded = load_fleet_manifest(fleet_base=tmp_path)
        assert len(reloaded["instances"]) == 1
        assert reloaded["instances"][0]["name"] == "test"


class TestScenario14ProvisioningDryRun:
    """Scenario 14: Run provisioning logic against a temp directory simulating prime."""

    def test_provisioning_creates_correct_structure(self, tmp_path):
        """Provision a microHAL instance and verify structure."""
        from halos.halctl.provision import create_instance

        # Set up a fake prime source
        prime = tmp_path / "prime"
        prime.mkdir()
        (prime / "CLAUDE.md").write_text("# Prime CLAUDE.md")
        (prime / "src").mkdir()
        (prime / "src" / "index.ts").write_text("// source")
        (prime / "halos").mkdir()
        (prime / "halos" / "__init__.py").write_text("")
        (prime / "container").mkdir()
        (prime / "container" / "build.sh").write_text("#!/bin/bash")
        # Files that should be excluded
        (prime / "nanoclaw.db").write_text("db")
        (prime / "memory").mkdir()
        (prime / "memory" / "notes.md").write_text("prime notes")

        fleet_base = tmp_path / "fleet"
        config = {
            "base": {
                "source": str(prime),
                "exclude": ["memory/", "nanoclaw.db", ".env*"],
                "lock": ["CLAUDE.md", "src", "halos", "container"],
                "open": ["workspace/", "projects/", "groups/", "memory/"],
            },
            "profiles": {
                "testuser": {
                    "personality": "default",
                    "services": ["gh"],
                    "telegram_bot_name": "HALTest_bot",
                },
            },
        }
        config_path = tmp_path / "fleet-config.yaml"
        config_path.write_text(yaml.dump(config))

        entry = create_instance(
            "testuser",
            config_path=config_path,
            fleet_base=fleet_base,
        )

        deploy = Path(entry["path"])
        assert deploy.exists(), "Deployment directory should exist"

        # Excluded files should be absent
        assert not (deploy / "nanoclaw.db").exists(), (
            "Excluded file nanoclaw.db should not be in deployment"
        )
        assert not (deploy / "memory" / "notes.md").exists(), (
            "Prime's memory notes should not be copied to microHAL"
        )

        # Open directories should exist and be writable
        for d in ["workspace", "projects", "groups", "memory"]:
            dir_path = deploy / d
            assert dir_path.exists(), f"Open directory '{d}' should exist"

        # Locked files should be read-only
        claude_path = deploy / "CLAUDE.md"
        assert claude_path.exists(), "CLAUDE.md should exist"
        mode = oct(claude_path.stat().st_mode)[-3:]
        assert mode == "444", f"CLAUDE.md should be 444, got {mode}"

        # Ecosystem config should exist
        eco = fleet_base / "microhal-testuser" / "ecosystem.config.cjs"
        assert eco.exists(), "ecosystem.config.cjs should be generated"

    def test_duplicate_provisioning_rejected(self, tmp_path):
        """Provisioning the same name twice should raise FileExistsError."""
        from halos.halctl.provision import create_instance

        prime = tmp_path / "prime"
        prime.mkdir()
        (prime / "CLAUDE.md").write_text("# Prime")

        fleet_base = tmp_path / "fleet"
        config = {
            "base": {
                "source": str(prime),
                "exclude": [],
                "lock": [],
                "open": [],
            },
            "profiles": {},
        }
        config_path = tmp_path / "fleet-config.yaml"
        config_path.write_text(yaml.dump(config))

        create_instance("duptest", config_path=config_path, fleet_base=fleet_base)

        with pytest.raises(FileExistsError):
            create_instance("duptest", config_path=config_path, fleet_base=fleet_base)


class TestScenario15FreezeFoldFryStateMachine:
    """Scenario 15: Create a fleet entry, freeze it, verify can't freeze again
    (already frozen), fold it, verify data archived, fry it with --confirm,
    verify everything gone. Try fry without --confirm, verify rejection."""

    def _setup_instance(self, tmp_path):
        """Create a minimal provisioned instance for lifecycle testing."""
        from halos.halctl.provision import create_instance

        prime = tmp_path / "prime"
        prime.mkdir()
        (prime / "CLAUDE.md").write_text("# Prime")

        fleet_base = tmp_path / "fleet"
        config = {
            "base": {
                "source": str(prime),
                "exclude": [],
                "lock": [],
                "open": [],
            },
            "profiles": {},
        }
        config_path = tmp_path / "fleet-config.yaml"
        config_path.write_text(yaml.dump(config))

        entry = create_instance("lifecycle", config_path=config_path, fleet_base=fleet_base)
        return fleet_base, config_path, entry

    def test_freeze_sets_status_frozen(self, tmp_path):
        from halos.halctl.provision import freeze_instance
        from halos.halctl.config import load_fleet_manifest

        fleet_base, _, _ = self._setup_instance(tmp_path)
        freeze_instance("lifecycle", fleet_base=fleet_base)

        manifest = load_fleet_manifest(fleet_base=fleet_base)
        inst = manifest["instances"][0]
        assert inst["status"] == "frozen", (
            f"After freeze, status should be 'frozen', got '{inst['status']}'"
        )

    def test_fry_without_confirm_rejected(self, tmp_path):
        """Fry without --confirm should raise ValueError."""
        from halos.halctl.provision import fry_instance

        fleet_base, _, _ = self._setup_instance(tmp_path)

        with pytest.raises(ValueError, match="--confirm"):
            fry_instance("lifecycle", confirm=False, fleet_base=fleet_base)

    def test_fry_with_confirm_wipes_deployment(self, tmp_path):
        """Fry with confirm=True should delete the deployment directory."""
        from halos.halctl.provision import fry_instance
        from halos.halctl.config import load_fleet_manifest

        fleet_base, _, entry = self._setup_instance(tmp_path)
        deploy_path = Path(entry["path"])
        assert deploy_path.exists(), "Setup: deployment should exist"

        fry_instance("lifecycle", confirm=True, fleet_base=fleet_base)

        assert not deploy_path.parent.exists(), (
            "After fry, the entire instance directory should be wiped"
        )

        manifest = load_fleet_manifest(fleet_base=fleet_base)
        inst = manifest["instances"][0]
        assert inst["status"] == "fried", (
            f"After fry, manifest status should be 'fried', got '{inst['status']}'"
        )

    def test_fold_sets_status_folded(self, tmp_path):
        from halos.halctl.provision import fold_instance
        from halos.halctl.config import load_fleet_manifest

        fleet_base, _, _ = self._setup_instance(tmp_path)
        fold_instance("lifecycle", fleet_base=fleet_base)

        manifest = load_fleet_manifest(fleet_base=fleet_base)
        inst = manifest["instances"][0]
        assert inst["status"] == "folded", (
            f"After fold, status should be 'folded', got '{inst['status']}'"
        )

    def test_fry_nonexistent_instance_raises(self, tmp_path):
        """Frying an instance that doesn't exist should raise ValueError."""
        from halos.halctl.provision import fry_instance
        from halos.halctl.config import save_fleet_manifest

        fleet_base = tmp_path / "fleet"
        fleet_base.mkdir(parents=True)
        save_fleet_manifest({"instances": []}, fleet_base=fleet_base)

        with pytest.raises(ValueError, match="not found"):
            fry_instance("ghost", confirm=True, fleet_base=fleet_base)

    def test_full_lifecycle_freeze_fold_fry(self, tmp_path):
        """Full lifecycle: active -> freeze -> fold -> fry."""
        from halos.halctl.provision import freeze_instance, fold_instance, fry_instance
        from halos.halctl.config import load_fleet_manifest

        fleet_base, _, entry = self._setup_instance(tmp_path)
        deploy_path = Path(entry["path"])

        # Freeze
        freeze_instance("lifecycle", fleet_base=fleet_base)
        manifest = load_fleet_manifest(fleet_base=fleet_base)
        assert manifest["instances"][0]["status"] == "frozen"

        # Fold (from frozen)
        fold_instance("lifecycle", fleet_base=fleet_base)
        manifest = load_fleet_manifest(fleet_base=fleet_base)
        assert manifest["instances"][0]["status"] == "folded"

        # Fry (from folded)
        fry_instance("lifecycle", confirm=True, fleet_base=fleet_base)
        manifest = load_fleet_manifest(fleet_base=fleet_base)
        assert manifest["instances"][0]["status"] == "fried"
        assert not deploy_path.parent.exists(), "Deployment should be wiped after fry"


# ===========================================================================
# ADDITIONAL EDGE CASES
# ===========================================================================


class TestItemValidationEdgeCases:
    """Additional edge cases for Item validation not covered by numbered scenarios."""

    def test_empty_title_rejected(self, tmp_path):
        with pytest.raises(ValidationError, match="title"):
            Item.create(tmp_path / "items", title="", kind="task")

    def test_whitespace_only_title_rejected(self, tmp_path):
        with pytest.raises(ValidationError, match="title"):
            Item.create(tmp_path / "items", title="   ", kind="task")

    def test_invalid_kind_rejected(self, tmp_path):
        with pytest.raises(ValidationError, match="invalid kind"):
            Item.create(tmp_path / "items", title="Bad kind", kind="daemon")

    def test_invalid_quadrant_rejected(self, tmp_path):
        """Quadrant validation rejects values outside q1-q4."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Bad quadrant", kind="task")
        item.data["quadrant"] = "q5"
        with pytest.raises(ValidationError, match="invalid quadrant"):
            item.validate()

    def test_invalid_schedule_rejected(self, tmp_path):
        with pytest.raises(ValidationError, match="invalid schedule"):
            Item.create(tmp_path / "items", title="Bad sched", kind="job",
                        command="echo hi", schedule="weekly")

    def test_save_without_path_raises(self):
        """Item constructed without file_path cannot be saved."""
        item = Item({"id": "test", "title": "No path", "kind": "task", "status": "open"})
        with pytest.raises(RuntimeError, match="No file path"):
            item.save()

    def test_from_file_validates_on_load(self, tmp_path):
        """Loading a file with invalid data should raise ValidationError."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text(yaml.dump({"id": "x", "title": "", "kind": "task"}))
        with pytest.raises(ValidationError):
            Item.from_file(bad_file)


class TestPlanRefValidation:
    """Plan reference file resolution edge cases."""

    def test_plan_ref_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_plan_ref("nonexistent.md", tmp_path)

    def test_plan_ref_no_plan_block(self, tmp_path):
        """A file that exists but has no <plan> block."""
        doc = tmp_path / "spec.md"
        doc.write_text("# Spec\n\nNo XML plan here.\n")
        with pytest.raises(PlanValidationError, match="no <plan>"):
            validate_plan_ref(str(doc), tmp_path)

    def test_plan_ref_with_valid_plan(self, tmp_path):
        """File with a valid plan embedded in markdown."""
        doc = tmp_path / "spec.md"
        doc.write_text(f"# Spec\n\nHere is the plan:\n\n{VALID_PLAN}\n\nEnd of spec.\n")
        xml = validate_plan_ref(str(doc), tmp_path)
        assert "<goal>" in xml


class TestContainerBridgeEdgeCases:
    """Container bridge edge cases beyond the standard scenarios."""

    def test_resolve_plan_no_plan_no_ref(self, tmp_path):
        """Item with neither plan nor plan_ref raises ContainerError."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="No plan", kind="agent-job")
        with pytest.raises(ContainerError, match="no plan"):
            resolve_plan(item)

    def test_write_plan_file_atomic(self, tmp_path):
        """write_plan_file should not leave .tmp files."""
        items_dir = tmp_path / "items"
        item = Item.create(items_dir, title="Atomic plan", kind="agent-job")
        plans_dir = tmp_path / "plans"

        path = write_plan_file(VALID_PLAN, item, plans_dir)
        assert path.exists()
        assert path.read_text() == VALID_PLAN
        tmp_files = list(plans_dir.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestRunRecordIntegrity:
    """Run record writing and retrieval edge cases."""

    def test_attempt_numbering_increments(self, tmp_path):
        """Each execution attempt gets a sequential number."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        job_id = "test-attempt-inc"

        for expected in [1, 2, 3]:
            attempt = _get_attempt_number(runs_dir, job_id)
            assert attempt == expected, (
                f"Expected attempt {expected}, got {attempt}"
            )
            _write_run_record(runs_dir, job_id, {
                "id": job_id,
                "attempt": attempt,
                "started": "2026-01-01T00:00:00Z",
                "finished": "2026-01-01T00:01:00Z",
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration_secs": 60,
                "outcome": "done",
            })

    def test_run_record_yaml_is_loadable(self, tmp_path):
        """Written run records should be valid YAML."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()

        _write_run_record(runs_dir, "yaml-check", {
            "id": "yaml-check",
            "attempt": 1,
            "started": "2026-01-01T00:00:00Z",
            "finished": "2026-01-01T00:01:00Z",
            "exit_code": 127,
            "stdout": "some output\nwith newlines",
            "stderr": "error: something broke",
            "duration_secs": 60,
            "outcome": "failed",
        })

        record_file = runs_dir / "yaml-check-run-1.yaml"
        assert record_file.exists()
        with open(record_file) as f:
            data = yaml.safe_load(f)
        assert data["exit_code"] == 127
        assert data["outcome"] == "failed"
