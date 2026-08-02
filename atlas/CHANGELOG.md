# Atlas ruleset changelog

`version:` in `SKILL.md`'s frontmatter is the **ruleset** a map was authored
against, and a map records it as `project.rules`. It is not a release number and
not semver: there is no independently-versioned consumer to negotiate with, so
it is a plain integer that goes up when the rules for *writing* a map change.

It is deliberately separate from `version` inside `atlas.json`, which describes
the JSON **shape**. The two move on different clocks — ruleset 3 redefined what
`cron` means without touching a single field name, and a shape version would
have said nothing about it.

**Why it exists.** A map written under older rules stays structurally valid
forever: `--check`, `--edges` and `--inventory` all pass, because the fields are
all still there and still populated. Only the *meaning* moved. The incremental
path is where that turns into a bug, since it re-reads an existing map and diffs
the repo rather than re-deriving the kinds — so stale semantics propagate with
every check green. `--check` compares the two numbers and says so.

**When to bump.** Any change to what a field means, which kind something takes,
or how finely to slice. Not for wording, new checks, or renderer work — those
don't invalidate an existing map.

---

## Unreleased — checks, not rules

No ruleset bump: nothing here changes what a field means, so no existing map
needs re-deriving. That includes ghost edges and tours — both are additive and
optional, and a map with neither is not wrong, only quieter.

- **Narrated tours.** An optional top-level `tours` array — authored stories
  over the main flows, played by the viewer with a gliding camera, a caption
  card, progressive path lighting and arrow-key control. Optional on purpose: a
  map without tours is complete, not deficient, and no existing map is worse
  for lacking them. `--check` warns on **teleports** (consecutive stops must
  follow real edges from any earlier stop, so forks are fine), on stops with no
  sentence, and on a story that has grown into a lecture. The teleport warning
  is deliberately ambiguous about blame: a hop with no edge means either the
  story invented it or the map is missing the edge.
- **Ghost edges.** `ghost: true` plus `claimedBy: "README.md:31"` records a
  doc-claimed arrow the code does not implement — the "arrows out of a diagram"
  case, which the rules previously told you to drop on the floor. Drawn dashed
  and captioned with its source; excluded from flow tracing, blast radius,
  particles and `--edges`; annotated in the "Ask agent…" prompts so no agent
  goes hunting for code that does not exist. `claimedBy` is required and is
  resolved strictly inside the repo root like `sourceRef`, and a ghost carrying
  `evidence` is flagged as the contradiction it is.
- **Blast radius.** Right-click any node (or use the detail popover's button):
  it dies, and everything that transitively depends on it goes dark, with a
  count and a one-click flip to change-impact. Pure viewer traversal over the
  edges a map already has — no contract change, nothing to author, and it works
  on every atlas ever written. It also makes edge correctness *visible*: an edge
  misattributed by one hop now darkens the visibly wrong half of the map.

**Cost.** A 138-file Go repo cost 877k subagent tokens to map. Most of that was
avoidable, and the fixes are process rather than contract:

- **`scripts/survey.sh`** does the measuring and the whole coverage sweep in one
  command — scale, largest files, manifests (nested ones too), env vars,
  scheduled work, entry points, schemas, exit codes, AI layer — in ~2-4k tokens.
  Run it once and paste from it, instead of having every agent re-derive the
  same metrics. It reads the **working tree**, not the git index, so untracked
  files count and deleted ones don't; it owns its own output path and creates
  `.atlas/`; and it caps matched-line length, because `head -N` bounds lines
  rather than bytes and one hit in a committed minified bundle produced an 89KB
  survey. `tests/test_survey.py` pins all of it.
- **The survey is now authoritative for the mechanical sweep, and
  `coverage-checklist.md` no longer duplicates its commands** — two copies of a
  grep drift, and the copy in a doc is the one that goes stale silently. The
  checklist keeps what a script cannot do: flag-unlocked modes, the
  machine-facing contract, dev-time AI, and how to read the largest-files list.
  Extending coverage means editing the script, so the next scan of that language
  inherits it. Env vars are detected across Node/Vite/Deno, Python, Go, Ruby,
  PHP, Java/Kotlin, C# and Rust — `os.getenv` (lowercase, and the most common
  idiom of all) was previously missed entirely — and the AI sweep now covers the
  major providers, SDK call shapes, agent frameworks and MCP.
- The measuring command was **undercounting test exclusions**: `_test.go` and
  `test_x.py` slip past a directory-name filter, so Go and Python repos measured
  about twice their real size and the largest-files list filled up with tests.
  armis-cli measured 267 files; it has 138. Fixed in the survey and in SKILL.md.
- **The fan-out discipline now applies at any repo size**, not only above 500
  files. `slice-prompt.md` was reachable only via `large-repos.md`, so a
  mid-size repo got six hand-rolled prose prompts, 651k tokens, under a fifth of
  it used. Slices return contract JSON, inventory lines, `counts` carrying the
  command behind each number, and an `uncertain` list. No reports.
- **Counts are run in the main loop, never taken from a subagent's prose.** One
  investigation reported "10 call sites" for a masker that has 26 across 8
  files; a one-second `grep -c` settled it.
- The refute pass should **batch 15–20 claims into one agent and return
  refutations only**. It stays the highest-value spend in the skill: 11 wrong
  sentences of ~37 in one run, 8 of 20 in the next, both with every check green.

**Validated, not projected.** The changes above were measured by mapping a
second repo (276 TS/React Native files, previously unmapped) end to end:

| | armis-cli, old way | nura, new way |
|---|---:|---:|
| source files | 138 | 276 |
| investigation | 651,079 | 339,096 |
| refute | 226,430 | 138,326 |
| **total subagent** | **877,509** | **477,422** |
| per source file | 6,359 | 1,730 |

−46% absolute on a repo twice the size; −73% per file. Quality held: clean under
`--strict` on the first iteration after merge, `detail` on 67/67 nodes, and all
13 counted claims correct because each arrived with the command that produced it.

The saving is from scoped prompts causing less exploratory reading, not from
shorter answers — "tell me about this package" has no stopping condition and one
baseline agent spent 161k across 55 tool calls; the slices averaged 26.

Two survey bugs surfaced only by running on an unfamiliar repo, neither caught
by the suite: `cohere` matched the word "coherent" (and `replicate` matched
"replicate the behaviour"), and the survey scanned its own `.atlas/survey.txt`
so each run re-reported the previous one. Both fixed, both now pinned by tests.

- The label budget is now measured at the opening view (edges re-routed to
  top-level ancestors and merged), matching what SKILL.md always said, and has a
  12-edge floor like every other ratio check.
- `--check` prints the ruleset number and notices a map stamped *newer* than the
  skill, not just older.
- The counted-claims worklist no longer drops large round numbers ("5000 rows").
- `--strict` exits non-zero when anything warned — what SKILL.md means by "clean".
- An inventory disposition must name its id after a disposition keyword to count
  as reconciled; naming the subject in backticks is no longer enough. **Existing
  inventories will report new unreconciled lines** — that is the fix working.
- `sourceRef` and edge `evidence` are resolved strictly inside the repo root.
- Node ids are restricted to `[A-Za-z0-9_.-]`; a `:` in an id silently dropped
  every edge on that node in the viewer.

## 3 — verifiability

Bumped because `cron` changed meaning and several merge rules were added, so
maps written under 1 or 2 have kinds that are now wrong.

- **`cron` means a job**, not just a scheduled one: work triggered from outside
  any request, by a schedule *or* a queue. Celery tasks, job-runner handlers and
  pub/sub consumers are `cron`, with the trigger in `sub`. **Re-scan any map
  with a queue-backed worker** — those task groups were previously `service`,
  and one audited map had 18 of them.
- A poller and the handler it dispatches take the same kind. Splitting them
  across `cron` and `service` hid that they are one mechanism.
- **One node per client, not per endpoint.** N classes differing only in the
  path they call on the same target are one node with the count in `sub`.
- **Boot wiring is never a node**; **stages are not services** and say so in
  `sub`; `group` may carry the layer when a backend has two parallel service
  layers.
- A `store` nested in a `store` is part of that engine, and the header now
  counts it that way. No map needs editing for this — the renderer changed, not
  the contract — but a map that split one database across several top-level
  `store` nodes to work around the old count should be collapsed.
- New required step: **verify the sentences the checks cannot**. Not a data
  change, but a map produced without it should not be trusted — ten of twelve
  load-bearing `detail` claims in one audited map were wrong with every check
  green.

## 2 — evidence

Legibility checks, verified edges, and the `evidence` discipline for edges a
text heuristic cannot see. Introduced `--edges` and the label budget.

## 1 — initial

The output contract, the eight node kinds, the five edge kinds, `--check`, and
the coverage inventory.

Rulesets 1 and 2 predate this file and were numbered retroactively from the
history; maps from that era have no `project.rules` at all, which `--check`
reports as "predates ruleset 3".
