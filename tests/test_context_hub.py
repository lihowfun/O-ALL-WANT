"""Behavioral regressions for the portable Context Hub CLI (stdlib only)."""

import contextlib
from datetime import datetime, timedelta, timezone
import errno
import importlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
hub = importlib.import_module("context_hub")
common = importlib.import_module("oaw_common")


def _memory_worker(base, start, number):
    """Real independent processes, each updating the same memory three times."""
    hub.BASE_DIR = base
    hub.MEMORY_FILE = str(Path(base) / ".agents/memory.md")
    start.wait(timeout=20)
    with contextlib.redirect_stdout(io.StringIO()):
        for entry in range(3):
            hub.memory_add(f"[NOTE] writer_{number}_entry_{entry}")


def _mixed_memory_worker(base, start, number):
    hub.BASE_DIR = base
    hub.MEMORY_FILE = str(Path(base) / ".agents/memory.md")
    original = hub.locked_update

    def route(path, *args, **kwargs):
        if number % 2 and Path(path) == Path(hub.MEMORY_FILE):
            raise PermissionError(errno.EACCES, "fixture primary lock denied")
        return original(path, *args, **kwargs)

    hub.locked_update = route
    start.wait(timeout=20)
    with contextlib.redirect_stdout(io.StringIO()):
        for entry in range(3):
            hub.memory_add(f"[NOTE] mixed-writer-{number}-entry-{entry}")


class ContextHubTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".context-fixture-", dir=Path(__file__).parent)
        self.top = Path(self.temporary.name).resolve()
        self.base = self.top / "project"
        self.docs = self.base / "docs/knowledge"
        self.docs.mkdir(parents=True)
        self.memory = self.base / ".agents/memory.md"
        self.change = patch.multiple(hub, BASE_DIR=str(self.base), DOCS_DIR=str(self.docs),
                                     RAW_DIR=str(self.base / "docs/raw"), MEMORY_FILE=str(self.memory),
                                     AI_CONTEXT_FILE=str(self.base / "AI_CONTEXT.md"))
        self.change.start()
        self.addCleanup(self.change.stop)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.assertEqual(os.path.commonpath([str(self.top), str(Path(__file__).parent.resolve())]), str(Path(__file__).parent.resolve()))
        self.temporary.cleanup()

    def quiet(self, function, *args, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = function(*args, **kwargs)
        return result, output.getvalue()

    def cli(self, *args):
        environment = dict(os.environ, AGENT_MEMORY_BASE_DIR=str(self.base),
                           PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, str(SCRIPTS / "context_hub.py"), *args],
                              env=environment, capture_output=True, text=True, encoding="utf-8")

    def test_get_and_annotate_reject_traversal_and_missing_topics(self):
        victim = self.top / "victim.md"
        victim.write_text("outside sentinel", encoding="utf-8")
        for command in ("get", "annotate"):
            for topic in ("../../../victim", "Missing"):
                args = [command, topic] + (["note"] if command == "annotate" else [])
                completed = self.cli(*args)
                self.assertNotEqual(completed.returncode, 0)
                self.assertNotIn("Traceback", completed.stderr)
        self.assertEqual(victim.read_text(encoding="utf-8"), "outside sentinel")

    def test_symlink_escape_is_rejected(self):
        outside = self.top / "outside.md"
        outside.write_text("outside sentinel", encoding="utf-8")
        try:
            (self.docs / "Linked.md").symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaises(ValueError):
            hub.get("Linked")
        with self.assertRaises(ValueError):
            hub.annotate("Linked", "note")
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside sentinel")

    def test_reserved_and_portable_topic_ids(self):
        for topic in ("CON", "Lpt1", "../Other", "Other.md", "a/b", "", "/absolute"):
            with self.subTest(topic=topic), self.assertRaises(ValueError):
                common.validate_topic_id(topic)
        self.assertEqual(common.validate_topic_id("專案_2026-決策"), "專案_2026-決策")

    def test_multiprocessing_memory_entries_all_survive(self):
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n\n---\n" + ("baseline text\n" * 6000), encoding="utf-8")
        context = multiprocessing.get_context("spawn")
        start = context.Barrier(6)
        workers = [context.Process(target=_memory_worker, args=(str(self.base), start, number)) for number in range(6)]
        for worker in workers:
            worker.start()
        try:
            for worker in workers:
                worker.join(40)
                self.assertEqual(worker.exitcode, 0)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
        content = self.memory.read_text(encoding="utf-8")
        for number in range(6):
            for entry in range(3):
                self.assertEqual(content.count(f"writer_{number}_entry_{entry}"), 1)
        self.assertIn("baseline text", content)

    def test_failed_mutation_preserves_original_and_releases_lock(self):
        path = self.base / "state.txt"
        path.write_text("before", encoding="utf-8")

        def fail(_content):
            raise ValueError("expected mutation failure")

        with self.assertRaisesRegex(ValueError, "expected"):
            common.locked_update(path, fail, root=self.base)
        self.assertEqual(path.read_text(encoding="utf-8"), "before")
        common.locked_update(path, lambda text: text + " after", root=self.base)
        self.assertEqual(path.read_text(encoding="utf-8"), "before after")
        self.assertTrue((self.base / ".state.txt.oaw.lock").exists())

    def test_concurrent_readers_cannot_fail_locked_replace(self):
        path = self.base / "shared.md"
        path.write_text("", encoding="utf-8")
        stop = threading.Event()

        def read():
            # Windows refuses os.replace while any handle is open; hold one most of the time.
            while not stop.is_set():
                try:
                    with open(path, encoding="utf-8") as handle:
                        handle.read()
                        time.sleep(0.002)
                except OSError:
                    pass
                time.sleep(0.001)

        reader = threading.Thread(target=read)
        reader.start()
        try:
            for number in range(30):
                common.locked_update(path, lambda text: text + f"{number}\n", root=self.base)
        finally:
            stop.set()
            reader.join()
        self.assertEqual(path.read_text(encoding="utf-8").split(), [str(number) for number in range(30)])

    def test_locked_update_refuses_symlinked_target_escape(self):
        outside = self.top / "outside.md"
        outside.write_text("outside sentinel", encoding="utf-8")
        try:
            (self.base / "linked.md").symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaises(ValueError):
            common.locked_update(self.base / "linked.md", lambda _text: "changed", root=self.base)
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside sentinel")

    def test_annotation_migrates_legacy_notes_and_refuses_meta(self):
        page = self.docs / "Topic.md"
        page.write_text("# Topic\n\n## AI Annotations\n\nlegacy note\n", encoding="utf-8")
        self.quiet(hub.annotate, "Topic", "new note")
        content = page.read_text(encoding="utf-8")
        self.assertEqual(content.count(common.ANNOTATIONS_START), 1)
        self.assertIn("legacy note", common.extract_annotations(content))
        self.assertIn("new note", common.extract_annotations(content))
        (self.docs / "index.md").write_text("---\npage_type: meta\n---\n# Index\n", encoding="utf-8")
        completed = self.cli("annotate", "index", "note")
        self.assertNotEqual(completed.returncode, 0)

    def test_annotation_marker_examples_cannot_discard_prior_notes(self):
        original = "# Topic\n\n" + common.render_annotations("keep original verified note")
        note = "Marker syntax is `<!-- oaw:annotations:start -->`, keep explanation."
        added = common.append_annotation(original, note)
        extracted = common.extract_annotations(added)
        self.assertIn("keep original verified note", extracted)
        self.assertIn(note, extracted)
        fenced = "```html\n" + common.ANNOTATIONS_START + "\n" + common.ANNOTATIONS_END + "\n```"
        added = common.append_annotation(added, fenced)
        self.assertIn(fenced, common.extract_annotations(added))
        added = common.append_annotation(added, common.ANNOTATIONS_START + "\nstandalone example")
        self.assertIn("keep original verified note", common.extract_annotations(added))
        self.assertIn("standalone example", common.extract_annotations(added))
        added = common.append_annotation(added, "```text\nunfinished example")
        self.assertIn("unfinished example", common.extract_annotations(added))
        self.assertIn("keep original verified note", common.extract_annotations(added))

    def test_execution_lists_native_agent_and_claude_packages_without_validator(self):
        for location in (".agents", ".claude"):
            package = self.base / location / "skills/example/SKILL.md"
            package.parent.mkdir(parents=True)
            package.write_text("---\nname: example\ndescription: Example skill.\n---\nInstructions.\n", encoding="utf-8")
        _, output = self.quiet(hub.context_lane, "execution")
        self.assertIn(".agents/skills/example/SKILL.md", output)
        self.assertIn(".claude/skills/example/SKILL.md", output)

    def secret_fixtures(self):
        """One positive and one negative note per credential pattern, built at run time.

        No real-looking token literal sits in the repository, so secret scanners
        and push protection stay quiet; every value below is fake.
        """
        hexa, word = "0123456789abcdef" * 4, "Ab3" * 30
        return {
            # Only a password that is wholly a placeholder is exempt; user:pass is refused by design.
            "url_credentials": (["clone https://deploy:" + "Hunter2x" + "@git.example.com/repo.git",
                                 "redis://:" + "pw9" + "@cache:6379/0", "postgres://app:$" + "ecretPw1@db/prod",
                                 "mysql://root:{abc}" + "def@db", "see https://user:" + "pass@host"],
                                ["postgres://app:${DB_PASS}@db/prod", "https://user:<PASSWORD>@host",
                                 "https://user@host", "https://host:8080/a@b", "git@github.com:org/repo",
                                 "POSTGRES://app:$DB_PASS@db", "mysql://root:{db_password}@localhost",
                                 "mysql://root:{{db_password}}@localhost", "postgres://u:%s@db",
                                 "postgres://u:%(password)s@db", "postgres://u:****@db"]),
            "aws_access_key": (["key AKIA" + "ABCDEFGHIJKLMNOP", "AWS_ACCESS_KEY_ID=AS" + "IAABCDEFGHIJKLMNOP done"],
                               ["the AKIA prefix and AKIA1234 in prose", "blob x9AKIA" + "ABCDEFGHIJKLMNOP" + "q7/+==",
                                "AKIA" + "ABCDEFGHIJKLMNOPQ is 17 long"]),
            "aws_secret_key": (["aws_secret_access_key = " + word[:40], '"SecretAccessKey": "' + "A/b+" * 10 + '"'],
                               ["AWS_SECRET_ACCESS_KEY=" + word[:39], "AWS_SECRET_ACCESS_KEY=<AWS_SECRET>"]),
            "aws_session_token": (["AWS_SESSION_TOKEN=" + word * 2], ["aws_session_token = " + word[:40]]),
            "github_pat": (["token gh" + "p_" + "A" * 36, "權杖gh" + "o_" + "A" * 36, "github" + "_pat_" + "B" * 82],
                           ["gh" + "p_" + "A" * 10]),
            "openai_key": (["sk" + "-proj-" + word[:30], "sk" + "-svcacct-" + word[:30], "key sk" + "-" + word[:48]],
                           ["use sk-learn or sk-123 here", "the sk-learn-compatible-estimator-api wrapper",
                            "read sk-internationalization-guide and sk-internationalization"]),
            "anthropic_key": (["sk" + "-ant-api03-" + word[:30]], ["the sk-ant- prefix alone"]),
            "slack_token": (["xo" + "xb-" + "1234567890-abcdef"], ["xoxb-123"]),
            "slack_webhook": (["https://hooks.slack.com/services/T0000/B0000/" + word[:24]],
                              ["https://example.com/hooks.slack.com/services/T0000/B0000/" + word[:24]]),
            "discord_webhook": (["https://discord.com/api/webhooks/" + "1" * 18 + "/" + word[:68]],
                                ["https://discord.com/api/webhooks/" + "1" * 18 + "/short"]),
            "jwt": (["ey" + "JhbGciOiJIUzI1NiJ9.ey" + "JzdWIiOiIxIn0.sig_value"],
                    ["eyJhbGciOi has one part", "blob-ey" + "JhbGciOiJIUzI1NiJ9.ey" + "JzdWIiOiIxIn0.sig inside a run"]),
            "private_key_pem": (["-----BEGIN " + "OPENSSH PRIVATE" + " KEY-----"], ["-----BEGIN " + "PUBLIC" + " KEY-----"]),
            "stripe_key": (["sk" + "_live_" + word[:24], "wh" + "sec_" + word[:32]], ["sk_live_short"]),
            "google_api_key": (["AI" + "za" + "S" * 35], ["AIza" + "S" * 10]),
            "gitlab_token": (["gl" + "pat-" + word[:20]], ["glpat-short"]),
            "huggingface_token": (["h" + "f_" + word[:34]], ["hf_" + word[:10]]),
            "npm_token": (["np" + "m_" + word[:36]], ["npm_" + word[:35]]),
            "docker_pat": (["dckr" + "_pat_" + word[:27]], ["dckr_pat_" + word[:5]]),
            "sendgrid_key": (["S" + "G." + word[:22] + "." + word[:43]], ["SG." + word[:22] + "." + word[:10]]),
            "digitalocean_token": (["do" + "p_v1_" + hexa], ["dop_v1_" + "g" * 64]),
            "shopify_token": (["shp" + "at_" + hexa[:32]], ["shpat_" + "z" * 32]),
            "pypi_token": (["py" + "pi-AgE" + word[:60]], ["pypi-AgE" + word[:10]]),
        }

    def test_secret_patterns_compile_at_import(self):
        code = (f"import re, sys; sys.path.insert(0, {str(SCRIPTS)!r}); import oaw_common; "
                "assert all(p.flags & re.ASCII for _n, p in oaw_common.SECRET_PATTERNS); "
                "print(','.join(n for n, _p in oaw_common.SECRET_PATTERNS))")
        completed = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip().split(","), [name for name, _pattern in common.SECRET_PATTERNS])

    def test_each_secret_pattern_has_positive_and_negative_fixture(self):
        fixtures = self.secret_fixtures()
        self.assertEqual(sorted(fixtures), sorted(name for name, _pattern in common.SECRET_PATTERNS))
        for name, (positives, negatives) in fixtures.items():
            for text in positives:
                with self.subTest(name=name, case="positive"):
                    self.assertIn(name, common.find_secret_names(text))
                    refusal = common.evidence_write_refusal("note " + text)
                    self.assertIn(name, refusal)
                    self.assertNotIn(text, refusal)
            for text in negatives:
                with self.subTest(name=name, case="negative"):
                    self.assertNotIn(name, common.find_secret_names(text))
                    # The whole guard accepts it too, so no other pattern refuses a negative.
                    self.assertIsNone(common.evidence_write_refusal("note " + text), text)
        for text in ("postgres://app:${DB_PASS}@db", "https://user@host", "https://host:8080/a@b",
                     "git@github.com:org/repo", "set password=hunter2 and API_TOKEN=abcdef123456 in prose",
                     "pip install scikit-learn; sk-learn-compatible-estimator-api docs"):
            self.assertIsNone(common.evidence_write_refusal(text), text)

    def test_secret_scan_is_linear_on_long_notes(self):
        # A note is bounded only by the argv limit. These shapes made url_credentials and jwt
        # scan quadratically (minutes at this length); bounded starts finish in well under a second.
        length = 120_000
        shapes = ("a." * (length // 2), "eyJ-" * (length // 4), "sk-" * (length // 3),
                  "a://u:" + "x:" * (length // 2), "a://" + "b" * length, "xoxb-" + "a" * length + "_")
        started = time.perf_counter()
        for text in shapes:
            self.assertIsNone(common.evidence_write_refusal(text))
        self.assertLess(time.perf_counter() - started, 5.0)
        self.assertIsNotNone(common.evidence_write_refusal("a." * (length // 2) + " https://u:" + "pw9@h"))

    def test_secret_refusal_leaves_file_unchanged_and_never_prints_value(self):
        token = "gh" + "p_" + "Z" * 36
        page = self.docs / "Topic.md"
        page.write_text("# Topic\n\nbody\n", encoding="utf-8")
        page_bytes = page.read_bytes()
        attempts = (("memory", "add", "[NOTE] use " + token), ("lesson", "pasted " + token, "use a placeholder"),
                    ("annotate", "Topic", "[FINDING] token " + token))
        for args in attempts:
            with self.subTest(command=args[0]):
                completed = self.cli(*args)
                self.assertEqual(completed.returncode, 1)
                self.assertIn("github_pat", completed.stdout)
                self.assertNotIn(token, completed.stdout + completed.stderr)
                self.assertFalse(self.memory.exists())
        self.assertEqual(page.read_bytes(), page_bytes)
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n\n---\n", encoding="utf-8")
        memory_bytes = self.memory.read_bytes()
        with self.assertRaisesRegex(ValueError, "url_credentials"):
            self.quiet(hub.memory_add, "[NOTE] db at postgres://app:" + "Hunter2x" + "@db/prod")
        self.assertEqual(self.memory.read_bytes(), memory_bytes)
        self.assertEqual(self.cli("memory", "add", "[NOTE] db at postgres://app:${DB_PASS}@db/prod").returncode, 0)
        self.assertIn("${DB_PASS}", self.memory.read_text(encoding="utf-8"))

    def test_recall_budgets_json_and_pages_independent_entries(self):
        self.memory.parent.mkdir()
        huge = "needle \"\\ quoted\n" * 3000
        self.memory.write_text("# Memory\n\n---\n\n## [2026-10-28] [NOTE] large\n" + huge
                               + "\n## [2026-10-27] [NOTE] needle second\n"
                               + "\n## [2026-10-26] [NOTE] needle third\n", encoding="utf-8")
        seen = []
        cursor = None
        for _ in range(5):
            _, output = self.quiet(hub.memory_recall, "needle", limit=2, cursor=cursor, max_chars=900, json_out=True)
            self.assertLessEqual(len(output), 900)
            packet = json.loads(output)
            self.assertLessEqual(len(packet["results"]), 2)
            for result in packet["results"]:
                self.assertEqual(result["source"], ".agents/memory.md")
                self.assertLessEqual(len(result["excerpt"]), 2000)
                self.assertGreaterEqual(result["line"], 1)
                seen.append(result)
            cursor = packet["continuation"]
            if not cursor:
                break
        self.assertIsNone(cursor)
        self.assertEqual(len(seen), 3)
        self.assertTrue(seen[0]["truncated"])
        self.assertIsNotNone(seen[0]["continuation"])

    def test_recall_text_is_bounded_and_cursor_detects_changes(self):
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [2026-10-28] [NOTE] needle first\n" + "needle\n" * 3000
                               + "## [2026-10-27] [NOTE] needle second\n", encoding="utf-8")
        _, text = self.quiet(hub.memory_recall, "needle", max_chars=700)
        self.assertLessEqual(len(text), 700)
        _, output = self.quiet(hub.memory_recall, "needle", limit=1, json_out=True)
        cursor = json.loads(output)["continuation"]
        with self.assertRaises(ValueError):
            self.quiet(hub.memory_recall, "different", cursor=cursor)
        self.memory.write_text(self.memory.read_text(encoding="utf-8") + "changed", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.quiet(hub.memory_recall, "needle", cursor=cursor)
        self.assertNotEqual(self.cli("memory", "recall", "needle", "--limit", "0").returncode, 0)

    def test_recall_trims_expensive_prefix_before_the_query_match(self):
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [2026-10-28] [NOTE] large\n" + '"' * 500 + "NEEDLE" + "B" * 1000
                               + "\n## [2026-10-27] [NOTE] NEEDLE second\n", encoding="utf-8")
        _, output = self.quiet(hub.memory_recall, "NEEDLE", limit=1, max_chars=512, json_out=True)
        self.assertLessEqual(len(output), 512)
        packet = json.loads(output)
        self.assertIn("NEEDLE", packet["results"][0]["excerpt"])
        self.assertIsNotNone(packet["continuation"])

    def test_recall_legacy_excerpts_unchanged_with_new_snapshot_cursor(self):
        # Byte-golden of the default mode, recorded before --index existed. A deliberate
        # change to default recall output must update these strings on purpose.
        # Provenance: this test passes unchanged against scripts/context_hub.py and
        # scripts/oaw_common.py from 790177e (the parent of OAW-15); to re-check, copy
        # those two files into a scratch scripts/ beside this test file and run this test.
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n\n## [2026-10-28] [DECISION] Keep recall bounded\nContext line one.\n"
                               "The needle sits on the third line of this entry.\n\n"
                               "## [2026-10-27] [NOTE] Second needle entry\nDetails without the word.\n", encoding="utf-8")
        (self.docs / "Topic.md").write_text("---\ntitle: Recall Topic\n---\n# Recall Topic\n\nBackground paragraph.\n"
                                            "A Needle in the knowledge page.\n", encoding="utf-8")
        first = (".agents/memory.md:4\n## [2026-10-28] [DECISION] Keep recall bounded\nContext line one.\n"
                 "The needle sits on the third line of this entry.\n\n")
        golden = {
            "text": (first + ".agents/memory.md:8\n## [2026-10-27] [NOTE] Second needle entry\nDetails without the word.\n\n"
                     "docs/knowledge/Topic.md:1\n---\ntitle: Recall Topic\n---\n# Recall Topic\n\nBackground paragraph.\n"
                     "A Needle in the knowledge page.\n"),
            "json": ('{"schema_version":1,"results":[{"source":".agents/memory.md","line":4,"kind":"memory",'
                     '"excerpt":"## [2026-10-28] [DECISION] Keep recall bounded\\nContext line one.\\nThe needle sits on '
                     'the third line of this entry.","truncated":false,"continuation":null},{"source":".agents/memory.md",'
                     '"line":8,"kind":"memory","excerpt":"## [2026-10-27] [NOTE] Second needle entry\\nDetails without the '
                     'word.","truncated":false,"continuation":null},{"source":"docs/knowledge/Topic.md","line":1,'
                     '"kind":"knowledge","excerpt":"---\\ntitle: Recall Topic\\n---\\n# Recall Topic\\n\\nBackground '
                     'paragraph.\\nA Needle in the knowledge page.","truncated":false,"continuation":null}],'
                     '"truncated":false,"continuation":null}\n'),
            "paged": first + "Next cursor: WzEsMSwiMDk4ODFmNmVkOTMzNjBhMmY2YWQ4MWY0IiwiMzYyY2I1Yjg5N2VmYTI3YTA0YzEzMmNkIl0\n",
        }
        for name, kwargs in (("text", {}), ("json", {"json_out": True}), ("paged", {"limit": 1})):
            with self.subTest(output=name):
                self.assertEqual(self.quiet(hub.memory_recall, "needle", **kwargs)[1], golden[name])

    def test_recall_index_rows_cite_match_line_and_fit_max_chars(self):
        self.memory.parent.mkdir()
        entries = [f"## [2026-10-{number + 10}] [NOTE] entry {number}\nfiller line\n" + "x" * 300
                   + f"\nThe NEEDLE line {number} " + "y" * 400 + "\n" for number in range(12)]
        self.memory.write_text("# Memory\n---\n\n" + "\n".join(entries), encoding="utf-8")
        lines = self.memory.read_text(encoding="utf-8").split("\n")
        rows, cursor = [], None
        for _ in range(12):
            _, output = self.quiet(hub.memory_recall, "needle", limit=5, cursor=cursor, max_chars=900,
                                   json_out=True, index=True)
            self.assertLessEqual(len(output), 900)
            packet = json.loads(output)
            self.assertEqual(packet["mode"], "index")
            rows += packet["results"]
            cursor = packet["continuation"]
            if not cursor:
                break
        self.assertEqual(len(rows), 12)
        for number, row in enumerate(rows):
            self.assertEqual((row["kind"], row["date"], row["tag"], row["title"]),
                             ("memory", f"2026-10-{number + 10}", "NOTE", f"entry {number}"))
            self.assertTrue(row["match"].startswith(f"The NEEDLE line {number} "))
            self.assertEqual(len(row["match"]), 120)
            self.assertIn("NEEDLE", lines[row["line"] - 1])
            self.assertEqual(lines[row["entry_line"] - 1], f"## [2026-10-{number + 10}] [NOTE] entry {number}")
            self.assertEqual(row["entry_chars"], len(entries[number].rstrip()))
        _, text = self.quiet(hub.memory_recall, "needle", max_chars=600, index=True)
        self.assertLessEqual(len(text), 600)
        header, quote = text.splitlines()[:2]
        self.assertEqual(header, f".agents/memory.md:{rows[0]['line']}  2026-10-10 [NOTE] entry 0  "
                                 f"({rows[0]['entry_chars']} chars)")
        self.assertEqual(quote, "  > " + rows[0]["match"])
        self.assertIn("Next cursor: ", text)
        completed = self.cli("memory", "recall", "needle", "--index", "--limit", "1")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("  > The NEEDLE line 0 ", completed.stdout)

    def test_recall_index_cursor_is_refused_by_default_mode(self):
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [2026-10-28] [NOTE] needle one\n## [2026-10-27] [NOTE] needle two\n",
                               encoding="utf-8")
        cursors = {}
        for index in (True, False):
            _, output = self.quiet(hub.memory_recall, "needle", limit=1, json_out=True, index=index)
            cursors[index] = json.loads(output)["continuation"]
        self.assertNotEqual(cursors[True], cursors[False])
        for index in (True, False):
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "Invalid recall cursor"):
                self.quiet(hub.memory_recall, "needle", cursor=cursors[not index], index=index)
            _, output = self.quiet(hub.memory_recall, "needle", cursor=cursors[index], json_out=True, index=index)
            self.assertEqual(len(json.loads(output)["results"]), 1)
        self.assertNotEqual(self.cli("memory", "recall", "needle", "--cursor", cursors[True]).returncode, 0)
        self.assertNotEqual(self.cli("memory", "recall", "needle", "--index", "--cursor", cursors[False]).returncode, 0)

    def test_recall_index_knowledge_page_row_uses_title_and_matched_line(self):
        (self.docs / "Titled.md").write_text("---\ntitle: Front Title\n---\n# Heading Title\n\nintro\nA needle here.\n",
                                             encoding="utf-8")
        (self.docs / "Headed.md").write_text("intro line\n# Heading Only\n\nneedle on line four\n", encoding="utf-8")
        (self.docs / "Plain_Page.md").write_text("no heading\nneedle\n", encoding="utf-8")
        _, output = self.quiet(hub.memory_recall, "needle", json_out=True, index=True)
        rows = {row["source"]: row for row in json.loads(output)["results"]}
        expected = {"docs/knowledge/Titled.md": ("Front Title", 7, "A needle here."),
                    "docs/knowledge/Headed.md": ("Heading Only", 4, "needle on line four"),
                    "docs/knowledge/Plain_Page.md": ("Plain Page", 2, "needle")}
        self.assertEqual(set(rows), set(expected))
        for source, (title, line, match) in expected.items():
            row = rows[source]
            self.assertEqual((row["kind"], row["date"], row["tag"], row["entry_line"]), ("knowledge", None, None, 1))
            self.assertEqual((row["title"], row["line"], row["match"]), (title, line, match))
        _, text = self.quiet(hub.memory_recall, "needle", index=True)
        self.assertIn("docs/knowledge/Titled.md:7  Front Title  (", text)
        self.assertIn("  > A needle here.", text)
        self.assertNotIn("None", text)

    def test_recall_index_match_window_keeps_a_long_query_match(self):
        # CM-05: the window is max(120, len(query) + 40), so a long query is never cut.
        query = " ".join(["long recall query segment"] * 4)
        self.assertGreater(len(query), 80)
        line = "lead " * 80 + query + " tail" * 80
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [2026-10-28] [NOTE] long\n" + line + "\n", encoding="utf-8")
        (self.docs / "Long.md").write_text("# Long\n\n" + line + "\n", encoding="utf-8")
        _, output = self.quiet(hub.memory_recall, query.upper(), json_out=True, index=True)
        rows = json.loads(output)["results"]
        self.assertEqual([(row["source"], row["line"]) for row in rows],
                         [(".agents/memory.md", 4), ("docs/knowledge/Long.md", 3)])
        for row in rows:
            self.assertIn(query, row["match"])
            self.assertGreater(len(row["match"]), 120)
            self.assertLessEqual(len(row["match"]), len(query) + 40)
        _, text = self.quiet(hub.memory_recall, query, index=True)
        quotes = [row for row in text.splitlines() if row.startswith("  > ")]
        self.assertEqual(len(quotes), 2)
        for quote in quotes:
            self.assertIn(query, quote)
        # A row whose complete match cannot fit is refused, never cut.
        self.memory.write_text("# Memory\n---\n## [2026-10-28] [NOTE] longest\n" + "z" * 480 + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "too small"):
            self.quiet(hub.memory_recall, "z" * 480, max_chars=512, index=True)

    def test_recall_index_rejects_multiline_query_and_caps_header_fields(self):
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [" + "d" * 3000 + "] [" + "T" * 3000 + "] " + "t" * 3000
                               + "\nfirst needle line\nsecond line\n", encoding="utf-8")
        for query in ("needle line\nsecond", "needle\r"):
            with self.subTest(query=query), self.assertRaisesRegex(ValueError, "single-line query"):
                self.quiet(hub.memory_recall, query, index=True)
        # The default mode keeps accepting it: its excerpts already span lines.
        self.assertIn("second line", self.quiet(hub.memory_recall, "needle line\nsecond")[1])
        _, output = self.quiet(hub.memory_recall, "needle", json_out=True, index=True)
        row = json.loads(output)["results"][0]
        self.assertEqual((row["date"], row["tag"], row["title"]), ("d" * 40, "T" * 40, "t" * 120))
        _, text = self.quiet(hub.memory_recall, "needle", index=True, max_chars=512)
        self.assertEqual(len(text.splitlines()), 2)
        self.assertLess(len(text.splitlines()[0]), 260)

    def test_recall_index_fixture_byte_counts(self):
        # Static-measured output sizes on a fixed fixture, not a model benchmark: 30
        # entries of about 1.5 KB. Only "index is shorter" is asserted as a property;
        # the pinned sizes record the evidence and change only with the output format.
        self.memory.parent.mkdir()
        filler = "Context words for a realistic entry body. " * 17
        entries = [f"## [2026-10-{number % 28 + 1:02d}] [NOTE] fixture entry {number}\n{filler}\n"
                   f"The needle detail {number} sits mid entry.\n{filler}\n" for number in range(30)]
        self.memory.write_text("# Memory\n---\n\n" + "\n".join(entries), encoding="utf-8")
        sizes = {}
        for index in (False, True):
            for json_out in (False, True):
                _, output = self.quiet(hub.memory_recall, "needle", limit=30, max_chars=1000000,
                                       json_out=json_out, index=index)
                sizes[("index" if index else "default", "json" if json_out else "text")] = len(output.encode("utf-8"))
        for form in ("text", "json"):
            self.assertLess(sizes[("index", form)], sizes[("default", form)])
        self.assertEqual(sizes, {("default", "text"): 31079, ("default", "json"): 32810,
                                 ("index", "text"): 3350, ("index", "json"): 6054})

    def pending(self):
        return self.base / ".oaw/memory-pending.md"

    def test_memory_order_preserves_new_note_before_local_day_legacy(self):
        self.memory.parent.mkdir()
        packets = []
        for offset in (8, -8):
            with self.subTest(local_offset=offset):
                local = timezone(timedelta(hours=offset))
                clock_value = datetime(2026, 11, 13, 23, 30, tzinfo=timezone.utc)
                self.memory.write_text("# Memory\n---\n## [2026-11-14] [DECISION] cache needle: use LRU\n")
                with patch.object(hub, "datetime", wraps=datetime) as clock:
                    # Simulate a host whose local clock differs; UTC-aware calls agree.
                    clock.now.side_effect = lambda tz=None: clock_value.astimezone(tz or local)
                    self.quiet(hub.memory_add, "[DECISION] cache needle: LRU superseded, use ARC")
                    rendered = []
                    for index in (False, True):
                        output = self.quiet(hub.memory_recall, "cache needle", json_out=True, index=index)[1]
                        rows = json.loads(output)["results"]
                        self.assertIn("use ARC", rows[0]["title" if index else "excerpt"])
                        self.assertIn("use LRU", rows[1]["title" if index else "excerpt"])
                        rendered.append(output)
                    packets.append(rendered)
                    self.assertIn("use ARC", self.quiet(hub.memory_show, 1)[1])
                    for function, kwargs in ((hub.status, {}), (hub.bootstrap, {"compact": True})):
                        output = self.quiet(function, **kwargs)[1]
                        self.assertLess(output.index("use ARC"), output.index("use LRU"))
        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[0], packets[1])

    def test_memory_order_merges_heads_without_reordering_either_file(self):
        def source(name, headers):
            return {"source": name, "content": "".join(
                f"## [{date}] [NOTE] {title}\n" for date, title in headers)}

        main = source("main", [("2026-11-14T02:00:00.000000+00:00", "m-new"),
                               ("2026-11-14", "m-legacy"),
                               ("2026-11-14T01:00:00.000000+00:00", "m-handwritten")])
        pending = source("pending", [("2026-11-14T03:00:00.000000+00:00", "p-new"),
                                     ("2026-11-14T01:30:00.000000+00:00", "p-middle"),
                                     ("2026-11-14T00:00:00.000000+00:00", "p-midnight"),
                                     ("2026-11-13", "p-old")])
        titles = lambda sources: [row["entry"].split("] ")[-1] for row in hub._memory_entries(sources)]
        self.assertEqual(titles([main, pending]),
                         ["p-new", "m-new", "p-middle", "p-midnight", "m-legacy", "m-handwritten", "p-old"])
        # A date alone cannot outrank a timestamp on the same UTC day, in either source.
        for sources in ([source("main", [("2026-11-14", "legacy")]),
                         source("pending", [("2026-11-14T00:00:00.000000+00:00", "stamp")])],
                        [source("main", [("2026-11-14T00:00:00.000000+00:00", "stamp")]),
                         source("pending", [("2026-11-14", "legacy")])]):
            self.assertEqual(titles(sources), ["stamp", "legacy"])
        # Compact and week dates must not acquire version-dependent ISO parsing semantics.
        for date in ("20261114", "2026-W46", "14 Nov 2026"):
            self.assertEqual(titles([source("main", [(date, "unknown")]),
                                     source("pending", [("2026-11-13", "dated")])]), ["dated", "unknown"])
        # A hand-written time after the date keeps the date, so one such header at the top of a file
        # does not push the whole file below older pending notes (release review C2-03).
        for date in ("2026-11-14 09:00", "2026-11-14T03:00:00Z", "2026-11-14T09:00"):
            self.assertEqual(titles([source("main", [(date, "handwritten"), ("2026-11-12", "m-older")]),
                                     source("pending", [("2026-11-13", "p-older")])]),
                             ["handwritten", "p-older", "m-older"])
            # Ordered by the date alone: a full timestamp on the same UTC day still comes first.
            self.assertEqual(titles([source("main", [(date, "handwritten")]),
                                     source("pending", [("2026-11-14T00:00:00.000000+00:00", "stamp")])]),
                             ["stamp", "handwritten"])

    def test_memory_add_puts_the_new_note_on_top_without_a_separator(self):
        # Release review R2-01: a memory file without '---' used to get new notes appended, so the
        # superseded decision stayed first for recall, show, status and bootstrap.
        self.memory.parent.mkdir()
        self.memory.write_text("# Notes\n\nPreamble text.\n\n## [2026-10-01] [DECISION] cache needle: use LRU\n\nBody.\n",
                               encoding="utf-8")
        self.quiet(hub.memory_add, "[DECISION] cache needle: LRU superseded, use ARC")
        text = self.memory.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Notes\n\nPreamble text.\n\n## ["), text[:60])
        self.assertLess(text.index("use ARC"), text.index("use LRU"))
        self.assertTrue(text.endswith("## [2026-10-01] [DECISION] cache needle: use LRU\n\nBody.\n"))
        for index in (False, True):
            rows = json.loads(self.quiet(hub.memory_recall, "cache needle", json_out=True, index=index)[1])["results"]
            self.assertIn("use ARC", rows[0]["title" if index else "excerpt"])
            self.assertIn("use LRU", rows[1]["title" if index else "excerpt"])
        self.assertIn("use ARC", self.quiet(hub.memory_show, 1)[1])
        self.assertNotIn("use LRU", self.quiet(hub.memory_show, 1)[1])
        for function, kwargs in ((hub.status, {}), (hub.bootstrap, {"compact": True})):
            output = self.quiet(function, **kwargs)[1]
            self.assertLess(output.index("use ARC"), output.index("use LRU"))
        # A file with no entry at all still gets the note appended after its text.
        self.memory.write_text("# Notes\n\nNothing yet.\n", encoding="utf-8")
        self.quiet(hub.memory_add, "[NOTE] first needle")
        self.assertTrue(self.memory.read_text(encoding="utf-8").startswith("# Notes\n\nNothing yet.\n\n## ["))

    def test_a_cursor_issued_under_another_entry_order_is_refused(self):
        # Release review R2-02: the order of unchanged files changed, so an old cursor must not
        # be accepted (it skipped one entry and repeated another).
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n" + "".join(
            f"\n## [2026-11-{day:02d}] [NOTE] needle {day}\n" for day in (14, 13, 12)), encoding="utf-8")
        for index in (False, True):
            with self.subTest(index=index):
                with patch.object(hub, "MEMORY_ORDER_MARKER", b"memory-sources-v2\0"):
                    old = json.loads(self.quiet(hub.memory_recall, "needle", limit=1, json_out=True, index=index)[1])["continuation"]
                self.assertTrue(old)
                with self.assertRaisesRegex(ValueError, "cursor"):
                    self.quiet(hub.memory_recall, "needle", limit=1, cursor=old, index=index)
                fresh = json.loads(self.quiet(hub.memory_recall, "needle", limit=1, json_out=True, index=index)[1])["continuation"]
                self.assertNotEqual(old, fresh)
                self.quiet(hub.memory_recall, "needle", limit=1, cursor=fresh, index=index)

    def test_read_only_main_routes_directly_to_pending_without_temporary_or_retry(self):
        self.memory.parent.mkdir()
        self.memory.write_bytes(b"# Memory\n---\n## [2026-10-01] [NOTE] original\n")
        original, mode = self.memory.read_bytes(), self.memory.stat().st_mode
        self.addCleanup(self.memory.chmod, mode)
        self.memory.chmod(0o444)
        access = os.access
        # Privileged hosts may ignore mode bits; still exercise the denial path there.
        def writable(path, flags):
            return False if Path(path) == self.memory and flags == os.W_OK else access(path, flags)
        access_patch = patch.object(hub.os, "access", side_effect=writable) if access(self.memory, os.W_OK) else contextlib.nullcontext()
        with access_patch, patch.object(hub, "locked_update", wraps=hub.locked_update) as update, \
                patch.object(common.time, "sleep", side_effect=AssertionError("permission fallback must not retry")):
            _, output = self.quiet(hub.memory_add, "[NOTE] read-only needle")
        self.assertEqual(self.memory.read_bytes(), original)
        self.assertIn("read-only needle", self.pending().read_text(encoding="utf-8"))
        self.assertIn(".oaw/memory-pending.md", output)
        self.assertEqual([Path(call.args[0]) for call in update.call_args_list], [self.pending()])
        self.assertEqual(list(self.base.rglob("*.tmp")), [])

    def test_memory_add_reports_relative_destination_for_symlink_base(self):
        link = self.top / "link"
        with contextlib.ExitStack() as stack:
            try:
                link.symlink_to(self.base, target_is_directory=True)
            except (OSError, NotImplementedError):
                # No symlink privilege: simulate resolution and keep the actual write.
                realpath, resolve = os.path.realpath, Path.resolve
                stack.enter_context(patch.object(os.path, "realpath", side_effect=lambda path, **kwargs:
                                    realpath(str(path).replace(str(link), str(self.base)), **kwargs)))
                stack.enter_context(patch.object(Path, "resolve", lambda path, *args, **kwargs:
                                    resolve(Path(str(path).replace(str(link), str(self.base))), *args, **kwargs)))
            stack.enter_context(patch.multiple(hub, BASE_DIR=str(link), MEMORY_FILE=str(link / ".agents/memory.md")))
            _, output = self.quiet(hub.memory_add, "[NOTE] linked destination")
        self.assertIn("added to .agents/memory.md", output)

    def deny_primary(self, err=errno.EACCES):
        original = hub.locked_update

        def update(path, *args, **kwargs):
            if Path(path) == self.memory:
                raise OSError(err, "fixture primary failure")
            return original(path, *args, **kwargs)
        return patch.object(hub, "locked_update", side_effect=update)

    def test_memory_fallback_only_for_permission_errors_and_reports_path(self):
        for code in (errno.EACCES, errno.EPERM, errno.EROFS):
            with self.subTest(code=code), self.deny_primary(code):
                _, output = self.quiet(hub.memory_add, f"[NOTE] pending-{code}")
                self.assertIn(".oaw/memory-pending.md", output)
                self.assertIn("permission denied", output)
                self.assertFalse(self.memory.exists())
                self.assertIn(f"pending-{code}", self.pending().read_text())
        before = self.pending().read_bytes()
        for code in (errno.EIO, errno.ENOSPC, errno.ENOENT, errno.ENOTDIR, errno.ETIMEDOUT):
            with self.subTest(code=code), self.deny_primary(code), self.assertRaises(OSError):
                self.quiet(hub.memory_add, "[NOTE] must not be saved")
            self.assertEqual(self.pending().read_bytes(), before)
        with self.deny_primary():
            # A directory at the fallback filename is a real write failure.
            self.pending().unlink()
            self.pending().mkdir()
            with self.assertRaises(OSError):
                self.quiet(hub.memory_add, "[NOTE] cannot save anywhere")

    def test_primary_lock_permission_failure_uses_pending_and_later_recall(self):
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [2026-10-01] [NOTE] old record\n")
        original = self.memory.read_bytes()
        # POSIX non-root: real directory denial; Windows/root: inject the same
        # lock failure, since chmod cannot enforce directory writes there.
        actual_denial = os.name != "nt" and getattr(os, "geteuid", lambda: 0)() != 0
        if actual_denial:
            self.memory.parent.chmod(0o555)
        try:
            if actual_denial:
                completed = self.cli("memory", "add", "[DECISION] sandbox needle")
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                output = completed.stdout
            else:
                with self.deny_primary():
                    _, output = self.quiet(hub.memory_add, "[DECISION] sandbox needle")
            self.assertIn(".oaw/memory-pending.md", output)
            self.assertEqual(self.memory.read_bytes(), original)
            self.assertFalse((self.memory.parent / ".memory.md.oaw.lock").exists())
            self.assertIn("sandbox needle", self.pending().read_text())
            recall = self.cli("memory", "recall", "sandbox needle", "--json")
            self.assertEqual(recall.returncode, 0, recall.stdout)
            self.assertEqual(json.loads(recall.stdout)["results"][0]["source"], ".oaw/memory-pending.md")
        finally:
            self.memory.parent.chmod(0o755)

    def test_fallback_preserves_confinement_and_rejects_secrets_before_any_write(self):
        with self.deny_primary(), self.assertRaises(ValueError):
            self.quiet(hub.memory_add, "ghp_" + "A" * 36)
        self.assertFalse(self.memory.exists())
        self.assertFalse(self.pending().exists())
        outside = self.top / "outside"
        outside.mkdir()
        try:
            (self.base / ".oaw").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.deny_primary(), self.assertRaises(ValueError):
            self.quiet(hub.memory_add, "[NOTE] no escape")
        self.assertEqual(list(outside.iterdir()), [])
        (self.base / ".oaw").unlink()
        self.memory.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.quiet(hub.memory_add, "[NOTE] primary escape is not a permission fallback")
        self.assertFalse(self.pending().exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_both_sources_recover_and_alternate_without_promoting_old_file_contents(self):
        self.memory.parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [2026-10-01] [DECISION] needle old\n")
        self.quiet(hub.memory_add, "[DECISION] needle primary-first")
        with self.deny_primary():
            self.quiet(hub.memory_add, "[DECISION] needle pending; supersedes needle old")
        self.quiet(hub.memory_add, "[DECISION] needle primary-restored")
        with self.deny_primary():
            self.quiet(hub.memory_add, "[DECISION] needle pending-latest")
        for index in (False, True):
            _, output = self.quiet(hub.memory_recall, "needle", json_out=True, index=index)
            rows = json.loads(output)["results"]
            self.assertEqual([r["source"] for r in rows], [
                ".oaw/memory-pending.md", ".agents/memory.md", ".oaw/memory-pending.md",
                ".agents/memory.md", ".agents/memory.md",
            ])
            rendered = [r["title"] if index else r["excerpt"] for r in rows]
            for row, expected in zip(rendered, ["pending-latest", "primary-restored", "supersedes", "primary-first", "needle old"]):
                self.assertIn(expected, row)
        self.assertIn("needle old", self.memory.read_text(), "superseded evidence is retained")
        shown = self.quiet(hub.memory_show, 2)[1]
        self.assertLess(shown.index("pending-latest"), shown.index("primary-restored"))

    def test_legacy_ties_and_invalid_dates_have_deterministic_order(self):
        self.memory.parent.mkdir()
        self.pending().parent.mkdir()
        self.memory.write_text("# Memory\n---\n## [2026-10-02] [NOTE] needle main\n"
                               "## [unknown] [NOTE] needle undated\n")
        self.pending().write_text("# Memory\n---\n## [2026-10-02] [NOTE] needle pending first\n"
                                  "## [2026-10-02] [NOTE] needle pending second\n")
        _, output = self.quiet(hub.memory_recall, "needle", json_out=True, index=True)
        self.assertEqual([r["title"] for r in json.loads(output)["results"]],
                         ["needle pending first", "needle pending second", "needle main", "needle undated"])

    def test_cursor_invalidated_by_either_source_presence_or_content(self):
        self.memory.parent.mkdir()
        original = "# Memory\n---\n## [2026-10-02] [NOTE] needle one\n## [2026-10-01] [NOTE] needle two\n"
        self.memory.write_text(original)
        for index in (False, True):
            for action in ("primary-edit", "pending-create", "pending-edit", "pending-delete"):
                with self.subTest(index=index, action=action):
                    self.memory.write_text(original)
                    self.pending().parent.mkdir(exist_ok=True)
                    if action in ("pending-edit", "pending-delete"):
                        self.pending().write_text("# no matching entries\n")
                    elif self.pending().exists():
                        self.pending().unlink()
                    _, output = self.quiet(hub.memory_recall, "needle", limit=1, json_out=True, index=index)
                    cursor = json.loads(output)["continuation"]
                    self.assertIsNotNone(cursor)
                    if action == "primary-edit":
                        self.memory.write_text(original + "changed")
                    elif action == "pending-delete":
                        self.pending().unlink()
                    else:
                        self.pending().write_text("" if action == "pending-create" else "nonmatching edit")
                    with self.assertRaisesRegex(ValueError, "sources changed"):
                        self.quiet(hub.memory_recall, "needle", cursor=cursor, index=index)

    def test_pending_only_visible_to_search_status_bootstrap_and_context_lanes(self):
        with self.deny_primary():
            self.quiet(hub.memory_add, "[NOTE] pending visibility")
        self.assertIn("pending visibility", self.quiet(hub.search, "visibility", include_memory=True)[1])
        self.assertIn("1 memories", self.quiet(hub.status, compact=True)[1])
        self.assertIn("pending visibility", self.quiet(hub.status)[1])
        self.assertIn("pending visibility", self.quiet(hub.bootstrap, compact=True)[1])
        for lane in ("operational", "debug"):
            self.assertIn("pending visibility", self.quiet(hub.context_lane, lane)[1])

    def test_empty_recall_has_plain_output_without_host_guidance(self):
        for index in (False, True):
            for json_out in (False, True):
                _, output = self.quiet(hub.memory_recall, "missing", max_chars=512, index=index, json_out=json_out)
                self.assertLessEqual(len(output), 512)
                if json_out:
                    packet = json.loads(output)
                    self.assertEqual(packet["results"], [])
                    self.assertNotIn("message", packet)
                    self.assertNotIn("next_action", packet)
                else:
                    self.assertEqual(output, "No matches found.\n")
        self.quiet(hub.memory_add, "[NOTE] missing word now exists")
        _, output = self.quiet(hub.memory_recall, "missing", json_out=True)
        self.assertNotIn("next_action", json.loads(output))

    def test_concurrent_primary_and_pending_writers_retain_all_entries(self):
        context = multiprocessing.get_context("spawn")
        start = context.Barrier(6)
        workers = [context.Process(target=_mixed_memory_worker, args=(str(self.base), start, number))
                   for number in range(6)]
        for worker in workers:
            worker.start()
        try:
            for worker in workers:
                worker.join(40)
                self.assertEqual(worker.exitcode, 0)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
        _, output = self.quiet(hub.memory_recall, "mixed-writer", limit=100, max_chars=100000, json_out=True)
        entries = json.loads(output)["results"]
        self.assertEqual(len(entries), 18)
        content = self.memory.read_text() + self.pending().read_text()
        for number in range(6):
            for entry in range(3):
                self.assertEqual(content.count(f"mixed-writer-{number}-entry-{entry}"), 1)
        self.assertEqual({entry["source"] for entry in entries},
                         {".agents/memory.md", ".oaw/memory-pending.md"})


if __name__ == "__main__":
    unittest.main()
