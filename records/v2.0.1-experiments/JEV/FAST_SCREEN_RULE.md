# Fast screen, rule v0 (written 2026-11-14 before the back-test; owner direction D50)

Purpose: say YES (absorb) or NO (do not absorb now) about a food quickly. There is no "undetermined"
outcome: whatever is not a clear YES is NO, with one line of reason and the condition that reopens it.

## Inputs

- 3 tasks from the food's home turf (the kind of task the food claims to help with), each with a
  checklist of concrete items an answer should contain or do. One fresh-context run per task and arm.
- Arms: native (no food) first; the food arm only if the native arm leaves room.
- A judge labels every checklist item of every answer `yes`, `no` or `unknown`. A `yes` needs a passage
  quoted character for character from the answer; code checks the quote. A `yes` whose quote is not in
  the answer becomes `unknown`. `unknown` never counts as `yes`.
- Logical tokens of each run (cache reads and subagents included).

## Steps (stop at the first decision)

| Step | Check | Decision |
|---|---|---|
| A. Static | Licence, executes code, runtime dependency, overlap with an existing skill (existing catalogue checks) | Blocked: NO. Needs the owner (tier C): ask the owner; nothing else runs |
| B. Native | Native met at least 90% of all checklist items over the 3 tasks | NO: native already does it. Reopen with a task that native fails |
| C. Food | `gained` = items the food met that native did not; `lost` = items native met that the food did not (an `unknown` on the food side counts as lost); `ratio` = food tokens / native tokens over the 3 tasks | YES if `gained` ≥ 2 and `lost` = 0 and `ratio` ≤ 1.5. Otherwise NO, with the failing condition as the reason |
| Budget | The screen has used more than 2,000,000 logical tokens of one model family, or 30 minutes of run time | NO: too expensive to screen. Reopen with smaller tasks |

## What YES and NO mean

- YES: absorbed as optional (available on explicit call). Becoming a default still needs the full
  measurement rules (`docs/EVAL_PROTOCOL.md`); a YES here is not evidence for that.
- NO: not absorbed now. It is not a verdict that the food is useless. The record keeps the reason and
  the reopening condition.

## Applying the rule to a past experiment (back-test only)

A past experiment did not use this design. To back-test, use its own recorded numbers:

- Step B: NO if the native arm's recorded quality is at least 90% of the maximum of that experiment's
  quality measure (per host; if hosts differ, report each).
- Step C: `gained` and `lost` from the recorded per-item or per-task results if they exist; if only
  aggregate scores exist, YES needs the food better than native on every host and grader recorded, no
  recorded item or task where it is worse, and the recorded token ratio ≤ 1.5; otherwise NO.
- If the records do not contain a number the rule needs, the back-test result for that experiment is
  "cannot be back-tested", with the missing number named. Do not estimate.
