# OAW v1 與 OAW v2：整體效益比較計畫

日期：2026-10-30。狀態：**設計草案，尚未啟動新模型試驗**。

主比較只有 **OAW v1** 與 **OAW v2（整合 EGM）**。希望驗證新版整體至少持平，
再看是否減少誤判、節省 token，或提升跨多次工作的記憶效果。
EGM 是新版元件；單用 EGM 是否勝過其他組，不是本計畫的發布門檻。

## 1. 版本與範圍先說清楚

| 比較項目 | OAW v1 | OAW v2 |
|---|---|---|
| 產品版本 | 1.1.0 | 2.0.0 proposed，含明確啟用的 EGM 整合設定 |
| 起始程式快照 | `5df531372330f6b0e1c9a81aee0c1c45f2f283ff` | `fda0cdcb39fcc408c8cf3d36a459a35e0cafa0e3`，正式執行前再固定實作 commit |
| 回復位置 | `backup/oaw-v1.1.0-20261029` | PR #4 的固定 commit；不用浮動 branch 當實驗身份 |
| 進入點 | 實際安裝的 AGENTS → CLAUDE、既有 flat skills／wiki／記錄流程 | 實際安裝的精簡 AGENTS、原生 skill packages、專案 evidence 與完整 EGM review 元件 |
| 框架來源 | 原版 installer 與 templates | 新版 installer 與 templates；EGM 另記版本／完整 SHA／授權與檔案 hashes |

目前 PR #4 **沒有自動安裝 EGM 的產品 runtime／catalog**。正式比較前，必須完成並
固定 `OAW v2` 測試設定：EGM 如何載入、哪些任務啟用、哪些任務不啟用，以及記憶
如何保存／查詢。設定尚未落實，就不能把手動讀檔流程寫成已完成的產品整合。

本階段 EGM 來源候選為 manifest 0.1.0、
[`f0ba151b252c9abf1318d9fe857a43265d06de89`](https://github.com/google/elephant-goldfish-model/tree/f0ba151b252c9abf1318d9fe857a43265d06de89)，
Apache-2.0。下一輪使用乾淨、完整的固定版本套件，先驗證原始檔案身份。
若換上游版本，要建立新登記，保留前一輪來源；不能執行中追隨 latest。

### 舊數據的用途

[2026-10-29 試驗](../validation/egm-codex-2026-10-29.md) 的 A 組**沒有安裝 OAW**，
因此不是 OAW v1，也不能拿它的 24/24 當作 OAW v1 成績。
那一輪保留為元件整合與評分流程的探索資料。舊 spec、門檻與結果不改寫；
本計畫另立新的版本比較，不把兩輪數據混在同一張勝負表。

## 2. 主要問題與指標

| 面向 | 要回答的問題 | 主要數據 |
|---|---|---|
| 任務成果 | 新版能否至少完成同樣多的工作？ | hidden tests／驗收通過率、重大缺陷漏抓、資料保存與交付正確率 |
| 誤判 | 是否捏造缺陷、誤讀已有條件、誤把偏好當要求？ | 無根據具體指控／task、明確反駁來源的指控、誤判率、有效新發現 |
| Token／成本 | 完成同等工作花多少？ | input、cached input、output、reasoning／cache-write（有回報才記）、全樹合計、每個成功任務成本 |
| 長期記憶 | 換新對話後，舊決策是否找得到、是否知道已失效？ | 最新有效決策採用率、過期記憶服從率、來源正確率、找回成本、重做次數 |
| 操作負擔 | 是否增加無效流程？ | 額外 reviewer contexts、工具步數、重試、無必要讀寫、端到端時間 |

分開報告品質與資源，不用一個加權總分把重大漏抓或誤判抵銷掉。
不以回答篇幅、引用數量、記憶檔大小、reviewer 人數代表品質或 token。

## 3. 公平比較設定

每個 task／完整記憶軌跡都建立兩份獨立的新專案，從相同 project commit、相同
外部決策、相同使用者目標開始，再各自安裝對應 OAW 版本。

- 同一 host runtime／版本、同一模型與 effort、同一工具權限／網路／OS 環境。
  Codex 與 Claude Code 若都測，分成獨立報表，不跨 host 合併成版本效果。
- 記錄 requested model 與實際回報 model／revision；缺少時明列，不從產品名稱猜。
- 保留各版實際啟動流程。v1 的 AGENTS 本來就要求讀 CLAUDE、AI_CONTEXT 與 flat skills；
  不可漏載而把它測成「沒裝 OAW」。v2 也不能只放檔案就宣稱 EGM 已啟用。
- 機械安裝驗證與 metered pilot 要證明版本入口確實被讀取、該用的能力實際被呼叫。
  不偷偷替 v1 補一套新版檢索器，也不替 v2 手工整理額外答案。
- 同一任務採固定 seed 的配對順序，半數 v1 先跑、半數 v2 先跑；兩邊不共享輸出。
- 主比較測各版預定使用方式：EGM 不應被強制用於每個簡單任務。實際啟用策略需先固定。
  另設 compute-matched 診斷才可回答「效果來自方法，還是更多模型工作」。
- 都有相同外部事實與存取機會；不要每題都直接把相關 ADR 檔名與答案提示塞進 prompt，
  但兩邊都能從同一份專案原始資料找到它。
- 使用不透露版本／有無缺陷的代號。避免把控制案例命名為 `clean`，也不把 gold 放在工作區。

模型自身內建能力是共同條件。全域 plugin、跨專案記憶或搜尋服務若會讓兩組互通，
必須先隔離／驗證；不能只因為新對話就宣稱檔案或記憶服務已隔離。
主試驗不改使用者日常設定，不複製私人 auth／記憶資料到公開 artifacts。

## 4. 工作負載

### 4.1 單次工作：先做 12 個獨立任務家族

| 任務類型 | 家族數 | 例子與驗收 |
|---|---:|---|
| 修 bug | 4 | 重複請求、並行寫入、快取失效、路徑邊界；用隱藏測試與既有測試驗收 |
| 交付 feature | 4 | 依現有介面新增功能、處理相容性、保留客製資料；看功能／整合測試與 diff |
| 設計／PR review | 4 | 誤導性的需求、長文件跨處矛盾、合法例外、缺少實作條件；用完整來源與語義評分 |

各家族包含正例與難負例、已存在的保護、合法例外、不同嚴重程度。
固定簡單／中等／困難分布，加入真實規模文件與程式相依；不只測十幾行、明顯違反 ADR 的文件。
開發用題與 held-out 題分開。不能看完 v1／v2 的輸出後換題或改難度以製造差距。

每家族 3 個獨立重複，每版各跑：`12 × 3 × 2 = 72` 個 primary task runs。
同題的重複不是 3 個獨立任務家族；推論與不確定性以家族為單位。

### 4.2 長期記憶：以完整專案軌跡比較

每條軌跡 6 次**新的對話／工作階段**，僅保留該版本自行產生的專案持久資料。
不把上一段 transcript 或研究者寫的摘要自動交給下一段。

| 階段 | 相同外部事件／任務 | 觀察重點 |
|---|---|---|
| S1 | 提供有來源的業務限制，要求留下可追溯決策 | 實際記住什麼、寫在哪裡、是否保留來源 |
| S2 | 無關但正常的功能工作，加入干擾資料 | 記憶膨脹、無必要記錄、token 負擔 |
| S3 | 新對話要求使用 S1 的限制完成另一項工作 | 找回率、來源正確率、搜尋／讀取成本 |
| S4 | 提供明確 superseding ADR／修正外部事實 | 是否更新理解、保留歷史與有效狀態 |
| S5 | 新對話加入近似但不同 scope 的舊紀錄／引用文字 | 過期／錯 scope 記憶是否被誤當權威 |
| S6 | 再次要求交付，涉及已完成工作與已改變的輸入 | 能否避免無必要重做，同時重新驗證已變更事項 |

事實與變更事件兩邊相同；記憶檔讓各版依自身流程形成，不只替 v2 塞一條有利答案。
若要測「完全相同起始記憶」的檢索能力，另設等量 seeded-memory 診斷，不與自然形成的
長期記憶結果混在一起。可以分 20／100／500 筆的歷史負載，但負載與事實集合事先固定。

記憶指標要看**最終答案／動作與正確來源**，不只看是否出現某個關鍵字：

- 正確使用目前有效決策；已 superseded 的限制不再主導交付。
- 找回相關資料時的 precision、漏掉的重要限制、錯誤引用與自創記憶。
- 每條完整軌跡的 token、有效成果與無必要重做；記錄 append／改寫／刪除的資料量。
- 從不良 feedback 更新方法後，是否反而破壞其他任務；不能只測記憶越寫越多。

跨 session 是本計畫的主要「長期」定義。用邏輯日期模擬間隔只能證明資訊距離／
版本變更的處理，不等於真的過了 30 天。真實 7／30 天的追蹤是後續獨立層，
本次不建立排程或宣稱已驗證日曆時間衰退。

小型 pilot：`2 軌跡 × 6 sessions × 1 repeat × 2 版本 = 24 sessions`。
正式擴充候選：`4 軌跡 × 6 × 3 × 2 = 144 sessions`；以整條軌跡為比較單位，
不可把其中 6 次對話當成彼此獨立樣本。

## 5. Token、成本與時間如何量

### 量測來源

優先使用能保存每個模型回合 usage 的同一個 runner。官方 Codex 非互動文件說明
`--json` 可輸出 JSONL，`turn.completed` 範例含 input、cached input、output 與
reasoning output 欄位；這是蒐集入口，不保證目前版本已完整涵蓋子代理。
[來源](https://learn.chatgpt.com/docs/non-interactive-mode)。

本機僅做免費 help/version 檢查：Codex CLI `0.164.0-alpha.11.1` 支援 `exec --json`、
`--output-schema`、`--ephemeral`、`--ignore-user-config`。尚未發出新模型請求。
執行時要重新固定實際 binary／版本；這些旗標本身不能證明所有記憶服務已關閉。

P1 必須驗證 parent／child usage 的涵蓋與加總規則：

1. 記錄 run／thread／turn／child 身份與原始 usage，區分增量、累計與 parent aggregate。
2. 不能同時加 parent aggregate 與已包含的 child，避免重複計費。
3. 若 parent 不含 child，要收齊每個 child 的 usage；缺任一部分就不能發表全樹 token／成本比較。
4. 缺欄位用 `null` 和原因，不填 0。錯誤／重試消耗也記錄，auth 失敗不能當便宜成功樣本。
5. reasoning 是否已包含在 output、cache read/write 是否包含在 input，依該版本 schema
   與文件驗證；保留原始欄位，不把細項重複加進總量。

本 App 的 subagent 數量不等於 token 或 API requests。若只拿得到這種資訊，可以
做品質探索，token／成本欄就保持「未量測」。不自動改用外部付費 API。

### 成本報表

- 分列一般 input、cached input、cache-write（有回報才算）、output、reasoning 細項。
  記錄實際 cache 命中，不能把 fresh session 宣稱為 provider cold cache。
- 每個 task 與整條記憶軌跡分別合計；所有失敗／重試的已知資源也納入。
- 報 p50／p90、配對差值／比例與每個成功任務的總成本；不要只保留便宜成功樣本。
- 保存執行當時的模型價格、service tier／區域／cache 計費條件與來源快照。
  API 等值估算與 ChatGPT 訂閱實際費用分欄，不能互相冒充。
- 評分者使用的 token／費用另列為 evaluation overhead，不混成產品推理成本。
- 用 monotonic clock 記錄真正起迄，排隊、執行、人工等待分開；沒有可比時間就不宣稱更快。

[官方 caching 欄位與計費處理](https://developers.openai.com/api/docs/guides/prompt-caching)
與[價格表](https://developers.openai.com/api/docs/pricing)只作為欄位／價格來源。
本文件不預填一個未量測的節省數字或把訂閱配額換算成真實現金支出。

## 6. 評分與判定

先用可執行的 hidden tests／資料完整性／驗收條件，再補語義 review；關鍵字 regex
僅作篩選。引用條件是否存在、缺陷是否成立，必須對照完整原文。

兩個新的評分上下文看相同匿名成果與**完整的實際方法來源**：兩版 policy、skills、
EGM standards、引用的記憶與當時有效資料。方法文件是證據，不是新增產品要求。
source manifest／hash／必要檔案覆蓋要先過檢查；不能重演漏給標準後說標準不存在。

明確區分具體指控、條件風險、問題、方法／格式偏好。放進 uncertainties 不會自動
免除假的事實前提，也不會自動讓問題變成誤報。有效新發現允許計入。
重大漏抓／誤判分歧明確裁決並保留原判；規則不因結果好壞而改寫。

### 發布判定以 OAW v2 對 OAW v1 為主

1. 任務成功與重大缺陷偵測至少持平；每個家族與整體都列出，不用總平均藏退步。
2. 無新增重大錯誤，具體誤判與過期記憶誤用不增加。
3. 記憶軌跡的正確交付與來源品質至少持平；不能靠忘記事實或不做工作省 token。
4. 品質持平且 token／成本較低，才稱效率收益；品質持平而較貴，就明說成本增加。
   品質較好而成本較高則是 trade-off，不能包裝成全面優勝。
5. 欠缺 usage／版本身份／完整模型回合或對照資料，對應結論為 inconclusive。
   不要求所有維度都變好，但「整體至少持平」不能容許重大品質損失被較低 token 抵銷。

先報配對的 observed non-regression，附家族／軌跡層級的不確定性。
有限樣本無法證明所有任務零退步；不能用「未顯著變差」當成統計持平。
若未來要做正式 non-inferiority，需另在看結果前固定有業務意義的 margin、樣本量
與檢定方案；本草案不偷偷引入可接受的品質損失百分比。

EGM 的單獨表現只在需要定位原因時做診斷，不是新版必須額外通過的產品門檻。
若要歸因個別元件，追加「OAW v2 關閉 EGM」「OAW v2 關閉記憶檢索」等消融，
每個消融仍固定其他條件；更多 reviewer 工作量與方法效果也應分開。

## 7. 執行順序與交付資料

| 階段 | 工作 | 預期規模／是否用模型 |
|---|---|---|
| P0 | 固定版本與整合 profile、任務／軌跡、gold、來源清單、JSON schema、配對 seed | 免費靜態／合成驗證，不呼叫模型 |
| P1 | 安裝／入口與 usage schema 實測，核對 parent-child 聚合及成本上限 | 2 種任務 × 2 版 × 1 次＝4 primary runs；僅量測校準 |
| P2 | 12 家族單次任務與小型記憶 pilot | 72 task runs＋24 memory sessions，分批執行、完整報告 |
| P3 | 用未曝光 held-out 家族與較長記憶軌跡確認 | 另固定樣本／預算；可擴充至上述 144 memory sessions |
| P4 | 版本比較報告、每家族 counterexample、成本／記憶曲線、採用／保留／淘汰結論 | 評分成本分開列；決策後才談發布 |

P1 校準不拿來宣稱品質提升，也不將 4 個 runs 的成本當成可靠分布估計。
P2／P3 開始前固定總 token／費用／時間上限與停止規則；不要一開始就放行全部大樣本。
到上限保留未完成資料、標為未完成，不挑便宜成功或無限重跑直到通過。

建議 artifacts：`protocol.json`、`versions.json`、`cases/`、`trajectories/`、
`runs.jsonl`、`usage.jsonl`、`grades.jsonl`、`adjudications.jsonl`、`aggregate.json`、
`report.md`。版本、安裝 profile、模型、runner、來源檔案與價格快照均要有身份／hash。
原始 trace 留本機私有區；公開成果只保留去識別的必要資料。

報告固定用下表欄位，不再讓讀者猜組別名稱：

| 指標 | OAW v1 | OAW v2 | 配對差值／比例 | 證據完整性與限制 |
|---|---:|---:|---:|---|
| 任務成功率／重大漏抓 | 待量測 | 待量測 | 待量測 |  |
| 具體誤判／task | 待量測 | 待量測 | 待量測 |  |
| Input／cache／output／reasoning | 待量測 | 待量測 | 待量測 |  |
| 全樹 token／成功任務成本 | 待量測 | 待量測 | 待量測 |  |
| 跨 session 最新決策採用／過期誤用 | 待量測 | 待量測 | 待量測 |  |
| 完整記憶軌跡成本／重做量 | 待量測 | 待量測 | 待量測 |  |

本次交付到計畫與來源核對。沒有新實驗成績，也不因改了比較設計就重標舊數據或自動 merge。

## 8. 參考來源

- [Codex 非互動 JSONL 與 usage](https://learn.chatgpt.com/docs/non-interactive-mode)，查閱 2026-10-30。
- [OpenAI skills eval 實務](https://developers.openai.com/blog/eval-skills)，查閱 2026-10-30；採用可重現 traces／客觀檢查的方向，實驗門檻由本計畫定義。
- [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)、[pricing](https://developers.openai.com/api/docs/pricing)，查閱 2026-10-30；執行時再保存對應模型與 tier 的價格快照。
- [EGM 固定來源](https://github.com/google/elephant-goldfish-model/tree/f0ba151b252c9abf1318d9fe857a43265d06de89)、[OAW 版本來源表](../releases/2.0.0-sources.md)。
