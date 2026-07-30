# Large repos (500+ real source files, measured)

Do NOT read files one by one — you will run out of context.

- **Skeleton first**: top-level layout, `package.json`/`pyproject.toml`/`go.mod`
  (dependencies reveal models, tools and integrations instantly), route
  manifests, `docker-compose.yml`, cron/queue config, CI workflows.
- **Useful greps**: provider SDKs (`@ai-sdk/`, `anthropic`, `openai`),
  `streamText|generateText|tool(`, `stripe|resend|twilio|slack`, DB clients,
  `cron|queue|worker` — hit locations show where each subsystem lives.
- **Fan out**, if subagents are available: 2–4 parallel investigations, e.g.
  entries+crons / AI usage / services+stores+integrations. Instruct each to
  return ONLY compact JSON (`{nodes, edges}` in the contract shape, with
  `sourceRef`s) — no prose report, no file excerpts; merge and dedupe yourself.
  Agree the shared ids up front: name the handful of nodes more than one of them
  will touch and fix each one's `kind` (`postgres`, not `neon-db` in one report
  and `db` in another). Reconciling id collisions afterwards costs more than the
  fan-out saves.
  A subagent has not read this skill, so the vocabulary has to travel with the
  prompt: the eight node kinds, the five edge kinds (`calls`/`reads`/`writes`/
  `triggers`/`enqueues`), and the `sourceRef` + `detail` rules. Left unstated
  they invent edge kinds (`uses`, `depends`) and you rewrite every edge by hand
  — in one run all four came back invalid. **`references/slice-prompt.md` is
  that block, ready to paste**, with four marked slots for the slice's own
  scope, budget and shared ids; writing it out per slice is where the fan-out
  cost goes. Ask each for inventory lines for its own slice too; reconciliation
  is per-line, and the agent that read the code is the one who knows what it
  found.
- **Budget TOTAL nodes per slice, not just top-level ones.** Children are where
  the overrun happens: cap each slice's top level and its children are still
  unbounded, so five slices that each respected their top-level budget returned
  392 nodes against the 300 cap, and ~100 nodes had to be generated, paid for
  and then deleted in the merge. Divide 300 across the slices up front — "at
  most 11 top-level and 55 nodes in total" — and say that near-identical
  children merge with a count rather than being enumerated.
- **Tell subagents NOT to emit `evidence` or edge `label`.** Both are decisions
  about the whole map that a slice cannot see: the label budget is counted at
  the opening view, and attestation is only sound when it stays rare. Asked for
  them, subagents mass-produce — one Go run's five slices returned ~200 labels
  of which 20 survived, and two runs came back with evidence on 58% and 100% of
  edges, which switches `--edges` off across the map before it ever runs. Have
  them return the performing line as a plain field (`sawAt`) instead, then run
  `--edges` on the merged map with no attestation at all and promote to
  `evidence` only the true edges it flags.
- **Write in a few appends** rather than one enormous Write call — a 200-node
  graph can exceed the output limit mid-JSON, and a truncated file means
  starting the write over.
- **Monorepo**: scan the package the user cares about, or map the whole fleet
  with each package as a `group` keeping only its externally-visible pieces.
  This is the one case where grouping by directory is right, and it overrides
  the "never by file layout" rule: in a monorepo the package boundary *is* the
  domain boundary — it is what the team deploys, versions and owns separately.
  Group by package only when the packages really are that independent; a
  `packages/` tree of one product's internal modules is file layout again.
- **Cross-package edges are where every error in a monorepo has come from.**
  Verify each one individually: resolve barrel re-exports to the symbol actually
  imported, and check you have not conflated two files with the same name in
  different packages.
- **The caps are the design**: a 3,000-file repo still maps to at most 40 top
  nodes because near-identical things merge into one ("14 CRUD routes") and file
  layout is never the map.

## Merging the slices

This is the step that goes wrong, and it is mechanical enough to do in a script
rather than by hand. Merge, *then* run the checks — never the reverse.

**Collapsing a child rewires its edges, and rewired edges are not facts.** When
a merge folds a child into its parent, its edges have to go somewhere, and
pointing them at the parent invents relationships nobody verified. One run
collapsed ~100 children and manufactured four edges that were never true,
including one that pointed backwards up its own call chain — all four looked
plausible and none had a call site. Two rules make it safe:

- An edge whose `from` and `to` both resolve to the **same** node is dropped,
  not kept as a self-loop.
- An edge from a node to its **own container** is dropped. `--check` flags these
  now; the other cause it catches is a genuine inversion, where a wrapper that
  calls a subsystem was filed underneath it.

**When you are over the node cap, cut in this order.** Do not cut evenly — the
tiers differ enormously in what a reader loses:

1. **Interchangeable implementations of one slot** → one node with the count in
   `sub` (30 vector backends, 14 storage backends, 8 trace exporters, 5 typed
   clients over one daemon). Costs the reader nothing; it is what the
   Granularity rules ask for anyway.
2. **Route/CRUD children that mirror a sibling surface** — the same resource
   exposed under a second token usually needs one line in the parent's `detail`,
   not its own box.
3. **Stages that only ever run inside one parent flow**, folded into the stage
   that names them.
4. **Whole subsystems** — last resort, and record each one in the inventory as
   omitted so the coverage record still accounts for it.

**Any pass that deletes or merges nodes invalidates the checks you already
ran.** Re-run `--check --edges --inventory` afterwards, not just after the first
write: dropped ids leave dead dispositions that read as reconciled, and dropped
nodes leave edges pointing at their parents.

**A node that merges N implementations points its `sourceRef` at the directory,
not at one member.** Point it at the factory or at whichever file you happened
to open and `--edges` flags every edge on it, because the performing lines live
in the siblings you merged away — six flags on one node in one run, all from a
`sourceRef` that named a member instead of the subject.
