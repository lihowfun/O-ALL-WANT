---
id: Merge_Readiness_2026-04-20
title: Merge Readiness — study/future-optimization-plan-confirmed → main
page_type: decision
date: 2026-04-20
status: open
branch: study/future-optimization-plan-confirmed
target: main
related:
  - docs/archive/Future_Optimization_Plan_Confirmed_2026-04-20.md
  - docs/archive/Future_Optimization_Plan_Amendment_v2_2026-04-20.md
---

# Merge Readiness — `study/future-optimization-plan-confirmed` → `main`

> **Purpose**: single checklist for deciding when this branch can merge. Built
> 2026-04-20 while handing off to Mac. The new Merge Gate added in this
> branch (see `CLAUDE.md` + `templates/AGENT_RULES.md`) applies here —
> smoke-test-passed is not sufficient.

## 0. Status Snapshot (2026-04-20, from Linux worktree)

| Item | Value |
|---|---|
| Commits ahead of `origin/main` | **6** |
| Commits behind | 0 (no rebase needed) |
| Total diff | 4,201 insertions / 130 deletions across 38 files |
| `./scripts/harness_check.py` | **7/8 green** — `example-drift` fails |
| `wiki_sync.py lint` (default) | ✅ pass (22 soft warnings) |
| `wiki_sync.py lint --strict` | ❌ would fail (placeholders in `OAW_Session_Continuity_Test.md`) |
| `VERSION.json.version` | `1.1.0-preview` (needs bump or explicit keep-as-preview) |
| CI (GitHub Actions) | not run yet on this branch — triggers only on PR-to-main |

## 1. Merge Gate — which condition are we trying to meet?

From the newly-added rule (`CLAUDE.md` §Merge Gate):

> Infrastructure code merges to `main` only if one of:
> 1. End-to-end test passes in the worktree (`./scripts/harness_check.py` green, AND any affected skill runs its own acceptance criteria)
> 2. Quantified improvement vs current `main` baseline (measured, not asserted)
> 3. Explicit user authorization for experimental scaffold (clearly marked as such)

**Decision**: we aim for **condition 1 (end-to-end test + skill acceptance)**.
Condition 2 does not apply (this is governance, not a measurable perf win).
Condition 3 is the fallback if we decide the new review skills should ship
as explicit `[EXPERIMENTAL]` scaffold.

## 2. Hard Blockers — MUST fix before merge

### B-1. `example-drift` check fails
- **Symptom**: `harness_check.py` → `example-drift: example/minimal-project/scripts/wiki_sync.py differs from scripts/wiki_sync.py`
- **Root cause**: commit `881cb25` added ~280 lines (`add-experiment`, `update-state`, `_ensure_experiment_log`, `_replace_frontmatter_field`) to `scripts/wiki_sync.py` but did not sync `example/minimal-project/scripts/wiki_sync.py`.
- **Fix**: `cp scripts/wiki_sync.py example/minimal-project/scripts/wiki_sync.py && ./scripts/harness_check.py` — expect 8/8 green.
- **Rule violated**: `CLAUDE.md` §Project-Specific Forbidden Actions #3 — "Do not modify `templates/` without updating `example/minimal-project/` accordingly" (this check's spirit extends to `scripts/`).

### B-2. `example/minimal-project/.agents/skills/` out of sync with `templates/.agents/skills/`
- **Symptom**: new skills `classify-evidence.md` + `harness-evaluator.md` exist under `templates/.agents/skills/` but not under `example/minimal-project/.agents/skills/`.
- **Current state**: `example/minimal-project/.agents/skills/` has 8 files; `templates/.agents/skills/` has 10. Missing: `classify-evidence.md`, `harness-evaluator.md`.
- **Fix**: `cp templates/.agents/skills/classify-evidence.md templates/.agents/skills/harness-evaluator.md example/minimal-project/.agents/skills/`, then re-run `harness_check` (fresh-install diff should stay quiet).
- **Note**: `harness_check` `fresh-install` check currently passes because it only asserts an *expected file set* exists, not that counts match. So B-2 is caught by `CLAUDE.md` rule 3, not by tooling. Consider tightening the check in a follow-up (not a blocker here).

### B-3. Skill acceptance criteria not exercised
- **Merge Gate §1 clause**: "AND any affected skill runs its own acceptance criteria."
- **Affected skills** (new, never run end-to-end):
  - `classify-evidence` — expected output: `T1`/`T2`/`T3`/`T4`/`T5` tier tag on a pending memory entry, optional `[CAVEAT: ...]`
  - `harness-evaluator` — expected output: `.agents/memory.md` entry with `[REVIEW]` tag + per-criterion verdict
- **Fix options** (pick one):
  1. **Run each skill manually once** against a real pending change — last commit `881cb25` is a natural target for `harness-evaluator`; the Amendment v2 feedback (GNN_explainer comments) is a natural target for `classify-evidence`. Record both results in `.agents/memory.md` with `[REVIEW]` / `[CLASSIFICATION]` tags. Acceptance = skill produced the declared output; reviewer judges quality.
  2. **Re-label as experimental scaffold** (Merge Gate §3): add `[EXPERIMENTAL]` note to each skill's frontmatter or README and cite explicit user authorization in the memory log. Skip manual run.
- **Recommendation**: option 1 — the skills were written precisely to catch the kinds of problems this branch introduces; using them on this branch is the most honest dogfooding.

## 3. Soft Blockers — SHOULD fix, can be punted with justification

### S-1. `wiki_sync lint --strict` fails on placeholder leakage
- 22 warnings, ~18 of them are `${VERSION}` / `${PROJECT_NAME}` / `${CURRENT_PHASE}` placeholders inside `docs/knowledge/OAW_Session_Continuity_Test.md` (intentional — that doc is a *test report about placeholder leakage*).
- Options:
  1. Leave as-is; `harness_check` runs lint in default (non-strict) mode, so this doesn't block CI.
  2. Move the literal placeholder examples into a fenced code block with `{% raw %}` / fenced escapes so lint sees them as code, not unfilled fields.
  3. Rename `${VAR}` → `%%VAR%%` in that doc only.
- **Recommendation**: option 1 (keep). Document in merge notes that `--strict` is expected to fail on this file until we harden lint to skip fenced code blocks. Open issue, don't block merge.

### S-2. `VERSION.json` still `1.1.0-preview`
- `notes` field literally says: "`1.1.0-preview` indicates the worktree has the pending v1.1.0 content but has not been merged to main yet."
- `task_state.in_progress` lists A-1 / A-2 / A-3 / R-1 as still in progress, but A-1/A-2/A-3 are done on this branch; R-1 produced the two new skills.
- **Pre-merge edit**:
  - `version`: `1.1.0-preview` → `1.1.0`
  - `last_updated`: bump to merge date
  - `current_phase`: `v1.1 preview — ...` → `v1.1 — Taiwan.md wiki packet + harness quality gates + merge gate + evaluator scaffolds`
  - `task_state.in_progress`: drop A-1/A-2/A-3; keep `R-1 harness-evaluator dogfooding` if skills ship as experimental
  - `notes`: remove the "not been merged to main yet" sentence
  - `benchmark_snapshot.summary`: update to "harness_check 8/8 green" once B-1 fixed

### S-3. CHANGELOG.md for v1.1.0
- Currently has entries but likely still headed under `1.1.0-preview`.
- Need a final pass to align heading with the bumped version and add the Amendment v2 items (merge gate, evidence tiers, deprecation protocol, classify-evidence, harness-evaluator).

### S-4. CI has not run on this branch yet
- Workflow triggers: `push: branches: [main]` OR `pull_request: branches: [main]`. Pushing the feature branch does **not** run CI.
- **Action**: open a draft PR (`gh pr create --draft --base main --head study/future-optimization-plan-confirmed`) → GHA runs → confirm green before flipping to "ready for review".

## 4. Non-Blockers (informational)

- **No merge conflicts**: branch is 6 ahead / 0 behind `origin/main`.
- **`self-improving.md` and other pre-existing skills** pass frontmatter lint (confirmed in VERSION.json `benchmark_snapshot`).
- **`docs/archive/` additions** (plan docs, decision logs) are docs-only and carry zero runtime risk.
- **`.github/` additions** (issue templates, PR template, workflow tweaks) are CI-scoped and will validate themselves when §S-4's draft PR runs.

## 5. Execution Order on Mac

```bash
# 0. Pick up the branch
cd <OAW worktree root>
git fetch origin
git checkout study/future-optimization-plan-confirmed
git pull --ff-only

# 1. Fix B-1 — sync example wiki_sync.py
cp scripts/wiki_sync.py example/minimal-project/scripts/wiki_sync.py

# 2. Fix B-2 — sync example skills
cp templates/.agents/skills/classify-evidence.md \
   templates/.agents/skills/harness-evaluator.md \
   example/minimal-project/.agents/skills/

# 3. Verify harness_check 8/8 green
./scripts/harness_check.py

# 4. B-3 — dogfood the new skills on this branch
#    (4a) classify-evidence on the Amendment v2 feedback entries
#    (4b) harness-evaluator on commit 881cb25 (fresh subagent context)
#    Record both results in .agents/memory.md as [CLASSIFICATION] / [REVIEW] entries.

# 5. Soft fixes
#    - Optional: address S-1 (placeholder escaping in OAW_Session_Continuity_Test.md)
#    - Edit VERSION.json per §S-2
#    - Edit CHANGELOG.md per §S-3

# 6. Commit + push the fixes
git add -p
git commit -m "chore(release): sync example + bump to 1.1.0 + dogfood new skills"
git push

# 7. Open draft PR so CI runs
gh pr create --draft --base main --head study/future-optimization-plan-confirmed \
  --title "v1.1.0: Taiwan.md wiki packet + harness gates + merge gate + evaluator scaffolds" \
  --body-file docs/archive/Merge_Readiness_2026-04-20.md

# 8. When CI green + B-3 done, flip PR to ready-for-review; squash or merge
```

## 6. Exit Criteria Checklist

Before flipping PR from draft → ready:

- [ ] B-1: `./scripts/harness_check.py` shows 8/8 green
- [ ] B-2: `example/minimal-project/.agents/skills/` contains the two new skills
- [ ] B-3: `.agents/memory.md` has `[REVIEW]` entry from `harness-evaluator` on this branch AND `[CLASSIFICATION]` entry from `classify-evidence` on Amendment v2 feedback
- [ ] S-2: `VERSION.json` bumped to `1.1.0`, `in_progress` cleaned, `notes` updated
- [ ] S-3: `CHANGELOG.md` v1.1.0 section finalized
- [ ] S-4: CI green on PR
- [ ] Author (you) confirms: "the new skills actually caught something in §B-3, not just produced empty shells" — if they produced nothing useful, consider Merge Gate §3 (ship as explicit `[EXPERIMENTAL]`) instead of §1.

## 7. Fallback Plan

If §B-3 reveals that the new skills produce shallow or wrong output:

- **Option A (scope down)**: revert commit `881cb25` from the merge, keep the first 5 commits (Taiwan.md wiki + harness_check + A-3 lint + v1.1.0 metadata + Amendment v2 docs). Ship v1.1.0 without the new skills. Re-introduce skills in v1.2.0 after redesign.
- **Option B (ship as experimental)**: keep the commit but add `status: experimental` to both skill frontmatters, document in CHANGELOG, invoke Merge Gate §3 with explicit authorization.
- **Option C (iterate on this branch)**: rewrite the skills based on §B-3 feedback, recommit, re-dogfood. Stay on `study/*` until useful.

Default preference: **Option C → Option B → Option A**. A cannot be revisited easily because Amendment v2 docs reference the skills.
