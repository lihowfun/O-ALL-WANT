"""User skill installs (plan 2.0.1 W3, D34): oaw.py add / list / remove on local fixtures, no network."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_verdicts  # noqa: E402
import catalog_core as core  # noqa: E402
import oaw  # noqa: E402
import user_install  # noqa: E402

MIT = "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software.\n"


def tree(root: Path, *, skip=()) -> dict:
    """Every file under root (bytes and mode), so a test can assert byte-for-byte restoration."""
    found = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file() and not any(relative.startswith(prefix) for prefix in skip):
            found[relative] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    return found


def digest_tree(root: Path, **kwargs) -> dict:
    return {k: (hashlib.sha256(v[0]).hexdigest(), v[1]) for k, v in tree(root, **kwargs).items()}


class UserInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oaw-user-install-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.markers = self.base / "markers"
        self.markers.mkdir()
        self.sources = self.base / "sources"
        self.project = self.base / "project"
        self.project.mkdir()
        self.config = self.base / "config"
        self.fixtures = self.make_fixtures()
        self.verdicts = self.base / "verdicts.json"
        self.write_verdicts()
        environment = patch.dict(os.environ, {"OAW_CONFIG_HOME": str(self.config), "OAW_VERDICTS": str(self.verdicts)})
        environment.start()
        self.addCleanup(environment.stop)

    # ------------------------------------------------------------------ fixtures

    def put(self, root: Path, relative: str, text: str, mode: int = 0o644) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        os.chmod(path, mode)

    def runs(self, name: str) -> str:
        """Python that leaves a marker file if anything ever executes it."""
        return f"open({str(self.markers / name)!r}, 'w').write('ran')\n"

    def make_fixtures(self) -> dict:
        hooky = self.sources / "hooky"
        self.put(hooky, "skills/hooky/SKILL.md", "---\nname: hooky\ndescription: Guard shell commands.\n---\n\nFollow the guard.\n")
        self.put(hooky, "hooks/hooks.json", json.dumps({"hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/guard.py\""}]}],
            "SessionStart": [{"hooks": [{"type": "command", "command": "bash hooks/start.sh"}]}]}}, indent=2))
        self.put(hooky, "hooks/guard.py", self.runs("hook-guard"), 0o755)
        self.put(hooky, "hooks/start.sh", f"echo ran > {self.markers / 'hook-start'}\n", 0o755)
        self.put(hooky, ".mcp.json", json.dumps({"mcpServers": {"hooky-server": {"command": "python3", "args": ["mcp/server.py"]}}}))
        self.put(hooky, "mcp/server.py", self.runs("mcp-server"))
        self.put(hooky, "setup.py", "from setuptools import setup\n" + self.runs("setup-py") + "setup()\n")
        self.put(hooky, "package.json", json.dumps({"name": "hooky", "scripts": {"postinstall": "node postinstall.js"}}))
        self.put(hooky, "postinstall.js", f"require('fs').writeFileSync({json.dumps(str(self.markers / 'postinstall'))}, 'ran')\n")
        self.put(hooky, "LICENSE", MIT)
        twin = self.sources / "twin"
        self.put(twin, "SKILL.md", "---\nname: oaw-review\ndescription: Another review skill that took OAW's name.\n---\n\nReview.\n")
        mapper = self.sources / "mapper"
        self.put(mapper, "SKILL.md", "---\nname: mapper\ndescription: Map callers in a repository.\n---\n\nMap.\n")
        scripty = self.sources / "scripty"
        self.put(scripty, "tool/SKILL.md", "---\nname: scripty\ndescription: Summarize a log file.\n---\n\nRun `python3 scripts/run.py LOG`.\n")
        self.put(scripty, "tool/scripts/run.py", self.runs("bundled-script"), 0o755)
        pinger = self.sources / "pinger"
        self.put(pinger, "hooks/hooks.json", json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "bash hooks/ping.sh"}]}]}}))
        self.put(pinger, "hooks/ping.sh", f"echo ran > {self.markers / 'ping'}\n", 0o755)
        self.put(pinger, "skills/pinger/SKILL.md", "---\nname: pinger\ndescription: Ping before tools.\n---\n\nPing.\n")
        return {name: str(self.sources / name) for name in ("hooky", "twin", "mapper", "scripty", "pinger")}

    def key(self, name: str) -> str:
        return "file://" + Path(self.fixtures[name]).as_posix()

    def write_verdicts(self) -> None:
        def tasting(outcome, label):
            return {"date": "2026-11-07", "outcome": outcome, "label_zh": label, "verdict": "decline" if outcome == "excrete" else outcome,
                    "conditions": {"corpus": "fixture corpus", "models": ["model-x"], "questions": 12, "repeats": 1},
                    "evidence": {"branch": "records", "commit": "abc1234", "path": "records/fixture"}, "reason_zh": label}
        document = {"schema": "oaw-verdicts/1", "categories": {"code-map": "程式碼地圖", "review": "審查、批判"},
                    "builtin": {"oaw-codemap": {"category": "code-map"}, "oaw-review": {"category": "review"}},
                    "foods": [
                        {"id": "hooky", "key": self.key("hooky"), "category": None, "commit": None, "tasting": tasting("default", "進預設（更好）")},
                        {"id": "twin", "key": self.key("twin"), "category": None, "commit": None, "tasting": tasting("excrete", "排掉（比原生差）")},
                        {"id": "mapper", "key": self.key("mapper"), "category": "code-map", "commit": None, "tasting": tasting("optional", "可選用（能力未定）")},
                    ]}
        self.verdicts.write_text(json.dumps(document), encoding="utf-8")

    def test_a_local_source_never_writes_its_path_into_the_project(self):
        self.add("scripty", choice="oaw", consent="all", apply=True)
        text = (self.project / ".oaw" / "user-skills.json").read_text(encoding="utf-8")
        self.assertNotIn(str(self.sources), text)
        self.assertNotIn("file://", text)
        self.assertIn('"key": "local:', text)
        again = self.add("scripty", choice="oaw", consent="all")
        self.assertIn("已經裝過", json.dumps(again, ensure_ascii=False), "the hashed key still finds the earlier install")
        listed = json.dumps(self.cli("list"), ensure_ascii=False)
        self.assertIn("local/scripty", listed)
        self.assertNotIn(str(self.sources), listed)

    # ------------------------------------------------------------------ helpers

    def cli(self, *args, code=0):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            actual = oaw.main([*args, "--target", str(self.project), "--json"])
        self.assertEqual(actual, code, out.getvalue() + err.getvalue())
        return json.loads(out.getvalue())

    def init(self):
        return self.cli("init")

    def add(self, *names, **flags):
        args = ["add", *[self.fixtures[n] for n in names]]
        for flag, value in flags.items():
            if flag == "code":
                continue
            if value is True:
                args.append("--" + flag.replace("_", "-"))
            elif isinstance(value, list):
                for item in value:
                    args += ["--" + flag.replace("_", "-"), item]
            else:
                args += ["--" + flag.replace("_", "-"), value]
        return self.cli(*args, code=flags.get("code", 0))

    def seed_settings(self):
        """Pre-existing project settings that must survive every add and remove byte for byte."""
        self.put(self.project, ".claude/settings.json",
                 '{\n    "permissions": {"allow": ["Bash(ls)"]},\n    "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo mine"}]}]}\n}\n')
        self.put(self.project, ".mcp.json", '{"mcpServers": {"mine": {"command": "my-server"}}}\n')
        return (self.project / ".claude/settings.json").read_bytes(), (self.project / ".mcp.json").read_bytes()

    def assert_nothing_ran(self):
        self.assertEqual(sorted(p.name for p in self.markers.iterdir()), [])

    def rows(self):
        return {row["skill"].split("（")[0].split("，")[0]: row for row in self.cli("list")["receipt"]}

    # ------------------------------------------------------------------ preview

    def test_preview_writes_nothing_on_clean_and_installed_projects(self):
        for installed in (False, True):
            with self.subTest(installed=installed):
                if installed:
                    self.init()
                before = tree(self.base, skip=("config/",))
                config_before = tree(self.config) if self.config.exists() else {}
                result = self.add("hooky", "twin", "mapper", "scripty")
                self.assertEqual(result["status"], "preview")
                self.assertEqual(tree(self.base, skip=("config/",)), before)
                self.assertEqual(tree(self.config) if self.config.exists() else {}, config_before)
                self.assertIn("1 ①", result["question"])
                self.assertIn("oaw-review", result["question"])
                self.assertIn("hooks", result["consent_needed"])
                self.assertIn("--apply", result["apply_command"])
                self.assert_nothing_ran()

    # ------------------------------------------------------------------ choice 1

    def test_choice_oaw_on_clean_project_then_remove_one_restores_exactly(self):
        settings, mcp = self.seed_settings()
        result = self.add("hooky", "twin", "mapper", "scripty", "pinger", choice="oaw", consent="all",
                          on_conflict=["oaw-review=rename", "mapper=keep-both"], apply=True)
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["oaw_step"]["kind"], "init")
        self.assertTrue((self.project / "AGENTS.md").is_file())
        for skill in ("hooky", "oaw-review-2", "mapper", "scripty", "pinger", "oaw-review", "oaw-codemap"):
            self.assertTrue((self.project / ".agents/skills" / skill / "SKILL.md").is_file(), skill)
        renamed = (self.project / ".agents/skills/oaw-review-2/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: oaw-review-2", renamed)
        self.assertTrue(os.access(self.project / ".agents/skills/scripty/scripts/run.py", os.X_OK))
        hooks = json.loads((self.project / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]
        commands = [h["command"] for group in hooks["PreToolUse"] for h in group["hooks"]]
        self.assertEqual(commands[0], "echo mine")
        self.assertIn('python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/hooky/hooks/guard.py"', commands)
        self.assertIn('bash "${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/pinger/hooks/ping.sh"', commands)
        self.assertTrue((self.project / ".claude/oaw-user/hooky/hooks/guard.py").is_file())
        servers = json.loads((self.project / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        self.assertEqual(sorted(servers), ["hooky-server", "mine"])
        self.assertEqual(servers["hooky-server"]["args"], ["${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/hooky/mcp/server.py"])
        self.assertFalse((self.project / "setup.py").exists())
        self.assertFalse((self.project / ".agents/skills/hooky/setup.py").exists())
        rows = self.rows()
        self.assertEqual(rows["oaw-review"]["added_by"], "OAW 內建")
        self.assertEqual(rows["scripty"]["added_by"], "你")
        self.assertTrue(rows["scripty"]["tasting"].startswith("未試吃"))
        self.assertIn("catalog.py taste scripty", rows["scripty"]["tasting"])
        self.assertIn("進預設（更好）", rows["hooky"]["tasting"])
        self.assertIn("hook：PreToolUse、SessionStart", rows["hooky-hooks"]["runs"])
        self.assertEqual(rows["hooky-server"]["runs"], "MCP server")
        self.assertEqual(rows["scripty"]["runs"], "1 個 script")
        self.assertEqual(rows["mapper"]["remove"], "oaw.py remove mapper")
        record = json.loads((self.project / ".oaw/user-skills.json").read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], "oaw-user-skills/1")
        self.assertEqual(record["packages"]["hooky"]["consents"], ["hooks", "mcp", "scripts"])
        self.assertEqual(record["packages"]["hooky"]["license"]["spdx"], "MIT")
        self.assertIsNone(record["packages"]["twin"]["source"]["path"])  # never a local path in the project
        self.assertTrue(record["packages"]["twin"]["source"]["key"].startswith("local:"))
        self.assertTrue(record["packages"]["twin"]["source"]["tree_sha256"])
        self.assertTrue(self.cli("doctor")["status"] == "healthy")

        before = tree(self.project)
        result = self.cli("remove", "hooky")
        self.assertEqual(result["status"], "removed")
        self.assertEqual(result["conflicts"], [])
        after = tree(self.project)
        hooky_paths = {p for p in before if p.startswith((".agents/skills/hooky/", ".claude/oaw-user/hooky/"))}
        changed = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
        state = {p for p in changed if p.startswith(".oaw/user-skills/")}  # the .mcp.json baseline is no longer needed
        self.assertEqual(changed - hooky_paths - state, {".claude/settings.json", ".mcp.json", ".oaw/user-skills.json"})
        self.assertFalse(any(p in after for p in hooky_paths))
        hooks = json.loads(after[".claude/settings.json"][0])["hooks"]
        self.assertEqual([h["command"] for group in hooks["PreToolUse"] for h in group["hooks"]],
                         ["echo mine", 'bash "${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/pinger/hooks/ping.sh"'])
        self.assertNotIn("SessionStart", hooks)
        self.assertEqual(after[".mcp.json"][0], mcp)
        self.assertNotIn("hooky", json.loads(after[".oaw/user-skills.json"][0])["packages"])
        for name in ("pinger", "scripty", "mapper", "twin"):
            self.cli("remove", name)
        self.assertEqual((self.project / ".claude/settings.json").read_bytes(), settings)
        self.assertEqual((self.project / ".mcp.json").read_bytes(), mcp)
        self.assertFalse((self.project / ".oaw/user-skills.json").exists())
        self.assertFalse((self.project / ".oaw/user-skills").exists())
        self.assertFalse((self.project / ".claude/oaw-user").exists())
        self.assert_nothing_ran()

    def test_choice_oaw_on_installed_project_replace_restores_oaw_file(self):
        self.init()
        original = (self.project / ".agents/skills/oaw-review/SKILL.md").read_bytes()
        before = tree(self.project)
        self.add("twin", choice="oaw", on_conflict=["oaw-review=replace"], apply=True)
        self.assertEqual((self.project / ".agents/skills/oaw-review/SKILL.md").read_bytes(),
                         (Path(self.fixtures["twin"]) / "SKILL.md").read_bytes())
        doctor = self.cli("doctor")
        self.assertEqual(doctor["status"], "healthy")
        self.assertTrue(any(c["status"] == "WARN" and c["path"] == ".agents/skills/oaw-review/SKILL.md" for c in doctor["checks"]))
        self.cli("remove", "oaw-review")
        self.assertEqual((self.project / ".agents/skills/oaw-review/SKILL.md").read_bytes(), original)
        self.assertEqual(tree(self.project), before)

    def test_same_name_and_consent_need_answers_before_apply(self):
        self.init()
        before = tree(self.project)
        result = self.add("twin", choice="oaw", apply=True, code=3)
        self.assertEqual(result["status"], "needs-choice")
        self.assertEqual(result["conflicts"][0]["options"], ["rename", "skip", "replace"])
        result = self.add("hooky", choice="oaw", apply=True, code=3)
        self.assertEqual(sorted(result["consent_needed"]), ["hooks", "mcp"])
        self.assertEqual(tree(self.project), before)

    def test_refused_consent_installs_only_what_does_not_run_on_its_own(self):
        settings, mcp = self.seed_settings()
        self.init()
        result = self.add("hooky", "scripty", choice="oaw", consent="none", apply=True)
        parts = {p["name"]: p for package in result["packages"] for p in package["parts"]}
        self.assertEqual(parts["hooky"]["status"], "install")
        for name in ("hooky-hooks", "hooky-server", "scripty"):
            self.assertEqual(parts[name]["status"], "skip", name)
            self.assertIn("沒有同意", parts[name]["reason"])
        self.assertEqual((self.project / ".claude/settings.json").read_bytes(), settings)
        self.assertEqual((self.project / ".mcp.json").read_bytes(), mcp)
        self.assertFalse((self.project / ".agents/skills/scripty").exists())
        self.assertFalse((self.project / ".claude/oaw-user").exists())
        result = self.add("hooky", choice="oaw", consent="hooks", apply=True)
        self.assertEqual(result["packages"][0]["status"], "skip")
        self.assertIn("已經裝過", result["packages"][0]["reason"])

    def test_overlap_use_theirs_retires_oaw_skill_and_remove_brings_it_back(self):
        self.init()
        codemap = self.project / ".agents/skills/oaw-codemap/SKILL.md"
        original = codemap.read_bytes()
        preview = self.add("mapper", choice="oaw")
        overlap = [c for c in preview["conflicts"] if c["type"] == "overlap"][0]
        self.assertEqual(overlap["with"], ["oaw-codemap"])
        self.assertEqual(overlap["options"], ["keep-both", "use-theirs", "use-oaw"])
        result = self.add("mapper", choice="oaw", on_conflict=["mapper=use-theirs"], apply=True)
        self.assertEqual(result["oaw_step"]["kind"], "retire")
        self.assertFalse(codemap.exists())
        self.assertNotIn("oaw-codemap", json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))["skills"])
        self.assertEqual(self.cli("list")["retired_oaw_skills"], ["oaw-codemap"])
        self.assertEqual(self.cli("doctor")["status"], "healthy")
        removed = self.cli("remove", "mapper")
        self.assertEqual(removed["restored_oaw"], ["oaw-codemap"])
        self.assertEqual(codemap.read_bytes(), original)
        self.assertIn("oaw-codemap", json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))["skills"])
        result = self.add("mapper", choice="oaw", on_conflict=["mapper=use-oaw"], apply=True)
        self.assertEqual(result["packages"][0]["status"], "skip")
        self.assertFalse((self.project / ".agents/skills/mapper").exists())

    def test_remove_leaves_what_the_user_changed(self):
        self.seed_settings()
        self.add("hooky", "mapper", choice="oaw", consent="all", on_conflict=["mapper=keep-both"], apply=True)
        skill = self.project / ".agents/skills/mapper/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nmy note\n", encoding="utf-8")
        settings = json.loads((self.project / ".claude/settings.json").read_text(encoding="utf-8"))
        settings["hooks"]["SessionStart"][0]["hooks"][0]["command"] = "bash my-own.sh"
        (self.project / ".claude/settings.json").write_text(json.dumps(settings, indent=4) + "\n", encoding="utf-8")
        result = self.cli("remove", "mapper", code=3)
        self.assertEqual([c["path"] for c in result["conflicts"]], [".agents/skills/mapper/SKILL.md"])
        self.assertIn("my note", skill.read_text(encoding="utf-8"))
        result = self.cli("remove", "hooky", code=3)
        self.assertEqual([c["path"] for c in result["conflicts"]], [".claude/settings.json hooks.SessionStart"])
        settings = json.loads((self.project / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["hooks"]["SessionStart"][0]["hooks"][0]["command"], "bash my-own.sh")
        self.assertEqual([h["command"] for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]], ["echo mine"])

    def test_settings_that_are_not_plain_json_block_only_hooks(self):
        self.init()
        self.put(self.project, ".claude/settings.json", '{\n  // my comment\n  "hooks": {}\n}\n')
        before = (self.project / ".claude/settings.json").read_bytes()
        result = self.add("hooky", choice="oaw", consent="all", apply=True)
        parts = {p["name"]: p["status"] for p in result["packages"][0]["parts"]}
        self.assertEqual(parts["hooky-hooks"], "blocked")
        self.assertEqual(parts["hooky-server"], "install")
        self.assertEqual((self.project / ".claude/settings.json").read_bytes(), before)

    def test_use_theirs_without_an_installed_part_changes_nothing(self):
        self.init()
        before = tree(self.project)
        self.put(self.sources, "mapper/tool.py", self.runs("mapper-tool"), 0o755)  # now the skill bundles a script
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = oaw.main(["add", self.fixtures["mapper"], "--target", str(self.project), "--choice", "oaw", "--consent", "none",
                             "--on-conflict", "mapper=use-theirs", "--apply", "--json"])
        self.assertEqual(code, 2)
        self.assertIn("use-theirs", json.loads(out.getvalue())["error"])
        self.assertEqual(tree(self.project), before)

    def test_builtin_skill_removal_previews_then_applies(self):
        self.init()
        before = tree(self.project)
        preview = self.cli("remove", "oaw-codemap")
        self.assertEqual(preview["status"], "preview")
        self.assertEqual(tree(self.project), before)
        self.cli("remove", "oaw-codemap", "--apply")
        self.assertFalse((self.project / ".agents/skills/oaw-codemap").exists())
        self.assertNotIn("oaw-codemap", self.rows())
        self.assertEqual(self.cli("doctor")["status"], "healthy")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(oaw.main(["remove", "nothing-here", "--target", str(self.project)]), 2)

    def test_claude_host_gets_claude_folders(self):
        self.add("mapper", "scripty", choice="only", host="claude", consent="scripts", apply=True)
        self.assertTrue((self.project / ".claude/skills/mapper/SKILL.md").is_file())
        self.assertTrue((self.project / ".claude/skills/scripty/scripts/run.py").is_file())
        self.assertFalse((self.project / ".agents").exists())
        self.assertEqual(json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))["hosts"], ["claude"])

    def test_a_new_host_adds_oaw_folders_for_it_too(self):
        self.init()
        result = self.add("mapper", choice="oaw", host="claude", on_conflict=["mapper=keep-both"], apply=True)
        self.assertEqual(result["oaw_step"]["kind"], "hosts")
        self.assertEqual(json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))["hosts"], ["codex", "claude"])
        for root in (".agents/skills", ".claude/skills"):
            self.assertTrue((self.project / root / "mapper/SKILL.md").is_file())
            self.assertTrue((self.project / root / "oaw-review/SKILL.md").is_file())
        self.assertEqual(self.cli("doctor")["status"], "healthy")

    def test_use_theirs_warns_when_project_policy_names_the_oaw_skill(self):
        self.init()
        self.put(self.sources, "mapper/SKILL.md", "---\nname: reviewer\ndescription: Review changes.\n---\n\nReview.\n")
        verdicts = json.loads(self.verdicts.read_text(encoding="utf-8"))
        verdicts["foods"][2]["category"] = "review"
        self.verdicts.write_text(json.dumps(verdicts), encoding="utf-8")
        preview = self.add("mapper", choice="oaw", on_conflict=["mapper=use-theirs"])
        self.assertTrue(any("AGENTS.md 還提到 oaw-review" in note for note in preview["notes"]))

    # ------------------------------------------------------------------ choice 2

    def test_choice_only_on_clean_project_is_manager_only(self):
        result = self.add("mapper", "scripty", choice="only", consent="scripts", apply=True)
        self.assertEqual(result["status"], "installed")
        manifest = json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["profile"], manifest["managed_files"], manifest["skills"]), ("manager-only", {}, []))
        for absent in ("AGENTS.md", "CLAUDE.md", "scripts", ".agents/skills/oaw-review", ".oaw/integrations"):
            self.assertFalse((self.project / absent).exists(), absent)
        self.assertTrue((self.project / ".agents/skills/mapper/SKILL.md").is_file())
        doctor = self.cli("doctor")
        self.assertEqual(doctor["status"], "healthy", doctor["checks"])
        rows = self.cli("list")["receipt"]
        self.assertEqual({row["added_by"] for row in rows}, {"你"})
        self.assertEqual(self.add("twin")["choice"], "only")  # a manager-only project keeps its choice by default
        self.cli("remove", "mapper")
        self.cli("remove", "scripty")
        self.assertEqual(sorted(p.relative_to(self.project).as_posix() for p in self.project.rglob("*") if p.is_file()), [".oaw/install.json"])

    def test_choice_only_without_sources_switches_an_installed_project(self):
        self.init()
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(oaw.main(["add", "--target", str(self.project), "--choice", "only", "--apply", "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue())["oaw_step"]["kind"], "manager-only")
        self.assertEqual(sorted(p.relative_to(self.project).as_posix() for p in self.project.rglob("*") if p.is_file()
                                and not p.relative_to(self.project).as_posix().startswith(".oaw/backups/")), [".oaw/install.json"])
        self.assertEqual(self.cli("doctor")["status"], "healthy")

    def test_choice_only_on_installed_project_keeps_project_policy_and_switches_back(self):
        self.init()
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "\nOur own rule.\n", encoding="utf-8")
        before = tree(self.project)
        preview = self.add("mapper", choice="only")
        self.assertEqual(preview["oaw_step"]["kind"], "manager-only")
        self.assertIn({"path": "AGENTS.md", "action": "preserve-retired-edit"}, preview["oaw_step"]["actions"])
        self.assertEqual(tree(self.project), before)
        migrate_preview = self.cli("migrate", "--profile", "manager-only")
        self.assertEqual(migrate_preview["status"], "dry-run")
        self.assertEqual(tree(self.project), before)
        self.add("mapper", choice="only", apply=True)
        manifest = json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["profile"], "manager-only")
        self.assertEqual(manifest["custom_files"], ["AGENTS.md"])
        self.assertIn("Our own rule.", agents.read_text(encoding="utf-8"))
        for gone in ("CLAUDE.md", ".agents/skills/oaw-review", "scripts/oaw_mode.py", ".oaw/integrations/egm"):
            self.assertFalse((self.project / gone).exists(), gone)
        self.assertTrue((self.project / ".agents/skills/mapper/SKILL.md").is_file())
        self.assertEqual(self.cli("doctor")["status"], "healthy")
        self.cli("init", "--profile", "minimal")
        manifest = json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["profile"], "minimal")
        self.assertIn("oaw-review", manifest["skills"])
        self.assertTrue((self.project / ".agents/skills/oaw-review/SKILL.md").is_file())
        self.assertIn("Our own rule.", agents.read_text(encoding="utf-8"))
        self.assertTrue((self.project / ".agents/skills/mapper/SKILL.md").is_file())

    # ------------------------------------------------------------------ choice 3

    def test_choice_recommended_follows_the_records_on_clean_and_installed_projects(self):
        for installed in (False, True):
            with self.subTest(installed=installed):
                if installed:
                    self.init()
                result = self.add("hooky", "twin", "mapper", "scripty", choice="recommended", consent="all", apply=True)
                packages = {p["name"]: p for p in result["packages"]}
                self.assertEqual(packages["twin"]["status"], "skip")
                self.assertIn("不建議：排掉（比原生差）", packages["twin"]["reason"])
                self.assertIn("fixture corpus", packages["twin"]["reason"])
                self.assertEqual(packages["hooky"]["recommendation"]["action"], "install")
                self.assertEqual(packages["mapper"]["recommendation"]["action"], "explicit")
                self.assertEqual(packages["scripty"]["recommendation"]["action"], "install")
                self.assertIn("未試吃", packages["scripty"]["recommendation"]["reason"])
                self.assertTrue(all(p["recommendation"]["reason"] for p in packages.values()))
                mapper = (self.project / ".agents/skills/mapper/SKILL.md").read_text(encoding="utf-8")
                self.assertIn("disable-model-invocation: true", mapper)
                self.assertIn("allow_implicit_invocation: false",
                              (self.project / ".agents/skills/mapper/agents/openai.yaml").read_text(encoding="utf-8"))
                rows = self.rows()
                self.assertIn("只在你叫它時用", rows["mapper"]["skill"])
                self.assertEqual(rows["mapper"]["startup"], "0（只在你叫它時載入）")
                self.assertIn("可選用（能力未定）", rows["mapper"]["tasting"])
                self.assertFalse((self.project / ".agents/skills/oaw-review-2").exists())
                self.assertTrue((self.project / "AGENTS.md").is_file())
                for name in ("hooky", "mapper", "scripty"):
                    self.cli("remove", name)
                self.assertFalse((self.project / ".oaw/user-skills.json").exists())
        self.assert_nothing_ran()

    # ------------------------------------------------------------------ one question

    def test_terminal_asks_exactly_one_question(self):
        asked = []

        def ask(prompt):
            asked.append(prompt)
            return "1 hooks,mcp,scripts oaw-review=rename"
        result, code = user_install.add(self.project, [self.fixtures[n] for n in ("hooky", "twin", "scripty")], ask=ask)
        self.assertEqual((code, result["status"], len(asked)), (0, "installed", 1))
        self.assertIn("同名 → rename / skip / replace", asked[0])
        self.assertTrue((self.project / ".agents/skills/oaw-review-2/SKILL.md").is_file())
        self.assertTrue((self.project / ".claude/oaw-user/hooky/hooks/guard.py").is_file())
        result, code = user_install.add(self.project, [self.fixtures["mapper"]], ask=lambda _prompt: "0")
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse((self.project / ".agents/skills/mapper").exists())
        result, code = user_install.add(self.project, [self.fixtures["mapper"]], ask=lambda _prompt: "")
        self.assertEqual(result["status"], "installed")  # Enter: choice 1, keep both, no consent needed here
        self.assert_nothing_ran()

    # ------------------------------------------------------------------ sources, records, boundaries

    def test_fetched_code_is_never_executed(self):
        self.add("hooky", "scripty", "pinger", choice="oaw", consent="all", apply=True)
        self.cli("list")
        self.cli("doctor")
        for name in ("hooky", "scripty", "pinger"):
            self.cli("remove", name)
        self.assert_nothing_ran()
        self.assertFalse(any(p.name.startswith("MARKER") for p in self.project.rglob("*")))

    def test_sources_parse_without_network(self):
        verdicts = {"schema": "oaw-verdicts/1", "categories": {}, "builtin": {}, "foods": [
            {"id": "graphify", "key": "github.com/graphify-labs/graphify", "url": "https://github.com/Graphify-Labs/graphify",
             "repo": "Graphify-Labs/graphify", "commit": "8e6a6d2129d4aeffc7a0e9ed79b153f7f057f42b", "category": None, "tasting": None}]}
        source = user_install.parse_source("https://github.com/owner/repo@v1.2", verdicts)
        self.assertEqual((source["kind"], source["key"], source["ref"]), ("github", "github.com/owner/repo", "v1.2"))
        source = user_install.parse_source("graphify", verdicts)
        self.assertEqual((source["display"], source["ref"], source["from_verdicts"]),
                         ("Graphify-Labs/graphify", "8e6a6d2129d4aeffc7a0e9ed79b153f7f057f42b", "graphify"))
        source = user_install.parse_source(self.fixtures["mapper"], verdicts)
        self.assertEqual(source["kind"], "local")
        for bad in ("https://gitlab.com/a/b", "owner/repo@-x", "not a source"):
            with self.assertRaises(oaw.InstallError):
                user_install.parse_source(bad, verdicts)

    def test_record_paths_stay_inside_the_boundary(self):
        self.add("mapper", choice="oaw", on_conflict=["mapper=keep-both"], apply=True)
        path = self.project / ".oaw/user-skills.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        for bad in ("AGENTS.md", "../outside", ".git/config"):
            tampered = json.loads(json.dumps(record))
            tampered["packages"]["mapper"]["parts"]["skill:mapper"]["files"][0]["path"] = bad
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(oaw.InstallError):
                user_install.load_record(self.project)
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(oaw.InstallError):
            user_install._dest(self.project, "AGENTS.md")
        with self.assertRaises(oaw.InstallError):
            user_install._dest(self.project, ".claude/skills/../../x")

    def test_init_records_the_checkout_outside_the_project(self):
        result = self.init()
        setting = self.config / "checkout.json"
        self.assertEqual(result["checkout_setting"], str(setting))
        self.assertEqual(json.loads(setting.read_text(encoding="utf-8"))["path"], str(ROOT.resolve()))
        self.assertFalse(any("checkout.json" in p.name for p in self.project.rglob("*")))

    # ------------------------------------------------------------------ review round 12

    def test_apply_command_is_quoted_and_sources_with_queries_are_refused(self):
        verdicts = user_install.load_verdicts()
        for bad in ("https://github.com/owner/repo?x=$(id)", "https://github.com/owner/repo#$(id)", "owner/repo?ref=main"):
            with self.assertRaises(oaw.InstallError, msg=bad):
                user_install.parse_source(bad, verdicts)
        odd = self.sources / "my skill $(id)"
        self.put(odd, "SKILL.md", "---\nname: odd\ndescription: A skill in an oddly named folder.\n---\n\nOdd.\n")
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(oaw.main(["add", str(odd), "--target", str(self.project), "--json"]), 0)
        preview = json.loads(out.getvalue())
        self.assertIn(str(odd), preview["apply_argv"])
        if os.name != "nt":
            words = shlex.split(preview["apply_command"])
            self.assertEqual(words, preview["apply_argv"])
            self.assertIn(str(odd), words)
        self.assertEqual(user_install.command_line(["python3", "a b"], platform="posix"), "python3 'a b'")
        self.assertEqual(user_install.command_line(["python3", "a b"], platform="nt"), 'python3 "a b"')
        self.assertIsNone(user_install.command_line(["python3", "$(id)"], platform="nt"))
        self.assertIsNone(user_install.command_line(["python3", "100%"], platform="nt"))

    def test_apply_command_reproduces_target_and_hosts(self):
        preview = self.add("mapper", host="claude")
        argv = preview["apply_argv"]
        self.assertEqual(argv[argv.index("--target") + 1], str(self.project))
        self.assertEqual(argv[argv.index("--host") + 1], "claude")
        self.init()
        self.cli("init", "--host", "both")
        argv = self.add("mapper")["apply_argv"]
        self.assertEqual(argv[argv.index("--host") + 1], "both")

    def test_parts_sharing_one_name_across_kinds_are_all_recorded_and_removed(self):
        same = self.sources / "same"
        self.put(same, "skills/foo/SKILL.md", "---\nname: foo\ndescription: Foo skill.\n---\n\nFoo.\n")
        self.put(same, "agents/foo.md", "---\nname: foo\ndescription: Foo agent.\n---\n\nAgent.\n")
        self.put(same, ".mcp.json", json.dumps({"mcpServers": {"foo": {"command": "python3", "args": ["srv/foo.py"]}}}))
        self.put(same, "srv/foo.py", self.runs("foo-server"))
        self.init()
        before = tree(self.project)
        self.cli("add", str(same), "--choice", "oaw", "--consent", "all", "--apply")
        record = json.loads((self.project / ".oaw/user-skills.json").read_text(encoding="utf-8"))
        parts = record["packages"]["same"]["parts"]
        self.assertEqual(sorted((p["kind"], p["name"]) for p in parts.values()), [("agent", "foo"), ("mcp", "foo"), ("skill", "foo")])
        rows = [row for row in self.cli("list")["receipt"] if row.get("package") == "same"]
        self.assertEqual(len(rows), 3)
        self.cli("remove", "same")
        self.assertEqual(tree(self.project), before)
        self.assert_nothing_ran()

    def test_old_records_keyed_by_name_still_load(self):
        self.add("mapper", choice="oaw", on_conflict=["mapper=keep-both"], apply=True)
        path = self.project / ".oaw/user-skills.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["packages"]["mapper"]["parts"] = {"mapper": next(iter(record["packages"]["mapper"]["parts"].values()))}
        path.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(list(user_install.load_record(self.project)["packages"]["mapper"]["parts"]), ["skill:mapper"])
        self.cli("remove", "mapper")
        self.assertFalse((self.project / ".agents/skills/mapper").exists())

    def test_each_mcp_server_keeps_its_own_scripts(self):
        pair = self.sources / "pair"
        self.put(pair, ".mcp.json", json.dumps({"mcpServers": {"first": {"command": "python3", "args": ["first.py"]},
                                                               "second": {"command": "python3", "args": ["second.py"]}}}))
        self.put(pair, "first.py", self.runs("first"))
        self.put(pair, "second.py", self.runs("second"))
        self.put(pair, "hooks/hooks.json", json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 common.py"}]}]}}))
        self.put(pair, "common.py", self.runs("common"))
        self.put(pair, "third.json", "{}")
        servers_spec = json.loads((pair / ".mcp.json").read_text(encoding="utf-8"))
        servers_spec["mcpServers"]["third"] = {"command": "python3", "args": ["common.py"]}
        (pair / ".mcp.json").write_text(json.dumps(servers_spec), encoding="utf-8")
        self.init()
        self.cli("add", str(pair), "--choice", "oaw", "--consent", "all", "--apply")
        support = self.project / ".claude/oaw-user/pair"
        self.assertTrue(all((support / name).is_file() for name in ("first.py", "second.py", "common.py")))
        result = self.cli("remove", "first")
        self.assertEqual(result["conflicts"], [])
        self.assertFalse((support / "first.py").exists())
        self.assertTrue((support / "second.py").is_file())
        self.assertEqual(sorted(json.loads((self.project / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]), ["second", "third"])
        self.cli("remove", "pair-hooks")
        self.assertTrue((support / "common.py").is_file(), "the third server still runs common.py")
        self.cli("remove", "third")
        self.assertFalse((support / "common.py").exists())
        self.cli("remove", "second")
        self.assertFalse(support.exists())
        self.assert_nothing_ran()

    def test_explicit_oaw_skills_ship_a_codex_policy(self):
        for name in ("oaw-add", "oaw-codemap"):
            policy = ROOT / "templates/.agents/skills" / name / "agents/openai.yaml"
            self.assertRegex(policy.read_text(encoding="utf-8"), r"(?m)^policy:\n  allow_implicit_invocation: false$")
        self.init()
        for name in ("oaw-add", "oaw-codemap"):
            self.assertTrue((self.project / ".agents/skills" / name / "agents/openai.yaml").is_file())

    def test_explicit_only_keeps_a_shipped_openai_yaml_and_forces_the_policy(self):
        self.put(self.sources, "mapper/agents/openai.yaml",
                 'interface:\n  display_name: "Mapper"\npolicy:\n  allow_implicit_invocation: true\n  other: kept\n')
        self.add("mapper", choice="recommended", apply=True)
        text = (self.project / ".agents/skills/mapper/agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Mapper"', text)
        self.assertIn("other: kept", text)
        self.assertIn("allow_implicit_invocation: false", text)
        self.assertNotIn("allow_implicit_invocation: true", text)
        merged = user_install.force_explicit_policy(b'interface:\n  display_name: "X"\n')
        self.assertTrue(merged.decode().endswith("policy:\n  allow_implicit_invocation: false\n"))
        self.assertIn(b"allow_implicit_invocation: false", user_install.force_explicit_policy(b"policy: {allow_implicit_invocation: true}\n"))

    def test_mcp_env_values_point_at_the_installed_copy(self):
        envy = self.sources / "envy"
        self.put(envy, ".mcp.json", json.dumps({"mcpServers": {"envy": {
            "command": "python3", "args": ["${CLAUDE_PLUGIN_ROOT}/srv.py"],
            "env": {"PLUGIN_HOME": "${CLAUDE_PLUGIN_ROOT}", "TOOL": "${CLAUDE_PLUGIN_ROOT}/srv.py", "NESTED": ["${CLAUDE_PLUGIN_ROOT}"]}}}}))
        self.put(envy, "srv.py", self.runs("envy"))
        self.cli("add", str(envy), "--choice", "only", "--consent", "mcp", "--apply")
        spec = json.loads((self.project / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["envy"]
        root = "${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/envy"
        self.assertEqual(spec["env"], {"PLUGIN_HOME": root, "TOOL": root + "/srv.py", "NESTED": [root]})
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", json.dumps(spec))

    def test_hook_paths_stay_one_argument_in_a_project_with_spaces(self):
        self.project = self.base / "my project"
        self.project.mkdir()
        self.add("hooky", choice="only", consent="all", apply=True)
        hooks = json.loads((self.project / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]
        start = hooks["SessionStart"][0]["hooks"][0]["command"]
        guard = hooks["PreToolUse"][0]["hooks"][0]["command"]
        self.assertEqual(start, 'bash "${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/hooky/hooks/start.sh"')
        self.assertEqual(guard, 'python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/hooky/hooks/guard.py"')
        self.assertEqual(user_install.rewrite_command("cd '${CLAUDE_PLUGIN_ROOT}/x.sh'", "${R:-.}/p", ["x.sh"], shell=True),
                         "cd ''\"${R:-.}/p/x.sh\"''")
        shell = shutil.which("sh")
        if shell and os.name != "nt":
            # Only printf runs: the hook's own script is never executed.
            probe = subprocess.run([shell, "-c", "printf '%s\\n' " + start.removeprefix("bash ")], capture_output=True, text=True,
                                   env={**os.environ, "CLAUDE_PROJECT_DIR": str(self.project)}, check=True)
            self.assertEqual(probe.stdout.splitlines(), [str(self.project / ".claude/oaw-user/hooky/hooks/start.sh")])
        self.assert_nothing_ran()

    def test_github_refs_may_contain_slashes(self):
        verdicts = user_install.load_verdicts()
        for text, ref in (("https://github.com/owner/repo@feature/branch", "feature/branch"), ("owner/repo@feature/x", "feature/x"),
                          ("git@github.com:owner/repo@v1", "v1"), ("https://github.com/owner/repo/tree/main", "main"),
                          ("github.com/owner/repo.git@release/2.0", "release/2.0")):
            source = user_install.parse_source(text, verdicts)
            self.assertEqual((source["key"], source["ref"]), ("github.com/owner/repo", ref), text)

    # ------------------------------------------------------------------ review round 13

    def replaced_server(self):
        """hooky's MCP server replaces one of the user's own, and the user then edits the installed setting."""
        self.put(self.project, ".mcp.json", '{"mcpServers": {"hooky-server": {"command": "my-original"}}}\n')
        original = (self.project / ".mcp.json").read_bytes()
        self.add("hooky", choice="only", consent="mcp", on_conflict=["hooky-server=replace"], apply=True)
        servers = json.loads((self.project / ".mcp.json").read_text(encoding="utf-8"))
        servers["mcpServers"]["hooky-server"]["command"] = "my-edit"
        (self.project / ".mcp.json").write_text(json.dumps(servers) + "\n", encoding="utf-8")
        return original

    def record(self):
        return json.loads((self.project / ".oaw/user-skills.json").read_text(encoding="utf-8"))

    def test_a_conflicted_remove_keeps_every_restore_source(self):
        original = self.replaced_server()
        result = self.cli("remove", "hooky-server", code=3)
        self.assertEqual(result["status"], "partial")
        self.assertEqual([c["path"] for c in result["conflicts"]], [".mcp.json mcpServers.hooky-server"])
        self.assertIn("oaw.py remove hooky-server --force", result["finish"])
        part = self.record()["packages"]["hooky"]["parts"]["mcp:hooky-server"]
        self.assertEqual(part["entries"][0]["previous"], {"command": "my-original"})
        self.assertTrue(part["left_in_place"])
        self.assertTrue((self.project / self.record()["shared"][".mcp.json"]["backup"]).is_file())
        self.cli("remove", "hooky-server", code=3)  # still edited: still kept, nothing lost
        self.assertIn("mcp:hooky-server", self.record()["packages"]["hooky"]["parts"])
        self.cli("remove", "hooky-server", "--force")
        self.assertEqual((self.project / ".mcp.json").read_bytes(), original)
        self.assertNotIn("mcp:hooky-server", self.record()["packages"]["hooky"]["parts"])
        self.assertNotIn(".mcp.json", self.record()["shared"])

    def test_a_conflict_resolved_by_hand_finishes_on_the_next_remove(self):
        original = self.replaced_server()
        self.cli("remove", "hooky-server", code=3)
        servers = json.loads((self.project / ".mcp.json").read_text(encoding="utf-8"))
        servers["mcpServers"]["hooky-server"]["command"] = "python3"
        (self.project / ".mcp.json").write_text(json.dumps(servers) + "\n", encoding="utf-8")
        self.assertEqual(self.cli("remove", "hooky-server")["conflicts"], [])
        self.assertEqual((self.project / ".mcp.json").read_bytes(), original)

    def test_keep_accepts_the_edit_and_forgets_the_part(self):
        self.replaced_server()
        self.cli("remove", "hooky-server", code=3)
        self.cli("remove", "hooky-server", "--keep")
        self.assertEqual(json.loads((self.project / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["hooky-server"],
                         {"command": "my-edit", "args": ["${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/hooky/mcp/server.py"]})
        self.assertNotIn("mcp:hooky-server", self.record()["packages"]["hooky"]["parts"])
        self.assertFalse((self.project / ".oaw/user-skills/baselines/.mcp.json").exists())

    def test_force_puts_back_an_overwritten_file(self):
        self.init()
        original = (self.project / ".agents/skills/oaw-review/SKILL.md").read_bytes()
        self.add("twin", choice="oaw", on_conflict=["oaw-review=replace"], apply=True)
        skill = self.project / ".agents/skills/oaw-review/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\nmy note\n", encoding="utf-8")
        self.cli("remove", "twin", code=3)
        backup = self.record()["packages"]["twin"]["parts"]["skill:oaw-review"]["files"][0]["backup"]
        self.assertTrue((self.project / backup).is_file())
        self.cli("remove", "twin", "--force")
        self.assertEqual(skill.read_bytes(), original)
        self.assertFalse((self.project / ".oaw/user-skills.json").exists())

    def test_receipt_remove_commands_are_unambiguous(self):
        alpha, beta = self.sources / "alpha", self.sources / "beta"
        self.put(alpha, "skills/beta/SKILL.md", "---\nname: beta\ndescription: Beta inside alpha.\n---\n\nBeta.\n")
        self.put(alpha, "agents/beta.md", "---\nname: beta\ndescription: Beta agent.\n---\n\nAgent.\n")
        self.put(beta, "SKILL.md", "---\nname: gamma\ndescription: Gamma inside beta.\n---\n\nGamma.\n")
        self.cli("add", str(alpha), str(beta), "--choice", "only", "--apply")
        rows = {(row["package"], row["kind"]): row["remove"] for row in self.cli("list")["receipt"]}
        self.assertEqual(rows[("alpha", "skill")], "oaw.py remove skill:beta")
        self.assertEqual(rows[("alpha", "agent")], "oaw.py remove agent:beta")
        self.assertEqual(rows[("beta", "skill")], "oaw.py remove gamma")
        self.cli("remove", "skill:beta")
        self.assertFalse((self.project / ".agents/skills/beta").exists())
        self.assertTrue((self.project / ".agents/skills/gamma/SKILL.md").is_file())
        self.assertTrue((self.project / ".claude/agents/beta.md").is_file())
        self.cli("remove", "alpha/agent:beta")
        self.assertFalse((self.project / ".claude/agents/beta.md").exists())
        self.assertTrue((self.project / ".agents/skills/gamma/SKILL.md").is_file())
        record = {"schema": "oaw-user-skills/1", "shared": {}, "packages": {
            name: {"parts": {"skill:x": {"name": "x", "kind": "skill", "files": [], "entries": []}}} for name in ("one", "two")}}
        with self.assertRaises(oaw.InstallError):
            user_install._matches(record, "skill:x")
        self.assertEqual(user_install._matches(record, "two/skill:x"), [("two", ["skill:x"])])
        self.assertEqual(user_install.remove_form(record, "two", "skill:x"), "two/skill:x")

    # ------------------------------------------------------------------ review round 14

    def test_a_kept_setting_keeps_the_files_it_runs(self):
        self.add("hooky", choice="only", consent="all", apply=True)
        mcp = json.loads((self.project / ".mcp.json").read_text(encoding="utf-8"))
        mcp["mcpServers"]["hooky-server"]["args"].append("--verbose")
        (self.project / ".mcp.json").write_text(json.dumps(mcp) + "\n", encoding="utf-8")
        settings = json.loads((self.project / ".claude/settings.json").read_text(encoding="utf-8"))
        settings["hooks"]["SessionStart"][0]["hooks"][0]["command"] += " --quiet"
        (self.project / ".claude/settings.json").write_text(json.dumps(settings) + "\n", encoding="utf-8")
        support = self.project / ".claude/oaw-user/hooky"
        self.cli("remove", "hooky-server", code=3)
        self.assertTrue((support / "mcp/server.py").is_file())
        files = [f["path"] for f in self.record()["packages"]["hooky"]["parts"]["mcp:hooky-server"]["files"]]
        self.assertEqual(files, [".claude/oaw-user/hooky/mcp/server.py"])
        self.cli("remove", "hooky-hooks", code=3)
        self.assertTrue((support / "hooks/start.sh").is_file())
        self.cli("remove", "hooky-server", "--keep")
        self.assertTrue((support / "mcp/server.py").is_file(), "--keep leaves the file the kept setting runs")
        self.assert_nothing_ran()

    def test_a_hook_the_project_already_had_is_never_taken_for_ours(self):
        own = {"matcher": "Bash", "hooks": [{"type": "command",
                                            "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/hooky/hooks/guard.py"'}]}
        self.put(self.project, ".claude/settings.json", json.dumps({"hooks": {"PreToolUse": [own]}}, indent=2) + "\n")
        original = (self.project / ".claude/settings.json").read_bytes()
        self.add("hooky", choice="only", consent="hooks", apply=True)
        settings = json.loads((self.project / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["hooks"]["PreToolUse"], [own, own])
        settings["hooks"]["PreToolUse"][1]["hooks"][0]["command"] += " --strict"
        (self.project / ".claude/settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        result = self.cli("remove", "hooky-hooks", code=3)
        self.assertIn(".claude/settings.json hooks.PreToolUse", [c["path"] for c in result["conflicts"]])
        settings = json.loads((self.project / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["hooks"]["PreToolUse"][0], own, "the project's own hook stays")
        self.assertEqual(len(settings["hooks"]["PreToolUse"]), 2)
        # Unedited, the added copy goes and the project's own file comes back byte for byte.
        settings["hooks"]["PreToolUse"][1] = own
        (self.project / ".claude/settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        self.cli("remove", "hooky-hooks")
        self.assertEqual((self.project / ".claude/settings.json").read_bytes(), original)

    def test_the_tasted_commit_comes_from_the_tasting_not_the_current_pin(self):
        first, second = "a" * 40, "b" * 40
        catalog = self.project / ".oaw" / "catalog"
        write_ledger(catalog, "graphify", current=second, snapshots=[(first, "2026-11-05T00:00:00Z"), (second, "2026-11-07T00:00:00Z")],
                     tasted_at="2026-11-06T00:00:00Z")
        verdicts = user_install.load_verdicts()
        key = "github.com/graphify-labs/graphify"
        status = user_install.tasting_status(self.project, {"key": key, "commit": second}, verdicts)
        self.assertEqual((status["tasted_commit"], status["same_version"]), (first, False))
        self.assertIn("不是你裝的版本", user_install.tasting_text(status, "graphify"))
        self.assertTrue(user_install.tasting_status(self.project, {"key": key, "commit": first}, verdicts)["same_version"])
        document = build_verdicts.build(self.project)
        food = document["foods"][0]
        self.assertEqual((food["commit"], food["tasting"]["commit"]), (first, first))
        write_ledger(catalog, "graphify", current=second, snapshots=[(first, "2026-11-05T00:00:00Z"), (second, "2026-11-05T12:00:00Z")],
                     tasted_at="2026-11-06T00:00:00Z")
        status = user_install.tasting_status(self.project, {"key": key, "commit": second}, verdicts)
        self.assertEqual((status["tasted_commit"], status["same_version"]), (None, False))
        self.assertIn("不確定試吃的是哪個版本", user_install.tasting_text(status, "graphify"))
        self.assertIsNone(build_verdicts.build(self.project)["foods"][0]["tasting"]["commit"])

    def test_a_chosen_new_name_survives_into_the_apply_command(self):
        self.init()
        preview = self.add("twin", on_conflict=["oaw-review=rename:custom-review"])
        self.assertEqual(preview["conflicts"][0]["new_name"], "custom-review")
        self.assertIn("oaw-review=rename:custom-review", preview["apply_argv"])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(oaw.main(preview["apply_argv"][2:] + ["--json"]), 0)
        self.assertTrue((self.project / ".agents/skills/custom-review/SKILL.md").is_file())

    # ------------------------------------------------------------------ review round 15

    def test_two_sources_adding_the_same_hook_both_remove_cleanly(self):
        for name in ("echo-one", "echo-two"):
            self.put(self.sources / name, "hooks/hooks.json",
                     json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo same"}]}]}}))
            self.put(self.sources / name, "skills/" + name + "/SKILL.md", f"---\nname: {name}\ndescription: Echo.\n---\n\nEcho.\n")
        self.cli("add", str(self.sources / "echo-one"), str(self.sources / "echo-two"), "--choice", "only", "--consent", "hooks", "--apply")
        self.assertEqual(self.cli("remove", "echo-one")["conflicts"], [])
        self.assertEqual(self.cli("remove", "echo-two")["conflicts"], [])
        self.assertFalse((self.project / ".claude/settings.json").exists())

    def test_support_files_keep_what_the_entry_script_needs(self):
        need = self.sources / "need"
        self.put(need, ".mcp.json", json.dumps({"mcpServers": {"deep": {"command": "python3", "args": ["srv/main.py"]},
                                                               "flat": {"command": "python3", "args": ["tool.py"]}}}))
        self.put(need, "srv/main.py", "import helper\n" + self.runs("deep"))
        self.put(need, "srv/helper.py", "VALUE = 1\n")
        self.put(need, "srv/data/table.json", "{}\n")
        self.put(need, "tool.py", "from lib import util\n" + self.runs("flat"))
        self.put(need, "lib/__init__.py", "")
        self.put(need, "lib/util.py", "from . import more\n")
        self.put(need, "lib/more.py", "X = 2\n")
        self.put(need, "unrelated.py", "Y = 3\n")
        self.put(need, "hooks/hooks.json", json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "node hooks/run.js"}]}]}}))
        self.put(need, "hooks/run.js", "const u = require('../shared/util.js');\n")
        self.put(need, "shared/util.js", "module.exports = {};\n")
        self.cli("add", str(need), "--choice", "only", "--consent", "all", "--apply")
        root = self.project / ".claude/oaw-user/need"
        for relative in ("srv/main.py", "srv/helper.py", "srv/data/table.json", "tool.py", "lib/__init__.py", "lib/util.py",
                         "lib/more.py", "hooks/run.js", "shared/util.js"):
            self.assertTrue((root / relative).is_file(), relative)
        self.assertFalse((root / "unrelated.py").exists())
        self.cli("remove", "need")
        self.assertFalse(root.exists())
        with patch.object(user_install, "SUPPORT_LIMITS", {"files": 1, "bytes": 10 ** 6}):
            result = self.cli("add", str(need), "--choice", "only", "--consent", "all", "--apply")
        parts = {p["name"]: p for p in result["packages"][0]["parts"]}
        self.assertEqual(parts["deep"]["status"], "blocked")
        self.assertIn("support", parts["deep"]["reason"])
        self.assert_nothing_ran()

    def test_local_sources_skip_junctions_and_vcs_metadata(self):
        source = self.sources / "linked"
        self.put(source, "SKILL.md", "---\nname: linked\ndescription: Linked.\n---\n\nLinked.\n")
        self.put(source, ".git", "gitdir: /home/someone/private/repo/.git/worktrees/linked\n")
        self.put(source, "sub/.hg/store", "x\n")
        self.put(source, "junction/secret.txt", "from elsewhere\n")
        real_alias = oaw.is_path_alias
        with patch.object(user_install.oaw, "is_path_alias", lambda path: Path(path).name == "junction" or real_alias(path)):
            snapshot = user_install.read_local(source)
        self.assertNotIn("junction/secret.txt", snapshot["files"])
        self.assertIn("junction", snapshot["symlinks"])
        self.assertFalse(any(p == ".git" or "/.hg/" in "/" + p for p in snapshot["files"]))
        self.cli("add", str(source), "--choice", "only", "--apply")
        self.assertFalse((self.project / ".agents/skills/linked/.git").exists())
        self.assertNotIn("/home/someone", json.dumps(tree(self.project).__repr__()))

    def test_manager_only_keeps_new_hosts(self):
        self.add("mapper", choice="only", apply=True)
        self.add("scripty", choice="only", host="both", consent="scripts", apply=True)
        self.assertEqual(json.loads((self.project / ".oaw/install.json").read_text(encoding="utf-8"))["hosts"], ["codex", "claude"])
        self.cli("add", str(self.sources / "twin"), "--apply")
        for root in (".agents/skills", ".claude/skills"):
            self.assertTrue((self.project / root / "oaw-review/SKILL.md").is_file(), root)

    def test_an_invalid_skill_name_is_rewritten_to_the_installed_folder(self):
        self.put(self.sources, "badname/tool/SKILL.md", "---\nname: Bad_Name\ndescription: Bad name.\n---\n\nBody.\n")
        self.cli("add", str(self.sources / "badname"), "--choice", "only", "--apply")
        installed = self.project / ".agents/skills/tool/SKILL.md"
        fields, _body = core.parse_frontmatter(installed.read_text(encoding="utf-8"))
        self.assertEqual(fields["name"], "tool")
        self.assertEqual(oaw.skill_issues(installed), [])
        self.put(self.sources, "nodesc/x/SKILL.md", "---\nname: x\n---\n\nBody.\n")
        result = self.cli("add", str(self.sources / "nodesc"), "--choice", "only", "--apply")
        self.assertEqual(result["packages"][0]["parts"][0]["status"], "blocked")
        self.assertFalse((self.project / ".agents/skills/x").exists())


def write_ledger(catalog: Path, food: str, *, current: str, snapshots: list, tasted_at: str) -> None:
    """A minimal catalog ledger: one GitHub food pinned at `current`, its sealed snapshots, and one tasting."""
    (catalog / "evidence" / food).mkdir(parents=True, exist_ok=True)
    for old in (catalog / "evidence" / food).glob("*.json"):
        old.unlink()
    (catalog / "registry.json").write_text(json.dumps({"schema_version": 1, "foods": {food: {"id": food, "source": {
        "kind": "github", "key": "github.com/graphify-labs/graphify", "owner": "Graphify-Labs", "repo": "graphify",
        "commit": current}}}}), encoding="utf-8")
    for commit, when in snapshots:
        (catalog / "evidence" / food / f"I0-{commit[:12]}.json").write_text(json.dumps(
            {"schema_version": 1, "tier": "I0", "food": food, "commit": commit, "recorded_at": when}), encoding="utf-8")
    raw = {"schema": "oaw-tasting/1", "food": food, "date": tasted_at[:10],
           "records": {"branch": "records", "commit": "9c5886a", "path": "records/digestion/x"},
           "protocol": {"models": ["claude-haiku-5-5"], "corpus": "ERPNext at d9cb916 (frozen)",
                        "questions": {"count": 4, "sha256": "c" * 64, "file": None}, "repeats": 3, "grading": "two gradings"},
           "arms": [{"id": "N", "label": "native", "food_arm": False, "runs": 12, "graded_runs": 12},
                    {"id": "G", "label": "graphify 0.9", "food_arm": True, "runs": 12, "graded_runs": 12}],
           "food_arm_ran": {"graded_runs": 12, "evidence": "rows.jsonl"},
           "verdict": "decline", "verdict_zh": "排掉。", "blocked_on_owner": None, "notes": None,
           "judgment": {"quality": "worse", "cost_ratio": 1.4, "cheaper": False, "grading": "double-graded", "conditions": 4}}
    stored = {**raw, "tasting_id": core.tasting_id(core.validate_tasting(raw, food)), "recorded_at": tasted_at,
              "provenance": "agent-tasting"}
    (catalog / "evidence" / food / "tasting-1.json").write_text(json.dumps(stored), encoding="utf-8")


class VerdictsTests(unittest.TestCase):
    def test_shipped_file_is_valid_public_and_in_generator_form(self):
        path = ROOT / "catalog" / "verdicts.json"
        data = user_install.load_verdicts(path)
        self.assertEqual(path.read_bytes(), build_verdicts.render(data))
        build_verdicts._public(data, "verdicts")
        self.assertTrue(data["foods"])
        for food in data["foods"]:
            self.assertTrue(food["key"].startswith("github.com/"))
            self.assertEqual(food["url"], "https://github.com/" + food["repo"])
            self.assertEqual(food["key"], "github.com/" + food["repo"].casefold())
            if food["tasting"]:
                self.assertIn(food["tasting"]["outcome"], ("default", "optional", "excrete", None))
                self.assertTrue(food["tasting"]["evidence"]["commit"])
        self.assertEqual(data["builtin"]["oaw-codemap"]["category"], "code-map")

    def test_generator_builds_from_a_ledger(self):
        with tempfile.TemporaryDirectory(prefix="oaw-ledger-") as temporary:
            ledger = Path(temporary)
            catalog = ledger / ".oaw" / "catalog"
            (catalog / "evidence" / "graphify").mkdir(parents=True)
            registry = {"schema_version": 1, "foods": {
                "graphify": {"id": "graphify", "source": {"kind": "github", "key": "github.com/graphify-labs/graphify",
                                                          "owner": "Graphify-Labs", "repo": "graphify", "commit": "a" * 40}},
                "untasted": {"id": "untasted", "source": {"kind": "github", "key": "github.com/someone/untasted",
                                                          "owner": "someone", "repo": "untasted", "commit": None}},
                "mine": {"id": "mine", "source": {"kind": "file", "key": "file:///home/me/mine", "owner": None, "repo": "mine"}}}}
            (catalog / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
            tasting = {
                "schema": "oaw-tasting/1", "food": "graphify", "date": "2026-11-06",
                "records": {"branch": "records", "commit": "9c5886a", "path": "records/digestion/x"},
                "protocol": {"models": ["claude-haiku-5-5"], "corpus": "ERPNext at d9cb916 (frozen)",
                             "questions": {"count": 4, "sha256": "c" * 64, "file": None}, "repeats": 3, "grading": "two gradings"},
                "arms": [{"id": "N", "label": "native", "food_arm": False, "runs": 12, "graded_runs": 12},
                         {"id": "G", "label": "graphify 0.9", "food_arm": True, "runs": 12, "graded_runs": 12}],
                "food_arm_ran": {"graded_runs": 12, "evidence": "rows.jsonl"},
                "verdict": "decline", "verdict_zh": "排掉。", "blocked_on_owner": None, "notes": None,
                "judgment": {"quality": "worse", "cost_ratio": 1.4, "cheaper": False, "grading": "double-graded", "conditions": 4,
                             "basis": "more wrong claims"}}

            def store(raw):
                stored = {**raw, "tasting_id": core.tasting_id(core.validate_tasting(raw, "graphify")),
                          "recorded_at": "2026-11-06T00:00:00Z", "provenance": "agent-tasting"}
                (catalog / "evidence" / "graphify" / "tasting-0123456789ab.json").write_text(json.dumps(stored), encoding="utf-8")
            store(tasting)
            document = build_verdicts.build(ledger)
            self.assertEqual(build_verdicts.render(document), build_verdicts.render(build_verdicts.build(ledger)))
            foods = {food["id"]: food for food in document["foods"]}
            self.assertEqual(sorted(foods), ["graphify", "untasted"])
            self.assertEqual(foods["graphify"]["category"], "code-map")
            self.assertEqual((foods["graphify"]["tasting"]["outcome"], foods["graphify"]["tasting"]["label_zh"]), ("excrete", "排掉（比原生差）"))
            self.assertEqual(foods["graphify"]["tasting"]["conditions"]["food_arm"], "graphify 0.9")
            self.assertIsNone(foods["untasted"]["tasting"])
            tasting["protocol"]["corpus"] = "/home/me/private/repo"
            store(tasting)
            with self.assertRaises(build_verdicts.BuildError):
                build_verdicts.build(ledger)


if __name__ == "__main__":
    unittest.main()
