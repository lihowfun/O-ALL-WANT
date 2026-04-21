---
id: Memory_Discipline_Experiment_2026-04-21
title: Memory Write Discipline — fresh-context subagent on 8 synthetic events
page_type: experiment
date: 2026-04-21
status: complete
branch: study/future-optimization-plan-confirmed
related:
  - docs/archive/Dogfood_Session_2026-04-21.md
  - templates/.agents/skills/classify-evidence.md
  - templates/.agents/memory.md
---

# Memory Write Discipline Experiment

> **Design intent**: With the new `classify-evidence` skill + the updated
> memory.md TAG header, does a fresh-context agent produce **good write
> discipline** — skip trivia, write substance, pick sane tiers, stay
> concise — without extra nannying? Or does it fall into the three
> classic failure modes: over-writing, over-tiering, essay bloat?
>
> **Proportionate scoring** (the "not over-engineered" part): three binary-ish
> dimensions, not a 10-point rubric. Reference answers authored before the
> subagent saw the events.

## Protocol

- **Reviewer**: fresh-context `Agent(subagent_type="general-purpose")`, zero parent bleed.
- **Given**: `memory.md` TAG header (verbatim), `classify-evidence` decision rules §1–4 (verbatim), 8 synthetic events.
- **NOT given**: prior memory entries, project specifics, this document.
- **Task**: per event, output a single row — Decision (WRITE/SKIP) · Tag · Tier · CAVEAT · Body · Word count. No preamble, no reasoning essays.

## The 8 events (synthetic — do not treat as real OAW decisions)

| # | Event | Reference verdict |
|---|-------|-------------------|
| E1 | Single-seed benchmark: +14.2% vs baseline | MUST_WRITE `[T2]` + `[CAVEAT: single seed]` |
| E2 | Typo fix in README line 5 | SHOULD_SKIP |
| E3 | Chose lazy-load over eager after considering cold-start vs warm throughput | MUST_WRITE `[DECISION]` |
| E4 | Three config knobs tried, all slightly worsened p95, didn't pinpoint | ACCEPTABLE either way; if WRITE, short `[T1]`/`[FAILURE]` |
| E5 | NPE crash reproduced on macOS/FF + Linux/Chrome + Win/Edge | MUST_WRITE `[BUG]` `[T3]` |
| E6 | Rename local `tmp` → `scratch_buf` | SHOULD_SKIP |
| E7 | p95 latency 3 independent runs: 142/147/139ms (mean 142.7, σ~3.3) | MUST_WRITE `[T4]` |
| E8 | User said in passing: "please don't use emojis in comments" | ACCEPTABLE either way — belongs in user-memory, but that wasn't exposed |

## Scoring rubric (three dimensions, deliberately simple)

1. **Decision accuracy** — clear cases: binary PASS/FAIL. Flexible cases: any defensible choice counts.
2. **Tag/tier correctness** — tier ≤ reference (Rule 1: default lower). Tag must be a defined Kind TAG and semantically reasonable.
3. **Conciseness** — median body ≤ 60 words, max ≤ 120 words. (These ceilings are far above what a well-disciplined entry should need.)

## Subagent output (verbatim)

| # | Decision | Tag | Tier | CAVEAT | Body | Words |
|---|----------|-----|------|--------|------|-------|
| 1 | WRITE | `[EXPERIMENT]` | `[T2]` | single run on seed 42, no variance estimate | New code shows 14.2% speedup over baseline; unconfirmed until replicated across seeds. | 13 |
| 2 | SKIP | — | — | — | — | — |
| 3 | WRITE | `[DECISION]` | — | — | Chose lazy-load for the config module because cold-start latency dominates warm throughput in this app's usage profile. | 17 |
| 4 | WRITE | `[EXPERIMENT]` | `[T1]` | — | Config knobs A, B, C each slightly worsened p95; root cause and worst combination not yet isolated. | 16 |
| 5 | WRITE | `[BUG]` | `[T3]` | — | Null-pointer crash reproduces on macOS/Firefox, Linux/Chrome, Windows/Edge with identical input; platform-independent. | 12 |
| 6 | SKIP | — | — | — | — | — |
| 7 | WRITE | `[ARCHITECTURE]` | `[T4]` | — | p95 latency baseline: 142.7ms mean, ~3.3ms stddev across 3 independent runs (142/147/139). Method: 3-run p95 mean. | 18 |
| 8 | WRITE | `[DECISION]` | — | — | Convention: no emojis in code comments, per user request. | 9 |

## Scoring verdict

### Dimension 1 — Decision accuracy

| Subset | Pass rate |
|---|---|
| Clear MUST_WRITE (E1, E3, E5, E7) | 4/4 ✅ |
| Clear SHOULD_SKIP (E2, E6) | 2/2 ✅ |
| Flexible (E4, E8) | 2/2 ✅ (both chose WRITE with defensible outcome) |

### Dimension 2 — Tag/tier correctness

| Event | Verdict | Note |
|---|---|---|
| E1 | ✅ | Tier T2 with CAVEAT; CAVEAT text more specific than reference (additive, not wrong). |
| E3 | ✅ | `[DECISION]` exact. |
| E4 | ✅ | `[T1]` correct per Rule 3 (no reproduction, no measurement). |
| E5 | ✅ | `[T3]` correct (three independent environments). |
| E7 | ⚠️ | Tier `[T4]` correct; Kind tag `[ARCHITECTURE]` is misapplied — this is a measurement, not a design choice. `[EXPERIMENT]` would fit better, or tier alone without a Kind tag. |
| E8 | ✅ | Treating user preference as a project convention via `[DECISION]` is a reasonable call given the exposed rules. |

5/6 exact, 1/6 tier-correct-tag-misapplied.

### Dimension 3 — Conciseness

- Non-skip word counts: 13, 17, 16, 12, 18, 9 words.
- **Median = 14.5 words**, max = 18, min = 9.
- Ceilings (≤60 median, ≤120 max) cleared by an order of magnitude.
- No essay bloat. No restating of the event. No rationale padding.

## Failure modes NOT observed (the real finding)

| Failure mode | Observed? | Why it matters |
|---|---|---|
| Over-writing (writing trivia) | ❌ none | E2 + E6 both correctly skipped |
| Over-tiering (T3+ for single-run claims) | ❌ none | T2 paired with CAVEAT (Rule 2); T3 only after 3-env repro; T4 only with measured σ |
| Essay bloat | ❌ none | Max entry 18 words; no entry restated its event |

Under the exposed rules, a fresh-context agent produced **disciplined memory writes** on the first try with no nudging.

## Ambiguities surfaced (actionable follow-ups for OAW)

### Gap 1 — When is a tier tag enough on its own?

E7 exposed that the rules don't say whether `[T4]` can stand alone or must pair with a Kind tag. The subagent chose `[ARCHITECTURE]` as the Kind partner, which reads wrong for a measurement. Either:
- **(a) Guidance**: "Tier tags can stand alone when the event is a pure measurement; Kind tags are for event *nature* (bug/decision/etc.) not evidence strength", OR
- **(b) Mandate**: "Measurements use `[EXPERIMENT]` + tier; `[ARCHITECTURE]` is reserved for design decisions."

**Recommendation**: add one sentence to `memory.md` header: *"Kind tag optional when the entry is a pure measurement — tier alone is fine. `[ARCHITECTURE]` means a design choice, not a measurement."*

### Gap 2 — User preferences: project memory vs user memory?

E8 ("please don't use emojis in comments") is objectively a user-level preference that applies across projects. OAW's rules expose only project-level `.agents/memory.md`; the subagent had nowhere else to put it and reasonably landed it as a project `[DECISION]`. This is the correct bug fix for agent authors using Claude Code's user-memory system — project memory should **reference** user preferences, not duplicate them.

**Recommendation**: add to `memory.md` header: *"User preferences that apply across projects belong in user-level memory (e.g. Claude Code auto memory), not here. This file records project-specific decisions, bugs, and findings."*

## Overall verdict

- **Discipline present under exposed rules**: ✅ (9/10 signals green; only E7 tag was soft).
- **Review standard proportionate**: ✅ the scoring took <5 minutes and produced two concrete follow-up items. No 10-point rubric needed.
- **Tier-claim evidence level for THIS experiment**: `[T2] [CAVEAT: n=1 subagent invocation on synthetic data; two ambiguities are real but the generalization "rules produce discipline" needs replication on non-synthetic streams]`.

## Next steps (not done on this branch)

1. Apply Gap 1 + Gap 2 one-sentence edits to `templates/.agents/memory.md` header in a follow-up PR (1-line changes each, but deserve review separate from the v1.1.0 merge).
2. Re-run this experiment on a *real* session slice from `.agents/memory.md` (non-synthetic) to test whether discipline persists when events are messier.
