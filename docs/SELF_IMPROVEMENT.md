# Evidence-driven self-improvement

This opt-in workflow turns a recurring failure or measurable cost into a reviewable candidate. It does not run a background agent, create a skill after each task, modify native memory, or apply a patch. A valid result can be no action or rejection.

Install with `python3 scripts/oaw.py init --target PROJECT --with-improve`. In an installed project, `improvement.py` uses that project as its base; `--base-dir PROJECT` selects it explicitly. All supplied artifact paths must be inside the project.

## Propose a concrete change

Write a focused git text diff and a falsifiable hypothesis. A target can be one file or a directory scope; paths in the diff must stay within it. Binary, rename-only and quoted-path diffs are not supported by this first version. Keep source files unchanged while collecting the proposal; run the candidate in an isolated branch/worktree.

Create a fixed evaluation JSON, for example:

```json
{
  "schema_version": 1,
  "id": "policy-ablation-v1",
  "cases": ["small-change", "session-handoff"],
  "repeats": 3,
  "assertions": ["task_correct", "source_correct"],
  "required_checks": ["regression_tests"],
  "minimum_improvement": 0.05,
  "maximum_resource_regression": 0.1
}
```

Use at least two distinct cases and three repeats per case. These minimums discourage single-run promotion; they do not establish statistical confidence. Define assertions and resource limits before observing candidate results. The repository also includes `evals/native-ablation/spec.json` as a task-set starting point.

```bash
python3 scripts/improvement.py propose --title "Remove duplicate startup rules" --hypothesis "Keep correctness while reducing context" --target AGENTS.md --patch runs/candidate.diff --evaluation runs/spec.json --snapshot BASE_COMMIT
```

The command returns a candidate ID and saves its diff, hypothesis, base snapshot and evaluation contract under `.oaw/improvements/`. It does not change the target.

## Capture matched runs

Run the same task bundle with and without the candidate. Hold model/effort, host/version, environment, base snapshot, permissions and grading method constant. Record actual native traces/artifacts, not an evaluator's unsupported recollection. Use separate baseline/candidate evidence files so one run cannot overwrite the other.

A run artifact is a JSON object with the following structure. Its cases list must contain every case/repeat from the fixed specification, not just the one example row below:

```json
{
  "schema_version": 1,
  "run_id": "unique-baseline-run",
  "variant": "baseline",
  "evaluation_id": "policy-ablation-v1",
  "base_snapshot": "BASE_COMMIT",
  "model": "gpt-6.1-sol",
  "effort": "medium",
  "host": "codex",
  "host_version": "YOUR_ACTUAL_VERSION",
  "environment": "YOUR_FIXED_ENVIRONMENT_AND_PERMISSION_PROFILE",
  "patch_sha256": null,
  "checks": {"regression_tests": true},
  "cases": [
    {
      "case_id": "small-change",
      "repeat": 1,
      "assertions": {"task_correct": true, "source_correct": true},
      "tokens": 1000,
      "latency_ms": 2000,
      "cost_usd": 0.01,
      "evidence": ["runs/baseline-small-change-1.jsonl"]
    }
  ]
}
```

For the candidate use variant `candidate`, a different run_id, and the proposal's patch SHA-256. Keep the matched metadata identical. Use `claude-opus-5-5` with the actual Claude host metadata for a separate model evaluation; do not mix models in an ablation pair. The numbers above demonstrate format only, not measured model results. Report unavailable metrics honestly instead of fabricating them; a run with missing required measurements cannot pass this contract.

## Compare and decide

```bash
python3 scripts/improvement.py compare ID --baseline runs/baseline.json --candidate runs/candidate.json
python3 scripts/improvement.py decide ID --decision accept --reason "Reviewed artifacts and the proposed tradeoff"
```

The comparator checks complete/matched cases and metadata, evidence availability, finite measurements, and patch identity. Any previously passing assertion that fails in the candidate is a quality regression even if the overall pass count is unchanged. Required candidate checks must pass. Resource regressions beyond the predeclared limit reject the candidate. Otherwise, increased complete-case passes or a sufficient efficiency gain makes it eligible; no demonstrated gain is inconclusive.

Acceptance requires an eligible comparison and an explicit reason. It revalidates artifact hashes, evidence and the comparison before recording the decision. A rejected candidate can be recorded with `--decision reject`. Decided proposals are immutable; create a new proposal for another attempt. Decisions never apply code, publish, merge or expand permission.

The tool validates operator-supplied measurements and hashed evidence. It cannot certify the truth of a trace, independence of graders, statistical significance, or future applicability. Files can change after a decision, so preserve the reviewed artifacts and hashes. A human/independent reviewer still evaluates the patch and provenance; applying it is a separate development action.

## Privacy and stopping conditions

Keep `.oaw/improvements/`, native transcripts and sensitive run artifacts out of public Git history. Use a project-approved artifact location and retention policy. Do not extract private user preferences into shared project knowledge. Promote a durable lesson only when its scope, sources and current applicability are clear.

If native-only behavior is already adequate, stop. If evidence is inconclusive, gather a targeted missing observation or reject the change; do not keep adding instructions until a grader agrees.
