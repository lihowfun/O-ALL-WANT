# X3b：W1 修正後重跑 X3（2026-11-07，跑之前登記）

X3（`records` 的 fea2474）在 Haiku 上不通過：A 4/6、B 2/6、0 2/6。A 錯的兩題都是 deep，原因有兩個：
- dry run 的文字讓 agent 連計畫都跳過；
- `suggest --paths` 不認目錄。

`claude/oaw-2` 的 d32561f 修了這兩點：
1. `--paths` 收到資料夾時，把它當成「要在裡面新增的檔案」：已存在的資料夾、結尾有斜線的、或已知的觸發資料夾（`migrations`、`db/migrations`、`.github/workflows`、`docs/plans`、`templates` 等）都算。
2. dry run 的文字改成「run no review and record nothing; still plan first when a step says so, and stop before changing code at a design review」。`oaw_mode.py` 的輸出和 `oaw-review` skill 都改了。

X3b 用同一套情境和評分，量修正後的 2.0.1。沒寫到的地方都照 X3 的 `PREREG.md`。

## 和 X3 相同的部分
- 測試專案：`make_fixture.py`，沒有改動。
- 六個情境（L1、L2、S1、S2、D1、D2）：需求原文、預期模式都和 X3 一樣。
- 主機與指令完全相同：
  - Claude Code 2.1.287，`--effort high`，`--max-turns 30`，逾時 900 秒；
  - `--tools Read Edit Write Glob Grep Bash Skill --allowedTools Bash --setting-sources project --strict-mcp-config`；
  - 清掉 `ANTHROPIC_*` 和 `CLAUDE*`，PATH 上沒有 `claude` 和 `codex`，apiKeySource 必須是 none。
- 機械評分照 X3 的規則（改程式、計畫文件、模式檢查、開審查、實際走的模式），只有下面「改了的部分」列出的兩處不同。

## 組別
- **0**：OAW 2.0.0（332c585），和 X3 的 0 組是同一個 repo（同一份複本）。
- **A**：OAW 2.0.1 的 d32561f，`oaw.py init --host claude`。AGENTS.md 原樣（一句 EGM 加兩行政策），加上 `oaw-review` skill，`.oaw/settings.json` 設 `{"review": {"dry_run": true}}`。
- **B 拿掉**：X3 已經量到只有 skill 不會被叫用，政策行要留。

## 模型與次數（30 次）
- **Haiku 5.5**：只跑 A，6 次。
  - 0 組直接沿用 X3 的 6 次（haiku-*-0）：CLI 版本、模型、測試專案和 2.0.0 程式都相同。
  - 這 6 份紀錄用 X3b 的評分程式重新評一次（見下面第 2 點），token 不算進 X3b 的預算。
- **Opus 5.5、Sonnet 5.5**：0 和 A 各 6 次，共 24 次。
- 已用 0 token 核對 d32561f 下的預期模式（`verify_modes.py`）：
  - 六個情境的預期模式和 X3 相同。
  - 用資料夾寫的計畫，A 組判成 deep：D1 `--paths .github/workflows`，D2 `--paths migrations ledger/store.py tests/test_store.py`。0 組（2.0.0）照舊判成 light。

## 改了的部分（跑之前寫死）
1. **A 組 deep 的「做對」**：dry run 下，以下三件事都要成立：
   - 在任何改程式之前跑過 `oaw_mode.py suggest`（Bash）；
   - 寫了計畫文件，或在回覆裡提出計畫（最後的回覆含 plan 這個字）；
   - 整次都沒改程式，而且正常結束。

   先寫計畫再改程式，在 X3 算對，在 X3b 的 A 組算錯，因為新的 dry run 文字要求停在改程式之前。0 組沒有 dry run，deep 照 X3 的規則：改程式之前寫計畫，或停下來不改。
   每次作答也記 X3 規則下的結果（`correct_x3_rule`），方便和 X3 對照。
2. **Bash 改檔的漏判（X3 偏離第 3 點）**：
   - Bash 指令有寫檔動作、但指令裡沒有程式路徑時（例如 `git grep -l X | xargs sed -i …`），先記成「可能改了程式」。
   - 結束時專案裡有程式改動，又找不到是哪個 Edit、Write 做的，這些指令就算改程式。
   - 用這個規則重評 X3 的 Haiku 0 組：haiku-S1-0 從 none 變成 light，6 題對錯都不變（2/6）。

## 順序與預算
- 順序：先 Haiku（A），再 Opus，最後 Sonnet。每塊內 6 個情境的順序輪替，同一情境的 0 和 A 同時開跑，開跑順序也輪替。完整順序由 `run.py order` 印出。
- **預算上限 9M Claude logical token**，只算 X3b 新跑的作答。
- **停止規則**：每組開跑前，已花 + 組內次數 × 目前看過的最大單次（含 X3，起始值 379,951）> 9M 就停，不跳著跑。
- 被用量上限切斷或花 0 token 的作答算「沒跑」，花掉的 token 照算，之後接著跑。
- 預估：A 組 deep 這次會停在改程式之前，比較便宜。全部約 5–8M。

## 判定（和 X3 相同）
- 對每個模型：A **至少 5/6 做對，而且做對數不少於 0**，就算通過。
- 三個模型都報告。每格只跑 1 次，只描述行為，不做顯著性檢定。
