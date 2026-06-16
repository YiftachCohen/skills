# Bug analysis playbook

Load this only when classification = `bug` and verdict = `valid bug`. Otherwise stay in `SKILL.md`.

The point of this file: produce a **complete fix**, not a patch. A complete fix changes the code at the root cause and leaves the system in a state where the *class* of bug — not just this instance — is gone.

## Step 1 — Reproduce path

Walk the bug from entrypoint to failure site, in order. Show actual `file:line` references for each step. Don't summarize; trace.

```
1. User clicks <Component> at <path/to/component.tsx:42>
2. → fires server action <serverAction> at <app/actions/x.ts:88>
3. → calls <serviceFn> at <app/services/y.ts:120>
4. → which queries <dbCall> at <db/repositories/z.ts:54>
5. → fails because <specific condition> at <line>
```

If you can't get to line numbers, you haven't done the work yet — go look.

## Step 2 — Root cause vs proximate cause

Use the "five whys" but with a specific target: keep going until **you can describe a property of the system that, if changed, makes this whole class of bug impossible.** That's a root cause. Anything shallower is a proximate cause.

Examples of the difference:

| Symptom | Proximate cause | Root cause |
|---|---|---|
| Coupon code returns "invalid" | Validation function rejects empty string | The form passes empty string for "no code" instead of `null`; the validator was never spec'd for that case |
| App crashes on submit | Null deref in handler | A required field on the entity isn't enforced at the schema layer; client sometimes sends partial data and nothing else catches it |
| Wrong scholarship shown to user | Cache key collision | Cache key doesn't include user-tier, but the result depends on tier |

## Step 3 — Reject patches and name them

Before proposing the real fix, name the tempting patch out loud and explain why it's wrong. This is non-negotiable; it forces honesty.

Common patch shapes — call them out by name when you see one being tempting:
- **Error swallowing.** `try { ... } catch (e) { /* nothing */ }` or `catch (e) { return null }` to make the symptom go away.
- **Special-case branch.** `if (user.id === 'this_one_customer') ...` or `if (env === 'prod') skip(...)`.
- **UI-only fix for a data problem.** Hiding the broken data instead of fixing the data path.
- **Re-render workaround.** Adding a `key={Date.now()}` or extra `useEffect` to mask a stale-state issue rooted in the data flow.
- **Defensive fallback masking the bug.** `value ?? defaultValue` where the real question is "why is value missing here".
- **Migration without backfill.** Adding a new required column and only handling new rows.

State the patch and why it's wrong before describing the real fix:

> A patch would be to add `if (!coupon) return { valid: true }` in the validator, but that hides the actual problem (the form submits empty strings instead of null) and will misfire whenever the form is reused elsewhere.

## Step 4 — Complete fix

Describe the actual fix. It usually has multiple components:

1. **The change at the root** — what file, what function, what behavior change. Include a code sketch if useful.
2. **Adjacent paths to update** — anywhere else that depends on the same root assumption.
3. **Data fix** — if existing rows are corrupted, describe the migration/backfill (and how to verify it ran).
4. **Regression test** — exactly what test to add, and at which layer (unit / integration / e2e). The test should fail without the fix.
5. **Type/schema tightening, if applicable** — make the bug structurally impossible to reintroduce.

## Step 5 — Blast radius and rollback

- **Who/what is affected?** Existing users? Specific roles? Data already in production? In-flight requests?
- **Is it backwards compatible?** If not, what's the migration sequence? (e.g. deploy schema → backfill → deploy code.)
- **Rollback plan.** How do you undo this safely if it goes wrong? If the fix involves a destructive migration, double-check.
- **Monitoring.** What log/metric/dashboard tells you the fix is working in production?

## Step 6 — Apply the fix

For a `valid bug`, implement the complete fix from Step 4 — don't leave it as a plan.

1. **Risk gate first.** If the fix is destructive or wide-blast-radius (per Step 5: non-backfilled migration, schema change on a populated table, auth/permission change, billing path, mass deletion/update), stop and get a go/no-go via `AskUserQuestion` before editing. Otherwise proceed.
2. **Make the root-cause change** in the file(s) Step 4 named — matching the surrounding code's idiom, naming, and conventions (see `CLAUDE.md`/`AGENTS.md`).
3. **Update the adjacent paths** that share the same root assumption.
4. **Add the regression test** Step 4 specified, at the layer it specified. It must fail without the fix.
5. **Run cheap, relevant checks** — typecheck and the single test file you added/touched (find the commands in `CLAUDE.md`/`AGENTS.md`). Don't run the full suite/build unless warranted.
6. **Report honestly.** List edited files with `file:line`, the test added, and check results. If a check fails or the fix is partial, say so plainly with the output — don't claim done.

Skip data migrations/backfills as live actions unless explicitly told to run them; describe them and flag for the user.

## Output for the SKILL.md `## Analysis` section

Use this structure:

```markdown
### Reproduce path
1. ...
2. ...

### Root cause
<one paragraph; ends with "the property of the system that needs to change is X">

### Patches to reject
- <patch shape>: <why it's wrong>

### Complete fix
1. **Root change:** <file:line> — <what to do>
2. **Adjacent updates:** <files / locations>
3. **Data fix:** <migration/backfill or "none needed">
4. **Regression test:** <where, what it asserts>
5. **Schema/type tightening:** <or "n/a">

### Blast radius & rollback
- Affected: <users / data>
- Compatibility: <forward/backward notes>
- Rollback: <plan>
- Monitoring: <signal to watch>
```
