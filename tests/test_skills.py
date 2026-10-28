"""Native package contracts and removal of v1's mandatory workflow defaults."""

import importlib.util
import contextlib
import io
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("validate_skills", ROOT / "scripts" / "validate_skills.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class SkillValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.package = self.root / ".agents" / "skills" / "sample-skill"
        self.package.mkdir(parents=True)
        self.skill = self.package / "SKILL.md"

    def tearDown(self):
        self.temp.cleanup()

    def write_skill(self, frontmatter=None, body="Preserve the requested project evidence.\n"):
        if frontmatter is None:
            frontmatter = "name: sample-skill\ndescription: Preserve project evidence when requested."
        self.skill.write_text("---\n" + frontmatter + "\n---\n\n" + body, encoding="utf-8")
        return validator.lint_skill_file(self.skill)

    def test_native_minimum_needs_no_custom_trigger_or_heading(self):
        self.assertEqual(self.write_skill(), [])

    def test_folded_description_and_metadata_are_supported(self):
        self.assertEqual(self.write_skill(
            "name: sample-skill\ndescription: >-\n  Preserve requested evidence\n  for later project work.\nmetadata:\n  owner: project-team"
        ), [])

    def test_required_fields_and_name_location_are_checked(self):
        for frontmatter in (
            "description: Valid description.",
            "name: sample-skill",
            "name: another-skill\ndescription: Valid description.",
            "name: Sample_Skill\ndescription: Valid description.",
            "name: sample-skill\ndescription: ''",
        ):
            with self.subTest(frontmatter=frontmatter):
                self.assertTrue(self.write_skill(frontmatter))

    def test_malformed_and_unsupported_yaml_fails_explicitly(self):
        for frontmatter in (
            "name: sample-skill\ndescription: [a, list]",
            "name: sample-skill\ndescription: false",
            "name: sample-skill\ndescription: \"unterminated",
            "name: sample-skill\nname: repeated\ndescription: Valid description.",
            "name: sample-skill\ndescription: *alias",
            "name: sample-skill\ndescription: Valid description.\ntriggers: always",
            "name: sample-skill\ndescription: Valid description.\nmetadata:\n  invalid: [list]",
        ):
            with self.subTest(frontmatter=frontmatter):
                self.assertTrue(self.write_skill(frontmatter))

    def test_missing_delimiter_and_empty_body_fail(self):
        self.skill.write_text("---\nname: sample-skill\n", encoding="utf-8")
        self.assertTrue(validator.lint_skill_file(self.skill))
        self.assertTrue(self.write_skill(body=""))

    def test_legacy_and_incomplete_packages_cannot_disappear_from_discovery(self):
        flat = self.package.parent / "legacy.md"
        flat.write_text("Legacy workflow", encoding="utf-8")
        discovered = validator.find_skill_files(self.root)
        self.assertIn(str(flat), discovered)
        self.assertIn(str(self.skill), discovered)
        self.assertTrue(validator.lint_skill_file(flat))
        self.assertTrue(validator.lint_skill_file(self.skill))

    def test_framework_canonical_and_native_install_locations(self):
        self.write_skill()
        claude = self.root / ".claude" / "skills" / "claude-skill"
        claude.mkdir(parents=True)
        (claude / "SKILL.md").write_text("", encoding="utf-8")
        self.assertEqual(len(validator.find_skill_files(self.root)), 2)
        canonical = self.root / "templates" / ".agents" / "skills" / "canonical"
        canonical.mkdir(parents=True)
        self.assertEqual(validator.find_skill_files(self.root), [str(canonical / "SKILL.md")])

    def test_local_references_exist_and_are_transitively_checked(self):
        references = self.package / "references"
        references.mkdir()
        guide = references / "guide.md"
        guide.write_text("See [details](details.md).\n", encoding="utf-8")
        self.assertTrue(self.write_skill(body="Read [guide](references/guide.md).\n"))
        (references / "details.md").write_text("Evidence details.\n", encoding="utf-8")
        self.assertEqual(self.write_skill(body="Read [guide](references/guide.md).\n"), [])

    def test_references_cannot_escape_package_or_depend_on_absolute_paths(self):
        (self.package.parent / "outside.md").write_text("Outside", encoding="utf-8")
        for destination in ("../outside.md", "%2e%2e/outside.md", "file:///outside.md", "C:/outside.md", "/outside.md"):
            with self.subTest(destination=destination):
                self.assertTrue(self.write_skill(body="Read [source](%s).\n" % destination))

    def test_external_links_and_fenced_examples_are_not_local_dependencies(self):
        self.assertEqual(self.write_skill(body=(
            "Read [source](https://example.com/reference).\n"
            "```markdown\n[example](missing-example.md)\n```\n"
        )), [])

    def test_cli_reports_schema_failure_as_nonzero(self):
        self.write_skill("name: sample-skill\ndescription: [bad]")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(validator.main([str(self.root)]), 1)


class TemplateDefaultsTests(unittest.TestCase):
    def test_only_scoped_native_packages_are_shipped(self):
        packages = validator.find_skill_files(ROOT)
        self.assertEqual({Path(path).parent.name for path in packages},
                         {"oaw-evidence", "oaw-wiki", "oaw-improve"})
        for path in packages:
            with self.subTest(path=path):
                self.assertEqual(validator.lint_skill_file(path), [])

    def test_policy_uses_one_native_instruction_source_without_startup_scaffolds(self):
        templates = ROOT / "templates"
        self.assertEqual((templates / "CLAUDE.md").read_text(encoding="utf-8").strip(), "@AGENTS.md")
        policy = (templates / "AGENTS.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(policy.splitlines()), 25)
        self.assertNotIn("${", policy)
        for retired in ("AGENT_RULES.md", "AI_CONTEXT.md", "ROADMAP.md", "VERSION.json", ".agents/memory.md"):
            with self.subTest(retired=retired):
                self.assertFalse((templates / retired).exists())
        self.assertEqual({path.name for path in (templates / "docs" / "knowledge").iterdir()},
                         {"index.md", "log.md"})

    def test_v1_mandatory_session_workflows_are_not_shipped(self):
        for path in (ROOT / "templates").rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for retired_rule in ("memory_nudge.py", "do_not_rerun", "4-section report", "self-improving.md", "triggers:"):
                with self.subTest(path=path, rule=retired_rule):
                    self.assertNotIn(retired_rule, text)


if __name__ == "__main__":
    unittest.main()
