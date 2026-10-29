#!/usr/bin/env python3
"""Plan or run the EGM fast-track pilot (arms A native, B EGM, C OAW + EGM).

--dry-run (the default) prints the planned headless commands and run counts and
calls nothing. --live runs `claude -p` and spends model quota: it refuses unless
--i-have-approval <phase>-<first 12 hex of spec.sha256> is given and spec.json,
its pinned inputs and the EGM plugin tree still match their recorded hashes.
--freeze rewrites spec.json's input hashes and spec.sha256; --verify checks them.
Raw outputs stay outside the repository (default: the system temp directory).
"""

from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import pilot_common as pc  # noqa: E402

DEFAULT_CLAUDE = os.environ.get(
    "OAW_EGM_CLAUDE", "C:/Users/User/AppData/Roaming/Claude/claude-code/2.1.309/9078b9c1d466/claude.exe")
PHASES = ("F1", "F2", "F3")
MAX_ARTIFACT_BYTES = 1_000_000
CLOCK = time.monotonic  # wall clock for latency_ms; replaceable in tests


class Refused(Exception):
    """A live run is not allowed; nothing was executed."""


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def slug(case_id: str) -> str:
    return case_id.replace("/", "__")


def load(root: Path):
    return pc.load_json(root / pc.SPEC_FILE), pc.load_json(root / pc.SCENARIOS_FILE)["scenarios"]


def suite_cases(spec: dict, scenarios: list[dict], suite: str) -> dict:
    if suite == "protocol":
        return {scenario["case_id"]: scenario for scenario in scenarios}
    return {case["case_id"]: case for case in spec["suites"]["outcome"]["cases"]}


def prompts(spec: dict, suite: str, arm: str, case: dict) -> list[str]:
    command = spec["invocation"]["slash_command"]
    if suite == "protocol":
        turns = [turn["user_input"] for turn in case["turns"]]
        if spec["arms"][arm]["egm_plugin"]:
            turns[0] = f"{command.format(skill=case['skill'])} {turns[0]}"
        return turns
    prompt = spec["suites"]["outcome"]["prompt"]
    if spec["arms"][arm]["egm_plugin"]:
        return [f"{command.format(skill=prompt['skill'])} {prompt['body']}"]
    return [prompt["native_prefix"] + prompt["body"]]


def plan(spec: dict, scenarios: list[dict], phase: str) -> list[dict]:
    if phase == "F1":
        calibration = spec["phases"]["F1"]
        items = [(item["suite"], suite_cases(spec, scenarios, item["suite"])[item["case_id"]])
                 for item in calibration["cases"]]
        repeats = {arm: calibration["repeats"] for arm in calibration["arms"]}
        order = [(arm, suite, case) for suite, case in items for arm in calibration["arms"]]
    else:
        suite = spec["phases"][phase]["suite"]
        repeats = spec["suites"][suite]["repeats"]
        order = [(arm, suite, case) for arm in pc.ARMS for case in suite_cases(spec, scenarios, suite).values()]
    runs = []
    for arm, suite, case in order:
        for repeat in range(1, repeats[arm] + 1):
            runs.append({"phase": phase, "suite": suite, "arm": arm, "case_id": case["case_id"], "repeat": repeat,
                         "key": f"{suite}/{arm}/{slug(case['case_id'])}/r{repeat}",
                         "turns": prompts(spec, suite, arm, case)})
    return runs


def permission_path(path: Path) -> str:
    """Claude Code permission-rule form of an absolute path (//c/... on Windows)."""
    path = Path(os.path.abspath(path))
    if len(path.drive) == 2 and path.drive[1] == ":":
        return "//" + path.drive[0].lower() + "/" + "/".join(path.parts[1:])
    return "/" + path.as_posix()


def settings(spec: dict, plugin_dir: Path | None) -> dict:
    allow = []
    if plugin_dir is not None:
        allow = [f"Read({permission_path(plugin_dir / folder)}/**)"
                 for folder in spec["invocation"]["settings"]["plugin_read_allow"]]
    return {"disableAllHooks": spec["invocation"]["settings"]["disableAllHooks"], "permissions": {"allow": allow}}


def command(spec: dict, binary, run: dict, turn: int, *, config_dir, plugin_dir, session_id: str) -> list[str]:
    invocation = spec["invocation"]
    cmd = [str(binary), "-p", "--output-format", invocation["output_format"]]
    if invocation["output_format"] == "stream-json":
        cmd.append("--verbose")
    cmd += ["--max-budget-usd", f"{spec['budget']['max_budget_usd_per_invocation']:g}",
            "--model", spec["model"] or "<model: fill at F1>"]
    if spec.get("effort"):
        cmd += ["--effort", spec["effort"]]
    cmd += ["--setting-sources", invocation["setting_sources"], "--settings", str(Path(config_dir) / "settings.json"),
            "--permission-mode", invocation["permission_mode"], "--permission-prompts", invocation["permission_prompts"]]
    if len(run["turns"]) == 1:
        cmd.append("--no-session-persistence")
    else:
        cmd += ["--session-id", session_id] if turn == 0 else ["--resume", session_id]
    if plugin_dir is not None:
        cmd += ["--plugin-dir", str(plugin_dir)]
    if invocation["strict_mcp_config"]:
        cmd += ["--strict-mcp-config", "--mcp-config", str(Path(config_dir) / "mcp.json")]
    return cmd + ["--", run["turns"][turn]]


def planned_commands(spec: dict, run: dict, binary, run_dir) -> list[list[str]]:
    run_dir = Path(run_dir)
    plugin = run_dir / "plugin" / spec["upstream"]["plugin_name"] if spec["arms"][run["arm"]]["egm_plugin"] else None
    return [command(spec, binary, run, turn, config_dir=run_dir / "config", plugin_dir=plugin,
                    session_id="<session-uuid>") for turn in range(len(run["turns"]))]


# ---- workspaces ---------------------------------------------------------------------

def oaw_init(target: Path) -> dict:
    """Run this checkout's `scripts/oaw.py init --host claude` in-process (no subprocess)."""
    module_spec = importlib.util.spec_from_file_location("oaw_installer_for_pilot", REPO / "scripts" / "oaw.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = module.main(["init", "--target", str(target), "--host", "claude", "--json"])
    result = json.loads(output.getvalue())
    if code != 0:
        raise RuntimeError(f"OAW init failed: {result}")
    return {"status": result.get("status"), "paths": sorted(item["path"] for item in result.get("actions", []))}


def build_workspace(root: Path, spec: dict, suite: str, arm: str, dest: Path) -> dict:
    """Fresh copy of the suite fixture; arm C also gets OAW init and its overlay."""
    shutil.copytree(Path(root) / spec["suites"][suite]["fixture"], dest)
    oaw = spec["arms"][arm]["oaw"]
    if not oaw:
        return {"oaw": None}
    installed = oaw_init(dest)
    overlay = (oaw.get("overlay") or {}).get(suite)
    if overlay:
        source = Path(root) / overlay
        for path in sorted(source.rglob("*")):
            if path.is_file():
                target = dest / path.relative_to(source)
                if target.exists():
                    raise RuntimeError(f"overlay would overwrite {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                installed["paths"].append(path.relative_to(source).as_posix())
    return {"oaw": installed}


def snapshot(workspace: Path) -> dict:
    return {path.relative_to(workspace).as_posix(): pc.sha256(path.read_bytes())
            for path in workspace.rglob("*") if path.is_file() and not path.is_symlink()}


def collect_changes(workspace: Path, before: dict, dest: Path) -> dict:
    after = snapshot(workspace)
    added = sorted(set(after) - set(before))
    modified = sorted(name for name in after if name in before and after[name] != before[name])
    copied = []
    for name in added + modified:
        source = workspace / name
        if source.stat().st_size <= MAX_ARTIFACT_BYTES:
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied.append(name)
    return {"added": added, "modified": modified, "deleted": sorted(set(before) - set(after)), "copied": copied}


# ---- live guard and execution -------------------------------------------------------

def git(*args) -> str | None:
    try:
        process = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return process.stdout.strip() if process.returncode == 0 else None


def guard_live(root: Path, spec: dict, args) -> dict:
    """Raise Refused unless every pre-registered condition holds. Runs nothing before the token check."""
    if args.phase not in PHASES:
        raise Refused("--live needs one --phase of F1, F2 or F3")
    recorded = pc.recorded_spec_digest(root)
    if not args.i_have_approval:
        raise Refused("live runs spend model quota: pass --i-have-approval <phase>-<spec hash prefix> given by the user")
    if recorded is None or args.i_have_approval != pc.approval_token(args.phase, recorded):
        raise Refused("approval token does not match this phase and the recorded spec.sha256")
    problems = pc.spec_problems(root)
    if problems:
        raise Refused("pre-registered contract changed: " + "; ".join(problems))
    if not spec.get("model"):
        raise Refused("spec.json model is unset; fill it at F1 and re-freeze before any live run")
    if not args.egm_src:
        raise Refused("--egm-src (EGM checkout at the pinned commit) is required for live runs")
    plugin = Path(args.egm_src) / spec["upstream"]["plugin_subdir"]
    tree = pc.tree_digest(Path(args.egm_src), [spec["upstream"]["plugin_subdir"]]) if plugin.is_dir() else None
    if not tree or tree != spec["upstream"]["plugin_tree_sha256"]:
        raise Refused("EGM plugin tree is missing or differs from upstream.plugin_tree_sha256")
    binary = Path(args.claude)
    if not binary.is_file():
        raise Refused(f"Claude binary not found: {binary}")
    version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=60)
    if version.returncode != 0 or spec["host"]["version"] not in version.stdout:
        raise Refused(f"host version differs from spec ({spec['host']['version']}): {version.stdout.strip()!r}")
    return {"plugin": plugin, "host_version": version.stdout.strip(), "spec_sha256": recorded}


def execute(root: Path, spec: dict, runs: list[dict], args, checked: dict) -> int:
    out = Path(args.out) / args.phase
    manifest_path = out / "manifest.json"
    if manifest_path.is_file() and pc.load_json(manifest_path).get("spec_sha256") != checked["spec_sha256"]:
        raise Refused(f"{out} holds runs of another spec version; choose a new --out")
    head, status = git("rev-parse", "HEAD"), git("status", "--porcelain")
    overrides = dict(spec["invocation"]["env"])
    manifest = {
        "schema_version": 1, "phase": args.phase, "live": True, "spec_sha256": checked["spec_sha256"],
        "approval_token": args.i_have_approval, "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {"name": spec["host"]["name"], "binary": str(args.claude), "version": spec["host"]["version"],
                 "version_output": checked["host_version"]},
        "model": spec["model"], "effort": spec.get("effort") or "host-default",
        "oaw": {"head": head, "dirty": bool(status) if status is not None else None},
        "egm": {"commit": spec["upstream"]["commit"], "plugin_tree_sha256": spec["upstream"]["plugin_tree_sha256"]},
        "environment": f"{platform.system()} {platform.release()}; setting-sources={spec['invocation']['setting_sources']}; fresh temp fixture per run",
        "env_overrides": overrides, "anthropic_api_key_env_present": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "runs_planned": len(runs), "metrics_label": "operator-reported",
    }
    out.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    environment = {**os.environ, **overrides}
    for number, run in enumerate(runs, 1):
        run_dir = out / "runs" / run["key"]
        if (run_dir / "run.json").is_file():
            continue
        if run_dir.exists():
            shutil.rmtree(run_dir)
        workspace = run_dir / "workspace"
        run_dir.mkdir(parents=True)
        built = build_workspace(root, spec, run["suite"], run["arm"], workspace)
        before = snapshot(workspace)
        plugin_dir = None
        if spec["arms"][run["arm"]]["egm_plugin"]:
            plugin_dir = run_dir / "plugin" / spec["upstream"]["plugin_name"]
            shutil.copytree(checked["plugin"], plugin_dir)
        config = run_dir / "config"
        config.mkdir()
        (config / "settings.json").write_text(json.dumps(settings(spec, plugin_dir), indent=2), encoding="utf-8")
        (config / "mcp.json").write_text(json.dumps(spec["invocation"]["mcp_config"]), encoding="utf-8")
        (run_dir / "raw").mkdir()
        session = str(uuid.uuid4())
        invocations = []
        for turn in range(len(run["turns"])):
            cmd = command(spec, args.claude, run, turn, config_dir=config, plugin_dir=plugin_dir, session_id=session)
            stdout_path, stderr_path = run_dir / "raw" / f"turn{turn + 1}.out", run_dir / "raw" / f"turn{turn + 1}.stderr.txt"
            start, code, timed_out = CLOCK(), None, False
            with open(stdout_path, "wb") as stdout, open(stderr_path, "wb") as stderr:
                try:
                    code = subprocess.run(cmd, cwd=workspace, env=environment, stdin=subprocess.DEVNULL, stdout=stdout,
                                          stderr=stderr, timeout=spec["timeouts_s"][run["suite"]]).returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
            invocation = {"turn": turn + 1, "command": cmd, "exit_code": code, "timed_out": timed_out,
                          "wall_ms": round((CLOCK() - start) * 1000),
                          "stdout": stdout_path.relative_to(run_dir).as_posix(),
                          "stderr": stderr_path.relative_to(run_dir).as_posix()}
            parsed = pc.parse_output(stdout_path.read_text(encoding="utf-8", errors="replace"))
            invocation.update(pc.usage(parsed))
            invocation.update({"subagents": pc.subagent_count(parsed), "init": pc.init_summary(parsed),
                               "failure": pc.failure(parsed, invocation)})
            invocations.append(invocation)
            if invocation["failure"]:
                break
        changes = collect_changes(workspace, before, run_dir / "artifacts")
        record = {"schema_version": 1, **{key: run[key] for key in ("phase", "suite", "arm", "case_id", "repeat", "key")},
                  "prompts": run["turns"], "workspace": built, "invocations": invocations,
                  "workspace_changes": changes, "metrics_label": "operator-reported"}
        (run_dir / "run.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if not args.keep_workspaces:
            shutil.rmtree(workspace, ignore_errors=True)
            shutil.rmtree(run_dir / "plugin", ignore_errors=True)
        status = invocations[-1]["failure"] or "ok"
        print(f"[{number}/{len(runs)}] {run['key']}: {status}", file=sys.stderr)
    return 0


# ---- dry-run, estimate, freeze --------------------------------------------------------

def summary_rows(spec: dict, plans: dict) -> list[dict]:
    rows = []
    cap = spec["budget"]["max_budget_usd_per_invocation"]
    for phase, runs in plans.items():
        groups = {}
        for run in runs:
            group = groups.setdefault((run["suite"], run["arm"]), {"runs": 0, "invocations": 0})
            group["runs"] += 1
            group["invocations"] += len(run["turns"])
        for (suite, arm), group in groups.items():
            rows.append({"phase": phase, "suite": suite, "arm": arm, **group, "cap_usd": group["invocations"] * cap})
    return rows


def estimate(spec: dict, plans: dict, calibration: Path) -> list[dict]:
    """Project spend from F1 run records: mean and max cost per invocation by (suite, arm)."""
    samples = {}
    for path in Path(calibration).rglob("run.json"):
        record = pc.load_json(path)
        for invocation in record.get("invocations", []):
            if isinstance(invocation.get("cost_usd"), (int, float)):
                samples.setdefault((record["suite"], record["arm"]), []).append(invocation["cost_usd"])
    rows = []
    for row in summary_rows(spec, {phase: runs for phase, runs in plans.items() if phase != "F1"}):
        values = samples.get((row["suite"], row["arm"]))
        mean = sum(values) / len(values) if values else None
        rows.append({**row, "samples": len(values or []),
                     "expected_usd": None if mean is None else round(mean * row["invocations"], 2),
                     "high_usd": None if not values else round(max(values) * row["invocations"], 2)})
    return rows


def freeze(root: Path, egm_src: str | None) -> dict:
    spec = pc.load_json(root / pc.SPEC_FILE)
    spec["inputs"] = pc.input_digests(root)
    if egm_src:
        import convert_scenarios
        if convert_scenarios.resolve_head(Path(egm_src)) != spec["upstream"]["commit"]:
            raise Refused("EGM checkout is not at the pinned commit")
        spec["upstream"]["plugin_tree_sha256"] = pc.tree_digest(Path(egm_src), [spec["upstream"]["plugin_subdir"]])
    if not spec["upstream"].get("plugin_tree_sha256"):
        raise Refused("pass --egm-src once so the plugin tree hash can be pinned")
    (root / pc.SPEC_FILE).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = pc.spec_digest(spec)
    (root / pc.SPEC_HASH_FILE).write_text(f"{digest}  {pc.SPEC_FILE}\n", encoding="utf-8")
    return {"spec_sha256": digest, "inputs": spec["inputs"],
            "plugin_tree_sha256": spec["upstream"]["plugin_tree_sha256"]}


def print_dry_run(spec: dict, plans: dict, args, root: Path) -> None:
    problems = pc.spec_problems(root)
    recorded = pc.recorded_spec_digest(root)
    print("EGM pilot dry-run: nothing is executed and no model is called.")
    print(f"spec.sha256 {recorded or 'missing'} ({'intact' if not problems else 'CHANGED: ' + '; '.join(problems)})")
    print(f"model={spec['model'] or 'unset (fill at F1)'} effort={spec.get('effort') or 'host default'} "
          f"cap=${spec['budget']['max_budget_usd_per_invocation']:g} per invocation")
    print("approval token for --live: <phase>-<first 12 hex of spec.sha256>")
    print(f"\n{'phase':5} {'suite':9} {'arm':3} {'runs':>5} {'invocations':>11} {'cap total USD':>13}")
    totals = {}
    for row in summary_rows(spec, plans):
        print(f"{row['phase']:5} {row['suite']:9} {row['arm']:3} {row['runs']:>5} {row['invocations']:>11} {row['cap_usd']:>13.2f}")
        total = totals.setdefault(row["phase"], [0, 0, 0.0])
        total[0], total[1], total[2] = total[0] + row["runs"], total[1] + row["invocations"], total[2] + row["cap_usd"]
    for phase, (runs, invocations, cap) in totals.items():
        print(f"{phase}: {runs} runs, {invocations} invocations, hard spend ceiling ${cap:.2f}")
    if args.estimate_from:
        print("\nprojection from calibration runs (operator-reported cost per invocation):")
        for row in estimate(spec, plans, Path(args.estimate_from)):
            print(f"  {row['phase']} {row['suite']} {row['arm']}: n={row['samples']} "
                  f"expected=${row['expected_usd']} high=${row['high_usd']} ceiling=${row['cap_usd']:.2f}")
    placeholder = Path("<OUT>")
    shown = set()
    print("\ncommands (one example per phase/suite/arm; --show-all for every run):")
    for phase, runs in plans.items():
        for run in runs:
            group = (phase, run["suite"], run["arm"], len(run["turns"]) > 1)
            if not args.show_all and group in shown:
                continue
            shown.add(group)
            run_dir = placeholder / phase / "runs" / run["key"]
            print(f"# {phase} {run['key']}  (cwd {run_dir / 'workspace'})")
            for cmd in planned_commands(spec, run, args.claude, run_dir):
                print("  " + shlex.join(cmd))


def main(argv=None, root: Path | None = None) -> int:
    configure_stdio()
    root = Path(root or HERE)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="print the plan and commands (default)")
    mode.add_argument("--live", action="store_true", help="run claude -p (needs --i-have-approval)")
    mode.add_argument("--freeze", action="store_true", help="re-pin input hashes in spec.json and write spec.sha256")
    mode.add_argument("--verify", action="store_true", help="check spec.sha256 and pinned input hashes")
    parser.add_argument("--phase", choices=(*PHASES, "all"), default="all")
    parser.add_argument("--i-have-approval", metavar="TOKEN")
    parser.add_argument("--claude", default=DEFAULT_CLAUDE, help="Claude Code binary (default: %(default)s)")
    parser.add_argument("--egm-src", default=os.environ.get("OAW_EGM_SRC"), help="EGM checkout at the pinned commit")
    parser.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "oaw-egm-pilot"),
                        help="raw run directory, kept outside the repository (default: %(default)s)")
    parser.add_argument("--keep-workspaces", action="store_true")
    parser.add_argument("--show-all", action="store_true")
    parser.add_argument("--estimate-from", metavar="F1_DIR", help="project spend from calibration run records")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.freeze:
            print(json.dumps(freeze(root, args.egm_src), indent=2))
            return 0
        if args.verify:
            problems = pc.spec_problems(root)
            spec = pc.load_json(root / pc.SPEC_FILE)
            if args.egm_src:
                tree = pc.tree_digest(Path(args.egm_src), [spec["upstream"]["plugin_subdir"]])
                if tree != spec["upstream"]["plugin_tree_sha256"]:
                    problems.append("EGM plugin tree differs from upstream.plugin_tree_sha256")
            print(json.dumps({"intact": not problems, "problems": problems}, indent=2))
            return 0 if not problems else 1
        spec, scenarios = load(root)
        if args.live:
            checked = guard_live(root, spec, args)
            return execute(root, spec, plan(spec, scenarios, args.phase), args, checked)
        phases = PHASES if args.phase == "all" else (args.phase,)
        plans = {phase: plan(spec, scenarios, phase) for phase in phases}
        if args.json:
            print(json.dumps({"dry_run": True, "spec_sha256": pc.recorded_spec_digest(root),
                              "summary": summary_rows(spec, plans),
                              "runs": [{**run, "commands": planned_commands(spec, run, args.claude, Path("<OUT>") / phase / "runs" / run["key"])}
                                       for phase, runs in plans.items() for run in runs]}, indent=2, ensure_ascii=False))
        else:
            print_dry_run(spec, plans, args, root)
        return 0
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
