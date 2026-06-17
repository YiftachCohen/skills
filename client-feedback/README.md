# Client Feedback

Analyze client or end-user feedback with a bias toward verification before
implementation.

## What it does

This skill helps the agent:

- Translate and restate client feedback, including non-English feedback.
- Verify whether the reported issue is real against the active codebase.
- Classify the report as a bug, feature/change, misunderstanding, or UX issue.
- Produce either a root-cause-driven fix plan or a full impact analysis.
- Draft client-facing replies when the client is wrong or the recommendation
  needs explanation.

## Installation

Claude Code:

```bash
npx skills add YiftachCohen/skills --skill client-feedback
```

Codex can use the same `client-feedback/SKILL.md` directory when it is linked
or copied into the Codex skills folder.

## When it triggers

Use this when a user shares client feedback, support tickets, bug reports,
feature requests, complaints, or end-user messages.

## Safety stance

The skill should not assume the client is right. It first verifies the premise,
then decides whether to fix, plan, explain, or ask for more information.
