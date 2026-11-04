# graphify 試吃（agent 層）預先登記

依 D25、D26。寫在任何 agent 作答之前；題目檔 `questions.json` 的 sha256：`df4e53cc0921e5a4f4e8e3f32ab8bfd188a52529591f87d3e142b0d11e1bc3d7`（凍結於任何作答之前，之後不改）。出題本身用了約 3.5M token（含 cache），算在消化系統的開銷，不算 graphify 的 10M。

## 問題
agent 有了 graphify 的圖（照官方方式安裝），是不是更能理解 OAW 的程式之間怎麼串在一起？OAW 自己的 `code_index.py` 呢？

## 三組（同一個 commit 51b00db，各自一份副本，在 WSL）
- **N 原生**：Claude Code，只有 Read、Grep、Glob。
- **G graphify 0.9.101**：照它的建議設定（`.graphifyignore` 排除 `example/` 產生複本）建好程式碼圖；`graphify install --project --platform claude` 寫入的 skill、CLAUDE.md 規則和 PreToolUse hook 都在；工具是 Read、Grep、Glob，加上只能跑 `graphify` 的 Bash。沒有做 LLM 語意抽取（文件部分），只有程式碼 AST 圖。
- **S OAW**：`scripts/code_index.py`，CLAUDE.md 加一段和 graphify 同樣風格的使用規則；工具是 Read、Grep、Glob，加上只能跑 `python3 scripts/code_index.py` 的 Bash。

三組都是同一個 Claude Code（WSL、訂閱、apiKeySource 必須是 none）、同模型和使用者預設、同提示、沒有 MCP、沒有子 agent、不能改檔。

## 題目
6 題，由一個全新的 agent 在原生副本裡出題（只能讀檔），它只知道要考「理解程式之間的串聯」，不知道參賽的工具。2 題流程、2 題影響、2 題機制；每題 5–8 個可檢查的事實，標出必要事實。

## 評分
- 零上下文評分者（`claude -p`、沒有工具、空資料夾）逐題對照事實判定 present／absent／contradicted，並計算錯誤陳述。答案裡會洩漏組別的工具名稱先遮掉，評分順序打亂。
- 每組的指標：事實覆蓋率（平均）、必要事實全對的題數、錯誤陳述數；token 總量、tool call 次數、時間（每題中位數）。

## 判定規則（先寫死）
- **理解比較好**：某組平均事實覆蓋率比 N 高 0.10 以上，或必要事實全對的題數比 N 多 2 題以上。
- **一樣懂但比較省**：覆蓋率和 N 相差不到 0.05，而且每題 token 中位數不到 N 的 70%。
- 其他：沒有證明比原生好。
- **如果 S 贏 G**（OAW 贏了高星工具）：依 D26 先懷疑考法，換一個不是 OAW 的 repo 再跑一次，才下結論。

## 預算
graphify 這份食物的上限 10M token（D13，token 總量含 cache）。先每組每題跑 1 次（18 次）；預算夠才跑第 2 次。超過預算就停，照實記錄。
