"""Regression tests for plan 004: every sourceRef read confined to the repo.

An atlas.json is a file people send each other, so a sourceRef that escapes
the repo root (an absolute path, a "..") must not be opened — not to check
whether it exists, not to count its lines, not to classify any of them.
Same by-path import shim as atlas/tests/test_render.py. Run with:
python3 -m unittest discover atlas/tests -v
"""

import importlib.util
import os
import pathlib
import tempfile
import unittest

_RENDER = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "render.py"
_spec = importlib.util.spec_from_file_location("atlas_render", _RENDER)
render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render)


class FakeRepo:
    """A TemporaryDirectory laid out as a minimal fake repo for these tests."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name).resolve()
        (self.root / "inside.py").write_text(
            "def handle():\n    return 1\n"
        )
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "mod.py").write_text("x = 1\n")
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()


class TestResolveInRepo(unittest.TestCase):
    def test_ordinary_path_resolves(self):
        with FakeRepo() as repo:
            target = render.resolve_in_repo(repo.root, "inside.py")
            self.assertEqual(target, repo.root / "inside.py")

    def test_escapes_are_rejected(self):
        with FakeRepo() as repo:
            for rel in ("/etc/hosts", "../escape", "a/../../escape", ""):
                with self.subTest(rel=rel):
                    self.assertIsNone(render.resolve_in_repo(repo.root, rel))


class TestCheckSourceRefsConfinement(unittest.TestCase):
    def test_absolute_ref_is_rejected_without_reading(self):
        with FakeRepo() as repo:
            warnings, checked, ok, weak = render.check_source_refs(
                [{"id": "a", "sourceRef": "/etc/hosts:1"}], repo.root
            )
        joined = " ".join(warnings)
        self.assertIn("not a path inside the repo", joined)
        # The load-bearing assertion: nothing was read out of the file. A
        # warning that merely fires is not enough — the point of confinement
        # is that /etc/hosts's line count and classification never appear.
        self.assertNotIn("lands on", joined)
        self.assertNotIn("lines)", joined)


class TestDescribeRefConfinement(unittest.TestCase):
    def test_absolute_ref_reports_confinement(self):
        with FakeRepo() as repo:
            result = render.describe_ref("/etc/hosts:1", repo.root)
        self.assertIsNotNone(result)
        self.assertIn("not a path inside the repo", result)


class TestEdgeSourceConfinement(unittest.TestCase):
    def test_root_ref_returns_none(self):
        with FakeRepo() as repo:
            self.assertEqual(render.edge_source({"sourceRef": "/"}, repo.root), (None, False))

    def test_escape_ref_returns_none(self):
        with FakeRepo() as repo:
            self.assertEqual(
                render.edge_source({"sourceRef": "../escape"}, repo.root), (None, False)
            )

    def test_symlink_escape_is_rejected(self):
        with FakeRepo() as repo:
            link = repo.root / "escape_link"
            try:
                os.symlink("/etc", link)
            except OSError:
                self.skipTest("symlink creation not permitted in this environment")
            self.assertEqual(
                render.edge_source({"sourceRef": "escape_link/hosts"}, repo.root),
                (None, False),
            )

    def test_vendor_directory_is_not_walked(self):
        with FakeRepo() as repo:
            vendor = repo.root / "pkg" / "node_modules"
            vendor.mkdir()
            (vendor / "leaked.js").write_text("SECRET_MARKER_TOKEN")
            blob, truncated = render.edge_source({"sourceRef": "pkg"}, repo.root)
            self.assertIsNotNone(blob)
            self.assertNotIn("SECRET_MARKER_TOKEN", blob)


if __name__ == "__main__":
    unittest.main()
