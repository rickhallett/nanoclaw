"""Tests for halos.memctl.enrich — semantic link proposal engine.

These tests exercise the scoring rubric and filters without touching
real memory directories. We build minimal index files and call propose_links().
"""
from pathlib import Path

import pytest
import yaml

from halos.memctl import config as cfgmod
from halos.memctl import index as idxmod
from halos.memctl.enrich import propose_links
from halos.memctl.index import Entry, Index


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfg(tmp_path) -> cfgmod.Config:
    """Build a Config pointing at tmp_path as memory_dir."""
    return cfgmod.Config(
        memory_dir=str(tmp_path / "memory"),
        index_file=str(tmp_path / "memory" / "INDEX.md"),
    )


def _make_entry(id: str, type: str, tags: list, entities: list,
                backlink_count: int = 0, **kw) -> Entry:
    defaults = dict(
        file="", title=f"Note {id}", summary="", hash="",
        modified="2025-01-01T12:00:00Z", expires=None,
    )
    defaults.update(kw)
    return Entry(id=id, type=type, tags=tags, entities=entities,
                 backlink_count=backlink_count, **defaults)


def _write_index(cfg: cfgmod.Config, entries: list[Entry]):
    idx = Index(note_count=len(entries), notes=entries)
    Path(cfg.memory_dir).mkdir(parents=True, exist_ok=True)
    idxmod.write(cfg.index_file, idx)


def _write_note_files(cfg: cfgmod.Config, entries: list[Entry],
                      backlinks_map: dict[str, list[str]] | None = None):
    """Write minimal note .md files so propose_links can read backlinks."""
    notes_dir = Path(cfg.memory_dir) / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    backlinks_map = backlinks_map or {}
    for e in entries:
        bl = backlinks_map.get(e.id, [])
        text = (
            f"---\nid: {e.id}\ntitle: {e.title}\ntype: {e.type}\n"
            f"tags: {e.tags}\nentities: {e.entities}\n"
            f"backlinks: {bl}\nconfidence: high\n"
            f"created: 2025-01-01T12:00:00Z\nmodified: 2025-01-01T12:00:00Z\n"
            f"---\n\nBody of {e.id}.\n"
        )
        (notes_dir / f"{e.id}.md").write_text(text)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNoSharedMetadata:
    def test_no_overlap_filtered_at_threshold_7(self, tmp_path):
        """Two notes with zero shared tags/entities => semantic_bridge=0, low score, filtered."""
        cfg = _make_cfg(tmp_path)
        entries = [
            _make_entry("a", "fact", ["alpha"], ["x"]),
            _make_entry("b", "fact", ["beta"], ["y"]),
        ]
        _write_index(cfg, entries)
        _write_note_files(cfg, entries)
        proposals = propose_links(cfg, verbose=False)
        assert proposals == []


class TestSharedTags:
    def test_one_to_two_shared_tags_sweet_spot(self, tmp_path):
        """1-2 shared tags (after noise exclusion) => semantic_bridge=2."""
        cfg = _make_cfg(tmp_path)
        entries = [
            _make_entry("a", "person", ["security", "ops"], ["kai", "alice"],
                        backlink_count=1),
            _make_entry("b", "decision", ["security", "policy"], ["alice"],
                        backlink_count=1),
        ]
        _write_index(cfg, entries)
        _write_note_files(cfg, entries)
        proposals = propose_links(cfg, verbose=True)  # lower threshold to see results
        # Should have at least one proposal with semantic_bridge=2
        bridges = [p["dimensions"]["semantic_bridge"] for p in proposals]
        assert 2 in bridges


class TestCrossType:
    def test_cross_type_scores_higher(self, tmp_path):
        """person<->decision should get cross_type=2."""
        cfg = _make_cfg(tmp_path)
        entries = [
            _make_entry("a", "person", ["ops"], ["shared-ent"], backlink_count=1),
            _make_entry("b", "decision", ["ops"], ["shared-ent"], backlink_count=1),
        ]
        _write_index(cfg, entries)
        _write_note_files(cfg, entries)
        proposals = propose_links(cfg, verbose=True)
        for p in proposals:
            if p["from_type"] != p["to_type"]:
                assert p["dimensions"]["cross_type"] == 2
                return
        # If no proposal found at all, that's also informative
        # but given our setup (shared metadata, cross-type, backlinks)
        # we expect at least one.
        assert proposals, "Expected at least one cross-type proposal"


class TestAlreadyLinked:
    def test_already_linked_excluded(self, tmp_path):
        """Pairs that already have backlinks between them are skipped."""
        cfg = _make_cfg(tmp_path)
        entries = [
            _make_entry("a", "fact", ["ops"], ["shared"], backlink_count=1),
            _make_entry("b", "decision", ["ops"], ["shared"], backlink_count=1),
        ]
        _write_index(cfg, entries)
        # Write note files with a<->b backlink
        _write_note_files(cfg, entries, backlinks_map={"a": ["b"]})
        proposals = propose_links(cfg, verbose=True)
        pair_ids = {(p["from_id"], p["to_id"]) for p in proposals}
        assert ("a", "b") not in pair_ids
        assert ("b", "a") not in pair_ids


class TestBothPerson:
    def test_both_person_excluded(self, tmp_path):
        """person<->person pairs are filtered out."""
        cfg = _make_cfg(tmp_path)
        entries = [
            _make_entry("a", "person", ["team"], ["alice"]),
            _make_entry("b", "person", ["team"], ["bob"]),
        ]
        _write_index(cfg, entries)
        _write_note_files(cfg, entries)
        proposals = propose_links(cfg, verbose=True)
        assert proposals == []


class TestNoiseTags:
    def test_noise_tags_excluded_from_scoring(self, tmp_path):
        """Tags like 'the-pit', 'identity' are in NOISE_TAGS and don't count as shared."""
        cfg = _make_cfg(tmp_path)
        # Only shared tag is 'identity' which is noise — no real overlap
        entries = [
            _make_entry("a", "fact", ["identity"], ["x"]),
            _make_entry("b", "reference", ["identity"], ["y"]),
        ]
        _write_index(cfg, entries)
        _write_note_files(cfg, entries)
        proposals = propose_links(cfg, verbose=False)
        # With no real shared metadata, semantic_bridge=0, score too low
        assert proposals == []
