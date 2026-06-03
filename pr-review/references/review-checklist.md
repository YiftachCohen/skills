# Review checklist — detailed prompts per dimension

Use this when you want the full set of questions to ask of a diff. You don't need to apply every line to every PR — let the nature of the change tell you which lenses matter. A pure-refactor PR needs heavy "design" and "tests" scrutiny; a new endpoint needs heavy "security" and "error handling."

## Correctness
- Does the code actually do what the PR description says?
- Off-by-one errors, inverted conditionals, wrong operator (`&&` vs `||`, `<` vs `<=`).
- Async/concurrency: awaited promises, race conditions, shared mutable state, missing locks.
- Are loop bounds and recursion termination correct?
- Does it handle the boundary the PR is supposedly about?

## Edge cases & error handling
- Null / undefined / empty collections / zero / negative / very large inputs.
- What happens when an external call fails or times out? Is the error swallowed, logged, or surfaced?
- Are exceptions caught at the right level, or too broadly (`catch (e) {}` hiding real failures)?
- Resource cleanup: files, connections, locks, subscriptions released on every path including errors?
- Partial failure: if step 3 of 5 fails, is the system left consistent?

## Security
- All external/user input validated and sanitized before use.
- Injection: SQL, command, XSS, path traversal, template injection.
- AuthN/AuthZ: is the new code path protected? Can a user access another user's data?
- Secrets, API keys, tokens hardcoded or logged?
- Unsafe deserialization, SSRF, open redirects.
- New dependencies: trustworthy, maintained, pinned?
- Does it weaken an existing security control?

## Tests
- Is the new logic covered by tests at all?
- Do tests assert on behavior/output, or just execute code without meaningful assertions?
- Are the edge cases and error paths above tested, not just the happy path?
- For a bug fix: is there a regression test that fails without the fix?
- Are tests readable and not brittle (over-mocking, asserting on internals)?

## Design & complexity
- Does the change fit the existing architecture and conventions, or fight them?
- Is it the simplest thing that works, or over-engineered for imagined future needs (YAGNI)?
- Duplicated logic that should reuse an existing helper? New helper that duplicates an existing one?
- Are responsibilities in the right place (right layer, right module)?
- Are abstractions leaky — does the caller need to know internals?
- Is state managed sensibly, or scattered global/mutable state added?

## API & compatibility
- Breaking changes to public function signatures, REST/GraphQL schemas, events?
- Database migrations: reversible, safe on a live table, backfill considered?
- Backward compatibility for existing clients / serialized data / config?
- Versioning and deprecation handled if this is a public interface?
- Feature flags for risky rollouts?

## Performance
- N+1 queries, queries inside loops, missing indexes implied by new query patterns.
- Unnecessary work repeated per-iteration that could be hoisted.
- Large allocations, unbounded caches/collections, memory leaks.
- Blocking I/O on a hot/async path.
- Only raise these when they plausibly matter at the code's real scale — premature optimization is its own smell.

## Readability & maintainability
- Names that mislead or are too generic (`data`, `tmp`, `handle`, `flag`).
- Control flow that's hard to follow — deep nesting that could be early-returns.
- Missing "why" comments where the code is non-obvious or works around something subtle. (Don't ask for "what" comments that restate the code.)
- Dead code, commented-out blocks, leftover debug logging / `console.log` / `print`.
- Magic numbers/strings that should be named constants.

## Scope & hygiene
- Changes unrelated to the PR's stated purpose (sneak-in refactors, formatting churn that hides the real diff).
- Generated files, lockfiles, or build artifacts committed by accident.
- TODO/FIXME left without context or a tracking issue.

## Documentation
- Public API changes reflected in docs / README / changelog?
- New config or env vars documented?
- Complex algorithm or non-obvious decision explained somewhere durable?
