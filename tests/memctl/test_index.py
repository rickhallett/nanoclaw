"""Tests for halos.memctl.index — read, write, verify, rebuild, hashing."""
import hashlib
from pathlib import Path

import pytest

from halos.memctl.index import (
    Entry,
    Index,
    VerifyResult,
    _atomic_write,
    collect_entities,
    hash_bytes,
    hash_file,
    read,
    rebuild_from_notes,
    verify,
    write,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(**overrides) -> Entry:
    defaults = dict(
        id="20250101-120000-001",
        file="notes/test.md",
        title="Test",
        type="fact",
        tags=["tag1"],
        entities=["ent1"],
        summary="A test note.",
        hash="abc123",
        backlink_count=0,
        modified="2025-01-01T12:00:00Z",
        expires=None,
    )
    defaults.update(overrides)
    return Entry(**defaults)


VALID_NOTE_MD = """\
---
id: "20250101-120000-001"
title: "Test Note"
type: fact
tags: [testing]
entities: [claude]
backlinks: []
confidence: high
created: "2025-01-01T12:00:00Z"
modified: "2025-01-01T12:00:00Z"
---

This is a test note body.
"""


# ---------------------------------------------------------------------------
# write() and read() round-trip
# ---------------------------------------------------------------------------

class TestWriteRead:
    def test_round_trip(self, tmp_path):
        idx_path = str(tmp_path / "INDEX.md")
        entry = _make_entry()
        idx = Index(
            generated="2025-01-01T12:00:00Z",
            note_count=1,
            entities=["ent1"],
            tag_vocabulary=["tag1"],
            notes=[entry],
        )
        write(idx_path, idx)
        restored = read(idx_path)
        assert restored.note_count == 1
        assert len(restored.notes) == 1
        assert restored.notes[0].id == "20250101-120000-001"
        assert restored.notes[0].title == "Test"
        assert restored.notes[0].type == "fact"
        assert restored.notes[0].tags == ["tag1"]
        assert restored.entities == ["ent1"]
        assert restored.tag_vocabulary == ["tag1"]

    def test_read_nonexistent_file_returns_empty(self, tmp_path):
        idx = read(str(tmp_path / "nope.md"))
        assert idx.note_count == 0
        assert idx.notes == []

    def test_read_file_with_no_yaml_block(self, tmp_path):
        p = tmp_path / "INDEX.md"
        p.write_text("# just a heading\nno yaml here\n")
        idx = read(str(p))
        assert idx.note_count == 0
        assert idx.notes == []

    def test_write_creates_parent_dirs(self, tmp_path):
        idx_path = str(tmp_path / "deep" / "nested" / "INDEX.md")
        write(idx_path, Index())
        assert Path(idx_path).exists()


# ---------------------------------------------------------------------------
# hash_bytes() and hash_file()
# ---------------------------------------------------------------------------

class TestHashing:
    def test_hash_bytes_known_value(self):
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert hash_bytes(data) == expected

    def test_hash_bytes_empty(self):
        expected = hashlib.sha256(b"").hexdigest()
        assert hash_bytes(b"") == expected

    def test_hash_file(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_bytes(b"file content")
        expected = hashlib.sha256(b"file content").hexdigest()
        assert hash_file(str(p)) == expected


# ---------------------------------------------------------------------------
# verify()
# ---------------------------------------------------------------------------

class TestVerify:
    def test_match(self, tmp_path):
        p = tmp_path / "note.md"
        p.write_bytes(b"content")
        h = hash_bytes(b"content")
        entry = _make_entry(file=str(p), hash=h)
        results = verify([entry])
        assert len(results) == 1
        assert results[0].status == "MATCH"

    def test_drift(self, tmp_path):
        p = tmp_path / "note.md"
        p.write_bytes(b"original")
        entry = _make_entry(file=str(p), hash="wrong-hash")
        results = verify([entry])
        assert results[0].status == "DRIFT"

    def test_missing(self, tmp_path):
        entry = _make_entry(file=str(tmp_path / "gone.md"))
        results = verify([entry])
        assert results[0].status == "MISSING"

    def test_mixed_statuses(self, tmp_path):
        p1 = tmp_path / "match.md"
        p1.write_bytes(b"ok")
        p2 = tmp_path / "drift.md"
        p2.write_bytes(b"changed")

        entries = [
            _make_entry(id="1", file=str(p1), hash=hash_bytes(b"ok")),
            _make_entry(id="2", file=str(p2), hash="stale"),
            _make_entry(id="3", file=str(tmp_path / "missing.md")),
        ]
        results = verify(entries)
        statuses = {r.id: r.status for r in results}
        assert statuses["1"] == "MATCH"
        assert statuses["2"] == "DRIFT"
        assert statuses["3"] == "MISSING"


# ---------------------------------------------------------------------------
# rebuild_from_notes()
# ---------------------------------------------------------------------------

class TestRebuildFromNotes:
    def test_empty_dir(self, tmp_path):
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        entries, errors = rebuild_from_notes(str(notes_dir), 120)
        assert entries == []
        assert errors == 0

    def test_nonexistent_dir(self, tmp_path):
        entries, errors = rebuild_from_notes(str(tmp_path / "nope"), 120)
        assert entries == []
        assert errors == 0

    def test_valid_notes(self, tmp_path):
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "note1.md").write_text(VALID_NOTE_MD)
        entries, errors = rebuild_from_notes(str(notes_dir), 120)
        assert len(entries) == 1
        assert errors == 0
        assert entries[0].id == "20250101-120000-001"
        assert entries[0].title == "Test Note"
        assert entries[0].hash != ""

    def test_corrupt_file_counted_as_parse_error(self, tmp_path):
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "good.md").write_text(VALID_NOTE_MD)
        (notes_dir / "bad.md").write_text("no frontmatter here")
        entries, errors = rebuild_from_notes(str(notes_dir), 120)
        assert len(entries) == 1
        assert errors == 1

    def test_non_md_files_ignored(self, tmp_path):
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "readme.txt").write_text("not a note")
        (notes_dir / "data.json").write_text("{}")
        entries, errors = rebuild_from_notes(str(notes_dir), 120)
        assert entries == []
        assert errors == 0

    def test_summary_truncation(self, tmp_path):
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        long_body = "A" * 200
        note_text = f"---\nid: x\ntitle: T\ntype: fact\ntags: [t]\nconfidence: high\ncreated: now\nmodified: now\n---\n\n{long_body}\n"
        (notes_dir / "long.md").write_text(note_text)
        entries, _ = rebuild_from_notes(str(notes_dir), 50)
        assert len(entries[0].summary) <= 53  # 50 + "..."
        assert entries[0].summary.endswith("...")


# ---------------------------------------------------------------------------
# _atomic_write()
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    def test_write_succeeds(self, tmp_path):
        p = str(tmp_path / "test.md")
        _atomic_write(p, "content here")
        assert Path(p).read_text() == "content here"

    def test_no_tmp_file_remains(self, tmp_path):
        p = str(tmp_path / "test.md")
        _atomic_write(p, "content")
        assert not Path(p + ".tmp").exists()


# ---------------------------------------------------------------------------
# collect_entities()
# ---------------------------------------------------------------------------

class TestCollectEntities:
    def test_deduplication_preserves_order(self):
        entries = [
            _make_entry(entities=["alpha", "beta"]),
            _make_entry(entities=["beta", "gamma"]),
        ]
        result = collect_entities(entries)
        assert result == ["alpha", "beta", "gamma"]

    def test_empty_entries(self):
        assert collect_entities([]) == []
