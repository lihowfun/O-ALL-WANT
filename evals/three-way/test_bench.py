"""Offline behavioral tests for measurement rejection and source fixtures."""
import unittest
import tempfile
from pathlib import Path
import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
import bench
import continue_budget
import summarize


class MeasurementTests(unittest.TestCase):
    def event(self, **values):
        usage = {"input_tokens": 100, "cached_input_tokens": 60, "output_tokens": 20, "reasoning_output_tokens": 10}
        usage.update(values)
        return {"type": "turn.completed", "usage": usage}

    def test_preserves_usage_without_double_counting_reasoning(self):
        usage = bench.usage_of([self.event()])
        self.assertEqual(usage["input_tokens"] + usage["output_tokens"], 120)

    def test_rejects_multiple_unknown_cumulative_turns(self):
        with self.assertRaises(ValueError):
            bench.usage_of([self.event(), self.event()])

    def test_rejects_missing_usage_and_invalid_cache(self):
        for events in ([], [self.event(input_tokens=None)], [self.event(cached_input_tokens=101)], [self.event(output_tokens=True)]):
            with self.subTest(events=events), self.assertRaises(ValueError):
                bench.usage_of(events)

    def test_rejects_unmetered_nested_agent(self):
        with self.assertRaises(ValueError):
            bench.usage_of([self.event(), {"item": {"type": "collab_tool_call"}}])

    def test_invalid_report_is_not_a_success(self):
        with self.assertRaises(ValueError):
            bench.parse_answer('{"looks_good":true}')

    def test_transient_memory_fact_is_not_in_original_source(self):
        for name in ("larch", "pumice"):
            self.assertNotIn("731", "\n".join(bench.memory_source(name).values()))

    def test_arm_sources_are_real_versions(self):
        spec = bench.read(bench.SPEC)
        self.assertEqual(set(spec["sources"]), set(bench.ARMS))
        self.assertTrue(all(len(sha) == 40 for sha in spec["sources"].values()))

    def test_continuation_never_retries_dispatched_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = continue_budget.ContinuedRunner.__new__(continue_budget.ContinuedRunner)
            runner.out = Path(folder)
            bench.write(runner.out / "raw/trial/result.json", {"status": "incomplete"})
            with self.assertRaisesRegex(ValueError, "cannot be retried"):
                runner.call("trial", Path(folder), "prompt")

    def test_continuation_rejects_ambiguous_partial_call(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = continue_budget.ContinuedRunner.__new__(continue_budget.ContinuedRunner)
            runner.out = Path(folder)
            bench.write(runner.out / "raw/trial/events.jsonl", "partial evidence")
            with self.assertRaisesRegex(ValueError, "Ambiguous"):
                runner.call("trial", Path(folder), "prompt")

    def test_wrong_scope_and_bool_numbers_do_not_pass_handoff(self):
        self.assertFalse(summarize.matches("scope", "analytics-larch", "export-larch"))
        self.assertFalse(summarize.matches("retry_seconds", True, 1))
        self.assertEqual(summarize.expected_contract("larch", 4)["approval_ticket"], "EX-LARCH-942")

    def test_citation_existence_is_not_claimed_as_grounding(self):
        self.assertEqual(summarize.citation_paths("docs/decisions/044.md:3"), ["docs/decisions/044.md"])

    def test_exit_zero_and_valid_json_without_real_io_stop_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = bench.Runner.__new__(bench.Runner)
            runner.out = Path(folder)
            runner.cli = "unused"
            runner.spec = {"model": "fixture", "effort": "medium", "limits": {"input_plus_output_tokens": 10000, "output_tokens": 1000, "total_seconds": 30, "per_process_seconds": 1}}
            runner.started = time.monotonic()
            runner.abort, runner.lock = threading.Event(), threading.Lock()
            runner.total = runner.output = 0
            runner.rows = []
            def fake_run(*args, **kwargs):
                events = [{"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps({"findings": [], "answers": {}, "sources": {}, "unknowns": []})}}, self.event()]
                kwargs["stdout"].write("\n".join(json.dumps(e) for e in events))
                kwargs["stdout"].flush()
                return SimpleNamespace(returncode=0)
            with patch.object(bench.subprocess, "run", side_effect=fake_run), self.assertRaises(RuntimeError):
                runner.call("fixture", Path(folder) / "workspace", "task")
            self.assertTrue(runner.abort.is_set())
            self.assertEqual(runner.rows[0]["status"], "incomplete")
            self.assertEqual(runner.total, 120)


if __name__ == "__main__":
    unittest.main()
