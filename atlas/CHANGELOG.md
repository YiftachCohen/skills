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
needs re-deriving.

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
