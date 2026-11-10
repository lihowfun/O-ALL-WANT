# H1 審查第 2 輪（Codex gpt-6.1-sol，reasoning high，2026-11-10）

審的是第 2 版的 `PREREG.md`、兩份 brief、`h1_run.py`、`h1_judge.py`（第 1 輪修過之後的版本）；下面的行號指的是第 2 版。原文照錄，只把本機路徑換成 repo 內的相對位置。

---

先修再凍結
Round 1：已關閉 1、2、3、4、6、8、10、12、13、15、16；仍開放 5、7、9、11、14。

1. **阻擋｜`H1/h1_run.py:605`、1339、1343｜Round 1 #5 未關閉。** `manifest()` 沒有涵蓋實際複製進 sandbox 的完整內容，也沒有涵蓋 CLI、Python runtime 的內容。arm 只核對 commit、tree、dirty 數量及 `.venv` digest；CLI 只核對版本字串，runtime 掛載只核對路徑。反例：freeze 後在 N 樣板加入被 `.gitignore` 忽略的 `.vscode/answers.txt`，commit、tree、dirty 數量都不變，run 仍接受，agent 卻能看到新增答案；同版本 CLI 或 `.venv` symlink 指向的 runtime 也能換內容。最小修正：對實際送入 sandbox 的完整樣板、CLI 及外部 runtime 做 content digest；不納入 digest 的檔案必須在複製時排除。

2. **阻擋｜`H1/h1_run.py:1149`、1211、1255｜Round 1 #14 部分未關閉。** 沒有強制 author chronology、最多補兩次、只補缺型，以及每題只做一次指定 calibration。反例：第一次 calibration 某題得 1.0，operator 用另一個 tag 重跑，得到 0.75，再把後者交給 `freeze --calibration`；或看完結果後調換 `--candidates` 的 author 順序，改選另一題。程式都接受。最小修正：建立固定的 author／calibration ledger，自動使用完整 author chronology 與每題第一筆有效 calibration，拒絕替代 tag、重複結果及超額補題。

3. **阻擋｜`H1/h1_run.py:1066`、1116、1238、1256。** solver、audit、calibration 都只靠 unit ID 對接，沒有核對候選內容及驗題版本。反例：`large-1-a` 已通過 audit，後來同 ID 的 hidden test 加入未公開需求並重新 verify；`cmd_audit` 因 ID 已存在而跳過，freeze 仍套用舊 audit。B 的舊 solver 成績也能套到改過的 prompt；calibration 的 runner digest 雖有記錄，freeze 沒有要求它與正式版本一致。最小修正：各報告綁定 candidate、unit、verification、runner 的 digest，任何不符即拒絕；不可只用 ID 重用結果。

4. **阻擋｜`H1/PREREG.md:86`、`H1/h1_run.py:988`｜Round 1 #11 未關閉。** 同時換掉所有 facts，不能證明每個 fact 都有被測到；程式符合新版文字，但新版效度規則仍不足。反例：決定包含 key `QZ_H1_TTL_729` 和 default `871931`；兩個 recall tests 都提供該 key 的自訂值，只檢查自訂值生效。key/default 一起換錯時，兩個 tests 都失敗、base tests 都通過；但 agent 只記對 key、把 default 寫錯，仍會被記為「記得」。最小修正：逐 fact 單獨 mutation，要求至少一個相關 recall test 失敗，全部 base tests 仍通過；superseded 也逐 fact 換回舊值。

5. **阻擋｜`H1/h1_run.py:447`、569、579｜Round 1 #9 未關閉。** frozen 清單只保留 function 名稱及 case 數，沒有 round 1 要求的完整 node IDs；既有 suite 也只看 exit code。反例：reference 收集到 `test_r01[a]`、`test_r01[b]`，候選實作使動態 parametrization 變成兩個 `a`，case 數仍是 2，缺少的 `b` 不會被發現。另一個反例是原本通過的 suite case 變成 skip，pytest 仍可 exit 0，因此不算 regression。最小修正：凍結並核對完整 node IDs 與 baseline statuses；原本 passing 的 case 消失、skip 或 xfail 都應算 regression。另須拒絕 brief 不允許的 test methods，避免同名 methods 被合併成一個 function。

6. **阻擋｜`H1/h1_run.py:219`、684、703、743、1404｜Round 1 #7 未關閉。** 預算沒有可靠的固定 ledger，也沒有在取得完整 usage 後重新檢查。反例：最後一個 run 剩 0.5M 額度，stream 只看到 0.4M，正常結束的完整 usage 是 0.6M；這筆仍會計分，甚至讓整格 complete，違反應記「沒跑並停止」的規則。run 尚未 append 時 runner 中斷，已花 token 也不進 `cell_spent()`；續跑還能任意降低 `--spent-before` 或提高 `--cap`，沒有 owner 放行紀錄的檢查。最小修正：固定初始支出及核准額度、逐 session 持久記帳、單一 Claude process 鎖定；完整 usage 回來後及下一個 session 前都檢查額度。

7. **阻擋｜`H1/h1_judge.py:74`、320、345。** completeness 只檢查單格 PRIMARY rows 的 digest 一致，沒有核對兩格同一個 freeze、同一份 roster，L 也未納入 digest 檢查。反例已重算：Claude 使用 `old` digest 的 12 題，Codex 使用 `new` digest 的另外 12 題，各臂同分；兩格都得到 complete，合併為「沒差」，共同 unit 數卻是 0。最小修正：judge 讀取實際 FREEZE 與其題庫，核對所有 rows（含 L）的 digest、unit→class、runner／units provenance，並核對載入的 `eval_stats.py` digest。

8. **阻擋｜`H1/h1_run.py:885`、1017。** `large_enough` 把 `src/` 下所有新增、刪除行都算成 code，包含 Markdown。反例：20 行功能加上 `src/flask/notes.md` 的 300 行文件，會通過 large 檢查；但 `oaw_mode.py` 排除文件後不會因此升到 standard，與 PREREG 所稱「正好是主場條件」不符。最小修正：使用與凍結版 `oaw_mode.py` 相同的 non-documentation 計數定義。design reference 也應確認真的加入指定 note，現在只確認 prompt 有檔名。

9. **阻擋｜`H1/h1_run.py:271`、378。** Claude 的 usage-limit 判斷會搜尋 agent 自己寫的正常 final answer。反例：任務要求錯誤訊息為 `usage limit reached`，agent 成功完成並在 final 提到該字串；runner 會把成功答案當 subscription failure，排除並容許重做，兩臂不同的敘述方式便能改變有效 attempts。最小修正：只依 CLI 的結構化 rate-limit／error 事件判斷，不搜尋正常答案內容。

10. **阻擋｜`H1/h1_run.py:234`、318、382。** model／billing 驗證不完整：model 缺失仍接受、名稱只比 prefix；Claude 不核對實際主模型訊息，Codex 的 billing source 則直接寫死為 `chatgpt`。反例：init 標示要求的 Opus，但實際主模型訊息為 Haiku，仍可計入 Opus cell；Codex 登入改成 API-key 模式也仍被記成訂閱。最小修正：核對實際 root model，僅接受明定的 aliases；缺失或不符算 not run。billing source 必須由實際 authentication/provider metadata 驗證。

11. **阻擋｜`H1/h1_run.py:1139`。** audit 用 `bool()` 轉換 `stated`，會把 JSON string `"false"` 當成 true。反例：audit 回覆某函式 `"stated": "false"`，該函式不進 `struck`，含未公開需求的 unit 可以被接受。最小修正：嚴格驗證 schema：`stated` 必須是 boolean、函式名稱不得重複，且必須完整對上 frozen functions；不合法的回覆不得當成通過。

12. **應修｜`H1/h1_run.py:814`。** C gate 在每次續跑都重新保留「整批 C」的預估，包含已完成部分。反例：已花 20M、C 推估 6M，初次需要 27.5M，准跑；完成其中 3M 後遇 usage limit，續跑卻要求 23M＋7.5M＝30.5M 而拒絕，儘管剩餘 C 推估只有 3M。最小修正：保存首次進入 C 的 gate 決定；續跑由 hard cap 管理，或只推估尚未完成的 runs。

13. **應修｜`H1/h1_run.py:364`、1131。** `run_codex()` 先把 final 截成 2,000 字元，audit 才解析 JSON。反例：允許的 20 個 functions，即使用簡短 sentence/reason，JSON 也可達 3,035 字元；完整合法答案被截斷後，audit 只能失敗。最小修正：保留完整 final 供機械解析，另設摘要欄位給報表。

14. **應修｜`H1/h1_run.py:317`、`H1/h1_judge.py:284`。** Codex 的 `skills` 初始化為空後從未填入，因此 `used_skill` 永遠是 0；也沒有像 Claude 一樣記錄啟動時的 skill/tool availability。反例：Codex 實際載入並遵循 `oaw-review/SKILL.md`，報表仍顯示未使用 skill。最小修正：解析 rollout 中實際 skill 載入及工具清單；無法辨識的欄位應記 unknown，不能記 0。

15. **應修｜`H1/h1_judge.py:349`、174。** `--attempts` 可省略，輸出卻仍把 `attempts_not_counted` 寫成空物件。反例：O 有兩次失敗共花 2M，operator 只提供 counted rows，報表便完全隱去這筆支出，違反第三步必須並列的規則。最小修正：要求完整 attempts 輸入並核對 counted rows；未提供時明標「未提供」，不可表示零次失敗。

Launch configuration：同格各臂使用相同權限，未見額外洩露 hidden tests 的掛載；兩格保留原生權限差異。pilot 確認 Codex 的 `.agents/` 唯讀會阻擋 OAW memory helper，這是預設安裝的產品限制，應記錄受阻操作，不能替 O 單獨放寬。

驗證平台與範圍：Linux 6.8.0-136-generic x86_64、Python 3.10.20；完整讀取 H1 全部 7 檔、EVAL_PROTOCOL.md、eval_stats.py，另讀 oaw_mode.py／context_hub.py 相關段落、OAW templates、3 份 synthetic checks、env.sh 與 pilot rows／raw；執行唯讀查詢、CLI help 與 in-memory judge／stats 反例重算，未執行 model session、未寫檔。