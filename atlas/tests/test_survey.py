"""Regression tests for scripts/survey.sh.

The survey feeds the branch decision (read-all / command-first / large-repos),
the largest-files list and every inventory category, so a wrong number here
propagates into the whole map. Each test below pins a bug that shipped:

- `.atlas/` does not exist on a first scan, so the documented `> .atlas/...`
  redirect died in the shell before the script ran. The script owns the path now.
- `git ls-files` is the INDEX: it omitted untracked files and kept deleted ones,
  which maps stale code during active development.
- Test files were excluded by directory name only, so `_test.go` / `test_x.py`
  slipped through and doubled the measured size of Go and Python repos.
- Monorepo manifests under apps/* and packages/* were invisible.
- `head -N` caps lines, not bytes: one match in a committed minified bundle
  turned a 16KB survey into 89KB.

Run with: python3 -m unittest discover atlas/tests -v
"""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

_SURVEY = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "survey.sh"


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _run(repo):
    proc = subprocess.run(
        ["bash", str(_SURVEY), str(repo)],
        capture_output=True, text=True, timeout=120,
    )
    return proc.stdout


def _scale(out):
    for line in out.splitlines():
        if line.startswith("real source files:"):
            return int(line.split(":")[1])
    raise AssertionError(f"no scale line in survey output:\n{out[:500]}")


def _section(out, name):
    keep, body = False, []
    for line in out.splitlines():
        if line.startswith("== "):
            keep = name in line
            continue
        if keep:
            body.append(line)
    return "\n".join(body)


class SurveyRepo(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def write(self, rel, text="package main\n"):
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p


class TestOutputPath(SurveyRepo):
    def test_creates_atlas_dir_and_writes_survey(self):
        """A first scan has no .atlas/; the script must create it, not fail."""
        self.write("main.go")
        _git(self.dir, "init", "-q", ".")
        self.assertFalse((self.dir / ".atlas").exists())
        out = _run(self.dir)
        saved = self.dir / ".atlas" / "survey.txt"
        self.assertTrue(saved.is_file(), "survey.txt was not written")
        self.assertIn("real source files:", saved.read_text())
        self.assertIn("real source files:", out, "must also print to stdout")

    def test_non_git_repo_still_surveys(self):
        self.write("app.py", "import os\n")
        out = _run(self.dir)
        self.assertEqual(_scale(out), 1)


class TestWorkingTree(SurveyRepo):
    def test_untracked_included_and_deleted_excluded(self):
        self.write("src/tracked.go")
        self.write("src/deleted.go")
        _git(self.dir, "init", "-q", ".")
        _git(self.dir, "add", "-A")
        _git(self.dir, "commit", "-qm", "init")

        self.write("src/untracked.go")          # new, never added
        (self.dir / "src" / "deleted.go").unlink()  # gone from disk, still in index

        out = _run(self.dir)
        self.assertEqual(_scale(out), 2, "should count tracked + untracked, not deleted")
        largest = _section(out, "LARGEST SOURCE FILES")
        self.assertIn("src/untracked.go", largest)
        self.assertNotIn("src/deleted.go", largest)

    def test_gitignored_files_stay_out(self):
        """--others must not drag in build output .gitignore excludes."""
        self.write("keep.go")
        self.write(".gitignore", "ignored.go\n")
        self.write("ignored.go")
        _git(self.dir, "init", "-q", ".")
        self.assertEqual(_scale(_run(self.dir)), 1)


class TestScale(SurveyRepo):
    def test_per_file_test_conventions_excluded(self):
        """The bug that made armis-cli measure 267 files when it has 138."""
        self.write("internal/thing.go")
        self.write("internal/thing_test.go")
        self.write("pkg/test_helper.py", "x = 1\n")
        self.write("lib/widget_spec.rb", "x = 1\n")
        out = _run(self.dir)
        self.assertEqual(_scale(out), 1, "only thing.go is real source")
        self.assertNotIn("_test.go", _section(out, "LARGEST SOURCE FILES"))

    def test_vendored_directories_excluded(self):
        self.write("app.ts", "export {}\n")
        self.write("node_modules/dep/index.ts", "export {}\n")
        self.assertEqual(_scale(_run(self.dir)), 1)


class TestManifests(SurveyRepo):
    def test_nested_monorepo_manifests_found(self):
        self.write("package.json", '{"name":"root"}\n')
        self.write("apps/web/package.json", '{"name":"web"}\n')
        self.write("packages/core/pyproject.toml", "[project]\n")
        body = _section(_run(self.dir), "MANIFESTS")
        self.assertIn("apps/web/package.json", body)
        self.assertIn("packages/core/pyproject.toml", body)

    def test_vendored_manifests_not_listed(self):
        self.write("package.json", '{"name":"root"}\n')
        self.write("node_modules/dep/package.json", '{"name":"dep"}\n')
        body = _section(_run(self.dir), "MANIFESTS")
        self.assertNotIn("node_modules", body)


class TestOutputBounded(SurveyRepo):
    def test_minified_bundle_does_not_blow_up_output(self):
        """One match in a 400KB single-line file must not become 400KB of survey."""
        self.write("app.js", 'import OpenAI from "openai";\n')
        self.write("bundle.js", "var x=1;" * 50_000 + 'require("openai");\n')
        out = _run(self.dir)
        self.assertLess(len(out), 60_000, "a long matched line must be truncated")
        self.assertIn("openai", _section(out, "AI LAYER"))

    def test_no_hang_on_large_vendored_tree(self):
        """Recursive grep from the repo root used to walk node_modules and hang."""
        self.write("app.ts", 'const k = process.env.API_KEY\n')
        for i in range(300):
            self.write(f"node_modules/p{i}/index.js", "module.exports={}\n")
        out = _run(self.dir)  # _run has timeout=120; a hang fails the test
        self.assertEqual(_scale(out), 1)
        self.assertIn("API_KEY", _section(out, "ENV VARS"))


class TestCategories(SurveyRepo):
    def test_return_based_exit_reported(self):
        """The checklist's `return [1-9]` case, which the first survey dropped."""
        self.write("cli.py", "def main():\n    return 2\n")
        body = _section(_run(self.dir), "EXIT CODES")
        self.assertIn("return 2", body)

    def test_explicit_exit_calls_reported(self):
        self.write("m.go", "func f() { os.Exit(1) }\n")
        self.assertIn("os.Exit(1)", _section(_run(self.dir), "EXIT CODES"))

    def test_env_vars_collected(self):
        self.write("m.go", 'v := os.Getenv("ARMIS_API_URL")\n')
        self.assertIn("ARMIS_API_URL", _section(_run(self.dir), "ENV VARS"))

    def test_env_vars_across_languages(self):
        """The survey is authoritative for the sweep, so its language coverage is
        pinned here. `os.getenv` (lowercase, Python) was missing and is the most
        common idiom of the lot."""
        self.write("a.py", 'os.getenv("PY_LOWER")\nos.environ["PY_ENVIRON"]\n')
        self.write("b.rb", "ENV['RUBY_BRACKET']\nENV.fetch('RUBY_FETCH')\n")
        self.write("c.php", "<?php getenv('PHP_GETENV'); $_ENV['PHP_ARRAY'];\n")
        self.write("d.java", 'System.getenv("JAVA_KEY");\n')
        self.write("e.cs", 'Environment.GetEnvironmentVariable("CSHARP_KEY");\n')
        self.write("f.ts", 'import.meta.env.VITE_KEY\nDeno.env.get("DENO_KEY")\n')
        self.write("g.rs", 'std::env::var("RUST_KEY")\n')
        self.write("h.js", 'process.env.NODE_KEY\n')
        body = _section(_run(self.dir), "ENV VARS")
        for want in ("PY_LOWER", "PY_ENVIRON", "RUBY_BRACKET", "RUBY_FETCH",
                     "PHP_GETENV", "PHP_ARRAY", "JAVA_KEY", "CSHARP_KEY",
                     "VITE_KEY", "DENO_KEY", "RUST_KEY", "NODE_KEY"):
            self.assertIn(want, body, f"{want} not detected")

    def test_ai_layer_across_providers(self):
        """Absence of an AI layer is a claim the map makes, so a miss here
        becomes a wrong sentence rather than a blank section."""
        self.write("a.py", "import google.generativeai as genai\n")
        self.write("b.py", "from mistralai import Mistral\n")
        self.write("c.ts", 'import Anthropic from "@anthropic-ai/sdk"\n')
        self.write("d.ts", "await client.messages.create({})\n")
        self.write("e.py", "client.chat.completions.create()\n")
        self.write("f.ts", 'import { generateText } from "ai"\n')
        self.write("g.py", "from langgraph.graph import StateGraph\n")
        self.write("h.ts", 'server = new McpServer() // modelcontextprotocol\n')
        body = _section(_run(self.dir), "AI LAYER")
        for want in ("generativeai", "mistralai", "anthropic", "messages.create",
                     "chat.completions", "generateText", "langgraph",
                     "modelcontextprotocol"):
            self.assertIn(want, body, f"{want} not detected")

    def test_ai_patterns_do_not_match_english_prose(self):
        """`cohere` matched "coherent" and `replicate` matched "replicate the
        behaviour" — both found on a real repo, where two doc comments about
        coherent design read as an AI provider."""
        self.write("a.ts", "// so the set stays coherent across surfaces\n")
        self.write("b.py", "# we replicate the behaviour of the old scheduler\n")
        self.assertEqual(_section(_run(self.dir), "AI LAYER").strip(), "")

    def test_survey_does_not_ingest_its_own_output(self):
        """.atlas/ is the script's own output; scanning it makes each run read
        the previous one back and double-report every hit."""
        self.write("m.ts", 'import OpenAI from "openai"\n')
        first = _run(self.dir)
        second = _run(self.dir)
        self.assertNotIn("survey.txt", _section(second, "AI LAYER"))
        self.assertEqual(_scale(first), _scale(second))
        self.assertEqual(
            _section(first, "AI LAYER").strip(),
            _section(second, "AI LAYER").strip(),
            "a second run must be identical, not cumulative",
        )

    def test_no_ai_layer_reports_empty_not_missing(self):
        """A repo with no AI must still produce the section, so 'no AI layer'
        is something observed rather than something skipped."""
        self.write("m.go", "func main() {}\n")
        out = _run(self.dir)
        self.assertIn("AI LAYER", out)
        self.assertEqual(_section(out, "AI LAYER").strip(), "")

    def test_scale_line_present_for_empty_repo(self):
        """An empty repo reports 0, not a crash or a blank."""
        self.write("README.md", "# hi\n")
        self.assertEqual(_scale(_run(self.dir)), 0)


if __name__ == "__main__":
    unittest.main()
