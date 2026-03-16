"""Tests for yaml_shim — loader and dumper."""
import sys
import os
import io
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nightctl_lib.yaml_shim import safe_load, dump


class TestScalars(unittest.TestCase):
    def test_string(self):
        self.assertEqual(safe_load("key: hello"), {"key": "hello"})

    def test_quoted_string(self):
        self.assertEqual(safe_load('key: "hello world"'), {"key": "hello world"})

    def test_integer(self):
        self.assertEqual(safe_load("key: 42"), {"key": 42})
        self.assertIsInstance(safe_load("key: 42")["key"], int)

    def test_float(self):
        self.assertEqual(safe_load("key: 3.14"), {"key": 3.14})

    def test_bool_true(self):
        result = safe_load("key: true")
        self.assertIs(result["key"], True)
        self.assertIsInstance(result["key"], bool)

    def test_bool_false(self):
        result = safe_load("key: false")
        self.assertIs(result["key"], False)
        self.assertIsInstance(result["key"], bool)

    def test_null_tilde(self):
        self.assertIsNone(safe_load("key: ~")["key"])

    def test_null_keyword(self):
        self.assertIsNone(safe_load("key: null")["key"])

    def test_empty_value(self):
        self.assertIsNone(safe_load("key:")["key"])

    def test_string_with_colon(self):
        result = safe_load('key: "http://example.com"')
        self.assertEqual(result["key"], "http://example.com")

    def test_integer_zero(self):
        result = safe_load("key: 0")
        self.assertEqual(result["key"], 0)
        self.assertIsInstance(result["key"], int)

    def test_multiple_keys(self):
        result = safe_load("a: 1\nb: 2\nc: 3\n")
        self.assertEqual(result, {"a": 1, "b": 2, "c": 3})


class TestInlineLists(unittest.TestCase):
    def test_inline_list(self):
        self.assertEqual(safe_load("tags: [a, b, c]"), {"tags": ["a", "b", "c"]})

    def test_empty_inline_list(self):
        result = safe_load("tags: []")
        self.assertEqual(result["tags"], [])
        self.assertIsInstance(result["tags"], list)

    def test_inline_list_integers(self):
        result = safe_load("nums: [1, 2, 3]")
        self.assertEqual(result["nums"], [1, 2, 3])
        self.assertIsInstance(result["nums"][0], int)

    def test_inline_list_mixed(self):
        result = safe_load("vals: [foo, 42, true]")
        self.assertEqual(result["vals"][0], "foo")
        self.assertEqual(result["vals"][1], 42)
        self.assertIs(result["vals"][2], True)


class TestBlockLists(unittest.TestCase):
    def test_block_list_of_scalars(self):
        yaml = "items:\n  - alpha\n  - beta\n  - gamma\n"
        result = safe_load(yaml)
        self.assertEqual(result["items"], ["alpha", "beta", "gamma"])

    def test_block_list_of_dicts(self):
        yaml = (
            "jobs:\n"
            "  - id: abc\n"
            "    title: Test job\n"
            "    status: pending\n"
            "  - id: def\n"
            "    title: Second job\n"
            "    status: done\n"
        )
        result = safe_load(yaml)
        self.assertEqual(len(result["jobs"]), 2)
        self.assertEqual(result["jobs"][0]["id"], "abc")
        self.assertEqual(result["jobs"][0]["title"], "Test job")
        self.assertEqual(result["jobs"][0]["status"], "pending")
        self.assertEqual(result["jobs"][1]["id"], "def")
        self.assertEqual(result["jobs"][1]["status"], "done")

    def test_block_list_dict_with_nested_list(self):
        yaml = (
            "jobs:\n"
            "  - id: abc\n"
            "    tags:\n"
            "      - maintenance\n"
            "      - memctl\n"
            "    status: pending\n"
        )
        result = safe_load(yaml)
        self.assertEqual(result["jobs"][0]["id"], "abc")
        self.assertEqual(result["jobs"][0]["tags"], ["maintenance", "memctl"])
        self.assertEqual(result["jobs"][0]["status"], "pending")

    def test_block_list_preserves_order(self):
        yaml = "items:\n  - z\n  - a\n  - m\n"
        result = safe_load(yaml)
        self.assertEqual(result["items"], ["z", "a", "m"])


class TestNestedDicts(unittest.TestCase):
    def test_nested_dict(self):
        yaml = "execution:\n  mode: serial\n  max_workers: 1\n"
        result = safe_load(yaml)
        self.assertEqual(result["execution"]["mode"], "serial")
        self.assertEqual(result["execution"]["max_workers"], 1)

    def test_deeply_nested(self):
        yaml = "a:\n  b:\n    c: deep\n"
        result = safe_load(yaml)
        self.assertEqual(result["a"]["b"]["c"], "deep")

    def test_sibling_keys_dont_bleed(self):
        yaml = "outer:\n  x: 1\n  y: 2\ntop: 3\n"
        result = safe_load(yaml)
        self.assertEqual(result["outer"]["x"], 1)
        self.assertEqual(result["outer"]["y"], 2)
        self.assertEqual(result["top"], 3)
        self.assertNotIn("top", result["outer"])


class TestComments(unittest.TestCase):
    def test_comment_line_skipped(self):
        yaml = "# this is a comment\nkey: value\n"
        self.assertEqual(safe_load(yaml), {"key": "value"})

    def test_comment_does_not_produce_key(self):
        result = safe_load("# comment\nkey: value\n")
        self.assertEqual(len(result), 1)
        self.assertNotIn("comment", result)


class TestFileObject(unittest.TestCase):
    def test_file_like_object(self):
        f = io.StringIO("key: value\n")
        self.assertEqual(safe_load(f), {"key": "value"})

    def test_file_like_multiline(self):
        f = io.StringIO("a: 1\nb: 2\n")
        result = safe_load(f)
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 2)


class TestDumperFormat(unittest.TestCase):
    """Verify the actual text format produced by dump(), not just roundtrip."""

    def test_flat_dict_key_value_format(self):
        obj = {"key": "value"}
        text = dump(obj)
        self.assertIn("key: value", text)

    def test_integer_not_quoted(self):
        obj = {"num": 42}
        text = dump(obj)
        self.assertIn("num: 42", text)
        self.assertNotIn('"42"', text)
        self.assertNotIn("'42'", text)

    def test_null_written_as_null_keyword(self):
        obj = {"key": None}
        text = dump(obj)
        self.assertIn("key: null", text)
        self.assertNotIn("key: None", text)

    def test_bools_written_lowercase(self):
        obj = {"a": True, "b": False}
        text = dump(obj)
        self.assertIn("a: true", text)
        self.assertIn("b: false", text)
        self.assertNotIn("True", text)
        self.assertNotIn("False", text)

    def test_simple_list_written_inline(self):
        # Simple scalar lists should be [a, b, c] not block style
        obj = {"tags": ["a", "b", "c"]}
        text = dump(obj)
        self.assertIn("tags: [a, b, c]", text)
        self.assertNotIn("- a", text)

    def test_empty_list_written_as_brackets(self):
        obj = {"tags": []}
        text = dump(obj)
        self.assertIn("tags: []", text)

    def test_nested_dict_uses_indentation(self):
        obj = {"outer": {"inner": "val"}}
        text = dump(obj)
        lines = text.strip().splitlines()
        self.assertTrue(any(l.startswith("outer:") for l in lines))
        self.assertTrue(any("inner: val" in l for l in lines))
        inner_line = next(l for l in lines if "inner: val" in l)
        self.assertTrue(inner_line.startswith(" "), "nested key should be indented")

    def test_special_chars_quoted(self):
        obj = {"url": "http://example.com"}
        text = dump(obj)
        # colon in value must be quoted
        self.assertIn('"http://example.com"', text)

    def test_stream_writes_and_returns_none(self):
        obj = {"key": "val"}
        buf = io.StringIO()
        result = dump(obj, stream=buf)
        self.assertIsNone(result)
        self.assertIn("key: val", buf.getvalue())

    def test_sort_keys_false_preserves_insertion_order(self):
        # keys should appear in insertion order when sort_keys=False
        obj = {"z": 1, "a": 2, "m": 3}
        text = dump(obj, sort_keys=False)
        positions = {k: text.index(k + ":") for k in "zam"}
        self.assertLess(positions["z"], positions["a"])
        self.assertLess(positions["a"], positions["m"])

    def test_list_of_dicts_block_style(self):
        obj = {"jobs": [{"id": "abc", "status": "pending"}]}
        text = dump(obj)
        self.assertIn("jobs:", text)
        self.assertIn("- id:", text)
        self.assertIn("status: pending", text)


class TestRoundtrip(unittest.TestCase):
    """Roundtrip tests validate that load(dump(x)) == x.
    These are necessary but not sufficient — format tests are in TestDumperFormat."""

    def test_roundtrip_flat(self):
        obj = {"id": "20260315-221515-abc12345", "title": "Test", "priority": 1, "status": "pending"}
        recovered = safe_load(dump(obj, sort_keys=False))
        self.assertEqual(recovered["id"], obj["id"])
        self.assertEqual(recovered["priority"], 1)
        self.assertIsInstance(recovered["priority"], int)
        self.assertEqual(recovered["status"], obj["status"])

    def test_roundtrip_with_list(self):
        obj = {"tags": ["maintenance", "memctl"], "status": "pending"}
        recovered = safe_load(dump(obj, sort_keys=False))
        self.assertEqual(recovered["tags"], ["maintenance", "memctl"])
        self.assertIsInstance(recovered["tags"], list)

    def test_roundtrip_preserves_types(self):
        obj = {"n": 42, "b": True, "f": 3.14, "s": "hello", "none": None}
        recovered = safe_load(dump(obj, sort_keys=False))
        self.assertIsInstance(recovered["n"], int)
        self.assertIs(recovered["b"], True)
        self.assertIsNone(recovered["none"])

    def test_roundtrip_list_of_dicts(self):
        obj = {
            "jobs": [
                {"id": "abc", "title": "Job A", "status": "done", "tags": ["x", "y"]},
                {"id": "def", "title": "Job B", "status": "pending", "tags": []},
            ]
        }
        recovered = safe_load(dump(obj, sort_keys=True))
        self.assertEqual(len(recovered["jobs"]), 2)
        # verify values, not just presence
        job_a = next(j for j in recovered["jobs"] if j["id"] == "abc")
        job_b = next(j for j in recovered["jobs"] if j["id"] == "def")
        self.assertEqual(job_a["status"], "done")
        self.assertEqual(job_a["tags"], ["x", "y"])
        self.assertEqual(job_b["status"], "pending")
        self.assertEqual(job_b["tags"], [])

    def test_roundtrip_zero_int(self):
        obj = {"retries": 0, "priority": 0}
        recovered = safe_load(dump(obj, sort_keys=False))
        self.assertEqual(recovered["retries"], 0)
        self.assertIsInstance(recovered["retries"], int)


if __name__ == "__main__":
    unittest.main()
