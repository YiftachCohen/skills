# Renderer reference

`scripts/render.py` (Python 3 stdlib only, fully offline) inlines the JSON into
a single self-contained HTML file.

```bash
python3 scripts/render.py .atlas/atlas.json [--open] [--check] [--strict] [-o out.html]
                          [--theme living|print|terrain] [--online-icons]
                          [--repo PATH] [--no-source-check]
                          [--edges] [--inventory [PATH]]
```

| flag | what it does |
|---|---|
| `-o`, `--out` | output HTML path (default: `atlas.html` beside the atlas file) |
| `--open` | open the rendered file in the default browser once it's written |
| `--check` | validate and write nothing; also confirms every `sourceRef` resolves to a real file and to a line worth jumping to, naming the line to use instead when it lands on a comment, a blank or a bare block opener. Flags the `service` share at the **top level** as well as over all nodes, and any edge pointing at its own container. Prints a **counted-claims worklist** — every `sub`/`detail` asserting a number — because nothing here can verify "30 backends", and an audited map had 8 of 32 counts wrong. Also prints a **labelled-edges worklist** (skipped when `--edges` already produced a sharper one) so each label can be verified at a call site |
| `--strict` | exit 1 if anything warned, not just on errors — the "re-run until it is clean" contract SKILL.md describes, made machine-checkable. Works in both `--check` and render mode |
| `--edges` | looks in the `from` node's file for the line that performs each edge's claim, and lists the edges where nothing could. Does nothing without a repo root: pass `--repo`, or let it infer from the `<repo>/.atlas/atlas.json` layout — otherwise it's silently a no-op with a warning telling you to pass `--repo` |
| `--inventory` | reads the dispositions in `.atlas/inventory.md` back, verifies **every** id named on a line exists (a line whose first id is live and whose rest are stale used to pass), and counts what was never dispositioned |
| `--repo` | repo root the `sourceRef`s are relative to (inferred from the `<repo>/.atlas/atlas.json` layout; pass it explicitly when the atlas lives elsewhere) |
| `--no-source-check` | skip the `sourceRef` file check |
| `--theme print` | bright editorial theme for embeds and printing (default `living`: near-black, animated) |
| `--theme terrain` | surveyed-chart theme: aged paper, earth-pigment ink, serif throughout; prints as itself rather than falling back to `print` |
| `--online-icons` | preset the Icons toggle on (favicons are opt-in; letter tiles render otherwise, so the file makes zero network requests by default) |

## Ruleset drift

`--check` compares the map's `project.rules` against the `version:` in
`SKILL.md`'s frontmatter and warns when the map is behind or unstamped. This is
the one staleness a map cannot show on its own: the rules change what a *kind
means* without moving a field, so an older map stays structurally valid while
its kinds are wrong. It matters most on the incremental path, which re-reads
existing kinds instead of re-deriving them. `CHANGELOG.md` says what changed
between any two rulesets and therefore what needs re-scanning.

`project.rules` is not the same as `version` inside the atlas, which describes
the JSON shape and moves far less often.

## What none of these can tell you

Every flag here checks *structure*: that a path resolves, an id exists, a caller
mentions its callee. None reads a `detail` sentence, and that is the field a
reader trusts most. One map passed `--check --edges --inventory` clean while ten
of its twelve load-bearing sentences were wrong, including one that asserted the
opposite of the code. A green run means well-formed, not true — see "Details" in
SKILL.md for the adversarial pass that catches those.

## What `--edges` can and can't tell you

It asks, per target kind, the question a reviewer would ask: does this file
reach a database at all, does it import that module, does it name that URL, does
it mention that SDK. Comments and docstrings don't count — an arrow copied out
of an architecture diagram is one of the two ways wrong edges get drawn.

A flag is not a verdict. An edge that is real through a barrel re-export, a DI
container, or a framework's implicit dispatch will land here too. It means you
have to point at the line, not that the edge is wrong. Equally, a clean run is
not a proof: the check finds edges with *no* evidence, not edges with the
*wrong* evidence, and it cannot see a label that overstates what the line does.

Once you have pointed at the line, put it in the edge's `evidence`
(`path.ts:120`) and the flag retires: the ref is verified (bad path, missing
line number, or a line past the end of the file is reported) but the heuristic
stands down. The run prints how many edges are attested this way.

Two shapes are skipped rather than flagged. An edge whose `from` and `to` refs
are plain files in the *same directory* is one package's scope — the callee is
visible unqualified, so there is no import to find; asking for one is asking a
file to import itself. (A container whose ref is the directory is still
checked.) And a `from` node of kind `external` has no code here to read.

Expect roughly a 10% flag rate with about a 30% hit rate on a Go codebase — two
unrelated Go repos landed within a point of each other. The 70% it cannot see
are interface fields filled by DI, handlers registered into an ordered slice
with no call site anywhere, generated clients across a network hop, child
processes, and Kubernetes watches, which have no call site in either direction
by design. Treat a clean result on those mechanisms as unproven, not verified.

Flags reading *inconclusive* are different from the rest: the `from` node's
`sourceRef` is a directory holding more than 40 source files, only the first 40
were scanned, and nothing was found in that slice. That is not evidence of
absence — before this was reported, a container over the cap could pass
vacuously while its edges went unchecked.

## `evals/legibility/stats.py` — measuring the opening view

`render.py --check` validates the contract; `stats.py` measures the *view*
that contract produces. It reconstructs what the viewer draws at open
(children collapsed, edges re-routed to their top-level ancestor and merged)
and reports the load each element puts on a reader: hub fan-out, drawn-edge
density, the label ratio after containers collapse, groups spanning too many
kinds, oversized containers, and top-level nodes left floating with no visible
edge. Thresholds are heuristics from eyeballing real maps, not laws — worth
running on anything large, on top of `--check`.

```bash
python3 /abs/path/to/skill/evals/legibility/stats.py /abs/repo/.atlas/atlas.json
```

Exit code is always 0 unless the file is unreadable; its warnings are signal
for a human or vision grader to go look at, not a gate.

## What the rendered viewer does at runtime

Pan/zoom, hover flow tracing, double-click focus mode, expandable containers,
search (matches hidden children), a collapsible minimap, a guided Play tour, an
interactive header (kind pills filter by kind; integration/model chips jump to
their node), an "Ask agent…" button that turns any node or flow into a copyable
context-loaded prompt, and theme/motion/icon toggles remembered per map across
reloads. Share the HTML by sending the file, hosting it, or committing it — zero
network requests unless icons are switched on.
