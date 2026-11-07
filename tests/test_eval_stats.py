"""Shared tasting statistics (D32): four classes, the zero-spread floor, cost classes and how they combine."""
import contextlib
import importlib.util
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("eval_stats_test", ROOT / "scripts/eval_stats.py")
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)

QUESTIONS = [f"q{i}" for i in range(1, 13)]


def arm(values):
    return {q: [v] for q, v in zip(QUESTIONS, values)}


NATIVE = arm([0.80, 0.70, 0.90, 0.60, 0.75, 0.85, 0.65, 0.95, 0.70, 0.80, 0.60, 0.90])


class CompareTests(unittest.TestCase):
    def test_clear_gain_is_better_and_clear_loss_is_worse(self):
        noise = [0.03, -0.02, 0.01, 0.0, -0.01, 0.02, 0.03, -0.03, 0.0, 0.01, -0.02, 0.02]
        food = {q: [NATIVE[q][0] + 0.25 + n] for q, n in zip(QUESTIONS, noise)}
        self.assertEqual(stats.compare(food, NATIVE, 0.10)["class"], "better")
        food = {q: [NATIVE[q][0] - 0.25 + n] for q, n in zip(QUESTIONS, noise)}
        self.assertEqual(stats.compare(food, NATIVE, 0.10)["class"], "worse")

    def test_small_noisy_difference_is_equivalent_or_undetermined_never_better(self):
        noise = [0.04, -0.05, 0.03, -0.02, 0.05, -0.04, 0.01, -0.03, 0.02, -0.01, 0.03, -0.02]
        food = {q: [NATIVE[q][0] + n] for q, n in zip(QUESTIONS, noise)}
        self.assertEqual(stats.compare(food, NATIVE, 0.10)["class"], "equivalent")
        wide = {q: [NATIVE[q][0] + 10 * n] for q, n in zip(QUESTIONS, noise)}  # SE about 0.09: too wide to call
        self.assertEqual(stats.compare(wide, NATIVE, 0.10)["class"], "undetermined")

    def test_zero_spread_floor_stops_a_point_interval(self):
        # Every question +0.05: without a floor the bootstrap collapses to a point and reads "better" (the V6 flaw).
        food = {q: [NATIVE[q][0] + 0.05] for q in QUESTIONS}
        bare = stats.compare(food, NATIVE, 0.10)
        self.assertEqual(bare["ci95"][0], bare["ci95"][1])
        self.assertEqual(bare["class"], "better")
        floored = stats.compare(food, NATIVE, 0.10, floor_sd=0.15)
        self.assertTrue(floored["floor_applied"])
        self.assertAlmostEqual(floored["se"], 0.15 * math.sqrt(2 / 12))
        self.assertEqual(floored["class"], "undetermined")
        same = stats.compare(NATIVE, NATIVE, 0.10, floor_sd=0.05)
        self.assertEqual(same["class"], "equivalent")
        self.assertEqual(stats.compare(NATIVE, NATIVE, 0.10, floor_sd=0.15)["class"], "undetermined")

    def test_lower_is_better_for_wrong_claims_and_runs_are_averaged(self):
        native = {q: [2, 2, 3] for q in QUESTIONS}
        food = {q: [0, 1, 0] for q in QUESTIONS}
        result = stats.compare(food, native, 0.5, lower_is_better=True)
        self.assertEqual(result["class"], "better")
        self.assertAlmostEqual(result["point"], 1 / 3 - 7 / 3)
        self.assertEqual(stats.compare(native, food, 0.5, lower_is_better=True)["class"], "worse")

    def test_results_are_deterministic_and_inputs_checked(self):
        food = {q: [NATIVE[q][0] + 0.01 * i] for i, q in enumerate(QUESTIONS)}
        self.assertEqual(stats.compare(food, NATIVE, 0.1), stats.compare(food, NATIVE, 0.1))
        for call in (lambda: stats.compare({}, NATIVE, 0.1), lambda: stats.compare(food, NATIVE, 0),
                     lambda: stats.compare(food, NATIVE, 0.1, floor_sd=-1)):
            with self.assertRaises(stats.StatsError):
                call()


class CostTests(unittest.TestCase):
    def tokens(self, ratios):
        native = {q: [100_000] for q in QUESTIONS}
        return {q: [100_000 * r] for q, r in zip(QUESTIONS, ratios)}, native

    def test_cost_classes(self):
        for ratios, expected in (([2.0, 2.1, 1.9] * 4, "over"), ([0.7, 0.72, 0.68] * 4, "cheaper"),
                                 ([1.2, 1.25, 1.15] * 4, "within"), ([0.9, 2.4, 1.1, 1.9] * 3, "undetermined")):
            with self.subTest(expected=expected):
                result = stats.cost(*self.tokens(ratios))
                self.assertEqual(result["class"], expected, result)
        with self.assertRaises(stats.StatsError):
            stats.cost({"q1": [0]}, {"q1": [10]})

    def test_edge_ratios_keep_full_precision_for_the_catalog(self):
        # codex review of d8b1cfc: rounding made 0.99999x read 1.0 while its class said cheaper.
        for per_run, expected in ((99_999, "cheaper"), (150_001, "over")):
            with self.subTest(per_run=per_run):
                result = stats.cost({q: [per_run] for q in QUESTIONS}, {q: [100_000] for q in QUESTIONS})
                self.assertEqual(result["class"], expected)
                judged = stats.judgment("equivalent" if expected == "cheaper" else "better", result, grading="cross-family")
                low, high = judged["cost_ci"]
                self.assertTrue(low <= judged["cost_ratio"] <= high)
                if expected == "cheaper":
                    self.assertTrue(judged["cheaper"] and high < 1)
                else:
                    self.assertGreater(low, 1.5)


class CombineTests(unittest.TestCase):
    def test_quality_agree_lowest(self):
        self.assertEqual(stats.quality("better", "undetermined"), "better")
        self.assertEqual(stats.quality("better", "worse"), "worse")
        self.assertEqual(stats.quality("equivalent", "equivalent"), "equivalent")
        self.assertEqual(stats.quality("equivalent", "undetermined"), "undetermined")
        self.assertEqual(stats.agree("better", "better"), "better")
        # codex review round 3: one family's -0.5 against the other's 0 is not shown equivalent.
        self.assertEqual(stats.agree("better", "equivalent"), "undetermined")
        self.assertEqual(stats.agree("worse", "equivalent"), "undetermined")
        self.assertEqual(stats.agree("better", "worse"), "undetermined")
        self.assertEqual(stats.agree("undetermined", "equivalent"), "undetermined")
        self.assertEqual(stats.lowest("better", "equivalent", "undetermined"), "undetermined")
        self.assertEqual(stats.lowest("better", "worse"), "worse")
        for call in (lambda: stats.quality("same", "better"), lambda: stats.lowest()):
            with self.assertRaises(stats.StatsError):
                call()

    def test_judgment_never_makes_undetermined_cheaper(self):
        cheap = {"ratio": 0.7, "ci95": [0.65, 0.75], "class": "cheaper"}
        self.assertTrue(stats.judgment("equivalent", cheap, grading="cross-family")["cheaper"])
        undetermined = stats.judgment("undetermined", cheap, grading="cross-family")
        self.assertEqual((undetermined["quality"], undetermined["cheaper"]), ("same", False))
        self.assertEqual(stats.judgment("better", cheap, grading="cross-family", conditions=4)["quality"], "better")

    def test_pooled_within_sd(self):
        self.assertAlmostEqual(stats.pooled_within_sd({"a": [1, 3], "b": [2, 2, 2], "c": [5]}), math.sqrt(2 / 3))
        with self.assertRaises(stats.StatsError):
            stats.pooled_within_sd({"a": [1]})


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = stats.main(list(args))
        return code, output.getvalue(), errors.getvalue()

    def test_compare_and_cost_from_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            food, native, bad = (Path(temporary) / name for name in ("f.json", "n.json", "b.json"))
            food.write_text(json.dumps({q: [v[0] + 0.3] for q, v in NATIVE.items()}), encoding="utf-8")
            native.write_text(json.dumps(NATIVE), encoding="utf-8")
            bad.write_text('{"q1": "x"}', encoding="utf-8")
            code, output, _ = self.run_cli("compare", str(food), str(native), "--margin", "0.1", "--floor-sd", "0.05")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["class"], "better")
            code, output, _ = self.run_cli("cost", str(food), str(native))
            self.assertEqual((code, json.loads(output)["class"]), (0, "within"))
            # The JSON keeps full precision (codex review round 4): 0.99999x stays below 1.
            food.write_text(json.dumps({q: [99_999] for q in NATIVE}), encoding="utf-8")
            native.write_text(json.dumps({q: [100_000] for q in NATIVE}), encoding="utf-8")
            result = json.loads(self.run_cli("cost", str(food), str(native))[1])
            self.assertEqual(result["class"], "cheaper")
            self.assertLess(result["ci95"][1], 1)
            code, _, errors = self.run_cli("cost", str(bad), str(native))
            self.assertEqual(code, 2)
            self.assertIn("expected an object", errors)


if __name__ == "__main__":
    unittest.main()
