# Stage 8: Intermediate Zoom Out Report

**Target:** `docs/plans/v2.0.1-execution.md` (full file, lines 1-325)
**Standard:** `zoom-out-standard.md`
**Inputs:** the Stage 5-7 reports. The design was not edited between stages, by the user's instruction.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed |

**Context sufficiency:** passes.
**Verdict:** Revise. 1 Blocker (widens ZO-1), 7 Major, 3 Nits. The reviewer agrees that CR-1 is a Blocker.

**Overall view:** The plan builds a new layer next to each existing part instead of extending that part:

| New in the plan | Existing part it sits beside |
| --- | --- |
| `oaw-review` | `suggest`/`show` |
| `oaw-goldfish` | `goldfish_review.py` |
| `oaw.py list` | `catalog effect` and `oaw.py skills` |
| `EVAL_PROTOCOL.md` | `SKILL_INTAKE.md` and `SHARED_ACCEPTANCE_PROTOCOL.md` |
| `verdicts.json` | the ledger |

It also spends about 7M tokens (X1) to decide whether one skill description may be auto-invoked. Meanwhile X2, the experiment the owner actually asked for, is under-budgeted. Most earlier mitigations remove scope. The exceptions are CR-5 and CR-6, which are narrowed below.

The Elephant checked the citations for Z8-1 (`docs/SKILL_INTAKE.md:304, 306, 317, 319`) and for Z8-2 (`scripts/oaw.py:863, 884`). They match.

## Prioritized Findings

### Z8-1. The user route conflicts with the catalog's own D17 and X1-inline gates, not only with its hook/MCP denylist. Severity: Blocker (widens ZO-1)
* **Affected Scope:** Lines 64, 73, 89, 163-176, 186, 284
* **Discrepancy:** Line 284 says users can install skills before tasting them ("不花 token 就能裝好，試吃可以事後再做"). The catalog blocks exactly that, even for skills that are only text:
  * `docs/SKILL_INTAKE.md:306` and `:317`: model-facing skill text is held until a behavior A/B is run (D17).
  * `docs/SKILL_INTAKE.md:319`: a SKILL.md that tells the agent to run commands is classed `X1-inline` and held. Hooks, MCP servers and scripts are never installed.
  * `docs/SKILL_INTAKE.md:304`: foods stay out of the project until the owner approves absorption.
  * The engine enforces these rules at `scripts/catalog_core.py:1207, 1247-1248, 1261-1263`.

  The plan also breaks its own principle 2 (line 73): every model-visible line needs an A/B or a safety reason, and untasted user skills have neither.
* **Rationale & Recommendation:** This needs an owner decision the plan does not list. Add it as Q4: do D17/D21 govern only OAW's defaults, with user installs labelled "未試吃" and left to the user's choice? The simplest compliant user route:
  * copies skill text and agent definitions only;
  * writes a receipt and a restore point;
  * lists hooks, MCP servers and scripts as "not installed by OAW" (D29.3, `DECISIONS-D21-D31.md:148-150`).

  This also removes step 4 (the consent checkbox), the hook and MCP conflict checks, and the hook fixture in the completion test (line 192).

### Z8-2. Option ③ is a ledger lookup, and option ② already exists. Severity: Major
* **Affected Scope:** Lines 58, 165-171, 186, 193, 195
* **Discrepancy:**
  * **③ and the ledger:** ③'s three outputs (預設 / 明確呼叫 / 不建議) are D29's 進預設 / 可選用 / 排掉 (`DECISIONS-D21-D31.md:142-145`).
  * **③ for untasted skills:** line 186 forbids guessing from descriptions, so ③ has no data for skills the user supplies.
  * **A second question:** ③'s follow-up question ("你主要做什麼") breaks "問一題" (one question, line 58) and "只回答 1 題" (answer only one question, line 193).
  * **② already exists:** option ② is `oaw.py init/migrate --skills none` (`scripts/oaw.py:863, 884`).
  * **Owner's wording:** the owner described the three options as what "最後的版本 可能" (the final version may) look like (`evidence/OWNER_REQUEST.md:5`).
* **Recommendation:** Make ③ a deterministic mapping from the ledger, with "offer to taste" for untasted items. Implement ② as `--skills none` plus `add`. Applying ② to an existing install depends on CR-11's removal fix.

### Z8-3. X3 has no status-quo arm, and W4's extra X3 runs are unbudgeted and create a dependency loop. Severity: Major
* **Affected Scope:** Lines 41, 83, 113, 198, 235, 252-253
* **Discrepancy:**
  * **No baseline arm:** X3 compares A (policy line plus skill) with B (skill only). It never tests the 2.0.0 route, one AGENTS.md line, which was followed 2/2 (`DECISIONS-D21-D31.md:180`).
  * **Unbudgeted runs:** W4 needs X3 before and after its deletions (line 198). X3 is budgeted once (line 235).
  * **Dependency loop:** W4 sits in segment 1, but X3 runs in segment 2.
* **Recommendation:** Run one X3 with three arms:
  * 2.0.0 AGENTS.md as it is;
  * 2.0.1 AGENTS.md plus `oaw-review`;
  * 2.0.1 AGENTS.md with the line only.

  If the line-only arm matches, ship no new skill.

### Z8-4. The simplest fix to deep mode is to drop its dependency on plan mode and effort level. Severity: Major (refines ZO-7, supports CR-1)
* **Affected Scope:** Lines 8-11, 43, 55, 108, 121
* **Discrepancy:** EGM's measured gain came from its readiness stage flagging gaps in a document (`egm-selftest:42-45`). It did not come from host plan mode or `--effort max`, neither of which was measured. Plan mode forces the restart and the spike. Codex plan mode is "not mapped yet" (`scripts/oaw_mode.py:318-319`).
* **Recommendation:** Define deep as:
  1. `suggest --paths` on the intended paths (exists, `oaw_mode.py:402-403`);
  2. write the plan to a file;
  3. follow the installed `egm-review/SKILL.md` on that file;
  4. implement;
  5. re-classify the actual diff.

  This changes D31.1, so put it in Q2.

### Z8-5. "Second opinion from another family" rests on grader-agreement data, not reviewer data. Severity: Major (root cause of CR-6)
* **Affected Scope:** Lines 10, 36, 76, 107, 117-120, 270
* **Discrepancy:** V4's kappa values measure how much graders agree when scoring fixed answers (`validation:17-20, 65-72`). Nothing compared a reviewer from another family with a same-family reviewer that has no prior context. D31.5's Codex rounds have no comparison arm (`DECISIONS-D21-D31.md:175-178`).
* **Recommendation:** Default to a same-family reviewer with no prior context (`goldfish_review.py`, or a fresh `codex exec`). Make cross-family review an opt-in, or add a reviewer-family arm to X2.

### Z8-6. X2 is under-budgeted, the Q3 fallback does not fit the cap, and S should be replaced rather than added to. Severity: Major (refines CR-2, CR-9)
* **Affected Scope:** Lines 107, 234, 244, 276, 300
* **Discrepancy:**
  * **Budget:** the E arm alone is 9 × 1.137M = 10.2M at the median (`egm-selftest:17`). At the 1.43M per-run high (`validation:87`) it is 12.9M. Nothing is left for a pilot (about 2M last time, `egm-selftest:81`) or for runs cut off by usage limits.
  * **Q3 fallback:** with 8 new cases the total is about 10.0-10.5M, not "within 10M" (line 276).
  * **Ceiling case:** `orders` is a known ceiling case (`validation:52`). Keeping it goes against D32 rule 3 and step 4 (line 300).
  * **The S arm:** S reviews a diff and its tests (line 107). A new design document always triggers deep (`oaw_mode.py:246-249, 283-285`), so "deep 改用 S" is not coherent.
* **Recommendation:**
  * Replace S with a cheap readiness-checklist arm (about 40k per run, `egm-selftest:18`).
  * Size X2 at 7 new cases, or ask Q3 for about 13M explicitly.
  * Leave `orders` out of the analysis.

### Z8-7. X1 has low decision value. Shrink it or defer it. Severity: Major (extends ZO-4)
* **Affected Scope:** Lines 57, 84, 136-143, 233, 263
* **Discrepancy:**
  * **Expected outcome:** line 263 itself rates an inconclusive X1 as likely.
  * **What X1 decides:** only whether one skill description is auto-invokable.
  * **Ceiling cell:** ERPNext × Opus 5.5 is near ceiling (`codemap-comparison:75`).
  * **Already built:** truncation marking largely exists (`code_index.py:1730-1734`, the JSON `total` at `:1634`).
* **Recommendation:** Ship `code_index.py` in every recipe, as a CLI plus an explicit skill. Then either run only VS Code × Opus and ERPNext × Haiku (about 4.7M), or defer X1 until after the release.

### Z8-8. Three documents would each hold the measurement rules. Severity: Major
* **Affected Scope:** Lines 95, 200, 280-306
* **Discrepancy:**
  * **Three copies of the rules:** `EVAL_PROTOCOL.md` (new), Appendix A, and `SKILL_INTAKE.md`, which already carries D29 (`:71`).
  * **Two older protocols:** `SHARED_ACCEPTANCE_PROTOCOL.md` is still "the single current test protocol" (`docs/plans/v2.0.0-execution.md:16-17`).
  * **Known cost:** D21 named drift between copies of the same content as the main source of waste (`DECISIONS-D21-D31.md:2-5`).
* **Recommendation:** Keep one document, `SKILL_INTAKE.md`, with Appendix A at its head plus the D32 rules and a glossary. Drop `EVAL_PROTOCOL.md`, and mark the older protocols as historical.

### Nits
* **Z8-9 (line 237):** X5 does not need to record `suggest` on every commit. Classification is deterministic, so it can be recomputed later from history with a pinned `oaw_mode.py`, as V7 did. This also closes CO-6's "who records it without hooks" gap. Caveat: `hook_files` reads the current settings (`oaw_mode.py:164-181`), so snapshot them.
* **Z8-10 (lines 59, 236, 253-254):** X4 runs before the X3 fixes and before X1/X2 decide which skill descriptions load. Because G5 is a release gate, run X4 last before W6.
* **Z8-11 (conditional, line 87):** A Claude subagent may still receive CLAUDE.md. `goldfish_review.py` gets its isolation from a fresh temp folder with settings off (`goldfish_review.py:6-7, 34-35`). Host behavior not verified. (The Elephant notes that `omitClaudeMd: true` in `templates/.claude/agents/egm-design.md` suggests the agent route can work, so this stays conditional.)

## Positions on earlier findings

| Finding | Position |
| --- | --- |
| ZO-1 | Agree; widened by Z8-1. Take the text-and-agents-only option for 2.0.1. |
| ZO-2, ZO-3, ZO-4, ZO-6, ZO-N1-N4 | Agree. Each removes scope. |
| ZO-5, CR-3, CR-4, CR-14 | Agree. Text fixes only. |
| ZO-7 | Replaced by Z8-4. |
| ZO-N5 | Agree, conditional. X2 only has to come before auto-EGM, and X1 only before auto-invoking the map. |
| ZO-N6 | (The Elephant contests it: `docs/SKILL_INTAKE.md` has 400 total lines, so the plan's figure is right.) |
| CO-1..CO-4 | Agree. Write one glossary in the single document. |
| CO-5 | Agree. Reuse `oaw.py`'s `--target` pattern (`oaw.py:856`). |
| CO-6, CO-7 | Resolved by Z8-3 and Z8-2. |
| CR-1 | Agree it is a Blocker. The fix needs no new code (`suggest --paths`). |
| CR-2 | Agree. For X2, replace S rather than add a fourth arm. |
| CR-5 | Agree there is a problem. Use the smallest guard: a cost line in `show deep`, the per-project off switch, and count cut-off runs as "not run". Do not build quota-tracking code. |
| CR-6 | Agree. Z8-5 fixes the cause. |
| CR-7, CR-8, CR-10, CR-12, CR-13 | Agree. Low added complexity. |
| CR-9 | Agree. Also add the X3 runs from Z8-3 and the X2 shortfall from Z8-6. |
| CR-11 | Agree. It is a prerequisite for W3 and option ②; schedule it as a work item. |

## Simplest plan that still meets the owner's request
1. **Review:** extend `suggest`/`show`. Deep means classify, write the plan to a file, follow the installed `egm-review`, implement, re-classify. Standard uses the existing same-family reviewer with no prior context. Add `oaw-review` only if X3 shows it beats the line-only route.
2. **Code map:** install `code_index.py` everywhere with a user-level cache and an explicit skill. Defer `overview` and the TS parser. Run a shrunken X1 or defer it.
3. **User-added skills:** text and agent definitions only, with a receipt and a restore point. ① is the default, ② is `--skills none`, ③ is a ledger lookup. Build `list` from `catalog effect` plus the ledger. Add Q4 on D17 scope.
4. **Subtraction:** keep W4, checked inside the single X3.
5. **SOP:** one document. Merge W0 and W5.
6. **Experiments:** size X2 properly, run one X3, run X4 last, compute X5 afterwards.
