"""Working-mode helper: fixed triggers, host instructions and the installed policy (stdlib only)."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shlex
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
    def assertMode(self, expected, entries, hooked=None, rule=None):
        result = mode.classify(entries, hooked)
        self.assertEqual(result["mode"], expected, result)
        if rule:
            self.assertIn(rule, [trigger["rule"] for trigger in result["triggers"]])
        return result

    def test_harness_and_infrastructure_paths_are_deep(self):
        for path in ("AGENTS.md", "CLAUDE.md", "sub/AGENTS.md", "templates/AGENTS.md", "templates/.agents/skills/x/SKILL.md",
                     ".github/workflows/ci.yml", ".claude/settings.json", ".claude/settings.local.json",
                     ".claude/hooks/guard.sh", ".codex/config.toml", ".githooks/pre-commit", ".husky/pre-push",
                     ".pre-commit-config.yaml", "install.sh", "install.ps1", "tools/setup_env.sh", "bootstrap.py",
                     "tools/setupEnv.sh", "installDeps.py", "Bootstrap-Dev.ps1", "installer.cmd",
                     "scripts/oaw.py", "scripts/harness_check.py", "scripts/context_hub.py", "scripts/oaw_mode.py"):
            with self.subTest(path=path):
                result = self.assertMode("deep", [entry(path, lines=1)], rule="harness")
                self.assertIn(path, result["triggers"][0]["paths"])

    def test_ordinary_paths_are_not_harness(self):
        for path in ("src/app.py", "scripts/train.py", "tools/scripts/oaw.py", "docs/AGENTS_notes.md", "README.md",
                     ".github/ISSUE_TEMPLATE/bug.md", ".claude/agents/reviewer.md", "tests/test_setup.py",
                     "tools/setupEnv.txt", "reinstall.sh", "src/my_setup.py"):
            with self.subTest(path=path):
                self.assertMode("light", [entry(path, lines=10)])

    def test_scripts_named_in_claude_hook_commands_are_harness(self):
        hooked = {"tools/guard.py"}
        self.assertMode("deep", [entry("tools/guard.py", lines=2)], hooked, rule="harness")
        self.assertMode("light", [entry("tools/guard.pyc", lines=2), entry("other/tools/guard.py", lines=2),
                                  entry("guard.py", lines=2)], hooked)

    def hook_files(self, *commands):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / ".claude").mkdir()
            hooks = [{"type": "command", "command": command.replace("ROOT", root.as_posix())} for command in commands]
            settings = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": hooks}]}}
            (root / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
            (root / ".claude/settings.local.json").write_text("not json", encoding="utf-8")
            return mode.hook_commands(root), mode.hook_files(root)

    def test_hook_commands_name_whole_project_relative_paths(self):
        commands, files = self.hook_files("bash tools/check.sh")
        self.assertEqual(commands, ["bash tools/check.sh"])
        self.assertIn("tools/check.sh", files)
        # Same file name in another directory is not the hooked file (codex review of 08dbe3c, item 4).
        self.assertMode("light", [entry("check.sh", lines=1), entry("other/tools/check.sh", lines=1)], files)
        self.assertMode("deep", [entry("tools/check.sh", lines=1)], files, rule="harness")
        _, files = self.hook_files('python3 "$CLAUDE_PROJECT_DIR"/hooks/a.py --x=./cfg/b.json && ${CLAUDE_PROJECT_DIR}/c.sh',
                                   "ROOT/scripts/d.py; node ./e.js|tee /tmp/log ../outside.sh")
        self.assertTrue({"hooks/a.py", "cfg/b.json", "c.sh", "scripts/d.py", "e.js"} <= files, files)
        self.assertFalse({"/tmp/log", "../outside.sh", "tmp/log", "outside.sh"} & files, files)

    def test_shell_wrapped_hook_commands_are_parsed_one_level(self):
        # codex review of 4225749, item 2: `bash -c '...'` and `sh -lc "..."` hide the script in one word.
        _, files = self.hook_files("bash -c 'bash tools/check.sh'",
                                   'sh -lc "cd . && ./tools/lint.sh --fix"',
                                   "/usr/bin/env zsh -e -c '$CLAUDE_PROJECT_DIR/hooks/z.py'")
        self.assertTrue({"tools/check.sh", "tools/lint.sh", "hooks/z.py"} <= files, files)
        self.assertMode("deep", [entry("tools/check.sh", lines=1)], files, rule="harness")
        self.assertMode("light", [entry("check.sh", lines=1)], files)
        self.assertEqual(mode.command_tokens("python3 -c 'print(1)' x.py"), ["python3", "-c", "print(1)", "x.py"])

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

    def test_a_new_plan_or_decision_document_is_deep_and_marked_as_added_in_2_0_1(self):
        for path in ("docs/plans/v2.0.1-execution.md", "docs/adr/0001-cache.md", "docs/rfcs/x.md", "plan.md",
                     "notes/migration-plan.md", "notes/rollout_plan.md", "Docs/Plans/X.md"):
            with self.subTest(path=path):
                result = self.assertMode("deep", [entry(path, status="A", lines=40)], rule="new-plan-doc")
                self.assertEqual(result["triggers"][0]["since"], "2.0.1")
                self.assertEqual(result["design_docs"], [path])
                self.assertMode("light", [entry(path, status="M", lines=40)])
        # The V7-checked design rule keeps its own name; a path both rules match counts once, as a design doc.
        result = self.assertMode("deep", [entry("docs/designs/x-plan.md", status="A")], rule="new-design-doc")
        self.assertEqual([t["rule"] for t in result["triggers"]], ["new-design-doc"])
        for path in ("explan.md", "docs/planning.md", "docs/plans/diagram.png", "src/plan.py",
                     ".oaw/integrations/egm/agents/design_critic.md", ".oaw/integrations/egm/skills/x/design_doc.md",
                     ".claude/skills/x/plan.md", ".agents/skills/x/design.md", "vendor/lib/docs/plans/a.md",
                     "node_modules/p/design.md"):
            with self.subTest(path=path):
                self.assertMode("light", [entry(path, status="A", lines=4)])

    def test_size_threshold_counts_code_only(self):
        self.assertMode("light", [entry("src/a.py", lines=299)])
        self.assertMode("standard", [entry("src/a.py", lines=300)], rule="size")
        self.assertMode("light", [entry(f"src/f{i}.py", lines=1) for i in range(9)])
        self.assertMode("standard", [entry(f"src/f{i}.py", lines=1) for i in range(10)], rule="size")
        result = self.assertMode("light", [entry("docs/guide.md", lines=5000), entry("README.md", lines=900)])
        self.assertEqual(result["reasons"], ["documentation only (2 files)"])
        self.assertEqual(mode.classify([])["reasons"], ["no changes found; for committed work or a pull request, pass --range BASE..HEAD"])

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
        self.assertEqual(self.suggest()["reasons"], ["no changes found; for committed work or a pull request, pass --range BASE..HEAD"])
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

    def test_committed_work_needs_its_range(self):
        self.write("a.py", "A = 1\n")
        self.commit("base")
        self.write(".github/workflows/ci.yml", "on: push\n")
        self.commit("ci")
        # A clean tree says light and points at --range (codex review of 08dbe3c, item 1).
        result = self.suggest()
        self.assertEqual(result["mode"], "light")
        self.assertIn("--range BASE..HEAD", result["reasons"][0])
        self.assertEqual(self.suggest("--range", "HEAD~1..HEAD")["mode"], "deep")

    def test_sub_project_root_sees_only_its_own_files_with_relative_paths(self):
        # codex review of 08dbe3c, item 2: --root inside a larger repository.
        self.write("sub/src/app.py", "A = 1\n")
        self.write("sub/README.md", "# Sub\n")
        self.write("outside/big.py", "B = 1\n")
        self.commit("base")
        self.write("sub/src/app.py", "A = 2\n")
        self.write("sub/new.py", "N = 1\n")  # untracked inside
        self.write(".github/workflows/ci.yml", "on: push\n")  # untracked outside
        self.write("outside/big.py", "".join(f"B{i} = {i}\n" for i in range(400)))
        self.write("outside/AGENTS.md", "# Other\n")
        sub = self.repo / "sub"
        code, output, errors = run("suggest", "--root", str(sub), "--json")
        self.assertEqual(code, 0, errors)
        result = json.loads(output)
        self.assertEqual((result["mode"], result["files"], result["code_lines"]), ("light", 2, 3), result)
        self.commit("change")
        self.write("sub/AGENTS.md", "# Sub policy\n")
        self.git("mv", "sub/README.md", "sub/docs.md")
        self.commit("policy")
        code, output, errors = run("suggest", "--root", str(sub), "--json", "--range", "HEAD~2..HEAD")
        result = json.loads(output)
        self.assertEqual(result["mode"], "deep", result)
        self.assertEqual(result["triggers"][0]["paths"], ["AGENTS.md"])
        self.assertEqual(result["files"], 4, result)  # src/app.py, new.py, AGENTS.md, README.md renamed to docs.md
        self.assertFalse(any(path.startswith(("sub/", "outside/", ".github/")) for t in result["triggers"] for path in t["paths"]))

    def test_path_list_counts_missing_paths_as_new(self):
        self.write("docs/designs/old.md", "# Old\n")
        self.commit("old design")
        result = self.suggest("--paths", "docs/designs/old.md", "./docs/designs/new.md", str(self.repo / "src/a.py"))
        self.assertEqual(result["mode"], "deep")
        self.assertEqual(result["triggers"][0]["paths"], ["docs/designs/new.md"])
        self.assertEqual(result["source"], "path list")
        # A plan saved a moment ago exists but HEAD does not have it: still new (codex review of 78e02e1, P1).
        self.write("docs/plans/cache.md", "# Plan\n")
        result = self.suggest("--paths", "docs/plans/cache.md")
        self.assertEqual((result["mode"], result["triggers"][0]["rule"]), ("deep", "new-plan-doc"))
        self.assertEqual([s["step"] for s in result["steps"]], ["plan", "design-review", "code-review"])
        self.commit("plan")
        self.assertEqual(self.suggest("--paths", "docs/plans/cache.md", "docs")["mode"], "light")
        code, _, errors = run("suggest", "--root", str(self.repo), "--paths", "../elsewhere.py")
        self.assertEqual(code, 2)
        self.assertIn("not a project path", errors)

    def test_text_output_names_the_mode_reasons_and_next_command(self):
        self.write("a.py", "A = 1\n")
        code, output, _ = run("suggest", "--root", str(self.repo))
        self.assertEqual(code, 0)
        lines = output.splitlines()
        self.assertEqual(lines[0], "mode: light  (working tree against HEAD: 1 file, 1 code line)")
        self.assertEqual(lines[-1], "how to run it: the oaw-review skill, or python3 scripts/oaw_mode.py show light")


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

    def test_deep_without_egm_keeps_the_highest_effort_and_falls_back_on_the_review(self):
        output = self.show("deep")
        self.assertIn("deep: plan first at the highest effort, then one fresh-context review (EGM is not installed)", output)
        self.assertIn("  claude --permission-mode plan --effort max\n", output)
        self.assertIn("  " + mode.CLAUDE_REVIEW + "\n", output)
        self.assertIn("  codex --sandbox read-only", output)
        self.assertIn("  review: codex review --uncommitted", output)
        self.assertNotIn("egm-review", output)
        self.assertNotIn("--effort high", output)

    def test_deep_with_egm_for_both_hosts(self):
        self.entry(".claude")
        self.entry(".agents")
        lines = self.show("deep").splitlines()
        self.assertEqual(lines, [
            "deep: plan first at the highest effort, then the EGM design review (EGM switch: auto)",
            "Claude Code:",
            "  claude --permission-mode plan --effort max",
            "  design review: the agent runs EGM through the oaw-review skill before any code; "
            "to run it yourself, type /egm-review",
            "  " + mode.CLAUDE_REVIEW,
            "  " + mode.DEEP_ROUNDS,
            "Codex:",
            "  " + mode.CODEX_PLAN,
            "  design review: select the egm-review skill in the skill picker",
            "  " + mode.CODEX_REVIEW,
            "  " + mode.DEEP_ROUNDS,
        ])

    def test_deep_with_egm_for_one_host_names_the_missing_entrypoint(self):
        self.entry(".agents")
        code, output, _ = run("show", "deep", "--root", str(self.root), "--json")
        result = json.loads(output)
        self.assertEqual(result["egm"], {"claude": False, "codex": True})
        self.assertTrue(result["summary"].endswith("(Claude Code has no EGM entrypoint here: one fresh-context review instead)"))
        self.assertEqual(result["hosts"]["claude"][:4], ["claude --permission-mode plan --effort max", mode.FRESH_DESIGN_REVIEW,
                                                         mode.CLAUDE_REVIEW, mode.DEEP_ROUNDS])
        self.assertTrue(result["hosts"]["claude"][-1].endswith(
            "to add it, run from the OAW checkout: " + mode.add_entrypoint(self.root, "claude")))
        self.assertEqual(result["hosts"]["codex"][1:], ["design review: select the egm-review skill in the skill picker",
                                                        mode.CODEX_REVIEW, mode.DEEP_ROUNDS])
        self.entry(".claude")
        (self.root / ".agents/skills/egm-review/SKILL.md").unlink()
        codex = json.loads(run("show", "deep", "--root", str(self.root), "--json")[1])["hosts"]["codex"]
        self.assertTrue(codex[-1].endswith(mode.add_entrypoint(self.root, "codex")))

    def test_entrypoint_hint_quotes_the_target_for_the_shell(self):
        # codex review of 4225749, items 1 and 3: one format on every platform, and no shell expansion.
        for path in ("/work/project", "/work/my project", "/work/project$(printf WRONG)", "/work/a`id`b",
                     "/work/it's \"here\"", "/work/$HOME/x"):
            with self.subTest(path=path):
                command = mode.add_entrypoint(PurePosixPath(path), "claude", platform="posix")
                self.assertEqual(shlex.split(command), ["python3", "scripts/oaw.py", "init", "--target", path,
                                                        "--host", "claude"])
                if path != "/work/project":
                    self.assertIn("'", command)
        self.assertEqual(mode.add_entrypoint(PurePosixPath("/work/project"), "codex", platform="posix"),
                         "python3 scripts/oaw.py init --target /work/project --host codex")
        windows = mode.add_entrypoint(PureWindowsPath(r"C:\Users\RUNNER~1\my project"), "claude", platform="nt")
        self.assertEqual(windows, 'python3 scripts/oaw.py init --target "C:/Users/RUNNER~1/my project" --host claude')
        self.assertEqual(mode.add_entrypoint(PureWindowsPath(r"C:\work\proj"), "claude", platform="nt"),
                         "python3 scripts/oaw.py init --target C:/work/proj --host claude")
        self.assertTrue(mode.add_entrypoint(PureWindowsPath(r"C:\work\$x"), "claude", platform="nt").endswith(
            "(check the quoting: this path contains %, $ or ` that a Windows shell may expand)"))

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
                self.assertIn("Work light by default: no extra review.", policy)
                self.assertIn("Before a change, use the `oaw-review` skill or run "
                              "`python3 scripts/oaw_mode.py suggest --paths <files you plan to change>`", policy)
                self.assertIn("after it, run `python3 scripts/oaw_mode.py suggest`", policy)
                # Committed work needs its range; a clean tree alone says light (codex review of 08dbe3c, item 1).
                self.assertIn("(add `--range BASE..HEAD` for committed work or a pull request)", policy)
                self.assertEqual("EGM" in policy, egm)
                self.assertEqual("EGM runs only as the design review of deep work" in policy, egm)
                self.assertNotIn("explicit invocation", policy)  # D33: the agent starts EGM by the switch
                installed = {p.split("/")[2] for p in package if p.startswith(".agents/skills/")}
                # The default recipe ships the review skill; an explicit selection keeps the suggest fallback line.
                self.assertEqual("oaw-review" in installed, skills is None)
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

    def test_entrypoint_hint_adds_the_missing_host_to_this_project(self):
        # codex review of 08dbe3c, item 3: the printed command must target the project, not the checkout.
        with tempfile.TemporaryDirectory(prefix="oaw-mode-hint-") as temporary:
            target = Path(temporary) / "project"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(oaw.main(["init", "--target", str(target)]), 0)  # default: Codex entrypoints only
            # Default root is the project that holds the installed script, whatever the working directory.
            process = subprocess.run([sys.executable, str(target / "scripts/oaw_mode.py"), "show", "deep", "--json"],
                                     capture_output=True, text=True, check=False, cwd=temporary)
            self.assertEqual(process.returncode, 0, process.stderr)
            note = json.loads(process.stdout)["hosts"]["claude"][-1]
            argv = shlex.split(note.split("run from the OAW checkout: ", 1)[1])
            self.assertEqual(argv[:3], ["python3", "scripts/oaw.py", "init"])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(oaw.main(argv[2:]), 0)
            self.assertTrue((target / ".claude/skills/egm-review/SKILL.md").is_file())
            self.assertFalse((ROOT / ".claude/skills/egm-review").exists(), "never installs into the checkout")
            lines = mode.instructions("deep", target)["hosts"]["claude"]
            self.assertTrue(lines[1].startswith("design review: the agent runs EGM through the oaw-review skill"), lines)

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
                          if "oaw_mode.py" not in line and not line.startswith(("Work light", "(add `--range"))
                          ).encode("utf-8")
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


class SwitchAndStepTests(unittest.TestCase):
    """The EGM switch (D33), review steps and review records."""

    def setUp(self):
        if GIT is None:
            self.skipTest("git is not installed")
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-mode-steps-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        subprocess.run([GIT, "init", "-q", str(self.root)], check=True)

    def run_ok(self, *args):
        code, output, errors = run(*args, "--root", str(self.root))
        self.assertEqual(code, 0, errors)
        return output

    def json(self, *args):
        return json.loads(self.run_ok(*args, "--json"))

    def install_egm_entry(self):
        path = self.root / ".claude/skills/egm-review/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: egm-review\n---\n", encoding="utf-8")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def steps(self, *args):
        return {step["step"]: step for step in self.json("suggest", *args)["steps"]}

    def test_default_switch_is_auto_and_auto_means_egm_today(self):
        result = self.json("egm")
        self.assertEqual((result["egm"], result["source"]), ("auto", "default"))
        self.assertIn("EGM today", result["meaning"])
        self.assertIn("3/3", result["basis"])
        self.assertEqual(mode.AUTO_DESIGN_REVIEW, "egm")
        self.assertFalse((self.root / ".oaw/settings.json").exists(), "showing the switch writes nothing")

    def test_switch_positions_change_the_deep_design_review(self):
        self.install_egm_entry()
        self.write("docs/plans/cache.md", "# Cache plan\n")
        design = self.steps()["design-review"]
        self.assertEqual((design["how"], design["switch"], design["before_code"], design["done"]), ("egm", "auto", True, False))
        self.assertEqual(design["targets"], ["docs/plans/cache.md"])
        self.assertTrue(design["report_dir"].startswith(".oaw/reviews/") and design["report_dir"].endswith("-cache/"))
        self.assertGreaterEqual(design["estimate"]["tokens_low"], int(mode.EGM_TOKENS_FLOOR * mode.ESTIMATE_LOW))
        self.assertFalse(design["ask_first"])
        self.run_ok("egm", "off")
        steps = self.steps()
        self.assertEqual(list(steps), ["plan", "code-review"])
        self.assertEqual(steps["code-review"]["rounds"], 3)
        self.run_ok("egm", "on")
        self.assertEqual(self.steps()["design-review"]["how"], "egm")
        self.assertNotIn("basis", self.steps()["design-review"], "on is the user's choice, not evidence")
        output = self.run_ok("egm")
        self.assertIn("EGM switch: on", output)
        self.assertIn("every deep task gets the full EGM design review", output)

    def test_without_egm_installed_deep_falls_back_to_a_fresh_context_review(self):
        self.write("docs/plans/cache.md", "# Cache plan\n")
        design = self.steps()["design-review"]
        self.assertEqual(design["how"], "fresh-context")
        self.assertIn("EGM is not installed", design["note"])
        self.assertNotIn("estimate", design)

    def test_light_has_no_steps_and_standard_has_one_code_review(self):
        self.write("a.py", "A = 1\n")
        self.assertEqual(self.json("suggest")["steps"], [])
        self.write("big.py", "".join(f"X{i} = {i}\n" for i in range(300)))
        steps = self.json("suggest")["steps"]
        self.assertEqual([(s["step"], s["rounds"], s["before_code"]) for s in steps], [("code-review", 1, False)])

    def test_planned_paths_before_code_ask_for_a_plan_first(self):
        self.install_egm_entry()
        steps = self.steps("--paths", ".github/workflows/ci.yml")
        self.assertEqual(list(steps), ["plan", "design-review", "code-review"])
        self.assertEqual(steps["design-review"]["targets"], ["the plan you save under docs/plans/"])
        self.assertNotIn("estimate", steps["design-review"])
        text = self.run_ok("suggest", "--paths", ".github/workflows/ci.yml")
        self.assertIn("before code: plan, then save it under docs/plans/", text)
        self.assertIn("before code: design review by EGM (EGM switch: auto)", text)
        self.assertIn("after code: code review by a fresh session of the same model family, up to 3 rounds", text)

    def test_a_recorded_review_counts_only_for_the_same_file_content(self):
        self.install_egm_entry()
        self.write("docs/plans/cache.md", "# Cache plan\n")
        self.run_ok("reviewed", "docs/plans/cache.md", "--how", "egm", "--status", "cut")
        self.assertFalse(self.steps()["design-review"]["done"], "a run cut short is not a review")
        output = self.run_ok("reviewed", "./docs/plans/cache.md", "--how", "egm", "--report", ".oaw/reviews/r1/", "--tokens", "1200000")
        self.assertIn("reviewed by egm (done)", output)
        self.assertTrue(self.steps()["design-review"]["done"])
        self.assertIn("[done for this file content]", self.run_ok("suggest"))
        self.write("docs/plans/cache.md", "# Cache plan\nChanged.\n")
        self.assertFalse(self.steps()["design-review"]["done"])
        records = json.loads((self.root / ".oaw/reviews/index.json").read_text(encoding="utf-8"))["reviews"]
        self.assertEqual([r["status"] for r in records], ["cut", "done"])
        for bad in ("../x.md", "/etc/passwd", "C:/x.md", "docs/missing.md"):
            with self.subTest(bad=bad):
                code, _, errors = run("reviewed", bad, "--how", "egm", "--root", str(self.root))
                self.assertEqual(code, 2, errors)

    def test_cap_and_estimate(self):
        self.install_egm_entry()
        self.write("docs/plans/big.md", "x" * 120_000)
        design = self.steps()["design-review"]
        self.assertTrue(design["ask_first"], design["estimate"])  # 120 KB is above the default 25M at the high end
        self.run_ok("egm", "auto", "--max-tokens", "900000000")
        self.assertFalse(self.steps()["design-review"]["ask_first"])
        small, large = mode.egm_estimate(2_300), mode.egm_estimate(105_000)
        self.assertLess(small["tokens_low"], 1_100_000)
        self.assertGreater(small["tokens_high"], 1_100_000)
        self.assertLess(large["tokens_low"], 18_500_000)
        self.assertGreater(large["tokens_high"], 18_500_000)
        self.assertEqual(mode.egm_estimate(0)["tokens_low"], int(mode.EGM_TOKENS_FLOOR * mode.ESTIMATE_LOW))
        output = self.run_ok("egm", "estimate", "docs/plans/big.md")
        self.assertIn("one EGM run reading 120,000 bytes", output)
        for args in (("egm", "estimate"), ("egm", "estimate", "nope.md"), ("egm", "off", "x.md"), ("egm", "--max-tokens", "0")):
            with self.subTest(args=args):
                self.assertEqual(run(*args, "--root", str(self.root))[0], 2)

    def test_settings_keep_other_keys_and_refuse_bad_values(self):
        self.write(".oaw/settings.json", json.dumps({"mine": 1, "review": {"egm": "off", "custom": True}}))
        self.run_ok("egm", "on")
        data = json.loads((self.root / ".oaw/settings.json").read_text(encoding="utf-8"))
        self.assertEqual(data, {"mine": 1, "review": {"egm": "on", "custom": True}})
        self.run_ok("second-opinion", "codex")
        review = self.steps("--paths", "AGENTS.md")["code-review"]
        self.assertIn("codex review", review["claude"])
        self.assertIn("the codex family", review["who"])
        self.run_ok("second-opinion", "claude")
        self.assertIn("claude -p", self.steps("--paths", "AGENTS.md")["code-review"]["codex"])
        for content, words in (("{bad", "not readable JSON"), ('{"review": {"egm": "maybe"}}', "review.egm must be"),
                               ('{"review": {"egm_max_tokens": true}}', "egm_max_tokens"),
                               ('{"review": {"dry_run": "yes"}}', "dry_run"), ('{"review": []}', '"review" object')):
            with self.subTest(content=content):
                self.write(".oaw/settings.json", content)
                code, _, errors = run("suggest", "--root", str(self.root))
                self.assertEqual(code, 2)
                self.assertIn(words, errors)
                self.assertEqual(run("egm", "on", "--root", str(self.root))[0], 2, "never overwrites a broken file")
                self.assertEqual((self.root / ".oaw/settings.json").read_text(encoding="utf-8"), content)

    def test_a_lighter_review_never_stands_in_for_egm(self):
        self.install_egm_entry()
        self.write("docs/plans/cache.md", "# Cache plan\n")
        self.run_ok("reviewed", "docs/plans/cache.md", "--how", "fresh-context")
        self.assertFalse(self.steps()["design-review"]["done"], "EGM is required (codex review of 78e02e1)")
        self.run_ok("egm", "off")
        self.run_ok("reviewed", "docs/plans/cache.md", "--how", "egm")
        self.run_ok("egm", "on")
        self.assertTrue(self.steps()["design-review"]["done"])

    def test_state_never_leaves_the_project_through_links(self):
        outside = Path(tempfile.mkdtemp(prefix="oaw-mode-outside-"))
        self.addCleanup(shutil.rmtree, outside, True)
        (outside / "secret.md").write_text("# not ours\n", encoding="utf-8")
        try:
            (self.root / ".oaw").symlink_to(outside, target_is_directory=True)
            (self.root / "linked.md").symlink_to(outside / "secret.md")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available")
        for args in (("egm", "off"), ("reviewed", "linked.md", "--how", "egm"), ("egm", "estimate", "linked.md")):
            with self.subTest(args=args):
                code, _, errors = run(*args, "--root", str(self.root))
                self.assertEqual(code, 2, errors)
                self.assertIn("outside the project", errors)
        self.assertEqual(sorted(p.name for p in outside.iterdir()), ["secret.md"], "nothing written outside")

    def test_estimate_with_context_applies_the_cap(self):
        self.write("docs/plans/small.md", "x" * 2_300)
        self.write("docs/context.md", "y" * 105_000)
        alone = self.json("egm", "estimate", "docs/plans/small.md")
        self.assertFalse(alone["ask_first"])
        both = self.json("egm", "estimate", "docs/plans/small.md", "docs/context.md")
        self.assertTrue(both["ask_first"], both)
        self.assertEqual(both["egm_max_tokens"], mode.DEFAULT_EGM_MAX_TOKENS)
        self.assertIn("ask the user first", self.run_ok("egm", "estimate", "docs/plans/small.md", "docs/context.md"))

    def test_show_follows_the_second_opinion_setting(self):
        self.run_ok("second-opinion", "codex")
        standard = mode.instructions("standard", self.root)["hosts"]
        self.assertTrue(standard["claude"][1].startswith("review: codex review"), standard)
        self.run_ok("egm", "off")  # off holds without an EGM entrypoint too (codex review round 3)
        deep = mode.instructions("deep", self.root)
        self.assertIn("the EGM switch is off", deep["summary"])
        self.assertNotIn(mode.FRESH_DESIGN_REVIEW, deep["hosts"]["claude"])
        self.run_ok("egm", "auto")
        self.run_ok("second-opinion", "claude")
        codex = mode.instructions("deep", self.root)["hosts"]["codex"]
        self.assertTrue(any("claude -p" in line and "untracked files included" in line for line in codex), codex)

    def test_concurrent_writers_keep_every_review(self):
        self.write("docs/plans/a.md", "# A\n")
        import threading
        errors = []

        def record():
            try:
                mode.record_review(self.root, "docs/plans/a.md", "egm", None, "done", None)
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)

        threads = [threading.Thread(target=record) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(mode.review_records(self.root)), 8)

    def test_dry_run_is_reported(self):
        self.write(".oaw/settings.json", json.dumps({"review": {"dry_run": True}}))
        self.write("docs/plans/a.md", "# A\n")
        self.assertTrue(self.json("suggest")["dry_run"])
        self.assertIn("dry run", self.run_ok("suggest"))

