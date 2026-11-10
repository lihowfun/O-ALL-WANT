#!/usr/bin/env python3
"""H1 judge: the frozen rule of PREREG.md (the section on the verdict) applied to the runner's counted rows.

    python3 h1_judge.py --stats <eval_stats.py> --freeze FREEZE.json --units units_A.json units_B.json units_C.json \\
        --rows rows-main-claude.jsonl rows-main-codex.jsonl --attempts attempts-main-claude.jsonl attempts-main-codex.jsonl \\
        --starts starts-main-claude.jsonl starts-main-codex.jsonl

Before anything is judged, the inputs are bound to FREEZE.json: the unit files, the loaded eval_stats.py and this
judge must have the frozen digests, and every row and attempt (L included) must be a main run of the frozen units,
arms, unit entries and runner. Every attempt must have a start record, a start without an attempt is an
interrupted attempt whose tokens are unknown, and nothing may be given twice. Every counted row must be among the
attempts, and every attempt that counted must be among the rows.

Each cell is judged on its own: quality of O against N (N is the mean of its two runs per unit), memory on class B,
token cost, the owner's word and the protocol outcome. Then the two cells are merged, the lower one deciding. A cell
with a run missing gets no word. Statistics come from OAW's eval_stats.py only. Prints JSON.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

MARGIN = 0.10       # equivalence margin on the unit score
FLOOR_MIN = 0.1318  # borrowed lower bound of the run-to-run spread; the cell's own N1/N2 spread is used when larger
STEP = 0.10         # a unit counts as won or lost from this score difference on
MORE = 1.10         # the batch token ratio must pass this and native's own run-to-run ratio to count as more
EPS = 1e-9
CELLS = ("claude", "codex")
PRIMARY = ("N1", "N2", "O")
CLASSES = ("A", "B", "C")
PER_CLASS = 4
WORDS = ("更慘", "未定", "雞肋", "沒差", "有幫助")                      # worst first
OUTCOMES = ("提案移出預設", "該改成選配", "能力未定", "留在預設站得住")  # worst first
UNFINISHED = "未完成"
UNKNOWN = "未知"
NOT_GIVEN = "未提供"
MORE_TOKENS, FEWER_TOKENS, NOT_MORE = "token 變多", "token 變少", "沒有確實變多"


def digest(path):
    total = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            total.update(block)
    return total.hexdigest()


def unit_digest(unit):
    """The same digest the runner puts on each row as unit_sha256."""
    return hashlib.sha256(json.dumps(unit, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Frozen:
    """What FREEZE.json allows: the unit files, the runner, the arms per cell and class, and each unit's entry."""

    def __init__(self, freeze_path, unit_paths, stats_path):
        self.freeze = json.load(open(freeze_path, encoding="utf-8"))
        self.sha256 = digest(freeze_path)
        if digest(stats_path) != self.freeze["eval_stats_sha256"]:
            raise SystemExit("the eval_stats.py given is not the frozen one")
        if digest(os.path.abspath(__file__)) != self.freeze["files"]["h1_judge.py"]:
            raise SystemExit("this judge is not the frozen h1_judge.py")
        self.units, self.entry = {}, {}
        for path in unit_paths:
            data = json.load(open(path, encoding="utf-8"))
            if digest(path) != self.freeze["units"].get(data["klass"]):
                raise SystemExit(f"{os.path.basename(path)} is not the frozen class {data['klass']} unit file")
            self.units[data["klass"]] = [u["id"] for u in data["units"]]
            for unit in data["units"]:
                self.entry[unit["id"]] = (data["klass"], unit_digest(unit))
        if sorted(self.units) != list(CLASSES):
            raise SystemExit("give the frozen unit files of classes A, B and C")
        arms = self.freeze["launch"]["arms"]
        self.roster = {cell: {(u, arm) for k in CLASSES for u in self.units[k] for arm in arms[cell][k]}
                       for cell in CELLS}

    def check(self, row, what):
        """Refuse a row or attempt that is not a main run of a frozen unit entry, arm and runner."""
        name = f"{what} {row.get('cell')} {row.get('unit')}/{row.get('arm')}"
        klass, entry = self.entry.get(row.get("unit"), (None, None))
        problems = []
        if row.get("tag") != "main":
            problems.append("not tag main")
        if row.get("freeze_sha256") != self.sha256:
            problems.append("another FREEZE.json")
        if klass is None or row.get("klass") != klass:
            problems.append("not a frozen unit of its class")
        elif row.get("units_sha256") != self.freeze["units"][klass]:
            problems.append("another unit file")
        if entry is not None and row.get("unit_sha256") != entry:
            problems.append("another version of the unit")
        if row.get("runner_sha256") != self.freeze["files"]["h1_run.py"]:
            problems.append("another runner")
        if row.get("cell") not in self.roster or (row.get("unit"), row.get("arm")) not in self.roster[row["cell"]]:
            problems.append("not in the frozen roster")
        if problems:
            raise SystemExit(f"{name}: {', '.join(problems)}")


def reconcile(attempts, starts):
    """The attempts with the start records: every attempt was started, nothing is listed twice, and a run that was
    started and never finished becomes an attempt 'interrupted' whose tokens are unknown."""
    tried, started = set(), set()
    for row in attempts:
        if row.get("event") == "start" or "sessions" not in row:
            raise SystemExit(f"{row.get('cell')} {row.get('root')}: an --attempts entry that is not a finished attempt")
        key = (row["cell"], row.get("root"))
        if key in tried:
            raise SystemExit(f"attempt {key[1]} of the {key[0]} cell is given twice")
        tried.add(key)
    for row in starts:
        if row.get("event") != "start" or any(key in row for key in ("score", "grade", "not_run", "sessions")):
            raise SystemExit(f"{row.get('cell')} {row.get('root')}: a --starts entry that is not a start record")
        key = (row["cell"], row.get("root"))
        if key in started:
            raise SystemExit(f"start {key[1]} of the {key[0]} cell is given twice")
        started.add(key)
    if tried - started:
        raise SystemExit(f"attempts without a start record: {sorted(tried - started)[:3]}")
    return attempts + [dict(row, not_run="interrupted", tokens_total=None, tokens_noncache=None)
                       for row in starts if (row["cell"], row.get("root")) not in tried]


def cross_check(rows, attempts, cell):
    """Every counted row is an attempt, and every attempt that counted is a row; a cell with rows needs attempts."""
    def key(row):
        return row["cell"], row["unit"], row["arm"], row["attempt"], row.get("root")

    mine, counted = [a for a in attempts if a["cell"] == cell], [r for r in rows if r["cell"] == cell]
    if counted and not mine:
        raise SystemExit(f"{cell}: the attempts are {NOT_GIVEN}; they are needed to judge the cell")
    tried, kept = {key(a) for a in mine}, {key(r) for r in counted}
    missing = [key(r) for r in counted if key(r) not in tried]
    dropped = [key(a) for a in mine if not a.get("not_run") and key(a) not in kept]
    if missing or dropped:
        raise SystemExit(f"{cell}: rows not among the attempts {missing[:3]}, counted attempts not among the rows "
                         f"{dropped[:3]}")


def load_stats(path):
    spec = importlib.util.spec_from_file_location("eval_stats", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["eval_stats"] = module
    spec.loader.exec_module(module)
    return module


def read(paths):
    rows = []
    for path in paths or []:
        with open(path, encoding="utf-8") as handle:
            rows += [json.loads(line) for line in handle if line.strip()]
    return rows


def table(rows, cell):
    """arm -> unit -> row, and unit -> class, for one cell. Only counted main runs, one row per run."""
    arms, klass = {}, {}
    for row in rows:
        if row["cell"] != cell:
            continue
        name = f"{cell} {row['unit']}/{row['arm']}"
        if row.get("tag") != "main" or row.get("not_run") or row.get("score") is None:
            raise SystemExit(f"{name}: not a counted main run")
        if row["unit"] in arms.setdefault(row["arm"], {}):
            raise SystemExit(f"{name}: two rows for one run")
        if klass.setdefault(row["unit"], row["klass"]) != row["klass"]:
            raise SystemExit(f"{name}: the unit appears in two classes")
        arms[row["arm"]][row["unit"]] = row
    return arms, klass


def finished(arms, frozen):
    """The classes whose four frozen units all have N1, N2 and O, and why the cell is not complete (empty when it
    is). The units are the frozen ones, not the ones that happen to have rows."""
    done, why = {}, []
    for name in CLASSES:
        units = sorted(frozen.units[name])
        full = [u for u in units if all(u in arms.get(arm, {}) for arm in PRIMARY)]
        if len(units) == PER_CLASS and full == units:
            done[name] = units
        else:
            why.append(f"class {name}: {len(full)} of {PER_CLASS} units have N1, N2 and O")
    return done, why


def values(arms, units, key):
    """(O, N) as unit -> list of values; N holds its two runs."""
    return ({u: [key(arms["O"][u])] for u in units},
            {u: [key(arms["N1"][u]), key(arms["N2"][u])] for u in units})


def score(row):
    """The unit score from the grade's exact counts (0 on a suite regression); the stored score otherwise."""
    grade = row.get("grade") or {}
    if grade.get("n"):
        return 0.0 if grade.get("suite_regression") else grade["passed"] / grade["n"]
    return float(row["score"])


def recalled(row):
    return 1.0 if row["grade"].get("recall") else 0.0


def floor(stats, native):
    """(the floor used, the bank's own spread): the pooled within-unit SD of native's two runs, FLOOR_MIN at least."""
    try:
        own = stats.pooled_within_sd(native)
    except stats.StatsError:
        own = 0.0
    return max(own, FLOOR_MIN), own


def brief(result):
    return {key: result[key] for key in ("class", "point", "ci95", "ci90", "se", "mde", "floor_applied", "questions")}


def subset(mapping, units):
    return {u: mapping[u] for u in units}


def quality(stats, arms, done, complete):
    """Step 1: the composite and each class with one floor; the cell's class Q by the ordered rule."""
    units = [u for name in done for u in done[name]]
    food, native = values(arms, units, score)
    used, own = floor(stats, native)
    parts = {name: stats.compare(subset(food, done[name]), subset(native, done[name]), MARGIN, floor_sd=used)
             for name in done}
    out = {"floor": used, "own_spread": own, "by_class": {name: brief(parts[name]) for name in parts}}
    if not complete:
        return out
    whole = stats.compare(food, native, MARGIN, floor_sd=used)
    worse = [name for name in CLASSES if parts[name]["class"] == "worse"]
    low = [name for name in CLASSES if parts[name]["point"] <= -MARGIN + EPS]
    if worse:
        q, why = "worse", f"class {', '.join(worse)} is worse"
    elif whole["class"] == "worse":
        q, why = "worse", "the composite is worse"
    elif low:
        q, why = "undetermined", f"類別不一致：class {', '.join(low)} is {MARGIN} or more below native"
    else:
        q, why = whole["class"], "the composite class"
    own_only = stats.compare(food, native, MARGIN, floor_sd=own or None)
    out.update({"Q": q, "why": why, "composite": brief(whole),
                "sensitivity_own_spread_only": brief(own_only)})  # reported, not used
    return out


def memory(stats, arms, units):
    """Step 2: whether the earlier decisions were recalled (class B), judged apart from quality."""
    food, native = values(arms, units, recalled)
    used, _own = floor(stats, native)
    result = stats.compare(food, native, MARGIN, floor_sd=used)
    counts = {arm: sum(1 for u in units if recalled(arms[arm][u])) for arm in PRIMARY}
    if result["class"] == "better":
        word = "記憶變好"
    elif result["class"] == "worse":
        word = "記憶變差"
    elif all(count == len(units) for count in counts.values()):
        word = "都記得，這組題目分不出來（天花板，未證等價）"
    else:
        word = "未定"
    return {"word": word, "remembered": counts, "of": len(units), "floor": used, **brief(result)}


def batch(arms, units, key):
    """Token totals of a set of units, O over the mean of N's two runs, and native's own run-to-run ratio."""
    o, n1, n2 = (sum(arms[arm][u].get(key) or 0 for u in units) for arm in ("O", "N1", "N2"))
    out = {"O": o, "N1": n1, "N2": n2, "ratio": None, "band": None}
    if n1 > 0 and n2 > 0:
        out.update({"ratio": o / ((n1 + n2) / 2), "band": max(n1 / n2, n2 / n1)})
    return out


def token_sentence(totals):
    if totals["ratio"] is None:
        return NOT_MORE
    if totals["ratio"] > max(MORE, totals["band"]):
        return MORE_TOKENS
    if totals["ratio"] < min(1 / MORE, 1 / totals["band"]):
        return FEWER_TOKENS
    return NOT_MORE


def not_counted(attempts, cell):
    """Tokens of the main attempts that did not count, per arm; an interrupted attempt's tokens are unknown, so the
    totals are then lower bounds."""
    out = {}
    for row in attempts:
        if row["cell"] == cell and row.get("tag") == "main" and row.get("not_run"):
            entry = out.setdefault(row["arm"], {"attempts": 0, "tokens_total": 0, "tokens_noncache": 0,
                                                "tokens_unknown": 0})
            entry["attempts"] += 1
            if row.get("tokens_total") is None:
                entry["tokens_unknown"] += 1
            entry["tokens_total"] += row.get("tokens_total") or 0
            entry["tokens_noncache"] += row.get("tokens_noncache") or 0
    return out


def spending(stats, arms, done, complete, wasted):
    """Step 3: the batch token ratio for the owner's word, and the protocol's per-unit cost class."""
    units = [u for name in done for u in done[name]]
    out = {"by_class": {name: batch(arms, done[name], "tokens_total") for name in done},
           "noncache_by_class": {name: batch(arms, done[name], "tokens_noncache") for name in done},
           "attempts_not_counted": wasted}
    if not complete:
        return out
    out["batch"] = batch(arms, units, "tokens_total")
    out["noncache_batch"] = batch(arms, units, "tokens_noncache")
    out["sentence"] = token_sentence(out["batch"])
    food, native = values(arms, units, lambda row: row.get("tokens_total") or 0)
    try:
        result = stats.cost(food, native)
        out["protocol"] = {key: result[key] for key in ("class", "ratio", "ci95", "cap")}
    except stats.StatsError as error:
        out["protocol"] = {"class": "undetermined", "error": str(error)}
    return out


def owner_word(q, sentence):
    """Step 4."""
    if q == "worse":
        return "更慘"
    if q == "better":
        return "有幫助"
    if q == "equivalent":
        return "雞肋" if sentence == MORE_TOKENS else "沒差"
    return "未定"


def outcome(q, cost_class):
    """Step 5: what the result means for OAW itself, by the protocol's result table."""
    if q == "worse":
        return "提案移出預設"
    if q == "better":
        return "該改成選配" if cost_class == "over" else "留在預設站得住"
    if q == "equivalent":
        return {"cheaper": "留在預設站得住", "over": "提案移出預設"}.get(cost_class, "該改成選配")
    return "提案移出預設" if cost_class == "over" else "能力未定"


def difference(arms, unit):
    return score(arms["O"][unit]) - (score(arms["N1"][unit]) + score(arms["N2"][unit])) / 2


def sign(arms, unit):
    diff = difference(arms, unit)
    return "+" if diff >= STEP - EPS else "-" if diff <= -STEP + EPS else "0"


def direction(arms, units):
    """Secondary: unit-level wins and losses of O against the mean of N in one class. Not part of the word."""
    signs = [sign(arms, u) for u in units]
    wins, losses = signs.count("+"), signs.count("-")
    net = wins - losses
    if net >= 2:
        text = "方向：較好"
    elif net <= -2:
        text = "方向：較差"
    elif net:
        text = "差一題，不下結論"
    elif wins:
        text = "勝負抵銷，未證等價"
    else:
        text = "看不出差別，未證等價"
    ceiling = [u for u in units if score(arms["N1"][u]) == 1.0 and score(arms["N2"][u]) == 1.0]
    return {"wins": wins, "losses": losses, "direction": text, "at_ceiling": ceiling,
            "ceiling_note": "頂到天花板，只看得出變差" if ceiling else ""}


def control(stats, arms, frozen, used):
    """Secondary, codex cell: O against L and L against N on the frozen class B and C units, same margin and floor."""
    units = sorted(frozen.units["B"] + frozen.units["C"])
    have = [u for u in units if all(u in arms.get(arm, {}) for arm in ("L",) + PRIMARY)]
    if len(units) != 2 * PER_CLASS or have != units:
        return {"status": UNFINISHED, "units": len(have)}
    food, native = values(arms, units, score)
    policy = {u: [score(arms["L"][u])] for u in units}

    def pick(result):
        return {key: result[key] for key in ("class", "point", "ci95")}

    return {"units": len(units), "O_vs_L": pick(stats.compare(food, policy, MARGIN, floor_sd=used)),
            "L_vs_N": pick(stats.compare(policy, native, MARGIN, floor_sd=used))}


def usage(arms):
    """What each arm actually used, as numbers of units (recorded, not scored). Skill use, skills listed at startup
    and blocked writes are 未知 for an arm in which any session could not be read for them."""
    out = {}
    for arm in sorted(arms):
        rows = list(arms[arm].values())

        def count(test, rows=rows):
            return sum(1 for row in rows if any(test(s) for s in row.get("sessions") or []))

        def known(field, test, rows=rows):
            if any(s.get(field) is None for row in rows for s in row.get("sessions") or []):
                return UNKNOWN
            return count(test)

        out[arm] = {"units": len(rows),
                    "touched_oaw": count(lambda s: (s.get("evidence") or {}).get("oaw")),
                    "used_skill": known("skills", lambda s: s.get("skills")),
                    "listed_oaw_skills": known("listed_skills", lambda s: any(
                        str(name).startswith("oaw-") for name in s.get("listed_skills"))),
                    "blocked_writes": known("blocked", lambda s: s.get("blocked")),
                    "used_subagent": count(lambda s: s.get("agents")),
                    "touched_notes": count(lambda s: (s.get("evidence") or {}).get("notes")),
                    "touched_memory": count(lambda s: (s.get("evidence") or {}).get("memory")),
                    "memory_files": count(lambda s: s.get("memory_files")),
                    "cut_by_limit": sum(1 for row in rows if row.get("flags"))}
    return out


def judge_cell(stats, frozen, rows, attempts, cell):
    cross_check(rows, attempts, cell)
    arms, klass = table(rows, cell)
    wasted = not_counted(attempts, cell)
    if not klass:
        return {"status": UNFINISHED, "why": ["no rows"], "attempts_not_counted": wasted}, arms
    done, why = finished(arms, frozen)
    complete = not why
    out = {"status": "complete" if complete else UNFINISHED, "why": why, "classes_done": sorted(done),
           "attempts_not_counted": wasted}
    if done:
        out["quality"] = quality(stats, arms, done, complete)
        out["cost"] = spending(stats, arms, done, complete, wasted)
        out["direction"] = {name: direction(arms, done[name]) for name in done}
    if "B" in done:
        out["memory"] = memory(stats, arms, done["B"])
    if complete:
        q, sentence = out["quality"]["Q"], out["cost"]["sentence"]
        out["word"] = owner_word(q, sentence)
        out["token_sentence"] = sentence
        out["outcome"] = outcome(q, out["cost"]["protocol"]["class"])
        if out["word"] == "未定":
            whole = out["quality"]["composite"]
            out["undetermined_detail"] = {key: whole[key] for key in ("point", "ci95", "mde")}
    if cell == "codex" and "L" in arms and done:
        out["L_control"] = control(stats, arms, frozen, out["quality"]["floor"])
    out["usage"] = usage(arms)
    return out, arms


def merge(cells):
    """Step 6: the lower word and the lower outcome decide; a missing or unfinished cell leaves no merged result."""
    if any(cells[cell]["status"] != "complete" for cell in CELLS):
        only = [cell for cell in CELLS if cells[cell]["status"] == "complete"]
        return {"word": UNFINISHED, "outcome": UNFINISHED,
                "note": f"only the {only[0]} cell is complete" if only else "no cell is complete"}
    words = {cell: cells[cell]["word"] for cell in CELLS}
    outcomes = {cell: cells[cell]["outcome"] for cell in CELLS}
    return {"word": min(words.values(), key=WORDS.index), "outcome": min(outcomes.values(), key=OUTCOMES.index),
            "words": words, "outcomes": outcomes, "cells_agree": len(set(words.values())) == 1}


def across(tables):
    """The same unit in the two cells, described only: the same unit is not two independent samples."""
    shared = sorted(u for u in tables[CELLS[0]].get("O", {})
                    if all(u in tables[cell].get(arm, {}) for cell in CELLS for arm in PRIMARY))
    units = {u: {cell: sign(tables[cell], u) for cell in CELLS} for u in shared}
    pairs = [tuple(units[u][cell] for cell in CELLS) for u in shared]
    return {"units": units,
            "same_direction": sum(1 for a, b in pairs if a == b and a != "0"),
            "no_difference_in_both": sum(1 for a, b in pairs if a == b == "0"),
            "opposite": sum(1 for a, b in pairs if {a, b} == {"+", "-"}),
            "difference_in_one_cell": sum(1 for a, b in pairs if a != b and "0" in (a, b))}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stats", required=True, help="path to OAW's scripts/eval_stats.py")
    parser.add_argument("--freeze", required=True, help="FREEZE.json")
    parser.add_argument("--units", required=True, nargs=3, help="the frozen unit files of classes A, B and C")
    parser.add_argument("--rows", required=True, nargs="+")
    parser.add_argument("--attempts", required=True, nargs="+")
    parser.add_argument("--starts", required=True, nargs="+")
    args = parser.parse_args()
    frozen = Frozen(args.freeze, args.units, args.stats)
    stats = load_stats(args.stats)
    rows, attempts, starts = read(args.rows), read(args.attempts), read(args.starts)
    for row in rows:
        frozen.check(row, "row")
    for row in attempts:
        frozen.check(row, "attempt")
    for row in starts:
        frozen.check(row, "start")
    attempts = reconcile(attempts, starts)
    cells, tables = {}, {}
    for cell in CELLS:
        cells[cell], tables[cell] = judge_cell(stats, frozen, rows, attempts, cell)
    out = {"rule": {"margin": MARGIN, "floor_min": FLOOR_MIN, "step": STEP, "more": MORE, "per_class": PER_CLASS,
                    "word_order": WORDS, "outcome_order": OUTCOMES},
           "inputs": {"freeze_sha256": frozen.sha256, "units": frozen.freeze["units"],
                      "eval_stats_sha256": frozen.freeze["eval_stats_sha256"]},
           "cells": cells, "merged": merge(cells), "across_cells": across(tables)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
