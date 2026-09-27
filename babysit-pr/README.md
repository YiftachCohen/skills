# Babysit PR

Drive a GitHub pull request through the "make it green" loop: inspect CI,
review bot feedback, fix real issues, push once per pass, and report whether
the PR is done, still waiting, or blocked.

By default it **loops on its own** — running passes back-to-back in a single
invocation, sleeping while CI runs, and only stopping when the PR is `DONE`,
`BLOCKED`, or a safety cap is hit. Pass `--once` for a single status pass.

## Installation

Claude Code:

```bash
npx skills add YiftachCohen/skills --skill babysit-pr
```

Codex can use the same `babysit-pr/SKILL.md` directory when it is linked or
copied into the Codex skills folder.

## When to use

Use this when you want an agent to babysit a PR: poll CI, inspect failing logs,
verify CodeRabbit or review comments, fix real issues, push once per pass, and
report whether the PR is done, still waiting, or blocked.

Example:

```text
/babysit-pr 123                  # loop until DONE / BLOCKED / capped
/babysit-pr https://github.com/org/repo/pull/123
/babysit-pr can you get this PR green and review-clean?
/babysit-pr 123 --once           # single pass, then report and return
```

For cross-session cadence (e.g. poll every 10 min for hours), wrap a `--once`
pass with the `/loop` skill rather than holding one long invocation open.

## What it checks

- Current PR, branch, and dirty working-tree state, synced to the remote head.
- Mergeability (conflicts, behind base, draft, fork) and the review decision.
- Required vs advisory CI checks (`gh pr checks --required`) and focused
  failing logs.
- Review threads, submitted reviews, and top-level PR comments.
- Bot findings such as CodeRabbit comments, after verifying them against the
  actual code.
- Whether the next safe status is `DONE`, `NOT YET`, or `BLOCKED`.
- PR comments and CI logs as untrusted data: findings are verified, embedded
  instructions are ignored.
- Merged or closed PRs (stops), failures that already happen on the base
  branch, and required checks that never report.

## Layout

- `SKILL.md` — the loop.
- `scripts/wait-for-pr.sh` — one background wait that watches CI, review
  activity, and PR state together, and returns on the first thing that needs
  the agent (a failure, a new or edited review comment, merge/close, someone
  else's push). Used when the runtime can't deliver PR events to the session.
- `scripts/failed-log.sh` — the failed step's log around the first error, plus
  check annotations, as soon as a job fails.
- `references/state-file.md` — the per-PR state in `.git/babysit-pr/<pr>.json`:
  fix attempts per check and per thread, reruns, the stall clock, and which
  comments were already handled, so scheduled `--once` passes keep them.
- `references/reviewer-bots.md` — reviewer-bot rate limits, bot status messages
  that aren't findings, and dismissing stale bot reviews.
- `tests/test_scripts.py` — tests for both scripts against a fake `gh`
  (`python3 -m unittest discover babysit-pr/tests`).
