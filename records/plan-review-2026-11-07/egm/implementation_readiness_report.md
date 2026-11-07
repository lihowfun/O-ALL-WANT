# Stage 9: Implementation Readiness Report

**Target:** `docs/plans/v2.0.1-execution.md` (DetailedRange, lines 92-325)
**Standards:** `egm-implementation-readiness` and `egm-codebase-details` use `implementation-readiness-standard.md`; `egm-style` uses its persona only.
**Loop note:** One review round was run. The user's instruction for this run was "do not apply fixes to the design", so the `egm-resolve` hand-off and the re-audit rounds were not performed. All findings are open.

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-implementation-readiness` | completed |
| `egm-codebase-details` | completed |
| `egm-style` | completed |

Raw counts:
* implementation-readiness: 3 Blocker, 12 Major, 9 Nit.
* codebase-details: 2 Blocker, 12 Major, 4 Nit.
* style: 0 Blocker, 10 Major, 12 Nit.

After deduplication: 4 Blockers, 14 Majors, 10 Nits.

**The Elephant checked these citations against the code:**
* `scripts/code_index.py:1525-1528` (`callers` skips non-Python files) and `:1594-1596` (`affected` returns "only Python imports and calls are tracked").
* `scripts/catalog.py:1374-1404` and `scripts/catalog_core.py:78`.
* `docs/SKILL_INTAKE.md:304-319`.
* `scripts/oaw.py:863, 884` (`--skills none`).
* The repository has `VERSION.json`, not `VERSION`.

**One claim could not be checked.** The statistics code and `xgrade.py` live on the `records` branch, which is not in the workspace (lines 96, 204).

## Prioritized Findings

### IR-1. W3's user install path relies on catalog behavior the code forbids. Severity: Blocker
* **Reviewer Lens:** codebase-details B1, implementation-readiness B2; matches ZO-1 and Z8-1
* **Affected Scope:** Lines 157-176, 184, 192-193, 267, 284
* **Discrepancy:** The plan says `add` reuses catalog `add`/`taste`/`builds`/`restore` at no token cost, installs untasted skills, and installs hooks, MCP servers, scripts and dependencies after a consent checkbox. It also says `remove` restores the files byte-for-byte. The code blocks each of these:
  * **Untasted text is held.** Skill text is put on `hold` (`x0-text-ab`) until a live A/B passes (`scripts/catalog_core.py:1259-1263`). `cmd_absorb` installs only `disposition == "absorb"` (`scripts/catalog.py:1863-1864`).
  * **Hooks and MCP servers are refused.** "OAW never installs hooks or MCP servers" (`catalog_core.py:1268-1270`). Scripts are held (`:1242-1245`), dependency manifests are excreted (`:1276-1278`), and agents are held (`:1282-1284`).
  * **Only skill text can be installed.** Install is limited to `.md`/`.txt` inside a skill folder (`catalog.py:1391-1404`; `catalog_core.py:78`).
  * **Restore cannot cover host settings.** Builds deny `.mcp.json`, `.claude.json` and `.claude/settings*.json` (`catalog.py:1374-1375`), so restore cannot cover hook or MCP registration.
  * **Same names are refused.** A skill that shares a bundled skill's name is rejected (`catalog.py:1869-1870`), so option ① "用它的" (use theirs) and the same-name fixture fail.
  * **Plain folders are not accepted.** Local sources must be `file://` git repositories (`catalog_core.py:306-329`), so "本機資料夾" (local folder, line 157) fails.
  * **Tests lock these rules in** (`tests/test_catalog_core.py:102, 182, 450, 471`).
  * **Owner decisions say the same.** D21 tier C and D29.3 make runtime dependencies wait on the owner, and say the owner installs external plugins (`DECISIONS-D21-D31.md:21-23, 148-150`).
* **Recommendation:** Add an owner decision (Q4/D33) on what the user route may install. Then name the functions to change (`propose_component`, `absorbed_skill_path`, `layer_path_allowed`, `cmd_absorb`), the new consent record, and the tests to change. The simplest option: install text and agent definitions only, and list hooks and MCP servers as "not installed by OAW".

### IR-2. The W2 TS/JS work is a new call-graph engine, not an upgrade. Severity: Blocker
* **Reviewer Lens:** codebase-details B2
* **Affected Scope:** Lines 137, 139, 147-148, 233
* **Discrepancy:** The commands the plan relies on do not work for TS/JS today:
  * `callers` skips every file that has no Python record (`scripts/code_index.py:1525-1528`).
  * `affected` returns "only Python imports and calls are tracked" (`:1594-1596`).
  * `path` refuses non-Python modules (`:1556-1558`).
  * JS/TS gets only a one-line definition regex, with no imports, methods or call sites (`:646-649, 763-767`).

  So the following depend on a call-resolution engine that does not exist yet:
  * Stage 0(b), callers recall ≥ 0.95 on VS Code;
  * the call-graph ranking in `overview`;
  * X1's VS Code × Opus cell, which line 263 calls the cell that can show a difference.

  The design choices are left to the implementer: regex or tokenizer, how receivers resolve, tsconfig path aliases, re-exports. The 11-06 `callers` evidence (`codemap-comparison:56`) is Python-only (ERPNext).
* **Recommendation:** Either scope X1 and Stage 0 to Python for 2.0.1, or specify the TS/JS resolver (approach, supported syntax, fixtures) as its own work item, with its own estimate and a gate before X1.

### IR-3. The W1 deep flow cannot be run as written. Severity: Blocker
* **Reviewer Lens:** implementation-readiness B1, codebase-details M3; supports CR-1 and Z8-4
* **Affected Scope:** Lines 108, 114-116, 121 (with line 83)
* **Discrepancy:**
  * **Upstream EGM waits for a human.** `egm-review` asks for the target, the context and a preset, and stops at a gate after each stage (`vendor/egm/skills/egm-review/SKILL.md:85-113, 213-241`). OAW's bridge requires keeping "all upstream … human checkpoint requirements" and has `disable-model-invocation: true` (`templates/.agents/skills/egm-review/SKILL.md:5,16`).
  * **The plan leaves the EGM call open.** Line 115 gives no preset (for example `uninterrupted`), no TargetFile or GoldfishContext, no rule for who approves `egm-resolve` edits, no round cap, and no report directory. Upstream writes reports into the working directory, so they would enter the diff and `suggest`'s input.
  * **The 9 agents may not exist.** "呼叫已安裝的 9 個 egm agent" (call the 9 installed EGM agents) is false for a Codex-only install (`oaw.py:55, 287`).
  * **The timing contradicts itself.** Line 83 runs `oaw-review` after the change, but deep step 1 needs a plan before implementing. The plan never names the input (`--paths` or a diff) that triggers deep before any code exists.
  * **Code and tests that must change are not listed.** `oaw_mode.py:357` says "the agent cannot start it", and `tests/test_oaw_mode.py:319, 413` assert that text.
  * **Conditional.** Plan mode may block file writes that EGM needs. Codex has no mapped plan mode (`oaw_mode.py:318-319`). The spike (line 121) covers effort only.
* **Recommendation:**
  * Fix the call to the uninterrupted preset with explicit inputs.
  * Write reports to a gitignored `.oaw/reviews/<id>/`.
  * Define the automatic resolve policy and the round cap.
  * Run deep before editing, using `suggest --paths`.
  * Add a plan-mode spike, or drop plan mode (Z8-4).
  * List the code and tests to change.

### IR-4. `oaw_mode.py plan` has no interface. Severity: Blocker
* **Reviewer Lens:** implementation-readiness B3; matches CO-6 and ZO-N1
* **Affected Scope:** Lines 113, 123, 235 (with line 88)
* **Discrepancy:** "輸出 JSON 步驟給 skill 照做" (outputs JSON steps for the skill to follow) gives no arguments, no JSON schema, no relation to the existing `show --json` (`oaw_mode.py:337-372, 404-408`), and no dry-run flag. X3 needs that flag (line 235). The skill and X3 both depend on this contract.
* **Recommendation:** Give the CLI signature, a JSON example per mode and host, and the dry-run flag. Or extend `show --json` instead of adding a subcommand.

### IR-5. File lists are incomplete, and the AGENTS.md validation steps are missing. Severity: Major
* **Reviewer Lens:** implementation-readiness M5, codebase-details M1, M2
* **Affected Scope:** Lines 110-113, 135-143, 199, 215-218
* **Discrepancy:**
  * **Unlisted changes the work items need:**
    * in `scripts/oaw.py`: `BUNDLED_SKILLS`/`default_skills` (`:36, 173-174`), the `source_files` mappings (`:277-288`) and the doctor `required` list (`:745-778`);
    * in `scripts/harness_check.py`: `cli_check` (`:107-115`), `REQUIRED_TEST_MODULES` (`:17-22`) and `install_check`;
    * the fake framework in `tests/test_install.py:32-55`;
    * the `agents/openai.yaml` files for the new skills.
  * **The new agent breaks a gate.** Adding `templates/.claude/agents/oaw-goldfish.md` fails `sync_egm.py --check-bundled`, which requires that folder to match the EGM bridges exactly (`scripts/sync_egm.py:153-158`; gate `harness_check.py:187`). That folder is also installed only when EGM is selected on Claude (`oaw.py:287-288`).
  * **Required commands are not named.** No completion criterion names `python scripts/harness_check.py` or `python scripts/sync_examples.py --write`, both required by `AGENTS.md:10-13`.

### IR-6. Changing the AGENTS.md lines breaks tests and doctor logic. Severity: Major
* **Reviewer Lens:** codebase-details M4, implementation-readiness M7; matches CR-7
* **Affected Scope:** Lines 198-200 (§4 line 83)
* **Discrepancy:**
  * `tests/test_oaw_mode.py:374-380` asserts the `suggest`/`--range`/"Run the full EGM review only when…" text and a limit of 25 lines or fewer.
  * Doctor decides that `oaw_mode.py` is required by searching the policy for "oaw_mode.py" (`oaw.py:766-773`).
  * `templates/AGENTS.md:6` conflicts with Q2.
  * The exact replacement text is not given.

### IR-7. The experiment decision rules are incomplete and overlap (X1, X2, X3). Severity: Major
* **Reviewer Lens:** implementation-readiness M1, M2, M9; style M3, M4, M8; matches CR-N1 and Z8-6
* **Affected Scope:** Lines 233-235, 264, 275
* **Discrepancy:**
  * **X1:**
    * "不差" (not worse) is undefined. If it includes 未定 (undecided), it contradicts principle 6 (line 77) and D29.2 (`DECISIONS:142-145`).
    * "Same quality, efficiency fails" has no rule.
    * The quality metric is not named.
    * "M 是 2.0.1 的地圖" (M is the 2.0.1 map) doesn't say whether the arm gets only the map or the whole install.
  * **X2:**
    * The metric behind "多抓" (catches more) and "±0.10" is not named.
    * Outcomes 1 and 2 can both hold, with no precedence.
    * Arm S is not defined for design documents (W1's standard runs `codex review` on diffs). If S runs on Codex, cost compares Codex tokens with Claude tokens.
    * The fallback when E does not win differs in three places: line 234, line 264 ("deep 改用 S", deep switches to S) and line 116 / Q2.
    * `orders` is a ceiling case (`validation:52`), against line 300.
    * Reusing old answers is ambiguous: old cases had 2-3 runs, and S never ran on them.
  * **X3:**
    * "做對" (got it right) and "一樣好" (equally good) have no observable criteria.
    * There is no path if X3 fails, though W1 completion depends on it.
    * 6 scenarios departs from D32's 12-question rule.

### IR-8. The budget leaves out items, and the cap rule conflicts with X1 and X2. Severity: Major
* **Reviewer Lens:** implementation-readiness M3, style M2, M8; matches CR-9 and Z8-6
* **Affected Scope:** Lines 229, 233-244, 252, 276
* **Discrepancy:**
  * **Not counted anywhere:**
    * the second X3 that W4 requires (+1.5M);
    * W1's deep E2E run (one EGM run is 1.1-1.4M, `validation:87`);
    * option ③ E2E runs;
    * Opus grading (0.63M last round, `validation:143`);
    * question and case writing (0.37M last round, `validation:144`).
  * **X2 is the median case.** E costs 1.07-1.43M per run, so 9 new cases × 3 arms come to about 10.5-13.8M.
  * **The Q3 fallback barely fits.** 8 new cases still come to about 9.9-10.5M.
  * **X1's 4th cell hits the cap.** It makes X1 about 10M, the D13 cap, while line 229 stops runs near the cap.
  * **The cap rule omits the exception.** Line 229 does not mention the X2 exception.
  * **Segment 1 is not near-zero.** It is labelled "幾乎 0 token" (almost 0 tokens) but includes W4's X3 runs and W1's deep E2E.

### IR-9. The run order measures the wrong configuration, and phases have no gates. Severity: Major
* **Reviewer Lens:** implementation-readiness M4; matches Z8-3 and Z8-10
* **Affected Scope:** Lines 147, 198, 248-255
* **Discrepancy:**
  * X4 runs before X1 and X3 decide which skills and policy text ship.
  * W4 (segment 1) needs X3 (segment 2).
  * Stage 0(a) needs frozen questions that no step writes.
  * Segment 1 bundles six workstreams. Only W0 ends with `harness_check`.

### IR-10. W2's design choices are left to the implementer, and existing eval code is ignored. Severity: Major
* **Reviewer Lens:** implementation-readiness M6, codebase-details M5, M6; style M10
* **Affected Scope:** Lines 136-149
* **Discrepancy:**
  * **Cache:** today there is no cache by default (`code_index.py:1751, 1808`). The plan gives no per-OS path and no way to detect a network drive.
  * **`overview`:** the entry-point, module-grouping and ranking methods are undefined.
  * **Output format:** "file:line 加一行簽名" (file:line plus a one-line signature) changes the JSON contract (`SCHEMA_VERSION = 1`, `:36`) and the current text output (`:1704-1729`). There is no schema bump and no test update.
  * **Truncation:** truncation reporting already exists (`total`, "... N more", `:1547-1550, 1730-1732`).
  * **Existing eval code:** `evals/code-map/score.py`, `native_search.py` and the PREREG A1 rule ("+2 top-5 hits", `evals/code-map/PREREG.md:189-196`) are ignored.
  * **Stage 0 rules:**
    * "輸出不比 grep 多" (output no larger than grep) has no unit; D24 uses bytes.
    * (c) has no thresholds.
    * Failing Stage 0 has no stated consequence. Under D24.4, a failed Stage 0 means no paid Stage 1, so X1 would not run.
    * With 4 questions per class, one question moves the hit rate by 0.25, so it decides the 0.15 threshold.

### IR-11. W1 standard review: existing code not reused, and Codex details are open. Severity: Major
* **Reviewer Lens:** codebase-details M6, implementation-readiness M11; matches ZO-3
* **Affected Scope:** Lines 107, 117-119
* **Discrepancy:**
  * **Existing review script:** `scripts/goldfish_review.py` already runs a zero-context `claude -p` review with tools, MCP and settings off, plus `apiKeySource` and leak checks and a canary (`:34-41, 349-413`).
  * **Existing CLI detection:** `oaw_common.resolve_cli` (`:428-440`) already detects the `codex`/`claude` CLIs.
  * **Agent definition:** the `oaw-goldfish` frontmatter is not given.
  * **Round cap:** "最多 3 輪" (at most 3 rounds) has no rule for what happens when it is reached. Line 219 says "直到沒有新發現" (until nothing new is found), with no cap.

### IR-12. W3 interface: where commands run, preview and apply, ② and ③. Severity: Major
* **Reviewer Lens:** implementation-readiness B2 (interface part), codebase-details M7, M8; style M6; matches CO-5, CO-7, Z8-2
* **Affected Scope:** Lines 157-176, 187-189, 193
* **Discrepancy:**
  * **Where commands run:** `oaw.py` and `catalog.py` run from the framework checkout (`catalog.py:4`). `/oaw-add` has no way to find the checkout, and Codex uses a skill picker (`oaw_mode.py:363`).
  * **Preview and apply:** catalog previews unless `--apply` is given and needs `--reason` (`catalog.py:2048-2049, 2568-2572`). AGENTS.md requires preview by default.
  * **Option ②:** it needs a new recipe kind (`oaw.py:277-279, 745`), or it is `--skills none` (`oaw.py:863`).
  * **Option ③:** it needs a model runtime the plan doesn't name.
  * **"One question":** follow-up prompts break it (lines 169, 171, 173, 174, 176 vs 193).
  * **Undefined pieces:** `verdicts.json` has no path or schema, and the conflict thresholds are undefined.
  * **Existing data:** `catalog_core.effect_vs_default` already computes startup bytes (`:1453-1508`).

### IR-13. W6 migration and versioning facts are wrong or incomplete, and only 2.0.0 → 2.0.1 is covered. Severity: Major
* **Reviewer Lens:** codebase-details M9, implementation-readiness M5; matches CR-12
* **Affected Scope:** Lines 216-218
* **Discrepancy:**
  * **New skills are not added for explicit recipes.** "新的 skill…會加進去" (new skills will be added) is false for projects with explicit skill selections: `plan_install` keeps the previous selection (`oaw.py:352-356`).
  * **The version file is `VERSION.json`,** not `VERSION`.
  * **The version check needs more files.** `version_check` needs `oaw.FRAMEWORK_VERSION` (`oaw.py:24`) and `docs/releases/2.0.1-sources.json` (`harness_check.py:148-158`). `catalog_core.RELEASE` (`:32`) and `tests/test_install.py:99` also change.
  * **CI already covers most of this.** CI already runs `windows-latest` on PRs into main (`.github/workflows/test.yml:4-7, 17`). The plan doesn't say what changes.

### IR-14. W0, W4, W5 and X5 leave mechanisms undefined. Severity: Major
* **Reviewer Lens:** implementation-readiness M7, M8, M10, M12; codebase-details M10-M12; style M9; matches Z8-8 and Z8-9
* **Affected Scope:** Lines 95-100, 121, 198-213, 237, 275
* **Discrepancy:**
  * **W0:**
    * There is no 4-quality × 3-cost → D29 mapping (D32's "成本未定", cost undecided, has no slot in D29).
    * There is no pooling rule for the zero-variance floor.
    * There are no source files or function signatures.
    * The first-turn baselines need model runs, despite "幾乎不花 token" (almost no tokens).
  * **W4:**
    * The doctor checks have no mechanism. Doctor deliberately does not inspect host settings (`oaw.py:794-797`).
    * V6's missing `Skill` tool came from a runner flag, not a setting (`validation:91`).
  * **W5:** no location, CLI or data source. Raw transcripts are local only (`validation:155`).
  * **X5:** nothing runs `suggest` per commit, since hooks are excluded. There is no storage location, and the "60 days or 150 commits" condition doesn't say which comes first.
  * **Spike fallback and Q2 setting:** neither is specified.

### Nits
* **IR-N1:** "實作審查（EGM 各一次）" (implementation review, one EGM run each, line 241) vs cross-family code review (lines 219, 255). EGM reviews documents, not code.
* **IR-N2:** "C 級問題一次最多問 3 題" (at most 3 tier-C questions at once, line 291) comes from D24.2, not D21/D28.
* **IR-N3:** "約為重跑一次的三分之一" (about a third of a rerun, line 311): with two arms, reusing N saves about half.
* **IR-N4:** "約 180 token" for `oaw-review` (line 182) is court-skill's measurement (`validation:94`). Label it an estimate.
* **IR-N5:** "VS Code 約 90k" (line 309) is not in the supplied evidence.
* **IR-N6:** The catalog has 23 top-level plus 4 nested subcommands, not 25 (line 189, `catalog.py:2519-2600`).
* **IR-N7:** "owner 只出現兩次" (the owner appears only twice, line 257) overstates it. Other owner touchpoints: manual checks (line 148), the Windows host (216), tier-C questions (291, 306), the setup-token (321).
* **IR-N8:** Group letters are reused: X3 A/B vs skills A B C, and X1 "M" vs Appendix A "O".
* **IR-N9 (conditional):** `code_index.py` is not in `HARNESS_SCRIPTS` (`oaw_mode.py:38-39`). Decide whether changes to it trigger deep.
* **IR-N10 (style preference):** promotional phrases: "一步到位" (one step, line 131), "證明可用" (proven usable, line 203), "直接受益" (benefit directly, line 187). The risk table's 機率 (probability) column holds "已知" (known).

## Numbers checked and consistent
* EGM about 1.1M tokens and about 8 minutes per run.
* X1 about 7M.
* Codex grading of 100-150 answers costs 2-3M (9.9M / 560).
* The totals 22.5M ≈ "23M" and 25.5M ≈ "26M".
* The standard thresholds of 300 lines / 10 files (`oaw_mode.py:31-32`).
* The D24 threshold of 0.15.
* `SKILL_INTAKE.md` has 400 lines.
* kappa 0.97; court 0/8.
