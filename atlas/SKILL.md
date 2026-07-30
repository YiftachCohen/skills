---
name: atlas
description: |
  Map a codebase into a beautiful, interactive, local-only architecture atlas — entry points, services, data flow, integrations, and any AI layer — rendered as a single self-contained HTML file with drill-down and flow tracing. No upload, no account, no network: nothing leaves the machine. Use whenever the user asks to "map this repo", "atlas this codebase", "scan the codebase", "visualize the architecture", "diagram this system", "show me how this project fits together", "draw the agent/model/tool graph", or wants a shareable-but-private architecture diagram.
---

# Atlas (local codebase map)

Analyze a repository and produce a local, interactive atlas — entry points,
services, data flow, integrations, plus the AI layer when the repo has one. You
produce only the data (a small JSON object); a fixed renderer draws the map.
Write no HTML or CSS. Nothing is uploaded: the output is a single self-contained
HTML file on disk.

## Steps

1. **Resolve the target repo**: an explicit path or repo name in the request
   (confirm it exists), a git URL (shallow-clone it, `--depth 1`, to a temp
   directory), or the current working directory. All paths below are relative to
   the target repo, not to this skill.
2. **Measure and investigate** — see "Investigating" below.
3. **Write the coverage inventory** to `.atlas/inventory.md` — one line per
   item, no prose. A working file, not a deliverable.
4. **Write the map** to `.atlas/atlas.json` in the contract shape below,
   reconciling it against every inventory line. Leave the repo's `.gitignore`
   alone — whether the map gets committed is the user's call; note in your
   summary that `.atlas/` is untracked so they can decide deliberately.
5. **Check it**, and fix what comes back. Instant, writes nothing:
   ```bash
   python3 /abs/path/to/skill/scripts/render.py /abs/repo/.atlas/atlas.json \
     --repo /abs/repo --check --edges --inventory
   ```
   Use targeted edits, not full rewrites, and re-run until it is clean.
   `evals/legibility/stats.py` additionally measures the *opening* view (hub
   fan-out, drawn-edge density, label ratio after containers collapse) — worth
   running on anything large.
6. **Render** once, at the end:
   ```bash
   python3 /abs/path/to/skill/scripts/render.py /abs/repo/.atlas/atlas.json \
     --repo /abs/repo --open
   ```
   Drop `--open` when there's no browser (headless, CI, a sandboxed run); the
   file is written either way.
7. **Report** the file paths and a few summary lines — counts, main flows,
   anything surprising. Don't echo the JSON back. `atlas.html` is renderer
   output, always safe to delete and regenerate; `atlas.json` is yours.

Re-running does not overwrite `atlas.json` for you. Default to a clean scan:
`rm .atlas/atlas.json .atlas/atlas.html` first. Take the incremental path — read
the existing map and check `git log`/`git diff` since `project.date` rather than
re-scanning — only when that date is recent and you wrote the map yourself.

On the incremental path, three things repay the minute they cost:

- **Run `--check` before you edit anything.** It turns the diff into a worklist:
  a deleted file shows up as a dead `sourceRef`, and any warning it reports that
  the diff didn't cause is one the previous run left you.
- **A commit message is a doc, and the code-wins rule applies to it too** — with
  more force here, because on this path the log is your primary input rather
  than a footnote. One tested commit announced a subsystem's removal and deleted
  none of it; the service, its scheduled task, its migrations and ~17 call sites
  were all still live. Confirm each claim in the diff before believing it.
- **Grep for the name of anything deleted.** A removed package leaves references
  no check can see — a CI job still requiring it, a test config still pointing
  at the missing directory, docs still telling users to import it. That debris
  is a finding worth reporting even though the map itself is now correct.

`evidence` refs are `path:line` pins, so an insertion above the call silently
moves the line out from under them and `--check` still passes. One more reason
to attest only the few edges that truly need it.

Never read the viewer sources (`templates/*`) or the rendered `atlas.html`: all
are fixed, and the CLI prints everything you need.

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

The viewer derives the whole header from the graph — no summary fields to keep
in sync. Legacy `stats`/`topModels`/`topTools`/`topIntegrations` are ignored;
don't write them. `project.date` = today.

| field | rule |
|---|---|
| `kind` | one of `entry` (route/page/CLI/webhook), `cron` (scheduled job), `service` (a subsystem that performs the product's own work at runtime — not a catch-all for "internal", see Kind discipline), `agent` (an LLM call the product makes), `model` (the model behind it — an actual model id), `tool` (**a function a model can call**: a `tool({...})` definition, an MCP server tool), `store` (DB/cache/index/config/disk), `external` (3rd-party API). Kinds drive the layout lanes (Entry points → Services & agents → Models & tools → Data & external), so choose accurately. A single-shot LLM call with no loop and no tools is still an `agent`, so its model edge reads correctly — say what it really is in `sub` ("single-shot classify"). |
| `parent` | optional, max depth 2: children render inside their container, collapsed with a `+N` badge and expanding in place. A container with a single child usually wants to be one node. When the real hierarchy runs deeper — app → feature → route in a monorepo — keep the two levels a teammate names out loud (usually feature as container, routes as children) and compress the rest: the outer level becomes a `group`, the inner detail a child's `sub`. Don't invent a middle tier just to have one. |
| `group` | optional, <=24: nodes sharing a group render as one labeled stack. Group by feature/domain the way a team talks ("Billing"), never by file layout; hub nodes stay ungrouped. The viewer puts a group in its members' median lane, so one spanning kinds pulls nodes out of their semantic column — a real cost, worth paying when the team genuinely names the thing as one unit. No groups at all beats a forced one. |
| edge `kind` | optional, prefer setting it: `calls`/`reads`/`writes`/`triggers`/`enqueues`, revealed on flow trace. Two nodes can have more than one edge — a service that both reads and writes a store gets both, not a compromise label. Use `enqueues` for a hand-off that returns before the work happens (a task queue, a job runner, a pub/sub publish): it is where the flow stops being synchronous, which is the first thing a reader needs when the far end never ran. |
| edge `label` | optional, <=24, always visible — spend it on the few relationships that would surprise a reader ("charges on trial end"). See the label budget below. |
| edge `evidence` | optional `path:line` — the call site you read that proves this edge. Records a verification the text heuristic can't repeat (DI, barrel re-exports, generated registries), so `--edges` stops re-flagging it. Use it for the few edges that need it, not as a default: attesting everything switches the check off, and `--check` warns past 80% attested. |
| `domain` | optional favicon domain, no scheme (openai.com) — only for things a recognizable company owns; use the product domain for models (claude.ai). |
| `detail` | <=200: one sentence shown on click. **Treat it as required for internal nodes, like `sourceRef`** — it is what a reader who has never seen the repo actually reads. In a controlled pair of maps of one repo, the one with `detail` on 92% of nodes answered 16/16 comprehension questions and the one with 19% answered 10/16, and every missed answer was a missing sentence rather than a missing box. `--check` warns below 80%. |
| `sourceRef` | repo path plus `:line` (<=120). Treat it as **required for internal nodes** — it feeds jump-to-code and the viewer's "Ask agent…" prompt, and a node without one produces a vague prompt. Rules below. |
| caps | top-level nodes <= 40, children per container <= 20, nodes <= 300, edges <= 500. Labels <= 28 chars, `sub` <= 40. Ids unique; every edge endpoint an existing id. |

**Kind discipline.** `service` is the only kind with no natural boundary, so it
quietly becomes the bucket everything internal lands in — in the two largest
maps this skill has produced it took 69% and 70% of all nodes, absorbing UI
trees, bundler scripts, type definitions and the third-party editors an
installer writes into. It is not "internal code"; the test is runtime work on
the product's own data — something calls it, and it moves or transforms
something. When nothing else seems to fit, one of these does:

- A **UI surface** — screen, panel, component tree, client-side state — belongs
  to the entry point that mounts it, as a child of that `entry`, and the child
  carries kind `entry` too: the header pills count children, so a UI tree filed
  as `service` inflates the service count into a lie about the product. A kit
  shared by several entries is one node, not a container of its components.
- **Build, bundling, release and CI** hang off whatever triggers them: an
  `entry` for push/dispatch, a `cron` for a `schedule:` block.
- A **third-party product you read or write** is `external`, even though the
  code doing it is yours — an installer that writes VS Code's `settings.json`
  is the service; VS Code is not.
- A **shared library** passes the runtime test — a retrying HTTP client is
  called and transforms things — so the line between it and a service is drawn
  by the flow trace, not the call stack: a service is a *stop* in some flow's
  story; a library is *how* a stop does its work. If every edge it would get is
  the same `calls` from half the map and none would earn a label, it's a
  library: at most the single hub node below, otherwise a line in its callers'
  `sub`/`detail`. The swap test settles arguments — replace its implementation
  and no flow redraws → no node. Judge against *this* product's story: secret
  masking is a helper in a web app and a product promise in a security CLI.
  When the tests disagree — auth middleware and rate limiters are hub-shaped
  but can *end* any flow with a 401 or 429 — the flow trace wins: a gatekeeper
  is a stop, and the hub rule prunes its edges, not its node.
- **Types, constants and vocabulary** perform nothing and are never nodes; fold
  them into the node that uses them.

What survives is what a teammate names when asked what the product *does*: an
eligibility engine, an export pipeline, a scan pipeline.

**Granularity.** A kind says what a node *is*; it doesn't say how finely to
slice, and left unstated the same repo maps three different ways. Two rules
settle the cases that actually diverged — three runs over one monorepo produced
11, 2 and 2 stores and 23, 4 and 5 crons, all of them defensible:

- **One `store` per datastore engine**, not per table. Postgres is one node;
  tables, collections and indexes are `children` of it when they earn their own
  line. Two Postgres databases with separate connection strings are two engines
  and two nodes; two schemas in one database are not.
- **One `cron` per job** — the thing that runs — with the schedule in `sub`
  ("Vercel · every 5m"). Not one per cadence, and not one node for all of them.
  Jobs that share a schedule *and* a handler merge with a count ("6 reminder
  crons"); jobs that merely run at the same time do not.

The same instinct generalises: slice by what the system has one of, not by what
happens to be convenient — and when merging, say so in `sub` so the reader knows
a count was collapsed rather than a subsystem dropped.

**Sizing.** The top level is the picture a staff engineer draws on a whiteboard:
as many nodes as the system genuinely has things worth naming out loud, up to
the ceiling of 40. That is the only number — don't aim at a count, and don't pad
a small repo or flatten a large one to look thorough. Completeness lives in
`children`, which enumerate a container's full contents; children only have to
exist in the repo, while every top-level node has to earn its place.

**Label budget.** Labels never fade, so they compete with each other and with
the edges underneath. Count the budget at the *opening* view, not over the raw
edge list: collapsed containers merge every child edge into one drawn edge per
top-level pair, so labels concentrate — a map that passes one-in-four raw has
opened at more than half its visible edges labeled. Collapse the map in your
head to top-level pairs and count again, or run `evals/legibility/stats.py`.
Let `kind` carry the ordinary relationships.

**`sourceRef` rules.** Use a path you actually saw — don't infer one from a
naming pattern (`.ts` when the file is `.tsx`, an index route that doesn't
exist). Point at the definition the node names — the type, the func, the route —
not the doc comment above it, not a bare `const (`, and never the same line as
the node's parent. A container whose subject is a directory points at the
directory itself (`src/stores`, `app/api/admin`) with no `:line`; don't borrow
one member's file, and give every member its own child with its own ref.
`--check` verifies all of this against the repo.

## Coverage — the map must account for everything

Before writing the map, assemble `.atlas/inventory.md` from manifests and greps:
`references/coverage-checklist.md` has the commands and the categories. Keeping
the list in your head is how a scheduled job or a whole flag-driven mode goes
missing without anything registering that it did.

Reconcile every line: each item appears in the map — as a node, a child, or
named in a node's `sub`/`detail` ("+ Google Maps geocoding") — or is omitted in
one sentence. Record the disposition on the line itself, naming the node **id in
backticks**, so the claim can be checked rather than believed:

```markdown
- `scan repo [path]` — child `cmd-scan-repo`
- `ARMIS_LOCAL_S3_ENDPOINT` relaxes the SSRF check — detail on `api-ssrf`
- `completion`, `help` — omitted: cobra boilerplate, no architectural consequence
```

Not `— node (route trees)` or `— mapped`: a disposition that doesn't name an id
reads as reconciliation without being it, and it is how a whole subsystem goes
missing from a map whose inventory looked complete. `--inventory` reads these
back, verifies every id exists, and counts what was never dispositioned:

```bash
# inventory: 83 items — 73 mapped, 10 omitted, 0 unreconciled
```

**Omitted-with-a-reason is a finished state, not a failure.** A large repo
should have a healthy omitted count; inflating nodes to drive it to zero is the
worse error, and it is what pushes maps to hug the 40 ceiling. Only
`unreconciled` must reach 0. Done means: a new engineer clicking through every
container sees nothing missing.

## Edges — where a map misleads

A confidently-labelled edge that isn't real is the one error a reader cannot
detect: it looks exactly like the true ones. `--check` cannot fault one on its
own — an edge is structurally valid as long as both ends are node ids.

`--edges` looks for the line that performs each claim in the `from` node's file
and lists the edges where it found nothing. For each flag, either point at the
line or move the edge to the node whose file performs it. A clean run isn't a
proof: it finds edges with no evidence, not edges with the wrong evidence.

A flag is not a verdict. The heuristic reads text, so it cannot see through a DI
container, a barrel re-export or a generated registry — architectures where
every true edge is invisible by design. When you have found the call site
yourself, record it as the edge's `evidence`:

```json
{ "from": "bookings", "to": "tasker", "kind": "triggers",
  "evidence": "packages/features/bookings/lib/handleNewBooking.ts:412" }
```

That ref is itself checked — a path that doesn't exist or a line past the end of
the file is reported, so `evidence` can't excuse an edge by being vague — and
the edge stops being re-litigated on every run. Flags marked *inconclusive*
rather than absent mean the container's directory was too big to scan whole;
those need the same treatment, and reading them as "no evidence" is how a
container passes vacuously.

Then verify the rest yourself, as one pass over the finished list — not while
drafting, so a habit of mind can't carry across ten edges. For each edge open
the file the `from` node's `sourceRef` names and find the line that performs the
claim: an import of the exact symbol *plus* a call to it, a query naming the
exact table, a fetch or spawn of the exact path. If the performing line lives in
another file, the edge belongs to that file's node. Set `kind` from the call you
found rather than from what the two nodes are for — a screen that loads a record
to prefill a form `reads`; the write is in the hook it hands the form to.

Three quarters of the wrong edges this skill has produced were off by exactly
one hop, and every one looked correct from the import block. Four shapes:

- **The wrapper credited with the work.** A composite action, CLI front-end,
  facade or page shell gets credited with what its caller or callee does — the
  config load that happens in the command rather than the engine, the query that
  happens in the driver script rather than the pure function it calls. If the
  `from` file cannot reach the thing at all (no db client, no import), the edge
  belongs elsewhere. When a node's `detail` describes a step, confirm that step
  is in the file the node's `sourceRef` points at.
- **Import ≠ call, package ≠ symbol.** A utility package routinely exports both
  the thing you assumed and a far smaller thing everyone actually uses (a
  retrying client and a bare transport; a path sanitiser and a plain join). Get
  it wrong once and you write the same wrong edge five times, because every
  importer looks alike from the import block. Read the imported name, not the
  path. Two mechanisms recur: a barrel file re-exporting both a trivial helper
  and the heavyweight writer you meant, and two files with the same name in
  different packages (`features/coupon/actions/general.ts` vs
  `features/subscription/...`).
- **Arrows out of a diagram.** A funnel described in a docstring, README or
  CLAUDE.md that no module implements. When docs and code disagree, map the code
  and say so in your summary. This holds inside a sentence too: if a doc is your
  only source for a mechanism ("streams uploads through io.Pipe"), grep for it
  before repeating it in a `detail` — a stale detail inherits the doc's
  authority and outlives the doc.
- **Hub nodes.** Shared infrastructure (a db connection module, a logger, a
  config loader) touches everything; drawing every true edge buries the story
  the map exists to tell. Give it one node and only load-bearing edges: past a
  dozen edges on one node in the opening view its fan stops being followable,
  which is the signal to prune the ones drawn from theme ("everything reads
  config"). Treat arrows *into* a hub as the highest-risk claims on the map — it
  is the box whose contents everyone assumes and nobody checks. Verify each one
  or leave it out.

Point every edge at the most specific node that's true — the viewer re-routes
and merges edges automatically when a container is collapsed. Draw from a
container only when every child does the same thing.

## Investigating

Measure first, because file trees lie. Vendored directories (`node_modules`,
`.venv`, `vendor`, `dist`, `.next`, `build`) routinely outnumber real source
50:1, and the user's own description ("it's a big python repo") is a guess too.
Count only what you would actually read:

```bash
git ls-files | grep -E '\.(ts|tsx|js|jsx|py|go|rb|rs|java|swift|kt|m|cs|php)$' \
  | grep -vE '(^|/)(tests?|__tests__|spec|fixtures|locales)/|\.(test|spec)\.' | wc -l
```

(or `find` with vendored directories pruned, if it isn't a git repo). Excluding
tests and fixtures matters, and so does keeping `.swift`/`.kt`/`.m`/`.cs` in — a
mobile repo whose native half you never counted is a system you never saw.
Branch on the measured number, not the impression:

| files | approach |
|---|---|
| under ~20 | read every one end to end, then go straight to the contract; skip the largest-files sweep and the fan-out. When the whole system is one file, the top level is its *concepts*, not its functions: five or six nodes a teammate would say out loud beat one node per helper, and landing under 10 is finished, not short. |
| 20–500 | command-first, below |
| 500+ | `references/large-repos.md` |

Work command-first at every size: directory listings for structure, grep for
locations, and open only the files that define agents, tools, services and
schemas — manifests and grep hits answer most of the map.

- **Main flows first**: entry points (routes, webhooks, pages, CLIs), scheduled
  jobs (crons/queues/workers), and the stores/services they read and write.
  Scheduled work hides in CI — grep `.github/workflows/` (or the equivalent) for
  `schedule:`/`cron` before concluding a repo has no `cron` nodes; a nightly job
  is a real actor even when no application code schedules anything.
- **Business logic**: the internal services and pipelines the product is built
  from (billing, ingestion, domain services) — these become `service` nodes,
  with the interesting sentence on the edge ("charges Stripe on trial end").
- **External integrations** (payments, email, auth, analytics).
- **Then the AI layer**, if any: `generateText`/`streamText`/`generateObject`,
  `@ai-sdk/*` providers, Anthropic/OpenAI SDK clients, agent loops, `tool({...})`
  definitions, MCP servers. Identify each model's provider and the tools models
  can call. Give every distinct agent its own node when there are <= 10; merge
  only numerous near-identical ones and say so in `sub` ("12 near-identical
  scrapers"). Chain agents with agent→agent edges when one feeds the next. Repos
  with no AI scan just as well — leave the AI kinds empty.

## Render

See `references/renderer.md` for the full CLI and what the viewer does at
runtime. Shared by Claude and Codex: use the local shell tool for `render.py`;
no network access is required at any step.
