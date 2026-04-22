# R-3: Skill Failure Modes Analysis

Date: 2026-04-20
Status: **Decided — pivot away from original Recovery framing. Defer both paths.**
Research budget: target 3 days in original plan; collapsed to 1 session after
the evidence disqualified the original framing.

Source of the research question:
- [Harness_Engineering_Quality_Audit_2026-04-20.md](Harness_Engineering_Quality_Audit_2026-04-20.md) §6 — "No generic retry/backoff rule for flaky commands or API failures. No rollback workflow exists."
- [Future_Optimization_Plan_Confirmed_2026-04-20.md](Future_Optimization_Plan_Confirmed_2026-04-20.md) R-3

## The Question We Had To Answer

The original R-3 hypothesis was:

> Add a **Recovery section** to the skill template: retry conditions, retry
> budget, unsafe-to-retry operations, root-cause record.

And the guardrail was:

> Don't design a generic Recovery skeleton before real failure cases
> accumulate — premature abstraction.

So the research task was: **enumerate real OAW failures and check whether
the Recovery framing actually fits them.**

## Corpus: 9 Real Failure Cases

Assembled from three sources:

1. `git log` of `lihowfun/O-ALL-WANT` main branch (all fix/revert/bug commits)
2. `.agents/memory.md` at OAW repo root (gitignored, local-only history)
3. `docs/archive/` review reports (OAW_README_REFRESH_REPORT, Repo_Health_Review)

| # | Source | What Happened | Classification |
|---|--------|---------------|----------------|
| F1 | `f91c824` / memory.md 2026-04-17 | `install.sh $(pwd)` overwrote framework's own root files when run from repo root | **Logic bug (unsafe default)** |
| F2 | `7ccbdf7` + `1738e28` | v1.1.0 shipped and reverted within 24h — premature minor bump on single integrator's feedback | **Process failure (release judgment)** |
| F3 | `769bd1a fix(wiki_sync): restore strict placeholder checks` | Strict mode silently lost in a refactor | **Regression (feature removed accidentally)** |
| F4 | `74a898e fix: recreate VERSION.json with correct content` | VERSION.json corrupted / had wrong content | **Data corruption** |
| F5 | `8aa60f4 fix: metadata consistency + honest design sources` | Metadata drift + overclaimed provenance in design sources | **Documentation drift** |
| F6 | `540fafb fix(readme): use 'multi-agent workflows' for accurate scope` | README scope language too broad, implied features we didn't ship | **Documentation accuracy** |
| F7 | `ec5a7ff fix(readme): replace ToS-violating 'shared accounts'` | README phrasing violated platform ToS | **Compliance risk** |
| F8 | `5d68159 docs(ux): first-run demo + fix existing-project agent prompt` | Agent prompt worked for brand-new projects but not existing ones | **UX / template assumption mismatch** |
| F9 | `OAW_README_REFRESH_REPORT.md` | Public README presentation hid architecture strengths ("template regression" noted internally) | **Template regression** |

Threshold from the confirmed plan:
> ✅ 累積 ≥ 5 個真實案例 + 跨 ≥ 2 類 → 基於實例設計 Recovery section
> ❌ 案例 < 5 或過於均質 → 不做通用骨架,改成單一 skill 的 case study

9 cases across 5 classifications. Formally: passes the "≥5 cases, ≥2 classes" gate.

## The Finding That Changed The Decision

**Every single case was caught by human review AFTER the change landed, and
every fix required either a code change or a process change.** None of them
match the "runtime retry / rollback / repair-loop" pattern that the original
Recovery section was going to standardize.

Breaking down by whether the Recovery framing would have helped:

| # | Could Recovery skeleton have helped? | What would have helped |
|---|:-:|-----------------------|
| F1 | ❌ No | Preventive check in `install.sh` before it copies files |
| F2 | ❌ No | Release cadence rule (don't minor-bump on single feedback) |
| F3 | ❌ No | Test coverage for strict mode |
| F4 | ❌ No | Schema validation on `VERSION.json` |
| F5 | ❌ No | Lint on metadata / provenance claims |
| F6 | ❌ No | Review of scope language |
| F7 | ❌ No | ToS-awareness checklist during README review |
| F8 | ❌ No | Prompt test against existing-project target |
| F9 | ❌ No | Review of public-facing surface |

**0 / 9** cases would have benefited from retry / backoff / rollback
conventions. **9 / 9** needed preventive measures (CI check, lint, schema,
review discipline).

This is a decisive signal. The Recovery framing — imported from the
Harness Engineering article — addresses a failure mode OAW does not yet
have. The real failure mode is **"change landed, no reviewer caught it"**.

## Decision

### 1. Do NOT ship a Recovery section in the skill template (for now)

Rationale: designing for 0 observed cases is exactly the over-engineering the
confirmed plan anti-patterns warn against. Solving imagined problems is worse
than doing nothing — it spreads noise across the skill surface and anchors
later designs on the wrong axis.

### 2. Do NOT ship a "Failure Modes" catalog either (for now)

This was my fallback. It would make every skill declare its failure modes.
But the failures we have aren't skill-scoped — they're repo-wide (install
script, README scope, release cadence, schema drift). Forcing per-skill
declarations is again answering the wrong question.

### 3. Instead: redirect the R-3 energy to what the corpus actually shows

The 9 failures cluster around **3 real meta-patterns**:

| Meta-pattern | Count | Defense that would close it |
|---|:-:|---|
| Content drift at public surfaces (README, VERSION.json, metadata) | F4 + F5 + F6 + F7 + F9 = 5 | **Independent review before landing** — exactly what the R-1 evaluator skill does. |
| Missed behavioral regression in refactors | F3 + F8 = 2 | **Frontmatter/behavior contract tests** — the new skill lint (A-3) + future per-skill acceptance tests. |
| Unsafe defaults in shipped tools | F1 = 1 | **Self-protection probes** (like the `install.sh` self-install refusal, already shipped). |

**R-1's subagent evaluator skill already addresses the biggest cluster** (5 of
9 failures). **A-3's skill frontmatter lint partially addresses the second.**
**F1's mitigation already shipped** as the self-install refusal.

So **R-3's real answer is**: the work is mostly already being done through
other accepted items. There's no separate deliverable needed here.

### 4. Reopen conditions (when to revisit)

Collect a second round of failures after 3 months. Revisit if:

- **≥ 3 new cases** emerge that are specifically runtime flakiness / network
  retries / rollback scenarios. Current count: 0.
- **A single skill** accumulates ≥ 2 failure cases in its own execution path.
  Then build a Recovery section *for that skill only*, not the template.

Until then, the skill template stays recovery-free.

## Update To Confirmed Plan Calendar

| Week | Original (confirmed plan) | After R-3 decision |
|:---:|---------------------------|--------------------|
| 5 | R-3 Recovery research | **R-3 done (this doc).** No new deliverable; redirect the slot. |
| 5 | — | **Suggested new use of slot**: first real use of the evaluator skill from R-1, run against the LLM-wiki merge PR or any Week 4 work. |
| 6 | R-3 結論執行 OR 留白接 community feedback | **留白接 community feedback** (R-3 has nothing to execute). |

This gives Week 5 + Week 6 back to the calendar as **slack** — which the
anti-patterns section already flagged as valuable.

## Roll-up To The Six-Layer Audit Score

Audit §6 "Constraints + Recovery" is the layer where R-3 was supposed to
lift the score. Honest update:

- Score stays at **5.5 / 10**, as in the confirmed plan's realistic target
  (we projected 6.0 ± 0.3)
- The gap is real but **the right response is "not yet"**, not "ship a fake fix"
- Future score gain comes from R-1 evaluator coverage over time, not from
  a skill template section

## Connecting Back To The Original Harness Engineering Article

The audit's §6 Recovery recommendation is correct **as a general harness
design principle**. OAW hasn't yet grown into needing it. Shipping an
unused Recovery section now creates documentation debt; waiting for a
concrete failure keeps the skill template honest.

The equivalent of "Recovery" for OAW today is:
- **Prevention via independent review** (R-1 evaluator)
- **Prevention via structural lint** (A-3 skill lint)
- **Prevention via self-refusal** (install.sh pattern)

These are the layers OAW can credibly claim to have. Recovery itself
remains honestly marked **"not yet"**.

## Anti-Pattern Reaffirmed (from confirmed plan §6)

> **對每個 P1 項目,先問「這東西的消費者是誰」。如果答案是"未來某個尚未存在的
> evaluator"或"某個還沒發生的使用場景",立刻降級為研究項。**

R-3 originally framed Recovery for "future flaky runtime scenarios that
don't currently exist in OAW." That's exactly the pattern the rule warns
against. Downgrading was correct; deferring after research is consistent.

---

*Decided 2026-04-20. Supersedes the "R-3 research" placeholder in the
confirmed plan. No skill-template change ships. Week 5/6 slots return to slack.*
