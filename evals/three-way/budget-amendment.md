# Budget-only amendment, 2026-10-30

The first no-tool CLI probe reported 14,527 logical input/output tokens. Actual
tool-using review turns reported roughly 79k–164k cumulative input tokens each.
The original 2.5m token cap stopped dispatch as designed, with two already active
calls completing and an observed total of 2,646,161. No candidate quality report
or grade was inspected to choose this amendment; only statuses and usage were
examined. This is a budget calibration limitation of the preregistration.

Increase the total cohort input/output cap to **12m**. Keep the original 100k
output cap, 3000-second wall-time origin, per-call timeout, concurrency, tasks,
repeats, source identities, exact prompts, rubric and grading rules unchanged.
Keep every completed original call and its cost; dispatch only calls that never
started. No failed/interrupted model call may be retried. Continuation is not a
fresh repeat. No fixed-original-budget completion claim is permitted.

`continue_budget.py` imports the unchanged registered runner, verifies existing
prompt identity, preserves existing worker inputs and records hashes of every
pre-amendment raw file. An ambiguous partial call stops continuation. Only empty
directories created before the original budget check may be removed, without
recursive deletion. The old execution/runtime summaries are copied before the
continued summaries are written. The original protocol remains intact.

An experiment requiring a fully fixed prospective total budget must rerun under
a new registration; this pilot is descriptive and explicitly includes this
cost-driven protocol amendment.
