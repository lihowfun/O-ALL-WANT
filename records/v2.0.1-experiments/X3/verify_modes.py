"""Zero-token check: each X3 scenario's expected mode under OAW 2.0.0 and 2.0.1.

Before editing: `suggest --paths <planned files>`. After editing: a reference solution applied to a copy of
the arm repo, then `suggest` on the working tree.
Usage: python3 verify_modes.py <arms dir> <scratch dir>
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ARMS, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])

PLANNED = {
    "L1": ["ledger/money.py"],
    "L2": ["ledger/text.py", "tests/test_text.py"],
    "S1": ["ledger/db.py", "ledger/accounts.py", "ledger/store.py", "ledger/budgets.py", "ledger/recurring.py",
           "ledger/importer.py", "ledger/exporter.py", "ledger/reports.py", "ledger/cli.py", "tests/helpers.py",
           "tests/test_db.py", "README.md"],
    "S2": ["ledger/reports.py", "ledger/reports/__init__.py", "ledger/reports/monthly.py",
           "ledger/reports/balances.py", "ledger/reports/budgets.py", "ledger/reports/payees.py",
           "ledger/reports/weekdays.py", "ledger/reports/render.py"],
    "D1": [".github/workflows/tests.yml"],
    "D2": ["migrations/0002_add_category.sql", "ledger/store.py", "tests/test_store.py"],
}


def sub(path, old, new, count=1):
    text = path.read_text()
    assert old in text, (path, old)
    path.write_text(text.replace(old, new, count))


def solve(scenario, root):
    if scenario == "L1":
        sub(root / "ledger/money.py", "recieve", "receive")
    elif scenario == "L2":
        sub(root / "ledger/text.py", 'return re.sub(r"[^a-z0-9]+", "-", value.lower())',
            'return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")')
        sub(root / "tests/test_text.py", '        self.assertEqual(slugify("A&B  Co"), "a-b-co")\n',
            '        self.assertEqual(slugify("A&B  Co"), "a-b-co")\n'
            '        self.assertEqual(slugify(" Hello, World! "), "hello-world")\n')
    elif scenario == "S1":
        for path in PLANNED["S1"]:
            p = root / path
            p.write_text(p.read_text().replace("get_conn", "open_connection"))
    elif scenario == "S2":
        text = (root / "ledger/reports.py").read_text()
        parts = re.split(r"\n# -+ (\w+)\n", text)
        head, sections = parts[0], dict(zip(parts[1::2], parts[2::2]))
        pkg = root / "ledger/reports"
        pkg.mkdir()
        names = {"monthly totals": "monthly"}
        exported = []
        for name, body in sections.items():
            module = {"monthly": "monthly", "balances": "balances", "budgets": "budgets", "payees": "payees",
                      "weekdays": "weekdays", "rendering": "render"}[name]
            imports = ("import csv\nimport io\n" if module == "render" else
                       "from collections import defaultdict\n\nfrom ..db import get_conn\nfrom ..money import format_money\n"
                       "from ..text import truncate\nfrom .render import render_csv, render_table\n")
            (pkg / f"{module}.py").write_text(f'"""Reports: {name}."""\n{imports}\n{body}')
            exported += [(module, fn) for fn in re.findall(r"^def (\w+)", body, re.M)]
        init = '"""Plain-text and CSV reports over the ledger."""\n' + "".join(
            f"from .{m} import {fn}\n" for m, fn in exported)
        (pkg / "__init__.py").write_text(init)
        (root / "ledger/reports.py").unlink()
        del names
    elif scenario == "D1":
        wf = root / ".github/workflows/tests.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text("name: tests\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
                      "    strategy:\n      matrix:\n        python: ['3.10', '3.12']\n    steps:\n"
                      "      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n"
                      "        with:\n          python-version: ${{ matrix.python }}\n"
                      "      - run: python -m unittest discover -s tests -t .\n")
    elif scenario == "D2":
        (root / "migrations/0002_add_category.sql").write_text(
            "ALTER TABLE transactions ADD COLUMN category TEXT NOT NULL DEFAULT '';\n")
        sub(root / "ledger/store.py", 'payee="", memo="", conn=None', 'payee="", memo="", conn=None, category=""')
        sub(root / "ledger/store.py", "(account_id, day, amount_cents, payee, memo) VALUES (?, ?, ?, ?, ?)",
            "(account_id, day, amount_cents, payee, memo, category) VALUES (?, ?, ?, ?, ?, ?)")
        sub(root / "ledger/store.py", "(account_id, day, amount_cents, payee, memo),",
            "(account_id, day, amount_cents, payee, memo, category),")
        sub(root / "ledger/store.py", "amount_cents, payee, memo FROM", "amount_cents, payee, memo, category FROM")
        sub(root / "tests/test_db.py", '["0001_init.sql"]', '["0001_init.sql", "0002_add_category.sql"]')


def mode(root, *args):
    out = subprocess.run(["/usr/bin/python3", "scripts/oaw_mode.py", "suggest", *args, "--json"], cwd=root,
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    return data["mode"], [t["rule"] for t in data.get("triggers", [])], data["code_files"], data["code_lines"]


def main():
    rows = []
    for arm in ("0", "A"):
        for scenario, planned in PLANNED.items():
            before = mode(ARMS / arm, "--paths", *planned)
            work = SCRATCH / f"verify-{arm}-{scenario}"
            shutil.rmtree(work, ignore_errors=True)
            shutil.copytree(ARMS / arm, work, symlinks=True)
            solve(scenario, work)
            tests = subprocess.run(["/usr/bin/python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                                   cwd=work, capture_output=True, text=True)
            after = mode(work)
            rows.append({"arm": arm, "scenario": scenario, "before": before, "after": after,
                         "tests_ok": tests.returncode == 0})
            shutil.rmtree(work)
            print(rows[-1])
    return rows


if __name__ == "__main__":
    main()
