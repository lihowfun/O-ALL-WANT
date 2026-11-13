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
| #17 FIXCHECK | 離線準備與 fresh review 完成；28 tests、最終 4/4 PASS。獨立 state／17M 預算／候選與 H1 來源均已綁定。Codex A/B 共 8 題已完成，C 執行中；最新快照見 [RUN_STATUS](../v2.0.1-experiments/FIXCHECK/RUN_STATUS.md)；尚無回歸結論 |
| #18 CI | PR #16 的 base 仍為 codex/oaw-2-native-upgrade；六格 CI 尚未驗證。已向 owner 提出具體選項：新修復 branch 對 main 的 draft PR，或沿用 PR #16。等待安排確認 |
| #10／#12 文件與修整 | 在 codex/v2.0.1-release-polish 獨立工作樹已實作並驗證、待整合：locator opt-in、doctor 摘要、EGM 文件、評估雙軌 SOP。97 installer tests、最終 full gate 9/9／685 tests；code review finding closed，4/4 PASS。已推送 5af21f6；FIXCHECK 候選 c2d9852 未改 |
| #11 發佈 | VERSION 仍 2.0.0 proposed；待 FIXCHECK／CI、完整發佈 review、owner merge／tag |
| PPT 收尾 | 原校準結果與本次修復分開；沒有改題、凍結或重跑 |
| G5 舊判定 | 發佈後用原資料重判；尚未執行 |
| Harness² U1／U2／U3 | 依評估規劃排在發佈後；尚未重建、試吃或宣告收益 |

FIXCHECK 的 Claude 預估約 8M、上限 17M，使用獨立帳本；不使用 H1 剩餘額度。原 H1 的 36 筆 Claude／44 筆 Codex 計分列已重新確認存在，後續 manifest 要綁定原始列摘要。複查不能產生新的整包有效判詞。

## FIXCHECK 準備完成

[預登記](../v2.0.1-experiments/FIXCHECK/FIXCHECK.md)、[manifest](../v2.0.1-experiments/FIXCHECK/MANIFEST.json)、[離線驗證與 review](../v2.0.1-experiments/FIXCHECK/VALIDATION.md) 已備妥。原 H1 36/44 rows 的整檔 SHA 與公開 72 筆 O/N1/N2 摘要均核對；12 題 mapping 與原 runner／工具快照一致。

初審抓到 functions/items 矛盾、偽造 recall、負數 session token 三個缺口；修復後 reviewer 重放原反例全部拒絕，最終 4/4 PASS。這些是計算器驗證，不是產品收益；準備完成時為 0 次 FIXCHECK 作答；之後執行進度見 RUN_STATUS，沒有新效果判定。records toolkit gate 9/9、167 tests；產品 gate 677 tests 是另一個 checkout 的先前驗證。

## 發佈修整的獨立進度

[RELEASE_POLISH.md](RELEASE_POLISH.md) 由 fresh-context agent 做實作前審查，4/4 PASS。GitHub #10 確認要求幫助型／能力型兩軌（不是拿維護者／使用者路線替代）；#12 要求 repo 外設定寫入須同意、doctor 簡潔、EGM 文件指向。

[原候選的實測](FEEDBACK_PROBE.json)：both-host 安裝會未經 opt-in 寫 locator；doctor 141 行、136 個 PASS。新工作樹的同樣隔離實測：預設與 preview 都不寫，明確選擇 apply 才寫；doctor 7 行，verbose 141 行、JSON 136 checks。兩個 host 共 14 個 EGM bridge 與四份上游文件都存在。沒有模型作答，也沒有更動 EGM vendored bytes。完整驗證與 code review 已完成：9/9 gate、685 tests、0 skips，原 review 文件 finding 已 closed。另修正舊 D19 測試全面禁用「遊戲」字詞與 D38 能力範圍的衝突，保留介面命名限制。[驗證](https://github.com/lihowfun/O-ALL-WANT/blob/5af21f61d1d30d844ead3169081532842d3fe375/docs/validation/v2.0.1-release-polish.md)。此批待 FIXCHECK 處置後整合，未發布。

## 後續順序

- **P0**：繼續已核准的一次 FIXCHECK（Claude 預估約 8M、上限 17M；Codex 另帳），每次 resume 檢查實際 PPT 程序與已推送 manifest。同時等待 CI PR 安排選擇，最終仍需六格實際結果。
- **P1**：依複查結果處理規則還原或保留，完成發佈文件／版本與完整 review；約 0.5–1 天，依賴複查與 CI。
- **P2**：發佈後 #9 接 Harness² U1 帳目／報告 adapter，估 1–2 天；U2／U3 與能力試吃依 pilot、真實需求和既有預算規則往下。

上述為剩餘工程估算與既有預算，非本次已完成／已支出。影片、長期使用、獨立 H1 replication 等有條件工作仍保留原重啟條件。

## 文件關係

- [原始進度 review](../review-2026-11-13/REVIEW.md) 第 1–9 節保留實作前快照。
- [Harness² 評估](../intake-2026-11-13-harness2/EVALUATION.md) 保留雙目標、客觀評估與三單位 shortlist。
- 本頁記錄執行後的差異與待辦，不改寫舊實驗的判定。


## FIXCHECK 執行補充

Codex A/B 已完成，8/24 題共 2,489,756 logical tokens；C 執行中，Claude
尚未開始。期間磁碟滿截斷一份 rollout，但完整 parent stream 與答案保留；
經獨立 4/4 review 用同一答案恢復機械評分與完整帳目，沒有重抽。
[恢復紀錄](../v2.0.1-experiments/FIXCHECK/RECOVERY.md) 保留缺失 metadata、
30,642 token 差額、完整性檢查與初審失敗；records gate 9/9、167 tests。
這個實例也補進 Harness² 評估的 U1 離線驗收案例，未增加常駐規則。
數值門檻與保留／還原處置仍等兩格完成後統一核對。
