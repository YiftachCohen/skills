"""Regression tests for plan 003's crash fixes: validate() must never raise.

--check is the mode that exists to diagnose a malformed map, so a malformed
map has to come back as a readable error, not a Python traceback. Same
by-path import shim as atlas/tests/test_render.py (render.py lives outside
any package). Run with: python3 -m unittest discover atlas/tests -v
"""

import importlib.util
import pathlib
import tempfile
import unittest

_RENDER = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "render.py"
_spec = importlib.util.spec_from_file_location("atlas_render", _RENDER)
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)

# name, malformed shape
_MALFORMED_SHAPES = [
    ("top-level array", ["a"]),
    ("node is a string",
     {"version": 2, "project": {"name": "x"},
      "graph": {"nodes": ["oops"], "edges": []}}),
    ("edge is a string",
     {"version": 2, "project": {"name": "x"},
      "graph": {"nodes": [{"id": "a", "kind": "service"}], "edges": ["a"]}}),
    ("nodes is a dict",
     {"version": 2, "project": {"name": "x"},
      "graph": {"nodes": {"a": 1}, "edges": []}}),
    ("id is a list",
     {"version": 2, "project": {"name": "x"},
      "graph": {"nodes": [{"id": [], "kind": "service"}], "edges": []}}),
]


class TestMalformedShapesDoNotRaise(unittest.TestCase):
    def test_malformed_shapes(self):
        for name, data in _MALFORMED_SHAPES:
            with self.subTest(name=name):
                # validate() must return, never raise, and report the
                # malformation as a non-empty errors list.
                errors, warnings, top_level, node_count, edge_count = render.validate(data)
                self.assertTrue(errors, f"{name}: expected a non-empty errors list")


class TestNullEdges(unittest.TestCase):
    def test_null_edges_validates_cleanly(self):
        data = {
            "version": 2,
            "project": {"name": "x"},
            "graph": {
                "nodes": [{"id": "a", "label": "A", "kind": "service", "detail": "d"}],
                "edges": None,
            },
        }
        errors, warnings, top_level, node_count, edge_count = render.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(edge_count, 0)
        self.assertEqual(node_count, 1)


class TestEmptyFileSourceRef(unittest.TestCase):
    """A zero-byte sourceRef target used to raise IndexError on line 1."""

    def test_check_source_refs_on_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = pathlib.Path(tmp)
            (repo_root / "empty.py").write_text("")
            warnings, checked, ok, weak = render.check_source_refs(
                [{"id": "a", "sourceRef": "empty.py:1"}], repo_root
            )
            self.assertTrue(any("0 lines" in w for w in warnings))

    def test_describe_ref_on_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = pathlib.Path(tmp)
            (repo_root / "empty.py").write_text("")
            result = render.describe_ref("empty.py:1", repo_root)
            self.assertIsNotNone(result)
            self.assertIn("0 lines", result)


class TestListIdIsAnErrorNotATypeError(unittest.TestCase):
    def test_list_id_reports_as_error(self):
        data = {
            "version": 2,
            "project": {"name": "x"},
            "graph": {
                "nodes": [{"id": [], "kind": "service"}],
                "edges": [],
            },
        }
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("expected a string" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
