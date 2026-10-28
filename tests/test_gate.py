import contextlib
import io
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
