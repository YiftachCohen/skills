# Demo page

A page that explains work you did, in the same look every time. Use it for a
showcase, a proposal for the team, an architecture write-up, a metrics report,
or an explainer of how something works.

```text
/demo-page write up the search rollout for the platform team
```

Every page uses one look, **Journal**: warm paper, a quiet sans headline over
serif text, and one clay accent. The reading column is narrow, and figures and
diagrams sit wider than the text on soft panels. The look lives in one
stylesheet, so pages stay consistent and the agent spends its effort on the
content instead of choosing a new style each time.

Pages are written for a mixed technical audience: engineers, a technical lead,
a product manager. The first screen states the claim and the ask on its own;
everything below stays fully technical. The agent digs through the repo and the
PR for its facts, asks you only for what the code can't tell (numbers,
decisions, dates), and before handing over has a fresh agent read the finished
page to confirm it says what you meant.

## What's inside

- `assets/journal.css`: the look. Tokens and every component.
- `references/arcs.md`: the order of sections for a showcase, a proposal, an
  architecture page, a metrics report and a how-it-works page.
- `references/diagrams.md`: which diagram answers which question, and what
  draws it (hand SVG, Mermaid rendered at build time, or HTML).
- `examples/diagrams/`: every diagram type in the Journal look.
- `references/comprehension-check.md`: the questions the fresh reader answers.
- `examples/babysit-pr/`: a real page about PR #15 in this repo, with an
  animated figure, a before-and-after table and a Questions section.
- `examples/search-rollout/`: a complete page with a showcase, a metrics table,
  an architecture diagram, steps and a decision, plus an animated product
  figure. New pages start from it.
- `figure/look.ts`: the Journal tokens for stageshow
  figures, so product animations match the page.
- `scripts/build.mjs`: turns a page and its figures into one self-contained
  HTML file, ready to publish as an Artifact or send as a file.

## Requirements

- Node 20 or later.
- For animated figures only: the `stageshow` skill installed, with
  `npm install` run in its folder. Set `STAGESHOW_DIR` if it lives outside
  `~/.claude/skills`, `~/.agents/skills` or `~/.codex/skills`.

## Build the example

```bash
node demo-page/scripts/build.mjs demo-page/examples/babysit-pr/page.html
open demo-page/examples/babysit-pr/dist/page.preview.html
```

## Installation

```bash
npx skills add YiftachCohen/skills --skill demo-page
```
