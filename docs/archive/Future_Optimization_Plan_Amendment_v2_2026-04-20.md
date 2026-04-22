# Amendment v2 — Feedback v2 Integration

Date: 2026-04-20 (same-day amendment)
Status: **Amends the Confirmed Plan — applies after it, does not replace it.**
Parent document: [`Future_Optimization_Plan_Confirmed_2026-04-20.md`](Future_Optimization_Plan_Confirmed_2026-04-20.md)
New input: `GNN_explainer/.claude/worktrees/harness-v2-research/research/OAW_FEEDBACK_v2_PUBLIC.md` — 3-week production use of OAW v1.0.0 on a biomedical GNN research project.

## 0. Why This Amendment Exists

The Confirmed Plan was written with **one** integrator's feedback (SEAL_GNN).
Its cadence rule was:

> Feature work driven by a single integrator's feedback should live on a
> `study/*` / `*-preview` branch until at least one more user confirms.

**Today that second user arrived.** The GNN_explainer project submitted
detailed feedback after 3 weeks of production OAW use. It validates some
items we previously deferred, surfaces entirely new gaps, and — critically —
**re-validates two features we explicitly reverted or rejected in the
Confirmed Plan**.

This amendment re-triages **only** the items where v2 feedback changes the
calculus. Everything else in the Confirmed Plan stands as-is.

## 1. The 2-User Validation Test

| Pattern | SEAL_GNN | GNN_explainer | 2-user signal? |
|---------|:---:|:---:|:---:|
| 4-lane router | ✅ (works) | ✅ ("single biggest win", §1.1) | already shipped |
| `do_not_rerun` state machine | ✅ | ✅ (§1.2) | already shipped |
| Skills-first principle | ✅ | ✅ (§1.3) | already shipped |
| 4-segment Session End report | ✅ | ✅ (§1.4) | already shipped |
| **CURRENT_STATE / WORLD_MODEL compiled entry** | ✅ (proposed, shipped, reverted) | ✅ (built their own as `WORLD_MODEL.md`) | **YES — re-accept** |
| **Non-interactive wiki ops** | ✅ (partial: `add-experiment`, `update-state`) | ✅ (§3.6 explicit) | **YES — finish the job** |
| Wiki auto-sync from skills | ✅ | ✅ (§2.5) | **YES — re-accept** |
| Staleness detection | ✅ (implicit via "wiki goes outdated") | ✅ (§3.3 explicit subcommand) | **YES — ship lightweight** |
| Evidence tiers / [CAVEAT] | ❌ | ✅ (§3.1, §2.1) | 1 user — research |
| SSOT cross-check | ❌ | ✅ (§2.2, §3.2; documented 6-day drift incident) | 1 user + concrete incident |
| Deprecation protocol | ❌ | ✅ (§3.4) | 1 user — research |
| Merge gate convention | ❌ | ✅ (§3.5; documented untested-merge incident) | 1 user + concrete incident |
| `install.sh --add-ci` | ❌ | ✅ (§3.7) | 1 user — reject |

## 2. Decisions — New Items Only (B-series)

### ✅ B-1. Un-revert CURRENT_STATE.md template (1–2h)

**Why now**: The v1.1.0 revert on 2026-04-17 was correct *at that moment*
(single-user feedback, immediately after v1.0.0 tag). Both conditions have
changed: we now have **2 independent users** who independently **built the
same pattern** (SEAL_GNN proposed it; GNN_explainer built `WORLD_MODEL.md`
without prompting). The compiled-entry-point pattern is genuinely emergent.

**What ships**: Copy the reverted `templates/docs/knowledge/CURRENT_STATE.md`
back from the `v1.1-preview` history at commit `709c132`.

**Polish learned from the revert cycle**:
- Drop the `${...}` placeholders where the content is obvious ("what is the
  project mission" — just say "One paragraph. Example:").
- Keep §9 "Common Commands" — the most copy-pastable section per SEAL_GNN.
- Mark the template as **optional** in install.sh — users who don't need it
  shouldn't feel obligated.

**Acceptance**:
- `install.sh` into fresh tempdir drops `docs/knowledge/CURRENT_STATE.md`
- `wiki_sync.py lint --strict` correctly flags the placeholders until user fills them
- README's "What you get after install" table mentions it

### ✅ B-2. Non-interactive mode for ALL wiki commands (2–3h)

**Why now**: SEAL_GNN half-solved this (added `add-experiment`, `update-state`
in v1.1-preview → reverted). GNN_explainer §3.6 re-raises it, specifically
calling out `wiki_sync.py refresh` as still interactive. **2 users, same pain
point, different angles.**

**What ships**:
1. Un-revert `add-experiment` + `update-state` subcommands (from v1.1-preview)
2. Audit `wiki_sync.py refresh` — does it actually have interactive paths? If yes, add full CLI flag coverage.
3. Audit every other path in `wiki_sync.py` for `input(` / `read -p` / prompt patterns.

**Acceptance**:
- Every `wiki_sync.py` subcommand runs to completion with no stdin input required
- CI adds: `echo '' | wiki_sync.py <subcommand> --required-flags-only` passes for each subcommand
- Agents running overnight schedules can invoke any wiki operation

### ✅ B-3. Merge gate convention in `CLAUDE.md` (1h)

**Why now**: Only 1 user (GNN_explainer) asked, but the **incident severity
is real and generalizable**: autonomous agent merged untested infrastructure
to main. "import ok" ≠ behavior-ok is a universal pattern for any AI-assisted
codebase, not ML-specific.

**What ships**: Add a `## Merge Gate` section to `templates/AGENT_RULES.md`:

```markdown
## Merge Gate — Forbidden To Merge Untested Infrastructure

Infrastructure code merges to `main` only if one of:

1. An end-to-end test passes in the worktree (not just `import ok`)
2. Quantified improvement vs current `main` baseline
3. Explicit user authorization for experimental scaffold

"Smoke test passed" proves no crash, not benefit. A passing `py_compile`
or `harness_check` is necessary, not sufficient.
```

**Acceptance**:
- Section present in `templates/AGENT_RULES.md` and root `CLAUDE.md`
- Mentioned in CHANGELOG
- No code change — this is a protocol convention

**Why not scope this wider**: The 3-gate wording is deliberately generic. ML
teams read "E2E benchmark"; webapp teams read "E2E test suite". Same rule.

### ✅ B-4. `wiki_sync.py cross-check` subcommand (3–4h)

**Why now**: Only 1 user (GNN_explainer) asked, but the **bug class is
concrete and costs time** (documented 6-day drift between VERSION.json and
WORLD_MODEL.md). A narrow cross-checker is cheap insurance.

**What ships**: New subcommand that verifies specific declared facts appear
identically across files. Configurable via frontmatter annotation:

```yaml
---
id: Performance_Baselines
title: Performance Baselines
page_type: topic
ssot_mirrors:
  - VERSION.json:benchmark_snapshot.summary
  - AI_CONTEXT.md:Current Baselines
---
```

Then `wiki_sync.py cross-check` walks the graph, extracts the mirrored
value from each location, and reports mismatches.

**Scope discipline**: **Do not** try to make this a general-purpose fact-
verifier. Only check values explicitly declared in frontmatter. No NLP.

**Acceptance**:
- Subcommand returns 0 when mirrors match; non-zero + line diff when they don't
- At least one OAW knowledge page uses it as a dogfood example
- Documented in `Wiki_Sync_Guide.md`

### ✅ B-5. `wiki_sync.py stale` subcommand (1h)

**Why now**: Taiwan.md's lint already added stale-page warnings. GNN_explainer
§3.3 asks for a **dedicated subcommand** that can be run ad-hoc with a
configurable threshold. Low cost because the underlying check exists.

**What ships**:
```bash
python3 scripts/wiki_sync.py stale                 # default --threshold 30
python3 scripts/wiki_sync.py stale --threshold 60
```

Reuses the same date-parsing and page-loading already in `lint`.

**Acceptance**:
- Prints one line per stale page: `path | last_updated | age_in_days`
- Exit code 0 always (stale-ness is informational, not an error)
- CONTRIBUTING.md mentions it in the "periodic maintenance" section

## 3. Decisions — New Research Items (R-series continuation)

### 🔬 R-5. Evidence-tier vocabulary — ML-specific or general? (Week 7, 3-day time box)

**Question**: GNN_explainer's §3.1 proposes `T1 WIP / T2 Observation /
T3 Confirmed / T4 Baseline / T5 Frozen`. This makes sense for any project
with **uncertain measurements**. But does a web-app repo with a "login bug
worked around" entry benefit from the same 5-tier scheme?

**Decision criteria**:
- ✅ If the tier vocabulary generalizes to at least 2 non-ML scenarios → ship as skill
- ❌ If it's inherently tied to statistical uncertainty → ship as **optional** `.agents/skills/classify-evidence-ml.md` with explicit "ML research only" tag
- 🔬 If borderline → collect one more user's take before committing

**Why this is Research not Accept**: 1 user, and the framing is inherently
ML-shaped. Premature generalization is the original mistake we reverted
v1.1.0 for.

### 🔬 R-6. Deprecation protocol — skill vs convention? (Week 8, 2-day time box)

**Question**: GNN_explainer §3.4 proposes a `[DEPRECATED YYYY-MM-DD]` marker
pattern. Design question: should this be a **skill** (invoked via trigger
"mark this as deprecated") or a **convention** documented in
`CONTRIBUTING_WIKI.md`?

**Decision criteria**:
- Skill if: deprecation has a repeatable multi-step workflow (find entry,
  move it, write replacement pointer, update cross-links)
- Convention if: it's one markdown section people type by hand

**Why this is Research not Accept**: 1 user, and wrong design makes it
ceremonial. Want to see the workflow once before committing.

## 4. Decisions — New Rejected Item

### ❌ X-4. `install.sh --add-ci` flag (GNN_explainer §3.7)

**Rejection rationale**:
- 1 user ask, no incident
- Users can copy OAW's CI to their project with `cp -r OAW/.github/workflows my-project/.github/`
- Building installer plumbing for "one extra convenience" is premature automation
- The current `install.sh` already does one job (copy harness). Bolting on optional-component flags starts it down the configuration-menu path

**Reactivation**: if 3+ users ask, revisit with a broader `install.sh
--profile=<minimal|full|ci>` design instead of per-component flags.

## 5. Items in Confirmed Plan That Do NOT Change

| Confirmed Plan item | Previous decision | v2 feedback says | Still valid? |
|---|---|---|---|
| A-1 Taiwan.md merge | ✅ Accept | (silent — v2 doesn't comment) | ✅ Still valid |
| A-2 harness_check | ✅ Accept | (silent) | ✅ |
| A-3 skill frontmatter lint | ✅ Accept | (silent) | ✅ |
| R-1 evaluator skill | 🔬→ Accept | (silent; orthogonal) | ✅ |
| P2-1 Recovery pattern | 🔬 → Reject | v2's "merge gate" is **prevention**, not recovery — different pattern | ✅ Still Reject |
| P2-2 Task-state CLI | ❌ Reject | (silent — GNN didn't ask) | ✅ Still Reject |
| P2-4 Worktree skill | ❌ Defer | (silent) | ✅ Still Defer |
| P3 items | ❌ Defer | (silent) | ✅ Still Defer |

Important distinction on P2-1: GNN_explainer's merge gate (§3.5) is a
**forbidding** rule ("don't merge untested infra"), not a recovery loop
("retry failed deploys"). Same word "gate" but different layer. B-3
addresses §3.5; Recovery skeleton remains unjustified.

## 6. Revised 7-Week Calendar

Confirmed Plan was 6 weeks; v2 adds 4 weeks of B-work. Compress where possible:

| Week | Work | Source | DoD |
|:----:|------|:----:|-----|
| 1 | A-1 Taiwan.md merge + **B-3 merge gate** (1h textual) | Confirmed + Amend | v1.1.0 tag + merge gate section in CLAUDE.md |
| 2 | A-2 harness_check + A-3 skill lint | Confirmed | CI green, external contributor can run one command |
| 3 | R-1 decided (done today) + **B-2 non-interactive refresh** | Confirmed + Amend | All wiki subcommands non-interactive |
| 4 | R-1 impl: `harness-evaluator.md` skill + first real use | Confirmed | Skill passes A-3 lint, used on v1.1.0 PR |
| 5 | **B-1 un-revert CURRENT_STATE** (polished) + **B-5 stale subcommand** | Amend | Template ships, stale CLI works |
| 6 | **B-4 cross-check subcommand** | Amend | Detects the v2 documented 6-day drift class |
| 7 | R-5 evidence tiers research + R-6 deprecation design | Amend | Two decision docs; implementation if research says yes |

**Unchanged from Confirmed Plan**: R-3 (Recovery) stays deferred. R-2 (lane
audit), R-4 (JSON output) stay contingent on R-1 usage.

## 7. Updates to OAW Conventions

### CONTRIBUTING.md — release cadence

Currently (per the v1.0.0 ship):

> Feature work driven by a single integrator's feedback should live on a
> `study/*` or `*-preview` branch until at least one more user confirms.

**Amend with a concrete example reference**:

> Example: the CURRENT_STATE.md template was proposed by integrator A on
> 2026-04-17, shipped briefly, reverted under the 1-user rule, and
> **re-accepted 2026-04-20** when integrator B independently built the same
> pattern (`WORLD_MODEL.md`). See
> `docs/archive/Future_Optimization_Plan_Amendment_v2_2026-04-20.md` for
> the re-triage.

### CLAUDE.md / templates/AGENT_RULES.md — merge gate (B-3)

Add the Merge Gate section verbatim as specified in §2 B-3 above.

### ROADMAP.md — add B-series

Add new rows to Active Work:

```
| P1 | B-1 CURRENT_STATE.md un-revert        | Queued (Week 5) | 2-user validated |
| P1 | B-2 Non-interactive wiki full coverage | Queued (Week 3) | 2-user validated |
| P1 | B-3 Merge gate convention             | Queued (Week 1) | 1 user + incident |
| P2 | B-4 wiki_sync cross-check             | Queued (Week 6) | 1 user + incident |
| P2 | B-5 wiki_sync stale subcommand        | Queued (Week 5) | low cost, Taiwan.md built foundation |
| P2 | R-5 Evidence tiers                    | Research (Week 7) | 1 user, ML-specific |
| P2 | R-6 Deprecation protocol              | Research (Week 8) | 1 user, design-dependent |
| ❌ | X-4 install.sh --add-ci               | Rejected       | users can copy manually |
```

### CHANGELOG.md — Unreleased section

Nothing to change yet. B-items aren't committed; their CHANGELOG entries
get written as each one ships.

## 8. Anti-Pattern Audit

Verify this amendment obeys the Confirmed Plan's own discipline:

| Rule | This amendment's compliance |
|------|-----------------------------|
| "Don't ship minor on single-user feedback" | ✅ B-1/B-2 require 2 users. B-3/B-4 are single-user but gated by documented incident severity. |
| "Ask who the consumer is" | ✅ Every B-item has a concrete consumer (users who already built the pattern themselves). |
| "Don't let audit scores become checklist obligation" | ✅ This amendment is user-driven, not audit-driven. |
| "Prevention ≠ Recovery" | ✅ B-3 is prevention (forbidding rule), not a retry/rollback loop. R-3 Recovery stays deferred. |

## 9. What Still Requires Judgment

Three open questions where I (the drafter) don't know the right answer and
need the maintainer's call:

1. **1-user-plus-incident threshold**: B-3 and B-4 are single-user asks but
   have documented incidents. Should the cadence rule be amended to "2 users
   OR 1 user + concrete incident > 2h impact"? Current stance: yes, codify
   it, but needs a vote.
2. **Timing of un-revert**: B-1 (CURRENT_STATE un-revert) can be Week 1
   (adjacent to Taiwan.md merge, re-ships v1.1-preview content together) or
   Week 5 (as currently scheduled). Week 1 is lower cost but less demonstrably
   "we learned from the first attempt". Week 5 is more disciplined but
   artificially delays a validated win.
3. **Merge gate wording tone**: The current B-3 text is stern ("forbidden to
   merge"). Could soften to a checklist ("before merging, confirm one of
   three gates"). The sterner version matches GNN_explainer's proposed wording;
   the softer version invites contributor pushback less.

My default recommendations: (1) yes with that wording, (2) Week 5 for
discipline, (3) keep stern — softening defeats the purpose.

---

## Appendix A — Per-Item Implementation Hints

### B-2 Non-interactive refresh — concrete audit list

Paths in current `wiki_sync.py` to audit:

```bash
grep -n 'input(\|raw_input\|read -p' scripts/wiki_sync.py
```

(To be run during Week 3.)

### B-4 Cross-check — minimum viable schema

Simplest path: declare one `ssot_mirrors` list per page in frontmatter;
dot-path into JSON files; simple substring match into markdown files.
No YAML parsing, no fancy path syntax, no cross-page joins.

### R-5 Evidence tiers — generalization test

Before committing, try the 5-tier vocab on 3 non-ML repos:
- A webapp (login bug discovered → reproduced in 2 environments → fixed)
- A CLI tool (perf regression found via bench → patch lands → rollback)
- A docs repo (claim edited → verified with citation → canonical source)

If 2/3 fit cleanly, ship as general skill. If <2, ship as ML-specific.

---

*Amendment v2 drafted 2026-04-20 after 2nd integrator feedback.
Lives alongside Future_Optimization_Plan_Confirmed_2026-04-20.md.
Not yet approved for implementation; the B/R/X items are proposals.*
