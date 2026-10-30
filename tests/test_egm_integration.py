"""Offline integration checks for V2's complete, pinned EGM runtime.

These tests exercise files and installer behavior. They never invoke an EGM
workflow, a model, a host CLI, or a network service; native discovery and review
quality consequently remain outside what these checks establish.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("oaw_egm_integration_test", ROOT / "scripts/oaw.py")
oaw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(oaw)

COMMIT = "f0ba151b252c9abf1318d9fe857a43265d06de89"
EGM_SKILLS = (
    "egm-bootstrap", "egm-brainstorm", "egm-draft", "egm-drift-report",
    "egm-resolve", "egm-review", "egm-review-loop",
)
AGENTS = (
    "bootstrap_orchestrator", "codebase_details", "comprehension", "design_critic",
    "implementation_readiness", "structural", "style", "synthesizer", "zoom_out",
)
CLAUDE_AGENTS = {
    "egm-bootstrap-orchestrator": "bootstrap_orchestrator",
    "egm-codebase-details": "codebase_details",
    "egm-comprehension": "comprehension",
    "egm-design": "design_critic",
    "egm-implementation-readiness": "implementation_readiness",
    "egm-structural": "structural",
    "egm-style": "style",
    "egm-synthesizer": "synthesizer",
    "egm-zoom-out": "zoom_out",
}
RUNTIME = ".oaw/integrations/egm/"

# The pinned upstream packer's shared runtime contract, rather than an inventory
# inferred only from whatever the current vendored directory happens to contain.
REQUIRED_RUNTIME = {
    "LICENSE", "README.md", "plugin.json", "assets/icon.svg",
    "docs/assets/readme-header.svg", "docs/index.md", "docs/getting_started.md",
    "docs/harnesses.md", "docs/claude.md", "docs/codex.md", "docs/faq.md",
    "docs/privacy.md", "docs/releases.md", "resources/README.md",
    "resources/execution_instructions.md", ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json", ".claude-plugin/icon.png",
    "skills/egm-bootstrap/references/templates.md",
    "skills/egm-bootstrap/references/worker-return.schema.json",
    "skills/egm-draft/references/design_doc.md",
}
REQUIRED_RUNTIME.update(
    f"skills/{name}/{relative}"
    for name in EGM_SKILLS
    for relative in ("SKILL.md", "agents/openai.yaml", "assets/icon.svg")
)
REQUIRED_RUNTIME.update(f"agents/{name}.md" for name in AGENTS)
REQUIRED_RUNTIME.update(f".claude-plugin/agents/{name}.md" for name in AGENTS)
REQUIRED_RUNTIME.update(
    f"resources/document_standards/{name}-standard.md"
    for name in ("feature-spec", "heilmeier", "implementation-readiness", "re-implementation", "zoom-out")
)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    } if root.exists() else {}


def frontmatter_and_body(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError("Expected native agent frontmatter")
    end = lines.index("---", 1)
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1:]).strip()


class EgmIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oaw-egm-integration-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.framework = ROOT
        self.target = self.base / "project with spaces"
        root_patch = patch.object(oaw, "FRAMEWORK_ROOT", self.framework)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def mutable_source_copy(self):
        # Most checks only read source. Isolate the tests that deliberately
        # damage it, retaining dot directories and the upstream raw bytes.
        self.framework = self.base / "framework"
        for relative in ("scripts", "templates", "vendor/egm"):
            shutil.copytree(
                ROOT / relative, self.framework / relative,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        oaw.FRAMEWORK_ROOT = self.framework

    @property
    def vendor(self):
        return self.framework / "vendor/egm"

    def install(self, *, target=None, hosts=None, skills=None, migrate=False, keep_custom=None):
        plan = oaw.plan_install(
            target or self.target, "minimal", False, migrate=migrate,
            hosts=hosts, skills=skills, keep_custom=keep_custom,
        )
        return oaw.apply_plan(plan, migrate=migrate)

    def native_files(self, names, *, target=None, hosts=(".agents",)):
        target = target or self.target
        prefixes = tuple(f"{host}/skills/{name}/" for host in hosts for name in names)
        return {name: data for name, data in snapshot(target).items() if name.startswith(prefixes)}

    def assert_source_refused_without_install(self):
        with self.assertRaises(oaw.InstallError):
            oaw.plan_install(self.target, "minimal", False)
        self.assertFalse(self.target.exists(), "Source integrity failures must not partially install")

    def test_provenance_covers_complete_raw_upstream_runtime_and_license(self):
        provenance = json.loads((self.vendor / "OAW_SOURCE.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["schema_version"], 1)
        self.assertEqual(provenance["repository"], "https://github.com/google/elephant-goldfish-model")
        self.assertEqual(provenance["commit"], COMMIT)
        self.assertEqual(provenance["version"], "0.1.0")
        self.assertEqual(provenance["license"], "Apache-2.0")
        self.assertEqual(set(provenance["skills"]), set(EGM_SKILLS))
        self.assertEqual(provenance["packaging_source"], "scripts/pack_plugin.py")
        self.assertEqual(provenance["packaging_sha256"],
                         "4997bec838a6f093691174ddc1756d464b0e8243f1f4cee0eb119ed02b8fc8bc")
        self.assertTrue(REQUIRED_RUNTIME <= set(provenance["files"]),
                        sorted(REQUIRED_RUNTIME - set(provenance["files"])))
        for relative, expected in provenance["files"].items():
            with self.subTest(source=relative):
                self.assertFalse(Path(relative).is_absolute())
                self.assertNotIn("..", Path(relative).parts)
                self.assertRegex(expected, r"^[0-9a-f]{64}$")
                self.assertEqual(sha256((self.vendor / relative).read_bytes()), expected)
        license_text = (self.vendor / "LICENSE").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(license_text, (ROOT / "evals/egm-pilot/LICENSE.egm").read_bytes().replace(b"\r\n", b"\n"))
        self.assertIn(b"Apache License", license_text)

    def test_default_minimal_v2_includes_all_bridges_and_the_complete_runtime(self):
        package = oaw.source_files("minimal", False)
        self.assertIn(".agents/skills/oaw-evidence/SKILL.md", package)
        for name in EGM_SKILLS:
            self.assertIn(f".agents/skills/{name}/SKILL.md", package)
        for relative, content in snapshot(self.vendor).items():
            self.assertIn(RUNTIME + relative, package)
            self.assertEqual(package[RUNTIME + relative], content)
        result = self.install()
        self.assertEqual(result["pending_conflicts"], [])
        manifest = json.loads((self.target / ".oaw/install.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["framework_version"], "2.0.0")
        self.assertTrue(set(EGM_SKILLS) <= set(manifest["skills"]))
        self.assertEqual(oaw.doctor(self.target)["status"], "healthy")

    def test_each_host_gets_its_native_bridges_and_identical_shared_runtime(self):
        for hosts, prefixes in ((["codex"], (".agents",)), (["claude"], (".claude",)),
                                (["codex", "claude"], (".agents", ".claude"))):
            with self.subTest(hosts=hosts):
                target = self.base / ("project-" + "-".join(hosts))
                self.install(target=target, hosts=hosts)
                for prefix in prefixes:
                    for name in (*EGM_SKILLS, "oaw-evidence"):
                        self.assertTrue((target / prefix / "skills" / name / "SKILL.md").is_file())
                for other in {".agents", ".claude"} - set(prefixes):
                    self.assertFalse((target / other / "skills").exists())
                self.assertEqual(snapshot(target / RUNTIME), snapshot(self.vendor))
                if len(prefixes) == 2:
                    self.assertEqual(snapshot(target / ".agents/skills"), snapshot(target / ".claude/skills"))

    def test_native_bridges_keep_manual_invocation_policy_for_both_hosts(self):
        self.install(hosts=["codex", "claude"])
        for host in (".agents", ".claude"):
            for name in EGM_SKILLS:
                with self.subTest(host=host, skill=name):
                    native = self.target / host / "skills" / name
                    text = (native / "SKILL.md").read_text(encoding="utf-8")
                    self.assertRegex(text, r"(?m)^disable-model-invocation:\s*true\s*$")
                    policy = (native / "agents/openai.yaml").read_text(encoding="utf-8")
                    self.assertRegex(policy, r"(?m)^policy:\s*$")
                    self.assertRegex(policy, r"(?m)^\s+allow_implicit_invocation:\s*false\s*$")

    def test_bridge_entrypoints_and_execution_references_resolve_from_installed_location(self):
        self.install(hosts=["codex", "claude"])
        for host in (".agents", ".claude"):
            for name in EGM_SKILLS:
                with self.subTest(host=host, skill=name):
                    native = self.target / host / "skills" / name
                    reference = f"../../../{RUNTIME}skills/{name}/SKILL.md"
                    self.assertIn(reference, (native / "SKILL.md").read_text(encoding="utf-8"))
                    entrypoint = (native / reference).resolve()
                    self.assertEqual(entrypoint, (self.target / RUNTIME / "skills" / name / "SKILL.md").resolve())
                    self.assertEqual(entrypoint.read_bytes(), (self.vendor / "skills" / name / "SKILL.md").read_bytes())
                    text = entrypoint.read_text(encoding="utf-8")
                    references = re.findall(r"\]\(((?:\.\./\.\./docs/|references/)[^\s)]+)\)", text)
                    self.assertTrue(references, "Every upstream entrypoint links its Codex integration instructions")
                    for relative in references:
                        self.assertTrue((entrypoint.parent / relative.split("#", 1)[0]).is_file(), relative)
        for name in AGENTS:
            self.assertTrue((self.target / RUNTIME / "agents" / f"{name}.md").is_file())

    def test_explicit_skill_selection_filters_bridges_but_keeps_full_upstream_runtime(self):
        package = oaw.source_files("minimal", False, hosts=["codex", "claude"], skills=["egm-review"])
        entrypoints = {path for path in package if re.fullmatch(r"\.(?:agents|claude)/skills/[^/]+/SKILL\.md", path)}
        self.assertEqual(entrypoints, {".agents/skills/egm-review/SKILL.md", ".claude/skills/egm-review/SKILL.md"})
        self.assertEqual({path.removeprefix(RUNTIME): data for path, data in package.items() if path.startswith(RUNTIME)},
                         snapshot(self.vendor))

    def test_explicit_empty_selection_installs_core_and_runtime_without_native_skills(self):
        result = self.install(skills=[])
        self.assertEqual(result["pending_conflicts"], [])
        self.assertFalse((self.target / ".agents/skills").exists())
        self.assertTrue((self.target / "AGENTS.md").is_file())
        self.assertTrue((self.target / "scripts/context_hub.py").is_file())
        self.assertEqual(snapshot(self.target / RUNTIME), snapshot(self.vendor))
        self.assertEqual(oaw.doctor(self.target)["status"], "healthy")

    def test_invalid_skill_selection_is_rejected_before_target_creation(self):
        for skills in (["unknown-egm"], ["egm-review", "egm-review"], ["../egm-review"], "egm-review"):
            with self.subTest(skills=skills), self.assertRaises(oaw.InstallError):
                oaw.plan_install(self.target, "minimal", False, skills=skills)
        self.assertFalse(self.target.exists())

    def test_subset_migration_previews_without_writes_then_backs_up_owned_bridge_removal(self):
        self.install(hosts=["codex", "claude"])
        retired = self.native_files(
            [name for name in EGM_SKILLS if name != "egm-review"], hosts=(".agents", ".claude"),
        )
        before = snapshot(self.target)
        plan = oaw.plan_install(self.target, "minimal", False, migrate=True, skills=["egm-review"])
        self.assertEqual(snapshot(self.target), before)
        actions = {action["path"]: action["action"] for action in plan["actions"]}
        for relative in retired:
            self.assertEqual(actions[relative], "retire")
        result = oaw.apply_plan(plan, migrate=True)
        self.assertEqual(result["pending_conflicts"], [])
        backup = self.target / result["backup"]
        for relative, content in retired.items():
            self.assertFalse((self.target / relative).exists(), relative)
            self.assertEqual((backup / relative).read_bytes(), content)
        for host in (".agents", ".claude"):
            self.assertTrue((self.target / host / "skills/egm-review/SKILL.md").is_file())
        self.assertEqual(snapshot(self.target / RUNTIME), snapshot(self.vendor))
        self.assertEqual(oaw.doctor(self.target)["status"], "healthy")

    def test_edited_skill_blocks_retirement_of_its_entire_native_package(self):
        self.install()
        package = self.target / ".agents/skills/egm-draft"
        entrypoint = package / "SKILL.md"
        entrypoint.write_bytes(entrypoint.read_bytes() + b"\nProject-owned draft guidance.\n")
        before = snapshot(package)
        result = self.install(skills=["egm-review"], migrate=True)
        self.assertIn(".agents/skills/egm-draft/SKILL.md", result["pending_conflicts"])
        self.assertEqual(snapshot(package), before)
        self.assertFalse((self.target / ".agents/skills/egm-resolve/SKILL.md").exists())
        self.assertEqual(oaw.doctor(self.target)["status"], "unhealthy")
        entry = ".agents/skills/egm-draft/SKILL.md"
        acknowledged = self.install(skills=["egm-review"], migrate=True, keep_custom=[entry])
        self.assertEqual(acknowledged["pending_conflicts"], [])
        manifest = json.loads((self.target / ".oaw/install.json").read_text(encoding="utf-8"))
        self.assertTrue(all(".agents/skills/egm-draft/" + name in manifest["custom_files"] for name in before))
        self.assertEqual(snapshot(package), before)
        health = oaw.doctor(self.target)
        self.assertEqual(health["status"], "healthy")
        self.assertTrue(any(c["status"] == "WARN" and "outside the selected recipe" in c["detail"] for c in health["checks"]))
        self.assertEqual(self.install(skills=["egm-review"], migrate=True)["pending_conflicts"], [])
        self.assertEqual(snapshot(package), before)

    def test_init_with_subset_never_silently_retires_existing_bridges(self):
        self.install()
        before = self.native_files(EGM_SKILLS)
        try:
            self.install(skills=["egm-review"])
        except oaw.InstallError:
            pass  # Refusing a removal through init is also safe.
        for relative, content in before.items():
            self.assertEqual((self.target / relative).read_bytes(), content)
        manifest = json.loads((self.target / ".oaw/install.json").read_text(encoding="utf-8"))
        self.assertTrue(set(before) <= set(manifest["managed_files"]), "Retained bridges must remain owned for a later migration")

    def test_reinit_without_selection_preserves_previous_explicit_selection(self):
        self.install(skills=["egm-review"])
        before = snapshot(self.target)
        self.install()
        self.assertEqual(snapshot(self.target), before)
        self.assertFalse((self.target / ".agents/skills/egm-draft").exists())

    def test_migration_preserves_custom_policy_project_memory_and_foreign_native_skills(self):
        retained = {
            "AGENTS.md": b"# Project-specific policy\nKeep evidence within this repository.\n",
            ".agents/memory.md": b"# Existing project decisions\n",
            "AI_CONTEXT.md": b"# Application context\n",
            "VERSION.json": b'{"version": "application-7"}\n',
            ".agents/skills/local-tool/SKILL.md": b"---\nname: local-tool\ndescription: Existing project workflow.\n---\n",
            ".claude/skills/local-tool/SKILL.md": b"---\nname: local-tool\ndescription: Existing Claude workflow.\n---\n",
        }
        for relative, content in retained.items():
            destination = self.target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        result = self.install(hosts=["codex", "claude"], migrate=True, keep_custom=["AGENTS.md"])
        self.assertEqual(result["pending_conflicts"], [])
        for relative, content in retained.items():
            self.assertEqual((self.target / relative).read_bytes(), content)
        self.assertTrue((self.target / ".agents/skills/egm-review/SKILL.md").is_file())
        self.assertTrue((self.target / ".claude/skills/egm-review/SKILL.md").is_file())

    def test_tampered_upstream_source_is_refused_without_partial_install(self):
        self.mutable_source_copy()
        entrypoint = self.vendor / "skills/egm-review/SKILL.md"
        entrypoint.write_bytes(entrypoint.read_bytes() + b"\nTampered upstream instructions.\n")
        self.assert_source_refused_without_install()

    def test_missing_pinned_runtime_file_is_refused_without_partial_install(self):
        self.mutable_source_copy()
        (self.vendor / "agents/synthesizer.md").unlink()
        self.assert_source_refused_without_install()

    def test_unlisted_runtime_source_is_refused_instead_of_shipping_unpinned_content(self):
        self.mutable_source_copy()
        (self.vendor / "agents/unpinned.md").write_bytes(b"# Unreviewed reviewer\n")
        self.assert_source_refused_without_install()

    def test_provenance_pin_or_inventory_tampering_is_refused(self):
        self.mutable_source_copy()
        source = self.vendor / "OAW_SOURCE.json"
        pristine = json.loads(source.read_text(encoding="utf-8"))
        for change in ("commit", "inventory", "self-approved-hash"):
            with self.subTest(change=change):
                provenance = json.loads(json.dumps(pristine))
                if change == "commit":
                    provenance["commit"] = "0" * 40
                elif change == "inventory":
                    provenance["files"].pop("skills/egm-review/SKILL.md")
                else:
                    relative = "skills/egm-review/SKILL.md"
                    changed = (self.vendor / relative).read_bytes() + b"\nAltered instructions.\n"
                    (self.vendor / relative).write_bytes(changed)
                    provenance["files"][relative] = sha256(changed)
                source.write_text(json.dumps(provenance), encoding="utf-8")
                self.assert_source_refused_without_install()

    def test_installed_runtime_drift_fails_doctor_instead_of_claiming_pristine_upstream(self):
        self.install()
        entrypoint = self.target / RUNTIME / "skills/egm-review/SKILL.md"
        entrypoint.write_bytes(entrypoint.read_bytes() + b"\nEdited installed runtime.\n")
        health = oaw.doctor(self.target)
        self.assertEqual(health["status"], "unhealthy", health)
        self.assertTrue(any(check["status"] == "FAIL" and "egm" in check["path"] for check in health["checks"]), health)

    def test_doctor_cannot_hide_selected_egm_runtime_loss_or_drift_by_omitting_manifest_inventory(self):
        for damage in ("missing", "tampered"):
            with self.subTest(runtime=damage):
                target = self.base / f"hidden-runtime-{damage}"
                self.install(target=target, skills=["egm-review"])
                manifest_path = target / ".oaw/install.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest.pop("integrations")
                manifest["managed_files"] = {
                    relative: checksum for relative, checksum in manifest["managed_files"].items()
                    if not relative.startswith(RUNTIME)
                }
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                runtime = target / RUNTIME
                if damage == "missing":
                    self.assertTrue(runtime.resolve().is_relative_to(self.base))
                    shutil.rmtree(runtime)
                else:
                    entry = runtime / "skills/egm-review/SKILL.md"
                    entry.write_bytes(entry.read_bytes() + b"\nAltered installed instructions.\n")
                self.assertTrue((target / ".agents/skills/egm-review/SKILL.md").is_file())
                health = oaw.doctor(target)
                self.assertEqual(health["status"], "unhealthy", health)
                self.assertTrue(any(check["status"] == "FAIL" and check["path"] == RUNTIME
                                    for check in health["checks"]), health)

    def test_doctor_requires_modern_v2_runtime_even_when_all_native_skills_are_disabled(self):
        self.install(skills=[])
        manifest_path = self.target / ".oaw/install.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("integrations")
        manifest["managed_files"] = {
            relative: checksum for relative, checksum in manifest["managed_files"].items()
            if not relative.startswith(RUNTIME)
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        runtime = self.target / RUNTIME
        self.assertTrue(runtime.resolve().is_relative_to(self.base))
        shutil.rmtree(runtime)
        health = oaw.doctor(self.target)
        self.assertEqual(health["status"], "unhealthy", health)
        self.assertTrue(any(check["status"] == "FAIL" and check["path"] == RUNTIME
                            for check in health["checks"]), health)

    def test_doctor_requires_runtime_for_managed_egm_entry_even_without_modern_recipe_fields(self):
        self.install()
        manifest_path = self.target / ".oaw/install.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("integrations", "skills", "skills_explicit"):
            manifest.pop(field)
        manifest["managed_files"] = {
            relative: checksum for relative, checksum in manifest["managed_files"].items()
            if not relative.startswith(RUNTIME)
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        runtime = self.target / RUNTIME
        self.assertTrue(runtime.resolve().is_relative_to(self.base))
        shutil.rmtree(runtime)
        health = oaw.doctor(self.target)
        self.assertEqual(health["status"], "unhealthy", health)
        self.assertTrue(any(check["status"] == "FAIL" and check["path"] == RUNTIME
                            for check in health["checks"]), health)

    def test_claude_native_agent_identities_restrictions_and_runtime_bindings_match_upstream(self):
        self.install(hosts=["claude"])
        adapters = self.target / ".claude/agents"
        self.assertEqual({path.stem for path in adapters.glob("*.md")}, set(CLAUDE_AGENTS))
        for name, canonical in CLAUDE_AGENTS.items():
            with self.subTest(agent=name):
                upstream = (self.vendor / ".claude-plugin/agents" / f"{canonical}.md").read_text(encoding="utf-8")
                installed = (adapters / f"{name}.md").read_text(encoding="utf-8")
                original_fields, original_body = frontmatter_and_body(upstream)
                installed_fields, installed_body = frontmatter_and_body(installed)
                self.assertRegex(installed_fields, rf"(?m)^name: {name}$")
                # Compare the complete native frontmatter, including tools,
                # model and omitClaudeMd (and absence when upstream omits it).
                self.assertEqual(installed_fields, original_fields)
                adapted = original_body.replace("${CLAUDE_PLUGIN_ROOT}", RUNTIME.rstrip("/")).replace("egm:egm-", "egm-")
                self.assertIn(adapted, installed_body)
                self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", installed)
                references = re.findall(r"`(\.oaw/integrations/egm(?:/[^`\s]+)?)`", installed)
                self.assertTrue(references)
                self.assertIn(RUNTIME + f"agents/{canonical}.md", references)
                for relative in references:
                    self.assertTrue((self.target / relative).exists(), relative)

    def test_claude_subset_recipe_includes_all_nine_native_agents_and_codex_does_not(self):
        expected = {f".claude/agents/{name}.md" for name in CLAUDE_AGENTS}
        for hosts, skills, active in ((["claude"], ["egm-review"], True),
                                     (["codex", "claude"], ["egm-bootstrap"], True),
                                     (["claude"], ["oaw-evidence"], False),
                                     (["claude"], [], False),
                                     (["codex"], ["egm-review"], False)):
            with self.subTest(hosts=hosts, skills=skills):
                package = oaw.source_files("minimal", False, hosts=hosts, skills=skills)
                native = {relative for relative in package if relative.startswith(".claude/agents/")}
                self.assertEqual(native, expected if active else set())

    def test_claude_subset_migration_keeps_native_agents_required_by_remaining_egm_skill(self):
        self.install(hosts=["claude"])
        before = snapshot(self.target / ".claude/agents")
        result = self.install(hosts=["claude"], skills=["egm-review"], migrate=True)
        self.assertEqual(result["pending_conflicts"], [])
        self.assertEqual(snapshot(self.target / ".claude/agents"), before)
        self.assertFalse((self.target / ".claude/skills/egm-draft/SKILL.md").exists())
        self.assertTrue((self.target / result["backup"] / ".claude/skills/egm-draft/SKILL.md").is_file())
        self.assertEqual(oaw.doctor(self.target)["status"], "healthy")

    def test_disabling_all_egm_previews_and_backs_up_native_agent_retirements(self):
        self.install(hosts=["claude"])
        foreign = self.target / ".claude/agents/project-reviewer.md"
        foreign.write_bytes(b"---\nname: project-reviewer\ndescription: Project-owned reviewer.\n---\n")
        originals = {f".claude/agents/{name}.md": (self.target / f".claude/agents/{name}.md").read_bytes()
                     for name in CLAUDE_AGENTS}
        before = snapshot(self.target)
        plan = oaw.plan_install(self.target, "minimal", False, migrate=True, hosts=["claude"], skills=["oaw-evidence"])
        self.assertEqual(snapshot(self.target), before)
        actions = {action["path"]: action["action"] for action in plan["actions"]}
        for relative in originals:
            self.assertEqual(actions[relative], "retire")
        result = oaw.apply_plan(plan, migrate=True)
        self.assertEqual(result["pending_conflicts"], [])
        for relative, content in originals.items():
            self.assertFalse((self.target / relative).exists(), relative)
            self.assertEqual((self.target / result["backup"] / relative).read_bytes(), content)
        self.assertEqual(foreign.read_bytes(), before[".claude/agents/project-reviewer.md"])
        self.assertTrue((self.target / ".claude/skills/oaw-evidence/SKILL.md").is_file())
        self.assertEqual(snapshot(self.target / RUNTIME), snapshot(self.vendor))
        self.assertEqual(oaw.doctor(self.target)["status"], "healthy")

    def test_edited_native_agent_retirement_preserves_edit_and_remains_pending(self):
        self.install(hosts=["claude"])
        relative = ".claude/agents/egm-design.md"
        agent = self.target / relative
        edited = agent.read_bytes() + b"\nUse the project's additional critique checklist.\n"
        agent.write_bytes(edited)
        result = self.install(hosts=["claude"], skills=[], migrate=True)
        self.assertIn(relative, result["pending_conflicts"])
        self.assertEqual(agent.read_bytes(), edited)
        self.assertEqual(oaw.doctor(self.target)["status"], "unhealthy")
        for other in set(CLAUDE_AGENTS) - {"egm-design"}:
            other_relative = f".claude/agents/{other}.md"
            self.assertFalse((self.target / other_relative).exists())
            self.assertTrue((self.target / result["backup"] / other_relative).is_file())
        kept = self.install(hosts=["claude"], skills=[], migrate=True, keep_custom=[relative])
        self.assertEqual(kept["pending_conflicts"], [])
        self.assertEqual(agent.read_bytes(), edited)
        self.assertEqual(oaw.doctor(self.target)["status"], "healthy")
        self.assertEqual(self.install(hosts=["claude"], skills=[], migrate=True)["pending_conflicts"], [])
        self.assertEqual(agent.read_bytes(), edited)

    def test_generated_adapter_drift_is_rejected_offline(self):
        self.mutable_source_copy()
        script = self.framework / "scripts/sync_egm.py"
        def check():
            return subprocess.run([sys.executable, str(script), "--check-bundled"],
                                  capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(check().returncode, 0)
        for relative in ("templates/.agents/skills/egm-review/agents/openai.yaml",
                         "templates/.claude/agents/egm-design.md"):
            path = self.framework / relative
            original = path.read_bytes()
            path.write_bytes(original + b"\nUnreviewed adapter change\n")
            result = check()
            self.assertNotEqual(result.returncode, 0, relative)
            self.assertIn("Generated EGM adapter changed", result.stderr)
            path.write_bytes(original)

    def test_retained_custom_claude_skill_keeps_its_native_agent_dependencies(self):
        self.install(hosts=["claude"], skills=["egm-review"])
        relative = ".claude/skills/egm-review/SKILL.md"
        entry = self.target / relative
        entry.write_bytes(entry.read_bytes() + b"\nCustom project review guidance.\n")
        agents = snapshot(self.target / ".claude/agents")
        disabled = self.install(hosts=["claude"], skills=[], migrate=True)
        self.assertIn(relative, disabled["pending_conflicts"])
        self.assertEqual(snapshot(self.target / ".claude/agents"), agents)
        kept = self.install(hosts=["claude"], skills=[], migrate=True, keep_custom=[relative])
        self.assertEqual(kept["pending_conflicts"], [])
        self.assertEqual(snapshot(self.target / ".claude/agents"), agents)
        health = oaw.doctor(self.target)
        self.assertEqual(health["status"], "healthy", health)
        self.assertTrue(any(c["status"] == "WARN" and c["path"] == relative for c in health["checks"]))
        next(iter((self.target / ".claude/agents").glob("*.md"))).unlink()
        self.assertEqual(oaw.doctor(self.target)["status"], "unhealthy")

    def test_doctor_requires_selected_claude_agents_even_if_missing_file_is_not_declared(self):
        relative = ".claude/agents/egm-comprehension.md"
        for declared in (True, False):
            with self.subTest(managed_declaration=declared):
                target = self.base / f"missing-agent-{declared}"
                self.install(target=target, hosts=["claude"], skills=["egm-review"])
                (target / relative).unlink()
                if not declared:
                    path = target / ".oaw/install.json"
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    manifest["managed_files"].pop(relative)
                    path.write_text(json.dumps(manifest), encoding="utf-8")
                health = oaw.doctor(target)
                self.assertEqual(health["status"], "unhealthy", health)
                self.assertTrue(any(check["path"] == relative and check["status"] == "FAIL"
                                    for check in health["checks"]), health)

    def test_init_cannot_silently_retire_installed_claude_native_agents(self):
        self.install(hosts=["claude"])
        before = snapshot(self.target / ".claude/agents")
        try:
            self.install(hosts=["claude"], skills=[])
        except oaw.InstallError:
            pass
        self.assertEqual(snapshot(self.target / ".claude/agents"), before)
        manifest = json.loads((self.target / ".oaw/install.json").read_text(encoding="utf-8"))
        self.assertTrue({f".claude/agents/{name}" for name in before} <= set(manifest["managed_files"]))

    def test_missing_required_native_agent_source_refuses_install_before_writing(self):
        self.mutable_source_copy()
        (self.framework / "templates/.claude/agents/egm-synthesizer.md").unlink()
        with self.assertRaises(oaw.InstallError):
            oaw.plan_install(self.target, "minimal", False, hosts=["claude"], skills=["egm-review"])
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
