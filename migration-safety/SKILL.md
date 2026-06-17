---
name: migration-safety
description: |
  Migration and backfill safety review for MSSQL to Postgres
  work. Use this skill whenever the user mentions migrations, backfills,
  idempotency, dry runs, clean-start rebuilds, "delete everything and rerun",
  Neon, MSSQL, Postgres, schema drift, one-off data fixes, indexes, triggers,
  reconciliation, or asks "will this work next migration run?". This skill should
  trigger before implementing or running risky migration changes. It forces a
  dry-run impact check, idempotency proof, source/target reconciliation, rerun
  safety verdict, and clear go/no-go recommendation.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - AskUserQuestion
---

# Migration Safety

Use this skill to keep migration and backfill work boring in the best possible
way. The user often cares less about "can this script run once?" and more about:

- Will it survive a clean database rebuild?
- Is it idempotent if rerun?
- Did it change the right rows and only the right rows?
- Does the app repo and migration repo agree about the schema and behavior?
- Can we tell the client or partner, in plain language, what is safe now?

The skill is deliberately conservative. It should slow down destructive or
wide-blast-radius work just enough to prevent expensive mistakes, without
turning every small migration into a committee meeting.

## Runtime compatibility

Map tool names to the current runtime. Use available file search, file read,
shell, edit, browser, and user-question tools.

Prefer:

- `rg`/Grep for code and SQL search.
- Project docs (`CLAUDE.md`, `AGENTS.md`, `agent.md`, README) before guessing
  commands.
- Read-only verification scripts before live writes.
- Existing migration helpers and scripts over ad hoc SQL.

## Autonomy

Default to **analysis first**.

You may implement migration-code changes when they are non-destructive and
inside the repo. You must ask for confirmation before:

- Running a live backfill or migration against production/staging data.
- Deleting, truncating, or rebuilding any database.
- Updating many existing rows.
- Changing auth, subscription, billing, or user identity data.
- Adding/removing schema objects that existing deployed code may depend on.
- Force-pushing or merging after migration work.

If the user explicitly says "run it", still do the safety summary first unless
the safety summary already exists in the current conversation.

## Phase 0 - Orient

Start with a tight project snapshot:

```bash
git rev-parse --show-toplevel 2>/dev/null
git status --short
ls agent.md CLAUDE.md AGENTS.md README.md 2>/dev/null
```

Read the relevant project instructions. Identify whether you are in:

- The migration repo.
- The product app repo.
- A Conductor workspace.
- The wrong repo for the requested action.

If the request spans repos, state which repo owns each part:

- Migration repo: extraction, transform, load, clean-start rebuild behavior,
  one-off backfills, schema sync helpers.
- App repo: UI/API behavior, Drizzle schema, runtime queries, admin exports,
  app-level validation and tests.

## Phase 1 - Classify the migration work

Pick the primary class:

- **Schema change** - tables, columns, indexes, triggers, functions, constraints.
- **Data migration** - transforms old-system data into new-system rows.
- **Backfill** - fixes existing target rows after a bug or missing invariant.
- **One-off operational fix** - intended to run once against current data.
- **Verification only** - answer whether current data/code is correct.
- **Cross-repo contract** - migration output must satisfy app repo schema/logic.

Also mark risk:

- **Low** - read-only, tests only, docs only, local-only.
- **Medium** - migration code change, deterministic and covered by dry run.
- **High** - bulk data writes, destructive rebuild, schema change on populated
  data, auth/subscription/user identity, or anything hard to undo.

## Phase 2 - Find the real source of truth

Do not trust memory, filenames, or agent summaries. Find the actual code and
data path.

Search for:

- Migration step registration and execution order.
- Source-table extraction query.
- Transform function.
- Target upsert/insert/update.
- Existing indexes/triggers/functions.
- App code that reads the resulting data.
- Tests or fixtures that already encode the invariant.

For each important object, record `file:line` or the function/script name.

If the user asks whether a past migration "ran", inspect migration logs, marker
tables, commit history, or target data where available. Do not infer from the
presence of a file alone.

## Phase 3 - Prove idempotency and clean-start safety

Answer these questions explicitly:

- **Idempotency:** What happens if the step runs twice against the same target?
  Which key/constraint/upsert prevents duplicates?
- **Clean start:** If the target DB is deleted and rebuilt from scratch, where
  does this data/object get created?
- **Partial rerun:** If the previous run failed halfway, can rerun recover?
- **Ordering:** Does this depend on a prior step, table, index, trigger, or
  backfill? Is that dependency encoded or accidental?
- **Existing data:** Does the change handle rows already in Neon, or only future
  rows?
- **App compatibility:** Does deployed/current app code tolerate both old and
  new states during rollout?

If you cannot prove one, say so. The right output is "not proven yet" plus the
smallest verification step, not optimistic language.

## Phase 4 - Dry-run and reconciliation plan

Before any write, design or run a read-only dry-run whenever possible.

The dry-run should include:

- Impact count: how many rows would insert/update/delete.
- Sample affected rows: enough to catch wrong joins and bad assumptions.
- Duplicate/conflict check: target keys that would collide.
- Null/empty check: required target fields that would be missing.
- Old-vs-new reconciliation: source count, transformed count, target count.
- Invariant check: the app-facing property that must be true after migration.

Prefer writing a temporary read-only script if the repo has established DB
helpers. Put throwaway probes in `/tmp` or an ignored scratch area when
possible. If a probe lives inside the repo, remove it before finalizing unless
it is generally useful, and call out any intentionally kept artifact.

For date/time fields, explicitly check timezone/day-shift risk. A one-day drift
in exports or migrated dates is high severity for this product.

## Phase 5 - Implementation rules

When implementing:

- Match existing migration patterns, naming, logging, batching, and transaction
  style.
- Make reruns safe by construction: stable keys, upserts, uniqueness checks, or
  explicit skip logic.
- Put durable behavior in the migration pipeline, not only in a one-off script,
  when the user plans to rebuild the database.
- Add a one-off backfill only when current data needs repair before the next
  full migration.
- Keep app repo schema/types in sync when migration output changes the runtime
  contract.
- Add or update tests around the invariant, not just the implementation detail.

Do not hide a data problem with UI filtering unless the product intentionally no
longer wants that data visible.

## Phase 6 - Verification after changes

Run the cheapest relevant checks from project docs. Common useful checks:

- Unit test for the changed transform/service.
- Migration dry run for the affected step.
- Typecheck/lint when schema or types changed.
- Read-only reconciliation query after a live run, if the user approved a live
  run.

If a command requires credentials or live DB access and is unavailable, provide
the exact command/query to run and what result to expect.

## Output format

Use this structure for substantial migration work:

```markdown
## Migration safety review

**Scope:** <what is being changed or verified>
**Repo(s):** <migration repo / app repo / both>
**Risk:** low | medium | high
**Class:** schema | data migration | backfill | one-off | verification | cross-repo contract

## Source of truth
- <file:line or script/function> - <what it owns>

## Safety verdict
**Go/no-go:** go | go after fixes | no-go | needs live confirmation
**Why:** <short decisive explanation>

## Idempotency and rerun proof
- Idempotency: <proven by key/upsert/etc, or not proven>
- Clean-start rebuild: <proven path, or gap>
- Partial rerun: <safe/unsafe/unknown>
- Ordering/dependencies: <encoded or accidental>

## Dry-run / reconciliation
- Impact count: <number or query to get it>
- Sample check: <what was inspected>
- Invariants: <what must be true after>
- Date/time risk: <checked or n/a>

## Changes applied
<omit if no edits; otherwise files changed, tests/checks run>

## Next action
<run it / fix these gaps / ask user / tell client / open PR>
```

For quick questions, keep it shorter, but always include:

- verdict,
- idempotency/clean-start answer,
- evidence,
- next action.

## Red flags

Stop and ask before proceeding if you see:

- A migration step that only exists as an untracked local script.
- Current data is correct but the clean-start path would still regenerate bad
  data.
- Backfill fixes production but migration pipeline remains broken.
- App repo expects a Drizzle schema object that the migration repo creates only
  as raw SQL, or vice versa, and the mismatch matters.
- A destructive command is being suggested to "test" something that read-only
  queries could verify.
- A temporary probe or generated reconciliation output is staged with the real
  migration change.
- The user asks "just delete the user/data" and the affected tables are not fully
  understood.

User passed: $ARGUMENTS
