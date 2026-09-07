# Investigation behind the walkthrough

Read this for a broader walk or a consequential uncertainty that needs tracing.
Use only the depth needed by the request. Keep working evidence separate from
the explanation so the reviewer sees what changes their understanding.

## Trace the change

Recover intent from the linked issue, supplied prompt, and opened commits.
Distinguish documented intent from inferred intent. For each consequential
hunk, read the enclosing function and relevant callers at the pinned revision.
For a touched public symbol, examine other consumers before stating its blast
radius. For an exhaustive walk, cover every non-mechanical change and record
any coverage gaps. Order the explanation by cause, not filename.

Inspect tests for what their assertions establish. Notice removed, skipped,
or loosened tests, and important scenarios that lack coverage. Keep per-test
notes when useful; present coverage by behavior. Read CI status for the pinned
head without treating it as evidence that every promised case is tested.

## Correct the picture

Check description claims relevant to the explanation and review decision.
Surface discrepancies that change behavior, scope, risk, or confidence in test
evidence. Explain what the code actually does and why the difference matters.
An unmentioned consequential change belongs in the story too.

Keep harmless omissions and bookkeeping out of the walkthrough. If a number
matters, state what you measured at the pinned revision; label its origin
unresolved unless verified. Attribute motives and historical causes only to
sources you actually opened. The explanation needs a faithful account of the
change; a complete claim inventory belongs to the separate description audit.

## Look for consequential surprises

These are investigation prompts, not findings by themselves. Report a hit only
with a reachable scenario, its consequence, and code evidence. Choose depth
according to the affected behavior:

- Assertions of internal calls, state, or log strings that leave the promised
  behavior untested; mocks that replace the behavior under test.
- Errors swallowed or converted into misleading defaults.
- APIs, options, or fields absent from the codebase or pinned dependencies.
- Comments or descriptions that disagree with implementation.
- New helpers duplicating existing behavior, or defensive branches masking a
  contract mismatch. Explain the actual consequence before presenting these.
- Changes to CI, lint, build, dependencies, or behavior outside documented scope.
- Retries, timeouts, or concurrency without a relevant bound or idempotency.
- Permission, authentication, tenancy, deletion, or data-retention changes.
- Migrations or backfills: compatibility during rollout, failure recovery, and
  whether rollback or another recovery strategy is feasible.

Give the reviewer the causal explanation and evidence, then identify any
judgment the evidence cannot settle. A small PR may have no consequential
open decision. Say what was established without manufacturing a concern.
