"""Behavioral regressions for the portable Context Hub CLI (stdlib only)."""

import contextlib
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


if __name__ == "__main__":
    unittest.main()
