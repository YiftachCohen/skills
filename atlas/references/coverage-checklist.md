# Coverage checklist — what the inventory must account for

Run these against the target repo and put every hit in `.atlas/inventory.md`. A
category with no hits gets one line saying so; silence is not the same as none.
Adapt the extensions and grep syntax to the repo's languages.

```bash
# dependencies — group them (30 UI packages = 1 line)
cat package.json pyproject.toml go.mod Cargo.toml Gemfile 2>/dev/null

# env vars — flag any that change behaviour the map draws
grep -rnE 'process\.env|os\.environ|os\.Getenv|ENV\[' --include='*.*' . | head -60
cat .env.example 2>/dev/null

# entry points and route directories
git ls-files | grep -E '(^|/)(routes?|api|pages|app|cmd|handlers)/' | head -40

# scheduled work — application code AND CI
grep -rnE 'schedule:|cron|@daily|setInterval|celery|APScheduler' \
  .github/ .gitlab-ci.yml vercel.json 2>/dev/null

# schemas and the tables they define
git ls-files | grep -E 'schema|migration|models?\.' | head -30

# exit codes — check the success branch can actually return non-zero
grep -rnE 'sys\.exit|os\.Exit|process\.exit|return [1-9]' --include='*.*' . | head -30

# the largest non-test source files — a category sweep skips these silently
git ls-files '*.py' '*.ts' '*.tsx' '*.go' | grep -vE 'test|spec|fixtures' \
  | xargs wc -l | sort -rn | head -30

# the AI layer, if any
grep -rnE '@ai-sdk|anthropic|openai|generateText|streamText|tool\(|@mcp\.tool' . | head -40
```

## Categories the greps above don't reach

- **Modes a flag unlocks.** A `--changed`/`--watch`/`--dry-run` that takes a
  different code path is a branch of the system, not a flag.
- **The machine-facing contract** — everything a caller depends on that is not a
  function signature, and the axis maps miss most: output files and report
  formats, the wire format of each response, the status a rejection returns and
  which layer returns it (framework middleware answers 400 before your handler
  runs), which routes are unauthenticated, the lifecycle of any gate token you
  draw (something writes it — what deletes it?), whether each enforcement
  surface fails open or closed rather than the two you happened to read,
  in-database functions the app compiles queries against, OS-level contracts (an
  App Group identifier, a background-mode entitlement), and token/cost
  accounting.
- **Dev-time AI.** `.mcp.json` servers, agent workflows in CI, vendored skill
  packs — real actors even in a product with no runtime AI.

## Reading the largest-files list

Walk down until files drop below ~300 lines, or until the list turns into one
repeating shape (leaf UI components, generated clients, fixtures) — then stop,
ticking that shape off once. Don't stop at a round rank: in one 140-file repo
the two biggest misses sat at 25 and 29. If one repeating shape dominates twenty
consecutive ranks, that shape is itself a finding: it is where most of the code
lives, and it probably deserves more than the single node you were about to give
it.
