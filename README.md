# Agent Skills for Claude Code and Codex

Reusable agent skills for Claude Code and Codex. Each directory is a
self-contained workflow playbook with a `SKILL.md` file, optional references,
and optional eval prompts.

These skills are intentionally practical: they encode repeated engineering
workflows such as PR babysitting, client-feedback triage, and migration safety
reviews.

## Installation

Install an individual skill in Claude Code:

```bash
npx skills add YiftachCohen/skills --skill atlas
npx skills add YiftachCohen/skills --skill babysit-pr
npx skills add YiftachCohen/skills --skill client-feedback
npx skills add YiftachCohen/skills --skill loom-watch
npx skills add YiftachCohen/skills --skill migration-safety
npx skills add YiftachCohen/skills --skill walk-me-through
```

For Codex, expose the same skill directory in your Codex skills folder. The
shared source of truth is the `SKILL.md` file inside each skill directory.

## Skills

| Skill | Description |
|---|---|
| [atlas](./atlas) | Map a codebase into a local-only interactive architecture atlas with drill-down, flow tracing, blast radius, and no upload. |
| [babysit-pr](./babysit-pr) | Drive a GitHub pull request through failing CI, bot comments, review feedback, and final green status. |
| [client-feedback](./client-feedback) | Translate, verify, classify, and respond to client or end-user feedback before implementing changes. |
| [loom-watch](./loom-watch) | Convert Loom recordings into metadata, captions, sampled frames, and a timestamped review manifest. |
| [migration-safety](./migration-safety) | Review migrations, backfills, dry runs, idempotency, clean-start rebuilds, and reconciliation plans. |
| [walk-me-through](./walk-me-through) | Guide a reviewer through an unfamiliar, often agent-written pull request: foothold, one concrete scenario, the judgment that is theirs, and what the description got wrong. |

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

## License

MIT — see [LICENSE](./LICENSE).
