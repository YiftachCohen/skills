# Comprehension check

The prompt for the fresh subagent that reads a built page. Build with `--check` first: it writes `dist/page.txt` (the page's text in reading order) and `dist/page.first-screen.png` (what a reader sees before scrolling). Give the subagent those two paths and nothing else: not the conversation, not the source files, not the brief. A reader who knows the brief fills its gaps and passes a page that fails. A smaller model is fine for this.

```text
You are reading a page written for a team of engineers, a technical lead and a
product manager. Use only these two files.

Look at <FIRST-SCREEN PNG> first. From that image alone:
1. In one sentence, what is the page's main claim?
2. What, if anything, is the reader being asked to do, and by when?

Then read <PAGE TXT>, the whole page as text:
3. Explain in three sentences how the thing works, as you would to a colleague.
4. What does it cost, what got worse, or what is still risky?
5. If you had to decide what the page asks, what would you decide, and why?
6. As the product manager: quote any sentence you could not follow.
7. As an engineer: what technical question does the page leave unanswered?

Answer from the page alone. Where the page does not say, write "not on the page".
Reply with the seven numbered answers only.
```

## Judging the answers

Compare them with the claim and the ask written down in step 1 of the skill.

- **Pass:** answers 1 and 2 match the intended claim and ask from the first screen alone. Answer 3 is correct. Answer 4 names the real cost. Answer 5 weighs the tradeoffs the page meant to show.
- **Answers 6 and 7 are triage, not a to-do list.** A reader can always ask one more question. Fix a gap only when it would change the claim, the ask or the decision, or when a skimmer would stop on it in the headline, the deck or a first sentence. Technical terms in diagrams and in depth sections stay; the audience is mostly engineers. The rest are questions the team is likely to ask: answer the ones your sources cover in the closing Questions section, and list the others in the handover.
- **Fix** each mismatch at its source: a first screen that misses the claim needs a new headline or deck, not a later paragraph. An unanswered technical question gets a sentence, or a link to where it is answered.
- **Run it again only if answers 1, 2 or 5 missed.** Rebuild with `--check` and send a fresh subagent. If anything still fails, hand over anyway and list the remaining gaps for the user.
