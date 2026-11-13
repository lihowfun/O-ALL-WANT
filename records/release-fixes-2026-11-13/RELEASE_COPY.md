# v2.0.1 發佈文字候選

2026-11-13。**尚未套用到產品**，候選仍是 `c2d9852`。這份先完成不依賴 FIXCHECK 結果的文字；修復是否保留、2.0.1 版本與發佈結論，等一次複查及 CI 後確定。不得把本文件當成已發佈聲明。

## README：取代過期的驗證段落

目標：候選 `README.md` L165。建議文字：

> OAW's frozen H1 comparison used 12 tasks in one Python repository with Claude Code + Opus 5.5 and Codex CLI + gpt-6.1-sol. The combined verdict was inconclusive: the Codex condition met H1's benefit criteria; the Claude condition did not establish a benefit. Total logical tokens, including cache reads and subagents, were 2.58× the native mean for Claude and 1.92× for Codex, mostly from large changes. These are H1 measurements, not a general token-savings claim. [H1 results](https://github.com/lihowfun/O-ALL-WANT/blob/268429d/records/v2.0.1-experiments/H1/RESULT.md).
>
> D45 retains the defaults as a product decision while repairing the observed memory and review defects. FIXCHECK reuses the diagnostic tasks to check those repairs once; it cannot establish an independent effectiveness benefit. Native discovery and permissions remain host/version dependent. [Repair plan](docs/plans/v2.0.1-release-path.md).

FIXCHECK 完成後另加一小段：哪些修正保留、哪些事件驗到／未驗到、逐題門檻與還原處置。不把兩個 protocol 的數字合成新平均收益。

## SKILL_INTAKE：現行雙路線

保留一頁版作為入口；刪掉「使用者路線仍只是 W3 計畫」的括號，換成：

> **維護者路線**：決定 OAW 預設與正式推薦內容。以具名能力單位提出保留、替換或刪除，用同類一致的試吃、完整成本與回歸證據判定。靜態檢查只能驗證其涵蓋的結構與相容性，不能證明模型效果。
>
> **使用者路線**：使用者用 `oaw.py add / list / remove` 安裝自己選擇的技能或套件，包括尚未試吃的 PPT、遊戲、影片等能力。安裝與有效性分開記錄；未試吃就清楚標示，不因此改成 OAW 預設推薦。hooks、MCP、scripts 依 `--consent` 選擇安裝；抓取的程式不會在安裝時執行、匯入或建置。
>
> 每項內容以 receipt 管理：來源與 pin、安裝位置、host、同意的元件、試吃狀態、移除方式與備份。啟動成本沒有實測就標「未量測」。移除時遇到使用者改過的檔案，不能默默覆蓋。

依據：[user_install.py](https://github.com/lihowfun/O-ALL-WANT/blob/c2d9852bf8cabf13fd86a4340ab89f69044cae5a/scripts/user_install.py) L1–12、L990 起 plan、L1648 起 inventory；[oaw.py CLI](https://github.com/lihowfun/O-ALL-WANT/blob/c2d9852bf8cabf13fd86a4340ab89f69044cae5a/scripts/oaw.py#L1083)。

## #10 的評估雙軌（與安裝路線分開）

GitHub [#10](https://github.com/lihowfun/O-ALL-WANT/issues/10) 要求的是幫助型／能力型兩軌；前面的維護者／使用者是「誰決定安裝」，不能拿來替代這一項。

| 比較面向 | 幫助型：改善既有工作 | 能力型：新增成品能力 |
|---|---|---|
| 對照 | 原生；官方食物；skill 的 description-only；適用時加廉價做法 | 原生加相同底層工具；官方食物；description-only |
| 任務 | 同類一致、盲出題與凍結；依正式 protocol | 成品任務與機械檢查；先凍結各能力的 protocol |
| 評分 | 機械優先，否則不同家族盲評；套正式統計規則 | 成品正確性，另驗 installed-but-idle 對開場 token／一般任務的影響 |
| 可用結果 | 預設／可選用／排掉；資料不足保留無判定 | 可選用／排掉，永不進預設；沒有完整有效資料就無判定 |
| 額外成本 | 作者、作答、審查、選擇、重試與失敗都記錄 | 相同，另列工具／授權／artifact 成本 |

依據 [D38/D41/D42](https://github.com/lihowfun/O-ALL-WANT/blob/268429d/records/digestion-2026-11-03/ingest/DECISIONS.md)：D38 定義兩目的，能力型門檻是草案（成品通過數增加、閒置啟動成本不超過 2%、一般工作不變差）；具體試吃以預登記為準。D41 選定先 harness、再 PPT／影片；遊戲是可選能力範例，尚未啟動正式試吃。D42 只授權 H1 的特定天花板補題，不能概括成事後換題的通行證。OAW 自己亦需面對相同效果門檻；H1 合併仍未定。

#12 的實作驗收以 [RELEASE_POLISH.md](RELEASE_POLISH.md) 為準：repo 外 locator 必須明確 opt-in，不能僅列路徑；doctor 要實際縮短預設文字，保留完整檢查與 JSON。

## 舊原型限制：逐條改範圍

候選 `SKILL_INTAKE.md` L352–374 不再當整個產品現況。

| 舊敘述 | 發佈時的處理 |
|---|---|
| 盲審、實測、整合檢查都是規劃中 | 分開 catalog 自動引擎與維護者離線實驗；X1/X2/I16/H1 已有結果，不等於自動排程已實作 |
| 沒有 A/B runner，所以任何食物 skill 都不能吸收 | 移除全稱敘述；維護者試吃已有正式結果，使用者明確安裝不以完成試吃為前提 |
| 只裝純文字，hooks/MCP/scripts 一律不安裝 | 限定為舊 catalog absorb 路徑；使用者 add 已依 consent 管理這些元件 |
| D21 尚未用在使用者專案 | 使用者 add 有自己的 D34 流程，不宣稱它已是自動試吃／推薦引擎 |
| POSIX 未跑，只驗 Windows/Python 3.13 | 列實際平台表：Linux 修復 gate 677 tests；macOS/Windows 六格 CI 結果待補 |
| 吸收只有照原樣複製、沒有重建 | 分開各路徑的現有能力與缺口，不將歷史原型限制外推到全部產品 |
| hash-chain、排程、跨 host 補裝等其餘限制 | 尚未逐條核實，不標完成；以當前程式確認後再改 |

## 真實專案回饋三件事

1. **專案外設定寫入**：`oaw.py` L561–608 會記錄 checkout locator。文件應列 `OAW_CONFIG_HOME/checkout.json`（有指定 override 時）、Windows `%APPDATA%/oaw/checkout.json`、macOS `~/Library/Application Support/oaw/checkout.json`、Linux `$XDG_CONFIG_HOME/oaw/checkout.json`（未設時 `~/.config/oaw/checkout.json`）。不能寫入時只失去定位便利。這不是 host 個人記憶檔。
2. **EGM 文件指向**：發佈前以 path probe 核對 CLI／skill 的相對文件位置，在原 repo 與已安裝專案是否都可用。只在開發 repo 可用的須明示。此項未標完成。
3. **doctor 輸出**：分開 packaged、host discovery、實際啟用與未驗證。`doctor --probe` 會啟動一次 Claude Code，不能稱為純離線檢查。使用者呈現與 path probe 仍待驗收，不能只靠這份草稿關閉 #12。

## Harness² 的發佈邊界

[評估](../intake-2026-11-13-harness2/EVALUATION.md) 的 U1/U2/U3 仍是候選，不寫成已吸收或已省 token。後續先做 U1 帳目／重播資料機制；模型會讀的 U2/U3 依正式對照驗證。新增能力進使用者可選清單；更動預設同時檢查移除舊規則、路由衝突、整體成本與跨任務回歸。

本草稿未調整任何預算、門檻、產品版本或 H1／FIXCHECK 凍結內容。
