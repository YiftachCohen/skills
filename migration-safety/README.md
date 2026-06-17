# Migration Safety

Review migration, backfill, and clean-start rebuild safety before code changes
or live data operations.

## Installation

Claude Code:

```bash
npx skills add YiftachCohen/skills --skill migration-safety
```

Codex can use the same `migration-safety/SKILL.md` directory when it is linked
or copied into the Codex skills folder.

## When to use

Use this when working on migrations, backfills, one-off data fixes, schema
drift, indexes, triggers, Postgres, MSSQL extraction, dry runs, reconciliation,
or questions like "will this still work on a clean rebuild?"

The skill pushes for idempotency proof, clean-start proof, dry-run impact counts,
and old-vs-new reconciliation before risky migration work proceeds.

## What it produces

- Risk classification.
- Source-of-truth files and migration entrypoints.
- Idempotency and rerun proof.
- Dry-run and reconciliation plan.
- Go/no-go recommendation.
