#!/usr/bin/env python3
"""Stage 0 for OAW 2.0.1 work item W2: the code map against a grep baseline, with no model tokens.

  stage0_v201.py run --repo NAME=DIR --commit NAME=SHA --questions NAME=FILE --truth NAME=FILE \\
      [--repo ...] --cache-root DIR --out RESULTS.json [--md SUMMARY.md]

For each repository (a read-only checkout or `git archive` of the named commit):

(a) find: every frozen question's text goes to `code_index.py find --limit 5` (arm S) and to
    `native_search.py find --limit 5` (arm R, the grep baseline). Gold files are the files named in
    the question's facts (`where`). A gold file counts when it is in the arm's top 5 and its path is
    also in the arm's text output. Hit rates are reported per question type; the D24 rule is checked:
    S beats R by at least 0.15 in some type without more text output bytes.
(b) callers: every symbol of a hand-built truth set goes to `code_index.py callers --limit 1000`;
    call-site recall and rows that are not true callers are counted, for all rows and for resolved
    rows only. Arm R's `callers` is scored at file level beside it.
(c) cost: index build time and peak RSS (cold with the default worker processes, and in one
    process), warm query times, overview size, and cache size on disk.

Every measured command runs in its own wrapper process that reports wall time and the peak RSS of
the largest process it waited for (resource.getrusage(RUSAGE_CHILDREN).ru_maxrss). Results hold
repository-relative paths only. Standard library only; POSIX (resource) for the RSS figures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CODE_INDEX = REPO / "scripts" / "code_index.py"
NATIVE = HERE / "native_search.py"
TOP = 5
PASS_DELTA = 0.15
CALLER_LIMIT = 1000
TIMEOUT = 1800
WRAPPER = r"""
import json, resource, subprocess, sys, time
command, out = json.loads(sys.argv[1]), sys.argv[2]
started = time.perf_counter()
with open(out, "wb") as stdout:
    process = subprocess.run(command, stdout=stdout, stderr=subprocess.PIPE, timeout=float(sys.argv[3]))
seconds = time.perf_counter() - started
peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
if sys.platform == "darwin":
    peak //= 1024
print(json.dumps({"seconds": round(seconds, 3), "peak_rss_kb": peak, "returncode": process.returncode,
                  "stderr": process.stderr.decode("utf-8", "replace")[-2000:]}))
"""
SERIAL = ("import sys; sys.path.insert(0, sys.argv[1]); import code_index; "
          "code_index.PARALLEL_MIN_FILES = 10 ** 9; sys.exit(code_index.main(sys.argv[2:]))")


def measure(command, scratch):
    """Run command under the wrapper: (stdout bytes, metrics)."""
    out = Path(scratch) / "stdout.bin"
    wrapped = subprocess.run([sys.executable, "-c", WRAPPER, json.dumps([str(part) for part in command]), str(out),
                              str(TIMEOUT)], capture_output=True, text=True, timeout=TIMEOUT + 60)
    if wrapped.returncode:
        raise SystemExit(f"wrapper failed: {wrapped.stderr}")
    metrics = json.loads(wrapped.stdout)
    data = out.read_bytes().replace(b"\r\n", b"\n")
    if metrics["returncode"]:
        raise SystemExit(f"command failed ({metrics['returncode']}): {command[:4]} ...\n{metrics['stderr']}")
    return data, metrics


def code_index(sub, args, root, cache, as_json=False):
    return [sys.executable, CODE_INDEX, sub, *args, "--root", root, "--cache", cache] + (["--json"] if as_json else [])


def native(sub, args, root, as_json=False):
    return [sys.executable, NATIVE, sub, *args, "--root", root, "--limit", str(TOP if sub == "find" else CALLER_LIMIT)] + (
        ["--json"] if as_json else [])


def corpus_identity(root):
    paths = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        paths.extend(os.path.relpath(os.path.join(directory, name), root).replace(os.sep, "/") for name in filenames)
    paths.sort()
    return {"files": len(paths), "file_list_sha256": hashlib.sha256("".join(p + "\n" for p in paths).encode()).hexdigest()}


def gold_files(question):
    """Ordered unique files named by a question's facts, with the facts that name each."""
    files, facts = [], []
    for fact in question["facts"]:
        named = []
        for part in fact["where"].split(";"):
            path = part.split("::", 1)[0].strip().split(" ", 1)[0]
            if path and path not in named:
                named.append(path)
        facts.append({"id": fact["id"], "essential": bool(fact.get("essential")), "files": named})
        files.extend(path for path in named if path not in files)
    return files, facts


def ranked_paths(data):
    report = json.loads(data.decode("utf-8"))
    paths = []
    for row in report.get("results", []):
        path = row["path"].replace("\\", "/")
        if path not in paths:
            paths.append(path)
    return paths


def shown(path, text):
    return path in text.replace("\\", "/")


def score_find(root, cache, questions, scratch):
    rows = []
    for question in questions:
        files, facts = gold_files(question)
        row = {"id": question["id"], "type": question["type"], "gold_files": files,
               "missing_gold": [path for path in files if not (Path(root) / path).is_file()]}
        for arm in ("S", "R"):
            make = (lambda as_json: code_index("find", [question["question"], "--limit", str(TOP)], root, cache, as_json)) \
                if arm == "S" else (lambda as_json: native("find", [question["question"]], root, as_json))
            text, text_metrics = measure(make(False), scratch)
            data, _ = measure(make(True), scratch)
            top = ranked_paths(data)[:TOP]
            decoded = text.decode("utf-8", "replace")
            counted = [path for path in top if shown(path, decoded)]
            hits = [path for path in files if path in counted]
            row[arm] = {"top5": top, "hits": hits, "file_hit_rate": round(len(hits) / len(files), 4),
                        "facts_hit": sum(1 for fact in facts if set(fact["files"]) & set(counted)),
                        "essential_facts_hit": sum(1 for fact in facts if fact["essential"] and set(fact["files"]) & set(counted)),
                        "text_bytes": len(text), "seconds": text_metrics["seconds"]}
        row["facts"], row["essential_facts"] = len(facts), sum(1 for fact in facts if fact["essential"])
        rows.append(row)
    classes = {}
    for row in rows:
        entry = classes.setdefault(row["type"], {"questions": [], "gold_files": 0, "S_hits": 0, "R_hits": 0,
                                                "S_bytes": 0, "R_bytes": 0, "facts": 0, "S_facts": 0, "R_facts": 0})
        entry["questions"].append(row["id"])
        entry["gold_files"] += len(row["gold_files"])
        entry["facts"] += row["facts"]
        for arm in ("S", "R"):
            entry[f"{arm}_hits"] += len(row[arm]["hits"])
            entry[f"{arm}_bytes"] += row[arm]["text_bytes"]
            entry[f"{arm}_facts"] += row[arm]["facts_hit"]
    for entry in classes.values():
        for arm in ("S", "R"):
            entry[f"{arm}_top5_file_hit_rate"] = round(entry[f"{arm}_hits"] / entry["gold_files"], 4)
        entry["delta"] = round(entry["S_top5_file_hit_rate"] - entry["R_top5_file_hit_rate"], 4)
        entry["passes_d24"] = entry["delta"] >= PASS_DELTA - 1e-9 and entry["S_bytes"] <= entry["R_bytes"]
        entry["passes_d24_with_two_more_hits"] = entry["passes_d24"] and entry["S_hits"] - entry["R_hits"] >= 2
    gate = {"rule": f"S top-5 file hit rate - R >= {PASS_DELTA} in some question type, S text bytes <= R text bytes",
            "passed": any(entry["passes_d24"] for entry in classes.values()),
            "passed_with_two_more_hits": any(entry["passes_d24_with_two_more_hits"] for entry in classes.values())}
    return {"questions": rows, "by_type": classes, "gate": gate}


SITE = re.compile(r"^([^\s:]+):(\d+)")


def sites_of(entries):
    found = set()
    for entry in entries:
        match = SITE.match(entry["site"] if isinstance(entry, dict) else entry)
        if match:
            found.add((match.group(1), int(match.group(2))))
    return found


def check_truth(root, truth):
    """Truth entries whose file:line does not exist or does not contain the symbol's name."""
    problems = []
    for item in truth["symbols"]:
        name = item["symbol"].split("::", 1)[1].rsplit(".", 1)[-1]
        for path, line in sorted(sites_of(item["callers"])):
            try:
                text = (Path(root) / path).read_text(encoding="utf-8", errors="replace").split("\n")[line - 1]
            except (OSError, IndexError):
                problems.append(f"{item['symbol']}: {path}:{line} missing")
                continue
            if name not in text:
                problems.append(f"{item['symbol']}: {path}:{line} does not contain {name}")
    return problems


def score_callers(root, cache, truth, scratch):
    rows = []
    for item in truth["symbols"]:
        expected = sites_of(item["callers"])
        dynamic = sites_of(item.get("dynamic", []))
        data, metrics = measure(code_index("callers", [item["symbol"], "--limit", str(CALLER_LIMIT)], root, cache, True), scratch)
        report = json.loads(data.decode("utf-8"))
        everything = {(row["path"], row["line"]) for row in report["results"]}
        resolved = {(row["path"], row["line"]) for row in report["results"] if row["resolved"]}
        native_data, native_metrics = measure(native("callers", [item["symbol"]], root, True), scratch)
        native_files = set(ranked_paths(native_data))
        true_files = {path for path, _ in expected}
        s_files = {path for path, _ in everything}
        rows.append({
            "symbol": item["symbol"], "question": item.get("question"), "true_callers": len(expected),
            "targets": report["targets"], "returned": len(everything), "resolved_returned": len(resolved),
            "found": len(expected & everything), "found_resolved": len(expected & resolved),
            "wrong_resolved": len(resolved - expected), "wrong_unresolved": len((everything - resolved) - expected),
            "returned_dynamic": len(everything & dynamic), "complete": report.get("complete"),
            "truncated": report.get("truncated"), "missed": sorted(f"{p}:{n}" for p, n in expected - everything),
            "wrong_resolved_sites": sorted(f"{p}:{n}" for p, n in resolved - expected)[:20],
            "seconds": metrics["seconds"],
            "files": {"true": len(true_files), "S_found": len(true_files & s_files), "S_wrong": len(s_files - true_files),
                      "R_found": len(true_files & native_files), "R_wrong": len(native_files - true_files),
                      "R_seconds": native_metrics["seconds"]}})
    total = sum(row["true_callers"] for row in rows)
    summary = {
        "symbols": len(rows), "true_callers": total,
        "recall_all_rows": round(sum(row["found"] for row in rows) / total, 4) if total else None,
        "recall_resolved_rows": round(sum(row["found_resolved"] for row in rows) / total, 4) if total else None,
        "wrong_resolved_rows": sum(row["wrong_resolved"] for row in rows),
        "resolved_rows": sum(row["resolved_returned"] for row in rows),
        "wrong_unresolved_rows": sum(row["wrong_unresolved"] for row in rows),
        "unresolved_rows": sum(row["returned"] - row["resolved_returned"] for row in rows),
        "returned_dynamic_rows": sum(row["returned_dynamic"] for row in rows),
        "symbols_with_full_recall_all_rows": sum(1 for row in rows if row["found"] == row["true_callers"]),
        "file_level": {key: sum(row["files"][key] for row in rows) for key in ("true", "S_found", "S_wrong", "R_found", "R_wrong")},
    }
    summary["meets_0_95_all_rows"] = summary["recall_all_rows"] is not None and summary["recall_all_rows"] >= 0.95
    summary["meets_0_95_resolved_rows"] = summary["recall_resolved_rows"] is not None and summary["recall_resolved_rows"] >= 0.95
    return {"symbols": rows, "summary": summary}


def cache_bytes(directory):
    return sum(path.stat().st_size for path in Path(directory).glob("code-index-*.json"))


def score_cost(root, cache, scratch, probe_symbol, probe_question):
    cost = {}
    shutil.rmtree(cache, ignore_errors=True)
    os.makedirs(cache)
    data, metrics = measure(code_index("stats", [], root, cache, True), scratch)
    stats = json.loads(data.decode("utf-8"))
    cost["cold_build"] = {"seconds": metrics["seconds"], "peak_rss_mb": round(metrics["peak_rss_kb"] / 1024, 1),
                          "worker_processes": "up to 8", "index_seconds_reported": stats["build_seconds"]}
    cost["cache_bytes"] = cache_bytes(cache)
    cost["cache_mb"] = round(cost["cache_bytes"] / 1e6, 1)
    cost["files"], cost["kinds"], cost["symbols"], cost["imports"], cost["calls"] = (
        stats["files"], stats["kinds"], stats["symbols"], stats["imports"], stats["calls"])
    _, metrics = measure([sys.executable, "-c", SERIAL, REPO / "scripts", "stats", "--root", root, "--no-cache"], scratch)
    cost["one_process_build_no_cache"] = {"seconds": metrics["seconds"], "peak_rss_mb": round(metrics["peak_rss_kb"] / 1024, 1)}
    for name, (sub, args) in {"stats": ("stats", []), "callers": ("callers", [probe_symbol]),
                              "find": ("find", [probe_question]), "overview": ("overview", [])}.items():
        data, metrics = measure(code_index(sub, args, root, cache), scratch)
        cost[f"warm_{name}"] = {"seconds": metrics["seconds"], "peak_rss_mb": round(metrics["peak_rss_kb"] / 1024, 1)}
        if name == "overview":
            cost["overview_chars"] = len(data.decode("utf-8").rstrip("\n"))
            cost["overview_bytes"] = len(data)
            cost["overview_text"] = data.decode("utf-8")
    return cost


def pairs(values):
    found = {}
    for value in values or ():
        name, separator, rest = value.partition("=")
        if not separator:
            raise SystemExit(f"expected NAME=VALUE: {value}")
        found[name] = rest
    return found


def markdown(results):
    lines = []
    for name, repo in results["repositories"].items():
        cost, find, callers = repo["cost"], repo["find"], repo["callers"]["summary"]
        lines += [f"## {name} ({repo['commit'][:7]}, {repo['corpus']['files']} files)", "",
                  "| question type | questions | gold files | S top-5 hits | R top-5 hits | S rate | R rate | delta | S bytes | R bytes | D24 |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for kind, entry in sorted(find["by_type"].items()):
            lines.append(f"| {kind} | {', '.join(entry['questions'])} | {entry['gold_files']} | {entry['S_hits']} | "
                         f"{entry['R_hits']} | {entry['S_top5_file_hit_rate']:.2f} | {entry['R_top5_file_hit_rate']:.2f} | "
                         f"{entry['delta']:+.2f} | {entry['S_bytes']} | {entry['R_bytes']} | "
                         f"{'pass' if entry['passes_d24'] else 'fail'} |")
        lines += ["", f"callers: {callers['symbols']} symbols, {callers['true_callers']} true call sites; recall "
                      f"{callers['recall_all_rows']} (all rows), {callers['recall_resolved_rows']} (resolved rows); "
                      f"wrong rows: {callers['wrong_resolved_rows']} of {callers['resolved_rows']} resolved, "
                      f"{callers['wrong_unresolved_rows']} of {callers['unresolved_rows']} unresolved; file level "
                      f"S {callers['file_level']['S_found']}/{callers['file_level']['true']} (wrong "
                      f"{callers['file_level']['S_wrong']}), grep {callers['file_level']['R_found']}/"
                      f"{callers['file_level']['true']} (wrong {callers['file_level']['R_wrong']})", "",
                  f"cost: cold build {cost['cold_build']['seconds']} s, peak RSS {cost['cold_build']['peak_rss_mb']} MB "
                  f"(one process, no cache: {cost['one_process_build_no_cache']['seconds']} s, "
                  f"{cost['one_process_build_no_cache']['peak_rss_mb']} MB); cache {cost['cache_mb']} MB; overview "
                  f"{cost['overview_chars']} chars; warm stats {cost['warm_stats']['seconds']} s / "
                  f"{cost['warm_stats']['peak_rss_mb']} MB, callers {cost['warm_callers']['seconds']} s / "
                  f"{cost['warm_callers']['peak_rss_mb']} MB, find {cost['warm_find']['seconds']} s / "
                  f"{cost['warm_find']['peak_rss_mb']} MB, overview {cost['warm_overview']['seconds']} s / "
                  f"{cost['warm_overview']['peak_rss_mb']} MB", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    for flag in ("--repo", "--commit", "--questions", "--truth", "--origin"):
        run.add_argument(flag, action="append", metavar="NAME=VALUE")
    run.add_argument("--cache-root", required=True, help="local (not network) directory for index caches")
    run.add_argument("--out", required=True)
    run.add_argument("--md")
    args = parser.parse_args(argv)
    repos, commits, questions, truths, origins = map(pairs, (args.repo, args.commit, args.questions, args.truth, args.origin))
    results = {"schema_version": 1, "title": "OAW 2.0.1 W2 Stage 0 (0 model tokens)",
               "code_index_sha256": hashlib.sha256(CODE_INDEX.read_bytes()).hexdigest(),
               "native_search_sha256": hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
               "platform": f"{platform.system()} {platform.release()}, Python {platform.python_version()}, "
                           f"{os.cpu_count()} CPUs", "repositories": {}}
    for name, root in repos.items():
        root = os.path.abspath(root)
        if name in origins:
            head = subprocess.run(["git", "-C", origins[name], "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            if head != commits[name]:
                raise SystemExit(f"{name}: origin HEAD {head} is not {commits[name]}")
        question_file = json.loads(Path(questions[name]).read_text(encoding="utf-8"))
        truth = json.loads(Path(truths[name]).read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=args.cache_root, prefix=f"stage0-{name}-") as scratch:
            cache = os.path.join(scratch, "cache")
            entry = {"commit": commits[name], "corpus": corpus_identity(root),
                     "questions_sha256": hashlib.sha256(Path(questions[name]).read_bytes()).hexdigest(),
                     "truth_sha256": hashlib.sha256(Path(truths[name]).read_bytes()).hexdigest(),
                     "truth_problems": check_truth(root, truth)}
            entry["cost"] = score_cost(root, cache, scratch, truth["symbols"][0]["symbol"],
                                       question_file["questions"][0]["question"])
            entry["find"] = score_find(root, cache, question_file["questions"], scratch)
            entry["callers"] = score_callers(root, cache, truth, scratch)
        results["repositories"][name] = entry
        print(f"{name}: done", file=sys.stderr)
    Path(args.out).write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.md:
        Path(args.md).write_text(markdown(results), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
