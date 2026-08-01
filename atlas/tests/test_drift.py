"""Regression tests for plan 005: pin SKILL.md prose and render.py behavior
together so they cannot silently diverge again.

SKILL.md is not documentation — it is a prompt an agent reads and obeys on
every invocation. Tests 1-3 turn it into a CI-checked artifact: anyone
editing the contract example or the stats.py citations now gets a red test
instead of silent drift. Same by-path import shim as
atlas/tests/test_render.py. Run with: python3 -m unittest discover atlas/tests -v
"""

import importlib.util
import json
import pathlib
import re
import unittest

_RENDER = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "render.py"
_spec = importlib.util.spec_from_file_location("atlas_render", _RENDER)
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)

_ATLAS_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SKILL_MD = _ATLAS_ROOT / "SKILL.md"
_EXAMPLES = _ATLAS_ROOT / "examples"


def _atlas(nodes, edges=(), project=None):
    return {
        "version": 2,
        "project": project if project is not None else {"name": "T", "rules": 3},
        "graph": {"nodes": list(nodes), "edges": list(edges)},
    }


class TestSkillExampleIsContractCompliant(unittest.TestCase):
    """The first ```json block in SKILL.md is the output contract example."""

    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def test_example_has_detail_and_sourceref_on_every_internal_node(self):
        md = _SKILL_MD.read_text()
        match = re.search(r"```json\n(\{.*?\n\})\n```", md, re.S)
        self.assertIsNotNone(match, "no fenced json block found in SKILL.md")
        # Confirm this is the contract example, not some other fenced block:
        # it must actually be a graph with nodes and edges.
        data = json.loads(match.group(1))
        self.assertIn("graph", data)
        self.assertIn("nodes", data["graph"])

        internal = [n for n in data["graph"]["nodes"]
                    if n.get("kind") not in ("external", "model")]
        self.assertTrue(internal, "expected at least one internal node")
        missing_detail = [n["id"] for n in internal if not n.get("detail")]
        missing_ref = [n["id"] for n in internal if not n.get("sourceRef")]
        self.assertEqual(missing_detail, [])
        self.assertEqual(missing_ref, [])

        errors, warnings, *_ = render.validate(data)
        self.assertEqual(errors, [])


class TestDemoIsClean(unittest.TestCase):
    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def test_demo_json_has_no_errors_or_warnings(self):
        data = json.loads((_EXAMPLES / "demo.json").read_text())
        errors, warnings, *_ = render.validate(data)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


class TestStatsPathsAreAbsolute(unittest.TestCase):
    def test_every_stats_py_mention_is_prefixed_absolute(self):
        md = _SKILL_MD.read_text()
        for m in re.finditer(r".{0,40}stats\.py", md):
            snippet = m.group(0)
            self.assertIn(
                "/abs/path/to/skill/", snippet,
                f"stats.py mentioned without the absolute-path prefix: {snippet!r}",
            )


class TestCountedClaimsKeepsRoundNumbers(unittest.TestCase):
    def test_round_numbers_are_reported_identifiers_are_not(self):
        nodes = [
            {"id": "a", "detail": "1000 users"},
            {"id": "b", "detail": "5000 rows"},
            {"id": "c", "detail": "port 5050"},
            {"id": "d", "detail": "RFC 8628"},
        ]
        found = dict(render.counted_claims(nodes))
        self.assertEqual(found.get("a"), "1000 users")
        self.assertEqual(found.get("b"), "5000 rows")
        self.assertNotIn("c", found)
        self.assertNotIn("d", found)


class TestLabelRatioUsesDrawnEdges(unittest.TestCase):
    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def test_labels_inside_a_container_do_not_warn(self):
        # 20 top-level nodes, one container with children connected by heavily
        # labelled edges INTERNAL to the container — invisible at open, so
        # merging into the opening view should produce no drawn edges for them
        # and no label-ratio warning.
        nodes = [{"id": "container", "kind": "service"}]
        nodes += [
            {"id": f"child{i}", "kind": "service", "parent": "container"}
            for i in range(4)
        ]
        nodes += [{"id": f"top{i}", "kind": "service"} for i in range(19)]
        edges = [
            {"from": f"child{i}", "to": f"child{i+1}", "label": f"internal {i}"}
            for i in range(3)
        ]
        data = _atlas(nodes, edges=edges)
        errors, warnings, *_ = render.validate(data)
        self.assertFalse(any("carry a" in w and "label" in w for w in warnings))

    def test_labels_between_top_level_nodes_warn(self):
        # A hub with 12 labelled edges to 12 distinct top-level nodes: 12
        # drawn edges (at the floor), 100% labelled — must warn.
        nodes = [{"id": "hub", "kind": "service"}]
        nodes += [{"id": f"n{i}", "kind": "service"} for i in range(12)]
        edges = [{"from": "hub", "to": f"n{i}", "label": f"l{i}"} for i in range(12)]
        data = _atlas(nodes, edges=edges)
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(
            any("edges drawn in the opening view carry a label" in w for w in warnings)
        )


class TestLabelRatioHasAFloor(unittest.TestCase):
    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def test_three_edges_all_labelled_does_not_warn(self):
        nodes = [{"id": f"n{i}", "kind": "service"} for i in range(4)]
        edges = [
            {"from": "n0", "to": "n1", "label": "a"},
            {"from": "n1", "to": "n2", "label": "b"},
            {"from": "n2", "to": "n3", "label": "c"},
        ]
        data = _atlas(nodes, edges=edges)
        errors, warnings, *_ = render.validate(data)
        self.assertFalse(
            any("edges drawn in the opening view carry a label" in w for w in warnings)
        )


class TestNewerRulesetWarns(unittest.TestCase):
    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def test_rules_99_warns_newer(self):
        data = _atlas(
            [{"id": "a", "kind": "service"}],
            project={"name": "x", "rules": 99},
        )
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("NEWER" in w for w in warnings))


class TestNoDanglingGradeAtlas(unittest.TestCase):
    def test_grade_atlas_appears_nowhere(self):
        # Built by concatenation so this test file's own docstring/name don't
        # self-match the citation it's checking for.
        needle = "grade" + "_atlas"
        this_file = pathlib.Path(__file__).resolve()
        hits = []
        for path in _ATLAS_ROOT.rglob("*"):
            if path.resolve() == this_file:
                continue
            if path.is_file() and path.suffix in (".md", ".py", ".json", ".js", ".html", ".css"):
                try:
                    text = path.read_text(errors="replace")
                except OSError:
                    continue
                if needle in text:
                    hits.append(str(path))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
