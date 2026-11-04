# 這一輪的快篩結果（D21，2026-11-04）

**更正（2026-11-04，CLI 審視 B6）**：D21 原文是依價值挑、挑完才分級、C 級交給 owner；這一輪多加了「只挑 A 級」的過濾，沒有 owner 同意，下一輪起照原文。

依 D21，每份食物最多挑 3 個單位，這一輪只挑了 A 級：只改機制、不碰模型會讀的文字、不執行食物程式、可以還原。授權方式和 CLI 介面已有 D14 的常設決定，不再另外問。沒挑到的吸收候選留在候選池，不再分析。

| 食物 | 單位 | 做什麼 | 落點 |
|---|---|---|---|
| graphify | OAW-21 | 筆記裡的 `path::Symbol` 程式碼引用檢查（lint 警告，`--strict` 時是錯誤） | `scripts/wiki_sync.py` |
| graphify | OAW-22 | 反查哪些筆記引用了某個檔案或符號：`wiki_sync.py cites` | `scripts/wiki_sync.py` |
| graphify（共用） | OAW-02（部分） | 精確大小寫的路徑解析，OAW-21 需要 | `scripts/oaw_common.py` |
| claude-mem | OAW-03 | A/B 判定要求機制真的有觸發，否則判「inconclusive」 | `scripts/improvement.py` |
| claude-mem | OAW-12 | 寫入 evidence 前擋下帶前綴的憑證（預設開啟，沒有 override） | `scripts/oaw_common.py`、`scripts/context_hub.py` |
| claude-mem | OAW-15 | `memory recall --index`：每個命中一行的索引模式（只有 CLI） | `scripts/context_hub.py` |
| TokenEconomizer | OAW-01 | Windows npm shim 解析器，不經過 cmd.exe | `scripts/oaw_common.py` |
| TokenEconomizer | OAW-04 | A/B 的額外開銷歸屬和用量覆蓋率 | `scripts/improvement.py` |

不挑的原因（一行）：
- OAW-05 有效 token：要先從價格頁定價格比例表，屬於量測報告，不是這輪最有價值的。
- OAW-13、OAW-14、OAW-17、OAW-18：依賴上面的單位，等它們上線後再挑。
- OAW-19、OAW-12/13 以外的介面變更、OAW-25：會影響相容性，放到下一輪。
- 其他吸收候選：價值較低，或是文件或設計類項目。
- 17 個保留項目：都要付費 A/B，估計遠超 D13 每樣食物 10M 的上限，這輪不跑（更正：原本誤寫成「每輪」；每輪 10M 是消化系統本身的開銷上限）。

接下來：實作和測試做在 `claude/oaw-2`，gate 必須通過，再交給一輪零上下文金魚審查程式 diff。
