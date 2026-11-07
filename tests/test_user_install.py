"""User skill installs (plan 2.0.1 W3, D34): oaw.py add / list / remove on local fixtures, no network."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import stat
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
        self.assertIn("bash ${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/pinger/hooks/ping.sh", commands)
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
        self.assertEqual(record["packages"]["twin"]["source"]["path"], self.fixtures["twin"])
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
                         ["echo mine", "bash ${CLAUDE_PROJECT_DIR:-.}/.claude/oaw-user/pinger/hooks/ping.sh"])
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
        result = self.cli("remove", "mapper")
        self.assertEqual([c["path"] for c in result["conflicts"]], [".agents/skills/mapper/SKILL.md"])
        self.assertIn("my note", skill.read_text(encoding="utf-8"))
        result = self.cli("remove", "hooky")
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
            tampered["packages"]["mapper"]["parts"]["mapper"]["files"][0]["path"] = bad
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
