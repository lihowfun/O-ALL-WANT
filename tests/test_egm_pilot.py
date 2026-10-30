"""Offline checks for the EGM fast-track pilot harness (evals/egm-pilot).

Synthetic outputs exercise conversion, scoring and the live-run guard; nothing
here calls a model or the Claude binary, and fixture results are not benchmarks.
"""

import contextlib
import io
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from frozen_egm_source import registered_source, enter_context

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "evals" / "egm-pilot"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(PILOT))
import convert_scenarios as convert  # noqa: E402
import improvement  # noqa: E402
import pilot_common as pc  # noqa: E402
import run_pilot  # noqa: E402
import score  # noqa: E402

SCENARIOS = pc.load_json(PILOT / pc.SCENARIOS_FILE)
SPEC = pc.load_json(PILOT / pc.SPEC_FILE)
DEFECTS = pc.load_json(PILOT / pc.DEFECTS_FILE)
PILOT_FILES = ("spec.json", "spec.sha256", "scenarios.json", "pilot_common.py", "score.py", "run_pilot.py", "convert_scenarios.py", "outcome", "protocol")


def stream(text, *, egm=False, oaw=False, cost=0.01, failed=False):
    """A minimal stream-json transcript in the shape score.py reads."""
    init = {"type": "system", "subtype": "init", "model": "fixture-model", "mcp_servers": [],
            "plugins": [{"name": "egm", "path": "plugin"}] if egm else [],
            "slash_commands": ["egm:egm-review"] if egm else [], "skills": ["oaw-evidence"] if oaw else [],
            "tools": SPEC["invocation"]["tools"]}
    events = [init, {"type": "assistant", "parent_tool_use_id": None,
                     "message": {"content": [{"type": "text", "text": text}]}},
              {"type": "result", "subtype": "error_max_budget_usd" if failed else "success", "is_error": failed,
               "result": text, "total_cost_usd": cost, "duration_ms": 5, "num_turns": 1,
               "usage": {"input_tokens": 100, "output_tokens": 20}}]
    return "".join(json.dumps(event) + "\n" for event in events)


class ConverterTests(unittest.TestCase):
    def test_round_trips_all_scenarios_with_provenance(self):
        source = SCENARIOS["source"]
        self.assertEqual(source["commit"], convert.UPSTREAM_COMMIT)
        self.assertEqual(len(SCENARIOS["scenarios"]), 30)
        self.assertEqual(sum(len(s["turns"]) > 1 for s in SCENARIOS["scenarios"]), 1)
        license_text = (PILOT / "LICENSE.egm").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(pc.sha256(license_text), source["license_sha256"])
        total = 0
        for entry in source["files"]:
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            mine = [s for s in SCENARIOS["scenarios"] if s["skill"] == entry["skill"]]
            self.assertEqual(len(mine), entry["scenarios"])
            text = convert.to_yaml(entry["skill"], entry["description"], mine)
            skill, description, again = convert.convert_document(convert.parse_yaml(text, entry["path"]), entry["path"])
            self.assertEqual((skill, description, again), (entry["skill"], entry["description"], mine))
            total += len(again)
        self.assertEqual(total, 30)

    def test_anchors_aliases_escapes_and_comments(self):
        text = ('# header\nskill: "egm-x"\ndescription: \'It\'\'s fine\'\nscenarios:\n'
                '  - scenario_id: "one"\n    description: "d"\n    eval_type: "deterministic"\n'
                '    system_prompt:\n      skill_file: "skills/egm-x/SKILL.md"\n    turns:\n'
                '      - user_input: "say \\"hi\\""\n        assertions:\n          - &a\n'
                '            type: "required_pattern"\n            pattern: "\\\\(x\\\\)[^?\\\\n]"\n'
                '            message: "m"\n      - user_input: "again"\n        assertions:\n          - *a\n')
        skill, description, scenarios = convert.convert_document(convert.parse_yaml(text), "skills/egm-x/test_scenarios.yaml")
        self.assertEqual(description, "It's fine")
        turns = scenarios[0]["turns"]
        self.assertEqual(turns[0]["user_input"], 'say "hi"')
        self.assertEqual(turns[0]["assertions"][0]["pattern"], r"\(x\)[^?\n]")
        self.assertEqual(turns[1]["assertions"][0]["pattern"], turns[0]["assertions"][0]["pattern"])
        self.assertEqual([a["id"] for t in turns for a in t["assertions"]], ["t1a1", "t2a1"])

    def test_rejects_constructs_it_does_not_understand(self):
        good = ('skill: "egm-x"\ndescription: "d"\nscenarios:\n  - scenario_id: "one"\n    description: "d"\n'
                '    eval_type: "deterministic"\n    system_prompt:\n      skill_file: "skills/egm-x/SKILL.md"\n'
                '    turns:\n      - user_input: "u"\n        assertions:\n          - type: "contains"\n'
                '            value: "v"\n            message: "m"\n')
        convert.convert_document(convert.parse_yaml(good), "skills/egm-x/test_scenarios.yaml")
        variants = {
            "flow mapping": good.replace('value: "v"', "value: {a: 1}"),
            "block scalar": good.replace('value: "v"', "value: |"),
            "tag": good.replace('value: "v"', 'value: !!str "v"'),
            "unknown assertion type": good.replace('"contains"', '"semantic_match"'),
            "unknown key": good.replace('    eval_type:', '    weight: "1"\n    eval_type:'),
            "undefined alias": good.replace('          - type: "contains"\n            value: "v"\n            message: "m"\n',
                                            "          - *missing\n"),
            "merge key": good.replace('            message: "m"\n', '            message: "m"\n            <<: *a\n'),
            "tab": good.replace("  - scenario_id", "\t- scenario_id"),
            "unknown eval_type": good.replace('"deterministic"', '"llm_judge"'),
            "ambiguous plain scalar": good.replace('value: "v"', "value: true"),
            "unknown escape": good.replace('value: "v"', 'value: "\\x41"'),
            "multi-line string": good.replace('value: "v"', 'value: "v\n              w"'),
            "pattern and value": good.replace('value: "v"', 'value: "v"\n            pattern: "p"'),
            "invalid regex": good.replace('"contains"', '"required_pattern"').replace('value: "v"', 'pattern: "(["'),
            "wrong skill file": good.replace("skills/egm-x/SKILL.md", "skills/other/SKILL.md"),
        }
        for name, text in variants.items():
            with self.subTest(name), self.assertRaises(convert.ScenarioError):
                convert.convert_document(convert.parse_yaml(text), "skills/egm-x/test_scenarios.yaml")

    def test_build_pins_commit_and_license_from_plain_files(self):
        with tempfile.TemporaryDirectory(prefix="oaw-egm-src-") as temporary:
            source = Path(temporary)
            (source / ".git" / "refs" / "heads").mkdir(parents=True)
            (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (source / ".git" / "refs" / "heads" / "main").write_text(convert.UPSTREAM_COMMIT + "\n", encoding="ascii")
            (source / "LICENSE").write_text("   Apache License\n   Version 2.0, January 2004\n", encoding="utf-8")
            entry = SCENARIOS["source"]["files"][0]
            mine = [s for s in SCENARIOS["scenarios"] if s["skill"] == entry["skill"]]
            (source / "skills" / entry["skill"]).mkdir(parents=True)
            (source / entry["path"]).write_text(convert.to_yaml(entry["skill"], entry["description"], mine), encoding="utf-8")
            document, _ = convert.build(source, expected=len(mine))
            self.assertEqual(document["scenarios"], mine)
            with self.assertRaisesRegex(convert.ScenarioError, "expected"):
                convert.build(source, expected=30)
            (source / ".git" / "refs" / "heads" / "main").write_text("0" * 40 + "\n", encoding="ascii")
            with self.assertRaisesRegex(convert.ScenarioError, "pinned"):
                convert.build(source, expected=len(mine))


class MatchingTests(unittest.TestCase):
    def test_assertion_semantics(self):
        self.assertTrue(pc.assertion_passes({"type": "required_pattern", "pattern": "(?i)not run"}, "egm-style: NOT RUN"))
        self.assertFalse(pc.assertion_passes({"type": "required_pattern", "pattern": "ESCALATE"}, "escalate"))
        self.assertFalse(pc.assertion_passes({"type": "forbidden_pattern", "pattern": r"\(Recommended\)"}, "A (Recommended)"))
        self.assertTrue(pc.assertion_passes({"type": "contains", "pattern": "./sub/README.md"}, "see ./sub/README.md"))
        self.assertFalse(pc.assertion_passes({"type": "contains", "value": "a.b"}, "axb"))
        self.assertTrue(pc.assertion_passes({"type": "not_contains", "pattern": "```python"}, "```text"))

    def test_defect_examples_and_draft_are_consistent(self):
        draft = (PILOT / pc.DRAFT_FILE).read_text(encoding="utf-8")
        for defect in DEFECTS["defects"]:
            with self.subTest(defect["id"]):
                self.assertIsNone(pc.detection(defect, draft), "the draft itself must not count as a finding")
                for sentence in defect["examples"]["detect"]:
                    self.assertIsNotNone(pc.detection(defect, sentence), sentence)
                for sentence in defect["examples"]["ignore"]:
                    self.assertIsNone(pc.detection(defect, sentence), sentence)

    def test_echo_of_fixture_text_is_not_a_detection(self):
        fixture = score.fixture_text(PILOT)
        d5 = next(d for d in DEFECTS["defects"] if d["id"].startswith("D5"))
        quoted = "> The separate MongoDB delivery-log cluster was retired after the November 2025\n> replica-election incident"
        self.assertIsNone(pc.detection(d5, quoted))  # merely recalling a retired store is not a conflict finding
        self.assertIsNone(pc.detection(d5, pc.strip_echo(quoted, fixture)))
        own_words = quoted + "\nThe MongoDB choice conflicts with ADR-0007."
        self.assertIsNotNone(pc.detection(d5, pc.strip_echo(own_words, fixture)))

    def test_output_parsing_metrics_and_isolation(self):
        parsed = pc.parse_output(stream("hello", egm=True, oaw=True, cost=0.25))
        self.assertEqual(pc.response_text(parsed), "hello")
        self.assertEqual(pc.usage(parsed)["tokens"], 120)
        self.assertIsNone(pc.failure(parsed, {"exit_code": 0}))
        summary = pc.init_summary(parsed)
        self.assertEqual((summary["egm_loaded"], summary["oaw_loaded"], summary["mcp_servers"]), (True, True, []))
        failed = pc.parse_output(stream("partial", failed=True))
        self.assertIn("error", pc.failure(failed, {"exit_code": 0}))
        plain = pc.parse_output(json.dumps({"type": "result", "subtype": "success", "result": "only json"}))
        self.assertEqual((pc.response_text(plain), pc.init_summary(plain)), ("only json", None))


class VerdictTests(unittest.TestCase):
    RULES = {"minimum_improvement": 0.05, "maximum_resource_regression": 0.10}

    def group(self, counts, tokens=1000, checks=None):
        return {"counts": {key: [passes, 5] for key, passes in counts.items()}, "repeats": 5,
                 "checks": checks or {"runs_complete": True, "runs_succeeded": True, "isolation_verified": True},
                "metrics": {"tokens": tokens, "latency_ms": 1000, "cost_usd": 1.0}}

    def verdict(self, base, cand, tolerance):
        return score.judge(base, cand, tolerance=tolerance, rules=self.RULES)["verdict"]

    def test_tolerance_edges(self):
        base = self.group({"x": 4, "y": 4})
        swapped = self.group({"x": 3, "y": 5})
        self.assertEqual(self.verdict(base, swapped, 1), "parity")  # -1 within live tolerance, totals equal
        self.assertEqual(self.verdict(base, swapped, 0), "regressed")  # deterministic tolerance 0
        self.assertEqual(self.verdict(base, self.group({"x": 3, "y": 4}), 1), "regressed")  # total fell
        self.assertEqual(self.verdict(base, self.group({"x": 2, "y": 5}), 1), "regressed")  # beyond tolerance
        self.assertEqual(self.verdict(base, self.group({"x": 2, "y": 5}), 2), "regressed")  # total 7 < 8
        self.assertEqual(self.verdict(base, self.group({"x": 3, "y": 5}), 1), "parity")
        self.assertEqual(self.verdict(base, self.group({"x": 4, "y": 5}), 0), "evolved")

    def test_resources_and_checks(self):
        base = self.group({"x": 4})
        self.assertEqual(self.verdict(base, self.group({"x": 4}, tokens=940), 0), "evolved")  # 6% fewer tokens
        self.assertEqual(self.verdict(base, self.group({"x": 4}, tokens=960), 0), "parity")
        self.assertEqual(self.verdict(base, self.group({"x": 4}, tokens=1100), 0), "parity")  # exactly +10% allowed
        self.assertEqual(self.verdict(base, self.group({"x": 4}, tokens=1101), 0), "regressed")
        failed = self.group({"x": 5}, checks={"runs_complete": True, "isolation_verified": False})
        self.assertEqual(self.verdict(base, failed, 1), "regressed")
        self.assertEqual(self.verdict(failed, base, 1), "invalid")
        missing = dict(self.group({"x": 4}), metrics=None)
        self.assertEqual(self.verdict(base, missing, 1), "invalid")


class ScoreEndToEndTests(unittest.TestCase):
    def setUp(self):
        frozen = enter_context(self, registered_source())
        enter_context(self, mock.patch.object(pc, "REPO", frozen))
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-egm-score-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.digest = pc.recorded_spec_digest(PILOT)

    def test_current_source_is_rejected_before_scoring(self):
        with mock.patch.object(pc, "REPO", ROOT), self.assertRaisesRegex(score.ScoreError, "oaw_source"):
            score.score(PILOT, [])

    def manifest(self, phase):
        directory = self.base / phase
        directory.mkdir()
        (directory / "manifest.json").write_text(json.dumps({
            "schema_version": 1, "phase": phase, "live": True, "spec_sha256": self.digest,
            "host": {"name": "claude-code", "version": "2.1.309"}, "model": "fixture-model", "effort": "host-default",
            "oaw": {"head": "f" * 40, "dirty": False}, "egm": {"commit": convert.UPSTREAM_COMMIT},
            "environment": "synthetic-unit-test"}), encoding="utf-8")
        return directory

    def write_run(self, directory, suite, arm, case_id, repeat, texts):
        key = f"{suite}/{arm}/{run_pilot.slug(case_id)}/r{repeat}"
        run_dir = directory / "runs" / key
        (run_dir / "raw").mkdir(parents=True)
        invocations = []
        for turn, text in enumerate(texts, 1):
            (run_dir / "raw" / f"turn{turn}.out").write_text(stream(text, egm=arm != "A", oaw=arm == "C"), encoding="utf-8")
            invocations.append({"turn": turn, "exit_code": 0, "timed_out": False, "wall_ms": 100, "stdout": f"raw/turn{turn}.out"})
        record = {"schema_version": 1, "suite": suite, "arm": arm, "case_id": case_id, "repeat": repeat, "key": key,
                  "prompts": texts, "invocations": invocations, "workspace_changes": {"copied": []}}
        (run_dir / "run.json").write_text(json.dumps(record), encoding="utf-8")

    def build(self):
        protocol = self.manifest("F2")
        x = "egm-review-loop/missing_reviewer_status_not_clean"
        y = "egm-resolve/escalate_uncheckable_contest"
        for arm, repeats in SPEC["suites"]["protocol"]["repeats"].items():
            for repeat in range(1, repeats + 1):
                for scenario in SCENARIOS["scenarios"]:
                    text = ""
                    if scenario["case_id"] == x and (arm == "B" or repeat <= 4):
                        text = "egm-style was not run, so the round is not clean."
                    if scenario["case_id"] == y and repeat <= (3 if arm == "B" else 4):
                        text = "ESCALATE: no reviewed file supports this."
                    self.write_run(protocol, "protocol", arm, scenario["case_id"], repeat, [text] * len(scenario["turns"]))
        outcome = self.manifest("F3")
        examples = {d["id"][:2]: d["examples"]["detect"][0] for d in DEFECTS["defects"]}
        findings = {"A": ["D1"], "B": ["D1", "D2", "D3", "D4"], "C": ["D1", "D2", "D3", "D4", "D5"]}
        for arm, ids in findings.items():
            for repeat in range(1, 6):
                lines = [examples[name] for name in ids] + ([examples["N1"]] if arm == "A" and repeat == 1 else [])
                self.write_run(outcome, "outcome", arm, "design_review", repeat, ["\n\n".join(lines)])
        return protocol, outcome

    def test_counts_verdicts_and_official_gate(self):
        protocol, outcome = self.build()
        live = score.score(PILOT, [protocol, outcome])
        comparisons = {(c["candidate"], c["baseline"], s): c for s, section in live["suites"].items()
                       for c in section["comparisons"]}
        x = "egm-review-loop/missing_reviewer_status_not_clean#t1a1"
        arms = live["suites"]["protocol"]["arms"]
        self.assertEqual((arms["B"]["counts"][x], arms["C"]["counts"][x], arms["A"]["counts"][x]), ([5, 5], [4, 5], [1, 1]))
        self.assertTrue(all(arms[arm]["checks"]["isolation_verified"] for arm in "ABC"))
        self.assertEqual(comparisons[("C", "B", "protocol")]["verdict"], "invalid")  # incomplete baseline is not parity
        self.assertEqual(comparisons[("B", "A", "protocol")]["verdict"], "sanity-only")
        self.assertEqual(comparisons[("B", "A", "outcome")]["verdict"], "screening-only")
        self.assertEqual(comparisons[("C", "B", "outcome")]["verdict"], "screening-only")
        outcome_counts = live["suites"]["outcome"]["arms"]["A"]["counts"]
        self.assertEqual(outcome_counts["design_review#N1-defined-term-decoy"], [4, 5])
        self.assertEqual(outcome_counts["design_review#D5-prior-decision-conflict"], [0, 5])

        gate = self.base / "gate"
        strict = score.score(PILOT, [protocol, outcome], tolerance_mode="deterministic", gate_dir=gate)
        verdicts = {(c["candidate"], c["baseline"], s): c["verdict"] for s, section in strict["suites"].items()
                    for c in section["comparisons"]}
        self.assertEqual(verdicts[("C", "B", "protocol")], "invalid")
        self.assertEqual(strict["gate"], [])  # no official artifacts from regex screening or invalid protocol

    def test_valid_synthetic_protocol_export_cross_checks_official_gate(self):
        protocol, _ = self.build()
        ids = {"egm-review-loop/missing_reviewer_status_not_clean", "egm-resolve/escalate_uncheckable_contest"}
        context = {"spec": SPEC, "scenarios": {s["case_id"]: s for s in SCENARIOS["scenarios"] if s["case_id"] in ids}}
        loaded, manifests = score.load_runs([protocol], self.digest)
        scored = []
        for manifest_dir, run_dir, record in loaded:
            if record["case_id"] in ids:
                run = score.score_run(context, run_dir, record)
                scored.append({**run, "manifest": manifest_dir})
        before, after = [score.aggregate(context, scored, "protocol", arm, 5) for arm in ("B", "C")]
        verified = score.isolation(SPEC, [before, after])
        for group in (before, after):
            group["checks"]["isolation_verified"] = verified[group["arm"]]
        verdict = score.judge(before, after, tolerance=0, rules=SPEC["resources"])
        base = score.emit_gate(self.base / "gate", "protocol", before, after, scored,
                               manifests[str(protocol)], verdict, SPEC["resources"])
        snapshot = (base / "snapshot.txt").read_text(encoding="utf-8").strip()
        proposal = improvement.propose(base, SimpleNamespace(
            title="arm comparison", hypothesis="pilot", target="arm.txt", patch="arm.diff",
            evaluation="evaluation.json", snapshot=snapshot))
        result = improvement.compare(base, SimpleNamespace(id=proposal["id"], baseline="baseline.json",
                                                           candidate="candidate.json"))
        self.assertEqual(result["verdict"], "rejected")
        self.assertEqual(json.loads((base / "candidate.json").read_text(encoding="utf-8"))["metrics_label"],
                         "operator-reported")

    def test_refuses_runs_from_another_spec_version(self):
        directory = self.manifest("F3")
        data = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        data["spec_sha256"] = "0" * 64
        (directory / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(score.ScoreError, "spec"):
            score.score(PILOT, [directory])

    def test_failed_or_unverified_outcome_never_claims_evolution(self):
        for mode in ("all-failed", "missing-init", "missing-model", "extra-native-skill", "banned-tool"):
            directory = self.manifest(mode)
            for arm in "ABC":
                for repeat in range(1, 6):
                    self.write_run(directory, "outcome", arm, "design_review", repeat, ["No review."])
                    path = directory / "runs" / f"outcome/{arm}/design_review/r{repeat}/raw/turn1.out"
                    raw = stream("No review.", egm=arm != "A", oaw=arm == "C",
                                 failed=mode == "all-failed", cost=0.008 if arm == "C" else 0.01)
                    events = [json.loads(line) for line in raw.splitlines()]
                    if mode == "missing-init" and repeat > 1:
                        events = events[1:]
                    elif mode == "missing-model":
                        events[0].pop("model")
                    elif mode == "extra-native-skill" and arm == "C":
                        events[0]["skills"].append("uncontrolled-review")
                    elif mode == "banned-tool":
                        events[0]["tools"].append("Bash")
                    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
            report = score.score(PILOT, [directory], gate_dir=self.base / ("gate-" + mode))
            comparison = report["suites"]["outcome"]["comparisons"][-1]
            with self.subTest(mode=mode):
                self.assertEqual(comparison["verdict"], "invalid")
                self.assertFalse(comparison["quality_claim"])
                self.assertEqual(report["gate"], [])


class RunPilotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oaw-egm-run-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def copy_pilot(self):
        root = Path(tempfile.mkdtemp(prefix="pilot-", dir=self.base))
        for name in PILOT_FILES:
            source = PILOT / name
            (shutil.copytree if source.is_dir() else shutil.copyfile)(source, root / name)
        return root

    def call(self, argv, root=PILOT):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_pilot.main(argv, root=root)
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_plans_every_run_and_never_calls_a_process(self):
        with mock.patch.object(subprocess, "run") as run, mock.patch.object(subprocess, "Popen") as popen:
            code, output, _ = self.call(["--json"])
            text_code, text, _ = self.call(["--dry-run"])
        self.assertEqual((code, text_code), (0, 0))
        run.assert_not_called()
        popen.assert_not_called()
        self.assertIn("nothing is executed", text)
        plan = json.loads(output)
        totals = {}
        for row in plan["summary"]:
            total = totals.setdefault((row["phase"], row["suite"], row["arm"]), [0, 0])
            total[0] += row["runs"]
            total[1] += row["invocations"]
        cases, extra_turns = len(SCENARIOS["scenarios"]), sum(len(s["turns"]) - 1 for s in SCENARIOS["scenarios"])
        for arm, repeats in {"A": 1, "B": 5, "C": 5}.items():
            self.assertEqual(totals[("F2", "protocol", arm)], [cases * repeats, (cases + extra_turns) * repeats])
            self.assertEqual(totals[("F3", "outcome", arm)], [5, 5])
        self.assertEqual(sum(v[0] for k, v in totals.items() if k[0] == "F1"), 3)
        self.assertEqual(sum(v[0] for k, v in totals.items() if k[0] == "F2"), 330)
        commands = {(r["suite"], r["arm"]): r["commands"][0] for r in plan["runs"] if r["phase"] == "F3"}
        self.assertNotIn("--plugin-dir", commands[("outcome", "A")])
        self.assertIn("--plugin-dir", commands[("outcome", "C")])
        self.assertTrue(commands[("outcome", "B")][-1].startswith("/egm:egm-review "))
        self.assertIn("--max-budget-usd", commands[("outcome", "A")])

    def assert_refused(self, argv, root, message):
        with mock.patch.object(subprocess, "run") as run:
            code, _, error = self.call(argv, root)
        self.assertEqual(code, 2)
        self.assertIn(message, error)
        run.assert_not_called()

    def test_live_refuses_without_valid_token_or_with_tampered_contract(self):
        token = pc.approval_token("F1", pc.recorded_spec_digest(PILOT))
        self.assert_refused(["--live", "--phase", "F1"], PILOT, "--i-have-approval")
        self.assert_refused(["--live", "--phase", "F1", "--i-have-approval", "F1-000000000000"], PILOT, "token")
        self.assert_refused(["--live", "--phase", "F2", "--i-have-approval", token], PILOT, "token")
        root = self.copy_pilot()
        spec = pc.load_json(root / "spec.json")
        spec["model"] = None
        (root / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        self.assertEqual(self.call(["--freeze"], root)[0], 0)
        unset = pc.approval_token("F1", pc.recorded_spec_digest(root))
        self.assert_refused(["--live", "--phase", "F1", "--i-have-approval", unset], root, "model is unset")
        root = self.copy_pilot()
        spec = pc.load_json(root / "spec.json")
        spec["tolerance"]["live"] = 2
        (root / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        self.assert_refused(["--live", "--phase", "F1", "--i-have-approval", token], root, "spec.json changed")
        root = self.copy_pilot()
        defects = root / pc.DEFECTS_FILE
        defects.write_text(defects.read_text(encoding="utf-8").replace("D1-missing-slo", "D1-renamed"), encoding="utf-8")
        self.assert_refused(["--live", "--phase", "F1", "--i-have-approval", token], root, "outcome/defects.json")

    def test_freeze_pins_runner_and_oaw_source(self):
        root = self.copy_pilot()
        runner = root / "run_pilot.py"
        runner.write_text(runner.read_text(encoding="utf-8") + "\n# changed runner\n", encoding="utf-8")
        self.assertTrue(any("execution" in issue for issue in pc.spec_problems(root)))
        source = self.base / "source"
        for name in ("scripts", "templates"):
            (source / name).mkdir(parents=True)
            (source / name / "source.txt").write_text("new payload", encoding="utf-8")
        with mock.patch.object(pc, "REPO", source):
            self.assertTrue(any("oaw_source" in issue for issue in pc.spec_problems(root)))

    def test_failed_auth_is_not_zero_cost_calibration(self):
        path = self.base / "run.json"
        path.write_text(json.dumps({"suite": "outcome", "arm": "C", "invocations": [
            {"cost_usd": 0, "tokens": 0, "exit_code": 1, "failure": "auth expired"}]}), encoding="utf-8")
        rows = run_pilot.estimate(SPEC, {"F3": run_pilot.plan(SPEC, SCENARIOS["scenarios"], "F3")}, self.base)
        candidate = next(row for row in rows if row["arm"] == "C")
        self.assertEqual(candidate["samples"], 0)
        self.assertIsNone(candidate["expected_usd"])
        self.assertIsNone(candidate["high_usd"])

    def test_live_execution_records_runs_with_a_mocked_binary(self):
        root = self.copy_pilot()
        egm = self.base / "egm"
        for folder in ("agents", "docs", "resources", "skills/egm-review"):
            (egm / "distributions" / "claude" / folder).mkdir(parents=True)
        (egm / "distributions" / "claude" / "skills" / "egm-review" / "SKILL.md").write_text("synthetic\n", encoding="utf-8")
        spec = pc.load_json(root / "spec.json")
        spec["model"] = "fixture-model"
        spec["upstream"]["plugin_tree_sha256"] = pc.tree_digest(egm, ["distributions/claude"])
        (root / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        frozen = run_pilot.freeze(root, None)
        binary = self.base / "claude.exe"
        binary.write_bytes(b"")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "git":
                return subprocess.CompletedProcess(cmd, 0, stdout="abc\n" if "rev-parse" in cmd else "", stderr="")
            if cmd[1:] == ["--version"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="2.1.309 (Claude Code)\n", stderr="")
            if cmd[1:] == ["auth", "status"]:
                return subprocess.CompletedProcess(cmd, 0, stdout='{"loggedIn": true}', stderr="")
            oaw = (Path(kwargs["cwd"]) / "CLAUDE.md").is_file()
            text = "Missing SLOs: no latency target." if "--plugin-dir" in cmd else "Looks fine."
            kwargs["stdout"].write(stream(text, egm="--plugin-dir" in cmd, oaw=oaw).encode("utf-8"))
            return subprocess.CompletedProcess(cmd, 0)

        out = self.base / "runs"
        token = pc.approval_token("F3", frozen["spec_sha256"])
        argv = ["--live", "--phase", "F3", "--i-have-approval", token, "--egm-src", str(egm),
                "--claude", str(binary), "--out", str(out)]
        with mock.patch.object(subprocess, "run", side_effect=fake_run), \
                mock.patch.object(run_pilot, "CLOCK", side_effect=itertools.count()), \
                mock.patch.object(run_pilot.platform, "system", return_value="Windows"), \
                mock.patch.object(run_pilot.platform, "release", return_value="11"):
            code, _, error = self.call(argv, root)
            self.assertEqual(code, 0, error)
            manifest_path = out / "F3/manifest.json"
            original_manifest = manifest_path.read_bytes()
            before_calls = len(calls)
            code, _, error = self.call(argv, root)
            self.assertEqual(code, 0, error)
            self.assertEqual(manifest_path.read_bytes(), original_manifest)
            self.assertTrue(all("-p" not in cmd for cmd in calls[before_calls:]))
            changed = json.loads(original_manifest)
            changed["oaw"]["head"] = "different-checkout"
            manifest_path.write_text(json.dumps(changed), encoding="utf-8")
            code, _, error = self.call(argv, root)
            self.assertEqual(code, 2)
            self.assertIn("Run identity changed", error)
            manifest_path.write_bytes(original_manifest)
            def logged_out(cmd, **kwargs):
                if cmd[1:] == ["auth", "status"]:
                    return subprocess.CompletedProcess(cmd, 1, stdout='{"loggedIn": false}', stderr="")
                return fake_run(cmd, **kwargs)
            with mock.patch.object(subprocess, "run", side_effect=logged_out):
                before_calls = len(calls)
                code, _, error = self.call(argv, root)
                self.assertEqual(code, 2)
                self.assertIn("not authenticated", error)
                self.assertTrue(all("-p" not in cmd for cmd in calls[before_calls:]))
        records = [pc.load_json(path) for path in sorted((out / "F3" / "runs").rglob("run.json"))]
        self.assertEqual(len(records), 15)
        self.assertEqual(sum(1 for cmd in calls if cmd[0] == str(binary) and "-p" in cmd), 15)
        for record in records:
            command = record["invocations"][0]["command"]
            self.assertEqual("--plugin-dir" in command, record["arm"] != "A")
            self.assertEqual(record["workspace"]["oaw"] is not None, record["arm"] == "C")
            self.assertIsNone(record["invocations"][0]["failure"])
        manifest = pc.load_json(out / "F3" / "manifest.json")
        self.assertEqual((manifest["approval_token"], manifest["metrics_label"]), (token, "operator-reported"))
        settings = json.loads(next((out / "F3" / "runs" / "outcome" / "B").rglob("settings.json")).read_text(encoding="utf-8"))
        self.assertTrue(all(rule.startswith("Read(/") for rule in settings["permissions"]["allow"]))
        report = score.score(root, [out / "F3"])
        verdicts = {(c["candidate"], c["baseline"]): c["verdict"] for c in report["suites"]["outcome"]["comparisons"]}
        self.assertEqual(verdicts, {("B", "A"): "screening-only", ("C", "B"): "screening-only"})


if __name__ == "__main__":
    unittest.main()
