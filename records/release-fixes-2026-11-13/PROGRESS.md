# 執行進度：D45 修復與 Harness² 計畫

更新：2026-11-13。整體目標仍進行中，沒有縮減成「只寫文件」或「只建立 branch」。

## 已完成的第一批

- 從 `claude/oaw-2@359e6e3` 建立獨立 worktree `OAW-release-fixes`。
- 新 branch：`codex/v2.0.1-release-fixes`。
- 產品 commit：`c2d9852bf8cabf13fd86a4340ab89f69044cae5a`。
- M1／M2：同步保存政策與 evidence skill；空 recall 提供 host 記憶／歷史接續指引。
- M3：僅 EACCES／EPERM／EROFS 轉寫 `.oaw/memory-pending.md`；兩來源按逐筆時間排序，保留歷史、來源行號、原子寫入與 cursor 失效。
- R1／R2：Codex 同家族使用原生 fresh-context subagent，保留明確跨家族選擇；standard／deep code review 一輪。
- #18：修正 literal path audit 的 symlink／canonical 別名與同前綴 sibling 漏判。
- 文件、template 與生成的 example 同步；ROADMAP 明記已實作但發佈條件尚未完成。

產品設計與驗證：
[設計](https://github.com/lihowfun/O-ALL-WANT/blob/c2d9852bf8cabf13fd86a4340ab89f69044cae5a/docs/plans/v2.0.1-release-fixes.md)、
[驗證報告](https://github.com/lihowfun/O-ALL-WANT/blob/c2d9852bf8cabf13fd86a4340ab89f69044cae5a/docs/validation/v2.0.1-release-fixes.md)、
[gate 原始結果及來源雜湊](https://github.com/lihowfun/O-ALL-WANT/blob/c2d9852bf8cabf13fd86a4340ab89f69044cae5a/docs/validation/v2.0.1-release-fixes-gate.json)。

## 驗證結果

| 檢查 | 結果／範圍 |
|---|---|
| 實作前 fresh-context 設計審查 | 4/4 PASS |
| 最終完整 gate | 9/9，677 tests，0 skips；Linux／Python 3.10.20 |
| retained-skill 離線測試 | 31/31 |
| three-way 離線測試 | 14/14 |
| Codex 原生 sandbox 探針 | CLI 0.167.2；.agents 寫入 EROFS，pending 保存成功，另一命令 recall 成功，原筆記未變；模型呼叫 0 |
| 原始碼與結果一致 | 10 個受核對來源 SHA-256 與 gate 紀錄相同 |
| 原本的 OAW-v2 | working tree 乾淨，HEAD 不變 |
| H1 freeze | SHA-256 仍為 `4943bf2ce02c9c9383828d201f59198f951c0446e263a5b05ba381095fa3a4d8` |

第一次 code review 為 2/4 PASS、2/4 FAIL，發現三個問題：Unicode casefold 合併不同目錄、指回 workspace 的 symlink 被誤報、skill 指引覆蓋明確跨家族選擇。三項均修正；原 reviewer 重跑兩個原始 path probe 並核對文字，全部 **closed**。沒有抹掉第一輪失敗。既有 wiki lint 的 22 項 soft warnings 仍在。

## 尚未完成的要求

| 項目 | 現況與下一個可驗證交付 |
|---|---|
| #17 FIXCHECK | 尚未啟動模型作答。先建立 FIXCHECK.md、獨立 manifest／帳本與門檻計算 script，綁定上述候選 commit，fresh review 後才跑 |
| #18 CI | PR #16 即時核對仍為 draft，base 為 codex/oaw-2-native-upgrade；六格 CI 尚未驗證。新 branch 不自動替換原 PR head |
| #10／#12 文件 | 本批只同步變更行為；發佈主張、使用者安裝 SOP 舊敘述與其餘回饋待後續整理 |
| #11 發佈 | VERSION 仍 2.0.0 proposed；待 FIXCHECK／CI、完整發佈 review、owner merge／tag |
| PPT 收尾 | 原校準結果與本次修復分開；沒有改題、凍結或重跑 |
| G5 舊判定 | 發佈後用原資料重判；尚未執行 |
| Harness² U1／U2／U3 | 依評估規劃排在發佈後；尚未重建、試吃或宣告收益 |

FIXCHECK 的 Claude 預估約 8M、上限 17M，使用獨立帳本；不使用 H1 剩餘額度。原 H1 的 36 筆 Claude／44 筆 Codex 計分列已重新確認存在，後續 manifest 要綁定原始列摘要。複查不能產生新的整包有效判詞。

## 後續順序

- **P0**：FIXCHECK 設計、離線計算器與資料身分驗證，約 0.5–1 天；依賴本次候選 commit 與既有 H1 資料。並行解決 CI 的 PR 安排，最終以六格實際結果為準。
- **P1**：依複查結果處理規則還原或保留，完成發佈文件／版本與完整 review；約 0.5–1 天，依賴複查與 CI。
- **P2**：發佈後 #9 接 Harness² U1 帳目／報告 adapter，估 1–2 天；U2／U3 與能力試吃依 pilot、真實需求和既有預算規則往下。

上述為剩餘工程估算與既有預算，非本次已完成／已支出。影片、長期使用、獨立 H1 replication 等有條件工作仍保留原重啟條件。

## 文件關係

- [原始進度 review](../review-2026-11-13/REVIEW.md) 第 1–9 節保留實作前快照。
- [Harness² 評估](../intake-2026-11-13-harness2/EVALUATION.md) 保留雙目標、客觀評估與三單位 shortlist。
- 本頁記錄執行後的差異與待辦，不改寫舊實驗的判定。
