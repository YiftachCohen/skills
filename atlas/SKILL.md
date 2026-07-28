---
name: atlas
description: |
  Map a codebase into a beautiful, interactive, local-only architecture atlas — entry points, services, data flow, integrations, and any AI layer — rendered as a single self-contained HTML file with drill-down and flow tracing. No upload, no account, no network: nothing leaves the machine. Use whenever the user asks to "map this repo", "atlas this codebase", "scan the codebase", "visualize the architecture", "diagram this system", "show me how this project fits together", "draw the agent/model/tool graph", or wants a shareable-but-private architecture diagram.
---

# Atlas (local codebase map)

Analyze a repository and produce a local, interactive atlas — a map of how the
codebase works: entry points, services, data flow, integrations, plus the AI
layer (agents, models, tools) when the repo has one — one facet, not the
point. You produce only the data (a small JSON object); a fixed renderer
draws the map. Write no HTML or CSS. Nothing is uploaded anywhere: the output
is a single self-contained HTML file on disk.

## Target repo

1. An explicit path or repo name in the request — resolve it and confirm it
   exists before starting.
2. A git URL — shallow-clone it (`--depth 1`) to a temp directory.
3. Otherwise, the current working directory.

All paths below are relative to the target repo, not to this skill.

## Steps

1. Investigate the repo (below) and write the coverage inventory to
   `.atlas/inventory.md` — one line per item, no prose. It is a working file,
   not a deliverable: writing it down is what makes the reconciliation below
   something you did rather than something you meant to do, and on a re-run it
   shows what the repo grew since last time.
2. Build the JSON contract, reconciling it against every inventory line.
3. Write it to `.atlas/atlas.json`. Leave the repo's `.gitignore` alone — it's a
   tracked file, and whether the map gets committed is the user's call, not
   yours. Note in your summary that `.atlas/` is currently untracked so they can
   ignore or commit it deliberately.
4. Render: `python3 <skill-dir>/scripts/render.py .atlas/atlas.json --open` —
   writes `.atlas/atlas.html` and opens it. Drop `--open` when there's no
   browser to open (headless, CI, a sandboxed run); the file is written either
   way. On a validation error, fix the JSON and re-run.
5. Tell the user where the files live and what the map shows. Re-running
   overwrites them — safe to repeat as the repo evolves.

## Working efficiently

Investigation is where your context goes — spend it deliberately:

- Never read the viewer sources (`templates/viewer.html`, `viewer.css`,
  `viewer.js`) or the rendered `.atlas/atlas.html`: all are fixed, and the CLI
  prints everything you need (validation errors/warnings, output path).
- While iterating on the JSON, validate with `--check` (instant, writes
  nothing) and fix findings with targeted edits, not full rewrites; render
  with `--open` once, at the end.
- Know what `--check` can't do. It checks nodes — shapes, caps, and that every
  `sourceRef` lands on a real file and a line worth landing on. It cannot check
  an edge: an edge is structurally valid as long as both ends are node ids, so
  "166/166 sourceRefs resolve" says nothing about the 97 claims your edges make.
  Edges are where a map misleads, and verifying them is entirely on you.
- On a re-run, read the existing `.atlas/atlas.json` and update it — check
  what changed (git log/diff) instead of re-scanning the whole repo.
- Report to the user with the file paths and a few summary lines (counts,
  main flows, anything surprising) — don't echo the JSON back.

## Coverage — the map must account for everything

Two levels: the TOP LEVEL is the picture a staff engineer draws on a whiteboard
— as many nodes as the system genuinely has things worth naming out loud. In
practice that lands near 10 for a small app and near 30 for a large product, but
those are observations, not targets. The only hard number is the ceiling of 40
below: a map that stops at 34 because 34 is what the system has is finished, not
short, and there is nothing to agonise over between 34 and 39. Completeness
lives in `children` (nodes with `parent` set) that
enumerate a container's full contents — every admin section, route group, schema
cluster, agent tool. The viewer renders containers collapsed with a `+N` badge,
expanding in place.

Before writing the map, write the coverage inventory to `.atlas/inventory.md` —
a compact checklist (one line per item, assembled from manifests and greps, not
prose). Keeping it in your head is how a scheduled job or a whole flag-driven
mode goes missing without anything registering that it did:

- every dependency in the package manifest (grouped; 30 UI packages = 1 line)
- every env var (`.env.example`, an env schema, or a `process.env`/`os.Getenv`
  grep) — flag the ones that change behaviour the map draws, like an escape
  hatch that disables a validation step you drew as a security control
- every route/entry directory, every scheduled job (including CI `schedule:`)
- every schema/model file and its tables
- every internal service/feature module
- **the largest non-test source files, by line count** — every other line here
  is organised by category, and a category sweep silently skips a big file
  sitting in a package you already ticked off ("internal/cmd → the command nodes
  above"). Sorting by size finds it:
  `git ls-files '*.ext' | grep -v test | xargs wc -l | sort -rn`
  Walk down the list checking each against the map and stop when several
  consecutive files in a row are ones you would fairly omit — not at a fixed
  count. The cutoff is where the list goes quiet, and it is usually further down
  than feels necessary: in one 140-file repo the two biggest misses sat at ranks
  25 and 29, well past any round number you would have picked in advance.
- every mode a flag unlocks — a `--changed`/`--watch`/`--dry-run` that takes a
  different code path is a branch of the system, not a flag
- the machine-facing contract, where there is one: exit codes, output files,
  report formats that CI consumes
- every AI agent, model id, and tool definition

Reconcile: each inventory item must appear in the map — as a node, a child,
or named in a node's `sub`/`detail` ("+ Google Maps geocoding") — or be
omittable in one sentence (dead code, pure UI libraries). Say which it was, in
one word, next to the line. Done means: a new engineer clicking through every
container sees nothing missing.

## How to investigate

Measure first, because file trees lie. Vendored directories (`node_modules`,
`.venv`, `vendor`, `dist`, `.next`, `build`) routinely outnumber real source
50:1, and the user's own description ("it's a big python repo") is a guess too.
Count only what you would actually read:

```bash
git ls-files | grep -cE '\.(ts|tsx|js|jsx|py|go|rb|rs|java)$'
```

(or `find` with those directories pruned, if it isn't a git repo). A repo that
looks like 2,000 files is often 20 — and reading 20 files beats inferring from
greps every time. Pick your approach from the measured number, not the
impression.

Then work command-first at every repo size: directory listings for structure,
grep for locations, and open only the files that define agents, tools, services,
and schemas — manifests and grep hits answer most of the map.

- Main flows first: entry points (routes, webhooks, pages, CLIs), scheduled
  jobs (crons/queues/workers), and the stores/services they read and write.
- Business logic: the internal services/pipelines the product is built from
  (billing, ingestion, domain services) — these become `service` nodes, with
  the interesting sentence on the edge ("charges Stripe on trial end").
- External integrations (payments, email, auth, analytics).
- Then the AI layer, if any: `generateText`/`streamText`/`generateObject`,
  `@ai-sdk/*` providers, Anthropic/OpenAI SDK clients, agent loops,
  `tool({...})` definitions, MCP servers. Identify each model's provider and
  the tools models can call.
- Repos with no AI scan just as well — leave the AI kinds empty.
- Scheduled work hides in CI. Grep `.github/workflows/` (or the equivalent) for
  `schedule:`/`cron` before concluding a repo has no `cron` nodes — a nightly
  job or a daily self-scan is a real actor even when no application code
  schedules anything.
- An import is not a call, and a package is not a symbol. Every edge asserts that
  A does something to B, and a confidently-labelled edge that isn't real is the
  one error a reader cannot detect — it looks exactly like the true ones. Grep
  the call site and read *which exported name* is called: a utility package
  routinely exports both the thing you assumed and a far smaller thing everyone
  actually uses (a retrying client and a bare transport; a path sanitiser and a
  plain join). Get that wrong once and you write the same wrong edge five times,
  because every importer looks alike from the import block. Name the function in
  your head before you draw the arrow.
- Shared infrastructure (a db connection module, a logger, a config loader)
  touches everything; drawing every true edge buries the story the map exists to
  tell. Give it one node and only the edges that are load-bearing. Treat arrows
  *into* that node as the highest-risk claims on the map — it is the box whose
  contents everyone assumes and nobody checks, so it attracts edges drawn from
  theme rather than fact. Verify each one or leave it out.
- Attribute behaviour to the code that performs it, not to the thing the user
  thinks of. A wrapper that people invoke (a composite action, a CLI front-end,
  a facade) is constantly credited with work that actually lives one layer away
  in the caller or the callee — the config load that happens in the command
  rather than the engine, the upload that happens in the workflow rather than
  the action it calls. When a node's `detail` describes a step, confirm that
  step is in the file the node's `sourceRef` points at.
- When docs and code disagree, map the code and say so in your summary. READMEs
  and CLAUDE.md drift, and a subsystem that exists only in documentation doesn't
  belong on a map of how the thing actually works. This holds inside a sentence
  too: if a doc is your only source for a mechanism ("streams uploads through
  io.Pipe"), grep for it before repeating it. A stale detail copied into a
  node's `detail` inherits the doc's authority and outlives the doc — and it is
  a special trap when you have already noticed that file is out of date.

### Large repos (500+ real source files, measured)

Do NOT read files one by one — you will run out of context. Instead:

- Skeleton first: top-level layout, `package.json`/`pyproject.toml`/`go.mod`
  (dependencies reveal models, tools, and integrations instantly), route
  manifests, `docker-compose.yml`, cron/queue config, CI workflows.
- Useful greps: provider SDKs (`@ai-sdk/`, `anthropic`, `openai`),
  `streamText|generateText|tool(`, `stripe|resend|twilio|slack`, DB clients,
  `cron|queue|worker` — hit locations show where each subsystem lives.
- If subagents are available, fan out 2–4 parallel investigations — e.g.
  entries+crons / AI usage / services+stores+integrations. Instruct each to
  return ONLY compact JSON (`{nodes, edges}` in the contract shape, with
  `sourceRef`s) — no prose report, no file excerpts; merge and dedupe
  yourself. Agree the shared ids up front: name the handful of nodes more than
  one of them will touch and fix each one's `kind` (`postgres`, not `neon-db`
  in one report and `db` in another). Reconciling id collisions afterwards
  costs more than the fan-out saves.
- Write a large atlas in a few appends rather than one enormous Write call —
  a 200-node graph can exceed the output limit mid-JSON, and a truncated file
  means starting the write over.
- Monorepo: scan the package the user cares about, or make each package a
  `group` keeping only its externally-visible pieces.
- The caps are the design, not a limitation: a 3,000-file repo still maps to
  20–40 top nodes because near-identical things merge into one ("14 CRUD
  routes") and file layout is never the map. Every node must be something a
  teammate would name out loud when explaining the system.

## Output contract — write EXACTLY this shape to `.atlas/atlas.json`

```json
{
  "version": 2,
  "project": {
    "name": "string (<=48)",
    "slug": "lowercase-dashed (<=48)",
    "tagline": "one line (<=80, optional)",
    "iconDomain": "favicon domain for the project, e.g. acme.com (optional)",
    "date": "YYYY-MM-DD"
  },
  "graph": {
    "nodes": [
      { "id": "chat", "label": "Dashboard chat", "kind": "entry", "sub": "/api/chat" },
      { "id": "agent", "label": "Support agent", "kind": "agent", "sub": "streamText",
        "sourceRef": "src/agents/support.ts:42",
        "detail": "Answers tickets with order lookups (<=200, optional)" },
      { "id": "gpt4o", "label": "GPT-4o", "kind": "model", "domain": "openai.com" },
      { "id": "billing", "label": "Billing service", "kind": "service",
        "sourceRef": "src/services/billing.ts" },
      { "id": "billing-plans", "label": "Plans & quotas", "kind": "service",
        "parent": "billing", "sourceRef": "src/services/billing/plans.ts" },
      { "id": "pg", "label": "Postgres", "kind": "store", "domain": "postgresql.org" }
    ],
    "edges": [
      { "from": "chat", "to": "agent", "kind": "triggers" },
      { "from": "agent", "to": "gpt4o", "kind": "calls" },
      { "from": "billing", "to": "pg", "kind": "writes", "label": "charges on trial end" }
    ]
  }
}
```

The viewer derives the whole header from the graph (kind counts include
children; model chips from `model` nodes; integration chips from
store/external nodes with a `domain`) — no summary fields to keep in sync. Legacy
`stats`/`topModels`/`topTools`/`topIntegrations` fields are ignored; don't
write them.

## Rules (these keep every atlas consistent)

- `kind` is one of: `entry` (route/page/CLI/webhook trigger), `cron`
  (scheduled job), `service` (internal business-logic module the project
  owns), `agent`, `model`, `tool`, `store` (DB/cache/index), `external`
  (3rd-party API). Kinds drive the semantic layout lanes (Entry points →
  Services & agents → Models & tools → Data & external; externals render as
  dashed outlines) — choose them accurately. Two calls come up constantly: a
  single-shot LLM call with no loop and no tools is still an `agent`, because it
  belongs in the models lane for its model edge to read correctly — say what it
  really is in `sub` ("single-shot classify"). Runtime config the system reads
  (`.env`, a settings table) is a `store`.
- Two levels via `parent` (optional): children render inside their container
  when expanded; max depth 2. Point every edge at the most specific node
  that's true — the viewer re-routes and merges edges automatically when a
  container is collapsed. A container with a single child is usually a node that
  wants to be one node; keep it only when that child is a real thing a reader
  would look for (a table, a tool). Two nodes can have more than one edge
  between them — a service that both reads and writes a store gets both, not a
  compromise label.
- Caps are ceilings, not targets: top-level nodes <= 40, children per container
  <= 20, nodes <= 300, edges <= 500. Size the top level to the system rather
  than to a number — padding a small repo with invented nodes and flattening a
  large one to look thorough are the same mistake pointing opposite ways. Every
  top-level node must earn its place; children just need to exist in the repo.
- Give every distinct agent its own node when there are <= 10; merge only
  numerous near-identical ones and say so in `sub` ("12 near-identical
  scrapers"). Chain agents with agent→agent edges when one feeds the next.
- `group` (optional, <=24 chars): nodes sharing a group render as one labeled
  stack. Group by feature/domain the way a team talks ("Billing",
  "Ingestion"), never by file layout; hub nodes stay ungrouped. The viewer puts
  a group in its members' median lane, so one spanning kinds pulls some nodes out
  of their semantic column. That's a real cost, not a prohibition: prefer
  same-kind groups, and spend it when the team genuinely names the thing as one
  unit (a scoring funnel that runs service → agent → service is worth more
  together than lane-pure apart). A couple of groups of a few nodes each is
  typical, and no groups at all beats a forced one.
- Edge `kind` (optional, prefer setting it): `calls`|`reads`|`writes`|`triggers`,
  revealed on flow trace. Add a `label` (always visible, <=24) only when a
  specific phrase says more — put the business logic on edges ("charges on
  trial end"). Labels never fade, so they compete with each other and with the
  edges underneath: past roughly one label per four edges the map opens as a
  thicket of grey text at fit-zoom, legible only once you zoom in. Let `kind`
  carry the ordinary relationships and spend labels on the few that would
  surprise a reader.
- `domain` (optional): favicon domain, no scheme (openai.com, exa.ai) — only
  for things a recognizable company/product owns; omit for internal nodes.
  Use the product domain for models (claude.ai, gemini.google.com). Favicons
  are opt-in (toolbar "Icons" toggle or `--online-icons`); letter tiles
  render otherwise, so the file makes zero network requests by default.
- `detail` (optional, <=200): one sentence shown on click. `sourceRef`
  (optional, <=120): repo path plus `:line` (`src/agents/support.ts:42`) —
  add it to internal nodes so teammates can jump to code. Both feed the
  viewer's "Ask agent…" prompt, so a node with a real `sourceRef` and a
  `detail` hands the next agent a usable starting point; one without them
  produces a vague prompt. Treat them as required for internal nodes. Use a path
  you actually saw — don't infer one from a naming pattern (`.ts` when the file
  is `.tsx`, an index route that doesn't exist). Point at the definition the
  node names — the type, the func, the route — not the doc comment above it, not
  the file's bare `const (`, and never the same line as the node's parent (a
  child sharing its parent's ref is a child you never actually located).
  `--check` verifies every sourceRef against the repo and flags those three
  cases with the line to use instead, so a guess surfaces as a warning rather
  than as a dead link a teammate finds later.
- Labels <= 28 chars, `sub` <= 40. Edge `from`/`to` must be existing node
  ids; ids unique. `project.date` = today.

## Render

`scripts/render.py` (Python 3 stdlib only, fully offline) inlines the JSON
into a single self-contained HTML file:

```bash
python3 scripts/render.py .atlas/atlas.json [--open] [--check] [-o out.html]
                          [--theme living|print] [--online-icons]
                          [--repo PATH] [--no-source-check]
```

`--check` validates without writing, including confirming that every `sourceRef`
resolves to a real file and to a line worth jumping to — it flags refs that land
on a comment, a blank, or a bare block opener, and names the line to use instead
(it finds the repo automatically from the `<repo>/.atlas/atlas.json` layout;
pass `--repo` if the atlas lives elsewhere, or `--no-source-check` to skip). `--theme print` is a bright editorial
theme for embeds/printing (default `living`: near-black, animated). The
rendered viewer handles the rest at runtime — pan/zoom, hover flow tracing,
double-click focus mode, expandable containers, search (matches hidden
children), a collapsible minimap (click or drag to move the camera), a guided
Play tour, an interactive header (kind pills filter by kind; integration/model
chips jump to their node), an "Ask agent…" button that turns any node or flow into a copyable,
context-loaded prompt, and theme/motion/icon toggles that are remembered per map
across reloads (the rendered `--theme`/`--online-icons` stay the default until
the reader changes them). Share the HTML by sending the file, hosting it, or
committing it — zero network requests unless icons are switched on.

## Runtime compatibility

Shared by Claude and Codex. Use the local shell tool for `render.py`; no
network access is required at any step.
