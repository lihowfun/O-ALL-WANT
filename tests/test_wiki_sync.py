"""Compiler regressions: confinement, stable rebuilds, provenance and freshness."""

import contextlib
import importlib
import io
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
wiki = importlib.import_module("wiki_sync")
common = importlib.import_module("oaw_common")


def _experiment_worker(base, start, number):
    wiki.BASE_DIR = base
    wiki.KNOWLEDGE_DIR = str(Path(base) / "docs/knowledge")
    start.wait(timeout=20)
    with contextlib.redirect_stdout(io.StringIO()):
        for entry in range(2):
            wiki.add_experiment(f"writer_{number}_entry_{entry}", "accepted", "result", "conclusion")


class WikiSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".wiki-fixture-", dir=Path(__file__).parent)
        self.top = Path(self.temporary.name).resolve()
        self.base = self.top / "project"
        self.raw_dir = self.base / "docs/raw"
        self.knowledge = self.base / "docs/knowledge"
        self.raw_dir.mkdir(parents=True)
        self.knowledge.mkdir()
        self.change = patch.multiple(wiki, BASE_DIR=str(self.base), RAW_DIR=str(self.raw_dir),
                                     KNOWLEDGE_DIR=str(self.knowledge))
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

    def raw(self, topic="Topic", body="Fact observed in 2025.", name="source.md", updated="2025-01-01"):
        path = self.raw_dir / name
        path.write_text(f"---\nsource_id: {name[:-3]}\ntitle: Source\ntopic_id: {topic}\n"
                        f"summary: Measured 12 items.\nlast_updated: {updated}\nrelated_topics: []\n"
                        f"---\n\n# Source\n\n{body}\n", encoding="utf-8")
        return path

    def manual(self, topic, updated):
        path = self.knowledge / (topic + ".md")
        path.write_text(f"---\nid: {topic}\ntitle: {topic}\npage_type: topic\nbuild_origin: manual\n"
                        f"source_refs: []\nlast_updated: {updated}\nrelated_topics: []\n---\n"
                        f"# {topic}\nFact 1\nFact 2\nFact 3\nFact 4\n", encoding="utf-8")
        return path

    def test_compile_rejects_path_and_reserved_topic_ids(self):
        for topic in ("../../../escaped", str(self.top / "absolute"), "index", "log", "CON"):
            self.raw(topic)
            with self.subTest(topic=topic), self.assertRaises(ValueError):
                self.quiet(wiki.build)
        self.assertFalse((self.top / "escaped.md").exists())
        self.assertFalse((self.top / "absolute.md").exists())

    def test_input_symlink_escape_is_rejected(self):
        outside = self.top / "outside.md"
        outside.write_text("outside sentinel", encoding="utf-8")
        try:
            (self.raw_dir / "linked.md").symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaises(ValueError):
            self.quiet(wiki.build)

    def test_output_directory_symlink_escape_is_rejected(self):
        self.raw()
        outside = self.top / "outside"
        outside.mkdir()
        self.knowledge.rmdir()
        try:
            self.knowledge.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.knowledge.mkdir(exist_ok=True)
            self.skipTest(f"Symlink creation unavailable: {exc}")
        with self.assertRaises(ValueError):
            self.quiet(wiki.build)
        self.assertEqual(list(outside.iterdir()), [])

    def test_stale_page_cannot_borrow_unrelated_page_date(self):
        self.raw("A", updated="2025-01-01")
        self.quiet(wiki.build)
        page = self.knowledge / "A.md"
        page.write_text(page.read_text(encoding="utf-8").replace("last_updated: 2025-01-01", "last_updated: 2020-01-01"), encoding="utf-8")
        self.manual("Z", "2026-01-01")
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 1)
        self.assertIn("stale page 'A'", output)

    def test_fresh_page_is_not_marked_stale_by_unrelated_old_page(self):
        self.raw("A", updated="2025-01-01")
        self.quiet(wiki.build)
        self.manual("Z", "2020-01-01")
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 0, output)
        self.assertNotIn("stale page 'A'", output)

    def test_raw_annotation_heading_does_not_grow_on_refresh(self):
        self.raw(body="## AI Annotations\n\nraw-only marker")
        self.quiet(wiki.build)
        page = self.knowledge / "Topic.md"
        original = page.read_text(encoding="utf-8")
        for _ in range(3):
            self.quiet(wiki.refresh, "Topic")
            self.assertEqual(page.read_text(encoding="utf-8"), original)
        self.assertEqual(original.count("raw-only marker"), 1)
        self.assertEqual(original.count(common.ANNOTATIONS_START), 1)

    def test_legacy_annotations_survive_migration_and_rebuild(self):
        self.raw(body="## AI Annotations\n\nraw-only marker")
        self.quiet(wiki.build)
        page = self.knowledge / "Topic.md"
        content = page.read_text(encoding="utf-8")
        content = content[:content.rfind("## AI Annotations")] + "## AI Annotations\n\n> legacy user note\n"
        page.write_text(content, encoding="utf-8")
        self.quiet(wiki.refresh, "Topic")
        migrated = page.read_text(encoding="utf-8")
        self.assertEqual(migrated.count("raw-only marker"), 1)
        self.assertEqual(migrated.count("legacy user note"), 1)
        self.assertIn("legacy user note", common.extract_annotations(migrated))
        self.quiet(wiki.refresh, "Topic")
        self.assertEqual(page.read_text(encoding="utf-8"), migrated)

    def test_relative_links_images_and_reference_definitions_are_rebased(self):
        (self.raw_dir / "_appendix.md").write_text("# Appendix\n", encoding="utf-8")
        (self.raw_dir / "_space name.md").write_text("# Spaced\n", encoding="utf-8")
        (self.raw_dir / "_diagram(1).png").write_bytes(b"fixture")
        body = ('[appendix](_appendix.md#part "title")\n\n'
                '![image](_appendix.md)\n\n'
                '[query](_appendix.md?raw=1#part)\n\n'
                '[reference]: <_space name.md> "title"\n\n'
                '![parenthesized](_diagram(1).png)\n\n'
                '[external](https://example.invalid/path)\n\n'
                '[same](#part)\n\n'
                '`[code](_appendix.md)`\n\n'
                '```md\n[example](_appendix.md)\n```')
        self.raw(body=body)
        self.quiet(wiki.build)
        page = (self.knowledge / "Topic.md").read_text(encoding="utf-8")
        self.assertIn('[appendix](../raw/_appendix.md#part "title")', page)
        self.assertIn('![image](../raw/_appendix.md)', page)
        self.assertIn('[query](../raw/_appendix.md?raw=1#part)', page)
        self.assertIn('[reference]: <../raw/_space name.md> "title"', page)
        self.assertIn('![parenthesized](../raw/_diagram%281%29.png)', page)
        self.assertIn('`[code](_appendix.md)`', page)
        self.assertIn('[example](_appendix.md)', page)
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 0, output)

    def test_unclosed_raw_fences_cannot_swallow_annotations(self):
        self.raw(body="Example:\n\n```python\nprint('unterminated')")
        self.raw(body="~~~~\n```\nstill inside the tilde fence", name="second.md")
        self.quiet(wiki.build)
        page = self.knowledge / "Topic.md"
        page.write_text(common.append_annotation(page.read_text(encoding="utf-8"), "keep this note"), encoding="utf-8")
        self.quiet(wiki.build)
        built = page.read_text(encoding="utf-8")
        self.assertIn("keep this note", common.extract_annotations(built))
        self.assertEqual(built.count("keep this note"), 1)
        self.quiet(wiki.build)
        self.assertEqual(page.read_text(encoding="utf-8"), built)

    def test_root_relative_and_out_of_repo_links_do_not_abort(self):
        self.raw("Bee", name="b.md")
        self.raw("Ay", "See [b](/docs/raw/b.md) and [spec](../../../upstream/SPEC.md).", name="a.md")
        self.quiet(wiki.build)
        page = (self.knowledge / "Ay.md").read_text(encoding="utf-8")
        self.assertIn("[b](../raw/b.md)", page)
        self.assertIn("[spec](../../../upstream/SPEC.md)", page)
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 0, output)
        self.assertIn("outside the project", output)

    def test_footnote_definitions_are_not_rebased_as_links(self):
        self.raw(body="Latency fell 30%.[^bench]\n\n[^bench]: Measured on the nightly runner.")
        self.quiet(wiki.build)
        page = (self.knowledge / "Topic.md").read_text(encoding="utf-8")
        self.assertIn("[^bench]: Measured on the nightly runner.", page)
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 0, output)

    def test_moved_raw_source_cannot_leave_a_passing_stale_page(self):
        self.raw("OldTopic", "Retry limit is 3.")
        self.quiet(wiki.build)
        self.raw("NewTopic", "Retry limit is 5.")
        self.quiet(wiki.build)
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 1)
        self.assertIn("orphaned compiled page 'OldTopic'", output)
        self.assertTrue((self.knowledge / "OldTopic.md").exists())
        (self.knowledge / "OldTopic.md").unlink()
        self.raw("NewTopic", "Second fact 2.", name="other.md")
        self.quiet(wiki.build)
        self.raw("Split", "Moved fact 4.", name="other.md")
        self.quiet(wiki.refresh, "Split")
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 1)
        self.assertIn("stale page 'NewTopic'", output)
        self.quiet(wiki.build)
        self.quiet(wiki.add_experiment, "experiment", "accepted", "result", "conclusion")
        result, output = self.quiet(wiki.lint)
        self.assertEqual(result, 0, output)

    def test_repeated_build_is_byte_stable_including_meta_pages(self):
        self.raw()
        self.quiet(wiki.build)
        before = {path.name: path.read_bytes() for path in self.knowledge.glob("*.md")}
        with patch.object(wiki, "_today", return_value="2099-01-01"):
            self.quiet(wiki.build)
        after = {path.name: path.read_bytes() for path in self.knowledge.glob("*.md")}
        self.assertEqual(before, after)

    def test_manual_page_and_failed_state_update_are_preserved(self):
        self.raw()
        page = self.manual("Topic", "2025-01-01")
        before = page.read_bytes()
        with self.assertRaises(ValueError):
            self.quiet(wiki.build)
        self.assertEqual(page.read_bytes(), before)
        state = self.knowledge / "CURRENT_STATE.md"
        state.write_text("---\nlast_updated: 2020-01-01\n---\n# State\n\n| A | queued |\n", encoding="utf-8")
        before = state.read_bytes()
        with self.assertRaises(ValueError):
            self.quiet(wiki.update_state, phase="Missing", status="done")
        self.assertEqual(state.read_bytes(), before)

    def test_multiprocessing_experiment_rows_all_survive(self):
        context = multiprocessing.get_context("spawn")
        start = context.Barrier(4)
        workers = [context.Process(target=_experiment_worker, args=(str(self.base), start, number)) for number in range(4)]
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
        text = (self.knowledge / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
        for number in range(4):
            for entry in range(2):
                self.assertEqual(text.count(f"writer_{number}_entry_{entry}"), 1)

    def test_missing_refresh_fails_without_traceback(self):
        environment = dict(os.environ, AGENT_MEMORY_BASE_DIR=str(self.base), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        completed = subprocess.run([sys.executable, str(SCRIPTS / "wiki_sync.py"), "refresh", "Missing"],
                                   env=environment, capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
