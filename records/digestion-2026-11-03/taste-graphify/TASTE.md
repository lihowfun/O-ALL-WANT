# graphify 試吃（D25，2026-11-04）

第一次真的執行 graphify。這是證據，不是指令。

## 怎麼吃的
- PyPI `graphifyy==0.9.101`（兩個 y），裝在 WSL 的獨立 conda 環境（Python 3.12），連依賴共 34 個套件。
- 在 OAW 2 的本機 detached worktree（`claude/oaw-2` 51b00db，沒有建分支、沒有推上 GitHub）執行 `graphify update .`：只做程式碼 AST 抽取，不用 LLM。環境變數清空，沒有 API key，HOME 指向一個臨時資料夾。
- 沒有跑它的安裝程式，所以沒有寫 hook、沒有改 CLAUDE.md 或 AGENTS.md。它只寫了 `graphify-out/`；HOME 和 repo 其他檔案都沒有被動到。
- 結果：5,165 個節點、9,602 條邊。群組數兩次跑出來不一樣（417 和 422）。時間：WSL 磁碟 4.6 秒，OneDrive 路徑 54 秒。

## 兩張圖比較（同一個 commit、同 64 個 Python 檔）
- 檔案之間的連線：兩邊都有 55 條，只有 OAW `code_index.py` 有 17 條，只有 graphify 有 7 條。
- graphify 漏掉的都是真的依賴，例如 `scripts/context_hub.py → scripts/oaw_common.py`（6 個 import、27 次呼叫）；看起來是多行的 `from oaw_common import (...)` 沒有被解析，根本原因未確認。
- graphify 多出的 7 條全是 INFERRED，兩端之間沒有 import，是靠名稱推測的錯誤連線。
- graphify 多看到文件（956 個節點）、註解和 docstring（433 個）、JavaScript 和群組；雜訊是 `example/` 產生複本（1,322 個節點，26%）、`vendor/` 352 個、標準函式庫模組也變成節點。
- 它建議的消歧義寫法 `path::symbol` 重試後仍然有歧義，要用完整的 node id。

## 同一套 39 題（Stage 0-α 凍結的題目、語料 6481437 和評分程式，三組在 WSL 重跑）
| 題型 | R 前 5 | S 前 5 | G 前 5 | R 輸出 | S 輸出 | G 輸出 |
|---|---|---|---|---|---|---|
| a 概念 → 定義（12） | 0.750 | **1.000** | 0.667 | 15,298 | 10,451 | 81,505 |
| b 誰呼叫（9） | 1.000 | 1.000 | 1.000 | 4,940 | 5,888 | 3,971 |
| c 改動影響（13） | 0.846 | **0.923** | 0.615 | 15,903 | 10,256 | 87,108 |
| d 模組路徑（5） | **1.000** | 0.000 | 0.000 | 1,489 | 429 | 994 |

- R、S 的數字和 Windows 上的 run2 完全一樣。
- b 類找全的程度（R@10）：R 1.000、S 0.907、G 0.463。
- d 類：S 和 G 都有格式問題，依規則算 0。直接讀答案，S 5/5、G 3/5（G 的 `path` 只印檔名、不印路徑）。
- G 對 R 的閘門：FAIL（沒有任何一類過關）。
- 偏差：`g_arm.py` 是看過 R、S 結果之後才寫的，沒有預先登記；評分程式也照此記錄（`results.json` 的 deviations）。

## 判定
graphify 的程式碼地圖：**不吸收原版，也不當外掛**。在這個 repo 上它找檔案沒有比原生搜尋準，輸出卻多 5 倍以上，還漏掉一半的呼叫者；OAW 的 `code_index.py` 在同一套題目上較好。沒有測的：文件、註解、多語言、LLM 語意抽取、MCP、hook。依 D25，graphify 不進付費的 Stage 1；Stage 1 只比原生和 OAW 版。

檔案：`g_arm.py`（G 的轉接程式）、`results.json`、`results.md`（本機路徑已換成 `{repo}` 和 `~`）。
