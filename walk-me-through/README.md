# Walk me through

Guide a reviewer through a pull request they do not understand, usually one a
teammate opened with a coding agent, until they know enough to have an opinion
without reading every line.

The walkthrough opens with a foothold written from the code, not the
description: what the system does before and after, where the weight of the
diff sits, the one decision that matters, and where the PR description is
accurate, incomplete, or wrong. It then follows one concrete scenario through
the change, explains the existing code the change depends on, separates
understanding from agreement, and closes with what was covered, what was not,
and the judgment that is still yours.

## Installation

Claude Code:

```bash
npx skills add YiftachCohen/skills --skill walk-me-through
```

Codex can use the same `walk-me-through/SKILL.md` directory when it is linked
or copied into the Codex skills folder.

## When to use

Use this when you have been asked to review a PR you have no context on and
the description is long, confident, and possibly wrong.

```text
/walk-me-through 123
/walk-me-through https://github.com/org/repo/pull/123
/walk-me-through I got assigned this PR and have no idea what it does
/walk-me-through is the description on #123 actually accurate?
```

During the walk you can say "I know this part", "back up", "what's a ...?",
"why does it ...?", "show me the implementation", "skip to the risky bit",
"quick", or "everything", and the walkthrough adapts.

## What it does

- Reads the implementation and the surrounding code before saying anything.
- Checks every claim in the description against the diff and lists the
  changes the description never mentions.
- Recovers the original intent from the issue, branch, and commits, and
  flags scope drift.
- Sorts files into skim and read, and orders the read set by cause rather
  than alphabet.
- Runs a checklist of agent-specific failure modes and anchors each hit to a
  line.
- Distinguishes what the code does, what it infers, and what it could not
  confirm.
- Drafts review comments to a local file on request. It never posts to
  GitHub and never recommends approve or reject unless you ask.
