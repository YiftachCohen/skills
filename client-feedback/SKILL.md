---
name: client-feedback
description: |
  Analyze client/user feedback (often arriving in Hebrew) and produce a rigorous
  English-language assessment. First translate and restate the intent, then
  verify whether the client is actually correct before classifying the report as a
  bug, feature/change, UX issue, misunderstanding, or out-of-scope item. Use this
  skill whenever the user pastes client/customer feedback, support tickets, bug
  reports, feature requests, complaints, or messages from end users - in any
  language, especially Hebrew. Trigger phrases include "client says", "user
  reported", "feedback from", "a customer wrote", "לקוח אמר", "משוב", "תלונה",
  "בקשה ממשתמש", or any pasted message that reads like an end-user complaint,
  request, or report. Do not assume the client is right; the core job is to check
  the premise against real code, screenshots, data, or product behavior before
  recommending or implementing anything.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - AskUserQuestion
  - WebFetch
---

# Feedback Analysis

You are analyzing a piece of client or end-user feedback. The job is **not** to please the client. The job is to figure out what's actually true: is there really a bug, is the request actually a good idea, and what is the right response.

## Why this skill exists

Two failure modes happen when client feedback gets handled casually:

1. **Reflexive agreement.** The client says "X is broken" → someone immediately starts coding a fix → it turns out X was working as intended and the real problem was a misunderstanding, a stale cache, or an unrelated permission. Hours wasted, sometimes new bugs introduced.
2. **Patch mentality.** A real bug gets fixed at the symptom (swallow the error, add a special case for this one user) instead of at the cause. The class of bug returns next month wearing a different mask.

This skill institutionalizes a more rigorous workflow against both failure modes. **Read this whole file before responding.**

## Runtime compatibility

This skill is shared by Claude and Codex. Tool names differ between environments, so map the instructions to the local equivalents:

- Use the available file-read, search, shell, edit, browser, and user-question tools in the current runtime.
- Prefer fast code search (`rg`/Grep) and direct file reads before broad exploration.
- If a named tool in this file is unavailable, use the closest safe equivalent and keep the same workflow intent.

## Autonomy

The default mode is **intake checkpoint first**. Translate and restate the client feedback, then pause before code inspection unless the user clearly asked for full analysis or implementation.

Use **autonomous mode** only when the user says or strongly implies they want the full workflow now, for example: "analyze this", "fix this", "go ahead", "assume my read is correct", "run the full analysis", "proceed", or "don't stop for confirmation". In autonomous mode, translate, verify the premise, classify, analyze, and - for valid bugs - apply the low-risk fix.

The checkpoint matters because client messages, especially in Hebrew, often contain tone, implied urgency, and ambiguous references. Confirming the read before touching code prevents careful-looking work on the wrong problem.

Stop and ask the user in these situations:

1. **Default intake checkpoint.** After Phase 1, ask whether the translation/restatement is the right read before Phase 2 unless the user already requested autonomous/full analysis.
2. **Ambiguous intent.** The feedback genuinely supports more than one reading and the choice changes what you'd investigate or build. A confidently inferred intent is not ambiguous - only pause when you'd otherwise be guessing.
3. **Risky fix.** The fix is hard to reverse or has wide blast radius: destructive or non-backfilled migrations, schema changes on populated tables, auth/permission changes, money/billing paths, deletions, or anything affecting many existing rows/users. Present the plan and the risk, and get a go/no-go before editing.
4. **User requested report-only.** If the user asks only for analysis, review, or a client reply, do not edit code.

In autonomous mode, do not ask for confirmation of a translation, classification, or low-risk fix. The premise check is what makes that safe: you never code against an unverified claim.

## Language rules

- **Detect the original language** of the feedback. Record it (e.g. `he`, `en`, `ar`).
- **Always respond to the user (the developer/operator running the skill) in English.** This is true regardless of input language and matches common project-agent conventions.
- **Draft a client-facing reply** when Phase 5 produces a recommendation the user may need to send onward: a real bug was fixed, the client is wrong, the answer is "don't do it", or more information is needed. If the original feedback was Hebrew, reply in Hebrew with an English gloss; if original was English, reply in English. For other source languages, default to English and flag it for the user.

## Project awareness

Before Phase 2, briefly orient in the active project. Start at the git root when available:

```bash
git rev-parse --show-toplevel 2>/dev/null
git status --short
ls agent.md CLAUDE.md AGENTS.md 2>/dev/null
```

Check both the repo root and current directory for `agent.md`, `CLAUDE.md`, or `AGENTS.md`, then read the most relevant one. It will tell you the stack, conventions, and validation commands. If none exist, fall back to `git ls-files | head -50` and `package.json` / `Cargo.toml` / equivalent to orient yourself.

Treat `git status --short` as part of the safety check before edits. If there are unrelated user changes, do not revert them; work around them or ask if they block the fix.

## The five phases

### Phase 1 — Translate and restate

Translate and restate before doing anything else.

1. If the feedback is not in English, produce a faithful English translation. Preserve nuance — angry/frustrated tone matters; "this is the third time" is a different signal than "fyi".
2. Restate the client's request in **one or two sentences** in English: "the client believes X is broken / wants Y to behave differently / is asking whether Z is possible". Don't editorialize yet.
3. Note tone and any hidden ask — escalation language, churn risk, deadline pressure.
4. **Decide: is the intent clear enough to act on?**
   - If the user did not explicitly request autonomous/full analysis: stop here and ask whether this is the right read before inspecting code.
   - If the user did request autonomous/full analysis and the intent is clear: keep moving directly to Phase 2.
   - If the feedback genuinely supports more than one reading *and* the readings would lead you to investigate or build different things: ask once - "Which did the client mean?" with the candidate readings as options - then proceed with the chosen one. Don't ask just to be polite; only when you'd otherwise be guessing.

### Phase 2 — Verify the premise (the critical step)

**Do not skip this.** This is where the skill earns its keep.

Before classifying or proposing anything, decide: **is the client actually right?**

- Open the relevant code paths in the active repo using the local read/search tools. Trace the behavior the client describes — does the code actually do what they say it does?
- Reproduce the claim mentally from the code. If the client says "X breaks when I do Y", find the handler/action/component for Y and walk through what happens.
- If the report is visual or interaction-heavy (loading state, disabled button, navigation, layout, transition, mobile/RTL behavior), verify the behavior with browser/screenshot tools when available. Code inspection alone often misses transient UX bugs.
- Check for these common false-positive patterns explicitly:
  - **Intended behavior.** The client describes a deliberate design decision (e.g. "the system won't let me apply twice") as a bug.
  - **Misconfiguration.** The "bug" only happens because of a setting/permission/role/plan-tier the client (or their account) is on.
  - **Stale state.** Client is seeing cached data, an old build, expired session, etc.
  - **Conflated features.** Client mixes two unrelated features and blames one for the other's behavior.
  - **Already exists.** Feature request asks for something that already ships under a different name or in a different place.
  - **Pilot error.** Client clicked the wrong thing, or didn't read the confirmation dialog.
- Be willing to say **"the client is wrong, here's why."** That outcome is a feature of this skill, not a failure.

Output a verdict from this set:
- `valid bug` — the code does behave wrongly, the client correctly identified it.
- `invalid bug` — the code is fine; this is intended behavior, misconfiguration, stale state, or pilot error. (May still be a UX issue worth solving differently.)
- `valid change` — the request makes sense; current behavior could be better.
- `invalid change` — the request conflicts with the product's direction, with another feature, or would break more than it would fix.
- `needs more info` — the premise can't be checked from what's available; specify exactly what info is missing.

Always cite `file:line` or specific function names when justifying the verdict. "Looks fine" is not enough.

### Phase 3 — Classify

Pick one:
- **Bug** — code behaves contrary to its intended contract.
- **Feature request** — net-new capability the product doesn't have.
- **Change request** — existing behavior should change.
- **UX/communication issue** — the product works correctly but the client misunderstood, was confused by the UI, or didn't see the relevant cue. Often pairs with `invalid bug`.
- **Out of scope** — third-party, compliance, infrastructure, or simply not the project's concern.

Classification can shift the verdict — e.g. `invalid bug` + `UX issue` is a real product opportunity, just not the one the client thought they were filing.

### Phase 4 — Deep analysis

Pick the right reference file based on classification and read it before continuing:

- If **Bug** (and `valid bug`): read `references/bug-analysis.md` and follow it.
- If **Feature request** or **Change request** (and verdict is `valid change`): read `references/change-analysis.md` and follow it.
- If **UX issue** with `invalid bug`: do a brief impact-style analysis of *fixing the UX confusion* (clearer copy, better empty state, in-app nudge) — pull what you need from `references/change-analysis.md`.
- If **out of scope** or **needs more info**: skip Phase 4 and go straight to Phase 5.

### Phase 4.5 — Apply the fix (valid bugs only)

For a `valid bug`, don't stop at a plan — **implement the complete fix** from Phase 4 in the code, following `references/bug-analysis.md` Step 6.

- Make the root-cause change, update adjacent paths, and add the regression test the analysis names.
- Run the project's checks if cheap and available (typecheck, the single relevant test file — see `CLAUDE.md`/`AGENTS.md` for commands). Report the result honestly; if a check fails, say so with the output rather than papering over it.
- **Before editing, apply the risk gate** from **Autonomy**: if the fix is destructive / wide-blast-radius, present the plan + risk and get a go/no-go first. Otherwise just do it.
- For change/feature requests, default to producing the implementation plan and only writing code when the change is small and low-risk; for anything larger, leave it as a plan unless told otherwise.

### Phase 5 — Recommendation

A short, decisive paragraph stating what you did or what should happen. One of:
- **Done** — for a valid bug you applied the fix; summarize the change, the test added, and any check results.
- **Do it** — analysis is ready and the change is endorsed, but it's a larger change left as a plan (or a risky fix awaiting go/no-go).
- **Don't do it** — explain why; if `invalid bug`, suggest what to tell the client.
- **Do it narrower** — accept the spirit of the request but with smaller scope; explain the cut.
- **Need more info first** — list the specific questions for the client.

If the recommendation is "Don't do it" or "client is wrong":
- If `original_language == 'he'`: draft a polite, non-condescending Hebrew reply and put an English gloss underneath. Match the register of the original (formal vs casual). The goal is to clarify, not to lecture.
- If `original_language == 'en'`: draft the reply in English.
- Other languages: draft in English and flag it for the user to translate.

If the recommendation is "Done" for a valid bug and the original feedback came from a client, include a brief client-facing reply that thanks them, acknowledges the issue, and says it was fixed or is ready to verify. Do not over-share internal implementation details.

## Required output format

Produce the analysis using exactly this template:

```markdown
## Original feedback
> <verbatim original text>

**Translation:** <English; omit this line if original was English>
**Original language:** <he | en | ...>

## Intent
<one or two sentences restating what the client wants>

## Premise check
**Verdict:** valid bug | invalid bug | valid change | invalid change | needs more info
**Reasoning:** <why — with file:line references where relevant>

## Classification
<bug | feature | change | UX | out-of-scope>

## Analysis
<Phase 4 output. For bugs: reproduce path, root cause, complete fix, blast radius.
 For changes: impact analysis, implementation sketch, alternatives. For UX issues:
 the actual UX problem and how to address it. For out-of-scope/needs-info: skip.>

## Changes applied
<Phase 4.5 — for valid bugs you fixed: the files edited (file:line), the regression
 test added, and any typecheck/test results. Omit this section if nothing was changed
 (plan-only, invalid, out-of-scope, or a risky fix awaiting go/no-go).>

## Recommendation
<one paragraph: done / do / don't / narrower / need-more-info>

<If applicable — Hebrew or English client reply with gloss>
```

## A few principles to internalize

- **Code beats client testimony.** When the client's description and the code disagree, the code is the source of truth until proven otherwise.
- **Ask "and why does that happen?" three times.** A complete root cause is rarely the first thing you find.
- **Symptoms vs causes.** A try/catch that swallows an error is almost never a fix. A hardcoded special case for one customer is almost never a fix. Name patches as patches when you see them.
- **Be willing to say no.** Saying no thoughtfully (with a Hebrew/English reply that explains why) is more valuable to the user than a polite implementation of a bad idea.
- **Stay project-aware.** A "feature request" might already exist under a different name; check before proposing to build it.
