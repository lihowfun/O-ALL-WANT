---
id: Dogfood_Session_2026-04-21
title: Dogfood Session — harness-evaluator + classify-evidence on commit 881cb25
page_type: audit
date: 2026-04-21
status: complete
branch: study/future-optimization-plan-confirmed
related:
  - docs/archive/Merge_Readiness_2026-04-20.md
  - docs/archive/Evaluator_Design_Decision_2026-04-20.md
  - templates/.agents/skills/harness-evaluator.md
  - templates/.agents/skills/classify-evidence.md
---

# Dogfood Session — harness-evaluator + classify-evidence

> **Purpose**: Satisfy Merge Gate §1 "any affected skill runs its own
> acceptance criteria" by actually invoking the two new skills on this
> branch's work. This is the committed audit trail; a mirrored local copy
> exists in `.agents/memory.md` (git-ignored per CLAUDE.md architecture).

## 1. harness-evaluator — independent subagent review of commit 881cb25

### Setup

- **Change under review**: commit `881cb25` "feat(harness): merge gate + evidence tiers + 2 review skills (Amendment v2 follow-through)"
- **Files affected**: 11 (see commit stat)
- **Reviewer**: `Agent(subagent_type="general-purpose")`, fresh context, no parent bias
- **Prompt**: skill's Step 2 template verbatim, 7 testable criteria

### Criteria used (each verifiable from files alone)

1. `./scripts/harness_check.py` exits 0 with "ALL GREEN — 8/8 checks passed"
2. `wiki_sync.py --help` lists both `add-experiment` and `update-state`
3. `CLAUDE.md` has "## Merge Gate" section with exactly 3 numbered conditions
4. `templates/AGENT_RULES.md` has the same section with matching bold leads
5. `classify-evidence.md` has proper frontmatter + 5-tier table
6. `harness-evaluator.md` has proper frontmatter + subagent-spawn code block in Step 2
7. `CONTRIBUTING_WIKI.md` has "Deprecating an entry" section with `[DEPRECATED YYYY-MM-DD]` + Why/Replaced by/Lesson block

### Verdict (from fresh-context subagent)

```
Verdict: 7/7 PASS, 0 FAIL, 0 UNCERTAIN
Tokens: ~28k
Duration: 78s
```

### Concrete evidence returned by subagent (abridged)

1. **PASS** — final line: `ALL GREEN — 8/8 checks passed`
2. **PASS** — usage line: `{build,refresh,lint,stale,cross-check,add-experiment,update-state}`
3. **PASS** — `CLAUDE.md:107` heading; conditions at L112–114: **End-to-end test passes in the worktree**, **Quantified improvement vs current `main` baseline**, **Explicit user authorization for experimental scaffold**
4. **PASS with note** — MATCH on bold leads; differs only in parenthetical after #1: CLAUDE.md says "`./scripts/harness_check.py` green, AND any affected skill runs its own acceptance criteria"; `templates/AGENT_RULES.md` says "not just `import ok` or `py_compile`"
5. **PASS** — frontmatter OK; tiers verbatim: "Work-in-progress hypothesis", "Observation", "Confirmed", "Baseline", "Frozen"
6. **PASS** — frontmatter OK; Step 2 code block L67–89 contains all four required tokens
7. **PASS** — section at `docs/wiki/CONTRIBUTING_WIKI.md:79`; marker at L91/L104; Why/Replaced by/Lesson at L93/L94/L95

### Notable finding (worth a follow-up, not a merge blocker)

**Merge Gate drift between root and template**: both files carry identical bold leads for the 3 conditions, but the parenthetical after condition 1 differs materially:
- **Root `CLAUDE.md`**: cites `./scripts/harness_check.py` (OAW-specific) **and** adds the "any affected skill runs its own acceptance criteria" clause.
- **`templates/AGENT_RULES.md`** (what users install): says only "not just `import ok` or `py_compile`", dropping the skill-acceptance clause.

The skill-acceptance clause is the generic-reusable part — it belongs in the template too. Flagged for a follow-up alignment PR; does not block this merge because criterion 4 was written to test bold-lead match, not parenthetical match, and both passed.

### Skill self-assessment (per harness-evaluator Step 5)

Subagent returned 7/7 PASS. Is it rubber-stamping?
- Criteria were mechanical (file existence, literal string match, exit codes) by design — low false-positive risk.
- Subagent still surfaced the Merge Gate parenthetical drift unprompted as a "Notes" item → **not rubber-stamping**.
- **Conclusion**: skill is functioning. First real dogfood success.

## 2. classify-evidence — tier three claims made by this branch

Applied the 5-tier vocabulary to three claims surfaced by this branch:

### Target 1: "subagents get zero parent-context inheritance (~19k tokens, 13s per review)"

- **Source**: `VERSION.json` `do_not_rerun` notes, R-1 entry.
- **Tier**: **T2 [CAVEAT: n=1, single invocation on 2026-04-20]**
- **Rule invoked**: Rule 1 (default lower) + Step 1 Q1 (reproduced? No → T1 or T2).
- **Why not T4 (baseline)**: a single spike is not a named-method measurement with dispersion. Needs at least one re-run on a different change to establish reproducibility range.
- **Action implication**: tier-tag the claim in memory; do **not** move it out of `do_not_rerun` (that list is a procedural re-run guard, not a primary claim store). But when future work cites the 19k/13s numbers as baseline, caller must reference this CAVEAT.
- **Corroboration available**: today's dogfood subagent observed ~28k / 78s on a larger criteria set. Different workload, not directly comparable, but shows the 19k/13s number is not a universal baseline.

### Target 2: "8 skills pass frontmatter lint"

- **Source**: the claim CHANGELOG + VERSION.json should carry after this branch lands.
- **Tier**: **T3 (Confirmed)**
- **Rule invoked**: Step 1 Q1 (reproduced? Yes — `harness_check.py` runs the lint every invocation and has been run at least twice: once yesterday with 6 skills, once today with 8 after adding classify-evidence + harness-evaluator).
- **Note**: stays T3, not T4, because it's a binary pass/fail, not a measured statistic.

### Target 3: "harness-evaluator validated commit 881cb25 at 7/7 criteria"

- **Source**: section 1 of this document.
- **Tier**: **T2 [CAVEAT: single invocation; criteria all mechanical — no judgment calls]**
- **Rule invoked**: Rule 1 + Rule 2 (T2 always pairs with CAVEAT).
- **Why not T3**: not reproduced (single subagent invocation). Would need a second subagent with the same prompt reaching the same verdict for T3.
- **Action implication**: do not cite this as proof the skill works in general. It's one successful dogfood run on a branch with explicit, narrow criteria.

### Self-assessment

The classify-evidence skill forced three different outcomes (T2/T3/T2 with differing reasoning) within five minutes of applying it, which is exactly the value proposition. The discipline of writing the `[CAVEAT: ...]` line surfaced the n=1 limitation on Target 1 that would otherwise have propagated as "verified."

## 3. Merge Gate §1 Status After Dogfooding

| Requirement | Status |
|---|---|
| `./scripts/harness_check.py` green | ✅ 8/8 (confirmed by criterion 1 above) |
| Affected skill runs its own acceptance criteria | ✅ both skills dogfooded in §1 and §2 |
| Findings recorded in memory | ✅ `.agents/memory.md` (local) + this committed doc |

**Conclusion**: Merge Gate §1 conditions met for the runtime-affecting pieces of this branch. Remaining merge blockers from `Merge_Readiness_2026-04-20.md` are documentation hygiene (VERSION bump, CHANGELOG finalize) + opening the draft PR to run CI.
