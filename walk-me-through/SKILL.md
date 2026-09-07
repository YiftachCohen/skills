---
name: walk-me-through
description: |
  Make an unfamiliar pull request understandable: explain the missing context,
  what changes, and where the reviewer's judgment matters. Use when the user
  asks to be walked through a PR, is overwhelmed by a large or AI-written diff,
  or wants to understand a PR before approving it. Explain material mismatches
  with the description as part of the story.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
  - Agent
---

# Walk me through

**Turn an unfamiliar PR into a small, understandable story. Give the reviewer
their bearings early, carry the background context for them, and bring them
to the few choices that deserve their judgment.**

The intended feeling is relief: "Oh, that's what this does. Now I know where
to look." Assume a capable engineer who has no context on this area and little
attention to spare. Each explanation should make the next piece easier to
understand. The first answer must be useful even if they never reply.

## Start with a verified foothold

The first user-facing message is the verified explanation itself. Begin
without asking about role, expertise, or preferred depth.

1. Resolve the PR using `gh`, the runtime's GitHub tools, or a supplied local
   PR record. Pin the base and head commits and inspect the full diff shape.
   Use an isolated worktree or `git show` to read the pinned files without
   switching the user's checkout. If only partial artifacts are available,
   explain what they establish and name the access needed for the rest.
2. Read enough surrounding implementation at base and head to explain the
   affected system's job, the problem, and the main behavior change. Follow
   the entry point, changed core logic, and relevant callers. Descriptions
   and issues suggest intent; code establishes behavior.
3. Scan all changed paths and hunks for separate consequential changes,
   especially permissions, data loss, migrations, dependencies, and CI.
   A mechanical label needs evidence: generated output and tests can contain
   consequential changes too. Identify the main scenario and the likely
   review focus; qualify anything not yet traced.
4. Once the system's job, main before/after, concrete path, and consequential
   review focus are verified, deliver the foothold. For a quick or default walk,
   finish there unless unresolved evidence could change the explanation or the
   reviewer's judgment.

A foothold has enough context to stand alone. Usually a few short paragraphs
(roughly 150–250 words) can carry:

- **The system's job and the change.** Introduce the affected part in everyday
  product terms, then before/after behavior and the problem it addresses.
  Explain a necessary term before using it; implementation names come later.
- **One concrete path.** Follow an event, request, or piece of data through
  cause and effect. A small arrow chain or diagram helps when it removes
  prose. For a refactor or tooling PR, explain the responsibility or workflow
  that changes; establish behavior preservation only to the extent checked.
- **Where to focus and why.** Identify the most consequential choice and its
  practical consequence, with one or two useful code anchors. Mention which
  areas can be skimmed only when inspected. Several independent changes may
  need a compact map; do not invent one unifying story or a risk for a trivial PR.
- **A material caveat, if needed.** Surface a description discrepancy or
  unchecked area when it affects this explanation or the review decision.
  A caveat names what is unverified; it never certifies the rest. Keep minor
  omissions and administrative details in notes.

This is a complete small explanation, not a teaser followed by "continue?".
For a longer requested walk, deepen it in the same turn or at the user's pace.
The final answer stands alone and incorporates what was learned. For a
quick request, the foothold can be the entire
answer, including any consequential uncertainty. Match investigation depth to
the requested scope; never imply that a quick account is a completed audit.

## Deepen only where it helps

By default, finish the compact story and its review focus in the first turn.
Choose any further investigation by whether it could change that story or
the reviewer's judgment. Follow relevant callers, tests, and failure paths;
read [references/investigation.md](references/investigation.md) for a broader
walk or a consequential uncertainty that needs tracing.

When asked for "everything", explain every meaningful part of the change in
causal order, grouping plumbing and repetition. Finish when the explanation
faithfully covers the requested changes, the important choices, and any
consequential uncertainty. The reviewer need not keep typing "continue".

If asked whether the description gives the wrong picture during a walk,
explain the material mismatches and actual behavior. Accounting for every
claim and omission is a separate task; an ordinary walk never starts it.

Carry one scenario through the explanation. At each useful stop, connect what
happens, the existing behavior it depends on, and why the change matters.
Introduce only the code needed for that connection; snippets earn their place
when they clarify a decision. Keep citations near supported claims without
making the prose read like a file index.

Adapt to ordinary language. "Back up" means explain the prerequisite more
simply; "I know this part" means skip it; "show me the code" means open that
part of the causal path; "can this happen?" means trace that case. Answer the
question fully, then connect it back only if useful. A plain "continue" takes
the most useful next step without repeating the setup. Mention at most one
natural follow-up when helpful; a command menu is unnecessary. Pause between
stops when the user explicitly wants an interactive, step-by-step walk.

## Carry the reasoning to the decision

For each consequential point, explain **the choice → the concrete consequence
→ the protection or evidence present → the remaining uncertainty or decision**.
Prioritize by impact and reachable behavior. A question for the reviewer comes
after this reasoning, when their product or engineering judgment is needed.
State an established defect directly rather than disguising it as a question.

For example: "Retrying reduces lost notifications. If the customer received an
event but its acknowledgment was lost, retrying can deliver it twice. The same
event ID is reused, but this code cannot ensure the customer ignores duplicates.
The decision is whether requiring customers to deduplicate is acceptable."

Make test evidence specific: what scenario the assertions cover, and which
consequential scenario remains unchecked. Read tests; take reported execution
status from CI for the pinned head, marking missing or stale status honestly.
Run a local check only when requested or when it is the fastest safe way to
answer a concrete what-if. Green CI alone does not establish a behavior claim.

Finish once the reviewer can explain what changes and where to focus. For a
long walk, leave a short takeaway with the few consequential open points and
the best next action, if one is warranted. Suggest an author question or local
command only when it resolves an actual uncertainty; verify any command from
the repo and make clear if it was not run. For a short answer, the explanation
already serves as the close. Let the reviewer decide whether they understand.

## Evidence and boundaries

- Ground behavior claims in implementation you read. Distinguish observed
  facts, reasoned inference, and uncertainty in natural language. State why
  you infer intent; code shape alone does not establish the author's motive.
  A PR description may be accurate, incomplete, or wrong: check it without
  assuming which. Scope drift needs evidence of the requested scope.
- Before writing a `path:line`, re-read that line at the pinned revision and
  confirm it supports the claim. Identify base-revision citations explicitly;
  ordinary citations refer to head. If no stable line can be verified, describe
  the location in words; an approximate line reference is not a citation.
  Re-read any citations returned by another agent.
- Record notes when the investigation benefits from them in
  `.walk-me-through/pr-<id>.md` in the worktree; first add `.walk-me-through/`
  to the file returned by `git rev-parse --git-path info/exclude`. Preserve
  existing exclusions and leave `.gitignore` alone. Include inspected scope, unchecked areas,
  base/head IDs, and relevant evidence. Notes are optional for a compact walk.
  Citations saved in notes follow the same re-read rule as citations in the
  answer; verify with `git show` if no matching worktree exists.
- Keep the full investigation behind the explanation. Never claim the whole
  description matches, all callers are safe, or an area can be skipped beyond
  the scope actually checked. Finding no mismatch in what you read is not the
  description checking out: say what you compared. Expose gaps plainly.
- Explain tradeoffs and prioritize attention freely. Recommend approve or
  request-changes only when asked, with reasons and remaining uncertainty.
  Leave PR source code untouched locally and remotely. Never post, comment,
  review, or push on GitHub. Local notes and isolated read-only checkouts
  support the walk; the reviewer owns the PR.

## Example of the experience

Illustrative only; a real answer needs verified code anchors and actual evidence:

> This service tells customers' systems when an order changes. Today, a
> temporary outage on their side can lose that notification. This PR saves
> failed deliveries and retries them.
>
> The path is **delivery fails → save it → retry later**.
>
> The part worth your attention is duplicate delivery: the customer might
> receive an event even though we never receive their acknowledgment. A retry
> could send it again. The retry keeps the event's ID, so the customer can
> recognize a repeat, but we cannot make their system ignore it.
>
> Focus on the worker's retry decision and the receiving-system contract.
> The generated client changes follow the schema and can be skimmed. I checked
> that path; the deployment configuration is still unchecked.
