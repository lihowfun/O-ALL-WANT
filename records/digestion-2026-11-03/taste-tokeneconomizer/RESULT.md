# TokenEconomizer 試吃結果（agent 層，session 串流，Flask）

**結論：沒證明比原生好（not-shown-better），不收。** 食物有實際安裝並跑完（D28）。兩組 T 都有 12 個評過分的 session，品質和原生一樣（每組 12/12 全對）。依預先登記的規則：
- 第 1 輪 T（`microskills=on`）判 decline：後段成本是原生的 1.25 倍，主要花在它自己的 fact proposer。
- 追加組 T2（`microskills=envfacts`，不呼叫模型）後段省 2.3%，沒達到接上的門檻（省 15%），判 not-shown-better。
- 依追加組預先寫好的總結論規則，採較好的一輪：**not-shown-better**。

規則和設定見 `PREREG.md`、`followup-envfacts/PREREG.md`，兩份都在任何 session 之前 commit（`3c4c32e`、`6d10b05`）。

## 跑了什麼
- 食物：`microsoft/TokenEconomizer` @ `519c65fff990e14480accca8a7629b3befcb7630`，官方安裝、project scope，用 `refresh-catalog`（記下 26 個工具）。它的模型呼叫用 Haiku 5.5（`claude-haiku-5-5`），走同一個訂閱。
- 語料：`pallets/flask` @ `49943b5a`；12 題（`tasks.json`，sha256 `0ecc8d51…`），由一個不知道 OAW 的新 agent 出題，驗證時 0 token（`verify.json`，14 題丟 2 題）。
- 三條串流，每條 12 個 session，同一個 CLI（Claude Code 2.1.310）、`claude-opus-5-5`、effort high、同一段提示、預設工具、`--setting-sources project,local`，每題前程式碼回到 base：
  - **N 原生**、**T（`microskills=on`、`toolprune_quiet_minutes=0`）**：N 和 T 交錯跑，每題輪流先後。
  - **T2（`microskills=envfacts`、`toolprune_quiet_minutes=0`，狀態放本機磁碟）**：單獨跑，跟同一批 N 比。
- 36 個 session 全部成功：計費來源都是訂閱（`apiKeySource: none`），init 的 plugin 清單都對（N 沒有它，T、T2 都有），沒有碰到回合上限或逾時。
- 品質用機械方式評分，評分時看不到組別：每題結束後 `tests/` 回到 base，放入隱藏測試，跑整個 suite（約 495 個測試）。36 個 session 全部通過，既有測試沒有新的失敗。

## 成本（effective token，它自己的權重：input 1、cache read 0.10、cache write 1.25、output 5；T 含它自己的模型呼叫）

| | 前段（1–6） | 後段（7–12） | 後段比值 R | 後段比較省的對數 | 後段不含它的呼叫 |
|---|---|---|---|---|---|
| N | 346.2K | 300.8K | — | — | — |
| T（on） | 406.3K（1.17） | 376.8K | **1.25** | 2/6 | 312.9K（1.04） |
| T2（envfacts） | 389.8K（1.13） | 293.9K | **0.98** | 4/6 | 同左（它沒有呼叫模型） |

每一題（括號是它自己模型呼叫的部分）：

| # | 題 | N | T（on） | T/N | T2（envfacts） | T2/N | T 生效的機制 | T2 生效的機制 |
|---|---|---|---|---|---|---|---|---|
| 1 | t01 | 48.0K | 55.5K | 1.16 | 47.4K | 0.99 | — | — |
| 2 | t02 | 53.6K | 101.9K（22.2K） | 1.90 | 68.2K | 1.27 | — | — |
| 3 | t03 | 75.2K | 69.5K | 0.92 | 87.7K | 1.17 | — | — |
| 4 | t04 | 57.9K | 66.1K | 1.14 | 77.0K | 1.33 | — | — |
| 5 | t05 | 61.0K | 69.8K（31.5K） | 1.14 | 65.4K | 1.07 | 事實 | — |
| 6 | t07 | 50.5K | 43.3K | 0.86 | 44.0K | 0.87 | 事實 | 事實、11 個工具 |
| 7 | t09 | 54.0K | 73.7K | 1.36 | 71.6K | 1.33 | 事實 | 事實、11 個工具 |
| 8 | t10 | 49.6K | 98.7K（36.4K） | 1.99 | 52.5K | 1.06 | 事實、11 個工具 | 事實、11 個工具 |
| 9 | t11 | 38.7K | 28.2K | 0.73 | 26.9K | 0.70 | 事實、11 個工具 | 事實、11 個工具 |
| 10 | t12 | 62.9K | 44.1K | 0.70 | 58.4K | 0.93 | 事實、11 個工具 | 事實、11 個工具 |
| 11 | t13 | 52.9K | 71.9K（27.5K） | 1.36 | 47.0K | 0.89 | 事實、11 個工具 | 事實、11 個工具 |
| 12 | t14 | 42.9K | 60.3K | 1.41 | 37.4K | 0.87 | 事實、11 個工具 | 事實、11 個工具 |

原始 token（D13 計帳）：N 2,700,325；T 2,629,145（含它的 4 次模型呼叫 53,678）；T2 2,708,350。

## 它的機制實際做了什麼
- **micro-skills**：兩組都學到同一條事實並在 session 開頭注入（T 從第 5 個 session 起，T2 從第 6 個起）：「`python -m pytest` 在這裡找不到，要用 `.venv/bin/python -m pytest`」。這條來自不花 token 的 envfacts 層。T 的付費 proposer 跑了 4 次（Haiku，共 117.7K effective token，佔 T 成本 15%），提出 9 條候選事實，其中 4 條在最後 3 個 session（第 10–12 題）變成 active 並注入（每次連同 envfacts 那條共 4–5 條、約 700–800 字元）。這 3 題 T 含它的呼叫共 176.3K，N 是 158.6K，所以提出的事實沒有讓這幾題變便宜。proposer 的成本是 T 判 decline 的主因。
- **tool pruning**：5 個 session 後，它把 26 個工具中 15 個沒用過的（Cron、worktree、通知、Workflow 等）寫進 deny list，之後的 session 只載入 11 個，每回合讀的 prompt 變小。第 11–13 題 cache read 比 N 少 33–54%（t14 則沒有少，T2 的 t14 少 26%）。但工具一變，下一個 session 要重寫 prompt cache（T 的 t10 cache write 21K，平常約 11K），所以前一兩個 session 反而比較貴，之後才開始省。
- **loop guard**：三條串流都沒有出手、也沒有呼叫 judge。12 題都是小改動，最長 20 回合，沒有卡在失敗迴圈；它的門檻是 20 個工具呼叫以上，而且要先累積 5 個好結尾的 turn。
- 機制都生效後（第 9–12 題），T2 每題都比 N 省，合計少 13.9%（169.8K 對 197.2K）；T 不含它的呼叫少 10.3%，含了反而多 3.7%。方向對它有利，但這段只有 4 題、只有一條串流，前段 T2 也比 N 貴 13%（那時機制還沒作用，代表兩組本來就有起伏）。所以不能把它當成證明。

## 和預先登記不同的地方（照實記錄）
1. **NFS 時鐘偏差**（第 1 輪）：試吃區在 NFS 上，NFS 伺服器時鐘比本機快約 28 分鐘。它用「現在 − 檔案 mtime」判斷 repo 是否閒置，算出來是負的，所以 `toolprune_quiet_minutes=0` 失效，deny list 在第 5 個 session 後一直停在 pending。我發現時第 7 題的 T session 已經開始，於是用文件列出的 `te toolprune apply` 寫入，從第 8 題起生效；之後開了一個 watcher 做同樣處理，但沒有再觸發。所以第 1 輪 T 的工具剪裁晚了兩個 session（照設計應從第 6 題開始）。T2 把狀態放在本機磁碟，照設計從第 6 題生效，沒有人工處理。不管有沒有這個延遲，第 1 輪的判定都不會變：不含它的呼叫，後段比值也有 1.04。
2. **追加組 T2** 是第 1 輪結果出來後才加的，但在 T2 任何 session 之前先登記並 commit 了（`followup-envfacts/PREREG.md`）。T2 和 N 不是交錯跑，時間不同。
3. 第 1 輪 `rows.jsonl` 裡 T 的 ledger `untool_applied` 是 fold 當下的清單；計算「工具剪裁有沒有生效」用的是該 session init 實際載入的工具數。
4. **更正**：`followup-envfacts/PREREG.md` 的動機段寫「proposer 提出的事實在 12 個 session 內一條都沒變成 active」，這是錯的。我當時只看到第 6 個 session 為止的狀態；實際上第 10–12 題有 4 條變成 active 並注入（見上面「它的機制實際做了什麼」）。那份登記已凍結，不改；它的判定規則和 T2 的設定不受影響。T2 改用 envfacts 的理由仍然成立：proposer 的成本是第 1 輪多出來的主要部分。

## 限制
- 每組只有一條 12 題的串流，沒有重複；每題成本本來就有 ±30% 的起伏。論文是每個 repo 約 46 題、3 個 seed，報告的節省是 18–31%。這次的設定下沒有看到那個幅度，但也不足以說它在長串流裡不會出現。
- 題目都是 Flask 裡 5–40 行的小改動，原生 agent 本來就一次做對，沒有失敗迴圈讓 loop guard 發揮。
- 這台機器的 Claude Code 預設是 2.1.287，不在它支援的範圍（2.1.300–2.1.310）內；試吃用另外裝的 2.1.310，兩組相同。

## 對 OAW 的意義
- 不接上、不吸收。能看到效果的是兩個不花 token 的機制（envfacts 事實、tool pruning），但在 12 個 session 內加起來不到 15%。
- 有一點值得記住，但沒有達到吸收門檻：工具清單一換，prompt cache 就要重寫一次，所以剪工具要等之後的 session 才回本。它 README 也寫了這個代價。OAW 若要做類似的事，要在長串流上量過再說。
- 這是第一次在 agent 層實際吃它；靜態消化（`../ingest/tokeneconomizer/`）的單位清單不受影響。

## 預算（D13）
- 食物：第 1 輪 5,329,470 + T2 2,708,350 = **8,037,820**，上限 10M。
- 消化開銷：出題 6,539,760（51 回合，大多是 cache read）；題目驗證和評分 0（機械方式）。

## 安裝的痕跡（`proof.json`）
- project scope：`~/.claude/settings.json` 和 user 層啟用清單從頭到尾沒變。
- Claude Code 在 user 層的 plugin 登錄檔記了一筆 project scope 紀錄：`installed_plugins.json`、`known_marketplaces.json`，以及 1.9 MB 的 plugin cache。解除安裝後兩個登錄檔的 sha256 回到安裝前，cache 資料夾也刪了。
- `~/.claude.json` 的 sha256 有變，因為每次執行 claude 都會改寫它（這台機器同時有其他 session 在跑）。但它和 plugin 有關的 key 只變了 `pluginUsage`，整份檔案沒有任何地方提到它。
- 它的狀態在試吃區和本機暫存區（`TOKENECONOMIZER_HOME`），不在 `~/.tokeneconomizer`。原始 stream-json、diff 和它的狀態留在本機，不公開。

## 檔案
`rows.jsonl`、`grades.jsonl`、`summary.json`（N 對 T）；`followup-envfacts/` 的同名檔案（T2 對 N）；`tasting-run1.json`、`tasting.json`（`catalog.py record-tasting` 用，先記第 1 輪，再記最終）；`taste_run.py`、`summarize.py`、`sidecall_shim.py`、`verify_tasks.py`、`setup.sh`、`run.sh`。
