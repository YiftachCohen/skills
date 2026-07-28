#!/usr/bin/env python3
"""Screenshot a rendered atlas with headless Chrome, so legibility can be judged
by looking at the map instead of inferring it from the JSON.

Captures the view a first-time reader actually gets — the fitted overview — and
optionally the worst case, every container expanded at once. Both themes, since
"legible" differs between the near-black living theme and the print theme.

Usage:
  python3 screenshot.py <atlas.json | atlas.html> [--out-dir DIR]
      [--width 1600] [--height 1000] [--no-expanded] [--chrome PATH]

From an atlas.json this renders temp HTML itself (via ../../scripts/render.py,
--no-source-check, so it works on a copied artifact without the repo). From an
atlas.html it screenshots as-is (single theme — whatever the file was rendered
with).

Stdlib only, apart from a Chrome/Chromium binary.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RENDER = Path(__file__).resolve().parent.parent.parent / "scripts" / "render.py"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
]

# Injected before </body> for the expanded capture: the viewer's own
# expand-all, then a refit. Runs under Chrome's virtual time, so the delays
# cost nothing real.
EXPAND_SCRIPT = """
<script>
setTimeout(() => {
  document.getElementById("expand-all").click();
  setTimeout(() => document.getElementById("fit").click(), 900);
}, 900);
</script>
"""


def find_chrome(explicit):
    if explicit:
        return explicit
    for c in CHROME_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    sys.exit("error: no Chrome/Chromium found; pass --chrome PATH")


def shoot(chrome, html_path, out_png, width, height):
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",  # labels are judged at fit zoom; 1x antialiasing blurs the verdict
        f"--window-size={width},{height}",
        "--virtual-time-budget=15000",
        f"--screenshot={out_png}",
        html_path.resolve().as_uri(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not Path(out_png).exists():
        sys.exit(f"error: Chrome produced no screenshot for {html_path.name}:\n{proc.stderr[-800:]}")


def render_theme(atlas_json, theme, out_html):
    proc = subprocess.run(
        [sys.executable, str(RENDER), str(atlas_json), "-o", str(out_html),
         "--theme", theme, "--no-source-check"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"error: render.py failed for --theme {theme}:\n{proc.stderr[-800:]}")


def with_expand_script(html_path, tmp):
    src = html_path.read_text(errors="replace")
    out = tmp / f"expanded-{html_path.name}"
    out.write_text(src.replace("</body>", EXPAND_SCRIPT + "</body>"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("atlas", type=Path)
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--no-expanded", action="store_true")
    ap.add_argument("--chrome", default=None)
    args = ap.parse_args()

    chrome = find_chrome(args.chrome)
    out_dir = args.out_dir or args.atlas.parent / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if args.atlas.suffix == ".json":
            targets = []
            for theme in ("print", "living"):
                html = tmp / f"{theme}.html"
                render_theme(args.atlas, theme, html)
                targets.append((theme, html))
        else:
            targets = [(args.atlas.stem, args.atlas)]

        for name, html in targets:
            png = out_dir / f"overview-{name}.png"
            shoot(chrome, html, png, args.width, args.height)
            print(png)
            if not args.no_expanded:
                png = out_dir / f"expanded-{name}.png"
                shoot(chrome, with_expand_script(html, tmp), png, args.width, args.height)
                print(png)


if __name__ == "__main__":
    main()
