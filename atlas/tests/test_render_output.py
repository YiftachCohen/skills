"""Regression tests for the two silently-broken-map defects fixed in plan 002.

1. A `<!-- <script` sequence anywhere in the atlas JSON used to swallow the
   entire viewer once inlined into the template's <script> element.
2. A colon in a node id used to make the viewer's port-key lookup throw,
   dropping every edge on the node while the card still drew.

Same by-path import shim as atlas/tests/test_render.py (render.py lives
outside any package). Run with: python3 -m unittest discover atlas/tests -v
"""

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

_RENDER = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "render.py"
_spec = importlib.util.spec_from_file_location("atlas_render", _RENDER)
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)

_EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"

_POISON_ATLAS = {
    "version": 2,
    "project": {"name": "T", "rules": 3},
    "graph": {
        "nodes": [
            {
                "id": "a",
                "label": "A",
                "kind": "entry",
                "detail": "<!-- <script>alert(1)</script>",
            },
            {"id": "b", "label": "B", "kind": "store"},
        ],
        "edges": [{"from": "a", "to": "b", "kind": "writes"}],
    },
}


class TestPayloadEscaping(unittest.TestCase):
    """html_safe_json (render.py) — the JSON-level markup encoding."""

    def test_payload_escapes_markup(self):
        out = render.html_safe_json(_POISON_ATLAS)
        for raw in ("<", ">", "&"):
            self.assertNotIn(raw, out)
        # The round-trip is the load-bearing assertion: the escaping must be
        # lossless, or the viewer would parse a corrupted graph.
        self.assertEqual(json.loads(out), _POISON_ATLAS)


class TestRenderedOutput(unittest.TestCase):
    """Rendering the poison fixture must not change the <script> element count."""

    def test_rendered_html_has_no_injected_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            poison_json = tmp_path / "poison.json"
            poison_html = tmp_path / "poison.html"
            poison_json.write_text(json.dumps(_POISON_ATLAS))

            result = subprocess.run(
                [sys.executable, str(_RENDER), str(poison_json),
                 "-o", str(poison_html)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0)
            poison_text = poison_html.read_text()

            demo_html = tmp_path / "demo.html"
            control = subprocess.run(
                [sys.executable, str(_RENDER), str(_EXAMPLES / "demo.json"),
                 "-o", str(demo_html)],
                capture_output=True, text=True,
            )
            self.assertEqual(control.returncode, 0)
            control_text = demo_html.read_text()

        self.assertNotIn("<!-- <script>", poison_text)
        self.assertEqual(poison_text.count("<script"), control_text.count("<script"))


class TestNodeIdCharset(unittest.TestCase):
    """validate() (render.py:158) — the NODE_ID_RE charset check."""

    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def _atlas(self, node_id):
        return {
            "version": 2,
            "project": {"name": "T", "rules": 3},
            "graph": {
                "nodes": [
                    {"id": node_id, "label": "B", "kind": "service"},
                    {"id": "pg", "label": "P", "kind": "store"},
                ],
                "edges": [{"from": node_id, "to": "pg", "kind": "writes"}],
            },
        }

    def test_colon_id_is_an_error(self):
        errors, warnings, *_ = render.validate(self._atlas("svc:billing"))
        self.assertTrue(any("svc:billing" in e for e in errors))

    def test_ordinary_ids_pass(self):
        for node_id in ("a", "billing-plans", "api.v2", "snake_case_id"):
            with self.subTest(node_id=node_id):
                errors, warnings, *_ = render.validate(self._atlas(node_id))
                self.assertFalse(
                    any("has an id outside" in e for e in errors),
                    f"ordinary id {node_id!r} incorrectly rejected: {errors}",
                )


class TestExamplesStillValidate(unittest.TestCase):
    """The bundled example fixtures must not regress under the new id check."""

    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def test_examples_still_validate(self):
        for name in ("demo.json", "demo-v1.json", "bad-atlas.json"):
            with self.subTest(name=name):
                data = json.loads((_EXAMPLES / name).read_text())
                errors, warnings, *_ = render.validate(data)
                self.assertEqual(errors, [], f"{name}: {errors}")


if __name__ == "__main__":
    unittest.main()
