| ID | 判定 | 證據 |
|---|---|---|
| R1-01 | closed | 重跑 hooks → all → remove：舊版回傳 `partial` 且原始備份遭覆蓋；新版回復原始 bytes；中途失敗回復與分開移除也通過。 |
| R1-02 | closed | 重跑 capture 與 lock 之間完成 migration 的原始情境：新版拒絕 restore，保留後來的自訂政策；三個 caller 的新增檢查及正常往返均通過。 |
| R1-03 | closed | 已移除自動登記與暫存目錄豁免說法，改連結至 `--remember-checkout` 同意規則。 |
| R1-04 | closed | 兩份 README 均改為「沒有預期外的 skips」，並連結實際平台例外規則。 |
| R1-05 | closed | 中文 README 的 H1 結果、成本及 FIXCHECK 處置與本地 pinned records 相符。 |
| C1-01 | closed | 實際呼叫 `memory_add`，有／無分隔線兩種情境均解析成兩筆；兩個 wiki commands 的日期與缺失路徑歸屬正確。 |
| C1-02 | partly closed | 原始 UTC+8、有分隔線情境已修正；無分隔線來源仍會先顯示被取代的舊決策，見 R2-01。 |
| C1-03 | closed | Linux 未 mock 的 `0444` 情境直接寫 pending，主檔 bytes 不變，沒有暫存檔。 |
| C1-04 | closed | Python 3.10／Windows 路徑模型中，extended drive 與 UNC 的 `..` 逃逸均被拒絕；未在 Windows 主機執行。 |
| C1-05 | partly closed | 已阻止隱含 cwd lookup，但正常 Windows `PATHEXT` lookup 被破壞，見 R2-03。 |
| C1-06 | closed | 真實 symlink base 情境現在輸出 `.agents/memory.md`，沒有 `../`。 |

18 個新增測試均在 `b898e4d` 出現預期失敗、在 `73fb8f7` 通過。完整 Linux gate 為 8/9：716 tests、0 skips；剩下 16 errors 全是沙盒禁止建立 loopback sockets，不能宣稱完整 gate 通過。

**R2-01 — blocker — 無分隔線記憶檔把取代決策排在舊決策後面**

位置：[scripts/context_hub.py:344](scripts/context_hub.py:344)。

既有 `.agents/memory.md` 沒有 `---`，包含 `2026-10-01` 的「cache needle: use LRU」。執行 `memory add "[DECISION] cache needle: LRU superseded, use ARC"` 後，writer 仍將新筆記追加到底部，新 reader 卻固定保留檔案順序。因此 `memory show --last 1` 只顯示 LRU，recall 也先列 LRU；status／bootstrap 沿用同一錯誤順序。舊版會先列 ARC。

**已重現**：Linux、`/usr/bin/python3`，base／fixed 對照。新增排序測試只涵蓋有分隔線情境。**最小修正**：讓無分隔線來源也維持最新優先，新增時插在第一筆之前，並兼容既有追加順序；補上此情境測試。

**R2-02 — blocker — 排序改變卻未使舊 recall cursor 失效，造成漏筆與重複**

位置：[scripts/context_hub.py:344](scripts/context_hub.py:344)，snapshot marker 仍是第 521 行的 `memory-sources-v2`。

檔案依序放入 timestamp `2026-11-13T23:30:00.000000+00:00` 的 ARC，以及 date-only `2026-11-14` 的 LRU。舊版以 `--limit 1` 回傳 LRU 與 cursor；保持記憶檔不變，換新版續讀。新版接受 cursor，再次回傳 LRU，並表示沒有下一頁：ARC 被整段分頁流程漏掉。

**已重現**：一般 recall 與 `--index` 都如此。現有 cursor 測試只檢查來源內容變更。**最小修正**：更新排序語意的 snapshot marker，使舊 cursor 被拒絕並要求重新查詢；補跨版本 cursor 測試。

**R2-03 — blocker — Windows／Python 3.10 找不到正常安裝的 Claude launcher**

位置：[scripts/oaw.py:856](scripts/oaw.py:856)。

新版逐一呼叫 `shutil.which(absolute_directory / "claude")`。Python 3.10 的 `which()` 遇到帶目錄的參數會直接檢查該檔名，完全跳過 `PATHEXT`。因此可信的絕對 PATH 目錄即使包含 `claude.cmd` 或 `claude.exe`，`doctor --probe` 仍回報 `not found in absolute PATH directories`。

**已重現於 Windows 分支模型**：使用 `/usr/bin/python3` 3.10.12 的原版 `shutil.which`，僅模擬平台與分隔符；舊版解析到 fixture `claude.CMD`，新版找不到。未在 Windows 主機執行。回傳 launcher 的 mock 測試掩蓋了這項語意。**最小修正**：在每個絕對 PATH 目錄明確展開 `PATHEXT`，再檢查完整檔名，保留 cwd 排除規則。

RELEASE: blocked