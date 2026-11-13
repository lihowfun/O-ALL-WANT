| ID | Verdict | 證據 |
|---|---|---|
| R2-01 | closed | 重跑無 `---` 的 LRU→ARC 情境；show、兩種 recall、status、bootstrap 均先列 ARC，舊筆記保留。 |
| R2-02 | closed | 原排序及 `73fb8f7` 發出的兩種 recall cursor 均被拒絕；新版 cursor 可正常續頁，來源變更後也會失效。 |
| R2-03 / C2-01 | closed | 使用 Python 3.10 真實 `shutil`／`os.path` 語意及 round 2 平台模型；僅有 `claude.cmd`、同時有 `claude`＋`claude.cmd`，新版均選到 `.cmd`，並排除隱含 cwd 搜尋。未在實體 Windows 執行。 |
| C2-03 | closed | 重跑手寫時間標頭與十月 pending 筆記情境；新版主檔的十一月筆記不再整批排在 pending 後面。 |

新增 findings：**無符合本輪門檻的 blocker**。

原始情境均在暫存副本以 `/usr/bin/python3` 3.10.12 離線執行。32 組記憶檔情境涵蓋前言、首筆前文字、僅標題、空檔、CRLF，以及主檔／pending，未發現遺失、重複或新增錯序；115 個相關測試通過。

link test 在 Python 3.10／3.12 對注入的實際越界 `os.stat`、`os.path.exists` 存取仍會失敗。`Path.exists` 的涵蓋缺口在 `73fb8f7`／3.10 已存在，不列為新增回歸。

完整 gate 為 8/9：718 tests，30 failures 均包含 Git `dubious ownership` 拒絕，16 errors 為沙盒禁止 loopback socket。抽查原版亦重現相同 Git 失敗，不能宣稱完整 gate 通過。

RELEASE: not blocked by this review