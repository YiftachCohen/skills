#!/usr/bin/env python3
"""Render an atlas JSON file into a self-contained interactive HTML map.

Usage:
  render.py [atlas.json] [-o OUT.html] [--open] [--check]
            [--theme {living,print}] [--online-icons]
            [--repo PATH] [--no-source-check]

Everything stays local: the JSON is inlined into a single HTML file that makes
zero network requests unless you switch icons on. Favicons are opt-in — off by
default (letter tiles render instead); enable them with the toolbar "Icons"
toggle or preset that toggle on with --online-icons.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# The viewer ships as three source files so each stays editable on its own, and
# is stitched back into ONE self-contained HTML file here. Nothing about the
# output changes: no external stylesheet, no external script, no extra request.
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE = TEMPLATES / "viewer.html"
CSS_TEMPLATE = TEMPLATES / "viewer.css"
JS_TEMPLATE = TEMPLATES / "viewer.js"

PLACEHOLDER = "/*__SCAN_DATA__*/"
CONFIG_PLACEHOLDER = "/*__SCAN_CONFIG__*/"
CSS_PLACEHOLDER = "/*__CSS__*/"
JS_PLACEHOLDER = "/*__JS__*/"

NODE_KINDS = {"entry", "cron", "agent", "model", "tool", "service", "store", "external"}
EDGE_KINDS = {"calls", "reads", "writes", "triggers"}
THEMES = ("living", "print")
SLUG_RE = re.compile(r"^[a-z0-9-]{1,48}$")

# Graph-size ceilings. The legacy topModels/topTools/topIntegrations summary
# fields are ignored by the viewer and must not be written any more, so there is
# nothing left to validate about them.
CAPS = {"nodes": 300, "edges": 500}
TOP_LEVEL_CAP = 40
CHILDREN_CAP = 20

# per-field character length limits from SKILL.md — over-length warns, never errors
LEN_LIMITS = {
    "label": 28,
    "sub": 40,
    "group": 24,
    "detail": 200,
    "sourceRef": 120,
}
EDGE_LABEL_LIMIT = 24
# Labels never fade, so past roughly one per four edges the map opens as a
# thicket of grey text at fit-zoom and is legible only once you zoom in.
LABEL_RATIO_CAP = 0.25
# Five whitespace-separated fields of digits/*/,- — a crontab line, not a comment.
CRON_RE = re.compile(r"^[\d*/,\-]+(\s+[\d*/,\-]+){4}(\s|$)")
# Dispositions the inventory writes back at itself. The contract is "name the
# id in backticks" — any backticked token that IS a node id counts, whatever the
# connecting words ("child `x`", "container `x`", "→ `x`"). The keyword form is
# still recognised separately so that "node `x`" naming an id the map lacks can
# be reported as a disagreement rather than lumped in as undispositioned.
INVENTORY_REF_RE = re.compile(
    r"\b(?:node|child|children|sub|detail|container|group|edge)s?\b"
    r"[^`\n]{0,16}`([A-Za-z0-9_-]+)`")
BACKTICKED_RE = re.compile(r"`([A-Za-z0-9_-]+)`")
OMITTED_RE = re.compile(r"\bomitted\b", re.I)

# --- edge evidence (see check_edges) ------------------------------------------
# What reaching a store looks like in source, in the languages an atlas points at.
SQL_VERB_RE = re.compile(r"\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|UPSERT|"
                         r"CREATE\s+TABLE)\b", re.I)
DB_CALL_RE = re.compile(
    r"(\bexecute\b|\bexecutemany\b|\bcursor\b|psycopg|asyncpg|sqlalchemy|sqlite3|"
    r"\bsession\.|\bdb\.|drizzle|prisma\.|\bknex\b|mongoose|\.query\(|\.insert\(|"
    r"\.update\(|\.select\(|\.findMany\(|\.upsert\(|\.delete\(|"
    # A key-value store is reached without a query at all. An offline-first
    # mobile app has no SQL anywhere in it, so without these every store edge
    # in one reads as unevidenced.
    r"\.setItem\(|\.getItem\(|\.removeItem\(|AsyncStorage|\bMMKV\b|SecureStore|"
    r"localStorage|sessionStorage|indexedDB|\.getObject\(|\.putObject\()", re.I)
# A caller never names the product; it names the driver or the env var. Substring
# matched, not word-bounded: `import psycopg2` must satisfy "psycopg".
STORE_DRIVERS = {
    "postgres": ("psycopg", "asyncpg", "pg8000", "sqlalchemy", "drizzle", "prisma",
                 "DATABASE_URL", "neon", "supabase"),
    "mysql": ("mysql", "mariadb", "DATABASE_URL"),
    "sqlite": ("sqlite", "better-sqlite", "expo-sqlite", "openDatabase"),
    "redis": ("redis", "REDIS_URL"),
    "mongo": ("mongodb", "mongoose", "pymongo", "motor", "MONGO_URL"),
    "clickhouse": ("clickhouse", "CLICKHOUSE_"),
    "bigquery": ("bigquery", "google-cloud-bigquery"),
    "firestore": ("firebase", "firestore", "google-cloud-firestore"),
    "firebase": ("firebase", "firestore"),
    "r2": ("S3Client", "R2_", "boto3", "aws-sdk"),
    "s3": ("S3Client", "boto3", "aws-sdk"),
    "gcs": ("storage.Client", "google-cloud-storage"),
    "dynamo": ("dynamodb", "boto3"),
    "elastic": ("elasticsearch", "opensearch"),
    "kafka": ("kafkajs", "confluent", "KAFKA_"),
    "sqs": ("sqs", "boto3", "aws-sdk"),
    # On-device and in-browser stores — the whole datastore tier of a mobile or
    # offline-first app, where nothing resembles a query.
    "asyncstorage": ("AsyncStorage", "async-storage"),
    "async storage": ("AsyncStorage", "async-storage"),
    "mmkv": ("MMKV", "react-native-mmkv"),
    "securestore": ("SecureStore", "expo-secure-store"),
    "secure store": ("SecureStore", "expo-secure-store"),
    "keychain": ("Keychain", "keytar", "SecItem"),
    "localstorage": ("localStorage", "sessionStorage"),
    "indexeddb": ("indexedDB", "Dexie"),
}
ENV_READ_RE = re.compile(r"process\.env|os\.environ|os\.Getenv|getenv|dotenv|ENV\[", re.I)
# Config lives in a module or a .env, never in a schema file — an id containing
# "config" is not enough to tell those apart, so the ref decides.
CONFIG_REF_RE = re.compile(r"(^|/)(\.env|config|settings|constants)(\.|/|$)", re.I)
IMPORT_LINE_RE = re.compile(
    r"^\s*(from\s+\S+\s+import\b|import\b|export\s+.*\bfrom\b|.*\brequire\s*\(|"
    r"\s*use\s+|#include\b)")
# Route files whose URL path is the thing a caller actually names.
ROUTE_FILE_RE = re.compile(r"(^|/)(route|page|index|\+page|\+server)\.[jt]sx?$")
EDGE_SOURCE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".go", ".rb", ".rs",
                   ".java", ".swift", ".kt", ".m", ".cs", ".php", ".sql", ".yml",
                   ".yaml", ".sh", ".html", ".jinja", ".j2", ".erb", ".vue", ".svelte"}
DIR_FILE_CAP = 40


def validate(data):
    errors, warnings = [], []

    if data.get("version") not in (1, 2):
        warnings.append(f"version is {data.get('version')!r}, expected 1 or 2")

    proj = data.get("project")
    if not isinstance(proj, dict) or not proj.get("name"):
        errors.append("project.name is required")
    if isinstance(proj, dict):
        name = proj.get("name")
        if isinstance(name, str) and len(name) > 48:
            warnings.append(f"project.name is {len(name)} chars (cap 48)")
        tagline = proj.get("tagline")
        if isinstance(tagline, str) and len(tagline) > 80:
            warnings.append(f"project.tagline is {len(tagline)} chars (cap 80)")
        slug = proj.get("slug")
        if isinstance(slug, str) and not SLUG_RE.match(slug):
            warnings.append(
                f"project.slug {slug!r} does not match ^[a-z0-9-]{{1,48}}$"
            )

    graph = data.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not nodes:
        errors.append("graph.nodes is empty — nothing to render")

    ids = [n.get("id") for n in nodes]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"duplicate node ids: {sorted(dupes)}")

    id_set = set(ids)
    for i, n in enumerate(nodes):
        if not n.get("id"):
            errors.append(f"nodes[{i}] has no id")
        if not n.get("label"):
            warnings.append(f"node {n.get('id')!r} has no label")
        if n.get("kind") not in NODE_KINDS:
            warnings.append(
                f"node {n.get('id')!r} kind {n.get('kind')!r} is not one of "
                f"{sorted(NODE_KINDS)} (renders as 'external')"
            )
        for field, limit in LEN_LIMITS.items():
            val = n.get(field)
            if isinstance(val, str) and len(val) > limit:
                warnings.append(
                    f"node {n.get('id')!r} {field} is {len(val)} chars (cap {limit})"
                )

    parents = {n.get("id"): n.get("parent") for n in nodes}
    for n in nodes:
        p = n.get("parent")
        if p is None:
            continue
        if p not in id_set:
            errors.append(f"node {n.get('id')!r} parent {p!r} is not a node id")
        elif p == n.get("id"):
            errors.append(f"node {n.get('id')!r} is its own parent")
        elif parents.get(p):
            errors.append(
                f"node {n.get('id')!r} is nested more than 2 levels deep "
                f"(parent {p!r} itself has a parent) — max depth is 2"
            )
    top_level = [n for n in nodes if not n.get("parent")]
    if len(top_level) > TOP_LEVEL_CAP:
        warnings.append(
            f"{len(top_level)} top-level nodes (cap {TOP_LEVEL_CAP}) — "
            "move detail nodes under a parent so the overview stays readable"
        )
    from collections import Counter
    kid_counts = Counter(n["parent"] for n in nodes if n.get("parent"))
    for pid, count in kid_counts.items():
        if count > CHILDREN_CAP:
            warnings.append(f"container {pid!r} has {count} children (cap {CHILDREN_CAP})")

    # `service` is the only kind with no natural boundary, so it is where a map
    # rots: UI trees, build tooling and shared libraries all filed as services.
    # Both observed cases of the failure sat at 69-70% of all nodes; the honest
    # maps peak in the 40s, and a genuinely service-heavy backend has headroom
    # to ~60%. Children count too — the header pills count every node, so a UI
    # tree filed as `service` misreports the product even while drawn collapsed.
    svc = sum(1 for n in nodes if n.get("kind") == "service")
    if len(nodes) >= 30 and svc > 0.6 * len(nodes):
        warnings.append(
            f"{svc} of {len(nodes)} nodes are `service` ({100 * svc // len(nodes)}%) — "
            "the residual-bucket signature. Recheck each against Kind discipline "
            "in SKILL.md: UI trees are `entry` children, build/CI hangs off its "
            "trigger, third-party products are `external`, libraries fold into "
            "callers or one hub node"
        )

    for i, e in enumerate(edges):
        for end in ("from", "to"):
            if e.get(end) not in id_set:
                errors.append(f"edges[{i}].{end} = {e.get(end)!r} is not a node id")
        if "kind" in e and e["kind"] not in EDGE_KINDS:
            warnings.append(f"edges[{i}] kind {e['kind']!r} is not one of {sorted(EDGE_KINDS)}")
        lbl = e.get("label")
        if isinstance(lbl, str) and len(lbl) > EDGE_LABEL_LIMIT:
            warnings.append(f"edges[{i}] label is {len(lbl)} chars (cap {EDGE_LABEL_LIMIT})")

    for key, cap in CAPS.items():
        items = graph.get(key)
        if items and len(items) > cap:
            warnings.append(f"{key} has {len(items)} items (cap is {cap})")

    # The opening view re-routes every edge to its top-level ancestor, so a
    # top-level node can be edge-connected in the JSON's terms yet float
    # unconnected in the view the reader actually meets. A floating box reads
    # as unfinished — draw its real relationship or fold it into a neighbour.
    def top_ancestor(nid):
        seen = set()
        while parents.get(nid) and nid not in seen:
            seen.add(nid)
            nid = parents[nid]
        return nid

    if edges:
        visible = set()
        for e in edges:
            f, t = e.get("from"), e.get("to")
            if f in id_set and t in id_set:
                fa, ta = top_ancestor(f), top_ancestor(t)
                if fa != ta:
                    visible.update((fa, ta))
        for n in top_level:
            if n.get("id") not in visible:
                warnings.append(
                    f"top-level node {n.get('id')!r} has no edge in the opening view "
                    "— a floating box reads as unfinished; draw its real relationship "
                    "or fold it into a related node"
                )

    labelled = sum(1 for e in edges if e.get("label"))
    if edges and labelled / len(edges) > LABEL_RATIO_CAP:
        warnings.append(
            f"{labelled} of {len(edges)} edges carry a label (1 per "
            f"{len(edges) / labelled:.1f}) — past 1 per {1 / LABEL_RATIO_CAP:.0f} "
            "the map opens as a thicket of text; let `kind` carry the ordinary "
            "relationships and keep labels for the ones that would surprise a reader"
        )

    return errors, warnings, len(top_level)


def infer_repo_root(atlas_path):
    """Repo root to resolve sourceRefs against, or None if we can't be sure.

    Only the skill's own layout (<repo>/.atlas/atlas.json) is inferred. Guessing
    more widely — say, walking up to the nearest .git — would make rendering a
    bundled example from inside some unrelated checkout spray false warnings
    about files that were never meant to exist there.
    """
    p = atlas_path.resolve()
    return p.parent.parent if p.parent.name == ".atlas" else None


def describe_weak_line(text):
    """Name why a line is a poor landing spot, or None if it's a real landmark.

    A line number that resolves is not the same as a line number that helps. The
    ref exists so a reader lands on the thing the node names — the type, the
    func, the route. Landing on the doc comment above it, a blank line, or the
    file's bare `const (` opener is what a line number guessed from nearby
    context looks like, and nothing else in the pipeline can tell the difference.
    """
    s = text.strip()
    if not s:
        return "a blank"
    # A crontab expression starts with the same '*' that opens a block-comment
    # continuation line, and pointing at one is exactly right for a cron node.
    if CRON_RE.match(s):
        return None
    # Comment leaders across the languages an atlas is likely to point at. A
    # bare '*' catches the continuation lines of a /* */ or docstring block.
    if s.startswith(("//", "#", "*", "/*", "--", ";", "%", '"""', "'''", "<!--")):
        return "a comment"
    # Openers that carry no identifier: the reader still has to go hunting.
    if s.rstrip(":") in {"const (", "var (", "import (", "type (", "(", ")", "{", "}",
                         "};", "});", "]", "[", "else", "try", "end"}:
        return "a bare block-opener"
    return None


def check_source_refs(nodes, repo_root):
    """Verify every sourceRef points at a file, and a useful line, that exists.

    A sourceRef is a promise: teammates click it to jump to code, and it is fed
    into the node's agent prompt. A plausible-looking path that was never checked
    (an index route that doesn't exist, .ts where the file is .tsx) breaks both,
    and it is invisible unless something verifies it — so this does.
    """
    warnings, checked, ok, weak = [], 0, 0, 0
    parent_ref = {n.get("id"): n.get("sourceRef") for n in nodes}
    for n in nodes:
        ref = n.get("sourceRef")
        if not isinstance(ref, str) or not ref:
            continue
        checked += 1
        rel, _, line = ref.partition(":")
        target = repo_root / rel
        if not target.exists():
            warnings.append(
                f"node {n.get('id')!r} sourceRef {ref!r} does not exist in {repo_root} "
                "— jump-to-code and the node's agent prompt both dead-end"
            )
            continue
        if line.isdigit() and target.is_file():
            try:
                lines = target.read_text(errors="replace").splitlines()
            except OSError:
                lines = None
            if lines is not None:
                if int(line) > max(len(lines), 1):
                    warnings.append(
                        f"node {n.get('id')!r} sourceRef {ref!r} points past the end of "
                        f"the file ({len(lines)} lines)"
                    )
                    continue
                what = describe_weak_line(lines[int(line) - 1]) if int(line) >= 1 else None
                if what:
                    weak += 1
                    # A doc comment sits directly above what it documents, so the
                    # fix is usually a line or two down. Naming it turns the
                    # warning into an edit instead of another investigation.
                    nearest = next(
                        (i + 1 for i in range(int(line), min(int(line) + 10, len(lines)))
                         if not describe_weak_line(lines[i])), None)
                    hint = f" (try :{nearest})" if nearest else ""
                    warnings.append(
                        f"node {n.get('id')!r} sourceRef {ref!r} lands on {what} line "
                        f"— point it at the definition the node names{hint}"
                    )
        # A child that reuses its parent's ref adds nothing to click on, and
        # usually means the child was never located in the source at all.
        par = n.get("parent")
        if par and ref and parent_ref.get(par) == ref:
            weak += 1
            warnings.append(
                f"node {n.get('id')!r} sourceRef {ref!r} is identical to its parent "
                f"{par!r} — find the line where the child itself is defined"
            )
        ok += 1
    return warnings, checked, ok, weak


def edge_source(node, repo_root):
    """The text of the file(s) the node's sourceRef names, or None.

    A container pointing at a directory is checked against everything under it:
    the claim is about the container, so any member performing it counts.
    """
    ref = (node.get("sourceRef") or "").partition(":")[0]
    if not ref:
        return None
    target = repo_root / ref
    files = []
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = [f for f in sorted(target.rglob("*"))
                 if f.is_file() and f.suffix in EDGE_SOURCE_EXT][:DIR_FILE_CAP]
    if not files:
        return None
    chunks = []
    for f in files:
        try:
            chunks.append(f.read_text(errors="replace"))
        except OSError:
            pass
    return "\n".join(chunks) if chunks else None


def code_only(text):
    """Drop comments and docstrings.

    The second recurring wrong-edge shape is an arrow copied out of an
    architecture diagram: `analyze.py`'s docstring describes a
    prefilter -> classifier -> scorer funnel that no module implements, and the
    map drew it. If a prose mention of the target counts as evidence, the check
    endorses exactly the source the error came from — so only code counts.
    """
    out, in_block, block_end = [], False, None
    for line in text.splitlines():
        s = line.strip()
        if in_block:
            if block_end in s:
                in_block = False
            continue
        for opener, closer in (('"""', '"""'), ("'''", "'''"), ("/*", "*/"),
                               ("<!--", "-->")):
            if s.startswith(opener) and s.count(opener) == 1 and closer not in s[len(opener):]:
                in_block, block_end = True, closer
                break
        if in_block:
            continue
        # `*` catches the continuation lines of a /* */ block, but a crontab
        # entry starts with one too — and a schedule line is the ONLY evidence a
        # cron edge ever has, so dropping it as a comment makes every true
        # `cron -> script` edge in a crontab read as unevidenced.
        if CRON_RE.match(s):
            out.append(line)
            continue
        if s.startswith(("//", "#", "*", "--", ";;", '"""', "'''", "/*", "<!--")):
            continue
        out.append(line)
    return "\n".join(out)


def store_names(node):
    """Identifier-shaped names for a store: the table, not the prose label."""
    names = set()
    for v in (node.get("label"), node.get("sub"), node.get("id")):
        for t in re.split(r"[^A-Za-z0-9_]+", v or ""):
            if len(t) >= 4:
                names.add(t.lower())
    # "Raw items" and "t-raw-items" are both `raw_items` at the call site.
    lbl = re.sub(r"[^a-z0-9]+", "_", (node.get("label") or "").lower()).strip("_")
    if len(lbl) >= 4:
        names.add(lbl)
    nid = re.sub(r"^t[-_]", "", (node.get("id") or "").lower()).replace("-", "_")
    if len(nid) >= 4:
        names.add(nid)
    for key, drivers in STORE_DRIVERS.items():
        if key in f"{node.get('id')} {node.get('label')} {node.get('domain')}".lower():
            names.update(drivers)
    return names


def is_db_store(node):
    """Whether reaching this store should look like a query in the caller.

    `store` covers both a Postgres table and a directory of files on disk, and
    only the first has a call shape worth insisting on — demanding a db client
    of a script that writes a folder would flag every true edge it has.
    """
    text = f"{node.get('id')} {node.get('label')} {node.get('sub')} {node.get('domain')}".lower()
    if node.get("domain") or any(k in text for k in STORE_DRIVERS):
        return True
    if re.search(r"\b(db|database|table|tables|schema|index|cache|queue|bucket)\b", text):
        return True
    # A store whose ref is the schema that defines it is a database.
    return bool(re.search(r"(schema|migration|models?)\b|\.sql$",
                          (node.get("sourceRef") or ""), re.I))


def name_hint(names, k=4):
    """The names worth showing in a warning: most specific first.

    An alphabetical head is nearly useless — it surfaces 'Access' and '3.1k'
    while `document/bulk-download`, the name that would actually settle the
    question, falls off the end.
    """
    return sorted(names, key=lambda n: (-len(n), n))[:k]


def symbolish(token):
    """Whether a token is a name a caller types, not a word from a prose `sub`.

    `streamText`, `check_gate`, `lib/storage` and `depot.yaml` are written
    verbatim at a call site; `files`, `timeout` and `later` are English that
    happens to appear in one. A leading digit rules out "3.1k lines".
    """
    if not token or token[0].isdigit():
        return False
    return ("_" in token or "/" in token or "." in token
            or any(a.islower() and b.isupper() for a, b in zip(token, token[1:])))


def module_names(node):
    """How a caller would name this node in an import or a URL.

    Both spellings matter: `scout/analyzer/classifier.py` is imported as
    `scout.analyzer.classifier` and as `@/analyzer/classifier`, and an
    `app/api/copilot/route.ts` is reached as `/api/copilot` — never as `route`.
    """
    ref = (node.get("sourceRef") or "").partition(":")[0]
    names = set()
    if not ref:
        return names
    p = Path(ref)
    if ROUTE_FILE_RE.search(ref):
        # Strip framework scaffolding to leave the URL a caller would fetch.
        segs = [s for s in p.parent.parts
                if s not in ("src", "app", "pages", "routes", "api")
                and not (s.startswith("(") and s.endswith(")"))]
        if segs:
            names.add("/".join(segs))
    elif p.stem not in ("index", "__init__", "mod", "main"):
        names.add(p.stem)
    names.add(p.name)
    parts = [s for s in p.with_suffix("").parts if s not in (".", "src")]
    if len(parts) >= 2:
        tail = parts[-2:]
        names.add("/".join(tail))
        names.add(".".join(tail))
    # A `sub` naming the symbol ("streamText", "POST /api/chat") is often the
    # only thing the caller writes — but `sub` is free prose ("3.1k lines, panel
    # layout", "File System Access API"), and mining it for bare words let
    # common English stand in as evidence: six edges across three repos passed
    # only because "local", "files" or "timeout" appeared somewhere in the
    # caller. Keep the tokens a caller literally types — camelCase, snake_case,
    # a path, a dotted name — and drop the prose.
    for t in re.split(r"[^A-Za-z0-9_/.]+", node.get("sub") or ""):
        if len(t) >= 4 and not t.isupper() and symbolish(t):
            names.add(t)
    # The id, and an acronym or one-word label, are usually the code's own name
    # for the thing: a Jinja template calls `csrf_token()`, never `app.py`.
    # Multi-word prose labels ("Scholarship catalog") are excluded — matching
    # "catalog" anywhere would wave through the misattributions this looks for.
    for t in re.split(r"[^A-Za-z0-9]+", node.get("id") or ""):
        if len(t) >= 4:
            names.add(t)
    label = (node.get("label") or "").strip()
    words = label.split()
    for word in words:
        t = re.sub(r"[^A-Za-z0-9_]", "", word)
        if not t.isalnum() or not t[:1].isalpha():
            continue
        if (t.isupper() and len(t) >= 3) or (len(words) == 1 and len(t) >= 4):
            names.add(t)
    return {n for n in names if len(n) >= 3}


def check_edges(nodes, edges, repo_root):
    """Look for the line that performs each edge's claim, in the caller's file.

    `--check` cannot fault an edge — one is structurally valid as long as both
    ends are node ids — so the map's actual claims about behaviour have always
    been unverified. The recurring failure is not invention but misattribution:
    a leaf module gets credited with work its driver performs (a pure function
    with no db import drawn as reading a table), or a stage->stage arrow is
    copied out of an architecture doc that no code implements.

    Both leave the same fingerprint: the `from` node's file contains nothing
    that could perform the claim. So ask, per target kind, the question a
    reviewer would ask — does this file reach a database at all, does it import
    that module, does it name that URL, does it mention that SDK — and report
    the ones with no evidence as a worklist. A flag is not a verdict: an edge
    that is real through a barrel re-export or a DI container will land here
    too. It means *you* have to point at the line, not that the edge is wrong.
    """
    by_id = {n.get("id"): n for n in nodes}
    findings, checked = [], 0
    # A hub node is the `from` of many edges, and a container ref can be a whole
    # directory — without this the same files are read once per edge.
    source_cache = {}
    for e in edges:
        src, dst = by_id.get(e.get("from")), by_id.get(e.get("to"))
        if not src or not dst:
            continue
        # An external service's behaviour is not in this repo: a scheduler that
        # triggers a route is configured in its own dashboard or a vercel.json,
        # not in a file we could point at.
        if src.get("kind") == "external":
            continue
        if src.get("id") not in source_cache:
            blob = edge_source(src, repo_root)
            source_cache[src.get("id")] = (blob, code_only(blob) if blob else None)
        blob, code = source_cache[src.get("id")]
        if blob is None:
            continue
        checked += 1
        kind, why = dst.get("kind"), None

        if kind == "store":
            named = [n for n in store_names(dst) if n.lower() in blob.lower()]
            reaches_db = bool(SQL_VERB_RE.search(blob) or DB_CALL_RE.search(blob))
            # Config and .env are stores too, and nothing queries them.
            config_ref = bool(CONFIG_REF_RE.search(dst.get("sourceRef") or ""))
            imports_config = any(n.lower() in blob.lower() for n in module_names(dst))
            # Almost nothing calls a store driver directly: a route reads R2 by
            # importing the repo's own `lib/storage`, and the S3Client sits one
            # file further in. A store's sourceRef names that fronting module,
            # so importing it IS the evidence. Only path-shaped names count — a
            # bare `settings` or `admin` matches any admin page's own prose and
            # would wave through the misattributions this exists to catch.
            imports_front = any(n.lower() in blob.lower()
                                for n in module_names(dst) if "/" in n)
            if imports_front:
                pass
            elif config_ref and (imports_config or ENV_READ_RE.search(blob)):
                pass
            elif not is_db_store(dst):
                # A directory of artifacts is a store too, and writing to one
                # looks like nothing in particular. Only the name can be checked.
                if not named:
                    why = f"never names {name_hint(store_names(dst))}"
            elif not reaches_db:
                why = ("no query, ORM call or db client anywhere in it — a file that "
                       f"cannot reach {dst.get('label') or dst.get('id')!r} cannot "
                       f"{e.get('kind') or 'touch'} it; the access is probably in "
                       "whatever calls this")
            elif not named:
                why = f"reaches a database but never names {name_hint(store_names(dst))}"
        elif kind in ("external", "model"):
            names = {t for t in re.split(r"[^A-Za-z0-9_.\-]+",
                                         f"{dst.get('sub')} {dst.get('label')}")
                     if len(t) >= 4}
            dom = (dst.get("domain") or "").split(".")[0]
            if dom:
                names.add(dom)
            if names and not any(n.lower() in code.lower() for n in names):
                why = f"no mention of {name_hint(names)}"
        else:  # entry / cron / service / agent / tool — something in this repo
            names = module_names(dst)
            if names and not any(n.lower() in code.lower() for n in names):
                imports = "\n".join(l for l in code.splitlines()
                                    if IMPORT_LINE_RE.match(l))
                why = (f"does not import or name {name_hint(names, 3)}"
                       + ("" if imports else " (and imports nothing)"))
        if why:
            findings.append((e, src, why))

    warnings = [
        f"edge {e.get('from')} -{e.get('kind') or '?'}-> {e.get('to')}: "
        f"{src.get('sourceRef')} {why}"
        for e, src, why in findings
    ]
    return warnings, checked, len(findings)


def fill(template, values):
    """Substitute every placeholder in ONE pass over the template.

    Chained .replace() calls rescan text that was already substituted, so a
    payload containing another marker would have that marker replaced too — an
    atlas.json holding the literal config placeholder used to get the config
    object spliced into the middle of the graph. A single pass makes inserted
    content inert, whatever it happens to contain.
    """
    pattern = re.compile("|".join(re.escape(k) for k in values))
    # A function replacement is used verbatim: no backslash processing, which
    # the escaped "<\/" sequences in the payload depend on.
    return pattern.sub(lambda m: values[m.group(0)], template)


def load_template():
    """Read the three viewer sources and return the single-file HTML template.

    The result still carries the scan data/config placeholders — only the CSS
    and JS are inlined here.
    """
    for path in (TEMPLATE, CSS_TEMPLATE, JS_TEMPLATE):
        if not path.exists():
            sys.exit(f"error: viewer source {path} is missing")

    html = TEMPLATE.read_text()
    for name, placeholder in (
        ("data", PLACEHOLDER),
        ("config", CONFIG_PLACEHOLDER),
        ("CSS", CSS_PLACEHOLDER),
        ("JS", JS_PLACEHOLDER),
    ):
        if placeholder not in html:
            sys.exit(f"error: template {TEMPLATE} is missing the {name} placeholder")

    css = CSS_TEMPLATE.read_text()
    js = JS_TEMPLATE.read_text()
    # A stray closing tag in either source would end its block early. These are
    # our own files, so this is a guard against a bad edit, not untrusted input.
    if "</style" in css:
        sys.exit(f"error: {CSS_TEMPLATE} contains a '</style' sequence")
    if "</script" in js:
        sys.exit(f"error: {JS_TEMPLATE} contains a '</script' sequence")

    # rstrip keeps the sources newline-terminated on disk without doubling the
    # blank line ahead of the closing tag.
    return fill(html, {
        CSS_PLACEHOLDER: css.rstrip("\n"),
        JS_PLACEHOLDER: js.rstrip("\n"),
    })


def check_inventory(inv_path, nodes):
    """Diff the coverage inventory against the map it was supposed to produce.

    The inventory is where the skill decides what the map must account for, and
    reconciling it is otherwise self-graded: the agent that wrote both files also
    grades whether they agree. This reads the dispositions back — "node `x`",
    "child `y`", "detail on `z`" — and checks each named id exists, then flags
    bullets that name nothing and were never marked omitted.
    """
    try:
        lines = inv_path.read_text(errors="replace").splitlines()
    except OSError as e:
        return [f"could not read {inv_path}: {e}"], None

    ids = {n.get("id") for n in nodes}
    warnings = []
    mapped = omitted = unreconciled = 0
    for i, raw in enumerate(lines, 1):
        s = raw.strip()
        # Only bullets are inventory items; headings and prose are scaffolding.
        if not s.startswith(("- ", "* ")) or s.endswith(":"):
            continue
        hits = [t for t in BACKTICKED_RE.findall(s) if t in ids]
        named = INVENTORY_REF_RE.findall(s)
        if hits:
            mapped += 1
        elif named:
            # Keyword-form disposition, but every id it names is missing from
            # the map: that is a disagreement, not a missing disposition.
            warnings.append(
                f"{inv_path.name}:{i} points at node id(s) {sorted(set(named))} that "
                "the map does not contain — the inventory and the map disagree"
            )
        elif OMITTED_RE.search(s):
            omitted += 1
        else:
            unreconciled += 1
            warnings.append(
                f"{inv_path.name}:{i} names no node and is not marked omitted: "
                f"{s[:70]!r}"
            )
    total = mapped + omitted + unreconciled
    if not total:
        return warnings, None
    return warnings, (f"inventory: {total} items — {mapped} mapped, {omitted} omitted, "
                      f"{unreconciled} unreconciled")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("atlas", nargs="?", default=".atlas/atlas.json",
                    help="path to atlas.json (default: .atlas/atlas.json)")
    ap.add_argument("-o", "--out", help="output HTML path (default: alongside atlas.json)")
    ap.add_argument("--open", action="store_true", help="open the result in the default browser")
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--theme", choices=THEMES, default="living",
                    help="visual theme (default: living)")
    ap.add_argument("--online-icons", action="store_true",
                    help="preset the Icons toggle ON (fetches favicons from google.com)")
    ap.add_argument("--repo", help="repo root to resolve sourceRefs against "
                                   "(default: inferred when the atlas lives in <repo>/.atlas/)")
    ap.add_argument("--no-source-check", action="store_true",
                    help="skip verifying that sourceRef paths exist")
    ap.add_argument("--edges", action="store_true",
                    help="look for the line that performs each edge's claim in the "
                         "`from` node's file, and list the edges with no evidence")
    ap.add_argument("--inventory", nargs="?", const="", metavar="PATH",
                    help="diff the coverage inventory against the map "
                         "(default: inventory.md beside atlas.json)")
    args = ap.parse_args()

    atlas_path = Path(args.atlas)
    if not atlas_path.exists():
        sys.exit(f"error: {atlas_path} not found")

    try:
        data = json.loads(atlas_path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"error: {atlas_path} is not valid JSON: {e}")

    errors, warnings, top_level_count = validate(data)

    repo_root = Path(args.repo).resolve() if args.repo else infer_repo_root(atlas_path)
    source_note = ""
    if repo_root and not args.no_source_check:
        ref_warnings, checked, ok, weak = check_source_refs(
            (data.get("graph") or {}).get("nodes") or [], repo_root)
        warnings.extend(ref_warnings)
        if checked:
            source_note = f", {ok}/{checked} sourceRefs resolve (path and line)"
            if weak:
                source_note += f", {weak} land somewhere unhelpful"
            # Edges carry the map's claims about behaviour, and validate() cannot
            # fault one: an edge is valid as long as both ends are node ids.
            if not args.edges:
                source_note += ("; edges unchecked — run --edges to find the ones "
                                "with no evidence in the caller's file")

    edge_note = None
    if args.edges:
        if not repo_root:
            warnings.append("--edges needs a repo root to read source from — pass --repo")
        else:
            graph = data.get("graph") or {}
            edge_warnings, edges_checked, flagged = check_edges(
                graph.get("nodes") or [], graph.get("edges") or [], repo_root)
            warnings.extend(edge_warnings)
            if edges_checked:
                edge_note = (f"edges: {edges_checked} checked against the caller's "
                             f"source — {flagged} with no evidence found")
                if flagged:
                    edge_note += ("; point at the line for each, or move the edge to "
                                  "the node whose file performs it")

    inv_note = None
    if args.inventory is not None:
        inv_path = (Path(args.inventory) if args.inventory
                    else atlas_path.with_name("inventory.md"))
        if inv_path.exists():
            inv_warnings, inv_note = check_inventory(
                inv_path, (data.get("graph") or {}).get("nodes") or [])
            warnings.extend(inv_warnings)
        else:
            warnings.append(f"no inventory at {inv_path} — coverage is unreconciled")

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if edge_note:
        print(edge_note, file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    if args.check:
        # Labelled edges are claims a reader will trust, so print them as a
        # worklist — but only when --edges hasn't already produced a sharper one,
        # since a list of every labelled edge next to a list of the suspect ones
        # just dilutes the suspect ones.
        labelled = ([] if args.edges else
                    [e for e in (data.get("graph") or {}).get("edges") or [] if e.get("label")])
        if labelled:
            print("labelled edges to verify at a call site:", file=sys.stderr)
            for e in labelled:
                print(f"  {e['from']} -> {e['to']}  {e['label']!r}", file=sys.stderr)
        if inv_note:
            print(inv_note, file=sys.stderr)
        print(f"{atlas_path} is valid "
              f"({top_level_count} top-level of {len(data['graph']['nodes'])} nodes, "
              f"{len(data['graph'].get('edges', []))} edges{source_note})")
        return

    template = load_template()
    # </script> inside a JSON string would end the tag early; escape it.
    payload = json.dumps(data).replace("</", "<\\/")
    # The "Ask agent" prompts cite this so the agent can read the whole graph;
    # only useful when it is a repo-relative path, not someone's home directory.
    rel = None
    if not atlas_path.is_absolute() and ".." not in atlas_path.parts:
        rel = atlas_path.as_posix()
    config = json.dumps({
        "theme": args.theme,
        "onlineIcons": args.online_icons,
        "atlasPath": rel,
    }).replace("</", "<\\/")
    html = fill(template, {PLACEHOLDER: payload, CONFIG_PLACEHOLDER: config})

    out_path = Path(args.out) if args.out else atlas_path.with_name("atlas.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    print(f"wrote {out_path}")

    if args.open:
        if sys.platform == "win32":
            os.startfile(str(out_path))  # noqa: S606 — Windows default handler
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.run([opener, str(out_path)], check=False)


if __name__ == "__main__":
    main()
