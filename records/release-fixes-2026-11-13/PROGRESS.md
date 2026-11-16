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
| #17 FIXCHECK | 離線準備與 fresh review 完成；28 tests、最終 4/4 PASS。獨立 state／17M 預算／候選與 H1 來源均已綁定。Codex A/B/C 共 12 題已完成；Claude 第一題因每週 quota 停止，服務回報 18:00 台北時間重置；最新快照見 [RUN_STATUS](../v2.0.1-experiments/FIXCHECK/RUN_STATUS.md)；尚無回歸結論 |
| #18 CI | PR #16 的 base 仍為 codex/oaw-2-native-upgrade；六格 CI 尚未驗證。已向 owner 提出具體選項：新修復 branch 對 main 的 draft PR，或沿用 PR #16。等待安排確認 |
| #10／#12 文件與修整 | 在 codex/v2.0.1-release-polish 獨立工作樹已實作並驗證、待整合：locator opt-in、doctor 摘要、EGM 文件、評估雙軌 SOP。97 installer tests、最終 full gate 9/9／685 tests；code review finding closed，4/4 PASS。已推送 5af21f6；FIXCHECK 候選 c2d9852 未改 |
| #11 發佈 | VERSION 仍 2.0.0 proposed；待 FIXCHECK／CI、完整發佈 review、owner merge／tag |
| PPT 收尾 | 已依本次 review 收在「校準停止／候選未判定」；[CLOSURE](../v2.0.1-experiments/capability/CLOSURE.md) 保留逐題摘要及成本，獨立核對 4/4 PASS。沒有改題、凍結、重跑或 candidate verdict |
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
- **D46 平行工程**：owner 已指定提前做 Harness² U1 帳目／報告 adapter；隔離 branch `codex/harness2-evaluation-u1`，詳見 [實作驗收](../intake-2026-11-13-harness2/IMPLEMENTATION.md)。不更動 frozen FIXCHECK 候選，也不另開模型實驗。U2／U3 與能力試吃仍依 pilot、真實需求和既有預算規則往下。

上述為剩餘工程估算與既有預算，非本次已完成／已支出。影片、長期使用、獨立 H1 replication 等有條件工作仍保留原重啟條件。

## 文件關係

- [原始進度 review](../review-2026-11-13/REVIEW.md) 第 1–9 節保留實作前快照。
- [Harness² 評估](../intake-2026-11-13-harness2/EVALUATION.md) 保留雙目標、客觀評估與三單位 shortlist。
- 本頁記錄執行後的差異與待辦，不改寫舊實驗的判定。


## FIXCHECK 執行補充

Codex A/B/C 已完成，12/24 題共 6,802,657 logical tokens。Claude 第一題
因每週 usage limit 停止，沒有有效答案，帳本記錄 0 tokens；服務回報
2026-11-13 18:00（台北時間）重置，須屆時重新 preflight 後接同一 state。期間磁碟滿截斷一份 rollout，但完整 parent stream 與答案保留；
經獨立 4/4 review 用同一答案恢復機械評分與完整帳目，沒有重抽。
[恢復紀錄](../v2.0.1-experiments/FIXCHECK/RECOVERY.md) 保留缺失 metadata、
30,642 token 差額、完整性檢查與初審失敗；records gate 9/9、167 tests。
這個實例也補進 Harness² 評估的 U1 離線驗收案例，未增加常駐規則。
數值門檻與保留／還原處置仍等兩格完成後統一核對。

Codex 12 列的事件稽核與 90 筆證據引用雜湊已核對；完整 FIXCHECK runtime check 通過。Claude 缺 12 列，未執行數值判定，未改動候選或宣告可發佈。


## 2026-11-13 晚：Claude Code 接手後

依 [D47](../digestion-2026-11-03/ingest/DECISIONS.md) 接續。以下每一項的數字和限制都在連結的紀錄裡，這裡只列狀態。

| 項目 | 狀態 |
|---|---|
| #17 FIXCHECK | **完成。** 24/24 計分列；凍結計算器 exit 1（fail）；照預先登記的處置是還原 M1、M2、R2，保留 M3、R1，沒有擋發佈的項目。事件稽核兩格都由 Codex 做；獨立結果審查第一版判 FAIL（敘述四處），已改正並確認關閉。[RESULT](../v2.0.1-experiments/FIXCHECK/RESULT.md) |
| 處置的落實 | 還原已在本機的最終整合工作樹做好（Codex 實作、Claude 審 diff、自行重跑 Linux 閘門 9/9、685 tests），**尚未 commit**：同一批資料也量到相反方向的差異，已請 owner 決定是否偏離預先登記；沒有新決定就照登記執行 |
| #18 CI | 仍等 owner 決定 PR #16 的 base。還原後必須的三件事（最終 commit 的閘門、六格 CI、文件同步）都還沒完成 |
| Harness² U1 | 跨家族審查完成；三個設計缺口已修（`codex/harness2-evaluation-u1` adf2033，閘門 9/9、718 tests）。已用它匯出 FIXCHECK 的完整帳目 |
| Harness² U2 | 候選做好（卡片、唯讀檢查、測試；閘門 9/9、730 tests），只在本機、未推；模型會讀的文字，A/B 前不進發佈。[預先登記草稿](../v2.0.1-experiments/U2/PREREG.draft.md) |
| Harness² 官方 runtime | 只有試吃計畫，未安裝、未執行。兩道關卡等 owner：官方走 API／Vertex 計費；沒有官方的 Claude Code 執行器。[計畫草稿](../intake-2026-11-13-harness2/tasting-plan/TASTING_PLAN.draft.md) |
| #15 G5 | **完成第一步。** 三項都重判為「沒有結論」。[REJUDGE](../v2.0.1-experiments/G5/REJUDGE.md)。產品隨附的 verdict 清單尚未跟著改 |
| EGM | 既有 trace 的成本拆解與大型文件的研究設計草稿完成，未跑模型。[ANATOMY](../v2.0.1-experiments/EGM-anatomy/ANATOMY.md) |

沒有做的：版本定稿、六格 CI、完整發佈審查、merge、tag。這些都還在原來的順序上。


## 2026-11-14：owner 回覆後動工（D48）

依 [D48](../digestion-2026-11-03/ingest/DECISIONS.md)。數字的來源和限制在連結的紀錄裡。

| 項目 | 狀態 |
|---|---|
| FIXCHECK 的處置 | **定案，照預先登記。** 還原 M1、M2、R2，保留 M3、R1。`claude/oaw-2` 快轉到最終整合 `5c4e53b`，沒有新開遠端分支 |
| #18 CI | **完成條件達成。** PR #16 的 base 改成 `main`；六輪之後在 `7504eca` 六格全過（run 43510582580）。過程修掉三個 Windows 上的產品缺陷。[紀錄](../release-review-2026-11-14/README.md) |
| 版本 | `06ed481` 定為 2.0.1。2.0.0 提案版的安裝與 build 名稱可照常升級、還原，有回歸測試 |
| #11 發佈審查 | **三輪做完，最後一輪沒有擋發佈的問題。** 共修 15 個審查發現，其中 2 個會丟使用者資料。留下的開成 #21、#22、#23。[紀錄](../release-review-2026-11-14/README.md) |
| 還原後必須的三件事 | 都完成：最終 commit 的 Linux 閘門 9/9、718 tests、0 skips；六格 CI；文件同步在發佈 commit |
| 合併、tag | owner |
| 本機實驗 state | H1 與 FIXCHECK 的 state（254,542 與 49,437 個檔案，約 18.3 GB）由 Opus 5.5 搬到共用儲存區，逐檔 SHA-256 核對零差異，原位置是 symlink。空的憑證佔位檔（167 個，都是 0 bytes）沒有搬。封存後 `fixcheck.py check` 不能在共用儲存區原地跑（Git 拒絕擁有者不同的 repo）；複製回本機後通過 |
| #20 EGM 原生校準 | **跑完。形式判定：兩格都是無結論**（有了資料之後做了兩個程序變更，獨立結果審查判為事後變更）。照標籤算（描述性）：兩格都有空間，Claude 兩次合起來找到阻擋級 3/9，Codex 5/9。沒有跑 EGM，對 EGM 不下判定。等 owner 決定要不要照「無結論」收。[結果](../v2.0.1-experiments/EGM-calibration/RESULT.md) |
| Harness² U2 A/B | **試跑照 D49 跑完 18 次；沒有通過試跑關卡，成本停損條件成立，測試階段不做。** 原生三次都符合全部機械項目；A、B 兩組的 patch 逐位元組相同。對照卡沒有效果判定；照快速判定規則（D50）套現有數字是 NO。只跑了 Codex 那一格。[紀錄](../v2.0.1-experiments/U2/PILOT_STATUS.md) |
| 快速判定與 JEV（D50） | 規則第 0 版、判定工具 `scripts/fast_screen.py`、小模型判定的第一次校準、用過去紀錄做的回測都完成；工具與文件在下一版的草稿 PR #25。校準照事先的條件是「未准入」（token 條件沒過，準確度條件都過），等 owner 裁決。[校準](../v2.0.1-experiments/JEV/RESULT.md)、[回測](../v2.0.1-experiments/JEV/BACKTEST_SUMMARY.md) |
| 下一版 | owner 決定照正常的版本迭代（D50）：2.0.1 照已審查的內容發佈，評估帳本、量法總覽、快速判定進下一版（PR #25，等 #16 合併後） |

兩個 preflight 的共同發現：Codex CLI 0.167.2 的 hosted 工具（`codex_apps`）在本機網路被擋時仍能連外，原本的 runner 沒有關掉它。
已封存的 H1（254 份）與 FIXCHECK（46 份）Codex rollout 全部掃過：工具清單裡都有這組工具，沒有任何一次呼叫。

Claude 的花費（logical tokens，含快取讀取）：EGM 校準合計 7,207,968（上限 30M）；U2 是 0；JEV 校準 266,642。Codex 另計：EGM 校準最終 state 內 8,191,441；U2 合計 9,387,480。發佈審查的兩位 Opus 審查者與搬移用的 Opus agent 是工程用量，沒有逐筆計入實驗帳。


## 2026-11-15：2.0.1 發佈（D51）

依 [D51](../digestion-2026-11-03/ingest/DECISIONS.md)：owner 把 PR 類的判斷交給 lead，並決定採用 JEV。

| 項目 | 狀態 |
|---|---|
| 發佈 | **完成。** PR #16 以 merge commit 合併進 `main`（`dd91780`，2026-11-14 16:13 UTC），內容和驗證過的發佈 commit `036a3e6` 逐位元組相同；PR #4 一併顯示為已合併。annotated tag `v2.0.1` 已推上去，release 已建立 |
| 已知事項 | 一個既有的測試在 windows-latest＋Python 3.13 偶發失敗過一次（#26）。讀程式的判斷是筆記被分流到待併檔，不是遺失；CI 上沒有直接觀察到。判斷不擋發佈；測試在下一版改成分得出兩者 |
| JEV | owner 決定採用（校準的準確度條件都過，token 條件沒過，由這個決定擱置）。目前用的是 Claude Haiku 5.5、低 effort |
| 下一版 | **PR #25 已合併進 `main`（`95dd28a`，2026-11-14 16:29 UTC）**：評估帳本、量法總覽、快速判定工具與流程、#26 的測試修正，列在 CHANGELOG 的 Unreleased。合併前：Linux 閘門 9/9、785 個測試；六格 CI 在 `3107ef7` 全過（run 43614976092）；`main` 的內容與該 commit 逐位元組相同。版本號沒有動，仍是 2.0.1 |
| 還沒決定 | 已留作「可選用」的幾樣（程式碼地圖、EGM、TokenEconomizer）要不要照快速判定規則重判；owner 要求用更白話的方式再說明一次 |

## 2026-11-15（續）：D52 的落實

| 項目 | 狀態 |
|---|---|
| TokenEconomizer | **已排掉。** owner 的決定記進試吃帳本（`catalog.py decide`），出貨的 verdict 清單由帳本重新產生；當時的量測原樣保留。隨 PR #29 合併進 `main`（`2b5e22a`）：Linux 閘門 9/9、793 個測試；六格 CI 在 `806a1c1` 全過（run 43619957213） |
| owner 決定的紀錄 | 新的 `catalog.py decide`：記在試吃旁邊、可取代並保留歷史、不能把東西變成預設；清單、catalog 頁面、安裝建議都標明「owner 決定，非實測判定」 |
| EGM | 保留開關。「預設依這一次的審查判斷要不要用」還沒有實作，追蹤在 #27 |
| 程式碼地圖 | 保留。更新重畫的時機與優化追蹤在 #28 |
| 快速判定的實例 | 最小改動對照卡：NO，停在原生那一步（判定模型 19/21）。[紀錄](../v2.0.1-experiments/JEV/example-card/EXAMPLE.md)；文件加上「檢查清單只寫答案裡看得到的東西」 |
| Harness² | [整理](../intake-2026-11-13-harness2/SUMMARY.md)：評估帳本吸收了；對照卡測過不吸收；經驗索引沒有做；整套 runtime 沒有試吃 |
| issue | owner 把關閉 issue 也交給 lead。關閉 #10、#11、#12、#15、#17、#18（完成）與 #13、#20、#24（不做） |
| 還沒決定 | 快速判定要不要加「有補上、沒弄壞、但超過 1.5 倍 → 可選用並標明幾倍」 |


## 2026-11-16：D53 的落實（快速判定加上「有效但貴」）

依 [D53](../digestion-2026-11-03/ingest/DECISIONS.md)：owner 回覆「有效但貴 這邊加上」。

| 項目 | 狀態 |
|---|---|
| 規則 | 第 1 版：補上至少 2 項、沒弄壞的食物，token 超過原生 1.5 倍時不再是 NO，而是 YES（可選用），標明貴幾倍。補上不到 2 項或有弄壞仍然是 NO。[規則第 1 版](../v2.0.1-experiments/JEV/FAST_SCREEN_RULE.v1.md)；第 0 版原樣保留 |
| 沒有改的 | 預算（同一個模型家族 200 萬 logical token 或 30 分鐘，最先算）。EGM 自測那種大小的審查（每次中位數 1,137,230）三次約 340 萬，實際走快速判定會先停在預算，走不到這一條。lead 在 11-15 提問時說「規則因為價格把 EGM 判成 NO」，那是回測的說法，回測沒有套預算；D53 已記下這個補正 |
| 程式 | `fast_screen.py verdict` 多回報 `expensive`；PR #30 合併進 `main`（`996c7c7`，內容和測過的 `133460d` 相同）。Linux 閘門 9/9、797 個測試（Python 3.10.12）；六格 CI 全過（run 43787643834）。列在 CHANGELOG 的 Unreleased，版本號不變 |
| 新舊規則逐一比對 | 3 題、每題一項、兩組各三種標籤的全部 729 種組合 × 6 種 token 設定，共 4,374 種：38 種由「NO，停在 C」變成「YES，停在 C」，每一種都是補上至少 2 項、沒弄壞、超過 1.5 倍；其餘欄位與停在其他步的文字都沒有差異。lead 與 Codex 各自跑過，數字相同 |
| 舊紀錄改套第 1 版 | 24 筆裡 2 筆改判（EGM 自測、V5，都由 NO 變 YES 並標明約 28 倍、30.6 倍）；H1 與 FIXCHECK 整筆不變，只有 Codex 那一格會變。這一條是看過這些紀錄才加的，不算驗證。[差異](../v2.0.1-experiments/JEV/BACKTEST_V1_DELTA.md) |
| 獨立複核 | 一個全新 context 的 Codex（`gpt-6.1-sol`）一次：PASS；差異頁有兩項要補，已補，沒有第二輪。[報告](../v2.0.1-experiments/JEV/BACKTEST_V1_REVIEW.md)。Codex CLI 結束時顯示 tokens used 108,000（它自己的算法，沒有另外加總含快取的用量）；Claude 沒有另外開實驗 |
| 還沒做 | 規則兩個版本都還沒有用在一樣新的食物上 |

同一天 owner 另外要求：進度與版本差異要像發表會那樣，用一句核心思想加幾個數字講清楚；之後的更新如果講不出核心思想，要大檢討。
進度頁最上面改成這個寫法。三代各自的一句話與數字的來源：

| 數字 | 怎麼量的 |
|---|---|
| 開工必讀 157 行 → 20 行 | `v1.0.0` 的 `example/minimal-project/` 裡 CLAUDE.md 85 行加 AI_CONTEXT.md 72 行；`v2.0.1` 同一個範例的 AGENTS.md 20 行（CLAUDE.md 是 1 行 import）。是檔案行數，不是實際對話的 token |
| 自動測試 0 → 718 → 797 | `v1.0.0` 沒有測試檔（CI 只有冒煙檢查）；718 是 2.0.1 發佈 commit 的 Linux 閘門數字；797 是 `996c7c7` 的 |
| CI 1 格 → 6 格 | `v1.0.0` 的 workflow 是 ubuntu-latest、Python 3.10 一格；`v2.0.1` 是 3 種作業系統 × Python 3.10／3.13 |
| 腳本 2 支 → 20 支 | `scripts/` 底下的 `.py` 檔數（`v1.0.0`、`v2.0.1`） |
| 37 筆試吃與實驗 | 2026-11-14 回測時在 records 分支盤點到的筆數（同一樣食物的不同次各算一筆） |
