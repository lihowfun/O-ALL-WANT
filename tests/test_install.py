"""Safety regressions for the source-only OAW installation CLI (stdlib only)."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("oaw_install_test", SOURCE_ROOT / "scripts" / "oaw.py")
oaw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oaw)


def checksum(data):
    return hashlib.sha256(data).hexdigest()


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-install-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.framework = self.base / "framework"
        self.target = self.base / "project"
        self.framework.mkdir()
        files = {
            "templates/AGENTS.md": "# Project policy\nUse native runtime capabilities.\n",
            "templates/CLAUDE.md": "@AGENTS.md\n",
            "scripts/context_hub.py": "from oaw_common import VALUE\n",
            "scripts/oaw_common.py": "VALUE = 1\n",
            "scripts/wiki_sync.py": "from oaw_common import VALUE\n",
            "scripts/validate_skills.py": "def lint_skill_file(path):\n    return [] if 'description:' in path.read_text(encoding='utf8') else ['missing description']\n",
            "scripts/improvement.py": "print('improvement workflow')\n",
            "templates/docs/knowledge/index.md": "# Knowledge index\n",
            "templates/docs/raw/README.md": "# Source notes\n",
        }
        for name in ("oaw-evidence", "oaw-wiki", "oaw-improve"):
            files[f"templates/.agents/skills/{name}/SKILL.md"] = f"---\nname: {name}\ndescription: Use this workflow when relevant.\n---\n\n# Workflow\n"
        for relative, text in files.items():
            self.write(self.framework, relative, text.encode())
        self.legacy = {
            "CLAUDE.md": b"# Old v1 policy\n",
            "AGENTS.md": b"Read CLAUDE.md first.\n",
            ".agents/skills/benchmark.md": b"# Legacy benchmark\n",
            ".agents/skills/README.md": b"# Legacy skills index\n",
            ".cursorrules": b"Read CLAUDE.md first.\n",
            "scripts/context_hub.py": b"# Legacy helper\n",
            "scripts/wiki_sync.py": b"# Legacy wiki\n",
            ".agents/memory.md": b"# Retain decisions\n",
            "docs/knowledge/index.md": b"# Retain wiki\n",
            "VERSION.json": b'{"version":"my-app-3"}\n',
            "ROADMAP.md": b"# Retain plans\n",
            "AI_CONTEXT.md": b"# Retain context\n",
        }
        hashes = {relative: [checksum(content), checksum(content.replace(b"\n", b"\r\n"))] for relative, content in self.legacy.items()}
        self.write(self.framework, "scripts/legacy_manifest.json", json.dumps({"schema_version": 1, "files": hashes}).encode())
        self.root_patch = patch.object(oaw, "FRAMEWORK_ROOT", self.framework)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    @staticmethod
    def write(root, relative, content):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def invoke(self, command, *args):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = oaw.main([command, "--target", str(self.target), "--json", *args])
        return code, json.loads(output.getvalue())

    def snapshot(self):
        return {p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob("*") if p.is_file()} if self.target.exists() else {}

    def seed_legacy(self):
        for relative, content in self.legacy.items():
            self.write(self.target, relative, content)

    def test_fresh_minimal_install_and_idempotence(self):
        code, result = self.invoke("init")
        self.assertEqual(code, 0, result)
        manifest = json.loads((self.target / ".oaw/install.json").read_text())
        self.assertEqual(manifest["framework_version"], "2.0.0")
        self.assertEqual(len(manifest["managed_files"]), 5)
        for relative, expected in manifest["managed_files"].items():
            self.assertEqual(checksum((self.target / relative).read_bytes()), expected)
        self.assertFalse((self.target / "scripts/oaw.py").exists())
        self.assertFalse((self.target / "scripts/wiki_sync.py").exists())
        self.assertFalse((self.target / "VERSION.json").exists())
        self.assertFalse((self.target / ".agents/memory.md").exists())
        before = self.snapshot()
        self.assertEqual(self.invoke("init")[0], 0)
        self.assertEqual(self.snapshot(), before)
        code, health = self.invoke("doctor")
        self.assertEqual(code, 0, health)
        self.assertTrue(all(c["enabled"] == "UNKNOWN" for c in health["capabilities"]))

    def test_additive_profiles_preserve_domain_content(self):
        self.write(self.target, "docs/knowledge/index.md", b"# My knowledge\n")
        code, result = self.invoke("init", "--profile", "knowledge", "--with-improve")
        self.assertEqual(code, 0, result)
        self.assertEqual((self.target / "docs/knowledge/index.md").read_bytes(), b"# My knowledge\n")
        self.assertTrue((self.target / "scripts/oaw_common.py").is_file())
        self.assertTrue((self.target / "scripts/validate_skills.py").is_file())
        self.assertTrue((self.target / "scripts/improvement.py").is_file())
        before = self.snapshot()
        self.assertEqual(self.invoke("init")[0], 0)
        self.assertEqual(self.snapshot(), before)
        manifest = json.loads((self.target / ".oaw/install.json").read_text())
        self.assertEqual(manifest["profile"], "knowledge")
        self.assertTrue(manifest["with_improve"])
        self.assertFalse(any(path.startswith("docs/") for path in manifest["managed_files"]))

    def test_claude_host_uses_native_claude_skill_folder_only(self):
        code, result = self.invoke("init", "--host", "claude")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["hosts"], ["claude"])
        self.assertTrue((self.target / ".claude/skills/oaw-evidence/SKILL.md").is_file())
        self.assertFalse((self.target / ".agents/skills").exists())
        self.assertTrue((self.target / "AGENTS.md").is_file())
        self.assertEqual(self.invoke("doctor")[0], 0)

    def test_both_hosts_receive_identical_native_skill_packages(self):
        code, result = self.invoke("init", "--host", "both", "--profile", "knowledge", "--with-improve")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["hosts"], ["codex", "claude"])
        for name in ("oaw-evidence", "oaw-wiki", "oaw-improve"):
            self.assertEqual((self.target / f".agents/skills/{name}/SKILL.md").read_bytes(),
                             (self.target / f".claude/skills/{name}/SKILL.md").read_bytes())
        self.assertEqual(self.invoke("doctor")[0], 0)
        self.write(self.target, ".claude/skills/oaw-wiki/SKILL.md", b"# Invalid native skill\n")
        self.assertEqual(self.invoke("doctor")[0], 1)

    def test_host_selection_is_additive_and_default_source_api_stays_codex(self):
        self.assertTrue(any(path.startswith(".agents/skills/") for path in oaw.source_files("minimal", False)))
        self.assertFalse(any(path.startswith(".claude/") for path in oaw.source_files("minimal", False)))
        self.assertEqual(self.invoke("init", "--host", "claude")[0], 0)
        code, result = self.invoke("migrate", "--apply", "--host", "codex")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["hosts"], ["codex", "claude"])
        before = self.snapshot()
        self.assertEqual(self.invoke("init")[0], 0)
        self.assertEqual(self.snapshot(), before)
        manifest = json.loads((self.target / ".oaw/install.json").read_text())
        self.assertEqual(manifest["hosts"], ["codex", "claude"])

    def test_init_preserves_custom_conflict_without_partial_writes(self):
        self.write(self.target, "AGENTS.md", b"# User policy\n")
        before = self.snapshot()
        code, result = self.invoke("init")
        self.assertEqual(code, 2, result)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.target / ".oaw").exists())

    def test_directory_conflict_preflight(self):
        (self.target / "CLAUDE.md").mkdir(parents=True)
        code, result = self.invoke("init")
        self.assertEqual(code, 2, result)
        self.assertIn("regular file", result["error"])
        self.assertFalse((self.target / "AGENTS.md").exists())
        self.assertFalse((self.target / ".oaw").exists())

    def test_parent_file_conflict_preflight(self):
        self.write(self.target, ".agents", b"not a directory")
        code, result = self.invoke("init")
        self.assertEqual(code, 2, result)
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_missing_source_does_not_create_target(self):
        (self.framework / "scripts/oaw_common.py").unlink()
        code, result = self.invoke("init")
        self.assertEqual(code, 2, result)
        self.assertIn("missing", result["error"])
        self.assertFalse(self.target.exists())

    def test_missing_optional_source_does_not_partially_install(self):
        (self.framework / "scripts/improvement.py").unlink()
        code, result = self.invoke("init", "--with-improve")
        self.assertEqual(code, 2, result)
        self.assertFalse(self.target.exists())

    def test_symlink_parent_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.target.mkdir()
        try:
            (self.target / ".agents").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Host cannot create symlinks: {exc}")
        code, result = self.invoke("init")
        self.assertEqual(code, 2, result)
        self.assertIn("traversal refused", result["error"])
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_system_alias_ancestor_is_canonicalized_for_source_and_target(self):
        alias = self.base / "system-alias"
        try:
            alias.symlink_to(self.base, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Host cannot create symlinks: {exc}")
        canonical_target = self.target
        with patch.object(oaw, "FRAMEWORK_ROOT", alias / "framework"), patch.object(self, "target", alias / "project"):
            code, result = self.invoke("init")
            self.assertEqual(code, 0, result)
            self.assertEqual(Path(result["target"]), canonical_target)
            self.assertEqual(self.invoke("doctor")[0], 0)
            self.assertEqual(self.invoke("migrate")[0], 0)
        self.assertTrue((canonical_target / "AGENTS.md").is_file())

    def test_explicit_symlink_project_root_is_refused(self):
        outside = self.base / "outside-project"
        outside.mkdir()
        try:
            self.target.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Host cannot create symlinks: {exc}")
        code, result = self.invoke("init")
        self.assertEqual(code, 2, result)
        self.assertIn("traversal refused", result["error"])
        self.assertEqual(list(outside.iterdir()), [])

    def test_managed_file_symlink_is_refused_after_root_canonicalization(self):
        outside = self.base / "outside-policy.md"
        outside.write_bytes(b"# Outside project policy\n")
        self.target.mkdir()
        try:
            (self.target / "AGENTS.md").symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"Host cannot create symlinks: {exc}")
        code, result = self.invoke("init")
        self.assertEqual(code, 2, result)
        self.assertIn("traversal refused", result["error"])
        self.assertEqual(outside.read_bytes(), b"# Outside project policy\n")
        self.assertFalse((self.target / "CLAUDE.md").exists())
        self.assertFalse((self.target / ".oaw").exists())

    if os.name == "nt":
        # Junctions need no privilege, so these always run on Windows; POSIX has no such test.
        def assert_junction_refused(self, name, *args):
            import _winapi
            outside = self.base / f"outside-{name}"
            outside.mkdir()
            (outside / "keep.md").write_bytes(b"# Outside\n")
            self.target.mkdir()
            link = self.target / name
            _winapi.CreateJunction(str(outside), str(link))
            self.addCleanup(os.rmdir, link)
            code, result = self.invoke("init", *args)
            self.assertEqual(code, 2, result)
            self.assertIn("traversal refused", result["error"])
            self.assertEqual(os.listdir(self.target), [name])
            for relative, content in self.legacy.items():
                if not relative.startswith(name + "/"):
                    self.write(self.target, relative, content)
            before = {k: v for k, v in self.snapshot().items() if not k.startswith(name + "/")}
            code, result = self.invoke("migrate", "--apply", *args)
            self.assertEqual(code, 2, result)
            self.assertIn("traversal refused", result["error"])
            self.assertEqual({k: v for k, v in self.snapshot().items() if not k.startswith(name + "/")}, before)
            self.assertFalse((self.target / ".oaw").exists())
            self.assertEqual({p.name: p.read_bytes() for p in outside.iterdir()}, {"keep.md": b"# Outside\n"})

        def test_windows_junction_at_agents_is_refused(self):
            self.assert_junction_refused(".agents")

        def test_windows_junction_at_docs_is_refused(self):
            self.assert_junction_refused("docs", "--profile", "knowledge")

    def test_manifest_traversal_is_refused(self):
        self.invoke("init")
        path = self.target / ".oaw/install.json"
        manifest = json.loads(path.read_text())
        manifest["managed_files"]["../escape"] = "0" * 64
        path.write_text(json.dumps(manifest))
        code, result = self.invoke("doctor")
        self.assertEqual(code, 2, result)
        self.assertIn("Unsafe", result["error"])

    def test_migrate_is_dry_run_then_backs_up_retirements(self):
        self.seed_legacy()
        self.write(self.target, ".agents/skills/my-custom.md", b"# My own workflow\n")
        before = self.snapshot()
        code, preview = self.invoke("migrate")
        self.assertEqual(code, 0, preview)
        self.assertEqual(preview["status"], "dry-run")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.target / ".oaw").exists())
        code, result = self.invoke("migrate", "--apply")
        self.assertEqual(code, 0, result)
        backup = self.target / result["backup"]
        self.assertEqual((backup / "CLAUDE.md").read_bytes(), self.legacy["CLAUDE.md"])
        self.assertEqual((backup / ".agents/skills/benchmark.md").read_bytes(), self.legacy[".agents/skills/benchmark.md"])
        self.assertTrue((backup / "migration.json").is_file())
        self.assertFalse((self.target / ".agents/skills/benchmark.md").exists())
        self.assertFalse((self.target / ".cursorrules").exists())
        self.assertFalse((self.target / "scripts/wiki_sync.py").exists())
        self.assertTrue((self.target / ".agents/skills/my-custom.md").is_file())
        for relative in [*oaw.ALWAYS_PRESERVE, "docs/knowledge/index.md"]:
            self.assertEqual((self.target / relative).read_bytes(), self.legacy[relative])

    def test_migration_conflicts_stage_proposals_and_fail_doctor(self):
        self.seed_legacy()
        self.write(self.target, "CLAUDE.md", b"# User customized policy\n")
        self.write(self.target, ".agents/skills/benchmark.md", b"# User customized skill\n")
        code, result = self.invoke("migrate", "--apply")
        self.assertEqual(code, 3, result)
        self.assertEqual(result["status"], "conflicts")
        self.assertEqual((self.target / "CLAUDE.md").read_bytes(), b"# User customized policy\n")
        self.assertEqual((self.target / ".agents/skills/benchmark.md").read_bytes(), b"# User customized skill\n")
        # The v1 AGENTS.md only points at the custom router, so the policy pair stays together.
        self.assertEqual(result["pending_conflicts"], ["AGENTS.md", "CLAUDE.md"])
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), self.legacy["AGENTS.md"])
        proposals = {Path(p).name: (self.target / p).read_bytes() for p in result["proposals"]}
        self.assertEqual(proposals, {"AGENTS.md": (self.framework / "templates/AGENTS.md").read_bytes(), "CLAUDE.md": b"@AGENTS.md\n"})
        self.assertEqual(self.invoke("doctor")[0], 1)
        # Explicit manual resolution is recognized; no force-overwrite flag exists.
        self.write(self.target, "CLAUDE.md", b"@AGENTS.md\n")
        self.assertEqual(self.invoke("migrate", "--apply")[0], 0)
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), (self.framework / "templates/AGENTS.md").read_bytes())
        self.assertEqual(self.invoke("doctor")[0], 0)

    def test_kept_v1_router_keeps_policy_pair_and_doctor_warns(self):
        self.seed_legacy()
        self.write(self.target, "CLAUDE.md", b"# User customized v1 router\n")
        code, result = self.invoke("migrate", "--apply", "--keep-custom", "CLAUDE.md")
        self.assertEqual(code, 3, result)
        self.assertEqual(result["pending_conflicts"], ["AGENTS.md"])
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), self.legacy["AGENTS.md"])
        self.assertEqual(self.invoke("doctor")[0], 1)
        code, result = self.invoke("migrate", "--apply", "--keep-custom", "AGENTS.md")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["custom_files"], ["AGENTS.md", "CLAUDE.md"])
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), self.legacy["AGENTS.md"])
        code, health = self.invoke("doctor")
        self.assertEqual(code, 0, health)
        self.assertTrue(any(c["status"] == "WARN" and c["path"] == "CLAUDE.md" and "different policy" in c["detail"]
                            for c in health["checks"]), health)

    def test_modified_v2_managed_file_is_never_overwritten(self):
        self.invoke("init")
        self.write(self.target, "AGENTS.md", b"# Edited policy\n")
        self.write(self.framework, "templates/AGENTS.md", b"# Framework revision\n")
        self.assertEqual(self.invoke("init")[0], 2)
        code, result = self.invoke("migrate", "--apply")
        self.assertEqual(code, 3, result)
        self.assertEqual(result["pending_conflicts"], ["AGENTS.md"])
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), b"# Edited policy\n")
        self.assertEqual((self.target / result["proposals"][0]).read_bytes(), b"# Framework revision\n")

    def test_user_edit_to_current_policy_does_not_block_host_or_profile_addition(self):
        self.assertEqual(self.invoke("init")[0], 0)
        installed = (self.target / "AGENTS.md").read_bytes()
        edited = installed + b"Run the project test suite before commits.\n"
        self.write(self.target, "AGENTS.md", edited)
        code, result = self.invoke("init", "--host", "claude")
        self.assertEqual(code, 0, result)
        self.assertIn({"path": "AGENTS.md", "action": "preserve-edit", "before": checksum(edited), "after": checksum(installed)},
                      result["actions"])
        self.assertTrue((self.target / ".claude/skills/oaw-evidence/SKILL.md").is_file())
        code, result = self.invoke("migrate", "--apply", "--with-improve")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["pending_conflicts"], [])
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), edited)
        manifest = json.loads((self.target / ".oaw/install.json").read_text())
        self.assertEqual(manifest["managed_files"]["AGENTS.md"], checksum(installed))
        self.assertEqual(manifest["custom_files"], [])
        code, health = self.invoke("doctor")
        self.assertEqual(code, 0, health)
        detail = next(c["detail"] for c in health["checks"] if c["path"] == "AGENTS.md" and c["status"] == "WARN")
        self.assertIn("conflict", detail)
        self.assertNotIn("will preserve your changes", detail)

    def test_explicit_keep_custom_resolves_reviewed_policy_and_stays_protected(self):
        self.seed_legacy()
        merged = b"@AGENTS.md\n\n# Reviewed project-specific rules\n"
        self.write(self.target, "CLAUDE.md", merged)
        self.assertEqual(self.invoke("migrate", "--apply")[0], 3)
        # A custom adapter that imports AGENTS.md lets the v1 pointer be replaced.
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), (self.framework / "templates/AGENTS.md").read_bytes())
        code, result = self.invoke("migrate", "--apply", "--keep-custom", "CLAUDE.md")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["custom_files"], ["CLAUDE.md"])
        manifest = json.loads((self.target / ".oaw/install.json").read_text())
        self.assertNotIn("CLAUDE.md", manifest["managed_files"])
        self.assertEqual(manifest["custom_files"], ["CLAUDE.md"])
        code, health = self.invoke("doctor")
        self.assertEqual(code, 0, health)
        self.assertTrue(any(c["path"] == "CLAUDE.md" and "Project-owned custom" in c["detail"] for c in health["checks"]))
        self.assertFalse(any(c["status"] == "WARN" for c in health["checks"]), health)
        self.write(self.framework, "templates/CLAUDE.md", b"# Future framework adapter\n")
        self.assertEqual(self.invoke("migrate", "--apply")[0], 0)
        self.assertEqual((self.target / "CLAUDE.md").read_bytes(), merged)
        self.assertEqual(self.invoke("init")[0], 0)
        self.assertEqual((self.target / "CLAUDE.md").read_bytes(), merged)
        self.assertEqual(self.invoke("migrate", "--apply", "--keep-custom", "CLAUDE.md")[0], 0)

    def test_keep_custom_rejects_unknown_nonconflict_and_dry_run_without_writes(self):
        self.write(self.target, "AGENTS.md", b"# User policy\n")
        before = self.snapshot()
        code, result = self.invoke("migrate", "--keep-custom", "AGENTS.md")
        self.assertEqual(code, 2, result)
        self.assertIn("requires --apply", result["error"])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.target / ".oaw").exists())
        for relative in ("unknown.md", "../escape", "CLAUDE.md"):
            code, result = self.invoke("migrate", "--apply", "--keep-custom", relative)
            self.assertEqual(code, 2, result)
            self.assertEqual(self.snapshot(), before)
            self.assertFalse((self.target / ".oaw").exists())

    def test_keep_custom_is_repeatable_and_does_not_skip_skill_validation(self):
        self.invoke("init")
        self.write(self.target, "AGENTS.md", b"# Reviewed custom policy\n")
        self.write(self.target, ".agents/skills/oaw-evidence/SKILL.md", b"# Invalid custom skill\n")
        code, result = self.invoke("migrate", "--apply", "--keep-custom", "AGENTS.md",
                                   "--keep-custom", ".agents/skills/oaw-evidence/SKILL.md")
        self.assertEqual(code, 0, result)
        self.assertEqual(len(result["custom_files"]), 2)
        self.assertEqual(self.invoke("doctor")[0], 1)

    def test_unchanged_v2_managed_file_gets_backed_up_on_upgrade(self):
        self.invoke("init")
        old = (self.target / "AGENTS.md").read_bytes()
        self.write(self.framework, "templates/AGENTS.md", b"# Updated framework policy\n")
        self.assertEqual(self.invoke("init")[0], 2)
        code, result = self.invoke("migrate", "--apply")
        self.assertEqual(code, 0, result)
        self.assertEqual((self.target / result["backup"] / "AGENTS.md").read_bytes(), old)
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), b"# Updated framework policy\n")

    def test_doctor_rejects_missing_required_managed_helper(self):
        self.invoke("init")
        (self.target / "scripts/oaw_common.py").unlink()
        code, result = self.invoke("doctor")
        self.assertEqual(code, 1, result)

    def test_doctor_rejects_invalid_native_skill(self):
        self.invoke("init")
        self.write(self.target, ".agents/skills/oaw-evidence/SKILL.md", b"# Broken skill\n")
        code, result = self.invoke("doctor")
        self.assertEqual(code, 1, result)

    def test_source_repository_is_refused(self):
        with self.assertRaisesRegex(oaw.InstallError, "Refusing"):
            oaw.target_path(self.framework)

    def test_preflight_snapshot_detects_concurrent_changes(self):
        plan = oaw.plan_install(self.target, "minimal", False)
        self.write(self.target, "AGENTS.md", b"# Arrived after preflight\n")
        with self.assertRaisesRegex(oaw.InstallError, "changed since preflight"):
            oaw.apply_plan(plan, migrate=False)
        self.assertFalse((self.target / "CLAUDE.md").exists())
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), b"# Arrived after preflight\n")

    def test_migration_write_failure_rolls_back_and_retains_backup(self):
        self.seed_legacy()
        before = self.snapshot()
        original_write = oaw.atomic_write
        failed = False

        def fail_once(path, content):
            nonlocal failed
            if path == self.target / "scripts/oaw_common.py" and not failed:
                failed = True
                raise OSError("simulated disk failure after earlier writes")
            original_write(path, content)

        with patch.object(oaw, "atomic_write", side_effect=fail_once):
            code, result = self.invoke("migrate", "--apply")
        self.assertEqual(code, 2, result)
        self.assertIn("recoverable backups", result["error"])
        after = {path: content for path, content in self.snapshot().items() if not path.startswith(".oaw/")}
        self.assertEqual(after, before)
        backups = list((self.target / ".oaw/backups").glob("*/CLAUDE.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.legacy["CLAUDE.md"])
        self.assertFalse((self.target / ".oaw/install.json").exists())

    def test_migration_preflight_preserves_manifest_on_write_failure(self):
        self.invoke("init")
        before = self.snapshot()
        self.write(self.framework, "templates/AGENTS.md", b"# Framework revision\n")
        original_write = oaw.atomic_write

        def fail_manifest(path, content):
            if path == self.target / ".oaw/install.json":
                raise OSError("simulated manifest disk failure")
            original_write(path, content)

        with patch.object(oaw, "atomic_write", side_effect=fail_manifest):
            self.assertEqual(self.invoke("migrate", "--apply")[0], 2)
        after = {path: content for path, content in self.snapshot().items() if not path.startswith(".oaw/backups/")}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
