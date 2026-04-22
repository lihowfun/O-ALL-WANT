---
name: harness-evaluator
description: "Independent subagent review of a completed change against explicit acceptance criteria. Spawns a fresh-context subagent so the review is not biased by the parent's reasoning."
triggers: ["review this change", "evaluate pr", "second pair of eyes", "is this ready to merge", "harness evaluator"]
requires:
  - .agents/memory.md (identifies which change is being evaluated)
optional_reads:
  - docs/archive/ (if the change references a plan document)
outputs:
  - .agents/memory.md entry with [REVIEW] tag and per-criterion verdict
---

# /harness-evaluator — Independent Subagent Review

> **Why this skill exists**: OAW's audit (2026-04-20) found that the same
> agent typically plans, executes, and evaluates a change. That's not real
> review — it's self-assessment. This skill forces a **fresh-context review
> pass** via a subagent spawn, so the reviewer has no inherited bias.
>
> Empirically verified: subagents get **zero parent-context inheritance**
> (measured in `docs/archive/Evaluator_Design_Decision_2026-04-20.md`).

## Parameters (inferred or asked)

| Param | Source | Notes |
|-------|--------|-------|
| CHANGE_SUMMARY | Last `[DECISION]` / `[EXPERIMENT]` / `[FEATURE]` entry in `.agents/memory.md`, OR user's explicit description | What was just done? |
| CHANGED_FILES | `git diff --name-only` between HEAD and base branch | Narrows the review surface |
| ACCEPTANCE_CRITERIA | The source skill's `outputs:` frontmatter OR the user's explicit "done when" list OR the plan doc's acceptance section | What "done" looks like |

## Rules

### Rule 1: Never skip the subagent spawn

If you are tempted to "just review this yourself" without spawning a
subagent, **stop**. That defeats the skill. The whole point is that your
context is too close to the work to evaluate it objectively.

### Rule 2: Give the subagent a narrow, testable prompt

Bad: "review this code"
Good: "verify that `scripts/harness_check.py` exits 0 on a clean repo,
reports each of 8 named checks, and exits non-zero if any check fails."

### Rule 3: Record the verdict even if positive

A pass is still evidence. Future reviewers of THIS review should be able to
see that the subagent said yes (and why).

## Steps

### Step 1: Identify the change and its acceptance criteria

Read the last 5 entries of `.agents/memory.md`. Locate the most recent
`[DECISION]`, `[EXPERIMENT]`, `[FEATURE]`, or `[FIX]` entry. That's the
change being evaluated.

Read the source skill for that change (if any). Its `outputs:` frontmatter
lists the acceptance criteria. If the change didn't use a skill, ask the
user for 3–5 "done when" bullet points.

### Step 2: Spawn a fresh-context subagent

Use the `Agent` tool with `subagent_type="general-purpose"` and a prompt
template like:

```
You are doing an independent review pass. You have no parent context.

CHANGE: <one-sentence description>

FILES AFFECTED: <list>

CRITERIA (each must be verifiable from the files alone):
1. <criterion 1>
2. <criterion 2>
3. <criterion 3>

TASK:
- Read the affected files.
- For each criterion, declare PASS or FAIL with concrete evidence
  (file path + line number or the exact text you relied on).
- If a criterion is ambiguous, declare UNCERTAIN and say what would
  make it verifiable.
- Keep the report under 250 words.

Do not suggest new features. Do not restate the change. Do not complement.
Just say whether each criterion is met.
```

### Step 3: Record the verdict to memory

Append to `.agents/memory.md`:

```
## [YYYY-MM-DD] [REVIEW] <change name> — <pass_count>/<total> criteria passed

Subagent verdict: <one-line summary, e.g. "3/3 PASS" or "2/3 PASS, 1 FAIL on criterion #2">

Failed criteria:
- <criterion # and subagent's evidence>, or "none"

Uncertain criteria:
- <criterion # and what's needed>, or "none"

Subagent notes: <anything else worth remembering>
```

### Step 4: Decide next action

- **All PASS** → the change can proceed to merge per the Merge Gate in
  `CLAUDE.md`.
- **Any FAIL** → do **not** merge. Raise the failing criteria in
  conversation with the user; do not silently continue.
- **Any UNCERTAIN** → treat as "needs more information". Either tighten the
  criterion or gather the missing evidence before deciding.

### Step 5: If the subagent only rubber-stamps, recalibrate

If the subagent always says PASS and never finds anything, one of these is
true:
1. The criteria are too loose (fix: narrow them).
2. The prompt primed for validation not review (fix: use the template in
   Step 2 verbatim).
3. The changes genuinely are all passing (fix: nothing, but be
   suspicious after 5+ consecutive all-PASS reviews).

Note suspicions in the review's "Subagent notes" line so patterns are
visible in `.agents/memory.md` history.

## Example Invocation

User: "Review the B-4 cross-check subcommand I just wrote."

Agent steps:
1. Find last `[FEATURE]` or `[DECISION]` in memory → "B-4: wiki_sync
   cross-check subcommand".
2. `git diff --name-only` → `scripts/wiki_sync.py`.
3. Criteria (inferred from amendment doc §2 B-4):
   - Subcommand `cross-check` exists in `--help` output.
   - Exit 0 when no page declares `ssot_mirrors`.
   - Exit 0 when all mirrored values agree.
   - Exit 1 and print specific mismatches when values disagree.
4. Spawn subagent with those 4 criteria + `scripts/wiki_sync.py` path.
5. Record verdict.

## Recovery / Edge Cases

- **Subagent tool unavailable**: fall back to a structured manual self-review
  — answer each criterion explicitly, but clearly mark the memory entry as
  `[REVIEW via self-review, not subagent]` so future reviewers see the
  lesser rigor.
- **Criteria not clear**: ask the user to pin down 3 acceptance bullets.
  Don't proceed without criteria. An objectively-passed review of
  undefined criteria is meaningless.
- **Subagent says FAIL but user disagrees**: record both positions in
  memory. Raise to the user. **Do not** retry the subagent with a leading
  prompt until it agrees — that's exactly the bias this skill prevents.

## References

- `docs/archive/Evaluator_Design_Decision_2026-04-20.md` — empirical spike
  that validated this design.
- `docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md` R-1 —
  the decision to proceed with subagent-based evaluation.
- `CLAUDE.md` Merge Gate — this skill's output feeds that gate's
  "end-to-end test passes" condition.
