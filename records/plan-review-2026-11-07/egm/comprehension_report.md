# Stage 6: Comprehension Test Report

**Target:** `docs/plans/v2.0.1-execution.md` (FeatureRange 1-91, DetailedRange 92-325)
**Reviewer:** `egm-comprehension` (status: completed). This stage uses no document standard.

**What this proposes**

OAW 2.0.1 would be the first released V2 version. It does four things:
- **A single review entry, the `oaw-review` skill.** The agent sorts each change into light, standard or deep using the existing D31 rules, through a new `oaw_mode.py plan`. Light means no review. Standard means one zero-context reviewer of the diff, from the other model family. Deep means the agent goes into plan mode by itself, the full EGM reviews the plan, then implementation, then cross-family code review for up to 3 rounds. The owner types nothing. Running EGM automatically depends on owner question Q2 and experiment X2.
- **`code_index.py` as the `oaw-codemap` skill in every recipe.** It adds an `overview` page, outputs only `file:line` plus a signature, marks results "complete" or "truncated", and parses TS/JS better. The agent may call it by itself only if X1 passes.
- **Three user commands, `oaw.py add/list/remove`, plus `/oaw-add`.** `add` asks one three-way question and prints an "absorption list" showing what was installed, its source, whether it was tasted, and how to remove it.
- **Subtraction.** No more model-visible rules than today, at most 600 extra tokens per session, the intake SOP cut to one page, and two new `doctor` checks.

Each new default is gated by a pre-registered experiment (X1-X5) graded under a new yardstick, "D32". The budget is about 23M Claude tokens, and the owner answers Q1-Q3.

**How the existing system works, per this document**

OAW 2.0.0 was never released. It installs:
- a 26-line `AGENTS.md` telling the agent to run `oaw_mode.py suggest`, then `show`;
- one skill the agent can start by itself (`oaw-evidence`);
- 7 explicit-only EGM skills, with a full EGM runtime and 9 Claude agents;
- three scripts, `oaw.py init/migrate/doctor/skills`, and no hooks.

Deep mode today means the owner restarts the session with `--effort max` in plan mode and types `/egm-review`. A separate "catalog" with 25 subcommands brings in outside skills. It follows a 400-line SOP and decisions D1-D31. Measurements say EGM finds more plan defects, but costs 28x the tokens of the native agent (no OAW additions) and takes 12x the time.

The reviewer could only partly paraphrase two parts: what `oaw_mode.py plan` outputs and how the skill uses it (CO-6), and what option ② does to an existing install (CO-7).

---

## Findings

No Blocker, 7 Major, 9 Nits.

### CO-1. "EGM" is never defined. Severity: Major
* **Affected Scope:** Lines 8, 34-35, 56, 66, 86, 108, 114-119
* **Description:** The plan is built around EGM: deep depends on it, it is G2, and X2 tests it. A reader learns its cost and its parts (runtime, 7 skills, 9 agents, `/egm-review`, a "Codex harness"). They never learn what it is. Expand the acronym, add one sentence on what EGM reviews and how, and link the vendored runtime.

### CO-2. Decision IDs are cited with no pointer to the decision log, and "D32" does not exist yet. Severity: Major
* **Affected Scope:** Lines 23, 28, 44, 73, 95, 147, 220, 229, 244, 274-276, 287-306
* **Description:** D13, D17, D22, D24-D31 and D32 are cited as authority, but the plan never says where decisions live. The summary (line 23) and §1 (line 44) treat D32 as an existing yardstick, and only line 274 shows it is a proposal awaiting Q1. The decision log ends at D31. D32's rules come from the "建議改的試吃規則" section of the validation result, which the plan doesn't cite. The D29 cost thresholds behind 進預設 / 可選用 / 排掉 (line 305) are never stated.

### CO-3. The statistics W0 asks someone to build are undefined. Severity: Major
* **Affected Scope:** Lines 23, 96, 274, 305
* **Description:** The plan never defines 四類判定 (four-class verdict), 零變異下限/保護 (zero-variance floor), 成本看區間 (judge cost by interval) or 題內配對 bootstrap (within-question paired bootstrap). Yet W0 asks for them to be implemented and tested in `scripts/eval_stats.py`. Define each in one line, or link the matching parts of the validation result.

### CO-4. The food and digestion vocabulary is undefined, and some of it is user-facing. Severity: Major
* **Affected Scope:** 試吃 (lines 164, 176, 182-186, 195); 食物 (187, 195, 212, 287-306); 帳本 (195); 消化道面板 (188); 主場 (39, 302, 305); 排掉 (24, 305); scout 清單 (297)
* **Description:** Appendix A, the SOP the owner explicitly asked for, is written almost entirely in these terms. The user-facing absorption list has a column "試吃結果", so users will see the jargon too. Add a short glossary.

### CO-5. "catalog" is undefined, and it is unclear where it runs. Severity: Major
* **Affected Scope:** Lines 45, 89, 164, 175, 187-189, 306
* **Description:** W3 wraps catalog's `add`, `taste`, `builds` and `restore`, but §4 does not list `catalog.py` among the scripts installed into projects (line 88). The plan never says whether `oaw.py add` runs in the user's project or in the OAW checkout, or how `/oaw-add` inside a project reaches catalog.

### CO-6. The core W1 mechanism is unclear. Severity: Major
* **Affected Scope:** Lines 83, 88, 108, 110-113, 121, 237
* **Description:**
  * **`plan` output:** The JSON steps that `plan` outputs (line 88) are not given, and neither is their relation to `suggest`/`show`.
  * **`suggest` usage:** §4 removes the `AGENTS.md` lines about `suggest`/`show`, but X5 (line 237) records `suggest` for every commit.
  * **X5 recording:** With no hooks (line 90), nothing says who or what does that recording.
  * **Plan mode:** The spike (line 121) does not ask whether an agent can enter plan mode on its own.

### CO-7. Option ② is not explained for a project that already has OAW. Severity: Major
* **Affected Scope:** Lines 169-170
* **Description:** "不裝 OAW 的 skill 和政策文字" (don't install OAW's skills and policy text) leaves a question open: does choosing it remove the already-installed `oaw-review`, `oaw-codemap`, EGM and `AGENTS.md` text, or only skip installing them? If it removes them, the plan doesn't say how `remove` undoes that.

### Nits
* **CO-N1:** The V1-V8 labels (lines 34-44) never map to files. "V2" also means both the product and a validation experiment.
* **CO-N2:** 配方 (recipe) and "2.0.0 minimal" are undefined (lines 57, 98, 136).
* **CO-N3:** The `code_index` subcommands `find`, `callers`, `affected` and the staleness check are not described (lines 40, 133, 138, 147).
* **CO-N4:** codegraph, graphify, court-skill, TokenEconomizer and claude-mem are unlinked (lines 12, 39, 41, 195, 318-321).
* **CO-N5:** The X2 case names `orders`/`events`/`clean` are undefined, and "±0.10" doesn't name its metric (line 234).
* **CO-N6:** These terms are unexplained:
  * SZZ (line 237)
  * PREREG (lines 225, 300)
  * 5 小時窗口 (5-hour window, line 254)
  * `harness_check` (line 100)
  * C 級 (class C, lines 291, 306)
  * F-PARTIAL (line 299)
  * 受管檔案 (managed files, line 192)
  * "EGM 的 Codex harness" (line 119)
  * the setting that turns off auto-EGM (line 275)
* **CO-N7:** "看起來不可逆的改動" (changes that look irreversible, line 108) is vaguer than the code, which uses more than 5 deleted files and migration/schema paths (`scripts/oaw_mode.py:33-34, 276-285`).
* **CO-N8:** Line 229 caps each experiment at 10M, but X2 is about 11M (line 234). Only Q3 reconciles this, so add a forward reference.
* **CO-N9:** "26 行" (26 lines, line 83) can't be reproduced. `templates/AGENTS.md` has 31 raw lines, which render to 25 with EGM or 23 without. The "two lines" are one wrapped sentence (template lines 10-11).
