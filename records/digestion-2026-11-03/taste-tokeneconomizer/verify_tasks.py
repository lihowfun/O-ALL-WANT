"""Zero-token check of the designer's tasks before they are frozen.

For each task, in a separate copy of the corpus at the base commit: the hidden test must fail at the base
commit, the reference patch must apply with `git apply`, the hidden test must pass with it, and the whole
existing suite must still pass with it. A task that fails any check is dropped, never edited; the frozen
set is the first N valid tasks in the designer's order.

    python3 verify_tasks.py <tasks.json> <copy dir> <base commit> <out.json>
"""
import json
import os
import subprocess
import sys


def sh(argv, cwd, stdin=None, timeout=600):
    done = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=timeout,
                          env={"HOME": os.environ["HOME"], "LANG": "C.UTF-8", "PATH": "/usr/bin:/bin"})
    return done.returncode, done.stdout + done.stderr


def reset(copy, base):
    sh(["git", "reset", "-q", "--hard", base], copy)
    sh(["git", "clean", "-qfdx", "-e", ".venv"], copy)


def main():
    tasks_path, copy, base, out_path = sys.argv[1:5]
    tasks = json.load(open(tasks_path, encoding="utf-8"))["tasks"]
    python = os.path.join(copy, ".venv", "bin", "python")
    pytest = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-header", "-rf"]
    reset(copy, base)
    code, text = sh(pytest + ["tests"], copy)
    report = {"base": base, "base_suite_exit": code, "base_suite_tail": text.strip().splitlines()[-1][:200], "tasks": []}
    for task in tasks:
        reset(copy, base)
        hidden = os.path.join("tests", f"test_hidden_{task['id']}.py")
        with open(os.path.join(copy, hidden), "w", encoding="utf-8") as handle:
            handle.write(task["hidden_test"])
        fails_at_base = sh(pytest + [hidden], copy)[0] != 0
        os.remove(os.path.join(copy, hidden))
        patch = task["reference_patch"] if task["reference_patch"].endswith("\n") else task["reference_patch"] + "\n"
        applies = sh(["git", "apply", "--check", "-"], copy, stdin=patch)[0] == 0
        passes = suite_ok = False
        suite_tail = ""
        if applies:
            sh(["git", "apply", "-"], copy, stdin=patch)
            touches_tests = any(line.startswith(("+++ b/tests", "--- a/tests")) for line in patch.splitlines())
            with open(os.path.join(copy, hidden), "w", encoding="utf-8") as handle:
                handle.write(task["hidden_test"])
            passes = sh(pytest + [hidden], copy)[0] == 0
            code, text = sh(pytest + ["tests"], copy)
            suite_ok = code == 0 and not touches_tests
            suite_tail = text.strip().splitlines()[-1][:200]
        valid = fails_at_base and applies and passes and suite_ok
        report["tasks"].append({"id": task["id"], "fails_at_base": fails_at_base, "patch_applies": applies,
                                "passes_with_reference": passes, "suite_ok_with_reference": suite_ok,
                                "suite_tail": suite_tail, "valid": valid})
        print(task["id"], "VALID" if valid else "DROP", report["tasks"][-1], flush=True)
    reset(copy, base)
    json.dump(report, open(out_path, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
