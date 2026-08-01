"""Regression tests for plan 003's check_inventory tightening.

A disposition has to dispose: a bare `` - `id` `` (any backticked token that
happens to be a node id, with no disposition keyword) must NOT count as
reconciled any more. The three SKILL.md:263-267-blessed forms must still
reconcile — a tightening that breaks the documented contract is worse than
the bug it fixes.

Same by-path import shim as atlas/tests/test_render.py. Run with:
python3 -m unittest discover atlas/tests -v
"""

import importlib.util
import pathlib
import tempfile
import unittest

_RENDER = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "render.py"
_spec = importlib.util.spec_from_file_location("atlas_render", _RENDER)
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)


def _node(node_id):
    return {"id": node_id, "label": node_id, "kind": "service", "detail": "d"}


class TestSevenLineTable(unittest.TestCase):
    """The exact table from "Why this matters" — the verdicts must flip."""

    def test_two_mapped_one_omitted_four_unreconciled(self):
        inventory_text = (
            "- `billing` — mapped\n"
            "- `billing` — node (route trees)\n"
            "- `billing`\n"
            "- `svc` is a thing we did not dispose of at all\n"
            "- `scan repo [path]` — child `billing`\n"
            "- `ARMIS_LOCAL_S3_ENDPOINT` relaxes the SSRF check — detail on `svc`\n"
            "- `completion`, `help` — omitted: cobra boilerplate, no architectural consequence\n"
        )
        nodes = [_node("billing"), _node("svc")]
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = pathlib.Path(tmp) / "inventory.md"
            inv_path.write_text(inventory_text)
            warnings, note = render.check_inventory(inv_path, nodes)
        self.assertEqual(
            note, "inventory: 7 items — 2 mapped, 1 omitted, 4 unreconciled"
        )


class TestBlessedForms(unittest.TestCase):
    """The three documented dispositions at SKILL.md:263-267, each in isolation.

    This is the load-bearing test: it pins that tightening the parser did not
    break the contract SKILL.md itself describes.
    """

    def _reconcile(self, line, nodes):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = pathlib.Path(tmp) / "inventory.md"
            inv_path.write_text(line + "\n")
            return render.check_inventory(inv_path, nodes)

    def test_child_keyword_form_reconciles(self):
        warnings, note = self._reconcile(
            "- `scan repo [path]` — child `cmd-scan-repo`",
            [_node("cmd-scan-repo")],
        )
        self.assertIn("1 items — 1 mapped, 0 omitted, 0 unreconciled", note)

    def test_detail_on_keyword_form_reconciles(self):
        warnings, note = self._reconcile(
            "- `ARMIS_LOCAL_S3_ENDPOINT` relaxes the SSRF check — detail on `api-ssrf`",
            [_node("api-ssrf")],
        )
        self.assertIn("1 items — 1 mapped, 0 omitted, 0 unreconciled", note)

    def test_omitted_form_reconciles(self):
        warnings, note = self._reconcile(
            "- `completion`, `help` — omitted: cobra boilerplate, no architectural consequence",
            [],
        )
        self.assertIn("1 items — 0 mapped, 1 omitted, 0 unreconciled", note)


class TestStaleDisposition(unittest.TestCase):
    def test_disposition_naming_a_missing_id_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = pathlib.Path(tmp) / "inventory.md"
            inv_path.write_text("- `x` — child `gone`\n")
            warnings, note = render.check_inventory(inv_path, [_node("x")])
        self.assertTrue(any("does not contain" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
