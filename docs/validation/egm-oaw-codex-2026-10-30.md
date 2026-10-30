# Codex 驗收報告：EGM／OAW v1／OAW v2

日期：2026-10-30。Codex 負責本報告；Claude 另交獨立報告。先講結論，詳細數據直接在下方。

| 問題 | 白話結論 |
|---|---|
| V2 至少跟 EGM 持平嗎？ | **歷史 pilot 已測的缺陷、readiness、記憶、交接持平。** 新 installer 的品質尚不能沿用此結論。 |
| V2 比 V1 好嗎？ | **Review 較完整，但 token 約 3.95 倍；記憶和交接沒有贏。** 不能說全面較好。 |
| 為何不直接用 EGM？ | **目前還沒有證明保留 OAW 各層的增量效果。** 已有 bounded recall、wiki、improve 與安全選配功能，但要以配對驗收證明價值。 |

**V2 的產品定義就是整套當前 OAW，已包含 EGM。** EGM 不再是名稱後的另一個附加包。
目前預設啟用七個 EGM skill 入口與 evidence，wiki／improve 可選。使用者可選配、停用與恢復；
不會每個任務都被強制跑 EGM 完整流程。自動覓食、消化、吸收的完整 catalog runtime 仍未實作。

**本頁有兩種不同證據：** 下列模型分數來自 `9ae4eba` 歷史來源，當時由測試 runner 提供 EGM；
最後一節才是本次完整 runtime／installer 的本機驗收。不要把兩者合併成新產品已全面驗收。
「完成 review」不算品質分；先前提到的 V2 4/8 是執行進度，不是正確率。

## 已完成的品質與記憶分數

| 指標 | EGM | OAW v1 | OAW v2 |
|---|---:|---:|---:|
| 已知 critical 缺陷 | 6/6 | 6/6 | 6/6 |
| 已知 major 缺陷 | 2/2 | 2/2 | 2/2 |
| 無來源具體指控 | 0 | 0 | 0 |
| 實作準備缺口覆蓋（事後稽核） | **14/14** | **2/14** | **14/14** |
| 其中 major readiness 缺口 | 2/2 | 0/2 | 2/2 |
| 主 memory 精確 business fields | 64/64 | 64/64 | 64/64 |
| 新 agent 的 ticket 保留／更新 | 4/4 | 4/4 | 4/4 |
| 同 snapshot receivers 精確 fields | 48/48 | 48/48 | 48/48 |
| 同 snapshot receivers pairwise agreement | 48/48 | 48/48 | 48/48 |
| 三名 receivers 一致且正確的 snapshot | 2/2 | 2/2 | 2/2 |
| 引用與接手前證據支持 | 雙評分通過 | 雙評分通過 | 雙評分通過 |

不是只有回答完就算：缺陷必須指出來源及失敗情境；記憶逐欄查 scope、revision 和 provenance。
36 份 memory／receiver 報告的 288 個 business fields 由兩位獨立盲評者查核，無引用問題或捏造事實。
主 memory 和 receiver 對照共用原 S2 的觀察，不把重複觀察當成更多獨立樣本。

### 每個已知缺陷

| 根因 | 嚴重度 | EGM | v1 | v2 |
|---|---|---:|---:|---:|
| K1：global request_id 導致跨 tenant 回傳別人的 settlement | critical | 2/2 | 2/2 | 2/2 |
| K2：28 天無 archive 刪除，違反 41 天 reconciliation | major | 2/2 | 2/2 | 2/2 |
| M1：舊事件 unconditional overwrite，version 會倒退 | critical | 2/2 | 2/2 | 2/2 |
| M2：計畫記錄 Authorization，違反已接受的 credential 禁令 | critical | 2/2 | 2/2 | 2/2 |

四個不同根因，各重複兩次；不是八個不同缺陷。三組皆抓到，所以原二元偵測指標有 ceiling，
無法只靠這一欄判誰 review 最好。兩位 primary graders 對全部偵測及具體誤判一致。

### Review 是否真的幫人準備實作

第三位不知道組別的 source auditor 把額外觀察按根因去重，再排除兩項純方法／呈現偏好。
以下每個根因在兩個 repeat 各有一次機會：

| 實作準備缺口 | 嚴重度／界線 | EGM | v1 | v2 |
|---|---|---:|---:|---:|
| reserve／receipt／commit／ack／index 順序、同 pair 併發與 timeout recovery | major readiness；不是已觀察 production race | 2/2 | 0/2 | 2/2 |
| kestrel correctness／fallback／load 等測試缺具體輸入與斷言 | minor | 2/2 | 0/2 | 2/2 |
| kestrel expansion 前通過哪些 checks 未具體化 | minor；已有 Done 條件 | 2/2 | 0/2 | 2/2 |
| logging 計畫與 code 證據界線 | minor；code 回傳 header 不證明已有 sink | 2/2 | 2/2 | 2/2 |
| hot／archive／history／restore 缺可執行細節 | minor；已批准 archive 不能當不存在 | 2/2 | 0/2 | 2/2 |
| writer disable／checkpoint／restore／resume 缺操作細節 | minor；trigger、owner 已存在 | 2/2 | 0/2 | 2/2 |
| marble reorder／duplicate／outage／load 測試缺輸入與預期 | minor | 2/2 | 0/2 | 2/2 |

**EGM／V2 確實展開了 V1 沒展開的實作問題。** 但這是看完輸出後建立、再由來源稽核支持的
探索性指標，不能改稱事前登記主指標，也不能當成已減少 production bugs 或人類工時。
沒有額外 major／critical product bug；major readiness 指的是未解的實作契約。

原兩位 graders 的額外觀察數是 EGM 13／13、v1 0／0、v2 9／10。
這是逐報告分組數，受拆分方式影響，不是獨立缺陷數。R06 爭議經第三人裁決為四項 grouped
observations；拆成根因時另有 method／readiness 之分。裁決沒有改變 primary 偵測或誤判分數。
新協議預先固定 readiness 與 evidence／safe remedy／concrete acceptance test 共 15 格，
後續必須收新輸出，不回頭把這批答案當成事前驗收。

## Token：品質先比較，用量再比較

### 完整 review workflow

| 實測 usage | EGM | OAW v1 | OAW v2 |
|---|---:|---:|---:|
| Input（包含 cached） | 2,734,505 | 698,744 | 2,755,983 |
| Cached input | 2,397,568 | 580,992 | 2,405,120 |
| 未快取 input | 336,937 | 117,752 | 350,863 |
| Output | 33,752 | 7,793 | 33,926 |
| **Input＋output** | **2,768,257** | **706,537** | **2,789,909** |
| Fresh CLI processes | 16 | 4 | 16 |

EGM／V2 每份 implementation-only review 含三名 fresh reviewers 及一名 fresh synthesis；
v1 使用其單一 review 流程。所有指定 worker／synthesis 用量都計入一次。
因此比較的是各自 workflow，**額外算力沒有被隔離**，不能把差異全歸因方法。
V2 比 EGM 多 **0.78%**，比 v1 多約 **295%（3.95 倍）**。
V1 較省 token 是事實；其 readiness 也較少，不能直接說整體最好。

### 其他工作用量分開列

| Logical input＋output | EGM | OAW v1 | OAW v2 |
|---|---:|---:|---:|
| 主 memory 8 sessions／組 | 1,986,046 | 2,366,784 | 2,013,603 |
| 額外四名 snapshot receivers／組 | 902,355 | 1,229,922 | 1,144,718 |
| 主 review＋memory 合計 | 4,754,303 | 3,073,321 | 4,803,512 |

額外 receivers 的 input／cached／output 分別為：EGM 895,014／780,672／7,341；
v1 1,219,515／1,112,960／10,407；v2 1,136,108／982,656／8,610。
主 review＋memory 的 input／cached／output 分別為：EGM 4,703,553／4,138,624／50,750；
v1 3,045,186／2,666,112／28,135；v2 4,750,720／4,180,736／52,792。
主輪 output 內含的 reasoning 分別 3,747／1,131／4,113，沒有重複加到總 token。

這些是 CLI actual usage，含共同 IO 健康檢查、system／tool context。不能扣除猜測的 overhead，
不能當 native plugin 的 production 成本。Cached input 仍計入 logical token，不冒充全部付費 input。
沒有推算美元；沒有 API-key 外部付費呼叫，使用的是使用者授權的 Codex 額度。
不同工作量的混合總和不拿來選 universal winner；未記錄完整 controller／評分開銷為產品成本。

## 方法、來源與失敗資料

- EGM：manifest 0.1.0，Apache-2.0，`f0ba151b252c9abf1318d9fe857a43265d06de89`。
- OAW v1：`5df531372330f6b0e1c9a81aee0c1c45f2f283ff`；實際歷史 installer。
- 本批 OAW v2：`9ae4eba01b948057efb8294df061dd995d03fc6e`；runner 提供同版 EGM。
- Codex CLI：0.164.0-alpha.11.1；requested `gpt-6.1-sol`／medium；provider 精確 revision 未回報。
- Review：kestrel／marble × 2 repeats × 3 組＝12 final reports。Implementation-only Stage 9，
  沒有宣稱已跑 EGM 全部五階段。工作者不同 context，不看其他 trial 的答案。
- Memory：larch／pumice × 4 fresh sessions × 3 組＝24 sessions。S1 只在 prompt 得到 ticket，
  留持久檔；S2 換 agent；S3 加 superseding ADR；S4 再換 agent。同 scope decoy／40 份 history／
  假 SYSTEM email 各組相同。兩條是同結構參數化軌跡，不是兩種獨立 failure families。
- 每個 S1 snapshot 額外派兩名 fresh receivers，共 12 次。與原 S2 合成每 snapshot 三名 receivers。
  逐欄正確率和彼此一致率分開算，三人同錯不算正確。
- 有效輪共有 72 fresh CLI processes；原始來源保護、每次未知 nonce 的真實讀寫、成功工具事件與
  完整 usage 均有驗證。12 final reviews、24 memory sessions、12 額外 receivers 齊全；這些是完整性。

首批 cohort-v4 因 CLI approval policy 擋住實際讀檔而整批無效；exit 0／JSON 不等於 review。
50 筆已知 completed usage 合計至少 **6,873,233** logical tokens，另兩筆取消用量未知。
該輪全部排除品質和效率比較，失敗成本另留。修正為正常 sandbox＋automatic approval review，
先驗 canary，再於每個呼叫驗 IO；無 permission bypass、無自動重試。
舊輪在只看用量時調過 budget，之後整輪失效；不將它的輸出補進新輪。

原始報告、雙盲評分、裁決、前後 snapshots、來源 hashes 與失敗 logs 保留在工作區
`review-fixtures/three-way-2026-10-30/`，供本機獨立 review。公開 repo 不放原始本機 traces。
協議與 scorer 在 `evals/three-way/` 保留，歷史 frozen spec 未重寫。
這不是統計等價、7／30 天記憶、跨主機重現或真實工程師效率證據。

## 本次 V2 完整整合的產品驗收

產品 source commit：`341b45014afd37f54f16e254452f9586e9d1b04f`。

V2 現在內含 65 個原始 upstream runtime 檔案、七個原生 skill bridges，以及 Claude 的九個
native agent adapters。上游 bytes 不改寫；Apache-2.0 與 commit／逐檔 hash 一起保存。
Project runtime 路徑與 plugin namespace 由 adapter 明確綁定；保留原有工具和 fresh-context 限制。

本機完整 gate：**9/9，169 tests、0 skips**（Windows，Python 3.12.14）。包括：

- runtime 缺檔、竄改、自改 provenance、未列出的檔案、生成 adapter 被改，均拒絕。
- Codex／Claude／both 的預設、精確／空配方、重啟、冪等、停用 preview 及備份。
- 客製 SKILL 阻止整包刪除；客製 native agent 不誤刪；明確 keep-custom 後持續保護，
  並 WARN「配方外仍有可呼叫入口」，不能冒稱 ablation 已停用。
- 專案記憶／policy／外來 skills 保留，symlink／junction／路徑／並行／rollback 回歸。
- manifest 欄位缺漏仍須驗完整 runtime；預覽後 ownership 被更新會拒絕舊 plan。
- 客製 Claude EGM skill 留存時保護其 native agent 相依，Windows YAML／SVG 固定 LF。
- 歷史實驗透過封存舊 source 驗證；拿現在 source 跑舊 contract 必須拒絕，沒有改舊 hash。

這證明本機封裝與 lifecycle 行為，**不等於 native host discovery 或模型效果提升**。
新共同協議檔為 `docs/SHARED_ACCEPTANCE_PROTOCOL.md`；Codex 與 Claude 各自執行、各自報分，
新分數與本頁歷史分數分開。完整技能推薦／消化 runtime 仍是待開發項。
本輪維持 Draft PR；不 merge、不 tag、不 release，舊版恢復點保留。
