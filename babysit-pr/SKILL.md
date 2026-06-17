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
---

# Babysit PR

Drive a pull request toward this definition of done:

- CI checks are green.
- No actionable unresolved review threads remain.
- CodeRabbit or bot comments were verified against the code before being fixed.
- Real failures were root-caused, not guessed around.
- Any push is intentional and contains only the PR fixes.

This skill is intentionally pass-based. Each pass gathers current PR state,
handles what is actionable, pushes once if it changed code, and reports one of
three statuses: `DONE`, `NOT YET`, or `BLOCKED`. It is safe to rerun manually or
from a scheduler/loop.

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

Default to an **actionable pass**. Keep polling only if the user explicitly asks
to "watch", "loop", "babysit until green", or similar. Even then, avoid an
endless hidden loop:

- After each push, wait for new CI results instead of speculating.
- If the same check fails after two fix attempts, stop with `BLOCKED`.
- If a human product/architecture decision is needed, stop with `BLOCKED`.
- If all remaining checks are pending, report `NOT YET`.
- If all checks are green and no unresolved actionable review threads remain,
  report `DONE`.

Ask before destructive or high-risk actions:

- Force-push.
- Merge.
- Rebase with conflicts.
- Applying a wide migration/backfill/schema change.
- Resolving a review thread whose finding is real but the fix is product-level
  or architectural.

## Step 0 - Resolve repo and PR

Orient first:

```bash
git rev-parse --show-toplevel 2>/dev/null
git status --short
git branch --show-current
```

Resolve the PR:

- If `$ARGUMENTS` contains a PR number or URL, use it.
- Otherwise detect from current branch.
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

Classify:

- `success` - done.
- `pending` - still running or queued.
- `failure` - actionable.
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

Fetch focused logs:

```bash
gh run view <run-id> --log-failed
gh run view --job <job-id> --log
```

First rule out environment reality:

- Stale build cache or generated artifacts.
- Wrong workspace or wrong branch.
- Missing dependency after merge.
- Flake or external outage.
- Secret/config unavailable in CI.

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

1. Read the full comment and cited code.
2. Prefer the bot's "prompt for AI agents" section if present, but verify the
   claim yourself.
3. Decide:
   - **Real and small:** fix it.
   - **Real but product/architecture-level:** ask before changing.
   - **False positive:** explain why and resolve or mark addressed according to
     repo convention.
   - **Already fixed:** resolve with a short note if the repo expects one.

Do not blindly apply CodeRabbit suggestions. The value is in distinguishing real
findings from noise.

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

- All required CI checks are green.
- No unresolved actionable review threads remain.
- Local branch is pushed.

Include PR URL and a one-line summary.

### `NOT YET`

Use when:

- Checks are pending.
- You pushed fixes and CI needs to rerun.
- A rerun was triggered.
- There are known remaining actionable items for the next pass.

Include:

- Pending checks.
- Failing checks.
- Open actionable threads count.
- Whether another pass should run.

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

User passed: $ARGUMENTS
