# 保留 skills 是否值得：同任務開關實驗

2026-10-30，協議 `oaw-retained-skill-value-v1`。目標是決定留下、選配或淘汰，
不是預設要證明 V2 贏。**V2 本身已包含 EGM。**

這是新登記的聚焦實驗，使用整合 source `341b45014afd37f54f16e254452f9586e9d1b04f`，
EGM manifest 0.1.0／`f0ba151b252c9abf1318d9fe857a43265d06de89`（Apache-2.0）。
不把歷史 9ae pilot 重標為本次結果，也不宣稱完成先前尚未 ready 的 110-call 擴充驗收。

## 每個 skill 都有三個對照

| 條件 | 能用什麼 | 要分辨的效果 |
|---|---|---|
| EGM | 完整固定上游＋正常檔案、搜尋、Python 工具 | 直接 EGM 的基線 |
| V2 skill off | 同版 V2，該 skill 入口關閉，但其 helper 仍可正常使用 | 工具／平台本身有沒有價值 |
| V2 skill on | 同版 V2，啟用該 skill；其他 policy／helpers／資料與 off 相同 | 多讀這份 SKILL 指引是否有增益 |

Wiki／improve 兩組都保留 default evidence；只切換當前被測入口。
Evidence 的 off 配方只有七個 EGM 入口，on 才加入 evidence。
兩邊的 helper 都實際安裝：不能故意讓 off 缺工具，然後宣稱 skill 贏。
EGM 可用普通工具做同一件事，不限制它建立持久文件或自行檢查證據。
這是 source-loaded controlled test；native discovery 與 OS read isolation 不在此宣稱通過。

## 新任務與固定母體

| Skill | 兩個預先固定的 case families | 每條件呼叫 |
|---|---|---:|
| evidence | 500筆混 scope／舊版／長行／假指令中的來源檢索與交接；S2遇到 superseding ADR 的更新交接 | 2 families × 2 repeats × 2 fresh sessions＝8 |
| wiki | raw-to-topic 更新、相對連結與人工註解保留；另一 topic 不得誤改、S2更新既有結論 | 2 × 2 × 2＝8 |
| improve | 表面整體進步卻有逐 assertion 退步；先前 eligible 證據被改動。各含正向 control，正負例位置交換 | 2 × 2 × 1＝4 |

三條件合計 **60 candidate calls**。另有 **12 independent grader calls**，每個 case family 兩名；
重要判定不一致才請第三人裁決，最多6次。各 call 都是新的 context，不繼承主聊天或其他組答案。
金標、controller 與其他 trial 不進候選 workspace；相同 family 的原始 facts／updates／prompt 相同。

Evidence 逐欄驗 scope、數值、revision、prompt-only ticket 及接手前 provenance。
Wiki 同時看實際產物的現行結論、有效連結、註解與 topic 邊界；不用 OAW 格式當成品質。
Improve 兩個 proposals 一好一壞，拒絕全部也不能過；輸入資源數是 synthetic fixture，
不能混進本次實際 token 用量。只審核 eligible/reject，不自動接受或套用使用者 policy。

先算 typed fields 與 artifact checks，再由兩位不知道 mapping 的 graders 查實際來源支持、
頁面語義、接手前證據與具體誤判；method風格仍可能削弱盲法，會列限制。
Wiki重建冪等另有離線工具測試，不能靠模型自述就當成已測的模型效果。

## 看結果之前就固定淘汰規則

1. **品質增益**：on 在兩個 families 都比 off、EGM 多完成正確且有來源支持的任務，
   配對沒有任何退步、無來源指控或資料／policy 破壞。
2. **效率增益**：三條件品質都完整通過，on 在每個 family 都比兩個基線至少少15% logical token；
   不能拿某個 family 省很多，抵銷另一個退步。
3. **只有 helper 有益**：off 比 EGM 好，但 on 沒比 off 好，優先保留工具，把冗餘 skill 指引改為選配。
4. **沒有觀察到增益**：同分、成本高或不滿足門檻，不再宣稱這個 skill 值得預設載入；
   建議移出預設／保留實驗性選配。小樣本或 ceiling 不能證明它在所有任務都無用。
5. **發生回歸**：新 critical error、具體誤判、source 破壞或未授權套用，阻擋 promotion，
   建議修復後另立新 cohort，或淘汰入口；不改舊輸出讓它變過。

不直接刪使用者已安裝或客製的 skill。若結果支持 repo 改預設，正常 migration 仍須保留 backup／conflicts。
三個 module 各自下結論，不用綜合分掩蓋弱項。

## 執行、用量與停止條件

Codex 固定 gpt-6.1-sol／medium；provider revision 不可見就標 unknown。
最多2個模型 process，單次300秒、每phase派送窗7200秒；candidate 20M logical／250k output、
grading/adjudication 5M logical／100k output。最多兩個在途請求可能超額，如實列出。
不自動 retry；缺真實 IO、metering、越界或 source/control 漂移就停，保留失敗原件及已知用量。
使用已登入的 ChatGPT/Codex；child env 移除 API-key 路徑，不呼叫外部付費 API 或 Claude F1。

Codex logical＝input（已含cached）＋output，reasoning 不重複加。輸出 input/cache/output 拆分。
Candidate、失敗、IO/canary、grader、adjudication 分開報。此處 controller 是 Python，
不是另一個模型；不拿平台不可見開銷、美元或訂閱百分比來猜測。

可重現工具在 `evals/skill-value/`。在 source checkout 執行：

```text
python -m unittest discover -s evals/skill-value -p test_*.py -v
python evals/skill-value/experiment.py prepare --repo . --out PRIVATE_NEW_COHORT
python evals/skill-value/experiment.py run --out PRIVATE_NEW_COHORT --codex CODEX_EXE
python evals/skill-value/experiment.py packets --out PRIVATE_NEW_COHORT
python evals/skill-value/experiment.py grade --out PRIVATE_NEW_COHORT --codex CODEX_EXE
python evals/skill-value/summarize.py --out PRIVATE_NEW_COHORT --write PRIVATE_NEW_COHORT/summary.json
```

prepare／packets／summarize 與 unittest 不呼叫模型；run／grade 使用使用者已授權的 Codex quota。
Source、fixtures、gold、判定規則與 runner 在看到候選輸出前存 commit 和 hashes。
原始 traces、完整本機路徑、snapshots 和其他私有執行資料只留工作區，不散布到公開 Git。

Claude 後續依同份 fixture／gold／endpoints 與母體，另建自己的 cohort 和 host adapter，
固定單一模型／effort、記錄唯一必要的 host path／guidance 替換；不能用這個 Codex-only run 冒充 Claude。
先驗 hashes 和完整 metering 能力，再執行；actor 結果、controller用量與表格分開，不跨 tokenizer 排名。

## 結果表

Codex 及 Claude 各交一張，不把尚未完成當成0錯誤。

準備／啟動紀錄：v1–v3 為免費準備版本，未派模型。v4 的兩個 CLI invocations
在 argument parsing 就因 `--sandbox` 與 `--approve-for-me` 互斥而拒絕，events 為空；
未達模型呼叫，不作品質或效率樣本。原始記錄保留，不重試原 trial；改用新 cohort。
修正只移除重複 sandbox flag；`--approve-for-me` 本身仍使用 workspace-write＋automatic review，
沒有放寬權限或 bypass。Facts、gold、60-call母體與保留門檻保持不變。

| Skill | EGM 正確且有來源支持 | V2 off | V2 on | 三條件token與完整性 | 保留／選配／淘汰判定 |
|---|---|---|---|---|---|
| evidence | 未測 | 未測 | 未測 | 未彙總 | 待實測 |
| wiki | 未測 | 未測 | 未測 | 未彙總 | 待實測 |
| improve | 未測 | 未測 | 未測 | 未彙總 | 待實測 |

完整報告先列這張表及白話結論，後面在同檔列逐 family/repeat/session、typed cells、
artifact failures、來源／裁決、實際 usage 與限制。不以「有跑完」或「skill很多」當增量價值。
