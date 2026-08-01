# Slice prompt — paste this into every subagent

A subagent has not read the skill. This is the block that has to travel with
every slice; without it they invent edge kinds and `sourceRef`s. Paste it
verbatim, then add the four slice-specific parts marked `<< >>`.

Written out once here because typing it per slice is where the fan-out cost
goes — one five-slice run spent most of its prompt budget re-deriving this.

**Use it whenever you delegate, at any repo size.** It lives next to
`large-repos.md` for historical reasons, not because it only applies there. A
140-file Go repo mapped with six hand-rolled prose prompts cost 651k subagent
tokens and yielded a map that used under a fifth of what came back; the same
slices asked for the JSON below would have returned something pasteable. The
return format *is* the saving — an agent that cannot write an essay does not
bill you for one.

Paste the relevant part of `.atlas/survey.txt` into the slice scope rather than
letting each agent re-derive file counts, largest files and env vars.

---

You are mapping ONE SLICE of the repo at `<<ABS PATH>>`. All `sourceRef` paths
must be RELATIVE to that root. Work command-first: `ls`, `grep`, and open only
files you must. Do NOT read files one by one — you will run out of context.

## YOUR SLICE
<< the directories, the manifests, and the specific questions this slice must
answer. Name what is NOT yours and say which agent owns it. >>

## VOCABULARY — use exactly this, nothing else

Node `kind` is EXACTLY ONE OF:
- `entry` — route group, page, CLI command, webhook. A UI surface is a CHILD of
  the entry that mounts it and carries kind `entry` too, never `service`.
- `cron` — a **job**: work triggered from outside any request, by a schedule OR
  a queue. Celery tasks, job-runner handlers and pub/sub consumers are `cron`,
  with the trigger in `sub` ("celery · queue: dataset", "every 5m"). If an
  `enqueues` edge would point at it, it is a job.
- `service` — a subsystem that performs the product's own work at runtime:
  something calls it and it moves or transforms data. NOT a catch-all for
  "internal code". See the exclusions below.
- `agent` — an LLM call the product makes. A single-shot call with no loop and
  no tools is still an `agent`; say what it really is in `sub`.
- `model` — an actual model id. If models are user-configured at runtime rather
  than hardcoded, use ONE node for the configured model and say so in `sub`.
- `tool` — a function a model can call: a `tool({...})` definition, an MCP tool.
  Not an SDK, not a CLI, not a helper package.
- `store` — DB, cache, index, queue, object storage, config, disk.
- `external` — a third-party or out-of-process product you call, even when the
  code doing the calling is yours.

Edge `kind` is EXACTLY ONE OF `calls`, `reads`, `writes`, `triggers`,
`enqueues`. Nothing else — never `uses`, `depends`, `invokes`, `publishes`.
Use `enqueues` for a hand-off that returns before the work happens. Two nodes
may have more than one edge: a service that both reads and writes a store gets
both, not a compromise.

## NOT a `service` — the exclusions that actually get violated
- **Shared libraries.** Swap test: replace the implementation and if no flow
  redraws, it gets no node — fold it into its callers' `detail`.
- **Boot wiring.** A 40-line `init_app` whose body is `if DSN: sdk.init(...)`
  moves none of the product's data. Map the `external` it ships to; drop the
  wiring.
- **Per-endpoint clients.** N classes differing only in which path they call on
  the same target are ONE node with the count in `sub`.
- **Types, constants, enums, schemas, serializers, fixtures.** Never nodes.
- **Build, bundling, lint and CI.** They hang off an `entry` (push) or a `cron`.
- **Stages.** A step that only ever runs inside one parent flow is a child, and
  its `sub` says so ("step 2 of 5").
- BUT a **gatekeeper** (auth middleware, rate limiter, egress proxy) CAN end a
  flow with a 401/429/block, so it IS a stop and DOES get a node.

## REQUIRED FIELDS
Every node needs `id` (unique, lowercase-dashed), `label` (<=28 chars), `kind`,
and for anything internal BOTH of:
- `sourceRef` — a repo-relative path you ACTUALLY SAW plus `:line` at the
  definition the node names (the class, the function, the route registration).
  A node whose subject is a directory, or that merges several files, points at
  the DIRECTORY with no `:line`. Never infer a path from a naming pattern
  (`.ts` when the file is `.tsx`; an index route you did not confirm with `ls`).
  Never reuse the parent's line for a child.
- `detail` — ONE sentence, HARD LIMIT 200 characters, that a reader who has
  never seen this repo actually needs. Count the characters.

Optional: `sub` (<=40), `parent` (max depth 2), `group` (<=24, a domain name a
team says out loud).

## HARD RULES
- Do NOT emit edge `label`. Do NOT emit `evidence`. Both are decisions about the
  whole map that a slice cannot see. Instead put `"sawAt": "path:line"` on each
  edge — the line you actually read that PERFORMS the claim (the `.delay()`, the
  `session.query`, the fetch of that exact path). If you did not see a
  performing line, `"sawAt": null`. Do not guess.
- Import != call, and package != symbol: read the imported NAME, not the module
  path.
- An edge belongs to the node whose `sourceRef` file contains the performing
  line. If that line is in another file, the edge belongs to that file's node.
- Budget: at most `<<N>>` top-level nodes AND `<<M>>` nodes in total. Merge
  near-identical things and say so in `sub` rather than enumerating them.
- **Every number you write must carry the command that produced it.** If a
  `sub` or `detail` says "13 editors" or "42 patterns", add an entry to
  `counts` giving the exact shell command whose output is that number. Do not
  write a number you did not run a command for — say "several" instead, or
  leave it out. Counts asserted from reading are the single most common wrong
  claim in a finished map, and yours will be re-run before it ships.

## SHARED IDS — use these EXACT ids; do not invent variants
<< the pre-agreed list, with kinds. Say which ones this slice DEFINES and which
it only references as edge endpoints. >>

## RETURN FORMAT
Return ONLY a JSON object — no prose, no summary, no file excerpts, no preamble,
no markdown fence. A report is not the deliverable; this is:

```
{"nodes":[...],"edges":[...],
 "inventory":["- `path/x.py` — node `some-id`","- `path/y.py` — omitted: <one reason>"],
 "counts":[{"claim":"13 editors","command":"grep -c '{' internal/install/editors.go"}],
 "uncertain":["one line per thing you could not resolve"]}
```

`inventory` is one line per real item in your slice, each ending in a
disposition that names the node id in backticks or says "omitted: <reason>". A
healthy omitted count is correct, not a failure.

`uncertain` is where anything you would have written a paragraph about goes —
one line each. It is cheaper for both of us than a report, and it is the only
place prose belongs.
