# Local Codex / EGM workflow experiment

This is a frozen experiment design, not a result. The contract was frozen before any independent trial output. The user has
now authorized Codex independent subagents; collection is in progress, and
there is no acceptance result yet. Claude
CLI and its F1/F2/F3 phases are not used here; model calls use Codex quota.

## The comparison

| Arm | Treatment |
|---|---|
| A | Native project review, with the same task, source access and tool budget |
| B | A plus the complete official EGM review workflow and fresh Goldfish contexts |
| C | B plus OAW minimal project guidance/evidence, installed from the current frozen source |

Three independent cases, three repeats each, 27 primary reviews. Orders tests
atomicity, idempotency, current decisions and retention. Events tests state
ordering, logging constraints and actionable plans. Clean tests legitimate
exceptions, superseded decisions and false alarms. C's historical note on the
clean case must be checked against current sources; it is not privileged truth.

Every arm can read the same current ADRs. The reviewer workspaces do not contain
the rubric. A may use fresh independent reviewers too, under the same cap.
All agents inherit one model/effort configuration. Record exposed metadata;
do not invent a provider version or claim a Sol/Opus-specific benchmark when
the execution API does not expose that identity.

The selected official path is `Subflow: Uninterrupted Full Flow`, with nine
direct fresh reviewers across five stages (1 + 1 + 3 + 1 + 3), and parent
synthesis. This is a bounded read-only pass, not iterative remediation or a
certification of EGM's review-loop convergence. Stage 8 may read its own trial's
earlier artifacts. Fresh conversation context does not provide filesystem
isolation. All arms have the same allowed reviewer cap; realized reviewer counts
may differ, so any observed gain would not isolate workflow from extra compute.

## Freeze before seeing results

[spec.json](spec.json) includes case hashes, rubric, resource bounds, grading
and decision rules; [spec.sha256](spec.sha256) identifies the exact contract.
Preparation and OAW source hashes are included. A changed source or rubric
requires a new registration and fresh workspaces, preserving the earlier run.

```sh
python3 evals/egm-local/prepare.py --verify
python3 evals/egm-local/prepare.py --out /outside/the/repo/fresh-run
python3 -m unittest tests.test_egm_local
```

These commands never dispatch agents, call models, or run subprocesses.
Preparation installs real OAW files only in C and adds source-linked notes.
It refuses an existing output directory. Keep raw execution evidence outside
the repository; publish only reviewed fixture-derived reports and aggregates.

## Grading and merge condition

An independent fresh grader sees shuffled anonymous findings, source and the
fixed rubric. Grade concrete defects against evidence; questions and conditional
risks are separate. Additional valid findings are allowed; non-gold does not
automatically mean wrong. No regex match earns a quality verdict.

Both B vs A and C vs B must show no per-defect detection-count regression,
no reduction in total grounded planted findings and no increase in unsupported
concrete claims per case. All planned reviews/stages must complete. Invalid,
missing or unverified runs are inconclusive, never a cheaper success. If C wins,
run a plain-index control and C-without-memory ablation before attributing that
gain to OAW indexing. Preserve failures and report the full result.

Passing demonstrates observed non-regression on this fixed small suite, not
statistical equivalence or general superiority. Reading EGM workflow files
through Codex agents also does not certify native plugin auto-discovery, Claude
compatibility or OS-enforced isolation. These limits stay explicit even if the
quality gate passes. Main must not be merged on synthetic tests alone.

`measure.py` applies the registered arithmetic to completed, independently
graded/adjudicated evidence. It rejects missing trials, invalid stages, input
mutation, a weak native baseline, unresolved grading disagreements and malformed
grades. It checks each planted defect and each case's unsupported-claim count
separately; a higher total cannot hide a critical regression. Its synthetic unit
tests validate bookkeeping only. They are not model results. The arithmetic
implementation was added during collection, before blind grading; the acceptance
rules remain those already frozen in the specification. Reviewers do not read it.

```sh
python3 evals/egm-local/measure.py adjudicated-evidence.json --out aggregate.json
```

EGM source: [full pinned commit](https://github.com/google/elephant-goldfish-model/tree/f0ba151b252c9abf1318d9fe857a43265d06de89),
manifest **0.1.0**, Apache-2.0. Use the complete official package. No skill text,
personas or runtime are vendored in this directory.
