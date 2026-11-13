# EGM cost anatomy：既有 traces 的離線拆解

**結論：小文件的主要開銷在 parent 維持、彙整累積 context；大型真實計畫的主要開銷在 implementation-readiness 階段的 subagents。這兩種成本不能用同一個比例外推。** X2 的 20 次主分析 E／cell：Claude 共 **33,413,778** logical tokens，parent **26,933,633（80.6%）**；Codex 共 **58,994,320**，parent **42,538,852（72.1%）**。大型 plan-review 的一次 Claude E 共 **18,480,203**，parent 只有 **4,603,232（24.9%）**，S9 的 codebase-details 一人可歸因用量已達 **7,785,499（42.1%）**。[來源：`summary.json`、`events.json`；X2 `PREREG.md` 的 headless uninterrupted protocol；plan-review `README.md` 的另一個歷史 protocol。]

**沒有證據支持自動啟用 EGM。** 兩格的 48 個 planted defects，其問題機制都已在 S5 初次 reviewer 回報出現；Codex 的 payouts M1 當時及最後仍只是 uncertainty。這是追溯既有 grade 的文字來源，**不是對 S5 重新評分，也不證明只跑 S5 能交付相同品質**。X2 最終 N 都抓到 47/48；E 是 Claude 48/48、Codex 47/48。小文件已在 detection ceiling，沒有空間展示一般性的品質提升。[`finding-provenance.json`；`records/v2.0.1-experiments/X2/results/main-grades-{opus,codex}.jsonl`。]

三項最小候選放在本文後段，均為 **untested hypothesis**：減少 parent 的重複載入、按任務選既有 implementation-only preset，以及保留現狀。沒有改 vendored bytes，沒有執行模型、EGM 或 regrading。大型文件研究設計見 [DESIGN.draft.md](DESIGN.draft.md)。

## 證據、樣本與計量邊界

先讀 `records/v2.0.1-experiments/X2/{PREREG,RESULT}.md`、`records/plan-review-2026-11-07/{README.md,usage.json}`，以及 `records/intake-2026-11-13-harness2/EVALUATION.md` §2、§5。沿用後者的方法：事件→最小假說→留出驗證；品質和成本分開；允許不改。這裡只使用本機已存在的證據。

短 locator 的根由操作者傳入腳本，報告不記本機絕對位置：

- `x2/`：原 scratchpad 的 X2 目錄；本次原位置可讀，無須依賴 archive 替代位置。
- `plan-review/`：同一 scratchpad 的大型計畫審查；找到 `out/egm.jsonl`、`out/codex.jsonl`、工作區與 evidence，公開 README 所說的本機完整 stream **仍存在**。
- `h1-review/`：另一個既有 scratchpad 的 `h1/review/`，只用於版本 inventory；找回 `PREREG.v2.md` 和配套程式。沒有寫入 H1、FIXCHECK 或正在執行的工作區。

解析 **49 個 E traces**：X2 44 次完成（每格 20 主分析＋events、clean 各一次）、Claude 2 次 usage-limit 中斷、兩格 orders pilot 各一次，以及大型 plan-review 一次。沒有 JSON parse failure。主表用 20 次／格，描述案、pilot、中斷另列，避免改變 X2 的分析母體。校準只有 N；未把出題、核實、grader、判定的歷史支出誤算為 E 階段。它們的 experiment-wide 支出仍見 X2 `RESULT.md`，本次不是重建整個 X2 帳本。

**logical tokens 的定義**：Claude 為 input＋cache creation＋cache reads＋output；Codex 為 input＋output（cached input 已包含在 input）。`rest` 是扣除 cache reads 的全部，不是「output」或「現金成本」。thinking／reasoning 不再額外加一次。不同供應商的 token 不能拿來作美元比較。

**Claude 的特殊限制與處理**：同一 assistant message 的 thinking、text、tool blocks 會重複 usage，依 message ID 留最後一筆。這仍不是完整用量：sync child 的最後一次 request 會在 `tool_use_result.usage`；async 的最後輸出以 `task_notification.usage.total_tokens` 修補；root 每 turn 的 `result.usage` 補回 parent 輸出。每筆修補的 line／方法在 `anatomy.json`。最後仍保留：主分析 **347,254 rest（1.04%）**，44 次完成中的 Claude 部分 **367,600**，大型 plan **113,794（0.62%）** 未歸因；cache 全部對齊。completion counter 不是整個 child 的 cumulative logical cost，不能直接取代其所有 requests。另有 parent output **557,308**（X2 主分析）、**67,563**（plan）只能分到 actor，不能分到 turn 內各 stage。缺口不按比例攤平。

**Codex**：逐 rollout 取最後的 cumulative `token_count`，加 root 和 descendants，兩格 orders pilot 與正式 E 的總額均另存核對差額。主分析與描述 E 的差額為零。父 agent 的階段是 token-count 事件與 dispatch／寫報告的區間歸因；並行工作與跨 stage 的單一 request 不能精確切開。因此是成本位置的描述，非因果消融。child 的 stage 按實際 agent path 映射；完整逐 agent 數字在 JSON，未把 `wait` 當新 reviewer。

S5＝Initial Zoom Out；S6＝Comprehension；S7＝Design／Structural／Style；S8＝Intermediate Zoom Out；S9＝Implementation Readiness／Codebase Details／Style；`final`＝報告彙整與 JSON 交付；`prep`＝入口、personas、context／semantic split 準備。Claude 額外開的 `statusline-setup`／通用 agent 留在 unknown。parent 的 phase 遇這些額外呼叫也可能暫時 unknown；沒有把這段強塞入 S7。

## 成本落在哪裡

下方附錄表列 cache／rest、stage／actor 及每次 run。幾個可檢核的解讀：

| Protocol／runs | cache reads / logical | 可歸因的主要工作 |
|---|---:|---|
| X2 Claude，20 E | 27,323,608 / 33,413,778（81.8%） | S7 22.7%、S9 26.7%、final 22.2%；parent 的 cache reads 24,344,801 |
| X2 Codex，20 E | 55,434,240 / 58,994,320（94.0%） | S7 23.7%、S9 27.5%、final 9.0%；parent 的 cache reads 41,050,112 |
| plan-review Claude，1 E | 17,134,038 / 18,480,203（92.7%） | S9 63.5%；S9 subagents 10,433,348，其中 codebase-details 7,785,499 |

這些比例由 `event_summary.py` 重算，缺口仍留在分母。**cache reads 高表示多次 input 計量，不等於 agent 發出了同樣多次 Read，也不是花掉等量未快取推理或等價金錢。** cache 單位與 permission／上下文隔離仍需保留。

具體事件：

1. **同一 context 被各 persona 重讀。** Claude X2 主分析的 `README.md`、`docs/design.md` 各有 **200 次 Read／20 runs**，每 run 各 **10 次**，即 parent 一次＋九個 reviewers 各一次；相對每 run 單次讀取，各有 **180 次**重讀。`flags` 的 `README.md`、`docs/design.md`、`src/flags.py` 都各讀十次；重複 zoom-out 與 style 各佔兩次。來源：`x2/runs/claude-a/raw/E-flags.a1.jsonl` 的 Read events、`events.json` 的逐 persona 計數。這是 fresh Goldfish 的設計成本，不能直接判為浪費。
2. **相同問題被多名 reviewer 再敘述。** `flags` 的 404／`get_global`、跨 tenant 寫入、1,200/s < 1,800/s 在 S5 已出現（raw line 83）；S7 design（212）、structural（217）、style（202）再次覆蓋其中問題；S8（268）、S9 readiness（361）、codebase（370）、style（376）繼續提到。沒有九個獨立新缺陷，這些是對相同問題的不同角度回報。來源：同一 raw trace 的 `task_notification`，`events.json` 留摘錄與 line。未逐段建立全部 reviewer overlap 矩陣，不把 regex 次數當品質分數。
3. **大型成本不是小文件成本乘 agent 數。** `plan-review/out/egm.jsonl` 的 codebase-details 累積 **7,785,499**，implementation-readiness **2,520,074**，兩者合計 **10,305,573**；完整 persona subtotals 在 `events.json`。該次指定 context 的 owner、validation、code-map、decisions 等檔案各被讀約 **9–10 次**，`catalog.py` 共 **14 次 Read**（可能是不同 range，不能叫十四次完整重讀）。所有 Goldfish 都有 context，codebase reviewer 又深入查實作，使 stage9 尤其昂貴。**不能把 X2 的 parent 比例套到這次。**
4. **不是多輪修文件再審的量測。** X2 44 次完成的 `sources_changed` 都是 false（既有 rows）。這些是固定文件的五階段 uninterrupted review；不是 review-loop 的互動修正輪數實驗。沒有新 planted mechanism 的 stage 不等於沒有新有效額外 finding；既有 grader 沒有為 stage artifacts 分別建立 labels。

## 何時已經有最後一個新 true finding

`finding-provenance.json` 為 **96 個 cell × defect 項目**各留 S5 原始 reviewer return 的短 locator、raw line、人工選的 anchor、摘錄及既有兩家 final grade。Claude 用首次 zoom-out 的 `task_notification.summary`；Codex 用 initial-zoom child rollout 的 final message。**沒有只用 run 結束後保存的 stage 文件推斷時間**，那些文件可能包含 parent 的事後 disposition。

逐項結果見附錄：16 案的 C1／C2／M1／M2 都最早可追到 S5。Claude 48 項都最後被既有 graders 算 detected；Codex 47 項 detected，payouts M1 從 S5 就有 `HoldPolicy` 未定義的說明，卻放在 uncertainty，最後仍只有 mentioned_only。Claude 的相同項在 S5 已標成 Major／factual defect＋open question。**多跑後續 stages 沒有使 Codex 這一條轉為 detected。**「最早」限於可見 reviewer 回報；看不到模型內在認知，parent 也可能更早察覺。

以 **16 個有缺陷案例／格**、S5 完成後的 S6–S9＋final stage 計量，後續支出為：

| Cell／16 E | 全額 | S6–S9＋final 已歸因下界 | 保守上界 | 約佔全額 |
|---|---:|---:|---:|---:|
| Claude | 26,506,990 | 21,054,496 | 22,390,891 | 79–84% |
| Codex | 47,634,344 | 39,333,974 | 39,333,974 | 83% |

上界＝總額扣掉已知 prep＋S5，其餘 unknown／未分 stage 的 output 都算後段；下界不含那些差額。這是 **stage boundary 下界**，S5 回報後、尚未 dispatch S6 的 parent 工作仍可能列在 S5，故實際 chronological tail 可以更多。Codex 上下界相同只表示區間歸因完整，並不代表 token-time 能精確切開單一 request。清白案沒有「最後真缺陷」，不放進此分母。對大型 plan 沒有 planted key、沒有獨立 grading，**無法算最後新 true finding 之後的比例**；不能沿用這張表。

## EGM 增加與損失了什麼

**X2 的既有評分**（20 個主分析報告／arm／cell；每格有 48 planted defects）：

| Cell | N → E detection（兩 grader 一致） | unsupported claims 總數，Opus grader | unsupported claims 總數，Codex grader | clean cases 兩 grader 都判 E 有誤報 |
|---|---|---:|---:|---|
| Claude | 47 → 48 | 4 → 9 | 4 → 33 | registry、supplier、sessions |
| Codex | 47 → 47 | 1 → 1 | 1 → 1 | registry |

來源：`quality_extract.py` → `quality.json`，完全沿用 `main-grades-{opus,codex}.jsonl`，沒有重新決定對錯。Claude 多的一項就是 payouts M1；不足以跨過 X2 預登記的品質門檻。描述案例 events 的 N 兩格都是 2/4 detected，E 都 4/4；R 也 4/4，且已因選案偏差排除主判定。不能把它重新當作 E 的留出勝利。

clean-case 負面例子（沿用 grader 的理由）：

- `registry`：E 把已接受的 fail-static outage 例外再指為 R3 重大缺陷；Claude 又把正常 20s polling＋30s deadline＝50s 的範圍擴成 outage 下最壞情況。Claude 的 E 被記 H2、H4；Codex 的 E 被記 H4。兩 grader 都否決。
- `supplier`：Claude E 把沒有列滿偏好中的 test matrix、或沒有留存 body 的猜測，說成完成標準不可驗證。Opus 記 1、Codex 記 3 unsupported。
- `sessions`：Claude E 要求另列已在 Accepted ADR-003 規定的 admission task，或對完成條件作過度字面解讀。Opus 記 3、Codex 記 4 unsupported；另有一些主張兩 grader 對是否 grounded 不一致，不能擇一當真值。

**流程成品確實更多**：E 生成 zoom-out、comprehension、critic、intermediate zoom-out、readiness、consolidated，以及統一 JSON；有分 severity、uncertainty、read verification 與 proposed checks / actual verification 的區別。這能協助作者追查推理，但 X2 沒有評結構的使用價值、修復成功率或人類節省時間。沒有看到這批 review 實際產生獨立 drift-report，不能把別的 EGM skill 的能力當成已量到的收益。

**大型 plan 的內容差異，不能當品質勝負**：公開 E 報告 **18 findings（3 blocker、13 major、2 minor）**，Codex native **15（10 major、5 minor）**；流程是不同家族、單次、無獨立評分。E 明列 TS/JS callers 尚不存在、另加 `oaw-goldfish.md` 會違反既有 gate，以及 automatic EGM 的成本／中斷契約；這些明確主張未出現在 native 的 15-item findings 中。native 則明列 singleton statistical floor 無法估 within-question variation、catalog judgment mapping 等 E 最終列表未同樣表述的項目。這只是輸出內容差異，可能有交疊或合併粒度不同，**不是新增有效缺陷數**。33 條處置中 30 採納、1 部分、2 不改也不是盲評。來源：`records/plan-review-2026-11-07/{egm,codex}/report.json`、`README.md`。

## 至多三項最小候選（全是 untested hypothesis）

| 候選 | 具體事件 → 假說 → 最小改動 | 預期節省與可量邊界 | 混雜／退回條件 |
|---|---|---|---|
| A：parent 少重複載入 | `flags` 十次讀同一 context，parent cache reads 在 X2 佔 24.345M／33.414M → parent 不必再重述每份 Goldfish context → OAW invocation 明列完整檔案 manifest，parent 只讀 upstream 要求的 intake／split 內容，完整原件仍給每個 Goldfish；已讀未變的檔案不因收報告再讀 | 期待減少 parent input 與彙整回合；trace **不能識別可刪比例**。24.345M 是 X2 parent cache 的機會上界，絕不是可實現節省；大型 parent cache 只有 4.330M。應先測，不填造一個節省百分比 | fresh context、mandatory reads 不能拿掉；少看原文可能使 parent 無法排除假警報；CLI cache 與 dispatch 行為也會變。若 upstream 要求該讀，照讀／不改 |
| B：選既有 implementation-only preset | S5 已覆蓋 X2 最終 detected mechanisms，且 plan 的 S5–S8 已歸因 5.576M → 只要 implementation readiness 的任務未必需要完整五階段 → OAW 以明確 opt-in 選 pinned entry 既有 Preset 3，保留其 split／checkpoints／S9 reviewers；不改 vendored 檔、不冒稱 full EGM | 刪去的已觀察 S5–S8 工作：Claude X2 12,283,198／20＝約 0.614M/run（36.8%）；Codex 35,654,548／20＝約 1.783M/run（60.4%）；plan 一次 5,575,547（30.2%）。這只是可移除工作量的 counterfactual proxy，實際 T 還要付不同的 prep／final | S9 是大 plan 最貴的部分；feature-only 缺陷可能漏掉，不能說同品質。full→T 同時改 scope，不能隔離「多 agent vs 多 compute」。Part 3 最多測這一個 trimmed variant |
| C：keep as is | N 已在小文件 ceiling，E 的 clean false alarms 未解，且大文件沒有可比 quality grade → 尚無足夠收益證據 → 維持 explicit opt-in，auto 維持 native fresh-context review | 相對現況節省 **0**；避免用假說宣告優化完成。不另跑 EGM 並非對 opt-in 使用者刪功能 | 大型難案可能有重要收益；本批資料無法否定。若新 bank 有有效增益，重新評估適用範圍 |

不提出「發現零新增就自動停」的產品規則：本次沒有逐 stage 獨立 grade，stage9 也可能增加有效額外 finding。也不從 raw token 推論應刪掉某個 persona；這需要消融。

## 重算、缺失與驗證

使用標準函式庫、Linux、`/usr/bin/python3`（版本與平台寫入 `anatomy.json`）。所有 Python 命令都設定 `PYTHONDONTWRITEBYTECODE=1`。操作順序和參數說明見 [REPRODUCE.md](REPRODUCE.md)。產品 source、templates、vendor、其他 records 均未修改；沒有 git commit／branch／stash。未執行產品 gate：這裡是獨立分析腳本，沒有產品或 installer 變更。

實際離線驗證：**Linux 6.8.0-136-generic x86_64、glibc 2.35、Python 3.10.12；455 項一致性檢查 PASS，核對 281 個來源 SHA-256、49 個 E traces 與 96 個 provenance items**，詳見 `validation.json`。檢查涵蓋原 rows 的外部總額、逐 bucket 加總／非負、既有 grades 對照、成本算式與本機路徑掃描；不把它當模型效果驗證。

確切缺失／限制：

- Claude stream 即使用 completion counters 修補仍有上述 rest 差額；被指向的 child `.output` transcript symlink 在抽查中是 dangling，無法靠它恢復逐 request 的完整 output。沒有把它解讀成零成本。
- Claude parent 的跨 stage turn output 無法細分，部分非 EGM agent 事件的 phase 不明。逐 stage 欄位是可歸因值，非所有 stage 的精確全額。
- Codex 只把 shell 中的文件引用當 command reference；未做完整 shell AST／Read 等價解析。**不報 Codex 與 Claude 可比的「重讀次數」**。
- 沒有逐 stage 的既有獨立 quality grade；first-found 是對 final 已評項的來源追蹤。未評估所有額外 findings 的首次出現、reviewer overlap 的完整矩陣或 false alarm 首次起源。
- 小文件每案／arm／cell 只有一次，兩格的同案不算兩份獨立文件；planted bank 經核實且強模型高 effort，N 有 ceiling。大型只有一份、兩 arm 模型家族不同，沒有人類 usefulness 或 downstream outcome labels。
- H1 v1／v3 完整文件目前未找到可獨立引用的 snapshot；v2 已找回。FIXCHECK 的三個 pre-closure 缺陷有紀錄，但本次未找回完整 pre-fix 文件／calculator 綁定快照。不能拿目前已修版測「找回已不存在的缺陷」。
- 此處沒有新實驗結果，也沒有證明 native host discovery、模型 benchmark 或 trim 的收益。

## 數字附錄（由 `render_tables.py` 生成）
### X2 Claude，20 主分析 E

單位：logical tokens。各列是已歸因值；末列差額仍計入總額。

| Stage | parent cache reads | parent rest | subagents cache reads | subagents rest |
|---|---:|---:|---:|---:|
| prep | 2,511,469 | 734,301 | 0 | 0 |
| S5 | 992,382 | 133,996 | 409,821 | 349,249 |
| S6 | 439,938 | 55,061 | 235,921 | 305,362 |
| S7 | 5,567,035 | 408,963 | 659,659 | 939,533 |
| S8 | 355,344 | 33,936 | 798,739 | 598,259 |
| S9 | 6,731,704 | 381,425 | 874,667 | 944,897 |
| final | 7,169,298 | 258,083 | 0 | 0 |
| parent_output_unallocated | 0 | 557,308 | 0 | 0 |
| unknown | 577,631 | 25,759 | 0 | 16,784 |
| 未歸因（actor 不明） | — | 347,254 | — | — |

總計：cache reads **27,323,608**；rest **6,090,170**；logical **33,413,778**。

### X2 Codex，20 主分析 E

單位：logical tokens。各列是已歸因值；末列差額仍計入總額。

| Stage | parent cache reads | parent rest | subagents cache reads | subagents rest |
|---|---:|---:|---:|---:|
| prep | 1,365,888 | 411,855 | 0 | 0 |
| S5 | 6,180,096 | 389,912 | 1,627,136 | 345,923 |
| S6 | 4,729,472 | 95,626 | 1,332,096 | 184,521 |
| S7 | 8,484,224 | 158,628 | 4,742,784 | 604,903 |
| S8 | 4,679,936 | 121,703 | 1,658,624 | 318,964 |
| S9 | 10,426,752 | 169,440 | 5,023,488 | 617,029 |
| final | 5,183,744 | 141,576 | 0 | 0 |
| 未歸因（actor 不明） | — | 0 | — | — |

總計：cache reads **55,434,240**；rest **3,560,080**；logical **58,994,320**。

### plan-review Claude E，1 次

單位：logical tokens。各列是已歸因值；末列差額仍計入總額。

| Stage | parent cache reads | parent rest | subagents cache reads | subagents rest |
|---|---:|---:|---:|---:|
| prep | 140,630 | 47,629 | 0 | 0 |
| S5 | 102,770 | 11,096 | 787,716 | 95,405 |
| S6 | 187,363 | 7,040 | 109,494 | 63,331 |
| S7 | 1,587,134 | 66,608 | 1,145,956 | 221,001 |
| S8 | 272,640 | 11,067 | 794,907 | 112,019 |
| S9 | 1,268,616 | 36,778 | 9,966,103 | 467,245 |
| final | 770,709 | 25,589 | 0 | 0 |
| parent_output_unallocated | 0 | 67,563 | 0 | 0 |
| 未歸因（actor 不明） | — | 113,794 | — | — |

總計：cache reads **17,134,038**；rest **1,346,165**；logical **18,480,203**。

### 每次完成作答的總額

原始 locator：`x2/runs/{cell}-{part}/raw/E-{case}.a{attempt}.jsonl`；`anatomy.json` 保存完整短 locator、逐 agent／stage 與 source hash。

| Case | Claude cache | Claude rest | Codex cache | Codex rest |
|---|---:|---:|---:|---:|
| auditlog | 1,064,205 | 310,875 | 2,307,456 | 135,832 |
| carts | 1,386,851 | 299,127 | 2,745,856 | 169,690 |
| clean | 1,161,656 | 230,647 | 2,243,328 | 148,613 |
| cron | 1,285,097 | 277,204 | 2,726,400 | 178,299 |
| dashboard | 1,296,627 | 334,807 | 3,028,736 | 184,813 |
| digest | 1,264,266 | 282,170 | 2,645,760 | 182,643 |
| events | 1,051,139 | 210,687 | 2,243,968 | 131,083 |
| export | 1,451,932 | 302,062 | 2,769,152 | 184,926 |
| flags | 1,282,572 | 262,290 | 3,479,936 | 207,793 |
| invites | 1,475,890 | 299,584 | 3,097,728 | 167,642 |
| invoices | 1,609,716 | 316,088 | 2,569,856 | 177,331 |
| metering | 1,334,553 | 325,657 | 3,514,496 | 178,866 |
| migrations | 1,327,372 | 335,050 | 2,872,192 | 161,068 |
| payouts | 1,291,890 | 308,270 | 2,880,384 | 188,112 |
| ratelimit | 1,347,336 | 273,856 | 2,855,424 | 165,643 |
| registry | 1,494,257 | 314,407 | 2,064,000 | 220,803 |
| resets | 1,367,769 | 281,587 | 2,387,712 | 201,087 |
| search | 1,671,307 | 292,783 | 2,581,376 | 159,382 |
| sessions | 1,454,131 | 342,050 | 2,623,744 | 163,480 |
| supplier | 1,356,996 | 313,513 | 2,919,808 | 154,592 |
| uploads | 1,377,168 | 323,140 | 2,970,368 | 164,548 |
| webhooks | 1,183,673 | 295,650 | 2,393,856 | 213,530 |

### Pilot 與未計入品質的中斷

| Cell / case / status | logical | cache | rest | 未歸因 rest |
|---|---:|---:|---:|---:|
| claude / dashboard / usage_limit | 337,643 | 230,413 | 107,230 | 2,471 |
| claude / carts / usage_limit | 1,364,955 | 1,096,205 | 268,750 | 15,775 |
| claude / orders / pilot | 1,492,115 | 1,271,392 | 220,723 | 8,052 |
| codex / orders / pilot | 2,531,919 | 2,400,128 | 131,791 | 0 |

### 各 planted defect 的最早可見 reviewer 回報

每個 ID 在兩格都是 **S5** 的初次回報；不是對中間報告另做評分。逐 ID 的原文摘錄、raw line、final 既有兩家 grade 見 `finding-provenance.json`。

| Case | IDs（Claude / Codex 都在 S5） | Claude S5 raw line | Codex S5 rollout raw line |
|---|---|---:|---:|
| auditlog | C1, C2, M1 | 78 | 32 |
| carts | C1, M1, M2 | 81 | 42 |
| cron | C1, M1, M2 | 88 | 47 |
| digest | C1, M1, M2 | 89 | 33 |
| export | C1, C2, M1 | 79 | 39 |
| flags | C1, M1, M2 | 83 | 34 |
| invites | C1, C2, M1 | 112 | 39 |
| invoices | C1, C2, M1 | 103 | 41 |
| metering | C1, C2, M1 | 101 | 55 |
| migrations | C1, C2, M1 | 108 | 43 |
| payouts | C1, C2, M1 | 111 | 40 |
| ratelimit | C1, M1, M2 | 75 | 37 |
| resets | C1, M1, M2 | 84 | 41 |
| search | C1, C2, M1 | 106 | 46 |
| uploads | C1, C2, M1 | 86 | 39 |
| webhooks | C1, M1, M2 | 67 | 32 |
