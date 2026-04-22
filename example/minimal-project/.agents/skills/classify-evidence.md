---
name: classify-evidence
description: "Tag a finding / memory entry with an evidence tier (T1–T5) before committing it to wiki or baseline. Prevents over-claiming what's actually just a single-run observation."
triggers: ["classify this", "what tier", "is this a finding or observation", "evidence tier", "is this confirmed"]
optional_reads:
  - docs/knowledge/index.md (see prior tier assignments for consistency)
outputs:
  - Tier tag (T1–T5) on the pending memory/knowledge entry
  - Optional [CAVEAT: ...] qualifier
---

# /classify-evidence — Evidence Tier Vocabulary

> **Why this skill exists**: Agents routinely write single-run observations
> as "findings" and single-source claims as "confirmed." This skill is a
> 30-second vocabulary gate before a write lands in memory or the wiki.
> **It doesn't enforce anything; it slows you down enough to pick the right word.**

## The Five Tiers

| Tier | Meaning | Lives in | Minimum evidence |
|:----:|---------|----------|------------------|
| **T1** | Work-in-progress hypothesis | `.agents/memory.md` only | Your intuition; no reproduction yet |
| **T2** | Observation | Experiment log / memory with `[CAVEAT]` | **One** run or source; not yet reproduced |
| **T3** | Confirmed | `docs/knowledge/` topic pages | **Two or more** independent reproductions / sources |
| **T4** | Baseline | `VERSION.json` benchmark_snapshot + knowledge page | Measured statistic (e.g. mean ± stddev) with named method |
| **T5** | Frozen | `VERSION.json` `do_not_rerun` | T4 + explicit decision not to retest |

"Seed / environment / source / reviewer" — substitute whichever term fits
your domain. The structure is the same:
**hypothesis → single observation → cross-validated → measured → locked.**

## Rules

### Rule 1: Default to the lower tier when in doubt

If you can't decide between T2 and T3, **it's T2**. The cost of under-claiming
is near zero; the cost of over-claiming is the entire reason this skill
exists.

### Rule 2: Always pair T2 with a `[CAVEAT]`

T2 without a caveat is a bug. Examples:
- `[T2] [CAVEAT: single seed]` for an ML result
- `[T2] [CAVEAT: tested on Firefox 120/macOS only]` for a web-app bug
- `[T2] [CAVEAT: single source]` for a factual claim

### Rule 3: Promote tier, don't re-write the entry

When a T2 becomes T3 (you reproduced it), don't delete the original — add a
dated note to the SAME entry:
```
[T2 → T3 2026-04-20] Reproduced on seed 42, 43, 44. Caveat removed.
```

## Steps

### Step 1: Before writing, decide the tier

Ask yourself in order:

1. Has this been reproduced or corroborated? → **No**: T1 or T2.
2. Is this based on measurement (stats, metrics)? → **No**: T3 or below.
3. Is this now the canonical baseline you'd compare future work against? → **No**: T3.
4. Is future re-measurement pointless? → **No**: T4.
5. Otherwise: T5.

### Step 2: Pick the right destination

| Tier | Write to |
|:----:|---------|
| T1 | `.agents/memory.md` (newest-first, prefix `[T1]`) |
| T2 | `.agents/memory.md` or experiment log; always with `[CAVEAT: ...]` |
| T3 | `docs/knowledge/<topic>.md` — promote from memory when T2 → T3 |
| T4 | `VERSION.json.benchmark_snapshot` + `docs/knowledge/Performance_Baselines.md` |
| T5 | `VERSION.json.do_not_rerun` list |

### Step 3: If unsure, ask for T3 criteria explicitly

A T3 claim is "I can point to two independent things that agree." If the
user said "confirmed" but you can't list the two, treat as T2 and ask.

## Edge Cases

- **User says "this is a finding"**: They might mean T3 or T4. Ask which
  before writing.
- **Multi-seed already run once**: T3 if seeds were part of the same run
  (not independent), T4 if they were genuinely independent runs with aggregated stats.
- **A source has contradictory data**: T2 with `[CAVEAT: contradicts <other>]`;
  do not average unreviewed.
- **Refactor / code change with no measurement**: Usually `[DECISION]` tag,
  not a tier. Tiers apply to **claims of truth**, not changes of intent.

## When NOT To Use This Skill

- Pure refactors, style changes, docs polish → just use `[DECISION]` or
  `[INSIGHT]` tags. Tiers don't add value.
- Trivial fixes (typo, broken link) → skip.
- User explicitly asks for a quick note → honor speed over ceremony.

## Reference

- `docs/archive/Evidence_Tier_Generalization_2026-04-20.md` — why this is
  general-purpose, not ML-only.
- `templates/AGENT_RULES.md` — memory tag list includes T1–T5 and CAVEAT.
