"""Stdlib unittest baseline for atlas/scripts/render.py.

render.py lives outside any package (atlas/scripts/ has no __init__.py), so it
is loaded by path rather than imported normally — see the module-scope shim
below. Every TestCase here is lifted from an inline comment in render.py that
names a specific regression; the comment is the specification these tests
pin down. Run with: python3 -m unittest discover atlas/tests -v
"""

import importlib.util
import pathlib
import subprocess
import sys
import unittest

_RENDER = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "render.py"
_spec = importlib.util.spec_from_file_location("atlas_render", _RENDER)
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)

_EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"


class TestShim(unittest.TestCase):
    """Proves the by-path import above actually loaded the real module."""

    def test_caps_constant(self):
        self.assertEqual(render.CAPS, {"nodes": 300, "edges": 500})


class TestWeakLine(unittest.TestCase):
    """describe_weak_line (render.py:425) — is this line a landmark or not."""

    def test_weak_lines(self):
        weak_cases = [
            ("", "blank"),
            ("   ", "blank whitespace-only"),
            ("// comment", "// line comment"),
            ("# comment", "# line comment"),
            ("* continuation", "block-comment continuation"),
            ("const (", "bare block-opener"),
            ("} catch (e) {", "catch clause"),
            ("} else {", "else clause"),
            ("try {", "try clause"),
            ("orderBy: {", "object-literal key opener"),
        ]
        for line, why in weak_cases:
            with self.subTest(line=line, why=why):
                self.assertIsNotNone(render.describe_weak_line(line))

    def test_real_landmarks_are_not_weak(self):
        strong_cases = [
            "def handle_request(req):",
            # CRON_RE carve-out (render.py:439): a schedule line is the only
            # evidence a cron edge ever has, so it must NOT read as a comment
            # even though it opens with digits the way `* continuation` does.
            "0 3 * * * /usr/bin/backup",
        ]
        for line in strong_cases:
            with self.subTest(line=line):
                self.assertIsNone(render.describe_weak_line(line))


class TestCodeOnly(unittest.TestCase):
    """code_only (render.py:590) — comments and docstrings must not count as evidence."""

    def test_drops_comments_and_docstrings_keeps_code_and_cron(self):
        text = (
            '"""docstring\n'
            "spanning lines\n"
            '"""\n'
            "/* block\n"
            "comment */\n"
            "// line comment\n"
            "real_statement()\n"
            "0 3 * * * /usr/bin/backup\n"
        )
        out = render.code_only(text)
        self.assertNotIn("docstring", out)
        self.assertNotIn("spanning lines", out)
        self.assertNotIn("block", out)
        self.assertNotIn("comment */", out)
        self.assertNotIn("line comment", out)
        self.assertIn("real_statement()", out)
        # A crontab line is the only evidence a cron edge has and must survive
        # code_only even though it opens with a digit/`*`-heavy pattern
        # (render.py:614-618).
        self.assertIn("0 3 * * * /usr/bin/backup", out)


class TestCountedClaims(unittest.TestCase):
    """counted_claims (render.py:960) — cardinal-plus-noun claims, minus identifiers."""

    def test_counted_and_excluded(self):
        nodes = [
            {"id": "a", "sub": "30 backends"},
            {"id": "b", "sub": "~140 tables"},
            {"id": "c", "sub": "137 tables"},
            {"id": "d", "sub": "1,519 files"},
            {"id": "e", "sub": "429 TooManyRequests"},
            {"id": "f", "sub": "RFC 8628"},
            # TODO(plan 005): "1000 users" is currently DROPPED (bare 4-digit
            # run with no separator reads as an identifier) — this is the
            # current, wrong-for-genuine-counts behavior; plan 005 changes it.
            {"id": "g", "sub": "1000 users"},
        ]
        found = dict(render.counted_claims(nodes))
        self.assertEqual(found.get("a"), "30 backends")
        self.assertEqual(found.get("b"), "~140 tables")
        self.assertEqual(found.get("c"), "137 tables")
        self.assertEqual(found.get("d"), "1,519 files")
        self.assertNotIn("e", found)
        self.assertNotIn("f", found)
        self.assertNotIn("g", found)


class TestNameHelpers(unittest.TestCase):
    """symbolish (render.py:673) and same_package (render.py:741)."""

    def test_symbolish(self):
        for token in ("streamText", "check_gate", "lib/storage", "depot.yaml"):
            with self.subTest(token=token):
                self.assertTrue(render.symbolish(token))
        for token in ("files", "timeout", "3.1k"):
            with self.subTest(token=token):
                self.assertFalse(render.symbolish(token))

    def test_same_package(self):
        a = {"sourceRef": "lib/foo.py:1"}
        b = {"sourceRef": "lib/bar.py:2"}
        self.assertTrue(render.same_package(a, b))
        # A container whose ref is a bare directory (no suffix) is excluded.
        container = {"sourceRef": "lib"}
        self.assertFalse(render.same_package(a, container))
        # Identical refs are excluded too.
        self.assertFalse(render.same_package(a, a))


class TestFill(unittest.TestCase):
    """fill (render.py:908) — single-pass substitution only."""

    def test_single_pass_does_not_rescan_substituted_content(self):
        template = "before /*__SCAN_CONFIG__*/ after"
        values = {
            "/*__SCAN_CONFIG__*/": "payload containing /*__SCAN_CONFIG__*/ literally",
        }
        out = render.fill(template, values)
        self.assertEqual(
            out, "before payload containing /*__SCAN_CONFIG__*/ literally after"
        )


def _atlas(nodes, edges=(), project=None):
    return {
        "version": 2,
        "project": project if project is not None else {"name": "T", "rules": 3},
        "graph": {"nodes": list(nodes), "edges": list(edges)},
    }


class TestValidate(unittest.TestCase):
    """Table-driven validate() (render.py:158) coverage.

    current_ruleset() reads SKILL.md's frontmatter `version:` off disk; pinned
    here so a future ruleset bump doesn't change what these tests assert.
    """

    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    # -- errors --------------------------------------------------------

    def test_duplicate_node_ids(self):
        data = _atlas([{"id": "a", "kind": "service"}, {"id": "a", "kind": "service"}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("duplicate node ids" in e for e in errors))

    def test_node_with_no_id(self):
        data = _atlas([{"kind": "service"}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("has no id" in e for e in errors))

    def test_missing_project_name(self):
        data = _atlas([{"id": "a", "kind": "service"}], project={"rules": 3})
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("project.name is required" in e for e in errors))

    def test_parent_not_a_node_id(self):
        data = _atlas([{"id": "a", "kind": "service", "parent": "missing"}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("is not a node id" in e for e in errors))

    def test_node_is_its_own_parent(self):
        data = _atlas([{"id": "a", "kind": "service", "parent": "a"}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("is its own parent" in e for e in errors))

    def test_depth_three_nesting(self):
        data = _atlas([
            {"id": "a", "kind": "service"},
            {"id": "b", "kind": "service", "parent": "a"},
            {"id": "c", "kind": "service", "parent": "b"},
        ])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("nested more than 2 levels deep" in e for e in errors))

    def test_edge_endpoint_not_a_node_id(self):
        data = _atlas(
            [{"id": "a", "kind": "service"}],
            edges=[{"from": "a", "to": "missing"}],
        )
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("is not a node id" in e for e in errors))

    def test_empty_graph_nodes(self):
        data = _atlas([])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("graph.nodes is empty" in e for e in errors))

    # -- warnings --------------------------------------------------------

    def test_tool_node_with_no_model_or_agent(self):
        data = _atlas([{"id": "a", "kind": "tool"}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("no `model` or `agent`" in w for w in warnings))

    def test_top_level_service_share_over_half(self):
        nodes = [{"id": f"svc{i}", "kind": "service"} for i in range(7)]
        nodes += [{"id": f"tool{i}", "kind": "tool"} for i in range(5)]
        data = _atlas(nodes)
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("TOP-LEVEL nodes are `service`" in w for w in warnings))

    def test_all_nodes_service_share_over_60_percent(self):
        # Isolate the ALL-NODES denominator (render.py:301) from the TOP-LEVEL
        # one above: most `service` nodes are nested under one container so
        # top_level stays under the 12-node threshold and only the all-nodes
        # check can fire.
        nodes = [{"id": "container", "kind": "service"}]
        nodes += [
            {"id": f"child{i}", "kind": "service", "parent": "container"}
            for i in range(25)
        ]
        nodes += [{"id": f"tool{i}", "kind": "tool"} for i in range(5)]
        data = _atlas(nodes)
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("of 31 nodes are `service`" in w for w in warnings))

    def test_over_length_sub_field(self):
        data = _atlas([{"id": "a", "kind": "service", "sub": "x" * 41}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("sub is 41 chars" in w for w in warnings))

    def test_over_length_group_field(self):
        data = _atlas([{"id": "a", "kind": "service", "group": "x" * 25}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("group is 25 chars" in w for w in warnings))

    def test_edge_points_at_own_container(self):
        data = _atlas(
            [
                {"id": "parent", "kind": "service"},
                {"id": "child", "kind": "service", "parent": "parent"},
            ],
            edges=[{"from": "child", "to": "parent"}],
        )
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("points at its own container" in w for w in warnings))

    def test_detail_coverage_below_80_percent(self):
        nodes = [{"id": f"n{i}", "kind": "service", "detail": "x"} for i in range(9)]
        nodes += [{"id": f"m{i}", "kind": "service"} for i in range(3)]
        data = _atlas(nodes)
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("carry a `detail`" in w for w in warnings))

    def test_floating_top_level_node(self):
        data = _atlas(
            [{"id": "a", "kind": "service"}, {"id": "b", "kind": "service"}],
            edges=[{"from": "a", "to": "a"}],
        )
        # a's self-edge keeps `edges` non-empty but neither node appears in
        # `visible` because fa == ta for a's own edge, and b has no edge at all.
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("has no edge in the opening view" in w for w in warnings))

    def test_label_ratio_over_cap(self):
        # The label ratio is measured over edges DRAWN IN THE OPENING VIEW (one
        # per distinct top-level pair), with a 12-edge floor — see plan 005.
        # 13 top-level nodes, 12 edges from a hub to each of the others, all
        # distinct top-level pairs and all labelled: 12 drawn, 100% labelled.
        nodes = [{"id": "hub", "kind": "service"}]
        nodes += [{"id": f"n{i}", "kind": "service"} for i in range(12)]
        edges = [{"from": "hub", "to": f"n{i}", "label": f"label {i}"} for i in range(12)]
        data = _atlas(nodes, edges=edges)
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(
            any("edges drawn in the opening view carry a label" in w for w in warnings)
        )

    def test_over_length_label_field(self):
        data = _atlas([{"id": "a", "kind": "service", "label": "x" * 29}])
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("label is 29 chars" in w for w in warnings))

    def test_over_length_edge_label(self):
        data = _atlas(
            [{"id": "a", "kind": "service"}, {"id": "b", "kind": "service"}],
            edges=[{"from": "a", "to": "b", "label": "x" * 25}],
        )
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("edges[0] label is 25 chars" in w for w in warnings))

    def test_project_rules_lower_than_current_ruleset(self):
        data = _atlas([{"id": "a", "kind": "service"}], project={"name": "T", "rules": 2})
        errors, warnings, *_ = render.validate(data)
        self.assertTrue(any("this skill is ruleset 3" in w for w in warnings))

    # -- negative case --------------------------------------------------------

    def test_well_formed_atlas_has_no_errors(self):
        nodes = [
            {
                "id": "a",
                "kind": "service",
                "label": "A",
                "detail": "does a thing",
            },
            {
                "id": "b",
                "kind": "service",
                "label": "B",
                "detail": "does another thing",
            },
            {
                "id": "c",
                "kind": "service",
                "label": "C",
                "detail": "does a third thing",
            },
        ]
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}]
        data = _atlas(nodes, edges=edges, project={"name": "T", "rules": 3})
        errors, warnings, *_ = render.validate(data)
        self.assertEqual(errors, [])


class TestCli(unittest.TestCase):
    """The exit-code contract of the real CLI, run as a subprocess.

    Pins CURRENT behavior only: `--check` alone always exits 0, even with
    warnings. `--strict` is what makes a warning-carrying map fail the check.
    """

    def _run(self, *args):
        fixture = _EXAMPLES / "bad-atlas.json"
        return subprocess.run(
            [sys.executable, str(_RENDER), str(fixture), *args],
            capture_output=True,
            text=True,
        )

    def test_check_alone_exits_zero_despite_warnings(self):
        result = self._run("--check")
        self.assertEqual(result.returncode, 0)

    def test_check_strict_exits_nonzero_on_warnings(self):
        result = self._run("--check", "--strict")
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
