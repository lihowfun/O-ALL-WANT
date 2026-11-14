#!/usr/bin/env python3
"""Offline M3 probe using the installed Codex sandbox, without a model session.

Uses named permission profiles (Codex CLI 0.167.2). No user config is changed.
The child must observe .agents as read-only and .oaw as writable.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    version = subprocess.run([args.codex, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="oaw-native-memory-probe-") as temporary:
        root = Path(temporary)
        primary = root / ".agents/memory.md"
        primary.parent.mkdir()
        original = "# Memory\n---\n## [2026-10-01] [NOTE] existing evidence\n"
        primary.write_text(original, encoding="utf-8")
        environment = dict(os.environ, AGENT_MEMORY_BASE_DIR=temporary, PYTHONDONTWRITEBYTECODE="1")
        command = [
            args.codex, "sandbox", "-P", "oaw_probe",
            "-c", 'permissions.oaw_probe.filesystem={":root"="read",":workspace_roots"={"."="write"}}',
            "-c", "permissions.oaw_probe.network.enabled=false",
            "-C", temporary, "--", sys.executable, "-c",
        ]
        write_code = """
import contextlib, errno, io, json, sys
from pathlib import Path
sys.path.insert(0, SCRIPTS)
import context_hub
try:
    Path('.agents/direct-probe.txt').write_text('must be denied')
except OSError as exc:
    assert exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS), exc
    denied = exc.errno
else:
    raise AssertionError('.agents is writable; this is not the required sandbox probe')
output = io.StringIO()
with contextlib.redirect_stdout(output):
    context_hub.memory_add('[DECISION] native sandbox needle; scope=fixture')
assert Path('.oaw/memory-pending.md').is_file()
print(json.dumps({'primary_write_errno': denied, 'memory_add': 'ok', 'output': output.getvalue()}))
""".replace("SCRIPTS", repr(str(scripts)))
        write = subprocess.run(command + [write_code], env=environment, capture_output=True, text=True, encoding="utf-8")
        if write.returncode:
            print(json.dumps({"status": "failed", "stage": "sandbox-write", "codex": version,
                              "exit_code": write.returncode, "stdout": write.stdout, "stderr": write.stderr}))
            return 1
        recall_code = """
import contextlib, io, json, sys
sys.path.insert(0, SCRIPTS)
import context_hub
out = io.StringIO()
with contextlib.redirect_stdout(out):
    context_hub.memory_recall('native sandbox needle', json_out=True)
packet = json.loads(out.getvalue())
assert len(packet['results']) == 1, packet
assert packet['results'][0]['source'] == '.oaw/memory-pending.md', packet
print(json.dumps({'later_recall': 'ok', 'source': packet['results'][0]['source']}))
""".replace("SCRIPTS", repr(str(scripts)))
        recall = subprocess.run(command + [recall_code], env=environment, capture_output=True, text=True, encoding="utf-8")
        if recall.returncode:
            print(json.dumps({"status": "failed", "stage": "sandbox-recall", "codex": version,
                              "exit_code": recall.returncode, "stdout": recall.stdout, "stderr": recall.stderr}))
            return 1
        assert primary.read_text(encoding="utf-8") == original
        assert not (primary.parent / ".memory.md.oaw.lock").exists()
        print(json.dumps({"status": "passed", "codex": version, "python": sys.version.split()[0],
                          "model_calls": 0, "network": "disabled", "primary_unchanged": True,
                          "write": json.loads(write.stdout), "recall": json.loads(recall.stdout)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
