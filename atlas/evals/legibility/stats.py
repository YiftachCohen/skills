#!/usr/bin/env python3
"""Legibility stats for an atlas.json — the numbers that predict whether the
opening view of a complex map reads as a diagram or as a hairball.

`render.py --check` validates the contract; this measures the *view*. It
reconstructs what the viewer draws at open (children collapsed, edges re-routed
to their top-level ancestor and merged) and reports the load every element puts
on the reader. Thresholds are heuristics from eyeballing real maps, not laws —
each warning names the element so a human or vision grader can go look at it.

Usage:
  python3 stats.py <atlas.json> [--json]

Exit code is always 0 unless the file is unreadable; warnings are signal for a
grader, not a gate.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Past these, real maps we scored started reading as clutter at fit zoom.
MAX_VISIBLE_DEGREE = 12   # edges touching one node in the opening view
MAX_TOP_EDGES = 90        # distinct drawn edges in the opening view
MAX_LABEL_RATIO = 0.25    # same cap render.py warns on, applied to the top view
MAX_GROUP_KINDS = 2       # a group spanning 3+ kinds pulls nodes out of their lanes
MAX_CHILDREN = 20         # contract cap; also the point expansion stops being scannable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("atlas", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    data = json.loads(args.atlas.read_text())
    nodes = data["graph"]["nodes"]
    edges = data["graph"]["edges"]

    parent = {n["id"]: n.get("parent") for n in nodes}
    label = {n["id"]: n.get("label", n["id"]) for n in nodes}

    def top_ancestor(nid):
        seen = set()
        while parent.get(nid) and nid not in seen:
            seen.add(nid)
            nid = parent[nid]
        return nid

    top = [n for n in nodes if not n.get("parent")]
    children = defaultdict(list)
    for n in nodes:
        if n.get("parent"):
            children[n["parent"]].append(n["id"])

    # --- the opening view: collapse every edge to its top-level pair ---------
    merged = {}  # (from, to) -> {"count": raw edges merged in, "labeled": any label}
    for e in edges:
        f, t = top_ancestor(e["from"]), top_ancestor(e["to"])
        if f == t:
            continue  # internal to a container; invisible until expanded
        m = merged.setdefault((f, t), {"count": 0, "labeled": False})
        m["count"] += 1
        m["labeled"] = m["labeled"] or bool(e.get("label"))

    degree = Counter()
    indeg, outdeg = Counter(), Counter()
    for (f, t) in merged:
        degree[f] += 1
        degree[t] += 1
        outdeg[f] += 1
        indeg[t] += 1

    top_ids = {n["id"] for n in top}
    isolated = sorted(i for i in top_ids if degree[i] == 0)
    labeled_top = sum(1 for m in merged.values() if m["labeled"])

    groups = defaultdict(list)
    for n in top:
        if n.get("group"):
            groups[n["group"]].append(n)

    stats = {
        "top_level_nodes": len(top),
        "total_nodes": len(nodes),
        "raw_edges": len(edges),
        "opening_view_edges": len(merged),
        "opening_view_labeled_edges": labeled_top,
        "opening_view_label_ratio": round(labeled_top / len(merged), 3) if merged else 0,
        # Every node over the threshold, not a fixed top-N: truncating at 5 hid
        # a sixth hub in a 40-node map, and "the five worst" is not the question
        # the reader has. The list stays sorted, so hubs[0] is still the busiest.
        "hubs": [{"id": i, "label": label[i], "visible_degree": d,
                  "in": indeg[i], "out": outdeg[i]}
                 for i, d in degree.most_common()
                 if d > MAX_VISIBLE_DEGREE][:20]
        or [{"id": i, "label": label[i], "visible_degree": d,
             "in": indeg[i], "out": outdeg[i]}
            for i, d in degree.most_common(5)],
        "isolated_top_nodes": isolated,
        "containers": sorted(
            ({"id": c, "children": len(ids)} for c, ids in children.items()),
            key=lambda x: -x["children"]),
        "groups": [{"name": g, "size": len(ns),
                    "kinds": sorted({n.get("kind", "?") for n in ns})}
                   for g, ns in sorted(groups.items())],
    }

    warnings = []
    for h in stats["hubs"]:
        if h["visible_degree"] > MAX_VISIBLE_DEGREE:
            # A pure sink — many edges in, none out — is the signature of a
            # thematic fan rather than a story: "everything persists",
            # "everything logs". Those are the edges to prune first, because
            # none of them is the reason the reader opened the map. A hub with
            # traffic in both directions is usually a real dispatcher and its
            # fan is the point.
            shape = ""
            if h["out"] == 0 and h["in"] > MAX_VISIBLE_DEGREE:
                shape = (f" — {h['in']} in, 0 out: a pure sink, which is the "
                         "'everything writes here' fan. Keep the writes that "
                         "shape the product and drop the rest")
            warnings.append(
                f"hub: '{h['label']}' ({h['id']}) touches {h['visible_degree']} edges "
                f"in the opening view ({h['in']} in, {h['out']} out; > {MAX_VISIBLE_DEGREE})"
                f"{shape or ' — look at whether its fan is readable'}")
    if len(merged) > MAX_TOP_EDGES:
        warnings.append(
            f"density: {len(merged)} distinct edges drawn at open (> {MAX_TOP_EDGES}) "
            f"for {len(top)} top-level nodes — the overview may read as a mesh")

    # A group renders as a labeled stack, so a group of one is a label with no
    # stack: it costs a line of chrome and buys nothing, and it can still drag
    # its member out of its semantic lane. Counted over every node, not just the
    # top level, because children carry groups too.
    all_groups = Counter(n["group"] for n in nodes if n.get("group"))
    lonely = sorted(g for g, c in all_groups.items() if c == 1)
    if lonely:
        warnings.append(
            f"group of one: {lonely} — a group renders as a labeled stack, so a "
            "single member is a label with no stack. Fold it into a neighbouring "
            "group or drop the field")
    if merged and labeled_top / len(merged) > MAX_LABEL_RATIO:
        warnings.append(
            f"labels: {labeled_top}/{len(merged)} opening-view edges carry always-on labels "
            f"(> {MAX_LABEL_RATIO:.0%}) — label thicket at fit zoom")
    for g in stats["groups"]:
        if len(g["kinds"]) > MAX_GROUP_KINDS:
            warnings.append(
                f"group: '{g['name']}' spans {len(g['kinds'])} kinds {g['kinds']} — "
                f"pulls nodes out of their semantic lanes")
    for c in stats["containers"]:
        if c["children"] > MAX_CHILDREN:
            warnings.append(f"container: '{c['id']}' expands to {c['children']} children "
                            f"(> {MAX_CHILDREN}) — unscannable when opened")
    if isolated:
        warnings.append(f"isolated: {len(isolated)} top-level node(s) with no visible edge "
                        f"at open: {isolated[:6]} — floating boxes read as unfinished")

    stats["warnings"] = warnings

    if args.json:
        print(json.dumps(stats, indent=2))
        return

    print(f"{args.atlas}: {len(top)} top-level / {len(nodes)} total nodes; "
          f"{len(merged)} edges drawn at open ({len(edges)} raw), "
          f"{labeled_top} labeled ({stats['opening_view_label_ratio']:.0%})")
    if stats["hubs"]:
        h = stats["hubs"][0]
        print(f"busiest node at open: '{h['label']}' with {h['visible_degree']} edges")
    for w in warnings:
        print(f"warning: {w}")
    if not warnings:
        print("no legibility warnings")


if __name__ == "__main__":
    sys.exit(main())
