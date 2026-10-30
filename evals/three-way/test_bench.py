"""Offline behavioral tests for measurement rejection and source fixtures."""
import unittest
import bench


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


if __name__ == "__main__":
    unittest.main()
