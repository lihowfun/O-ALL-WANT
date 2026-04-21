---
id: Inheritance_Check_Dogfood_2026-04-21
title: Inheritance-check skill — first dogfood on OAW itself
page_type: audit
date: 2026-04-21
status: complete
branch: study/future-optimization-plan-confirmed
related:
  - templates/.agents/skills/inheritance-check.md
  - docs/archive/Inheritance_And_Promotion_Experiment_2026-04-21.md
  - docs/archive/Experiment_Followups_Plan_2026-04-21.md
---

# inheritance-check skill — first dogfood

> **Purpose**: Acceptance criterion for L-5 from
> `Experiment_Followups_Plan_2026-04-21.md` — "dogfood once; current agent
> drafts 3 questions from OAW's own project state; subagent answers; at
> least 2/3 exact." We ran 5 questions; 5/5 exact — and the intentionally
> hard Q5 surfaced a real documentation drift.

## Setup

- **SOURCES** (exactly four files): `AI_CONTEXT.md`, `VERSION.json`,
  `.agents/memory.md` (top of file — newest first), `ROADMAP.md` (first 60
  lines).
- **Subagent**: `Agent(subagent_type="general-purpose")`, fresh context.
- **Questions + reference answers** drafted before spawn.

## Questions + reference + subagent output

| # | Question | Reference | Subagent answer | Class |
|---|----------|-----------|-----------------|:-----:|
| 1 | Version per VERSION.json | `1.1.0` | `1.1.0 — VERSION.json:2` | ✅ EXACT |
| 2 | Entries in `task_state.in_progress` | `Empty` | `Empty (no entries) — VERSION.json:8` | ✅ EXACT |
| 3 | `do_not_rerun` entry identifiers | P0 validation / pre-launch smoke / R-1 evaluator / R-3 failure corpus (4 entries) | Same 4, verbatim — `VERSION.json:16-19` | ✅ EXACT |
| 4 | Most recent memory entry's TAG + gist | `[INSIGHT] Merge Gate drift between root and template` | Verbatim — `.agents/memory.md:11` | ✅ EXACT |
| 5 (hard) | Does AI_CONTEXT.md state the same version as VERSION.json? | **No — drift**: VERSION.json 1.1.0 vs AI_CONTEXT.md v1.0.0 | `Differ — VERSION.json says 1.1.0, AI_CONTEXT.md says v1.0.0 — VERSION.json:2, AI_CONTEXT.md:5` | ✅ EXACT |

**Score: 5/5 EXACT · 0 hallucination · 0 over-refuse · 0 partial.**

## What the skill caught that the current session had not noticed

Q5 was intentionally hard: I suspected there was cross-file drift but had
not verified. The subagent confirmed it: after bumping `VERSION.json` to
`1.1.0` in an earlier commit (`37f15c4`), `AI_CONTEXT.md` line 5 was never
updated and still reads `v1.0.0`. The current-context agent (me) missed it
across multiple file reads. A cold reader caught it in one pass. **This is
the skill functioning as designed.**

## Action taken

- `AI_CONTEXT.md:5` patched from `v1.0.0` → `v1.1.0` immediately after the
  subagent surfaced the drift (in this commit or adjacent).

## Verdict per skill's Step 6 traffic light

Score ≥ 4/5 exact, 0 hallucinations, 0 over-refuse → **🟢 green**.
SOURCES set is cold-start-sufficient for OAW itself.

## Tier classification of this dogfood's claims

- "inheritance-check skill works on a self-dogfood" → `[T2] [CAVEAT: single invocation, OAW's own state, 5 questions all extractable]`
- "SOURCES default (AI_CONTEXT + VERSION + last-5-memory + first-60-lines-ROADMAP) is cold-start-sufficient" → `[T2] [CAVEAT: one project (OAW), one snapshot; needs reruns on peer projects]`
- "Cold reader catches drift current-context agent misses" → `[T1]` (hypothesis with one supporting data point)

## Next validation opportunities

- Rerun on main branch post-v1.1.0 merge — different state, same SOURCES shape.
- Run on any peer project that installed OAW template, see if defaults still hold.
- If Q-type drift (like Q5) is consistently caught, this pattern may warrant a separate `cross-file-consistency` skill.
