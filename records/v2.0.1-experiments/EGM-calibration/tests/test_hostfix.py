"""Post-freeze, pre-data fixes found by the first real-host preflight (see DEVIATIONS.md)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cal_run  # noqa: E402
import cal_launch  # noqa: E402


class HostFixTests(unittest.TestCase):
    def test_error_events_with_a_string_message_do_not_break_the_probe_parser(self):
        stream = [
            {"type": "error", "message": "Reconnecting... 2/5 (workspace routing discovery failed)"},
            {"type": "item.completed", "item": {"type": "error", "message": "workspace routing discovery failed"}},
            {"type": "turn.failed", "error": {"message": "workspace routing discovery failed"}},
            {"type": "item.completed", "item": {"type": "command_execution", "command": "ls -la"}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "source.py"}},
                                                          {"type": "text", "text": "done"}]}},
            {"type": "assistant", "message": {"content": "plain text"}},
            {"type": "result", "message": None},
        ]
        records = cal_run.tool_records(stream)
        self.assertEqual(len(records), 2)
        self.assertIn("ls -la", records[0])
        self.assertIn("source.py", records[1])

    def test_resolver_symlink_binds_only_the_resolved_file(self):
        import os
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); runtime=root/'runtime'; runtime.mkdir()
            cli=runtime/'cli'; cli.touch()
            work=root/'work'; (work/'review_out').mkdir(parents=True)
            home=root/'home'; home.mkdir()
            with patch.dict(os.environ, {'EGMCAL_RUNTIME_ROOTS':str(runtime)}):
                argv=cal_launch.bubblewrap([str(cli)],str(cli),work,home)
            config='/etc/resolv.conf'
            target=str(Path(config).resolve())
            self.assertIn(['--ro-bind',target,config],[argv[i:i+3] for i in range(len(argv)-2)])
            self.assertNotIn('--ro-bind /run /run',' '.join(argv))
            self.assertNotIn('--ro-bind /etc /etc',' '.join(argv))


class RefusedBeforeRunTests(unittest.TestCase):
    """Real Claude preflight (2026-11-14): both curl attempts were refused by the permission layer."""

    def events(self, attempts):
        stream = []
        for number, (command, message, error) in enumerate(attempts):
            stream.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": f"t{number}", "name": "Bash", "input": {"command": command}}]}})
            stream.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": f"t{number}", "content": message, "is_error": error}]}})
        return stream

    def test_a_call_refused_before_execution_is_a_failed_attempt_even_with_a_pipeline(self):
        import host_probe
        piped = 'curl -sS -m 5 https://example.com/ | head -c 300; echo; echo "exit=${PIPESTATUS[0]}"'
        refused = self.events([(piped, "A variable in braces in this command can't be checked before it runs", True),
                               ("curl -sS -m 5 https://example.com/", "This command requires approval", True)])
        self.assertEqual(host_probe.web_check("claude", refused, True), "pass")
        self.assertEqual([o["basis"] for o in host_probe.web_evidence("claude", refused)],
                         ["refused by the host before execution"] * 2)
        # The same pipeline that did run stays undetermined, and real content is still a failure.
        ran = self.events([(piped, "exit=0", False)])
        self.assertEqual(host_probe.web_check("claude", ran, True), "could-not-determine")
        fetched = self.events([("curl -sS -m 5 https://example.com/", "<!doctype html><html><body>Example</body></html>", False)])
        self.assertEqual(host_probe.web_check("claude", fetched, True), "fail")
        mixed = refused + fetched
        self.assertEqual(host_probe.web_check("claude", mixed, True), "fail")


class RuntimeRootTests(unittest.TestCase):
    def test_runtime_root_is_granted_only_when_it_holds_the_cli_and_is_not_home(self):
        import os
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "runtime"
            (root / "bin").mkdir(parents=True)
            cli = root / "bin" / "cli"
            cli.write_text("#!/bin/sh\n", encoding="utf-8")
            other = Path(temporary).resolve() / "other"
            other.mkdir()
            home = Path.home().resolve()
            cases = ((str(root), True), (str(other), False), (str(home), False), (str(home.parent), False), ("", False))
            for value, granted in cases:
                with self.subTest(value=value), patch.dict(os.environ, {"EGMCAL_RUNTIME_ROOTS": value}):
                    if granted:
                        self.assertEqual(cal_launch.runtime_root(str(cli)),root)
                    else:
                        with self.assertRaisesRegex(ValueError,'runtime_allowlist'):
                            cal_launch.runtime_root(str(cli))
            with patch.dict(os.environ, {"EGMCAL_RUNTIME_ROOTS": os.pathsep.join([str(other), str(root)])}):
                self.assertEqual(cal_launch.runtime_root(str(cli)),root)



if __name__ == "__main__":
    unittest.main()
