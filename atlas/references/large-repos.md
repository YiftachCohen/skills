# Large repos (500+ real source files, measured)

Do NOT read files one by one — you will run out of context.

- **Skeleton first**: top-level layout, `package.json`/`pyproject.toml`/`go.mod`
  (dependencies reveal models, tools and integrations instantly), route
  manifests, `docker-compose.yml`, cron/queue config, CI workflows.
- **Useful greps**: provider SDKs (`@ai-sdk/`, `anthropic`, `openai`),
  `streamText|generateText|tool(`, `stripe|resend|twilio|slack`, DB clients,
  `cron|queue|worker` — hit locations show where each subsystem lives.
- **Fan out**, if subagents are available: 2–4 parallel investigations, e.g.
  entries+crons / AI usage / services+stores+integrations. Instruct each to
  return ONLY compact JSON (`{nodes, edges}` in the contract shape, with
  `sourceRef`s) — no prose report, no file excerpts; merge and dedupe yourself.
  Agree the shared ids up front: name the handful of nodes more than one of them
  will touch and fix each one's `kind` (`postgres`, not `neon-db` in one report
  and `db` in another). Reconciling id collisions afterwards costs more than the
  fan-out saves.
- **Write in a few appends** rather than one enormous Write call — a 200-node
  graph can exceed the output limit mid-JSON, and a truncated file means
  starting the write over.
- **Monorepo**: scan the package the user cares about, or map the whole fleet
  with each package as a `group` keeping only its externally-visible pieces.
  This is the one case where grouping by directory is right, and it overrides
  the "never by file layout" rule: in a monorepo the package boundary *is* the
  domain boundary — it is what the team deploys, versions and owns separately.
  Group by package only when the packages really are that independent; a
  `packages/` tree of one product's internal modules is file layout again.
- **Cross-package edges are where every error in a monorepo has come from.**
  Verify each one individually: resolve barrel re-exports to the symbol actually
  imported, and check you have not conflated two files with the same name in
  different packages.
- **The caps are the design**: a 3,000-file repo still maps to at most 40 top
  nodes because near-identical things merge into one ("14 CRUD routes") and file
  layout is never the map.
