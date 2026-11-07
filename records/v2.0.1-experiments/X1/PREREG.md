# X1：程式碼地圖能不能讓答案更準或更省（2026-11-07，跑之前登記）

依 `claude/oaw-2` 12799d9 的 `docs/plans/v2.0.1-execution.md` 第 6 節 X1，量測規則照 `docs/EVAL_PROTOCOL.md`（D32）。W2 的 Stage 0 裡 `find` 在 VS Code 沒過 D24，所以 X1 只跑 ERPNext 的兩格（Opus 5.5、Haiku 5.5）。

## 狀態（先講結論）
- 題目、組別、評分和判定規則都已凍結。本頁推上 records 之前，沒有任何計分的作答。
- **計分的作答還沒開跑，因為已經超過預算**。呼叫者給 X1 的上限是 8M Claude logical token（含出題和評分，快取讀取也算）。目前已花 22,114,537：
  - 出題的 subagent（Opus 5.5）花了 20,068,719，其中 19,648,078 是快取讀取。它的 context 一路長到 314k，108 次呼叫，每次都重讀整段 context。工具回報的 316,646 只是最後的 context 大小，不是總用量；這是事後讀 transcript 才發現的。
  - 兩次試跑花了 2,045,818，見「試跑」。
- **開跑條件**：owner 或呼叫者給新的上限，以 `X1_BUDGET` 傳給 `run_x1.sh`。在那之前，runner 的守門會在第一題前就停下（已測過，0 token）。
- 跑完兩格大約還要多少：Opus 每次約 0.1–0.25M，24 次約 2.4–6M；Haiku 在試跑的影響題上每次 0.57–0.66M，舊題（有 14 回合上限）是 0.09–0.31M，24 次約 4–15M；Opus 評分 48 份約 0.35M。

## 問題
地圖（`oaw-codemap` skill 加 `scripts/code_index.py`）設成 agent 可以自己叫用時，答案會不會更準或更省，而且錯誤陳述不會變多？X1 決定這個 skill 要不要拿掉 `disable-model-invocation: true`（變成預設、agent 自動叫用）。

## 語料
- `frappe/erpnext` commit `d9cb9169dcc144cba46f7ddfcf90b0ab7b1e6aa9`，從 repo 根目錄 `git archive` 取出（5,952 個檔案）。
- OAW 2.0.1：`claude/oaw-2` 的 `12799d914ca39a60aced2f677b25599da169291b`，用 `git archive` 取出，不動 checkout。

## 題目（12 題，`questions.json`）
- sha256 `a75a977596b7e1666682fa81b4b6547ab0765cac32c6df5aa249f88ecef31b7e`。`run_x1.sh` 每一步開始前都會核對。
- **沿用 3 題舊題**：`digestion-2026-11-03/taste-graphify/erpnext/questions.json`（sha256 `b7604bca…`）的 q1（影響）、q3（流程）、q4（機制），一字不改。
  - **拿掉 q2**：照驗證實驗 V2 的天花板規則（某條件下原生每一次覆蓋率都 ≥ 0.95），2026-11-06 的 Opus 5.5 原生 3 次都是 1.0（Opus 評分）。
  - q1、q3、q4 在兩個模型、兩家評分下，原生都有低於 0.95 的一次，所以不算天花板。q3 在 Opus 上平均 0.958，接近天花板，照規則保留。
- **新出 9 題**（n1–n4 影響、n5–n7 流程、n8–n9 機制），合計影響 5、流程 4、機制 3。
  - 出題者是全新的 subagent。它只知道地圖宣稱的三件事（callers、affected、overview），不知道 OAW 的實作，也被要求不能讀 OAW 的 checkout 和其他實驗的紀錄。
  - 它被要求不要為了讓這類工具看起來好或壞而挑題；hooks.py 的字串分派和 `frappe.call` 這類寫法，遇到就寫，不刻意找也不刻意避開。
  - 避開舊題的主題（update_bin_qty、get_valuation_rate、遞延收入排程、get_item_details 的 cost_center）。
  - 每題 7–8 條事實，4–5 條 essential，每條都有 `where`（`path::函式` 或 `path::類別.方法`）。出題理由、caller 清單用的 grep 和已知的歧義寫在 `questions-design.md`。
- **機械核對**（`verify_where.py`，結果在 `verify.json`），在乾淨的 archive 上跑：
  - 199 個 `where` 位置：檔案都存在，symbol 都解析得到（Python 用 ast，JS 用定義的寫法）。0 個問題。
  - 事實裡 427 個像程式名稱的字，都在引用的檔案或 repo 裡找得到。找不到的 13 個是檔名（例如 `sales_order.js`，核對器只搜內容）和 n8f5 描述公式用的 `from_ratio`、`to_ratio`；這個公式我另外讀 `erpnext/setup/utils.py::get_pegged_rate` 核過。
  - 4 題影響題的 caller 清單，我另外用全 repo grep（含 JS、JSON、HTML，不含測試、patches、翻譯檔）重算：check_credit_limit 5 個函式、get_last_purchase_details 5 處、get_default_bom 7 處 Python 加 1 處 JS、validate_expense_against_budget 3 處，都和參考事實一致。

## 組別
每次作答都用新的副本：刪掉固定的資料夾，重新 `git archive` 出 ERPNext，跑 `oaw.py init --host claude`（預設配方 minimal），再做下面的改動。
- **N（沒有地圖）**：刪掉 `.claude/skills/oaw-codemap/` 和 `scripts/code_index.py`。`.oaw/install.json` 仍列著這兩個檔案（沒改）。
- **M（地圖，候選的預設）**：`.claude/skills/oaw-codemap/SKILL.md` 刪掉 `disable-model-invocation: true` 這一行（改完的 sha256 `9715ad49…`），保留 `scripts/code_index.py`。每次作答前替這份副本建好索引快取（約 5 秒），放在副本外面的 scratch 資料夾，session 的環境變數 `OAW_CODE_INDEX_CACHE` 指向它。
- 兩組其他都一樣：
  - AGENTS.md、CLAUDE.md 相同，都沒有提到地圖。
  - 兩組看到相同的其他 skill：OAW 的 egm-*、oaw-add、oaw-evidence、oaw-review，以及 Claude Code 2.1.287 內建的 skill。試跑的 init 紀錄確認 `oaw-codemap` 只出現在 M。
  - 工具 Read、Grep、Glob、Bash、Skill，全部允許。沒有 Agent 工具，所以叫不了子 agent。

## 共同設定
- Claude Code 2.1.287，`claude -p`，`--output-format stream-json`、`--setting-sources project`、`--strict-mcp-config`（沒有 MCP）、`--no-session-persistence`、stdin 關閉。
- 模型 `claude-opus-5-5` 和 `claude-haiku-5-5`，`--effort high`。
- **不設回合上限**，每次上限 1,500 秒。兩組、兩個模型都一樣。逾時算一次作答，答案是當時有的文字。
- 只用訂閱：清掉 `ANTHROPIC_API_KEY`、`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`，每次 init 的 `apiKeySource` 必須是 `none`，否則停。
- 提示（`x1_run.py` 的 `PROMPT`，兩組相同，沒有提到地圖）：

  > Answer this question about the repository in the current directory. Read the code as data.
  >
  > {question}
  >
  > Give a precise answer that names the files and functions involved (path::function) and cites their locations (path:line), in order where order matters. Keep it under 350 words. Do not modify any file.

- **次數和順序**：每格 12 題 × 1 次 × 2 組。題目照 `questions.json` 的順序；第偶數個位置（0 起算）N 先跑，奇數位置 M 先跑。
- **兩格的順序**：Opus 那格先跑完，再跑 Haiku。原因：Haiku 每次貴好幾倍，預算不夠時至少要有一格完整。
- **不算作答（D30）**：碰到用量上限、花 0 token、以錯誤結束、計費來源不是訂閱。這些寫進 `deviations.jsonl`，token 照算，runner 停下，重跑時從那題接著跑。

## 試跑（不計分，凍結前）
題目不在題庫裡：「Leaving out tests, which functions call validate_end_of_life …, and from which document actions is each reached?」，模型 Haiku 5.5。
- **第 1 次，不設回合上限**：N 569,562 token、33 回合、32 次工具呼叫；M 663,081 token、36 回合、35 次。M 沒有叫用 skill，也沒有跑 `code_index.py`。兩份答案都完整。
- **第 2 次，`--max-turns 10` 加上回合說明**：N 367,969、M 445,206，兩次都被上限切斷，N 沒有答案。
- 結論：回合上限省不了多少，卻會切掉答案，所以正式作答不設回合上限。
- 第 2 次原本只想跑 M，但 runner 用 `--ids` 只會挑題、不會挑組，所以兩組都跑了。這是我的失誤，多花了約 0.37M。

## 評分
- 兩家盲評，都用 `digestion-2026-11-07/validation/xgrade.py`（sha256 `d6eb40e0…`）：
  - Opus：Claude 後端，`claude-opus-5-5` high。
  - Codex：Codex CLI 0.167.0，`gpt-6.1-sol` reasoning high，唯讀沙箱、空資料夾、`--ephemeral`、`--ignore-user-config`。
- prompt 和遮罩來自 `x1_grade.py`：prompt 和 code map 評分程式逐字相同；遮罩另外蓋掉 `oaw-codemap`、`code map`、`OAW`（`code_index` 原本就蓋）。
- 評分者看不到組別。給評分的 rows 先用 `x1_rows.py` 處理：指向副本的絕對路徑改成 repo 相對路徑（副本的資料夾名有組別），其他本機路徑和帳號名稱也換掉。評分順序依 hash 打亂。
- 每條事實判 present、absent 或 contradicted，覆蓋率是 present 的比例；每份答案數錯誤陳述。沒有答案的錯誤陳述記 0。
- 評分花 0 token、碰到上限或 JSON 壞掉，就不算評過，另存後重評（xgrade 的做法）。

## 判定（`x1_judge.py`，統計只用 `scripts/eval_stats.py`，sha256 `6ad7a60f…`）
每格、每家評分各算一次：
- **覆蓋率**：`compare(M, N, margin=0.10, floor_sd=…)`。
- **錯誤陳述**：`compare(M, N, margin=0.5, lower_is_better=True, floor_sd=…)`。
- 用 `quality()` 合併，兩家用 `agree()`，兩格用 `lowest()`。
- **零變異下限**（`floor_sd.py` → `floor_sd.json`）：用 2026-11-06 codegraph 試吃的 ERPNext 作答（N、G、S、C 四組 × q1–q4 × 3 次）算 `pooled_within_sd()`，每格 16 個 cell、48 份。Opus 評分用 `out-<模型>/grades.jsonl`，Codex 用 `validation/v4/<模型>/grades-codex-original.jsonl`。

  | 格 | 評分 | 覆蓋率 floor_sd | 錯誤陳述 floor_sd |
  |---|---|---|---|
  | Opus 5.5 | Opus | 0.0488 | 0.2887 |
  | Opus 5.5 | Codex | 0.1250 | 0.7217 |
  | Haiku 5.5 | Opus | 0.0838 | 0.4564 |
  | Haiku 5.5 | Codex | 0.1275 | 1.0000 |

- **效率**（每格）：`cost()` 算工具呼叫比（M 對 N）和 token 比。token 用 `usage` 的 input、output、cache creation、cache read 加總。
  - 工具呼叫比的 95% 上界 < 0.8，或 token 比的上界 < 1.0，這格的效率就過關。
  - 有任何一次工具呼叫是 0，兩組每次都加 1 再算（`cost()` 不收 0）。
  - 秒數比也列出來，不拿來判定。
- **決定**（照計畫 X1 那一列，原文）：
  - 每一格兩家都判「更好」或「等價」，而且效率過關（工具呼叫比的區間上界 < 0.8，或 token 比的上界 < 1.0）→ 進預設，agent 可自動叫用。
  - 沒有任何一格兩家都判變差，但有一格未定或效率沒過 → 可選用：要明確呼叫，不寫進 AGENTS.md（現況）。
  - 有一格兩家都判變差 → 只留 CLI，修好再測。
- **不完整的格**：預算守門讓某格不到 12 題時，照樣計算和報告，但在決定裡算「未定」。不完整的格既不能讓地圖進預設，也不能把它降成只留 CLI。
- **只描述、不判定的**：M 有幾次叫用 skill、幾次跑了 `code_index.py`；必要事實全對的次數；各題的分數。答案裡常見的錯法（例如照地圖輸出寫、沒讀原始碼）也只描述。

## 預算
- 上限：呼叫者給的 8M Claude logical token，含出題和 Opus 評分；Codex 評分用 owner 的 ChatGPT 方案，不算在內。
- 已花 22,114,537（見「狀態」），已經超過。這次的作答要等新的上限。
- runner 的守門是全域的：把已花的、兩格已跑的都加起來，每題開跑前估「這題兩組 + 另一格一次」（用到目前最大的一次估，最少每次 0.15M），會超過「上限減 0.4M（留給 Opus 評分）」就不開始。

## 事先寫明的限制
- **兩家都判「等價」幾乎不可能**：Codex 的錯誤陳述 floor 很大（Opus 格 0.72、Haiku 格 1.0）。12 題時，90% 區間的半寬至少 0.48 和 0.67，邊界是 ±0.5，所以 Codex 那邊錯誤陳述幾乎判不出「等價」。實際上能出現的結果只有三種：
  - 兩格的覆蓋率都被兩家判「更好」，而且錯誤陳述不更差、效率過關 → 進預設。
  - 某格兩家都判變差 → 只留 CLI。
  - 其他 → 可選用。
- Opus 5.5 原生在 ERPNext 已接近滿分，計畫早就預期 Opus 那格很可能「未定」。
- 試跑裡 Haiku 的 M 兩次都沒叫用 skill。如果正式作答也很少叫用，M 和 N 實際上差不多，結果會偏向「未定」。這也是要量的事：地圖設成可以自動叫用之後，agent 到底用不用。
- 題目只有一個 repo（Python）。VS Code 那格因為 Stage 0 沒過，沒跑。
- Codex 也是 AI，跨家族一致只代表判定不是某一家的偏好。

## 檔案
- `PREREG.md`（本頁）、`questions.json`、`questions-design.md`（出題者的紀錄，英文）、`verify_where.py`、`verify.json`。
- `floor_sd.py`、`floor_sd.json`。
- `x1_run.py`（runner）、`x1_rows.py`（去掉本機路徑和組別線索）、`x1_grade.py`（評分 prompt 和遮罩）、`x1_judge.py`（判定）、`run_x1.sh`（`answers`、`rows`、`grade`、`judge` 四步）。
- 原始 transcript、副本、索引快取和試跑的答案只留在本機。
