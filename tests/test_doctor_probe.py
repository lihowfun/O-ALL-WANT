"""doctor: the Skill tool denied in project settings, and --probe of Claude Code's own skill discovery (W4)."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("oaw_doctor_test", ROOT / "scripts/oaw.py")
oaw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oaw)

FAKE = """#!{python}
import json, sys, time
print(json.dumps({event}), flush=True)
{after}
"""


class DoctorProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-doctor-")
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "project"
        self.config = Path(self.temporary.name) / "config"
        os.environ["OAW_CONFIG_HOME"] = str(self.config)
        self.addCleanup(os.environ.pop, "OAW_CONFIG_HOME", None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(oaw.main(["init", "--target", str(self.target), "--host", "claude"]), 0)

    def fake(self, event, after="time.sleep(30)"):
        path = Path(self.temporary.name) / f"fake-claude-{len(list(Path(self.temporary.name).glob('fake-*')))}"
        path.write_text(FAKE.format(python=sys.executable, event=repr(event), after=after), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def claude_capability(self, result):
        return next(c for c in result["capabilities"] if c["capability"].startswith("Claude"))

    def test_without_probe_discovery_is_unknown(self):
        result = oaw.doctor(self.target)
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(self.claude_capability(result)["enabled"], "UNKNOWN")

    def test_a_denied_skill_tool_is_reported(self):
        settings = self.target / ".claude" / "settings.json"
        settings.write_text(json.dumps({"permissions": {"deny": ["Bash(rm:*)", "Skill"]}}), encoding="utf-8")
        result = oaw.doctor(self.target)
        self.assertEqual(self.claude_capability(result)["enabled"], "NO")
        self.assertTrue(any(c["status"] == "WARN" and "Skill tool" in c["detail"] for c in result["checks"]))

    def test_probe_reads_init_and_stops_the_host(self):
        skills = [p.parent.name for p in (self.target / ".claude" / "skills").glob("*/SKILL.md")]
        cases = (({"type": "system", "subtype": "init", "tools": ["Read", "Skill"], "skills": skills,
                   "claude_code_version": "9.9.9"}, "YES"),
                 ({"type": "system", "subtype": "init", "tools": ["Read"], "skills": skills}, "NO"),
                 ({"type": "system", "subtype": "init", "tools": ["Skill"], "skills": skills[:1]}, "NO"))
        for event, expected in cases:
            with self.subTest(expected=expected, tools=event["tools"]):
                started = time.monotonic()
                result = oaw.doctor(self.target, probe=True, probe_command=self.fake(event))
                self.assertLess(time.monotonic() - started, 20, "the host is stopped once init arrives")
                self.assertEqual(self.claude_capability(result)["enabled"], expected, self.claude_capability(result))
        quiet = oaw.doctor(self.target, probe=True, probe_command=self.fake({"type": "result"}, after=""))
        self.assertEqual(self.claude_capability(quiet)["enabled"], "UNKNOWN")
        self.assertIn("exited before reporting init", self.claude_capability(quiet)["reason"])
        missing = oaw.doctor(self.target, probe=True, probe_command=str(Path(self.temporary.name) / "no-such-claude"))
        self.assertIn("cannot start", self.claude_capability(missing)["reason"])


if __name__ == "__main__":
    unittest.main()
