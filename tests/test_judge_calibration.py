"""Offline JUDGE contract; V3 fixtures retain labels/counts only, never answers or notes.

Source: OAW-records/records/digestion-2026-11-07/validation/v3/.
score.json preserves archived per-grader metrics, omitting the admission-like reading.
The 24 answers are variants of four questions, not 24 independent cases.
"""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/judge_calibration"
spec = importlib.util.spec_from_file_location("judge_calibration_test", ROOT / "scripts/judge_calibration.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)


class JudgeCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.gold, self.ids = judge.load_gold(FIXTURES / "expected.json")
        self.rows = [json.loads(line) for line in (FIXTURES / "grades-codex-1.jsonl").read_text().splitlines()]

    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = judge.main([str(arg) for arg in args])
        return code, output.getvalue()

    def write_rows(self, directory, rows):
        path = Path(directory) / "candidate.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_four_archived_graders_replay_exactly(self):
        expected = json.loads((FIXTURES / "score.json").read_text())
        self.assertEqual(len(self.gold), 24)
        self.assertEqual(sum(len(entry["labels"] or {}) for entry in self.gold.values()), 116)
        for name, archived in expected.items():
            with self.subTest(grader=name):
                grades, errors = judge.load_grades(FIXTURES / name, self.gold, self.ids)
                self.assertEqual(errors, [])
                metrics = judge.score(self.gold, grades)
                self.assertEqual({field: metrics[field] for field in archived}, archived)
                self.assertEqual(metrics["known_label_cells"], 116)
                self.assertEqual(metrics["graded"], 24)
                self.assertEqual(metrics["abstention"]["coverage"], 1)
                self.assertIsNone(metrics["critical_misses"]["count"])
                self.assertIsNone(metrics["token_cost"]["recorded_tokens"])

    def test_missing_unknown_malformed_and_not_run_reject_whole_candidate(self):
        cases = []
        cases.append(("missing answer", self.rows[1:], "missing valid grades"))
        for name, change, message in (
            ("unknown answer", lambda row: row.update(key="a|unknown|1"), "unknown answer ID"),
            ("missing label", lambda row: row["verdict"]["facts"].pop("q4f1"), "missing label IDs"),
            ("unknown fact", lambda row: row["verdict"]["facts"].update(unknown="present"), "unknown label IDs"),
            ("unknown label", lambda row: row["verdict"]["facts"].update(q4f1="yes"), "unknown label"),
            ("null label", lambda row: row["verdict"]["facts"].update(q4f1=None), "unknown label"),
            ("object label", lambda row: row["verdict"]["facts"].update(q4f1={}), "unknown label"),
            ("null facts", lambda row: row["verdict"].update(facts=None), "facts must be an object"),
            ("null verdict", lambda row: row.update(verdict=None), "malformed verdict"),
            ("no count", lambda row: row["verdict"].pop("wrong_claims"), "wrong_claims"),
            ("null count", lambda row: row["verdict"].update(wrong_claims=None), "wrong_claims"),
            ("negative count", lambda row: row["verdict"].update(wrong_claims=-1), "wrong_claims"),
            ("boolean count", lambda row: row["verdict"].update(wrong_claims=True), "wrong_claims"),
            ("zero tokens", lambda row: row["verdict"].update(_grader_tokens=0), "did not run"),
            ("null tokens", lambda row: row["verdict"].update(_grader_tokens=None), "invalid tokens"),
            ("boolean tokens", lambda row: row["verdict"].update(_grader_tokens=True), "invalid tokens"),
            ("not run", lambda row: row.update(status="not_run"), "did not run"),
            ("usage limit", lambda row: row.update(status="usage_limit"), "did not run"),
            ("error", lambda row: row.update(error="quota exceeded"), "did not run"),
            ("bad key", lambda row: row.update(key="a|q4|0"), "invalid key"),
            ("identity mismatch", lambda row: row.update(rep=2), "disagrees with key"),
            ("boolean rep", lambda row: row.update(rep=True), "disagrees with key"),
            ("bad derived field", lambda row: row.update(coverage="0.5"), "invalid archived coverage"),
            ("unknown schema", lambda row: row.update(labels={}), "unknown grade fields"),
        ):
            rows = copy.deepcopy(self.rows)
            change(rows[0])
            cases.append((name, rows, message))
        cases.extend((("duplicate answer", self.rows + [self.rows[0]], "duplicate answer ID"),
                      ("array row", [[], *self.rows], "grade must be an object"),
                      ("empty file", [], "missing valid grades")))
        with tempfile.TemporaryDirectory() as temporary:
            for name, rows, message in cases:
                with self.subTest(case=name):
                    path = self.write_rows(temporary, rows)
                    code, output = self.run_cli(FIXTURES / "expected.json", path, "--json")
                    result = json.loads(output)["candidates"][0]
                    self.assertEqual((code, result["status"]), (2, "rejected"))
                    self.assertNotIn("metrics", result)
                    self.assertIn(message, " ".join(result["errors"]))

    def test_invalid_json_duplicate_fields_and_unreadable_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.jsonl"
            for text in ('{"key":', '{"key":"a|q1|1","key":"b|q1|1"}', '{"x":NaN}', '\n'):
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    code, output = self.run_cli(FIXTURES / "expected.json", path, "--json")
                    self.assertEqual(code, 2)
                    self.assertNotIn("metrics", json.loads(output)["candidates"][0])
            path.write_bytes(b"\xff")
            self.assertEqual(self.run_cli(FIXTURES / "expected.json", path, "--json")[0], 2)
            self.assertEqual(self.run_cli(FIXTURES / "expected.json", path.with_name("missing"), "--json")[0], 2)

    def test_gold_schema_and_pair_baseline_are_validated(self):
        invalid = [[], {}, {"bad": {"labels": {"x": "present"}}}]
        for mutate in (
            lambda gold: gold["a|q1|1"]["labels"].update(q1f1="unknown"),
            lambda gold: gold["a|q1|1"]["labels"].pop("q1f1"),
            lambda gold: gold["a|q1|1"].update(critical=["missing"]),
            lambda gold: gold["a|q1|1"].update(wrong=True),
            lambda gold: gold["a|q1|1"].update(wrong_at_least=1),
            lambda gold: gold.pop("e|q1|1"),
            lambda gold: gold["f|q1|1"].update(wrong_over_e=0),
            lambda gold: gold["e|q1|1"].update(critical=["q1f1"]),
        ):
            gold = copy.deepcopy(self.gold)
            mutate(gold)
            invalid.append(gold)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gold.json"
            for gold in invalid:
                path.write_text(json.dumps(gold), encoding="utf-8")
                code, output = self.run_cli(path, FIXTURES / "grades-codex-1.jsonl", "--json")
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(output)["candidates"], [])

    def test_confusion_false_credit_critical_misses_and_explicit_abstention(self):
        # A synthetic critical annotation: V3 itself has no adjudicated critical labels.
        gold = {"a|q|1": {"labels": {"p": "present", "a": "absent", "c": "contradicted", "u": "present"},
                            "critical": ["p", "c", "u"]}}
        grades = {"a|q|1": {"facts": {"p": "absent", "a": "present", "c": "contradicted", "u": "unknown"},
                              "wrong_claims": 0}}
        with tempfile.TemporaryDirectory() as temporary:
            gold_path = Path(temporary) / "gold.json"
            gold_path.write_text(json.dumps(gold), encoding="utf-8")
            path = self.write_rows(temporary, [{"key": key, "verdict": value} for key, value in grades.items()])
            code, output = self.run_cli(gold_path, path, "--json")
        self.assertEqual(code, 0)
        result = json.loads(output)["candidates"][0]["metrics"]
        self.assertEqual(result["confusion"]["present"], {"present": 0, "absent": 1, "contradicted": 0, "unknown": 1})
        self.assertEqual(result["confusion"]["absent"]["present"], 1)
        self.assertEqual(result["confusion"]["contradicted"]["contradicted"], 1)
        self.assertEqual(result["false_credit"]["count"], 1)
        self.assertEqual(result["false_credit"]["cells"][0]["fact"], "a")
        self.assertEqual(result["critical_misses"]["evaluated_cells"], 3)
        self.assertEqual(result["critical_misses"]["count"], 1)
        self.assertEqual(result["critical_misses"]["abstained"], 1)
        self.assertEqual(result["abstention"]["known_rate"], 0.25)
        self.assertEqual(result["abstention"]["coverage"], 0.75)
        self.assertEqual(result["abstention"]["covered_accuracy"], 1 / 3)
        self.assertEqual(len(result["label_errors"]), 2)  # Unknown is an abstention, not a wrong label.
        self.assertEqual(result["label_accuracy_a_to_d"], 0.25)  # Exact matches / all known cells.

    def test_token_totals_and_partial_cost_disclosure(self):
        grades, errors = judge.load_grades(FIXTURES / "grades-codex-1.jsonl", self.gold, self.ids)
        self.assertEqual(errors, [])
        for value in grades.values():
            value["_grader_tokens"] = 10
        result = judge.score(self.gold, grades)["token_cost"]
        self.assertEqual(result, {"recorded_tokens": 240, "recorded_grades": 24, "missing_grades": 0, "complete": True})
        next(iter(grades.values())).pop("_grader_tokens")
        result = judge.score(self.gold, grades)["token_cost"]
        self.assertEqual(result, {"recorded_tokens": 230, "recorded_grades": 23, "missing_grades": 1, "complete": False})

    def test_pair_delta_is_signed_thresholded_and_uses_gold_expectation(self):
        grades, _ = judge.load_grades(FIXTURES / "grades-codex-1.jsonl", self.gold, self.ids)
        grades["e|q1|1"]["wrong_claims"] = 3
        grades["f|q1|1"]["wrong_claims"] = 1
        self.gold["f|q2|1"]["wrong_over_e"] = 3
        result = judge.score(self.gold, grades)
        self.assertEqual(result["planted_wrong_delta_f_minus_e"], [-2, 2, 2, 2])
        self.assertEqual(result["planted_detected_rate"], 0.5)
        self.assertEqual(result["planted_partial_or_better_rate"], 0.75)

    def test_multiple_candidates_json_and_text_report_rejections_without_scores(self):
        with tempfile.TemporaryDirectory() as temporary:
            bad = self.write_rows(temporary, self.rows[1:])
            valid = FIXTURES / "grades-opus-1.jsonl"
            for json_output in (False, True):
                code, output = self.run_cli(FIXTURES / "expected.json", valid, bad,
                                            *(["--json"] if json_output else []))
                self.assertEqual(code, 2)
                if json_output:
                    candidates = json.loads(output)["candidates"]
                    self.assertEqual(candidates[0]["metrics"]["graded"], 24)
                    self.assertNotIn("metrics", candidates[1])
                else:
                    for text in ("no judge installed or approved", "confusion", "critical_misses", "token_cost", "rejected"):
                        self.assertIn(text, output)


if __name__ == "__main__":
    unittest.main()
