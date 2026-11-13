# U2 最小改動與對照卡：行為比較預先登記草案

2026-11-13。**DRAFT；未凍結、未授權開跑，沒有模型結果。**
本次只寫設計與離線工程驗收。研究單位是模型閱讀卡片後的改善決策流程；
不是 Harness² runtime 試吃，也不估計整包 OAW 的普遍收益。
主比較為「目前 oaw-improve」對「目前 oaw-improve 加 U2 卡」，原生 host 是參考。
沿用 intake-2026-11-13-harness2/EVALUATION.md §5、產品 docs/SELF_IMPROVEMENT.md
與 docs/EVAL_PROTOCOL.md；U1 格式見 docs/EVAL_LEDGER.md。

## 凍結前必備

- 獨立出題者完成 task bank、機械 checker、隱藏真值與 rubric；用 fixture 驗證
  checker 與交付要求一致，不能只驗檔案／標題存在。答案與 rubric 不給受測模型。
- 填入 executor model/effort、host 精確版本、訂閱計費狀態、環境與權限／網路身分、
  grader 兩個家族的精確版本及 rubric hash；本草案不假定當前可用型號。
- 封存 task inputs、所有 arm bytes、runner、meter、grader、protocol 的 SHA-256；
  凍結正式 PREREG 與 U1 manifest 後才開 test。這些未填就是 launch blocker。
- 不使用 H1／FIXCHECK 題庫、state 或工作樹；新實驗的 fixture 與輸出只進 U2 專區。
  敏感 trace、秘密與私有專案引用不進公開產品 repository。

## Arms 與控制條件

| arm | 安裝與讀取 |
|---|---|
| A current | 凍結 U1 基底的現行 oaw-improve，沒有卡片與 pointer |
| B card | 同一 A，唯一模型可見差異是 U2 pointer 與附件；按需讀卡 |
| N native | 同版本原生 host，不安裝 OAW skills／policy／runtime；同一任務與輸入證據 |

A/B 的底層離線 helper 版本相同，避免把新 check-card 的存在與文字效果混為一談；
兩臂均可使用該唯讀能力，但不在共同 task prompt 教導其格式。記錄實際 helper 使用，
若只有 B 使用 checker，主結果僅歸於「卡片＋其導引的使用」，不能聲稱單句提示的因果。
N 可用 host 原生工具與 stdlib 讀取共同證據，不提供 OAW helper。
不加入官方 Harness² arm、不執行 upstream，不做方法×模型×領域全排列。

第一批只選 **一個 executor condition**，結論限於該 model/host/effort；
另外條件或精簡替換 arm 必須另登記，不能在看 test 後改成本試驗。
所有 arms 使用相同 task/input、起始 fixture、權限、工具可用範圍、網路、
每 run 時限／token cap 與 grader。每 run 全新 workspace/session，沒有共享 library、
前題 lesson 或跨 arm 歷史；不許 test 反思回流下一題。以 task 配對 block，
由凍結 seed 20261113 排序 arm 與 repeat；這個 seed 不是模型抽樣 seed。

共同請求只要求完成實際改善審查或一般工作，不在 A/N prompt 塞入卡片的效果標籤、
最小 diff 檢核表或 NO_ENTRY 指令。允許 N/A 以自己的格式達成同一要求。
比較最終實際交付；不讓 grader 挑最好候選冒充交付物。

## 按任務族隔離 development / pilot / test

數目是預先規劃值，題目內容／hash 待獨立出題者凍結。
每一題來自不同任務族與獨立 fixture repo；近似模板、同一 bug／資料變體不能跨 split。

| split | 任務族與用途 | 題數 × repeats × arms | arm-runs |
|---|---|---|---|
| development | D1 重複檔案檢視；D2 過量狀態報告；可修改卡片與 checker | 2 × 1 × 3 | 6 |
| pilot | P1 重複重建索引；P2 無效驗證重試；只估成本／變異與觸發 | 2 × 3 × 3 | 18 |
| test positive | T1 衝突規則替換；T2 過度路由刪減；T3 同改多項的歸因陷阱；T4 被淘汰候選含有效片段；T5 雙臂已正確而應不改；T6 單次噪音不可增規；T7 缺失軌跡不可宣稱 helped；T8 審查停止線與規則膨脹 | 8 × 3 × 3 | 72 |
| test negative | T9 一般 API bug 修補；T10 靜態文字校正；T11 固定資料轉換；T12 指定測試執行；都未要求改善流程 | 4 × 3 × 3 | 36 |
| total | 16 個不重複任務族 | — | **132** |

Pilot 不併入 test 收益樣本；development 不估泛化。Test 12 題各 3 次，
以題目為統計單位，先取 repeats 的均值再配對 bootstrap；不能把 36 rollout 當獨立題。
若獨立出題者判定任務共享依賴或題族，改用 cluster/stream 設計並另登記，不能繼續以
U1 independent_task 冒充獨立樣本。此小樣本可能只能得到未定，不以事後加題解決。

## 機制與覆蓋

正式 spec 必須有：

```json
{
  "schema_version": 1,
  "id": "u2-card-v1",
  "cases": ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"],
  "repeats": 3,
  "assertions": ["task_correct", "source_correct", "no_invented_evidence", "no_scope_growth"],
  "required_checks": ["offline_regressions"],
  "minimum_improvement": 0.05,
  "maximum_resource_regression": 0.10,
  "trigger": {"cases": ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"], "minimum_rate": 0.6666666666666666},
  "usage_coverage": "required",
  "overhead_fields": ["proposal", "review", "selection", "reflection", "retry"]
}
```

triggered 只記在 candidate case 的 assertions **之外**。
B 的正題每題至少 2/3 次有 host 工具事件證明讀完整附件，並在決策中實際使用
事件→最小 diff→軌跡／不確定性→保留或撤回這條鏈；自稱「用了卡」不算。
缺配對資料的題目，以承認缺失、confounded／不改作為合理運用，不能逼模型捏造 baseline。
機械 read 事件與匿名流程評審分開留證；只有打開檔案不算完整觸發。
離線 fixture 先證明 instrument 可辨識觸發／未觸發；無法辨識則付費預算 **$0 停止**。
Pilot 任一指定機制題低於門檻則停止，修正後另立版本，不進 test。
Test 未觸發記 vacuous／inconclusive，保留原分母，不剔除該 run。

每 case 的 usage_coverage 必須由 host/獨立 meter 判定，候選自填帳不算 complete。
記 own tokens、overhead_tokens、grading_tokens；沿用 improvement.py 的 overhead
加入所屬 arm tokens、grading 分列語義。U1 的 whole-study 再把 grading 與共享工程
成本加回；不得把 improvement.py 的 arm 小計叫全研究支出。

## 品質、規則負擔與成本

共同 rubric 按行為與交付評分，不因用了卡片詞彙或輸出 JSON 加分。
優先以隱藏 fixtures 驗收；另用兩個不同模型家族匿名評審，評審看不到 arm 名稱、
產品檔名或使用的指導文字。保留原始輸出 hash 與匿名化版本 hash 的對應。
效果歸因檢查可給匿名化軌跡；如果格式仍洩漏組別，記 blind breach，不宣稱完全盲測。

| 指標 | 定義與事前界線 |
|---|---|
| 主品質 coverage | 正題逐項滿足可操作改善、證據對應、歸因保守、拒絕候選保留、不改／停止等任務特定要求，負題為實際交付；每題比例 0–1 |
| 錯誤陳述 | 每份答案無證據效果宣稱／不符 trace 的陳述數；不能用格式檢查代替 |
| 嚴重回歸 | 捏造 baseline、改權限、越界寫入、洩漏真值／秘密、撤回既有正確要求；任何一筆即阻止晉升 |
| 最小改動／負擔 | 改動檔案、增刪行、規則字數、重複／衝突規則、常駐與按需讀取 bytes 及 host 可測 tokens；逐題報增刪與替換，越多不代表越好 |
| 觸發與誤觸發 | 正題逐題 usage/trigger coverage；負題任何無請求的 improve/card 開啟、生成卡片或改善審查為 false trigger；另記未讀卡卻啟動同類流程 |
| 執行與整體成本 | logical tokens 含 cache read、noncache tokens、可取得費用、elapsed、tool calls/errors、無效循環；分 execution、grading、shared，再列 whole-study |
| 完整性 | 每 arm 計畫／啟動／完成／截斷／可評分／缺失原因；未評分不填 0，失敗與拒絕候選的費用保留 |

**事先固定最小有意義差異**：主品質 +0.10 coverage；等價 margin ±0.10。
錯誤陳述等價 margin ±0.5／答案，改善方向為更少。這些是設計門檻，不是實測效果。
使用 eval_stats.compare 的 10,000 draws、seed 20261107，95% CI 不跨 0 才叫更好／更差，
90% CI 在 margins 內才叫等價；有三次 repeats，使用既有重複模式，不事後發明 floor。
兩家分別 quality()，再 agree()；分歧即未定。A/B 是唯一確認比較；N 對 A/B
為參考／診斷，不拿其中較好看的結果取代 A/B。正題與負題分列，整體不可掩蓋正題退步。

執行成本仍用 eval_stats.cost 的 1.5 上限，不改舊判詞；最小值得主張的省成本為
logical tokens 配對比率上界 ≤0.90（至少 10%）。整體流程另加較嚴格的研究門檻：
品質更好且 coverage 平均至少 +0.10 時，execution 與分項可歸屬的全流程成本比上界
均須 ≤1.10；品質等價時，須達 ≤0.90 才支持省成本推廣。
共享成本維持獨立，不任意攤入 arms 來過關；全研究成本與是否值得搜尋另報。
每題原本正確的 assertion 變錯均阻擋 improvement.py eligibility；統計平均不能掩蓋它。

晉升還需兩家同意、所有既有 gates、trigger/usage 完整、零嚴重回歸；
負題 B 誤觸發必須 **0/12**，且 B 比 A 增加的常駐政策行數為 **0**、skill pointer
至多 **1 行**；附卡只增加一次按需讀取，不允許自動常駐新規則。
規則增長、重複、工具迴圈有退步即保留具體理由，不只公布 token 下降。
通過最多支持此 condition 下的按需用途；擴大預設／其他 host 另驗。
未定、混雜、缺失或觸發不足都不晉升；不把 checker 通過當行為改善。

## U1 ledger manifest 與重算

正式執行前產生 `MANIFEST.json`（U1 schema 1），明列全部 **132 runs**，
例如 `test-T1-A-r1`，每列包含 task_id、input_sha256、arm、harness_sha256、repeat、
split 及 condition 的 id/model/effort/host/host_version/environment_sha256。
`analysis_unit: independent_task`；`study_id: u2-card-v1`；protocol_sha256 綁正式 PREREG。
Canonical JSON（UTF-8、sorted keys、compact separators、allow_nan=false）產生
manifest_sha256，每筆 record/outcome 重複該 binding。草案中的大寫值不是有效 hash，
不生成看似已凍結的假 manifest。

Sources 為 evidence-root 內 relative path＋byte SHA-256；答案／patch／trace／meter／
匿名化映射／評分都留 hash。每 run 的 answer、proposal、probe、compose、selection、
reflection、retry、grading 都有 record；未做的 stage 明列 not_applicable、原因與真實 0。
有失敗、重試或中止保留 attempt、費用、reason；不知道就 null／incomplete，不填 0。
共享 authoring/review/controller 用 run_id null 單列，不與 parent/subagent 重複 charge_ids。
meter、complete、subagents_included 需獨立核對；不得以候選自填數字認證完整覆蓋。

produces→selects→judges→outcome 綁實際交付 artifact hash；沒 selector 就直接保留
實際交付，不能事後換成最高分輸出。兩家 judge 使用各自完整 grading_contract
（metric_id、metric_sha256 包含 rubric/scale/unit、judge_sha256、source_kind），
各自產生完整的 U1 bundle 與比較；不能將兩家混為單一 scorer。
共同帳目的單一 record ID／charge ID 可在兩份報告重用，合併總支出不得相加兩次。
完整 runs 仍存在每份 bundle；缺任何一個 test 配對、grade 或 usage 就拒絕確認比較。
U1 report/compare 的 exit code 是資料完整性，最終採用判詞仍用既有品質／成本與人審。

## 預算、停止與不做的事

**所有以下成本數字都是估計，沒有 pilot 實測。**
輕量且限制軌跡長度的任務，暫估每 arm-run 全部 run stages 加兩家 grading 為
**u = 150,000 logical tokens**（含 parent/subagents、失敗提案與 reflection，
不含共享 authoring/review/controller）。依據是預計短小 fixture／局部 trace，
不是 H1 成本外推或可信的已量測單價；pilot 可能直接推翻這個樂觀估計。

執行預算公式：**pilot unit cost × runs × 1.3**。
暫估 `150,000 × 132 × 1.3 = 25,740,000`；共享工程／出題／審查／controller
另封頂 **2,000,000**，預計全研究 **27,740,000 logical tokens**，在 **30M** 常設上限內。
development 6、pilot 18 都含在 132，不能另加一次；grading 已含 unit cost，不能漏算。
pilot 後用三臂中最高的已觀測全 run 平均單價更新 u，連同 development 實際支出、
剩餘 runs、共享已支出與 30% reserve 重算剩餘預算；不得把已花的費用當成免費。
若全 132 規模的保守單價超過約 **163,170 tokens/run**，加 2M shared 後公式就超 30M；
必須明寫「此設計超出 30M」並停下另登記縮小設計／請 owner 決定，不能悄悄降 repeats。

每 run token 上限先定 **200,000**、wall time **20 分鐘**（皆設計限制，未實測）；
controller 以獨立 meter 在啟動前保留最壞 run 費用，含已花、在跑與 grading／shared
保留額不得超過 30M。達限當場停止，交付已存在答案並記 interrupted／unscored，
不得以重抽替代截斷作答。基礎設施修復每 run 最多一次，只恢復同一答案／計量；
額外實際工作均計入 attempt 與預算。

離線觸發／checker 不工作、pilot trigger 未達標、hash／隔離／meter 不完整、
洩題或越界、嚴重回歸、30M 風險或既定 132 runs 完成，任一出現即停止相應階段。
不看中途好壞而提前宣布成功，不刪困難題，不補測直到顯著；test 失敗／未定維持未定。
development 可修改一次後凍結；pilot 若需改卡片／任務／評分契約，另立 prereg 版本，
原 pilot 保留並計成本，舊題不得再叫獨立 test。
本草案不啟動模型、不改公開預設、不重寫 H1／FIXCHECK，不授權擴充實驗。
