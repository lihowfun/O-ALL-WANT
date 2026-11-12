#!/usr/bin/env python3
"""cap_report: the tables of RESULT.md from a state folder and the judge's output. Reads only; no local path is
printed.

usage: cap_report.py <state folder> <judge.json>
"""
import json
import os
import sys

CELLS = ("claude", "codex")
ARMS = ("N1", "N2", "P1", "P2", "P3")
NAMES = {"P1": "OfficeCLI", "P2": "huashu-design", "P3": "professional-pptx"}
ZH = {"new pass": "新過", "regression": "確定退步", "missed": "漏掉", "ceiling": "頂到天花板", "same": "—",
      "improved": "改善", "worse": "變差", "undecided": "未定", "pass": "通過", "fail": "不通過"}


def rows(path):
    if not os.path.exists(path):
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def million(value):
    return f"{value / 1e6:.2f}M"


def why(row):
    """Short reason a run did not pass: the general rules broken and how many of the task's own requirements."""
    grade = row.get("grade") or {}
    if grade.get("pass"):
        return ""
    if not grade.get("deliverable", True) or grade.get("error") == "no deliverable":
        return "沒交 output.pptx"
    if grade.get("error"):
        return "開不起來或算繪不出來"
    rules = sorted({f["rule"] for f in grade.get("failures", [])})
    task = len(grade.get("task_failures", []))
    parts = ([" ".join(rules)] if rules else []) + ([f"題目要求 {task} 項"] if task else [])
    return "；".join(parts)


def main():
    state, judge = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
    tasks, idle = judge["tasks"], judge["idle_tasks"]
    data = {cell: {(r["unit"], r["arm"]): r for r in rows(os.path.join(state, f"rows-main-{cell}.jsonl"))}
            for cell in CELLS}
    short = {task: f"T{place + 1}" for place, task in enumerate(tasks)}
    print("## 每題結果（過＝機械檢查全過）\n")
    for cell in CELLS:
        print(f"### {cell} 格\n")
        print("| 題 | " + " | ".join(ARMS) + " |")
        print("|---|" + "---|" * len(ARMS))
        for task in tasks:
            cells = []
            for arm in ARMS:
                row = data[cell].get((task, arm))
                cells.append("（沒跑）" if row is None else "過" if row["passed"] else "沒過")
            print(f"| {short[task]} | " + " | ".join(cells) + " |")
        print()
    print("## 沒過的原因\n")
    print("| 格 | 題 | 組 | 原因 |")
    print("|---|---|---|---|")
    for cell in CELLS:
        for task in tasks:
            for arm in ARMS:
                row = data[cell].get((task, arm))
                if row is not None and not row["passed"]:
                    print(f"| {cell} | {short[task]} | {arm} | {why(row)} |")
    print("\n## 每格的分類和閒置條件\n")
    print("| 候選 | 格 | 新過 | 確定退步 | 漏掉 | 頂到天花板 | 這一格 | 閒置 |")
    print("|---|---|---|---|---|---|---|---|")
    for cand, found in judge["candidates"].items():
        for cell in CELLS:
            entry = found["cells"].get(cell)
            if entry is None:
                print(f"| {cand} {NAMES[cand]} | {cell} | | | | | 未完成 | |")
                continue
            c = entry["counts"]
            print(f"| {cand} {NAMES[cand]} | {cell} | {c['new pass']} | {c['regression']} | {c['missed']} | "
                  f"{c['ceiling']} | {ZH[entry['result']]} | {ZH.get(found['idle'], '—')} |")
    print("\n## 閒置條件的每一對（啟動 token：第一次呼叫模型的輸入，含快取）\n")
    print("| 候選 | 格 | 題 | N | S | S÷N | N 做對 | S 做對 | 結果 | 用到候選 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for cand, found in judge["candidates"].items():
        for key, pair in sorted((found.get("idle_pairs") or {}).items()):
            cell, task = key.split("/")
            used = pair.get("used") or {}
            touched = bool((used.get("tool_calls_naming_a_candidate") or {})) or any(
                name in (used.get("skills_loaded") or []) for name in NAMES.values())
            print(f"| {cand} | {cell} | {task} | {pair['n_tokens']:,} | {pair['s_tokens']:,} | {pair['ratio']} | "
                  f"{'是' if pair['n_solved'] else '否'} | {'是' if pair['s_solved'] else '否'} | "
                  f"{ZH[pair['result']]}{'：' + pair['why'] if pair['why'] else ''} | {'有' if touched else '沒有'} |")
    print("\n## 判定\n")
    print("| 候選 | 判定 | 依據 |")
    print("|---|---|---|")
    for cand, found in judge["candidates"].items():
        print(f"| {cand} {NAMES[cand]} | {found['verdict_zh']} | {'; '.join(found['why'])} |")
    print("\n## token（logical：輸入＋輸出＋快取；括號內不含快取讀取）\n")
    print("| 格 | 組 | run 數 | 合計 | 每次平均 |")
    print("|---|---|---|---|---|")
    for cell in CELLS:
        for arm, entry in sorted(judge["tokens"][cell].items()):
            print(f"| {cell} | {arm} | {entry['runs']} | {million(entry['logical'])}（{million(entry['noncache'])}） | "
                  f"{million(entry['logical'] / max(1, entry['runs']))} |")
    print("\n## 候選有沒有被用到（作答題；看 tool 呼叫裡有沒有提到候選）\n")
    print("| 格 | 組 | 4 題裡用到候選的題數 | 每題平均秒數 |")
    print("|---|---|---|---|")
    for cell in CELLS:
        for arm in ARMS:
            mine = [data[cell][(t, arm)] for t in tasks if (t, arm) in data[cell]]
            if not mine:
                continue
            key = {"P1": "officecli", "P2": "huashu-design", "P3": "professional-pptx"}.get(arm)
            used = sum(1 for r in mine if key and (((r.get("session") or {}).get("evidence") or {}).get(key)
                                                   or key in ((r.get("session") or {}).get("skills") or [])))
            print(f"| {cell} | {arm} | {used if key else '—'} | {sum(r['seconds'] for r in mine) / len(mine):.0f} |")
    for tag in ("calibration", "main"):
        for cell in CELLS:
            failed = [a for a in rows(os.path.join(state, f"attempts-{tag}-{cell}.jsonl")) if a.get("not_run")]
            if failed:
                print(f"\n沒計分的嘗試（{tag}／{cell}）：" + "；".join(
                    f"{a['unit']}/{a['arm']} 第 {a['attempt']} 次：{a['not_run'][:60]}" for a in failed))


if __name__ == "__main__":
    main()
