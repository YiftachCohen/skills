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

- Current PR, branch, and dirty working-tree state.
- CI check status and focused failing logs.
- Review threads, submitted reviews, and top-level PR comments.
- Bot findings such as CodeRabbit comments, after verifying them against the
  actual code.
- Whether the next safe status is `DONE`, `NOT YET`, or `BLOCKED`.
