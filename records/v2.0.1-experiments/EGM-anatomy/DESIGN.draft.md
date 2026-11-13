# 大型真實文件的 EGM 評估：最小、可停的設計草案

**自然缺陷庫可作候選來源，尚不是已驗證的 gold bank。** 最完整的是 capability 的版本鏈，以及 execution plan 的原稿／兩份獨立 review；H1 另找回 v2 文件和配套程式。FIXCHECK 缺 pre-closure 綁定快照，暫不適合進 primary。後輪因修正才引入的問題不能算早稿的既存缺陷，同一文件五個版本也不能算五個獨立樣本。

**建議只做一份 plan 規模文件的 staged diagnostic，先做兩次 native，通過非 ceiling／可判定性與預算 gate 才做 full EGM。** Claude 完整三臂（N、兩次 N 合併、E）約 **26.69–27.62M logical tokens**；Codex 約 **41.41–45.88M**，分開記帳。加入唯一 trimmed arm T 後 Claude 約 **41.88–44.40M，明確超過每 experiment 30M 上限**。最便宜有意義的停止點是只做兩次 native＋合併／獨立判讀：Claude 約 **2.66–3.60M**、Codex **3.73–4.64M**；它只能告訴我們該 bank 是否又在 ceiling，以及重複 native 的變異，不能判 EGM 的收益。

這些是既有 pilot proxies 的**規劃情境，沒有本次新 pilot**；不是實測新文件單價、保證上界或 confidence interval。若 owner 不接受以單案作診斷，**no change／不花 token** 比將它包裝成有統計檢定力的研究誠實。完整四臂多文件研究目前預算不合適。

## 1. Inventory 與可判定性

數量由 `inspect_bank.py`、`local_bank_inventory.py`、`cost_design.py` 重算，bytes 是 UTF-8 檔案大小，非 tokens。repository 名稱明確區分：records repository 的路徑以 `records/` 開頭；product repository 的路徑以 `docs/` 開頭。每個 snapshot 的完整 commit／SHA-256 見 `bank-inventory.json`、`local-bank-inventory.json`。

| 候選 | 早稿／版本鏈與大小 | 後續 blocking 證據與 independent presence/absence 判讀 | hindsight／contamination／處置 |
|---|---|---|---|
| Capability tasting plan | `records/v2.0.1-experiments/capability/PLAN.md`：v1 `d027959` **94 lines / 6,507 bytes**；v2 `81c00bd` **141 / 13,632**；v3 `a2aed61` **188 / 19,360**；v4 `ea791fc` **212 / 22,621**；v5 `ba4c7f4` **225 / 24,957**，收斂註記 `b3605ba` **225 / 25,170** | `review-1.md` #1–4、6–9、11–12 為 v1 的 blocking 候選；v2 對 `review-2.md` #4、6、9、13、14；v3 對 `review-3.md` #1、5、9；v4 對 `escalation-astra.md` #1。下表逐條說明判讀條件 | sol 做三輪、astra 與 Fable 做 escalation；Codex cell 家族重疊，Claude cell 也有歷史 Claude 作者及 Fable review。v1 本體不大；稱為大型案例必須連同當時必要的工具／需求 context，不可為了「大」灌不相關檔案。v3 可作較難的次順位候選，但只有三個已知 blockers |
| H1 preregistration | git 最早可見為 v4 `c5fd20a`：`records/v2.0.1-experiments/H1/PREREG.md` **328 / 42,926**；後來 amendment 為 `3ac075a`、`777676a`。本機找回 `h1-review/PREREG.v2.md`：**256 / 26,995**；配套 B brief **78 / 5,584**、C brief **59 / 3,749**、runner **1,442 / 77,854**、judge **364 / 16,020** | `H1/review-1.md` #1–11 是 v1 blocking candidates，但本次未找回完整 v1。v2 可對 `review-2.md` #1–11 建 key；很多是 plan＋implementation 契約問題，必須提供同版五檔，必要時補當時 launch metadata／product code。`review-3.md` #1–8 不能自動倒掛在 v2 上 | sol 三輪，astra／Fable 看 v4；同家族 contamination 明顯。v2 可用，但附件多、預算不確定；v1/v3 原文若僅從 transcript 重建，須先逐檔確認，不把 review 的引文當完整早稿。現行 v4 已有答案與 fixes，不能代替 v1/v2 |
| 2.0.1 execution plan | `records/plan-review-2026-11-07/draft-as-reviewed.md`，**324 / 27,907**；原目標為 product `docs/plans/v2.0.1-execution.md` 的當時初稿。原審查工作區仍有 code＋evidence，非只剩 324 行 | `egm/report.json` 的前三條 blocker：catalog wrapper 與既有 installer／政策矛盾、deep review 時序／host checkpoint 契約、TS/JS callers 缺實作。`codex/report.json` 另有 10 major／5 minor，採 **兩份 report 的聯集候選**，先獨立確認 severity、合併同根原因；不能只拿 E 發現的三條當偏袒 E 的 gold | Claude Opus full E、Codex sol native 都已審過；兩格皆 contaminated。公開處置 30 採納、1 部分、2 不改不是 validity label。原 evidence 在當時已存在的即可用；後來 X2、H1 結果、owner 新決定不放入 review context。**建議第一份成本／難度診斷標的**，因唯一有同規模歷史 full-E 單價 |
| D45 release path | product `docs/plans/v2.0.1-release-path.md@e2c3315`，**98 / 7,313**；review 還讀 D45 初稿。修正版 `71b0db2` 不可代替早稿 | `records/v2.0.1-experiments/H1/D45-review.md` #1、#2 blocking：H1 freeze 不容許直接換修正版 product，及整體 pass conditions 不能證明五個機制被觸發；可由早稿＋H1 freeze／原 runner／D45 當時決定判斷。#3–8 另作 nonblocking secondary | sol 一輪，Codex family overlap；Claude 作者亦見過。H1 的結果在 D45 當時已知，這不是 future leakage。D45 **初稿 decision log 的精確版本還需綁定**；僅用已收斂決定會洩答。本體很短，只能算依賴 context 大的次要診斷案 |
| FIXCHECK preregistration | `records/v2.0.1-experiments/FIXCHECK/FIXCHECK.md@4033f52` **84 / 8,639** 是已修正、通過 review 的版本 | `REVIEW.json`、`VALIDATION.md` 記三項已關閉：function false／item true 不一致、偽造 recall 掩蓋失敗、negative session tokens 抵銷。這三項主要在 calculator／mapping，**單給 prereg text 無法評** | sol fresh review 已看過。未找回完整 pre-fix manifest＋calculator＋文件組合，故 **暫不納入**。現行版可作已修反例材料，不能當天然未修缺陷，也不把正在跑的實驗當可修改 fixture |

### Capability 的 item-level eligibility

每條預先寫一個最小成立條件、可接受同義說法及不算命中的邊界；下面只是從歷史 review 轉錄的候選，不是本次重判。

| Snapshot / finding IDs | 已記錄的 blocking mechanism | 新 review 可以獨立判 present / absent 嗎？ |
|---|---|---|
| v1 R1 #1 | N／S 底層工具不一致，skill 效果與引擎能力混淆 | 可以；須指出比較臂工具差異與歸因後果，泛說「要公平」不算 |
| v1 R1 #2 | 全新 home／官方安裝沒有可驗的接線 | 可以；提供當時安裝方案／工具需求。未證明可執行與「確定裝不起來」要區分 |
| v1 R1 #3 | 沿用 H1 不代表 solver 斷網 | 需要同時提供當時 H1 runner 的 `net=True` 與安裝行為；只有「可能連網」不夠 |
| v1 R1 #4 | `pdftotext` 座標不證明完整可見／未遮擋 | 可以；明確指出 clipping／遮擋而非泛說要看圖 |
| v1 R1 #6 | 單一參考成品 PSNR 會錯拒合法替代／放過小區域錯字 | 可以；需符合該版允許的自由度，不能引用後來才加的像素限制 |
| v1 R1 #7 | 整體 LUFS 不能確認旁白、來源時序與混音 | 可以；接受漏旁白但音量合格的具體反例 |
| v1 R1 #8 | 四題門檻矛盾且不足以支撐採用／無效二分 | 可以；偵測互相矛盾規則或具體低檢定力，僅說樣本小列 secondary |
| v1 R1 #9 | 總過題數掩蓋逐題退步／跨格規則不完整 | 可以；須指出能導致錯推薦的具體模式 |
| v1 R1 #11 | 未凍結出題、容差、閒置題、重試等有看後選擇空間 | 可以；至少一條可影響結果的選擇路徑，非要求無限文件化 |
| v1 R1 #12 | 隔離環境可行性與全成本／磁碟證據未建立 | **條件式**；需要當時可行性狀態與依賴。不能用日後 ffmpeg 未安裝等新觀察反推 v1 產品必敗 |
| v2 R2 #4、#6、#9 | 可見性、PSNR、單次 N 的疑似退步仍有缺口 | 各自可以；僅對 v2 文字與當時需求判，與 R1 同根原因須去重 |
| v2 R2 #13、#14 | 剪接／淡出辨識規則衝突；正確字幕軌＋色塊可通過燒入要求 | 可以；這是 **v2 的新規則問題**，不可當成 v1 的兩個額外 blockers |
| v3 R3 #1、#5、#9 | 部分字形差異不證明完整墨跡；1% 全片缺幀可隱藏錯切；保留幀碼但替換主畫面 | 可以；僅把此 v3 當新 snapshot 的 bank，不以「後來 reviewers 發現」當作 v1 就有同樣形式 |
| v4 astra #1 | 非轉場允許任意 gain，普通片段調暗仍能通過 | 可以；這是修前輪時引入／顯化的 v4 契約，不屬 v1/v3 gold |

### H1、plan、D45、FIXCHECK 的判讀邊界

H1 v2 的 R2 #1–11 逐項：全依賴 freeze 缺口、出題／校準順序、核實 reports 未綁內容、逐 fact mutation 不足、node IDs／suite baseline 未固定、固定 budget ledger／事後重檢不足、judge 來源／名單核對不足、large／design 題型判斷不符、答案字串被當 usage limit、model／billing 驗證不足、`bool("false")` 當 true。**各項都能在同版 source＋公開契約內有機械反例**；判「新 review 有沒有提出此反例機制」不需重新執行模型實驗。#1、#8、#10 若缺當時 launch／product 定義則標 `not adjudicable`，不當 absent。v3 的 rounding、atomic resume、重新 freeze、timeout retry 等須先找回 v3 文件和同版 code 才能入 bank；不能因目前 runner 已修就認定早稿沒有問題。

Execution plan 三條 E blockers 的可判性取決於當時的 catalog allow/deny 規則、mode classifier／host instructions、TS/JS caller 實作。必須把這些 code／policy 證據給所有 arms；若 source 在早稿當時存在但工作包沒給，該條不是模型漏檢。把「採納」當附加資訊，不作 grader 的唯一依據。native 與 E report 都要納入 curated candidate union，reviewer 不看它們。

D45 #1、#2 可明確判：是否指出換 product 會與 freeze 打架，以及 aggregate pass 不保證每項 mechanism 實際觸發；「應多做測試」不算。FIXCHECK 三條若恢復 pre-fix calculator，可以判上述精確資料不一致；現在只有 closure summary，沒有足以凍結題目的完整舊件。**沒有完整 early snapshot 的案例，成本表只作假設封包，不排 run。**

## 2. Bank preparation 與污染控制（尚未執行）

以 execution v1 作第一候選；capability v3 作固定的下一順位。不要看新 N 結果後從其餘版本挑最有利 E 的稿件。第一份若 ceiling，止於診斷；若要換題，視為新的預登記留出研究，舊支出仍計入本 experiment，不以改名字重置 30M。

1. 由未參與該輪撰寫／review 的 curator，從**當時文件＋當時 context**建立 item ledger：item ID、source snapshot hash、historical finding／closure ref、可見於早稿的 evidence、severity、同根原因 cluster、反例、acceptable detection、mention-only、hindsight flag。人工工時照記；目前尚未量測。可機械提取檔案、hash、line counts，不呼叫模型造新缺陷。
2. 至少一位獨立人類／非受測 reviewer 核對 bank eligibility；分歧未解的 item 在開跑前排除，不能看新輸出才調 severity。選 execution 的 item 用兩份歷史 report 聯集，不能只保留 E 原本找到的項目。每條若依賴後來新 requirement 或新實驗結果，排除 primary，留 hindsight appendix。
3. 同一 frozen packet 給全部 arms：目標、必要 ADR／原始 owner constraints、固定 product source。不掛 live records、`.git`、later fixes、reviews、grader keys、memory、其他 arms；filename 重新命名但保留私下 provenance map。移除目標自身的 review 回應／修正對照附錄，保留其技術規範原文，逐行 redaction map 凍結。不能讓 parent 繼承本次分析的 context。
4. Fresh workspace、home、session，attempt 也分開；native／EGM 同模型同 effort 同權限。帳本記所有 tools／subagents／model、cache reads、其餘 input、output、unmatched usage、failure attempts、wall time。凍結 pinned EGM 和 OAW invocation digest。
5. 訓練記憶或同家族記憶無法靠 fresh session 證明消失。sol 尤其可能重現自己的舊發現；Claude 亦曾撰寫、審查這些稿件。兩格分層報告，標 `historical-family overlap`；不能把回溯 bank 包裝為完全無污染的新任務。若要晉升為 automatic，仍須將來真正未見文件的 prospective 留出。

本次只做 inventory 與設計，沒有請 curator／grader 重判既有報告。

## 3. Arms：分開回答產品問題與流程問題

| Arm | 固定方法 | 回答什麼 |
|---|---|---|
| N | 一次 native fresh-context review，無 EGM／checklist；輸出 findings、evidence、severity、uncertainties | 現行 product baseline |
| N²＋merge | 完全相同 prompt 各跑 **k=2** 次，fresh context 互不看見；預定匿名 merger 去重、不讀新 source、不發明新 findings，矛盾並列 | 額外獨立抽樣能否得到 E 的收益，即最低限度 more-compute control |
| E | pinned full EGM，uninterrupted 五階段與統一交付 schema；所有 checkpoints／host 邊界照既有 entry | full E 相對 N、N² 的產品品質／成本 |
| T（唯一可選 trim） | ANATOMY 候選 B：既有 Preset 3 implementation-plan-only，保留其正常 S9、split、checkpoint；不改 vendor | 較窄 scope 的流程是否可在 implementation-readiness 工作替代 full；不能泛稱等價 full |

N arm 直接使用 N² 的第一份輸出：一份文件只有 **兩次 native generation**，不是三次。這省成本，也造成已知相依；比較以 document 配對，不能當獨立樣本。merger 是 N² arm 的成本與風險，所有保留／刪除 finding 都留 mapping。人類可另算兩份 N 的 oracle union，僅作上限，不取代實際 merger 交付。

**產品問題**：E 的有效 blocker coverage、錯誤指控、可修復性與人類使用價值是否值得成本？

**流程問題**：同一品質能否由 N² 或 T 便宜取得？E > N、但 E = N²，不支持 EGM 流程有獨有優勢。T 少花錢但漏 feature blockers，也不能稱優化成功。k=2 不是 cost-matched：歷史比例約 27–29 倍，等成本 native 可能要數十次；此最小研究只能排除「多一次 native 就足夠」，不能識別所有更多 compute 的影響。不得用這個控制宣稱已證明多 persona 的因果效果。

盲評新交付：兩位獨立 graders 用凍結 item 定義，先各自判 detected／mentioned-only／absent，unknown＝無法判；unsupported claims 要逐條給來源反證，並分 severe false alarm、合理 uncertainty、nonblocking suggestion。新有效 findings 可以獨立 adjudicate 作 secondary，不能看到它們後擴 primary key。評分者匿名／arm order 隨機，先看統一 schema；結構／閱讀效益另外評，不能為了盲化刪除 E 的主要可用性。若格式使 arm 可辨識，記 blinding failure。

## 4. Cost ledger：每個階段都有帳，現在只有 proxy

所有估算均用 **pilot unit cost × unique runs × 1.3**；1.3 套在 generation、merge、bank／selector／報告、grading／adjudication 的小計一次，不能拿它把超額藏起來。論文／Harness² 的最優化／選擇／反思如果實際使用，亦必須另列；本設計沒有 improvement-rollout 或事後調 prompt，所以這兩項預定 0，任何後來增加都要先過預算 gate。

實際可用的歷史 unit：

- 大型 Claude **E＝18,480,203**：`records/plan-review-2026-11-07/usage.json`，一次 Opus 5.5 high full E，含 17,134,038 cache reads。
- 大型 Codex **N＝1,085,264**：同次計畫 native，high，含 946,560 cached input。不是 Claude N，也不是 Codex E。
- X2 主分析的 **同 cell** E/N：用 median ratio 及 total ratio 兩種縮放，形成情境範圍。Claude N proxy＝18.480M ÷ Claude 自己 E/N，得 **0.674–0.683M**；Codex E proxy＝1.085M × Codex 自己 E/N，得 **28.982–31.721M**。不跨供應商換算 token。
- T 沒有 pilot。Claude 按 X2／plan 可移除 S5–S8 的份額，得到保留工作量 proxy **11.687–12.905M**；Codex 沒有大型 full-E anatomy，採 **11.466–31.721M** 的寬敏感度範圍，最壞不預承諾節省。這不表示 T 的品質不變。

還未量測的每文件操作預留（unit×1 run，再乘 1.3）：merge **0.10–0.20M**；bank／selector／報告 **0.10–0.20M**；grading＋source validation＋adjudication **0.50–1.00M**。這些是**預算 allowance，非 pilot 實測**。記錄兩 grader 各自用量，不能因只計最後裁決而漏掉；跨家族 grader 按實際 provider 進各自帳，Claude provider 的所有用途仍受該 experiment 30M 限制。可用人類雙評使這幾項 model tokens 為零，但人工工時另記、不能稱總成本免費。下列總額先把所有 allowance 放在該 cell 帳內，是保守的可審批規劃；真正 launch 前依 grader 配置再分 provider 對帳。

### 每文件、每 arm 的規劃數字

單位 M logical tokens，**以下已乘 1.3**。除已標不適格者，暫採同一 plan 規模 reference envelope；沒有假設 Markdown 行數與 token 成線性。必要 context 無法容入可比 packet 的文件，必須重新 pilot，不能沿用低價。這比以小文件 1.66M／2.93M 當大型 E 單價保守，但仍不是保證上限。

| Document packet | Claude N | Claude N²＋merge | Claude E | Claude T | Codex N | Codex N²＋merge | Codex E | Codex T |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| execution v1，建議首案 | 0.876–0.888 | 1.883–2.037 | 24.024 | 15.193–16.776 | 1.411 | 2.952–3.082 | 37.676–41.238 | 14.906–41.238 |
| capability v1（含必要 context） | 0.876–0.888 | 1.883–2.037 | 24.024 | 15.193–16.776 | 1.411 | 2.952–3.082 | 37.676–41.238 | 14.906–41.238 |
| capability v3（不與 v1 算獨立文件） | 0.876–0.888 | 1.883–2.037 | 24.024 | 15.193–16.776 | 1.411 | 2.952–3.082 | 37.676–41.238 | 14.906–41.238 |
| H1 v2＋五檔同版 packet | 同上僅作 1× reference 情境；runner／附件可能要求 **2× sensitivity**，見下文 | 同左 | 同左 | 同左 | 同上僅作 1× reference 情境 | 同左 | 同左 | 同左 |
| D45 v1＋當時 H1 context | 0.876–0.888 | 1.883–2.037 | 24.024 | 15.193–16.776 | 1.411 | 2.952–3.082 | 37.676–41.238 | 14.906–41.238 |
| H1 v1/v3、FIXCHECK pre-closure | 不排 run：缺完整 early packet，不能給可信文件單價 | — | — | — | — | — | — | — |

重複數字是刻意的**相同成本情境**，不代表已量到每文件同價。特別是 H1 v2 已知五檔合計 **2,199 lines / 130,202 bytes**，尚未計其他 source；對其 generation 單價另做 2× sensitivity：三臂 Claude **52.46–53.42M**、Codex **81.91–89.94M**，均不適合目前 Claude cap。不是用行數算出兩倍，而是沒有同規模 pilot 時明列的風險情境；若不願承擔，就先不選 H1。FIXCHECK 沒舊 snapshot 時連這種 envelope 都不應被當 runnable estimate。

### 唯一文件的完整／縮減設計

| 設計（unique generations／document） | Claude，M | Codex，M | 可以／不能回答 |
|---|---:|---:|---|
| N1＋N2＋merge＋bank/grade/report；先停的 feasibility screen | **2.66–3.60** | **3.73–4.64** | bank 是否有 headroom、native 抽樣差異；不能比較 E |
| N1＋N2＋E＋merge＋bank/grade/report；三臂最小產品診斷 | **26.69–27.62** | **41.41–45.88** | 此單案 E 是否比一次或兩次 native 有價值；不能一般化到所有大型文件 |
| N1＋N2＋T＋merge＋bank/grade/report；無 full E 的便宜 variant | **17.86–20.37** | **18.64–45.88** | trimmed implementation-only 能否超過 native；**不能回答 full E 的效益或 full→T 等價** |
| N1＋N2＋E＋T＋merge＋bank/grade/report；四臂 | **41.88–44.40，超過 30M** | **56.31–87.12** | 才有同案 full／trim 比較；目前不建議 |
| 兩份獨立文件，各做三臂（同 reference unit） | **53.37–55.24，超過 30M** | **82.82–91.76** | 多一份獨立文件；仍只是小型描述研究 |

不要把四臂拆成多個名字躲過 cap。若要完整四臂，必須明示提高本 experiment 上限；本草案不要求現在批准，也沒有啟動它。最便宜仍能觸及「full E 值不值」的是**單文件三臂**，代價是拿不到 trim 比較及文件間變異。數值由 `cost_design.py` → `design-costs.json` 重算；N1 在 N² 內共享，總額沒有把 N arm 再加一次。

## 5. 順序、決策表與 stop rules

先凍結問題、bank、arms、預算與 scope，再取得資料。**不能以預期 EGM 會贏的方向選題或繼續花錢。**

1. **Offline gate（0 generation）**：early packet／hindsight／family overlap／grader 可判性未完成，停。缺少必要 context 的 item 標 `not adjudicable`，不算模型漏檢。
2. **Native screen（固定 k=2）**：匿名盲評 N1、N2 與 merged 交付。若 primary key 已全被兩次 native 的 union 覆蓋，且 severe unsupported 沒有足夠預登記改善空間，標 `ceiling diagnostic`，不跑 E。只可說此 bank 無法展示該 primary gain；不能說 E 無用。若同義判定一致性不足，先停止花 generation，修 measurement，保留既有支出。
3. **Launch cost gate**：N1 實測後更新 N allowance，E 初始仍以大型歷史 **18.480M × 1.3** 而非 X2 小文件值保留。每次啟動前：spent＋該完整比較 block 尚缺的 generation／grade／report reserve 不得超過 **Claude 30M**。單一 historical unit 不足以保證 cap，須有可觀測 live ledger 和停止程序；若 host 無法追 parent＋child 即時 usage，必須先解決可觀測性，不能承諾守住 cap。硬上限中止結果照記，成本是 observed lower bound／未知 reserve，不免費重抽。
4. **只做一次 E**：不看 outcomes 調 prompt、不換模型重試找好報告、不再開 loop。正常 timeout／超額也是結果；只有結構化 infrastructure failure 可按事前固定最多一次 retry，兩次都計費，且剩餘完整 block 不足預算就停。
5. **T 不自動追加**：30M 版本不跑 T。若預登記的是 N²＋T variant，從一開始就沒有 full E，結論只能談 T。若已有 E 後才想 trim，只留為下一次預先凍結的研究；不能用同份答案調到成功再叫留出。

本單案診斷的成功事件先定為：E 比 **N² 實際 merged output** 至少多抓 **1 個已核實且可修復的 blocker**，兩 grader 獨立確認，且沒有丟掉 N 已抓到的 blocker、沒有新增 severe unsupported 指控。逐 item 列出，不把 1 個 finding 拆成多個 score。這是**實用的 case-level signal**，不是 p 值／population superiority。誤報、nonblocking 建議、額外有效 finding、結構／人類節省時間各自報，不用總篇幅代替品質。

| 觀察結果 | Product：EGM status | Process：成本判讀／下一步 |
|---|---|---|
| E 只贏 N，N² 追平，無 severe false alarm | 保持 explicit opt-in；沒有 EGM 獨有優勢證據 | 若 N² 更便宜，保留它作便宜替代候選；不能說 E 的 stages 有因果收益 |
| E 比 N、N² 多有效 blocker，無 regression／severe unsupported，成本在預定範圍 | 可增列「這類文件值得使用者選用」的受限證據；**單案不改 automatic** | 記每個新增 blocker 的增量 tokens；先用另一份真正未見文件確認，再談擴大 |
| T 與 E 的 blocker 相同且便宜，但只有一案／沒有正式 noninferiority 證據 | 不宣告等價、不改 auto | 可把 trimmed 路線列為待驗候選；需更多文件及 scope 一致的判準 |
| E 沒新增／新增只是 structure 或 uncertainty | 保持 explicit opt-in | 結構效益如有人類量測可另報；不能改寫成 detection gain，也不能宣稱已證明 E 無效 |
| E 增加 severe false alarm、漏掉原生的 blocker | 不擴大使用範圍；保留使用者明確選擇 | 停止該候選的後續支出；保留失敗事件，不加規則追到贏 |
| ceiling、grader 分歧未解、hindsight、缺 context、污染洩答、超額／缺 arm | **無結論**，保留現況 | 報 partial／lower-bound cost；不以剩餘成功 runs 宣稱優越或等價 |
| 將來：多份真正未見的大型文件、相同 scope、相同 host，兩家獨立確認增益及誤報安全，且成本符合 owner 預定門檻 | 才能提出某一受限類型的 automatic 候選，另走產品決定 | 須另有足夠文件樣本／變異估計；本草案的單案、兩格、版本數不能冒充它 |

跨 cell 一勝一敗不以 token 相加投票；每格獨立呈現，再標 scope 未定。現有資料沒有可靠的大文件 variance floor，不借 X2 0.1318 來保證新研究的 power。沒有達成效果證據時，**keep as is 是完整結果**。

## 6. 本次完成範圍

僅離線讀取與設計。沒有模型實驗、EGM、new grading、產品／vendored 修改或 git commit／push／branch／stash；沒有寫進任何受保護的實驗資料夾。成本、版本與 trace 的重算命令在 [REPRODUCE.md](REPRODUCE.md)；所有數字都應連同所屬 protocol、文件規模及未量測 allowance 使用。
