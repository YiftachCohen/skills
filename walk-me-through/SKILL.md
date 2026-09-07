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
  it rather than fix it. It should trigger even when the user only says "review
  this with me", "I got assigned this PR and it's huge", or "can you check
  whether the PR description is accurate". It is a guided, conversational
  walkthrough, not an automated review: it never posts to GitHub on its own and
  never issues an approve/reject verdict unless asked.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - AskUserQuestion
  - Agent
---

# Walk me through

One promise: **the reviewer understands this PR well enough to have an
opinion, without reading every line.**

The reviewer already has a long description. They do not need another
summary; they need a path through unfamiliar code and a clear view of what
the description gets right, gets wrong, and leaves out. The experience should
feel like a patient teammate who has already read everything: "Here is what
is happening. This is the part worth thinking about."

## Rules that make or break it

These hold in every phase. When a rule and a template conflict, the rule wins.

1. **Read the implementation before trusting the description.** The
   description is the author's claim, and on agent-written PRs it is often
   confident and partly wrong. Every sentence you say about behavior comes
   from the code, the tests, and the surrounding system, never from the
   description alone.
2. **One step, one next move.** Each turn gives one useful explanation and
   states the next move you will take. Short beats complete. The reviewer can
   redirect at any time.
3. **Three registers, always.** Say "the code does X" only when you read it.
   Say "I think X, because Y" for inference. Say "I could not confirm X" for
   anything you did not verify. Smooth prose that blurs these is how a guide
   manufactures false confidence.
4. **Spend attention where it matters.** Explain a three-line permission
   change in depth. Collapse 800 lines of generated client into one sentence.
   Say explicitly which files can be skimmed and which need a human.
5. **Begin immediately with sensible defaults.** Never open by asking about
   the reviewer's role, expertise, or preferred depth. Start the walk; the
   reviewer adjusts with the standing moves below.
6. **Understanding before agreement.** First make the behavior clear. Only
   then introduce the decisions the author made and the judgment that is the
   reviewer's. Do not mix the two.
7. **No verdict, no posting, unless asked.** The walkthrough ending is not an
   approval. Give an approve/request-changes recommendation only when the
   reviewer asks, and post nothing to GitHub without an explicit instruction
   naming what to post.

## Runtime compatibility

Use whatever the current runtime provides.

- In Claude Code, prefer `gh` for PR metadata, the diff, linked issues,
  commits, review threads, and check status.
- In Codex, prefer the GitHub connector tools for the same, and `gh` where the
  connector lacks something.
- Either way, **check the branch out locally** (a worktree is fine) so you can
  read whole files, follow call sites, and run tests. Hunks alone are not
  enough to explain unfamiliar code.
- If you cannot reach the PR at all, say exactly what access is missing and
  stop. Do not walk through a diff you cannot see.

## Phase 0: Silent prep

Do all of this before showing anything beyond a single "reading the PR" line.
The foothold has to be true, and it cannot be true until you have read the
code.

1. **Resolve the PR**: a number, a URL, a branch name, or "this PR" for the
   current branch. Confirm the base branch.
2. **Gather the record**: description, linked issues, branch name, commit
   messages, any prompt or task text pasted into the description, existing
   review threads, CI status.
3. **Recover the intent.** From the record, write one sentence for what was
   asked. Later you compare this to what was delivered; the gap is scope
   drift, the most common defect in agent output and invisible from the diff
   alone.
4. **Read the code, not just the diff.** For every non-trivial hunk, read the
   enclosing function and the callers. For every touched public symbol, find
   who else uses it. This is the blast radius; you will need it at the stops.
5. **Build the claims ledger.** Split the description into discrete claims
   ("adds retry up to 24h", "no behavior change for existing customers",
   "tests cover the crash case"). Mark each one:
   - `verified`: the diff does this, at these locations.
   - `partial`: it does some of this; say what is missing.
   - `unsupported`: nothing in the diff does this.
   - `contradicted`: the diff does the opposite or something incompatible.
   Then build the inverse list: **changes the description never mentions.**
   On agent PRs this list is where the trouble usually lives.
6. **Triage the files** into three buckets and order them:
   - *Mechanical*: formatting, renames, lockfiles, generated code, snapshots.
   - *Boilerplate*: wiring, registrations, straightforward tests, types that
     mirror the core change.
   - *Needs a human*: the decision-bearing logic, anything touching
     permissions, money, data deletion, migrations, concurrency, retries,
     auth, CI, or config.
   Then write a **causal reading order**: the entry point that motivates the
   change, then the core logic, then plumbing, then tests, then mechanical
   noise. GitHub's alphabetical file list is never the order.
7. **Run the lens checklist** (see the reference below) and note each hit
   with a `path:line`.
8. **Pick the spine.** If the PR changes runtime behavior, the spine is a
   concrete scenario: one event followed through the system before and after.
   If it does not (a refactor, a dependency bump, config, tooling), the spine
   is the causal reading order. Most agent PRs have a scenario; find it.
9. **Run the tests** if the suite finishes in a couple of minutes, and note
   which tests the PR added versus changed versus removed. If tests are slow
   or need infrastructure, note that you did not run them and say so in the
   close.
10. **Keep working notes** in `.walk-me-through/pr-<number>.md` inside the
    repo: ledger, triage, reading order, lens hits, scenario. Do not commit
    it and leave `.gitignore` alone; tell the reviewer it is there.

## Phase 1: The foothold

One screen, roughly twelve lines. Written from the code. In this order:

1. **Before and after, in the system's terms.** "Today a temporary outage
   permanently loses a webhook event. After this PR, delivery is retried for
   up to 24 hours." Not "modifies `queue.ts` and adds `RetryWorker`."
2. **Where the weight is.** "41 files. 33 are queue plumbing, generated
   types, and tests you can skim. Three carry the decision: ..." This is the
   attention budget in one sentence.
3. **The one decision that matters.** "The important choice is what happens
   when a delivery succeeds but its acknowledgment is lost."
4. **The trust line.** From the claims ledger: "The description is accurate
   about the retry window. It does not mention that the config loader was
   rewritten. It claims the crash-after-delivery case is tested; I could not
   find that test." Only discrepancies belong here; if there are none, say
   the description matches the code.
5. **Intent line, only if there is drift.** "The linked issue asked for
   retries. The PR also changes how config is loaded; I found no reason for
   that in the code or the commits."
6. **The next move, already chosen.** "Next I will follow one failed delivery
   through the change." Then one line naming the standing moves.

Default depth is the ten-minute walk. If the reviewer says "quick", give the
two-minute version: the foothold, the judgment section, and the close. If
they say "everything", walk every non-mechanical file in causal order after
the scenario.

Do not wait for permission after the foothold. On any reply that is not a
redirect, take the stated next move.

## Phase 2: The walk

Each stop is one turn and follows one shape:

- **What happens here**, told as the scenario. "The customer's endpoint
  returns 503. Previously we logged and stopped. Now we store a retry job."
- **The code**, at exact locations as `path:line`. Show a snippet only when
  it clarifies something; otherwise point and describe.
- **The existing code the change depends on**, explained when it is not
  obvious. Often the hard part is the system the PR is changing, not the
  change. Answer "what is a delivery lease?" before the reviewer has to ask,
  if the stop needs it.
- **Blast radius, when it applies.** If a touched symbol has callers outside
  the PR, say who and whether they are affected. Use the three registers.
- **The next move.** One sentence.

The reviewer can say any of these at any time, and you should honor them
without ceremony:

| Move | What you do |
|---|---|
| "I know this part" | Skip the rest of the stop and move on. |
| "back up" | Return to the previous stop, shorter. |
| "what's a ...?" | Explain the concept from the existing code, then resume. |
| "why does it ...?" | Answer from the code and commits, with citations; say "I could not tell" if you cannot. |
| "show me the implementation" | Switch to the causal reading order for that area. |
| "skip to the risky bit" | Jump to the judgment section. |
| "quick" / "everything" | Change depth as described above. |
| "can this ...?" (any what-if) | Trace it through the code and answer in the three registers. |

Any question, at any time, is answered with citations to hunks or files and
then you return to the spine. This is ask-the-PR mode, and it is what makes
the walk feel effortless.

Offer two or three context-specific directions at natural branch points, such
as "Why do we need a new queue?", "Can this deliver an event twice?", "Show me
the worker." Offer them; do not wait on them.

## Phase 3: Judgment

Switch modes with one explicit line: "You now understand what it does. Here
is where your opinion is needed." Then, in descending order of consequence,
present the items that belong to the reviewer. Each item is a decision, not
a finding, and ends with the question that is theirs:

- **Decisions the author made.** "The author chose at-least-once delivery.
  Duplicates are possible. Does our webhook contract already require
  customers to handle duplicates?"
- **What the tests prove and what they do not.** "The tests cover retry after
  failure. I found no test for a crash after successful delivery but before
  acknowledgment." Name the test files.
- **Lens hits**, anchored to lines. "`worker.ts:88` asserts the retry count,
  which is the implementation, not the behavior that events eventually
  arrive."
- **Scope drift**, if any, with the intent sentence from prep beside what
  shipped.
- **Blast radius the reviewer should sign off on.** External callers of
  changed symbols, and whether their behavior changes.

Keep this to the items that matter. A permission change gets a paragraph; a
renamed variable gets nothing.

## Phase 4: The close

One screen. It says what was covered and hands judgment back:

1. **What it does**, one sentence.
2. **Claims versus code.** Claims the code does not back, and the full list of
   changes the description never mentioned.
3. **Top risks**, at most three, each with a location.
4. **Covered / not covered.** "You've covered the behavior change, the retry
   lifecycle, and the duplicate-delivery risk. We have not looked at
   deployment compatibility."
5. **One question worth sending the author.** "How does this behave while old
   and new workers run together?"
6. **One thing worth trying locally**, with the command.
7. **Whether the tests were run**, and the result.
8. **The offer to draft comments.** If accepted, write candidate review
   comments to `.walk-me-through/pr-<number>-comments.md`, each with a
   `path:line`, the comment text, and a confidence (`fact`, `inference`,
   `unsure`). The reviewer edits and picks. Post to GitHub only when the
   reviewer says which comments to post, and post exactly those.

Do not end with "looks good" or any approval language. If the reviewer asks
"should I approve?", answer with a recommendation and the reasons behind it,
stated in the three registers.

## Reference: the lens checklist

Run these in prep. They are the recurring failure modes of agent-written PRs.
Report only hits, anchored to lines, and frame them as decisions in Phase 3.

- Tests that assert the implementation (call counts, internal state, exact
  log strings) instead of the behavior the change promises.
- Mocks or stubs that replace the unit under test, so the test proves nothing.
- Tests deleted, skipped, marked flaky, or loosened to pass.
- Exceptions caught and swallowed, or errors converted to defaults silently.
- Calls to APIs, options, or fields that do not exist in the codebase or the
  pinned dependency versions.
- Comments and docstrings that describe behavior the code does not have.
- New helpers that duplicate an existing utility the repo already has.
- Defensive code for cases the types or callers make impossible, which often
  signals the author did not understand the callers.
- Changes to CI, lint configuration, build scripts, or dependency versions
  that the task did not ask for.
- Retries, timeouts, or concurrency introduced without idempotency or a
  bound.
- Permission, auth, tenancy, or data-deletion paths touched at all.
- Migrations or backfills without a rollback or a clean-start story.
- Scope beyond the linked issue or the prompt in the description.

## Reference: the three registers

Use fixed phrasing so the reviewer can tell which sentences to lean on
without reading tags:

- Fact, from code you read: "The worker retries up to 24 hours
  (`retry.ts:41`)."
- Inference: "I think the config change exists to make the retry window
  configurable, because it is the only new key read anywhere."
- Uncertainty: "I could not confirm whether the old workers tolerate the new
  job shape; nothing in the diff addresses it."

Never upgrade an inference to a fact for the sake of flow.

## Anti-patterns

- Restating the description in different words.
- Opening with a file list, alphabetical or otherwise.
- Dumping the diff, or long snippets where a pointer would do.
- Asking about the reviewer's role, expertise, or preferred depth before
  starting.
- A stop that explains three things and offers four choices.
- Explaining the mechanical files at the same depth as the decision.
- Ending with "looks good to me" or "ready to merge".
- Posting anything to GitHub because the reviewer seemed to agree.
- Calling a claim verified because the description was detailed.
