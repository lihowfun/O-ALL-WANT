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
        rows = native.callers(native.Corpus(self.corpus), "core.write_record", 10)
        self.assertEqual([row["path"] for row in rows], ["pkg/service.py", "tests/test_core.py", "docs/notes.md"])
        self.assertEqual([row["score"] for row in rows], [1.0, 1.0, 0.25])

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

    def test_gate_needs_delta_and_no_more_text_bytes(self):
        def summary(top5, text_bytes):
            return {"a": {"top5": top5, "text_bytes": text_bytes}}
        result = scorer.gate({"R": summary(0.5, 1000), "S": summary(0.65, 1000)}, "R", False)
        self.assertTrue(result["arms"]["S"]["pass"])
        self.assertFalse(scorer.gate({"R": summary(0.5, 1000), "S": summary(0.9, 1001)}, "R", False)["arms"]["S"]["pass"])
        self.assertFalse(scorer.gate({"R": summary(0.5, 1000), "S": summary(0.64, 10)}, "R", False)["arms"]["S"]["pass"])
        self.assertFalse(scorer.gate({"R": summary(0.5, 1000), "S": summary(0.9, 10)}, "R", True)["evaluated"])
        self.assertFalse(scorer.gate({"S": summary(0.9, 10)}, "R", False)["evaluated"])

    def test_run_scores_arms_as_subprocesses_on_their_own_corpus_copy(self):
        perfect = {"find": {"Where is a title frobnicated into a slug?": ["pkg/core.py"],
                            "store a record on disk": ["app/main.py"]},
                   "callers": {"write_record": ["pkg/service.py", "tests/test_core.py"]},
                   "path": {"app/main.py": ["app/main.py", "pkg/service.py", "pkg/core.py"]}}
        fake = self.base / "fake_arm.py"
        fake.write_text("import json, sys\nfrom pathlib import Path\nANSWERS = " + json.dumps(perfect) + "\n"
                        "Path('fake-arm-was-here').write_text('x')\n"
                        "sub, first = sys.argv[1], sys.argv[2]\n"
                        "if '--json' in sys.argv:\n"
                        "    paths = ANSWERS[sub][first]\n"
                        "    print(json.dumps({'schema_version': 1, 'results': [{'path': p, 'score': 1, 'line': 5} for p in paths]}))\n"
                        "else:\n    print('ok')\n", encoding="utf-8")
        out = self.base / "out"
        process = self.score("run", "--questions", str(self.questions_file()), "--corpus", str(self.corpus),
                             "--arm", "R={python} {repo}/evals/code-map/native_search.py {sub} {args}",
                             "--arm", f"F={{python}} {fake.as_posix()} {{sub}} {{args}}", "--out", str(out))
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads((out / "results.json").read_text(encoding="utf-8"))
        fake_summary, native_summary = report["summary"]["F"], report["summary"]["R"]
        self.assertTrue(all(fake_summary[kind]["top1"] == 1.0 for kind in "abcd"))
        self.assertEqual((fake_summary["b"]["precision"], fake_summary["c"]["recall"]), (1.0, 1.0))
        self.assertEqual((native_summary["a"]["top1"], native_summary["a"]["line_top1"]), (1.0, 1.0))
        self.assertAlmostEqual(native_summary["b"]["precision"], 2 / 3, places=3)
        self.assertEqual((native_summary["c"]["top5"], native_summary["d"]["top1"]), (0.0, 1.0))
        self.assertEqual(fake_summary["a"]["text_bytes"], 3)
        self.assertEqual(report["gate"]["arms"]["F"]["passing_classes"], ["c"])
        self.assertIn("Gate for F vs R: PASS", (out / "results.md").read_text(encoding="utf-8"))
        self.assertFalse((self.corpus / "fake-arm-was-here").exists())
        self.assertIn(fake.as_posix(), report["arms"]["F"]["files_sha256"])
        self.assertEqual(report["prereg"], "not checked")
        self.assertFalse(any(row["error"] for row in report["rows"]))

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
        problems = scorer.check_questions({"questions": leaky}, self.corpus)
        self.assertIn("qa: question text names its target (frobnicate_title)", problems)
        self.assertFalse([problem for problem in problems if problem.startswith(("qb", "qc", "qd"))])


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
