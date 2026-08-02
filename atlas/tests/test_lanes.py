"""Semantic lanes: horizontal position is the map's one always-true statement.

A user group is laid out as one unit and takes its members' median lane. That is
usually right, but a feature group is typically one command plus the services it
drives — so the median landed on the services and dragged the command out of the
Entry points lane, putting the reader's starting point in among the things it
starts. Observed on a real map: 4 of 9 entries were displaced, and they were
exactly the 4 carrying a `group`.

The rule is now: a group never moves an `entry` or `cron` out of lane 0. Such a
node detaches from the unit and keeps its natural lane, while KEEPING its
`group` field — which is why the fix lives in the renderer rather than asking
authors to strip `group`, since that field also feeds search and the agent
prompt.

These assertions are structural. Lane assignment happens inside render() against
a live DOM, so it cannot be exercised from Python; the behavioural verification
is in-browser (see the PR). What is pinned here is that the invariant is still
implemented and still wired into every consumer.

Run with: python3 -m unittest discover atlas/tests -v
"""

import pathlib
import re
import unittest

_TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "templates"
_JS = (_TEMPLATES / "viewer.js").read_text()
_SKILL = (pathlib.Path(__file__).resolve().parent.parent / "SKILL.md").read_text()


def _strip_comments(src):
    """Line comments removed, so prose about a rule can't satisfy a test for it."""
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in src.splitlines())


class TestEntryLaneInvariant(unittest.TestCase):
    def setUp(self):
        self.code = _strip_comments(_JS)

    def test_layout_group_consults_the_detached_set(self):
        """Every consumer (bucketing, sub-columns, padding, group boxes) reads
        layoutGroup, so consulting the set there is what makes the detachment
        consistent — a detached node must not reappear inside its group's box."""
        body = self.code[self.code.index("function layoutGroup"):]
        body = body[:body.index("\n  }") + 4]
        self.assertIn("detachedFromGroup.has", body)
        # and it must come before the user-group return, or it never applies
        self.assertLess(body.index("detachedFromGroup.has"), body.index('"__g:"'))

    def test_container_membership_still_wins_over_detachment(self):
        """A child of an expanded container is laid out with its parent stack.
        That is structural, not a user grouping, so it must be decided before
        the detachment check — otherwise expanding a container containing an
        entry would scatter the stack."""
        body = self.code[self.code.index("function layoutGroup"):]
        body = body[:body.index("\n  }") + 4]
        self.assertLess(body.index('"__c:"'), body.index("detachedFromGroup.has"))

    def test_detachment_is_limited_to_the_entry_lane(self):
        """Detaching every off-median member would dissolve grouping entirely.
        Only lane 0 is protected."""
        self.assertIn("ENTRY_LANE = 0", self.code)
        lane_pass = self.code[self.code.index("a unit stays in one lane")
                              if "a unit stays in one lane" in self.code
                              else self.code.index("ENTRY_LANE = 0"):]
        lane_pass = lane_pass[:lane_pass.index("const layers")]
        self.assertIn("lane !== ENTRY_LANE", lane_pass)
        self.assertIn("laneOf(m) === ENTRY_LANE", lane_pass)

    def test_the_set_is_cleared_before_units_are_built(self):
        """Stale membership from the previous render would detach nodes whose
        group no longer moves them — and render() runs on every expand."""
        self.assertIn("detachedFromGroup.clear()", self.code)
        clear_at = self.code.index("detachedFromGroup.clear()")
        units_at = self.code.index("const units = new Map()")
        self.assertLess(clear_at, units_at)

    def test_group_field_is_not_discarded(self):
        """The whole argument for fixing this in the renderer rather than in the
        map is that `group` keeps working elsewhere. If these two consumers ever
        stop reading it, stripping the field would have been the simpler fix."""
        self.assertIn("n.group", self.code)              # search haystack
        self.assertIn("group: ${safeField(n.group)}", _JS)  # agent prompt

    def test_skill_documents_the_exception(self):
        """SKILL.md's `group` row previously described the median rule with no
        carve-out; a reader following it would still expect the old behaviour."""
        self.assertIn("never moves an `entry` or `cron` out of the Entry points lane",
                      _SKILL)


if __name__ == "__main__":
    unittest.main()
