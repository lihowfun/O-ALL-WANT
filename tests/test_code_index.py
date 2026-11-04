"""Fixture trees for scripts/code_index.py: names, imports, calls, fallbacks, caches and paths.

The index parses fixture files with ast or regular expressions; nothing in a
fixture tree is imported or run.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import code_index  # noqa: E402

FIXTURE = {
    "pkg/__init__.py": "from .core import Engine\n",
    "pkg/core.py": '''
        """Engine core."""


        class Engine:
            """Drives the rotation of session keys."""

            def start(self):
                # kick off the first rotation
                return self.helper()

            def helper(self):
                return 1


        class TurboEngine(Engine):
            def boost(self):
                return self.helper()


        def make_engine():
            return Engine()
    ''',
    "pkg/util.py": '''
        RETRY_LIMIT = 3  # attempts before giving up


        def helper_func(parts):
            """Join path parts safely without escaping the root."""
            return "/".join(parts)
    ''',
    "pkg/sub/__init__.py": "",
    "pkg/sub/deep.py": '''
        from ..util import helper_func as hf
        from .. import core


        def go():
            hf(["a"])
            engine = core.Engine()
            engine.start()
            core.make_engine().start()
    ''',
    "app/main.py": '''
        import pkg.util as u
        from pkg.core import Engine


        def run():
            u.helper_func(["b"])
            Engine().start()
            return u.RETRY_LIMIT
    ''',
    "ns/inner/mod.py": '''
        def namespace_helper():
            return 2
    ''',
    "app/use_ns.py": '''
        import ns.inner.mod


        def use():
            return ns.inner.mod.namespace_helper()
    ''',
    "checks/check.py": '''
        import importlib
        import sys
        from pathlib import Path

        PACKAGE = Path(__file__).resolve().parents[1] / "pkg"
        sys.path.insert(0, str(PACKAGE))
        util = importlib.import_module("util")


        def check():
            return util.helper_func(["c"])
    ''',
    "tools/runner.py": '''
        from app.main import run


        def cli():
            run()
    ''',
    "broken.py": '''
        def fallback_target(value):
            return value


        def other(:
            fallback_target(2)
    ''',
    "docs/guide.md": '''
        # Guide

        Intro text.

        ## Rotating the session keys

        Keys rotate every day.

        ```
        # not a heading
        ```
    ''',
    "scripts/deploy.sh": '''
        #!/bin/sh
        # Release helpers
        deploy_release() {
            echo "shipping"
        }
    ''',
    "config/settings.json": '''
        {
          "cacheDirectory": "/tmp/x",
          "retryLimit": 3
        }
    ''',
    "pyproject.toml": '''
        [tool.oawtest]
        max_depth = 3
    ''',
    "dup/a.py": "def mirrored_quokka():\n    return 1\n",
    "dup2/a.py": "def mirrored_quokka():\n    return 1\n",
    ".git/config": "[core]\n",
    "venv/pyvenv.cfg": "home = x\n",
    "venv/lib/site.py": "def venv_only_quokka():\n    pass\n",
    "node_modules/x/index.js": "function nodeOnlyQuokka() {}\n",
    "pkg/__pycache__/core.cpython-313.py": "def cache_only_quokka():\n    pass\n",
    "example/gen/.oaw/install.json": json.dumps(
        {"installation_id": "generated-example-gen", "managed_files": {"scripts/copy.py": "0" * 64}}),
    "example/gen/scripts/copy.py": "def generated_only_quokka():\n    pass\n",
    "example/gen/README.md": "# Generated example readme\n",
}


def write_tree(root, files=FIXTURE):
    for relative, text in files.items():
        path = Path(root, *relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent(text).lstrip("\n") if "\n" in text else text
        path.write_text(content, encoding="utf-8", newline="\n")


def run_cli(*args, cwd=None):
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    environment.pop(code_index.CACHE_ENV, None)
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "code_index.py"), *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", env=environment, timeout=120)


class CodeIndexTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oaw-code-index-")
        self.addCleanup(temporary.cleanup)
        self.root = os.path.join(temporary.name, "repo")
        os.makedirs(self.root)
        write_tree(self.root)
        self.outside = os.path.join(temporary.name, "cache")
        self.index = code_index.build_index(self.root)

    def find(self, query, limit=5):
        return code_index.find(self.index, query, limit)["results"]

    def test_find_ranks_definitions_methods_and_lines(self):
        top = self.find("join path parts safely")[0]
        self.assertEqual((top["path"], top["symbol"]), ("pkg/util.py", "helper_func"))
        self.assertEqual(top["line"], 4)
        method = self.find("Engine start the first rotation")[0]
        self.assertEqual((method["path"], method["symbol"]), ("pkg/core.py", "Engine.start"))
        self.assertIn(method["line"], (7, 8))
        constant = self.find("attempts before giving up")[0]
        self.assertEqual((constant["path"], constant["symbol"], constant["line"]), ("pkg/util.py", "RETRY_LIMIT", 1))
        self.assertEqual(self.find("zzzz unknownword"), [])
        self.assertEqual(code_index.find(self.index, "where is the", 5)["terms"], [])

    def test_identifiers_split_into_stemmed_words_and_rare_words_weigh_more(self):
        self.assertEqual(code_index.words("parseHTTPResponse snake_case_name"),
                         ["pars", "http", "respons", "parsehttpresponse", "snak", "cas", "nam", "snakecasename"])
        self.assertEqual(code_index._stem("parsing"), code_index._stem("parsed"))
        top = self.find("makeEngine")[0]
        self.assertEqual((top["path"], top["symbol"]), ("pkg/core.py", "make_engine"))
        # "engine" is in many files, "rotation" in one: the rare word decides.
        self.assertEqual(self.find("engine rotation")[0]["path"], "pkg/core.py")

    def test_relative_imports_resolve_and_import_path_is_shortest(self):
        self.assertEqual(code_index.import_path(self.index, "pkg/sub/deep.py", "pkg/util.py")["path"],
                         ["pkg/sub/deep.py", "pkg/util.py"])
        chain = code_index.import_path(self.index, "tools/runner.py", "pkg/core.py")
        self.assertEqual((chain["path"], chain["direction"]),
                         (["tools/runner.py", "app/main.py", "pkg/core.py"], "forward"))
        back = code_index.import_path(self.index, "pkg/util.py", "pkg/sub/deep.py")
        self.assertEqual((back["path"], back["direction"]), (["pkg/sub/deep.py", "pkg/util.py"], "reverse"))
        self.assertEqual(code_index.import_path(self.index, "pkg/util.py", "dup/a.py")["path"], [])
        self.assertEqual(code_index.import_path(self.index, "pkg.sub.deep", "pkg.util")["path"][-1], "pkg/util.py")

    def test_callers_resolve_aliases_methods_and_instances(self):
        report = code_index.callers(self.index, "pkg.util.helper_func")
        self.assertEqual(report["targets"], ["pkg/util.py::helper_func"])
        sites = {(row["path"], row["line"], row["symbol"], row["resolved"]) for row in report["results"]}
        self.assertEqual(sites, {("pkg/sub/deep.py", 6, "go", True), ("app/main.py", 6, "run", True),
                                 ("checks/check.py", 11, "check", True)})  # importlib + sys.path variable
        starts = code_index.callers(self.index, "Engine.start")["results"]
        resolved = {(row["path"], row["line"]) for row in starts if row["resolved"]}
        self.assertEqual(resolved, {("pkg/sub/deep.py", 8)})  # engine = core.Engine(); engine.start()
        unresolved = {(row["path"], row["line"]) for row in starts if not row["resolved"]}
        self.assertEqual(unresolved, {("pkg/sub/deep.py", 9), ("app/main.py", 7)})  # receivers are call results
        helper = code_index.callers(self.index, "pkg/core.py::Engine::helper")["results"]
        self.assertEqual({(row["symbol"], row["resolved"]) for row in helper},
                         {("Engine.start", True), ("TurboEngine.boost", True)})  # self and inherited self
        classes = {(row["path"], row["line"]) for row in code_index.callers(self.index, "Engine")["results"]}
        self.assertTrue({("pkg/core.py", 21), ("app/main.py", 7), ("pkg/sub/deep.py", 7)} <= classes)
        self.assertEqual(code_index.callers(self.index, "no_such_function")["results"], [])
        namespace = code_index.callers(self.index, "ns.inner.mod.namespace_helper")["results"]  # no __init__.py
        self.assertEqual([(row["path"], row["line"], row["resolved"]) for row in namespace],
                         [("app/use_ns.py", 5, True)])

    def test_affected_lists_importers_and_callers_with_two_hops(self):
        importers = code_index.affected(self.index, "pkg/util.py")
        self.assertEqual([(row["path"], row["hop"]) for row in importers["results"]],
                         [("app/main.py", 1), ("checks/check.py", 1), ("pkg/sub/deep.py", 1)])
        two = code_index.affected(self.index, "pkg/util.py", hops=2)
        self.assertIn(("tools/runner.py", 2), [(row["path"], row["hop"]) for row in two["results"]])
        symbol = code_index.affected(self.index, "pkg/util.py::helper_func", hops=2)
        self.assertEqual([(row["path"], row["hop"]) for row in symbol["results"]],
                         [("app/main.py", 1), ("checks/check.py", 1), ("pkg/sub/deep.py", 1), ("tools/runner.py", 2)])
        constant = code_index.affected(self.index, "pkg/util.py::RETRY_LIMIT")["results"]
        self.assertEqual([(row["path"], row["line"]) for row in constant], [("app/main.py", 8)])
        self.assertEqual(code_index.affected(self.index, "pkg/util.py::missing")["results"], [])

    def test_file_that_does_not_parse_falls_back_to_regex(self):
        record = self.index.files["broken.py"]
        self.assertEqual(record["kind"], "python-regex")
        self.assertIn("SyntaxError", record["error"])
        self.assertIn("broken.py", code_index.stats(self.index)["parse_fallbacks"])
        top = self.find("fallback target value")[0]
        self.assertEqual((top["path"], top["symbol"], top["line"]), ("broken.py", "fallback_target", 1))
        rows = code_index.callers(self.index, "fallback_target")["results"]
        self.assertEqual([(row["path"], row["line"], row["symbol"]) for row in rows], [("broken.py", 6, "other")])

    def test_non_python_files_get_headings_functions_and_keys(self):
        heading = self.find("rotating the session keys", limit=10)
        guide = next(result for result in heading if result["path"] == "docs/guide.md")
        self.assertEqual((guide["symbol"], guide["line"]), ("Rotating the session keys", 5))
        self.assertNotIn("not a heading", [unit[0] for unit in self.index.files["docs/guide.md"]["units"]])
        shell = self.find("deploy release shipping")[0]
        self.assertEqual((shell["path"], shell["symbol"]), ("scripts/deploy.sh", "deploy_release"))
        key = self.find("retryLimit")[0]
        self.assertEqual((key["path"], key["symbol"], key["line"]), ("config/settings.json", "retryLimit", 3))
        section = self.find("oawtest max depth")[0]
        self.assertEqual((section["path"], section["symbol"]), ("pyproject.toml", "tool.oawtest"))

    def test_skips_vcs_virtualenv_caches_and_marked_generated_copies(self):
        paths = set(self.index.files)
        for skipped in (".git/config", "venv/lib/site.py", "node_modules/x/index.js",
                        "pkg/__pycache__/core.cpython-313.py", "example/gen/scripts/copy.py",
                        "example/gen/.oaw/install.json"):
            self.assertNotIn(skipped, paths)
        self.assertIn("example/gen/README.md", paths)
        self.assertEqual(code_index.stats(self.index)["skipped"]["generated copies"], 2)
        everything = code_index.build_index(self.root, include_generated=True)
        self.assertIn("example/gen/scripts/copy.py", everything.files)

    def test_identical_files_are_grouped(self):
        results = self.find("mirrored quokka")
        self.assertEqual(len(results), 1)
        self.assertEqual((results[0]["path"], results[0]["duplicates"]), ("dup/a.py", ["dup2/a.py"]))

    def test_cache_records_hashes_and_reindexes_stale_files(self):
        first = code_index.build_index(self.root, cache_dir=self.outside)
        self.assertEqual(first.info["counts"]["indexed"], len(first.files))
        cached = json.loads(Path(first.info["cache"]).read_text(encoding="utf-8"))
        record = cached["files"]["pkg/util.py"]
        self.assertEqual(record["size"], os.path.getsize(os.path.join(self.root, "pkg", "util.py")))
        self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("mtime_ns", record)
        again = code_index.build_index(self.root, cache_dir=self.outside)
        self.assertEqual((again.info["counts"].get("indexed", 0), again.info["counts"]["reused"]),
                         (0, len(again.files)))
        util = Path(self.root, "pkg", "util.py")
        util.write_text(util.read_text(encoding="utf-8") + "\n\ndef freshly_added_wombat():\n    pass\n",
                        encoding="utf-8", newline="\n")
        frozen = code_index.build_index(self.root, cache_dir=self.outside, frozen=True)
        self.assertEqual(frozen.info["stale"], ["pkg/util.py"])
        self.assertEqual(code_index.find(frozen, "freshly added wombat", 5)["results"], [])
        refreshed = code_index.build_index(self.root, cache_dir=self.outside)
        self.assertEqual(refreshed.info["counts"]["indexed"], 1)
        self.assertEqual(code_index.find(refreshed, "freshly added wombat", 5)["results"][0]["symbol"],
                         "freshly_added_wombat")
        os.remove(os.path.join(self.root, "tools", "runner.py"))
        self.assertEqual(code_index.build_index(self.root, cache_dir=self.outside).info["removed"], 1)

    def test_cache_stays_outside_the_tree_unless_named_there(self):
        before = sorted(str(path) for path in Path(self.root).rglob("*"))
        code_index.build_index(self.root)
        self.assertEqual(sorted(str(path) for path in Path(self.root).rglob("*")), before)
        inside = os.path.join(self.root, "index-cache")
        first = code_index.build_index(self.root, cache_dir=inside)
        self.assertTrue(os.path.isfile(first.info["cache"]))
        second = code_index.build_index(self.root, cache_dir=inside)
        self.assertFalse(any(path.startswith("index-cache/") for path in second.files))
        self.assertEqual(second.info["counts"].get("indexed", 0), 0)

    def test_windows_shaped_paths_are_accepted_and_output_is_posix(self):
        for text in ("pkg\\sub\\deep.py", "pkg/sub/deep.py", os.path.join(self.root, "pkg", "sub", "deep.py"),
                     "pkg.sub.deep", ".\\pkg\\sub\\deep.py"):
            with self.subTest(text=text):
                self.assertEqual(self.index.user_path(text), "pkg/sub/deep.py")
        for text in ("..\\outside.py", "C:\\elsewhere\\x.py", "/elsewhere/x.py"):
            with self.subTest(text=text), self.assertRaises(code_index.CodeIndexError):
                self.index.user_path(text)
        crlf = os.path.join(self.root, "win", "crlf.py")
        os.makedirs(os.path.dirname(crlf))
        with open(crlf, "wb") as handle:
            handle.write(b"\xef\xbb\xbfimport os\r\n\r\n\r\ndef windows_line_kangaroo():\r\n    return os.sep\r\n")
        index = code_index.build_index(self.root)
        top = code_index.find(index, "windows line kangaroo", 5)["results"][0]
        self.assertEqual((top["path"], top["line"]), ("win/crlf.py", 4))
        process = run_cli("affected", "pkg\\util.py", "--json", "--root", self.root)
        self.assertEqual(process.returncode, 0, process.stderr)
        paths = [row["path"] for row in json.loads(process.stdout)["results"]]
        self.assertEqual(paths, ["app/main.py", "checks/check.py", "pkg/sub/deep.py"])
        self.assertFalse(any("\\" in path for path in index.files))

    def test_cli_json_shapes_and_exit_codes(self):
        def as_json(*args):
            process = run_cli(*args, "--json", cwd=self.root)
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)

        found = as_json("find", "join path parts safely", "--limit", "2")
        self.assertEqual(found["schema_version"], 1)
        self.assertEqual(set(found["results"][0]) - {"duplicates"}, {"path", "score", "symbol", "line"})
        for report in (as_json("callers", "helper_func"), as_json("affected", "pkg/util.py::helper_func")):
            self.assertEqual(report["schema_version"], 1)
            self.assertTrue(report["results"])
            self.assertTrue({"path", "line", "symbol"} <= set(report["results"][0]))
        self.assertEqual(as_json("path", "app/main.py", "pkg/util.py")["path"], ["app/main.py", "pkg/util.py"])
        stats = as_json("stats")
        self.assertGreater(stats["symbols"], 0)
        self.assertIn("build_seconds", stats)
        self.assertEqual(as_json("find", "nothingmatchesthis")["results"], [])
        self.assertEqual(as_json("callers", "nothing_calls_this")["results"], [])
        text = run_cli("find", "join path parts", cwd=self.root)
        self.assertEqual(text.returncode, 0)
        self.assertIn("pkg/util.py:4  helper_func", text.stdout)
        for args in (("path", "app/main.py", "no/such/module.py"), ("affected", "../outside.py"),
                     ("stats", "--root", os.path.join(self.root, "missing"))):
            with self.subTest(args=args):
                failed = run_cli(*args, cwd=self.root)
                self.assertEqual(failed.returncode, 1)
                self.assertTrue(failed.stderr.startswith("code_index: "), failed.stderr)
                self.assertNotIn("Traceback", failed.stderr)
        self.assertEqual(run_cli("find", "x", "--limit", "0", cwd=self.root).returncode, 2)

    def test_script_and_its_help_use_no_game_wording(self):
        wording = re.compile(r"(?i)\bgames?\b|\bgaming\b|\bplay(?:s|ed|er|ers|ing)?\b|\u73a9|\u904a\u6232|\u95dc\u5361")
        self.assertIsNone(wording.search((ROOT / "scripts" / "code_index.py").read_text(encoding="utf-8")))
        process = run_cli("--help")
        self.assertEqual(process.returncode, 0)
        for command in ("find", "callers", "path", "affected", "stats"):
            self.assertIn(command, process.stdout)
        self.assertIsNone(wording.search(process.stdout))


if __name__ == "__main__":
    unittest.main()
