# Babysit PR

Drive a GitHub pull request through the "make it green" loop: inspect CI,
review bot feedback, fix real issues, push once per pass, and report whether
the PR is done, still waiting, or blocked.

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
/babysit-pr 123
/babysit-pr https://github.com/org/repo/pull/123
/babysit-pr can you get this PR green and review-clean?
```

## What it checks

- Current PR, branch, and dirty working-tree state.
- CI check status and focused failing logs.
- Review threads, submitted reviews, and top-level PR comments.
- Bot findings such as CodeRabbit comments, after verifying them against the
  actual code.
- Whether the next safe status is `DONE`, `NOT YET`, or `BLOCKED`.
