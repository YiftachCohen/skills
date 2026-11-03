# Diagrams

Pick a diagram by the question the reader is asking at that point in the page, then draw it with the renderer that question needs. `examples/diagrams/` shows every type below in the Journal look; copy from it.

## Which diagram

| The reader asks | Diagram | Draw it with |
|---|---|---|
| What are the parts, and how do they connect? | Architecture | Hand SVG (`examples/search-rollout`) |
| What changes? | Before and after, nodes in the same places | Hand SVG |
| In what order do things talk? | Sequence | Mermaid `sequenceDiagram` |
| What happens next, and where does it branch? | Flowchart | Mermaid `flowchart`; hand SVG if it is one row and the page's main picture |
| What states can it be in? | State machine | Mermaid `stateDiagram-v2` |
| What does the data look like? | Entities and relations | Mermaid `erDiagram` |
| What happened when, or what ships when? | Timeline | HTML `.timeline`; Mermaid `gantt` only for parallel workstreams with durations |
| How is it layered? | Layer stack | HTML `.layers` |
| What does it look like while it runs? | A screen in motion | stageshow figure |
| How did a number move? | Chart | Inline SVG, following the `dataviz` skill with the Journal tokens |
| Which option wins on what? | Comparison | `table.compare` |

A page rarely needs more than two diagrams. Each one sits where its question comes up, in a `figure.fig.breakout`, and its caption states the answer rather than naming the diagram.

## Hand SVG

Use hand SVG when position carries meaning: the page's main architecture picture, a before and after, anything where the focal node must sit where the eye lands.

- An inline `svg.diagram` inside `.panel`, with the `dg-*` classes: `dg-node` (add `.focus` for the one node the story is about), `dg-title`, `dg-sub`, `dg-lane`, `dg-edge` (add `.async` for periodic or asynchronous edges), `dg-arrow`, `dg-note`.
- Lay it out on a grid: equal node widths, equal gaps, edges straight across or down. Flows run left to right and hierarchies top to bottom.
- Keep a node's sub-label to about 20 characters at 12px; size the box to its longest label.
- A before and after keeps every node in the same position, so only the edges and the focus change.
- Give the `svg` a `<title>` that says what the diagram shows.

## Mermaid

Use Mermaid when correctness of every message, state or relation matters more than composition, and auto layout does the job: sequences, state machines, schemas, branching logic with more than a handful of paths.

- Write the source in `<pre data-mermaid>…</pre>` inside `.panel`. The build renders it to static SVG in the Journal theme (`assets/mermaid-theme.json`), so the page ships no Mermaid and reads complete at rest. Rendering needs Chrome and network access to jsDelivr at build time. A syntax error stops the build and names the diagram.
- Mark the focal node with `:::focus` in a flowchart, or `class X focus` in a state diagram; the theme draws it in clay.
- Keep labels short. A long label in a flowchart diamond makes the diamond huge, so put the question in two or three words and the detail in the edge labels.
- Name participants and states the way the reader does, and name every transition by its cause.
- Leave out options the theme already sets (colors, fonts, curves). Never use `%%{init}%%`, which overrides the look.

## HTML diagrams

- `.timeline`: an `ol` of `li` with a `time` and a `p` (`strong` for the title, then a line of detail). Set `data-state` to `done`, `now` or `next`.
- `.layers`: an `ol` from the layer closest to the user down, each `li` a `strong` name and a `span` of what it does. Mark one `.focus`.

## Checking a diagram

At 1280 and 390 wide, every label is readable and inside its box, no edge crosses a label, and the focal node is the first thing the eye lands on. On a phone a wide diagram scrolls inside its panel, while the rest of the page stays still.
