---
name: pr-review
description: Review a teammate's pull request from a link and produce structured, copy-paste-ready review comments. Use whenever the user shares a PR/MR URL (GitHub, GitLab, Bitbucket) and wants it reviewed, asks to "review this PR", "look over my coworker's PR", "give feedback on this pull request", "what should I comment on this PR", or wants a code review they can paste back onto the PR. Trigger even when the user just pastes a pull-request link with little other context, or says things like "can you check this before I approve it". Do NOT trigger for reviewing local uncommitted diffs with no PR (use a plain code-review flow) or for opening/creating a PR.
---

# PR Review

Review a teammate's pull request and produce review comments the user can paste directly back onto the PR — both inline line comments and an overall summary. The user reviews many PRs; your job is to do the careful reading and turn it into ready-to-paste output, not to merge or approve anything yourself.

The output is the product. Optimize relentlessly for "copy this block, paste it on that line." Everything else serves that.

## Workflow

### 1. Fetch the PR

You're given a URL like `https://github.com/org/repo/pull/123`. Pull down everything you need to review it well. Try these in order until one works:

1. **`gh` CLI** (best when available — gives diff with real line numbers and metadata):
   ```bash
   gh pr view 123 --repo org/repo --json title,body,author,baseRefName,headRefName,additions,deletions,files,reviewDecision,state
   gh pr diff 123 --repo org/repo
   ```
2. **GitHub MCP tools** (if `mcp__github__*` tools are available): use `pull_request_read` to get the PR, its diff, and its files/comments.
3. **Fetch the diff directly**: append `.diff` to the PR URL (`https://github.com/org/repo/pull/123.diff`) and fetch it. Works for public repos.
4. **Clone/checkout** as a last resort: fetch the branch and run `git diff <base>...<head>`.

Gather, at minimum: the **PR title and description** (intent matters — see step 2), the **full diff**, the **list of changed files**, and if cheaply available: linked issues, CI status, and existing review comments (so you don't repeat what's already been said).

If you genuinely can't access the PR by any method, tell the user and ask them to paste the diff rather than guessing.

### 2. Understand intent before judging

Read the PR description and any linked issue first. A change is only "correct" relative to what it's trying to do. Form a one-sentence understanding of the goal before you start critiquing — it stops you from flagging deliberate decisions as mistakes.

Then read the diff **in context**, not as isolated lines. When a hunk calls a function or touches an interface, look at the surrounding code (read the file, or the rest of the function) so you understand the blast radius. The most valuable review comments come from understanding the code around the change, which the diff alone doesn't show.

### 3. Review across these dimensions

Don't just hunt for syntax issues — that's what linters are for. Reviewers add value on judgment. Walk the diff with these lenses, roughly in priority order. `references/review-checklist.md` has the detailed prompts for each; read it if you want the full set.

1. **Correctness** — does it do what it claims? Logic errors, off-by-one, wrong conditionals, race conditions, unhandled async, incorrect assumptions.
2. **Edge cases & error handling** — null/empty/large inputs, failure paths, errors swallowed or surfaced poorly, resource cleanup.
3. **Security** — input validation, injection (SQL/command/XSS), authn/authz, secrets in code, unsafe deserialization, dependency risk.
4. **Tests** — are the new code paths tested? Do tests assert behavior (not just run)? Missing cases for the bugs/edge cases above?
5. **Design & complexity** — does it fit existing patterns? Is it simpler than it needs to be? Over-engineering, leaky abstractions, duplicated logic that should be reused.
6. **API & compatibility** — breaking changes to public interfaces, DB migrations, backward compatibility, versioning.
7. **Performance** — N+1 queries, unnecessary work in loops, allocations on hot paths — but only flag if it plausibly matters.
8. **Readability & naming** — names that mislead, unclear control flow, missing "why" comments for non-obvious code.
9. **Scope** — changes unrelated to the PR's stated purpose, or stray debug/commented-out code.

Two rules that keep reviews useful:
- **Tie every comment to a concrete line or file.** A reviewer who says "this could be cleaner" without a location is just noise. If you can't point at the code, it's probably not worth saying.
- **Don't bikeshed.** If a linter/formatter would catch it, or it's pure style preference, either skip it or mark it a `nitpick (non-blocking)`. Spend the user's credibility on things that matter.

### 4. Classify severity

The guiding principle (from Google's code-review standard): **approve once the change definitely improves the overall health of the codebase, even if it isn't perfect.** There's no perfect code — only better code. Don't withhold approval over polish; leave non-blocking notes and let good changes through. Technical facts beat personal preference; preference never blocks.

Every comment gets a severity so the user (and the PR author) knows what actually blocks merge. This is the single most useful thing you provide — it turns a wall of feedback into a clear "fix these two, the rest is optional."

- **🔴 Blocking** — must be addressed before merge. Bugs, security holes, missing tests for critical paths, breaking changes.
- **🟡 Non-blocking** — worth addressing but the author can reasonably decide. Design suggestions, better approaches, missing edge-case handling that's unlikely.
- **🟢 Nit** — trivial/style/preference. Explicitly optional. Author can ignore freely.

When unsure, err toward non-blocking — over-blocking erodes trust and slows the team down.

### 5. Write the comments using Conventional Comments

Use the [Conventional Comments](https://conventionalcomments.org/) format for every inline comment. It makes the *kind* and *weight* of feedback unmistakable, which is exactly what a paste-ready comment needs:

```
<label> [decoration]: <comment body>
```

- **Labels:** `praise`, `nitpick`, `suggestion`, `issue`, `question`, `todo`, `thought`, `chore`, `note`.
- **Decorations:** severity — `(blocking)`, `(non-blocking)`, `(if-minor)`; and optionally domain — `(security)`, `(test)`, `(performance)` — which you can combine, e.g. `issue (blocking, security):`.

Guidance that makes comments land well:
- **Lead with the label, then be specific and actionable.** Say what's wrong *and* what to do instead. "This will NPE when `users` is empty — guard with `if (users.isEmpty()) return` " beats "handle the empty case."
- **Pair every `issue` with a fix.** Point at the problem, then offer a concrete `suggestion:` so the author isn't left guessing what you'd accept.
- **Make suggestions concrete.** For a clear fix, include the replacement code so the author can apply it directly (GitHub renders ```suggestion blocks as one-click commits — use them for small inline fixes).
- **Critique the code, not the author.** "This concurrency model adds complexity I don't think we need" — not "why did you do this." No hyperbole ("always", "never", "obviously"). Assume the author is smart and already weighed alternatives.
- **Ask, don't command, when you're not sure.** A `question:` invites the author to explain a decision you might be misreading. You're reviewing a teammate, not gatekeeping.
- **Collapse repeats.** If the same nit recurs ten times, make the point once and note it applies throughout — don't paste ten identical comments.
- **Include genuine praise.** Note things done well (`praise:`), specifically — what to keep doing. It's not filler; it balances the review and makes the critical notes land better. Don't fabricate it, though — only when warranted.

Examples:
- `issue (blocking): \`parseInt(id)\` returns NaN for non-numeric ids, which then passes the \`> 0\` check as false silently. Validate before parsing or use \`Number.isInteger\`.`
- `suggestion (non-blocking): this mapping loop runs a query per item — N+1. Could batch with a single \`WHERE id IN (...)\`.`
- `question: is the retry intentional unbounded here? If the downstream stays down this loops forever.`
- `nitpick (non-blocking): \`data2\` doesn't say what it holds — maybe \`normalizedRows\`?`
- `praise: nice — pulling this into \`withRetry\` makes the call sites much cleaner.`

## Output format

Produce exactly this structure. The whole point is paste-ability, so keep each comment body self-contained and put it in its own fenced block the user can copy in one go.

````markdown
# PR Review: <PR title>

**Recommendation:** ✅ Approve / 💬 Comment / 🔴 Request changes
**Summary:** <2-4 sentences: what the PR does, your overall read, and the headline issues if any.>

**Blocking items:** <count> · **Non-blocking:** <count> · **Nits:** <count>

---

## 📋 Overall comment — paste as the PR review summary

```
<A few sentences the user can paste into the PR's top-level review box.
Start with the overall assessment, then list the blocking items as a short
bulleted list so the author sees the must-fixes immediately. Be warm and
specific — this is going to a teammate.>
```

---

## 💬 Inline comments — paste each onto the referenced line

### 🔴 Blocking

**`path/to/file.ext:42`**
> `the exact line of code being commented on (anchor)`
```
issue (blocking): <comment body in Conventional Comments format>
```

### 🟡 Non-blocking

**`path/to/file.ext:88`**
> `anchor line`
```
suggestion (non-blocking): <body>
```

### 🟢 Nits

**`path/to/other.ext:12`**
> `anchor line`
```
nitpick (non-blocking): <body>
```
````

Rules for the output:
- **Group by severity** (Blocking → Non-blocking → Nits) so the user can paste the important ones first and skip nits if short on time. Omit a section entirely if it's empty.
- **Each inline comment shows `file:line` and a quoted anchor line** from the diff, so the user can locate exactly where to paste it in the PR's "Files changed" view. Use the line number on the **new** side of the diff (the `+` side) unless commenting on a deleted line. Where it helps, name the enclosing symbol too (e.g. `userService.js:14 — in getUser()`) so the location survives a rebase that shifts line numbers.
- **The comment body sits alone in a fenced code block** — that's the part that gets copied. Don't put the file/line *inside* the block.
- **Mind the fence nesting.** A comment body that itself contains a ` ```suggestion ` block (three backticks) must be wrapped in a **four-backtick** fence, otherwise the inner block closes the outer one early and the "copy this block" affordance breaks. So a plain comment uses a three-backtick fence; a comment containing a suggestion uses a four-backtick fence:
  `````
  ````
  issue (blocking): guard the empty case — this NPEs otherwise.

  ```suggestion
  if (users.isEmpty()) return Collections.emptyList();
  ```
  ````
  `````
  GitHub renders ` ```suggestion ` blocks as one-click commit suggestions, so use them for small inline fixes.
- **End with a one-line note** if there are things you couldn't verify (e.g. "I couldn't see the test file — confirm `UserServiceTest` covers the null case").

Keep the total focused. A review with 4 sharp comments beats one with 20 where the real issues are buried. If the PR is clean, say so plainly and approve — don't manufacture findings to look thorough.
