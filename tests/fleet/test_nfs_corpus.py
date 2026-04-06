"""Tier 1: NFS memory corpus integrity and propagation.

Proves the shared memory architecture works: authority writes,
advisors read, nobody who shouldn't write can.
"""

import hashlib
import time
import uuid

import pytest

from .conftest import EXPECTED_ADVISORS, FLEET_NS

pytestmark = [pytest.mark.fleet, pytest.mark.tier1]


class TestNFSHashPropagation:
    """Write a unique hash via authority, verify all advisors see it."""

    def test_write_propagates_to_all_advisors(self, kubectl_exec, advisor_pod_names):
        """The Neo Test: cryptographic proof that NFS propagation works."""
        # Generate unique signal
        signal = uuid.uuid4().hex
        signal_hash = hashlib.sha256(signal.encode()).hexdigest()
        test_file = "/memory/test-signal.md"

        # Get authority pod name
        from .conftest import _kubectl_json
        pods = _kubectl_json("get", "pods")
        authority_pod = None
        for p in pods["items"]:
            if p["metadata"]["name"].startswith("memctl-authority-"):
                authority_pod = p["metadata"]["name"]
                break
        assert authority_pod, "memctl-authority pod not found"

        try:
            # Write via authority
            kubectl_exec(
                authority_pod,
                f'echo "{signal_hash}" > {test_file}',
                container="authority",
            )

            # Verify each advisor reads the exact hash
            # Allow up to 2s for NFS propagation (should be instant)
            deadline = time.time() + 2.0
            failures = {}

            for name, pod_name in advisor_pod_names.items():
                while True:
                    try:
                        result = kubectl_exec(pod_name, f"cat {test_file}")
                        if result.strip() == signal_hash:
                            break
                        if time.time() > deadline:
                            failures[name] = f"got '{result.strip()[:40]}', expected '{signal_hash[:40]}'"
                            break
                    except RuntimeError:
                        if time.time() > deadline:
                            failures[name] = "file not readable"
                            break
                        time.sleep(0.1)

            assert not failures, f"NFS propagation failed for: {failures}"

        finally:
            # Cleanup
            try:
                kubectl_exec(authority_pod, f"rm -f {test_file}", container="authority")
            except RuntimeError:
                pass


class TestNFSReadOnly:
    """Advisors must not be able to write to /memory/."""

    @pytest.mark.parametrize("advisor", EXPECTED_ADVISORS)
    def test_advisor_cannot_write(self, kubectl, advisor, advisor_pod_names):
        if advisor not in advisor_pod_names:
            pytest.skip(f"advisor-{advisor} not running")

        pod_name = advisor_pod_names[advisor]
        result = kubectl(
            "exec", pod_name, "--",
            "touch", "/memory/test-write-forbidden",
        )
        # Should fail with permission denied or read-only filesystem
        assert result.returncode != 0, (
            f"advisor-{advisor} was able to write to /memory/ — security violation"
        )


class TestNFSCorpusIntegrity:
    """Memory corpus is complete and parseable."""

    def test_index_exists_and_parseable(self, kubectl_exec, advisor_pod_names):
        # Pick any advisor
        pod = list(advisor_pod_names.values())[0]
        result = kubectl_exec(pod, "head -5 /memory/INDEX.md")
        assert "MEMORY INDEX" in result, f"INDEX.md header not found: {result[:100]}"

    def test_note_count_matches_index(self, kubectl_exec, advisor_pod_names):
        pod = list(advisor_pod_names.values())[0]
        file_count = kubectl_exec(pod, "ls /memory/notes/*.md 2>/dev/null | wc -l")
        file_count = int(file_count.strip())
        assert file_count > 100, f"Expected >100 notes, found {file_count}"

        # Check index claims the same count
        index_count = kubectl_exec(
            pod,
            "grep 'note_count:' /memory/INDEX.md | head -1 | awk '{print $2}'"
        )
        index_count = int(index_count.strip())
        assert abs(file_count - index_count) <= 5, (
            f"Note count mismatch: {file_count} files vs {index_count} in index"
        )

    def test_reflections_present(self, kubectl_exec, advisor_pod_names):
        pod = list(advisor_pod_names.values())[0]
        count = kubectl_exec(pod, "ls /memory/reflections/*.md 2>/dev/null | wc -l")
        assert int(count.strip()) > 0, "No reflections found on NFS"
