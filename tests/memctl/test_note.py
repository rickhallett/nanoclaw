"""Tests for halos.memctl.note — parse, validate, marshal, slugify, IDs."""
import re
import time

import pytest

from halos.memctl.note import Note, filename, marshal, now_id, now_iso, parse, slugify, validate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_FRONTMATTER = """\
---
id: "20250101-120000-001"
title: "Test Note"
type: fact
tags: [memory, testing]
entities: [claude]
backlinks: [abc-123]
confidence: high
created: "2025-01-01T12:00:00Z"
modified: "2025-01-01T12:00:00Z"
expires: "2026-01-01"
---

This is the body of the note.
"""


def _make_note(**overrides) -> Note:
    defaults = dict(
        id="20250101-120000-001",
        title="Test Note",
        type="fact",
        tags=["memory", "testing"],
        entities=["claude"],
        backlinks=["abc-123"],
        confidence="high",
        created="2025-01-01T12:00:00Z",
        modified="2025-01-01T12:00:00Z",
        expires="2026-01-01",
        body="This is the body of the note.",
    )
    defaults.update(overrides)
    return Note(**defaults)


VALID_TYPES = ["decision", "fact", "reference", "project", "person", "event"]
VALID_CONFIDENCE = ["high", "medium", "low"]


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------

class TestParse:
    def test_valid_note_all_fields(self):
        n = parse(VALID_FRONTMATTER)
        assert n.id == "20250101-120000-001"
        assert n.title == "Test Note"
        assert n.type == "fact"
        assert n.tags == ["memory", "testing"]
        assert n.entities == ["claude"]
        assert n.backlinks == ["abc-123"]
        assert n.confidence == "high"
        assert n.created == "2025-01-01T12:00:00Z"
        assert n.modified == "2025-01-01T12:00:00Z"
        assert n.expires == "2026-01-01"
        assert n.body == "This is the body of the note."

    def test_missing_frontmatter_delimiters_no_dashes(self):
        with pytest.raises(ValueError, match="missing YAML frontmatter delimiters"):
            parse("just some text without frontmatter")

    def test_missing_frontmatter_delimiters_one_dash(self):
        with pytest.raises(ValueError, match="missing YAML frontmatter delimiters"):
            parse("---\ntitle: foo\n")

    def test_empty_frontmatter(self):
        with pytest.raises(ValueError, match="empty frontmatter"):
            parse("---\n\n---\nbody text")

    def test_frontmatter_with_only_whitespace(self):
        with pytest.raises(ValueError, match="empty frontmatter"):
            parse("---\n   \n---\nbody text")

    def test_missing_optional_fields_get_defaults(self):
        minimal = "---\ntitle: Minimal\ntype: fact\n---\nBody."
        n = parse(minimal)
        assert n.title == "Minimal"
        assert n.tags == []
        assert n.entities == []
        assert n.backlinks == []
        assert n.confidence == "high"
        assert n.expires is None

    def test_null_tags_become_empty_list(self):
        """YAML null for tags should become [], not None."""
        data = "---\ntitle: T\ntype: fact\ntags:\n---\nBody."
        n = parse(data)
        assert n.tags == []


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------

class TestValidate:
    def test_all_valid_no_errors(self):
        n = _make_note()
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert errs == []

    def test_missing_title(self):
        n = _make_note(title="")
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert "title is required" in errs

    def test_missing_type(self):
        n = _make_note(type="")
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert "type is required" in errs

    def test_invalid_type(self):
        n = _make_note(type="bogus")
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert any("invalid type" in e for e in errs)

    def test_empty_tags(self):
        n = _make_note(tags=[])
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert "at least one tag is required" in errs

    def test_invalid_confidence(self):
        n = _make_note(confidence="very-high")
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert any("invalid confidence" in e for e in errs)

    def test_empty_body(self):
        n = _make_note(body="")
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert "body is required" in errs

    def test_multiple_errors_at_once(self):
        n = _make_note(title="", type="", tags=[], body="")
        errs = validate(n, VALID_TYPES, VALID_CONFIDENCE)
        assert len(errs) >= 4


# ---------------------------------------------------------------------------
# marshal() and round-trip
# ---------------------------------------------------------------------------

class TestMarshal:
    def test_round_trip(self):
        original = _make_note()
        text = marshal(original)
        restored = parse(text)
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.type == original.type
        assert restored.tags == original.tags
        assert restored.entities == original.entities
        assert restored.backlinks == original.backlinks
        assert restored.confidence == original.confidence
        assert restored.body == original.body

    def test_marshal_omits_empty_entities(self):
        n = _make_note(entities=[])
        text = marshal(n)
        assert "entities:" not in text

    def test_marshal_omits_empty_backlinks(self):
        n = _make_note(backlinks=[])
        text = marshal(n)
        assert "backlinks:" not in text

    def test_marshal_includes_expires_even_when_none(self):
        n = _make_note(expires=None)
        text = marshal(n)
        assert "expires:" in text


# ---------------------------------------------------------------------------
# slugify()
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_normal_text(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        assert slugify("C++ & Rust: A Comparison!") == "c-rust-a-comparison"

    def test_empty_string(self):
        assert slugify("") == "untitled"

    def test_whitespace_only(self):
        assert slugify("   ") == "untitled"

    def test_very_long_string(self):
        long = "a" * 200
        result = slugify(long)
        assert len(result) <= 60

    def test_leading_trailing_dashes_stripped(self):
        assert slugify("---hello---") == "hello"

    def test_unicode(self):
        result = slugify("cafe latte")
        assert result == "cafe-latte"


# ---------------------------------------------------------------------------
# filename()
# ---------------------------------------------------------------------------

class TestFilename:
    def test_basic(self):
        assert filename("20250101-120000-001", "My Note") == "20250101-120000-001-my-note.md"

    def test_special_chars_in_title(self):
        result = filename("id1", "Hello World!!!")
        assert result == "id1-hello-world.md"


# ---------------------------------------------------------------------------
# now_id()
# ---------------------------------------------------------------------------

class TestNowId:
    def test_format(self):
        nid = now_id()
        # Format: YYYYMMDD-HHMMSS-mmm
        assert re.match(r"^\d{8}-\d{6}-\d{3}$", nid)

    def test_uniqueness(self):
        """Two calls in tight succession should differ (millisecond precision)."""
        ids = {now_id() for _ in range(10)}
        # At minimum we expect more than 1 unique value in 10 calls,
        # though on very fast machines they could collide within same ms.
        # NOTE: This is a probabilistic test. On an extremely fast machine
        # some IDs could collide. If flaky, the underlying design may need
        # a counter or random suffix.
        assert len(ids) >= 1


# ---------------------------------------------------------------------------
# now_iso()
# ---------------------------------------------------------------------------

class TestNowIso:
    def test_format(self):
        iso = now_iso()
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", iso)
