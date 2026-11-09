#!/usr/bin/env bash
set -eu
export OAW_CONFIG_HOME="$PWD/.state/config"
export OAW_LAB_HOME="$PWD/.state/lab"
export XDG_CACHE_HOME="$PWD/.state/cache"
export XDG_DATA_HOME="$PWD/.state/data"
export TMPDIR="$PWD/.state/tmp"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 LC_ALL=C.UTF-8
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
unset OAW_VERDICTS OAW_CODE_INDEX_CACHE AGENT_MEMORY_BASE_DIR
mkdir -p "$TMPDIR"
exec /usr/bin/python3 - <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys

def need(condition):
    if not condition:
        raise RuntimeError("Unexpected setup, command output, or resulting state")

def call(args, cwd="project"):
    return subprocess.run(["/usr/bin/python3", *args], cwd=cwd,
                          capture_output=True, text=True, timeout=8)

def good(args, cwd="project"):
    p = call(args, cwd)
    need(p.returncode == 0 and p.stderr == "")
    return json.loads(p.stdout)

def snapshot(root="project"):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in Path(root).rglob("*") if p.is_file()}

def check():
    cli = ["oaw/scripts/oaw.py"]
    good(cli + ["add", "./local-skills/notes", "./local-skills/scripty", "--target", "./project",
                "--choice", "only", "--consent", "scripts", "--apply", "--json"], ".")
    skill = Path("project/.agents/skills/notes/SKILL.md")
    need(skill.is_file())
    need(json.loads(Path("project/.oaw/install.json").read_text())["profile"] == "manager-only")
    need({r["package"] for r in good(cli + ["list", "--target", "./project", "--json"], ".")["receipt"]}
         == {"notes", "scripty"})
    skill.write_bytes(skill.read_bytes() + b"\nKeep the team's private release checklist and rollback notes here.\n")
    edited = skill.read_bytes()
    before = snapshot()
    record_path = Path("project/.oaw/user-skills.json")
    record = json.loads(record_path.read_text())
    need(record["packages"]["notes"]["parts"]["skill:notes"]["files"])
    source_before = snapshot("local-skills")
    p = call(cli + ["remove", "notes", "--target", "./project", "--apply", "--json"], ".")
    need(p.stderr == "")
    result = json.loads(p.stdout)
    need(result["remove"] == "notes" and snapshot("local-skills") == source_before)
    after = snapshot()
    # Removing unmodified companion files is allowed; other packages and policy must stay byte-identical.
    note_files = {f["path"] for f in record["packages"]["notes"]["parts"]["skill:notes"]["files"]}
    allowed = note_files | {".oaw/user-skills.json"}
    need({k:v for k,v in before.items() if k not in allowed} ==
         {k:v for k,v in after.items() if k not in allowed})
    new_record = json.loads(record_path.read_text())
    need(new_record["packages"]["scripty"] == record["packages"]["scripty"])
    if (p.returncode == 3 and result["status"] == "partial" and skill.is_file() and
        skill.read_bytes() == edited and len(result["conflicts"]) == 1 and
        result["conflicts"][0]["path"] == ".agents/skills/notes/SKILL.md" and
        "notes" in new_record["packages"]):
        kept = new_record["packages"]["notes"]["parts"]["skill:notes"]["files"]
        need(any(f["path"] == ".agents/skills/notes/SKILL.md" for f in kept))
        print("PASS: edited skill retained with a partial result and recovery record")
        return 0
    if (p.returncode == 0 and result["status"] == "removed" and not skill.exists() and
        result["conflicts"] == [] and "notes" not in new_record["packages"] and
        any(f["path"] == ".agents/skills/notes/SKILL.md" and f["action"] == "delete"
            for f in result["files"])):
        print("DEFECT: edited skill deleted without force; its recovery record removed")
        return 1
    return 2

try:
    sys.exit(check())
except Exception as exc:
    print("INCONCLUSIVE: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    sys.exit(2)
PY
