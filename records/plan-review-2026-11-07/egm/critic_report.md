# Stage 7: Critic Review Report

**Target:** `docs/plans/v2.0.1-execution.md` (FeatureRange, lines 1-91)
**Standards:** `egm-design` and `egm-structural` use `feature-spec-standard.md`; `egm-style` uses its persona only.
**Loop note:** One review round was run. The user's instruction for this run was "do not apply fixes to the design", so the `egm-resolve` hand-off and the re-audit rounds were not performed. The findings below are open.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-structural` | completed |
| `egm-style` | completed |

Raw counts:
* `egm-design`: 1 Blocker, 8 Major, 4 Nit.
* `egm-structural`: 1 Blocker, 7 Major, 8 Nit.
* `egm-style`: 0 Blocker, 10 Major, 21 Nit.

After deduplication: 2 Blockers, 12 Majors, 14 Nits (the style nits are grouped).

## Prioritized Findings

### CR-1. The deep review is triggered after the work is done, but deep mode needs a plan before implementation. Severity: Blocker
* **Reviewer Lens:** `egm-design` (B1)
* **Affected Scope:** Lines 8, 43, 83 (and W1 line 108)
* **Discrepancy:** The new AGENTS.md line is "做完改動用 `oaw-review`" (run `oaw-review` after making changes, line 83). The depth is picked "依改動" (from the change, line 8). Deep mode is "plan mode → EGM reviews the plan → implement" (line 108). If the classification runs only on a finished diff, the deep trigger fires after implementation. EGM would then review a plan written after the fact.
* **Rationale:** EGM's measured gain came entirely from catching gaps in plans before implementation (`evidence/egm-selftest-2026-11-06-RESULT.md:42-45`). `oaw_mode.py` can already classify planned paths before any edit (`scripts/oaw_mode.py:402-403`, `--paths`).
* **Recommendation:** Classify twice. First, before the change, on the intended paths; if that says deep, enter plan mode and run EGM before editing. Second, after the change, on the actual diff; escalate if the diff turns out to be deep.

### CR-2. No "alternatives considered" section, and the cheapest credible deep-review alternative is missing. Severity: Blocker under the feature-spec standard
* **Reviewer Lens:** `egm-structural` (1), `egm-design` (M3)
* **Affected Scope:** Lines 5-28, 70-90 (the gap is document-wide)
* **Discrepancy:** `feature-spec-standard.md:15-18` requires the rejected designs and the reasons they were rejected. Several choices have neither:
  * one `oaw-review` skill, compared with today's `suggest`/`show` flow or a hook;
  * rebuilding features into `code_index.py`, compared with plugging in the original tool, which D26 makes the default (`DECISIONS-D21-D31.md:91-92`);
  * the one-question, three-option `add` flow;
  * full EGM in deep, compared with a cheaper review.

  The evidence shows that the leaked one-line checklist P reached 3/3 at 1x cost (`validation-2026-11-07-RESULT.md:28`; `egm-selftest:18`). It also shows that all of EGM's gain came from its implementation-readiness stage (`egm-selftest:42-45`). Yet a readiness-only arm, or one that uses a generic checklist, is not considered. Separately, X2's S arm is defined as a reviewer of the "diff 和測試" (diff and tests, line 107), while X2's cases are design documents (line 234). So the S result would not validate the standard mode that ships.
* **Recommendation:** Add a "考慮過的替代方案" (alternatives considered) table. Add a readiness-only or generic-checklist arm to X2.

### CR-3. The code-map evidence row misstates the measurements. Severity: Major
* **Reviewer Lens:** `egm-design` (M1), `egm-structural` (6), `egm-style` (M6); also Stage 5 ZO-5
* **Affected Scope:** Lines 12, 37
* **Discrepancy:** Line 37 says all three maps "都少走步" (cut steps), at 0.23-0.65x native tool calls. The comparison shows otherwise:
  * graphify was at 0.88 / 0.76 / 1.00 / 1.04 (`evidence/codemap-comparison-2026-11-06.md:28,32,36,40`);
  * OAW was at 1.04 on Opus 4.8 (`:36, :57`);
  * the 0.23 is codegraph on VS Code in V8 (`validation:113`);
  * the comparison's own summary says graphify won on neither axis (`:6`).

  Line 12 claims to absorb graphify's "量得到的長處" (measured strengths), but none were measured.
* **Rationale:** This row is the basis for "maps are efficiency tools first". X1 could also promote a map that costs more tokens, on tool calls alone (line 233).

### CR-4. "Zero unfounded claims" is a single-grader number. Severity: Major (conditional on which arm the V4 counts cover)
* **Reviewer Lens:** `egm-design` (M2), `egm-structural` (7), `egm-style` (M8)
* **Affected Scope:** Line 34
* **Discrepancy:** The 0 comes from the self-test's E arm, with one Opus grader (`egm-selftest:17, 66`). The V4 cross-family row "EGM 偵測" reports 1 (Opus) / 7 (Codex) unfounded claims (`validation:71`). The plan's own rule counts a claim only when both families agree (line 227).
* **Recommendation:** Name the grader and the arm. The "3/3 對 1/6" figure also needs its unit: runs in the `events` case that caught both main defects.

### CR-5. Auto-running deep has no cost or quota guard. Severity: Major
* **Reviewer Lens:** `egm-design` (M4)
* **Affected Scope:** Lines 9, 42, 55-56, 86
* **Discrepancy:**
  * 56% of code commits classify as deep (`validation:102`).
  * EGM costs about 1.1M tokens per run, and one run hit the 5-hour cap (`egm-selftest:74-75`).
  * The harness rule makes any change to `templates/`, AGENTS.md or a workflow deep (`oaw_mode.py:231-237`).
  * V7 is retrospective, on one repo (`validation:103-106`).

  "注意 deep 的比例" (watch the deep ratio) is not a mitigation.
* **Recommendation:** Set per-session or per-day caps on deep runs, show a cost notice before each run, and define what happens when a usage limit cuts a run off. Add these to §7.

### CR-6. Cross-family review sends user code to a second vendor without consent. Severity: Major
* **Reviewer Lens:** `egm-design` (M5)
* **Affected Scope:** Lines 10, 76 (W1 lines 107, 117-118)
* **Discrepancy:** An auto-invoked skill uses `codex review` whenever the CLI is present. This ships diffs to another provider and bills another subscription.
* **Recommendation:** Make cross-vendor review a per-project opt-in at `init`/`migrate`. Default to a same-family zero-context reviewer. Add this to §7.

### CR-7. The AGENTS.md change is under-specified and would leave contradictory lines. Severity: Major
* **Reviewer Lens:** `egm-design` (M6), `egm-structural` (9), `egm-style` (nit 19); also Stage 6 CO-N9
* **Affected Scope:** Line 83
* **Discrepancy:**
  * The rendered file is 25 lines with EGM and 23 without, not 26 (`example/minimal-project/AGENTS.md`; `scripts/oaw.py:188-210`).
  * The template's line 13, "Run the full EGM review only when `suggest` says deep", also depends on `suggest`.
  * Line 5, "EGM keeps its explicit invocation policy", contradicts Q2.
  * Dropping `--range BASE..HEAD` (`templates/AGENTS.md:11`) makes `suggest` on a clean tree return light (`oaw_mode.py:121-126, 291-292`).
* **Recommendation:** Give the exact before/after lines for both template branches (with and without EGM). Have `plan` pick the base commit itself.

### CR-8. Outcomes that depend on later tests or decisions are stated as certain, and contradict each other. Severity: Major
* **Reviewer Lens:** `egm-structural` (4), `egm-design` (N2, N3), `egm-style` (nit 15, nit 20)
* **Affected Scope:** Lines 9, 11, 56-57, 83-86
* **Discrepancy:**
  * The "no restart" promise (line 11) depends on the spike (line 121).
  * Deep running EGM (lines 9, 56, 86) can be reversed by X2 (line 234).
  * G3 (line 57) says `oaw-codemap` is auto-invoked only after X1 passes. §4 (line 84) says it is auto-invoked by default and downgraded on failure. It also ignores X1's "CLI only" outcome.
  * The one-line policy (line 83) can be dropped by X3 group B.
* **Recommendation:** Add a "depends on" column to §4, and mark these summary bullets as conditional.

### CR-9. The summary's budget does not add up. Severity: Major
* **Reviewer Lens:** `egm-structural` (5), `egm-style` (M3), `egm-design` (N4)
* **Affected Scope:** Line 26 (and lines 239-244, 252-255)
* **Discrepancy:** The experiments add up to about 19.8M (7 + 11 + 1.5 + <0.3 + 0). The other 2.7M is W3 testing plus the two EGM reviews. The schedule in §7 adds up to about 21.2M; the 1.2M plan review appears in no step. Q3 asks the owner to approve this number.

### CR-10. D32 is used as if it were already in force. Severity: Major
* **Reviewer Lens:** `egm-style` (M1), `egm-structural` (8), `egm-design` (N1); also Stage 6 CO-2
* **Affected Scope:** Lines 22-23, 28, 44
* **Discrepancy:** The decision log ends at D31 (`DECISIONS-D21-D31.md:161`). The six rules are proposals that need the owner's approval (`validation:123`). Line 23 lists only 3 of the 6. Line 22 also says X5 gates defaults, but X5 does not block release (line 237).

### CR-11. `remove` and option ② inherit a known incomplete-removal defect. Severity: Major
* **Reviewer Lens:** `egm-design` (M7); related to Stage 5 ZO-1
* **Affected Scope:** Lines 15, 45, 89
* **Discrepancy:** Both supported removal paths leave `.oaw/integrations/egm` (66 files) behind, and leave AGENTS.md saying EGM is included (`egm-selftest:57-63`, "這要另外修" (needs a separate fix)). The plan never schedules this fix, but W3 promises byte-identical restore.

### CR-12. G6 migration scope leaves out the only released installed base (v1). Severity: Major
* **Reviewer Lens:** `egm-design` (M8)
* **Affected Scope:** Lines 3, 60
* **Discrepancy:** 2.0.0 was never released (line 3), yet G6 targets only 2.0.0 → 2.0.1. `docs/UPGRADING.md:7-33` documents a v1 → v2 path that this plan never re-validates.

### CR-13. §4 is a file list, not an architecture, and there is no problem statement or traceability from the owner request to goals, work items and tests. Severity: Major
* **Reviewer Lens:** `egm-structural` (2, 3)
* **Affected Scope:** Lines 5-60, 79-90
* **Discrepancy:**
  * There is no data flow for `oaw-review` or for `oaw add`. `catalog.py` already has its own `add`/`list`/`remove` (`catalog.py:2519, 2523, 2568`), and the plan doesn't say which layer owns state.
  * `OWNER_REQUEST.md` is never cited.
  * G1-G6 are not mapped to W0-W6, X1-X5 or Q1-Q3, and G4 and G6 have no acceptance test.

### CR-14. "Subtraction" framing vs. the G5 budget, and other overstatements in the summary. Severity: Major
* **Reviewer Lens:** `egm-style` (M4, M5, M7), `egm-structural` (10, 11, 12), `egm-design` (N2)
* **Affected Scope:** Lines 16-18, 44, 59, 84
* **Discrepancy:**
  * "模型看得到的規則不增加" (model-visible rules do not increase) cannot be measured.
  * G5 allows +600 tokens, and two auto-invoked skill descriptions are added.
  * "400 行縮成一頁" (400 lines shrink to one page): W4 only replaces the opening of the file.
  * Line 44, "4 題 × 3 次的解析度差" (4 questions × 3 runs has poor resolution), contradicts its source, "覆蓋率的解析度不差" (coverage resolution is not poor, `validation:16, 40-42`). The real problems are noisy false-statement counts and zero-variance intervals.

### Nits (grouped)
* **CR-N1:** The verdict labels (不差 / 未定 / 一樣好 / 更懂 / same) are inconsistent between principle 6 (line 77) and the X1 rule (line 233). Define the four classes once. (style M9; graded Nit here because the fix is a definition.)
* **CR-N2:** Project jargon is undefined (吸收, 試吃, 主場, 家族, 配方, 帳本), and some of it reaches users. (style M10; duplicates Stage 6 CO-4.)
* **CR-N3:** The source labels V1-V8 / "11-06" are not mapped to files (lines 32-50), and the evidence paths have no commit pins.
* **CR-N4:** Row 38 ties graphify's truncated subgraphs to Haiku, but the source ties them to weaker models and Opus 4.8 (`codemap-comparison:59, 81`).
* **CR-N5:** `oaw add` (line 14) vs `python3 scripts/oaw.py add` (lines 89, 157). No `oaw` executable exists.
* **CR-N6:** "以標準函式庫為主" (mainly the standard library, line 64) weakens the repository rule (`AGENTS.md:8`).
* **CR-N7:** "3 個動詞" (three verbs, lines 45, 58) leaves out `/oaw-add`.
* **CR-N8:** G2 calls X2 a test of "EGM 的正確性" (EGM's correctness, line 56). X2 measures detection gain and false positives.
* **CR-N9:** §4's 2.0.0 column leaves out the opt-in `oaw-wiki` and `oaw-improve` skills (`templates/AGENTS.md:29-30`).
* **CR-N10:** "（不佔 context）" (takes no context, line 85) is asserted without a measurement.
* **CR-N11:** Relative date "這幾天" (these past few days, line 30). Generalizing from one skill (court) in line 41. "最有用" (most useful) rests on one question (line 40).
* **CR-N12:** The invocation verbs vary (叫用 / 呼叫 / 啟動 / 叫起來), and "自己" has four senses.
* **CR-N13 (style preference):** Bold pseudo-headings and `<br>•` bullets in tables.
* **CR-N14 (style preference):** Colloquial slogans (lines 70-75).

## Claims the reviewers checked and found consistent
* EGM 28x tokens and 12x time.
* p=0.048; kappa 0.97 vs 0.46-0.62.
* codegraph 0.73x tokens, 15 vs 7 / 24 vs 12 false statements, 8m54s / 2.2 GB / 12.7 GB.
* `callers` 7 vs 31 tool calls.
* court 0/8; D31 adherence 2/2.
* V7 41/81, 6/151, 3.5x, 56%.
* `SKILL_INTAKE.md` is 400 lines.
* 7 EGM skills, 9 Claude agents.
