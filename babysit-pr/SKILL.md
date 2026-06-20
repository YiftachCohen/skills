---
name: babysit-pr
description: |
  Babysit a GitHub pull request until it is green and review-clean. Use this
  skill whenever the user says "babysit this PR", "green PR loop", "get CI
  green", "watch the PR", "land this PR", "fix CI and CodeRabbit", "drive the
  PR to green", "keep checking until it passes", or asks to handle failing PR
  checks/review comments. This skill is the portable Claude/Codex source of
  truth for the PR loop: resolve the PR, poll CI and unresolved review threads,
  root-cause failures, verify review comments before changing code, push once per
  pass, and report DONE / NOT YET / BLOCKED. It should trigger even if the user
  only says "PR is red" or "can you babysit it?".
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - AskUserQuestion
  - Skill
  - Agent
---

# Babysit PR

Drive a pull request toward this definition of done:

- CI checks are green.
- No actionable unresolved review threads remain.
- CodeRabbit or bot comments were verified against the code before being fixed.
- Real failures were root-caused, not guessed around.
- Any push is intentional and contains only the PR fixes.

The unit of work is a **pass**: gather current PR state, handle what is
actionable, push once if it changed code, and classify the result as `DONE`,
`NOT YET`, or `BLOCKED`. A single pass is the building block — but babysitting
means **staying with the PR until it lands**, so by default this skill runs
passes back-to-back in one invocation, sleeping between them while CI runs,
and only returns to the user on a terminal status (`DONE` / `BLOCKED`) or a
safety cap. See **Loop procedure** below. Each pass is still self-contained and
safe to rerun manually or from an external scheduler.

## Runtime compatibility

Use the tools available in the current runtime.

- In Claude Code, prefer `gh` for PR checks, logs, and review thread GraphQL.
- In Codex, prefer the GitHub connector tools when available for PR metadata,
  comments, diffs, checks, and review threads; use `gh` when the connector lacks
  thread resolution or logs.
- If neither GitHub connector nor `gh` is authenticated, report `BLOCKED` with
  the exact missing access.

Use existing project skills when they exist:

- If no PR exists yet and the user wants one, use `ship` or the repo's
  established PR creation workflow after confirming scope. Once the PR exists,
  continue this babysitting pass instead of stopping.
- If the repo has a more specific CI/debug skill, use its root-cause workflow for
  the failing check, then return here for the PR loop.
- If a review comment is about migration/data correctness, apply
  `migration-safety` principles before fixing.

## Autonomy and stop conditions

**Loop by default.** Babysitting means owning the PR until it lands, so keep
running passes within this single invocation until you reach a terminal status —
do not hand a `NOT YET` back to the user and wait for them to re-invoke. Run
single-pass-and-return only when the user asks for a one-off (`--once`, "just
check it", "status only").

A pass ends the loop (returns to the user) only on a **terminal** status:

- `DONE` — all required CI checks green and no unresolved actionable review
  threads. Return.
- `BLOCKED` — auth/access missing, the same check failed after two fix attempts,
  a human product/architecture decision is needed, or a risky operation needs
  approval. Return and ask.

`NOT YET` is **not** terminal in loop mode — it means "more work is in flight,
continue the loop." Concretely:

- After a push, or while checks are pending, **wait** (see Loop procedure) and
  re-poll instead of speculating or returning.
- When fresh state shows new failures or review threads, run another pass.
- Only convert a long stall into a return if you hit a safety cap.

**Safety caps (hard limits, to prevent an endless loop):**

- Max 12 passes per invocation. On reaching it, return `NOT YET` with a summary
  and an explicit "re-invoke to continue" note.
- Same check failing after two distinct fix attempts → `BLOCKED` (never a third
  guess at the same failure).
- Total in-loop wait exceeding ~30 min with no state change → return `NOT YET`
  (CI may be queued/stuck; let the user decide).
- A genuine flake/outage: rerun the job once, then if it still fails treat it as
  a real failure (root-cause) or `BLOCKED`, not an infinite rerun.

Ask before destructive or high-risk actions:

- Force-push.
- Merge.
- Rebase with conflicts.
- Applying a wide migration/backfill/schema change.
- Resolving a review thread whose finding is real but the fix is product-level
  or architectural.

## Loop procedure

This is the outer loop that wraps Steps 0–5. Run it within the single
invocation — do not return between iterations unless a pass is terminal or a cap
is hit.

1. Run Step 0 once to resolve the repo/PR (no need to re-resolve every iteration).
2. **Pass loop** — repeat until terminal or capped:
   a. Steps 1–4: poll fresh state, root-cause failures, verify review threads,
      apply fixes, push at most once.
   b. Classify per Step 5.
   c. If `DONE` or `BLOCKED` → break and return.
   d. If `NOT YET` → **block until state changes, then loop** (do not return,
      and do NOT poll by waking the model up repeatedly — see Token discipline).
      Hand the waiting to a single blocking shell call that sleeps and re-checks
      `gh` itself, returning only when something actionable appears or the window
      closes. Then start the next pass at step (a) on the fresh state.
3. On break, emit the Output-format report once with the terminal status.

### Token discipline (this loop runs on the user's main model — keep it cheap)

The expensive resource is **model turns over a growing context**, not reasoning.
Two rules keep a 12-pass loop affordable:

**1. Never spend a model turn on waiting.** A `sleep` followed by a fresh poll is
a full model turn that did nothing. Collapse the entire wait into ONE blocking
Bash call that loops internally and returns only when the CI state is actionable
(or the window expires). Example (tune `PR`, interval, and window):

```bash
# REQUIRED = JSON array of required check names from Step 1's branch-protection
# query, e.g. REQUIRED='["test","lint","typecheck","build"]'. Filtering to it is
# what keeps advisory checks from waking the loop. (seq/sleep reflect --interval.)
# Blocks in-shell; returns when any required check fails OR all required checks
# finish, or after ~10 min. One tool call replaces ~10 idle model turns.
for i in $(seq 1 10); do
  states=$(gh pr checks "$PR" --json state,name 2>/dev/null)
  # stop early on the first REQUIRED failure (actionable now)
  [ "$(echo "$states" | jq --argjson req "$REQUIRED" '[.[]|select(.name as $n|$req|index($n))|select(.state=="FAILURE" or .state=="ERROR")]|length')" -gt 0 ] \
    && { echo "ACTIONABLE: required failure"; break; }
  # stop when no REQUIRED check is still running/queued (terminal — go classify)
  [ "$(echo "$states" | jq --argjson req "$REQUIRED" '[.[]|select(.name as $n|$req|index($n))|select(.state=="PENDING" or .state=="IN_PROGRESS" or .state=="QUEUED")]|length')" -eq 0 ] \
    && { echo "ACTIONABLE: all required settled"; break; }
  sleep 60
done
gh pr checks "$PR"   # one final snapshot the model reads
```

For waits beyond the bash ceiling, run it as a background command and act on the
completion notification — still no idle model turns. Respect the ~30 min
no-change cap before returning `NOT YET`.

**2. Read heavy things in an isolated subagent, not the main thread.** Failing
CI logs and the files a review thread cites are large and would otherwise sit in
context for every remaining pass (context grows each pass → later turns cost
more). Delegate the *reading* to a subagent that returns a compact finding; the
main driver keeps the *decisions*. See Step 2 and Step 3.

Cheap complements: pipe logs through `grep`/`tail` before they hit context, and
prefer `git diff --stat` before a full diff.

Notes:
- Count fix attempts **per check**: a given failing check gets at most two
  distinct fix attempts across the whole loop before it becomes `BLOCKED`.
- A newly pushed commit resets CI — always re-poll after the wait rather than
  trusting pre-push state.
- Narrate briefly between iterations (one line: "pass N: pushed fix for X,
  waiting on CI") so the user can follow a long-running loop.

### Cross-session scheduling (optional)

The in-invocation loop above covers a normal review cycle. If the user wants
babysitting to survive across sessions or run on a fixed cadence (e.g. "check
every 10 min for the next few hours"), use the `/loop` skill to schedule
recurring `/babysit-pr <pr> --once` passes instead of holding one very long
invocation open.

## Step 0 - Resolve repo and PR

Orient first:

```bash
git rev-parse --show-toplevel 2>/dev/null
git status --short
git branch --show-current
```

Resolve the PR and mode:

- If `$ARGUMENTS` contains a PR number or URL, use it.
- Otherwise detect from current branch.
- Mode flags in `$ARGUMENTS`: `--once` (or "just check"/"status only") → run a
  single pass and return. Absent any such flag, default to the **loop** (run
  passes until terminal or capped, per Loop procedure). An optional interval
  like `--interval 90s` overrides the default wait between polls.
- If no PR exists, do not stop too early:
  - If the branch is clean and has commits ahead of the base branch, summarize
    the ahead commits/diff and ask: "No PR exists yet. Create one and continue
    babysitting it?"
  - If the user already asked to create/ship/open a PR, create it through the
    repo's established workflow, then continue with Step 1 in the same pass.
  - If the working tree is dirty, review the diff before offering PR creation so
    unrelated local work does not get swept into the PR.
  - If there are no commits ahead of the base branch, report `BLOCKED` with the
    exact missing prerequisite.

Useful `gh` commands:

```bash
gh pr view --json number,url,headRefName,baseRefName,headRepositoryOwner
gh repo view --json owner,name
gh repo view --json defaultBranchRef
git log --oneline "origin/$BASE_BRANCH..HEAD"
git diff --stat "origin/$BASE_BRANCH...HEAD"
```

Capture:

- Repository.
- PR number and URL.
- Head branch.
- Base branch.
- Current local branch and dirty status.

If local branch does not match PR head, say so before editing.

## Step 1 - Poll current state

Gather all status before acting.

### CI checks

Use whichever is available:

```bash
gh pr checks "$PR" --json name,state,link,bucket,description,startedAt,completedAt
gh run list --branch "$HEAD_BRANCH" --limit 10
```

**Separate required checks from advisory ones first.** `gh pr checks` mixes
merge-gating checks with informational ones (preview-comment bots, coverage
posts, etc.). Only the **required** checks gate `DONE` and are worth looping on.
Fetch the required set from branch protection once per invocation:

```bash
gh api "repos/$OWNER/$REPO/branches/$BASE_BRANCH/protection/required_status_checks" \
  --jq '.contexts // (.checks[].context)' 2>/dev/null
```

If branch protection isn't readable (permissions/none configured), fall back to
treating the conventional CI checks as gating and clearly label anything you
can't classify.

Classify each check:

- `success` - done.
- `pending` - still running or queued.
- `failure` - actionable **if required**; if advisory, report it but do not loop
  on it or block `DONE`.
- `cancelled/skipped` - inspect context before treating as failure.

### Review threads and comments

Collect unresolved review threads, especially CodeRabbit or other bot threads.
GraphQL is often needed because REST does not expose thread resolution state:

```bash
gh api graphql -f query='
query($owner:String!,$repo:String!,$pr:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$pr){
      reviewDecision
      reviewThreads(first:100){ nodes{
        id isResolved path line
        comments(first:20){ nodes{ id body author{login} url } }
      }}
    }
  }
}' -f owner="$OWNER" -f repo="$REPO" -F pr="$PR"
```

Keep threads that are unresolved and actionable. Ignore already-addressed
threads only after confirming the cited code has the fix.

Also inspect top-level PR comments and submitted reviews. Some bots post a
status summary or actionable finding without creating a review thread.

```bash
gh pr view "$PR" --json comments,reviews,reviewDecision
gh pr view "$PR" --comments
```

Treat pure status summaries as non-actionable. Treat concrete file/line
findings as review work even if they are not threaded.

## Step 2 - Handle failing CI

For each failing check, find the real cause before editing.

**Triage large logs in a subagent (context isolation).** A failing job log can
be tens of KB; reading it inline parks all that text in the main thread for
every remaining pass. Instead, spawn an `Agent` (the `Explore` type, or a
`general-purpose` agent on a cheaper model like `sonnet` for plain log triage)
to read the log and the few cited files and return ONLY a compact finding:

```text
Read the failing CI log and any files it points at. Return strictly:
{ check, root_cause, file:line, minimal_fix, confidence, is_flake_or_env }
Do not propose large refactors; identify the smallest real cause.
```

The main driver keeps the *decision* (whether to apply the fix, dispute it, or
rerun) — only the bulky *reading* is offloaded. For a small/obvious log, just
read it inline; a subagent has fixed spin-up overhead and isn't worth it for a
few lines. Fetch logs trimmed when reading inline:

```bash
gh run view <run-id> --log-failed | grep -iE 'error|fail|✗|panic' | tail -80
gh run view --job <job-id> --log | tail -120
```

First rule out environment reality:

- Stale build cache or generated artifacts.
- Wrong workspace or wrong branch.
- Missing dependency after merge.
- Flake or external outage.
- Secret/config unavailable in CI.
- Branch out of date with base (a long loop can drift). If a required
  "up-to-date" check fails and the update merges cleanly, update the branch; if
  it would conflict, stop and ask (rebase-with-conflicts is in the ask-first
  list).

If it is likely a flake or external outage, rerun the failed job/check once if
allowed, then report `NOT YET`. Do not patch code to satisfy a flaky symptom.

If it is a real failure:

- Trace to the smallest code/test/config cause.
- Apply the smallest fix that matches project conventions.
- Add/update a test when the failure reveals missing coverage.
- Run the relevant local check if available and cheap.

Keep one todo per failing check so none silently disappear.

## Step 3 - Handle review comments

For each unresolved actionable thread:

1. Read the full comment and cited code. When a thread (or a batch of them)
   requires reading several files to judge, delegate the *verification read* to
   an `Agent` (`Explore`) that returns a compact verdict per thread —
   `{ thread, claim, verified_against_code, real_or_false_positive, evidence:file:line }`
   — so the cited files don't accumulate in the main context across passes. The
   main driver still makes the fix/dispute call. Skip the subagent for a
   one-line, single-file comment you can confirm directly.
2. Prefer the bot's "prompt for AI agents" section if present, but verify the
   claim yourself.
3. Decide:
   - **Real and small:** fix it.
   - **Real but product/architecture-level:** ask before changing.
   - **False positive:** explain why and resolve or mark addressed according to
     repo convention.
   - **Already fixed:** resolve with a short note if the repo expects one.

4. **Resolve what you fixed.** This applies to any reviewer thread — CodeRabbit,
   Copilot, or a human — not one specific bot. Once the fix is pushed and visible
   in the diff, mark that thread resolved so the loop can actually reach `DONE`
   (an unaddressed fix that leaves the thread open never clears). Reply-then-
   resolve via GraphQL with the thread `id` from the Step 1 query:

   ```bash
   gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -f id="$THREAD_ID"
   ```

   Only resolve threads your push genuinely addressed; for a false positive,
   leave a one-line reply explaining why instead of silently resolving.

Do not blindly apply bot suggestions (CodeRabbit, Copilot, or otherwise). The
value is in distinguishing real findings from noise.

For data, migration, permissions, auth, subscription, billing, export, or
date/time findings, require stronger evidence than a code skim:

- Read-only DB check if available.
- Generated file inspection for export findings.
- Browser verification for UI findings.
- Migration idempotency/clean-start proof for migration findings.

## Step 4 - Push once per pass

If code changed:

```bash
git status --short
git diff --stat
git diff
```

Before staging, scan for unrelated files, generated output, secrets, `.env`,
debug scripts, or files from another task.

Then stage intentionally. `git add -A` is acceptable only after checking the
status list.

Use a concise commit message tied to the PR loop, for example:

```bash
git add <intended files>
git commit -m "fix: address PR checks and review feedback"
git push
```

Do not push multiple tiny commits in one pass unless the repo convention demands
it.

## Step 5 - Report loop status

End every pass with exactly one status marker.

### `DONE`

Use only when:

- All **required** CI checks are green (see Step 1 — advisory checks don't gate).
- No unresolved actionable review threads remain.
- Local branch is pushed.
- No reviewer (bot or human) is mid re-review of your latest push. A push can go
  green on CI before the reviewer re-runs and posts fresh threads, so if the most
  recent commit hasn't been reviewed yet, treat it as `NOT YET` and let the loop
  wait one more cycle rather than declaring victory early.

Include PR URL and a one-line summary. `DONE` means **ready to merge**, not
merged — even when the user said "land this PR." Merging is a high-risk action
(see above): offer it or enable auto-merge only when the user explicitly asked
to merge, otherwise stop at green-and-clean.

### `NOT YET`

`NOT YET` describes the result of one pass: checks are pending, you pushed fixes
and CI must rerun, a rerun was triggered, or known actionable items remain.

In the default loop, `NOT YET` does **not** return to the user — it triggers the
wait-and-re-poll step of the Loop procedure and continues to the next pass. You
only surface `NOT YET` to the user when:

- The user asked for a single pass (`--once` / status-only), or
- You hit a safety cap (max passes, or the ~30 min no-change wait).

When you do surface it, include:

- Pending checks.
- Failing checks.
- Open actionable threads count.
- Whether to re-invoke to continue.

### `BLOCKED`

Use when:

- Auth/access is missing.
- Same failure repeated after two fix attempts.
- Human decision needed.
- Risky operation requires approval.
- Wrong workspace/branch prevents safe edits.

Include the specific question or missing access.

## Output format

Use this structure:

```markdown
## PR
<PR URL or "not found">

## Current state
- Checks: <green/pending/failing summary>
- Review threads: <count and type>
- Local state: <clean/dirty/branch mismatch>

## Actions this pass
- <what you inspected/fixed/reran/resolved>

## Verification
- <local checks/logs/connector evidence>

## Next
DONE | NOT YET | BLOCKED
<one-line reason and next pass guidance>
```

For very quick status requests, keep it shorter but still end with `DONE`,
`NOT YET`, or `BLOCKED`.

## Common traps

- Treating pending CI as failure and making speculative edits.
- Trusting bot comments without reading the cited code.
- Fixing a symptom from logs while missing the test's actual assertion.
- Staging unrelated local files.
- Resolving review threads before the fix is visible in the diff.
- Forgetting that a newly pushed commit restarts CI and changes the current
  state.
- Stopping at `BLOCKED` just because no PR exists when the clean branch is
  clearly ready for PR creation.
- Looping forever when the same failure keeps coming back.
- Polling by waking the model every interval (`sleep` then a fresh turn) instead
  of one blocking shell call — each idle wake is a wasted model turn over a
  growing context.
- Dumping full CI logs / diffs into the main thread when a subagent could return
  a compact finding — and the inverse: spinning up a subagent for a two-line log
  where inline reading is cheaper than the spawn overhead.

User passed: $ARGUMENTS
