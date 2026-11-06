"""Working-mode helper: fixed triggers, host instructions and the installed policy (stdlib only)."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mode = load("oaw_mode_test", "scripts/oaw_mode.py")
oaw = load("oaw_mode_installer_test", "scripts/oaw.py")


def entry(path, status="M", lines=0, old_path=None, known=True):
    return {"path": path, "status": status, "old_path": old_path, "lines": lines, "lines_known": known}


def run(*args):
    output, errors = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        code = mode.main(list(args))
    return code, output.getvalue(), errors.getvalue()


class TriggerTests(unittest.TestCase):
    def assertMode(self, expected, entries, commands=None, rule=None):
        result = mode.classify(entries, commands)
        self.assertEqual(result["mode"], expected, result)
        if rule:
            self.assertIn(rule, [trigger["rule"] for trigger in result["triggers"]])
        return result

    def test_harness_and_infrastructure_paths_are_deep(self):
        for path in ("AGENTS.md", "CLAUDE.md", "sub/AGENTS.md", "templates/AGENTS.md", "templates/.agents/skills/x/SKILL.md",
                     ".github/workflows/ci.yml", ".claude/settings.json", ".claude/settings.local.json",
                     ".claude/hooks/guard.sh", ".codex/config.toml", ".githooks/pre-commit", ".husky/pre-push",
                     ".pre-commit-config.yaml", "install.sh", "install.ps1", "tools/setup_env.sh", "bootstrap.py",
                     "scripts/oaw.py", "scripts/harness_check.py", "scripts/context_hub.py", "scripts/oaw_mode.py"):
            with self.subTest(path=path):
                result = self.assertMode("deep", [entry(path, lines=1)], rule="harness")
                self.assertIn(path, result["triggers"][0]["paths"])

    def test_ordinary_paths_are_not_harness(self):
        for path in ("src/app.py", "scripts/train.py", "tools/scripts/oaw.py", "docs/AGENTS_notes.md", "README.md",
                     ".github/ISSUE_TEMPLATE/bug.md", ".claude/agents/reviewer.md", "tests/test_setup.py"):
            with self.subTest(path=path):
                self.assertMode("light", [entry(path, lines=10)])

    def test_scripts_named_in_claude_hook_commands_are_harness(self):
        commands = ['python3 "$CLAUDE_PROJECT_DIR"/tools/guard.py --strict']
        self.assertMode("deep", [entry("tools/guard.py", lines=2)], commands, rule="harness")
        self.assertMode("light", [entry("tools/guard.pyc", lines=2), entry("other/tools/guard.py.bak", lines=2)], commands)

    def test_hook_commands_are_read_from_project_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".claude").mkdir()
            settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "bash tools/check.sh"}]}]}}
            (root / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
            (root / ".claude/settings.local.json").write_text("not json", encoding="utf-8")
            self.assertEqual(mode.hook_commands(root), ["bash tools/check.sh"])

    def test_renamed_harness_file_counts_by_its_old_path(self):
        self.assertMode("deep", [entry("archive/AGENTS.old", status="R", old_path="templates/AGENTS.md")], rule="harness")

    def test_deleting_more_than_five_files_is_deep(self):
        five = [entry(f"src/m{i}.py", status="D", lines=3) for i in range(5)]
        self.assertMode("light", five)
        self.assertMode("deep", [*five, entry("src/m5.py", status="D", lines=3)], rule="deletions")

    def test_migrations_and_schema_files_are_deep(self):
        for path in ("db/migrations/0002_add.sql", "app/migration/001.py", "alembic/versions/abc.py", "schema.sql",
                     "db/schema.prisma", "api/Schema.graphql", "config/user.schema.json", "prisma/models.prisma"):
            with self.subTest(path=path):
                self.assertMode("deep", [entry(path, lines=1)], rule="migration-or-schema")
        self.assertMode("light", [entry("src/schema_utils.py", lines=5), entry("tests/test_schema.py", lines=5)])

    def test_only_a_new_design_document_is_deep(self):
        for path in ("docs/designs/cache.md", "design.md", "docs/Design-v2.md", "notes/design_review.md"):
            with self.subTest(path=path):
                self.assertMode("deep", [entry(path, status="A", lines=40)], rule="new-design-doc")
                self.assertMode("light", [entry(path, status="M", lines=40)])
        self.assertMode("light", [entry("docs/designs/diagram.png", status="A"), entry("docs/redesign.md", status="A")])

    def test_size_threshold_counts_code_only(self):
        self.assertMode("light", [entry("src/a.py", lines=299)])
        self.assertMode("standard", [entry("src/a.py", lines=300)], rule="size")
        self.assertMode("light", [entry(f"src/f{i}.py", lines=1) for i in range(9)])
        self.assertMode("standard", [entry(f"src/f{i}.py", lines=1) for i in range(10)], rule="size")
        result = self.assertMode("light", [entry("docs/guide.md", lines=5000), entry("README.md", lines=900)])
        self.assertEqual(result["reasons"], ["documentation only (2 files)"])
        self.assertEqual(mode.classify([])["reasons"], ["no changes found"])

    def test_deep_wins_and_keeps_every_reason(self):
        result = self.assertMode("deep", [entry("src/a.py", lines=500), entry(".github/workflows/ci.yml", lines=3)])
        self.assertEqual([t["rule"] for t in result["triggers"]], ["harness", "size"])
        self.assertEqual(len(result["reasons"]), 2)


@unittest.skipUnless(GIT, "git is required for local fixture repositories")
class GitDiffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-mode-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve() / "repo"
        self.repo.mkdir()
        self.git("init", "-q")

    def git(self, *args):
        subprocess.run([GIT, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "core.autocrlf=false",
                        "-c", "commit.gpgsign=false", *args], cwd=self.repo, check=True, capture_output=True)

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self, message="change"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def suggest(self, *args):
        code, output, errors = run("suggest", "--root", str(self.repo), "--json", *args)
        self.assertEqual(code, 0, errors)
        return json.loads(output)

    def test_working_tree_against_head_covers_staged_unstaged_and_untracked(self):
        self.write("README.md", "# Demo\n")
        self.write("src/app.py", "VALUE = 1\n")
        self.commit("base")
        self.assertEqual(self.suggest()["reasons"], ["no changes found"])
        self.write("README.md", "# Demo\n\nMore words.\n")
        self.assertEqual(self.suggest()["mode"], "light")
        self.write("src/big.py", "".join(f"X{i} = {i}\n" for i in range(400)))  # untracked
        result = self.suggest()
        self.assertEqual((result["mode"], result["code_lines"], result["code_files"]), ("standard", 400, 1))
        self.git("add", "src/big.py")  # staged
        self.assertEqual(self.suggest()["code_lines"], 400)
        self.write(".github/workflows/ci.yml", "on: push\n")
        result = self.suggest()
        self.assertEqual(result["mode"], "deep")
        self.assertEqual(result["triggers"][0]["paths"], [".github/workflows/ci.yml"])

    def test_range_deletions_renames_and_binary_files(self):
        for index in range(6):
            self.write(f"old/m{index}.py", f"M = {index}\n")
        self.write("src/keep.py", "".join(f"K{i} = {i}\n" for i in range(50)))
        self.commit("base")
        self.git("mv", "src/keep.py", "src/kept.py")
        (self.repo / "logo.bin").write_bytes(b"\0\1\2" * 100)
        self.commit("rename")
        result = self.suggest("--range", "HEAD~1..HEAD")
        self.assertEqual(result["mode"], "light", result)
        self.assertEqual(result["deleted_files"], 0, "a rename is not a deletion")
        self.assertIn("binary", " ".join(result["reasons"]))
        self.git("rm", "-q", "-r", "old")
        self.commit("delete")
        result = self.suggest("--range", "HEAD~1..HEAD")
        self.assertEqual((result["mode"], result["deleted_files"]), ("deep", 6))

    def test_repository_without_commits_and_errors(self):
        self.write("design.md", "# Design\n")
        self.assertEqual(self.suggest()["mode"], "deep")
        code, _, errors = run("suggest", "--root", str(self.repo), "--range=--all..x")
        self.assertEqual(code, 2)
        self.assertIn("--range must look like", errors)
        code, _, errors = run("suggest", "--root", str(self.repo), "--range", "nope..HEAD")
        self.assertEqual(code, 2)
        self.assertTrue(errors.startswith("oaw_mode: git diff"), errors)
        outside = Path(self.temporary.name).resolve() / "plain"
        outside.mkdir()
        code, _, errors = run("suggest", "--root", str(outside))
        self.assertEqual(code, 2)

    def test_path_list_counts_missing_paths_as_new(self):
        self.write("docs/designs/old.md", "# Old\n")
        result = self.suggest("--paths", "docs/designs/old.md", "./docs/designs/new.md", str(self.repo / "src/a.py"))
        self.assertEqual(result["mode"], "deep")
        self.assertEqual(result["triggers"][0]["paths"], ["docs/designs/new.md"])
        self.assertEqual(result["source"], "path list")
        code, _, errors = run("suggest", "--root", str(self.repo), "--paths", "../elsewhere.py")
        self.assertEqual(code, 2)
        self.assertIn("not a project path", errors)

    def test_text_output_names_the_mode_reasons_and_next_command(self):
        self.write("a.py", "A = 1\n")
        code, output, _ = run("suggest", "--root", str(self.repo))
        self.assertEqual(code, 0)
        lines = output.splitlines()
        self.assertEqual(lines[0], "mode: light  (working tree against HEAD: 1 file, 1 code line)")
        self.assertEqual(lines[-1], "how to run it: python3 scripts/oaw_mode.py show light")


class ShowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-mode-show-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def show(self, name):
        code, output, errors = run("show", name, "--root", str(self.root))
        self.assertEqual(code, 0, errors)
        return output

    def entry(self, host_dir):
        path = self.root / host_dir / "skills/egm-review/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: egm-review\n---\n", encoding="utf-8")

    def test_light_and_standard_are_fixed(self):
        self.assertEqual(self.show("light"), "light: plain session, no extra review (the default)\n"
                                             "Claude Code:\n  claude\nCodex:\n  codex\n")
        standard = self.show("standard").splitlines()
        self.assertEqual(standard[:3], ["standard: higher effort and one fresh-context review", "Claude Code:",
                                        "  claude --effort high"])
        self.assertIn("  review: codex review --uncommitted  (a fresh-context review; --base BRANCH or --commit SHA for committed work)",
                      standard)
        self.entry(".claude")
        self.assertEqual(self.show("standard").splitlines(), standard, "EGM never changes standard")

    def test_deep_without_egm_is_standard_plus_plan_mode(self):
        output = self.show("deep")
        self.assertIn("EGM is not installed: standard plus plan mode", output)
        self.assertIn("  claude --permission-mode plan --effort high\n", output)
        self.assertIn("  codex --sandbox read-only", output)
        self.assertIn("  review: codex review --uncommitted", output)
        self.assertNotIn("egm-review", output)
        self.assertNotIn("--effort max", output)

    def test_deep_with_egm_for_both_hosts(self):
        self.entry(".claude")
        self.entry(".agents")
        lines = self.show("deep").splitlines()
        self.assertEqual(lines, [
            "deep: plan first at the highest effort, then the EGM review",
            "Claude Code:",
            "  claude --permission-mode plan --effort max",
            "  review: type /egm-review  (explicit invocation only; the agent cannot start it)",
            "Codex:",
            "  " + mode.CODEX_PLAN,
            "  review: select the egm-review skill in the skill picker",
        ])

    def test_deep_with_egm_for_one_host_names_the_missing_entrypoint(self):
        self.entry(".agents")
        code, output, _ = run("show", "deep", "--root", str(self.root), "--json")
        result = json.loads(output)
        self.assertEqual(result["egm"], {"claude": False, "codex": True})
        self.assertTrue(result["summary"].endswith("(Claude Code has no EGM entrypoint here: standard plus plan mode)"))
        self.assertEqual(result["hosts"]["claude"][0], "claude --permission-mode plan --effort high")
        self.assertIn("oaw.py init --host claude", result["hosts"]["claude"][-1])
        self.assertEqual(result["hosts"]["codex"][-1], "review: select the egm-review skill in the skill picker")

    def test_effort_levels_match_the_checked_claude_cli(self):
        # Claude Code 2.1.287 --help: --effort <level> (low, medium, high, xhigh, max); max is the highest.
        text = Path(mode.__file__).read_text(encoding="utf-8")
        self.assertEqual(sorted(set(re.findall(r"--effort (\w+)", text))), ["high", "max"])


class InstalledPolicyTests(unittest.TestCase):
    def test_both_recipes_install_the_helper_and_the_light_default(self):
        template = (ROOT / "templates/AGENTS.md").read_bytes()
        for skills, egm in ((None, True), (["oaw-evidence"], False)):
            with self.subTest(egm=egm):
                package = oaw.source_files("minimal", False, skills=skills)
                self.assertEqual(package["scripts/oaw_mode.py"], (ROOT / "scripts/oaw_mode.py").read_bytes())
                policy = package["AGENTS.md"].decode("utf-8")
                self.assertEqual(package["AGENTS.md"], oaw.render_policy(template, egm))
                self.assertIn("Work light by default: a plain session with no extra review.", policy)
                self.assertIn("`python3 scripts/oaw_mode.py suggest`", policy)
                self.assertEqual("EGM" in policy, egm)
                self.assertEqual("Run the full EGM review only when `suggest` says deep" in policy, egm)
                self.assertLessEqual(len(policy.splitlines()), 25)

    def test_installed_helper_reads_the_recipe(self):
        with tempfile.TemporaryDirectory(prefix="oaw-mode-install-") as temporary:
            for skills, expected in (("default", "select the egm-review skill"), ("oaw-evidence", "EGM is not installed")):
                target = Path(temporary) / skills
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(oaw.main(["init", "--target", str(target), "--skills", skills]), 0)
                    self.assertEqual(oaw.doctor(target)["status"], "healthy")
                process = subprocess.run([sys.executable, str(target / "scripts/oaw_mode.py"), "show", "deep",
                                          "--root", str(target)],
                                         capture_output=True, text=True, check=False)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertIn(expected, process.stdout)

    def test_install_from_before_working_modes_is_warned_then_migrated(self):
        with tempfile.TemporaryDirectory(prefix="oaw-mode-upgrade-") as temporary:
            target = Path(temporary) / "project"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(oaw.main(["init", "--target", str(target), "--skills", "oaw-evidence"]), 0)
            # Recreate an older install: no helper, and the policy without the working-mode lines.
            manifest_path = target / ".oaw/install.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            (target / "scripts/oaw_mode.py").unlink()
            del manifest["managed_files"]["scripts/oaw_mode.py"]
            policy = target / "AGENTS.md"
            old = "".join(line for line in policy.read_text(encoding="utf-8").splitlines(keepends=True)
                          if "oaw_mode.py" not in line and not line.startswith("Work light")).encode("utf-8")
            policy.write_bytes(old)
            manifest["managed_files"]["AGENTS.md"] = oaw.digest(old)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            health = oaw.doctor(target)
            self.assertEqual(health["status"], "healthy", health)
            self.assertIn(("WARN", "scripts/oaw_mode.py"), [(c["status"], c["path"]) for c in health["checks"]])
            plan = oaw.plan_install(target, "minimal", False, migrate=True)
            actions = {a["path"]: a["action"] for a in plan["actions"]}
            self.assertEqual((actions["AGENTS.md"], actions["scripts/oaw_mode.py"]), ("replace", "add"))
            oaw.apply_plan(plan, migrate=True)
            health = oaw.doctor(target)
            self.assertEqual(health["status"], "healthy", health)
            self.assertFalse([c for c in health["checks"] if c["status"] != "PASS"], health)
            # Once the policy names the helper, losing it fails doctor.
            (target / "scripts/oaw_mode.py").unlink()
            self.assertEqual(oaw.doctor(target)["status"], "unhealthy")


if __name__ == "__main__":
    unittest.main()
