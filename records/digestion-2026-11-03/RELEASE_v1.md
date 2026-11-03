# 版本頁：`claude/oaw-2` 第一輪 D21 吸收（2026-11-04）

依 D21，這是給 owner 的唯一一頁：多了什麼、和預設比、怎麼還原。全部是 A 級（只改機制、不碰模型會讀的文字、不執行食物程式），依 D17 用靜態證據出貨。release 目標照 D14：進還沒打 tag 的 `2.0.0`。

## 多了什麼

| 單位 | 食物 | 做什麼 | 對使用者的影響 |
|---|---|---|---|
| OAW-12 | claude-mem | 寫進 evidence（`memory add`、`lesson`、`annotate`）前，檢查 22 種帶前綴的憑證格式；命中就整筆不寫、結束碼 1，訊息不重複秘密 | **預設行為改變**：含憑證的筆記會被拒絕，沒有略過的旗標，要改用佔位字 |
| OAW-15 | claude-mem | `memory recall --index`：每個命中一行（來源、行號、日期、標題、包含完整命中的片段） | 新選項；預設輸出逐位元組不變 |
| OAW-03 | claude-mem | A/B 規格可宣告 `trigger`：機制沒真的觸發，判定就是 inconclusive，接受前的重新驗證也一樣 | 只影響有宣告的新規格 |
| OAW-21 | graphify | `lint` 檢查筆記裡 `` `path::Symbol` `` 的程式碼引用：檔案或符號不存在、大小寫不符就警告 | 預設只警告；**`lint --strict` 會因此失敗** |
| OAW-22 | graphify | `wiki_sync.py cites <path[::Symbol]>`：反查哪些筆記引用了這個檔案或符號（唯讀、可 `--json`） | 新指令 |
| OAW-02（部分） | graphify 等 | 引用路徑的精確大小寫解析和 Windows 路徑正規化 | 內部 helper |
| OAW-01 | TokenEconomizer | Windows 上把 npm shim 解析成 node＋腳本直接執行，不經過 cmd.exe；其他批次檔一律拒絕 | 內部 helper，還沒有 runner 使用 |
| OAW-04 | TokenEconomizer | A/B 的額外開銷算進造成它的那一組；用量沒完整記錄就不下「省 token」的結論 | 只影響有宣告的新規格 |

授權：照 D14，Apache-2.0 署名加修改說明，見 `THIRD_PARTY_NOTICES.md` 和 `LICENSES/Apache-2.0.txt`。graphify 的單位沒有複製程式碼。

## 和預設比

- 預設是 `codex/oaw-2-native-upgrade`（PR #4）的 2.0.0。
- **沒有任何實測的增益**，一律寫「齊平，未宣稱改善」；「和單吃食物比：未測」。
- 唯一的數字是測試資料的大小：30 筆、每筆約 1.5 KB 的記憶，`--index` 輸出 3,350 bytes，預設輸出 31,079 bytes。這是測試資料的量測，不是模型效果。
- 測試：Windows 上 359 個（POSIX 最低 337 個）。

## 怎麼還原

每一組是 `claude/oaw-2` 上的一個 merge commit，可以單獨拿掉：

| 組 | merge commit | 還原 |
|---|---|---|
| claude-mem 憑證＋索引（OAW-12、OAW-15） | `d6b0b67` | `git revert -m 1 d6b0b67` |
| graphify 引用（OAW-02、OAW-21、OAW-22） | `445df06` | `git revert -m 1 445df06` |
| 量測（OAW-01、OAW-03、OAW-04） | `d09a14d` | `git revert -m 1 d09a14d` |

整輪回到吸收前：`claude/oaw-2` 的 `790177e`。

## 還沒做完的

- **零上下文金魚審查程式 diff**：執行包在 `goldfish-diff/`，等 owner 在這台登入 Claude Code CLI 後由 Claude 執行。Elephant 處理發現；只有 Elephant 不接受的 blocker 才交給 owner。
- **PR**：金魚審完後開 Draft PR，base 用 `codex/oaw-2-native-upgrade`（PR #4 merge 後改成 `main`）。owner merge 就是這一版的核准。
