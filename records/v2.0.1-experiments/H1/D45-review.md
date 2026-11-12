# D45 和發佈路徑的獨立審查（Codex，一輪）

> 2026-11-12。審查者：Codex CLI，gpt-6.1-sol，reasoning high，read-only，沒有先前的脈絡。
> 審的是 `docs/plans/v2.0.1-release-path.md`（claude/oaw-2，e2c3315）和 D45 的初稿。
> 用量：input 548,351（cached 456,576）、output 7,075。
> 下面連結裡的 `OAW:` 是產品 checkout 的根目錄，`records:` 是 records checkout 的根目錄；行號是初稿的行號。

## 問了什麼

1. 紀錄裡的證據撐不撐得住五個修正（M1、M2、M3、R1、R2）和「預設不拿掉零件」？哪一項說得比證據多？
2. 複查（計畫第 4 節第 3 步）當成「修正有沒有生效」的檢查站不站得住？通過條件和限制誠不誠實？
3. 發佈路徑有沒有漏的、順序錯的、跟已記錄的決定衝突的？
4. M3 和 R2 在實作前要不要改？具體風險是什麼？
5. 停放的項目和做事規則有沒有丟掉 owner 在決定裡要的東西？

## 怎麼處理（八項都照改）

| # | 等級 | 審查者說的 | 改了什麼 |
|---|---|---|---|
| 1 | blocking | 修正後的 OAW 過不了 H1 的 freeze 核對；關掉核對又失去可追溯性 | 複查有自己的 manifest，H1 的 freeze、帳本、判定不動；逐題並排，不產生新的判定詞 |
| 2 | blocking | 通過條件證明不了五項都有生效 | 每項修正要看到自己的事件；沒觸發記「未驗到」。M1 一併改 `oaw-evidence` skill 的限制 |
| 3 | should-fix | 「沒有變差」說過頭 | 逐題列出每一筆下降和「記得變不記得」；結論只寫「符合事先定的回歸門檻」 |
| 4 | should-fix | M3 要先定兩個來源的讀寫規則 | 設計先定排序、被取代的紀錄、cursor、只在唯讀或權限錯誤時改寫；加三種回歸測試 |
| 5 | should-fix | 記憶以外的失敗、沒跑完的情況沒交代 | 加「沒過怎麼辦」表：M3、R1 擋發佈；資料沒跑完不算通過；有還原就重過 gate 和 CI |
| 6 | should-fix | 12M 算在哪一筆帳沒講清楚 | 複查是新的實驗、獨立帳本；預估約 8M，上限 17M（H1 的 O 組實測 12.76M × 1.3） |
| 7 | should-fix | 「是規則寫法，不是零件」太確定；R2 的證據是整題成本 | 改寫成「觀察支持先修；保留預設是決定，效果仍未定」；R2 標成待驗的假設並寫出風險 |
| 8 | note | 天花板規則要保留「同一把尺」；X5 的資料蒐集別丟 | 規則 2 加例外；寫明 X5 的逐筆紀錄沒做、哪些能從 git 歷史重算 |

沒有再送第二輪。複查的寫法（`FIXCHECK.md`）開跑前會另外審一次。

## 審查者的原文

先改再做。

1. **blocking — 「同一個 runner／判定程式」尚缺可執行的版本對接規則。**  
   [計畫:49–50](OAW:docs/plans/v2.0.1-release-path.md:49) 要測修正版，但原 [PREREG:105–116](records:records/v2.0.1-experiments/H1/PREREG.md:105) 凍結了 OAW、樣板、`oaw_mode.py` 等摘要；[207 行](records:records/v2.0.1-experiments/H1/PREREG.md:207) 又要求計分列共用同一份 freeze。直接換產品會被拒絕；關掉核對則破壞可追溯性。**修改：**開跑前另建 fix-check manifest，綁定修正版 O、原題庫、原 N/O 基準與評分器摘要；明定跨版本比較方式，保留原 H1 freeze、帳本與判定不動。

2. **blocking — pass conditions 不能證明五項修正都有生效。**  
   [計畫:57–59](OAW:docs/plans/v2.0.1-release-path.md:57) 的「有寫入、記得、審查零失敗、token 減少」可能在 M2 完全沒被觸發、agent 改寫其他檔案，甚至跳過審查時成立；也沒有核對 R2 的實際輪數。目前輪數與文字分別由 [review_steps():697–700](OAW:scripts/oaw_mode.py:697) 和 [DEEP_ROUNDS:713](OAW:scripts/oaw_mode.py:713) 提供。**修改：**預先登記逐項事件證據：M1 存入所需事實；M2 空 recall 後確實繼續 host retrieval；M3 經 `memory add` 寫入 fallback，後續 session 能 recall；R1 每個應審案例確實完成審查；R2 實際完成一輪 code review。未觸發的機制記「未驗到」，不能算通過。M1 同時須更新 [skill description 與本文的 explicitly requested 限制](OAW:templates/.agents/skills/oaw-evidence/SKILL.md:3)。

3. **should-fix — 「沒有變差」超過這次 check 能說的範圍。**  
   [計畫:59–62](OAW:docs/plans/v2.0.1-release-path.md:59) 允許大改動每題下降 0.10，十條需求的題可能少做到一條仍通過；記憶只比總題數，也可能掩蓋原本會記得的題變成失敗。原 [RESULT:84–87](records:records/v2.0.1-experiments/H1/RESULT.md:84) 已指出每題一次、樣本小的限制。**修改：**逐題列出所有下降與 recall 成敗轉換，明定是否容許失去一整條需求；結論改成「本次作答符合預設回歸門檻」。保留「不是獨立效果證據」是誠實的，但不能再推成已證明不退步。

4. **should-fix — M3 可保留 fallback、不搬檔，但須先定義雙來源的讀寫契約。**  
   [計畫:38](OAW:docs/plans/v2.0.1-release-path.md:38) 只寫兩邊都讀。目前 recall 依來源順序累積結果再截取，[context_hub.py:493–511](OAW:scripts/context_hub.py:493)；若舊檔先讀，舊決定可能擠掉 fallback 中的新決定。鎖檔也在目標旁建立，[oaw_common.py:200–205](OAW:scripts/oaw_common.py:200)，因此檢查目標檔可寫還不夠。**修改：**先定義跨來源排序、superseded 記錄與 cursor snapshot；fallback 僅處理明確的唯讀／權限寫入失敗，保留 confinement、credential refusal、locked atomic update。加入舊檔與 fallback 同時存在、權限恢復後交替寫入、並行寫入的無模型回歸測試。這是我會在實作前補的設計，無須先搬檔。

5. **should-fix — 非記憶項目失敗或 check 未完成時，release 分支未交代。**  
   [計畫:60](OAW:docs/plans/v2.0.1-release-path.md:60) 只定義 M1/M2 還原；[88 行](OAW:docs/plans/v2.0.1-release-path.md:88) 與 [D45:539](records:records/digestion-2026-11-03/ingest/DECISIONS.md:539) 卻泛稱失敗就還原。還原 M3/R1 會恢復已確認的產品缺陷；token 上限中止也不等於修正失敗。**修改：**分開列出「機制失敗、品質／成本門檻失敗、資料未完成」的處置；未完成不能宣告 pass。M3/R1 的缺陷仍存在時列為 release blocker；任何還原後的最終 commit 都須重新通過 gate／CI，並更新發佈限制。

6. **should-fix — 12M 的預算歸屬要寫清楚。**  
   [計畫:50](OAW:docs/plans/v2.0.1-release-path.md:50) 設 12M hard stop；[D45:519](records:records/digestion-2026-11-03/ingest/DECISIONS.md:519) 稱它在 D35 的 30M 內，但 [RESULT:55](records:records/v2.0.1-experiments/H1/RESULT.md:55) 已記 H1 花了 24.06M，而 [D35:389–394](records:records/digestion-2026-11-03/ingest/DECISIONS.md:389) 是每個 experiment 累計。**修改：**明記 D45 的 fix check 使用獨立 12M 帳本，或沿用 H1、僅剩約 5.94M；不能一面累計為同一 experiment，一面把 12M 當作仍在原上限內。

7. **should-fix — 證據支持修正方向，尚未證明唯一原因或最佳輪數。**  
   M1/M2 有行為觀察支持，M3/R1 有實際錯誤支持；但 [AUDIT:4、42–43](records:records/v2.0.1-experiments/H1/AUDIT-D40.md:4) 明定為事後描述。故 [計畫:30](OAW:docs/plans/v2.0.1-release-path.md:30)「是規則寫法，不是零件本身」說得太確定。R2 的 3.3–8.7 倍是整題成本；X2 支持的是 design review，並非 code review 輪數實驗，[AUDIT:61–63](records:records/v2.0.1-experiments/H1/AUDIT-D40.md:61)。**修改：**改寫為「觀察支持優先修規則；保留預設是 D45 的決策，效果仍未定」。我會保留 R2 一輪預設，但標為降低成本的待驗假設；具體風險是修正首輪 findings 後引入的缺陷未再被獨立審查。同步修改兩處輸出，避免仍印出三輪。

8. **note — 停放本身未丟掉 owner 選定項目；工作規則須保留公平比較例外。**  
   PPT／影片仍在路徑上；遊戲未列入不是遺漏，[D41:453–456](records:records/digestion-2026-11-03/ingest/DECISIONS.md:453) 明記未選。D45 也明確批准 G6/G7/X5 等停放。不過 [計畫:86](OAW:docs/plans/v2.0.1-release-path.md:86) 的天花板停止規則沒帶入 [D45:530–532](records:records/digestion-2026-11-03/ingest/DECISIONS.md:530) 保留的 D31 同一把尺要求。**修改：**補上「適用食品的既定比較不得為省 token 任意刪臂／刪格」；另把 X5 的資料蒐集與日後分析分開，保留 [原計畫:353](OAW:docs/plans/v2.0.1-execution.md:353) 從動工起記錄每個 commit 的要求，避免等重啟時才發現沒有資料。
