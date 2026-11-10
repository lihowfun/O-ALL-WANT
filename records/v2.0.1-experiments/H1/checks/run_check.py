"""Pure helpers of h1_run on synthetic input (version 3).
    python3 run_check.py <H1 folder> <OAW checkout>"""
import importlib.util, json, os, stat, sys, tempfile
os.environ.setdefault("H1_OAW", sys.argv[2])
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("h1_run", os.path.join(sys.argv[1], "h1_run.py"))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
PATCH = """diff --git a/src/flask/app.py b/src/flask/app.py
index 111..222 100644
--- a/src/flask/app.py
+++ b/src/flask/app.py
@@ -1,3 +1,5 @@
 import os
-OLD = 1
+RETRY_LIMIT = 37
+--- a/tests/fake.py
+LIMIT = RETRY_LIMIT + 37 + 370 + x37
 tail
diff --git a/docs/designs/note.md b/docs/designs/note.md
new file mode 100644
--- /dev/null
+++ b/docs/designs/note.md
@@ -0,0 +1 @@
+retry 37 times
\\ No newline at end of file
diff --git a/src/flask/README.rst b/src/flask/README.rst
--- a/src/flask/README.rst
+++ b/src/flask/README.rst
@@ -1,1 +1,2 @@
 a
+b
"""
checks = []
def expect(label, got, want):
    checks.append((label, got == want, got, want))
kinds = [k for k, _ in R.patch_walk(PATCH)]
expect("walk kinds", kinds[:18], ["head"] * 5 + ["ctx", "del", "add", "add", "add", "ctx"] + ["head"] * 5 + ["add", "note"])
paths, added, files = R.patch_files(PATCH)
expect("paths (a content line that looks like a header is not a path)", paths,
       ["docs/designs/note.md", "src/flask/README.rst", "src/flask/app.py"])
expect("added lines", len(added), 5)
expect("per file counts and new files (#8)", files, {
    "src/flask/app.py": {"added": 3, "deleted": 1, "new": False},
    "docs/designs/note.md": {"added": 1, "deleted": 0, "new": True},
    "src/flask/README.rst": {"added": 1, "deleted": 0, "new": False}})
expect("non-documentation lines by the frozen oaw_mode (#8: .md under docs and .rst under src left out)",
       R.code_lines(files), 4)
expect("oaw_mode threshold", R.oaw_mode().STANDARD_LINES, 300)
plain = "--- /dev/null\n+++ b/src/new.py\n@@ -0,0 +1,2 @@\n+a\n+b\n"
expect("a plain diff creating a file", R.patch_files(plain)[2], {"src/new.py": {"added": 2, "deleted": 0, "new": True}})
swapped = R.swap_added(PATCH, {"37": "379"})
expect("whole-token swap in added lines only", [l for l in swapped.splitlines() if "37" in l],
       ["+RETRY_LIMIT = 379", "+LIMIT = RETRY_LIMIT + 379 + 370 + x37", "+retry 379 times"])
expect("swap keeps the rest", swapped.replace("379", "37"), PATCH)
expect("wrong value of a number", R.wrong_value("37"), "379")
expect("wrong value of a name", R.wrong_value("X-Trace"), "X-Trace_X")
expect("token_in whole", (R.token_in("37", "a 37 b"), R.token_in("37", "a 370 b"), R.token_in("37", "x37")), (True, False, False))
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "j.xml")
    open(path, "w").write(
        '<testsuites><testsuite>'
        '<testcase classname="tests.test_hidden_u" name="test_a[1]"/>'
        '<testcase classname="tests.test_hidden_u" name="test_a[2]"><failure/></testcase>'
        '<testcase classname="tests.test_hidden_u" name="test_b"/>'
        '<testcase classname="tests.test_hidden_u" name="test_c"><skipped type="pytest.skip"/></testcase>'
        '<testcase classname="tests.test_hidden_u" name="test_x"><skipped type="pytest.xfail"/></testcase>'
        '<testcase classname="tests.test_hidden_u" name="test_d"><error/></testcase>'
        '<testcase classname="tests.test_hidden_u" name="test_b"><error/></testcase>'
        '<testcase classname="tests.test_hidden_u.TestK" name="test_m"/>'
        '</testsuite></testsuites>')
    nodes = R.junit(path)
    expect("junit statuses by full node id; a node seen twice keeps the worst (#5)", nodes, {
        "tests.test_hidden_u::test_a[1]": "passed", "tests.test_hidden_u::test_a[2]": "failed",
        "tests.test_hidden_u::test_b": "error", "tests.test_hidden_u::test_c": "skipped",
        "tests.test_hidden_u::test_x": "xfailed", "tests.test_hidden_u::test_d": "error",
        "tests.test_hidden_u.TestK::test_m": "passed"})
    mine, alien = R.hidden_cases({"id": "u"}, nodes)
    expect("hidden cases by function; methods are alien (#5)", (sorted(mine), mine["test_a"], alien),
           (["test_a", "test_b", "test_c", "test_d", "test_x"], {"test_a[1]": "passed", "test_a[2]": "failed"},
            ["tests.test_hidden_u.TestK::test_m"]))
    expect("junit unreadable", R.junit(path + "x"), None)
    # tree digest covers everything, caches and exec bits included (#1)
    root = os.path.join(tmp, "t"); os.makedirs(os.path.join(root, "__pycache__"))
    open(os.path.join(root, "a.txt"), "w").write("x")
    first = R.tree_digest(root)
    open(os.path.join(root, "__pycache__", "c.pyc"), "w").write("y")
    second = R.tree_digest(root)
    os.chmod(os.path.join(root, "a.txt"), 0o755)
    third = R.tree_digest(root)
    os.makedirs(os.path.join(root, ".vscode"))
    fourth = R.tree_digest(root)
    expect("tree digest changes with a cache file, an exec bit and an empty folder (#1)",
           len({first, second, third, fourth}), 4)
expect("hidden name", R.hidden_name({"id": "large-1-a"}), "test_hidden_large_1_a.py")
try:
    R.safe_id({"id": "../x"}); checks.append(("unsafe id", False, "accepted", "refused"))
except SystemExit:
    checks.append(("unsafe id", True, "", ""))
# not_run order and exact models (#9, #10)
row = {"exit": 0, "tokens_total": 10, "result_seen": True, "limit_seen": False, "api_key_source": "none",
       "root_models": ["claude-opus-5-5"]}
O = "claude-opus-5-5"
expect("a normal session counts", R.not_run(dict(row), "claude", O), "")
expect("dated alias of the model counts", R.not_run(dict(row, root_models=["claude-opus-5-5-20261101"]), "claude", O), "")
expect("a prefix match is not the model (#10)", R.not_run(dict(row, root_models=["claude-opus-5-5x"]), "claude", O),
       "model claude-opus-5-5x")
expect("no root model is not run (#10)", R.not_run(dict(row, root_models=[]), "claude", O), "model missing")
expect("two root models, one wrong (#10)", R.not_run(dict(row, root_models=[O, "claude-haiku-5-5"]), "claude", O),
       "model claude-opus-5-5,claude-haiku-5-5")
expect("timeout with the right model is an answer", R.not_run(dict(row, exit="timeout"), "claude", O), "")
expect("timeout with a wrong model is not run", R.not_run(dict(row, exit="timeout", root_models=["x"]), "claude", O), "model x")
expect("billing before the limit", R.not_run(dict(row, api_key_source="ANTHROPIC_API_KEY", limit_seen=True), "claude", O),
       "billing source ANTHROPIC_API_KEY")
expect("limit before 0 tokens", R.not_run(dict(row, limit_seen=True, tokens_total=0), "claude", O), "usage limit")
cx = dict(row, api_key_source="chatgpt", provider="openai", root_models=["gpt-6.1-sol"])
expect("codex counts with chatgpt and openai", R.not_run(cx, "codex", "gpt-6.1-sol"), "")
expect("codex billing from the login file (#10)", R.not_run(dict(cx, api_key_source="an API key is set"), "codex",
       "gpt-6.1-sol"), "billing source an API key is set")
expect("codex provider must be openai (#10)", R.not_run(dict(cx, provider="azure"), "codex", "gpt-6.1-sol"), "provider azure")
expect("a root message without a model is not run (round 3 #8)",
       R.not_run(dict(row, root_model_missing=True), "claude", O), "model claude-opus-5-5 (a root message without a model)")
expect("budget cap first", R.not_run(dict(row, exit="budget cap", api_key_source="x"), "claude", O), "budget cap")
# the audit schema (#11)
F = ["test_r01_a", "test_r02_b"]
good = json.dumps({"functions": [{"name": "test_r01_a", "stated": True}, {"name": "test_r02_b", "stated": False}]})
expect("audit reply in a code fence", R.audit_answer("```json\n" + good + "\n```", F)[1], "")
for label, text, why in (
        ("stated as a string", {"functions": [{"name": "test_r01_a", "stated": "false"}, {"name": "test_r02_b", "stated": True}]}, "an entry breaks the schema"),
        ("stated as a number", {"functions": [{"name": "test_r01_a", "stated": 0}, {"name": "test_r02_b", "stated": True}]}, "an entry breaks the schema"),
        ("a function missing", {"functions": [{"name": "test_r01_a", "stated": True}]}, "the functions differ from the frozen ones"),
        ("an extra function", {"functions": [{"name": n, "stated": True} for n in F + ["test_r03"]]}, "the functions differ from the frozen ones"),
        ("a duplicate", {"functions": [{"name": n, "stated": True} for n in F + ["test_r01_a"]]}, "a function is listed twice"),
        ("no list", {"fns": []}, "no functions list")):
    expect(f"audit refuses {label} (#11)", R.audit_answer(json.dumps(text), F), (None, why))
expect("audit refuses no JSON (#11)", R.audit_answer("all stated", F), (None, "no functions list"))
bad = [c for c in checks if not c[1]]
for label, good, got, want in checks:
    print("ok  " if good else "FAIL", label, "" if good else f"\n   got  {got!r}\n   want {want!r}")
print(len(checks) - len(bad), "of", len(checks), "pass")
sys.exit(1 if bad else 0)
