# TokenEconomizer 試吃（agent 層，session 串流）預先登記

依 D25、D26、D28。寫在任何組別作答之前。題目檔 `tasks.json` 的 sha256：`0ecc8d51ba450cc6c622251739390b1985c7fac2b4de0b9fb8f09f588b4b37c6`（出題 agent 寫出的檔案原樣，14 題；驗證結果在 `verify.json`）（凍結於作答之前，之後不改）。

## 食物和它的主張
`microsoft/TokenEconomizer`（Apache-2.0，GitHub 約 4.8k 星），試吃時固定 `519c65fff990e14480accca8a7629b3befcb7630`（2026-11-04；靜態消化看的是 `d58755d849`）。

主張（資料，取自它的 README 和 `plugin/README.md`）：同一個 repo 反覆使用 coding agent 時，它從已結束的 session 學習，讓後面的 session 變便宜，而且不降品質。三個機制：
- **micro-skills**：從重複出現的失敗、以及每 *k*=3 個 session 一次的模型提案（fact proposer），學到 repo 事實；三個 session 確認後在 session 開頭注入。
- **tool pruning**：沒用到的工具，在 *p*=10 個 prompt（跨 *m*=2 個 session）或 *s*=5 個 session 後，寫進 `.claude/settings.local.json` 的 deny list，之後的 session 不載入。
- **loop guard**：*e*=5 個好結尾的 turn 之後啟動；turn 卡在重複失敗時，judge（*c*=0.7）決定是否送一次 redirect（*r*=1）。
- 它的論文數字：SWE-Bench 五種 agent–模型組合平均成本低 18.4–30.9%（Claude Code + Opus 4.8：低 30.9%、Pass@1 −1.0），單一 repo×組合 5–40%。成本用 cache 加權的 effective token，含它自己的模型呼叫。

## 語料和題目
- 語料：`pallets/flask`，commit `49943b5a94413a530761350f04e896f76e8d620e`（2026-10-30）。`src/flask` 約 9.6k 行，`tests/` 約 8k 行。每組副本有自己的 `.venv`（uv，Python 3.12.10，只裝 `tests` dependency group）；PATH 上沒有 pytest，agent 要自己找到 `.venv`。Flask 是 SWE-Bench 的 repo 之一，不是我們的。
- 題目：一個全新的 agent（Opus 5.5、effort high、只能讀檔和寫出結果，不能執行指令，`--setting-sources project`）在原生副本出題（`design_prompt.txt`）。它知道上面的主張，不知道 OAW。它寫了 14 題（小的 bug 修正、小功能或行為改變，分散在 `src/flask/` 不同模組），每題有給 agent 的提示、一個隱藏測試、一份參考改動。提示只說要什麼行為、為什麼，不說怎麼跑測試、改哪個檔。
- 驗證（0 token，`verify_tasks.py`）：隱藏測試在 base 要失敗，參考改動要能 `git apply`、套上後隱藏測試要通過、整個既有測試也要通過。不合格的題目直接丟掉，不修改。凍結的題組是出題順序中前 12 個合格的題目：14 題中 12 題合格（t06、t08 的參考改動 `git apply` 套不上，丟掉），剛好 12 題。串流順序：1 t01 `Config.copy()`、2 t02 `MethodView` 405、3 t03 `session.new`、4 t04 `flask routes` 篩選、5 t05 JSON 序列化 Enum、6 t07 `get_flashed_messages` 單一分類；7 t09 每個回應的 `max_cookie_size`、8 t10 `.j2` 類副檔名自動跳脫、9 t11 `copy_current_request_context` 要有 request、10 t12 shell context processor 回傳值檢查、11 t13 JSON tag 強制重新註冊的順序、12 t14 模板名稱排序。base 時既有測試 494 個全過；每題套上參考改動後既有測試全過。
- 出題用了 6,539,760（51 回合，其中 cache read 6,167,683；它不能執行指令，回報「只用讀碼核對」） token（含 cache），算消化系統開銷。

## 兩組（同一個 commit，各自一份長期副本，Linux）
- **N 原生**：Claude Code 本身。
- **T TokenEconomizer**：官方安裝、project scope：`claude plugin marketplace add --scope project <clone>`、`claude plugin install --scope project tokeneconomizer@tokeneconomizer`（寫進副本的 `.claude/settings.json`）；裝完照文件做一次 `toolprune refresh-catalog`（用文件說的終端機寫法 `te --host claude …`，不花模型 turn）。它的狀態放在試吃區（`TOKENECONOMIZER_HOME`），不是 `~/.tokeneconomizer`。
- **沒有 O 組**：OAW 從 TokenEconomizer 拿的兩個單位（OAW-01 `oaw_common.resolve_cli`、OAW-04 `improvement.py` 的 overhead 計帳）是量測和啟動工具，都不會作用在 agent 的 session 上，所以沒有「OAW 版的這個主張」可以跑。

和預設的差別（照實記錄，兩項都是文件列出的設定，用 `te config set` 設在這個 repo）：
1. `microskills=on`：預設關（因為 proposer 要花模型呼叫）。主張的第一個機制就是它，論文的 TokenEconomizer 組（`trimech`）也開著；不開就沒有在測主張。
2. `toolprune_quiet_minutes=0`：預設 60 分鐘。這個等待只是為了不讓「續接中的對話」丟掉 prompt cache；這裡每個 session 都是全新的 headless session、一個接一個，從不續接。不改的話，整段試吃中 deny list 永遠不會寫入。

其他設定全用預設（`toolprune=auto`、`loopguard=nudge`、*k*、*p*、*m*、*s*、*e*、*c*、*r*、*b* 都是預設值，`paid_model` 空白 → 它的模型呼叫用 haiku）。

兩組相同的部分：
- Claude Code **2.1.310**（它支援 2.1.300–2.1.310；這台機器的預設 CLI 是 2.1.287，不支援），裝在試吃區，關閉自動更新；`claude-opus-5-5`、`--effort high`；同一段提示（`taste_run.py` 的 `PROMPT`，題目文字放進去，結尾要求「改原始碼、用專案的測試驗證、不要 commit」）。
- Claude Code 預設的整組工具（tool pruning 才有東西可以剪）；`--permission-mode acceptEdits`、允許 Bash；沒有 MCP（`--strict-mcp-config`）；`--setting-sources project,local`：user 層的 CLAUDE.md、plugins、skills、設定都不載入，副本自己的 project 設定和 local 設定（它寫 deny list 的地方）照常載入。
- 每題一個新的 session、session 會保存（它從 Claude Code 自己的 session 紀錄學習）；上限 60 回合、1,500 秒。
- 每個 session 開始前，程式碼回到 base commit（`.venv`、`.claude/` 保留），所以每題在兩組都從同樣的程式碼開始；它學到的東西（狀態、deny list）照常累積。
- 順序：每題輪流先跑 N 或先跑 T（t1 N→T、t2 T→N…）。T 的 session 結束後，等它在背景啟動的 `fold`（把這個 session 學進去）結束，才跑下一個 session（用 /proc 找 PID，不比對指令列）。
- 計費來源必須是訂閱（init 的 `apiKeySource: none`，不是就停）；N 的 init 不能有它，T 的 init 一定要有它，不符就停、不記錄。
- PATH：一個 side-call shim 放在最前面（兩組都有，N 不會呼叫它）。它自己的模型呼叫（judge、redirect、fact proposer）會找 PATH 上的 `claude`；shim 照原樣轉給同一個 CLI，只補上和各組相同的 `--setting-sources project,local`（不讓 owner 的 user 層 plugins 和 hooks 跑進它的呼叫裡），並記下每次呼叫的 usage（不記內容）。

## 計分
- **成本**：每個 session 的 effective token，用它自己的權重（input 1、cache read 0.10、cache write 1.25、output 5），加總 session 結果裡 `modelUsage` 的所有模型；T 再加上它自己的模型呼叫（shim 的紀錄，和它自己的 ledger 對照）。另外照實列出原始 token（D13 計帳用）和 CLI 回報的美元成本。
- **品質**（機械判定，不需要盲評）：session 結束後，`tests/` 回到 base（agent 自己改的測試不算），寫入該題的隱藏測試，用副本的 `.venv` 跑整個測試。一題算「對」＝隱藏測試通過，而且既有測試沒有新的失敗。判定程式看不到組別。
- 前段＝第 1–6 題，後段＝第 7–12 題。它三個機制按預設門檻，最早在第 6 個 session 左右開始作用，所以主張要看後段。

## 判定規則（先寫死）
令 R＝後段 T 的 effective token 總和 ÷ 後段 N 的總和（只算兩組都跑完的題）；Q_T、Q_N＝全部完成的題中各組答對的題數。
1. **有效性**：後段完成的成對題目少於 3 題 → 不下判定（no-verdict，串流太短），寫明需要多少預算。
2. **機制沒有觸發**：後段 T 的 session 完全沒有它的動作（沒有注入事實、沒有 deny list 生效、loop guard 沒有出手；依它自己的狀態檔和 session 開頭訊息判斷）→ not-shown-better（vacuous：機制沒有觸發），不判 decline。
3. **品質下降** → decline：Q_T ≤ Q_N − 2。
4. **接上（plug in）**：Q_T ≥ Q_N − 1，R ≤ 0.85（後段至少省 15%），而且後段成對的題目中 T 比 N 省的題數至少三分之二。
5. **吸收（absorb）而不是接上**：符合第 4 條，而且後段只有一個機制有動作、那個機制不需要它的付費模型呼叫（例如 tool pruning，或只靠重複失敗的事實）。這時用標準函式庫重寫那一個機制就能拿到整個節省，而且不花模型 token。否則照 D26 預設接上。
6. **成本變高** → decline：R ≥ 1.15。
7. 其他：not-shown-better（沒有證明比原生好）。

另外照實列出（不影響判定）：前段的比值、每題的比值、它自己模型呼叫佔的比例、每個 session 它做了什麼（注入幾條事實、剪掉哪些工具、judge 呼叫幾次）、測試跑了幾次、回合數。

## 預算（D13）
TokenEconomizer 上限 10M，之前沒有用過。N 組只給這份食物用，所以全部算這份食物；T 組和它自己的模型呼叫也算。runner 上限 10,000,000，加成對保護：開始一題之前，已用量加上「目前最大的一對」必須不超過上限，否則停止。所以只會比完整的成對結果。出題和驗證算消化開銷。

## 已知限制（照實記錄）
1. 每組只有一條 12 題的串流，沒有重複；每題的成本本來就會有起伏。論文每個 repo 約 46 題、3 個 seed。
2. 同一個 repo 只有 12 個 session，比它機制的門檻（5 個 session 之後才開始）長不了多少；它的價值如果要更長的串流才看得到，這次會低估。
3. 這台機器另有其他 session 共用同一個訂閱；如果因速率限制失敗，之後續跑，不把失敗的 session 當結果。
4. 安裝是 project scope：user 層的 `~/.claude/settings.json` 和 user 啟用清單不變（安裝前後的 sha256 記在 `proof.json`）；Claude Code 仍會在它 user 層的 plugin 登錄檔（`installed_plugins.json`、`known_marketplaces.json`、plugin cache）記一筆 project scope 的紀錄，試吃結束解除安裝後再比對一次。

5. project scope 安裝會在 T 副本留下 `.claude/settings.json`，`git status` 看得到（N 沒有）；這是官方安裝的一部分，照留。
6. `refresh-catalog` 記下 2.1.310 一個新 session 載入的 26 個工具（用同一個 shim 跑，沒有模型呼叫）。
7. 隱藏測試只在 records 和評分時出現，從不放進作答中的副本。

## 執行
`T=<試吃資料夾> RECORDS=<這個資料夾> bash setup.sh`，驗證題目（`verify_tasks.py`），然後 `T=<試吃資料夾> bash run.sh`。原始 stream-json 和 diff 留在本機，不公開；`rows.jsonl`、`grades.jsonl`、`summary.json`、`tasting.json` 和 `RESULT.md` 會 commit 到這裡。
