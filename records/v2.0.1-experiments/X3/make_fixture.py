"""X3 fixture: a small personal-ledger Python project (stdlib only, unittest).

Usage: python3 make_fixture.py <empty target dir>
Writes the files only; the caller runs git init and commits.
"""
import sys
from pathlib import Path

FILES = {}

FILES["README.md"] = """# ledger

A small personal-finance ledger: accounts, transactions, monthly budgets, CSV
import/export and plain-text reports, stored in SQLite.

## Layout

- `ledger/db.py`: the SQLite connection (`get_conn`) and the migration runner
- `migrations/`: SQL migrations, applied in file-name order
- `ledger/accounts.py`, `ledger/store.py`, `ledger/budgets.py`, `ledger/recurring.py`: data access
- `ledger/importer.py`, `ledger/exporter.py`: CSV in and out
- `ledger/reports.py`: monthly totals, balances, budget and payee reports
- `ledger/cli.py`: the `python3 -m ledger.cli` command line

## Tests

    python3 -m unittest discover -s tests -t .
"""

FILES[".gitignore"] = "__pycache__/\n*.pyc\n*.sqlite\n"

FILES["migrations/0001_init.sql"] = """CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    opened TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    day TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    payee TEXT NOT NULL DEFAULT '',
    memo TEXT NOT NULL DEFAULT ''
);

CREATE TABLE budgets (
    month TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    limit_cents INTEGER NOT NULL,
    PRIMARY KEY (month, account_id)
);

CREATE TABLE recurring (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    day_of_month INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL,
    payee TEXT NOT NULL
);
"""

FILES["ledger/__init__.py"] = '"""Personal ledger."""\n\n__version__ = "0.4.0"\n'

FILES["ledger/db.py"] = '''"""SQLite connection and schema migrations."""
import sqlite3
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


def get_conn(path=":memory:"):
    """Open a connection (rows behave like dicts) with every migration applied."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn


def apply_migrations(conn):
    """Run each migrations/*.sql file once, in file-name order."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (name TEXT PRIMARY KEY)")
    done = {row[0] for row in conn.execute("SELECT name FROM schema_version")}
    for sql in sorted(MIGRATIONS.glob("*.sql")):
        if sql.name not in done:
            conn.executescript(sql.read_text())
            conn.execute("INSERT INTO schema_version (name) VALUES (?)", (sql.name,))
    conn.commit()
'''

FILES["ledger/money.py"] = '''"""Money parsing and formatting. Amounts are stored as integer cents."""


def parse_amount(text):
    """Parse a user-entered amount like "1,234.50" or "-$12" and return it in cents.

    Amounts we recieve from bank CSV files may carry a currency sign, thousands
    separators, or a trailing minus ("12.00-").
    """
    cleaned = text.strip().replace(",", "").replace("$", "")
    negative = cleaned.startswith("-") or cleaned.endswith("-")
    cleaned = cleaned.strip("-")
    if not cleaned:
        raise ValueError(f"not an amount: {text!r}")
    whole, _, frac = cleaned.partition(".")
    cents = int(whole or "0") * 100 + int((frac + "00")[:2])
    return -cents if negative else cents


def format_money(cents):
    """Format cents as "-1,234.50"."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole:,}.{frac:02d}"
'''

FILES["ledger/text.py"] = '''"""Small text helpers."""
import re


def slugify(value):
    """Lower-case and replace each run of non-alphanumeric characters with one hyphen."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower())


def truncate(value, width):
    """Shorten value to width characters, ending with an ellipsis when cut."""
    if len(value) <= width:
        return value
    return value[: max(width - 1, 0)] + "\\u2026"
'''

FILES["ledger/accounts.py"] = '''"""Accounts."""
from .db import get_conn


def create_account(name, conn=None):
    conn = conn or get_conn()
    cur = conn.execute("INSERT INTO accounts (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


def list_accounts(conn=None):
    conn = conn or get_conn()
    return [dict(row) for row in conn.execute("SELECT id, name, opened FROM accounts ORDER BY name")]


def find_account(name, conn=None):
    conn = conn or get_conn()
    row = conn.execute("SELECT id, name, opened FROM accounts WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None
'''

FILES["ledger/store.py"] = '''"""Transactions."""
from .db import get_conn


def add_transaction(account_id, day, amount_cents, payee="", memo="", conn=None):
    conn = conn or get_conn()
    cur = conn.execute(
        "INSERT INTO transactions (account_id, day, amount_cents, payee, memo) VALUES (?, ?, ?, ?, ?)",
        (account_id, day, amount_cents, payee, memo),
    )
    conn.commit()
    return cur.lastrowid


def list_transactions(account_id, conn=None, month=None):
    conn = conn or get_conn()
    sql = "SELECT id, account_id, day, amount_cents, payee, memo FROM transactions WHERE account_id = ?"
    args = [account_id]
    if month:
        sql += " AND substr(day, 1, 7) = ?"
        args.append(month)
    return [dict(row) for row in conn.execute(sql + " ORDER BY day, id", args)]


def delete_transaction(transaction_id, conn=None):
    conn = conn or get_conn()
    conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
'''

FILES["ledger/budgets.py"] = '''"""Monthly spending limits per account."""
from .db import get_conn


def set_budget(month, account_id, limit_cents, conn=None):
    conn = conn or get_conn()
    conn.execute(
        "INSERT INTO budgets (month, account_id, limit_cents) VALUES (?, ?, ?) "
        "ON CONFLICT (month, account_id) DO UPDATE SET limit_cents = excluded.limit_cents",
        (month, account_id, limit_cents),
    )
    conn.commit()


def get_budget(month, account_id, conn=None):
    conn = conn or get_conn()
    row = conn.execute("SELECT limit_cents FROM budgets WHERE month = ? AND account_id = ?",
                       (month, account_id)).fetchone()
    return row["limit_cents"] if row else None
'''

FILES["ledger/recurring.py"] = '''"""Recurring transactions (rent, subscriptions)."""
from .db import get_conn
from .store import add_transaction


def add_recurring(account_id, day_of_month, amount_cents, payee, conn=None):
    conn = conn or get_conn()
    cur = conn.execute(
        "INSERT INTO recurring (account_id, day_of_month, amount_cents, payee) VALUES (?, ?, ?, ?)",
        (account_id, day_of_month, amount_cents, payee),
    )
    conn.commit()
    return cur.lastrowid


def post_due(day, conn=None):
    """Add the recurring transactions due on day (YYYY-MM-DD); return how many were added."""
    conn = conn or get_conn()
    due = conn.execute("SELECT * FROM recurring WHERE day_of_month = ?", (int(day[8:10]),)).fetchall()
    for row in due:
        add_transaction(row["account_id"], day, row["amount_cents"], row["payee"], "recurring", conn=conn)
    return len(due)
'''

FILES["ledger/importer.py"] = '''"""Import bank CSV exports (columns: date, payee, amount[, memo])."""
import csv

from .db import get_conn
from .money import parse_amount
from .store import add_transaction


def import_csv(path, account_id, conn=None):
    conn = conn or get_conn()
    count = 0
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            add_transaction(account_id, row["date"], parse_amount(row["amount"]),
                            row.get("payee", ""), row.get("memo", ""), conn=conn)
            count += 1
    return count
'''

FILES["ledger/exporter.py"] = '''"""Export transactions to CSV."""
import csv

from .db import get_conn
from .money import format_money
from .store import list_transactions


def export_csv(account_id, path, conn=None, month=None):
    conn = conn or get_conn()
    rows = list_transactions(account_id, conn=conn, month=month)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "payee", "amount", "memo"])
        for row in rows:
            writer.writerow([row["day"], row["payee"], format_money(row["amount_cents"]), row["memo"]])
    return len(rows)
'''

FILES["ledger/reports.py"] = '''"""Plain-text and CSV reports over the ledger."""
import csv
import io
from collections import defaultdict

from .db import get_conn
from .money import format_money
from .text import truncate


# ---------------------------------------------------------------- monthly totals

def monthly_totals(account_id, conn=None):
    """Income, spending and net per month for one account, oldest month first."""
    conn = conn or get_conn()
    rows = conn.execute(
        "SELECT substr(day, 1, 7) AS month, amount_cents FROM transactions WHERE account_id = ?",
        (account_id,),
    ).fetchall()
    totals = defaultdict(lambda: {"income": 0, "spending": 0})
    for row in rows:
        bucket = totals[row["month"]]
        if row["amount_cents"] >= 0:
            bucket["income"] += row["amount_cents"]
        else:
            bucket["spending"] += -row["amount_cents"]
    result = []
    for month in sorted(totals):
        income, spending = totals[month]["income"], totals[month]["spending"]
        result.append({"month": month, "income": income, "spending": spending, "net": income - spending})
    return result


def monthly_table(account_id, conn=None):
    rows = monthly_totals(account_id, conn=conn)
    header = ["month", "income", "spending", "net"]
    body = [[r["month"], format_money(r["income"]), format_money(r["spending"]), format_money(r["net"])]
            for r in rows]
    return render_table(header, body, align="lrrr")


def yearly_summary(account_id, conn=None):
    """Monthly totals rolled up per year, with the average monthly net."""
    years = {}
    for row in monthly_totals(account_id, conn=conn):
        year = years.setdefault(row["month"][:4], {"income": 0, "spending": 0, "months": 0})
        year["income"] += row["income"]
        year["spending"] += row["spending"]
        year["months"] += 1
    result = []
    for year in sorted(years):
        y = years[year]
        net = y["income"] - y["spending"]
        result.append({"year": year, "income": y["income"], "spending": y["spending"], "net": net,
                       "avg_monthly_net": net // y["months"]})
    return result


def yearly_table(account_id, conn=None):
    rows = yearly_summary(account_id, conn=conn)
    body = [[r["year"], format_money(r["income"]), format_money(r["spending"]), format_money(r["net"]),
             format_money(r["avg_monthly_net"])] for r in rows]
    return render_table(["year", "income", "spending", "net", "avg/month"], body, align="lrrrr")


# ---------------------------------------------------------------- balances

def account_balances(conn=None, as_of=None):
    """Balance of every account, optionally only counting transactions up to as_of (YYYY-MM-DD)."""
    conn = conn or get_conn()
    sql = ("SELECT a.id, a.name, COALESCE(SUM(t.amount_cents), 0) AS balance "
           "FROM accounts a LEFT JOIN transactions t ON t.account_id = a.id")
    args = []
    if as_of:
        sql += " AND t.day <= ?"
        args.append(as_of)
    sql += " GROUP BY a.id ORDER BY a.name"
    return [dict(row) for row in conn.execute(sql, args)]


def balances_table(conn=None, as_of=None):
    rows = account_balances(conn=conn, as_of=as_of)
    body = [[r["name"], format_money(r["balance"])] for r in rows]
    total = sum(r["balance"] for r in rows)
    body.append(["total", format_money(total)])
    return render_table(["account", "balance"], body, align="lr")


# ---------------------------------------------------------------- budgets

def budget_report(month, conn=None):
    """Spending against each account's budget for month (YYYY-MM)."""
    conn = conn or get_conn()
    rows = conn.execute(
        "SELECT a.name, b.limit_cents, "
        "COALESCE((SELECT -SUM(t.amount_cents) FROM transactions t "
        "          WHERE t.account_id = a.id AND substr(t.day, 1, 7) = ? AND t.amount_cents < 0), 0) AS spent "
        "FROM budgets b JOIN accounts a ON a.id = b.account_id WHERE b.month = ? ORDER BY a.name",
        (month, month),
    ).fetchall()
    report = []
    for row in rows:
        left = row["limit_cents"] - row["spent"]
        report.append({
            "account": row["name"],
            "limit": row["limit_cents"],
            "spent": row["spent"],
            "left": left,
            "over": left < 0,
            "used_pct": round(100 * row["spent"] / row["limit_cents"]) if row["limit_cents"] else None,
        })
    return report


def budget_table(month, conn=None):
    rows = budget_report(month, conn=conn)
    body = []
    for r in rows:
        flag = "OVER" if r["over"] else ""
        pct = "-" if r["used_pct"] is None else f"{r['used_pct']}%"
        body.append([r["account"], format_money(r["limit"]), format_money(r["spent"]),
                     format_money(r["left"]), pct, flag])
    return render_table(["account", "limit", "spent", "left", "used", ""], body, align="lrrrrl")


# ---------------------------------------------------------------- payees

def top_payees(account_id, conn=None, month=None, limit=5):
    """The payees with the most spending, largest first."""
    conn = conn or get_conn()
    sql = ("SELECT payee, -SUM(amount_cents) AS spent, COUNT(*) AS n FROM transactions "
           "WHERE account_id = ? AND amount_cents < 0")
    args = [account_id]
    if month:
        sql += " AND substr(day, 1, 7) = ?"
        args.append(month)
    sql += " GROUP BY payee ORDER BY spent DESC, payee LIMIT ?"
    args.append(limit)
    return [dict(row) for row in conn.execute(sql, args)]


def payees_table(account_id, conn=None, month=None, limit=5):
    rows = top_payees(account_id, conn=conn, month=month, limit=limit)
    body = [[truncate(r["payee"] or "(none)", 24), format_money(r["spent"]), str(r["n"])] for r in rows]
    return render_table(["payee", "spent", "count"], body, align="lrr")


# ---------------------------------------------------------------- weekdays

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def spending_by_weekday(account_id, conn=None, month=None):
    """Total spending per weekday (Mon..Sun) for one account."""
    conn = conn or get_conn()
    sql = ("SELECT CAST(strftime('%w', day) AS INTEGER) AS dow, -SUM(amount_cents) AS spent FROM transactions "
           "WHERE account_id = ? AND amount_cents < 0")
    args = [account_id]
    if month:
        sql += " AND substr(day, 1, 7) = ?"
        args.append(month)
    sql += " GROUP BY dow"
    spent = {(row["dow"] - 1) % 7: row["spent"] for row in conn.execute(sql, args)}
    return [{"weekday": name, "spent": spent.get(i, 0)} for i, name in enumerate(WEEKDAYS)]


def weekday_table(account_id, conn=None, month=None):
    rows = spending_by_weekday(account_id, conn=conn, month=month)
    peak = max((r["spent"] for r in rows), default=0)
    body = []
    for r in rows:
        bar = "#" * (round(20 * r["spent"] / peak) if peak else 0)
        body.append([r["weekday"], format_money(r["spent"]), bar])
    return render_table(["day", "spent", ""], body, align="lrl")


# ---------------------------------------------------------------- rendering

def render_table(header, body, align=None):
    """Render rows as a fixed-width text table; align is one l/r letter per column."""
    align = align or "l" * len(header)
    widths = [len(h) for h in header]
    for row in body:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def line(cells):
        out = []
        for i, cell in enumerate(cells):
            out.append(cell.rjust(widths[i]) if align[i] == "r" else cell.ljust(widths[i]))
        return "  ".join(out).rstrip()

    rule = "  ".join("-" * w for w in widths)
    return "\\n".join([line(header), rule] + [line(row) for row in body])


def render_csv(header, body):
    """Render rows as CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\\n")
    writer.writerow(header)
    writer.writerows(body)
    return buffer.getvalue()


def monthly_csv(account_id, conn=None):
    rows = monthly_totals(account_id, conn=conn)
    body = [[r["month"], r["income"], r["spending"], r["net"]] for r in rows]
    return render_csv(["month", "income_cents", "spending_cents", "net_cents"], body)
'''

FILES["ledger/cli.py"] = '''"""Command line: python3 -m ledger.cli --db FILE <command> ..."""
import argparse

from .accounts import create_account, find_account, list_accounts
from .db import get_conn
from .importer import import_csv
from .reports import balances_table, budget_table, monthly_table


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ledger")
    parser.add_argument("--db", default="ledger.sqlite")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("accounts")
    add = sub.add_parser("add-account")
    add.add_argument("name")
    imp = sub.add_parser("import")
    imp.add_argument("account")
    imp.add_argument("csv")
    sub.add_parser("balances")
    month = sub.add_parser("monthly")
    month.add_argument("account")
    budget = sub.add_parser("budget")
    budget.add_argument("month")
    args = parser.parse_args(argv)

    conn = get_conn(args.db)
    if args.command == "accounts":
        for account in list_accounts(conn=conn):
            print(account["name"])
    elif args.command == "add-account":
        create_account(args.name, conn=conn)
    elif args.command == "import":
        account = find_account(args.account, conn=conn)
        print(import_csv(args.csv, account["id"], conn=conn), "transactions imported")
    elif args.command == "balances":
        print(balances_table(conn=conn))
    elif args.command == "monthly":
        print(monthly_table(find_account(args.account, conn=conn)["id"], conn=conn))
    elif args.command == "budget":
        print(budget_table(args.month, conn=conn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

FILES["tests/__init__.py"] = ""

FILES["tests/helpers.py"] = '''"""Shared test fixtures."""
from ledger.accounts import create_account
from ledger.db import get_conn
from ledger.store import add_transaction


def sample_ledger():
    """An in-memory ledger with two accounts and a few transactions."""
    conn = get_conn()
    checking = create_account("checking", conn=conn)
    savings = create_account("savings", conn=conn)
    add_transaction(checking, "2026-01-03", 250000, "Employer", "salary", conn=conn)
    add_transaction(checking, "2026-01-05", -120000, "Landlord", "rent", conn=conn)
    add_transaction(checking, "2026-01-09", -4550, "Grocer", conn=conn)
    add_transaction(checking, "2026-02-03", 250000, "Employer", "salary", conn=conn)
    add_transaction(checking, "2026-02-11", -6025, "Grocer", conn=conn)
    add_transaction(savings, "2026-01-31", 50000, "Transfer", conn=conn)
    return conn, checking, savings
'''

FILES["tests/test_db.py"] = '''import unittest

from ledger.db import apply_migrations, get_conn


class DbTest(unittest.TestCase):
    def test_migrations_applied_once(self):
        conn = get_conn()
        apply_migrations(conn)
        names = [row[0] for row in conn.execute("SELECT name FROM schema_version")]
        self.assertEqual(names, ["0001_init.sql"])

    def test_tables_exist(self):
        conn = get_conn()
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertTrue({"accounts", "transactions", "budgets", "recurring"} <= tables)
'''

FILES["tests/test_money.py"] = '''import unittest

from ledger.money import format_money, parse_amount


class MoneyTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_amount("1,234.50"), 123450)
        self.assertEqual(parse_amount("-$12"), -1200)
        self.assertEqual(parse_amount("12.00-"), -1200)
        self.assertEqual(parse_amount(".5"), 50)

    def test_parse_rejects_empty(self):
        with self.assertRaises(ValueError):
            parse_amount(" - ")

    def test_format(self):
        self.assertEqual(format_money(123450), "1,234.50")
        self.assertEqual(format_money(-5), "-0.05")
'''

FILES["tests/test_text.py"] = '''import unittest

from ledger.text import slugify, truncate


class TextTest(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Grocery Store"), "grocery-store")
        self.assertEqual(slugify("A&B  Co"), "a-b-co")

    def test_truncate(self):
        self.assertEqual(truncate("abc", 5), "abc")
        self.assertEqual(truncate("abcdef", 4), "abc\\u2026")
'''

FILES["tests/test_store.py"] = '''import unittest

from ledger.budgets import get_budget, set_budget
from ledger.recurring import add_recurring, post_due
from ledger.store import delete_transaction, list_transactions
from tests.helpers import sample_ledger


class StoreTest(unittest.TestCase):
    def test_list_by_month(self):
        conn, checking, _ = sample_ledger()
        self.assertEqual(len(list_transactions(checking, conn=conn)), 5)
        self.assertEqual(len(list_transactions(checking, conn=conn, month="2026-02")), 2)

    def test_delete(self):
        conn, checking, _ = sample_ledger()
        first = list_transactions(checking, conn=conn)[0]["id"]
        delete_transaction(first, conn=conn)
        self.assertEqual(len(list_transactions(checking, conn=conn)), 4)

    def test_budget_upsert(self):
        conn, checking, _ = sample_ledger()
        set_budget("2026-01", checking, 100000, conn=conn)
        set_budget("2026-01", checking, 150000, conn=conn)
        self.assertEqual(get_budget("2026-01", checking, conn=conn), 150000)

    def test_recurring(self):
        conn, checking, _ = sample_ledger()
        add_recurring(checking, 15, -1599, "Streaming", conn=conn)
        self.assertEqual(post_due("2026-03-15", conn=conn), 1)
        self.assertEqual(post_due("2026-03-16", conn=conn), 0)
'''

FILES["tests/test_reports.py"] = '''import os
import tempfile
import unittest

from ledger.budgets import set_budget
from ledger.exporter import export_csv
from ledger.importer import import_csv
from ledger.reports import (account_balances, balances_table, budget_report, monthly_csv, monthly_totals,
                            spending_by_weekday, top_payees, weekday_table, yearly_summary)
from ledger.store import list_transactions
from tests.helpers import sample_ledger


class ReportsTest(unittest.TestCase):
    def test_monthly_totals(self):
        conn, checking, _ = sample_ledger()
        jan = monthly_totals(checking, conn=conn)[0]
        self.assertEqual((jan["month"], jan["income"], jan["spending"], jan["net"]),
                         ("2026-01", 250000, 124550, 125450))

    def test_balances(self):
        conn, _, _ = sample_ledger()
        balances = {r["name"]: r["balance"] for r in account_balances(conn=conn)}
        self.assertEqual(balances, {"checking": 369425, "savings": 50000})
        self.assertIn("total", balances_table(conn=conn))

    def test_budget_report(self):
        conn, checking, _ = sample_ledger()
        set_budget("2026-01", checking, 100000, conn=conn)
        (row,) = budget_report("2026-01", conn=conn)
        self.assertTrue(row["over"])
        self.assertEqual(row["used_pct"], 125)

    def test_top_payees(self):
        conn, checking, _ = sample_ledger()
        self.assertEqual(top_payees(checking, conn=conn)[0]["payee"], "Landlord")

    def test_yearly_summary(self):
        conn, checking, _ = sample_ledger()
        (year,) = yearly_summary(checking, conn=conn)
        self.assertEqual((year["year"], year["net"], year["avg_monthly_net"]), ("2026", 369425, 184712))

    def test_spending_by_weekday(self):
        conn, checking, _ = sample_ledger()
        spent = {r["weekday"]: r["spent"] for r in spending_by_weekday(checking, conn=conn)}
        self.assertEqual(spent["Mon"], 120000)
        self.assertIn("#", weekday_table(checking, conn=conn))

    def test_monthly_csv(self):
        conn, checking, _ = sample_ledger()
        self.assertTrue(monthly_csv(checking, conn=conn).startswith("month,income_cents"))

    def test_csv_round_trip(self):
        conn, checking, savings = sample_ledger()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.csv")
            self.assertEqual(export_csv(checking, path, conn=conn), 5)
            self.assertEqual(import_csv(path, savings, conn=conn), 5)
        self.assertEqual(len(list_transactions(savings, conn=conn)), 6)
'''


def main():
    target = Path(sys.argv[1])
    for name, text in FILES.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
