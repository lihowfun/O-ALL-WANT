# G5：三項 intake 的獨立重判（2026-11-13）

**三項正式重判都是「沒有結論」；OAW 自己的 code map 也沒有獲得較寬鬆的通過。** 既有觀察保留，但沒有一項完整通過 audit 的六條規則，因此本次不把既有 rows 送進 `eval_stats` 產生新的採納／排除判定。「沒有結論」是證據資格未過，並非 D32 統計類別 `undetermined` 自動換成 `optional`。

| 對象 | 原判 | 本次與原判的差異 | 決定性的缺口 |
|---|---|---|---|
| codegraph vs OAW code map | codegraph 先因「OAW 已有」不收，後因成本、再因 V8 品質排掉；OAW 留可選用 | **改為沒有結論，兩者相同**；不支持 OAW 優於或替代 codegraph | 原決策有競爭者作者介入；ERPNext 沿用已知題與答案；V8 沒有 OAW 組；X1 沒有 codegraph 組，不能拼成直接比較 |
| TokenEconomizer | T/on decline、T2/envfacts not-shown-better；後來 catalog 改 optional | **由經驗性 optional／不收改為沒有結論**；可選安裝仍可是 owner policy | 每設定僅一條有狀態串流；12/12 全對且 loop guard 未觸發；T2 看過 T 結果才選、沿用 N；無獨立長串流樣本 |
| graphify | 排掉（Haiku 錯誤較多），V4 跨家族重評後不變 | **由整包排掉改為沒有結論**；保留 Haiku 的局部風險觀察 | 獨立設計者／決策者的利益衝突紀錄不足；只有四題 code navigation；文件、semantic graph、視覺化不在試驗內 |

這不是將三項改成推薦，也沒有更動 catalog、產品政策或任何舊結果。已吸收的 bounded components 與整包效益判定分開；例如產品 `docs/intake/graphify-map.md:5,46,91` 明示 drawn-map 是獨立實作、先前試吃未量視覺理解，後續 comprehension study 尚未跑。

## 判定基準與來源定位

讀取時的 records HEAD：`6157c5e7f073544065f1a3d0ac1fdd33c6adfb66`；product HEAD：`26e019277e0db8a3d9edad5aa56f10dbe0fe583c`。下列行號以這次讀取的檔案為準；`ACCOUNTING.json` 保存主要輸入 SHA-256。全文沒有公開本機絕對路徑、帳號或 native transcript。

本次 reader／decider 是 OpenAI Codex；本 session 未參與被比較元件的實作、出題、執行或原評分，沒有建立新模型答案。可驗證的精確 model run metadata 未提供，記為 unknown；已讀 audit 與舊結果，**不是對結果盲測的新設計**。本次獨立閱讀能更正裁決，不能事後補成當年的獨立設計或未見樣本。

| 縮寫 | repository-relative 檔案 |
|---|---|
| AUD | [records/audit-2026-11-08/CODEX_AUDIT.md](../../audit-2026-11-08/CODEX_AUDIT.md) |
| DEC | [records/digestion-2026-11-03/ingest/DECISIONS.md](../../digestion-2026-11-03/ingest/DECISIONS.md) |
| CG-P / CG-R | [records/digestion-2026-11-06/taste-codegraph/PREREG.md](../../digestion-2026-11-06/taste-codegraph/PREREG.md) / [RESULT.md](../../digestion-2026-11-06/taste-codegraph/RESULT.md) |
| V-P / V-R | [records/digestion-2026-11-07/validation/PREREG.md](../../digestion-2026-11-07/validation/PREREG.md) / [RESULT.md](../../digestion-2026-11-07/validation/RESULT.md) |
| V8-A / V8-D | [records/digestion-2026-11-07/validation/v8/ADDENDUM-V8.md](../../digestion-2026-11-07/validation/v8/ADDENDUM-V8.md) / [DESIGN.md](../../digestion-2026-11-07/validation/v8/DESIGN.md) |
| X1-P / X1-R | [records/v2.0.1-experiments/X1/PREREG.md](../X1/PREREG.md) / [RESULT.md](../X1/RESULT.md) |
| TE-P / TE-R | [records/digestion-2026-11-03/taste-tokeneconomizer/PREREG.md](../../digestion-2026-11-03/taste-tokeneconomizer/PREREG.md) / [RESULT.md](../../digestion-2026-11-03/taste-tokeneconomizer/RESULT.md) |
| TE2-P | [records/digestion-2026-11-03/taste-tokeneconomizer/followup-envfacts/PREREG.md](../../digestion-2026-11-03/taste-tokeneconomizer/followup-envfacts/PREREG.md) |
| G0 | [records/digestion-2026-11-03/taste-graphify/TASTE.md](../../digestion-2026-11-03/taste-graphify/TASTE.md) |
| GA-P / GA-R | [records/digestion-2026-11-03/taste-graphify/agent/PREREG.md](../../digestion-2026-11-03/taste-graphify/agent/PREREG.md) / [RESULT.md](../../digestion-2026-11-03/taste-graphify/agent/RESULT.md) |
| GE-P / GE-R | [records/digestion-2026-11-03/taste-graphify/erpnext/PREREG.md](../../digestion-2026-11-03/taste-graphify/erpnext/PREREG.md) / [RESULT.md](../../digestion-2026-11-03/taste-graphify/erpnext/RESULT.md) |
| CONF-P / CONF-R | [records/digestion-2026-11-03/codemap-erpnext-confirm/PREREG.md](../../digestion-2026-11-03/codemap-erpnext-confirm/PREREG.md) / [RESULT.md](../../digestion-2026-11-03/codemap-erpnext-confirm/RESULT.md) |
| WEAK-P / WEAK-R | [records/digestion-2026-11-03/codemap-erpnext-weaker/PREREG.md](../../digestion-2026-11-03/codemap-erpnext-weaker/PREREG.md) / [RESULT.md](../../digestion-2026-11-03/codemap-erpnext-weaker/RESULT.md) |

六條資格規則取 AUD:40–45：Design、Cases、Run、Grade、Decide、Report。表中的「部分」不是通過；unknown 也不能當作通過。這是以今日指定的六條規則檢查歷史證據，不宣稱當年已承諾今日所有要求。

共同 yardstick 是 DEC:355–362（D32），重跑一致性是 DEC:344（D31 第 4 點）。產品 `docs/EVAL_PROTOCOL.md` 與 `scripts/eval_stats.py:56,91,109,128,148,161,168,177` 的機械流程是：依題配對、先平均 repetitions，對**題目** bootstrap 10,000 次、seed 20261107；覆蓋率 margin ±0.10、錯誤陳述 ±0.5；每家先 `quality()`、跨家 `agree()`、跨條件 `lowest()`；cost 是逐題 log logical-token 比的 CI，下界 >1.5 才算太貴。每格一次的 floor 必須來自同題庫、同模型的既有重複作答。預設 12 題 ×1、換掉天花板題、排除前至少一個主場條件。機械 grading 不另要求模型盲評。

**先資格、後算式。** V-P:22,43 的舊區間是題內重抽、題目固定；V8-A:20–22 的成本沿用 median ratio。它們不是今日 D32 的題目抽樣與 cost CI。不能把舊 `worse`、`same`、單點 1.72 或兩次 Opus 一致，直接當成新尺下的結果。因資格未過，本次只重算數量、usage 加總與規劃費用，不另算品質／成本 CI。

## 記帳方式與共用資料

`planned` 是當時登記的格數；`started` 列出可見作答或失敗嘗試；`completed` 是有完成 rows；`scored` 是有有效既有評分，不代表通過六條資格。`missing` 保留未完成格、失敗成本、未量主張與缺失角色紀錄。沒有證據的數字是 `null`，不是 0；機械評分的 **model logical tokens=0** 則有明確執行方式支持。

`ACCOUNTING.json` 是歷史盤點格式，逐資料集、arm、stage 保存 observed usage、unknown 與 input hashes。**各資料集重疊，不可相加當研究總數／總成本。** CONF 的 Opus N/G 第一輪八份，就是 GE 的八份；CG 的 N/G/S 是 seeded 舊答案；V4 全部是重評，不是新作答。TE2 也沒有再跑 N。各條件的 `started_all_attempts` 保留 null，避免將僅有成功列的檔案當成完整 attempt ledger。

| 共用 ERPNext 最終視圖 | planned / visible started / completed / scored | answer logical tokens | grading logical tokens（當輪 Opus） |
|---|---|---:|---:|
| Opus 5.5，N/G/S/C，4題 ×3 ×4組 | 48 /48 /48 /48 | 5,031,766 | 267,751 |
| Sonnet 5.5，同上 | 48 /48 /48 /48 | 3,048,777 | 269,802 |
| Opus 4.8，同上 | 48 /**至少49** /48 /48 | 3,347,401 **+ null 失敗成本** | 258,694 |
| Haiku 5.5，補完後同上 | 48 /48 /48 /48 | 7,923,440 | 528,088（A+B，各48份） |

來源是 CG 的 `out-{opus,sonnet,opus48,haiku}/rows.jsonl` 與 grades；最終視圖共 **192 份答案，只有48份是新增 C**，其餘144份是 N/G/S。V4 另有每條件48份 Codex original、48份 reversed，共384個有效 grading attempts，無新答案。original logical tokens 依條件為 840,699／842,034／838,869／846,441；reversed 為 845,381／846,497／838,087／849,818。不是 384 個獨立受測題。

另有 CG 的 99 筆零 token grading attempts（Opus18、Sonnet5、Haiku76；含 Haiku 後補評的失敗）保留在 `grades-not-run-ratelimit.jsonl`。它們是 **not_run grading，score=null**，不算99個零分；最後對應答案已有有效補評。CG-R:106–109,152–154 記錄 quota 與 JSON 問題。格式壞掉的 grading attempt 未有完整逐次收據，其用量是否非零亦 unknown，不能用有效 grades 的小計當 whole-study 總帳。

## 1. codegraph vs OAW code map

### Evidence inventory

- **角色**：原 protocol／解讀／裁決由 Claude 協調者控制，且維護競爭的 OAW map（AUD:3,12,17）。ERPNext 題目由 fresh agent 出，該作者 provider/family、實作介入履歷無完整紀錄；reference 由協調者核對（GE-P:21,23）。V8 作者是 fresh subagent、未使用 codegraph、未看答案（V8-A:8），family 與其 OAW 實作涉入仍 unknown。X1 新題作者是新 Opus subagent，聲明不看 OAW 實作／其他結果（X1-P:45,63）；其中三題仍沿用舊題。評分先 Opus 5.5，後 V4／V8 補 Codex `gpt-6.1-sol` high；是不同 family 的盲評，沒有完整 conflict-of-interest／disagreement adjudicator 紀錄。
- **版本與啟動**：C 是官方 project 安裝 **codegraph 1.6.2**；repo 基準 `f72c9d2efb14454ff4f9fd7b8460abd82f19a287`，npm payload 與 repo commit 相同內容未被獨立證明，只確認版本對應。ERPNext `d9cb9169…`；V8 VS Code `29ad5e7e…`、Opus 4.8 high、Claude Code 2.1.287。原 S 是 `code_index.py` @ `6f2d365`、從 OAW `721b2b7` 取；X1 則 OAW `12799d914ca39a60aced2f677b25599da169291b` 加 skill／policy amendment（CONF-P:18–21；X1-P:55,73；CG-P:20–31）。不可視作未變的同一 arm。
- **凍結**：CG protocol／runner SHA 與題目在新增 C 前登記（CG-P:3,17,83；commit `dde0cd8`），但 N/G/S 和題庫結果已知。NB 是看完結果才加、在自身執行前登記。弱模型、Haiku 第2/3輪也是對應補登後執行。V8 題目／arms 登記 `5904e48`，MCP 修正 `1446c40`，結果 `dbe2cfe`。X1 原登記 `7d35d57`，正式前 amendment `328c8be`，結果 `e261e02`。這證明登記順序，無法證明所有 host 實際載入的 bytes 與獨立利益衝突檢查。

OAW 更早的 Stage0 是39題×R/S兩組的**工具診斷**，不是agent答題：首輪78個serialized cells中，R的39次因shell路徑引號錯誤而未執行，整輪作廢；修路徑後run2有78格，S的5個格式不合依舊規則算失敗。兩輪均0 model tokens，不能把未執行R的零分當能力；作者與題目隔離亦只靠聲明。來源：`records/digestion-2026-11-03/codemap-stage0/RESULT.md` 的「偏差」與「這代表什麼、不代表什麼」；數量另列 `ACCOUNTING.json.tool_diagnostics`。Stage0通過D24不提供D32的agent效益證據。

| 輪次 | planned | visible started | completed | scored／missing |
|---|---:|---:|---:|---|
| ERPNext C 初兩模型 | 24 | 24 | 24 | 24；N/G/S 沿用，不重算新 run |
| C 弱模型首輪（Opus4.8 12＋Haiku4） | 16 | ≥17 | 16 | 16；另一次 Opus4.8 failure 的 usage missing |
| C Haiku 補第2/3輪 | 8 | 8 | 8 | 8；早先未跑8格已補齊（D31 第4點） |
| NB 原生＋Bash | 12 | 8 | 8 | 8；missing=4，預算守門停在第3輪前（CG-R:114） |
| V8 N/C | 24 | 24 | 24 | 24，Opus＋Codex 各24 grades；**沒有 S/M 組** |
| X1 N/M，Opus／Codex 各24 | 48 | 48 | 48 | 48，兩家合96 grades；**沒有 C 組** |

CG 的 food arm **有跑**：ERPNext hook 啟用、MCP connected，但明確 CLI/MCP 呼叫是 **0／48 C sessions**；不能寫成「未安裝」。V8 C 的12次有23次 codegraph tool calls（CG-R:19–22；V-R:115）。X1 Opus M **0/12** 使用 map，Codex M **12/12** 使用、24次命令（X1-R:10–12；rows 重算一致）。這表示 X1 的 Opus 格主要量 policy／可發現性，不能當 map 使用效果。

**成本 stages**：ERPNext C 的48份 answer 共 **5,408,247**；另有失敗 `C q2 repeat2` Opus4.8 的 cost=null。NB answer **1,032,229**、grading **44,495**。V8 answer N/C 合 **2,225,935**、grading Opus **160,473**／Codex **430,683**。CG 歷史 food 小計 **7,634,182** 含 V8 原生，尚未含未知 failure 與 shared costs。真 pilot 是 Sonnet 一次 **43,368**（CG-P:41；local row 相符）。V8 index 的8m54s／2.2GB是索引資源觀察，不是 logical-token 成本。

X1 answer 是 Opus **2,516,752**／Codex **4,472,442**；grading Opus **302,132**／Codex **867,287**。authoring **20,068,719**、Haiku pilots **2,045,818**；X1-P:33–37 另外記載 Codex 成功 pilot N 294,673、M315,192，以及較早被 billing check 擋下但有消耗的 N（用量 null）。X1-R 的24,933,421是 **Claude subtotal**，不能當含 Codex 的研究總成本。controller／獨立 review／部分失敗收據仍 null。

### 六條規則逐條檢查

| 規則 | 判定 | 檔案與行號所示 |
|---|---|---|
| 1 Design | **未滿足** | AUD:3,12,17：比較者維護 OAW；V8-A:8 只有 fresh context 聲明，缺 provider/family、prior implementation involvement 與獨立 evaluator 的完整紀錄 |
| 2 Cases | **部分** | CG-P:11–17：沿用已知題與 N/G/S；V8-D:5–9：4題、三題同 extension-host 通訊，追問拆獨立 sessions；X1-P:59,119：舊題與舊題庫 floor，Codex floor 更借 Haiku（:26）。凍結有據，unseen 與同題庫同模型 floor 不完整 |
| 3 Run | **部分** | CG-P:30,74、CG-R:88–90：N 無 Bash、food 有 Bash；NB 只8/12。CG-R:116,124 failure 未記用量；runner `taste_run.py:72–73` 同名 raw 以 `w` 開啟，retry 覆寫。V8-A:12–16 仍有工具權限差別，未獨立排除其影響 |
| 4 Grade | **部分** | CG-P:44–47 原本同家；V-R:64–80 與 V8-A:18 有跨家族 blind grades。V-R:78–80 記方向分歧，未見獨立 adjudication／兩位 grader 實作涉入聲明 |
| 5 Decide | **未滿足** | CG-R:10–16,81–85：承認依原規則有提升，卻因「OAW 已有」不收；X1-P:133–135 對自家採不同效率與降級規則，不能用自家保留反推外部排除 |
| 6 Report | **部分** | CG-R:103 明示 benchmark protocol 不同、:116 揭 failure；V-R:29 說不能稱 OAW 較好。product `catalog/verdicts.json:34–64` 仍以 V8 worse／ERP cost 支撐 excrete，無 D32 cost CI；未與 policy exclusion 清楚分開 |

### 同尺重判與最小補件

**沒有結論。** 最先缺的是獨立 evaluator 的角色／利益衝突紀錄與未見的成對題庫；跨 V8、X1 拼表不能補出 N/C/M 的同條件比較。X1 的三題已見、九題新題不具有同 bank 的重複 floor，Codex floor 跨模型借用；保守數字仍是已登記例外，不能默認等同 D32。舊 V8 的錯誤數 Opus C15/N7、Codex C24/N12 保留為**該四題的跨家族 adverse observation**，不是整體劣勢或自家勝出。

最小可交付的**窄版**重跑：在 codegraph 主場 VS Code、Opus4.8，獨立設計並凍結12題、references、權限相同的 N／官方C／OAW M、stopping rules；至少含多子系統、真多輪與一次 edit/index 同步任務，不從試跑挑有利案例。先對這12題做 N 各2次 calibration（24 answers，兩家盲評，先鎖 floor），再每題三組各1次 test（36 answers）。pilot 與 test 不共用結果，合 **60 answers／120 grading runs**；這是補齊比較的一個最小具體設計，非保證足夠 power，也不代替所有模型／repos 的廣泛測試。M 未在 VS Code 跑過，安裝與 activation 要先獨立核對，未啟動的 attempt 留帳。

成本依指定公式：真 Sonnet pilot **43,368 ×60 ×1.3 =3,382,704** logical tokens，但 corpus／模型不同，不能當可靠上限。較適切的 planning pilot surrogate 用 V8 N/C 24次：**(2,225,935÷24) ×60 ×1.3 ≈7,234,289**；grading 用 V8 48次 **(591,156÷48) ×120 ×1.3 ≈1,921,257**。合約 **9,155,546**，**另加 authoring／review／controller=null**。這些是估算，不是新的 pilot 或授權。

## 2. TokenEconomizer

### Evidence inventory

- **版本**：實測 `519c65fff990e14480accca8a7629b3befcb7630`，靜態 intake／catalog 頂層仍指 `d58755d849…`；不能把靜態版本當執行版本（TE-P:6、TE-R:11；product `catalog/verdicts.json:152–162`）。Flask `49943b5a…`、Claude Code2.1.310／Opus5.5 high；T/on sidecalls 是 Haiku5.5；T2/envfacts 不呼叫 proposer。兩者 `toolprune_quiet_minutes=0`，official project-scope 安裝。
- **角色與凍結**：fresh **Opus5.5** author，不知道 OAW；14題含 reference patches／hidden tests，base-fail、reference-pass 驗證後排除 t06/t08（patch 不可套用），凍結12題、順序、規則（TE-P:16–18）。這不是漏跑兩題。protocol `3c4c32e` 在 N/T 前，T2 protocol `6d10b05` 在 T 結果後、T2 前。runner 在版本紀錄可追，但 TE-P 只列 task SHA，**沒有 runner／setup／shim 的事前 hash freeze 清單**；不將「規格先登記」誇稱「全部實際 runner bytes 已證凍結」。協調者仍兼設計與解讀，沒有完整獨立 evaluator 的實作涉入聲明。
- **planned / started / completed / scored**：N/T 各12＝24；T2新增12。可見36個 successful sessions、36個有效機械 scores，**missing planned outputs=0**；全都 hidden tests＋既有 suite 通過。T2 與 N 比較雖有24個配對 appearances，N 是舊12份，因此獨立執行總數仍 **36**，每設定只有 **1 stream**，不是每設定12個獨立 stream。
- **food 確有跑**：T/T2 都載入 plugin，envfacts 分別第5／6個 session 起注入；tool pruning 生效，T/on 因 NFS 時鐘偏差，人工 apply 後第8個 session 才生效，T2 local storage 第6個正常生效。付費 proposer **4 calls**；loop guard／judge **0次觸發**是可見觀察，不是它的效益=0（TE-R:16,47–56）。
- **成本 stages**：answer N **2,700,325**；T **2,575,467**；T2 **2,708,350**；proposal sidecalls另 **53,678**（4次）；execution observed合 **8,037,820** logical tokens。authoring **6,539,760**；機械驗證／grading model tokens **0**，但 CPU elapsed 與其他 shared work 未完整收集，whole-study cost=null。舊後段R=1.25／0.98 是 **effective-token** 比（cache加權），不能代替 D32 logical-token CI（TE-R:19,44,68–70）。

### 六條規則逐條檢查

| 規則 | 判定 | 檔案與行號所示 |
|---|---|---|
| 1 Design | **未證符合** | AUD:3,13：協調者控制設計／決策、也選機制吸收；TE-P:16 只證出題者不知道 OAW，不能替代 evaluator 角色與利益衝突聲明 |
| 2 Cases | **部分** | TE-P:3,16–17 有凍結與機械 exclusions；TE2-P:3,18,24–25 看過 T 才選 T2、重用 N。TE-R:59–60 全易題、每設定一條串流；新設定不是 fresh confirmatory baseline |
| 3 Run | **部分** | TE-P:20–38 有 official install、subscription／plugin checks、sidecall shim；TE-R:53 人工 apply 修時鐘。TE-R:49,59 短串流未量 loop guard／長期回本；完整 frozen runner／獨立安裝檢查收據未具備 |
| 4 Grade | **符合已測的機械正確性範圍** | TE-P:17,42、TE-R:17、`verify.json`：base-fail/reference-pass，hidden test＋suite、arm-blind。此處不因缺第二家模型扣分；仍不能證明題目難度／長串流代表性 |
| 5 Decide | **部分／獨立性未過** | TE-P:47–53 是事先明定的後段規則，TE2-P:24–25 是較佳設定規則；但非獨立 evaluator，product catalog 又用 median1.01／same 宣稱 optional，非目前 D32 的 stream 推論 |
| 6 Report | **部分** | TE-R:49–60 誠實列未觸發、改設定、回本與限制；TE-R:3,63 的「不收」與 product catalog:180–187 的 optional，未完整區分 policy 與尚未量到的長期能力 |

### 同尺重判與最小補件

**沒有結論。** 這裡不能對12個 session 當12個獨立題 bootstrap：T 的學習狀態跨 session 累積，而且只有一條串流／設定。36/36 通過可以報 observed success；不能據此證明 quality equivalence，也不把 loop guard 未觸發判成無用。缺的是**獨立、足夠長且可重複的串流，含可鑑別的困難／迴圈工作**，以及重新配對的原生 baseline。單補模型重評沒有幫助。

最小分層方案：若只重判**目前 catalog 的 envfacts 配置**，先凍結一對46-session N/T2 串流作 pilot（92 sessions），保留所有機制狀態／sidecalls／失敗成本；46來自 TE-P:61 所述原研究尺度，是規劃選擇，**不是已證明的最短有效長度**。這對 pilot 仍不足以出正式結論。使用 D32 預設12個獨立單位時，需12對各46-session的 fresh streams，state 每條重設、同條內累積；以 stream 聚合分數／總 logical cost，bootstrap streams，不能 bootstrap sessions。至少一些預先指定的任務確實容許 loop guard／失敗恢復發揮；用已驗證 executable grading，保留難題篩選與停止規則的事前紀錄。若12條 trial 每格只一次，另需同 stream bank／同模型的重複 calibration 來鎖 floor，或預先註冊適用的 repeated-stream 設計。

沒有獨立真 pilot，估價只能把既有36 sessions 當 **pilot surrogate**：unit **8,037,820÷36=223,272.78** logical tokens（含 proposer）。單對 pilot **unit×92×1.3≈26,703,425**；envfacts 正式部分 **unit×1,104×1.3≈320,441,091**；若原 T/on decline 也一起重判，N/T/T2 三組 **1,656 sessions≈480,661,636**。後兩數**尚未含新增 calibration、pilot、authoring／controller**；難題與更長 context 的 unit cost unknown，不能當上限。機械 grading model tokens=0。若要小於預設12個 stream，須先獨立登記有理由的小樣本例外，不能為省 token 把 session 換算成獨立樣本（D31第4點）。這是最小具體主張範圍的拆分，不要求測其他 food。

## 3. graphify

### Evidence inventory

- **版本**：工具層與 OAW-repo agent 試吃是 PyPI `graphifyy==0.9.101`；ERPNext 是 **0.9.102**，官方 `install --project --platform claude`，AST graph、沒有 LLM semantic extraction／community naming。catalog intake commit `8e6a6d2129…` 不等於已驗證的 PyPI payload commit（G0:6；GA-P:9；GE-P:16）。
- **角色**：設計／裁決是維護 OAW map 的 Claude 協調者。6題與ERPNext4題各由 fresh agent 出、不知道參賽工具；family與 prior implementation involvement unknown。ERPNext reference 是協調者核對、沒有另一個 zero-context reviewer（GA-P:16；GE-P:21,23）。最初 grading 是 Opus5.5，同家第二次後才有V4 Codex；fresh grader 不等於獨立設計者。
- **凍結與 food activation**：初工具 adapter `g_arm.py` 看過 R/S 結果才寫（G0:30），不能算事前凍結。後續 agent 題目 hash 先登記；CONF／WEAK runner hash 有核對，amendments 在對應新 runs 前，但已知道舊題結果。OAW-repo G **6/6**、初ERPNext G **4/4** 先跑 graphify query；有裝也有用（GA-R:17；GE-R:17）。後續36個G/主條件答案留存工具紀錄，不能稱 food arm 沒跑。

| 輪次 | planned | visible started / completed / scored | missing 與原因 |
|---|---:|---|---|
| Stage0 工具診斷，R/S/G 各39題 | 117 query cells | 117 serialized tool rows，非model作答 | S有5個、G有1個 format/no-results failure；舊score保留，不能當agent失敗率 |
| OAW repo agent，6題×3組×1 | 18（預算足可加第2輪） | 18 /18 /18 | 條件式第2輪18份沒有跑，因天花板而轉ERPNext；不是承諾36次後丟掉18次（GA-R:22） |
| ERPNext 初 N/G，4題×1 | 8 | 8 /8 /8 | 沒有S，owner原本只准N/G；8份後來進CONF，不另加總 |
| CONF Opus／Sonnet，各3組×4題×3 | 72 | 72 /72 /72 | 8份沿用；新增64份 |
| WEAK Opus4.8／Haiku，各36 | 72 | 初48，後補到72 /72 /72 | Haiku原missing24，預算守門；補登後已補齊（WEAK-R:5–11） |
| V4 Codex 重評最終共用四組 | 192 original＋192 reversed grades | 384有效grading attempts | 只是重評，新增agent answers=0 |

最終ERPNext N/G/S是 **144份**，加早期OAW repo18份＝**162份獨特agent answers**；G 本身 **6＋48=54份**。不把初ERPNext8份、CG的seeded複本、或V4重評再算一次。四個模型條件（Opus5.5、Sonnet5.5、Opus4.8、Haiku5.5）和不同 corpora 也不能合成162個隨機題；ERPNext只有**4個不同題目**。

**成本 stages**：早期OAW agent answer **3,790,470**、grading **105,365**。初ERPNext answer **982,659**、grading **44,711**；CONF view answer Opus **3,763,507**（含該982,659）／Sonnet **2,119,494**，grading **199,779／202,802**。WEAK answer Opus4.8 **2,331,389**／Haiku補完 **5,728,747**，grading **191,935／392,742**。其中 historical graphify food allocation **9,511,482**；該 allocation 包含早期N/S，後期又只算G，不是全研究成本。authoring OAW約3.5M（僅約數）、ERPNext **1,518,689**；probe成本另有紀錄但 controller／獨立 review不完整，總數null。不得把「0 LLM credits建圖」寫成整份研究0成本。

### 六條規則逐條檢查

| 規則 | 判定 | 檔案與行號所示 |
|---|---|---|
| 1 Design | **未滿足** | AUD:3,11,17；CONF-P:6 說OAW已有自己的map，仍由競爭元件維護者設計解讀，缺獨立 evaluator 的完整角色聲明 |
| 2 Cases | **部分** | GA-P:3,16、GE-P:3,22–24題先凍結；G0:30 adapter事後寫；CONF-P:11–12沿用已見4題。GA-R:16、GE-R:16天花板；未換成未見的具代表性題庫 |
| 3 Run | **部分** | GE-P:16 official arm有跑；GA-R:21／GE-R:27 food額外有Bash，權限不完全對等。WEAK-P:14–18、WEAK-R:103的14回合設定實際沒切斷；語料大但文件／visual／semantic主張未跑（CONF-R:72） |
| 4 Grade | **部分** | WEAK-R:12,24同家A/B不能算獨立；V-R:74–79新增Codex，Haiku adverse方向有跨家支持，Opus4.8方向不一致；未見獨立adjudicator／grader涉入聲明 |
| 5 Decide | **未滿足** | WEAK-R:43對自家只描述、當食物「會可選用」；V-R:13,29對自家同樣弱模型風險，仍保留其optional而整包排graphify；沒有獨立同尺decider |
| 6 Report | **部分** | G0:32–33曾撤回過早排除，CONF-R:72明列未測功能；WEAK-R:36–43把Haiku結果合為整包排掉；product catalog:118–145仍列兩次Opus grading，未寫進後補Codex與D32 cost CI |

### 同尺重判與最小補件

**沒有結論。** 缺的是獨立設計、未見且非天花板的 matched N/G/M 題庫與同尺決策；其他 claimed capabilities 仍 **not tested**。Haiku 四題上，原兩次Opus G/N wrong counts **8/3、7/2**，V4 Codex亦有 adverse方向，保留為這個安裝／AST／題庫／模型範圍的警訊。原成本最高1.419是median ratio，不能保證D32 cost CI在1.5內；沒有因此反推optional。

最小 code-navigation 補跑可和前項共用獨立角色／runner檢查：ERPNext **Opus4.8主場＋Haiku警訊條件**，每條件新12題；N、官方G、OAW M的權限一致。每條件24次native calibration＋36次三組test，兩條件共 **120 answers／240 grading runs**。題庫凍結後不得依pilot結果挑題；可用獨立 development bank先排天花板，最終test bank另鎖。這個設計只足以更新code-navigation判定；不能拿來排除文件／semantic／視覺化整包價值。後三種若要裁決，要各自獨立對照／activation／grading contract；現有資料沒有unit cost，估價null，無法憑空說同一小考能補完。

規劃pilot surrogate取既有同模型N/G/S：Opus4.8 **(2,331,389÷36)×60×1.3≈5,051,343**，Haiku **(5,728,747÷36)×60×1.3≈12,412,286**；answer合 **17,463,629**。grading暫以V8兩家48次的unit，**(591,156÷48)×240×1.3≈3,842,514**，合約 **21,306,143** logical tokens，外加authoring／review／controller=null。這些既有run只作估價pilot surrogate，沒有新執行；不是測完整產品的總預算。

## Local recovery、ledger 適用性與驗證

依舊紀錄定位後，也檢查11-13 archive。找到 V8 raw24份、其arm與MCP設定、ERPNext C各條件12份raw、共享N/G/S各條件36份raw，以及TE N/T/T2共36份raw與36份diff。archive的官方安裝log可讀；但清理manifest明列ERPNext／VS Code的 `codegraph.db` 與daemon log已刪，原index bytes不能復核。CG失敗attempt的log找得到，對應raw只剩成功重跑，usage仍null。X1公開48答案／96grades齊全，但PREREG沒有可解析scratch locator；archive也未找到X1 run rows，不能宣稱其native transcripts已復原。WSL早期graphify raw同樣無可解析locator。詳見 `LOCAL_EVIDENCE.json`；沒有把私人原始內容複製進G5。這些是讀取時的presence與provenance檢查，**沒有重演安裝、food activation、模型作答或hidden tests**。

**未硬製 schema-1 bundle，因此沒有 `eval_ledger.py report` 輸出。** 目前rows可盤點legacy outcomes與null artifact，這本身不是障礙（產品`docs/EVAL_LEDGER.md:135`允許legacy identity note）；真正的障礙是manifest每run要求實際凍結的 `input_sha256`／`harness_sha256` 與非null `condition.environment_sha256`（:75–83；`scripts/eval_ledger.py:152–163`）。舊rows沒有完整arm／host環境的事前fingerprint，部分arm定義只在local、且index已刪；也缺answer artifact→grading contract的原始binding、charge IDs／attempt completeness與部分失敗usage。給「unknown environment」字串做hash、或將今天hash的raw／diff冒充原凍結manifest，都會捏造身份。可做的是本附檔的明示legacy accounting；有原始身份收據後可補合法診斷bundle，report仍不會證明六條資格或採納效益。TE須保留`stream`，不能為通過compare改標`independent_task`。

已在Linux、`/usr/bin/python3` 3.10環境、`PYTHONDONTWRITEBYTECODE=1`下完成一次資料盤點與一次self-check。僅執行標準函式庫讀取、加總與hash；未跑product runners、`eval_stats`品質重算、模型重評、food或安裝。重算方式：在G5執行 `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 recompute.py --product-root <product-checkout>`，只更新本資料夾兩個JSON。self-check 修正了少數來源行號、模型數用詞，並把格式壞掉的 grading 用量明確保留 unknown。結果在 `SELF_CHECK.json`：檢查JSON、來源hash、題目hash、分母、成本公式、重複列身份與公開文件路徑衛生；這些檢查不證明native discovery／實驗真實性，也不是模型benchmark。
