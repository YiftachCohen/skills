# Walk me through

An unfamiliar PR, a wall of generated code, and a description that assumes
you already know the system. Start here:

```text
/walk-me-through 123
```

Get your bearings: what this part of the product does, what changes, and
where your attention matters. The skill reads the implementation and turns
it into a short, concrete story you can reason about. The first explanation
stands on its own; conversation adds depth wherever you need it.

For example, a notification retry PR might become:

> When an order changes, this service notifies the customer's system. A
> timeout currently loses that notification; this PR saves it and retries.
>
> **Timeout → save the event → retry later.**
>
> Focus on duplicate delivery. The customer may receive the event even when
> their acknowledgment never reaches us. Reusing the event ID lets them
> recognize a retry, but they still need to ignore duplicates.

Real walkthroughs anchor that explanation to checked code and distinguish
what was verified from what remains uncertain.

## Installation

Claude Code:

```bash
npx skills add YiftachCohen/skills --skill walk-me-through
```

For Codex, link or copy the `walk-me-through` directory into your skills folder.

## Ask naturally

```text
/walk-me-through https://github.com/org/repo/pull/123
/walk-me-through quick version of #123, I have two minutes
/walk-me-through I have no context on #123; walk me through everything
/walk-me-through the description says no behavior change; what actually changes?
```

Say "back up", "I know this part", "show me the code", or "can this happen?"
whenever you need to. No command vocabulary to learn or required sequence of
"continue" replies. Ask for a step-by-step conversation if that suits you.

## What you get

- The missing background, explained as it becomes useful.
- Before/after behavior and a concrete path through the change.
- The consequential choices, their practical effects, and the evidence or
  protection present, so you can exercise your own judgment.
- Direction to the code worth reading and inspected areas you can skim.
- Material differences between the description and implementation, explained
  in terms of how they change your understanding.

A quick walk checks enough to support its explanation and names consequential
gaps. A full walk explains every meaningful part of the change. The skill reads
tests for what they establish and checks CI status; it runs local checks only when
requested or needed to answer a concrete what-if.

It can use isolated checkouts and local notes. It leaves PR code and GitHub
untouched, and recommends approval or changes only when you ask.

For a complete inventory of verified claims and unmentioned changes, use the
separate `pr-description-audit` skill. It is independently installable; an
ordinary walkthrough does not need it or launch it automatically.

The quality bar is simple: after the opening, you can explain what changes,
why it matters, and where to focus. See [the evaluation guide](evals/README.md)
for how that outcome is checked.
