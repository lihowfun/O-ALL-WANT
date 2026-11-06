# V8 補登記：凍結題目和組別（2026-11-07，任何作答之前）

- **repo**：`microsoft/vscode` @ `29ad5e7ec8d963aa67226f58a4472697b21d6f35`（shallow clone，20,942 個檔案）。每組各一份副本，放在本機 SSD。
- **題目**：`questions.json`，sha256 `eee033ec39e248520fea77ed776607c8d168cacfd8cb9ad2ddd993904d5fe6d6`。出處和取捨寫在 `DESIGN.md`，sha256 `f91094f5d55badc4e3539cd3b52f14bcdcc94778f25bfe320bfa3fe3893a215b`。
  - q1：一字不改照抄 codegraph README 的查詢。
  - q2、q3：題句照抄它三輪 benchmark 的追問，前面加前情說明。
  - q4：取自 codegraph 給 VS Code 的壓力測試查詢。
  - 出題者是零上下文的 subagent，沒有裝或跑 codegraph，也看不到任何作答。
  - 我另外機械核對過：每條事實的 `where` 檔案都存在，symbol 也都在檔案裡。
- **模型**：`claude-opus-4-8`，effort high。codegraph README 的 benchmark 用 Opus 4.8；README 沒寫 effort，它的腳本預設是 high。
- **組**：
  - N 原生：Read、Grep、Glob。
  - C codegraph 1.6.2：官方 project 安裝（`codegraph install --target=claude --location=local --yes`），事先用 `codegraph init --yes` 建好索引。工具多一個 Bash，只允許 `codegraph:*` 和 `mcp__codegraph__*`，和 2026-11-06 的 C 組相同。遙測關閉。
- **作答**：沿用 2026-11-06 code map 的 runner（`../../../digestion-2026-11-06/taste-codegraph/taste_run.py`），提示和作答上限相同。
  - 每組 4 題 × 3 次，組別順序每次輪替。
  - 單次上限 1,800 秒。
- **預算**：codegraph 這份食物剩 4,591,753，N 和 C 的作答都算。runner 的守門照舊。
- **評分**：code map 評分程式（Opus 5.5 high）和 Codex（`xgrade.py`），盲評，遮罩相同。
- **判定**：
  - 共用的四類規則（`../v1_resolution.py`）。
  - D29：品質要 Opus 和 Codex 兩位評分者一致才算方向；成本用 token 中位數比，和帳本相同。
  - 同時列出工具呼叫和秒數。codegraph 宣稱的是效率，所以這兩項也報。

## 開跑前的調整（同日，任何作答之前）
- **MCP 設定**：VS Code repo 自己就帶一個 `.mcp.json`（component-explorer），codegraph 的安裝是把 codegraph 加進這個檔。
  - C 組改用一份只含 codegraph 的 MCP 設定，從安裝後的檔案抽出來。
  - N 組照舊用 `--strict-mcp-config`、不給 `--mcp-config`，所以沒有任何 MCP server。
  - 這樣兩組只差 codegraph 本身。
- **codegraph 安裝結果**：寫了 `.claude/settings.json`（允許 `mcp__codegraph__*`，加一個 `UserPromptSubmit` hook 跑 `codegraph prompt-hook`）、`.claude/CLAUDE.md`，以及 `.mcp.json` 裡的 codegraph。
- **索引**：本機 SSD，8 分 54 秒，2.2 GB，峰值記憶體 12.7 GB。ERPNext 那次是 15 秒、189 MB。
