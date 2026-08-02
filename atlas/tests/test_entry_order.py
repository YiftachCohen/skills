"""Entry points lane: the origin leads, and the reader's anchor holds still.

The lane's job is telling a reader where to start. It used to order by kind and
then alphabetically, so the first box was whichever entry happened to sort first
by id, and a `cron` always came after every `entry` however much of the system
it drove. Observed on a real map: `armis-cli` — the root command every other
entry hangs off — sat second, and the nightly self-scan sat last, bottom-right
of a wrapped column, which reads as least important.

It now orders by ROOT-NESS: nodes nothing calls come first, then by how much of
the map each one opens up. Root-ness is computed once over the whole graph with
every container collapsed, not per render over the drawn graph — being the
origin is a property of the system, and the anchor should not move because the
reader expanded something three columns away.

These tests are BEHAVIOURAL, unlike the structural ones in test_lanes.py. Lane
assignment runs inside render() against a live DOM, so it is driven here the
only way it can be: render a fixture, load it in headless Chrome, dump the DOM,
and read the positions the layout actually wrote. Skipped when no Chrome is
installed — the same dependency evals/legibility/screenshot.py already takes.

Run with: python3 -m unittest discover atlas/tests -v
"""

import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RENDER = _ROOT / "scripts" / "render.py"

# Same list screenshot.py uses.
_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
]


def _find_chrome():
    for c in _CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


_CHROME = _find_chrome()

# A card carries its identity in data attributes and its layout in inline
# styles, which is what makes the DOM readable as a layout assertion.
_CARD = re.compile(
    r'data-id="([^"]+)" data-kind="([^"]+)"[^>]*?'
    r'style="[^"]*left: (-?[\d.]+)px; top: (-?[\d.]+)px;"'
)


def _fixture():
    """A graph where every old ordering rule gives a different answer.

    `zebra-cli` is the origin and sorts LAST alphabetically; `alpha-cmd` sorts
    first and is called by it; `nightly` is a root cron, which the old kind-
    grouping parked below every entry no matter what.

    `svc-b` is a container whose four children chain, so anything computing
    reach over the DRAWN graph would see `nightly` overtake `zebra-cli` the
    moment that container is expanded. It does not, and that is the point.

    The "Feature" group spans one entry and two services — median lane 1 — so
    it also exercises the rule that a group may not drag an entry out of lane 0.
    """
    nodes = [
        {"id": "zebra-cli", "label": "zebra", "kind": "entry",
         "sub": "root command", "sourceRef": "main.go:1"},
        {"id": "alpha-cmd", "label": "alpha", "kind": "entry", "group": "Feature",
         "sub": "subcommand", "sourceRef": "main.go:2"},
        {"id": "beta-cmd", "label": "beta", "kind": "entry",
         "sub": "subcommand", "sourceRef": "main.go:3"},
        {"id": "nightly", "label": "Nightly", "kind": "cron",
         "sub": "schedule — 03:00 UTC", "sourceRef": "main.go:4"},
        {"id": "svc-a", "label": "A", "kind": "service", "group": "Feature",
         "sub": "does a", "sourceRef": "a.go:1"},
        {"id": "svc-b", "label": "B", "kind": "service", "group": "Feature",
         "sub": "does b", "sourceRef": "b.go:1"},
        {"id": "svc-c", "label": "C", "kind": "service",
         "sub": "does c", "sourceRef": "c.go:1"},
    ]
    for i in range(1, 5):
        nodes.append({"id": f"b{i}", "label": f"b{i}", "kind": "service",
                      "parent": "svc-b", "sub": f"stage {i}",
                      "sourceRef": f"b.go:{i * 10}"})
    edges = [
        {"from": "zebra-cli", "to": "alpha-cmd", "kind": "triggers"},
        {"from": "zebra-cli", "to": "beta-cmd", "kind": "triggers"},
        {"from": "alpha-cmd", "to": "svc-a", "kind": "calls"},
        {"from": "nightly", "to": "b1", "kind": "calls"},
        {"from": "b1", "to": "b2", "kind": "calls"},
        {"from": "b2", "to": "b3", "kind": "calls"},
        {"from": "b3", "to": "b4", "kind": "calls"},
        {"from": "b4", "to": "svc-c", "kind": "calls"},
        # A doc's claim cannot make the origin stop being the origin.
        {"from": "svc-c", "to": "zebra-cli", "kind": "calls",
         "ghost": True, "claimedBy": "README.md:1"},
    ]
    return {"version": 1,
            "project": {"name": "Fixture", "slug": "fx", "tagline": "ordering",
                        "date": "2026-08-02", "rules": 3},
            "graph": {"nodes": nodes, "edges": edges}}


def _lane_order(expand_all=False):
    """Render the fixture, load it, and read back the Entry points column.

    Returns ids top-to-bottom, sub-column by sub-column — i.e. reading order.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / "fx.json").write_text(json.dumps(_fixture()))
        html = tmp / "fx.html"
        proc = subprocess.run(
            ["python3", str(_RENDER), str(tmp / "fx.json"), "-o", str(html),
             "--no-source-check"],
            capture_output=True, text=True)
        if not html.exists():
            raise AssertionError(f"render.py wrote nothing: {proc.stdout}{proc.stderr}")
        if expand_all:
            # render() is synchronous at load, so the click lands after the
            # first layout and before the DOM is dumped.
            html.write_text(html.read_text().replace(
                "</body>",
                '<script>document.getElementById("expand-all").click();</script></body>'))
        dom = subprocess.run(
            [_CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=8000",
             "--dump-dom", html.resolve().as_uri()],
            capture_output=True, text=True, timeout=180).stdout

    cards = [(id_, kind, float(x), float(y)) for id_, kind, x, y in _CARD.findall(dom)]
    if not cards:
        raise AssertionError("no positioned node cards in the dumped DOM — "
                             "the viewer threw before laying out")
    # Lane 0 is the leftmost column; a lane may wrap into sub-columns, so take
    # everything left of the first gap wider than one column.
    xs = sorted({x for _, _, x, _ in cards})
    cut = xs[-1]
    for a, b in zip(xs, xs[1:]):
        if b - a > 226:          # NODE_W 196 + SUBCOL_GAP 30
            cut = a
            break
    return [id_ for id_, _, x, y in sorted(cards, key=lambda c: (c[2], c[3])) if x <= cut]


@unittest.skipUnless(_CHROME, "no Chrome/Chromium installed")
class TestEntryLaneOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collapsed = _lane_order()
        cls.expanded = _lane_order(expand_all=True)

    def test_the_lane_holds_exactly_the_entry_points(self):
        """Guards the guard: every assertion below is vacuous if the probe is
        reading the wrong column."""
        self.assertEqual(sorted(self.collapsed),
                         ["alpha-cmd", "beta-cmd", "nightly", "zebra-cli"])

    def test_the_origin_leads(self):
        """`zebra-cli` sorts last alphabetically and is what the old rule put
        third. Nothing calls it and it opens the most of the map, so it is
        where a reader should start."""
        self.assertEqual(self.collapsed[0], "zebra-cli")

    def test_roots_come_before_what_they_call(self):
        called = {"alpha-cmd", "beta-cmd"}
        first_called = min(self.collapsed.index(c) for c in called)
        for root in ("zebra-cli", "nightly"):
            self.assertLess(self.collapsed.index(root), first_called,
                            f"{root} has no inbound edge and must precede a dispatched command")

    def test_a_cron_is_not_parked_at_the_bottom(self):
        """The old primary key was kind, and LANES[0].kinds is ["entry","cron"],
        so every cron sorted after every entry however much it drove. A nightly
        job at the bottom of a wrapped column reads as least important."""
        self.assertEqual(self.collapsed.index("nightly"), 1)
        self.assertNotEqual(self.collapsed[-1], "nightly")

    def test_reach_orders_the_rest(self):
        """`alpha-cmd` reaches a service, `beta-cmd` reaches nothing — so the
        wider door comes first rather than the alphabetically earlier one."""
        self.assertLess(self.collapsed.index("alpha-cmd"),
                        self.collapsed.index("beta-cmd"))

    def test_a_ghost_does_not_unseat_the_origin(self):
        """The fixture's ghost claims `svc-c` calls `zebra-cli`. If ghosts
        counted, the origin would be demoted below `nightly` by a sentence in a
        README — exactly what tracing and blast radius already refuse to do."""
        self.assertLess(self.collapsed.index("zebra-cli"),
                        self.collapsed.index("nightly"))

    def test_a_group_cannot_pull_an_entry_out_of_the_lane(self):
        """test_lanes.py pins this structurally; this is the behaviour. The
        "Feature" group is one entry plus two services, so its median lane is 1
        and the entry would ride along."""
        self.assertIn("alpha-cmd", self.collapsed)

    def test_the_order_survives_expanding_every_container(self):
        """The load-bearing one. `svc-b` hides a four-stage chain, so reach
        measured over the DRAWN graph would put `nightly` at 5 against
        `zebra-cli`'s 3 and swap the top of the lane the moment a container
        three columns away opens. Root-ness is a property of the system, so it
        is computed once with everything collapsed — and the anchor holds."""
        self.assertEqual([n for n in self.expanded if n in self.collapsed],
                         self.collapsed)
        self.assertEqual(self.expanded[0], "zebra-cli")


class TestEntryOrderIsImplementedOnce(unittest.TestCase):
    """Structural backstop for the parts a fixture cannot show."""

    def setUp(self):
        self.js = (_ROOT / "templates" / "viewer.js").read_text()
        self.code = "\n".join(re.sub(r"//.*$", "", ln) for ln in self.js.splitlines())

    def test_rank_is_computed_outside_render(self):
        """If ENTRY_RANK moves inside render() it becomes view-dependent, which
        is the bug test_the_order_survives_expanding_every_container catches —
        but only where Chrome exists. Pin it here too."""
        self.assertIn("const ENTRY_RANK", self.code)
        self.assertLess(self.code.index("const ENTRY_RANK"),
                        self.code.index("function render("))

    def test_ghosts_are_excluded_from_the_computation(self):
        body = self.code[self.code.index("const ENTRY_RANK"):]
        body = body[:body.index("const UNRANKED")]
        self.assertIn("e.ghost", body)
        self.assertIn("topAncestor", body)

    def test_only_the_entry_lane_reorders(self):
        """Kind grouping is right everywhere else — stores before externals,
        crons together. Dropping it globally would scatter those."""
        self.assertIn("r === ENTRY_LANE", self.code)
        self.assertIn("repKindIdx(a) - repKindIdx(b)", self.code)


if __name__ == "__main__":
    unittest.main()
