# Claude V2：skill 吸收流程、論文原型、D21 第一輪吸收與程式碼索引

`claude/oaw-2` → `codex/oaw-2-native-upgrade`（PR #4 merge 之前用這個 base；PR #4 merge 之後改成 `main`）。依 D22，這是 Claude 這邊唯一的 V2 分支。決定紀錄 D1–D24 在 `records` 分支的 `records/digestion-2026-11-03/ingest/DECISIONS.md`。

## 內容
1. **新增 skill 的正式流程和消化系統**（D4–D19、D21、D23）
   - `scripts/catalog.py`、`catalog_core.py`、`catalog_ui/`、`catalog_ui_server.py`：catalog 原型 v0，含入口（偵查、點名）、封存、靜態檢查、分流、吸收、版本和還原。
   - **論文入口**：除了 repo，還收 arXiv 論文和本機 PDF。只會連 arXiv、只用 https、有大小上限。依版本和 sha256 封存。不會照抄論文文字。
   - **本機頁面改成消化道介面**：每樣食物停在它真正的位置，附卡點說明。提問會記到 `.oaw/catalog/questions.jsonl`；新增 `POST /api/question` 和 `catalog.py questions`。
   - `docs/SKILL_INTAKE.md`：正式流程，含 D21 精簡流程。
2. **論文 arXiv 2606.03979 原型**：`wiki_sync.py memory-check`，唯讀、離線，檢查 memory.md 引用的檔案路徑還在不在。
3. **D21 第一輪吸收 8 個 A 級單位**（全部是靜態證據；沒有實測增益，標「齊平，未宣稱改善」）

   | 單位 | 來源 | 內容 |
   |---|---|---|
   | OAW-01 | TokenEconomizer | `resolve_cli`：Windows npm shim 直接啟動，不經過 cmd.exe |
   | OAW-02（部分） | graphify | 引用路徑的精確大小寫解析；`lf_sha256` |
   | OAW-03 | claude-mem | A/B 判定：機制沒觸發就是 inconclusive |
   | OAW-04 | TokenEconomizer | A/B 額外開銷歸屬和用量覆蓋率 |
   | OAW-12 | claude-mem | evidence 寫入前擋下帶前綴的憑證 |
   | OAW-15 | claude-mem | `memory recall --index` |
   | OAW-21 | graphify | `lint` 檢查 `path::Symbol` 程式碼引用 |
   | OAW-22 | graphify | `wiki_sync.py cites` 反查引用 |
4. **工具**
   - `scripts/goldfish_review.py build|run|check`：零上下文金魚審查程式 diff。只走訂閱計費，碰到其他計費來源就停；結果寫出前先遮蔽。
   - `scripts/code_index.py find|callers|path|affected|stats`：標準函式庫的程式碼索引（D24：可重建、agent 不寫入、不強制查詢、有過期檢查）。
   - `evals/code-map/`：Stage 0-α 預先登記的評估。結果在 records，判定通過。
5. **Gate**：每個檢查的 subprocess 上限從 360 秒改成 900 秒（獨立一個 commit，附實測時間）。
6. **授權**：`THIRD_PARTY_NOTICES.md`、`LICENSES/Apache-2.0.txt`（D14 的路線：Apache-2.0 署名，附修改說明）。

## 行為改變（請特別看）
- **OAW-12**：`memory add`、`lesson`、`annotate` 遇到帶前綴的憑證（22 種）會拒絕寫入，結束碼 1，訊息不重複秘密。**沒有略過旗標**，要改用佔位字。
- **OAW-21**：引用的檔案或符號找不到時會警告；`lint --strict` 會因此失敗。
- **memory-check**：檔名大小寫要完全一致，Windows 和 macOS 也一樣。
- **消化系統**：新增對外連線（只連 arXiv）和一個新的本機 POST endpoint（同樣有 token、Host、origin 檢查，body 上限 8 KB）。
- **Gate**：上限改成 900 秒。

## 驗證
- **Gate**：`py -3 scripts/harness_check.py` 在 Windows 11、Python 3.13 上單獨跑，9/9 通過：448 個測試、0 skipped、6 分 14 秒（`51b00db`，`MINIMUM_TESTS = 426`，POSIX 計數）。
- **零上下文金魚審查**（訂閱、`apiKeySource: none`、claude-opus-5-5）：
  - 這輪 8 個單位的 diff：34 個發現，18 個修正、11 個記錄、5 個駁回。
  - memory-check 的 diff：13 個發現，10 個修正、3 個駁回。
  - Stage 0-α 題目：10 個發現，在看到結果之前全部處理。
  - 每個發現的處理和理由都在 records 的 `goldfish-diff/resolution*.json` 和 `codemap-stage0/`。
- **Stage 0-α**：程式碼索引在概念題的前 5 名命中率是 1.000，原生搜尋是 0.750；輸出少 32%。這是工具層指標，不是 agent benchmark。兩個偏差都照實記在 `RESULT.md`。

## 已知限制
- catalog 原型 v0 還沒照 D21 自動分級，第 8 站仍要 owner 勾選。B 級還沒有會跑模型的 A/B runner。
- Stage 1（實際 agent 的 tool call 次數，上限 10M）還沒跑。
- Codex 那一半（D8）沒有實測。
- 早期有 3 個 commit 的標題含 game 或 play（D19 之前寫的）。要改得 force-push，這裡先不改。

## 還原
每一組都是一個 merge commit，可以用 `git revert -m 1 <merge>` 單獨拿掉。第一輪的版本頁在 records 的 `RELEASE_v1.md`。

給審查者的指南：records 分支的 `records/pr-claude-oaw-2/REVIEW_GUIDE.md`。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
