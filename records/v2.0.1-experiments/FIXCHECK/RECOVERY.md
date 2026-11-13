# FIXCHECK infrastructure recovery — 2026-11-13

Status: offline recovery completed and appended once after 4/4 independent review.
The proposal was recorded before offline grading of the interrupted task. No candidate,
preregistration, frozen source, threshold or budget changes. No new model answer.

## What happened

The local disk reached ENOSPC during Codex B `passing-1-b1/O/a1`. Both CLI streams
end in `turn.completed`; both final answers and the final candidate source exist.
The second stream also reports transcript persistence failure, and its copied
rollout ends in a partial JSON line. The runner then failed while copying the
base into the grading tree, before hidden tests ran and before the attempt row
was serialized. Five earlier counted rows are unchanged.

The complete parent streams report 165,952 and 262,326 logical tokens. The second
rollout's last complete token record is only 231,684. Using it would omit 30,642
tokens. There are no child sessions in these two streams or their session home.
This exception must stay visible: the frozen runner normally prefers a nonzero
rollout count even when a later transcript write fails.

## Storage repair

Relocate only the independent immutable FIXCHECK tool copy to a private directory
on the existing storage mount, after comparing each full tree digest with the
frozen manifest. Keep state, workspaces and model-visible bind paths unchanged.
Recheck the complete manifest after linking the relocated copy. Original H1
files and other users' caches are untouched. Record this backing-storage change;
wall-clock comparisons have an additional limitation.

## Recovery method to review

1. Preserve all original streams, truncated rollouts, source files, start record,
   and failed grading artifacts with hashes. No model calls, source edits or
   second answer. The serialized start remains attempt 1.
2. Verify both complete streams, their root model/provider and final replies;
   verify there are exactly the two known root sessions and no child activity.
   Recompute usage from complete `turn.completed` parent totals, including cache
   inputs; independently reconcile session 1 with its complete rollout. Use the
   parent stream for session 2 because the rollout is demonstrably truncated.
3. Reconstruct only fields supported by evidence. Mark the row `recovery` with
   explicit provenance for missing fields. Persist exit as null: reaching `grade()`
   proves that `not_run()` accepted both sessions, but does not distinguish exit 0
   from an accepted timeout. Do not invent the process-exit measurement.
   Exact wall time and intermediate memory snapshots are unavailable: use null
   or explicitly labeled reconstructed fields, never invented measurements.
4. Grade the preserved final source using the exact frozen `grade()` and unit.
   Save a proposed row separately. Verify original raw/source hashes unchanged.
   Offline-validate provenance, functions/items/recall and token sums with the
   frozen threshold functions. Replay unaffected completed rows to check the
   reconstruction's usage and metadata parsing; do not regrade those answers.
5. An independent reviewer must confirm recovery integrity before appending the
   proposed row. Under the original row lock, reject conflicts by both root and
   (cell, unit, arm); an exact canonical existing row is a no-op. Append the
   attempt first, fsync, then the counted row and fsync. If interrupted between
   the two, the unchanged runner recover() restores the counted row. Before
   append, recheck the row-bound input-index hash, every non-ledger input and
   each original ledger prefix; only this exact proposed row may be added. Re-entry
   must check both ledgers and never create a duplicate. Then the unchanged
   guarded adapter can resume the same B class, skipping all counted answers.

## Claims and limits

This is an infrastructure/accounting recovery exception, disclosed in the final
result, not a quiet change to the preregistration. Preserve both the stale
rollout count and the complete-stream count. Numerical reporting uses the full
observed usage; no correction may depend on whether a threshold passes. No
unqualified claim of an unchanged runner/accounting path for this task.

If complete usage, identity, source integrity or absence of child sessions cannot
be established, leave the task incomplete and do not manufacture a counted row.
Do not redraw the completed answer to conceal missing evidence.

Review criteria: (1) no redraw or frozen-content change; (2) complete and honest
usage/provenance including truncation; (3) mechanical grading and idempotent
ledger recovery; (4) missing evidence remains explicit and blocks unsupported
claims. This document does not authorize merge, release, a budget increase or
another experiment.

Initial independent review found that reaching grade does not prove exit 0
and a lock alone does not make append idempotent. The method above was corrected
before implementation; closure review is pending. No lost measurement is filled
with a guessed value.

Design closure: the original reviewer confirmed both corrections. Implementation
review then found that append must revalidate inputs after preparation; this guard
and source/prefix/extra-row/index tampering probes were added before append.
Preparation source is preserved at records commit `c206388`; the proposed row
keeps that source hash. Append uses the subsequently reviewed utility hash, so
no regrading is needed to fix ledger guards. Six prior sessions replayed **16**
usage/metadata fields exactly; an earlier progress note incorrectly called it 18.

Implementation validation so far: eight disposable integrity probes pass, including
added files and tampered source/index/ledger-prefix rejection. The independent
reviewer reconstructed all 17 saved grade fields from XML/code/tails without
running another grade; frozen validate_new/validate_grade/score accept the
proposed row. Truncated-rollout skill/evidence/blocked metadata is explicitly
labeled as observed lower bounds; only the complete parent stream supports full
usage. Ledger append remains pending the original reviewer's closure check.

Final independent closure: **4/4 PASS**, bound to the exact script and proposed
row hashes in [RECOVERY_REVIEW.json](RECOVERY_REVIEW.json). The reviewer reran all
eight disposable probes and the frozen validators; no model or second grade.
Final records repository gate: **9/9, 167 tests, 0 skips**, Linux/Python 3.10;
22 pre-existing wiki soft warnings remain. This gate validates the records
checkout; it is separate from the product's 685-test release-polish gate.

Execution: approved append completed under the original locks. Both ledgers now
hold six distinct roots and 1,545,078 logical Codex tokens; the recovered task is
still original attempt 1, with 428,278 tokens. Earlier five rows remain byte-
identical prefixes. No additional model calls or source changes occurred during
recovery. The run can resume remaining B tasks through the unchanged adapter.
