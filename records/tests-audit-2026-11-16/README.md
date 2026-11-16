# 測試是幫助還是拖累：2026-11-16 的盤點

owner 的問題（2026-11-16）：「我不確定你這個 718 or 797 到底是幫助還是拖累」。
測試的數量只說明做了多少。這份紀錄量兩件事：測試抓到多少錯、花多少時間。

對象：`main` 的 `996c7c7`（797 個測試，Linux 閘門回報的數字）。

## 一、故意放錯的抽樣（Linux，Python 3.10.12）

做法（`mut_sample.py`，結果 `results.jsonl`，彙整 `analyze.py`）：

- 在 `scripts/*.py` 共 23 支程式裡找出 6,690 個可以放錯的位置：比較運算 3,244、`and`／`or` 1,871、`not` 921、`True`／`False` 654。
- 放錯的方式四種，每次只放一個：把比較反過來或移一格（`==`↔`!=`、`<`↔`<=`、`>`↔`>=`、`is`↔`is not`、`in`↔`not in`）；`and`↔`or`（一個布林式的第一個連接詞）；`True`↔`False`（包含參數預設值）；拿掉一個 `not`。
- 不重複地隨機抽 60 個位置（亂數種子 20261116）；另外放 4 個不放錯的對照組，穿插在同一批裡。
- 指令：`mut_sample.py --base <996c7c7 的匯出> --work <暫存目錄> --out results.jsonl --n 60 --controls 4 --workers 10`。
- 每一個都在自己的一份完整程式上跑全部測試（`unittest` discover `tests/`），上限 900 秒，10 個平行。
- 沙盒是 bubblewrap：整個檔案系統唯讀、沒有網路。可寫的只有這個工作自己的目錄（程式副本、HOME、TMPDIR 都在裡面）和一個私有的 `/tmp`；另外掛上 `/dev` 與 `/proc`。

「抓到」與「漏掉」在程式裡的定義：

- 抓到：測試回報失敗或錯誤；或逾時；或沒有拿到彙整行。後兩種也算抓到，所以沙盒起不來或無關的逾時有可能被誤算。這一批的實際情況：逾時 0 個；37 個有彙整（36 個跑了 797 個測試，1 個因為有測試模組載入失敗只跑了 716 個）；3 個沒有彙整（見下）。
- 漏掉：整輪通過。程式沒有檢查「跑滿 797 個、沒有略過」，這一點是事後從結果核對的：20 個漏掉的都跑了 797 個、0 失敗、0 略過。
- 沒有彙整的 3 個（編號 17、25、61，都在 `improvement.py`）：`unittest` 已經印出 `FAILED (failures=7, errors=29)`、`FAILED (failures=7, errors=29)`、`FAILED (failures=25)`，return code 1；之後抽樣小程式在列出測試名稱時自己出錯（小程式的 bug）。原始輸出的尾段保留在 `results.jsonl` 的 `stderr_tail`。

結果：

| 項目 | 數字 |
|---|---|
| 對照組 | 4／4 全過（每次 797 個測試、0 失敗；176.2–185.5 秒） |
| 放錯的 60 個 | **抓到 40、漏掉 20（66.7%；95% Wilson 區間 54.1%–77.3%）** |
| 依放錯方式 | 比較 27／36；`and`／`or` 7／14；拿掉 `not` 6／6；`True`／`False` 0／4 |
| 抓到時有幾項失敗或錯誤 | 37 個有計數：最少 1、中位數 5、最多 147；其中 9 個只有 1 項 |

依程式（抓到／抽到）：`catalog.py` 3／5、`catalog_core.py` 5／6、`catalog_ui_server.py` 3／6、`code_index.py` 5／9、`context_hub.py` 0／2、`eval_ledger.py` 2／2、`eval_ledger_fixcheck.py` 2／2、`fast_screen.py` 1／1、`goldfish_review.py` 2／2、`harness_check.py` 1／2、`improvement.py` 3／3、`judge_calibration.py` 1／1、`oaw.py` 6／7、`oaw_mode.py` 1／2、`oaw_status.py` 0／2、`user_install.py` 3／5、`validate_skills.py` 0／1、`wiki_sync.py` 2／2。每支程式抽到的數量很少，這一列只能當線索。

漏掉的 20 個（lead 與複核者各自讀過 `996c7c7` 的程式；複核者對其中幾個另外做了不寫檔的小比對）：

| 位置 | 放的錯 | 放錯之後的行為 |
|---|---|---|
| `catalog.py:617` | `>`→`>=` | 剛好等於上限的 PDF 會被拒絕 |
| `catalog.py:888` | `==`→`!=` | 論文來源的註記對調 |
| `catalog_core.py:1686` | `or`→`and` | 相關性判斷用的名稱不同：只有 full name 的紀錄少了名稱 |
| `catalog_ui_server.py:797` | `==`→`!=` | 互動選單：還沒試吃時，答 `t` 不試吃，答其他（包含 Enter、`f`）反而送去試吃 |
| `catalog_ui_server.py:863` | `not in`→`in` | 互動選單：可加回的清單內容不同 |
| `catalog_ui_server.py:959` | `!=`→`==` | 顯示順序：中嚴重度排到高嚴重度前面 |
| `code_index.py:986` | `>=`→`>` | 沒有結尾的 JSX 元素到檔尾時丟 `IndexError`（原本回傳 `None`） |
| `code_index.py:1454` | `and`→`or` | 檔尾沒有換行時最後一行被丟掉，例如 `function f() {}` 這個定義不見 |
| `code_index.py:1646` | `False`→`True` | 箭頭函式多了一個自己的 `this`，型別紀錄不同 |
| `code_index.py:3709` | `in`→`not in` | JS default 匯入的別名比對反過來 |
| `context_hub.py:136` | `False`→`True` | 預設值改了，三個呼叫端都沒傳這個參數：meta 頁不再被排除 |
| `context_hub.py:379` | `False`→`True` | 寫入主檔成功時也印出「分流到待併檔」的訊息；寫到哪裡不變 |
| `harness_check.py:148` | `or`→`and` | 閘門自己的 CLI 檢查變寬 |
| `oaw.py:319` | `or`→`and` | 安裝來源的檢查變寬（少了 `SKILL.md` 的 skill 目錄不再被擋） |
| `oaw_mode.py:865` | `>`→`>=` | 只有 1 輪時多印「, up to 1 rounds」 |
| `oaw_status.py:545` | `or`→`and` | 狀態頁不再列出 goldfish 的結果；沒有這個欄位時丟 `TypeError` |
| `oaw_status.py:626` | `False`→`True` | **現有的呼叫路徑下不影響行為**：唯一的呼叫端明確傳入這個參數（直接呼叫函式而不傳參數時才會不同） |
| `user_install.py:837` | `or`→`and` | 安裝紀錄的檢查變寬 |
| `user_install.py:1256` | `in`→`not in` | hooks 事件的統計條件反過來 |
| `validate_skills.py:275` | `or`→`and` | 65 個字以上的 skill 名稱不再被擋 |

20 個裡，在現有呼叫路徑下不影響行為的有 1 個；其餘 19 個會改變行為，測試沒有反應。

限制：只在 Linux＋Python 3.10 上跑；只有四種邏輯小錯；只抽一次 60 個；量的是「放一個小錯會不會被發現」，不是設計上的錯會不會被發現。

## 二、CI 紅燈的盤點

範圍：GitHub Actions 的 `test` workflow，從 2.0 的第一個 commit（`31242a5`，2026-10-28）到 2026-11-16。共 36 次，26 次綠、10 次紅（清單 `ci-runs.tsv`）。10 次紅燈裡 Ubuntu 的 20 格全部是綠的；失敗都在 Windows 或 macOS 的格子（`ci-failed-jobs.tsv`）。失敗格子的原始 log 在 `ci-logs/`（檔名是 job 編號）。

| # | 日期 | run | commit | 哪一格 | log 裡看到的 | 之後的修正 |
|---|---|---|---|---|---|---|
| 1 | 10-28 | 40650841356 | `31242a5` | macOS ×2、Windows ×2 | macOS：安裝被 `Symlink/junction traversal refused: /var` 拒絕。Windows：測試通過後，閘門輸出遇到 cp1252 編不出的字元當掉 | `7801940`：`scripts/oaw.py`（路徑別名）、`scripts/harness_check.py`（輸出編碼）、對應的測試 |
| 2 | 10-30 | 41025531953 | `99a16b2` | Windows 3.10 | 多程序寫入的測試；`oaw_common._exclusive_lock` 的 `handle.flush()` 丟 `PermissionError`，寫入的程序以 1 結束 | 沒有：這一段程式在 `e7877dc`、`v2.0.1`、`996c7c7` 完全相同 |
| 3 | 10-30 | 41031844340 | `fc5fda1` | macOS ×2、Windows ×2 | `evals/skill-value/test_experiment.py`：實驗控制器的邊界稽核沒有標出一次對 gold 檔的存取 | 沒有逐一追到（複核者指出 `c2d9852` 之後改過同一個函式） |
| 4 | 11-13 | 43491981385 | `794d2d6` | macOS ×2、Windows ×2 | Windows：doctor probe 啟動不了 host、range review 判斷、建議指令的引號。macOS：建立非 UTF-8 檔名失敗 | `651d468`：`scripts/oaw.py`、`scripts/oaw_mode.py`（host 啟動；Git 換行轉換下的 range review）；另外改了兩處測試的平台寫法 |
| 5 | 11-13 | 43494428502 | `06ed481` | 同上 | 和 #4 相同的失敗 | 同 #4（這個 commit 是發佈準備，沒有包含那些修正） |
| 6 | 11-13 | 43496772666 | `651d468` | Windows 3.10 | 多個寫入者時其中一個被判成「在專案邊界外」 | `b898e4d`：`scripts/oaw_common.py`（路徑比對） |
| 7 | 11-13 | 43506889177 | `73fb8f7` | Windows 3.10 | doctor probe 在 PATH 上找不到 host | `7504eca`：`scripts/oaw.py`（Python 3.10／3.11 對帶目錄的名稱不套 PATHEXT） |
| 8 | 11-14 | 43566301228 | `cc78f1a` | Windows 3.13 | 多程序寫筆記，寫入的程序都以 0 結束，一筆不在主檔 | `d7910ce`：只改測試（把待併檔也算進去），產品沒改；issue #26 |
| 9 | 11-14 | 43614452107 | `dd91780`（push 到 `main`） | Windows 3.10 | 和 #2 同一行：`_exclusive_lock` 的 `handle.flush()` 丟 `PermissionError` | 沒有。`git diff 036a3e6 dd91780` 是空的，同一份內容在 PR 的 CI 是綠的（run 43515041144） |
| 10 | 11-14 | 43615890860 | `95dd28a`（push 到 `main`） | Windows 3.10 | 測試步驟超過 900 秒；沒有測試彙整，看不出慢在哪裡 | 沒有。同一份內容在 PR 的 CI 是綠的（run 43614976092） |

合計：

- **4 次（#1、#4、#6、#7）抓到 6 個程式問題，都在 `v2.0.1` 之前修掉。** 5 個在使用者會裝到的程式裡：安裝時的路徑別名、Git 換行轉換下的 range review、doctor probe 啟動 host、多個寫入者時的邊界判斷、PATHEXT。1 個在閘門自己（輸出編碼）。這 6 個都是在 Windows 或 macOS 的格子被抓到的；其中換行轉換那一個不限平台，開了 `core.autocrlf` 就會發生。
- **1 次（#5）是 #4 的同一批失敗再出現一次。**
- **2 次（#2、#9）停在同一行產品程式，沒有修。**
- **1 次（#3）是量測工具（實驗控制器）的問題**，不在使用者安裝的內容裡。
- **2 次（#8、#10）原因沒有確定。** #8 的判斷（筆記被分流到待併檔，測試只看主檔）是讀程式得到的，CI 上沒有直接看到。#10 只知道逾時。

#9、#10 發生在合併之後的 `main`。lead 的說明：當時沒有看這兩次的結果；2026-11-16 搜尋 records 分支、專案筆記和所有 issue，都找不到這兩個 run 的編號。

`_exclusive_lock` 那一行的成因是讀程式的推測，沒有重現；寫在 `issue-draft-windows-lock.md`。

## 三、花的時間與份量

| 項目 | 數字 | 怎麼量的 |
|---|---|---|
| 本機閘門一次 | 3 分 1.5 秒（9／9，797 個測試） | 2026-11-16 跑一次，Linux，Python 3.10.12 |
| 只跑測試一次 | 136.9 秒（單獨跑，`control-alone.jsonl`）；10 個平行時對照組 176.2–185.5 秒，全部 64 個的中位數 182.5、最長 194.1 秒 | 抽樣的沙盒 |
| CI 各格（最近三次綠燈的整格 job） | Ubuntu 102–145 秒；macOS 179–263 秒；Windows＋3.13 408–576 秒；Windows＋3.10 634、758、816 秒 | GitHub 的 job 起訖時間（run 43619957213、43787643834、43788916417） |
| Windows＋3.10 的測試步驟 | 559、740、784、851、882 秒（688–721 個測試時）；上限 900 秒 | 失敗那幾次 CI log 的 `Ran N tests in X s` |
| 程式與測試的行數 | `scripts/*.py` 23,989 行；`tests/` 下的 `.py` 16,178 行（`v2.0.1`：22,702／14,848；`v1.0.0`：1,222／0） | `git show` 逐檔 `wc -l` |
| D53 那次改動（PR #30） | 程式 +16／−7；測試 +51／−4；文件 +46／−18 | `git diff --shortstat 2b5e22a 133460d` |

## 四、複核

Codex（`gpt-6.1-sol`，reasoning high）獨立複核一次，結論 PASS WITH FIXES（`REVIEW.md`，是針對修正前那一版的意見）。它重算的數字全部一致：60 個位置的抽樣可以重現，40／60、區間、各分項、對照組都相同。它指出的問題已經照改：「抓到」的定義比程式實際做的窄、三個沒有彙整的缺原始證據、CI 的分類有幾處把推測寫成確定（#5、#8、#10 與「只在 Windows 或 macOS 才出現」）、缺陷數的算法（5 個加 1 個）、對照組的秒數寫錯。沒有做第二輪。Codex CLI 回報用量 133,676 tokens。

## 五、還沒做

- `_exclusive_lock` 的修正（草稿：`issue-draft-windows-lock.md`）。
- Windows＋Python 3.10 那一格的時間（草稿：`issue-draft-ci-time-limit.md`）。
- 漏掉的 19 個位置補測試；在 Windows、macOS 上重跑這個抽樣。
- 兩張 issue 還沒開：2026-11-16 開 issue 的動作被 owner 端的權限設定擋下，等 owner 決定。
