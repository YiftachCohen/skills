---
name: walk-me-through
description: |
  Guide a reviewer through a pull request they do not understand, typically one
  a teammate opened with a coding agent, until they know enough to have an
  opinion without reading every line. Use this skill whenever the user says
  "walk me through this PR", "walk me through #123", "I have no idea what this
  PR does", "explain this PR to me", "help me review this AI PR", "is this
  agent PR safe to approve", "what is this PR actually doing", "the description
  is too long, what matters here", or pastes a PR link and asks to understand
  it rather than fix it. It should trigger even when the user only says "I got
  assigned this PR and it's huge", "help me understand this PR", or "can you
  check whether the PR description is accurate". It is a guided, conversational
  walkthrough, not an automated review: it never writes to GitHub and never
  issues an approve/reject verdict unless asked. For a findings-style
  standards or spec review, use a code-review skill instead.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
  - Agent
---

# Walk me through

One promise: **the reviewer understands this PR well enough to have an
opinion, without reading every line.**

The reviewer already has a long description. They do not need another
summary; they need a path through unfamiliar code and a clear view of what
the description gets right, gets wrong, and leaves out. Be the patient
teammate who has already read everything: "Here is what is happening. This
is the part worth thinking about."

## Rules that make or break it

These hold in every phase. When a rule and a template conflict, the rule wins.

1. **Read the implementation before trusting the description.** On
   agent-written PRs the description is confident and partly wrong. Every
   sentence you say about behavior comes from the code, never from the
   description alone.
2. **One step, one next move.** Each turn gives one useful explanation and
   states the next move. Short beats complete; the reviewer can redirect.
3. **Three registers, always.** Fact, inference, uncertainty, with the fixed
   phrasing in the reference below. The sentences most likely to be
   inferences dressed as facts: why something is there, why a number in the
   description differs from what you measured, and anything about a PR,
   issue, or commit you did not open. Each of those gets "I think ...,
   because ..." unless a commit message or comment states it.
4. **A citation is re-read before it is written.** Diff line numbers are not
   file line numbers, and one wrong `path:line` costs every other citation
   its credibility. Before a `path:line` goes into a reply or the notes,
   print that line from the checked-out file and confirm it holds what you
   say it holds. After writing the notes, run
   `python3 <skill-dir>/scripts/check_citations.py <file> --root .` from the
   worktree; it prints every cited line beside its citation. Fix what does
   not match. A citation you cannot re-read is a description in words.
5. **Spend attention where it matters.** A three-line permission change gets
   depth; 800 lines of generated client get one sentence. Say which files
   can be skimmed.
6. **Begin immediately.** Never open by asking about the reviewer's role or
   preferred depth. Start; they adjust with the standing moves.
7. **Understanding before agreement.** Make the behavior clear first. Only
   then present the decisions that are the reviewer's to judge.
8. **No verdict, no writes.** Recommend approve or request-changes only when
   asked. Never post, comment, review, or push on GitHub; the reviewer does
   that themselves with what you gave them.

## Phase 0: Silent prep

Show one "reading the PR" line, then do all of this before saying anything
else. The foothold has to be true, and it cannot be true until you have read
the code. Scale the work to the PR. Read it yourself; fan out with `Agent`
only when the PR is too large for one pass (roughly twenty-five or more
non-mechanical files), and then use the cheapest model available for runners
and re-read every citation they return.

Use `gh` (or the runtime's GitHub tools) for the PR record, and check the
head commit out in a worktree so you can read whole files and follow callers.
If you cannot reach the PR, say what access is missing and stop.

1. **Resolve the PR** and confirm the base branch.
2. **Gather the record**: description, linked issues, branch name, commits,
   any prompt pasted into the description, review threads, CI status.
3. **Recover the intent** in one sentence. The gap between it and what
   shipped is scope drift, the most common defect in agent output and
   invisible from the diff alone.
4. **Read the code, not just the diff.** For each non-trivial hunk, the
   enclosing function and the callers. For each touched public symbol, who
   else uses it. This is the blast radius.
5. **Build the claims ledger.** Split the description into discrete claims
   and mark each `verified`, `partial`, `unsupported`, or `contradicted`,
   with locations. Then the inverse list: changes the description never
   mentions. On agent PRs that list is where the trouble lives. When a number
   in the description does not match what you count, find the commit where
   it was true before calling it stale: a head commit that merged the base
   branch includes other PRs' work. Report both numbers and where each held.
6. **Triage the files** into mechanical, boilerplate, and needs-a-human, then
   write a causal reading order: the entry point that motivates the change,
   the core logic, plumbing, tests, noise. Never the alphabetical list.
7. **Run the lens checklist** below; note each hit with a `path:line`.
8. **Pick the spine.** If the PR changes runtime behavior, one concrete
   scenario followed through the system before and after. Otherwise the
   causal reading order.
9. **Read the tests; do not run them.** Pass/fail is CI's job and you have
   its status. What CI cannot say is what the tests prove: one line per added
   or changed test on the behavior it pins, and what the change does that no
   test touches. Note tests removed, skipped, or loosened. Execute something
   only when a what-if during the walk is fastest answered that way.
10. **Keep working notes** in `.walk-me-through/pr-<id>.md` at the worktree
    root (ledger, triage, reading order, lens hits, scenario). First add
    `.walk-me-through/` to `$(git rev-parse --git-path info/exclude)` so it
    never shows in `git status` on the teammate's branch. Do not touch
    `.gitignore`.

## Phase 1: The foothold

One screen. The first sentence is the before/after sentence: not what you
read, not how you prepared, not where the notes are. Process notes go last.

1. **Before and after, in the system's terms.** "Today a temporary outage
   permanently loses a webhook event. After this PR, delivery is retried for
   up to 24 hours." Not "modifies `queue.ts` and adds `RetryWorker`."
2. **Where the weight is.** "41 files. 33 are plumbing and tests you can
   skim. Three carry the decision: ..."
3. **The one decision that matters.** "The important choice is what happens
   when a delivery succeeds but its acknowledgment is lost."
4. **The trust line.** From the ledger: which claims the code does not back,
   and how many changes the description never mentions, even when they are
   trivial. "Matches on every claim. One change it does not mention: a
   one-word README edit." Then "matches" is a claim the reviewer can check.
   Any number you could not reconcile goes here too.
5. **Intent line, only if there is drift.**
6. **The next move, already chosen**, one line naming the standing moves,
   and last the process line: notes location and what CI reports.

If the reviewer asked about the description's accuracy, the trust line is the
answer and expands to fill the screen: one line per claim with status and
citation, then the unmentioned changes. Do not collapse a dozen claims into
"almost all of it checks out."

Default depth is the ten-minute walk. "Quick" is the foothold, the judgment
section, and the close; "everything" walks every non-mechanical file in causal
order after the scenario. Depth changes what you show, not what you read.

Do not wait for permission after the foothold. On any reply that is not a
redirect, take the stated next move.

## Phase 2: The walk

Each stop is one turn: what happens here, told as the scenario; the code at
`path:line`, with a snippet only when it clarifies; the existing code the
change depends on, explained before the reviewer has to ask; blast radius
when a touched symbol has outside callers; the next move in one sentence.

Honor these at any time, without ceremony:

| Move | What you do |
|---|---|
| "I know this part" | Skip the rest of the stop. |
| "back up" | Previous stop, shorter. |
| "what's a ...?" | Explain from the existing code, then resume. |
| "why does it ...?" | Answer from code and commits with citations, or "I could not tell". |
| "show me the implementation" | Causal reading order for that area. |
| "skip to the risky bit" | Jump to judgment. |
| "quick" / "everything" | Change depth. |
| "can this ...?" | Trace it through the code; answer in the three registers. |

Any question is answered with citations and then you return to the spine.
Offer two or three context-specific directions at natural branch points; do
not wait on them.

## Phase 3: Judgment

Switch modes with one line: "You now understand what it does. Here is where
your opinion is needed." Then, by consequence, the items that are the
reviewer's: decisions the author made, what the tests prove and do not, lens
hits with lines, scope drift beside the intent sentence, blast radius to sign
off on. Each item ends in the reviewer's question. If you cannot phrase it as
their question, it is a finding and belongs in the trust line or the close.
"Worth a glance, not a blocker" is a verdict; "is this the same fix that
landed in #12?" is their question.

## Phase 4: The close

One screen that hands judgment back: what it does in one sentence; claims the
code does not back and every unmentioned change; top risks, at most three,
each with a location; covered and not covered; one question worth sending
the author; one thing worth trying locally, with the exact command; what CI
reports and what the tests cover.

No approval language. If asked "should I approve?", give a recommendation
with reasons, in the three registers.

## Reference: the lens checklist

The recurring failure modes of agent-written PRs. Report only hits.

- Tests that assert the implementation (call counts, internal state, log
  strings) instead of the promised behavior.
- Mocks that replace the unit under test.
- Tests deleted, skipped, marked flaky, or loosened.
- Errors swallowed or silently converted to defaults.
- Calls to APIs, options, or fields that do not exist in the codebase or the
  pinned dependency versions.
- Comments and docstrings describing behavior the code does not have.
- New helpers duplicating an existing utility.
- Defensive code for cases the types or callers make impossible.
- CI, lint, build, or dependency changes the task did not ask for.
- Retries, timeouts, or concurrency without idempotency or a bound.
- Permission, auth, tenancy, or data-deletion paths touched at all.
- Migrations or backfills without a rollback story.
- Scope beyond the linked issue or the prompt.

## Reference: the three registers

- Fact, from code you read: "The worker retries up to 24 hours
  (`retry.ts:41`)."
- Inference: "I think the config change exists to make the retry window
  configurable, because it is the only new key read anywhere."
- Uncertainty: "I could not confirm whether old workers tolerate the new job
  shape; nothing in the diff addresses it."

Never upgrade an inference to a fact for the sake of flow.

## Anti-patterns

- Restating the description in different words.
- Opening with a file list, or with what you read and where the notes are.
- A `path:line` you did not re-read.
- Calling a number wrong without finding where it was right.
- A stop that explains three things and offers four choices.
- Ending with "looks good to me".
