---
name: demo-page
description: |
  Build a single-file HTML page that explains work, in one fixed house look
  (Journal: warm paper, sans headlines over serif text, one clay accent). Use
  when the user wants a page to show what they built, a proposal for the team,
  an architecture write-up, a metrics or results report, or an explainer of
  how something works: "make a demo page", "write this up as a page", "a page
  for the team", "explainer page", "showcase this".
---

# Demo page

A page that explains work to a mixed technical audience: mostly engineers, plus a technical lead and a product manager. It is **skim-first**. The first screen states the claim and the ask on its own, and the depth below it stays fully technical. Every page uses one look, **Journal** (`assets/journal.css`). Two worked examples: `examples/babysit-pr/` is a real showcase of a PR in this repo, and `examples/search-rollout/` is a sample showcase that ends in a proposal.

## Steps

1. **Pin the page.** Write down the page type (`references/arcs.md`), the **claim** as one sentence, and the **ask** as one sentence (a decision and a date, or "none"). Done when the claim would work as the headline.
2. **Dig.** Read the material yourself: the PR and its description, the diff, commits, tests, related docs, dashboards the user points to. Keep a source for every fact (a file and line, a PR, a commit, or the user). Code tells you the mechanism. Numbers, decisions, dates and the audience come from the user: ask for whatever is missing in one message. Done when every fact the page will state has a source. No number is ever estimated into existence.
   - **Derived numbers** (a percent change, a total over the quarter) are fine when the page shows the inputs; list them as inferred at handover.
   - **Relative dates** ("next Friday") become an absolute date with its weekday, checked with `date`; list it as inferred.
   - **A fact nobody has given** (a cause, a limit, a cost) stays visible as a gap: a `.note` that says what is missing, or "Not measured" in its cell. The page still gets built, and the gap goes in the handover questions.
3. **Outline** with the arc for the page type, and drop the sections the story does not need.
4. **Write the page.** Copy `examples/search-rollout/page.html`. Keep its head: the `<title>`, the fonts link and the empty `<style data-journal></style>`. Write to the rules under Writing. Done when no sentence from the example is left.
5. **Add figures** where a picture answers a question the text raises. A page with none is fine: a metrics report often needs only its table.
   - A product moment (a screen, an interaction, a run in a terminal): at most one stageshow figure per page, since it is the most expensive part of a page. Start from the closest of this skill's figures, `examples/babysit-pr/figures/wait.tsx` (a system story: checks, a review, a terminal) or `examples/search-rollout/figures/search.tsx` (a gesture: typing filters a list). Both are themed and pass the film gate at 1280 and 390. Keep their stage sizes: 720 × 340 wide, and a compact design 358 wide that stays wider than tall. Load the `stageshow` skill and read its `references/craft.md`; open its other references only when a gate line names one. Its fresh-eye review and `REHEARSAL.md` are not needed here. Write the figure as `figures/<name>.tsx` next to the page, default-exporting a React component, with the kit imported from `'stageshow/kit'` and `JOURNAL` from `'demo-page/figure/look'` spread on the `Stage`. Mount it with `<div class="fig-stage" data-figure="<name>" data-ss-fill>` inside `figure.fig.breakout`.
   - Anything else (architecture, before and after, sequence, flow, states, data, timeline, layers, charts): pick the diagram by the reader's question with `references/diagrams.md`. It says when to draw by hand, when to use Mermaid (`<pre data-mermaid>`, rendered to SVG by the build) and when to use HTML.
6. **Build:** `node <this skill>/scripts/build.mjs page.html --check` renders figures and Mermaid, and writes `dist/page.html` (Artifact-ready), `dist/page.preview.html`, and the comprehension check's inputs. Never open the built `.html` files: the inlined bundle runs to hundreds of kilobytes. The printed paths are all you need.
7. **Look at it** at 1280 and 390 wide with the `agent-browser` skill. Done when nothing clips and the page never scrolls sideways (a diagram panel or a `.table-wrap` may scroll inside itself on a phone). A stageshow figure also passes the film gate at both widths: `node <stageshow>/scripts/film.mjs "file://<abs>/dist/page.preview.html" --select '.fig-stage' --gate --width 1280` (then `--width 390`) ends `rehearsal passed`. A `scale: … grown past the design size` line is expected for `data-ss-fill`.
8. **Comprehension check.** A fresh subagent reads only `dist/page.txt` and `dist/page.first-screen.png` and answers the questions in `references/comprehension-check.md`. Fix what it misreads, at the source. Its unanswered questions that your sources can answer become the closing **Questions** section (`.qa`), answered from those sources.
9. **Hand over.** Publish `dist/page.html` with the Artifact tool when available, and say it is private until shared. Otherwise, give the file path. In the message, list the facts that came from inference rather than a source or the user, so they can confirm them before sharing, and the questions no source could answer.

## Writing

- **Write in layers.** The headline, the deck, the section heads and each section's first sentence tell the whole story to someone who reads nothing else. A lead or PM can stop there. Everything after a first sentence is depth for engineers: the mechanism, the numbers, the code, the tradeoffs.
- **Headings state findings.** "Agents search twice as often", not "Usage". The headline carries the number when there is one, and it holds for the whole page: when a section reports a regression, the headline names it or leaves room for it.
- **Keep technical names.** On first use, say in plain terms what each one does: "the change feed, which streams every edit to an account". After that, use the bare name.
- **Show one concrete case.** A real request, account or incident traced through, before any general description.
- **Numbers carry their context:** the unit, what they compare against, the time window, and whether they were measured or estimated. Put the source in a caption or the facts row.
- **State the cost.** What got worse, what it costs to run, what is still open. A page with no downside reads as a pitch, and engineers stop trusting it.
- **Plain sentences.** Short and declarative, in active voice. Name things the way the reader names them. Hold the tone of a colleague explaining work they are proud of and honest about.
- **Depth that interrupts goes in `<details>`:** a full query, a config, a raw table. Give it a summary line that says what is inside.

## The look

**Color.** Warm paper ground, a darker paper `--panel`, near-black `--ink`, and gray-brown `--ink-2` for anything secondary. There is one accent, clay (`--accent`), and it marks the one thing in each element that matters: the focal diagram node, the recommended option, step numbers and links. `--good` and `--bad` are for status only: a win or a regression in a table, a passing or failing check. The page is light only, by design, and paints its own ground.

**Type.** Hanken Grotesk is the interface voice: the headline, section heads, labels, tables, diagrams and captions. Source Serif 4 is for reading text. JetBrains Mono is only for code and identifiers. The sizes live in `journal.css`. Use its classes and add no new sizes; a page that seems to need a new size usually needs one fewer level.

**Layout.** One 660px reading column. Figures, diagrams and wide tables take `.breakout` (920px, centered on the column). Panels (`--panel`, 16px radius) hold figures, diagrams, options, notes and details. Running text sits on the page ground.

**Components** (all in `journal.css`):

| Class | For |
|---|---|
| `.masthead` with `.kicker`, `h1`, `.deck`, `.byline`, `.facts` | The first screen: team and page type, the claim, two or three sentences of context, author and date, the status, and the ask stated as the decision itself with its date |
| `.fig.breakout` with `.fig-stage` or `img`, and `figcaption` | Every picture. The caption says what to notice |
| `.sec` with `h2` | One idea per section |
| `table.metrics` with `.before`, `.after`, `.good`, `.bad` | Before and after numbers |
| `table.compare` with a `th` per row and `.before` | Before and after in words: behavior that changed, one situation per row |
| `.stats` with `.stat`, `.stat-value`, `.stat-label` | Three or four big numbers, only when the numbers are the point of the page |
| `.panel` with `svg.diagram` and `dg-*`, or `<pre data-mermaid>` | Diagrams; `references/diagrams.md` picks the type |
| `ol.timeline`, `ol.layers` | A dated sequence; a layer stack |
| `ol.steps` | A real sequence, where the order matters |
| `.options` with `.option[data-recommended]` | A decision: each option's timing, what it gives, what it costs |
| `.note` with `.label` | A risk, caveat or open question the reader must not miss |
| `details` with `summary` | Depth that would interrupt: a query, a config, raw data |
| `dl.qa` with `dt` and `dd` | The closing Questions section: what readers are likely to ask, each answered in two or three sentences from a source |
| `pre > code` | Code, config, a command |
| `.foot` | Author and links back into the page |

A page that needs something new builds it from the tokens in a `<style>` after the `data-journal` one. If it will recur, add it to `journal.css` and to this table.
