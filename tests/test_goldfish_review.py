"""A fake `claude` (a Python fixture that prints canned stream-json) exercises the goldfish
review kit; no network, no model call, no real CLI."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import goldfish_review as gr  # noqa: E402

GIT = shutil.which("git")
REAL_CLAUDE_COMMAND = gr.claude_command

# Logs argv, stdin and cwd, then prints the stream-json shape of `claude -p --verbose`.
FAKE_CLAUDE = r'''
import json, os, re, sys, time
if sys.argv[1:] == ["--version"]:
    print("9.9.9 (Claude Code)")
    raise SystemExit(0)
packet = sys.stdin.buffer.read().decode("utf-8")
cwd = os.getcwd()
with open(os.environ["FAKE_CLAUDE_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"argv": sys.argv[1:], "stdin": packet, "cwd": cwd, "entries": os.listdir(cwd)}) + "\n")
with open(os.environ["FAKE_CLAUDE_SCENARIO"], encoding="utf-8") as handle:
    scenarios = json.load(handle)
group = re.search(r'group "([^"]+)"', packet)
scenario = scenarios.get(group.group(1) if group else "", scenarios["*"])
init = {"type": "system", "subtype": "init", "cwd": cwd, "model": "fixture-model", "claude_code_version": "9.9.9",
        "permissionMode": "default", "apiKeySource": "none", "memory_paths": {"auto": scenario.get("memory", "")},
        "output_style": "default", "tools": [], "mcp_servers": [], "slash_commands": [], "skills": [],
        "plugins": [{"name": "fixture", "path": "builtin", "source": "fixture@builtin"}], "agents": ["claude"]}
for key, value in scenario.get("init", {}).items():
    if value is None:
        init.pop(key, None)
    else:
        init[key] = value
time.sleep(scenario.get("sleep", 0))
print("a line that is not JSON")
print(json.dumps(init))
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "working"}]}}))
print(json.dumps({"type": "result", "subtype": "success", "result": scenario.get("result", ""),
                  "usage": {"input_tokens": 3, "output_tokens": 5}, "total_cost_usd": 0}))
sys.stderr.write(scenario.get("stderr", ""))
raise SystemExit(scenario.get("exit", 0))
'''


def review_text(canary="none", findings=()):
    body = {"canary": canary, "findings": list(findings), "coverage": {"reviewed": ["fixture"], "not_reviewed": []},
            "summary": "fixture review"}
    return "Review follows.\n\n```json\n" + json.dumps(body, indent=1) + "\n```\n"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="oaw-gfr-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.packets, self.results = self.root / "packets", self.root / "results"
        self.packets.mkdir()
        self.fake = self.root / "fake_claude.py"
        self.fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        self.log, self.scenario_file = self.root / "calls.jsonl", self.root / "scenario.json"
        environment = patch.dict(os.environ, {"FAKE_CLAUDE_LOG": str(self.log), "FAKE_CLAUDE_SCENARIO": str(self.scenario_file)})
        environment.start()
        self.addCleanup(environment.stop)
        for key in gr.BILLING_ENV:
            os.environ.pop(key, None)
        command = patch.object(gr, "claude_command", lambda name: [sys.executable, str(self.fake)])
        command.start()
        self.addCleanup(command.stop)
        self.scenario()

    def scenario(self, **groups):
        self.scenario_file.write_text(json.dumps({"*": {"result": review_text()}, **groups}), encoding="utf-8")

    def packet(self, name):
        text = f'# Goldfish blind review packet: OAW code change, group "{name}"\n\nbody of {name}\n'
        with open(self.packets / (name + ".md"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return text

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gr.main([str(item) for item in argv])
        return code, out.getvalue(), err.getvalue()

    def run_packets(self, *extra):
        return self.main("run", "--packets", self.packets, "--results", self.results, *extra)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def result(self, name):
        return json.loads((self.results / (name + ".json")).read_text(encoding="utf-8"))


class RunTests(Fixture):
    def test_run_starts_the_cli_with_zero_context_flags_in_a_fresh_empty_temp_folder(self):
        packet = self.packet("alpha")
        with patch.object(gr, "instruction_files_above", return_value=[]):
            code, out, _ = self.run_packets()
        self.assertEqual(code, 0, out)
        call, = self.calls()
        self.assertEqual(call["argv"], ["-p", "--tools", "", "--strict-mcp-config", "--disable-slash-commands",
                                        "--setting-sources", "project", "--output-format", "stream-json", "--verbose"])
        self.assertEqual(call["stdin"], packet)
        self.assertEqual(call["entries"], [])
        self.assertTrue(os.path.basename(call["cwd"]).startswith("oaw-goldfish-"))
        self.assertFalse(os.path.exists(call["cwd"]))
        self.assertFalse(os.path.normcase(call["cwd"]).startswith(os.path.normcase(str(self.root))))
        record = self.result("alpha")
        self.assertEqual(record["launch"]["argv"], ["claude", *gr.FLAGS])
        self.assertEqual(set(record["init_checks"]), {"tools", "mcp_servers", "slash_commands", "skills", "plugins_builtin_only",
                                                      "agents_unusable_without_tools", "cwd_is_fresh_temp",
                                                      "no_instruction_files_above_cwd", "auto_memory_empty"})
        self.assertTrue(all(record["init_checks"].values()), record["init_checks"])
        self.assertTrue(record["init_checks_passed"])
        self.assertTrue(record["zero_context_verified"])
        self.assertEqual((record["billing_source"], record["api_key_allowed"], record["exit_code"]), ("none", False, 0))
        self.assertEqual(record["host_version"], "9.9.9 (Claude Code)")
        self.assertEqual(record["packet_sha256"], hashlib.sha256(packet.encode("utf-8")).hexdigest())
        self.assertEqual(record["review"]["summary"], "fixture review")
        self.assertIsNone(record["raw_result_if_unparsed"])
        self.assertTrue(record["local_paths_redacted"])

    def test_canary_and_init_checks_are_recorded_separately(self):
        """D20: the canary is recorded and keeps zero_context_verified strict; init checks stand alone."""
        memory = self.root / "memory"
        memory.mkdir()
        (memory / "MEMORY.md").write_text("- a remembered fact\n", encoding="utf-8")
        failing = {"canary": None, "tools": "tools", "plugin": "plugins_builtin_only", "cwd": "cwd_is_fresh_temp",
                   "memory": "auto_memory_empty"}
        self.scenario(canary={"result": review_text(canary="a system prompt and an account reminder")},
                      tools={"result": review_text(), "init": {"tools": ["Bash"]}},
                      plugin={"result": review_text(), "init": {"plugins": [{"source": "helper@marketplace"}]}},
                      cwd={"result": review_text(), "init": {"cwd": "/elsewhere/project"}},
                      memory={"result": review_text(), "memory": str(memory)})
        for name in failing:
            self.packet(name)
        with patch.object(gr, "instruction_files_above", return_value=[]):
            code, out, _ = self.run_packets()
        self.assertEqual(code, 0, out)
        for name, check in failing.items():
            with self.subTest(name=name):
                record = self.result(name)
                self.assertFalse(record["zero_context_verified"])
                if check is None:
                    self.assertTrue(record["init_checks_passed"])
                    self.assertEqual(record["canary"], "a system prompt and an account reminder")
                else:
                    self.assertFalse(record["init_checks"][check])
                    self.assertFalse(record["init_checks_passed"])
                    self.assertEqual(record["canary"], "none")
        self.assertFalse(self.result("tools")["init_checks"]["agents_unusable_without_tools"])

    def test_an_instruction_file_above_the_temp_folder_fails_its_check(self):
        parent = self.root / "above" / "inner"
        parent.mkdir(parents=True)
        (self.root / "above" / "CLAUDE.md").write_text("project rules\n", encoding="utf-8")
        self.packet("alpha")
        with patch.object(gr, "WORK_PARENT", str(parent)):
            code, out, _ = self.run_packets()
        self.assertEqual(code, 0, out)
        record = self.result("alpha")
        self.assertTrue(record["init_checks"]["cwd_is_fresh_temp"])
        self.assertFalse(record["init_checks"]["no_instruction_files_above_cwd"])
        self.assertFalse(record["zero_context_verified"])
        self.assertTrue(any(path.replace("\\", "/").endswith("above/CLAUDE.md") for path in record["instruction_files_above_cwd"]))

    def test_an_api_key_in_the_environment_is_refused_before_any_packet(self):
        self.packet("alpha")
        for key in gr.BILLING_ENV:
            with self.subTest(key=key), patch.dict(os.environ, {key: "sk-fixture-secret"}):
                code, out, err = self.run_packets()
                self.assertEqual(code, 2)
                self.assertIn(key, err)
                self.assertNotIn("sk-fixture-secret", out + err)
                self.assertEqual((self.calls(), self.results.exists()), ([], False))
                code, out, _ = self.run_packets("--dry-run")
                self.assertEqual(code, 0)
                self.assertIn("would run alpha.md", out)
                self.assertIn("a real run refuses without --allow-api-key", out)
                self.assertEqual(self.calls(), [])
        self.scenario(alpha={"result": review_text(), "init": {"apiKeySource": "ANTHROPIC_API_KEY"}})
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-fixture-secret"}):
            code, out, _ = self.run_packets("--allow-api-key")
        self.assertEqual(code, 0, out)
        record = self.result("alpha")
        self.assertEqual((record["billing_source"], record["api_key_allowed"]), ("ANTHROPIC_API_KEY", True))
        self.assertNotIn("sk-fixture-secret", (self.results / "alpha.json").read_text(encoding="utf-8"))

    def test_a_billing_source_other_than_none_stops_before_further_packets(self):
        self.packet("alpha")
        self.packet("beta")
        for label, init, source in (("api-key", {"apiKeySource": "ANTHROPIC_API_KEY"}, "ANTHROPIC_API_KEY"),
                                    ("unreported", {"apiKeySource": None}, "unknown")):
            with self.subTest(label=label):
                shutil.rmtree(self.results, ignore_errors=True)
                self.log.unlink(missing_ok=True)
                self.scenario(alpha={"result": review_text(), "init": init})
                code, _, err = self.run_packets()
                self.assertEqual(code, 1)
                self.assertIn("No further packet was sent", err)
                self.assertEqual(len(self.calls()), 1)
                self.assertFalse((self.results / "beta.json").exists())
                self.assertEqual(self.result("alpha")["billing_source"], source)
                code, out, _ = self.main("check", "--results", self.results)
                self.assertEqual(code, 1)
                self.assertIn("billing source " + source, out)
        shutil.rmtree(self.results)
        self.log.unlink()
        both = {"result": review_text(), "init": {"apiKeySource": "ANTHROPIC_API_KEY"}}
        self.scenario(alpha=both, beta=both)
        code, out, _ = self.run_packets("--allow-api-key")
        self.assertEqual((code, len(self.calls())), (0, 2), out)
        code, out, _ = self.main("check", "--results", self.results)
        self.assertEqual(code, 0, out)
        self.assertIn("apiKeySource ANTHROPIC_API_KEY (allowed)", out)

    def test_results_are_written_redacted_and_pass_check(self):
        home, temp = os.path.expanduser("~"), tempfile.gettempdir()
        noisy = f"read {os.path.join(home, 'notes.txt')} and {os.path.join(temp, 'x.log')}, mail owner@example.com"
        self.scenario(alpha={"result": review_text(canary="memory folder " + os.path.join(home, ".claude")), "stderr": noisy})
        self.packet("alpha")
        code, out, _ = self.run_packets()
        self.assertEqual(code, 0, out)
        written = (self.results / "alpha.json").read_text(encoding="utf-8")
        for value in (home, temp, "owner@example.com"):
            self.assertNotIn(json.dumps(value)[1:-1], written)
            self.assertNotIn(value, json.loads(written)["stderr_tail"])
        record = json.loads(written)
        self.assertTrue(record["init_event"]["cwd"].startswith("<tmp>"))
        self.assertIn("<email>", record["stderr_tail"])
        self.assertEqual(record["canary"], "memory folder " + os.path.join("~", ".claude"))
        code, out, _ = self.main("check", "--results", self.results)
        self.assertEqual(code, 0, out)
        self.assertIn("no leak found; billing ok", out)

    def test_failed_unparsed_and_timed_out_runs_are_recorded(self):
        self.scenario(broken={"exit": 1, "stderr": "fixture failure"}, unparsed={"result": "no fenced block here"})
        for name in ("broken", "fine", "unparsed"):
            self.packet(name)
        code, out, _ = self.run_packets()
        self.assertEqual(code, 1)
        self.assertIn("fixture failure", out)
        self.assertEqual(len(self.calls()), 3)
        self.assertEqual(self.result("broken")["exit_code"], 1)
        self.assertIsNotNone(self.result("fine")["review"])
        unparsed = self.result("unparsed")
        self.assertIsNone(unparsed["review"])
        self.assertEqual(unparsed["raw_result_if_unparsed"], "no fenced block here")
        self.scenario(slow={"sleep": 60, "result": review_text()})
        self.packet("slow")
        code, out, err = self.run_packets("--only", "slow", "--timeout", "2")
        self.addCleanup(shutil.rmtree, self.calls()[-1]["cwd"], True)  # a killed process can hold its folder on Windows
        self.assertEqual(code, 1)
        self.assertIn("timed out", out)
        self.assertIn("slow reports no apiKeySource", err)  # no init event: billing is unknown, so the run stops
        slow = self.result("slow")
        self.assertEqual((slow["timed_out"], slow["exit_code"], slow["review"]), (True, None, None))

    def test_only_dry_run_and_refused_inputs(self):
        self.packet("alpha")
        self.packet("beta")
        code, out, _ = self.run_packets("--only", "beta")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(path.name for path in self.results.iterdir()), ["beta.json"])
        self.assertEqual(len(self.calls()), 1)
        code, out, _ = self.run_packets("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would run alpha.md", out)
        self.assertIn('--tools ""', out)
        self.assertEqual(len(self.calls()), 1)
        code, _, err = self.run_packets("--only", "nope")
        self.assertEqual(code, 2)
        self.assertIn("nope", err)
        self.assertEqual(self.run_packets("--timeout", "0")[0], 2)
        with patch.object(gr, "claude_command", REAL_CLAUDE_COMMAND):
            code, _, err = self.run_packets("--claude", self.root / "missing" / "claude")
        self.assertEqual(code, 2)
        self.assertIn("cannot start the Claude CLI", err)
        (self.packets / "bad.md").write_bytes(b"\xff\xfe not utf-8")
        code, _, err = self.run_packets()
        self.assertEqual(code, 2)
        self.assertIn("bad.md", err)
        self.assertEqual(len(self.calls()), 1)


class ParseAndRedactTests(unittest.TestCase):
    def test_review_is_parsed_from_the_last_json_block(self):
        draft = {"canary": "draft", "findings": []}
        final = {"canary": "none", "findings": [{"id": "AL-01", "evidence": "a ``` fence and a\n```json inline"}]}
        text = ("intro\n```json\n" + json.dumps(draft) + "\n```\nthen\n```json\n" + json.dumps(final, indent=1)
                + "\n```\ntrailing words\n")
        self.assertEqual(gr.parse_review(text), final)
        self.assertEqual(gr.parse_review("```JSON  \r\n{\"canary\": \"none\"}\r\n```\r\n"), {"canary": "none"})
        # Only the last block counts: an earlier valid draft does not stand in for a broken answer.
        self.assertIsNone(gr.parse_review("```json\n" + json.dumps(draft) + "\n```\n```json\n{\"broken\": \n```\n"))
        self.assertIsNone(gr.parse_review("no fence " + json.dumps(final)))
        self.assertIsNone(gr.parse_review("```json\n[1, 2]\n```\n"))
        self.assertIsNone(gr.parse_review(""))

    def test_redaction_covers_windows_git_bash_macos_and_dash_encoded_forms(self):
        windows = gr.Redactor(paths=[("C:\\Users\\alice\\AppData\\Local\\Temp", "<tmp>"), ("C:\\Users\\alice", "~")],
                              users={"alice"})
        mac = gr.Redactor(paths=[("/var/folders/xy/abc123/T", "<tmp>"), ("/Users/alice", "~")], users={"alice"})
        cases = [
            (windows, "C:\\Users\\alice\\AppData\\Local\\Temp\\oaw-goldfish-x", "<tmp>\\oaw-goldfish-x"),
            (windows, "c:/users/ALICE/AppData/Local/Temp/oaw-goldfish-x", "<tmp>/oaw-goldfish-x"),
            (windows, "/c/Users/alice/AppData/Local/Temp/oaw-goldfish-x", "<tmp>/oaw-goldfish-x"),  # Git Bash
            (windows, "/mnt/c/Users/alice/notes", "~/notes"),  # WSL
            (windows, "C:\\\\Users\\\\alice\\\\notes", "~\\\\notes"),  # JSON-escaped
            (windows, "~/.claude/projects/C--Users-alice-AppData-Local-Temp-oaw-goldfish-x/memory/",
             "~/.claude/projects/<tmp>-oaw-goldfish-x/memory/"),
            (windows, "D:\\Users\\alice\\repo", "D:\\Users\\<user>\\repo"),
            (windows, "mail alice@example.com", "mail <email>"),
            (windows, "User settings; C:\\Users\\alice2\\x; alice wrote it", "User settings; C:\\Users\\alice2\\x; alice wrote it"),
            (mac, "/private/var/folders/xy/abc123/T/oaw-goldfish-x", "<tmp>/oaw-goldfish-x"),
            (mac, "/var/folders/xy/abc123/T/oaw-goldfish-x", "<tmp>/oaw-goldfish-x"),
            (mac, "~/.claude/projects/-private-var-folders-xy-abc123-T-oaw-goldfish-x/memory/",
             "~/.claude/projects/<tmp>-oaw-goldfish-x/memory/"),
            (mac, "/Users/alice/.claude", "~/.claude"),
            (mac, "/home/alice/x and Users-alice-y", "/home/<user>/x and Users-<user>-y"),
        ]
        for redactor, before, after in cases:
            with self.subTest(before=before):
                self.assertEqual(redactor.text(before), after)
                self.assertEqual(redactor.leaks(after), set())
        self.assertEqual(windows.redact({"C:\\Users\\alice": ["bob@example.org", 3, None]}), {"~": ["<email>", 3, None]})
        self.assertEqual(windows.leaks("C:\\\\Users\\\\alice\\\\AppData\\\\Local\\\\Temp\\\\x bob@example.org"),
                         {"temp path", "home path", "account name", "email"})
        linux = gr.Redactor(paths=[("/tmp", "<tmp>")], users=set())
        self.assertEqual(linux.text("my-tmp-file and /tmp/x"), "my-tmp-file and <tmp>/x")


class CheckTests(Fixture):
    def write_result(self, name, record):
        self.results.mkdir(exist_ok=True)
        (self.results / name).write_text(json.dumps(record, indent=1), encoding="utf-8")

    def test_check_summarizes_each_result_and_flags_billing(self):
        findings = [{"severity": "major", "kind": "bug"}, {"severity": "minor", "kind": "bug"},
                    {"severity": "minor", "kind": "weak_test"}]
        self.write_result("new.json", {"exit_code": 0, "billing_source": "none", "zero_context_verified": False,
                                       "init_event": {"model": "fixture-model", "apiKeySource": "none"},
                                       "init_checks": {"tools": True, "cwd_is_fresh_temp": False},
                                       "review": {"canary": "a prompt", "findings": findings}})
        # Results from before billing_source existed fall back to the init event.
        self.write_result("old.json", {"exit_code": 0, "init_event": {"model": "fixture-model", "apiKeySource": "none"},
                                       "review": None})
        code, out, _ = self.main("check", "--results", self.results)
        self.assertEqual(code, 0, out)
        for text in ("new.json: exit 0 | model fixture-model | apiKeySource none | zero_context_verified False",
                     "tools ok, cwd_is_fresh_temp FAILED", "review: parsed, 3 finding(s)", "severity: major 1, minor 2",
                     "kind: bug 2, weak_test 1", "old.json: exit 0", "review: not parsed, 0 finding(s)",
                     "2 result(s) checked, 0 problem(s)"):
            self.assertIn(text, out)
        self.write_result("paid.json", {"exit_code": 0, "billing_source": "ANTHROPIC_API_KEY", "review": None})
        (self.results / "torn.json").write_text("{\"exit_code\": 0,", encoding="utf-8")
        code, out, _ = self.main("check", "--results", self.results)
        self.assertEqual(code, 1)
        self.assertIn("billing source ANTHROPIC_API_KEY", out)
        self.assertIn("not a JSON object", out)
        self.assertIn("4 result(s) checked, 3 problem(s)", out)  # torn.json: not JSON and billing unknown
        self.assertEqual(self.main("check", "--results", self.root / "empty")[0], 2)

    def test_check_detects_leaks_without_echoing_them(self):
        paths = [("C:\\Users\\alice\\AppData\\Local\\Temp", "<tmp>"), ("C:\\Users\\alice", "~")]
        # A path under the home folder also names the account, so one leak may report several kinds.
        leaks = {"clean.json": ("~\\notes <tmp>\\x <email> Users\\<user>", set()),
                 "email.json": ("contact bob@example.com", {"email"}),
                 "escaped.json": ("C:\\Users\\alice\\proj", {"home path", "account name"}),  # JSON-escaped on disk
                 "gitbash.json": ("/c/Users/alice/AppData/Local/Temp/x", {"temp path"}),
                 "dash.json": ("~/.claude/projects/C--Users-alice-AppData-Local-Temp-oaw-goldfish-1/memory", {"temp path"}),
                 "account.json": ("/home/alice/x", {"account name"})}
        for name, (text, _) in leaks.items():
            self.write_result(name, {"exit_code": 0, "billing_source": "none", "stderr_tail": text})
        with patch.object(gr, "local_paths", return_value=paths), patch.object(gr, "local_users", return_value={"alice"}):
            code, out, _ = self.main("check", "--results", self.results)
        self.assertEqual(code, 1)
        self.assertIn("6 result(s) checked, 5 problem(s)", out)
        blocks = re.split(r"(?m)^(?=\S+\.json: )", out)
        for name, (_, kinds) in leaks.items():
            block = next(item for item in blocks if item.startswith(name + ":"))
            with self.subTest(name=name):
                found = re.search(r"leak: ([a-z ,]+)", block)
                if kinds:
                    self.assertLessEqual(kinds, set(found.group(1).split(", ")))
                else:
                    self.assertIsNone(found)
                    self.assertIn("no leak found", block)
        self.assertNotIn("bob@example.com", out)
        self.assertNotIn("alice", out)


class InterfaceTests(unittest.TestCase):
    def test_help_lists_operations_and_flags_without_banned_words(self):
        self.assertIn("{build,run,check}", gr.parser().format_help())
        expected = {"build": ("--spec", "--repo", "--out"),
                    "run": ("--packets", "--results", "--only", "--claude", "--timeout", "--dry-run", "--allow-api-key"),
                    "check": ("--results",)}
        for name, flags in expected.items():
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                gr.parser().parse_args([name, "--help"])
            for flag in flags:
                self.assertIn(flag, out.getvalue(), (name, flag))
        banned = re.compile(r"(?i)\bgames?\b|\bgaming\b|\bplay(?:s|ed|er|ers|ing)?\b|玩|遊戲|關卡")
        self.assertIsNone(banned.search((ROOT / "scripts" / "goldfish_review.py").read_text(encoding="utf-8")))


@unittest.skipUnless(GIT, "git is required for local fixture repositories")
class BuildTests(Fixture):
    def git(self, *args):
        subprocess.run([GIT, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "core.autocrlf=false",
                        "-c", "commit.gpgsign=false", *args], cwd=self.repo, check=True, capture_output=True)

    def setUp(self):
        super().setUp()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        files = {"alpha.py": "def alpha():\n    return 1\n", "beta.py": "def beta():\n    return 2\n",
                 "shared.py": "SHARED = 1\n", "notes.md": "# Notes\n\nplain\n"}
        self.commit(files, "base")
        self.commit({"alpha.py": "def alpha():\n    return 'ALPHA_CHANGE'\n", "beta.py": "def beta():\n    return 'BETA_CHANGE'\n",
                     "shared.py": "SHARED = 'SHARED_CHANGE'\n", "notes.md": "# Notes\n\n```json\nNOTES_CHANGE\n```\n"}, "head")
        self.out = self.root / "out"

    def commit(self, files, message):
        for name, text in files.items():
            with open(self.repo / name, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def build(self, groups, **spec):
        (self.root / "spec.json").write_text(json.dumps({"groups": groups, **spec}), encoding="utf-8")
        return self.main("build", "--spec", self.root / "spec.json", "--repo", self.repo, "--out", self.out)

    def group(self, name, prefix, paths, design):
        return {"name": name, "id_prefix": prefix, "base": "HEAD~1", "head": "HEAD", "paths": paths, "design": design}

    def test_build_isolates_each_group_to_its_own_paths(self):
        self.out.mkdir()
        (self.out / "old.md").write_text("stale\n", encoding="utf-8")
        code, out, err = self.build([self.group("alpha", "AL", ["alpha.py", "notes.md", "missing.py"], "ALPHA_DESIGN"),
                                     self.group("beta", "BE", ["beta.py"], "BETA_DESIGN")], context_lines=3)
        self.assertEqual(code, 0, err)
        alpha = (self.out / "alpha.md").read_text(encoding="utf-8")
        beta = (self.out / "beta.md").read_text(encoding="utf-8")
        for text in ('group "alpha"', "<AL-NN>", "ALPHA_DESIGN", "ALPHA_CHANGE", "NOTES_CHANGE", "### alpha.py", "### notes.md",
                     "3 lines of context", "Only the files of this group are shown"):
            self.assertIn(text, alpha)
        for text in ("BETA_CHANGE", "BETA_DESIGN", "SHARED_CHANGE", "### shared.py", "### missing.py"):
            self.assertNotIn(text, alpha)
        for text in ('group "beta"', "<BE-NN>", "BETA_DESIGN", "BETA_CHANGE", "### beta.py"):
            self.assertIn(text, beta)
        for text in ("ALPHA_CHANGE", "ALPHA_DESIGN", "NOTES_CHANGE", "SHARED_CHANGE"):
            self.assertNotIn(text, beta)
        # The notes diff holds a ``` fence, so its own fence is longer and cannot be closed early.
        self.assertIn("\n````diff\n", alpha)
        self.assertIn("\n```diff\n", beta)
        self.assertRegex(out, r"alpha: \d+ bytes, \d+ characters, 2 changed path\(s\)")
        self.assertRegex(out, r"beta: \d+ bytes, \d+ characters, 1 changed path\(s\)")
        self.assertIn("unchanged, left out: missing.py", out)
        self.assertIn("old.md", out)

    def test_build_refuses_an_empty_group_or_unknown_revision_without_writing(self):
        alpha = self.group("alpha", "AL", ["alpha.py"], "design")
        # Literal pathspecs: '*.py' names a file called *.py, not every Python file of other groups.
        for label, other, message in (("glob", self.group("glob", "GL", ["*.py"], "design"), "no change to its paths"),
                                      ("unchanged", self.group("same", "SA", ["missing.py"], "design"), "no change to its paths"),
                                      ("revision", {**self.group("rev", "RV", ["beta.py"], "design"), "head": "no-such-branch"},
                                       "is not a commit")):
            with self.subTest(label=label):
                code, _, err = self.build([alpha, other])
                self.assertEqual(code, 2)
                self.assertIn(message, err)
                self.assertFalse(self.out.exists())


class SpecTests(Fixture):
    def test_spec_validation_refuses_unsafe_or_ambiguous_groups(self):
        good = {"name": "alpha", "id_prefix": "AL", "base": "HEAD~1", "head": "HEAD", "paths": ["alpha.py"], "design": "d"}
        bad = {
            "parent path": {**good, "paths": ["../outside.py"]},
            "absolute path": {**good, "paths": ["/etc/passwd"]},
            "drive path": {**good, "paths": ["C:\\x.py"]},
            "newline path": {**good, "paths": ["a.py\n### b.py"]},
            "empty paths": {**good, "paths": []},
            "name with separator": {**good, "name": "../evil"},
            "reserved name": {**good, "name": "con"},
            "option revision": {**good, "base": "--output=x"},
            "lower prefix": {**good, "id_prefix": "al"},
            "missing design": {key: value for key, value in good.items() if key != "design"},
            "unknown key": {**good, "path": ["typo.py"]},
        }
        for label, group in bad.items():
            with self.subTest(label=label):
                with self.assertRaises(gr.Refusal):
                    gr.load_spec(self.spec_file({"groups": [group]}))
        for label, spec in (("duplicate", {"groups": [good, {**good, "name": "ALPHA"}]}), ("no groups", {"groups": []}),
                            ("context", {"groups": [good], "context_lines": -1}), ("list", [good])):
            with self.subTest(label=label):
                with self.assertRaises(gr.Refusal):
                    gr.load_spec(self.spec_file(spec))
        context, groups = gr.load_spec(self.spec_file({"groups": [{**good, "paths": ["scripts\\a.py", "./scripts/a.py", "docs/"]}]}))
        self.assertEqual((context, groups[0]["paths"]), (25, ["scripts/a.py", "docs"]))
        code, _, err = self.main("build", "--spec", self.spec_file({"groups": [bad["parent path"]]}), "--repo", self.root,
                                 "--out", self.root / "out")
        self.assertEqual(code, 2)
        self.assertIn("refused:", err)
        self.assertFalse((self.root / "out").exists())

    def spec_file(self, spec):
        path = self.root / "spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
