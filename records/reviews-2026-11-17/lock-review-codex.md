VERDICT: merge

- **NOTE — FileIO 與兩個平台的鎖定流程相容。** [scripts/oaw_common.py:226](scripts/oaw_common.py:226) 的無緩衝二進位開啟會回傳 `FileIO`；`seek()` 回傳位置、`fileno()` 提供底層描述元，均符合後續用途。Windows 每次鎖定及解鎖前都回到 offset 0；POSIX 仍使用 `flock`。沒有其餘程式依賴原本的緩衝物件，且無緩衝寫入失敗後不會在 seek／close 時重送資料。[CPython 3.10 實作](https://github.com/python/cpython/blob/3.10/Modules/_io/fileio.c)

- **NOTE — 廣泛吞下 PermissionError 會隱藏初始化失敗，但不會繞過互斥鎖。** [scripts/oaw_common.py:231](scripts/oaw_common.py:231) 未檢查寫入回傳值；不過只寫一個 byte，沒有正數的部分寫入問題。即使回傳零，或真正的權限錯誤遭吞下，Windows 仍須成功鎖住 `[0, 1)` 才會進入臨界區（244–253 行）。Windows 允許鎖定 EOF 以外的範圍，因此空鎖檔也能維持互斥；POSIX 的初始化 PermissionError 則會重新拋出。沒有發現因此讓兩個 writer 同時取得鎖的路徑。[Microsoft `_locking` 文件](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking)

- **NOTE — 作者的原因解讀合理，但尚未證實。** [scripts/oaw_common.py:229](scripts/oaw_common.py:229) 的大小檢查過期，本身不足以解釋失敗：CRT 還會在 append 寫入前重新 seek 到 EOF。合理的競爭時序是：B 的 **CRT 內部 seek** 得到 0，A 隨後寫入並鎖住 byte 0，B 才實際寫入而被拒絕。這符合 [Microsoft `_O_APPEND` 說明](https://learn.microsoft.com/en-us/cpp/c-runtime-library/file-constants)與 byte-range lock 行為。現有證據沒有指出更可能的原因；此修改可處理該競爭，但無法僅憑 errno 13 證明根因。

- **NOTE — 三個測試可跨平台執行，但「等待」測試只驗證分支與呼叫順序。** [tests/test_cli_resolve.py:273](tests/test_cli_resolve.py:273) 只比較 basename，不受 macOS `/var`／`/private/var` 或 Windows 父目錄短檔名影響。前兩個測試替換兩種鎖機制；第三個使用原生鎖，依序驗證檔案大小與 atomic write，未發現會在真實 Windows runner 必然失敗的操作。不過 [287 行](tests/test_cli_resolve.py:287) 的假鎖永遠成功，因此沒有測到競爭、重試或 timeout；第三個也沒有測並行初始化。

- **NOTE — CHECK_TIMEOUT 的影響不限於整套單元測試，但沒有發現正確性問題。** [scripts/harness_check.py:67](scripts/harness_check.py:67) 將它用於所有經 `run()` 啟動的 subprocess，包含其他檢查及測試中的 fixture subprocess。增加至 1800 秒會延後偵測卡住的程序，沒有改變結果判定；[225–229 行](scripts/harness_check.py:225) 仍將 timeout 例外記為失敗。

- **NOTE — 驗證範圍。** 在 Linux／Python 3.10 執行獲准的 `python3 -m unittest tests.test_cli_resolve -v`：14 個測試全部通過，耗時 0.021 秒，包含 [ExclusiveLockTests](tests/test_cli_resolve.py:260) 三項。未執行完整 gate，也未原生執行 macOS／Windows 測試或重現原始競爭。