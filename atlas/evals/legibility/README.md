# Legibility harness

Everything else in the eval stack grades whether an atlas is *true*. This
directory grades whether it is *understood* — the difference that shows up on
large monorepos, where a map can pass every content check and still open as a
hairball.

Three instruments, cheapest first:

1. **`stats.py <atlas.json>`** — static metrics of the opening view (edges
   re-routed to top-level ancestors and merged, exactly as the viewer draws
   them): busiest hub, drawn-edge density, always-on label ratio, group lane
   spread, oversized containers, isolated nodes. Warnings name the element to
   go look at. `--json` for machine consumption.

2. **`screenshot.py <atlas.json>`** — headless-Chrome captures of what a
   reader actually sees: the fitted overview and the everything-expanded worst
   case, both themes, 2x scale. Feed the PNGs to a vision grader with the
   rubric in `comprehension.md`.

3. **`comprehension.md`** — the cold-reader protocol: an author agent with
   repo access writes 8 architecture questions with ground truth; a reader
   agent with *only* the atlas answers them; misses are split into coverage
   gaps (map lacks it) vs legibility gaps (map has it, reader couldn't find
   it). The legibility-gap list is the actionable output.

Why measure the *opening* view: `render.py --check` caps the label ratio over
raw edges, but collapsing children concentrates labels — the iteration-3
milgapo map passed `--check` clean and still opened with 53% of its drawn
edges labeled. The reader meets the collapsed view first; that is the view to
measure.

Requires Python 3 stdlib plus a Chrome/Chromium binary for screenshots.
