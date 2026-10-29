import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import harness_check
import sync_examples


class GateTests(unittest.TestCase):
    def test_complete_example_content_detects_broken_router(self):
        with tempfile.TemporaryDirectory(prefix="oaw-example-") as temporary:
            root = Path(temporary)
            with patch.object(sync_examples, "ROOT", root), patch.object(sync_examples, "EXAMPLES", (("minimal-project", "minimal", False),)):
                self.assertEqual(sync_examples.sync(write=True), [])
                self.assertEqual(sync_examples.sync(), [])
                target = root / "example/minimal-project/AGENTS.md"
                target.write_text("broken example policy\n", encoding="utf-8")
                issues = sync_examples.sync()
                self.assertTrue(any("AGENTS.md" in issue for issue in issues))

    def test_obsolete_example_framework_files_fail(self):
        with tempfile.TemporaryDirectory(prefix="oaw-example-") as temporary:
            root = Path(temporary)
            with patch.object(sync_examples, "ROOT", root), patch.object(sync_examples, "EXAMPLES", (("minimal-project", "minimal", False),)):
                sync_examples.sync(write=True)
                obsolete = root / "example/minimal-project/scripts/obsolete.py"
                obsolete.write_text("obsolete\n", encoding="utf-8")
                self.assertTrue(any("obsolete.py" in issue for issue in sync_examples.sync()))
                sync_examples.sync(write=True)
                self.assertFalse(obsolete.exists())

    def test_arbitrary_crash_is_a_failed_gate(self):
        check = harness_check.command_check("crash-fixture", [sys.executable, "-c", "raise SystemExit(42)"])
        self.assertFalse(check.passed)
        self.assertEqual(check.detail, "exit 42")

    def regression_fixture(self, root, files):
        for name, body in files.items():
            (root / name).write_text("import unittest\n\n" + body, encoding="utf-8")
        return root

    def test_regression_inventory_requires_modules_count_and_no_skips(self):
        passing = "class A(unittest.TestCase):\n    def test_ok(self):\n        pass\n"
        skipped = "class B(unittest.TestCase):\n    def test_skip(self):\n        self.skipTest('fixture')\n"
        with tempfile.TemporaryDirectory(prefix="oaw-gate-") as temporary:
            root = self.regression_fixture(Path(temporary), {"test_a.py": passing})
            self.assertTrue(harness_check.regression_check(root, ("test_a",), 1).passed)
            missing = harness_check.regression_check(root, ("test_a", "test_b"), 1)
            self.assertFalse(missing.passed)
            self.assertIn("missing test modules: test_b", missing.detail)
            self.assertFalse(harness_check.regression_check(root, ("test_a",), 2).passed)
            self.regression_fixture(root, {"test_b.py": skipped})
            with patch.dict(os.environ, {"OAW_ALLOW_SKIPS": ""}):
                result = harness_check.regression_check(root, ("test_a", "test_b"), 2)
            self.assertFalse(result.passed)
            self.assertIn("1 skipped test(s)", result.detail)
            with patch.dict(os.environ, {"OAW_ALLOW_SKIPS": "1"}):
                self.assertTrue(harness_check.regression_check(root, ("test_a", "test_b"), 2).passed)

    def test_regression_import_failure_fails_gate(self):
        with tempfile.TemporaryDirectory(prefix="oaw-gate-") as temporary:
            root = self.regression_fixture(Path(temporary), {"test_a.py": "raise RuntimeError('import fixture')\n"})
            result = harness_check.regression_check(root, (), 0)
            self.assertFalse(result.passed)
            self.assertIn("exit 1", result.detail)

    def test_redirected_cp1252_output_is_configured_as_utf8(self):
        scripts = str(Path(__file__).resolve().parents[1] / "scripts")
        code = f"import sys; sys.path.insert(0, {scripts!r}); import harness_check; harness_check.configure_stdio(); print('\\u26a0 wiki \\u4e2d\\u6587')"
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        process = subprocess.run([sys.executable, "-c", code], capture_output=True, env=environment)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("⚠ wiki 中文", process.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
