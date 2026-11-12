# H1 事後稽核：D40 決定前查到的事

> 2026-11-12。做 D40 決定前，回頭讀 H1 正式作答的原始紀錄（兩格 O 組，24 筆），逐筆解析「實際執行的指令和結束碼」。
> 這是事後描述，不是登記過的檢定，**不改 `RESULT.md` 的判定**，也不能證明哪一項是唯一的原因。原始 transcript 留在本機，不上傳。

## 結論

H1 量到的 O 組，有四件事跟設計不一樣。前兩件是 Codex 上的產品缺陷，後兩件是規則寫法的問題。

| # | 查到什麼 | 影響 |
|---|---|---|
| 1 | Codex 預設沙盒把專案裡的 `.agents/` 設成唯讀，OAW 的筆記檔（`.agents/memory.md`）寫不進去 | `memory add` 在 Codex 的 `workspace-write` 沙盒裡一定失敗 |
| 2 | OAW 叫 Codex 跑的審查指令 `codex review --uncommitted`，在 Codex 的 session 裡跑不起來 | C 類 4 題全部失敗，agent 自己改開 subagent |
| 3 | 筆記幾乎沒被寫 | B 類 4 題，兩格都只有「明講要記」那一題去寫 |
| 4 | 最貴的是走 deep 的題（設計審查，加「審到沒有新發現、最多 3 輪」的 code review） | design 題整題比原生貴 3.3–8.7 倍；這 8 筆裡分數沒有跟著變好 |

## 1. Codex 沙盒寫不進 `.agents/`

- Codex CLI 0.167.2，`workspace-write`。它保護專案裡的 `.git`、`.agents`、`.codex`：這三個資料夾唯讀，其他地方可寫。
- 不花 token 的探針（`codex sandbox -c 'sandbox_mode="workspace-write"' -- <寫檔指令>`）：專案根目錄、`docs/`、`.oaw/` 可寫；`.agents/`、`.git/` 唯讀。
- H1 實際發生的：Codex 格 explicit-1-b1 第 1 個 session，`context_hub.py memory add` 回 `[Errno 30] Read-only file system`（鎖檔在 `.agents/` 底下）。agent 自己改寫到 `docs/decisions/`，後面的 session 找得到，所以這題 O 還是贏了。
- 擋下來的是 Codex 自己的規則，不是 H1 的 runner：runner 把工作資料夾掛成可讀寫。
- 互動模式下 Codex 可以請使用者批准「到沙盒外執行」，所以是每次都要多按一次；`codex exec` 或不詢問的設定下就是失敗。

## 2. Codex 的審查指令跑不起來

- `oaw_mode.py` 在 Codex 上印的步驟是 `codex review --uncommitted`。
- Codex 格 C 類 4 題的 O 都照做了，4 次都是 `failed to initialize in-process app-server client: Read-only file system`（巢狀的 Codex 要寫自己的家目錄，沙盒不准；沙盒裡也沒有網路）。
- 4 題的 agent 都改用 subagent 審查（1–3 個），所以審查有做，只是不是照 OAW 寫的方式。

## 3. 筆記幾乎沒被寫

逐筆看 B 類 O 組有沒有「執行成功的筆記寫入」：

| 題 | Claude 格 | Codex 格 |
|---|---|---|
| explicit-1-b1（明講要記） | 寫了（`.agents/memory.md`） | 想寫、被第 1 點擋下，改寫 `docs/decisions/` |
| passing-1-b1（順口一提） | 沒寫 | 沒寫 |
| superseded-2-b1（決定後來改了） | 沒寫 | 沒寫 |
| handoff-1-b1（交接到一半） | 沒寫 | 沒寫 |

- OAW 的 `AGENTS.md` 寫的是「被要求時、或決定日後難以重建時才存」。L 組的兩行規則沒有條件，Codex 格 4 題都寫、都記得。
- Claude 格 O 輸的兩題：OAW 的筆記是空的，agent 查完就停，沒有再去翻原生紀錄；原生 N 反而直接翻前面 session 的紀錄找到了（見 `RESULT.md`「差在哪」第 2 點）。

## 4. token 花在哪

C 類 O 組，`oaw_mode.py suggest` 印出的模式和實際開的審查者數：

| 格 | 題 | 模式（印出的輪數上限） | 審查者 | O 的 token | N 平均 | 倍數 |
|---|---|---|---|---|---|---|
| Claude | design-1-c1 | deep（3） | 3 | 1.44M | 0.39M | 3.7 |
| Claude | design-3-c1 | deep（3） | 4 | 6.28M | 0.72M | 8.7 |
| Claude | large-2-c1 | standard（1） | 1 | 1.43M | 0.80M | 1.8 |
| Claude | large-3-c2 | standard（1） | 1 | 1.78M | 1.25M | 1.4 |
| Codex | design-1-c1 | deep（3） | 2 | 0.92M | 0.28M | 3.3 |
| Codex | design-3-c1 | deep（3） | 3 | 1.90M | 0.43M | 4.4 |
| Codex | large-2-c1 | standard（1） | 1 | 1.47M | 0.54M | 2.7 |
| Codex | large-3-c2 | standard（1） | 1 | 1.22M | 0.60M | 2.0 |

- token 是 H1 的 logical 總量（含 cache read 和 subagent），只在 H1 這個 protocol 內可比。
- standard（一次審查）貴 1.4–2.7 倍；deep（設計審查加最多 3 輪 code review）貴 3.3–8.7 倍。這是整題的成本，沒有把「多出來的輪數」單獨拆開量。
- 分數：8 筆裡只有 Codex 格 design-1-c1 贏原生（10/10 對 9.5/10）。4 題裡 2 題是天花板補題（D42），本來就只看得出持平或變差。
- 「最多 3 輪」是 2.0.1 計畫的設計（`v2.0.1-execution.md` W1），沒有量測支持；有量測的是 X2：一次原生的全新 context 審查找到 47/48 個埋的缺陷。

## 怎麼查的

- Codex：讀每個 session 的事件紀錄裡 `command_execution` 的指令、結束碼、輸出，和 `file_change`。
- Claude：把主 session 的 `tool_use` 和對應的 `tool_result` 配對（subagent 的不算）。
- 一開始用關鍵字搜「memory add」會把 skill 自己的說明文字算進去，數字偏高；改成只算實際執行的指令。
