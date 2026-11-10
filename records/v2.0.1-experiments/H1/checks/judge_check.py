"""Synthetic rows through h1_judge: every owner word, an unfinished cell, the L control and the memory step."""
import hashlib, importlib.util, json, subprocess, sys, tempfile, os, types
H = sys.argv[1]; STATS = sys.argv[2]
spec = importlib.util.spec_from_file_location("h1_judge", os.path.join(H, "h1_judge.py"))
J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
stats = J.load_stats(STATS)
UNITS = {k: [f"{k.lower()}{i}" for i in range(1, 5)] for k in "ABC"}

def row(cell, arm, unit, klass, score, tokens, recall=None, freeze="f1", **extra):
    r = {"cell": cell, "arm": arm, "unit": unit, "klass": klass, "tag": "main", "score": score, "attempt": 1,
         "started": f"{cell}-{arm}-{unit}", "root": f"runs/main/{cell}/{unit}/{arm}/a1",
         "tokens_total": tokens, "tokens_noncache": tokens // 10, "freeze_sha256": freeze, "flags": [],
         "grade": {"recall": recall}, "sessions": [{"evidence": {"oaw": 1} if arm == "O" else {}, "skills": [],
                                                    "agents": 0, "memory_files": {}}]}
    r.update(extra)
    return r

def cell(cell, o, n1, n2, tok=(100, 100, 100), recall=(True, True, True), classes="ABC", l=None):
    """o, n1, n2: class -> score for all its units (or a list of four)."""
    rows = []
    for k in classes:
        for i, u in enumerate(UNITS[k]):
            pick = lambda v: v[k][i] if isinstance(v[k], list) else v[k]
            rec = lambda j: (recall[j][i] if isinstance(recall[j], list) else recall[j]) if k == "B" else None
            rows.append(row(cell, "O", u, k, pick(o), tok[0] * 1000, rec(0)))
            rows.append(row(cell, "N1", u, k, pick(n1), tok[1] * 1000, rec(1)))
            rows.append(row(cell, "N2", u, k, pick(n2), tok[2] * 1000, rec(2)))
            if l is not None and k in "BC":
                rows.append(row(cell, "L", u, k, pick(l), tok[1] * 1000, None))
    return rows

same = {k: 1.0 for k in "ABC"}
FROZEN = types.SimpleNamespace(units=UNITS)
def one(rows, name="claude", attempts=None):
    return J.judge_cell(stats, FROZEN, rows, rows if attempts is None else attempts, name)[0]

checks = []
def expect(label, got, want):
    checks.append((label, got == want, got, want))

c = one(cell("claude", same, same, same, tok=(130, 100, 100)))
expect("equal scores, 1.3x tokens", (c["quality"]["Q"], c["word"], c["outcome"], c["cost"]["protocol"]["class"]),
       ("equivalent", "雞肋", "該改成選配", "within"))
expect("ceiling flagged", c["direction"]["A"]["ceiling_note"], "頂到天花板，只看得出變差")
expect("memory at ceiling", c["memory"]["word"], "都記得，這組題目分不出來（天花板，未證等價）")
c = one(cell("claude", same, same, same, tok=(100, 100, 100)))
expect("equal scores, equal tokens", (c["word"], c["token_sentence"], c["outcome"]), ("沒差", "沒有確實變多", "該改成選配"))
c = one(cell("claude", same, same, same, tok=(60, 100, 100)))
expect("equal scores, fewer tokens", (c["word"], c["token_sentence"], c["outcome"], c["cost"]["protocol"]["class"]),
       ("沒差", "token 變少", "留在預設站得住", "cheaper"))
c = one(cell("claude", same, same, same, tok=(115, 80, 100)))
expect("ratio 1.28 against a native band of 1.25", (c["word"], round(c["cost"]["batch"]["band"], 2)), ("雞肋", 1.25))
c = one(cell("claude", same, same, same, tok=(110, 80, 100)))
expect("ratio 1.22 inside the native band 1.25", c["word"], "沒差")
c = one(cell("claude", same, same, same, tok=(200, 100, 100)))
expect("equal scores, 2x tokens", (c["word"], c["outcome"], c["cost"]["protocol"]["class"]), ("雞肋", "提案移出預設", "over"))
c = one(cell("claude", {"A": 1.0, "B": 1.0, "C": 0.0}, same, same))
expect("class C collapses", (c["quality"]["Q"], c["word"], c["outcome"]), ("worse", "更慘", "提案移出預設"))
expect("names the class", c["quality"]["why"], "class C is worse")
half = {k: 0.5 for k in "ABC"}
c = one(cell("claude", same, half, half, tok=(200, 100, 100)))
expect("better and over the cap", (c["quality"]["Q"], c["word"], c["outcome"], c["token_sentence"]),
       ("better", "有幫助", "該改成選配", "token 變多"))
c = one(cell("claude", same, half, half))
expect("better within the cap", (c["word"], c["outcome"]), ("有幫助", "留在預設站得住"))
c = one(cell("claude", {"A": 1.0, "B": 1.0, "C": 0.85}, same, same))
expect("one class 0.15 lower, not worse", (c["quality"]["Q"], c["word"], c["outcome"], c["quality"]["why"][:5]),
       ("undetermined", "未定", "能力未定", "類別不一致"))
expect("undetermined carries detail", sorted(c["undetermined_detail"]), ["ci95", "mde", "point"])
c = one(cell("claude", {"A": 1.0, "B": 1.0, "C": 0.9}, same, same))
expect("one class exactly 0.10 lower", c["quality"]["Q"], "undetermined")
noisy = {"A": [1.0, 0.0, 1.0, 0.0], "B": [0.0, 1.0, 0.0, 1.0], "C": [1.0, 0.0, 0.0, 1.0]}
c = one(cell("claude", same, noisy, same))
expect("noisy native widens the floor", (round(c["quality"]["floor"], 3) == 0.5, c["quality"]["Q"]), (True, "undetermined"))
c = one(cell("claude", same, same, same, recall=(True, False, False)))
expect("memory better", (c["memory"]["word"], c["memory"]["remembered"]), ("記憶變好", {"N1": 0, "N2": 0, "O": 4}))
c = one(cell("claude", same, same, same, recall=(False, True, True)))
expect("memory worse", c["memory"]["word"], "記憶變差")
c = one(cell("claude", same, same, same, recall=([True, True, True, False], True, [True, True, False, True])))
expect("memory undetermined", c["memory"]["word"], "未定")
c = one(cell("claude", same, same, same, classes="AB"))
expect("class C missing", (c["status"], "word" in c, c["classes_done"], "composite" in c["quality"]),
       ("未完成", False, ["A", "B"], False))
rows = cell("claude", same, same, same)[:-1]
expect("one run missing", one(rows)["why"], ["class C: 3 of 4 units have N1, N2 and O"])
c = one(cell("codex", same, same, same, l={"B": 0.5, "C": 0.5}), "codex")
expect("L control", (c["L_control"]["O_vs_L"]["class"], c["L_control"]["L_vs_N"]["class"], c["L_control"]["units"]),
       ("better", "worse", 8))
expect("usage", (c["usage"]["O"]["touched_oaw"], c["usage"]["N1"]["touched_oaw"]), (12, 0))
a = cell("claude", same, same, same, tok=(130, 100, 100)); b = cell("codex", {"A": 1.0, "B": 1.0, "C": 0.0}, same, same)
both = {"claude": one(a), "codex": one(b, "codex")}
m = J.merge(both)
expect("merge takes the lower", (m["word"], m["outcome"], m["cells_agree"]), ("更慘", "提案移出預設", False))
both = {"claude": one(cell("claude", same, same, same, classes="AB")), "codex": one(b, "codex")}
expect("merge with an unfinished cell", (J.merge(both)["word"], J.merge(both)["note"]), ("未完成", "only the codex cell is complete"))
x = J.across({"claude": J.table(a, "claude")[0], "codex": J.table(b, "codex")[0]})
expect("across cells", (x["no_difference_in_both"], x["difference_in_one_cell"], x["opposite"]), (8, 4, 0))
attempts = [dict(row("claude", "O", "a1", "A", None, 5000), not_run="s1: 0 tokens")]
expect("tokens of attempts that did not count", J.not_counted(attempts, "claude"), {"O": {"attempts": 1, "tokens_total": 5000, "tokens_noncache": 500, "tokens_unknown": 0}})
rows = cell("claude", same, same, same); rows[0]["sessions"][0]["skills"] = None
c = one(rows)
expect("skill use unknown when a session could not be read (#14)", (c["usage"]["O"]["used_skill"], c["usage"]["N1"]["used_skill"]), ("未知", 0))
rows = cell("claude", same, same, same); rows[0]["sessions"][0]["listed_skills"] = ["oaw-review"]
expect("listed skills unknown unless every session has the list", one(rows)["usage"]["O"]["listed_oaw_skills"], "未知")
for label, bad_attempts in (("attempts not given for a cell with rows (#15)", []),
                            ("a counted attempt missing from the rows (#15)", a + [dict(a[0], root="other")]),
                            ("a row missing from the attempts (#15)", a[1:])):
    try:
        one(a, attempts=bad_attempts); checks.append((label, False, "accepted", "refused"))
    except SystemExit as error:
        checks.append((label, True, str(error), ""))
for label, bad in (("duplicate row", a + [a[0]]), ("pilot row", [dict(a[0], tag="pilot")])):
    try:
        one(bad); checks.append((label, False, "accepted", "refused"))
    except SystemExit as error:
        checks.append((label, True, str(error), ""))
def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

ARMS = {"claude": {k: ["N1", "O", "N2"] for k in "ABC"},
        "codex": {"A": ["N1", "O", "N2"], "B": ["N1", "O", "L", "N2"], "C": ["N1", "O", "L", "N2"]}}

def bound(tmp, rows, mutate_freeze=None):
    """Unit files and a FREEZE.json for the synthetic rows, and the rows bound to them."""
    paths, entries = [], {}
    for k in "ABC":
        units = [{"id": u, "type": "t"} for u in UNITS[k]]
        path = os.path.join(tmp, f"units_{k}.json")
        json.dump({"klass": k, "units": units}, open(path, "w"), sort_keys=True)
        paths.append(path)
        entries.update({u["id"]: J.unit_digest(u) for u in units})
    freeze = {"eval_stats_sha256": sha(STATS), "files": {"h1_judge.py": sha(os.path.join(H, "h1_judge.py")),
              "h1_run.py": "r1"}, "units": {k: sha(p) for k, p in zip("ABC", paths)}, "launch": {"arms": ARMS}}
    if mutate_freeze:
        mutate_freeze(freeze)
    fpath = os.path.join(tmp, "FREEZE.json")
    json.dump(freeze, open(fpath, "w"))
    out = [dict(r, freeze_sha256=sha(fpath), units_sha256=freeze["units"][r["klass"]], unit_sha256=entries[r["unit"]],
                runner_sha256="r1") for r in rows]
    return fpath, paths, out

def start_of(r):
    keys = ("tag", "cell", "klass", "unit", "arm", "attempt", "root", "freeze_sha256", "units_sha256", "unit_sha256",
            "runner_sha256", "candidate_sha256")
    return dict({k: r.get(k) for k in keys}, event="start")

def command(tmp, fpath, paths, rows, attempts, stats=STATS, starts=None):
    rpath, apath, spath = (os.path.join(tmp, n) for n in ("rows.jsonl", "attempts.jsonl", "starts.jsonl"))
    open(rpath, "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    open(apath, "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in attempts))
    starts = [start_of(r) for r in attempts] if starts is None else starts
    open(spath, "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in starts))
    argv = [sys.executable, os.path.join(H, "h1_judge.py"), "--stats", stats, "--freeze", fpath, "--units", *paths,
            "--rows", rpath, "--attempts", apath, "--starts", spath]
    return subprocess.run(argv, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

with tempfile.TemporaryDirectory() as tmp:
    fpath, paths, rows = bound(tmp, a + b)
    done = command(tmp, fpath, paths, rows, rows)
    out = json.loads(done.stdout) if done.returncode == 0 else {}
    expect("command line", (done.returncode, out.get("merged", {}).get("word"), done.stderr[-200:]), (0, "更慘", ""))
    refusals = {
        "a row of another FREEZE.json (#7)": lambda r: r[0].update(freeze_sha256="x"),
        "a row of another unit version (#7)": lambda r: r[0].update(unit_sha256="x"),
        "a row of another unit file (#7)": lambda r: r[0].update(units_sha256="x"),
        "a row of another runner (#7)": lambda r: r[0].update(runner_sha256="x"),
        "an L row in the claude cell (#7)": lambda r: r.append(dict(r[0], arm="L", started="l")),
        "an L row on class A in the codex cell (#7)": lambda r: r.append(dict([x for x in r if x["cell"] == "codex"][0], arm="L", started="l")),
        "a unit outside the frozen files (#7)": lambda r: r.append(dict(r[0], unit="z9", started="z")),
    }
    for label, change in refusals.items():
        copy = [dict(r) for r in rows]
        change(copy)
        done = command(tmp, fpath, paths, copy, copy)
        expect(label, (done.returncode != 0, "Traceback" in done.stderr), (True, False))
    for label, mutate in (("another eval_stats.py (#7)", lambda f: f.update(eval_stats_sha256="x")),
                          ("another judge (#7)", lambda f: f["files"].update({"h1_judge.py": "x"})),
                          ("a unit file that is not frozen (#7)", lambda f: f["units"].update(A="x"))):
        fpath2, paths2, rows2 = bound(tmp, a + b, mutate)
        done = command(tmp, fpath2, paths2, rows2, rows2)
        expect(label, (done.returncode != 0, "Traceback" in done.stderr), (True, False))
    fpath, paths, rows = bound(tmp, a + b)
    done = subprocess.run([sys.executable, os.path.join(H, "h1_judge.py"), "--stats", STATS, "--freeze", fpath,
                           "--units", *paths, "--rows", os.path.join(tmp, "rows.jsonl")], capture_output=True, text=True)
    expect("--attempts is required (#15)", done.returncode, 2)
    fpath, paths, rows = bound(tmp, a + b)
    failed = dict(rows[0], attempt=0, root="runs/failed", not_run="s1: 0 tokens", tokens_total=7000, tokens_noncache=700)
    lost = start_of(dict(rows[0], attempt=9, root="runs/lost"))
    done = command(tmp, fpath, paths, rows, rows + [failed], starts=[start_of(r) for r in rows + [failed]] + [lost])
    out = json.loads(done.stdout) if done.returncode == 0 else {"stderr": done.stderr[-300:]}
    expect("an interrupted start is reported with unknown tokens; failed cost always reported (round 3 #9)",
           out.get("cells", {}).get("claude", {}).get("attempts_not_counted", {}).get("O") or out.get("stderr"),
           {"attempts": 2, "tokens_total": 7000, "tokens_noncache": 700, "tokens_unknown": 1})
    done = command(tmp, fpath, paths, rows, rows, starts=rows)
    expect("counted rows given as start records are refused (escalation, astra)", (done.returncode != 0, "not a start record" in done.stderr), (True, True))
    done = command(tmp, fpath, paths, rows, rows + [rows[0]])
    expect("an attempt given twice is refused (round 3 #9)", (done.returncode != 0, "given twice" in done.stderr), (True, True))
    done = command(tmp, fpath, paths, rows, rows, starts=[start_of(r) for r in rows[1:]])
    expect("an attempt without a start is refused (round 3 #9)", (done.returncode != 0, "without a start" in done.stderr), (True, True))
    # Codex's round 3 counter-example: exact scores must decide, not stored rounded ones
    def graded(r, passed, n):
        return dict(r, score=round(passed / n, 4), grade=dict(r["grade"], passed=passed, n=n, suite_regression=False))
    ex = cell("claude", same, same, same)
    cpairs = {"c1": ((2, 12), (1, 12)), "c2": ((11, 12), (12, 12)), "c3": ((6, 10), (10, 10)), "c4": ((1, 1), (1, 1))}
    for i, r in enumerate(ex):
        if r["klass"] == "C":
            o, nn = cpairs[r["unit"]]
            ex[i] = graded(r, *(o if r["arm"] == "O" else nn))
        elif r["klass"] == "B" and r["unit"] in ("b1", "b2"):
            ex[i] = graded(r, *((5, 5) if r["arm"] == "O" else (4, 5)))
    c = one(ex)
    expect("exact C mean difference -0.10 is 類別不一致 (round 3 #1)", (c["quality"]["Q"], c["word"]), ("undetermined", "未定"))
bad = [c for c in checks if not c[1]]
for label, good, got, want in checks:
    print("ok  " if good else "FAIL", label, "" if good else f"got {got!r} want {want!r}")
print(len(checks) - len(bad), "of", len(checks), "pass")
sys.exit(1 if bad else 0)
