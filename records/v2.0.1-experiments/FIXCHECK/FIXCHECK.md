# H1 FIXCHECK — D45 一次修正複查

狀態：準備中；尚未啟動模型。2026-11-13。
候選 OAW：`c2d9852bf8cabf13fd86a4340ab89f69044cae5a`。
依據：[D45 發佈路徑](https://github.com/lihowfun/O-ALL-WANT/blob/c2d9852bf8cabf13fd86a4340ab89f69044cae5a/docs/plans/v2.0.1-release-path.md)。

## 目的與限制

只驗 M1/M2/M3/R1/R2 修正的事件與回歸門檻。H1 已用於找缺陷，這批題不是獨立測試集；不新增「有幫助／更慘」判詞，不更新 H1 的結論。只有完整資料符合數值門檻時才寫「這次作答符合事先定的回歸門檻」。機制未觸發仍列「未驗到」，不改為通過。

H1 的 FREEZE、runner、題庫、評分器、計分列、帳本與判定全部保留。
`MANIFEST.json` 綁定來源摘要、候選 commit、安裝後 O tree、工具快照、原 O/N 計分列、本文與計算器／啟動 adapter。`BASELINES.json` 只公開比較所需的結構化數字與隱藏測試名稱，不公開 native transcripts、憑證或私有路徑。原始 rows 的整檔摘要另存於 manifest；公開摘要不是原始 rows 的替代品。

## 固定執行

- 兩格：Claude Code Opus 5.5/high；Codex CLI gpt-6.1-sol/high，沿用 H1 的原始工具快照。
- 每格同樣 12 題，只跑 O，一題一次有效作答；順序 A→B→C，題序沿用凍結檔。兩格依序執行，先 Codex 再 Claude。
- 原樣匯入 `../H1/h1_run.py`；走既有 `cmd_run` 的自訂 tag `fixcheck`、`arms=O`。題目、prompt、session carry、沙盒、mechanical grade、model、timeout、token ceiling 及基礎 infrastructure retry 規則都不變。
- 原 runner 的非 main tag 不檢查 H1 FREEZE，也不跑需 N 組資料的 C 預算投影 gate。因此 adapter 在每次執行前比對 FIXCHECK manifest，固定只 O／兩格／12 題；用獨立 17M 帳本與原本逐題預估及逐 session watchdog 限額。不能直接呼叫裸 runner 繞過 adapter。
- 獨立 state，只複製 H1 的 N/L template、工具快照、題庫、suite baseline。O 從同一個 N corpus 用候選的官方 `oaw.py init --host both` 安裝並 commit。L 僅保留來驗證原 manifest 形狀，不執行。
- 不讀當前使用者工具設定、不換新 CLI。原工具的完整樹摘要與 system tools 必須仍符合 H1。動態後端模型版本／OS shared libraries 未被完全凍結，仍屬跨時間比較限制。
- 啟動前：本文件與 manifest／scripts 已 review 並 push records；檢查 PPT／其他 experiment 的實際程序，避免 D39 重疊。stale PID 檔不當成正在執行的證據。每次 resume 重查。
- 模型 session 的工作目錄只看得到安裝後產品與題目；records、隱藏測試、FIXCHECK audit 與原答案都維持 H1 的遮蔽邊界。

## 帳本、中斷與停止

Claude 預估約 8M logical tokens，上限 **17,000,000**，`spent_before=0`、decision=D45。不得挪用 H1 剩餘額度或改 cap。每次 attempt（含失敗／中斷）都算，沿用原 runner 的 start/end/reserve 保守計帳；Codex 另報 attempts 與子 agent 成本，不加入 Claude 帳。兩格未完成皆不宣告通過。

原 runner 的 session 上限 7,200 秒，Claude session ceiling 8M；達到 session timeout／ceiling 是作答，照原規則評分，不能重抽。只有 infrastructure 未完成才能按原規則續跑，同一 state、同一 manifest、每題最多三個一般 infra 失敗；usage-limit／budget-cap 記帳並停，不當成零分。完成的 attempt 先 recover，絕不因中斷而重跑已有分數的題。

到 17M 或超過剩餘額度的下一題預估即停，報實際帳目給 owner。不能自行提高額度、換 state 或另開 tag 重試。這次複查不跑第二遍；若規則失敗按下表還原。

## 事先固定的比較與門檻

`thresholds.py` 不呼叫模型。每個 cell/unit 並排新 O、舊 O、舊 N1/N2 平均；token 使用包括 cache input 與子 agent 的 logical total。分數以 mechanical grade 的 passed/n（suite regression 則 0）重算，使用有理數避免 0.10 邊界浮點誤差。未知／重複／缺漏／來源不符資料必須拒絕或列 incomplete，不能當通過。

| 題型 | 判定 |
|---|---|
| B 記憶 | 每格至少 3/4 題 M1 確認 observed；舊 O 記得的每題不得忘記；總記得題數不減 |
| A 小改動 | 每題新 O 分數 ≥ 舊 O；每題新 O token ≤ 同格同題 (N1+N2)/2 × 1.2 |
| C 大改動 | 每題新 O 分數 ≥ 舊 O − 0.10 |
| design 成本 | 逐題新 O token < 舊 O；另報合計，不能用合計掩蓋個別未降低 |

不因平均分數掩蓋某題退步。所有分數下降、recall true→false、hidden functions/items 的 true→false 都逐題列出，即使跌幅在 0.10 內。測試是 function／item 級證據，若要指到 assertion 內部，另查本機 pytest output；不能聲稱 row 有 assertion 級 trace。

## 機制事件稽核

`EVENTS.json` 在跑前先建立空模板。每題事件狀態僅 `observed / absent / unverified`；未知不能記 observed。審查者從 raw log 配對 command/call ID、tool result、exit、寫入內容與後續讀取，記錄本機相對證據路徑、行號、SHA-256、簡短去識別說明。公開只留來源雜湊與摘要；不貼 raw transcript。不能只看 skill 名稱、agent 數量或 agent 自述。

| 修正 | observed 的要求 |
|---|---|
| M1 | B 題學到未來事實的 session 成功 `memory add`，exit 0，內容含全部所需事實；superseded 題 s1 舊值及 s2 新值都要確認。一般 B 題 s1；學習 session 沒寫即 absent |
| M2 | 空 recall 的 tool result 之後，同 session 真正查 host 記憶／歷史；沒空 recall 為 unverified。CLI 空結果引導文字的離線測試另列 |
| M3 | Codex B 題 memory add exit 0、寫入 pending，後續 session 的 recall 實際回到所需事實；沒觸發 fallback 為 unverified，權限失敗且未 fallback 為 absent |
| R1 | Codex C 四題完成 fresh-context native subagent code review，有回覆且有處理合理 findings；無失敗 nested review command。A/B 若實際觸發 required review，也同樣記錄並納入 |
| R2 | design 題分開記錄 design review 與 code review。code review 實際完成一輪；不是把設計審查算進一輪。其他題如果走 deep 也納入。token 是否下降由計算器另算 |

`EVENTS.json` 必須綁定 manifest SHA、對應 counted row 的 SHA、每筆 evidence SHA；審查完才填 observed。計算器可以檢查格式與綁定，不能代替對 raw trace 的人工／Codex 核對。未填 evidence 的 observed 不被接受。

數值門檻與事件結果分開輸出。M2 未觸發可保留 unverified 並附離線測試；M3/R1 若 observed 不足則不得宣稱驗到。缺資料時保留 pending，不能自動判定規則有害而還原。

## 結果處置

| 結果 | 處置 |
|---|---|
| M3 或 R1 confirmed absent（缺陷仍在） | 擋發佈；以離線重現修復，不重跑整批 |
| B 記憶門檻失敗 | 還原 M1+M2；README 保留原 H1 結果 |
| design 分數低於舊 O 超過 0.10 | 還原 R2 |
| design token 沒減少 | 保留 R2，明記「沒有量到省 token」 |
| A 任何門檻失敗 | 還原 M1+M2+R2 |
| 非 design C 分數下降超過 0.10 | 擋發佈並回報 owner；D45 未規定自動還原哪條，不自行推導 |
| 資料不完整、來源失配、機制待查 | 不宣告通過；按帳本續跑或補離線證據。不能重新抽作答 |
| 有還原 | 最終 commit 重新 gate 與六格 CI，文件同步 |

## 可重做的離線檢查與操作

`fixcheck.py prepare --h1-state "$OLD_H1_STATE"`：在 `H1_STATE` 指定的新目錄建立資料；`H1_OAW` 必須為候選 checkout。不讀／複製 auth，不呼叫模型。沿用 H1_HIDE/H1_RO/H1_BIN 路徑設定。

`fixcheck.py freeze`：只在沒有任何 fixcheck starts／attempts／rows 時產生 manifest、baseline 與事件模板。
審查修正結束後才 freeze 最終 script bytes，commit/push，再以 `fixcheck.py check` 驗證。
`fixcheck.py run --cell codex --klass A`：只允許已提交且存在 origin/records 的 manifest bytes，依序 A/B/C；Claude 開始前 Codex 全部題已完成。
`thresholds.py --manifest MANIFEST.json --baselines BASELINES.json --state "$H1_STATE" --events EVENTS.json`：不呼叫模型；incomplete exit 2、門檻失敗 exit 1、全部數值門檻通過 exit 0。事件缺漏另顯示 pending，exit 不能取代完整 release gate。

模型執行尚未開始；實際 review 結果、離線測試、push 身分與後續結果寫在 `VALIDATION.md`／`RESULT.md`，不回頭重寫預先門檻。
