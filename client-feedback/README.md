# Client Feedback Skill

A Claude Code skill for analyzing client or end-user feedback with a bias toward verification before implementation.

## What it does

This skill helps the agent:

- Translate and restate client feedback, especially Hebrew feedback
- Verify whether the reported issue is real against the active codebase
- Classify the report as a bug, feature/change, misunderstanding, or UX issue
- Produce either a root-cause-driven fix plan or a full impact analysis
- Draft client-facing replies when the client is wrong or the recommendation needs explanation

## Installation

```bash
npx skills add YiftachCohen/skills --skill client-feedback
```

## When it triggers

Use this when a user shares client feedback, support tickets, bug reports, feature requests, complaints, or end-user messages, especially in Hebrew.
