---
id: Inheritance_And_Promotion_Experiment_2026-04-21
title: Cross-session knowledge inheritance + wiki promotion discipline
page_type: experiment
date: 2026-04-21
status: complete
branch: study/future-optimization-plan-confirmed
related:
  - docs/archive/Memory_Discipline_Experiment_2026-04-21.md
  - docs/archive/Dogfood_Session_2026-04-21.md
  - docs/wiki/WIKI_PIPELINE.md
  - templates/.agents/skills/classify-evidence.md
---

# Cross-session Inheritance + Wiki Promotion Experiment

> **Design intent**: The first discipline experiment tested *what a fresh
> agent WRITES*. This one tests the complementary half: *what a fresh agent
> READS* — does knowledge actually transfer across sessions via memory.md,
> and does the wiki pipeline prevent over-promotion?

## Protocol

- **Reviewer**: fresh-context `Agent(subagent_type="general-purpose")`, zero parent bleed.
- **Allowed reads**: exactly 3 files — `.agents/memory.md`, `docs/wiki/WIKI_PIPELINE.md`, `templates/.agents/skills/classify-evidence.md`. No other files, no scripts, no `git log`.
- **Two tasks**:
  - **Task A** — 4 questions about project state answerable only from those files.
  - **Task B** — promotion decision (STAY / PROMOTE / UNCERTAIN) on each of the 6 memory entries.
- **Reference answers pre-authored** before the subagent saw the prompt.

## Task A — Inheritance (4 questions, 4 reference answers)

| Q | Reference | Subagent | Verdict |
|---|-----------|----------|---------|
| Q1 Current evidence tier of R-1 subagent-independence claim | `[T2] [CAVEAT: n=1, single spike on 2026-04-20]` | Same verbatim | ✅ EXACT |
| Q2 Verdict on commit 881cb25 | "7/7 PASS, 0 FAIL, 0 UNCERTAIN" | Same + extras ("~28k tokens, 78s") | ✅ EXACT + enrichment |
| Q3 Skills passing frontmatter lint as of 2026-04-21 | 8 | "INSUFFICIENT EVIDENCE" with parenthetical "(memory states 8 as of 2026-04-21; no 2026-04-21 post-date figure given)" | ⚠️ OVER-CAUTIOUS — answer was in the file; refused to commit |
| Q4 Did harness-evaluator surface a novel finding? | Yes — Merge Gate parenthetical drift | Same verbatim | ✅ EXACT |

**3/4 exact, 1/4 over-cautious refusal.** No hallucinations. No invented content.

### Interpretation of the one miss (Q3)

Two non-exclusive diagnoses:

1. **Prompt ambiguity**: "as of 2026-04-21" is ambiguous — could mean "on that date" or "from that date forward". I (the prompt author) own this.
2. **"Do not guess" over-extension**: the subagent had the answer ("memory states 8") in its parenthetical rationale but still refused to state it as the answer. That's a read-discipline failure mode worth naming.

**Calibration lesson**: classify-evidence's Rule 1 ("default to lower tier when in doubt") is a *write* rule. A parallel *read* rule is missing: "If the answer is literally in the file, extract it; 'INSUFFICIENT EVIDENCE' is for when the answer is not there, not when the phrasing is ambiguous." Candidate addition to future skill / prompt guidance.

## Task B — Promotion (6 entries)

| # | Entry title (short) | Reference | Subagent | Verdict |
|---|---------------------|-----------|----------|---------|
| 1 | Merge Gate drift between root and template | STAY | STAY | ✅ |
| 2 | harness-evaluator 7/7 on 881cb25 (classification) | STAY | STAY | ✅ |
| 3 | 8 skills pass frontmatter lint (T3) | PROMOTE-debatable | UNCERTAIN — "T3 reproducible, but binary status metric borders on changelog/baseline territory" | ✅ Better calibrated than my reference |
| 4 | R-1 subagent independence (T2) | STAY | STAY | ✅ |
| 5 | Commit 881cb25 REVIEW | STAY | STAY | ✅ |
| 6 | Amendment v2 follow-through (FEATURE) | STAY | STAY | ✅ |

**6/6 PASS. Zero over-promotion.** The subagent correctly applied "default STAY when in doubt" and even produced a sharper UNCERTAIN reasoning than the reference on entry 3.

## Meta-findings

### 1. Inheritance via memory.md works

Fresh subagent with zero parent context correctly retrieved:
- Tier tags with caveats (Q1)
- Exact verdict numbers (Q2)
- A cross-entry finding mentioned only once in an `[INSIGHT]` entry, not highlighted anywhere (Q4)

No hallucinations across 4 questions × 6 promotion judgments. Inheritance is real.

### 2. Promotion discipline is properly conservative

`WIKI_PIPELINE.md`'s promote-stage gate + classify-evidence's tier rules combined to produce 0 over-promotes across 6 candidates. The "default STAY when in doubt" framing is doing its job.

### 3. Read discipline has a previously-unnamed failure mode: **over-refusal**

The first experiment showed fresh agents don't over-write. This experiment shows they *can* over-refuse to answer. Symmetric failure modes:

| Discipline | Laudable extreme | Failure extreme |
|---|---|---|
| Write | Skip trivia | Over-refuse: miss real signal by never writing |
| Read | "Don't guess" | Over-refuse: "INSUFFICIENT EVIDENCE" when answer is in the file |
| Promote | Default STAY | Over-promote: elevate single observations to wiki topics |

**All three failure modes observed or named.** OAW currently has explicit guidance for write-over and promote-over, but not for read-over-refuse. Gap worth closing.

## Caveats

- **Environment dependency**: `.agents/memory.md` is gitignored. This experiment ran in the Linux worktree where memory.md was authored yesterday. On any environment without that file, inheritance would trivially return "INSUFFICIENT EVIDENCE" across the board. The test assumed memory.md is seeded.
- **n=1 subagent invocation**: single fresh-context spawn, synthetic question set. Classified T2 with CAVEAT below.
- **Task A Q3 ambiguity**: the "as of 2026-04-21" phrasing was my prompt-writing mistake; the subagent's over-refusal is a real signal but confounded.

## Tier classification of THIS experiment's findings

Applying `classify-evidence` to the claims above:

| Claim | Tier | Why |
|---|---|---|
| "Inheritance via memory.md works" | `[T2] [CAVEAT: single subagent, n=1 question set]` | One run on one curated prompt. Not reproduced. |
| "Default STAY prevents over-promote" | `[T2] [CAVEAT: one 6-entry corpus, all authored by same agent]` | Curated corpus; not a natural sample. |
| "Over-refusal is a distinct read-discipline failure mode" | `[T1]` | Named, not quantified. One occurrence (Q3). Needs more data before calling it a pattern. |

## Follow-ups (not applied on this branch)

1. **Add a read-discipline sentence** to `classify-evidence.md` or a new `read-discipline.md` skill: *"If the answer is literally in the given files, extract it verbatim. 'INSUFFICIENT EVIDENCE' is for when no file contains the answer, not for when phrasing is ambiguous — in that case, state the extractable answer and flag the ambiguity."*
2. **Reproduce** both experiments on a non-synthetic session slice (e.g. real debug logs or a real design-decision thread) to move the T2 claims toward T3.
3. **Track the over-refusal rate** if Q3-style misses recur. If they exceed 1/20 reads, the read-discipline gap becomes P1 instead of P3.
