# Evaluate understanding, not template compliance

Use `evals.json` for request cases. Cases 10 and 12 name real PRs in
`YiftachCohen/skills`; resolve and record their exact base/head revisions.
Other cases need matching supplied PR artifacts: description, intent if
available, base/head trees, and CI status if available. Keep those inputs
identical when comparing skill versions. A prompt alone is not a runnable
fixture and expected output is not evidence.

## Run and inspect

Give the executing agent the skill, user prompt, and raw PR artifacts, without
the expected answer or evaluation criteria. Save the transcript and response
outside the source checkout. Record when the first useful explanation appears,
what was inspected before it, and what was left unchecked. Check behavior and
citations against the actual pinned implementation.

Then give an unfamiliar reader only the opening explanation. Ask them to
answer, in their own words:

1. What job does this part of the system do?
2. What changes, and why does that matter?
3. What concrete path illustrates the change?
4. Where would you focus your review, and what consequence makes it matter?

For a trivial change, recognizing that no substantial design decision was
found is a valid answer. Check that material description mismatches are
explained without turning the walk into an exhaustive claim inventory.

Score each applicable answer 0 (absent or wrong), 1 (partly clear), or 2
(correct and explainable without hidden context). The target is 2 on every
applicable question. A fluent but false explanation fails regardless of its
comprehension score. Use a separate evaluator with the raw artifacts to check
accuracy. A simulated reader is useful feedback, not a measured human result.

## Experience checks

- **Time to orientation:** a verified small account arrives before unnecessary
  exhaustive work. Compare elapsed time on the same fixture; do not substitute
  a universal latency promise for evidence. Inspect tool order as well as time.
- **Attention:** a quick response is comfortably readable within its budget;
  meaningful context and consequences dominate file names and bookkeeping.
- **Independence:** the reviewer gains a complete small understanding without
  selecting a mode or repeatedly saying continue. Honor explicit requests to
  pause between steps.
- **Judgment:** tradeoffs include reachable consequences, protections, and gaps.
  The reviewer is equipped to decide instead of receiving unexplained questions.
- **Calibration:** inspected scope is clear; missing evidence remains visible;
  mechanical grouping does not conceal consequential changes.

Apply each case's expectations semantically. Exact headings, fixed uncertainty
phrases, line counts, and a mandatory question or command are not success
criteria. Capture actual outputs and failures before claiming an eval passed.
