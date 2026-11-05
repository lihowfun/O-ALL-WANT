# graphify 試吃（agent 層，ERPNext）預先登記

依 D25、D26。owner 2026-11-05 指示「直接跑 ERPNext」。寫在任何 agent 作答之前；題目檔 `questions.json` 的 sha256：`b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83`（凍結於作答之前，之後不改）。

## 問題
OAW 那次（`../agent/`）有天花板效應：原生 agent 不靠地圖就答對每一題的必要事實。這次換到 graphify 自己 benchmark 用的大型陌生 repo，問同一件事：照官方方式裝好 graphify 的 Claude Code agent，是不是比原生更懂程式之間怎麼串在一起，或一樣懂但比較省？

## 食物自己的主張（資料，取自它的 README 和 BENCHMARKS.md）
ERPNext cross-tool（n=6）：key-fact coverage 82.0%，grep/read 基準 70.8%，每題約 140K token。它的設定：固定 coding agent（Claude Opus 4.8），最多 14 回合，grep/read/list 加一個 graphify 工具，Kimi K2.6 評分。

## 語料
`frappe/erpnext` develop，commit `d9cb9169dcc144cba46f7ddfcf90b0ab7b1e6aa9`。5,952 個檔案，Python 約 54 萬行、JavaScript 約 9.5 萬行。repo 裡沒有 CLAUDE.md、AGENTS.md 或 `.claude/`。它依賴的 Frappe 框架不在副本裡。

## 兩組（同一個 commit，各自一份副本，Linux）
- **N 原生**：只有 Read、Grep、Glob。
- **G graphify 0.9.102**（試吃當天 PyPI 的最新版，獨立的 uv 環境，Python 3.12）：`graphify update .` 建程式碼圖（只用 AST、不用 LLM，和它 benchmark 的「建圖 0 LLM credits」一致）；38,492 個節點、101,378 條邊、2,787 個群組（群組命名要 LLM，沒有做）。它會讀 `.gitignore`，文件沒有針對 ERPNext 建議忽略規則，所以不另加 `.graphifyignore`。`graphify install --project --platform claude` 寫入的 CLAUDE.md 規則、`.claude/CLAUDE.md`、skill 和 PreToolUse hook（Bash／Grep、Read／Glob）都保留。工具是 Read、Grep、Glob，加上只能跑 `graphify` 的 Bash。

兩組相同的部分：Claude Code 2.1.287、`claude-opus-5-5`、`--effort high`、同一段提示（和 OAW 那次相同）、沒有 MCP、沒有子 agent、不能改檔、每次一個新的 session；計費來源必須是訂閱（`apiKeySource: none`，不是就停）；每次上限 1,200 秒。順序：每題先 N 後 G。

## 題目
4 題，由一個全新的 agent 在原生副本裡出題（只能讀檔，`design_prompt.txt`）。它只知道要考「理解程式之間的串聯」，不知道參賽的工具。題型：2 題影響（q1 `update_bin_qty`、q2 `get_valuation_rate`）、1 題流程（q3 遞延收入排程）、1 題機制（q4 cost center 怎麼選）。事實數 8／6／8／7，其中必要事實 7／5／6／6。出題用了 1,518,689 token（含 cache），算消化系統開銷。

大象審題（本 session，不花模型 token）：用 grep 和讀碼逐題核對。兩題影響題的呼叫點都完整，沒有遺漏，也沒有誤列（`ProductionPlan.update_bin_qty` 是另一個同名方法，不受影響，題目沒列它）；q3 的排程登記和分錄借貸方向、q4 的優先順序和跨公司檢查都和程式一致。題目沒有修改。這次沒有另跑零上下文金魚審題。

## 評分
和 OAW 那次相同：零上下文評分者（`claude -p`、沒有工具、空資料夾、`--setting-sources project`，模型和 effort 同上）逐題判定每個事實 present／absent／contradicted，並計算錯誤陳述。答案裡會洩漏組別的工具名稱先遮掉，評分順序打亂。

## 判定規則（先寫死，和 OAW 那次相同）
- **理解比較好**：G 的平均事實覆蓋率比 N 高 0.10 以上，或必要事實全對的題數比 N 多 2 題以上。
- **一樣懂但比較省**：覆蓋率相差不到 0.05，而且每題 token 中位數不到 N 的 70%。
- 其他：沒有證明比原生好。
- 另外照實列出（不影響判定）：每組在影響題上的錯誤陳述數。OAW 那次兩個地圖組的錯誤都集中在影響題。

## 預算（D13）
graphify 上限 10M；OAW 那次用了 3,790,470，剩 6,209,530。runner 上限 6,200,000，而且加了成對保護：開始一題之前，已用量加上「目前最大單次 × 2」必須不超過上限，否則停止。所以只會比完整的成對結果；判定只算跑完的題，題數不到 4 會寫明。出題和評分算消化開銷。

## 和 OAW 那次的差別（照實記錄）
1. Linux，不是 WSL；graphify 0.9.102，不是 0.9.101。
2. 這台機器的 user 層設定很多（全域 CLAUDE.md、plugins、hooks、skills），而長效 token 還沒建立，不能換獨立的設定資料夾。所以出題、作答、評分都加上 `--setting-sources project`：user 層的 CLAUDE.md、plugins、skills、設定不載入，各組自己的專案檔照常載入。探測確認 `claude_md` 為空，只剩內建 plugins，計費來源是訂閱。
3. 模型和 effort 明確固定（`--model claude-opus-5-5 --effort high`），每一列記下 init 回報的模型。OAW 那次用的是使用者預設。
4. 4 題，不是 6 題；只比 N 和 G。S（OAW `code_index.py`）不參加：這輪 owner 核准的是 N 對 G。
5. 不設回合上限，這是 Claude Code 平常的用法。graphify 自己的 benchmark 限 14 回合，所以這次的覆蓋率不能直接和它的 70.8%／82.0% 對比。
6. runner 和評分程式是 `../agent/` 的副本，差別寫在檔頭（固定模型和 effort、`--setting-sources`、關閉 stdin、不保存 session、成對預算保護）；彙總沿用 `../agent/taste_summary.py`。

## 執行
`T=<試吃資料夾> CLAUDE=<claude CLI> bash run.sh`（`arms.json` 由 `../../../handoff-2026-11-05/kit/setup_arms.sh` 產生：`SRC=<ERPNext 的本機淺 clone> COMMIT=d9cb916… ARMS="base N G" G_IGNORE=""`）。原始 stream-json 留在本機，不公開；`rows.jsonl`、`grades.jsonl`、`summary.json` 和結果頁會 commit 到這裡。
