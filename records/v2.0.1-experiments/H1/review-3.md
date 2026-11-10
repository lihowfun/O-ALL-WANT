# H1 審查第 3 輪（Codex gpt-6.1-sol，reasoning high，2026-11-10）

審的是第 3 版的 `PREREG.md`、兩份 brief、`h1_run.py`、`h1_judge.py`；下面的行號指的是第 3 版。原文照錄，只把本機路徑換成 repo 內的相對位置。

---

先修再凍結
Round 2：文字與程式均關閉 3、5、6、7、8、9、11、12、13、14；仍開放 1、2、4、10、15。Round 1：7 關閉；5、9、11、14 仍開放。

1. **阻擋｜`h1_run.py:814`；`h1_judge.py:206`｜四捨五入會改變判定詞。**  
   計畫要求用通過項數除以總項數，runner 卻先取四位小數。已重算反例：N1＝N2，C 四題的 O／N 分數分別為 `(2/12, 1/12)`、`(11/12, 1)`、`(6/10, 1)`、`(1, 1)`；B 四題差為 `+0.2、+0.2、0、0`，A 全同分，token 相同。完整精度的 C 平均差恰為 −0.10，觸發「類別不一致」，詞為「未定」；四捨五入後變成 −0.099975，得到「等價／沒差」。  
   **最小修正：**儲存完整比例，僅在顯示時格式化；保留 passed／n 供重算。

2. **阻擋｜`h1_run.py:1199、1224、1230、1815`｜Round 2 #2 的「每題一次 calibration」仍可被中斷取代。**  
   attempts 先寫、rows 後寫。兩者之間中斷時，續跑只從 rows 判斷完成與否，會再做一次已成功的 calibration。反例：第一次正常完成得 1.0，第二次得 0.5，rows 只有第二筆；`counted_rows()` 接受，freeze 選中本應因天花板淘汰的題。已在記憶體中重算此接受路徑。  
   **最小修正：**續跑先恢復已成功但尚未寫入 rows 的 attempt；freeze 雙向對帳，拒絕同題多筆成功 calibration attempts。

3. **阻擋｜`h1_run.py:2016、2033、2050`｜Round 2 #1 的內容 digest 已補齊，但實際 CLI 選擇仍未凍結。**  
   `scrub()` 把整個 BIN 換成 `$H1_BIN`，而設定摘要只包含 HIDE、SHOW。反例：同一工具複本預先包含 `bin/`、`alt/bin/` 兩組同版本 CLI；freeze 後切換 H1_BIN，實際 executable 和 PATH 改變，manifest 卻完全相同。此反例已重算。  
   **最小修正：**把 BIN 納入未 scrub 的設定摘要，或記錄 SHOW index、複本內的相對 executable 路徑及其 digest。

4. **阻擋｜`h1_run.py:1849、1854、2097`｜看到第一個 main 輸出後，仍能重新凍結。**  
   鎖定條件只有「已有 counted rows」，不是「已有 main starts／attempts」。A 又只鎖題號，未鎖計畫指定的原始 bank digest。反例：第一個 main run 已產生可觀察輸出後中斷，rows 尚空；operator 可用另一份同題號 bank 重新 verify／freeze A，再覆寫 FREEZE。舊 start 沒有 freeze／unit provenance，續跑仍接受。  
   **最小修正：**任何 main start 出現後即鎖住題庫和 FREEZE；start 記完整 provenance；A 強制核對指定 bank 的 SHA-256。

5. **阻擋｜`h1_run.py:806、1046、1051`；`PREREG.md:136`｜候選程式弄壞 suite，可能獲得整題重試。**  
   反例：candidate 使既有測試無限迴圈。`timeout` 留下 `suite.code=124`，沒有 XML；runner 將它當 grading infrastructure failure，重試評分後再重做整個模型作答。計畫明定整套跑不起來應記 0 分。這使較容易卡死的臂得到額外作答機會。  
   **最小修正：**candidate 引起的 pytest timeout、crash 或無法執行，記 regression／0 分；只有可辨識的 sandbox／grading 基礎設施故障才能重做模型。

6. **阻擋｜`h1_run.py:1434–1438`；`AUTHOR_BRIEF_B.md:72`｜Round 2 #4 的舊值 mutation 還缺 base 檢查。**  
   新值逐 fact mutation 已修；但全部換回舊值、逐項換回舊值，只查 recall 失敗，沒有要求 base tests 通過。反例：某舊值使模組初始化失敗，recall 和 base 全失敗，仍通過這兩項驗題。正式作答使用舊值時，連不應依賴記憶的 base 分數也一起失去，放大記憶臂差異。  
   **最小修正：**對 `stale` 和每個 `back` 都要求所有 `test_base_*` 通過，與 wrong-value mutations 相同。

7. **阻擋｜`h1_run.py:283、352、1034`；`PREREG.md:119`｜8M session 總量上限沒有實現。**  
   watch 只看串流 message usage；完整 `modelUsage` 回來後，只重檢整格預算。反例：parent 3M、subagents 6M，串流沒有撞限，最後 9M 全數計費並正常計分，沒有 ceiling flag。這不是漏算 30M 預算，但違反每 session 8M 的條件，會讓依賴 subagent 的作答取得更多工作量。  
   **最小修正：**凍結前明定為可觀測串流的上限並標記實際超額；若維持 8M 總量承諾，須納入子代理即時用量。不能改成超額便重試，因計畫要求 ceiling 作答照常計分。

8. **阻擋｜`h1_run.py:324、427、541`｜Round 2 #10 仍忽略個別缺失的 root model。**  
   parser 只收集有值的 model，`not_run()` 再檢查收集結果。反例：第一則 root 回覆有正確 model，第二則非 synthetic root 回覆沒有 model；集合仍只有正確名稱，session 被接受。Codex 後續 `turn_context` 缺 model 也一樣。這不符合「每則／每個主執行緒模型都核對」。  
   **最小修正：**另記缺失旗標，任何應有 model 的 root 訊息／context 缺值即 not run；不要只驗證非空集合。

9. **應修｜`h1_judge.py:100、257、388、444`；`h1_run.py:1061`｜Round 2 #15 尚未保證完整失敗成本。**  
   反例有三種：把真實 counted files 同時交給 `--rows`、`--attempts`，失敗嘗試便消失；同一 attempts file 重複提供，失敗成本翻倍；中斷的 start 沒有進入 attempts file，正常續跑後也不會回報其成本。尚無完整類別時，失敗成本整段亦不輸出。這些不改 counted comparison，但會錯報支出。  
   **最小修正：**以完整 start ledger 對帳並產生 interrupted 終態、拒絕重複 identity；無論有沒有完整類別，都輸出失敗成本及未知／下限。

10. **應修｜`h1_run.py:1068、1668–1670`｜solver 中斷後無法按計畫續跑。**  
    `tried()` 合成的 interrupted 項只有 start 欄位，沒有三個 binding digests；`cmd_solver()` 隨即對它執行 `refuse_other()`，必然拒絕並要求新 state，尚未用完三次機會也一樣。  
    **最小修正：**開始紀錄即寫入完整 binding，復原 interrupted attempt 時保留並核對。

11. **應修｜`h1_run.py:888–894`；`PREREG.md:134`｜baseline 未強制「兩次全部通過」。**  
    程式只要求兩次 exit 0、statuses 相同。反例：兩次都是 493 passed、1 skipped，也會接受。現有 pipeline 的 494 passed 紀錄沒有這個問題。  
    **最小修正：**另要求 cases 非空且全部為 `passed`。

Launch configuration：同格各臂權限對稱，未見 hidden tests／其他臂的掛載洩漏；工具複本未見外指 symlink。Codex `.agents/` 唯讀是已登記的產品限制；CLI 選擇綁定與 8M 條件仍須修正。

平台與實讀／執行範圍：Linux 6.8.0-136-generic x86_64；Python 3.10.20，另核對 `/usr/bin/python3` 為 3.10.12。完整讀 H1 七檔、EVAL_PROTOCOL.md、eval_stats.py；另讀專案規則、相關 skills、oaw_mode.py／OAW review 相關段落、三支 checks、pipeline2.sh／log、manifest4.out、v2 briefs 差異及 pilot raw；執行唯讀查詢與 in-memory／mock 反例重算，未啟動 model session、未寫任何檔案。