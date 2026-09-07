#!/usr/bin/env python3
"""Print every path:line citation found in a markdown file next to the actual
line(s) from the checked-out tree, so a wrong citation is visible before the
reviewer sees it.

Usage:
    python3 check_citations.py <notes-or-reply.md> [--root <worktree>]

Finds `path/to/file.ext:12` and `path/to/file.ext:12-20` (optionally wrapped
in backticks). Exit code 1 if any citation points at a missing file or a line
past the end of the file. Everything else is for you to read: the script
cannot know whether line 41 is the retry you meant, only that line 41 exists
and what it says.
"""
import argparse
import pathlib
import re
import sys

CITE = re.compile(r"`?((?:[\w.@-]+/)*[\w.@-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?`?")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("--root", default=".", help="worktree root the paths are relative to")
    ap.add_argument("--context", type=int, default=0, help="extra lines to print around each citation")
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    text = pathlib.Path(args.markdown).read_text(encoding="utf-8")
    seen = set()
    bad = 0
    for m in CITE.finditer(text):
        path, start, end = m.group(1), int(m.group(2)), m.group(3)
        end = int(end) if end else start
        key = (path, start, end)
        if key in seen:
            continue
        seen.add(key)
        target = root / path
        label = f"{path}:{start}" + (f"-{end}" if end != start else "")
        if not target.is_file():
            # A bare filename is common in notes; accept it when it is unique.
            hits = [h for h in root.rglob(pathlib.Path(path).name)
                    if h.is_file() and ".git" not in h.parts and "node_modules" not in h.parts]
            if len(hits) == 1:
                target = hits[0]
                label += f"  (resolved to {target.relative_to(root)})"
            elif len(hits) > 1:
                print(f"AMBIGUOUS  {label}  matches: {', '.join(str(h.relative_to(root)) for h in hits[:5])}")
                bad += 1
                continue
            else:
                print(f"MISSING  {label}  (no such file under {root})")
                bad += 1
                continue
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        if start < 1 or end > len(lines):
            print(f"OUT-OF-RANGE  {label}  (file has {len(lines)} lines)")
            bad += 1
            continue
        lo = max(1, start - args.context)
        hi = min(len(lines), end + args.context)
        print(f"== {label}")
        for n in range(lo, hi + 1):
            mark = ">" if start <= n <= end else " "
            print(f"{mark}{n:5d}  {lines[n-1]}")
    if not seen:
        print("no path:line citations found")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
