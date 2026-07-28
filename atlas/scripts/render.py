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

    return errors, warnings


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
    args = ap.parse_args()

    atlas_path = Path(args.atlas)
    if not atlas_path.exists():
        sys.exit(f"error: {atlas_path} not found")

    try:
        data = json.loads(atlas_path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"error: {atlas_path} is not valid JSON: {e}")

    errors, warnings = validate(data)

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
            # Edges carry the map's claims about behaviour and nothing here can
            # check one: an edge is valid as long as both ends are node ids.
            edge_labels = sum(
                1 for e in (data.get("graph") or {}).get("edges") or [] if e.get("label"))
            if edge_labels:
                source_note += (f"; {edge_labels} labelled edges assert behaviour "
                                "that only you can verify")

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    if args.check:
        print(f"{atlas_path} is valid "
              f"({len(data['graph']['nodes'])} nodes, "
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
