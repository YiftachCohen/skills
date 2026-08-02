"""Authored tours: narrated stories over the graph, and the checks that keep
them honest.

A tour is the one field where the map speaks in sentences, which makes it the
one field that can be fluent and wrong — the same failure `detail` has, with a
camera and a soundtrack. The graph is what keeps it honest: every stop is a node
id, and consecutive stops must be joined by a real edge. The teleport check is
therefore the load-bearing test here, and it is deliberately ambiguous in its
reporting: a hop with no edge means either the story invented it or the MAP is
missing the edge, and both are worth a look.

(That check earned its keep immediately: the first draft of demo.json's own
support tour narrated the reply as drafted by GPT-5.5, when `support` calls
Claude. The teleport warning caught it.)

Same by-path import shim as atlas/tests/test_render.py. Run with:
python3 -m unittest discover atlas/tests -v
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

_EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples"
_TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"

# a -> b -> c, plus a -> d as a genuine fork off the first stop
_NODES = [
    {"id": "a", "label": "A", "kind": "entry"},
    {"id": "b", "label": "B", "kind": "service"},
    {"id": "c", "label": "C", "kind": "store"},
    {"id": "d", "label": "D", "kind": "external"},
    {"id": "lonely", "label": "L", "kind": "service"},
]
_EDGES = [
    {"from": "a", "to": "b", "kind": "calls"},
    {"from": "b", "to": "c", "kind": "writes"},
    {"from": "a", "to": "d", "kind": "calls"},
]


def _run(tours, nodes=None, edges=None):
    """validate_tours in isolation; returns (errors, warnings) as joined text."""
    nodes = _NODES if nodes is None else nodes
    edges = _EDGES if edges is None else edges
    errors, warnings = [], []
    render.validate_tours(
        {"tours": tours}, {n["id"] for n in nodes}, nodes, edges, errors, warnings
    )
    return " ".join(errors), " ".join(warnings)


def _tour(*steps, title="T"):
    return [{"title": title,
             "steps": [{"node": n, "text": "a sentence."} for n in steps]}]


class TestTeleports(unittest.TestCase):
    """The check that makes a tour more than prose in a JSON file."""

    def test_following_edges_is_quiet(self):
        errors, warnings = _run(_tour("a", "b", "c"))
        self.assertEqual(errors, "")
        self.assertNotIn("jumps to", warnings)

    def test_a_hop_with_no_edge_is_reported(self):
        _errors, warnings = _run(_tour("a", "c"))
        self.assertIn("steps[1] jumps to 'c'", warnings)

    def test_edges_count_in_either_direction(self):
        """A story may walk against the arrow — 'the reply comes back from' is a
        legitimate stop, and the edge is still what joins the two nodes."""
        _errors, warnings = _run(_tour("b", "a"))
        self.assertNotIn("jumps to", warnings)

    def test_a_fork_off_an_earlier_stop_is_allowed(self):
        """'Here it splits' is a story move, not an error: d hangs off a, which
        is two stops back."""
        _errors, warnings = _run(_tour("a", "b", "d"))
        self.assertNotIn("jumps to", warnings)

    def test_a_node_connected_to_nothing_is_still_a_teleport(self):
        _errors, warnings = _run(_tour("a", "lonely"))
        self.assertIn("jumps to 'lonely'", warnings)

    def test_revisiting_an_earlier_stop_is_not_a_teleport(self):
        """Coming back to a hub you already narrated is normal."""
        _errors, warnings = _run(_tour("a", "b", "a"))
        self.assertNotIn("jumps to", warnings)

    def test_a_ghost_cannot_carry_a_hop(self):
        """A tour that walks a doc-claimed edge is narrating something the code
        does not do — the most confidently wrong thing a map could say."""
        ghost_edges = [{"from": "a", "to": "c", "kind": "writes",
                        "ghost": True, "claimedBy": "README.md:1"}]
        _errors, warnings = _run(_tour("a", "c"), edges=ghost_edges)
        self.assertIn("jumps to 'c'", warnings)

    def test_a_container_stop_covers_its_children(self):
        """A stop on a container is connected if any of its children are: the
        edge lives on the child, but the story is pointing at the subsystem."""
        nodes = _NODES + [{"id": "kid", "label": "K", "kind": "service", "parent": "b"}]
        edges = [{"from": "a", "to": "kid", "kind": "calls"}]
        _errors, warnings = _run(_tour("a", "b"), nodes=nodes, edges=edges)
        self.assertNotIn("jumps to", warnings)


class TestTourShape(unittest.TestCase):
    def test_unknown_node_is_an_error(self):
        errors, _warnings = _run(_tour("a", "nope"))
        self.assertIn("node 'nope' is not a node id", errors)

    def test_missing_title_is_an_error(self):
        errors, _warnings = _run([{"steps": [{"node": "a", "text": "x"}]}])
        self.assertIn("has no title", errors)

    def test_no_steps_is_an_error(self):
        for steps in ({}, {"steps": []}, {"steps": "nope"}):
            with self.subTest(steps=steps):
                errors, _warnings = _run([{"title": "T", **steps}])
                self.assertIn("has no steps", errors)

    def test_a_stop_with_no_text_warns(self):
        _errors, warnings = _run([{"title": "T", "steps": [{"node": "a"}]}])
        self.assertIn("has no text", warnings)
        self.assertIn("auto tour wearing a title", warnings)

    def test_overlong_text_warns(self):
        long = "x" * (render.TOUR_TEXT_LIMIT + 1)
        _errors, warnings = _run([{"title": "T", "steps": [{"node": "a", "text": long}]}])
        self.assertIn(f"(cap {render.TOUR_TEXT_LIMIT})", warnings)

    def test_too_many_steps_warns(self):
        steps = [{"node": "a", "text": "x"}] * (render.TOUR_STEPS_CAP + 1)
        _errors, warnings = _run([{"title": "T", "steps": steps}])
        self.assertIn("is a lecture", warnings)

    def test_too_many_tours_warns(self):
        _errors, warnings = _run(_tour("a") * (render.TOURS_CAP + 1))
        self.assertIn(f"(cap {render.TOURS_CAP})", warnings)

    def test_absent_tours_is_silent(self):
        """Tours are optional. A map without them is complete, not deficient."""
        errors, warnings = [], []
        render.validate_tours({}, {"a"}, _NODES, _EDGES, errors, warnings)
        self.assertEqual((errors, warnings), ([], []))

    def test_malformed_tours_degrade_rather_than_raise(self):
        """--check exists to diagnose a broken map, so it must report the
        breakage rather than raise out of it."""
        for bad in ("nope", 7, {"a": 1}):
            with self.subTest(tours=bad):
                errors, warnings = [], []
                render.validate_tours(
                    {"tours": bad}, {"a"}, _NODES, _EDGES, errors, warnings)
                self.assertTrue(errors or warnings)

    def test_a_non_object_tour_is_reported_not_raised(self):
        errors, _warnings = _run(["just a string"])
        self.assertIn("expected an object", errors)


class TestDemoTours(unittest.TestCase):
    """demo.json's tours are the worked example, so they must stay clean."""

    def setUp(self):
        self._orig = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig

    def test_demo_tours_are_clean(self):
        data = json.loads((_EXAMPLES / "demo.json").read_text())
        self.assertTrue(data.get("tours"), "demo.json should demonstrate tours")
        _errors, warnings, *_ = render.validate(data)
        tour_warnings = [w for w in warnings if w.startswith("tour ")]
        self.assertEqual(tour_warnings, [])

    def test_demo_tours_stay_stories_not_coverage(self):
        """4-8 stops is the guidance; a demo that drifts into a lecture stops
        demonstrating the thing SKILL.md asks for."""
        data = json.loads((_EXAMPLES / "demo.json").read_text())
        for t in data["tours"]:
            with self.subTest(tour=t["title"]):
                self.assertGreaterEqual(len(t["steps"]), 4)
                self.assertLessEqual(len(t["steps"]), 8)


class TestBadAtlasFixture(unittest.TestCase):
    """bad-atlas.json is the everything-wrong fixture; it should exercise the
    tour checks too, or a regression in them shows up nowhere."""

    def setUp(self):
        self._orig = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig

    def test_bad_atlas_trips_tour_warnings(self):
        data = json.loads((_EXAMPLES / "bad-atlas.json").read_text())
        _errors, warnings, *_ = render.validate(data)
        joined = " ".join(warnings)
        self.assertIn("title is 78 chars", joined)
        self.assertIn("has no text", joined)


class TestViewerContract(unittest.TestCase):
    """The story chrome spans three files; a missing id throws at IIFE scope."""

    def test_story_ids_exist_in_the_template(self):
        js = (_TEMPLATES / "viewer.js").read_text()
        html = (_TEMPLATES / "viewer.html").read_text()
        wanted = set(re.findall(r'getElementById\(\s*"([^"]+)"\s*\)', js))
        for dom_id in ("storycard", "story-title", "story-count", "story-text",
                       "story-prev", "story-next", "story-stop", "tourmenu"):
            with self.subTest(id=dom_id):
                self.assertIn(dom_id, wanted)
                self.assertIn(f'id="{dom_id}"', html)

    def test_tour_titles_are_not_interpolated_as_html(self):
        """A tour title is LLM-authored text from an unvetted codebase, and the
        menu is the one place it lands in the DOM."""
        js = (_TEMPLATES / "viewer.js").read_text()
        menu_block = js[js.index("function menuEntry"):js.index("playBtn.addEventListener")]
        # Strip line comments first — the block explains in prose that it avoids
        # innerHTML, and matching that sentence would pass the test vacuously.
        code = "\n".join(re.sub(r"//.*$", "", ln) for ln in menu_block.splitlines())
        self.assertNotIn("innerHTML", code)
        self.assertIn("textContent", code)

    def test_story_chrome_is_hidden_on_paper(self):
        css = (_TEMPLATES / "viewer.css").read_text()
        print_block = css.rsplit("@media print", 1)[-1]
        self.assertIn("#storycard", print_block)
        self.assertIn("#tourmenu", print_block)


if __name__ == "__main__":
    unittest.main()
