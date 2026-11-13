# Evaluation accounting (U1)

`eval_ledger.py` makes the evidence and missing costs behind a harness comparison
visible. Run it from an OAW source checkout with Python 3.10+. It does not run a
model, grade an answer, change experiment files, or approve a skill. It is not
installed into ordinary projects and adds no startup instructions.

This is an independent implementation informed by the ledger, report and runmark
concepts in [Harness2 at 6868817](https://github.com/google-research/harness2/tree/6868817518876de8fd170c6a8354daca273b6191).
No upstream runtime is bundled. OAW additionally requires accounting for
selection, reflection and shared study work: upstream's ledger alone does not
establish complete study cost. This engineering change does not establish a
model-quality or token-saving benefit and is not a catalog absorption receipt.
The design and review history are in [the U1 plan](plans/harness2-u1.md).

## Commands

```bash
python3 scripts/eval_ledger.py report bundle.json --format markdown
python3 scripts/eval_ledger.py compare bundle.json \
  --baseline base --candidate candidate --condition c \
  --margin 0.1 --floor-sd 0.05 --format json
python3 scripts/eval_ledger.py fixcheck --manifest /path/to/FIXCHECK/MANIFEST.json \
  --state /path/to/existing/state --format markdown
```

The first two commands resolve source paths relative to the bundle's directory;
use `--evidence-root DIR` to specify another root. Only explicit relative paths
inside that root are allowed, including after symlink resolution. Reports go to
stdout. Redirect them explicitly if a saved report is wanted. Exit codes:

| Code | Meaning |
|---|---|
| 0 | Valid input, complete declared accounting and scored artifact identities |
| 2 | Valid input, incomplete accounting or outcomes; report still usable |
| 1 | Invalid, conflicting or unreadable input; do not use a partial result |

An exit code is never a benefit/adoption verdict. A `compare` report may exit 2
because shared costs are unknown even when its narrower execution comparison is
valid. Its scope explicitly excludes grading and shared engineering costs.

## Try a synthetic example

The following uses the regression fixture to create a complete, explicitly
synthetic bundle in a new temporary directory. These values are not benchmarks.
It invokes no model and modifies no experiment state.

```bash
python3 - <<'PY'
from pathlib import Path
import sys, tempfile
sys.path.insert(0, 'tests')
from test_eval_ledger import fixture, write_bundle
root = Path(tempfile.mkdtemp(prefix='oaw-ledger-example-'))
print(write_bundle(root, fixture(root)))
PY
```

Use the printed path in place of `bundle.json` above. The fixture has two tasks,
`base` and `candidate` arms, condition `c`, and one repeat. Execution logical
tokens total 300, grading 20, whole-study 320. The floor in the example is a
fixture parameter; predeclare a justified margin and floor for a real study.
Removing one task's evidence must leave four planned runs with missing coverage,
not create a three-run success rate. Deleting an outcome score must leave an
unscored outcome, not a zero score.

## Bundle contract, schema 1

Top-level fields are `manifest`, `manifest_sha256`, `sources`, `records`,
`outcomes`. Strict JSON rejects duplicate keys and non-finite numbers. Hashes
are lowercase SHA-256. Canonical JSON means UTF-8, sorted keys, compact
separators, `ensure_ascii=False`, `allow_nan=False`.

The **manifest** has `schema_version: 1`, `study_id`, `protocol_sha256`,
`analysis_unit` (`independent_task`, `stream`, `diagnostic`), an optional
`grading_contract`, and every planned `run`. Each run declares:

| Field | Meaning |
|---|---|
| `id`, `task_id`, `arm`, `repeat` | Unique run identity; positive integer repeat |
| `input_sha256`, `harness_sha256` | Frozen task input and arm identity |
| `split` | `development`, `pilot` or `test` |
| `condition` | `id`, `model`, `effort`, `host`, `host_version`, `environment_sha256` |

The same task, arm or condition ID cannot stand for conflicting identities.
`manifest_sha256` hashes the canonical manifest. Each record and outcome repeats
that binding. A grading contract declares `metric_id`, `metric_sha256` (including
rubric, scale and unit), `judge_sha256`, and `source_kind` (`mechanical`,
`independent_model`, `self_report`, `unknown`). Fingerprints must represent the
actual frozen protocol, not arbitrary labels reused after changing a grader.

**Sources** map unique IDs to `{ "path": "relative/file", "sha256": "…" }`.
The loader verifies bytes and checks again before returning. It never executes
source files. This is a snapshot check, not a transactional lock on other writers.

Every **record** includes:

| Fields | Contract |
|---|---|
| `id`, `manifest_sha256`, `run_id`, `stage`, `attempt` | Unique positive attempt per run/stage; null run for shared work |
| `status`, `reason` | Status below; nonempty reason for anything except completed |
| `sources` | Nonempty list of source IDs |
| `meter` | `host`, `independent`, `runner`, or `self_report` |
| `complete`, `subagents_included` | Boolean declarations of source and child coverage |
| `charge_ids` | Disjoint billed scope IDs; include covered children to detect overlap |
| `metrics` | All four metrics below, even when null |
| `produces`, `selects`, `judges` | Optional artifact hashes, with linkage rules below |

Run stages: `answer`, `proposal`, `probe`, `compose`, `selection`, `reflection`,
`retry`, `grading`. Shared stages: `authoring`, `review`, `controller`. Missing
stages stay unknown. Use `not_applicable` with a reason and all-zero metrics only
when no work occurred; it cannot coexist with work in the same stage. Other
statuses are `completed`, `failed`, `interrupted`, `not_run`, `unmeasured`.
Retries and failed attempts retain their costs. Completed answers require positive
logical tokens; a mechanical grader may use zero tokens.

Metrics are `logical_tokens`, `noncache_tokens` (exact nonnegative integers),
`cost_usd`, `elapsed_seconds` (finite nonnegative numbers). Null means unknown.
Noncache cannot exceed logical tokens. No prices or elapsed times are inferred.
Summed durations are stage durations, not experiment wall-clock time. Any
positive expense requires a charge ID. Parent and child records must declare
overlapping scope IDs if they contain the same spending; the reader cannot
reconstruct undeclared billing relationships.

Only completed answer/probe/compose records may `produce` an artifact, whose
hash must match a referenced source. A completed selection must `select` one
produced artifact from the same run. Completed grading must `judge` an artifact. A scored outcome cannot declare
grading not applicable; without complete matching grading evidence, the report
stays incomplete.
At most one final **outcome** exists per run. It declares `run_id`,
`manifest_sha256`, `status` (`completed` or `scored`), `output_sha256`, `sources`,
`score`, `judge_sha256`, and `grading_contract`. Its delivered artifact must be
produced by that run and agree with any selection and corresponding grading.
Unscored outcomes have null score and a reason. Scored zero is a real score.
Legacy outcomes may declare null artifact with `identity_note`; they are
incomplete and cannot enter comparisons.

## Reading and comparing reports

Reports retain planned/started/completed/scored/missing counts, per-run reasons,
per-stage costs, execution costs per condition/arm, grading, shared overhead and
whole-study totals. Each metric has `observed`, `complete`, `unknown_entries`
and `total`. A total is null unless all required entries are measured. An
observed subtotal includes declared observations even if completeness or
independence is unverified; it is not a certified bill or a whole-study total.

Comparison requires both arms' entire paired test set with identical repeat
sets, the same condition and frozen task identities, complete execution logical
usage, delivered artifacts, and matching metric/judge contracts. It refuses
pilot/development, stream/diagnostic, missing outcomes, self/unknown grading,
missing independent completed grading evidence, and incomplete execution tokens.
One-repeat tasks require explicit `--floor-sd`; the existing
[eval_stats protocol](EVAL_PROTOCOL.md) defines the quality and cost mathematics.
`--lower-is-better` preserves that protocol's direction option. This module
passes paired arrays to `eval_stats.compare` and `eval_stats.cost` unchanged.
It does not call `agree` or produce the cross-family quality/adoption judgment.

Verified hashes prove byte identity, not grader independence, task independence,
truthful coverage flags or absence of omitted work. Those remain review duties.
The generic report omits source paths and raw files, but keeps operator-provided
IDs/reasons: review them before publishing. Do not place secrets or private
locations in those fields.

## Historical FIXCHECK import

The adapter verifies the manifest/state binding, frozen source and unit-bank
hashes (including each unit using the historical H1 serialization), run identity,
launch effort, session sums, mechanical grade consistency,
counted-row/attempt equality, and Claude reservation/end events. It does not
regrade, execute the runner, rerun tasks, run regression thresholds, repair rows,
or modify the frozen study. A concurrent input change makes the import fail.

All planned cells remain visible. Quota zero is a not-run attempt; outstanding
reservation is not spending. Recovered totals remain the serialized totals,
including missing elapsed metadata. Started attempts lacking a serialized result
are shown as interrupted/possibly still running, not assumed free or complete.
The adapter does not replay native traces, so historical completeness stays
unverified. Legacy artifact and grading-contract gaps prevent statistical export.
See [U1 validation](validation/harness2-u1.md) for the measured import and limits.
