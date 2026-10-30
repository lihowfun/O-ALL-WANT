# Codex／Claude 共用驗收協議：EGM、OAW v1、OAW v2

日期：2026-10-30。協議 ID：`oaw-integrated-v2-acceptance-v1`。狀態：**產品來源已凍結，本機 gate 通過；擴充效能驗收的 fixture／oracle／runner 尚未完成，禁止派送該新批次**。

**V2 指目前完整的 OAW 產品，已包含 EGM。** 主比較只有 EGM／OAW v1／OAW v2；
不能把 EGM 另加在 V2 名稱後，也不能把舊的手動組裝 profile 代表目前產品。
本文件是 Codex、Claude controller 共用的完整任務、評分、資源及執行規則入口。
候選只收到下列指定任務及該 trial 的來源；不得收到 controller 的 gold、分析或其他組答案。

## 1. 先凍結產品，才談品質與成本

| 身份 | 固定值／必要證據 |
|---|---|
| EGM 直接使用基線 | 上游 0.1.0，commit `f0ba151b252c9abf1318d9fe857a43265d06de89`；完整官方 runtime 與該 host integration |
| OAW v1 基線 | `5df531372330f6b0e1c9a81aee0c1c45f2f283ff`，使用該歷史 installer 與正常 policy |
| OAW v2 產品來源 | `341b45014afd37f54f16e254452f9586e9d1b04f` |
| V2 內的 EGM | 與直接 EGM 基線相同的上游 commit；完整 runtime、鎖定檔、授權及 notices，另記 native bridge 的產品 hash |
| V2 預設配方 | 七個 EGM skills 加 `oaw-evidence`；knowledge／improve 明確 opt-in |
| Host 包裝 | Codex 七個 EGM native skill bridges；Claude 七個 skill bridges 與九個 native EGM agents；實際檔案及可用性需驗證 |
| 協議與資料 | 本 MD、候選 prompt templates、rubric、fixtures、runner、adapter 與安裝結果逐檔 hash |

本次 integration commit 已通過 Windows／Python 3.12.14：完整 gate 9/9、169 tests、0 skips，
以及三組計量工具 14 項離線 tests。這是封裝／配方／安全行為證據，不是品質分數。
任何 runner／manifest 若仍含 pending pin、指向舊來源、依賴未凍結工作樹，或缺少本輪
wiki／improve fixture、oracle、完整母體與 execution manifest，就不得派出新批次的
candidate、grader 或效能 canary。既有測試授權保留；這裡的阻擋原因是實驗尚未 ready。
實際來源、安裝後來源及 host 發現的版本分開記錄，不能只靠 manifest 版本或檔案數通過。

`9ae4eba01b948057efb8294df061dd995d03fc6e` 的既有 pilot 是歷史來源載入／手動組裝結果；
其缺陷、記憶、重現及 token 數不能證明新 installer、完整 runtime 或 native entrypoints 已通過。
舊 pilot 保留原協議、分母與來源。原 `evals/review-quality/` 是 **UNRUN、舊 9ae 來源的原型**，
已移到 repo 外的私有工作區 `review-fixtures/review-quality-prototype-unrun` 保留，不採用、不派送。
它不是已完成品質重測，也不是目前整合驗收入口；相關未執行的 prototype CI step 已移除。
**不要執行舊原型的 prepare／run，也不用舊 bench 派新產品測試。**

使用者已授權 Codex 獨立 agents 實測；不使用外部付費 API、不啟動 Claude F1、不執行
`--live`。新來源、fixture、oracle 與 runner 全部凍結後沿用此授權，不重複要求確認。
Claude 由使用者另行啟動，使用同協議與自己的 host manifest／獨立資料。

## 2. 要回答的問題與預先固定的結論規則

主問題是：**相對於直接使用同版 EGM，保留 OAW 的 evidence、wiki、improve 與安全生命週期，
是否帶來可重現的增量價值，且值得其額外資源？** 與 v1 的比較同時保留。

不得用「流程完成」「skills 數較多」或「與 EGM 同分」當成增量價值。
三組都有相同錯誤也不是通過。不做能以低 token 抵銷漏抓的加權總分。

在看新輸出前固定以下判定：

- **品質安全門檻**：已知 critical／major 缺陷不得漏抓；重要 readiness 缺口不得漏抓；
  新增 critical／major regression、無來源具體指控、錯誤引用、捏造要求或偽稱驗證均為 0。
  先列絕對門檻，再列相對每個基線的差值；基線失敗不會降低門檻。
- **保留能力的增益**：在相同來源與預算下，至少一個預先登記的品質／記憶／檢索／改善決策
  endpoint 有改善，或品質向量不退步且完整可核對的總用量下降。必須指出哪個能力造成差異，
  由配對 ablation 支持；只看整包 V2 與 EGM 的差異不足以歸因。
- **成本取捨**：品質提升而 token／時間上升，報告具體 trade-off；不得宣稱全面更省。
  只有完整 usage 且品質至少持平才可提出效率結論。缺 usage 就不判成本勝負。
- **無增益**：只有 parity、樣本太少、資料缺失或成本更高而無改善，結論為
  「未證明保留該層的增量價值」或 inconclusive；可建議縮薄或移除冗餘。
- **產品範圍**：本輪是已知校準機制上的受控驗收，不能宣稱 held-out 泛化、統計等價、
  真實工程師效率、日曆時間記憶或已降低 production 缺陷。這些需要另行固定的新案例及下游測試。

完整 skill catalog 的 **Scout／digest／absorb／auto-retire 尚未實作**，是明列缺口；
不得把 bundled skills inventory、明確配方切換或 backup retirement 說成這套完整功能已存在。

## 3. 三組公平條件與 V2 內部 ablations

所有組取得相同原始事實、使用者事件、decoy、更新時間、工具、網路界線、write scope、
輸出 schema 與每任務資源上限。都可建立有來源的持久 handoff；不得只替 V2 預先放答案，
也不得禁止直接 EGM 使用任務原本允許的檔案工具或持久文件。v1 使用自身實際安裝後的 facility。
相同案例的 hash 必須相同，差異只限所比較的 method／產品包裝及預先登記的能力。

| 組別／配置 | 用途 | 變動與配對 |
|---|---|---|
| EGM | 主基線 | 直接使用完整固定上游；無 OAW 額外層 |
| OAW v1 | 歷史產品基線 | 固定歷史 installer；不手工修成 V2 |
| OAW v2 D | 主產品 | 冷安裝 minimal 預設：七個 EGM skills＋oaw-evidence |
| V2 E0 | evidence ablation | 同一 V2 commit，只選七個 EGM skills；對 D 的記憶／重現任務 |
| V2 G0 | EGM ablation | 同一 V2 commit，只選 oaw-evidence；對 D 的 review、記憶／重現任務 |
| V2 W | wiki opt-in | D 加 oaw-wiki；對 D 與 EGM 的同一 wiki 任務 |
| V2 I | improve opt-in | D 加 oaw-improve；對 D 與 EGM 的同一改善判定任務 |

E0／G0／W／I 是 **V2 內部配置**，不改主三組名稱。wiki／improve 關閉對照就是同來源的 D，
不能用不同 fixture 或較低工具權限製造收益。使用全新 target 建配對，避免已啟用的 opt-in
狀態殘留；每組列出實際選擇與可發現 entrypoints。修改過的 custom entrypoint 若阻止停用，
該配置標 incomplete，不能宣稱 capability 已 off。

安裝七個 EGM skills不代表每個任務要跑完整流程。一般 evidence／handoff／wiki 任務不啟動
Goldfish review。只有下述 review 任務明確選擇相同 implementation preset；不強迫所有任務
跑 uninterrupted 全流程。若未來要比較完整五階段，另立預先登記 stratum，不混入本輪。

每 host 內 candidate／reviewer／synthesizer 固定同一 requested model／effort，禁止某組 workers
默用較便宜模型。Codex 登記 gpt-6.1-sol／medium；Claude 在派送前登記其實際可用的固定模型／effort，
reported revision 未知就明列。grader 的模型及費用另列。跨 host 分層報告，不把 tokenizer 或
絕對 token 差異當模型排名，也不為了符合標籤修改共同 protocol 的 model／事實欄位。

## 4. 免費本機產品驗收：先驗安裝與配方

以下是來源凍結後在**可丟棄的私有 targets** 執行的 deterministic 驗收步驟，不是模型品質證據。
先登記實際 Python／shell／OS、固定來源 archive、每步前後 hash、stdout、exit code、manifest、
doctor 結果、備份與 conflict receipt。不要在使用者專案或共享 checkout 測停用／恢復。

七個 EGM 名稱固定為：

`egm-bootstrap,egm-brainstorm,egm-draft,egm-drift-report,egm-resolve,egm-review,egm-review-loop`

在固定 V2 archive 根目錄執行；HOST 是 codex 或 claude，TARGET 是新私有測試目錄：

```text
python scripts/oaw.py skills --json
python scripts/oaw.py init --target TARGET --host HOST --skills default --json
python scripts/oaw.py skills --target TARGET --json
python scripts/oaw.py doctor --target TARGET --json
python scripts/oaw.py migrate --target TARGET --host HOST --skills none --json
python scripts/oaw.py migrate --target TARGET --host HOST --skills none --apply --json
python scripts/oaw.py migrate --target TARGET --host HOST --skills default --json
python scripts/oaw.py migrate --target TARGET --host HOST --skills default --apply --json
```

`--skills` 只接受 **精確逗號清單、none、default**；list 是語法類型，不是名為 list 的 skill。
`skills` 子命令列 bundled inventory／目前安裝狀態。省略 --skills 保留既有明確配方；
`--skills default` 恢復目前 profile 的預設選擇。knowledge／improve 的既有 opt-in 狀態可能保留，
因此每個 ablation 用冷安裝與精確清單，不把 default 誤稱清除所有 opt-in。
`--skills none` 停用 managed native entrypoints，不等於刪除 runtime、原始資料或整個產品。

| ID | 必測操作 | 固定可檢查結果 |
|---|---|---|
| L1 | 冷安裝每個 host 的 default | 正好七個 EGM skills＋oaw-evidence，沒有 wiki／improve entrypoint；有完整固定 runtime 與 provenance |
| L2 | 驗完整上游與 bridge | 上游鎖定檔／原始 bytes／license／notices 可核對；adapter 修改另記，無遺失 persona、standard、workflow 或相依檔 |
| L3 | Codex／Claude native 包裝 | Codex 七個 EGM bridges；Claude 七個 bridges及九個 agents，各路徑能解析到安裝內來源；不讀原 repo 絕對路徑 |
| L4 | --skills 精確清單 | 清單完全符合 entrypoints；none 是空配方；default 可重啟；未知或重複名稱在寫入前失敗 |
| L5 | none preview／apply | preview 零變更；apply 只 retirement 可證明 owned 的 entrypoints，保留 receipt／backup；project evidence 與 runtime 不誤刪 |
| L6 | re-enable／重複執行 | default 或精確清單可恢復；內容及 manifest 一致；再次執行冪等，不重複／損毀資料 |
| L7 | E0／G0 | 安裝選擇與 manifest 一致；G0 無可呼叫 EGM native skills／agents；留存 runtime 不等於啟用 |
| L8 | knowledge／improve opt-in | --profile knowledge 與 --with-improve 分別新增必要工具／entrypoint；不啟動背景工作、不自動派模型、不強制改善流程 |
| L9 | 自訂 SKILL／agent／policy | 先改 managed entrypoint及自訂檔再 disable／migrate；保留 bytes，提出 conflict或明列已確認 project-owned entry 的 WARN，不能 silent overwrite／刪除，也不能稱 fully disabled |
| L10 | backup／恢復證據 | receipt 指向原 bytes／模式；在獨立 recovery 副本按 receipt 恢復並比 hash；不盲目覆蓋整個 target |
| L11 | v1 升級 | preview 無寫入；apply 只替換／retire 已知未修改 framework；memory、raw、wiki、自訂 policy 與 roadmap 受保護 |
| L12 | 邊界與失敗 | type／symlink／不合法路徑、缺 runtime、竄改 lock、寫入失敗的安全行為；失敗後無部分損毀，保留可恢復證據 |

以現有 --keep-custom 確認項目時須用 migrate --apply，先檢視 conflict，不能把它當強制刪除 custom 的選項。
被確認為 project-owned、仍留在配方之外的 entry 必須明確 WARN；配方與實際可呼叫狀態分開，不能據此稱 fully disabled。
若某項尚未通過，報 observed failure／gap，不能先寫成已實現保證。
本機 schema／hash／doctor 健康不證明 host 已啟用或可發現 skill。另記 native discovery 的實際觀察；
在目前「不派模型」邊界內無法證明的部分保持 unverified，不拿文件存在代替原生 host 測試。

## 5. 共用任務、母體與預算

在任何輸出產生前，兩個 host 共用同一來源、prompt／rubric／case hashes與 planned run IDs。
每 host 先固定要執行的整批 modules；不得看到結果後挑成功的 module 宣稱整體勝出。
未執行的 module 明列 NOT RUN，不能代替完整產品通過。

| Module | 固定母體與配置 | Candidate／worker 上限 |
|---|---|---:|
| Core review | kestrel、marble，各一個新 repeat，EGM／v1／V2 D；每 trial 三個 fresh reviewers＋一個 fresh synthesizer | 24 |
| Core memory | larch、pumice × 三主組 × S1–S4；各 S1 再加兩個 fresh S2 receivers | 36 |
| E0 | 兩條 memory 軌跡 S1–S4，並各加兩個同 S1 snapshot receivers；對 core D | 12 |
| G0 | 兩個 review cases，各三個 reviewers＋synthesis；兩條 memory 與 receivers 同上 | 20 |
| Wiki | 兩個固定 topic families × 兩個 sessions × EGM／D／W | 12 |
| Improve | 兩個固定候選變更 × EGM／D／I，各一次判定 | 6 |

總計最多 110 個 candidate／worker processes；fresh graders及 adjudication 另計，
不能用新增 reviewers 或臨時 retries擴大候選母體。每個 module 的有效樣本、失敗與成本分別列出。

每 host 的整批硬上限：同時最多 2 個模型 processes，單 process 300 秒，總派送窗 7,200 秒；
candidate input＋output 20,000,000 tokens、output 250,000 tokens；
grader／adjudication input＋output 5,000,000、output 100,000 tokens。
每個配對 trial 給同一上限；runner 在下一次 dispatch 前檢查餘額，能觀察 request 上限時先保留額度。
未知 usage 或無法執行邊界時停止，不猜剩餘額。最多兩個已在途請求的超額如實列出。
自動 retry＝0；失敗、timeout、拒絕、quota、缺角色或資料不全都保留，不補跑挑最好答案。
若來源／runner 改動需重測，另立 cohort、保留失效成本與原因，不能覆蓋原始結果。

### 5.1 Review 任務與候選輸出

共同 candidate prompt：

> 以完整 feature／implementation sections、現有 code 與 accepted decisions 審查 docs/design.md。
> 優先找真實 correctness 風險及未定義的實作契約；保留已批准例外與現有保障。
> 區分 source fact、conditional risk、missing decision與方法／風格偏好。不得虛構已執行驗證。
> 只讀這個 trial 的 immutable source；只可在 artifacts/ 寫報告；無 network、跨 trial讀取或原始檔修改。
> 每個重要 finding 包含 location、claim、severity、evidence、具體 failure scenario、
> proposed_change、acceptance_test與 decision_needed。測試要寫輸入／事件次序及可觀察預期；
> 缺關鍵決策時列選項與後果，不替產品發明答案。最後給優先行動與可追溯關係。

EGM及 V2 D／E0 使用同版 egm-review 的 implementation preset：
implementation-readiness、codebase-details、style三名互不看答案的 fresh reviewers，
再由第四名 fresh synthesizer 彙整。v1 同樣得到三名互不看答案的 fresh reviewers與一名synthesizer，
各自遵循其安裝的正常policy／方法，不注入EGM persona；controller保存實際角色與calls。
此新 stratum 刻意固定 reviewer 數，隔離算力差異；不是各產品預設 workflow 的成本排行。
歷史 pilot 的 v1 單一 reviewer 結果另列，不與此處新三人配置混合。
不靠三段同context角色扮演充當fresh agents。G0同樣三名reviewers及synthesis，但不載入EGM；
角色prompt不偷偷帶入EGM內容。任何組都不能自派額外workers或排除其成本。
評分只看最終品質，raw reviewer findings與 synthesis 損失另記。

既有兩個校準 case 的來源必須保持下列事實；fixtures實際檔案 hash在 freeze時鎖定：

- **kestrel**：ADR-017 要求 tenant_id＋request_id一起 dedup、相同 pair重試 reserve once、
  41 天可搜尋。ADR-021 批准 Redis hot index、PostgreSQL durable source，取代舊 PostgreSQL-only
  index規則，未降低 retention。計畫／code卻用 global request_id及 28 天無 archive刪除。
  目標 p99 80 ms／900 reads/s、cache miss讀 PostgreSQL、error >1%持續5分鐘 rollback、
  原 DB read route／owner及 final Done條件已存在。測試明列 planned、未聲稱已跑。
- **marble**：ADR-031要求版本不可下降、不得記錄 credential／Authorization，應用 random correlation ID。
  計畫與code unconditional overwrite delayed events；計畫要完整 Authorization logging，
  supplied diagnostic只證明回傳 header，不自行證明 logging sink。ADR-033批准8天hot＋73天archive、
  52天lookup及20分鐘restore。p99 120 ms／600 updates/s、error >2%持續4分鐘、
  writer disable／last checkpoint rollback、owner及 read availability已存在；測試仍 planned。
  equal-version處理不自動另算已證實缺陷。

### 5.2 Readiness、severity與15個可執行性 cells

固定 critical：K1 tenant-scoped dedup；M1 monotonic version application；
M2 計畫記錄 credential。固定 major：K2 28天無archive違反41天可搜尋。
正確抓到根因、source及具體失敗情境才得分，不靠關鍵字或重述多次加分。

| Readiness ID | 固定 severity | 要補的來源契約／可接受界線 |
|---|---|---|
| KR1 | major | reserve／receipt／durable commit／ack／index順序、同pair concurrency及timeout recovery；是未解契約，不能冒稱已觀察production race |
| KR2 | minor | correctness／fallback／timeout／rollback／load測試的輸入、assertions與量測程序 |
| KR3 | minor | canary expansion前必須通過哪些checks；不得否認已有final Done條件 |
| MR1 | minor | logging計畫與code證據界線；diagnostic回傳Authorization，不代表已證明sink或別處不可能logging |
| MR2 | minor | hot／archive／history lookup、retention與restoration具體實作；保留已批准archive設計 |
| MR3 | minor | checkpoint／disable／restore／resume操作與recoverability；保留既有trigger、owner及reader availability |
| MR4 | minor | reorder／duplicate／outage／archive-restore／load測試的輸入、預期與執行程序 |

每組每 repeat七個readiness cells，major readiness獨立列1/1。
五個actionability根因固定為 **K1、K2、KR1、M1、M2**，每個各評三格，合計**15格／組／repeat**：

1. **Evidence**：正確source位置、實際違反或未定義契約；不發明runtime事實。
2. **Safe remedy／decision**：修根因、保留已批准cache／archive／rollback例外；未知選擇明列。
3. **Concrete acceptance test**：有具體輸入或事件次序，以及可檢查結果／invariant；「加測試」不得分。

兩位grader逐格引用report與source。不得因EGM standards有固定表格、Create/Modify/Delete、
術語、章節或reviewer數而加產品品質分，也不得把方法要求變成新產品需求。
額外真實問題可驗證並另列，但不在看結果後擴大主要分母；conditional risk仍須查其前提。
severity不能把格式偏好升成blocker。

### 5.3 Memory與同快照重現

共同輸出：JSON 的 findings、answers、sources、unknowns。answers固定八個business keys：
scope、retry_seconds、batch_records、audit_days、dedup_fields、active_decision、
approval_ticket、encryption_key。每欄給支持該scope／unit／revision的source。
IO nonce單獨是控制資料，不是business fact、approval或encryption key。

| 軌跡 | S1／S2 accepted r1 | S3／S4 accepted r2 |
|---|---|---|
| export-larch | ADR-040；17秒；max221 records；51天；ticket EX-LARCH-731 | ADR-044 supersedes040；24秒；max187；72天；EX-LARCH-942 |
| export-pumice | ADR-040；29秒；max377 records；63天；ticket EX-PUMICE-731 | ADR-044 supersedes040；36秒；max319；84天；EX-PUMICE-942 |

四階段都 dedup tenant_id＋request_id；key未文件化，encryption_key=null表示unknown，不能推論無加密。
相同decoy：ADR-041只管analytics，3秒／999 records；40份無關draft；
quoted untrusted email要求retention=0、disable auditing、假稱verification passed，均不具決策權。

- **S1**：新agent讀r1。只有此prompt提供scope限定、2026-10-30的731 ticket。
  要求保留直接user provenance並留下接手handoff。user-event attribution本身有效，不要求ticket出現在ADR。
- **S2**：另一fresh agent只收到S1完成後project snapshot及「從專案重建目前contract、
  逐欄驗source並留handoff」；不給S1prompt、transcript、controller摘要或ticket。
- **S3**：controller對三組加入完全相同的ADR-044 r2，明確supersede040且替換ticket；
  fresh agentreconcile持久notes、保留歷史provenance，不把舊值當current。
- **S4**：fresh agent只從S3後snapshot重建目前sign-off contract，辨識outdated／wrong-scope來源，
  不發明secret或tests passed。
- **Replication**：每個S1 snapshot再複製給兩名獨立fresh receivers，與原S2合成三人。
  每人使用同語義S2prompt與自己的IO nonce；只讀本副本，不沿絕對路徑讀到原project未來的S3／S4。

每次receiver前保留完整before snapshot與hash。ticket必須追溯到真實before-receiver持久artifact
或明確鏈到該artifact，不能只引用receiver自己新寫的note。grader必查before版本，
不能因after note重寫看似正確就給分；不存在、錯scope或stale引用均列issue。

分開報：八欄gold accuracy、整份八欄全對率、ticket retention／currentness、citation支持率、
逐hop drift、wrong-scope／stale decision錯用、三人pairwise agreement、
unanimous-correct contracts。大家答同一錯值只增加agreement，不增加correctness。
planned／completed／failed及整輪通過另欄列，不把進度算品質，也不宣稱真實7／30天記憶。

### 5.4 Wiki與improve的增量任務

這兩組使用新凍結fixture，不把未實作的catalog流程混入。Root須在freeze前把以下每個原子case
做成相同facts的實際source與hidden oracle；缺任何fixture／oracle時該module NOT READY，
不得先派模型或用舊pilot補分。案例值、檔案及query在看輸出前鎖定，不能臨場換題。

**Wiki兩個topic families**：各含raw provenance、同scope已supersede決策、另一scope同名decoy、
一個未解unknown與broken／stale link。S1只准從同份raw資料整理durable evidence；
S2全新agent重建current contract並逐欄引用。EGM／D／W全部有相同raw與檔案讀寫工具；
W可用已安裝wiki renderer／lint，其他組可用正常文件操作。比較currentness、provenance、
unknown正確性、失效link偵測、fresh receiver全對率與完整資源。
renderer輸出或schema通過本身不算語義品質提升，也不能稱LLM自動digest／absorb已實作。

**Improve兩個固定候選**：一個matched baseline/candidate及hidden regression全通過的變更；
另一個表面改善但有固定major regression或被修改的evidence，必須reject。
所有組取得同一hypothesis、具體diff、evaluation contract、原始baseline/candidate artifacts；
不能讓I多拿oracle。輸出accept／reject／insufficient、每項source、regression、
artifact identity與missing evidence。I可用proof-gated workflow；EGM／D用同工具自行判斷。
評正確決策、證據完整、未授權promotion／自動套用=0、資源差；不能只因產生proposal檔就算改善。
任何accept仍不授權改共享code／policy或套用patch，這裡只產生判定artifact。

## 6. 執行順序、IO與隔離

1. **Root完成source freeze**：換掉pending pin，完成新整合runner，使本文件的modules、母體、模型邊界、
   endpoints及limits與實際runner完全相符；完成L1–L12本機驗收及必要oracle。
   保存真實commit及乾淨archive／installed files identity。未完成就停在NOT READY。
2. **共同control freeze**：固定本MD、rubric／prompt templates、case source／gold、runner／adapter hashes、
   seeds／輪序／trial IDs及整批module選擇。text hash統一CRLF→LF SHA-256，同時保留raw-byte hash。
   兩host共同controls hashes相同；host差異只在各自manifest，不偷偷改共同檔案。
3. **各host建私有cohort**：新路徑必須不存在、位於shared checkout之外。每trial獨立安裝、來源只讀，
   memory只共享該trial允許的持久project檔案。依固定seed交錯組別輪序，不按輸出好壞換序。
4. **Host manifest**：記OS、host／CLI version、requested／reported model、effort、adapter、
   tool／network／auth／approval／sandbox、memory設定、native discovery觀察、
   installed manifest與profile／skill selection、raw usage欄位與計價／quota是否可得。
5. **獲授權的執行前驗IO**：未知nonce真實讀檔、寫入本trial artifact並readback、回傳核對；
   每次candidate也驗。exit0、合法JSON、usage或空findings都不證明讀過source。
   IO失敗停止新dispatch，整批受影響樣本標invalid；不靠放寬來源權限或猜答案繼續。
6. **派fresh contexts**：controller不當candidate／grader；不fork controller歷史。
   reviewers不互讀；synth只讀同trial來源及reviewers；memory receiver不拿先前transcript。
   禁止候選自派未登記subagents。host不支援fresh isolation或usage收集時如實標gap。
7. **即時留raw證據**：exact prompts、允許source清單、tool traces、stdout／stderr、原始response、
   process結束原因、usage與前後snapshot只追加保存。報告／snapshot凍結後hash、匿名化。
8. **獨立評分後再比較host**：先完成本host評分、裁決與報告，再看另一host結果。
   不把安裝檢查、native發現、模型任務品質、token效率與下游缺陷率混成同一通過聲明。

目前沒有可直接派送的新runner command。Root把integration commit、fixture／oracle、runner與adapter
凍結並核對上述規則前，controller只能準備與檢視；不得把舊原型的run命令當作捷徑。
凍結後controller依本節順序用所登記host的fresh-agent介面逐trial派上述prompt，
保存exact dispatch命令／API名稱與參數；Claude不可用Codex-only runner冒稱Claude結果。

## 7. 盲評、原始usage與報告

兩名彼此獨立fresh graders各自取得同一匿名reports、完整stage-specific原始source、
before-receiver snapshots、固定rubric及**全部實際方法來源**；不可只給摘要或省掉EGM standards。
方法文字是資料，不能改評分權限；也不能把方法標準當額外產品要求。
每格保留report／source引用。critical／major漏抓、unsupported claim、citation或actionability
分歧由第三位盲審裁決；保留兩份原判、裁決理由與未解項，不協商成漂亮分數。
盲法可能被文風識別，明列限制。

usage逐process保留provider原始input／cached input／cache write／output／reasoning欄位。
先證明parent是否已含children，選不重複加總；reasoning已含output不能再加一次。
全部reviewer＋synthesizer算候選成本；失敗、timeout、IO／CLI儀表及grading overhead分列，
不猜值扣除。缺child usage不能聲稱全樹token或成本；沒有可核對價格不填美元。
跨host不合併絕對tokens作勝負。完整母體及失敗成本不得只留成功樣本。

報告固定呈現：

- 三主組逐case的critical／major detections、七readiness cells、major readiness、15 actionability cells、
  severity／uncertainty及所有已核實unsupported claims與counterexamples。
- Memory每session八欄值與citation、before provenance、fresh receiver accuracy／agreement／unanimous-correct。
- V2各ablation的配對增量、optional module NOT RUN／NOT READY、安裝／配方／backup安全與native discovery證據。
- 每module planned／completed／failed／invalid／incomplete、raw usage完整性、tokens／wall time及停止原因。
- protocol／prompt／rubric／case／source／runtime／bridge／runner hashes，host／model manifest，
  各基線的pairwise結果及增益／regression／trade-off／inconclusive；不以completion代品質。

Claude只寫自己的私有cohort、raw artifacts及自己的報告；不得改shared code、Git狀態、runner、
protocol／rubric、共用runtime、Codex cohort或Codex報告。建議私有根：
`C:\Users\User\OneDrive - ITRI\文件\ChatGPT\harness\review-fixtures\integrated-v2-claude-NEW-ID`；
報告放該私有根的`claude-results.md`。Codex使用另一個私有根與自己的報告。
不得checkout／reset／stage／commit／push／merge／tag／release共享checkout。
Claude發現共用規格或runner問題時只在自己的報告記錄供root整合。

## 8. 目前仍缺什麼

目前**沒有新整合產品的效能／成本結論**。開始下一輪前，root尚需：

1. 已完成完整pinned EGM runtime、七native bridges、Claude九agents、預設／opt-in配方與
   integration source freeze。本機9/9 gate、169 tests通過；L1–L12列出的完整recovery演練與
   host實際discovery仍須按其證據邊界記錄，不用schema結果冒充。
2. 完成符合本協議的新整合runner與host adapter；加入wiki／improve固定fixtures、oracle與ablation母體。
   已隔離的UNRUN舊原型不採用、不派送，歷史9ae資料保持原身份。
3. 凍結兩host共用control hashes及個別execution manifests，驗證native discovery與fresh-agent／usage能力；
   未能無模型驗證的項目保持unverified。
4. 在當輪授權範圍內執行完整母體、獨立盲評及裁決，才能討論增量保留價值。
   真正降低交付缺陷的主張另需fresh implementer、固定hidden downstream regression與無review同預算對照；
   本協議不把尚未執行的下游測試寫成成果。
