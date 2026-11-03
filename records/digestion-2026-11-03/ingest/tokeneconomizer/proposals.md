# microsoft/TokenEconomizer 吸收提案（Elephant 草稿）

| 項目 | 內容 |
|---|---|
| 食物 | `microsoft/TokenEconomizer`，Apache-2.0，固定於 `d58755d849cd9157d29aef539f2beab3d5fee0fc`（2026-11-02） |
| 帳本 | 13 吸收、5 暫緩、17 排出（`ingest/tokeneconomizer/components.json`，第 1 版）。**整合後（第 2 版，以單位計）：12 吸收、7 暫緩、19 排出**，見第 6 節 |
| 整合檢查 | 13 個吸收項目：3 個 pass、10 個 flag、0 個 fail（`ingest/tokeneconomizer/integration.json`） |
| 狀態 | **草稿，尚未實作任何東西。** 依 D10，本文件要先交給金魚盲審，Elephant 處理審查意見後，才由你決定 |
| 一句話 | TE 是 token 和成本的控制層，不是資料地圖，**對 graphify 或向量化問題沒有幫助**。值得拿的是量測方法和生命週期規則，全部用 stdlib 在 OAW 既有腳本裡重寫。TE 本身不打包、不由 OAW 安裝 |

---

## 0. 共通約定

- **引用行格式**：寫進 `catalog/releases/<ver>.json` 的 `uses`，再產生 `docs/releases/<ver>.md`。每行都寫
  `absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): <方法> (<TE 檔案:行>) → <OAW used_in>`。
  以下 13 項全部是「重寫方法，沒有複製 TE 程式碼」，所以不需要附 NOTICE。若決定直接複製 TE 的 regex（只有吸收-10 可能這樣做），就要保留 Apache-2.0 標示。
- **凍結檔案不動**：`evals/egm-pilot/` 的 `pilot_common.py`、`score.py`、`run_pilot.py`、`convert_scenarios.py` 屬於已登記的 v2 pilot 合約；`evals/skill-value/` 的 `CONTROL_FILES` 屬於已登記的 `oaw-retained-skill-value-v1`；`evals/three-way/bench.py` 有 `runner_sha256` 檢查。要改這些檔案，只能放進**下一版合約或新的登記**，不能改現有的。
- **大小**是新增或修改的行數粗估，程式和測試分開列。
- **執行期成本**分三類：啟動文字（host 每個 session 載入的內容）、額外工具呼叫、額外模型呼叫。
- 「已用到的 OAW 位置」指 `oaw-ref/`（`origin/codex/oaw-2-native-upgrade`）。

### 吸收項目總覽與建議批次

| # | 元件 | 整合檢查 | 改的地方 | 對模型的影響 | 建議批次 |
|---|---|---|---|---|---|
| 1 | `te.effective-tokens` | flag | `scripts/improvement.py` | 只改量測 | 2 |
| 2 | `te.overhead-attribution` | flag | `scripts/improvement.py` | 只改量測 | 2 |
| 3 | `te.startup-size-probe` | flag | 計畫文件，之後是 `scripts/catalog.py` | 只改量測 | 1（文件），4（程式） |
| 4 | `te.host-load-probe` | flag | `scripts/oaw.py doctor` | 不影響模型；要啟動 host CLI | 4（等 Codex 對應做法確認） |
| 5 | `te.shadow-arm` | flag | 計畫文件 | 無 | 1 |
| 6 | `te.cache-aware-timing` | pass | `docs/UPGRADING.md`、`oaw.py migrate` 輸出 | 無，只是給人看的建議 | 1 |
| 7 | `te.failure-signature` | flag | 新的 `evals/diagnostics/` | 無，只產生報告 | 2 |
| 8 | `te.fact-lifecycle` | flag | `scripts/wiki_sync.py`、`context_hub.py`；SKILL.md 部分暫緩 | wiki 部分只是建議；SKILL.md 部分會影響模型 | 3（SKILL.md 部分要先 A/B） |
| 9 | `te.completion-advice-lint` | flag（輕微） | `scripts/oaw_common.py`、`wiki_sync.py`、`context_hub.py` | 只出警告 | 3 |
| 10 | `te.windows-cli-argv` | flag | `scripts/oaw_common.py`，以及新登記的 eval runner | 無 | 2（建議最先做） |
| 11 | `te.test-trap-fixture` | flag | 新的 `evals/skill-value/verification_fixtures.py` | 無，fixture 不會被安裝 | 2 |
| 12 | `te.repo-cannot-redirect-executables` | pass | 計畫文件 P2，之後是 `catalog.py` | 無 | 1 |
| 13 | `te.readme-teaser` | pass | P8 README 動畫 | 無 | P8 時做 |

批次 1 只改文件，風險為零。批次 2 是評估用的程式，fixture 測試就足夠。批次 3 是使用者看得到的建議性輸出。批次 4 要等本機裝好 Codex，確認 Codex 有對應做法以後才能做（D8）。

---

## 1. 吸收提案（13 項）

### 吸收-1 `te.effective-tokens`：依快取加權的有效 token（flag）

**要改的 OAW 檔案與函式**
- `scripts/improvement.py`
  - `validate_spec()`：檢查新加的選用區塊 `effective_tokens`，格式要嚴格。
  - `validate_run()`：spec 有這個區塊時，讀取每個 case 的 `usage` 明細。
  - `compare()`：在 comparison 裡多報一個 `effective_tokens`。**`verdict` 的判定邏輯不變。**
  - 新的純函式：`effective_tokens(rows, weights)`、`usage_rows_from_claude(model_usage)`、`usage_rows_from_codex(turn_usage, model_id)`。
- 不改的部分：`METRICS` 維持 `("tokens", "latency_ms", "cost_usd")`；`tokens` 仍然是原始整數（`:274` 的整數檢查不變）；`evals/egm-pilot/pilot_common.py usage()` 不動，改動放進下一版 pilot 合約。

**最小設計（只用 stdlib）**
```json
"effective_tokens": {
  "weights_snapshot": "<日期與來源，由人登記>",
  "models": {"<billed model id>": {"input": 1.0, "cache_read": "<比率>", "cache_write": "<比率>", "output": "<比率>"}},
  "unobservable": {"codex": ["cache_write"]}
}
```
1. 權重只能來自預先登記的 spec。整份 spec 在 `propose()` 時已經算進 `evaluation_sha256`（`improvement.py:221`），所以看過結果後要改權重，就得開新的 proposal。
2. 每個 case 的 `usage` 是一個 list，每筆是 `{"model", "input", "cache_read", "cache_write", "output"}`。其中 `input` 指沒有走快取的新輸入。
3. spec 有這個區塊時，只要某個 case 缺 `usage`，或出現表裡沒有的 model id，就丟 `ValueError`，整個 run 無效。**沒有 fallback**：不抄 `accounting.py` 的 `FALLBACK_WEIGHTS`，也不抄 `pricing.py:29, :173`「沒有明細就用原始總數」的做法。
4. 只有在 `unobservable` 列出的 host 上，`cache_write` 才可以是 `null`（目前只有 Codex）。報告會寫 `unobservable`，不會當成 0。
5. Codex 的對應方式：新輸入 = `input_tokens - cached_input_tokens`，`cache_read = cached_input_tokens`，`output = output_tokens`。**不再加 reasoning**，和 `test_bench.py::test_preserves_usage_without_double_counting_reasoning` 一致。
6. Claude 的對應方式：`result.modelUsage` 裡的每個 model id 各自有 `inputTokens`、`cacheReadInputTokens`、`cacheCreationInputTokens`、`outputTokens`。只要有一個 id 沒有定價，run 就無效。
7. 不跨 host 合併。現有的 `MATCHED_FIELDS` 已經包含 `host`，不同 host 的結果本來就會被拒絕。
8. 不算美元。

**驗收測試**（`tests/test_improvement.py`）
- `test_spec_without_effective_tokens_block_is_unchanged`：現有 fixture 的 comparison 輸出完全不變。
- `test_unknown_billed_model_id_invalidates_run`
- `test_missing_usage_breakdown_invalidates_run_when_block_declared`
- `test_weights_are_covered_by_evaluation_sha256`
- `test_raw_tokens_stay_integer_and_reported`
- `test_claude_model_usage_mapping_requires_every_model_id_priced`
- `test_codex_mapping_subtracts_cached_and_never_adds_reasoning`
- `test_codex_cache_write_is_marked_unobservable_not_zero`
- `test_effective_tokens_do_not_change_verdict`（第一版只報告）
- 以下現有測試必須維持原樣通過：`evals/skill-value/test_improve_fixtures.py`、`tests/test_egm_pilot.py::test_valid_synthetic_protocol_export_cross_checks_official_gate`。

**大小**：程式約 70–90 行，測試約 120–150 行。
**執行期成本**：啟動文字 0，工具呼叫 0，模型呼叫 0。只有跑 `compare` 時多幾次乘法。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): cache-weighted effective-token method and hard failure on an unpriced model id (tokeneconomizer/pricing.py:1-31, :135-160) → scripts/improvement.py (opt-in effective_tokens report); re-implemented; weights come from the pre-registered spec; TE price ratios and fallbacks not used.`

---

### 吸收-2 `te.overhead-attribution`：額外開銷算進該組成本，並標示 usage 覆蓋度（flag）

**要改的 OAW 檔案與函式**：`scripts/improvement.py` 的 `validate_spec()`、`validate_run()`、`compare()`；`docs/SELF_IMPROVEMENT.md` 補一段說明。

**最小設計**
- spec 可以選擇性寫 `"usage_coverage": "required"`，以及 `"overhead_fields": [...]`（只用來顯示在報告上）。
- 每個 case 可以帶三個選用欄位：
  - `overhead_tokens`：整數，候選方案自己另外開的程序（judge、背景工作、parent usage 沒有涵蓋的 subagent）所用的 token。
  - `grading_tokens`：整數，評分用掉的 token，只另外列出，不算進成本。
  - `usage_coverage`：`complete` 或 `incomplete`。
- spec 宣告 `required` 時，每個 case 都要有 `usage_coverage`。該組總量 = `tokens + overhead_tokens`。comparison 分開列出 `tokens`、`overhead_tokens`、`overhead_frac`、`grading_tokens`。
- **兩組都是 `complete`，才能判定效率有提升**；否則 `efficiency_gain=False`，並寫上 `efficiency_blocked: "usage coverage incomplete"`。資源退步的檢查照常用觀測到的數字做：覆蓋不完整時這個數字是下限，下限都已經超過 +10%，就確定是退步。
- 食物自己記的帳只是自我回報，不能讓覆蓋度變成 `complete`。只有 runner 自己觀測到的 usage，或獨立的計量器（例如包住 CLI 的 wrapper）才算數。
- 已經存在的 proposal，存起來的 spec 沒有這個欄位，就照舊規則判定。`decide()` 重新驗證時（`:375-379`）結果不會變。**不升 `SCHEMA`**；要不要改成升 `SCHEMA` 到 2 列在決策 4。

**驗收測試**（`tests/test_improvement.py`）
- `test_overhead_tokens_added_to_arm_and_reported_separately`
- `test_incomplete_coverage_blocks_efficiency_gain`
- `test_incomplete_coverage_still_detects_resource_regression`
- `test_grading_tokens_never_counted_as_candidate_cost`
- `test_spec_without_coverage_field_keeps_old_verdicts`（`test_eligible_decision_never_applies_patch`、`test_earlier_non_eligible_comparison_blocks_acceptance` 原樣通過）
- `test_decide_revalidates_legacy_proposal_as_eligible`

**大小**：程式約 40–60 行，測試約 100–130 行。
**執行期成本**：0。
**對暫緩測試的影響**：TE 的 judge 是另一個 `claude -p` 或 `codex exec` 程序，host 的 result 事件裡看不到。沒有獨立計量器的話，A1 和 A4 的 TE 組只會得到「覆蓋不完整，不做效率結論」。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): overhead charged to the arm it serves and reported as overhead_frac (tokeneconomizer/ledger.py:1-13; plugin/accounting.py:33-53; plugin/judge.py:87-96) → scripts/improvement.py (usage_coverage, overhead_tokens); re-implemented to enforce SHARED_ACCEPTANCE_PROTOCOL.md:61-62, :339-340.`

---

### 吸收-3 `te.startup-size-probe`：實際量測啟動請求的大小（flag）

**要改的 OAW 檔案**
- 現在只改文件：`docs/plans/skill-catalog-execution.md` 的「撐爆上下文」那一列（`:120`）和「預算」（`:127`）。
- P4/P5 時寫程式：`scripts/catalog.py` 新增 `measure_startup(host, project_copy, candidate)`，作為整合測試的一步。

**最小設計（寫進計畫的規則）**
1. 不再估算，改成實際量測：在候選專案的**副本**裡，分別量裝和不裝候選 skill 的啟動內容。這樣 `AGENTS.md` 和 skill 都會被算進去，不能在空的暫存資料夾裡量。
2. Codex：用 `codex debug prompt-input`，不呼叫模型，單位是**字元**，記錄時寫明單位，不偷偷換算成 token。依自動化界線（`:68`）可以自動執行。**還沒驗證**：skill metadata 會不會出現在 prompt-input 裡。本機裝好 Codex 後要先確認（免費）；確認前，Codex 的預算欄寫「未量測」。
3. Claude：送兩個一行的 `claude -p` 請求（裝與不裝），固定加上隔離旗標 `--setting-sources project,local`、`--strict-mcp-config` 搭配空的 `--mcp-config`、用 `--settings` 設 `disableAllHooks`、`--no-session-persistence`，再把 result usage 的 `input + cache_read + cache_creation` 加總。這要付費，所以只在 D11 的常設政策內執行，或由人啟動。
4. **探測失敗就是錯誤**：結束碼非 0、`is_error`、沒有 usage、輸出是空的，一律丟例外，絕不當成 0。
5. **大小要和是否載入一起看**：候選 skill 的名稱必須出現在 init 事件（Claude）或 prompt-input（Codex）裡。大小沒變、skill 卻不見了，判定失敗，因為可能是 host 截斷了 skill 清單。
6. 數字旁邊要記錄 host 版本和模式（headless `-p` 和互動模式不一樣）。
7. 每個 host 各有自己的預算，P5 依實測決定。TE 的「4 條事實、150 tokens」上限不引入。
8. 在 Windows 上，用吸收-10 的 `resolve_cli()` 啟動 CLI，因為這台機器的 Claude 只有 npm 的 `claude.cmd`。

**驗收測試**（之後的 `tests/test_catalog.py`，使用 mocked binary）：結束碼非 0 要丟例外；`is_error` 要丟例外；沒有 usage 要丟例外；prompt-input 是空的要丟例外；大小沒變但 skill 不見要判定失敗；預算依 host 分開；argv 要含隔離旗標；CLI 不接受某個旗標時要判定探測失敗，不能偷偷拿掉那個旗標。

**大小**：現在文件約 15 行；之後程式約 100–140 行，測試約 120–160 行。
**執行期成本**：使用者專案的啟動文字和工具呼叫都是 0。catalog 做整合測試時，每個候選 skill 在 Codex 上跑 1 個本機指令（免費），在 Claude 上送 2 個小的付費請求（每個大約是一份啟動前綴的量；OAW 還沒量過，第一次執行時記錄實際數字）。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): measured startup request size, a failed probe is an error and never 0 (tokeneconomizer/plugin/toolcheck.py:216-294) → docs/plans/skill-catalog-execution.md context-budget gate and scripts/catalog.py (planned); re-implemented; TE injection caps (plugin/config.py:149-150) not adopted.`

---

### 吸收-4 `te.host-load-probe`：不跑任務，只確認 host 載入了哪些 skill（flag：Claude 和 Codex 要一起出）

> **修訂 2**：在 Codex 的對應做法驗證之前，這一項改列**暫緩**（backlog `OAW-26`，kind = hold）。缺的測試是免費的：裝好 Codex（PRE-03）後，確認 `codex debug prompt-input` 會不會列出 OAW skill 名稱。成立就兩個 host 一起出；不成立就依 D8 排出，不做只有 Claude 能用的版本。

**要改的 OAW 檔案與函式**
- `scripts/oaw.py`：`main()` 加一個明確的旗標 `doctor --probe-host {claude,codex,both}`；新增 `probe_host(target, host)`，結果放在獨立的 key `host_probe`。**`doctor()` 預設行為不變。**
- init 事件的解析程式碼複製一小段到 `scripts/`，不 import 凍結的 `evals/egm-pilot/pilot_common.py`。
- 用吸收-10 的 `scripts/oaw_common.py resolve_cli()`。
- 文件：`docs/CLI_Reference.md`；`docs/Skill_Guide.md:19` 補充說明這個探測能證明什麼、不能證明什麼。

**最小設計**
- 預設的 `doctor` 維持離線、不變（`tests/test_install.py:111-113`、`harness_check.py install_check` 都繼續通過）。
- Claude：argv = 解析後的 claude + `-p --output-format stream-json --verbose --setting-sources project,local --strict-mcp-config --mcp-config <暫存空檔> --settings <暫存 {"disableAllHooks": true}> --no-session-persistence`，工作目錄是目標專案，從 stdin 送一句固定的 prompt。讀到 `system/init` 事件就結束整個程序樹，逾時 60 秒。**CLI 不接受任何一個旗標，就判定失敗（fail closed）**，不會像 TE（`sidecall.py:195-199`）那樣偷偷拿掉。
- 回報內容：已選的 OAW skill 有哪些出現在 init 的 `skills`、`slash_commands` 裡；host 版本；標示「headless 模式在 <版本> 上的載入結果，可能送出了一個小請求」。不能拿來證明互動模式也會載入。
- Codex：候選做法是在目標專案跑 `codex debug prompt-input`，搜尋 OAW skill 名稱。**還沒驗證**，要等本機確認後才實作。D8 和計畫 `:317` 不允許只有一個 host 能用的 doctor 功能，所以兩個 host 一起出。
- 暫存檔放在專案以外的暫存資料夾，專案裡什麼都不寫。不會讓 `status` 變成 unhealthy，也不改變結束碼。CI 不執行這個探測。

**驗收測試**（新的 `tests/test_doctor_probe.py`，寫法比照 `test_live_execution_records_runs_with_a_mocked_binary`）
- `test_doctor_without_probe_flag_is_unchanged_and_offline`（把 subprocess 換成一呼叫就丟例外的版本）
- `test_probe_reports_loaded_oaw_skills_from_init_event`
- `test_probe_pins_isolation_flags`
- `test_probe_fails_closed_when_cli_rejects_a_flag`
- `test_probe_failure_keeps_doctor_healthy_and_exit_code`
- `test_probe_kills_process_tree_after_init`（假的 binary 送出 init 後就一直 sleep）
- `test_probe_writes_nothing_in_project`
- `test_codex_probe_reads_prompt_input_for_skill_names`（假的 prompt-input 輸出）

**大小**：程式約 90–120 行，測試約 120–150 行。
**執行期成本**：沒加旗標就是 0。加了旗標：啟動 1 個 host 程序，可能送出 1 個小請求。啟動文字 0。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): host-side load check that reads the init event and stops (tokeneconomizer/plugin/toolcheck.py:58-98) → scripts/oaw.py doctor --probe-host; re-implemented with hooks, MCP and session persistence disabled; TE's settings writer not adopted (OAW already has equivalent safeguards).`

---

### 吸收-5 `te.shadow-arm`：只記錄、不執行的試吃（flag：說法要先更正）

**要改的 OAW 檔案**：`docs/plans/skill-catalog-execution.md` 行為消化的關卡（`:80`），以及自動化界線那一段（`:68`）。

**要寫進計畫的規則**
> 如果食物提供只記錄、不執行的模式，在付費 A/B 之前，可以先在沙盒裡跑一次 shadow 試吃，估計它在 OAW fixture 上會出手幾次。前提有三個：
> (1) 這是在執行食物的程式碼，屬於 D11 的沙盒試吃，不是自動靜態消化的一部分。
> (2) 先查清楚 shadow 模式還會不會呼叫模型。TE 的 shadow 只是不把結果送出去，judge 照樣付費呼叫（`controller.py:323`），hooks 和 fold 也照跑。會花錢就要算進預算。
> (3) shadow 的延遲和 token 包含食物自己的開銷，既不是 native 基準，也永遠不算 A/B 證據。

**驗收測試**：無（只改文件）。**大小**：約 8 行。**執行期成本**：0。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): log-only shadow arm before a paid trial (tokeneconomizer/plugin/config.py:26-28; plugin/controller.py:121, :334, :347; plugin/fold.py:327) → docs/plans/skill-catalog-execution.md behavior-digest stage; method only, with the correction that TE's shadow mode still makes paid judge calls.`

---

### 吸收-6 `te.cache-aware-timing`：在 session 之間才改啟動前綴（pass）

**要改的 OAW 檔案與函式**
- `docs/UPGRADING.md`：新增一小段說明。
- `scripts/oaw.py`：`main()` 在 `migrate` 的結果（preview 和 `--apply` 都算）加一個 `advice` list；`print_result()` 印出 `Advice:` 行。
- `docs/plans/skill-catalog-execution.md` P5 的 absorb/retire 步驟補一句。

**最小設計**（建議文字）
> Apply migrate between sessions, then start fresh sessions on both hosts so each loads the new AGENTS.md and skills. Changing the startup prefix of a conversation that will be resumed may force a full prompt-cache rewrite (upstream-reported for tool-list changes on Claude Code 2.1.307 and Codex 0.163.0; not measured by OAW).

只取這條時機規則。TE 那個最長等 24 小時的背景 waiter 列在排出（`te.background-daemons`）。

**驗收測試**（`tests/test_install.py`）：新增 `test_migrate_preview_includes_between_sessions_advice`，確認有 advice、仍然是 dry-run、沒有寫任何檔案。`test_migrate_is_dry_run_then_backs_up_retirements` 原樣通過。
**大小**：程式約 6 行，文件約 10 行，測試約 10 行。
**執行期成本**：只有執行 migrate 時多印一行。啟動文字 0。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): apply startup-prefix changes between sessions, not into a conversation that will be resumed (tokeneconomizer/plugin/fold.py:42-51; docs/PLUGIN.md:381-395) → docs/UPGRADING.md and scripts/oaw.py migrate advice; advice only, upstream-reported and not measured by OAW; the 24 h waiter not adopted.`

---

### 吸收-7 `te.failure-signature`：失敗特徵與停滯計數（flag：換到新的、不凍結的模組）

**要改的 OAW 檔案**
- 新增 `evals/diagnostics/failure_signature.py` 和 `evals/diagnostics/test_failure_signature.py`。
- `.github/workflows/test.yml` 加一行 `python -m unittest discover -s evals/diagnostics -p "test_*.py" -v`。
- **不改** `score.py` 和 `pilot_common.py`（凍結；而且 pilot 禁用 Bash 和 PowerShell，trace 裡本來就沒有測試指令）。也不改 skill-value 的 `CONTROL_FILES` 和 `bench.py`。
- ~~要不要在 `templates/.agents/skills/oaw-improve/SKILL.md` 加一行提到這個診斷工具，列為決策 9。~~ **修訂 2：不加，這一行排出。** 診斷工具放在 `evals/`，而 `scripts/oaw.py` 的 `source_files` 只安裝 `scripts/` 的 helper 和模板（`oaw-ref/scripts/oaw.py:225-245`），所以這一行會叫使用者專案去用一個它們沒有的模組；它也會變成每個已安裝專案的一次 framework 更新。

**最小設計**
- 執行方式：`python -I -X utf8 evals/diagnostics/failure_signature.py --trace <events.jsonl> --format codex|claude --workspace-root <path> [--json]`。這個模組不 import 本地的其他模組，所以 `-I` 不會出問題。
- Adapter：
  - Codex：讀 `command_execution` 項目的 `exit_code` 和輸出；`file_change` 算成編輯。
  - Claude：讀 stream-json 的 `tool_use` 和 `tool_result` 配對（看 `is_error`）；`Edit`、`Write`、`MultiEdit` 的 `file_path` 算成編輯。
- `normalize(line, workspace_root)`：
  - 工作區根目錄換成 `<WS>`，兩種斜線都處理，在 Windows 上不分大小寫。
  - `C:\...`、`C:/...`、UNC 和 POSIX 路徑換成 `<PATH>`。
  - `0x…` 換成 `<HEX>`，數字換成 `<N>`，連續空白壓成一個。
- 特徵值 = 正規化後第一行非空錯誤訊息的 `sha256`，取前 16 個 hex。
- 每個 run 只輸出雜湊和計數：`failures`、`distinct_signatures`、`repeated_identical_failures`、`max_repeat`、`stagnation`（重複次數 ÷ 失敗次數）、`edit_churn`、`distinct_edit_files`、`test_runs`。**不輸出原始指令，也不輸出 grep pattern**（TE 在 `state.py:187-194` 有記錄這些，不取）。
- 只產生報告，`improvement.py compare` 不會讀它，也不會當成關卡。

**驗收測試**
- `test_same_failure_across_windows_and_posix_workspaces_hashes_equal`（`C:\Users\a\ws1\x.py:12` 和 `/tmp/ws2/x.py:40` 要得到相同的雜湊）
- `test_backslash_and_forward_slash_paths_normalize_equal`
- `test_different_failures_hash_differently`
- `test_output_contains_no_raw_command_text`（指令裡放一個 `sk-test-123`，輸出裡不能出現）
- `test_codex_adapter_counts_nonzero_exit_as_failure`
- `test_claude_adapter_reads_is_error_tool_results`
- `test_empty_trace_reports_zero_counts`
- `test_signature_uses_sha256`

**大小**：程式約 120–160 行，測試約 100–130 行。
**執行期成本**：0，都是 run 結束後離線執行。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): normalized failure signatures and stagnation counters (tokeneconomizer/loopguard/state.py:120-134, :155-212) → evals/diagnostics/failure_signature.py (report-only); re-implemented with sha256 and Windows path normalization; raw command excerpts (state.py:187-194) not adopted.`

---

### 吸收-8 `te.fact-lifecycle`：有證據才升級的事實生命週期（flag：拆成兩部分）

#### 8a wiki 的建議性部分（現在可以做）

**要改的 OAW 檔案與函式**
- `scripts/wiki_sync.py`：`_parse_memory_entries()` 讀取取代標記；`promote_candidates()` 新增 `evidence_gate=False`；`main()` 新增 `--evidence-gate` 旗標。
- `scripts/context_hub.py`：`memory_add()` 新增選用參數 `--supersedes "<title>"`，在新的條目本文加一行標記。
- `docs/Wiki_Sync_Guide.md`。

**最小設計**
- **預設不變**：`--min-citations` 的預設值維持 0。如果改成 2，沒有 `docs/archive` 的專案（V2 模板不會建立這個資料夾）跑 promote-candidates 都會變成空清單，而且目前沒有測試會發現這件事。
- **定義取代標記**：在記憶條目本文加一行 `Supersedes: <較早條目的 title>`。title 的定義和 `_parse_memory_entries()` 現在一樣，也就是 `## [日期] [TAG]` 後面的文字。
- `--evidence-gate` 的條件：
  1. 至少 2 個引用。現在已經是每個 archive 檔案只算一次（`:1171-1181`），這部分不用改。
  2. 被較晚的條目取代的，一律排除。只要一個取代標記就夠，這是把 TE「一次可靠的矛盾就淘汰」的不對稱規則改成 OAW 的靜態版本。
  JSON 輸出會列出被排除的條目和 `reason: superseded_by <日期 title>`。
- 開了 gate 但沒有 `docs/archive` 時，明確印出「沒有 docs/archive，無法滿足證據門檻」，不會默默回傳空清單。
- **不採用**時間衰減和觸發門檻。它們需要每個 session 自動收集遙測，而 v2 已經拿掉了這個迴圈（`v2.0.0-execution.md:86`）。
- 文件要寫清楚：OAW 的「引用」是指有 archive 檔案提到這個 title，和 TE 的 grounding（在被引用的 session 裡由 host 執行的偵測器確認過）不一樣，不能說兩者等價。

**驗收測試**（`tests/test_wiki_sync.py` 目前沒有任何 promote-candidates 測試）
- `test_promote_candidates_default_unchanged_without_archive`
- `test_evidence_gate_requires_two_distinct_archive_files`
- `test_same_archive_file_mentioning_title_twice_counts_once`
- `test_superseded_entry_excluded_under_gate`
- `test_superseded_entry_still_listed_without_gate`
- `test_gate_without_archive_reports_reason`
- `tests/test_context_hub.py::test_memory_add_supersedes_appends_marker_line`

**大小**：程式約 40–60 行，測試約 90–120 行。**執行期成本**：啟動 0，只在執行指令時才有。

**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): evidence-gated promotion with asymmetric retirement, where one verified contradiction outweighs confirmations and at least two independent citations are required (tokeneconomizer/microskills/lifecycle.py:15-21, :102-117; microskills/distiller.py:33) → scripts/wiki_sync.py promote-candidates --evidence-gate (advisory); static rules only; recency decay and firing gate not adopted.`

#### 8b `oaw-evidence` SKILL.md 的措辭（暫緩，要先做 A/B）

原本想加的一句是「發現高風險筆記被驗證推翻時，記一筆取代條目」。這和 skill 自己的範圍「Append only the requested durable finding」以及 `AGENTS.md` 的規定衝突，而且會影響模型行為，依 proof-before-promotion（`README.md:143`）必須有配對證據。

- **預先登記的 A/B**：新登記 skill-value 的 `superseded-handoff` case。兩組：現在的 `oaw-evidence` 對比改過措辭的版本（只在使用者要求記錄時才記取代條目）。重複 5 次。**修訂 2：措辭會裝到兩個 host，所以兩個 host 都要跑**：Codex 用現有的 skill-value runner；Claude 用允許 shell 的 Claude 沙盒 runner（backlog PRE-04）。指標：最後用的決定是不是最新的那個、有沒有自己多記沒被要求的條目、有效 token。停止規則：改過的版本只要出現一次沒被要求卻自己寫入，就停，判定不採用。
- **token 估計**：每個 host 大約 10–20 個 session，約 **6–18M logical tokens**，兩個 host 約 12–36M。這是用 Claude 校準值（每個 agent 0.6–0.9M）推的估計，Codex 實際成本沒量過。
- 修訂 2：優先度低，由系統依 D11 決定：排在 TE 暫緩測試的最後（修訂 3 明確化：在 A1 之後，backlog test_order 第 10 步），TE 的額度還夠才跑；沒跑就 8b 維持暫緩，只上 8a（backlog `HOLD-03`）。

---

### 吸收-9 `te.completion-advice-lint`：攔下「叫 agent 跳過驗證」的筆記（flag，輕微）

**要改的 OAW 檔案與函式**
- `scripts/oaw_common.py`：新增 `SKIP_ADVICE_PATTERNS` 和 `skip_advice_hits(text)`。`wiki_sync.py` 和 `context_hub.py` 都已經 import `oaw_common`，放這裡可以共用。
- `scripts/wiki_sync.py lint()`：在 `HOLLOW_PHRASES` 的警告旁邊加上這類警告。
- `scripts/context_hub.py memory_add()`：條目照樣寫入，符合 pattern 時在 stderr 多印一行警告，stdout 不變。
- `CHANGELOG.md` 和 `docs/UPGRADING.md` 註明：`lint --strict` 多了一類警告，在 strict 模式下會變成錯誤。

**最小設計**（只抓「叫人跳過」的說法，不抓「怎麼驗證」的說法）
- 英文 pattern（不分大小寫）：
  - `\bno need to (?:re-?)?(?:run|test|verify|check)\b`
  - `\bskip(?:ping)? (?:the )?(?:tests?|test suite|verification|checks?|build)\b`
  - `\b(?:don't|do not|never) (?:bother to )?(?:re-?)?run (?:the )?(?:tests?|test suite|checks?|build|verification)\b`
  - `\binstead of (?:re-?)?(?:running|testing)\b`
  - `\b(?:tests?|verification) (?:is|are) (?:not needed|unnecessary)\b`
- 中文 pattern（選用，見決策 7）：`不(?:用|必|需要)(?:再)?(?:跑|執行|做)?(?:測試|驗證)`、`跳過(?:測試|驗證)`
- 不抓單獨出現的 verify、done、complete、finish、stop。TE 的 regex（`envfacts.py:51-53`）會抓這些字，對一般文字來說太寬。
- 只警告，絕不拒絕寫入。

**驗收測試**
- `tests/test_wiki_sync.py`：
  - `test_skip_advice_warns_in_lint`
  - `test_verification_instructions_do_not_warn`（例如 "verify with `python -m unittest`"、"Done: …"）
  - `test_oaw_knowledge_pages_have_no_skip_advice_hits`：讀 `docs/knowledge/`，要得到 0 筆。其中 `OAW_Session_Continuity_Test.md` 裡的 "DO NOT RERUN: 0 experiments locked" 不能被抓到。
  - `test_strict_mode_turns_skip_advice_into_error`
  - `test_non_strict_exit_code_unchanged`
- `tests/test_context_hub.py`：`test_memory_add_warns_on_skip_advice_but_appends`

**大小**：程式約 25–40 行，測試約 60–80 行。
**執行期成本**：啟動 0。只有筆記符合 pattern 時才在工具輸出多一行警告。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): lint that keeps learned notes from telling the agent to skip verification (tokeneconomizer/microskills/envfacts.py:51-53, :216-217) → scripts/oaw_common.py, scripts/wiki_sync.py lint and scripts/context_hub.py memory add (warning only); phrase list re-tuned, TE regex not copied.`

---

### 吸收-10 `te.windows-cli-argv`：把 Windows 的 npm shim 解析成直接執行的 argv（flag，比帳本寫的更重要）

整合檢查有更正：`run_pilot.py` 把每一輪的文字放在 argv 的最後（`:141`），**不是走 stdin**。這台機器上 Claude 只有 `~/AppData\Roaming\npm\claude.cmd`，透過 cmd.exe 執行時，prompt 本身會被 cmd.exe 再解析一次。修訂 3（goldfish-1 #10）：pilot 預設的 `DEFAULT_CLAUDE` 只找 `claude.exe`，找不到時用字面的 `claude.exe`（`:36-38`），所以這台機器上的預設執行會啟動失敗；只有用 `--claude` 指向 `claude.cmd`（這裡唯一的 Claude）時，prompt 才會經過 cmd.exe。

**要改的 OAW 檔案與函式**
- `scripts/oaw_common.py`：新增 `resolve_cli(name_or_path, *, platform=os.name, search_path=None) -> list[str]`。
- 用到它的地方：
  - `evals/three-way/bench.py` 的 Runner 設定和 `runtime.json` 的 `--version`。只用在新的登記，舊的登記會因為 `runner_sha256` 不同而拒絕執行，這是預期行為。
  - `evals/skill-value/experiment.py` 的 Engine 設定和 `:347` 的 `--version`。**不改 `cli_command()`**，這樣 `test_native_approval_shortcut_is_not_combined_with_conflicting_sandbox_flag` 結果仍然固定。
  - 下一版 pilot 合約的 `run_pilot.py` `DEFAULT_CLAUDE`（`:36-38`），同時把 prompt 改成走 stdin。
  - 吸收-3 和吸收-4 的探測。
- 每個 run manifest 記錄 `cli_argv`（解析後的絕對路徑 argv）和 `resolver_sha256`，執行時比照 `runner_sha256` 做驗證。這是為了補上被雜湊的 runner 去 import 一個沒被雜湊的 helper 所留下的漏洞。

**最小設計**
1. 自己逐一走 `PATH` 裡的資料夾，略過空字串和 `.`，再依 `PATHEXT` 找檔案。**不搜尋目前資料夾**（`shutil.which` 在 Windows 上可能會先找 cwd），找到的結果必須是絕對路徑。
2. 不是 Windows：直接回傳 `[path]`。
3. `.exe`：回傳 `[exe]`。
4. `.cmd` 或 `.bat`：最多讀 8 KB，內容必須符合 npm shim 的形狀，也就是 `"%_prog%" "%dp0%\<rel>\<script>.js" %*` 或 `"%dp0%\<rel>\<x>.exe" %*`。
   - `%dp0%` 換成 shim 所在的資料夾。
   - `%_prog%` 有 `%dp0%\node.exe` 就用它，沒有就用同一套解析找 `node.exe`。
   - 目標必須存在，而且在 shim 資料夾的 `node_modules` 裡面。
   - 回傳 `[node.exe, script.js]` 或 `[x.exe]`。
5. 其他批次檔一律丟 `ValueError("refusing non-npm batch file")`，**永遠不透過 cmd.exe 執行**。
6. 呼叫端用 `subprocess.run(argv + args, shell=False)`。只需要 Python 3.10+ stdlib。

**驗收測試**（新的 `tests/test_cli_resolve.py`，讓 `harness_check` 會跑到；CI 有 windows-latest）
- `test_npm_node_shim_resolves_to_node_and_script`（用 `platform="nt"` 參數，在任何平台都能測）
- `test_npm_exe_shim_resolves_to_exe`
- `test_non_shim_batch_file_is_refused`
- `test_current_directory_is_not_searched`（在 cwd 放一個 `claude.cmd`）
- `test_posix_behavior_unchanged`
- `test_arguments_with_percent_and_ampersand_pass_verbatim`（只在 Windows CI 跑：假的目標程式把 argv 原樣印回來，引數包含 `%PATH%` 和 `&`）
- 在 `evals/three-way/test_bench.py` 和 `evals/skill-value/test_experiment.py` 各加一個：新登記的 manifest 有記錄 `cli_argv` 和 `resolver_sha256`。

**大小**：helper 約 50–70 行，測試約 100–130 行；每個 runner 再改 5–10 行（只影響新的登記）。
**執行期成本**：啟動 0。每次設定 run 時多讀一個檔案。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): Windows npm shim resolved to a direct argv, other batch files refused (tokeneconomizer/plugin/sidecall.py:127-177) → scripts/oaw_common.py resolve_cli, used by the eval runners (new registrations) and host probes; re-implemented, TE regexes not copied.`

---

### 吸收-11 `te.test-trap-fixture`：測試指令陷阱 fixture（flag：獨立的新模組）

**要改的 OAW 檔案**
- 新增 `evals/skill-value/verification_fixtures.py` 和 `evals/skill-value/test_verification_fixtures.py`（CI 已經會跑 `evals/skill-value/test_*.py`）。
- **不改 `fixtures.py`**：它是 `oaw-retained-skill-value-v1` 的 `CONTROL_FILE`，而且 `test_fixtures.py` 假設只有兩個 evidence case。接上 runner 要等 A5 新登記時一起做。

**最小設計**
- `CASES = {"verification": ("pytest-absent-trap",)}`，`build(case, variant)` 回傳「路徑 → 內容」的 dict：
  - `pyproject.toml` 裡有 `[tool.pytest.ini_options]`；
  - `tests/test_calc.py` 用 unittest 寫；
  - `calc.py` 裡埋了一個 bug。
  - V1、V2、V3 三個變體各改不同的檔案，讓 TE 組能湊到 K=3 次「不同檔案」的確認。
- 每組的證據形式（由 controller 管理，預設不放進工作區）：
  - `agents_line`：`AGENTS.md` 裡一行 "Verification: `python -m unittest discover -s tests`"；
  - `memory_entry`：同一個事實寫成 oaw-evidence 的記憶條目；
  - `none`。
- `trap_armed(python, path_env)`：用候選方案的直譯器執行 `-I -c "import importlib.util,sys; sys.exit(importlib.util.find_spec('pytest') is not None)"`，同時確認在候選方案的 PATH 上 `pytest` 找不到。**陷阱沒有布置好的 run 一律判無效，不算通過。**
- `first_test_command(trace, format)`：從 Codex 的 `command_execution` 或 Claude 的 Bash `tool_use` 找出第一個測試指令，分成 unittest、pytest、其他三類。判定標準是第一個測試指令是不是記錄下來的那一個。
- 結果固定，不需要網路。

**驗收測試**
- `test_builder_is_deterministic_and_has_no_pytest_dependency`
- `test_fixture_tests_pass_under_unittest_after_fix`
- `test_trap_not_armed_when_fake_pytest_on_path_marks_run_invalid`
- `test_first_test_command_classifies_pytest_and_unittest_forms`（`python -m pytest`、`pytest -q`、`py -m unittest`、`python -m unittest discover`）
- `test_existing_skill_value_population_unchanged`（`protocol.json` 的雜湊和 60 次呼叫都不變）

**大小**：程式約 90–120 行，測試約 80–110 行。
**執行期成本**：0，fixture 不會被安裝。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): environment test-trap fixture design, a project configured for pytest with pytest absent whose tests pass under unittest (tokeneconomizer/plugin/probe.py:1-22) → evals/skill-value/verification_fixtures.py; design only, probe.py not adopted.`

---

### 吸收-12 `te.repo-cannot-redirect-executables`：repo 不能決定要執行哪個程式（pass）

**要改的 OAW 檔案**：`docs/plans/skill-catalog-execution.md` 攝取關卡那一列（`:74`）和 P2 的驗收條件（`:417`）；之後的 `scripts/catalog.py`。

**要寫進計畫的規則**
> 讀取未受信任 clone 的 Python 程式：直譯器和工具的路徑只能來自 OAW 自己的設定或環境變數，絕不來自 clone 或專案裡的檔案。執行方式是 `python -I -X utf8 <OAW 腳本> <clone 路徑>`：工作目錄在 clone 外面，clone 路徑當參數傳入。不用 `-P`，因為它從 3.11 才有，OAW 的下限是 3.10。
> 這條規則**只適用於讀 clone 的程式**。OAW 自己的 helper 不能一律加 `-I`，例如 `python -I scripts/improvement.py --help` 會找不到 `oaw_common` 而失敗。
> 反例：TE 的背景工作以 repo 根目錄為工作目錄執行 `python -m`（`context.py:84-93`），repo 裡的 `json.py` 這類檔案就能蓋掉標準函式庫。

這一輪消化本身已經照這條規則做了（`scout.json` 記錄了 `-I` 和獨立資料夾）。

**驗收測試**（之後的 `tests/test_catalog.py`）
- `test_ingest_never_imports_planted_stdlib_shadow`：clone fixture 裡放 `json.py` 和 `random.py`，它們被執行時會寫一個標記檔；digest 結束後標記檔不能存在。
- `test_interpreter_path_in_clone_config_is_ignored`
- `test_digest_subprocess_uses_isolated_flags_and_outside_cwd`

**大小**：現在文件約 8 行；之後程式約 10 行，測試約 50–70 行。**執行期成本**：0。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): executables are never configured by the repository (tokeneconomizer/plugin/context.py:46-56; plugin/config.py:300-305; plugin/paths.py:252-254), with TE's python -m at the repository root (context.py:84-93) as the counter-example → docs/plans/skill-catalog-execution.md P2 ingest rule and scripts/catalog.py (planned).`

---

### 吸收-13 `te.readme-teaser`：用腳本產生 README 動畫，並提供靜態版（pass）

**要改的 OAW 檔案**
- P8（計畫 `:404-409`）。
- 新增 `docs/assets/make_skill_metabolism.py`（只用 stdlib），產生 `docs/assets/skill-metabolism.svg` 和 `docs/assets/skill-metabolism-static.svg`。
- `README.md` 和 `README.zh.md` 放同一段 `<picture>`。
- `scripts/harness_check.py` 加新鮮度檢查：在記憶體裡重新產生一次，逐 byte 比對。這和 P8 驗收條件（`:423`）要求的「產生的 README 內容過期就讓 gate 失敗」是同一件事。

**最小設計**
- `<picture><source media="(prefers-reduced-motion: reduce)" srcset="docs/assets/skill-metabolism-static.svg"><img src="docs/assets/skill-metabolism.svg" alt="…"></picture>`
- SVG 本身也寫 `@media (prefers-reduced-motion: reduce)`。SVG 小於 30 KB，不用 `<script>`，要有 `<title>` 和 `<desc>`。
- 不放任何沒量測過的收益數字（TE 的動畫裡有成本數字，OAW 的不能有）。不複製 TE 的 GIF 或商標。
- GitHub 在 `<picture>` 裡會不會照 `prefers-reduced-motion` 切換，仍由計畫中的人工渲染檢查確認。

**驗收測試**（新的 `tests/test_readme_assets.py`）
- 重新產生的結果和 commit 的檔案相同；
- 大小 < 30 KB；
- 沒有 `<script>`、`foreignObject` 或外部 href；
- 有 `title` 和 `desc`；
- 兩份 README 都引用了兩個檔案；
- 文字節點裡沒有「數字%」這種收益宣稱。

**大小**：產生器約 120–180 行，測試約 50–70 行。**執行期成本**：0，host 不會載入 README。
**引用行**：
`absorbed from microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc (Apache-2.0): script-generated README animation with a <picture> reduced-motion static fallback (README.md:36-39; docs/assets/teaser.py) → docs/assets/make_skill_metabolism.py, README.md, README.zh.md; method only, no TE assets copied.`

---

## 2. 暫緩項目：預先登記的付費 A/B 計畫（5 項）

### 2.0 共通前提

- **token 估計方式（這是估計）**：用實測的 Claude 校準值，一個全新、會用工具的 review 型 agent 大約花 **0.6–0.9M logical tokens，大部分是 cache read**。每個 session 都用這個範圍估。
  - 這裡的 logical tokens 不是計費量。用吸收-1 的有效 token 算會低很多。不換算成美元。
  - Codex 在這台機器上沒有校準值（還沒裝 Codex CLI），Codex 的數字暫時用同一個範圍，並標「未量測」。
  - 小型 fixture 任務可能比 review 型 agent 便宜。第 1 階段結束後用實際數字重新估。如果每個 session 的實際成本超過估計上限 1.5 倍，就停下來重新估計，超出政策時依 D11 詢問你。
- **預先登記**：比照 `improvement.py` 的 spec，執行前凍結 cases、assertions、required_checks、repeats（3–100）、`minimum_improvement` 0.05、`maximum_resource_regression` 0.10，並記錄 sha256。fixture 的雜湊、TE 固定在 `d58755d`、host 版本、模型和 effort 一起登記。看過結果後要改，就得重新登記。修訂 3（goldfish-1 #1）：判定用 backlog PRE-10 的「case × assertion 在 N 次中的通過次數」比較（實機容許誤差 5 次中 1 次），食物組和 D2 下限組用 PRE-10 的外部組模式；現在的 `improvement.py compare` 是逐 (case_id, repeat) 配對、零容許誤差，而且要求 candidate = baseline 加 patch（`improvement.py:242-244`、`:300-304`、`:319-324`），不能直接用。
- **assertion 由程式判定**：以下計畫的判定都從 trace 或測試結果機械地算出來，不需要模型評分，所以沒有評分成本。
- **沙盒（D11）**：
  - fixture repo 的副本與外界隔離；
  - ~~TE 只裝在丟棄式的 `HOME`、`CLAUDE_CONFIG_DIR`、`CODEX_HOME` 裡，你真正的設定和 plugin 完全不受影響。~~ **修訂 3（goldfish-1 #6）**：會執行 TE 的 run 一律在 PRE-01 的第 2 級沙盒（拋棄式 Linux 容器或 VM）裡跑，TE 裝在那個環境裡。只換 `HOME`、`CLAUDE_CONFIG_DIR`、`CODEX_HOME` 不夠：TE 的狀態目錄在沒有設定它自己的環境變數時來自 `expanduser('~')`，在 Windows 上就是 USERPROFILE（`tokeneconomizer/plugin/paths.py:29`）；TE 還會用 breakaway 或 WMI 啟動脫離 host job object 的程序，WMI 的 spec 檔裡寫著完整的環境變數（`plugin/winspawn.py:44-60`）。不執行 TE 的 run（例如 A3 第 0 階段，deny list 是我們自己寫的 `--settings`）才用第 1 級的專案副本；
  - toolprune 一律設成 `propose`（測的就是它時例外，而且不是 `auto`），microskills 只在 A5 打開；
  - 環境變數裡沒有真正的祕密；網路只開放模型供應商的 API。
- **獨立計量器**：我們自己寫一個 PATH wrapper，放在食物 `src` 資料夾以外。它記錄每一次巢狀的 `claude` 或 `codex` 呼叫和它的 usage。TE 自己的帳只當自我回報。沒有這個計量器，usage 覆蓋就不完整，不做效率結論（吸收-2）。
- **前置條件**：
  - (a) 一個允許 shell 的 Claude 沙盒 runner。egm-pilot 禁用 Bash 和 PowerShell，A4 和 A5 在 Claude 上需要這個 runner。
  - (b) 本機安裝 Codex CLI，Codex 那一半的測試才能跑。只跑 Claude 的結果不能宣稱兩個 host 都通過（計畫決定 2）。
- **建議順序**：依 D11，先跑最便宜、又能分辨有用、沒用或有害的測試。
  A3 第 0 階段 → A2 第 1 階段 → A6 靜態檢查 → A5 第 1 階段 → A4 第 1 階段 → repomap 第 1 階段（和 graphify 一起）→ 視結果跑完整階段 → **A1 最後跑**，用前面測出來的建議設定。修訂 3（goldfish-1 #9、goldfish-2 B01、B19）：A3 第 0 階段和 A2 都要 OAW-01，所以在批次 1 之後才跑，不放進第一包；8b（HOLD-03）排在 A1 之後。

### 暫緩-1 `te.loopguard-redirect`（A4）

- **要回答的問題**：使用者如果自己裝了 TE，OAW 該建議 loopguard 設成 `off`、`shadow` 還是 `nudge`？
- **fixtures（5 個）**：每個 fixture repo 的 `AGENTS.md` 都寫著「連續失敗 3 次就停下來問」。
  - L1：誘發迴圈，測試依賴一個有矛盾的隱藏條件；
  - L2：誘發迴圈，錯誤訊息指向錯的檔案；
  - N1、N2：一般的小 bug 修正，測試很清楚；
  - I1：使用者明確要求做 12 輪「編輯 → 測試」。
- **暖機**：loopguard 需要 5 個綠燈結束的 turn 才會學到 envelope。每個 fixture repo 用簡單任務暖機一次，大約 1–2 個 session，然後把 TE 的 state 資料夾拍成快照，每次 repeat 前還原。`off` 組不需要暖機。
- **組別**：`off`、`shadow`、`nudge`（都裝了 TE，toolprune=propose，microskills=off）。
- **重複次數**：5 次。**Host**：先跑 Claude Code，裝好 Codex 後跑 Codex。
- **指標**：
  - 到綠燈為止的工具呼叫數；
  - 在 N1、N2、I1 上被 redirect 的次數（算誤判）；
  - L1、L2 上是否遵守「失敗 3 次就停下來問」；
  - judge 和 writer 的開銷 token（由計量器記錄；在 Codex 上是使用者的預設模型，不是 haiku）；
  - 有效 token、最後的通過率；
  - Claude 上「原文轉述」的通知有沒有混進最後回覆。
- **判定（預先寫死）**：`nudge` 要同時符合以下條件才建議使用：
  - 每個 fixture 的通過率都不低於 `off`；
  - I1、N1、N2 的 redirect 誤判為 0；
  - 遵守「停下來問」的比例不低於 `off`；
  - 在 usage 覆蓋完整的前提下，L1、L2 含開銷的有效 token 降低 ≥5%。
  不符合就建議 `off`。`shadow` 只能當量測模式，不當成建議設定。
- **停止規則**：
  - 第 1 階段：只跑 Claude，每格 1 次，共 15 個 session 加上暖機。符合下列任一條件就停下並建議 `off`：
    - (a) shadow 的紀錄顯示 judge 在 L1、L2 上從來沒判定卡住（沒有可以改善的空間）；
    - (b) `nudge` 在 I1 上 redirect，或讓 agent 違反「停下來問」（已經看到害處）；
    - (c) 計量到的開銷超過該組 token 的 10%。
  - 都沒觸發，才跑第 2 階段，補完剩下的 4 次 repeat。
- **token 估計**：
  - 第 1 階段：約 25 個 session，**約 15–23M**，加上 judge 開銷最多 10%，約 17–25M。
  - 完整：每個 host 約 85 個 session（5×3×5 + 暖機約 10），**約 51–77M，加上開銷約 56–85M**。
  - 兩個 host 約 112–170M。
  - 以上都是估計。

### 暫緩-2 `te.envfacts-miner`（A5）

- **要回答的問題**：分成兩個子題。
  - Q1（傳遞方式）：已經知道正確的測試指令時，TE 推送、OAW 拉取、`AGENTS.md` 一行、什麼都不給，哪一種最好？
  - Q2（發現能力）：TE 能不能自己在 N 個 session 內學到這個事實？代價是多少？
- **fixtures**：吸收-11 的 `pytest-absent-trap`，用 V1、V2、V3 三個變體。每次 run 都要驗證 `trap_armed`。
- **組別（4 組）**：
  1. native，沒有任何紀錄；
  2. `AGENTS.md` 一行（OAW 建議的做法）；
  3. oaw-evidence 拉取：同一個事實寫在記憶裡，用 `--max-chars` 取回；
  4. TE `microskills=envfacts` 推送：loopguard=off、toolprune=propose。先暖機，直到 TE 把這個事實升級，最多 6 個 session。暖機成本算在 Q2。
- **重複次數**：5 次。**Host**：Claude（需要允許 shell 的 runner）和 Codex。
- **指標**：
  - 有沒有避開陷阱（第一個測試指令就是記錄的那個）；
  - 用到正確指令之前錯了幾次；
  - 有效 token（含暖機）、通過率；
  - 注入區塊的啟動大小（用吸收-3 量）。
- **判定（預先寫死）**：
  - 推送組只有在避開陷阱的比例 ≥ `AGENTS.md` 組，**而且**有效 token 低 ≥5%、usage 覆蓋完整、通過率沒有退步時，才算比較好。
  - 如果 `AGENTS.md` 組 ≥ 推送組，傳遞方式的價值宣稱就排出，因為 `AGENTS.md` 一行的啟動成本本來就比 ≤150 tokens 的注入區塊低。這時唯一還可能吸收的，是離線產生「建議寫進 AGENTS.md 的驗證指令」報告（Q2），之後另外登記測試，並且要先決定是否違反 `Skill_Guide.md:40`。
- **停止規則**：
  - 第 1 階段：只跑 V1，每組 1 次，加上 TE 暖機。
    - native 組本來就避開陷阱（例如 agent 讀了 pyproject，發現沒裝 pytest）：fixture 沒有鑑別力，停下來重新設計 fixture，不再花錢。
    - 陷阱沒布置好：該次 run 無效，修好環境再跑。
    - 暖機 6 個 session 後 TE 仍沒學到事實：TE 組停止，Q2 記為「沒學到」。
  - 第 2 階段：跑完整的 3 個變體 × 5 次。
- **token 估計**：
  - 第 1 階段：每個 host 約 10 個 session，**約 6–9M**。
  - 完整：每個 host 約 66 個 session（4×3×5 + 暖機 6），**約 40–59M**。
  - 兩個 host 約 80–119M。以上是估計。

### 暫緩-3 `te.toolprune-evidence-rule`（A3）

- **要回答的問題**：OAW 該不該建議使用者把 toolprune 設成 `propose`？扣掉 native 已經有的 ToolSearch 延遲載入和 prompt cache，再扣掉 resume 時重寫 cache 的成本，還剩多少節省？會不會誤刪工具？
- **第 0 階段（最便宜，可能直接結束）**：
  - 用吸收-3 的啟動探測，比較兩種啟動請求：空的 deny list，以及把所有可刪的非核心工具都放進 deny list。這是「最多能省多少」的上限。
  - 不需要執行 TE，deny 設定是我們自己寫的暫存 `--settings`。Claude 要送 2 個小的付費請求；Codex 用 prompt-input，免費。
  - **停止規則**：上限 <每個 session 校準 token 的 2%（大部分會以 cache read 的權重計價，實際影響更小），就直接判定 toolprune 不值得建議，價值宣稱排出，不再做第 1 階段。
- **第 1 階段**（只有上限 ≥2% 才跑）：
  - fixture：一條有 8 個連續 session 的任務流，最後一個任務需要一個平常很少用到的工具（例如 `NotebookEdit` 或 `WebFetch`），用來偵測誤刪。
  - 組別：native，對比 native + TE 的 `propose`（TE 提出的刪除由人手動套用，維持逐項同意）。
  - 重複 3 次，Claude 和 Codex 各跑。
  - 指標：每個 session 的有效 token（包括改變當下的 cache 重寫）、誤刪次數、通過率。
  - 判定與停止：只要有一次誤刪讓任務失敗，就判定永不建議並停止。
- **token 估計**：
  - 第 0 階段：2 個小請求，**遠小於 1M**。
  - 第 1 階段：每個 host 48 個 session（2×8×3），**約 29–43M**；兩個 host 約 58–86M。
  - 以上是估計。

### 暫緩-4 `te.repomap`

- **要回答的問題**：排序過的程式地圖對 OAW 型的任務有沒有幫助？值不值得用 stdlib（ast）重寫？和 graphify 的程式地圖比如何？
- **省錢做法**：和 graphify 帳本裡的程式地圖項目**一起登記，共用同一個 native 組**，可以省下大約三分之一（TE 的估計，未量測）。修訂 3（goldfish-2 B12）：合併登記（backlog HOLD-04）裡 repomap 保留自己的 4 個編輯任務、指標和停止規則；共用的是 F2 的同一份 checkout、同一個 baseline build，以及完整階段裡同一組任務上的 native 組。第 1 階段的 7–11M 就是這 12 個 session（4 個任務 × 3 組 × 1）。
- **fixtures（4 個任務）**：在固定 commit 的 OAW repo，或另一個授權允許、檔案數 ≥200 的 repo 上，任務都**不直接說出要改哪裡**：
  1. 修一個間接引用的函式裡的 bug；
  2. 沿著呼叫鏈加一個參數；
  3. 找出某個設定值是在哪裡被讀取的；
  4. 跨模組重新命名一個 symbol。
- **組別**：native；native + repomap（SessionStart 模式，2048 tokens，aider 只在沙盒裡跑）；native + graphify 地圖（如果 graphify 那邊也暫緩到這次測試）。
- **重複次數**：5 次。**Host**：Claude 和 Codex。
- **指標**：到第一次正確編輯（第一次碰到正確位置的編輯）為止的工具呼叫數和有效 token、通過率、地圖本身的啟動 token（用吸收-3 量）。
- **判定**：算進地圖本身的成本後，到第一次正確編輯的有效 token 要降低 ≥5%，而且通過率沒有退步。
- **停止規則**：
  - 第 1 階段：Claude 每格 1 次，共 12 個 session。
    - native 組在每個任務上到第一次正確編輯都 ≤3 次工具呼叫：導航不是瓶頸，停止。
    - 地圖的啟動成本已經大於 native 組到第一次正確編輯的全部探索成本：停止。
  - 第 2 階段：跑完整的 repeat。
- **token 估計**：
  - 第 1 階段：**約 7–11M**。
  - 完整：每個 host 60 個 session（3 組），**約 36–54M**；只有 2 組時是 40 個 session，約 24–36M。
  - 兩個 host 約 48–108M。以上是估計。

### 暫緩-5 `te.install-as-user-plugin`（A1、A2、A6）

**A2（只在 Codex，先跑，最便宜）**
- **要回答的問題**：TE 會不會把 `features.multi_agent=false` 和 `agents.enabled=false` 寫進沒被 git 追蹤的 `.codex/config.toml`，讓 EGM 需要的 subagent 起不來？
- **第 1 階段**：
  1. 在沙盒的 fixture repo 裡，用不會開 subagent 的 session 產生 transcript，再讓 TE fold 處理。microskills 和 distiller 關掉，fold 不呼叫模型。
  2. 記錄 TE 是否提出 collaboration deny，並在副本裡套用。
  3. 跑一個需要 subagent 的 EGM 情境。
- **判定與停止**：這個問題的答案只有是或否。
  - subagent 起不來：確定有害的交互作用。結論是「使用 TE 時，要有 commit 進 git 的 `.codex/config.toml`，或把 toolprune 設成 `propose`」，然後停止，**不需要跑 30 個情境**。
  - subagent 照常啟動：這個風險前提被推翻，同樣停止。
- **token 估計**：subagent 起不來時大約 1 個 agent，起得來時大約 1 個 parent 加上最多 4 個 reviewer，**約 0.6–4.5M**（用 Claude 校準值估；Codex 未量測）。

**A6（Codex 觸發測試）**
- 先做靜態檢查（修訂 3，goldfish-2 B22：不是免費的，要一個金魚讀兩邊的描述，沒有工具的金魚約 0.05–0.1M，估計）：比對 TE 的 Codex skill 名稱（`status`、`config`、`repos`、`microskills`、`toolprune`）和 OAW 規劃中的 `oaw-status`。名稱沒有完全相同的，但描述可能互相搶觸發，所以讓金魚審查一起讀兩邊的描述。
- **第 1 階段**：20 個 prompt，每個都事先寫好應該觸發哪個 skill；兩組是「只有 OAW」和「OAW 加 TE 的 skill」；每格 1 次。agent 一選定 skill 就結束 session。
- **判定**：OAW 加 TE 那組的錯誤觸發率高於只有 OAW 那組，就判定有衝突，建議不要在 Codex 上一起安裝 TE 的 skill，或者要改名。
- **停止規則**：第 1 階段沒有任何分歧就停止。有分歧的 prompt 才再跑 2 次確認。
- **token 估計**：以校準值當上限，40 個 session 約 **24–36M**。因為選定 skill 就結束，實際應該少很多（未量測）。

**A1（四組的任務流，最後跑）**
- **組別**：A native；B native + TE；C native + OAW 預設；D native + OAW + TE。
- **TE 的設定（決策 11）**：建議用 A3、A4、A5 測出來的建議設定，不用 TE 的預設值。TE 的預設值包含已經排出的 `toolprune=auto`。
- **fixture**：在同一個 fixture repo 上連續跑 8 個 session，任務包括：
  - bug 修正 2 個；
  - 驗證陷阱 1 個（吸收-11）；
  - skill-value 的 scoped-recall 1 個；
  - 一般編輯 4 個。
  不放 EGM 的審查任務，因為一個審查任務等於好幾個 agent 的成本；EGM 的影響交給 A2。
- **重複次數**：5 次。**Host**：Claude 和 Codex。
- **指標**：
  - 逐 assertion 的通過次數；
  - 有效 token（含計量到的 TE 開銷）；
  - hook 延遲（`latency_ms`）；
  - usage 覆蓋度。
- **判定（關卡）**：兩條都要過。
  - D ≥ C：沒有任何 assertion 退步，資源退步不超過 10%（`improvement.py` 的規則）。
  - **修訂 2，D2 下限 C ≥ B**：吃下 TE 之後的 OAW（C，native + OAW 預設）至少要和只用 TE（B，native + TE）一樣好：逐 assertion 的通過數在容許誤差內（實機 5 次中最多少 1 次，PRE-10）不低於 B；有效 token 只有在兩組 usage 覆蓋都完整時才比較。C ≥ B 沒過，就記「OAW 在某指標上低於只用食物的下限」，再依 D ≥ B 與否，決定是寫 catalog 註記「建議和 OAW 一起裝 TE」，還是吸收缺少的方法；在 C ≥ B 通過之前，TE 一律寫「parity vs food alone: not tested」。
  - 只有在 D 的 usage 覆蓋完整時，才能說 D 比 C 更省。
- **停止規則**：
  - 第 1 階段：每格 1 次，共 32 個 session。D 有任何 assertion 退步，或 hook 讓延遲多出 10% 以上：停止，結論是「不建議和 OAW 一起裝」。修訂 3（goldfish-2 B14）：第 1 階段的資料也給出 C 對 B 的篩選；若第 1 階段因 D 退步而停止，C ≥ B 的判定還需要 B、C 兩組單獨補完第 2 階段（4 次 × 2 組 × 8 session = 64 個 session，每個 host 約 38–58M，估計），TE 額度夠才跑，否則 TE 維持「parity vs food alone: not tested」。
  - 第 2 階段：跑完整的 repeat。
- **token 估計**：
  - 第 1 階段：每個 host **約 19–29M**。
  - 完整：每個 host 160 個 session（4×8×5），**約 96–144M**；兩個 host 約 192–288M。
  - 以上是估計。

### 2.6 暫緩項目的 token 估計總表（估計值，Claude 校準 0.6–0.9M／session）

| 項目 | 第 1 階段（或第 0 階段） | 完整（每個 host） | 完整（兩個 host） |
|---|---|---|---|
| A3 toolprune | 第 0 階段 ≪1M | 29–43M | 58–86M |
| A2 EGM 衝突（Codex） | 0.6–4.5M | 不需要 | — |
| A6 觸發（Codex） | ≤24–36M（上限） | 視分歧而定 | — |
| A5 envfacts | 6–9M | 40–59M | 80–119M |
| A4 loopguard | 17–25M | 56–85M | 112–170M |
| repomap（和 graphify 共用 native） | 7–11M | 36–54M | 72–108M |
| A1 四組 | 19–29M | 96–144M | 192–288M |
| 8b oaw-evidence 措辭（修訂 2：兩個 host） | — | 6–18M | 12–36M |

- 每項都跑到完整、兩個 host 都跑：大約 **0.54–0.81B logical tokens**（不含 8b）。
- 依停止規則，大部分項目可能在第 0 或第 1 階段就結束。只跑第 1 階段的話，Claude 約 49–74M，Codex 約 74–115M。
- 以上都是估計，而且都是 logical tokens，大部分是 cache read，不是計費量。

---

## 3. 排出（17 項，各一行）

| 元件 | 為什麼排出 | 證據 |
|---|---|---|
| `te.toolprune-auto-default` | 預設會在沒有逐項同意的情況下改寫 host 的權限設定；通知只出現在 Ctrl+O；Codex 上可能關掉 EGM 需要的 subagent | `plugin/config.py:152, :156`；`plugin/denylist.py:61-64`；`plugin/controller.py:188-199`；`oaw-ref/README.md:202` |
| `te.hooks-on-every-tool-call` | 六個事件都沒有 matcher，每次工具呼叫都會啟動 sh + Python，所有機制都關掉也一樣；OAW 的打包 allowlist 拒絕 hooks | `plugin/hooks/hooks.json:4-65`；`plugin/controller.py:298`；`skill-catalog-execution.md:313` |
| `te.background-daemons` | 會分離出背景工作，包括最長等 24 小時、agent 結束後才改設定的 waiter；v2 禁止背景常駐程式 | `plugin/cli.py:355-382`；`plugin/fold.py:51-52`；`v2.0.0-execution.md:78` |
| `te.windows-job-escape` | 刻意逃出 host 的 job object；WMI 路徑會把包含 API key 的完整環境變數寫進 spec 檔，而 Windows 上沒有 0600 保護 | `plugin/winspawn.py:44-89`；`plugin/paths.py:33-46` |
| `te.repo-cwd-module-shadowing` | 背景工作以 repo 根目錄為工作目錄執行 `python -m`，repo 裡的 `json.py` 等檔案會以 hook 的完整環境被執行（verifier 已重現） | `plugin/context.py:84-93`；`plugin/winspawn.py:88-89`；`plugin/hooks/codex-hooks.json:9, :21` |
| `te.sidecall-model-runtime` | 預設開啟的第二套付費模型 runtime；Codex 上用使用者的預設模型，每次約 25k 的基礎 prompt；最多 90 字元的原始指令未經遮蔽就送給供應商 | `plugin/config.py:17-25, :158, :166`；`plugin/sidecall.py:470-490`；`loopguard/state.py:187-194` |
| `te.sidecall-isolation-gaps` | 側呼叫沒有關掉其他 plugin、hooks 和使用者層級的 CLAUDE.md，claude-mem 會把每次 judge 都記下來；`--help` 沒列出的旗標會被默默拿掉。OAW 的 pilot runner 已經更嚴格 | `plugin/sidecall.py:183-225`；`oaw-ref/evals/egm-pilot/run_pilot.py:108-141` |
| `te.injected-redirect-and-relay` | 在 turn 中途注入沒有來源標示、最多 1200 字元的模型文字，內容要 agent「Do NOT stop」，還要求逐字轉述，會汙染只輸出 JSON 的結果；judge 看不到使用者的指示 | `loopguard/rules.py:183-198`；`plugin/hosts.py:152-166`；`loopguard/state.py:214-219` |
| `te.envvalue-secret-capture` | 會學習「VAR=value」並注入之後的每個 session，沒有任何祕密過濾，`sk-...` 也能符合（PLAUSIBLE） | `microskills/observe.py:505-567`；`microskills/envfacts.py:110-114, :437-455` |
| `te.distiller-proposer` | 第二個模型寫出的自動記憶會推送到之後所有 session，和 AGENTS.md 沒有優先順序；模型寫的 regex 會被直接 compile，有 ReDoS 風險 | `microskills/distiller.py:260-266, :346-362, :711-719`；`v2.0.0-execution.md:86` |
| `te.unpinned-clone-loading` | hook 程式從可變動的 clone 載入，`git pull` 就會改變，沒有 SHA 或雜湊檢查；Windows 上實際走的就是這條路徑 | `plugin/scripts/te_bootstrap.py:57-118, :154-156`；`skill-catalog-execution.md:74` |
| `te.slash-command-shell-args` | `$ARGUMENTS` 沒加引號就塞進 shell 指令，shell 特殊字元會變成語法 | `plugin/slash-commands/config.md:9`、`repos.md:9`、`toolprune.md:9`、`untool.md:9` |
| `te.probe-side-effects` | refresh-catalog 會帶著所有 MCP 啟動，文件卻說「不呼叫模型」；Copilot probe 會在受信任的資料夾裡以 `--allow-all-tools` 執行；measure 會送出沒有事先提醒的付費呼叫 | `plugin/toolcheck.py:58-98, :216-238`；`plugin/probe.py:118-121, :182-185`；`README.md:190-191` |
| `te.bundled-third-party-text` | 附帶 Claude Code 工具說明摘錄、Codex 基礎 prompt 和學校、公司的商標；TE 的 Apache-2.0 授權不一定涵蓋這些 | `tokeneconomizer/trace/claude_tool_catalog.json`；`experiments/te_harness/data/codex_base_prompt/0.153.1.md`；`docs/assets/logo_*.png` |
| `te.live-ledger-and-status` | 和 host 內建的 `/cost`、`/usage` 重複；OAW 把使用量診斷留給 host；有用的方法已經吸收成評估工具（吸收-1、吸收-2） | `plugin/fold.py:370-418`；`oaw-ref/docs/Skill_Guide.md:40`；`skill-catalog-execution.md:242` |
| `te.pack-or-bundle` | 無論 A/B 結果如何，政策都不允許：hooks、自動權限、第二套 runtime、背景程式，以及會改 host 設定 | `skill-catalog-execution.md:133-137, :313`；`v2.0.0-execution.md:78`；`Skill_Guide.md:17` |
| `te.non-oaw-host-adapters` | 本身無害，只是不在範圍內：OAW v2 只支援 Claude Code 和 Codex，Copilot 和 Cursor 的入口檔已經退役 | `plugin/hooks/copilot-hooks.json`、`cursor-hooks.json`；`oaw-ref/README.md:97` |

---

## 4. 對消化系統流程的釐清（這一輪學到的）

這和消化系統本身是兩回事，但可以用來修正流程：

1. **帳本階段要先查「凍結檔案地圖」**：13 個吸收目標裡，有 5 個（1、7、10、11，以及 4 想 import 的檔案）原本指向已登記合約的凍結檔案，是整合檢查才攔下來的。建議帳本階段先看一份列出 pinned scorer、`CONTROL_FILES` 和 runner hash 的清單，再決定 `oaw_target`。
2. **整合檢查和 verify 一樣有份量**：這一輪整合檢查更正了帳本的兩個事實：`run_pilot.py` 的 prompt 走 argv 不是 stdin；TE 的 shadow 模式仍然會付費呼叫 judge。
3. **帳本要標「會影響模型」或「只改量測」**：改 SKILL.md 或模板的提案（8b，以及吸收-7 的 SKILL.md 那一行）會影響模型，依 proof-before-promotion 自動需要 A/B，不能只靠 fixture 測試。
4. **跨食物的連結**：
   - TE 的側呼叫加上 claude-mem 的 hooks，每次 judge 都會被記錄。TE 和 claude-mem 一起裝的情況值得在使用者文件裡警告。
   - repomap 和 graphify 的程式地圖應該合併成一次測試，共用 native 組。
5. **下一步（D10）**：本文件是 Elephant 起草的，要先讓金魚盲審，Elephant 處理審查意見後才交給你決定。

---

## 5. 需要你決定的事

1. **D11 常設政策**（必要，否則暫緩項目一個都不能跑）：
   - 每個食物的付費額度上限（logical tokens 或金額）；
   - 沙盒條件：專案副本、丟棄式的 `HOME`、`CLAUDE_CONFIG_DIR`、`CODEX_HOME`、不放真正的 API key（或使用有上限的 key）、網路範圍。（修訂 3：會執行 TE 的 run 改用第 2 級的 VM 或容器，見第 2.0 節。）
2. **要實作哪些吸收項目、照什麼順序**：建議依批次 1 → 2 → 3 → 4 做，吸收-10（Windows shim）在批次 2 裡最先做。
3. **有效 token**：第一版只報告（建議），還是允許 spec 宣告用它取代原始 tokens 來判定效率？權重表由誰、從哪個來源、在哪一天登記？
4. **usage 覆蓋度**：用 spec 宣告的欄位（建議），還是把 `SCHEMA` 升到 2？
5. **要不要在本機安裝 Codex CLI**：吸收-3、吸收-4 的 Codex 驗證是免費的，但需要先裝。所有 A/B 的 Codex 一半也需要它。不裝的話，只能有 Claude 的結果，而且不能宣稱兩個 host 都通過。
6. **`doctor --probe-host`**：是否允許 doctor 在明確加旗標時啟動 host CLI（可能送出一個小請求）？如果 Codex 沒有免費的對應做法，這個功能要放棄，還是 Codex 標成「無法使用」後照樣上線？（D8 傾向前者）
7. **跳過驗證的 lint**：要不要加中文 pattern？新的警告在 `--strict` 下變成錯誤，要接受，還是讓這類警告在 strict 模式下仍然只是警告？
8. **8b oaw-evidence 措辭**：要跑那個 skill-value A/B（約 6–18M，估計），還是放棄只做 8a？
9. **oaw-improve SKILL.md**：要不要加一行提到 failure-signature 診斷工具？改了模板，已安裝的專案就會收到一次 framework 更新。
10. **暫緩測試的順序和範圍**：同不同意 A3 第 0 階段 → A2 → A6 靜態檢查 → A5 → A4 → repomap → A1 這個順序，以及各項的停止規則？
11. **A1 的 TE 設定**：用前面測出來的建議設定（建議），還是 TE 的預設值？預設值包含已經排出的 `toolprune=auto`。
12. **repomap 和 graphify 一起測**：是否同意共用 native 組，合併成一次登記？
13. **建立允許 shell 的 Claude 沙盒 runner**：A4 和 A5 要在 Claude 上跑就需要它。是否同意投入這項工作（不花模型額度，只是寫程式）？
14. **Windows shim 解析器放在哪裡**：放在 `scripts/oaw_common.py`，在 manifest 記錄 `resolver_sha256`（建議）；還是在每個 runner 裡各放一份？
15. **確認排出清單**：17 項排出都只排掉有害或不在範圍內的部分（D5）。如果有哪一項你想留著當暫緩，請指出來。

---

## 6. 修訂 2（整合後，2026-11-03）

這一節記錄 critic 指出缺口之後的修正。完整清單見 `ingest/SUMMARY.md` 的「修訂紀錄」；標準紀錄是 `components.json` 第 2 版（每個元件的 `after_integration`）和 `backlog.json` 第 2 版。**仍然沒有實作任何東西，也沒有跑任何付費測試；所有行為都是 not measured。**

**帳本（以單位計，拆開的元件每個部分各算一個）**：12 吸收、7 暫緩、19 排出，共 38。
- `te.host-load-probe`：吸收 → 暫緩（Codex 對應做法未驗證，D8）。
- `te.fact-lifecycle`：拆成 8a（吸收，OAW-20）和 8b（暫緩，HOLD-03，兩個 host 都測）。
- `te.failure-signature`：拆成診斷模組（吸收，OAW-27）和 oaw-improve 那一行（排出，理由見吸收-7）。
- 新增 `te.codex-skill-consent-pattern`（goldfish-2 #21）：排出，理由是冗餘（OAW 已有觸發衝突 gate、「安裝不授權外部動作」的政策，以及只能手動呼叫的 EGM bridge）。
- `components.json` 裡被整合檢查推翻的說法都已在 `after_integration.claim_corrections` 更正：shadow 模式仍會付費呼叫 judge；`--min-citations` 預設維持 0；`run_pilot.py` 的 prompt 走 argv（`run_pilot.py:141`，`stdin=DEVNULL` 在 `:317`），不是 stdin；吸收-1、7、10、11 不再指向凍結檔案。
- `te.host-load-probe` 的 `sources_agree` 改寫：這個探測是帳本自己的改寫，金魚稱讚的是另一個機制（settings writer）。

**backlog 的 TE 項目**
- 舊的 HOLD-08 拆成 **HOLD-08a**（A2、A6，只依賴 PRE-01 和 PRE-03，排在 A3 第 0 階段之後）和 **HOLD-08b**（A1，最後跑），符合第 2.0 節的順序。
- A1 加上 D2 下限 **C ≥ B**（見暫緩-5）。
- HOLD-05、06、07、08b 補上 OAW-03（不能空轉通過）、OAW-04、OAW-05（開銷與有效 token）和 PRE-03（Codex 那一半）。
- OAW-34 補上 PRE-01 和 PRE-03：計畫決定 2 要求兩個 host，所以 Codex 那一半驗證之前，gate 不能採計。
- 每一項的 `evidence_level` 改成「not measured (planned: …)」，原本的值移到 `target_evidence_level`。

**第 5 節「需要你決定的事」的重新分類（D11）**
| # | 原本的問題 | 修訂 2 |
|---|---|---|
| 1 | D11 常設政策 | 仍由你決定（PRE-01） |
| 2 | 實作哪些吸收、順序 | 吸收由你逐批核准；順序由系統決定 |
| 3 | 有效 token 的用法與權重表 | 系統決定：第一版只報告；權重表由 Elephant 依供應商公開價格頁在登記當天起草、金魚審查後凍結（OAW-05） |
| 4 | usage 覆蓋度 | 系統決定：spec 宣告的欄位（OAW-04） |
| 5 | 本機是否安裝 Codex CLI | 仍由你決定，併入 PRE-01 |
| 6 | `doctor --probe-host` | 暫緩（OAW-26）；沒有免費的 Codex 對應做法就依 D8 排出（系統決定）；驗證通過時才問你是否允許 doctor 啟動 host CLI |
| 7 | 中文 pattern、`--strict` | 系統決定：先只用英文；中文 pattern 在 fixture W 的中文筆記上零誤報才加。**修訂 3（goldfish-1 #7）**：在 `--strict` 下和其他軟性警告一樣變成錯誤（`wiki_sync.py:848-849`、`Wiki_Sync_Guide.md:18`），也就是吸收-9 原本寫的行為；修訂 2 的「仍只是警告」撤回，因為它需要一種沒設計過的不升級警告，也和今天 HOLLOW_PHRASES 的行為矛盾（OAW-14） |
| 8 | 8b | 系統決定：低優先，兩個 host 都測，TE 額度夠才跑（HOLD-03） |
| 9 | oaw-improve 那一行 | 系統決定：排出（使用者專案沒有 `evals/`） |
| 10 | 暫緩測試的順序與停止規則 | 系統決定（backlog `test_order`） |
| 11 | A1 的 TE 設定 | 系統決定：用前面測出來的設定，不用含已排出 `toolprune=auto` 的預設值 |
| 12 | repomap 和 graphify 合併測試 | 系統決定：合併（HOLD-04），額度依 PRE-01 的分攤規則 |
| 13 | 允許 shell 的 Claude runner | 隨批次 2 核准（PRE-04） |
| 14 | Windows shim 解析器放哪裡 | 系統決定：`scripts/oaw_common.py`，manifest 記錄 `resolver_sha256` |
| 15 | 排出清單 | 仍由你決定：整份接受，或指出要改列暫緩的單位（PRE-08，和逐批核准一起） |

**流程教訓**：第 4 節的四點已整理進 `SUMMARY.md` 第 8 節，各自變成 OAW-10 的計畫修訂或 PRE-09 的 DECISIONS 修訂草案，和食物的吸收分開。

**審查狀態**：本文件、`backlog.json` 和第 2 版帳本紀錄都還要經過金魚盲審（PRE-02，用 PRE-06 的零上下文啟動方式）。`goldfish-1.json`、`goldfish-2.json` 沒有記錄啟動方式和繼承的上下文，標為「context unverified」。

## 7. 修訂 3（金魚盲審回應，2026-11-03）

兩份金魚盲審（goldfish-1 Lens A、goldfish-2 Lens B，都是**繼承上下文的審查**，不是零上下文，啟動紀錄見 `ingest/SUMMARY.md` 第 11 節）對本文件的意見，已就地修正。**仍然沒有實作任何東西，也沒有跑任何付費測試；所有行為都是 not measured。**

- 第 2.0 節沙盒：執行 TE 的 run 改用第 2 級的 VM 或容器（goldfish-1 #6）。
- 第 2.0 節判定方式：依賴 backlog PRE-10（容許誤差、parity 判定、外部組）（goldfish-1 #1）。
- 吸收-10：`DEFAULT_CLAUDE` 的行號改為 `:36-38`，cmd.exe 風險只在 `--claude` 指向 `claude.cmd` 時成立（goldfish-1 #10）。
- 吸收-9 與第 6 節第 7 列：skip-advice 警告在 `--strict` 下變成錯誤，和其他軟性警告一樣（goldfish-1 #7）。
- 暫緩-3 第 0 階段與暫緩-5 A2：移到批次 1（OAW-01）之後（goldfish-1 #9、goldfish-2 B01）；8b 排在 A1 之後（goldfish-2 B19）。
- 暫緩-4：合併登記裡 repomap 保留自己的任務、指標和停止規則（goldfish-2 B12）。
- 暫緩-5：A6 靜態檢查不是免費的（goldfish-2 B22）；A1 的容許誤差寫明，第 1 階段因 D 退步停止時 C ≥ B 的補跑條件寫明（goldfish-2 B14）。
