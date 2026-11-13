# 準備階段偏離與未驗證條件

1. 首次讀取 `DESIGN.draft.md` 時輸出了整份文件，包含指定 §2–5 以外的 §1。該節有歷史 findings 摘要。這超出指定閱讀範圍。沒有讀取 KEY.json、curator 目錄、禁止的兩份 historical reports，或現行 execution plan 的附錄 B。指定的 ANATOMY 也有歷史摘要。因此不能聲稱本次準備模型完全未見歷史背景。prompts 沒有加入這些答案。新的受測 sessions 不繼承本次對話。
2. Literal workspace-only host I/O 無法直接套在 subscription CLI：host 需讀 OS runtime、credential，並寫 fresh HOME 的 accounting state。runner 對 source 採 Landlock 唯讀，允許 review_out 與該次 fresh HOME 寫入。這是明列的 host 例外。Codex shell 的額外 tool boundary 尚未由真實 CLI 驗證。real gate 保持未通過。
3. Round 1 未解條件（歷史記錄，已被 round 2 lead 決策取代）：X2-style counters 加 polling 不能單獨保證 6M 絕對 hard cap。child requests／cache usage 可能晚報。runner 有 live stop 與 inflight reservation gate，但離線沒有建立可證的 unobserved-token bound。不能將預設 0.25M reserve 當成實測上界。需補 meter/reservation 證據或由 experiment lead 明確修訂 enforcement protocol；未解決前拒絕 real launch。

U1 plain-ledger fallback 是 task 明許的選項，不是暗改 U1。其 shared grading scope 限制與本案不合；詳見 PREREG 與 ledger_manifest。

目前只有 deterministic offline tests 和 dry preparation。沒有真實 model runs、EGM、network、實際 grading、git 操作，或工作目錄以外的寫入。

## Round 2：lead 在 freeze 前的明確決策

D48 experiment lead 是 freeze、gate、grader assignment 與 custody 的負責人；repository owner 僅在 room 後決定 funding。
原第 1 項的 §1 與 ANATOMY exposure 記錄保留；本輪沒有讀 key folder、historical reports 或現行 plan Appendix B。
原第 2 項的 runtime／fresh-HOME 例外保留，改以 real preflight 驗證 tool boundary；本輪未啟動任何 model。
原第 3 項的 bound 要求由 lead 在 freeze 前修訂：6M 是 stop threshold、30M 是唯一 absolute limit；
inflight_allowance=max(1M,4×每 cell preflight live/final gap)，是 engineering allowance 而非 bound。
late reporting 超過 6M 記 deviation、停止 launches，但完整 cell 仍評分；metering 不完整或超過 30M 為 no conclusion。
Codex freeze version 更新為 0.167.2，Claude 2.1.322；freeze 後改 version 仍先記 deviation。
Astra grader 亦為 curator，對 key 熟悉是限制；仍 blind to arm/cell。另一 grader 為 Claude Fable 5.2。
lead 須在 freeze 前完成 Claude-family 非受測 primary eligibility check（有爭議者降 tier，不加 item），
並修正 key 的 ad-hoc packet digest 為 official manifest digest；保存前後 key hashes。此準備沒有讀或改 key。

新增 commands 只交給 lead 執行。preflight 的任何 isolation fail／could-not-determine 都讓 gate 維持關閉。
離線測試與 dry-run 不替代 real preflight，不是正式 study freeze 或實驗結果。

## Round 3: final lead decisions before subject data

Round 2's 0.674–0.683M Claude N proxy, 2.66–3.60M stage estimate and 6M stop are
withdrawn BEFORE any subject run: the settled eligibility check measured
3,398,755 Claude logical tokens, 359,512 without cache reads, on 16 items.
Scaling from small documents was unsupported. Stage stop is now 15M; experiment
cap stays 30M; per-N ceiling is 8M in both cells. Inflight engineering allowance,
late-reporting treatment and infrastructure retry policy remain from round 2.
Earlier 6M statements above are historical records, superseded by this section.

Eligibility is done: all 16 original primaries real, 9 blocking kept, 7 disputed
blocking moved secondary, none excluded or added. Corrected key has 30 items,
9 primary, byte hash
6d7497e90b9baf7f872bfd04c4750fee77a523e69169fd840d48df02d8e1f99e.
Preparation has not opened the key or restricted findings/curator files.

Codex completes first; Claude N1 precedes blinded batch-1 grading/reconciliation.
N2 is conditional on N1 not ceiling and the runner's 1.3× measured-cost funding
rule. M is removed; its prompt and code remain frozen, unused. Batch 2, only in
the N2 branch, repeats all three earlier reports with new IDs/shuffle and fresh
sessions; only Claude N2's new labels enter decisions. Original independent
labels supply test–retest agreement. Graders no longer reconsider eligibility.
Claude Fable grades one inline report/request, tools disabled and no packet;
only Codex Astra assesses unsupported claims, descriptively attributed to one
grader. One reconciliation round exchanges initial label/passage/reason; final
consensus alone corrects a primary label. Claude's side is one tool-free request.

Import the already-spent checker through a lead-supplied shared-cost record with
session-transcript evidence, subagents none, and measured time; no private path
is public. Codex curator usage stays separate. No new content, model calls,
network calls or actual results are authorized by this preparation. Real
preflight and the lead's final freeze remain pending; offline tests cannot
supply them. No reading of packet content is needed in round 3 beyond existing
identity verification/dry copies.

Blind review: five blockers fixed before freeze.
