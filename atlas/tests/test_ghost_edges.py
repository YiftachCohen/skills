"""Ghost edges: the arrows the docs claim and the code never implements.

A ghost's entire value is its provenance, so the rules that keep one honest are
the ones worth pinning: `claimedBy` is required and is resolved inside the repo
like every other path in the contract, `evidence` on a ghost is a
self-contradiction, and a ghost is excluded everywhere the map speaks about
what the code actually does (--edges, the labelled-edge worklist, the
opening-view connectivity check).

Same by-path import shim as atlas/tests/test_render.py (render.py lives outside
any package). Run with: python3 -m unittest discover atlas/tests -v
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


def _atlas(nodes, edges=(), project=None):
    return {
        "version": 2,
        "project": project if project is not None else {"name": "T", "rules": 3},
        "graph": {"nodes": list(nodes), "edges": list(edges)},
    }


_TWO_NODES = [
    {"id": "a", "label": "A", "kind": "entry"},
    {"id": "b", "label": "B", "kind": "store"},
]


class TestGhostValidation(unittest.TestCase):
    """validate() — the two rules that keep a ghost from being a dashed rumor."""

    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def _warnings(self, edges):
        _errors, warnings, *_ = render.validate(_atlas(_TWO_NODES, edges))
        return " ".join(warnings)

    def test_ghost_without_claimedby_warns(self):
        joined = self._warnings([{"from": "a", "to": "b", "ghost": True}])
        self.assertIn("is a ghost with no `claimedBy`", joined)

    def test_ghost_with_empty_claimedby_warns(self):
        joined = self._warnings(
            [{"from": "a", "to": "b", "ghost": True, "claimedBy": ""}]
        )
        self.assertIn("is a ghost with no `claimedBy`", joined)

    def test_ghost_carrying_evidence_is_a_contradiction(self):
        joined = self._warnings([{
            "from": "a", "to": "b", "ghost": True,
            "claimedBy": "README.md:3", "evidence": "src/a.ts:12",
        }])
        self.assertIn("is a ghost yet carries `evidence`", joined)

    def test_well_formed_ghost_is_quiet(self):
        joined = self._warnings(
            [{"from": "a", "to": "b", "ghost": True, "claimedBy": "README.md:3"}]
        )
        self.assertNotIn("ghost", joined)

    def test_a_plain_edge_is_never_treated_as_a_ghost(self):
        joined = self._warnings([{"from": "a", "to": "b", "kind": "writes"}])
        self.assertNotIn("ghost", joined)


class TestGhostConnectivity(unittest.TestCase):
    """A node held onto the map by nothing but a doc's claim is still an orphan.

    The floating-box check exists to catch a top-level node with no relationship
    in the opening view. A ghost draws an arrow but asserts the code does NOT
    make the connection, so counting it would let a doc-claimed edge silence
    exactly the finding the check is for.
    """

    def setUp(self):
        self._orig_current_ruleset = render.current_ruleset
        render.current_ruleset = lambda: 3

    def tearDown(self):
        render.current_ruleset = self._orig_current_ruleset

    def test_ghost_only_node_still_reads_as_floating(self):
        _errors, warnings, *_ = render.validate(_atlas(
            _TWO_NODES,
            [{"from": "a", "to": "b", "ghost": True, "claimedBy": "README.md:3"}],
        ))
        joined = " ".join(warnings)
        self.assertIn("has no edge in the opening view", joined)

    def test_a_real_edge_clears_it(self):
        _errors, warnings, *_ = render.validate(_atlas(
            _TWO_NODES, [{"from": "a", "to": "b", "kind": "writes"}]
        ))
        self.assertNotIn("has no edge in the opening view", " ".join(warnings))


class TestGhostSkipsEdgeCheck(unittest.TestCase):
    """--edges must not hunt for a ghost's performing line.

    A ghost declares itself unimplemented, so the heuristic would flag every
    single one — and each flag would be the point missed.
    """

    def test_ghost_is_not_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp).resolve()
            (repo / "a.py").write_text("def handle():\n    return 1\n")
            nodes = [
                {"id": "a", "label": "A", "kind": "service", "sourceRef": "a.py:1"},
                {"id": "b", "label": "B", "kind": "store", "sub": "postgres"},
            ]
            ghost = [{"from": "a", "to": "b", "kind": "writes",
                      "ghost": True, "claimedBy": "README.md:3"}]
            real = [{"from": "a", "to": "b", "kind": "writes"}]

            _w, checked_ghost, flagged_ghost, _a, _p = render.check_edges(
                nodes, ghost, repo)
            _w, checked_real, flagged_real, _a, _p = render.check_edges(
                nodes, real, repo)

        self.assertEqual(checked_ghost, 0, "a ghost must not be checked at all")
        self.assertEqual(flagged_ghost, 0)
        # The same edge without `ghost` IS checked — proving the skip above is
        # the ghost flag doing the work, not the fixture being unreachable.
        self.assertEqual(checked_real, 1)
        self.assertEqual(flagged_real, 1)


def _run_check(atlas_obj, repo_root, extra=()):
    """Run render.py --check over a temp atlas; return (returncode, stdout+stderr)."""
    atlas_dir = repo_root / ".atlas"
    atlas_dir.mkdir(exist_ok=True)
    atlas_path = atlas_dir / "atlas.json"
    atlas_path.write_text(json.dumps(atlas_obj))
    proc = subprocess.run(
        [sys.executable, str(_RENDER), str(atlas_path), "--check", *extra],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


class TestClaimedByIsVerified(unittest.TestCase):
    """`claimedBy` is a citation, and a citation of a doc that does not exist
    is a ghost of a ghost. Path only — docs get renamed and the claim usually
    survives the move, so the line is not insisted on."""

    def test_missing_doc_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp).resolve()
            _rc, out = _run_check(_atlas(_TWO_NODES, [
                {"from": "a", "to": "b", "ghost": True, "claimedBy": "NOPE.md:3"},
            ]), repo)
        self.assertIn("claimedBy 'NOPE.md:3' does not exist", out)

    def test_present_doc_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp).resolve()
            (repo / "README.md").write_text("# docs\nthe agent writes to pg\n")
            _rc, out = _run_check(_atlas(_TWO_NODES, [
                {"from": "a", "to": "b", "ghost": True, "claimedBy": "README.md:2"},
            ]), repo)
        self.assertNotIn("does not exist", out)

    def test_claimedby_is_confined_to_the_repo(self):
        """An atlas.json is a file people send each other, so `claimedBy` gets
        the same confinement as `sourceRef`: an absolute path or a `..` must be
        reported as missing rather than probed on the invoking user's disk."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp).resolve()
            for ref in ("/etc/hosts:1", "../../../../etc/hosts:1"):
                with self.subTest(ref=ref):
                    _rc, out = _run_check(_atlas(_TWO_NODES, [
                        {"from": "a", "to": "b", "ghost": True, "claimedBy": ref},
                    ]), repo)
                    self.assertIn("does not exist", out)


class TestGhostsInTheCheckSummary(unittest.TestCase):
    def test_ghost_count_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp).resolve()
            (repo / "README.md").write_text("# docs\n")
            _rc, out = _run_check(_atlas(_TWO_NODES, [
                {"from": "a", "to": "b", "kind": "writes"},
                {"from": "b", "to": "a", "ghost": True, "claimedBy": "README.md:1"},
            ]), repo)
        self.assertIn("2 edges (1 doc-claimed)", out)

    def test_no_ghosts_leaves_the_summary_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp).resolve()
            _rc, out = _run_check(
                _atlas(_TWO_NODES, [{"from": "a", "to": "b", "kind": "writes"}]),
                repo)
        self.assertIn("1 edges", out)
        self.assertNotIn("doc-claimed", out)

    def test_ghost_is_not_listed_as_an_edge_to_verify(self):
        """The labelled-edge worklist says "verify this at a call site". A ghost
        has no call site by definition, so listing one sends the reader hunting
        for code the map already says does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp).resolve()
            (repo / "README.md").write_text("# docs\n")
            _rc, out = _run_check(_atlas(_TWO_NODES, [
                {"from": "a", "to": "b", "kind": "writes", "label": "real claim"},
                {"from": "b", "to": "a", "ghost": True, "claimedBy": "README.md:1",
                 "label": "ghost claim"},
            ]), repo)
        self.assertIn("real claim", out)
        self.assertNotIn("ghost claim", out)


class TestBundledExamples(unittest.TestCase):
    """The shipped fixtures are the feature's worked examples, so they have to
    keep demonstrating it: demo.json carries a well-formed ghost, bad-atlas.json
    carries one that breaks both rules at once."""

    def test_demo_has_a_well_formed_ghost(self):
        data = json.loads((_EXAMPLES / "demo.json").read_text())
        ghosts = [e for e in data["graph"]["edges"] if e.get("ghost")]
        self.assertTrue(ghosts, "demo.json should demonstrate a ghost edge")
        for g in ghosts:
            self.assertTrue(g.get("claimedBy"))
            self.assertNotIn("evidence", g)

    def test_bad_atlas_ghost_trips_both_rules(self):
        _errors, warnings, *_ = render.validate(
            json.loads((_EXAMPLES / "bad-atlas.json").read_text()))
        joined = " ".join(warnings)
        self.assertIn("is a ghost with no `claimedBy`", joined)
        self.assertIn("is a ghost yet carries `evidence`", joined)


if __name__ == "__main__":
    unittest.main()
