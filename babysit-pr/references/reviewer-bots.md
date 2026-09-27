# Reviewer bots: rate limits and re-triggering

Read this when a reviewer bot (CodeRabbit, Copilot, or another) reports a
limit, cooldown, quota, or billing problem instead of reviewing. That is
infrastructure state, not a code finding: wait and re-trigger, never edit code
to make it go away.

## Recognizing it

Scan reviewer-bot check descriptions, PR comments, and review summaries for
rate-limit language before treating a missing review as a failure:

- `rate limit`, `rate limited`, `quota`, `429`, `too many requests`,
  `resource exhausted`, `try again later`, `temporarily unavailable`,
  `retry after`, `limit exceeded`, `Review limit reached`,
  `More reviews will be available in`, `PR review rate limit`,
  `prepaid credits`, `review add-on`.
- If a retry time or `Retry-After` value is present, record it. If not, use a
  conservative 15-30 minute cooldown and say that it is an inferred wait.

Rate-limit evidence means the reviewer did not make a code-quality finding yet.
Report it as waiting/retry state, not as a code failure.

## Handling a rate limit

When CodeRabbit or another review bot is rate-limited:

1. Capture evidence: which bot, where it appeared (check/comment/review), latest
   PR head SHA, timestamp, and any retry-after/cooldown text. Append it to
   `rate_limits` in the state file (see SKILL.md, Autonomy and stop conditions)
   so the "same limit twice" rule survives across scheduled passes.
   - For CodeRabbit, a warning titled `Review limit reached` with text like
     `More reviews will be available in 21 minutes and 34 seconds` is explicit
     cooldown evidence. Parse that duration and add a small buffer before
     re-triggering.
   - If the warning says prepaid credits are used up or the review add-on is not
     enabled, include that billing note in the report; waiting may clear the
     normal rate window, but usage-based credits require an org admin decision.
2. Confirm required CI state separately. A rate-limited reviewer bot may be
   advisory; do not block `DONE` unless unresolved actionable review coverage is
   required for this repo or the user explicitly wants review-clean with that bot.
3. Wait through the cooldown in one blocking shell call. Prefer the bot's stated
   retry time; otherwise use 15-30 minutes depending on repo norms and remaining
   loop budget.
4. Re-trigger review once using the least noisy repo-supported mechanism:
   - For CodeRabbit, if its own comment says a review can be triggered using
     `@coderabbitai review`, post exactly that PR comment after the cooldown.
   - If the failed/pending item is a GitHub Actions workflow or check that can be
     rerun, rerun that workflow/check.
   - If repo history, PR instructions, or existing bot comments show a supported
     command such as a reviewer-bot "review again" comment, use that exact
     convention.
   - If no supported trigger is evident, ask before using noisy fallbacks like
     closing/reopening the PR, pushing an empty commit, or posting a guessed bot
     command.
5. Re-poll after the re-trigger. If the bot reviews successfully, continue the
   normal review-thread loop. If the same rate limit returns twice for this PR
   (per the state file), stop the
   active loop with `NOT YET`, include the next suggested check time, and do not
   edit code.

Never patch application code to satisfy a reviewer-bot infrastructure limit.

## Status messages that are not findings

Reviewer and CI bots post a lot of text that is progress or summary, not a
request for a change. Recognize it, count it as handled (record it in
`handled` in the state file), and do not re-read it every pass. Matching is by
author **and** wording — a real finding from the same bot still needs
verifying.

| Bot (login) | Message looks like | What it means |
|---|---|---|
| `coderabbitai[bot]` | "Currently processing new changes", "review in progress", a walkthrough / summary comment with no file:line findings | Review still running or summary only. Wait for the review for the current SHA; findings arrive as threads. |
| `coderabbitai[bot]` | "Review limit reached", "More reviews will be available in …" | Rate limit — see above. |
| `copilot-pull-request-reviewer[bot]` | "Copilot reviewed N out of M changed files … generated no comments" | Review finished with no findings. |
| `chatgpt-codex-connector[bot]` | usage limit / "reached your … limit" | Rate limit — see above. |
| `gemini-code-assist[bot]` | quota / "exhausted" | Rate limit — see above. |
| `sourcery-ai[bot]` | rate limit / "review limit" | Rate limit — see above. |
| `codecov[bot]`, `coveralls` | coverage report | Informational unless a *required* coverage check fails. |
| `vercel[bot]`, `netlify[bot]`, `cloudflare-*` | preview deployment status | Informational; a failed preview is advisory unless required. |
| `sonarcloud[bot]`, `sonarqubecloud[bot]` | "Quality Gate passed" | Informational. "Quality Gate failed" is a finding only if its check is required. |
| `github-actions[bot]` | workflow summaries, "This PR is stale" | Informational. |

Bots that post a formal `CHANGES_REQUESTED` review keep blocking the PR even
after every finding is fixed, unless they re-review. When all of a bot
review's findings are fixed on the current head and the bot has not
re-reviewed after one wait cycle, dismiss that review (never a human's):

```bash
gh api -X PUT "repos/$OWNER/$REPO/pulls/$PR/reviews/$REVIEW_ID/dismissals" \
  -f message="<!-- babysit-pr --> Findings addressed in <sha>; see replies on each thread." \
  -f event=DISMISS
```

This needs write access and some repos restrict dismissals; if it fails,
report the stale review as the remaining blocker instead.
