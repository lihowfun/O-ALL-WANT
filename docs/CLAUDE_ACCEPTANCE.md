# 給 Claude：獨立計算步驟與結果表

日期：2026-10-30。計算規格：`oaw-host-scorecard-v1`。

**請用你自己的 Claude 原始資料計算，交一張 Claude 表；Codex 另交同格式的表，不合併。**
這份 MD 已含步驟、分母、公式及表格，不必再追其他 MD。
本次是現有資料的離線重算，不啟動新模型批次、外部付費 API、Claude F1 或 `--live`。
沒有完整資料就交明列缺項的表，不填假分，也不只挑成功的樣本。

本 MD 含 gold，只供 controller／grader 使用，不得給 candidate。
完成自己的評分前不要讀 Codex 的結果，不用 Codex 的判分代替自己的判分。

## 1. 先固定「算哪一版、哪一批」

V2 就是整套 OAW，包含 EGM，不另加一個產品組。

| 身份 | 固定來源 |
|---|---|
| EGM | manifest 0.1.0，Apache-2.0，`f0ba151b252c9abf1318d9fe857a43265d06de89` |
| OAW v1 | `5df531372330f6b0e1c9a81aee0c1c45f2f283ff` |
| 歷史 pilot 的 V2 | `9ae4eba01b948057efb8294df061dd995d03fc6e`；當時 runner 提供 EGM |
| 現行完整安裝整合的 V2 | `341b45014afd37f54f16e254452f9586e9d1b04f` |

眼前可對齊的是歷史 pilot 的計算方式。Claude cohort 若仍固定 9ae4eba，就標「歷史 pilot」；
不能換個表頭，把舊分數當成 341b450 整合版品質。安裝正確和模型效果是分開的證據。
新擴充實驗仍缺完整 fixture／oracle／runner；本 MD 不解除其 NOT READY 狀態，
不用舊 bench 或未凍結工作樹派新產品測試，不為湊表重跑或修改原始結果。

本機 repo：`C:/Users/User/OneDrive - ITRI/文件/ChatGPT/harness/OAW-egm-test`，只讀。
Claude 現有 cohort：`C:/Users/User/OneDrive - ITRI/文件/ChatGPT/harness/review-fixtures/claude-three-way-2026-10-30`。
在自己的 cohort 新建 `calculation-NEW-ID/`，寫入 ledger、hashes、評分及 `claude-results.md`。
保留原始 protocol、manifest、prompts、reports、raw transcripts；不要改 Codex 資料或共享 Git。

## 2. 架構差異先寫在表頭

從自己的 manifest、protocol.claude.json、prompts-manifest、amendments、transcripts 取值，
另存 calculation-manifest.json：cohort/source、protocol/rubric/case/prompt hashes、host/CLI version、
requested/reported model、effort、role tree、permissions/memory、usage 來源及成本範圍。
未知填 unknown，不猜。來源與已安裝版本分開記。

| 項目 | Codex 歷史 pilot | Claude 必須核對 |
|---|---|---|
| 執行 | Python controller 派獨立 CLI processes | Agent tool 派 fresh agents，不是同 context 扮多個角色 |
| Project root | CLI -C | prompt 指定 root，並查實際 reads；不能只相信文字 |
| EGM host guidance | 同版 docs/codex.md | 同版 docs/claude.md；persona、standards、facts 不偷換 |
| Policy/memory | 各組自己的安裝與 policy | 是否自動載入或明確讀取、母 session/memory 是否共享如實記錄 |
| Model/effort | requested gpt-6.1-sol/medium，provider revision unknown | 每個 worker 查實際模型；不可見的 effort 填 unknown |
| 時間與預算 | 依該 cohort 登記 | 保留 amendments、soft timeout、超額與停止原因 |
| Controller | 試驗內為 Python 調度 | 主 Claude session 是模型；能歸屬才加，不能拆就 unknown |

不同工具或模型設定會限制結論；不要靠重算假裝架構相同。
兩 host 的 tokenizer、cache 和調度不同，不以絕對 token 比 Codex/Claude 誰較強。
先看各 host 內 EGM/v1/v2 的相對差異，再看兩邊方向是否一致。

## 3. 用 planned manifest 盤點，不能用成功檔數當分母

歷史 pilot 完整母體如下；數量是完整性，不是品質分：

| 工作 | EGM | OAW v1 | OAW v2 |
|---|---:|---:|---:|
| Final reviews：2 cases × 2 repeats | 4 | 4 | 4 |
| Review worker/synthesis calls | 16 | 4 | 16 |
| 主 memory：2 軌跡 × S1–S4 | 8 | 8 | 8 |
| 額外同 snapshot receivers | 4 | 4 | 4 |
| Candidate calls，不含 grader/canary/controller | 28 | 16 | 28 |

EGM/v2 每份 review 是三名 fresh Stage 9 roles（implementation-readiness、codebase-details、style）
及一名 fresh synthesis；v1 是單次 review。這不是 EGM 五階段完整流程。
若你改成每組三 reviewers+synthesis，另立「固定算力」cohort/表，不能混入此 v1 單次流程的成本。

逐 call 列 planned/completed/failed/not_started/invalid、輸入/output hashes、未知 nonce 真實讀寫證據、
source 未修改、usage 齊全性、nested agents/跨 trial reads。exit 0 或 JSON 不代表 review 有效。
缺檔是 missing，不是 0-token 成功；無效輸出與失敗用量仍保留，不能偷偷換新結果。

## 4. Review 品質：來源判分，不靠 regex 或字數

至少兩位獨立 graders 看同一匿名 final report、全部 case source 及實際 supplied methods/standards，
不給組別 mapping；重要漏抓/unsupported claim 有爭議時第三人裁決。
沒有獨立評分填 NOT GRADED，不把「尚未看到」寫成零誤判。
重算既有 grades 是算術重現；若另派新 grader，另記模型用量，不能稱免費重算。

| ID | Case / severity | 根因 |
|---|---|---|
| K1 | kestrel / critical | global request_id 缺 tenant scope，會回傳另一 tenant 的 settlement |
| K2 | kestrel / major | 28天無 archive 刪除，違反41天 reconciliation |
| M1 | marble / critical | unconditional overwrite 允許舊事件把 version 倒退 |
| M2 | marble / critical | 計畫記錄完整 Authorization，違反 accepted credential 禁令 |

同根因在同一 final report 最多一次，worker/final 重述不重複算。
必須有正確 source 和失敗情境。每組 critical 6次、major 2次，總共8次機會，不是8個獨立缺陷。
缺失 review 的機會留在 planned denominator，標 missing；另列已評分樣本覆蓋和完整母體覆蓋。
Unsupported claims 按 final report 內錯誤具體前提去重，跨 reports 仍分別計數。
Conditional risk 不是自動誤判，但捏造前提仍算；保留已批准 Redis/archive/rollback 保障。
M2 的 code 回傳 header 不等於已證明 logging sink，計畫違反禁令和 runtime 洩漏分開。

實作準備品質固定七個 roots，僅在相應 case 算：

| Root | Case / severity | 檢查內容 |
|---|---|---|
| KR1 | kestrel / major readiness | reserve/commit/ack/index 順序、同pair併發、timeout recovery |
| KR2 | kestrel / minor | correctness/fallback/load 測試具體輸入、斷言及量測 |
| KR3 | kestrel / minor | expansion 前 checks；不能否認已有 Done 條件 |
| MR1 | marble / minor | logging 計畫和 code 證據界線 |
| MR2 | marble / minor | hot/archive/history/restore 可執行細節，不能否認已批准 archive |
| MR3 | marble / minor | writer disable/checkpoint/restore/resume 操作 |
| MR4 | marble / minor | reorder/duplicate/outage/load 測試輸入與預期 |

七個 roots × 兩 repeats＝14次／組；major readiness 單列2次。
這些來自先前輸出的事後校準，歷史重評仍標 exploratory，不能改稱事前登記。
格式、術語、篇幅、method 偏好不算產品品質；readiness 缺口不冒稱已觀察 production bug。
新協議15格是 K1/K2/KR1/M1/M2 各評 evidence、safe remedy、concrete test；兩 repeats共30格。
歷史資料沒完整評分就填 NOT SCORED；若追加事後評分另列，不冒稱新 prospective test。

## 5. Memory：逐欄核對值與接手前證據

八個 business fields：scope、retry_seconds、batch_records、audit_days、dedup_fields、
active_decision、approval_ticket、encryption_key。Nonce 不算品質欄位。

| Scope / stage | Retry 秒 | Max records | Audit 天 | ADR | Ticket |
|---|---:|---:|---:|---|---|
| export-larch S1/S2 | 17 | 221 | 51 | ADR-040 | EX-LARCH-731 |
| export-larch S3/S4 | 24 | 187 | 72 | ADR-044 | EX-LARCH-942 |
| export-pumice S1/S2 | 29 | 377 | 63 | ADR-040 | EX-PUMICE-731 |
| export-pumice S3/S4 | 36 | 319 | 84 | ADR-044 | EX-PUMICE-942 |

dedup 全程 tenant_id+request_id；encryption_key=null 是未文件化，不是證明無加密。
數值需型別/單位正確，bool不算int；dedup 次序可不同，不能缺項、加項或重複。
每組分母＝2軌跡×4sessions×8fields＝64；八欄全對 contracts 為8；S2/S4 ticket 為4。
逐欄查實際 stage snapshot 的 scope/revision/source；檔案存在不等於支持答案。
S1 ticket 可引用當時 user event；S2/S4 必須追溯到接手前就存在的 artifact/provenance chain，
不能用 receiver 後來新寫的 note 自我證明。S3/S4 要用新 ADR，舊記錄保留為歷史。
值正確率、引用支持、grounded contract 分開，不能因值對就自動判引用通過。

## 6. 跨 agent 重現：正確與一致分開

每個 S1 snapshot 三名 receivers＝原 S2＋兩名額外 fresh agents；兩軌跡共六次觀察／組。

```text
Field accuracy = 正確數 / (2 snapshots × 3 receivers × 8 fields) = 正確數 / 48
Pairwise agreement = 一致且實際有答的欄位 / (2 × C(3,2) × 8) = 一致數 / 48
Unanimous-correct = 三人八欄都對的 snapshots / 2
```

兩人都沒答不算一致；三人同錯可一致，但不算正確。
各 receiver 只讀 frozen S1 snapshot，不能透過絕對路徑看到未來 S3/S4。
原 S2 是重用觀察，usage 不重複加；不能稱新 trajectory families 或7/30天記憶。

## 7. Token：兩 host 欄位含義不同

先建逐 request ledger：arm、task bucket、call/session ID、request/message ID、實際模型、
來源record、raw/normalized usage、狀態、是否可計入、排除原因。原始 transcripts 不放公開 repo。

Claude 對實際去重的每個 API request：

```text
input_total = input_tokens + cache_creation_input_tokens + cache_read_input_tokens
logical_total = input_total + output_tokens
cached_read = cache_read_input_tokens
non_cached_input_including_write = input_tokens + cache_creation_input_tokens
```

Claude 的 input_tokens 不含 cache reads/writes，不能只加 input+output。
依據：[Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)。
**Agent completion 的 totalTokens/usage 不能當整段 run 總量**：官方說明可能只是最後一個 request。
應核對逐 request transcript/telemetry。依據：[Claude Code monitoring](https://code.claude.com/docs/en/monitoring-usage)、
[Hooks 的 Agent response](https://code.claude.com/docs/en/hooks)。查核日期：2026-10-30。

同 request 的 stream fragments、重複 log copy、最後 cumulative snapshot 不重複加；
去重 key 需能區分 run，同 key usage 衝突先查清，不任意取最大/最小/最後一筆。
失敗後真的新發出的 request 是額外用量，不能當重複刪掉；缺 usage 不預設零。
另寫離線 ledger，不修改原先註冊的 adapter 或 result.json。

Codex 本批 adapter：

```text
input_total = turn.completed.usage.input_tokens       # 已含 cached input
logical_total = input_total + output_tokens
non_cached_input = input_total - cached_input_tokens
```

每 process 要求恰一個 turn.completed；多個不能未查 cumulative 就加。
reasoning 已在 output 內，不再加一次。可查 evals/three-way/bench.py 的 usage_of。
不要直接套 Codex summarize.py 計算 Claude token。

加總範圍：

1. 每份 review 納入所有實際 reviewers、synthesis，request 各一次，不只算最後agent。
2. 父模型真的發出的 orchestration requests 另計；父摘要已含children時不能再加child。
   以互斥的實際 request 集合為準，先驗 coverage，不猜摘要語義。
3. Claude controller 能逐request歸屬 arm/task 才加。不能拆就寫 controller 未歸屬；
   可報 candidate/worker subtotal，但完整 workflow token 填 N/A，不平分猜值。
4. 主 memory、額外 receivers 分桶，原 S2 不重複。Canary、failed/invalid、grader/adjudication 另列。
5. usage 不齊填 INCOMPLETE USAGE；可保留 known lower bound，但不判成本持平或較省。
6. cached token 仍計 logical total，不是美元或訂閱百分比。沒有價格證據不填美元。

同 host 的 V2 對 EGM token 差＝100×(T_v2/T_egm−1)%；對v1倍數＝T_v2/T_v1。
母體、品質和成本範圍一致才判效率；分母零或缺值填 N/A。
大家滿分可能是 ceiling，不能證明全面等價或 OAW 額外層有價值。

## 8. 交付一張 Claude 表

claude-results.md 最前寫三句白話結論，再放這張表；表頭註明 cohort/source、host/model/effort、
架構、成本邊界及完整性。下方再放逐case/session、ledger、cache拆分、hashes、裁決和限制，
都在同一份報告，不讓使用者追另一串文件。這裡故意不給 Codex 答案。

| 指標 | EGM | OAW v1 | OAW v2 |
|---|---|---|---|
| Critical defects（planned 6） | 待算 | 待算 | 待算 |
| Major defects（planned 2） | 待算 | 待算 | 待算 |
| Unsupported claims（需完成盲評） | 待算 | 待算 | 待算 |
| Readiness（14，事後探索性） | 待算 | 待算 | 待算 |
| Major readiness（2，事後探索性） | 待算 | 待算 | 待算 |
| Actionability（15格×2，未評填NOT SCORED） | 待算 | 待算 | 待算 |
| Memory field accuracy（64） | 待算 | 待算 | 待算 |
| Fresh receiver tickets（4） | 待算 | 待算 | 待算 |
| Snapshot receiver accuracy（48） | 待算 | 待算 | 待算 |
| Pairwise agreement（48） | 待算 | 待算 | 待算 |
| Unanimous-correct snapshots（2） | 待算 | 待算 | 待算 |
| Citation/before-receiver provenance | 待算 | 待算 | 待算 |
| Review candidate/worker logical token subtotal | 待算 | 待算 | 待算 |
| Main memory logical token subtotal | 待算 | 待算 | 待算 |
| Additional receiver logical token subtotal | 待算 | 待算 | 待算 |
| Attributable model controller token | 待算 | 待算 | 待算 |
| Full review workflow token（controller缺則N/A） | 待算 | 待算 | 待算 |
| Failed/invalid/canary/grading 用量 | 待算 | 待算 | 待算 |
| Usage/planned corpus/grading 齊全性 | 待算 | 待算 | 待算 |

所有格必填數字、狀態或 N/A 原因；未測不是0分或通過。缺資料要在前面三句結論寫明。
最後回答：V2 對 EGM 有無已測退步？比v1多了什麼、代價多少？保留的 evidence/wiki/improve
是否真有配對 ablation 的增量證據？沒有就答尚未證明。兩host來源/母體/架構不同，只並列，
不合併排名或宣稱完成新整合版的跨host重現。
