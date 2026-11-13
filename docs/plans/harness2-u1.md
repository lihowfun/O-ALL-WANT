# Harness2 U1: evidence-bound evaluation accounting

Date: 2026-11-13. Base: release-polish 5af21f6. The owner explicitly asked to
implement the evaluation absorption now, overriding the earlier post-release
ordering for this U1 work. This does not authorize a new model experiment,
change FIXCHECK, merge/release, pending CI routing or rejected cache relocation.

## Scope and integration

Implement a Python 3.10+ stdlib, operator-invoked `scripts/eval_ledger.py` plus a format-specific `scripts/eval_ledger_fixcheck.py` with
JSON and Markdown reports, a read-only FIXCHECK adapter, and an explicit bridge
to existing `eval_stats.compare` / `eval_stats.cost`. It is a checkout evaluation
tool, like eval_stats; no new startup rule, skill, router, dependency or installer
payload. No third scorer, adoption judgment, catalog tasting/absorption receipt,
model execution, repair/append into experiment ledgers, or automatic promotion.

Harness2 source: 6868817518876de8fd170c6a8354daca273b6191, ledger/report/runmark
concepts. Implement independently; upstream selection/reflection costs are not
fully inside its ledger. OAW's complete-stage requirement is an addition, not a
claim about upstream. U2 model-readable guidance and U3 retrieval remain later
validated candidates. Existing improvement.py cost semantics remain unchanged.

## Normalized immutable input bundle (schema 1)

A JSON bundle contains `manifest`, `manifest_sha256`, `sources`, `records`, and
`outcomes`. Canonical JSON SHA-256 (UTF-8, sort_keys, compact separators,
allow_nan=False) binds manifest and source-record identities. Strict JSON rejects
duplicate keys and NaN/Infinity. Malformed records are errors, not dropped rows.

Manifest: study_id, protocol_sha256, runs. Each planned run has unique id,
task_id, input_sha256, arm, harness_sha256, condition (model/effort/host/
host_version/environment identity), positive repeat and split (development,
pilot, test). Identity for a task/arm/condition must stay consistent. Plan keys
cannot duplicate. Explicit runs avoid generating an unwanted factorial design.
Optional grading_contract binds metric_id, metric_sha256 (rubric/scale/unit),
judge_sha256 and source_kind (mechanical/independent_model/self_report/unknown).
Each scored outcome records the same four fields; null/missing contract may be
reported as legacy/incomplete but never compared. The selected comparison must
match the full manifest grading contract across every arm/task/repeat. Only
mechanical or independent_model grading is eligible; unknown/self grading is
refused. This is declared source provenance, not proof of independence.

Sources: unique IDs with project-relative path and SHA-256, verified against an
explicit evidence root (default bundle parent); confine resolved paths and never
execute input code. Snapshot all source bytes once, verify they stayed unchanged
before returning; generated reports omit source paths and raw file contents. Operator-supplied
IDs and reasons are retained; review those before publishing. A report is a snapshot, not a guarantee that inputs never change later.

Records: unique id; manifest_sha256; run_id or null (study-wide), stage, positive
attempt, status, reason, source IDs, meter (host/independent/runner/self_report),
complete flag, subagents_included flag, unique charge_ids, metrics, produces and
selects, and judges (graded output SHA-256, required for completed grading). Metrics: logical_tokens and noncache_tokens (nonnegative exact integers
or null), cost_usd and elapsed_seconds (finite nonnegative numbers or null).
Null means unknown, never zero. noncache <= logical when both available.
Stages answer/proposal/probe/compose/selection/reflection/retry/grading belong
to runs; authoring/review/controller belong to study. Every planned run requires
an explicit record or an honest missing slot for every run-stage. Every study
stage likewise remains visible. Applicable stages can have multiple attempts;
not_applicable requires a reason and cannot coexist with work in that slot.
Statuses: completed, failed, interrupted, not_run, unmeasured, not_applicable.
Completed answers need positive logical usage; mechanical stages may consume zero tokens; quota not_run may have observed
zero, but cannot produce an outcome. Only observed metering with complete source
and subagent coverage can make a measured metric complete; self-report cannot.
Failed attempt costs count. Unknown/interrupted sources make totals lower bounds.
Charge IDs describe disjoint billed scopes (including covered children); any
intersection rejects double counting. Declared coverage is not authentication:
the tool verifies bytes/contract, not meter independence or absence of omitted work.

produces: optional output SHA-256. selects: optional output SHA-256, allowed
only on a completed selection record and must refer to a completed produced
output of the SAME run. A run with selection has exactly one selection result.
Outcomes: at most one per planned run, with manifest hash, status completed or
scored, output_sha256, source IDs, score (finite or null), grading_contract (or null), and judge_sha256 (or
null). Scored needs score, judge and the final delivered artifact; selection
chooses that same artifact. Without selection, it must be a completed produced
artifact. Grading failures stay unscored/missing with reasons; no fabricated 0.
The adapter may expose legacy outcomes lacking artifact identity as incomplete
coverage; these are ineligible for statistical export, never silently repaired.

## Aggregation and existing-comparator bridge

Report planned/started/completed/scored/not-run/interrupted/missing counts and
per-run reasons. Preserve every planned run; missing/scoring failure != 0 score.
Per-stage and three cost scopes: execution/improvement (all run stages excluding
grading), grading, study overhead. Whole-study spending includes all scopes.
For each metric report observed subtotal, complete boolean, unknown/missing
count and total=null unless complete. Also give per-condition/arm run-stage
costs; shared study costs remain shared, never arbitrarily amortized into arms.
Do not add elapsed durations and call the sum wall-clock time: it is summed
stage duration; unknown overlap remains a limitation.

`compare BUNDLE --baseline ARM --candidate ARM --condition ID --margin M
[--floor-sd SD]` uses only paired test tasks, equal repeat sets and matching
model/host/environment/input identity AND the complete metric/judge contract.
Mixed judge hashes, metric hashes/units/IDs, grading-source types, missing
contracts and self-report graders are errors for comparison. One judge/metric
comparison is labeled as such; it is never eval_stats.agree(), the D32
cross-family quality verdict or automatic catalog judgment. Refuse missing/unscored outcomes,
non-independent/self-reported evidence or incomplete execution token coverage;
never export only the convenient scored subset. Delegate score and execution
cost arrays to eval_stats, include source hashes and exact task/repeat set. Do
not label these as whole-study efficiency, significance beyond eval_stats or an
adoption verdict. Shared-library/stream grouping is unsupported and must be
rejected by an explicit manifest analysis_unit other than independent_task.
Existing lower-is-better and zero-variance floor options are preserved.

## FIXCHECK adapter (read-only; no recalculation of its decisions)

`fixcheck --manifest FILE --state DIR [--format json|markdown]` uses the frozen
manifest and BINDING, starts/attempts/counted rows for both cells, plus Claude's
start/end reservation ledger. Check candidate/runner/task identities and grade
structure, duplicates, session/row token agreement, one valid counted answer,
counted rows equal matching valid attempts. Verify record prefixes and files do
not change during snapshot; fail if another writer races. Do not import/execute
the external runner or grader. Do not run thresholds.py or change its verdict.

Build all 24 planned rows even at 12/24 completion. Account attempts, not rows
plus attempts; preserve quota 0 as not_run. For a started attempt with no result,
report unknown cost and separately report outstanding reserve (NOT spent).
For finished Claude sessions reconcile end entries and reported session totals;
reject contradictions/duplicate ledger events. For Codex row totals, expose
runner-reported observed usage; source-level completeness cannot be inferred
from a nonzero count. Thus the historical import retains incomplete coverage.
Missing engineering/reviewer/grading costs remain unknown; never whole-study
cost=6,802,657. Recovered passing-1-b1 retains428,278 and its recovery metadata;
never read a truncated rollout and choose its smaller number. No transcript or
private path appears in public report; no source file is rewritten. Sources are
hashed input files plus per-record canonical hashes, with a clear scope caveat.

## CLI behavior and validation

`report BUNDLE [--evidence-root DIR] [--format json|markdown]` validates/summarizes;
`compare` as above; `fixcheck` imports/summarizes real evidence. stdout only, no
implicit file writes. Exit0=valid complete accounting, exit2=valid incomplete,
exit1=invalid; numeric quality classes are data, not an exit0 benefit claim.
Repeated reads of identical inputs produce identical outputs (no current time).

Tests must exercise: missing denominators, failed/retried expense, quota0,
unscored versus scored0, absent cost vs0, duplicate/conflicting IDs or charges,
parent/child overlap, source/hash/manifest mismatch and path escape, changed
source snapshot, selection artifact/judge linkage, mixed/missing/self-grader and metric contracts, unknown/shared overhead,
recovered428278 vs truncated397636, finite nonnegative metrics and booleans,
paired comparator export refusing dropped tasks/unmatched repeats/pilot/stream
units, exact existing comparator output, JSON/Markdown CLI exit behavior, and a
synthetic FIXCHECK plus read-only actual Codex12/Claudequota import.

Run focused tests, `sync_examples.py --write` (expected no payload change), then
full harness gate. Add new test module to required inventory. One fresh-context
design review BEFORE code and one code review after; resolve concrete findings.
Record validation, limits, and the owner's sequencing override in product docs,
records progress and local CC handoff. No frozen file edits. Update README and
ROADMAP with the optional evaluation command and validation state.

Context files for review: scripts/eval_stats.py, scripts/improvement.py,
scripts/harness_check.py, docs/EVAL_PROTOCOL.md, docs/SELF_IMPROVEMENT.md;
records/intake-2026-11-13-harness2/EVALUATION.md and records/v2.0.1-experiments/
FIXCHECK/{MANIFEST.json,fixcheck.py,FIXCHECK.md,RECOVERY.md} on records worktree.

Design review round 1: 3/4 PASS; criterion 3 failed because metric/judge identity and grading-source independence were underspecified. The contract above adds explicit binding and rejection fixtures. Original reviewer confirmed criterion 3 closed; final design review 4/4 PASS before implementation.
