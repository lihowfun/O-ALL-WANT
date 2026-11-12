#!/usr/bin/env python3
"""Synthetic rows through cap_judge.py: every boundary and the order of PLAN.md sections 6 and 7. Exits 0 when all hold."""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import cap_judge as cj

TASKS, IDLE = ["a", "b", "c", "d"], ["t01", "t04"]


def cell(pattern, idle=None, cand="P1"):
    """Rows of one cell. pattern: per task a 3-letter string for N1, N2, S ('p' pass, 'f' fail).
    idle: per idle task (n_tokens, s_tokens, n_solved, s_solved)."""
    rows = []
    for task, letters in zip(TASKS, pattern):
        for arm, letter in zip(("N1", "N2", cand), letters):
            rows.append({"unit": task, "arm": arm, "kind": "answer", "passed": letter == "p", "tokens_total": 10})
    for task, (n_tok, s_tok, n_ok, s_ok) in zip(IDLE, idle or [(1000, 1000, True, True)] * 2):
        rows.append({"unit": task, "arm": "N", "kind": "idle", "passed": n_ok, "startup_tokens": n_tok})
        rows.append({"unit": task, "arm": cand, "kind": "idle", "passed": s_ok, "startup_tokens": s_tok})
    return rows


def verdict(claude, codex, incomplete=None):
    found = cj.judge({"claude": claude, "codex": codex}, incomplete or {}, TASKS, IDLE, candidates=("P1",))
    return found["candidates"]["P1"]


SAME = ["fff", "fff", "ppp", "pfp"]           # nothing new, nothing lost
BETTER = ["ffp", "ffp", "ppp", "fff"]         # two new passes
OK = [(1000, 1000, True, True)] * 2
cases = []


def expect(name, got, want):
    cases.append((name, got, want))


# section 6, per cell
for name, pattern, want in [
    ("2 new passes", BETTER, "improved"),
    ("1 new pass", ["ffp", "fff", "ppp", "fff"], "undecided"),
    ("2 new passes and a miss", ["ffp", "ffp", "pff", "fff"], "undecided"),
    ("2 new passes and a regression", ["ffp", "ffp", "ppf", "fff"], "undecided"),
    ("2 regressions", ["ppf", "ppf", "ffp", "ffp"], "worse"),
    ("1 regression", ["ppf", "ppp", "fff", "fff"], "undecided"),
    ("all pass", ["ppp"] * 4, "undecided"),
    ("a miss only", ["pff", "fpf", "ppp", "fff"], "undecided"),
    ("S passes where one N passed", ["pfp", "fpp", "fff", "fff"], "undecided"),
]:
    expect("cell: " + name, verdict(cell(pattern), cell(SAME))["cells"]["claude"]["result"], want)
expect("task kinds", [t["kind"] for t in verdict(cell(["ffp", "ppf", "pff", "ppp"]), cell(SAME))["cells"]["claude"]
                      ["tasks"].values()], ["new pass", "regression", "missed", "ceiling"])

# section 7, idle pairs
for name, claude_idle, codex_idle, want in [
    ("equal tokens", OK, OK, "pass"),
    ("exactly 1.02", [(1000, 1020, True, True), OK[0]], OK, "pass"),
    ("just above 1.02", [(10000, 10201, True, True), OK[0]], OK, "fail"),
    ("N solved, S not, both cells", [(1000, 1000, True, False), OK[0]], [(1000, 1000, True, False), OK[0]], "fail"),
    ("N solved, S not, one cell", [(1000, 1000, True, False), OK[0]], OK, "undecided"),
    ("N solved, S not, different tasks", [(1000, 1000, True, False), OK[0]], [OK[0], (1000, 1000, True, False)],
     "undecided"),
    ("neither solved", [(1000, 1000, False, False), OK[0]], OK, "undecided"),
    ("tokens missing", [(None, 1000, True, True), OK[0]], OK, "undecided"),
    ("S solved, N not", [(1000, 1000, False, True), OK[0]], OK, "pass"),
    ("fewer tokens with S", [(1000, 900, True, True), OK[0]], OK, "pass"),
    ("above 1.02 beats undecided", [(1000, 1100, False, False), OK[0]], OK, "fail"),
]:
    expect("idle: " + name, verdict(cell(SAME, claude_idle), cell(SAME, codex_idle))["idle"], want)

# the merge table, in order
BAD_IDLE = [(1000, 1100, True, True), OK[0]]
UNSURE_IDLE = [(1000, 1000, False, False), OK[0]]
WORSE = ["ppf", "ppf", "fff", "fff"]
for name, got, want in [
    ("improved + same + idle pass", verdict(cell(BETTER), cell(SAME)), "optional"),
    ("improved in both", verdict(cell(BETTER), cell(BETTER)), "optional"),
    ("improved, the other cell worse", verdict(cell(BETTER), cell(WORSE)), "not adopted"),
    ("improved, idle fails", verdict(cell(BETTER, BAD_IDLE), cell(SAME)), "not adopted"),
    ("improved, idle undecided", verdict(cell(BETTER, UNSURE_IDLE), cell(SAME)), "below the bar"),
    ("improved, the other cell has a miss", verdict(cell(BETTER), cell(["pff", "fff", "ppp", "fff"])), "below the bar"),
    ("improved, the other cell has one regression", verdict(cell(BETTER), cell(["ppf", "fff", "ppp", "fff"])),
     "below the bar"),
    ("nothing new", verdict(cell(SAME), cell(SAME)), "below the bar"),
    ("all ceiling", verdict(cell(["ppp"] * 4), cell(["ppp"] * 4)), "below the bar"),
    ("worse, install also failed in a cell", verdict(cell(WORSE), cell(SAME), {"codex": {"P1": ["install"]}}),
     "not completed"),
    ("a task row missing", verdict(cell(BETTER)[:-6], cell(SAME)), "not completed"),
    ("an idle row missing", verdict(cell(BETTER)[:-1], cell(SAME)), "not completed"),
    ("worse and idle fails", verdict(cell(WORSE, BAD_IDLE), cell(SAME)), "not adopted"),
]:
    expect("merge: " + name, got["verdict"], want)

full = cj.judge({"claude": cell(["ppp", "ffp", "fff", "pfp"]), "codex": cell(["ppp", "ppp", "fff", "fff"])}, {}, TASKS,
                IDLE, candidates=("P1",))
expect("ceiling list", full["ceiling"], {"P1": {"claude": ["a"], "codex": ["a", "b"]}})
partial = cj.judge({"claude": [r for r in cell(["ppp"] * 4) if r["arm"] != "P1"], "codex": cell(["ppp"] * 4)}, {}, TASKS,
                   IDLE, candidates=("P1",))
expect("no ceiling without the candidate's row", partial["ceiling"]["P1"]["claude"], [])
try:
    cj.judge({"claude": cell(SAME) + cell(SAME)[:1], "codex": cell(SAME)}, {}, TASKS, IDLE, candidates=("P1",))
    expect("a second counted row is refused", "accepted", "refused")
except SystemExit:
    expect("a second counted row is refused", "refused", "refused")

bad = [(name, got, want) for name, got, want in cases if got != want]
for name, got, want in cases:
    print(f"{'ok ' if got == want else 'BAD'} {name}: {got}" + ("" if got == want else f" (expected {want})"))
print(f"{len(cases) - len(bad)}/{len(cases)} hold")
sys.exit(1 if bad else 0)
