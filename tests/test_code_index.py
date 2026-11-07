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
import unittest.mock

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


CLI_CACHE = tempfile.TemporaryDirectory(prefix="oaw-code-index-user-cache-")  # never the real user cache


def tearDownModule():
    CLI_CACHE.cleanup()


def run_cli(*args, cwd=None, cache_home=None):
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    environment.pop(code_index.CACHE_ENV, None)
    environment["XDG_CACHE_HOME"] = environment["LOCALAPPDATA"] = cache_home or CLI_CACHE.name
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


JS_FIXTURE = {
    "tsconfig.base.json": '{"compilerOptions": {"baseUrl": "src"}}\n',
    "tsconfig.json": '{\n  // comments and trailing commas are allowed here\n  "extends": "./tsconfig.base.json",\n'
                     '  "compilerOptions": {"paths": {"@lib/*": ["lib/*"]},},\n}\n',
    "package.json": '{\n  "name": "fixture",\n  "main": "./src/app/main.js",\n  "bin": {"fx": "./bin/cli.js"}\n}\n',
    "src/base/event.ts": """
        /** Something that can fire. */
        export interface IEmitter {
            fire(value: number): void;
        }

        export class Emitter implements IEmitter {
            static create(): Emitter { return new Emitter(); }
            fire(value: number): void {
                this.deliver(value);
            }
            protected deliver(value: number) { }
        }

        export class LoudEmitter extends Emitter {
            protected deliver(value: number) {
                super.deliver(value * 2);
            }
        }

        export function createEmitter(): Emitter {
            // a comment that mentions fire(1)
            const text = "fire(2)", other = `fire(3) ${String(4)}`, pattern = /fire\(5\)/g;
            return new Emitter();
        }

        export default function makeDefault() { return 1; }
        export const registry = new Emitter();
    """,
    "src/base/index.ts": "export * from './event.js';\nexport { createEmitter as makeEmitter } from './event.js';\n",
    "src/lib/util.ts": """
        export const helper = (x: number) => x + 1;
        export namespace Strings {
            export function trim(s: string) {
                return s.trim();
            }
        }
    """,
    "src/app/main.ts": """
        import { Emitter, IEmitter, makeEmitter, registry } from '../base/index.js';
        import mk, { LoudEmitter } from '../base/event';
        import * as util from '@lib/util';
        import { Strings } from 'lib/util';
        import { readFile } from 'fs';

        export class App {
            private readonly emitter = new Emitter();
            constructor(private readonly other: IEmitter, private loud: LoudEmitter) {}

            getEmitter(): Emitter {
                return this.emitter;
            }

            async run(unknown: any) {
                this.emitter.fire(1);
                this.other.fire(2);
                this.loud.fire(3);
                this.getEmitter().fire(4);
                const made = makeEmitter();
                made.fire(5);
                registry.fire(6);
                unknown.fire(7);
                util.helper(8);
                Strings.trim(' x ');
                mk();
                readFile('x', () => {});
                const later = await import('../base/event.js');
            }
        }
    """,
    "src/legacy/old.js": """
        const { helper } = require('../lib/util');
        function legacy() {
            return helper(1);
        }
        exports.other = function () {
            return legacy();
        };
        module.exports.legacy = legacy;
    """,
    "src/legacy/use.js": "const old = require('./old');\nold.legacy();\nold.other();\n",
    "src/app/spread.ts": "import * as util from '@lib/util';\nexport const values = [...util.helper(1)];\n",
    "src/base/service.ts": """
        export const IService = createDecorator<IService>('service');
        export interface IService {
            run(): void;
        }
        export class Service implements IService {
            run(): void { }
        }
        export class Plain {
            run(): void { }
        }
    """,
    "src/app/consumer.ts": """
        import { IService } from '../base/service';
        export class Consumer {
            constructor(@IService private readonly service: IService) {}
            go() {
                this.service.run();
            }
        }
    """,
    "web/view.jsx": "export function View() {\n  return <p onClick={() => go()}>Don't stop</p>;\n}\nfunction go() {}\n",
    "bin/cli.js": "#!/usr/bin/env node\nrequire('../src/legacy/use');\n",
    "tools/jsconfig.json": '{"compilerOptions": {"baseUrl": "."}}\n',
    "tools/a.js": "import { b } from 'b';\nb();\n",
    "tools/b.js": "export function b() {}\n",
    "tools/report.py": """
        import argparse


        def main():
            argparse.ArgumentParser().parse_args()


        if __name__ == "__main__":
            main()
    """,
}


class JavaScriptIndexTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oaw-code-index-js-")
        self.addCleanup(temporary.cleanup)
        self.temporary = temporary.name
        self.root = os.path.join(temporary.name, "repo")
        os.makedirs(self.root)
        write_tree(self.root, JS_FIXTURE)
        self.index = code_index.build_index(self.root)

    def sites(self, symbol, limit=50):
        report = code_index.callers(self.index, symbol, limit)
        return {(row["path"], row["line"], row["resolved"]) for row in report["results"]}, report

    def test_scanner_blanks_comments_strings_templates_and_regular_expressions(self):
        text = "a(`x ${b(`y${c}`)} z`); // d()\nlet r = /e\\(/g.test(s) / 2; f('g(');\n/* h()\n */ i();\n"
        code, strings, comments = code_index._js_mask(text)
        self.assertEqual(code.count("\n"), text.count("\n"))
        self.assertEqual(re.findall(r"(?<![\w.])([a-z])\(", code), ["a", "b", "f", "i"])
        self.assertEqual(sorted(value for _, value in strings.values()), ["g("])
        self.assertEqual([raw[:4] for _, raw in comments], ["// d", "/* h"])

    def test_definitions_classes_methods_arrows_and_namespaces(self):
        defs = {(name, kind) for name, kind, _line, _end in self.index.files["src/base/event.ts"]["js"]["defs"]}
        self.assertTrue({("IEmitter", "interface"), ("IEmitter.fire", "method"), ("Emitter", "class"),
                         ("Emitter.create", "method"), ("Emitter.fire", "method"), ("Emitter.deliver", "method"),
                         ("LoudEmitter.deliver", "method"), ("createEmitter", "function"),
                         ("makeDefault", "function"), ("registry", "variable")} <= defs)
        util = {(name, kind) for name, kind, _line, _end in self.index.files["src/lib/util.ts"]["js"]["defs"]}
        self.assertEqual(util, {("helper", "function"), ("Strings", "namespace"), ("Strings.trim", "function")})
        legacy = {name for name, *_ in self.index.files["src/legacy/old.js"]["js"]["defs"]}
        self.assertTrue({"legacy", "other"} <= legacy)
        top = code_index.find(self.index, "something that can fire", 5)["results"][0]
        self.assertEqual((top["path"], top["symbol"].split(".")[0]), ("src/base/event.ts", "IEmitter"))  # JSDoc

    def test_imports_resolve_relative_index_tsconfig_paths_and_packages(self):
        module = self.index.js_module
        self.assertEqual(module("src/app/main.ts", "../base/index.js"), "src/base/index.ts")  # .js names .ts
        self.assertEqual(module("src/app/main.ts", "../base/event"), "src/base/event.ts")
        self.assertEqual(module("src/app/main.ts", "../base"), "src/base/index.ts")
        self.assertEqual(module("src/app/main.ts", "@lib/util"), "src/lib/util.ts")  # paths, after extends
        self.assertEqual(module("src/app/main.ts", "lib/util"), "src/lib/util.ts")  # baseUrl
        self.assertEqual(module("tools/a.js", "b"), "tools/b.js")  # jsconfig.json
        self.assertIsNone(module("src/app/main.ts", "fs"))
        self.assertIsNone(module("src/app/main.ts", "../../../outside"))
        labels = {(target, label) for _line, _scope, target, label in self.index.import_edges()["src/app/main.ts"]}
        self.assertIn(("src/base/event.ts", "import('../base/event.js')"), labels)
        self.assertIn(("src/lib/util.ts", "import * as util from '@lib/util'"), labels)
        chain = code_index.import_path(self.index, "src/legacy/use.js", "src/lib/util.ts")
        self.assertEqual(chain["path"], ["src/legacy/use.js", "src/legacy/old.js", "src/lib/util.ts"])

    def test_callers_resolve_types_returns_reexports_and_keep_unknown_receivers_apart(self):
        fire, report = self.sites("Emitter.fire")
        self.assertEqual({(line, resolved) for path, line, resolved in fire if path == "src/app/main.ts"},
                         {(16, True), (18, True), (19, True), (21, True), (22, True), (17, False), (23, False)})
        self.assertEqual(report["results"][-2]["line"], 17)  # through IEmitter, which Emitter implements: first
        self.assertFalse(any(path == "src/base/event.ts" for path, _line, _resolved in fire))  # strings, comments
        deliver, _ = self.sites("src/base/event.ts::Emitter::deliver")
        self.assertEqual(deliver, {("src/base/event.ts", 9, True), ("src/base/event.ts", 16, True)})
        self.assertEqual(self.sites("helper")[0], {("src/app/main.ts", 24, True), ("src/legacy/old.js", 3, True),
                                                   ("src/app/spread.ts", 2, True)})  # ...spread is no receiver
        self.assertEqual(self.sites("Strings.trim")[0], {("src/app/main.ts", 25, True)})
        self.assertEqual(self.sites("makeDefault")[0], {("src/app/main.ts", 26, True)})  # a default import alias
        self.assertEqual(self.sites("legacy")[0], {("src/legacy/old.js", 6, True), ("src/legacy/use.js", 2, True)})
        self.assertEqual(self.sites("fs.readFile")[0], {("src/app/main.ts", 27, True)})
        self.assertEqual(self.sites("go")[0], {("web/view.jsx", 2, True)})
        classes, _ = self.sites("Emitter")
        self.assertTrue({("src/base/event.ts", 7, True), ("src/base/event.ts", 23, True),
                         ("src/base/event.ts", 27, True), ("src/app/main.ts", 8, True)} <= classes)
        scopes = {row["symbol"] for row in code_index.callers(self.index, "Emitter.fire")["results"]}
        self.assertEqual(scopes, {"App.run"})

    def test_value_and_interface_sharing_a_name_and_interface_typed_receivers(self):
        kinds = {name: kind for name, kind, *_ in self.index.files["src/base/service.ts"]["js"]["defs"]}
        self.assertEqual(kinds["IService"], "interface")  # const IService = createDecorator(...) as well
        implemented = code_index.callers(self.index, "Service.run")
        self.assertEqual([(row["path"], row["line"], row["resolved"]) for row in implemented["results"]],
                         [("src/app/consumer.ts", 5, False)])  # through IService, which Service implements
        structural = code_index.callers(self.index, "Plain.run")  # may implement IService without saying so
        self.assertEqual([(row["path"], row["resolved"]) for row in structural["results"]],
                         [("src/app/consumer.ts", False)])

    def test_affected_follows_imports_reexports_and_calls_for_two_hops(self):
        module = code_index.affected(self.index, "src/lib/util.ts")
        self.assertEqual([(row["path"], row["hop"]) for row in module["results"]],
                         [("src/app/main.ts", 1), ("src/app/spread.ts", 1), ("src/legacy/old.js", 1)])
        two = code_index.affected(self.index, "src/lib/util.ts", hops=2)
        self.assertIn(("src/legacy/use.js", 2), [(row["path"], row["hop"]) for row in two["results"]])
        symbol = code_index.affected(self.index, "src/lib/util.ts::helper", hops=2)
        self.assertEqual([(row["path"], row["hop"]) for row in symbol["results"]],
                         [("src/app/main.ts", 1), ("src/app/spread.ts", 1), ("src/legacy/old.js", 1),
                          ("src/legacy/use.js", 2)])
        self.assertTrue(symbol["complete"])
        process = run_cli("path", "src\\legacy\\use.js", "src/lib/util.ts", "--root", self.root, "--json")
        self.assertEqual(json.loads(process.stdout)["path"][-1], "src/lib/util.ts")

    def test_lists_say_whether_they_are_complete_or_truncated(self):
        full = code_index.callers(self.index, "Emitter.fire", limit=50)
        self.assertEqual((full["complete"], full["truncated"], full["total"]), (True, 0, 7))
        self.assertIn("dynamic dispatch", full["limits"])
        cut = code_index.callers(self.index, "Emitter.fire", limit=3)
        self.assertEqual((cut["complete"], cut["truncated"], len(cut["results"])), (False, 4, 3))
        text = run_cli("callers", "Emitter.fire", "--limit", "6", "--root", self.root).stdout
        self.assertIn("truncated: 1 more (raise --limit)", text)
        self.assertIn("~ = same name on a receiver whose type is not known", text)
        text = run_cli("affected", "src/lib/util.ts", "--root", self.root).stdout
        self.assertIn("complete within the index", text)
        cut = code_index.affected(self.index, "src/lib/util.ts", hops=2, limit=1)
        self.assertEqual((cut["complete"], cut["truncated"], cut["hops"]), (False, 3, 2))
        report = json.loads(run_cli("callers", "Emitter.fire", "--json", "--root", self.root).stdout)
        self.assertEqual((report["complete"], report["truncated"]), (True, 0))

    def test_overview_is_one_capped_page_of_pointers(self):
        report = code_index.overview(self.index)
        entries = {(entry["path"], entry["kind"], entry.get("target")) for entry in report["entry_points"]}
        self.assertIn(("package.json", "package.json main", "src/app/main.ts"), entries)  # ./src/app/main.js
        self.assertIn(("package.json", "package.json bin fx", "bin/cli.js"), entries)
        self.assertIn(("bin/cli.js", "#! node script", None), entries)
        self.assertIn(("tools/report.py", 'if __name__ == "__main__", argparse', None), entries)
        self.assertEqual(next(entry["line"] for entry in report["entry_points"] if entry["kind"] == "package.json main"), 3)
        ranked = {row["symbol"]: row for row in report["most_called"]}
        self.assertEqual(report["most_called"][0]["symbol"], "Emitter")
        self.assertIn("Emitter.fire", ranked)
        self.assertEqual((ranked["Emitter.fire"]["signature"], ranked["Emitter.fire"]["calls"]),
                         ("fire(value: number): void {", 5))
        self.assertLessEqual(report["chars"], code_index.OVERVIEW_CHARS)
        small = code_index.overview(self.index, max_chars=400)
        self.assertLessEqual(small["chars"], 400)
        self.assertTrue(small["truncated"])
        self.assertIn("truncated:", small["text"])
        process = run_cli("overview", "--root", self.root)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertLessEqual(len(process.stdout), code_index.OVERVIEW_CHARS + 1)

    def test_default_cache_is_the_user_cache_directory_never_the_tree(self):
        home = os.path.join(self.temporary, "user-cache")
        before = sorted(str(path) for path in Path(self.root).rglob("*"))
        process = run_cli("callers", "helper", "--root", self.root, cache_home=home)
        self.assertEqual(process.returncode, 0, process.stderr)
        written = sorted(path.name for path in Path(home, "oaw", "code-index").iterdir())
        self.assertEqual(len(written), 2)
        self.assertTrue(written[0].startswith("code-index-") and written[1].endswith(".units.json"))
        self.assertEqual(sorted(str(path) for path in Path(self.root).rglob("*")), before)
        stats = json.loads(run_cli("stats", "--json", "--root", self.root, cache_home=home).stdout)
        self.assertEqual((stats["cache"]["origin"], stats["cache"]["reused"]), ("default", stats["files"]))
        empty = os.path.join(self.temporary, "unused-cache")
        run_cli("stats", "--no-cache", "--root", self.root, cache_home=empty)
        self.assertFalse(os.path.exists(empty))
        self.assertEqual(run_cli("stats", "--no-cache", "--cache", empty, "--root", self.root).returncode, 2)
        with unittest.mock.patch.dict(os.environ, {"XDG_CACHE_HOME": os.path.join(self.root, "c")}):
            if os.name != "nt":
                self.assertEqual(code_index.choose_cache(self.root), (None, "none"))  # inside the indexed tree
                self.assertEqual(code_index.choose_cache(self.root, no_cache=True), (None, "none"))
        with unittest.mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "relative/dir", "HOME": self.temporary}):
            if os.name != "nt":
                self.assertEqual(code_index.default_cache_dir(),
                                 os.path.join(self.temporary, ".cache", "oaw", "code-index"))
        with unittest.mock.patch.object(code_index.os, "name", "nt"), \
                unittest.mock.patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\me\\AppData\\Local"}):
            self.assertTrue(code_index.default_cache_dir().startswith("C:\\Users\\me\\AppData\\Local"))
            self.assertTrue(code_index.default_cache_dir().replace("\\", "/").endswith("oaw/code-index"))

    def test_cache_parts_engine_fingerprint_and_parallel_indexing(self):
        cache = os.path.join(self.temporary, "cache")
        first = code_index.build_index(self.root, cache_dir=cache)
        light = code_index.build_index(self.root, cache_dir=cache, need_units=False)
        self.assertEqual(light.info["counts"].get("indexed", 0), 0)
        self.assertNotIn("units", light.files["src/app/main.ts"])
        self.assertEqual(code_index.callers(light, "helper")["total"], 3)
        full = code_index.build_index(self.root, cache_dir=cache)
        self.assertEqual(full.files["src/app/main.ts"]["units"], first.files["src/app/main.ts"]["units"])
        os.remove(code_index._units_file(first.info["cache"]))  # a lost units file means a rebuild
        self.assertEqual(code_index.build_index(self.root, cache_dir=cache, need_units=False).info["counts"]["indexed"],
                         len(first.files))
        with unittest.mock.patch.object(code_index, "ENGINE", "other-engine"):
            self.assertEqual(code_index.build_index(self.root, cache_dir=cache).info["counts"]["indexed"],
                             len(first.files))
        with unittest.mock.patch.object(code_index, "PARALLEL_MIN_FILES", 1):
            parallel = code_index.build_index(self.root)
        self.assertEqual(parallel.files, self.index.files)

    def test_same_size_edit_with_restored_mtime_is_still_reindexed(self):
        cache = os.path.join(self.temporary, "cache")
        path = Path(self.root, "tools", "b.js")
        code_index.build_index(self.root, cache_dir=cache)
        info = os.stat(path)
        path.write_text("export function c() {}\n", encoding="utf-8", newline="\n")  # same size
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
        again = code_index.build_index(self.root, cache_dir=cache)
        if os.name == "nt":  # no inode change time: size and mtime alone, as documented
            self.assertIsNone(code_index._ctime(os.stat(path)))
        else:
            self.assertEqual(again.info["counts"]["indexed"], 1)
            self.assertIn("c", {name for name, *_ in again.files["tools/b.js"]["js"]["defs"]})

    def test_windows_shaped_paths_and_crlf_sources(self):
        self.assertEqual(self.index.user_path("src\\app\\main.ts"), "src/app/main.ts")
        self.assertEqual(self.index.user_path("src/lib/util"), "src/lib/util.ts")
        crlf = Path(self.root, "win", "crlf.ts")
        crlf.parent.mkdir()
        crlf.write_bytes(b"\xef\xbb\xbfimport { helper } from '../src/lib/util';\r\n\r\nexport function useIt() {\r\n"
                         b"    return helper(2);\r\n}\r\n")
        index = code_index.build_index(self.root)
        self.assertIn(("win/crlf.ts", 4, True), {(row["path"], row["line"], row["resolved"])
                                                 for row in code_index.callers(index, "helper")["results"]})
        self.assertEqual([row[:3] for row in index.files["win/crlf.ts"]["js"]["defs"]], [["useIt", "function", 3]])

    def test_pagerank_prefers_definitions_that_many_callers_reach(self):
        ranks = code_index.pagerank({("a", "c"): 1, ("b", "c"): 1, ("c", "d"): 1, ("a", "b"): 1})
        self.assertEqual(max(ranks, key=ranks.get), "d")
        self.assertAlmostEqual(sum(ranks.values()), 1.0)
        self.assertEqual(code_index.pagerank({}), {})


REVIEW_FIXTURE = {  # Codex review round 10 of the JS/TS engine
    "lib/save.ts": "export function save() {}\n",
    "app/shadow.ts": ("import { save } from '../lib/save';\nexport function run(save) {\n    save();\n}\n"
                      "export function run2() {\n    save();\n}\nexport function run3() {\n    const save = make();\n"
                      "    save();\n}\n"),
    "star/a.ts": "function save() {}\nexport function other() { save(); }\n",
    "star/b.ts": "export function save() {}\n",
    "star/barrel.ts": "export * from './a';\nexport * from './b';\n",
    "star/use.ts": "import { save } from './barrel';\nsave();\n",
    "alias/lib.ts": "export function original() {}\n",
    "alias/barrel.ts": "export { original as renamed } from './lib';\n",
    "alias/app.ts": "import { renamed } from './barrel';\nrenamed();\n",
    "alias/ns.ts": "import * as barrel from './barrel';\nbarrel.renamed();\n",
    "alias/direct.ts": "import { original as renamed } from './lib';\nexport function go() {\n    renamed();\n}\n",
    "pylib.py": "def original():\n    return 1\n",
    "pyapp.py": "from pylib import original as renamed\n\n\ndef main():\n    return renamed()\n",
    "anon/fn.ts": "export default function () {\n    return 1;\n}\n",
    "anon/cls.ts": "export default class {\n    run() {}\n}\n",
    "anon/use.ts": "import make from './fn';\nimport Thing from './cls';\nmake();\nnew Thing().run();\n",
    "index.js": "export function rootThing() {}\n",
    "main.js": "const root = require('./');\nroot.rootThing();\n",
    "sub/use.ts": "import { rootThing } from '..';\nrootThing();\n",
    "cfg/tsconfig.a.json": '{"compilerOptions": {"baseUrl": ".", "paths": {"@x/*": ["x/*"]}}}\n',
    "cfg/tsconfig.b.json": '{"compilerOptions": {"strict": true}}\n',
    "cfg/tsconfig.json": '{"extends": ["./tsconfig.a.json", "./tsconfig.b.json"]}\n',
    "cfg/x/thing.ts": "export function thing() {}\n",
    "cfg/use.ts": "import { thing } from '@x/thing';\nthing();\n",
    "jcfg/config/base.json": '{"compilerOptions": {"baseUrl": "..", "paths": {"#lib/*": ["lib/*"]}}}\n',
    "jcfg/tsconfig.json": '{"extends": "./config/base.json"}\n',
    "jcfg/lib/tool.ts": "export function tool() {}\n",
    "jcfg/use.ts": "import { tool } from '#lib/tool';\ntool();\n",
    # Codex review round 11
    "arrow/use.ts": "import { save } from '../lib/save';\nexport const run = save => save();\nexport const run2 = () => save();\n",
    "block/use.ts": ("import { save } from '../lib/save';\nexport function f(flag) {\n    if (flag) {\n"
                     "        const save = () => 1;\n        save();\n    }\n    save();\n}\n"),
    "defalias/lib.ts": "export function original() {}\n",
    "defalias/barrel.ts": "export { original as default } from './lib';\n",
    "defalias/app.ts": "import renamed from './barrel';\nrenamed();\n",
    "defalias/dlib.js": "function original2() {}\nmodule.exports = original2;\n",
    "defalias/req.js": "const renamed = require('./dlib');\nrenamed();\n",
    "reqlocal/use.js": ("function f() {\n    const path = require('path');\n    return path.resolve('x');\n}\n"
                        "if (ok) {\n    const lib = require('../lib/save');\n    lib.save();\n}\n"),
}


class JavaScriptResolutionReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oaw-code-index-review-")
        self.addCleanup(temporary.cleanup)
        self.root = os.path.join(temporary.name, "repo")
        os.makedirs(self.root)
        write_tree(self.root, REVIEW_FIXTURE)
        self.index = code_index.build_index(self.root)

    def rows(self, symbol):
        return {(row["path"], row["line"], row["resolved"]) for row in code_index.callers(self.index, symbol)["results"]}

    def test_parameters_and_local_names_shadow_imports(self):
        rows = self.rows("lib/save.ts::save")
        self.assertIn(("app/shadow.ts", 6, True), rows)
        self.assertNotIn(("app/shadow.ts", 3, True), rows)  # function run(save) { save(); }
        self.assertNotIn(("app/shadow.ts", 10, True), rows)  # const save = make(); save();
        self.assertIsNone(self.index.js_resolve("app/shadow.ts", "run", "save"))
        edges = code_index.call_graph(self.index)
        self.assertIn((("app/shadow.ts", "run2"), ("lib/save.ts", "save")), edges)
        self.assertNotIn((("app/shadow.ts", "run"), ("lib/save.ts", "save")), edges)

    def test_export_star_skips_names_a_module_does_not_export(self):
        self.assertEqual(self.index.js_resolve("star/use.ts", "", "save"), ("def", "star/b.ts", "save"))
        self.assertIn(("star/use.ts", 2, True), self.rows("star/b.ts::save"))
        self.assertNotIn(("star/use.ts", 2, True), self.rows("star/a.ts::save"))

    def test_callers_and_affected_follow_reexport_aliases(self):
        report = code_index.callers(self.index, "alias/lib.ts::original")
        self.assertTrue({("alias/app.ts", 2, True), ("alias/ns.ts", 2, True), ("alias/direct.ts", 3, True)}
                        <= {(row["path"], row["line"], row["resolved"]) for row in report["results"]})
        self.assertTrue(report["complete"])
        affected = {row["path"] for row in code_index.affected(self.index, "alias/lib.ts::original")["results"]}
        self.assertTrue({"alias/app.ts", "alias/barrel.ts", "alias/direct.ts"} <= affected)

    def test_anonymous_default_exports_are_exported(self):
        self.assertEqual(self.rows("anon/fn.ts::default"), {("anon/use.ts", 3, True)})
        self.assertEqual(self.rows("anon/cls.ts::default.run"), {("anon/use.ts", 4, True)})
        affected = code_index.affected(self.index, "anon/fn.ts::default")["results"]
        self.assertEqual([row["path"] for row in affected], ["anon/use.ts"])

    def test_call_graph_keeps_calls_through_import_aliases(self):
        edges = code_index.call_graph(self.index)
        self.assertIn((("pyapp.py", "main"), ("pylib.py", "original")), edges)
        self.assertIn((("alias/direct.ts", "go"), ("alias/lib.ts", "original")), edges)
        self.assertIn((("alias/app.ts", ""), ("alias/lib.ts", "original")), edges)

    def test_index_files_at_the_root_resolve(self):
        self.assertEqual(self.index.js_module("main.js", "./"), "index.js")
        self.assertEqual(self.index.js_module("sub/use.ts", ".."), "index.js")
        self.assertIn(("main.js", 2, True), self.rows("index.js::rootThing"))

    def test_extends_lists_merge_option_by_option(self):
        self.assertEqual(self.index.js_module("cfg/use.ts", "@x/thing"), "cfg/x/thing.ts")

    def test_a_single_arrow_parameter_shadows_an_import(self):
        rows = self.rows("lib/save.ts::save")
        self.assertIn(("arrow/use.ts", 3, True), rows)
        self.assertNotIn(("arrow/use.ts", 2, True), rows)  # const run = save => save()
        self.assertIsNone(self.index.js_resolve("arrow/use.ts", "run", "save"))

    def test_let_and_const_are_scoped_to_their_block(self):
        report = code_index.callers(self.index, "lib/save.ts::save")
        rows = {(row["path"], row["line"], row["resolved"]): row["symbol"] for row in report["results"]}
        self.assertEqual(rows.get(("block/use.ts", 7, True)), "f")  # after the block: the import
        self.assertNotIn(("block/use.ts", 5, True), rows)  # inside the block: the block's own save

    def test_default_and_require_aliases_follow_the_resolved_export(self):
        self.assertEqual(self.index.js_resolve("defalias/app.ts", "", "renamed"), ("def", "defalias/lib.ts", "original"))
        self.assertIn(("defalias/app.ts", 2, True), self.rows("defalias/lib.ts::original"))
        self.assertEqual(self.index.js_resolve("defalias/req.js", "", "renamed"),
                         ("def", "defalias/dlib.js", "original2"))
        self.assertIn(("defalias/req.js", 2, True), self.rows("defalias/dlib.js::original2"))

    def test_a_local_bound_by_require_keeps_resolving_through_it(self):
        self.assertEqual(self.index.js_resolve("reqlocal/use.js", "f", "path.resolve"), ("ext", "path.resolve"))
        self.assertIn(("reqlocal/use.js", 7, True), self.rows("lib/save.ts::save"))

    def test_extends_may_name_any_local_json_file(self):
        self.assertEqual(self.index.js_module("jcfg/use.ts", "#lib/tool"), "jcfg/lib/tool.ts")


if __name__ == "__main__":
    unittest.main()
