---
name: design-prompt
description: |
  Turn a rough request ("landing page for my productivity app", "redesign our
  settings screen", "a poster for the launch") into one ambitious,
  copy-pasteable design prompt for a coding or design agent, using the
  techniques from Anshu Chimala's "How to turn your AI into a world-class
  designer": a specific, bold creative direction instead of the model's
  default, a seed string for variety, a critic subagent loop scored out of 10,
  explicit use of image generation, and a restraint pass that strips AI tells.
  Use this whenever the user wants a prompt, brief, or spec for something
  visual: "write me a prompt for a landing page", "give me a design brief",
  "how should I prompt Claude Code to design X", "make the design less
  generic", "this looks like AI slop, write a better prompt", or when they
  describe something they want designed and ask for the prompt rather than the
  build. The output is a prompt, not the design itself.
allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
---

# Design prompt

The deliverable is a prompt the user pastes into a coding or design agent. Do
not build the design. Do not write code.

## Why the prompt matters

Models are next-token predictors trained toward safe, consistent choices. Left
alone, every landing page comes out the same: purplish gradient, text left,
graphic right, a few glows. Great design does the opposite. It bends a rule and
produces an emotional response. A generic request gets the 1% default. A
prompt that commits to a direction, injects variety, and sets up an objective
critic gets the other 99%.

## Read the input

From what the user gave you, pull out:

- What is being designed and for whom (product, audience, the one thing it
  must accomplish).
- Hard constraints: framework, existing design system, brand colors, copy that
  must appear, accessibility, deadline.
- Taste signals: anything they liked, disliked, or reacted to. These are the
  most valuable input. The user's reactions are what make the result something
  only they could have made.
- What tools the target agent has: image generation, a browser for
  screenshots, subagents. Assume Claude Code with subagents and a browser
  unless told otherwise. Do not assume an image generation key.

If the request is a one-liner, do not stall. Fill gaps with your judgment and
say what you assumed at the end.

## Pick a direction

The default output of a model is the average of everything. The prompt must
name a direction ambitious enough that the agent cannot fall back on it.

If the user gave a direction, sharpen it: make it more specific, more
physical, more committed. "Industrial control panel" becomes "tactile,
clicky components, texture instead of flat gray gradients, a restrained accent
color, no skeuomorphic cartoon."

If they gave none, always show four to six candidate directions in one line
each, above the prompt (the kind of thing that sounds like it should not work:
pixel-art stills from a video game, an isometric living city where features
are buildings, a radically asymmetric layout with dissonant type that still
looks good). Then write the full prompt for the one you would pick and say
why. The list is not optional even when running unattended: the user's
reaction to the options is the input that makes the next version theirs. If
you are in an interactive session and the choice would change the prompt
substantially, ask instead of guessing.

Ideas that sound terrible are the right kind. If you think "there is no way
this works," keep going.

## Write the prompt

Produce a single fenced block the user can copy. Cover, in prose or short
sections, whatever of the following applies. Skip anything the input makes
irrelevant. A prompt that is 80% boilerplate is a worse prompt.

1. **The build.** What, for whom, the one job it has, and the hard
   constraints. One short paragraph.

2. **The direction.** The committed aesthetic, described concretely enough
   that two runs would look like siblings. Include the user's taste notes
   verbatim where they are specific ("skeuomorphic feels tacky, avoid it").

3. **A seed for variety** when the user wants surprise or gave no direction.
   Use the article's technique: have the agent generate a long random
   alphanumeric string with a shell script, derive the creative direction
   (palette, layout, type) from patterns in the string, look beyond the
   surface for sub-patterns and special numbers, bring it to life with its
   own judgment, and never reveal the string in the design. Omit this when
   the user has already chosen a direction and wants it executed.

4. **Real imagery, not decoration.** Agents default to gradients, shapes,
   and pattern fills because they under-use image tools, and those are the
   most obvious AI tells. If the target agent has image generation, tell it
   to use it for personality, and to consider shaders or 3D effects combined
   with images. If it needs an API key, tell it to keep the key in a
   gitignored `.env.agents` file and never in shipped code. If no image tool
   exists, say so and ask for restraint over fake richness.

5. **The critic loop.** This is the part agents will not do on their own,
   because an implementer cannot zoom out and defends its past decisions.
   Include it close to this wording:

   > To decide what to improve, use a separate subagent as a design critic.
   > Use the strongest model available for the critic; it only sees
   > screenshots, so it costs little. At each iteration: take a screenshot
   > of the current design. Invoke the critic in a fresh context with only
   > the screenshot, not the code, implementation details, or earlier
   > critiques. Ask it to name the aesthetic the design is going for, imagine
   > how a top design studio would execute that aesthetic, and outline the
   > biggest gaps in structure and composition and in fine detail. It should
   > flag anything overdone, excessive, or obviously AI-generated. It should
   > be tight, specific, bold, and opinionated. Finally it scores the design
   > out of 10 against that studio-level bar. Stop when the score reaches
   > 9 or after N iterations, whichever comes first. Do not tell the critic
   > the stopping threshold.

   Pick N (usually 4 to 6). If the user has reference images, tell the agent
   to give them to the critic as the quality bar.

6. **The restraint pass.** AI loves adding more; restrained design reads as
   premium. End the prompt with a pass that removes what serves no purpose:
   glows, gradients, and effects that carry no meaning; random accent colors
   and highlights; redundant labels that over-explain; custom components
   that are worse than the native ones; containers and empty space that do
   no layout work. Frame it as "cut everything that does not earn its place"
   rather than a checklist to tick.

7. **Verification.** Open it in a browser and check every state and
   breakpoint frame by frame before calling it done.

## After the block

Under the prompt, in two or three lines: what you assumed, and which of the
listed directions you would try second. Nothing else. Do not explain the
techniques to the user; the prompt speaks for itself.

## Examples of direction sharpening

Input: "landing page for my productivity app, make it not boring"
Direction: "Each section is a still from a bold pixel-art video game, yet the
whole thing still reads and functions as a landing page. Chunky type, limited
palette, real illustrated scenes, no gradients."

Input: "settings screen, it looks like every other SaaS"
Direction: "Apple-native minimalism. Image-centric grid, native controls,
no containers around containers, typography does all the hierarchy work.
The goal is to remove until it looks expensive."

Input: "I want something tactile, like an industrial control panel, but the
skeuomorphic stuff looks tacky to me"
Direction: "Industrial control panel: consistent tactile components, clicky
satisfying interactions, texture instead of flat gray gradients, one live
accent color. No cartoon skeuomorphism, no fake screws or bevels."
