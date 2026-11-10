# H1 升級審查：gpt-6-astra（Codex，reasoning high，2026-11-10）

Codex gpt-6.1-sol 的 3 輪審查用完後，照 owner 的規則由 gpt-6-astra 和 Fable 5.1 各自獨立判斷第 4 版能不能凍結。審的是第 4 版；行號指第 4 版。原文照錄，只把本機路徑換成 repo 內的相對位置。用量：輸入 1,455,280（其中快取 1,320,960）、輸出 7,457。

---

可以凍結
Round 3：#1–8、#10–11 的計畫與程式均關閉；#9 計畫已關閉、程式仍部分開放（應修，不影響 primary 判定）。

1. **應修｜`H1/h1_judge.py:102`、`H1/h1_judge.py:481`｜仍可把 counted rows 同時當作三種 ledger。** `Frozen.check()` 不區分 record 類型，`reconcile()` 只核對輸入中的 identity，未確認 starts 是開始紀錄。**反例已在記憶體重算：**O 有一次失敗花 2M，之後成功；將 counted rows 同時提供為 rows、attempts、starts，judge 仍輸出 `complete／沒差`，失敗成本卻由 2M 變成 `{}`，連「未知」都沒有。**最小修正：**start 加上固定 `event: "start"`，judge 強制驗證 starts schema，拒絕 counted rows／terminal attempts 冒充 starts。這延續 #9 的成本揭露問題；未改變 counted comparison，因此不升為阻擋。

逐項關閉核對如下（P＝`PREREG.md`，R＝`h1_run.py`，J＝`h1_judge.py`）：

| Round 3 | 計畫／程式核對 |
|---|---|
| #1 關閉 | P:139 要求完整比例；R:829 不再 round，J:191 從 counts 重算；原反例得到「未定」。 |
| #2 關閉 | P:128 明定恢復與雙向對帳；R:1228 在續跑前 recover，R:1861 拒絕多筆成功或缺列。 |
| #3 關閉 | P:111 凍結 executable；R:2082 記位置、resolved target、digest，R:2120 納入 BIN。 |
| #4 關閉 | P:110–112 鎖 bank 與 main starts；R:1903、1910、2161 強制檢查，R:1011 寫 provenance。 |
| #5 關閉 | P:122 明定 candidate 測試故障照算；R:818 將有 exit code、無 suite report 判 regression／0 分。 |
| #6 關閉 | P:91 與 brief B 規則 8 均補齊；R:1478、1481 要求全部／逐項舊值 mutation 的 base tests 通過。 |
| #7 關閉 | P:120 已明定 observable-stream ceiling；R:368、1058 標記含 subagent 超額，照常計分。 |
| #8 關閉 | P:44 要求每則 root model；R:325、435 記 missing，R:555 拒絕；兩格旗標路徑重算通過。 |
| #9 部分開放 | P:206 已完整；J:102、283、415 補了對帳、去重與未知成本，但仍接受上述錯置輸入。 |
| #10 關閉 | P:127、323 記錄 binding 要求；R:1724 將 bound 寫入 start，R:1087 復原時保留。 |
| #11 關閉 | P:137 要求兩次全過；R:904–908 核對 exit、相同 statuses、非空且全部 passed。 |

未發現其餘阻擋；保留計畫已登記的 owner 決策與限制。

實讀：`CLAUDE.md`、`AI_CONTEXT.md`、`VERSION.json` 指定欄位、`CURRENT_STATE.md`、`harness-evaluator.md`、`read-discipline.md`、skills triggers；H1 的 `PREREG.md`、兩支 Python、兩份 brief、`review-1/2/3.md`；round3-input runner 與完整 diff；`EVAL_PROTOCOL.md`、`eval_stats.py`；三支 checks、`pipeline3.sh/log`。實跑：唯讀查詢與上述 pure-function 合成重算；未執行 checks scripts、未啟動 model session、未寫檔。