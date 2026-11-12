# 程式碼升級審查：Fable 5.1（2026-11-12）

Codex gpt-6.1-sol 三輪用完後的獨立判斷。原文照錄。用量：1,195,171 logical token（不含快取讀取 334,035），訂閱計費。

我先讀計畫、三輪審查紀錄，再逐檔看程式。
需要看 `h1_run.py` 裡被沿用的幾個函式（`not_run`、`run_claude`、`run_codex`、`stream`、`listed_skills` 的來源），我一次抓出來。
**先改再跑**

說明：這一輪我只能靜態讀程式（本 session 沒有 shell），沒有重跑 fixture、判定測試或沙箱探針；下面每一點都是對照程式行號確認過的路徑，不是推測。

## 第 3 次各點的狀態

| # | 狀態 | 核對結果 |
|---|---|---|
| 28a | 關閉（留一條新路徑，見 37） | `ppt_check.py:1161-1164` 把 `OSError`、`SubprocessError` 往外丟；`grade()` 在 `ppt_check.py:1278-1294` 把 ENOSPC 直接記 `infra`，其他例外先單獨轉檔一次再分 `infra`／不合格。只有簡報本身的例外才變成 `editable=False`。 |
| 28b | 關閉 | `cap_run.py:854` 把 `check_error` 算成評分失敗，`:861-862` 回傳「grading failed」不計分。驗題多跑 3 份 stress deck（`cap_run.py:1413-1437`），檢查器丟例外的題目在 `:1506-1508` 判不合格。 |
| 29 | 關閉 | `edit_table()` 回傳實際寫入的 (row, column, span)（`ppt_check.py:743-764`），`round_trip()` 用那一格的 `grid` 欄界驗證（`:1132-1144`）。 |
| 30 | 關閉 | `chart_ink()` 改用 RGB，任一色頻與中位數差 ≥64 即筆畫（`ppt_check.py:965-984`）。 |
| 31 | 關閉 | 欄位段落獨立成 piece、不逐字配對但照量筆畫（`ppt_check.py:163-182`）；`pin_numbers()` 在 A、B、E 三種變體都換成同一數字（`:560-574`、`:806`、`:823`、`:838`）。 |
| 32 | 關閉 | `swallowed()` 只認 `"1"`／`"true"`（`ppt_check.py:727-729`）。 |
| 33 | 關閉 | 計分列須與嘗試整筆相等、嘗試須帶開始紀錄的識別欄位、主 run 的 `unit_sha256` 須等於凍結的 unit（`checks/run_check.py:86-98`）。 |

## 我自己找到的問題

**34. 阻擋｜`ppt_check.py:78`、`:1141-1144`：改值標記在窄欄會換行，表格被誤判不可編輯。**
`round_trip()` 要求 E 變體頁面上有一個「整個字詞等於 `ZQ7XK`」的字詞落在該欄。`MARK` 是 5 個英數字，寫進第一個可寫的格（多半是表頭第一格，字級較大）。表格儲存格一定換行，欄寬不夠時 LibreOffice 會把單一長字在字元處折斷成「ZQ7X」「K」兩個字詞，沒有任何一個等於 `MARK`，`shown=False`，`editable=False`。12–30 列的長表格常有「序號／項次／#」這種 0.5–0.7 吋的第一欄，12–14 pt 的 `ZQ7XK` 加上預設 0.2 吋的左右邊距就放不下。這是候選和原生都可能踩到、而且題目設計上刻意出長表格的情境，一次誤判就改變那題的新過／退步分類。建議：把該欄界內的字詞照繪製順序串起來後用 `MARK in ...` 比對，或改用 2–3 個字元的標記。

**35. 應修｜`ppt_check.py:811-812`、`:1082`：圖表的「看得見」是跟「整頁拿掉整張圖表」比，不透明底色的圖表文字會被誤判看不見。**
文字框的 A 變體只拿掉文字，圖表的 A 變體拿掉整個圖表物件。於是圖表文字像素的「看得見」變成「文字顏色 vs 投影片背景」而不是「文字顏色 vs 圖表底色」。白底投影片上一張深色不透明底的圖表配白字（常見的 dark card 設計）：full 的文字像素是白、拿掉圖表後也是白，差 0，`coverage=0`，整張圖表判 `coverage` 不過；深色投影片上白底圖表配黑字同理。python-pptx 預設圖表沒有 `c:spPr` 所以透明（fixture `dark-chart` 過的原因），只有明確設底色的引擎會踩到；P1、P2 的引擎是否設底色未驗。建議：對圖表改用「字詞框內圖表自己的不透明像素（白底黑底相同的那些），在 full 頁面上是否與 B 白底算繪一致」當作看得見；開跑前至少加一個「白底投影片、不透明深色底、白字」的圖表 fixture。

**36. 應修｜`ppt_check.py:641-657`、`:602-621`：B 變體拿掉表格樣式，表頭的粗體跟著消失，B 的墨跡與 A 的可見區域不對齊。**
`plain_table()` 移除 `tableStyleId` 並把 `firstRow` 等旗標清成 0；`black_text()` 不設 `b`。python-pptx 預設表格樣式的第一列是粗體，所以 A 畫的是粗體字、B 畫的是一般字重。CJK 字寬不變，但拉丁字母和數字是比例寬，粗體累積的位移會讓後面的字詞核心筆畫落在 A 的變化區域之外，字詞覆蓋率掉到 0.9 以下。fixture 只有 2 位數字的表頭（`值01`、`旗00`），位移不到 1 px 所以過；「2024Q1」「NT$千元」「Revenue」這類表頭的影響我沒有量到。建議：B 保留表格樣式，改用逐格明寫 `noFill`、無框線、黑字去覆蓋樣式；或開跑前補一個長拉丁表頭的 fixture 看數字。

**37. 應修｜`ppt_check.py:869-880`、`:1284-1294`：soffice 寫不出 PDF 的環境失敗會被判成「簡報不算繪」。**
`convert()` 不會丟 `OSError`，磁碟滿時只回傳 "no PDF for …"；`grade()` 接著 `renders_alone()`，同一顆滿的磁碟上第二次轉檔也失敗，結果走到 `the deck does not render`，`pass=False` 且沒有 `infra`，runner 在 `cap_run.py:864` 記成候選沒過。28a 的「空間不足統一停止」只蓋到 Python 層的 ENOSPC。建議：轉檔失敗時看 `shutil.disk_usage(folder).free` 或 stderr 的 "No space" 判 `infra`。

**38. 應修｜`cap_run.py:848-863`、`:993-1004`、`FEASIBILITY.md` 3.4 節：候選引擎產出的簡報從沒經過 `ppt_check.py`，而 infra 路徑的代價是 3 個完整 session。**
`infra` 和 `check_error` 的 run 不計分、重開新 session，3 次後候選記「未完成」、原生則整格停（`return 5`）。這個設計對「量不出來就不算候選失敗」是對的，但驗收只確認 P1、P2 的最小成品「python-pptx 讀得回來」，沒有拿去 `ppt_check.py grade` 過。若某個引擎寫的 XML 讓 `read_deck()` 或變體構造固定丟例外（例如 `xfrm_of()` 的 `int()`、`table_frame()` 的 `tc` 數多於 `gridCol`），該
候選每題都會燒掉 3 個 session（Claude 格約 3M）後才記「未完成」，而這筆額度等於白費。建議：開跑前把每個候選的離線最小成品（最好再做一份含表格和圖表的）用 `ppt_check.py grade` 跑一次，確認沒有 `infra`，結果記進 `FEASIBILITY.md` 3.4 節。

**39. 應修｜`cap_run.py:488`、`:775-778`：作答 session 內部遇到磁碟滿，runner 看不到，會記成「no deliverable」而算候選沒過。**
`run_unit()` 只捕捉 runner 自己程序的 ENOSPC；agent 在沙箱裡 LibreOffice 或 python-pptx 存檔失敗、沒產出 `output.pptx`，`grade_answer()` 回 `no deliverable`，`passed=False`。計畫第 10 節說這種 run 要記未完成。`space_gate()` 的峰值 × 2 是主要防線，但峰值是從 Codex 校準 run 量的，Claude 格或 P2（Chromium 快取寫進家目錄）可能更大。建議：session 結束後若 `shutil.disk_usage(SCRATCH).free` 低於保留門檻、或 stderr 尾段出現 "No space"，把這次 run 記成沒跑成；至少寫進已知限制。

**40. 提醒｜`ppt_check.py:83`、`:993-995`：`is_bullet()` 不認中文自動編號。**
`NUMBERED` 只接受阿拉伯數字、拉丁字母、羅馬數字；LibreOffice 畫出的「一、」「①」因 `isalnum()` 為真而不算項目符號，該段落會 `unmatched`。只有用 `buAutoNum` 的 ea 類型才會觸發，python-pptx 幾乎不會產生；記成限制即可。

**41. 提醒｜`checks/run_check.py:65-70`：對帳器用狀態資料夾裡的 `units_ppt.json` 算 unit 摘要，沒有核對它等於 `FREEZE.json` 的 `units_ppt_sha256`。**
正式 run 開跑時 `cmd_run` 已核對 manifest，所以不影響結果；只是「對帳獨立驗證凍結綁定」這句目前少一環。

**42. 提醒｜`cap_run.py:100`：`SESSION_SECONDS = 3600`，H1 是 7200，計畫沒定。**
時間到就切斷照現狀評分，對所有組一樣；但工具鏈較重的候選（P2 的 Playwright 算繪）較可能被切。凍結前決定一次即可，之後不能動。

**43. 提醒｜`ppt_check.py:987-990`：`upright()` 對 2–3 個字的傾斜標籤偵測不到。**
LibreOffice 自動把放不下的類別標籤轉 45°，長標籤會被抓成 `rotated`，3 個字以內的不會。對各組一致，只是寬鬆得不一致。

## 實作跟計畫不同、但可以接受的細節

- 磁碟量測拆成兩顆：本機暫存要求「量到的峰值 × 2」，保留磁碟要求「剩餘 run × 保留量 + 15G」（`cap_run.py:678-694`）。本機只有 11G，這是合理的落地方式，FEASIBILITY 3.5 節已寫明。
- Claude 啟動清單守衛和暖機狀態檔（`cap_run.py:90-98`、`:289-307`、`:1195-1233`）：計畫第 7 節「啟動 token 幾乎不變」的前提在這版 CLI 不成立，這是補上的公平性控制，重啟不花 token、另外計數。
- `size_min` 雙向以算繪為準（差超過 1.5 點），和「版面配置段落寫 60 仍算 44」的實測，第 3 次已接受。
- 表格的 E 變體只留該表（`ppt_check.py:849-856`）；表格的 `outside` 不管往下長高，交給頁外規則（`:1087-1088`）。
- 圖表「可編輯」綁在 python-pptx 讀得到的 `c:chart` 部件；chartEx 或 `mc:AlternateContent` 裡的圖表會被整個略過，不是誤判成不可編輯，只是不算圖表。brief 已用 python-pptx 的類型名定義 `c.type`，範圍一致。
- 原生組某題 3 次基礎設施失敗就停整格（`cap_run.py:999-1000`），比計畫「每組每題最多 3 次」更嚴，但符合第 6 節「必要的 run 沒完成就未完成」。
- 校準只量 Codex N1 的峰值寫進凍結檔；開跑後 `disk_figures()` 會取所有嘗試的最大值滾動更新。
- 原生 `add_textbox` 預設 `wrap="none"` 加 `spAutoFit`，LibreOffice 會把框撐大，但檢查用檔案裡的框界算 `outside`。這和 PowerPoint 開檔不重算尺寸的行為一致，fixture `overflow`、`nowrap` 固定了這個語意，對各組相同。
- 六題依序取前四個合格題、16:9、標題 placeholder、純文字素材、50 dpi 預覽、完整 PDF 字詞套 0.9，沿用前三次已接受的項目。

結論的依據：34 單獨構成阻擋，改法是一行比對；35、36 建議在改 34 的同時各加一個 fixture 量一次，有數字再決定是修還是記成限制；37–39 可以修也可以寫進限制。改完 34 之後，以我讀到的程式，其餘部分符合計畫第 3 到 8、10、12 節的要求，候選和原生走的是同一條沙箱、同一套檢查、同一個判定程式。
