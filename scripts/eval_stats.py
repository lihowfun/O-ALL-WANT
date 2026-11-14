#!/usr/bin/env python3
"""Shared statistics for OAW tastings (owner decision D32), standard library only.

The default design is 12 questions x 1 run per arm, with questions treated as a random sample:

  compare()   question-paired difference of a food arm against native. The interval comes from a bootstrap over
              questions (10,000 draws, fixed seed). Better or worse when the 95% interval excludes 0 in that
              direction; equivalent when the 90% interval lies inside +/- margin (TOST); otherwise undetermined.
              With repeated runs in every cell, the per-question value is the mean of its runs.
  floor       one run per cell cannot show run-to-run noise, and identical answers make a bootstrap interval
              collapse to a point. Pass floor_sd, the pooled within-question SD from earlier repeated runs of the
              same question bank and model (pooled_within_sd()); the standard error is never below
              floor_sd * sqrt(2 / questions), and a normal interval is used when the floor binds.
  cost()      per-question log token ratio; "over" only when the 95% interval's lower end exceeds the cap (1.5x),
              "cheaper" when its upper end is below 1x, "within" when it is at most the cap, else undetermined.
  quality()   one grading: coverage and wrong-claim classes merged by the validation PREREG's rule.
  agree()     two gradings from different model families: a class counts only when both find it.
  lowest()    several conditions: the lowest decides (D29).
  judgment()  the catalog record fields (quality, quality_class, cost_ratio, cost_ci, cheaper). An undetermined
              quality is never "cheaper": undetermined does not become a default (plan principle 6).

    python3 scripts/eval_stats.py compare FOOD.json NATIVE.json --margin 0.10 [--lower-is-better] [--floor-sd SD]
    python3 scripts/eval_stats.py cost FOOD.json NATIVE.json

FOOD.json and NATIVE.json map a question id to a list of per-run values. Part of OAW.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys

DRAWS = 10_000
SEED = 20261107
Z95, Z90, MDE_FACTOR = 1.959964, 1.644854, 2.8  # MDE: 80% power at a two-sided 5% level
COST_CAP = 1.5
CLASSES = ("better", "equivalent", "undetermined", "worse")
COST_CLASSES = ("cheaper", "within", "undetermined", "over")


class StatsError(ValueError):
    """Input the statistics cannot use."""


def _quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    position = p * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _per_question(food: dict, native: dict, *, log_ratio: bool) -> dict:
    """Both arms must cover the same frozen questions with at least one run each; an unfinished arm is refused."""
    if set(food) != set(native):
        missing = sorted(set(food) ^ set(native))
        raise StatsError(f"the arms answer different questions ({', '.join(missing[:5])}); finish or drop them first")
    empty = sorted(q for q in food if not food[q] or not native[q])
    if empty:
        raise StatsError(f"no runs for {', '.join(empty[:5])}; a cell without runs is not a result")
    shared = sorted(food)
    if not shared:
        raise StatsError("no question has values in both arms")
    if any(not math.isfinite(v) for q in shared for v in (*food[q], *native[q])):
        raise StatsError("values must be finite numbers")
    if log_ratio:
        unrun = sorted(q for q in shared if any(v <= 0 for v in (*food[q], *native[q])))
        if unrun:
            raise StatsError(f"a run with 0 tokens did not run (D30): {', '.join(unrun[:5])}; drop or rerun it")
    result = {}
    for q in shared:
        f, n = statistics.mean(food[q]), statistics.mean(native[q])
        if log_ratio:
            if f <= 0 or n <= 0:
                raise StatsError(f"token counts must be above 0 (question {q})")
            result[q] = math.log(f / n)
        else:
            result[q] = f - n
    return result


def _bootstrap(values: list[float], draws: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    count = len(values)
    return [statistics.fmean(rng.choice(values) for _ in range(count)) for _ in range(draws)]


def _interval(diffs: dict, floor_sd: float | None, draws: int, seed: int) -> dict:
    values = list(diffs.values())
    point = statistics.fmean(values)
    boot = _bootstrap(values, draws, seed)
    se_boot = statistics.pstdev(boot)
    floor_se = floor_sd * math.sqrt(2 / len(values)) if floor_sd else 0.0
    if floor_se > se_boot:
        se = floor_se
        ci95 = [point - Z95 * se, point + Z95 * se]
        ci90 = [point - Z90 * se, point + Z90 * se]
    else:
        se = se_boot
        ci95 = [_quantile(boot, 0.025), _quantile(boot, 0.975)]
        ci90 = [_quantile(boot, 0.05), _quantile(boot, 0.95)]
    return {"point": point, "ci95": ci95, "ci90": ci90, "se": se, "floor_applied": floor_se > se_boot,
            "questions": len(values)}


def compare(food: dict, native: dict, margin: float, *, lower_is_better: bool = False, floor_sd: float | None = None,
            draws: int = DRAWS, seed: int = SEED) -> dict:
    """Four-class comparison of one metric (coverage, wrong claims, detections) against native."""
    if not math.isfinite(margin) or margin <= 0:
        raise StatsError("margin must be a finite number above 0")
    if floor_sd is not None and (not math.isfinite(floor_sd) or floor_sd < 0):
        raise StatsError("floor_sd must be a finite number, 0 or more")
    diffs = _per_question(food, native, log_ratio=False)
    result = _interval(diffs, floor_sd, draws, seed)
    lo95, hi95 = result["ci95"]
    lo90, hi90 = result["ci90"]
    good, bad = (hi95 < 0, lo95 > 0) if lower_is_better else (lo95 > 0, hi95 < 0)
    equivalent = -margin < lo90 and hi90 < margin
    cls = "better" if good else "worse" if bad else "equivalent" if equivalent else "undetermined"
    result.update({"class": cls, "within_margin": equivalent, "margin": margin, "lower_is_better": lower_is_better,
                   "mde": MDE_FACTOR * result["se"], "per_question": diffs})
    return result


def cost(food: dict, native: dict, *, cap: float = COST_CAP, draws: int = DRAWS, seed: int = SEED) -> dict:
    """Token cost of the food against native as a ratio with a 95% interval, and its class against the cap."""
    if not math.isfinite(cap) or cap <= 0:
        raise StatsError("cap must be a finite number above 0")
    logs = _per_question(food, native, log_ratio=True)
    result = _interval(logs, None, draws, seed)
    lo, hi = (math.exp(v) for v in result["ci95"])
    ratio = math.exp(result["point"])
    cls = "over" if lo > cap else "cheaper" if hi < 1 else "within" if hi <= cap else "undetermined"
    # Full precision: the catalog checks the class against these numbers.
    return {"ratio": ratio, "ci95": [lo, hi], "class": cls, "cap": cap, "questions": result["questions"],
            "per_question": {q: math.exp(v) for q, v in logs.items()}}


def _check(*classes: str) -> None:
    for name in classes:
        if name not in CLASSES:
            raise StatsError(f"unknown class: {name}")


def quality(coverage_class: str, wrong_class: str) -> str:
    """One grading of one condition (the validation PREREG's merge rule): worse if either metric is worse;
    better if coverage is better and wrong claims are not worse; equivalent if both are; else undetermined."""
    _check(coverage_class, wrong_class)
    if "worse" in (coverage_class, wrong_class):
        return "worse"
    if coverage_class == "better":
        return "better"
    if coverage_class == wrong_class == "equivalent":
        return "equivalent"
    return "undetermined"


def agree(first: str, second: str) -> str:
    """Two gradings from different model families (D32): a class counts only when both find it; any
    disagreement, including one family's difference against the other's equivalence, is undetermined."""
    _check(first, second)
    return first if first == second else "undetermined"


def lowest(*classes: str) -> str:
    """Several conditions (models, repositories): the lowest decides (D29)."""
    if not classes:
        raise StatsError("no condition given")
    _check(*classes)
    order = ("worse", "undetermined", "equivalent", "better")
    return min(classes, key=order.index)


def judgment(quality_class: str, cost_result: dict, *, grading: str, conditions: int = 1, basis: str = "") -> dict:
    """The catalog judgment fields for one tasting (the lowest condition already chosen by the caller)."""
    if quality_class not in CLASSES:
        raise StatsError(f"unknown quality class: {quality_class}")
    quality = {"better": "better", "worse": "worse"}.get(quality_class, "same")
    cheaper = quality_class == "equivalent" and cost_result["class"] == "cheaper"
    doc = {"quality": quality, "quality_class": quality_class, "cost_ratio": cost_result["ratio"],
           "cost_ci": cost_result["ci95"], "cheaper": cheaper, "grading": grading, "conditions": conditions}
    if basis:
        doc["basis"] = basis
    return doc


def pooled_within_sd(cells: dict) -> float:
    """Pooled within-question SD from repeated runs: cells maps (arm, question) or question to a list of values."""
    numerator = denominator = 0.0
    for values in cells.values():
        if len(values) >= 2:
            numerator += statistics.variance(values) * (len(values) - 1)
            denominator += len(values) - 1
    if not denominator:
        raise StatsError("no cell has two or more runs")
    return math.sqrt(numerator / denominator)


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not all(isinstance(v, list) and all(isinstance(x, (int, float)) for x in v)
                                             for v in data.values()):
        raise StatsError(f"{path}: expected an object of question id -> list of numbers")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    compare_parser = commands.add_parser("compare", help="four-class comparison of one metric")
    compare_parser.add_argument("food")
    compare_parser.add_argument("native")
    compare_parser.add_argument("--margin", type=float, required=True)
    compare_parser.add_argument("--lower-is-better", action="store_true")
    compare_parser.add_argument("--floor-sd", type=float)
    cost_parser = commands.add_parser("cost", help="token ratio with its interval and class")
    cost_parser.add_argument("food")
    cost_parser.add_argument("native")
    cost_parser.add_argument("--cap", type=float, default=COST_CAP)
    args = parser.parse_args(argv)
    try:
        food, native = _load(args.food), _load(args.native)
        if args.command == "compare":
            result = compare(food, native, args.margin, lower_is_better=args.lower_is_better, floor_sd=args.floor_sd)
        else:
            result = cost(food, native, cap=args.cap)
    except (OSError, ValueError) as exc:
        print(f"eval_stats: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))  # full precision: records are built from it
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
