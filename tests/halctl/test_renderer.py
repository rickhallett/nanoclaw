"""Tests for the parameterised personality renderer."""

import copy
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:
    from halos.nightctl import yaml_shim as yaml

from halos.halctl.renderer import (
    SchemaValidationError,
    _build_dimension_index,
    _load_yaml,
    _strip_frontmatter,
    _validate_profile,
    render_personality,
)


# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "templates" / "microhal"
SCHEMA_PATH = TEMPLATES_DIR / "personality-schema.yaml"
PROFILES_DIR = TEMPLATES_DIR / "profiles"
BLOCKS_DIR = TEMPLATES_DIR / "blocks"


class TestSchemaLoading(unittest.TestCase):
    """Schema loads and has expected structure."""

    def test_schema_loads(self):
        schema = _load_yaml(SCHEMA_PATH)
        self.assertIn("schema_version", schema)
        self.assertIn("categories", schema)

    def test_schema_has_16_dimensions(self):
        schema = _load_yaml(SCHEMA_PATH)
        dim_index = _build_dimension_index(schema)
        self.assertEqual(len(dim_index), 16)

    def test_schema_has_5_categories(self):
        schema = _load_yaml(SCHEMA_PATH)
        self.assertEqual(len(schema["categories"]), 5)

    def test_warmth_has_three_levels(self):
        """warmth should have clinical/neutral/warm (no effusive)."""
        schema = _load_yaml(SCHEMA_PATH)
        dim_index = _build_dimension_index(schema)
        warmth = dim_index["warmth"]
        self.assertEqual(warmth["levels"], ["clinical", "neutral", "warm"])
        self.assertNotIn("effusive", warmth["levels"])


class TestProfileValidation(unittest.TestCase):
    """Profile validation catches errors."""

    def setUp(self):
        self.schema = _load_yaml(SCHEMA_PATH)
        self.dim_index = _build_dimension_index(self.schema)
        self.ben_profile = _load_yaml(PROFILES_DIR / "ben.yaml")

    def test_ben_profile_validates(self):
        _validate_profile(self.ben_profile, self.dim_index)

    def test_default_profile_validates(self):
        default_profile = _load_yaml(PROFILES_DIR / "default.yaml")
        _validate_profile(default_profile, self.dim_index)

    def test_missing_dimension_raises(self):
        bad = copy.deepcopy(self.ben_profile)
        del bad["dimensions"]["brevity"]
        with self.assertRaises(SchemaValidationError) as ctx:
            _validate_profile(bad, self.dim_index)
        self.assertIn("Missing dimensions", str(ctx.exception))
        self.assertIn("brevity", str(ctx.exception))

    def test_unknown_dimension_raises(self):
        bad = copy.deepcopy(self.ben_profile)
        bad["dimensions"]["nonexistent_thing"] = "value"
        with self.assertRaises(SchemaValidationError) as ctx:
            _validate_profile(bad, self.dim_index)
        self.assertIn("Unknown dimensions", str(ctx.exception))
        self.assertIn("nonexistent_thing", str(ctx.exception))

    def test_invalid_ordinal_value_raises(self):
        bad = copy.deepcopy(self.ben_profile)
        bad["dimensions"]["brevity"] = "superlative"
        with self.assertRaises(SchemaValidationError):
            _validate_profile(bad, self.dim_index)

    def test_invalid_boolean_type_raises(self):
        bad = copy.deepcopy(self.ben_profile)
        bad["dimensions"]["summary_default"] = "yes"
        with self.assertRaises(SchemaValidationError):
            _validate_profile(bad, self.dim_index)

    def test_integer_out_of_range_raises(self):
        bad = copy.deepcopy(self.ben_profile)
        bad["dimensions"]["max_options"] = 99
        with self.assertRaises(SchemaValidationError):
            _validate_profile(bad, self.dim_index)


class TestRendering(unittest.TestCase):
    """Render produces expected output."""

    def _render(self, profile_name: str) -> str:
        return render_personality(
            profile_name=profile_name,
            schema_path=SCHEMA_PATH,
            profiles_dir=PROFILES_DIR,
            blocks_dir=BLOCKS_DIR,
        )

    def test_ben_renders_without_error(self):
        result = self._render("ben")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 100)

    def test_default_renders_without_error(self):
        result = self._render("default")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 100)

    def test_preamble_is_first(self):
        result = self._render("ben")
        self.assertTrue(
            result.startswith("## Core Principle"),
            f"Rendered output should start with preamble, got: {result[:80]!r}",
        )

    def test_ben_contains_key_do_dont_examples(self):
        """Ben's rendered profile should contain the deployed DO/DON'T prose."""
        result = self._render("ben")

        # From brevity/minimal block (deployed CLAUDE.md: Brevity section)
        self.assertIn(
            "Here's the key points. Want me to go deeper on any of these?",
            result,
        )
        self.assertIn(
            "Dump 1,500 words in response to an open-ended question",
            result,
        )

        # From max_options/1 block (deployed CLAUDE.md: One Recommendation)
        self.assertIn(
            "For your situation, I'd go with X because [reason].",
            result,
        )
        self.assertIn(
            "Which factors matter most to you?",
            result,
        )

        # From completion_signalling/firm block
        self.assertIn(
            "The last couple of changes are lateral",
            result,
        )
        self.assertIn(
            "Scope creep is the perfectionism cycle wearing a productivity hat.",
            result,
        )

        # From frustration_response/pause block
        self.assertIn(
            "Want to come back to this in a bit, or",
            result,
        )
        self.assertIn(
            "factual complaints carry more weight than emotional ones",
            result,
        )

    def test_ben_contains_bounded_helpfulness(self):
        result = self._render("ben")
        self.assertIn(
            "Bounded helpfulness beats unbounded compliance",
            result,
        )

    def test_deterministic_output(self):
        """Same inputs produce identical output."""
        result1 = self._render("ben")
        result2 = self._render("ben")
        self.assertEqual(result1, result2)

    def test_multi_dimension_block_satisfies_covered_dims(self):
        """The firm completion_signalling block covers iteration_cap and
        scope_creep_detection, so those should NOT appear as separate headings."""
        result = self._render("ben")
        # The firm block mentions scope creep, so content is there
        self.assertIn("Scope creep", result)
        # But iteration_cap and scope_creep_detection should not
        # produce their own separate block content since they're covered
        # by the multi-dimension block. Count occurrences of the
        # "This is finished" phrase — should appear exactly once.
        count = result.count("This is finished.")
        self.assertEqual(count, 1, f"'This is finished.' should appear once, got {count}")

    def test_ben_contains_energy_riding_prose(self):
        result = self._render("ben")
        self.assertIn("support momentum", result)
        self.assertIn("Deep dives are good", result)

    def test_ben_contains_warmth_prose(self):
        result = self._render("ben")
        self.assertIn("genuinely warm but not performative", result)

    def test_ben_contains_apology_suppression(self):
        result = self._render("ben")
        self.assertIn("Don't over-apologise", result)


class TestFrontmatterParsing(unittest.TestCase):
    """Frontmatter parsing utility works correctly."""

    def test_no_frontmatter(self):
        meta, body = _strip_frontmatter("Just some text.")
        self.assertEqual(meta, {})
        self.assertEqual(body, "Just some text.")

    def test_with_frontmatter(self):
        text = "---\ncovers: [a, b]\n---\nBody here."
        meta, body = _strip_frontmatter(text)
        self.assertEqual(meta["covers"], ["a", "b"])
        self.assertEqual(body.strip(), "Body here.")


class TestLegacyFallback(unittest.TestCase):
    """compose_claude_md falls back to legacy .md when no YAML profile."""

    def test_unknown_user_uses_legacy_personality(self):
        from halos.halctl.templates import compose_claude_md
        # "unknownuser" has no YAML profile — should fall back to .md
        result = compose_claude_md(
            personality="discovering-ben",
            user_name="unknownuser",
        )
        # Should include base.md content
        self.assertIn("microHAL", result)
        # Should include legacy personality content (if file exists)
        # The key point is no crash

    def test_ben_uses_yaml_profile(self):
        from halos.halctl.templates import compose_claude_md
        result = compose_claude_md(
            personality="discovering-ben",
            user_name="ben",
        )
        # Should have YAML-rendered content (preamble from blocks)
        self.assertIn("Bounded helpfulness beats unbounded compliance", result)
        # Should also have user context
        self.assertIn("User Context", result)


if __name__ == "__main__":
    unittest.main()
