---
id: Cross_Context_Validation_Review_2026-04-21
title: Cross-context validation + review — v1.1.0 strengths, weaknesses, future priorities
page_type: review
date: 2026-04-21
status: complete
branch: study/future-optimization-plan-confirmed
related:
  - docs/archive/Memory_Discipline_Experiment_2026-04-21.md
  - docs/archive/Inheritance_And_Promotion_Experiment_2026-04-21.md
  - docs/archive/v1_0_0_vs_v1_1_0_Comparison_2026-04-21.md
  - docs/archive/Experiment_Followups_Plan_2026-04-21.md
---

# Cross-context Validation + Review

> Earlier experiments were single-corpus, Claude-agent, OAW-adjacent. This
> round broadens the evidence: two new project archetypes (ML research, CLI
> tool), an adversarial corpus, an empty-memory cold-start, plus static
> audit of the adapter / example story. Result: v1.1.0 is genuinely strong
> on the axes we tested, but three real weaknesses surfaced that are worth
> fixing on this branch, plus three structural issues deferred to v1.2.0+.

## Test suite (this round)

| ID | Test | Outcome |
|----|------|---------|
| T-A1 | ML research archetype (8 events — benchmarks, seeds, baselines) | 7/8 clear pass, 1 debatable (R8 — Rule 5 mis-apply) |
| T-A2 | CLI tool archetype (8 events — features, fixes, CI, latency) | 8/8 pass, rules fit naturally |
| T-B | Empty-memory cold start (5 questions, seeded memory.md with no entries) | 5/5 pass, INSUFFICIENT EVIDENCE correctly returned twice when genuinely absent |
| T-C | Adversarial CAVEAT — Rule 3 traps (same seed, same laptop, single source, authority assertion) | 4/4 pass, every CAVEAT explicitly named the independence failure |
| S-D | Adapter file static audit (AGENTS.md, GEMINI.md, example/minimal-project content) | Exposed 2 structural drift issues |
| S-E | `_slugify_topic` non-ASCII test | Empty slug on pure-CJK titles |

**Four-test agent pass rate on v1.1.0 rules: 24/25 decisions correct (96%).**

## Strengths v1.1.0 actually has (validated, not claimed)

### 1. Rules generalise across project archetypes

ML research and CLI tool are very different evidence profiles:

- **ML research** has lots of measurements → v1.1.0 agents used `[T2]` for single-seed, `[T3]` for cross-seed, `[T4]` for aggregated baselines, with CAVEATs naming the specific independence axis.
- **CLI tool** has few measurements, mostly decisions → v1.1.0 agents mostly wrote `[FEATURE]` / `[FIX]` / `[DECISION]`, with tier only appearing where it actually fit (C5 pyinstaller `[T2]`, C6 cross-OS CI `[T3]`, C7 latency `[T4]`).

The vocabulary stretches to both without strain. No tier was forced where it didn't fit; no event was under-tagged.

### 2. Rule 3 traps (independence claims) are caught

The adversarial test deliberately presented four classic over-claim patterns: same-seed repeats, authority-as-evidence, single-env reproductions, single-source confirmation. The v1.1.0 agent:

- Tagged all four as T1 or T2 (default-lower held).
- Every T2 carried a CAVEAT that **explicitly named the independence failure**, not a generic "single run" hedge.
- Self-audited each CAVEAT against Rule 3 and confirmed it flagged the specific weakness.

This is the skill functioning as designed.

### 3. `read-discipline` handles empty-file cold-start correctly

Given a new project's memory.md (header only, no entries) + minimal VERSION.json:

- 2 questions whose answers were in VERSION.json → correctly extracted with cite.
- 2 questions that genuinely couldn't be answered ("most recent [DECISION]" / "what was the project doing last week") → correctly refused with precise "no entries exist" / "no historical activity" reasoning.
- 1 meta question → correctly refused.

No over-refuse. No hallucination. **First-session agents aren't blocked** — the rules still let them extract what's there.

### 4. Quantified vs v1.0.0: Pareto improvement, not trade-off

Separately measured in `v1_0_0_vs_v1_1_0_Comparison_2026-04-21.md`:
- +25 pp MUST_WRITE capture, −50 pp overclaim rate simultaneously.

This round's tests add a second data point (24/25 accuracy on a broader corpus) without retracting that delta.

## Weaknesses surfaced (this round)

### W-1 — Rule 5 ambiguity: "user preference" vs "team decision"

**Observation**: T-A1 event R8 was "advisor said use tensor-parallel format for all multi-GPU runs". The agent skipped it as "cross-project user/advisor preference". But a project-team lead saying "use format X" is a **project-team decision**, not a cross-project personal preference.

**The rule as written**: *"Cross-project user preferences (e.g. 'don't use emojis', 'prefer tabs') belong in user-level memory, not here."*

**The gap**: doesn't distinguish "preference that applies across all your projects" (→ user memory) from "decision/convention within this project team" (→ project `[DECISION]`). The emoji example is cross-project; the tensor-format example is not, but Rule 5 doesn't tell the agent that.

**Severity**: moderate. One event got mis-classified. If this rule were applied widely it would silently lose team-standard decisions. Fixable with one-sentence edit.

### W-2 — `_slugify_topic` produces empty string on CJK-only titles

**Observation**: Tested on 6 sample titles. Pure Chinese titles (`記憶傳承測試`) → `''`. Mixed (`多 Agent 協作模式`) → `'Agent'` (drops the Chinese, keeps only the Latin word).

**Severity**: moderate. If a project uses Chinese (or any non-Latin script) memory titles, `promote-candidates` produces useless "Suggested wiki topic" column. Either:
- Fallback to a short hash of the full title when slug is empty, OR
- Keep original text and only normalize whitespace.

Fixable: ~5 lines in `scripts/wiki_sync.py`.

### W-3 — `CURRENT_STATE.md` shipped but inheritance-check default ignores it

**Observation**: v1.1.0 added `templates/docs/knowledge/CURRENT_STATE.md` as the "single compiled cold-start entry". But the `inheritance-check` skill's default SOURCES list is `AI_CONTEXT.md / VERSION.json / last-5-memory / ROADMAP.md first-60`. CURRENT_STATE.md doesn't appear.

**Severity**: low-moderate. The feature exists but has no automatic consumer. If a project uses CURRENT_STATE.md, inheritance-check might falsely return "INSUFFICIENT EVIDENCE" when the answer is in CURRENT_STATE.md. Inconsistent with the "single compiled entry point" framing we shipped.

Fixable: add one line to inheritance-check Step 1 default SOURCES.

### W-4 — Adapter files are thin pointers; `example/minimal-project/CLAUDE.md` is a stale v1.0.0 snapshot

**Observation**: `AGENTS.md`, `GEMINI.md` both say "Read CLAUDE.md first". That delegation is fine **if CLAUDE.md carries v1.1.0 content**. But `example/minimal-project/CLAUDE.md` has no mention of Merge Gate, classify-evidence, harness-evaluator, read-discipline, inheritance-check, or tier vocabulary — it's a frozen post-install customization from an earlier release.

**The good news**: `templates/AGENT_RULES.md` (what becomes a fresh install's CLAUDE.md) **does** have Merge Gate. So new users installing v1.1.0 are fine.

**The bad news**:
- Existing users who already installed v1.0.0 won't get Merge Gate / new skills on upgrade. No migration mechanism.
- The example/minimal-project visible to prospective users shows v1.0.0-style CLAUDE.md, undersells v1.1.0.

**Severity for this branch**: low (doesn't break v1.1.0 shipping; new installs get full rules).
**Severity for roadmap**: high. Without a migration story, v1.1.0 rules are only visible to greenfield installs.

### W-5 — Adapter files don't mention skills directory specifically

**Observation**: `AGENTS.md` says "read CLAUDE.md first, then AI_CONTEXT.md". It doesn't point at `.agents/skills/` explicitly. A non-Claude agent that doesn't follow the pointer misses the entire skill system.

**Severity**: low. CLAUDE.md / templates/AGENT_RULES.md both explain Skills-First. But if an adapter agent stops reading after AGENTS.md (doesn't follow "read CLAUDE.md"), it's blind to skills.

Fixable: add one line to each adapter. Marginal cost, marginal benefit.

### W-6 (known unknown) — Only Claude agents tested

**Observation**: Every experiment this branch has run used `Agent(subagent_type="general-purpose")` which is a Claude agent. We have **zero measurements** on Codex / Cursor / Windsurf / Gemini under v1.1.0 rules.

**Severity**: real but unresolvable here. The install.sh creates their adapters but we can't spawn those agents from Claude Code.

**Action**: document as explicit caveat, not a fix.

## What's cheap to fix on this branch

| W | Action | Effort |
|---|--------|--------|
| W-1 Rule 5 ambiguity | Split Rule 5 into cross-project (→ user memory) vs team-convention (→ project `[DECISION]`) | 10m |
| W-2 Slugify CJK | Add hash-fallback when slug is empty | 5m |
| W-3 CURRENT_STATE default | Add to inheritance-check Step 1 default SOURCES | 5m |
| W-5 Adapter mention skills | One-line addition to AGENTS.md / GEMINI.md templates | 10m |

Total: ~30 min. Do on this branch.

## What stays open (v1.2.0+)

| W | Why defer | Priority |
|---|-----------|----------|
| W-4 example/minimal-project stale | Needs architectural decision: refresh example OR declare it "post-install customization snapshot" and make that explicit. Design Q, not edit. | P1 |
| W-4 upgrade migration | v1.2.0 should ship `install.sh upgrade` subcommand that merges new template content without clobbering customizations. Multi-hour work. | P1 |
| W-6 non-Claude adapter validation | Requires running Codex / Gemini / Cursor / Windsurf on real projects and measuring. External coordination. | P2 |

## Prioritised future roadmap (post-v1.1.0 merge)

### P1 — First 2 weeks after merge

1. **Upgrade migration** (W-4): Write `install.sh --upgrade` or equivalent — merges new template content into existing installed project without wiping user customizations. Without this, v1.1.0 only helps new installs.
2. **example/minimal-project refresh** (W-4): Either rebuild from fresh v1.1.0 install (simplest), or explicitly document it as a frozen v1.0.0-era customization snapshot (complicates README).
3. **M-3 first real-corpus rerun**: when any project has accumulated ≥20 organic memory entries, rerun the Memory_Discipline + Inheritance experiments. Promote their T2 claims to T3 if pass.

### P2 — Month 2

4. **W-6 non-Claude validation**: write a prompt-pack that a Codex / Gemini user can paste, have them run Exp 1 + Exp 2 + X-7 comparison, collect results. External dependency.
5. **W-5 skills invocation telemetry**: log which skills actually got invoked per session. If classify-evidence / read-discipline fire <1 per 10 sessions, the rules aren't reaching daily use.

### P3 — Month 3+

6. **wiki_sync cross-check for memory → wiki promotion**: when a T3 memory entry gets promoted to a `docs/knowledge/` page, verify the wiki page cites the memory entry as source.
7. **Per-project rule profile**: ML research projects may need stricter T4 discipline; docs-heavy projects may not need tier vocabulary at all. Consider a `.oaw-profile.yml` to selectively enable skills.

## Branch state

- 15 commits ahead of `origin/main`.
- `./scripts/harness_check.py` — 8/8 green throughout.
- Remaining cheap fixes (W-1/W-2/W-3/W-5) to apply in the next commit.
- Merge Gate §1 conditions 1 AND 2 both met (per `v1_0_0_vs_v1_1_0_Comparison_2026-04-21.md` + this review).

## Tier classification of THIS review's claims

Per `classify-evidence`:

| Claim | Tier | Rationale |
|-------|:----:|-----------|
| "Rules generalise across project archetypes" | `[T3]` | Two archetypes tested; both passed; + earlier OAW-adjacent corpus = 3 independent contexts |
| "Adversarial Rule-3 traps are caught" | `[T2] [CAVEAT: 4 events, single subagent]` | One run on one adversarial set |
| "Empty-memory cold-start handled correctly" | `[T2] [CAVEAT: synthetic seed memory, single spawn]` | Needs rerun on real projects |
| "v1.1.0 > v1.0.0 quantified" | `[T3]` | Parallel spawns on same corpus = 2 independent measurements |
| Six named weaknesses (W-1 through W-6) | `[T3]` | All observable by direct inspection / test; reproducible |
