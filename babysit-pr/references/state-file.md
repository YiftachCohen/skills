# babysit-pr state file

One JSON file per PR remembers what the conversation would otherwise forget.
Scheduled `--once` passes and new sessions start with no memory, so the safety
caps, the stall clock, and "which comments did I already handle" all live
here.

```bash
STATE="$(git rev-parse --path-format=absolute --git-common-dir)/babysit-pr/$PR.json"
mkdir -p "$(dirname "$STATE")"
[ -s "$STATE" ] || echo '{}' > "$STATE"
```

It sits inside `.git`, so it is never committed, and `--git-common-dir` makes
all worktrees of the repo share it. Read it at the start of every pass, update
it with `jq` whenever something below changes, and delete it once the PR is
merged or closed. Every key is optional — treat a missing key as empty.

## Keys

```json
{
  "passes": 7,
  "stall": { "fingerprint": "3f1c…", "since": 1760000000 },
  "fix_attempts": { "test (3.12)": [ { "sha": "abc123", "summary": "fix off-by-one in sum()" } ] },
  "thread_attempts": { "PRRT_kwDO…": 2 },
  "reruns": { "12345678": 2 },
  "retriggers": { "abc123": "update-branch" },
  "handled": { "PRRT_kwDO…": "9e0d…", "IC_kwDO…": "51aa…" },
  "rate_limits": [ { "bot": "coderabbitai[bot]", "at": "2026-09-26T10:00:00Z", "retry_after": "21m34s" } ]
}
```

- **`passes`** — incremented every pass. The 12-pass cap is per invocation;
  a large running total is worth mentioning in the report.
- **`stall`** — maintained by `wait-for-pr.sh --state "$STATE"`, which
  fingerprints everything that would make you act (head SHA, mergeability,
  review decision, each check's bucket, review activity) and reports
  `unchanged_minutes`. When you act without the script (a pass that pushes, a
  pass woken by an event), the next wait recomputes it.
- **`fix_attempts`** — one entry per pushed fix, keyed by check name. Two
  entries and a third failure of that check → `BLOCKED`.
- **`thread_attempts`** — fix rounds per review thread id. After 3 rounds on
  one thread (you fixed, the reviewer came back on the same point) → ask the
  user instead of guessing a fourth time. Reset a thread's count if its
  opening comment is edited.
- **`reruns`** — the run ids you already reran. The authoritative count is
  GitHub's own `attempt` (`gh run view <run-id> --json attempt`), which survives
  lost state; this map just saves the lookup.
- **`retriggers`** — per head SHA, the one retrigger already spent on required
  checks that never reported (`update-branch`, or `close-reopen` if the user
  approved it). A second time on the same SHA → report it, don't repeat.
- **`handled`** — per thread id (`PRRT_…`) or top-level comment / review id,
  a fingerprint of what you handled: the hash of its comments' ids, bodies and
  `lastEditedAt` (for a top-level comment or review, its id and body — an edit
  changes the body). If the current fingerprint differs — a new reply, or an edit
  to an existing comment — the item is live again. This is what stops each
  pass from re-reading and re-judging the same noise.

  ```bash
  jq -c '[.comments.nodes[] | [.id, .body, .lastEditedAt]]' <<<"$THREAD" | sha256sum | cut -c1-16
  ```

- **`rate_limits`** — reviewer-bot rate-limit hits, so "the same limit twice →
  stop" holds across scheduled passes (see `reviewer-bots.md`).
