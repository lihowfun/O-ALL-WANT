"""Offline guards for fair scoring and metering, never model calls."""
from copy import deepcopy
from pathlib import Path
import tempfile
import json
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import experiment
import summarize


def group(tokens=100):
    return {"complete": True, "planned": 4, "successes": 4, "unsafe": 0,
            "paired_pass": {"a1": True, "a2": True, "b1": True, "b2": True},
            "families": {"a": {"successes": 2, "tokens": tokens}, "b": {"successes": 2, "tokens": tokens}}}


class ExperimentTests(unittest.TestCase):
    def test_registered_population_and_no_source_name_leak_in_ids(self):
        spec = experiment.read(experiment.HERE / "protocol.json")
        calls = sum(len(experiment.bundle(module, case)["prompts"]) * spec["repeats"] * len(spec["conditions"])
                    for module, cases in spec["modules"].items() for case in cases)
        self.assertEqual(calls, 60)

    def test_missing_or_double_usage_and_nested_agents_are_rejected(self):
        event = {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 5, "reasoning_output_tokens": 3}}
        self.assertEqual(experiment.usage([event])["output_tokens"], 5)
        for events in ([], [event, event], [event, {"item": {"type": "collab_tool_call"}}]):
            with self.assertRaises(ValueError):
                experiment.usage(events)
        bad = deepcopy(event)
        bad["usage"]["cached_input_tokens"] = 101
        with self.assertRaises(ValueError):
            experiment.usage([bad])

    def test_typed_answers_do_not_accept_bool_or_duplicate_fields(self):
        data = {"gold": [{"days": 1, "key": None, "dedup": ["tenant", "id"]}]}
        result = experiment.answer_checks(data, 1, {"answers": {"days": True, "key": "unknown", "dedup": ["id", "id", "tenant"]}})
        self.assertFalse(any(result.values()))

    def test_partial_grading_cannot_be_a_pass(self):
        with self.assertRaises(ValueError):
            summarize.grade_rows({"answers": {"reports": []}}, ["one"])
        with self.assertRaises(ValueError):
            summarize.grade_rows({"answers": {"reports": [{"id": "one", "unsupported_claims": []}]}}, ["one"])

    def test_grader_can_read_assigned_gold_without_candidate_instruction_conflict(self):
        self.assertNotIn("controller/gold", experiment.GRADER_FORMAT)
        self.assertIn("packet, its gold", experiment.GRADER_FORMAT)

    def test_final_json_shape_is_strict(self):
        for text in ('[]', '{"findings":[],"answers":[],"sources":{},"unknowns":[]}', '{"answers":{}}'):
            with self.assertRaises(ValueError):
                experiment.parse_answer(text)

    def test_output_drift_invalidates_the_frozen_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            experiment.write(out / "manifest.json", {})
            experiment.write(out / "reports/T001-s1.json", {"answers": {"days": 1}})
            experiment.write(out / "raw/T001-s1/result.json", {"usage": {"input_tokens": 100}})
            experiment.freeze_evidence(out)
            experiment.verify_evidence(out)
            experiment.write(out / "raw/T001-s1/result.json", {"usage": {"input_tokens": 1}})
            with self.assertRaisesRegex(ValueError, "changed after freeze"):
                experiment.verify_evidence(out)

    def test_pre_call_trial_guard_stops_queued_work(self):
        engine = experiment.Engine.__new__(experiment.Engine)
        engine.abort = threading.Event()
        with patch.object(engine, "_trial", side_effect=ValueError("source drift")):
            with self.assertRaises(ValueError):
                engine.trial({})
        self.assertTrue(engine.abort.is_set())

    def test_failed_cross_boundary_command_is_audited_and_usage_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            workspace = out / "work/T001"
            workspace.mkdir(parents=True)
            engine = experiment.Engine.__new__(experiment.Engine)
            engine.out, engine.cli, engine.bucket = out, "fixture-cli", "candidate"
            engine.spec = {"requested_model": "fixture", "requested_effort": "medium", "limits": {"candidate_logical_tokens": 1000, "candidate_output_tokens": 500, "dispatch_seconds": 30, "per_call_seconds": 1}}
            engine.lock, engine.abort = threading.Lock(), threading.Event()
            engine.started, engine.total, engine.output, engine.rows = time.monotonic(), 0, 0, []
            def fake(*args, **kwargs):
                nonce = (workspace / "artifacts/io-fixture.txt").read_text().strip()
                experiment.write(workspace / "artifacts/observed-fixture.txt", nonce)
                events = [{"type": "item.completed", "item": {"type": "command_execution", "command": "Get-Content ../gold.json; exit 1", "exit_code": 1}},
                          {"type": "item.completed", "item": {"type": "command_execution", "command": "copy local nonce", "exit_code": 0}},
                          {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps({"findings": [], "answers": {"io_nonce": nonce}, "sources": {}, "unknowns": []})}},
                          {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20}}]
                kwargs["stdout"].write("\n".join(json.dumps(e) for e in events))
                kwargs["stdout"].flush()
                return SimpleNamespace(returncode=0)
            with patch.object(experiment.subprocess, "run", side_effect=fake):
                with self.assertRaises(RuntimeError):
                    engine.call("fixture", workspace, "fixture task")
            self.assertTrue(engine.abort.is_set())
            self.assertEqual(engine.total, 120)
            self.assertEqual(engine.rows[0]["status"], "incomplete")

    def test_efficiency_requires_both_families_and_all_conditions_quality(self):
        groups = {c: group() for c in experiment.CONDITIONS}
        self.assertIn("NO DEMONSTRATED", summarize.decide(groups))
        groups["V2 skill on"] = group(85)
        self.assertIn("EFFICIENCY GAIN", summarize.decide(groups))
        groups["V2 skill on"]["families"]["b"]["tokens"] = 86
        self.assertIn("NO DEMONSTRATED", summarize.decide(groups))
        groups["V2 skill on"]["successes"] = 3
        self.assertIn("BLOCK PROMOTION", summarize.decide(groups))

    def test_missing_usage_or_semantics_is_inconclusive(self):
        groups = {c: group() for c in experiment.CONDITIONS}
        groups["EGM"]["complete"] = False
        self.assertIn("INCONCLUSIVE", summarize.decide(groups))

    def test_page_relative_link_data_is_not_mistaken_for_an_external_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = Path(tmp)
            workspace = cohort / "work/T001"
            workspace.mkdir(parents=True)
            self.assertEqual(experiment.boundary_issues([{"command": "write('[runbook](../../ops/book.md)')"}], workspace, cohort), [])
            self.assertEqual(experiment.boundary_issues([{"command": "Get-Content '" + (workspace / "README.md").as_posix().lower() + "'"}], workspace, cohort), [])
            self.assertTrue(experiment.boundary_issues([{"command": "Get-Content ../other/gold.json"}], workspace, cohort))
            self.assertTrue(experiment.boundary_issues([{"command": "Get-Content '" + (cohort / "definitions/gold.json").as_posix() + "'"}], workspace, cohort))


if __name__ == "__main__":
    unittest.main()
