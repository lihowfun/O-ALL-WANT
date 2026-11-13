# Harness² 吸收評估：讓 OAW 更有效，也讓能力可選、可管理

日期：2026-11-13。上游：[google-research/harness2](https://github.com/google-research/harness2)，固定 commit `6868817518876de8fd170c6a8354daca273b6191`（2026-11-02）。論文：[Harness² v1](https://arxiv.org/html/2610.14224v1)。對照 OAW：`claude/oaw-2@359e6e3`；整體進度見 [REVIEW](../review-2026-11-13/REVIEW.md)。

**定位：重要的評估方法參考，優先吸收其證據設計；目前是來源研究與最多三項候選單位，尚無 OAW 採用判定。** 本次未安裝／執行上游 runtime、未呼叫實驗模型、未改產品 skill，也未把研究登記成完成試吃。上游方法的事實是 T2，caveat：固定版本的來源觀察；論文結果未由本次重現。OAW 方案均為待驗設計，不是已量測收益。[來源清單](SOURCE.json)記錄讀取檔案與 Git blob SHA，**不是完整上游封存，也不是 catalog tasting receipt**。

## 1. 先定義 OAW 要變好的兩件事

依使用者本次補充，OAW 的目標有兩條，管理上共用來源與證據，但成功標準不同：

| 目標 | 要回答的問題 | 不足以代表成功的數字 |
|---|---|---|
| **整體 harness 最佳化** | EGM、記憶、token 節省、code map、路由與審查怎麼組合，能在品質與可靠性守住的前提下，以合理成本完成工作？ | merge 的 repo 數、skill 數、規則字數、單次 token 下降 |
| **使用者按需取得能力** | 使用者選擇 PPT、遊戲或影片能力後，能否完成該類交付，並知道裝了什麼、何時會用、怎麼更新或移除？ | 安裝成功、CLI exit 0、生成了檔案、catalog 顯示已加入 |

這裡的「最好」應指**在指定任務、host、模型和預算下有證據支持的品質／成本取捨**。不能把不同用途壓成一個總分，也不能用「整包尚未證明更好」否定每個可選能力。

吸收的操作可以是重建、替換、合併、縮短、改成按需載入，或保留原方案。EGM 是現有組件，token economy、code map 與額外技能各有證據與用途；不把所有東西擴寫進 EGM 或另一份常駐規則。每次提案寫清楚：**解決哪個失敗、取代什麼、增加多少常駐負擔、怎樣被觸發、怎樣撤回**。若只是重複現有功能，先比較替換方案。

這是產品方向的釐清；不改 H1、X1、X2 的歷史判詞，也不將本文件變成 session 啟動必讀。

## 2. Harness² 的改進與審查流程

它固定模型權重，修改執行環境中的 prompt、guardrails、memory、tool guidance、subagents、skills、scripts、plugins。每個新任務從共同 base harness 開始；歷史 library 提供提案依據，不直接把前一題整棵 harness 當下一題的預設。參見 [結構定義](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/spec.py)、[遞迴流程](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/recursion.py)。

1. **取得參考執行**：留下 base 的軌跡與成品，找到可觀察的失敗或浪費。
2. **提出兩種候選**：跨任務流程改動（invariant）與領域改動（domain），分別實際跑同題。
3. **對照執行差異**：用具體事件支持改動，組合有依據的部分，再執行組合版本；不只審文字是否合理。
4. **選交付成品**：需要 selector 時匿名化候選，從現有輸出中選一份；這仍是模型判斷。
5. **事後反思與外部評分分開**：反思記錄可遷移的經驗；benchmark judge 另行衡量交付品質。

這裡有三種不同的證據：程式／規格審查支持「實作符合契約」，軌跡對照支持「某改動可能影響行為」，獨立留出評估才支持「在指定條件下優於基線」。**選中了候選，沒有完成後兩項證明。** 流程與範圍見 [experiment guide](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/EXPERIMENTS.md#L6)、[selector](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/selection.py#L295)、[judge 邊界](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/judge.py#L15)。

最值得學的細節在改進與反思提示：依據軌跡中的具體行為選最小合適改動；反思逐項區分 helped、hurt、no observed effect、confounded，保留被否決候選的證據；多處同改或單次結果不足以歸因，可明記混雜。無可靠經驗時允許 NO_ENTRY。這能抑制「每跑一題就增加規則」；仍須另外驗證下一題是否受益。[提案提示](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/prompts.py#L858)、[反思提示](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/prompts.py#L1105)。

## 3. 他們如何檢查 harness 是否真的比較好

論文使用三套 benchmark、不同模型與執行 host，報告三次任務順序重排的平均與離散程度；比較原生及其他優化方法。它也做 library／scope／composition 消融、跨任務與模型轉移、品質對完整改進成本的比較，並列出失敗案例。這些提供多種反證機會，比只看一個成功 demo 更有用。注意：重排 seed 不固定模型抽樣；含未來經驗的回溯轉移不等於線上預測；錯選成品與退步仍會發生。本次只確認方法與報告，沒有重現其數字。[論文 §3–4、附錄 E–F](https://arxiv.org/html/2610.14224v1)。

以下是可直接從固定版本程式核對的設計及限制：

| 核對項 | 上游實作 | OAW 的吸收判讀 |
|---|---|---|
| 審查資料分離 | 執行 context 過濾答案／grader 資料；judge 與改進流程分開 | 值得吸收，但過濾器不能保證網路、檔案和歷史都不洩題。[context](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/context.py) |
| 匿名選擇 | 候選 ID 由排序與 seeded shuffle 產生，selector 看任務與成品 | 減少名稱偏差，不能消除模型偏好；選擇品質需另量。[selection L71](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/selection.py#L71) |
| 可否保留 baseline | 最終選池只有 k 個 composed finals，排除 base／原始候選；k=1 不跑 selector，final 無成品也沒有 base fallback。composer 可以不改 base，但與選回 base 成品不同 | OAW 的產品晉升要保留「不改」；這是 **OAW 額外要求**，不是 upstream 已有的最終保底。[L93](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/selection.py#L93)、[L360](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/selection.py#L360) |
| 真實成本 | 每題 R=4k rollouts、P=3k improvement stages；retry 另計，selection／reflection 在這本 ledger 之外 | k=1 也是 4 次執行＋3 次改進階段＋反思；不能稱一次便宜審查，不能拿 ledger 小計冒充總花費。[ledger L15](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/ledger.py#L15) |
| 缺失評分 | judge 失敗記 unscored，而非 0；report 有有效分母／ungraded 等診斷 | 同時公開計畫題數、完成數、可評分數及原因，避免只看成功評分子集。[judge](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/judge.py)、[report](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/report.py) |
| 可重現／續跑 | harness fingerprint、task input identity、明確完成 marker | 舊 marker 缺 input identity 仍可重用是相容例外；OAW 新試驗要求完整 identity，不能照抄例外。[runmark L132](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/runmark.py#L132)、[identity test](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/tests/test_task_input_identity.py#L101) |
| 資料與環境版本 | task split 可固定；JobBench revision 在下載時解析並記錄 | commit 之外另固定 dataset、split、模型、host、judge、網路條件；任務 seed 不等於模型 seed。[分割程式](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/scripts/split_tasks.py)、[實驗設定](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/EXPERIMENTS.md#L64) |
| 評分的客觀程度 | 有 rubric／模型判分，也有容器 verifier；不同 benchmark 的分母、權重不一樣 | 可執行驗收優先；審美與可用性採盲評和明確 rubric，不能把所有分數叫作機械真值。[benchmarks](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/BENCHMARKS.md) |

**一項實際的效度風險：** upstream 明記未限制網路，驗證時曾有 Codex 下載該題公開 rubric；Codex 以 sandbox disabled 執行。日後官方試吃需放在隔離測試環境，先設執行端的資料／網路邊界並記錄，不把其設定移植成 OAW 使用者的預設。這影響「是否真的泛化」的判讀。[EXPERIMENTS Web access](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/EXPERIMENTS.md#L93)。

## 4. 最多三個吸收單位

以下是研究 shortlist，不是 absorb／decline 判詞；三項均**未重建、未測量**。

| 單位 | 具體產物與用途 | 如何融入 OAW | 等級、驗收與目前狀態 |
|---|---|---|---|
| **U1 完整實驗帳與可重算報告** | 每階段成本、固定輸入身分、完整／缺失覆蓋、候選→選擇→外部評分鏈 | 擴充 #9 runner 的資料 adapter；沿用 eval_stats／improvement 的判定，不再做第三套 scorer | A：只重建 stdlib 機制、不改模型文字；先離線 fixture 驗證，再接實際 trace。可優先設計 |
| **U2 最小改動與對照審查卡** | 問題事件→假設→最小 diff→baseline／candidate 軌跡→效果與混雜→保留／撤回；可提出刪減與替換 | 作為 oaw-improve 的按需附件；fresh review 看證據，EGM 只在適合的任務使用，不再增加一個競爭 router | B：模型會讀的流程文字須 A/B；測品質、全成本、錯誤觸發、規則負擔。候選 |
| **U3 有證據與作用域的經驗索引** | cue、lesson、evidence、confidence，加來源版本、適用條件、失效／矛盾關係；允許不新增 | 對接既有 evidence／recall，按需取用；任務事實與可重用工作方法分開，不把所有歷史變常駐 prompt | B：取用文字／策略影響模型；先做 cold-start、chronological transfer、消融。排在 U1／U2 之後 |

U1 借鑑 [ledger](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/ledger.py)、[report](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/report.py)、[runmark](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/runmark.py)；U2 借鑑 [prompts](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/prompts.py)；U3 借鑑 [library](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/harness2/core/library.py)。替換關係、失效治理、晉升 gate 是 OAW 建議，不能歸功為 upstream 已實作功能。

完整 Harness² runtime 屬 C 路線，另案隔離試吃。其 core 也是 stdlib，但需 Python ≥3.12、<3.14；特定 backend／benchmark 有其他工具與選用依賴，與 OAW Python 3.10+ 基線不同。無需為吸收評估方法而先替換 OAW runtime。核心 Apache-2.0 與 benchmark／資料各自授權分開記。[pyproject](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/pyproject.toml)、[setup](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/docs/SETUP.md)、[dependencies](https://github.com/google-research/harness2/blob/6868817518876de8fd170c6a8354daca273b6191/dependencies/README.md)。

## 5. OAW 下一次應怎樣測

以下是**新實驗的設計建議**。正式執行前另立 PREREG、固定題目／預算；不補寫 H1 的舊假設，不把 FIXCHECK 變成新技能比較，也不重啟本輪 PPT 校準。

### 5.1 分開測「成品 harness」與「改進流程」

- **成品問題**：凍結候選後，日常執行是否比目前 OAW 好？同題、模型、host、effort、權限，配對比較現行 OAW 與候選；另保留原生及便宜簡單方案，辨別改進來自哪裡。
- **流程問題**：為了找到同等品質的候選，Harness² 方法是否比目前改進／審查方法省總成本？共同起點、開發題、搜尋預算、最終留出測試；費用包括失敗提案與被淘汰候選。以「原生多跑幾次再選」或同等較強 editor 作對照，避免把更多 compute 或更強模型的收益歸給方法。
- **額外能力問題**：官方 skill 在自己的主場，以及使用者實際用途，是否改善可交付成品？依 intake 保留原生、官方 food arm；skill 另加 description-only。只有做了 OAW 重建才加對應候選，不先跑所有方法×模型×領域的笛卡兒積。

上述對照按問題分批做；**核心比較基準是當前 OAW，原生組是重要參考，兩者不能互相取代**。對外部食物下採用判詞仍需官方安裝並有評分過的 food arm；只重建幾句方法不算驗過整套 Harness²。

### 5.2 留出與歸因

1. 先用離線 fixture 證明觸發、輸入身分、帳目、缺失處理可工作，再用獨立開發 pilot 估成本／變異。pilot 不併入最終收益樣本。
2. 測試任務由獨立出題者建立，先驗證題目要求、checker 與成品真正一致。PPT 的 LINE／LINE_MARKERS 和字框誤判是本次必須避免的案例。
3. 以任務族／repo／領域分開開發與測試，近似模板不跨兩邊。題目、rubric、停止規則與最小有意義差異先固定；留出答案／評分不得回流到候選修改。
4. 凍結 harness 後才做留出評分。若測線上 library，按時間只允許先前任務經驗，每個 arm 使用獨立歷史；同時報 cold-start，不能用未來題經驗冒充線上能力。
5. 用 full／去掉某單位／精簡替換的定向消融定位收益；必要時再測有交互作用的組合。單次多處同改只能說整體差異，不能分配因果貢獻。
6. 任務內重複衡量模型變異，跨任務才衡量泛化；共享 library 的任務還受同一 stream 影響，分析須處理 stream／domain 群聚，不能把每個 rollout 當獨立樣本。

維護者 intake 目前使用 12 題一次的設計；self-improvement 的至少 2 題×3 次是另一套最小檢查。兩者都不是普遍足夠的檢定力保證。若新方法要改樣本數或統計單位，需在新 PREREG 明寫理由與方法，沿用現有門檻，不事後換尺。

### 5.3 指標：同時量效果、負擔和可管理性

| 面向 | 最少要留下的證據 | 例子 |
|---|---|---|
| 交付品質 | 預先固定驗收、逐題結果、配對差異與不確定性、嚴重回歸 | code：隱藏測試／回歸；PPT：可開啟、可編輯、內容正確、渲染可讀；遊戲：可玩迴圈／輸入／狀態；影片：規格、時序、音畫與交付需求 |
| 使用者品質 | 無法機械化部分用匿名成品、明確 rubric、獨立評審；有分歧保留未定 | PPT 美感／溝通、遊戲體驗、影片敘事不能被「檔案存在」取代；本次僅列方法，沒有受測能力的收益 |
| 運行成本 | logical tokens、扣快取讀取後 tokens、可取得的實際費用、時間、工具數與錯誤率 | 正常呼叫較少但錯誤率更高，未必較有效 |
| 改進總成本 | base、提案、probe、compose、selector、reflection、retry、外部 grading 分列 | 產品執行成本、改進成本、研究評分成本分開報，再報總支出；對照組用同一口徑 |
| 規則與路由負擔 | 常駐 context、相關任務觸發率、不相關任務誤觸發率、重複／衝突決策、無效工具循環 | code map 省了讀檔但觸發不準，不能只展示被成功使用的題 |
| 額外能力的閒置成本 | 同一核心 harness，在能力未安裝與已安裝但無關的配對任務上比較 | PPT skill 不應在普通修 bug 時觸發；還需計 description、hooks／MCP 啟動成本 |
| 可管理性 | 來源版本、安裝範圍、更新／移除結果、證據對應版本、使用者自改保留 | 安裝與移除驗收以 fixture／契約測試做；不為每個管理檢查花模型 token |
| 有效覆蓋 | 計畫／啟動／完成／被截斷／可評分／缺失原因逐組呈現 | 未評分不是 0；不能悄悄刪掉困難題後宣布提升 |

新流程的效率主張須有獨立 meter 或 host trace 覆蓋所有階段；候選自己填的帳不算完整。既有 improvement.py 將 overhead 加入 arm tokens，grading 分列；新增研究報告應另外把 grading 算進**整體實驗支出**，不改舊欄位語義。若評分所有候選以分析 selector 的選擇損失，列為事後診斷、計入評分費，不能把分數餵回 selector 或拿最優候選假裝實際交付。[OAW self-improvement](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/docs/SELF_IMPROVEMENT.md#L37)。

### 5.4 晉升而非比名次

OAW 已有配對 bootstrap、品質等價區間、成本區間、評審家族一致性、最差條件彙總與未定出口；improvement.py 也有觸發、證據 hash、逐 assertion 回歸與資源上限檢查。**保留這些既有 gate，不以 Harness² 的均值排行榜取代。** 新題型的適用指標／margin 要先定義，不能直接套審查 coverage 到 PPT 美感。[EVAL_PROTOCOL](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/docs/EVAL_PROTOCOL.md)、[SELF_IMPROVEMENT](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/docs/SELF_IMPROVEMENT.md)。

建議產品晉升時讀一張對照卡：品質／成本結論、可適用範圍、完整覆蓋、嚴重回歸、規則負擔、替換／移除關係與還原方法。能同等品質更省成本，或成本在事先範圍內且品質更好，才支持相應採用；廣泛收益不明但某用途成立，可保留明確選用。無法歸因、資料不足、觸發沒發生，均保留未定。簡化／刪減也能是成功候選，正式移除仍遵循既有 owner／版本流程。

## 6. 能力與套件清單：沿用現有管理，補上決策所需資料

**OAW 已做出基礎，應先對齊它，而不是另開一個 skill 市集。** 使用者 `oaw.py add / list / remove` 已有入口；`list` 收據列來源、加入者、試吃結果、description 成本估計、自動執行部分與移除方式。`recommended` 對 optional 使用明確觸發；相同名稱及已宣告類別有衝突處理，語意重疊仍需審查。維護者 catalog 則管理來源、證據、判定、吸收與版本。這些是既有程式／文件能力，未表示每個 skill 已實測。[CLI](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/docs/CLI_Reference.md#L38)、[add/list 入口](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/scripts/oaw.py#L1083)、[catalog derive](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/scripts/catalog_core.py#L3023)。

`SKILL_INTAKE.md` 一頁版仍將使用者路線稱為「2.0.1 計畫 W3」，後半有更早 v0 限制；應在既有 #10 文件工作中對齊目前 CLI／程式，不把舊敘述當成整個分支都尚未實作。

使用者可以自行加裝未試吃技能；管理器應如實標示「已安裝、未驗證」。**維護者將其納入 OAW 預設的證據要求，不應變成使用者自選能力的強制研究門檻。**

建議在同一清單／收據呈現下列資訊；這是欄位對齊方案，**本次未改 schema 或 UI**：

| 資訊 | 已有基礎 | 建議補齊 |
|---|---|---|
| 身分與版本 | source、pin／收據／檔案 hash | 安裝版本與受測版本並排；不同版本不繼承舊版收益 |
| 用途與範圍 | skill 名稱／description、host、target | 核心最佳化或額外能力、解決的任務、適用模型／host |
| 狀態 | 安裝收據、tasting／absorption 紀錄 | 分開「候選／已安裝／已移除」和「未試吃／未定／有條件證據」；避免單一綠燈 |
| 觸發與負擔 | optional 明確觸發、description 估計、自動 hooks／MCP | 實測閒置成本、觸發精確度、載入範圍 |
| 相依與整合 | 執行元件同意、依賴列示、結構衝突 | 語意替代／重複、能力間必要依賴、保留理由；不宣稱已能自動解決所有相依 |
| 效果與生命周期 | verdict 出處、備份／移除、版本紀錄 | 品質成本證據、使用條件、更新後重驗範圍、已知限制、退役理由 |

本次 Harness² 的正確清單定位是：**核心改進方法候選；固定版本；來源研究完成；官方 runtime 未試吃；未安裝／未吸收；U1→U2→U3 候選次序。** PPT、遊戲、影片則屬使用者能力方向；本文件沒有替任何未測套件背書。SOURCE.json 與此表是 review 證據，尚未寫入本機 catalog；日後進入 intake 時用既有 catalog 指令與封存流程登記，不手改一份新的平行 registry。

## 7. 後續順序與成本

估算是工程工作量，非已支出／模型預算授權。Harness² 研究現在完成，不另設 2.0.1 發佈 blocker。

| 優先 | 交付 | 估計成本與依賴 |
|---|---|---|
| P0：本次 | 記錄雙目標、來源 pin、三單位 shortlist、客觀評估與清單對齊方案 | 文件研究；新增模型試驗 0 次。產品仍依 #17／#18 修復與 D45 收尾 |
| P1：#10 文件 | 對齊使用者安裝路線的已實作狀態；保留證據與安裝狀態之別 | 約 0.5 天；可併既有發佈文件工作，無新增模型試驗 |
| P1：發佈後 #9 | U1 adapter／報表與離線 fixture；對接現有 comparator，先不另造 judge | 約 1–2 天；依 runner 資料格式與實際 trace 可用性 |
| P1：發佈後試吃 | 官方 Harness² k=1 小範圍主場試跑＋OAW 用途 pilot，估完整成本，再凍結正式比較；U2 做一個最小候選 | 設定／PREREG 約 1–2 天；token 需 pilot 後估。每 task／stream 至少 4 rollouts＋3 improvement stages，另加反思、重試、外部評分；不能沿用普通兩組 skill 的 2–4M 估計 |
| P2：證據支持後 | U3 chronological transfer；針對真實大型設計評 EGM；使用者有明確需求時續做 PPT／遊戲／影片能力評估 | 依領域環境、資料與 U1/U2 結果另估，不一次啟動所有領域 |

下一個方法上的具體交付應是 **U1 的最小資料契約與離線驗收案例**：全階段成本、缺失分母、版本身分、候選與證據關係。方法試吃完成前，U2／U3 留在按需設計候選，不增加所有 agent 每次都要讀的規則。

## 8. 本次驗證與限制

已做：讀取固定 SHA 的上游 core／docs／tests，核對 selector、ledger、judge、resume 的邊界；閱讀論文 v1；對照 OAW 現有 intake、eval protocol、self-improvement、CLI 與 branch review。檔案身分與本地連結檢查及獨立文件 review 結果另記 [VALIDATION](VALIDATION.md)。

**Not verified**：Harness² runtime 執行、官方 benchmark 重現、在 OAW 上的品質／token 改善、新欄位端到端管理、PPT／遊戲／影片候選效果。來源研究不能產生 absorb／decline 判詞；產品原始碼、catalog runtime 狀態、frozen 實驗與發佈狀態未因本文件改變。
