# Consolidated Review Report: OAW 2.0.1 Execution Plan

**Target:** `docs/plans/v2.0.1-execution.md` (325 lines, Traditional Chinese)
**Mode:** Uninterrupted full flow (Stages 5-9). The design was not edited, by the user's instruction.
**Semantic split:** FeatureRange 1-91; DetailedRange 92-325 (boundary: `## 5. 工作項目`).
**Owner request checked against:** `evidence/OWNER_REQUEST.md`.
**Date / platform:** 2026-11-07, Linux, Claude Code. Reviewers were fresh `egm:*` subagents with `omitClaudeMd` and read-only tools.

## Stage reports and reviewer status

| Stage | Report | Reviewers | Status |
| --- | --- | --- | --- |
| 5 Initial Zoom Out | `review_out/zoom_out_report.md` | egm-zoom-out | completed |
| 6 Comprehension | `review_out/comprehension_report.md` | egm-comprehension | completed |
| 7 Critic | `review_out/critic_report.md` | egm-design, egm-structural, egm-style | completed (3/3) |
| 8 Intermediate Zoom Out | `review_out/intermediate_zoom_out_report.md` | egm-zoom-out | completed |
| 9 Implementation Readiness | `review_out/implementation_readiness_report.md` | egm-implementation-readiness, egm-codebase-details, egm-style | completed (3/3) |

**What this run did not do:**
* **One round per stage.** Stages 7 and 9 each ran one review round. The `egm-resolve` hand-off and the re-audits were skipped because the user said not to apply fixes, so every finding is open.
* **Not verified:** the statistics code and `xgrade.py` that the plan says live on the `records` branch, because that branch is not in the workspace.

## Overall verdict

**Not ready to start work.**

**Where the plan holds up.** It covers all three owner requests:
* a harness with fewer rules, built-in EGM and a code map;
* an absorption SOP;
* `add A B C` with three options.

Most cited numbers match the evidence:
* EGM 28x tokens and 12x time.
* Fisher p=0.048; kappa 0.97 vs 0.46-0.62.
* codegraph 0.73x tokens and twice the false statements; 8m54s / 2.2 GB / 12.7 GB.
* `callers` 7 vs 31 tool calls; court 0/8; D31 adherence 2/2.
* V7 41/81, 6/151, 3.5x, 56%.
* `SKILL_INTAKE.md` 400 lines; 7 EGM skills, 9 Claude agents.
* Budget totals of about 23M / 26M.

**Why it is not ready.**
1. Three core features rest on behavior the current code forbids or does not have:
   * the user-install route through the catalog;
   * TS/JS call graphs;
   * an agent running EGM unattended before implementation.
2. Several §1 claims that motivate the design overstate the evidence.
3. X2, the experiment that decides the owner's main question ("正確很高的話值得", worth it if accuracy is high), is under-budgeted and compares against the wrong arm.

## Action items by priority

### 🔴 Blockers

**A1. Decide and re-scope what the user install route (W3) may install.**
* **Lines:** 89, 157-176, 184, 192-193, 284.
* **Problem:** The plan says `add` "wraps the existing catalog", installs untasted skills at no token cost, installs hooks, MCP servers and scripts after a consent checkbox, and restores byte-for-byte. The catalog forbids each of these:
  * untasted text is held (`scripts/catalog_core.py:1259-1263`; `docs/SKILL_INTAKE.md:306, 317`);
  * "OAW never installs hooks or MCP servers" (`catalog_core.py:1268-1270`);
  * only `.md`/`.txt` inside a skill folder can be installed (`scripts/catalog.py:1391-1404`; `catalog_core.py:78`);
  * builds deny `.mcp.json`, `.claude.json` and settings (`catalog.py:1374-1375`);
  * same-name skills are refused (`catalog.py:1869-1870`);
  * D21 tier C and D29.3 require the owner for runtime code (`DECISIONS-D21-D31.md:21-23, 148-150`).
* **Action:**
  * Add owner question Q4: do D17/D21 apply to user installs?
  * Choose one of two scopes: (a) text and agent definitions only, with hooks and MCP servers listed as "not installed by OAW"; or (b) a separately designed installer with its own restore.
  * Add the EGM-removal fix (`egm-selftest:57-63`) as a prerequisite work item.

**A2. Make the deep flow plan-first and runnable without a human.**
* **Lines:** 8, 43, 83, 108, 114-121.
* **Problem:** The plan runs `oaw-review` "after the change" (line 83), but deep needs a plan reviewed before implementation (line 108). EGM's measured gain came from catching plan gaps (`egm-selftest:42-45`).
  * Upstream `egm-review` stops for a human at intake and at every stage gate (`vendor/egm/skills/egm-review/SKILL.md:85-113, 213-241`).
  * The bridge requires keeping those checkpoints (`templates/.agents/skills/egm-review/SKILL.md:5,16`).
  * The plan gives no preset, no inputs, no approver, no round cap and no report directory.
  * Self-entry into plan mode is assumed. Codex plan mode is unmapped (`scripts/oaw_mode.py:318-319, 343, 357`).
* **Action:**
  * Classify the planned paths first (`suggest --paths`, `oaw_mode.py:402-403`).
  * Write the plan to a file and run EGM with the `uninterrupted` preset.
  * Write reports to a gitignored folder, define the auto-resolve policy and round cap, then implement and re-classify.
  * Drop the plan-mode dependency, or add it to the spike.
  * List the code and tests to change (`oaw_mode.py:357`; `tests/test_oaw_mode.py:319, 413`).

**A3. Rescope the TS/JS work in W2 and X1.**
* **Lines:** 137, 139, 147-148, 233, 263.
* **Problem:** `callers`, `affected` and `path` are Python-only today (`scripts/code_index.py:1525-1528, 1556-1558, 1594-1596`). The 11-06 `callers` evidence is ERPNext (Python). So VS Code Stage 0(b) recall, the call-graph ranking in `overview`, and X1's VS Code cell all depend on a new engine the plan does not design.
* **Action:** Either limit 2.0.1 Stage 0 and X1 to Python, or make the TS/JS resolver its own specified work item with a gate before X1.

### 🟡 Major

**A4. Correct the §1 evidence claims.**
* **Lines:** 12, 34, 37, 44.
* **Problems:**
  * Line 37's "all three maps cut steps, 0.23-0.65x" is false:
    * graphify is at 0.76-1.04 (`codemap-comparison-2026-11-06.md:28-40`);
    * OAW is at 1.04 on Opus 4.8 (`:36, 57`);
    * 0.23 is codegraph in V8 (`validation:113`).
  * Line 12 cites graphify strengths that were never measured (`codemap:6`).
  * Line 34's "0 unfounded claims" comes from a single Opus grader. V4 shows 1/7 (`validation:71`).
  * Line 44's "poor resolution" contradicts "覆蓋率的解析度不差" (coverage resolution is not poor, `validation:16, 40-42`).

**A5. Redesign X2 to test the real decision, and size its budget correctly.**
* **Lines:** 107, 234, 244, 276, 300.
* **Problems:**
  * **Arm S doesn't match what ships.** S is a diff reviewer, while X2's cases are design documents. A new design document always triggers deep (`oaw_mode.py:246-249, 283-285`).
  * **A cheaper alternative is missing.** The leaked checklist P reached 3/3 at 1x cost (`validation:28`; `egm-selftest:18`), but no cheap readiness-checklist arm is tested.
  * **The ceiling case is kept.** `orders` is at ceiling (`validation:52`), against line 300.
  * **The budget is optimistic.** E alone is 10.2-12.9M for 9 cases (`egm-selftest:17`; `validation:87`).
  * **The Q3 fallback does not fit.** 8 cases still come to about 10M or more.
  * **The rules are unclear.** Outcomes overlap with no precedence, the metric is unnamed, and there are three different fallbacks (lines 116, 234, 264).
* **Action:**
  * Replace S with a readiness-checklist arm.
  * Drop `orders` from the analysis.
  * Ask Q3 for about 13M, or use 7 new cases.
  * Add an alternatives table (feature-spec standard).

**A6. Complete the budget and the cap rule.**
* **Lines:** 26, 229, 233-244, 252-255.
* **Problems:**
  * The second X3 that W4 requires, the deep E2E run, Opus grading (0.63M last round, `validation:143`) and question writing are not budgeted.
  * "分 5 個實驗" (split across 5 experiments) is wrong: the experiments total about 19.8M.
  * The §7 phases add up to about 21.2M.
  * Line 229's cap omits the X2 exception.
  * X1's 4th cell lands exactly on the cap.

**A7. Write complete decision rules for X1 and X3, and add a status-quo arm to X3.**
* **Lines:** 77, 198, 233, 235.
* **Problems:**
  * X1's "不差" (not worse) is undefined. It can let 未定 (undecided) become a default, against principle 6 and D29.2 (`DECISIONS:142-145`).
  * "Same quality, efficiency fails" has no rule.
  * X3 has no 2.0.0 one-line-policy arm, though that policy was followed 2/2 (`DECISIONS:180`).
  * X3's "做對" (got it right) and "一樣好" (equally good) are undefined, and there is no fail path.

**A8. Mark D32 and other conditional outcomes as conditional, and resolve the contradictions.**
* **Lines:** 9, 11, 22-23, 28, 44, 56-57, 83-86.
* **Problems:**
  * D32 does not exist yet: the log ends at D31, and the rules are proposals (`validation:123`).
  * X5 does not gate defaults (line 237).
  * G3 (line 57) and §4 (line 84) give opposite defaults for `oaw-codemap`.
  * "No restart" depends on the spike.

**A9. Add a deep-mode cost guard and make cross-vendor review opt-in.**
* **Lines:** 10, 42, 76, 107, 117-118.
* **Problems:**
  * 56% of code commits classify as deep (`validation:102`).
  * EGM costs about 1.1M per run, and a run hit the 5-hour cap (`egm-selftest:74-75`).
  * Sending diffs to a second vendor by default has no consent model.
  * The "another family" principle rests on grader agreement (kappa), not on any reviewer comparison (`validation:17-20, 65-72`).
* **Action:** Add a cost line to `show deep` and a defined behavior when a run is cut off. Use a same-family zero-context reviewer by default, with cross-family review as an opt-in.

**A10. Specify the AGENTS.md change, and update the tests and doctor that depend on it.**
* **Lines:** 83, 198.
* **Problems:**
  * The rendered file is 25 lines with EGM and 23 without, not 26.
  * Template line 13 and line 5 also depend on `suggest`, and conflict with Q2.
  * Dropping `--range` misclassifies committed work (`oaw_mode.py:121-126`).
  * `tests/test_oaw_mode.py:374-380` and the doctor's `oaw_mode.py` detection (`oaw.py:766-773`) would break.
* **Action:** Give the exact before/after text for both template branches.

**A11. Reuse existing code instead of building parallel versions.**
* **Lines:** 87, 95, 112, 118, 147, 173, 180-189, 200, 207.
* **Existing code the plan ignores:**
  * `scripts/goldfish_review.py` (a zero-context `claude -p` review with leak and billing checks);
  * `catalog_core.effect_vs_default` (startup bytes, hooks, dependencies);
  * `oaw.py skills`;
  * `oaw.py --skills none` (this is option ②);
  * `evals/code-map/score.py` with the PREREG A1 rule;
  * `oaw_common.resolve_cli`;
  * the truncation `total` that `code_index` already reports.
* **Documents:** `EVAL_PROTOCOL.md`, Appendix A, `SKILL_INTAKE.md` and `SHARED_ACCEPTANCE_PROTOCOL.md` would duplicate rules. D21 named that kind of drift as the main waste (`DECISIONS:2-5`).

**A12. Define the `oaw_mode.py plan` interface, or extend `show --json` instead.**
* **Lines:** 88, 113, 235.
* **Problem:** No arguments, schema or dry-run flag are given (`oaw_mode.py:337-372, 404-408`).
* **Severity note:** Stage 9 rated this a Blocker. It is graded Major here because the fix is a short contract on an existing command.

**A13. Complete the file lists and the validation steps.**
* **Lines:** 110-113, 135-143, 199, 215-218.
* **Problems:**
  * The plan omits changes to:
    * `oaw.py` (`BUNDLED_SKILLS`, `source_files`, the doctor required list);
    * `harness_check.py` (`cli_check`, `REQUIRED_TEST_MODULES`);
    * `tests/test_install.py`;
    * the `openai.yaml` files.
  * Adding `templates/.claude/agents/oaw-goldfish.md` fails `sync_egm.py --check-bundled` (`scripts/sync_egm.py:153-158`; gate `harness_check.py:187`).
  * No criterion names `harness_check.py` or `sync_examples.py --write`, both required by `AGENTS.md:10-13`.

**A14. Fix the W6 migration and versioning steps.**
* **Lines:** 3, 60, 216-218.
* **Problems:**
  * Explicit recipes keep their old skill list (`oaw.py:352-356`), so "new skills are added" is false for them.
  * The file is `VERSION.json`, not `VERSION`.
  * The plan does not list `FRAMEWORK_VERSION`, `docs/releases/2.0.1-sources.json` or `catalog_core.RELEASE`.
  * The plan covers 2.0.0 → 2.0.1, but released users are on v1 (`docs/UPGRADING.md:7-33`).
  * CI already runs Windows on PRs into main.

**A15. Fix the run order and add a gate per phase.**
* **Lines:** 147, 198, 236, 248-255.
* **Problems:**
  * X4 runs before X1 and X3 decide what ships.
  * W4 (segment 1) needs X3 (segment 2).
  * The Stage 0 questions are never written in any step.
  * Segment 1 bundles six workstreams with one gate.

**A16. Define the mechanisms left open.**
* **Lines:** 95-100, 121, 136-149, 173, 199, 202-213, 237, 275.
* **Open items:**
  * W0: the D32 → D29 mapping and the zero-variance pooling rule.
  * W2: the cache path, the `overview` method, and the output schema bump.
  * W4: the doctor checks. Doctor does not inspect host settings (`oaw.py:794-797`).
  * W5: location and CLI.
  * X5: who runs `suggest` per commit without hooks.
  * The spike fallback and the Q2 off-switch location.
  * The W3 interface: where commands run, preview/apply, the model runtime for ③, the extra prompts that break "one question", and the `verdicts.json` schema.

**A17. Add the missing spec sections and definitions.**
* **Lines:** 5-91, 280-321.
* **Missing:**
  * An alternatives section (feature-spec standard).
  * An architecture and data flow, beyond the file list.
  * A problem statement citing `OWNER_REQUEST.md`.
  * A goal → work → experiment trace.
  * A glossary: EGM, catalog, D-number log, the 試吃/食物/主場/帳本 metaphor (user-facing in the list), the four verdict classes, the statistics terms, and V1-V8 source labels mapped to files.

### 🟢 Nits
* **N1:** 25 vs 23 top-level catalog subcommands (line 189).
* **N2:** "約 180 token" for `oaw-review` (line 182) is court-skill's measurement.
* **N3:** "VS Code 約 90k" (line 309) is uncited.
* **N4:** "三分之一" (one third, line 311) is about one half with two arms.
* **N5:** "實作審查（EGM 各一次）" (implementation review, one EGM run each, line 241) vs the cross-family code review (lines 219, 255).
* **N6:** The "C 級最多 3 題" rule (line 291) comes from D24.2.
* **N7:** "owner 只出現兩次" (the owner appears only twice, line 257) overstates it.
* **N8:** "以標準函式庫為主" (mainly the standard library, line 64) weakens the repository rule.
* **N9:** `oaw add` vs `python3 scripts/oaw.py add`.
* **N10:** "3 個動詞" (three verbs) leaves out `/oaw-add`.
* **N11:** Group letters are reused (A/B, M/O).
* **N12:** Promotional wording (lines 131, 187, 203).
* **N13:** Formatting: bold pseudo-headings and `<br>•` bullets.
* **N14:** A relative date at line 30.
* **N15:** The X4 host and statistic are not specified.
* **N16:** Should changes to `code_index.py` trigger deep?

### Contested / withdrawn
* **ZO-N6 is withdrawn.** It said `SKILL_INTAKE.md` is not 400 lines. The file has 400 total lines, so the plan's figure is right.
* **Z8-11 is kept as conditional.** It doubts that the `oaw-goldfish` agent can avoid reading CLAUDE.md. `omitClaudeMd: true` in `templates/.claude/agents/egm-design.md:8` suggests the agent route is feasible on Claude Code.

## Traceability matrix

| Action | Raw findings |
| --- | --- |
| A1 | ZO-1, ZO-N2, Z8-1, CR-11, IR-1, IR-12 (part) |
| A2 | CR-1, ZO-2, ZO-7, Z8-4, IR-3, CR-8 (part) |
| A3 | IR-2, ZO-4, Z8-7 |
| A4 | ZO-5, CR-3, CR-4, CR-14 (line 44), Stage 7 style M6-M8 |
| A5 | CR-2 (X2 part), Z8-6, IR-7 (X2), IR-8 (X2) |
| A6 | CR-9, IR-8, CO-N8, style M2/M3 |
| A7 | IR-7 (X1, X3), Z8-3, CR-N1 |
| A8 | CR-8, CR-10, CO-2, CR-14 (lines 17-18) |
| A9 | CR-5, CR-6, Z8-5 |
| A10 | CR-7, IR-6, CO-N9 |
| A11 | ZO-3, ZO-6, ZO-N3, Z8-8, IR-10 (reuse), IR-11 |
| A12 | IR-4, CO-6 (plan part), ZO-N1 |
| A13 | IR-5 |
| A14 | CR-12, IR-13 |
| A15 | IR-9, Z8-3 (loop), Z8-10 |
| A16 | IR-10 (design), IR-12, IR-14, CO-6, Z8-9, Z8-2, CO-7 |
| A17 | CR-2 (alternatives), CR-13, CO-1, CO-3, CO-4, CO-5, CO-N1-N6, CR-N2, CR-N3 |
| Nits | IR-N1-N10, CR-N4-N14, ZO-N4, ZO-N5 (conditional), CO-N7 |
