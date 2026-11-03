# Arcs

The order of sections for each page type. Every arc ends with a Questions section (`.qa`), filled from the comprehension check with answers your sources hold; leave it out when they hold none. Each arc answers the reader's first question first. Many pages are two types at once (the example is a showcase that ends in a proposal): take the first arc and append the second arc's closing sections.

## Showcase

The reader asks: *what changed, and does it work?*

1. **Masthead.** The headline is the result for its users ("Admin search now answers in 38 milliseconds"). The deck says who it is for and what they did before. The facts hold status, where it runs and the PR.
2. **See it.** One figure of the moment that changed, usually a stageshow animation. The caption says what to notice.
3. **Proof.** Before and after numbers in `table.metrics`, with their window and source. Include the cost row.
4. **How it works.** Short: a diagram or a few steps, enough for an engineer to judge the approach.
5. **What's next.** Rollout, follow-ups, known limits.

The usual failure is a feature tour. One moment, shown well, carries a showcase.

## Proposal

The reader asks: *what are you asking me to decide, and by when?*

1. **Masthead.** The headline is the question or the recommendation. The facts hold the ask, the deadline and who decides.
2. **The problem.** What hurts today, measured where possible. One worked example of the pain.
3. **Options.** Each option gets an `.option`: when it ships, what it gives and what it costs. Include doing nothing when it is a real option. Mark one `data-recommended`.
4. **Why the recommendation.** The deciding factor in one paragraph, then the evidence.
5. **Risks and open questions.** In a `.note` or a short list, each with what would resolve it.

The usual failure is options written to lose. Give each option its strongest honest case.

## Architecture

The reader asks: *what does the system look like, and what are you changing?*

1. **Masthead.** The headline names the change and its reason ("Move job dispatch off Postgres polling to stop connection exhaustion").
2. **Today.** A diagram of the current system, with the problem marked `.focus`.
3. **Proposed.** The same diagram after the change, in the same layout, so the difference is visible at a glance.
4. **What changes.** Data flow, failure modes, migration path, operational cost.
5. **Open questions.** What the team should weigh in on.

The usual failure is two diagrams in different layouts. Keep node positions fixed between before and after.

## Metrics

The reader asks: *are things better or worse, and why?*

1. **Masthead.** The headline is the finding, not the period ("Pages to on-call fell by 62% in Q3", not "Q3 reliability report").
2. **The numbers.** `.stats` for the three or four that matter, then `table.metrics` for the rest, with `.good` and `.bad`.
3. **Why they moved.** One section per real cause, each tied to the numbers it moved.
4. **Regressions.** Every number that got worse, with its cause and what is being done.
5. **Next.** Targets for the next period.

The usual failure is numbers without causes. Every big move gets a reason, or is marked unexplained.

## How it works

The reader asks: *how does this work, well enough that I could debug it?*

1. **Masthead.** The headline states how it works in one sentence ("Search runs in the browser against an index the server streams to it").
2. **One request, end to end.** Follow one concrete case through the system: a real input, each hop, the output. A diagram or a stageshow figure carries it.
3. **The parts.** Each component, what it owns and where it lives in the code.
4. **Edge cases.** What happens on failure, at scale, with stale data.
5. **Where to look.** Files, dashboards, runbooks.

The usual failure is describing components before the reader has seen them work. The worked example comes first.
