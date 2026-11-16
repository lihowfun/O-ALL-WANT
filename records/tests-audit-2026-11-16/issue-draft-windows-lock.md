標題：Windows：鎖檔還是空的時候多個程序同時寫，其中一個可能以 PermissionError 結束（CI 兩次，同一行）
標籤：bug

## 現象

CI 在 windows-latest＋Python 3.10 有兩次失敗停在同一行產品程式：`scripts/oaw_common.py` 的 `_exclusive_lock`，鎖檔在檢查當下是空的、寫入第一個位元組之後的 `handle.flush()` 丟出 `PermissionError: [Errno 13] Permission denied`，寫入的程序以 1 結束。

| 日期 | CI run | commit | 失敗的測試 | 呼叫路徑 |
|---|---|---|---|---|
| 2026-10-30 | 41025531953 | `99a16b2` | `test_wiki_sync.WikiSyncTests.test_multiprocessing_experiment_rows_all_survive` | `wiki_sync.add_experiment` → `locked_update` → `_exclusive_lock` |
| 2026-11-14 | 43614452107 | `dd91780`（v2.0.1 合併進 `main` 之後的那次 CI） | `test_context_hub.ContextHubTests.test_concurrent_primary_and_pending_writers_retain_all_entries` | `context_hub.memory_add`（寫待併檔）→ `locked_update` → `_exclusive_lock` |

第二次的同一份內容（`git diff 036a3e6 dd91780` 是空的）在 PR 的 CI 六格全過（run 43515041144）：同樣的程式有時過、有時不過。

## 知道的與推測的

- **知道（CI 紀錄）**：兩次都是 Windows＋Python 3.10；例外都從那一行丟出；`_exclusive_lock` 這一段從 `e7877dc`（2026-10-29）到現在的 `main` 沒有改過，`v2.0.1` 也是這一段。
- **推測（讀程式得到，沒有重現）**：鎖檔是空的時候，每個程序都先寫一個位元組再上鎖。兩個程序同時看到空檔時，後寫的那個可能寫到已經被對方鎖住的位元組，Windows 拒絕寫入。程式只在「上鎖」那一步等待重試，「寫第一個位元組」這一步沒有。檔案是用 append 模式開的，所以「兩邊都看到空檔」還不足以說明後寫的那一筆會落在被鎖的位元組上；log 裡沒有位移、鎖的持有者或檔案大小，這個成因要在 Windows 上實際驗證。
- **影響（照這個推測）**：Windows 上多個程序同時寫同一個檔案、而鎖檔還是空的時候，其中一個會直接報錯結束，而不是等待。不是靜默遺失：那個程序以非 0 結束。Linux 與 macOS 走 `fcntl`，不經過這個情況。

## 當時怎麼處理

lead 的說明：兩次都沒有被當成產品缺陷追查。第二次發生在 2.0.1 合併之後 `main` 的 CI，當時沒有看那次結果；records 分支、專案筆記和 issue 裡都找不到這兩個 run 的編號。2026-11-16 盤點 CI 紅燈時才把兩次對起來。

## 要做

- 「寫第一個位元組」被拒絕時，當成對方已經建好鎖檔，照常往下走上鎖的等待。
- 加一個每個平台都能跑的測試：模擬這一步被拒絕，仍然要拿得到鎖。
- Windows 上的實際行為只能靠 CI 驗證；偶發問題，一次通過不能當成修好。
