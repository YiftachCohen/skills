# Agent Skills for Claude Code and Codex

Reusable agent skills for Claude Code and Codex. Each directory is a
self-contained workflow playbook with a `SKILL.md` file, optional references,
and optional eval prompts.

These skills are intentionally practical: they encode repeated engineering
workflows such as PR babysitting, client-feedback triage, migration safety
reviews, and multi-agent orchestration.

## Installation

Install an individual skill in Claude Code:

```bash
npx skills add YiftachCohen/skills --skill babysit-pr
npx skills add YiftachCohen/skills --skill client-feedback
npx skills add YiftachCohen/skills --skill migration-safety
npx skills add YiftachCohen/skills --skill ruflo-orchestrator
```

For Codex, expose the same skill directory in your Codex skills folder. The
shared source of truth is the `SKILL.md` file inside each skill directory.

## Skills

| Skill | Description |
|---|---|
| [babysit-pr](./babysit-pr) | Drive a GitHub pull request through failing CI, bot comments, review feedback, and final green status. |
| [client-feedback](./client-feedback) | Translate, verify, classify, and respond to client or end-user feedback before implementing changes. |
| [migration-safety](./migration-safety) | Review migrations, backfills, dry runs, idempotency, clean-start rebuilds, and reconciliation plans. |
| [ruflo-orchestrator](./ruflo-orchestrator) | Use Ruflo MCP tools for multi-agent coordination, consensus review, memory, and workflow orchestration. |

## Repository Scope

This public repository is for reusable, non-sensitive skills. Do not commit
customer-specific names, private project workflows, internal URLs, credentials,
database details, or real support transcripts. Keep that material in a private
repository or an ignored local skills folder.

## Skill Layout

```text
skill-name/
  SKILL.md
  README.md
  evals/
```

`SKILL.md` is the file the agent reads when the skill triggers. `README.md`
explains the skill for humans. `evals/` contains lightweight test prompts for
future tuning.
