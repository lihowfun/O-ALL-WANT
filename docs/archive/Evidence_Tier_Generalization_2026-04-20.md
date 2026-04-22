# R-5: Evidence-Tier Vocabulary — Generalization Decision

Date: 2026-04-20
Status: **Decided — ship as general-purpose optional skill.**
Source of question: [Future_Optimization_Plan_Amendment_v2_2026-04-20.md](Future_Optimization_Plan_Amendment_v2_2026-04-20.md) R-5

## The Research Question

GNN_explainer proposed a 5-tier evidence vocabulary:

```
T1 WIP           → .agents/memory.md only (not yet in experiment log)
T2 Observation   → EXPERIMENT_LOG with [CAVEAT: seed=X, single run]
T3 Confirmed     → 2+ independent runs cross-validated
T4 Baseline      → Multi-seed avg ± stddev, in VERSION.json
T5 Frozen        → do_not_rerun list
```

**Is this framing ML-specific, or general-purpose?** The original plan said
"decide after testing on 3 non-ML repos; ≥2/3 must fit for general ship."

## Three-Repo Generalization Test

### Test 1: Web-app repo — auth/session bug

Scenario: "SSO tokens aren't refreshing correctly."

| Tier | Direct ML translation | Web-app translation | Fits? |
|:----:|----------------------|---------------------|:-----:|
| T1 WIP | "I think training is broken" | "I think token refresh is broken" | ✅ |
| T2 Observation | Single seed run | Reproduced in Firefox 120 on macOS | ✅ |
| T3 Confirmed | Multi-seed same direction | Reproduced in Firefox, Safari, Chrome on macOS + Linux | ✅ |
| T4 Baseline | Multi-seed avg ± stddev | 99.8% session success over 10k sessions post-fix | ✅ |
| T5 Frozen | `do_not_rerun` | Ship fix, close issue, lock in regression test | ✅ |

**Fit: 5/5.** "Seed" translates directly to "environment" or "test run".

### Test 2: CLI tool — performance regression

Scenario: "v1.2.3 is slower than v1.2.2."

| Tier | Translation | Fits? |
|:----:|-------------|:-----:|
| T1 WIP | "I think v1.2.3 regressed" | ✅ |
| T2 Observation | Ran bench 1× on dev machine, saw 30% slowdown | ✅ |
| T3 Confirmed | Ran bench 5× on 3 different machines, same pattern | ✅ |
| T4 Baseline | New measured baseline: v1.2.4 is 5% faster than v1.2.2; stddev 0.3% | ✅ |
| T5 Frozen | Locked into CI as regression bar | ✅ |

**Fit: 5/5.** Perfect 1:1 with the ML case.

### Test 3: Docs repo — unsourced claim

Scenario: "README claims '80% of users prefer X'."

| Tier | Translation | Fits? |
|:----:|-------------|:-----:|
| T1 WIP | "Citation needed for the 80% claim" | ✅ |
| T2 Observation | Found one source: 2023 survey, n=500 | ✅ |
| T3 Confirmed | Found 3 independent surveys showing 75–85% | ✅ |
| T4 Baseline | "Established range 75–85%, 3 sources dated 2021–2024" | ✅ |
| T5 Frozen | "Don't re-research unless new data" | ✅ |

**Fit: 5/5** with minor translation: "seed" → "source."

## Decision

The 5-tier vocabulary **generalizes cleanly** across ML research, webapp
bugs, CLI performance, and docs. The test passed 3/3 (threshold was 2/3).

**Ship as a general-purpose optional skill.**

## What Ships

### File: `templates/.agents/skills/classify-evidence.md`

Skill that asks agents to pick a tier before writing to `.agents/memory.md`
or `docs/knowledge/`. Non-enforcing — it prompts vocabulary discipline but
doesn't block the write.

### Vocabulary addition to `templates/AGENT_RULES.md`

Add `[T1]` through `[T5]` alongside existing memory tags (`[BUG]`,
`[DECISION]`, etc.):

```markdown
**Available TAGs**:
  `[BUG]` `[INSIGHT]` `[DECISION]` `[WORKAROUND]` `[EXPERIMENT]` `[ARCHITECTURE]`
  `[T1]` `[T2]` `[T3]` `[T4]` `[T5]` — evidence tier (optional, see classify-evidence skill)
  `[CAVEAT: ...]` — qualifier (e.g. `[CAVEAT: single source]`, `[CAVEAT: one environment]`)
```

### Skill README update

Already exists. Add `classify-evidence.md` to its table.

## What Does NOT Ship

- **No per-tier enforcement**. We don't block a write because it's "only T2."
  Vocabulary, not gate.
- **No new CLI subcommand**. The tiering happens in skill prose, not tooling.
- **No cross-check that tiers match evidence quality**. That would require
  LLM judgment, which the harness-evaluator skill (R-1) can do on demand;
  automating it is out of scope here.

## Acceptance

- `classify-evidence.md` present and passes A-3 skill frontmatter lint
- `AGENT_RULES.md` memory tag list mentions the new tags
- Referenced from CONTRIBUTING_WIKI.md (wiki quality contribution guide)
- Zero code changes — pure convention + skill prose

## North-Star Check

Does this violate "very simple to use, smart knowledge recording,
self-evolving, useful without over-engineering"?

- **Simple**: yes — 5 tiers, one skill, optional. Users who don't need it
  can ignore it.
- **Smart knowledge recording**: yes — directly addresses "over-claiming
  finding when you only ran 1 seed."
- **Self-evolving**: yes — the tier makes the evolution visible
  (T1 → T3 → T4 over time).
- **Not over-engineered**: yes — no enforcement, no tooling, no gate.
  Just vocabulary.

Pass on all four.

---

*Decided 2026-04-20. Supersedes the "R-5 research" placeholder in Amendment v2.*
