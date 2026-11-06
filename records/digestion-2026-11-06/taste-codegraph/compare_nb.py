"""Control NB (ADDENDUM-NB.md): judge C, S and G against NB with the unchanged judge() of summary.py.

  python3 compare_nb.py <opus rows.jsonl> <opus grades.jsonl> <nb rows.jsonl> <nb grades.jsonl> <out.json>

NB ran in its own output folder (the runner's budget guard counts every unseeded row of its folder, so it would
not start NB next to the 12 C rows); its rows and grades are merged here with the Opus condition's.
C's Opus verdict is the worse of C vs N and C vs NB (ADDENDUM-NB.md).
"""
import json
import sys

from summary import describe, judge

ORDER = ["worse than native", "not shown better than native", "same understanding, cheaper", "understands better"]


def rank(verdict):
    return next(i for i, prefix in enumerate(ORDER) if verdict.startswith(prefix))


def main(rows_path, grades_path, nb_rows, nb_grades, out_path):
    rows = [json.loads(line) for path in (rows_path, nb_rows) for line in open(path, encoding="utf-8")]
    grades = {g["key"]: g for path in (grades_path, nb_grades) for g in (json.loads(line) for line in open(path, encoding="utf-8"))}
    summary = describe(rows, grades)
    vs_n = {arm: judge(summary[arm], summary["N"]) for arm in ("C", "S", "G", "NB")}
    vs_nb = {arm: judge(summary[arm], summary["NB"]) for arm in ("C", "S", "G")}
    worse_of = min((vs_n["C"]["verdict"], vs_nb["C"]["verdict"]), key=rank)
    result = {"summary": summary, "verdicts_vs_N": vs_n, "verdicts_vs_NB": vs_nb, "C_opus_verdict": worse_of}
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
    for arm in ("N", "NB", "S", "G", "C"):
        s = summary[arm]
        print(f"{arm}: runs {s['runs']} coverage {s['coverage_mean']} essential-ok {s['essential_ok_runs']} wrong {s['wrong_claims']} "
              f"tokens median {s['tokens_median']:,} total {s['tokens_total']:,} tools median {s['tool_calls_median']}")
    for arm in ("C", "S", "G"):
        print(arm, "vs N:", vs_n[arm]["verdict"], vs_n[arm], "| vs NB:", vs_nb[arm]["verdict"], vs_nb[arm])
    print("NB vs N:", vs_n["NB"])
    print("C (Opus) official:", worse_of)


if __name__ == "__main__":
    main(*sys.argv[1:6])
