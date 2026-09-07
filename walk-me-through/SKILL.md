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
  - Agent
---

# Walk me through

**Turn an unfamiliar PR into a small, understandable story. Give the reviewer
their bearings, carry the background context for them, and bring them to the
few choices that deserve their judgment.**

Assume a capable engineer with no context on this area and little attention
to spare. The first message is the explanation itself, useful even if they
never reply. Do not ask about role, expertise, or preferred depth.

## Investigate before explaining

Pin the base and head commits and read them in an isolated worktree or with
`git show`, without switching the user's checkout. Read enough surrounding
implementation at both revisions to explain the system's job, the problem,
and the main behavior change: entry point, changed core logic, relevant
callers. Descriptions and issues suggest intent; code establishes behavior.
A description, the user's included, may be accurate, incomplete, or wrong:
check it without assuming which.

Triage the whole diff for separate consequential changes, especially
permissions, data loss, migrations, dependencies, and CI. "Mechanical" needs
evidence: generated output and tests can carry consequential changes too.

Match depth to the request. A quick walk checks enough to support its story
and names what it did not check. "Everything" means every meaningful change in
causal order, with plumbing grouped. Deepen further only where it could change
the story or the reviewer's judgment; see
[references/investigation.md](references/investigation.md) for tracing a
broader walk or a consequential uncertainty. If only partial artifacts are
available, explain what they establish and name what access would resolve.

## The foothold

A few short paragraphs that stand alone, not a teaser followed by "continue?".
Keep the investigation behind the explanation: what you verified shows up as
confidence and specific caveats, not as a log of counts, sweeps, and checks.
Every fact in the story stays exact; shorten by leaving bookkeeping out, not
by compressing facts together. Say what was not checked in one sentence.

- **The system's job and the change.** The affected part in everyday product
  terms, then before/after behavior and the problem addressed. Explain a
  necessary term before using it; implementation names come later.
- **One concrete path.** Follow an event, request, or piece of data through
  cause and effect. An arrow chain helps when it removes prose. For a refactor
  or tooling PR, explain the responsibility or workflow that changes.
- **Where to focus and why.** The most consequential choice, its practical
  consequence, and one or two code anchors. Call an area skimmable only after
  inspecting it. Several independent changes get a compact map; do not invent
  one unifying story, or a risk or a verdict for a trivial PR.
- **A material caveat, if needed.** A description discrepancy or unchecked
  area that affects the explanation or the review decision. A caveat names
  what is unverified; it never certifies the rest. Minor omissions and
  bookkeeping stay out of the story.

Carry one scenario through. At each stop, connect what happens, the existing
behavior it depends on, and why the change matters. Snippets earn their place
when they clarify a decision. Follow the user's questions without restarting
the walk: answer the question fully first, then connect it back only if
useful. No command menu; pause between stops only when they ask for
step-by-step.

## Carry the reasoning to the decision

For each consequential point: **the choice → the concrete consequence → the
protection or evidence present → the remaining uncertainty or decision**.
Prioritize by impact and reachable behavior. A question for the reviewer
comes after this reasoning, when their judgment is needed. State an
established defect directly rather than disguising it as a question.

> Retrying reduces lost notifications. If the customer received an event but
> its acknowledgment was lost, retrying can deliver it twice. The same event
> ID is reused, but this code cannot ensure the customer ignores duplicates.
> The decision is whether requiring customers to deduplicate is acceptable.

Make test evidence specific: what the assertions cover and which consequential
scenario remains unchecked. Read tests; take execution status from CI for the
pinned head, and say when it is missing or stale. Green CI does not establish
a behavior claim. Run a local check only when asked or when it is the fastest
safe way to answer a concrete what-if.

Suggest an author question or local command only when it resolves a named
uncertainty; verify the command against the repo and say it was not run.
Finish once the reviewer can explain what changes and where to focus; a long
walk ends with the few open points.

## Evidence and boundaries

- Ground behavior claims in implementation you read. Distinguish observed
  facts, inference, and uncertainty in natural language. Say why you infer
  intent; code shape alone does not establish motive. Calling something
  scope drift needs evidence of what was requested.
- Before writing a `path:line`, re-read that line at the pinned revision and
  confirm it supports the claim. Mark base-revision citations explicitly. If
  no stable line can be verified, describe the location in words. Re-read
  citations returned by another agent.
- Never claim the whole description matches, all callers are safe, or an area
  can be skipped beyond what you checked. Finding no mismatch in what you read
  is not the description checking out: say what you compared.
- Recommend approve or request-changes only when asked, with reasons and
  remaining uncertainty. Leave PR code untouched. Never post, comment, review,
  or push on GitHub. The reviewer owns the PR.

## Example of the experience

Illustrative only; a real answer needs verified code anchors:

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
