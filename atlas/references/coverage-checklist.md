# Coverage checklist — what the inventory must account for

**`scripts/survey.sh` is the sweep.** It runs once, reads the working tree, and
collects every mechanical category below. This file no longer duplicates those
commands: two copies of a grep drift, and the copy in a doc is the one that goes
stale silently. What lives here is the part a script cannot do — the categories
no pattern reaches, and how to read what the survey hands you.

Every item goes in `.atlas/inventory.md` with a disposition. A category with no
hits gets one line saying so; silence is not the same as none.

## What the survey collects

Scale (the measured file count that picks the approach) · the largest non-test
source files · manifests, including nested ones in a monorepo · env vars · CI
schedules and queue/job code · entry-point and route directories · schemas and
migrations · exit codes, both explicit calls and return-based · the AI layer ·
dev-time AI config · CI workflows.

Env vars are detected across Node/Vite/Deno, Python (`os.environ` and
`os.getenv`), Go, Ruby, PHP, Java/Kotlin, C# and Rust. The AI sweep covers the
major providers, the SDK call shapes (`messages.create`, `chat.completions`,
`generateText`), the agent frameworks and MCP.

## Extending it

If a repo's language or framework is not covered, **add the pattern to
`scripts/survey.sh` and re-run it** rather than running a one-off grep beside
it. A one-off answers this scan; the script answers every scan after it, and the
next person mapping a repo in that language does not repeat your work. The env
var and AI-layer regexes are the two designed to grow — each is a single
alternation with a comment saying so.

Two things worth knowing when you read its output. The `return [1-9]` block is
deliberately noisy and capped: confirm each hit actually reaches an exit before
believing it is a failure path. And a hit inside a committed build artifact is a
hit in generated code — check the path before mapping it.

## Categories no sweep reaches

These are judgment, and they are where maps go incomplete:

- **Modes a flag unlocks.** A `--changed`/`--watch`/`--dry-run` that takes a
  different code path is a branch of the system, not a flag. The survey can list
  flag registrations; only reading tells you which ones fork the flow.
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
  packs — real actors even in a product with no runtime AI. The survey lists the
  files; whether CI actually invokes an agent is something you read.
- **What the code does that no name reveals.** A `util` package holding the
  product's two most important security controls looks like helpers from every
  angle a grep has.

## Reading the largest-files list

Walk down until files drop below ~300 lines, or until the list turns into one
repeating shape (leaf UI components, generated clients, fixtures) — then stop,
ticking that shape off once. Don't stop at a round rank: in one 140-file repo
the two biggest misses sat at 25 and 29. If one repeating shape dominates twenty
consecutive ranks, that shape is itself a finding: it is where most of the code
lives, and it probably deserves more than the single node you were about to give
it.
