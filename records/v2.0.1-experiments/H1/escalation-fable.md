# H1 升級審查：Fable 5.1（Claude 子代理，2026-11-10）

Codex gpt-6.1-sol 的 3 輪審查用完後，照 owner 的規則由 gpt-6-astra 和 Fable 5.1 各自獨立判斷第 4 版能不能凍結。審的是第 4 版；行號指第 4 版。原文照錄（模型名稱是子代理自己回報的）。用量約 194K token、16 次工具呼叫。

---

可以凍結
第 3 輪 11 項：1、2、3、4、5、6、7、8、9、10、11 全部在計畫和程式裡都關閉；沒有未關的項目。

逐項核對（計畫／程式）：
1. 四捨五入：`h1_run.py:829` 存完整比例、保留 passed/n；`h1_judge.py:191-196` 用 passed/n 重算；PREREG 評分 5。關閉。
2. 校準中斷重跑：`recover()`（`h1_run.py:1092-1100`，`cmd_run` 1228 和 `cmd_solver` 1704 都先呼叫）把已算數但沒進 rows 的 attempt 補進 rows；`counted_rows()` 1864-1881 雙向對帳、同題兩筆算數 attempt 拒絕；PREREG「一個 unit 怎麼跑」。關閉。
3. CLI 執行檔綁定：`cli_file()` 2082-2092 記複本索引、相對路徑、最終指到的檔案和 sha256（manifest5.out 實測有值：claude → `lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe`，codex → `.../codex/bin/codex.js`）；`BIN` 進 `local_settings_sha256` 2120；PREREG「凍結」。關閉。
4. 開始後重新凍結：`main_started()` 1103-1106 看 starts/attempts/rows；`cmd_freeze` 1903、`cmd_manifest --write` 2161 都拒絕；開始紀錄帶完整 provenance 1011、1259-1263；`cmd_run` 1220-1227 連 starts 一起核對 runner、unit、FREEZE 摘要；A 類 `A_BANK_SHA256` 1910（我算過 tasks.json 的 sha256 一致）。關閉。
5. 候選程式弄壞 suite：`grade()` 818-819 suite 有結束碼但沒有報告 → 退步 0 分；`error` 822-823 只剩腳本本身壞掉；PREREG 「一個 unit 怎麼跑」第 3 點。關閉。
6. 換回舊值的 base 檢查：1478、1481-1482 兩項新檢查；brief B 第 65-68 行。關閉。
7. 8M 上限：串流上限照舊（294），`over_ceiling` 368 另標、照常計分 1058-1059；PREREG 第 120 行改成「管串流看得到的用量」。關閉。
8. 個別 root 回覆缺模型：Claude 325-329 `missing`、Codex 438-439 `model_missing`，`not_run()` 555 任一缺就不算跑。關閉。
9. 失敗成本：`h1_judge.py` `reconcile()` 102-119 用 starts 對帳、重複拒絕、中斷的 start 變 interrupted（token 未知）；`not_counted` 不論格完不完整都輸出 420、424；`--starts` 必填 477。關閉。
10. solver 續跑：開始紀錄帶 `bound` 1724-1725，`tried()` 合成的 interrupted 項過得了 `refuse_other`；`recover("solver")`。關閉。
11. 基準全過：908-909。關閉。

剩下的項目（都不會讓計分結果錯或臂間不公，也不給操作者看到資料後挑選的空間）：

1. 應修｜`h1_run.py:1228`（`recover()`）與 1229（codex 格沒有鎖）｜PREREG 允許 codex 格同時跑多個 process，但 `recover()` 在沒有鎖的情況下讀 attempts 再 append rows。反例：process A 在 1265 寫完 attempt、還沒執行 1271 寫 row 的瞬間，process B 啟動呼叫 `recover()`，把同一筆補進 rows；之後 A 也寫一次 → 同一 run 兩列。後果是 `h1_judge.py:164` 拒絕判定（「two rows for one run」），不是算錯，但只能手改 rows 才能解。最小修正：codex 格也拿一個 per-state 檔案鎖包住 `recover()`＋「寫 attempt → 寫 row」那兩行（或 `recover()` 只在持鎖時執行）。

2. 應修｜`h1_run.py:158-163`（`offline()`，timeout=2400）與 789-794｜兩段內層 `timeout 600`／`timeout 1500` 沒加 `-k`，只送 SIGTERM；整段 bash 只剩約 300 秒餘裕。反例：候選程式在 `src/flask/__init__.py` 裡忽略 SIGTERM 並讓某測試卡住，內層 timeout 殺不掉，`subprocess.run` 在 2400 秒丟 `TimeoutExpired`，沒人接 → runner 以 traceback 結束，這次變成「interrupted」嘗試（計入 3 次後再從頭重跑），而不是計畫規定的「退步 0 分」。極端情況、兩臂對稱，所以不算阻擋。最小修正：內層用 `timeout -k 30 ...`，`offline()` 捕捉 `TimeoutExpired` 回傳 124 並讓 `grade()` 當成 suite 退步／hidden 全失敗處理。

3. 應修｜`h1_run.py:2160-2177`｜`main_started()` 只鎖 `manifest --write`；不加 `--write` 的 `manifest` 仍會把同格式 JSON 印到 stdout，操作者可以在正式 run 開始後重導向成另一份 FREEZE.json 再用 `run --freeze` 跑別的類。目前不會產生錯的結果：`cmd_run` 1225-1227 和 `h1_judge.py:86-87` 都要求所有列、嘗試、開始紀錄是同一份 FREEZE 摘要，混用就整批拒絕；但「開始後 FREEZE 不能再寫」這條靠的是下游拒絕而不是上游鎖。最小修正：`cmd_run --freeze` 只接受 `here/FREEZE.json`，或 `main_started()` 時 `manifest` 不加 `--write` 也只印摘要不印整份。

其餘核對過沒有問題：判定第 1–6 步、分類細目、L 對照、成本門檻、第五步結果表都跟 PREREG 和 `eval_stats.py` 的語意一致（`compare`/`cost`/`pooled_within_sd` 只從凍結版載入）；評分環境用全新 N 樣板只收 `src/`、無網路、空家目錄；臂序輪轉、N1/N2 各自全新工作區；預算基數寫一次、加額度要 D 編號、session 前後都重檢；出題帳本、補題只補缺型、審核綁摘要、校準不可重跑；A 類題庫 sha256 和題號寫死；管線實跑（pipeline3.log）顯示 solver 第二次呼叫不重跑、manifest 無本機名稱、Codex 計費／provider／模型核對都讀得到。

實際讀過或執行：`PREREG.md`、`review-3.md`、`h1_run.py`（全文）、`h1_judge.py`（全文）、`AUTHOR_BRIEF_B.md`、`AUTHOR_BRIEF_C.md`、`h1_run.round3-input.py`（與現版 diff）、`OAW-v2/docs/EVAL_PROTOCOL.md`、`OAW-v2/scripts/eval_stats.py`、`oaw_mode.py`（只 grep `STANDARD_LINES`／`is_doc`）、`pipeline3.sh`、`pipeline3.log`、`manifest5.out`（cli_file 欄位）、`checks/freeze_check.py`（只看段落標題）、tokeneconomizer `tasks.json` 的 sha256 與題序；只執行唯讀指令，沒有啟動任何 model session，沒有寫任何檔案。
Fable 5.1
