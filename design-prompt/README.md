# Design prompt

Turn a rough description of something visual into one ambitious,
copy-pasteable prompt for a coding or design agent.

Based on Anshu Chimala's ["How to turn your AI into a world-class
designer"](https://www.lennysnewsletter.com/p/how-to-turn-your-ai-into-a-world)
(Lenny's Newsletter). The skill packages the article's techniques into the
prompt it writes: a committed creative direction instead of the model's
default, a random seed string for variety, explicit image generation, a
design-critic subagent loop scored out of 10, and a restraint pass that cuts
AI tells.

## Installation

```bash
npx skills add YiftachCohen/skills --skill design-prompt
```

## Usage

```text
/design-prompt landing page for my productivity app, not boring
/design-prompt redesign our settings screen, it looks like every SaaS
/design-prompt something tactile like an industrial control panel, but skeuomorphic looks tacky to me
```

The output is a prompt, not a design. Paste it into Claude Code, Codex, or
whatever agent builds the thing.

## What the generated prompt contains

- The build: product, audience, the one job it has, hard constraints.
- A concrete, committed direction, sharpened from the user's taste notes.
- A seed-string instruction for variety when no direction was given.
- Use real imagery over gradients and shapes when an image tool exists.
- A critic loop: fresh-context subagent, screenshot only, score out of 10,
  stopping threshold hidden from the critic.
- A restraint pass that removes what does not earn its place.
- Browser verification.
