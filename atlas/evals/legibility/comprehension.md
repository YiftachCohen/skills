# Comprehension protocol — is the map understood, not just correct?

Content accuracy is already graded (`--check`, `--edges`, `--inventory`). This
protocol tests the thing those can't: whether someone who
has **never seen the repo** can answer real questions about the system using
only the atlas. That is the property the user buys a map for, and on large
monorepos it is where maps fail even when every edge is true.

Three roles, three prompts, run as separate agents so no context leaks:

## 1. Question author (has the repo, never sees the atlas)

Spawn with access to the target repo only. It must not read `.atlas/`.

```
You are writing a comprehension exam about the repository at <REPO>.
Do not read anything under .atlas/. Investigate the repo directly.

Write 8 questions a senior engineer would ask about how this system fits
together, each answerable in one or two sentences. Cover: (1) what triggers a
given flow, (2) where a given kind of data ends up, (3) which external services
are involved in a flow, (4) what runs on a schedule, (5) at least one question
about the seam between two packages/apps if this is a monorepo. Avoid questions
about single functions or line-level details — this exam is about architecture.

Return ONLY raw JSON: [{"q": "...", "answer": "...", "evidence": "path:line"}]
The answer is the ground truth; evidence is where you confirmed it.
```

## 2. Cold reader (has the atlas, never sees the repo)

Spawn with the atlas artifacts only — copy `atlas.json` and the screenshots to
a temp dir so the agent cannot wander into the repo. The reader gets exactly
what a new teammate gets: the map.

```
You have never seen this codebase. Your ONLY sources are the attached
architecture map (atlas.json — nodes, edges, containers, details) and the
screenshot(s) of its rendered form at <DIR>. Do not search for or open any
other files.

Answer each question in one or two sentences. If the map does not contain the
answer, say "not on the map" — do not guess from general knowledge; a wrong
guess scores worse than an honest gap.

Questions: <QUESTIONS JSON, "q" fields only>

Return ONLY raw JSON: [{"q": "...", "answer": "...",
"basis": "node/edge ids you used"}]
```

## 3. Scorer

Score each answer against the author's ground truth (a third agent, or the
orchestrator with the answer key):

- **2** — matches the ground truth in substance
- **1** — partially right, or an honest "not on the map" for something the
  map genuinely omits (an omission is a *coverage* finding, not a legibility one)
- **0** — wrong, or "not on the map" when the answer is plainly there
  (that's a legibility finding: the information exists but can't be found)

Report `score / 16`, and split the misses: **coverage gaps** (map lacks it) vs
**legibility gaps** (map has it, reader couldn't find it). The second list is
the actionable one for this harness — each entry names information that is on
the map but effectively invisible.

**Pass bar:** ≥ 12/16 with zero legibility gaps on flow-trigger questions.

## Vision check (screenshots)

Separately, show `overview-*.png` (and `expanded-*.png` for the worst case) to
a grader agent with this rubric — one verdict per line, with the region named:

1. At fit zoom, are node labels readable, or do they need zoom to parse?
2. Are the four lanes (Entry → Services → Models → Data/External) visually
   discernible as columns?
3. Is there a hairball — a region where edges cross so densely that individual
   connections can't be followed? Name the nodes at its center.
4. Do always-on edge labels overlap each other or the edges under them?
5. In the expanded shot, can any single container's children be read as a
   group, or does expansion collapse into noise?

Feed the `stats.py` warnings to the grader as hypotheses to confirm or refute
by looking — the stats name the suspects (hubs, label ratio, dense regions);
the screenshot says whether they actually hurt.
