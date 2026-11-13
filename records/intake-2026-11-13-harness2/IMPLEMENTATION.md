# Harness² U1 方法吸收實作與交接

2026-11-13。依 D46，owner 指定現在開始吸收評估方法，提前 U1 工程；本頁接續
[EVALUATION](EVALUATION.md) 的來源研究，並保留研究當時與現在實作狀態的區別。

## 已交付

隔離 branch `codex/harness2-evaluation-u1`，基底 release-polish `5af21f6`。
產品 commit：[`26e019277e0db8a3d9edad5aa56f10dbe0fe583c`](https://github.com/lihowfun/O-ALL-WANT/commit/26e019277e0db8a3d9edad5aa56f10dbe0fe583c)。

- `scripts/eval_ledger.py`：stdlib、人工按需呼叫；JSON／Markdown 帳目報表與既有 `eval_stats` 比較橋接。
- `scripts/eval_ledger_fixcheck.py`：唯讀匯入固定 FIXCHECK；不呼叫 runner／grader／thresholds、不修寫帳本、不重抽答案。
- 顯式保留 planned 分母、failed/retry/selection/reflection 成本、未知欄位、研究與 grading 成本；不存在的資料不填零。
- manifest／source／run／artifact／judge 身分與 paired test set 檢查；比較範圍只含單一 metric/judge 與 execution tokens，不自動給 D32／absorb 判詞。
- 29 個 synthetic tests、完整 gate inventory、使用契約與驗收文件。未增啟動規則、預設 skill、runtime 依賴或 installer payload。

不是「merge 更多規則」：這層用於把之後的 EGM、code map、token 優化或候選 skill
放到相同且可查核的評估條件。能力清單與既有使用者安裝／移除管理不受此次工程改動。

## 審查與測試

設計 fresh-context 初審 3/4，補上 metric／rubric／judge／source contract 後 4/4，於動碼前閉合。
原 reviewer 也確認後續欄位澄清仍在核准範圍內。

一次獨立 code review 找到兩個缺陷：已評分卻將 grading 標 N/A 能誤報完整；unit bank
總 hash 驗證沒有逐題綁定實際內容。兩項已修正並加反例，原 reviewer **2/2 closed**，
獨立重跑 29 tests 通過。沒有藏掉初審失敗，也沒有以原先 712 tests 全過代替修正。

修正後完整 gate：**9/9 checks，714 tests，0 skips**。平台 Linux／Python 3.10.20；不等於跨平台 CI。
產品 [使用文件](https://github.com/lihowfun/O-ALL-WANT/blob/26e019277e0db8a3d9edad5aa56f10dbe0fe583c/docs/EVAL_LEDGER.md)、[驗收紀錄](https://github.com/lihowfun/O-ALL-WANT/blob/26e019277e0db8a3d9edad5aa56f10dbe0fe583c/docs/validation/harness2-u1.md) 和 [gate](https://github.com/lihowfun/O-ALL-WANT/blob/26e019277e0db8a3d9edad5aa56f10dbe0fe583c/docs/validation/harness2-u1-gate.json) 保存測試與來源 hash。

## 實際資料驗收

JSON／Markdown 各兩次均一致，exit 2（valid incomplete），19 個輸入路徑的 hash／存在狀態
前後未變。保存的公開報表不含私有路徑或 native transcripts。

- planned **24**，started **13**，completed／scored **12**，missing **12**。
- Codex observed **6,802,657 logical tokens**；Claude quota not-run **1**，usage **0**、outstanding reserve **0**。
- 完整研究總額仍為 **null／unknown**；工程、審查、其他階段與 usage 完整性未量測，不冒充總成本。
- 恢復題仍為 **428,278**，elapsed **null**；沒有採用截斷紀錄的 397,636，也沒有重評答案。
- manifest `d1bec84b95004f7d27f9adf6a1acc07ae53be41f45fcbb50943c334f1ea5b80e`，candidate `c2d9852bf8cabf13fd86a4340ab89f69044cae5a` 維持固定。

這是既有帳目的 importer 驗收，**不是 Harness²／OAW 效益試驗**。新增實驗作答呼叫 0；
controller／設計／code reviewer 的模型成本未獨立量測，不能說此次工程成本是 0。

## CC 接手

1. 原 Claude FIXCHECK 仍在 18:00 後依原 state／guarded adapter 接 A→B→C，17M cap，
   候選 checkout 必須是 `OAW-release-fixes @ c2d9852`。不要因 U1 提前而換候選。
2. 若要看當前帳目，在 **U1 checkout** 用 `eval_ledger.py fixcheck --manifest FILE --state DIR`
   唯讀匯入。exit 2 是預期的 incomplete；不得將此報告取代原 thresholds／保留還原處置。
3. 下一個新評估使用 U1 contract，先凍結 task／arm／condition／judge，再記錄完整階段成本與
   artifact。以真實觀測補足未量測欄位，不能倒填歷史工程成本。
4. U2（最小規則改動／取代刪除）與 U3（檢索／chronological transfer）仍需各自 pilot／比較；
   能力路線的 PPT／遊戲／影片仍依使用者需求與既有 intake 管理。這次不提前新模型試驗。

release 整合、CI routing owner 選擇、六格實際 CI、最終 review／merge／tag 仍待原流程。
新 U1 分支並未更改這些狀態。估計接上下一份新評估契約約 0.5–1 天工程，依其原始計量格式；
模型預算須依該實驗 pilot 另算。這是估計，不是此次已支出。
