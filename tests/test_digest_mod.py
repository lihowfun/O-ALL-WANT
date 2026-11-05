"""The Claude Code mod `mods/oaw-digest-monitor` against the catalog engine it draws.

The mod's own behaviour is tested by `claude plugin test mods/oaw-digest-monitor`
(TypeScript, needs the Claude Code CLI). These standard-library tests keep the
contract between the two from drifting where the gate can see it: the view
schema, the files view.json is derived from, every pipeline action, the keys the
mod reads, the packaging, and that no local path or identity ships with it.
"""

import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog_core  # noqa: E402
import oaw_status  # noqa: E402

MOD = ROOT / "mods" / "oaw-digest-monitor"
MODEL = MOD / "hooks" / "model.ts"
FIXTURE = MOD / "tests" / "fixtures.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fixture_view() -> dict:
    text = read(FIXTURE)
    start = text.index("export const VIEW = ") + len("export const VIEW = ")
    end = text.rindex(" as const")
    return json.loads(text[start:end])


def minimal_view() -> dict:
    return catalog_core.build_view({"registry": {"foods": {"x": {
        "id": "x", "display": "x", "origin": "url", "source": {"kind": "repo", "url": "https://github.com/a/b"}}}}})


class DigestModPackagingTests(unittest.TestCase):
    def test_manifest_hooks_and_types_are_where_the_engine_looks(self):
        manifest = json.loads(read(MOD / ".claude-plugin" / "plugin.json"))
        self.assertEqual(manifest["name"], MOD.name)
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["license"], "MIT")
        self.assertIn("MIT License", read(ROOT / "LICENSE"))
        self.assertTrue((MOD / manifest["types"]).is_file())
        hooks = json.loads(read(MOD / "hooks" / "hooks.json"))
        self.assertEqual(len(hooks["modules"]), 1)
        self.assertTrue((MOD / "hooks" / hooks["modules"][0]).is_file())
        for field in ("project", "oawCheckout", "python", "motion"):
            self.assertIn(field, manifest["userConfig"])

    def test_repository_marketplace_lists_the_mod(self):
        marketplace = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertIn(MOD.name, entries)
        source = (ROOT / entries[MOD.name]["source"]).resolve()
        self.assertEqual(source, MOD.resolve())

    def test_nothing_local_ships_with_the_mod(self):
        local = re.compile(r"/home/|/mnt/|/Users/|[A-Za-z]:\\\\Users|noreply\.github|@[a-z0-9-]+\.(?:org|com)\.tw")
        for path in MOD.rglob("*"):
            if path.is_file() and ".claude-plugin/types" not in path.as_posix():
                self.assertIsNone(local.search(read(path)), path.relative_to(ROOT).as_posix())


class DigestModContractTests(unittest.TestCase):
    def test_view_schema_matches_the_engine(self):
        match = re.search(r"export const VIEW_SCHEMA = '([^']+)'", read(MODEL))
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), catalog_core.VIEW_SCHEMA)
        self.assertEqual(match.group(1), oaw_status.VIEW_SCHEMA)

    def test_view_sources_match_the_status_cli(self):
        match = re.search(r"export const VIEW_SOURCES = \[([^\]]+)\]", read(MODEL))
        self.assertIsNotNone(match)
        self.assertEqual(tuple(re.findall(r"'([^']+)'", match.group(1))), oaw_status.VIEW_SOURCES)

    def test_every_pipeline_action_has_a_handler(self):
        model = read(MODEL)
        for action_id, spec in catalog_core.PIPELINE_ACTIONS.items():
            with self.subTest(action=action_id):
                if spec["where"] == "terminal":
                    self.assertIn("action.where === 'terminal'", model)
                else:
                    self.assertIn(f"case '{spec['endpoint']}':", model)

    def test_the_keys_the_mod_reads_are_the_ones_build_view_writes(self):
        view = minimal_view()
        food = view["foods"][0]
        pipeline = food["pipeline"]
        model = read(MODEL)
        for key in ("stage", "stage_label_zh", "state", "state_zh", "stages", "waiting_on", "waiting_zh", "note_zh",
                    "actions", "blocker"):
            self.assertIn(key, pipeline)
            self.assertIn(f"p.{key}", model)
        for key in ("where_zh", "basis_zh", "if_ignored_zh", "unknown_zh"):
            self.assertIn(key, pipeline["blocker"])
            self.assertIn(f"b.{key}", model)
        for key in ("headline", "symbol", "label_zh", "level"):
            self.assertIn(key, food["verdict"])
        for key in ("stages", "symbols", "states_zh", "legend", "live_stages", "automation_zh"):
            self.assertIn(key, view["pipeline"])
            self.assertIn(f"pipeline.{key}", model)
        for key in ("submitted", "tasted", "measured", "absorbed_parts"):
            self.assertIn(key, view["funnel"])
        for action in pipeline["actions"]:
            self.assertTrue({"id", "endpoint", "where", "label_zh", "params"} <= set(action))

    def test_the_mod_fixture_still_has_the_engine_shape(self):
        fixture = fixture_view()
        self.assertEqual(fixture["schema"], catalog_core.VIEW_SCHEMA)
        self.assertEqual(fixture["pipeline"]["order"], list(catalog_core.PIPELINE_ORDER))
        engine_keys = set(minimal_view()["foods"][0]["pipeline"])
        for food in fixture["foods"]:
            with self.subTest(food=food["id"]):
                self.assertLessEqual({"stage", "state", "stages", "waiting_on", "actions", "blocker"}, set(food["pipeline"]))
                self.assertLessEqual(set(food["pipeline"]), engine_keys)

    def test_live_stages_written_by_a_taste_are_drawn_on_the_tract(self):
        self.assertTrue(set(catalog_core.LIVE_STAGES.values()) <= set(catalog_core.PIPELINE_ORDER))


if __name__ == "__main__":
    unittest.main()
