# PRE-02 零上下文金魚審查包（修訂 3）

這個分支只放審查包，不改任何 OAW 程式碼。用途：讓「完全沒有專案上下文」的金魚（D10、D15），盲審三樣食物（TokenEconomizer、claude-mem、graphify）的吸收提案與 backlog。

## 內容
- `packets/plan.md`：摘要、owner 決定表、backlog（Lens B：計畫與依賴）
- `packets/te.md`、`cm.md`、`gf.md`：各食物的提案與成分帳本（Lens A：主張與證據）
- 每份包都內嵌所有被引用的原始碼行，金魚不需要任何工具。外部 repo 的內容標成 untrusted DATA。
- `run_goldfish.py`：只用標準函式庫的執行器。

## 怎麼跑（任何已登入 Claude Code CLI 的電腦或雲端環境）
```
python3 review-kit/pre02/run_goldfish.py --dry-run   # 先看會跑什麼
python3 review-kit/pre02/run_goldfish.py             # 跑全部 4 份
```
- 每份包都在一個全新的空資料夾裡用 `claude -p` 執行，並關閉工具、MCP、slash commands 和 user/local 設定。
- 結果寫到 `results/<packet>.json`：啟動參數、CLI 版本、init event、零上下文檢查、canary 回答、審查意見、用量。
- `zero_context_verified` 只有在以下條件全部成立時才是 true：
  - init event 的 tools、MCP、slash commands、skills 全空；
  - plugins 只有 `@builtin`；
  - auto-memory 資料夾是空的；
  - canary 回答 "none"。

  內建 agent 類型一定會列在 init event 裡，但金魚沒有任何工具，所以叫不動它們。
- 2026-11-03 在 Windows 上用 CLI 2.1.309 測過：未登入時 init event 照樣先送出，上述檢查全部通過，接著在驗證登入那一步失敗，沒有呼叫模型。
- 預估用量：4 份合計約 0.5–1.5M logical tokens，在 D13 的開銷上限 10M 以內。

## 跑完之後
把 `results/` commit 並 push 回這個分支（`review/pre02-goldfish`）。之後由 Elephant 在本機處理意見，才交給 owner 逐批核准。
