"""Code-map Stage 0-alpha harness: native-search baseline and scorer on a tiny fixture corpus.

These tests check arithmetic and plumbing only; they never run an arm on the frozen questions.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "evals" / "code-map"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load("codemap_native_search", "native_search.py")
scorer = load("codemap_score", "score.py")

CORE = ('"""Core helpers for the fixture."""\n\n\n'
        "def frobnicate_title(text):\n"
        '    """Turn a title into a frobnicated slug."""\n'
        '    return "-".join(text.lower().split())\n\n\n'
        "def write_record(path, data):\n"
        '    with open(path, "w") as handle:\n'
        "        handle.write(data)\n")
FILES = {
    "pkg/core.py": CORE,
    "example/demo/pkg/core.py": CORE,
    "pkg/service.py": "import core\nfrom helpers import format_row\n\n\ndef handle(path, data):\n"
                      "    core.write_record(path, format_row(data))\n",
    "pkg/helpers.py": "import core\n\n\ndef format_row(row):\n    return core.frobnicate_title(str(row))\n",
    "app/main.py": "import service\n\n\ndef main():\n    service.handle(\"out.txt\", \"data\")\n",
    "docs/notes.md": "The write_record helper stores data.\n",
    "tests/test_core.py": "import core\n\n\ndef test_write(tmp):\n    core.write_record(tmp, \"data\")\n",
}


def build_corpus(root: Path) -> Path:
    for relative, text in FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    (root / "data").mkdir()
    (root / "data" / "blob.bin").write_bytes(b"write_record\0\x01\x02")
    return root


def question(qid, kind, sub, args, files, **gold):
    return {"id": qid, "class": kind, "text": args[0] if sub == "find" else f"fixture {qid}",
            "command": {"sub": sub, "args": args}, "gold": {"files": files, **gold},
            "gold_method": "fixture", "difficulty": "fixture"}


FIXTURE_QUESTIONS = [
    question("qa", "a", "find", ["Where is a title frobnicated into a slug?"], ["pkg/core.py"],
             symbol="frobnicate_title", lines=[4, 6]),
    question("qb", "b", "callers", ["write_record"], ["pkg/service.py", "tests/test_core.py"], defined_in="pkg/core.py"),
    question("qc", "c", "find", ["store a record on disk"], ["app/main.py"], commit="0" * 40),
    question("qd", "d", "path", ["app/main.py", "pkg/core.py"], ["pkg/service.py"],
             chains=[["app/main.py", "pkg/service.py", "pkg/core.py"]]),
]


class CodeMapFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="codemap-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.corpus = build_corpus(self.base / "corpus")


class NativeSearchTests(CodeMapFixture):
    def test_keywords_drop_stop_words_split_identifiers_and_keep_quotes(self):
        terms = native.keywords('Where is the `write_record` helper that parses camelCaseName and snake_case "exact phrase"?')
        self.assertEqual(terms[:2], ["write_record", "exact phrase"])
        for expected in ("helper", "parses", "camelcasename", "camel", "case", "name", "snake_case", "snake"):
            self.assertIn(expected, terms)
        for dropped in ("where", "the", "that", "and", "is", "record"):
            self.assertNotIn(dropped, terms)  # quoted names are not split

    def test_find_ranks_by_idf_weighted_hits_with_best_line(self):
        rows, terms = native.find(native.Corpus(self.corpus), "Where is a title frobnicated into a slug?", 10)
        self.assertEqual(terms, ["title", "frobnicated", "slug"])
        self.assertEqual({row["path"] for row in rows[:2]}, {"pkg/core.py", "example/demo/pkg/core.py"})
        self.assertEqual(rows[2]["path"], "pkg/helpers.py")
        self.assertEqual(rows[0]["line"], 5)
        self.assertNotIn("data/blob.bin", {row["path"] for row in rows})

    def test_callers_skip_definitions_and_rank_calls_before_mentions(self):
        rows = native.callers(native.Corpus(self.corpus), "write_record", 10)
        self.assertEqual([row["path"] for row in rows], ["pkg/service.py", "tests/test_core.py", "docs/notes.md"])
        self.assertEqual([row["score"] for row in rows], [1.0, 1.0, 0.25])

    def test_callers_rank_files_tied_to_a_qualified_module_first(self):
        (self.corpus / "other").mkdir()
        (self.corpus / "other" / "store.py").write_text(
            "def write_record(path):\n    return path\n\n\ndef save():\n    return write_record('x')\n", encoding="utf-8")
        corpus = native.Corpus(self.corpus)
        bare = [row["path"] for row in native.callers(corpus, "write_record", 10)]
        self.assertEqual(bare, ["other/store.py", "pkg/service.py", "tests/test_core.py", "docs/notes.md"])
        for symbol in ("core.write_record", "pkg/core.py::write_record"):
            rows = native.callers(corpus, symbol, 10)
            self.assertEqual([row["path"] for row in rows],
                             ["pkg/service.py", "tests/test_core.py", "other/store.py", "docs/notes.md"], symbol)
            self.assertEqual([row["score"] for row in rows], [11.0, 11.0, 1.0, 0.25])
        self.assertEqual(native.callers(corpus, "no-such.write_record", 10), [])

    def test_path_finds_two_hop_chain_direct_import_and_reports_no_chain(self):
        corpus = native.Corpus(self.corpus)
        rows, notes = native.module_path(corpus, "app/main.py", "pkg/core.py", 10)
        self.assertEqual([row["path"] for row in rows], ["app/main.py", "pkg/service.py", "pkg/core.py"])
        self.assertEqual(notes, ["app/main.py -> pkg/service.py -> pkg/core.py"])
        rows, notes = native.module_path(corpus, "service", "core", 10)
        self.assertEqual([row["path"] for row in rows], ["pkg/service.py", "pkg/core.py"])
        rows, notes = native.module_path(corpus, "pkg/core.py", "app/main.py", 10)
        self.assertEqual(rows, [])
        self.assertIn("no import chain", notes[0])

    def test_affected_combines_importers_symbol_callers_and_mentions(self):
        rows, _notes = native.affected(native.Corpus(self.corpus), "pkg/core.py::write_record", 10)
        scores = {row["path"]: row["score"] for row in rows}
        self.assertEqual(scores, {"pkg/service.py": 3.0, "tests/test_core.py": 3.0, "pkg/helpers.py": 2.0,
                                  "docs/notes.md": 0.25})

    def test_cli_prints_compact_text_and_versioned_json(self):
        command = [sys.executable, str(HERE / "native_search.py"), "callers", "write_record"]
        text = subprocess.run(command, cwd=self.corpus, capture_output=True, text=True, encoding="utf-8", check=True).stdout
        self.assertEqual(text.splitlines()[0], "pkg/service.py:6: core.write_record(path, format_row(data))")
        payload = json.loads(subprocess.run(command + ["--json", "--limit", "2"], cwd=self.corpus, capture_output=True,
                                            text=True, encoding="utf-8", check=True).stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["results"], [{"path": "pkg/service.py", "score": 1.0, "line": 6},
                                              {"path": "tests/test_core.py", "score": 1.0, "line": 5}])


class ScorerTests(CodeMapFixture):
    def questions_file(self, **corpus):
        identity = scorer.corpus_identity(self.corpus)
        document = {"schema_version": 1, "corpus": {"commit": "fixture", **identity, **corpus},
                    "questions": FIXTURE_QUESTIONS}
        path = self.base / "questions.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def score(self, *arguments):
        return subprocess.run([sys.executable, str(HERE / "score.py"), *arguments], capture_output=True, text=True,
                              encoding="utf-8")

    def test_corpus_identity_hashes_sorted_posix_paths(self):
        identity = scorer.corpus_identity(self.corpus)
        listing = "".join(path + "\n" for path in sorted([*FILES, "data/blob.bin"])).encode()
        self.assertEqual(identity["files"], 8)
        self.assertEqual(identity["file_list_sha256"], hashlib.sha256(listing).hexdigest())

    def test_generated_copy_counts_as_its_source_once(self):
        twins = scorer.generated_twins(self.corpus)
        self.assertEqual(twins, {"example/demo/pkg/core.py": {"pkg/core.py"}})
        result = scorer.score_question(FIXTURE_QUESTIONS[0], ["example/demo/pkg/core.py", "pkg/core.py", "pkg/helpers.py"],
                                       [5, 5, 4], twins)
        self.assertEqual(result["ranked"], ["pkg/core.py", "pkg/helpers.py"])
        self.assertTrue(result["hit1"] and result["line_hit1"])

    def test_rank_metrics_precision_recall_and_path_endpoints(self):
        callers = FIXTURE_QUESTIONS[1]
        payload = {"results": [{"path": "docs\\notes.md"}, {"path": "./pkg/service.py:6", "line": 6},
                               {"path": str(self.corpus / "app" / "main.py")}, {"score": 1}]}
        paths, lines, error = scorer.ranked_paths(payload, self.corpus)
        self.assertEqual((paths, lines, error), (["docs/notes.md", "pkg/service.py", "app/main.py"], [None, 6, None], None))
        result = scorer.score_question(callers, paths, lines, {})
        self.assertEqual((result["hit1"], result["hit5"], result["rr"]), (False, True, 0.5))
        self.assertAlmostEqual(result["precision"], 1 / 3)
        self.assertAlmostEqual(result["recall"], 1 / 2)
        path = scorer.score_question(FIXTURE_QUESTIONS[3], ["app/main.py", "pkg/service.py", "pkg/core.py"], [1, 2, 3], {})
        self.assertEqual(path["ranked"], ["pkg/service.py"])
        self.assertTrue(path["hit1"])
        late = scorer.score_question(callers, [f"x{i}.py" for i in range(10)] + ["pkg/service.py"], [1] * 11, {})
        self.assertEqual((late["hit5"], late["rr"]), (False, 0.0))  # beyond the first 10 distinct files

    def test_ranked_file_counts_only_when_the_text_output_shows_it(self):
        callers = FIXTURE_QUESTIONS[1]
        paths = ["pkg/service.py", "tests/test_core.py"]
        hidden = scorer.score_question(callers, paths, [6, 5], {}, shown="ok\n")
        self.assertEqual((hidden["hit1"], hidden["hit5"], hidden["recall"], hidden["gold_not_in_text"]), (False, False, 0.0, 2))
        partly = scorer.score_question(callers, paths, [6, 5], {}, shown="C:\\copy\\tests\\test_core.py:5: call\n")
        self.assertEqual((partly["hit1"], partly["hit5"], partly["rr"], partly["recall"]), (False, True, 0.5, 0.5))
        twins = scorer.generated_twins(self.corpus)
        copy = scorer.score_question(FIXTURE_QUESTIONS[0], ["example/demo/pkg/core.py"], [5], twins,
                                     shown="example/demo/pkg/core.py:5: title\n")
        self.assertTrue(copy["hit1"])

    @staticmethod
    def gate_rows(arm, hits, text_bytes, failed=None):
        failed = failed or [False] * len(hits)
        return [{"arm": arm, "id": f"q{index}", "class": "d", "hit5": hit, "text_bytes": size, "json_bytes": 2 * size,
                 "failed": fail} for index, (hit, size, fail) in enumerate(zip(hits, text_bytes, failed))]

    def test_gate_needs_delta_two_gained_questions_and_no_more_text_bytes(self):
        base = self.gate_rows("R", [1, 0, 0, 0, 0], [50] * 5)
        verdict = scorer.gate(base + self.gate_rows("S", [1, 1, 1, 0, 0], [50] * 5), "R", False)["arms"]["S"]
        self.assertTrue(verdict["pass"])
        self.assertEqual(verdict["classes"]["d"]["top5_hits_gained"], 2)
        one = scorer.gate(base + self.gate_rows("S", [1, 1, 0, 0, 0], [10] * 5), "R", False)["arms"]["S"]
        self.assertEqual((one["classes"]["d"]["top5_delta"], one["pass"]), (0.2, False))  # 0.2 >= 0.15 but one question
        more = scorer.gate(base + self.gate_rows("S", [1, 1, 1, 1, 1], [50, 50, 50, 50, 51]), "R", False)["arms"]["S"]
        self.assertFalse(more["pass"])
        self.assertFalse(scorer.gate(base + self.gate_rows("S", [1] * 5, [1] * 5), "R", True)["evaluated"])
        self.assertFalse(scorer.gate(self.gate_rows("S", [1] * 5, [1] * 5), "R", False)["evaluated"])

    def test_gate_byte_comparison_skips_questions_where_either_arm_failed(self):
        base = self.gate_rows("R", [1, 0, 0, 0, 0], [5, 5, 5, 5, 100])
        failing = self.gate_rows("S", [1, 1, 1, 0, 0], [10, 10, 10, 10, 0], [False, False, False, False, True])
        verdict = scorer.gate(base + failing, "R", False)["arms"]["S"]["classes"]["d"]
        self.assertEqual((verdict["text_bytes"], verdict["baseline_text_bytes"]), (40, 20))
        self.assertEqual((verdict["bytes_compared_questions"], verdict["bytes_excluded_questions"]), (4, 1))
        self.assertEqual((verdict["json_bytes"], verdict["baseline_json_bytes"]), (80, 40))
        self.assertFalse(verdict["passes"])  # summed over all five, 40 < 120 would have passed

    NATIVE_ARM = "R={python} {repo}/evals/code-map/native_search.py {sub} {args}"

    def fake_arm(self):
        perfect = {"find": {"Where is a title frobnicated into a slug?": ["pkg/core.py"],
                            "store a record on disk": ["app/main.py"]},
                   "callers": {"write_record": ["pkg/service.py", "tests/test_core.py"]},
                   "path": {"app/main.py": ["app/main.py", "pkg/service.py", "pkg/core.py"]}}
        fake = self.base / "fake_arm.py"
        fake.write_text("import json, sys\nfrom pathlib import Path\nANSWERS = " + json.dumps(perfect) + "\n"
                        "Path('fake-arm-was-here').write_text('x')\n"
                        "sub, first = sys.argv[1], sys.argv[2]\n"
                        "paths = ANSWERS[sub][first]\n"
                        "if '--json' in sys.argv:\n"
                        "    print(json.dumps({'schema_version': 1, 'results': [{'path': p, 'score': 1, 'line': 5} for p in paths]}))\n"
                        "else:\n    print('\\n'.join(paths))\n", encoding="utf-8")
        return fake

    def test_run_scores_arms_as_subprocesses_on_their_own_corpus_copy(self):
        fake = self.fake_arm()
        out = self.base / "out"
        process = self.score("run", "--questions", str(self.questions_file()), "--corpus", str(self.corpus),
                             "--arm", self.NATIVE_ARM, "--arm", f"F={{python}} {fake.as_posix()} {{sub}} {{args}}",
                             "--arm", 'E={python} -c "import sys; sys.exit(3)" {sub} {args}', "--out", str(out))
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads((out / "results.json").read_text(encoding="utf-8"))
        fake_summary, native_summary = report["summary"]["F"], report["summary"]["R"]
        self.assertTrue(all(fake_summary[kind]["top1"] == 1.0 for kind in "abcd"))
        self.assertEqual((fake_summary["b"]["precision"], fake_summary["c"]["recall"]), (1.0, 1.0))
        self.assertEqual((native_summary["a"]["top1"], native_summary["a"]["line_top1"]), (1.0, 1.0))
        self.assertAlmostEqual(native_summary["b"]["precision"], 2 / 3, places=3)
        self.assertEqual((native_summary["c"]["top5"], native_summary["d"]["top1"]), (0.0, 1.0))
        self.assertEqual(fake_summary["a"]["text_bytes"], len("pkg/core.py\n"))
        fake_gate = report["gate"]["arms"]["F"]
        self.assertEqual((fake_gate["passing_classes"], fake_gate["classes"]["c"]["top5_hits_gained"]), ([], 1))
        self.assertIn("Gate for F vs R: FAIL", (out / "results.md").read_text(encoding="utf-8"))
        broken = [row for row in report["rows"] if row["arm"] == "E"]
        self.assertTrue(all(row["failed"] and not row["hit5"] and row["error"].startswith("exit") for row in broken))
        self.assertEqual(report["gate"]["arms"]["E"]["classes"]["a"]["bytes_excluded_questions"], 1)
        self.assertFalse((self.corpus / "fake-arm-was-here").exists())
        self.assertIn(fake.as_posix(), report["arms"]["F"]["files_sha256"])
        self.assertEqual((report["prereg"], report["deviations"]), ("not checked", []))
        self.assertFalse(any(row["error"] for row in report["rows"] if row["arm"] != "E"))

    def test_full_run_requires_frozen_arms_and_records_deviations(self):
        questions = self.questions_file()
        native_sha = hashlib.sha256((HERE / "native_search.py").read_bytes()).hexdigest()
        prereg = self.base / "PREREG.md"
        prereg.write_text(f"questions.json sha256: `{hashlib.sha256(questions.read_bytes()).hexdigest()}`\n"
                          f"native_search.py sha256: `{native_sha}`\n", encoding="utf-8")
        arms = ["--arm", self.NATIVE_ARM, "--arm", f"F={{python}} {self.fake_arm().as_posix()} {{sub}} {{args}}"]
        common = ["run", "--questions", str(questions), "--corpus", str(self.corpus), *arms]
        refused = self.score(*common, "--out", str(self.base / "refused"))
        self.assertEqual(refused.returncode, 2)
        self.assertIn("arm F", refused.stderr)
        self.assertNotIn("arm R", refused.stderr)
        for extra, name in ((["--allow-unfrozen-arm"], "allowed"), (["--ids", "qa"], "partial")):
            process = self.score(*common, *extra, "--out", str(self.base / name))
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads((self.base / name / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(report["prereg"], "matches PREREG")
            self.assertEqual(report["prereg_sha256"], hashlib.sha256(prereg.read_bytes()).hexdigest())
            self.assertEqual(len(report["deviations"]), 2)  # score.py is not recorded, nor is arm F
            self.assertTrue(report["deviations"][0].startswith("score.py sha256"))
            self.assertTrue(report["deviations"][1].startswith("arm F:"))

    def test_run_refuses_changed_corpus_and_unregistered_questions(self):
        changed = self.score("run", "--questions", str(self.questions_file(file_list_sha256="0" * 64)), "--corpus",
                             str(self.corpus), "--arm", "R=x", "--out", str(self.base / "out"))
        self.assertEqual(changed.returncode, 2)
        self.assertIn("corpus file list", changed.stderr)
        prereg = self.base / "PREREG.md"
        prereg.write_text("questions.json sha256: `" + "0" * 64 + "`\n", encoding="utf-8")
        unregistered = self.score("run", "--questions", str(self.questions_file()), "--corpus", str(self.corpus),
                                  "--arm", "R=x", "--prereg", str(prereg), "--out", str(self.base / "out"))
        self.assertEqual(unregistered.returncode, 2)
        self.assertIn("differs from the one recorded", unregistered.stderr)

    def test_check_reports_a_question_that_names_its_target(self):
        leaky = json.loads(json.dumps(FIXTURE_QUESTIONS))
        leaky[0]["text"] = leaky[0]["command"]["args"][0] = "Where is frobnicate_title defined?"
        leaky[1]["text"] = "Which files in the core package call it?"  # 'core' is a word of tests/test_core.py
        problems = scorer.check_questions({"questions": leaky}, self.corpus)
        self.assertIn("qa: question text names its target (frobnicate_title)", problems)
        self.assertIn("qb: question text uses a word of a gold path (core); reword or allow it", problems)
        self.assertFalse([problem for problem in problems if problem.startswith(("qc", "qd"))])
        leaky[1]["allowed_path_words"] = ["core"]
        leaky[1]["command"]["args"] = ["core.write_record"]
        problems = scorer.check_questions({"questions": leaky}, self.corpus)
        self.assertFalse([problem for problem in problems if problem.startswith("qb")])
        leaky[1]["command"]["args"] = ["helpers.write_record"]
        self.assertIn("qb: helpers.write_record is not defined in pkg/core.py",
                      scorer.check_questions({"questions": leaky}, self.corpus))


class FrozenHarnessTests(unittest.TestCase):
    def test_harness_uses_only_the_standard_library_and_never_imports_an_arm(self):
        for name in ("native_search.py", "score.py"):
            tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
            imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
                        for alias in node.names}
            imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                         if isinstance(node, ast.ImportFrom) and node.module}
            self.assertLessEqual(imported - {"__future__"}, set(sys.stdlib_module_names), name)
            self.assertNotIn("native_search", imported)
            self.assertNotIn("code_index", imported)

    def test_frozen_questions_match_the_preregistered_hash_and_counts(self):
        data = (HERE / "questions.json").read_bytes()
        recorded = re.findall(r"questions\.json sha256:\s*`([0-9a-f]{64})`", (HERE / "PREREG.md").read_text(encoding="utf-8"))
        self.assertEqual(recorded, [hashlib.sha256(data).hexdigest()])
        document = json.loads(data.decode("utf-8"))
        counts = {kind: sum(item["class"] == kind for item in document["questions"]) for kind in "abcd"}
        self.assertEqual(counts, {"a": 12, "b": 9, "c": 13, "d": 5})
        self.assertEqual(document["corpus"]["commit"], "6481437f14705dacf18f5b7d713003598e2f0bfe")


if __name__ == "__main__":
    unittest.main()
