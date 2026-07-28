# Renderer reference

`scripts/render.py` (Python 3 stdlib only, fully offline) inlines the JSON into
a single self-contained HTML file.

```bash
python3 scripts/render.py .atlas/atlas.json [--open] [--check] [-o out.html]
                          [--theme living|print] [--online-icons]
                          [--repo PATH] [--no-source-check]
                          [--edges] [--inventory [PATH]]
```

| flag | what it does |
|---|---|
| `--check` | validate and write nothing; also confirms every `sourceRef` resolves to a real file and to a line worth jumping to, naming the line to use instead when it lands on a comment, a blank or a bare block opener |
| `--edges` | looks in the `from` node's file for the line that performs each edge's claim, and lists the edges where nothing could |
| `--inventory` | reads the dispositions in `.atlas/inventory.md` back, verifies each named id exists, and counts what was never dispositioned |
| `--repo` | repo root the `sourceRef`s are relative to (inferred from the `<repo>/.atlas/atlas.json` layout; pass it explicitly when the atlas lives elsewhere) |
| `--no-source-check` | skip the `sourceRef` file check |
| `--theme print` | bright editorial theme for embeds and printing (default `living`: near-black, animated) |
| `--online-icons` | preset the Icons toggle on (favicons are opt-in; letter tiles render otherwise, so the file makes zero network requests by default) |

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

Flags reading *inconclusive* are different from the rest: the `from` node's
`sourceRef` is a directory holding more than 40 source files, only the first 40
were scanned, and nothing was found in that slice. That is not evidence of
absence — before this was reported, a container over the cap could pass
vacuously while its edges went unchecked.

## What the rendered viewer does at runtime

Pan/zoom, hover flow tracing, double-click focus mode, expandable containers,
search (matches hidden children), a collapsible minimap, a guided Play tour, an
interactive header (kind pills filter by kind; integration/model chips jump to
their node), an "Ask agent…" button that turns any node or flow into a copyable
context-loaded prompt, and theme/motion/icon toggles remembered per map across
reloads. Share the HTML by sending the file, hosting it, or committing it — zero
network requests unless icons are switched on.
