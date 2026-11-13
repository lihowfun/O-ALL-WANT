"""doctor: the Skill tool denied in project settings, and --probe of Claude Code's own skill discovery (W4)."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("oaw_doctor_test", ROOT / "scripts/oaw.py")
oaw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oaw)

FAKE = """#!{python}
import json, sys, time
assert sys.argv[1:] == ["-p", "Reply with OK.", "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
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
        directory = Path(self.temporary.name) / "host commands"
        directory.mkdir(exist_ok=True)
        path = directory / f"fake-claude-{len(list(directory.glob('fake-*')))}"
        if os.name == "nt":
            path = path.with_suffix(".py")
        path.write_text(FAKE.format(python=sys.executable, event=repr(event), after=after), encoding="utf-8")
        if os.name == "nt":
            launcher = path.with_suffix(".cmd")
            launcher.write_text(f'@echo off\n"{sys.executable}" "{path}" %*\n', encoding="utf-8")
            return str(launcher)
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

    def test_probe_resolves_host_from_path(self):
        command = Path(self.fake({"type": "system", "subtype": "init", "tools": ["Skill"]}, after=""))
        with patch.dict(os.environ, {"PATH": str(command.parent) + os.pathsep + os.environ.get("PATH", "")}):
            result = oaw.probe_claude(self.target, command=command.stem)
        self.assertEqual(result.get("tools"), ["Skill"], result)

    def test_probe_passes_the_resolved_cmd_or_exe_to_popen(self):
        for extension in ("cmd", "exe"):
            resolved = rf"C:\Program Files\Claude\claude.{extension}"
            with self.subTest(extension=extension), patch.object(oaw.shutil, "which", return_value=resolved) as which:
                with patch.object(subprocess, "Popen", side_effect=OSError("fixture")) as popen:
                    result = oaw.probe_claude(self.target)
                which.assert_called_once_with("claude")
                self.assertEqual(popen.call_args.args[0], [resolved, "-p", "Reply with OK.", "--output-format",
                                                         "stream-json", "--verbose", "--no-session-persistence"])
                self.assertFalse(popen.call_args.kwargs.get("shell", False))
                self.assertIn("cannot start", result["error"])

    def test_windows_probe_stops_the_launcher_and_its_children(self):
        process = Mock(pid=123, poll=Mock(return_value=None))
        with patch.object(subprocess, "run") as run:
            oaw.stop_probe(process, platform="nt")
        self.assertEqual(run.call_args.args[0], ["taskkill", "/PID", "123", "/T", "/F"])
        process.terminate.assert_not_called()
        process.wait.assert_called_once_with(timeout=10)
        # If taskkill fails, still stop/reap the direct process; a hung process is killed and reaped.
        process.reset_mock()
        process.wait.side_effect = [subprocess.TimeoutExpired("fixture", 10), None]
        with patch.object(subprocess, "run", side_effect=OSError("fixture")):
            oaw.stop_probe(process, platform="nt")
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
