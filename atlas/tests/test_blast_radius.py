"""Blast radius: right-click a node, watch everything downstream of it go dark.

The feature is pure viewer traversal — no contract change, nothing for the agent
to author — so there is no Python behaviour to assert. What there IS to protect
is the three-file contract it spans: viewer.js reaches for DOM ids at IIFE
scope, and a single missing one throws before `render()` ever runs, blanking the
whole map rather than just breaking this feature. That failure is silent in
every Python test we have, because render.py writes the HTML happily either way.

So the load-bearing test here is the general one: every id viewer.js looks up
must exist in viewer.html. Run with: python3 -m unittest discover atlas/tests -v
"""

import importlib.util
import pathlib
import re
import shutil
import subprocess
import unittest

_TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"
_RENDER = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "render.py"
_spec = importlib.util.spec_from_file_location("atlas_render", _RENDER)
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)

_JS = (_TEMPLATES / "viewer.js").read_text()
_HTML = (_TEMPLATES / "viewer.html").read_text()
_CSS = (_TEMPLATES / "viewer.css").read_text()


class TestDomContract(unittest.TestCase):
    """Every getElementById target in the viewer exists in the template."""

    def test_every_looked_up_id_exists(self):
        wanted = set(re.findall(r'getElementById\(\s*"([^"]+)"\s*\)', _JS))
        present = set(re.findall(r'\bid="([^"]+)"', _HTML))
        missing = sorted(wanted - present)
        self.assertEqual(
            missing, [],
            f"viewer.js looks up ids that viewer.html does not define: {missing} "
            "— this throws at IIFE scope and blanks the entire map",
        )

    def test_the_blast_controls_are_among_them(self):
        """Guards the guard: if the regex above ever stops matching, this fails
        too rather than passing vacuously on an empty set."""
        wanted = set(re.findall(r'getElementById\(\s*"([^"]+)"\s*\)', _JS))
        for dom_id in ("blastbar", "blast-msg", "blast-flip", "blast-exit", "d-blast"):
            with self.subTest(id=dom_id):
                self.assertIn(dom_id, wanted)
                self.assertIn(f'id="{dom_id}"', _HTML)


class TestBlastStyling(unittest.TestCase):
    """The classes the JS toggles must be styled, in every theme.

    `--danger` is the one token blast radius introduced. A theme that never
    defines it renders the dead node with an invalid border-color — i.e. no
    visible answer to the question the user just asked.
    """

    def test_classes_are_styled(self):
        for cls in (".node.blast-dead", ".node.blast-hit", "g.edge.blast-hit"):
            with self.subTest(cls=cls):
                self.assertIn(cls, _CSS)

    def test_every_theme_defines_danger(self):
        themes = re.findall(
            r':root\[data-theme="(\w+)"\]\s*\{(.*?)\n  \}', _CSS, re.S)
        self.assertEqual(
            {t for t, _ in themes}, set(render.THEMES),
            "themes in viewer.css drifted from render.py's THEMES",
        )
        for name, body in themes:
            with self.subTest(theme=name):
                self.assertIn("--danger:", body)

    def test_blastbar_is_hidden_on_paper(self):
        """Interactive chrome is noise in print, and the bar is fixed-position
        so it would otherwise land on top of the map."""
        print_block = _CSS.rsplit("@media print", 1)[-1]
        self.assertIn("#blastbar", print_block)


class TestGhostStyling(unittest.TestCase):
    def test_ghost_edges_are_dashed(self):
        self.assertIn("g.edge.ghost .edge-path", _CSS)
        self.assertIn("stroke-dasharray", _CSS)

    def test_traced_ghost_keeps_its_dashes(self):
        """A highlighted ghost is still a claim: if `hl` restored a solid stroke
        the map would assert, at exactly the moment a reader looks closest, that
        the code makes a connection it does not."""
        self.assertIn("g.edge.ghost.hl .edge-path", _CSS)


class TestViewerParses(unittest.TestCase):
    """A syntax error in viewer.js is invisible to every other test here —
    render.py inlines the file as text and reports success."""

    def test_js_is_syntactically_valid(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        proc = subprocess.run([node, "--check", str(_TEMPLATES / "viewer.js")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
