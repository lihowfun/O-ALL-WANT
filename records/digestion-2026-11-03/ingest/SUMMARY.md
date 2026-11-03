# 本輪消化摘要：TokenEconomizer、claude-mem、graphify（修訂 3）

| 項目 | 內容 |
|---|---|
| 日期 | 2026-11-03（修訂 3：依兩份金魚盲審的 42 條意見修正，見第 11 節；修訂 2 的紀錄見第 10 節） |
| 狀態 | **no paid test run; every behavior not measured.** 沒有實作任何東西，沒有安裝任何東西，也沒有跑任何付費測試。所有效果都是 not measured |
| 身分 | Elephant 草稿。第 2 版已經由兩個金魚盲審（2026-11-03），但兩者都是**繼承上下文**的審查（收到使用者的 auto-memory 索引，其中一個還收到 oaw-ref 的 CLAUDE.md 和 AGENTS.md），不是 D10 要求的零上下文。修訂 3 處理完它們的意見；PRE-02 還要用 PRE-06 的零上下文方式再審一次修訂 3，之後才交給你核准任何批次（D10）。一頁的決策清單在 `ingest/OWNER_SHEET.md` |
| 食物 | `microsoft/TokenEconomizer@d58755d849cd9157d29aef539f2beab3d5fee0fc`、`thedotmack/claude-mem@02584c4ac9d92fea45adf5c61e22c546b5738621`、`Graphify-Labs/graphify@8e6a6d2129d4aeffc7a0e9ed79b153f7f057f42b`，全部只讀、從未執行 |
| OAW 參照 | `oaw-ref` @ `fc5fda1`（origin/codex/oaw-2-native-upgrade，VERSION.json 2.0.0 proposed，尚未打 tag） |
| 標準紀錄 | `ingest/backlog.json`（第 3 版，60 項）；`ingest/<food>/components.json`（`ledger_revision` 2，每個元件的 `after_integration`；`cm.recall-data-fence` 的第 3 版更新還沒做，見 backlog `foods.claude-mem.ledger_after_revision_3`） |

## 1. 一句話

三份食物都**不整包吸收**。拿的是方法，全部用標準函式庫在 OAW 既有腳本或 catalog 計畫裡重寫：graphify 補「程式碼引用檢查」和「反查哪些筆記引用了這段程式碼」；claude-mem 補 recall 的 index／file 模式、寫入時的憑證與私密標籤守門，以及讓 A/B 不能空轉通過的規則（recall 的資料聲明改列保留，先跑 A/B）；TokenEconomizer 補量測方法（快取加權 token、額外開銷、Windows shim）。**沒有任何一項有實測的增益**，上線一律寫「parity, no improvement claimed」；三份食物對「只用食物本身」的 D2 下限都是 **not tested**，下限組都已設計，但都有執行條件，可能長期不跑。

## 2. 各食物帳本（整合後）

「單位」：沒拆開的元件算一個；被拆成「機制」和「影響模型的那一行」等部分的元件，每個部分各算一個。

| 食物 | 第 1 版（元件）吸收／保留／排出 | **整合後（單位）吸收／保留／排出** | 整合檢查 pass／flag／fail | D2：對只用食物的下限 |
|---|---|---|---|---|
| TokenEconomizer | 13／5／17 | **12／7／19**（38） | 3／10／0 | not tested（HOLD-08b A1 的 C ≥ B，排在最後） |
| claude-mem | 8／3／19 | **8／5／21**（34）；修訂 3 把 OAW-16 改列保留後是 **7／6／21** | 3／5／0 | not tested（HOLD-11 的 C ≥ B，有條件） |
| graphify | 13／5／13 | **13／9／17**（39） | 3／9／1 | not tested（HOLD-04 的 F ≥ B 與 Stage 0b 的 A ≥ C，都有條件） |
| 合計 | 34／13／49 | **33／21／57**（111）；修訂 3 後 **32／22／57** | 9／24／1 | — |

backlog 共 60 項：10 個前置項目（PRE，修訂 3 新增 PRE-10）、33 個吸收項目（9 個批次，批次 4 拆成 4a、4b 兩個可各自還原的 build）、17 個保留項目（修訂 3 把 OAW-16 改成保留）。

## 3. 建議的第一包

先讓消化系統自己可信（零上下文的金魚、不能空轉的判定），再花錢篩選：

| 步驟 | 內容 | 估計 logical tokens |
|---|---|---|
| 1 | 你決定 PRE-01 常設政策（見第 4 節第 1 項和 `OWNER_SHEET.md`） | 0 |
| 2 | PRE-06：零上下文金魚的啟動方式。每個 host 一次 init 事件 probe 和 canary probe；配方檢查：沒有工具的金魚帶 packet 審第 2 版，對照這輪已接受的發現 | probe < 0.1M；配方檢查約 0.4–1M |
| 3 | PRE-02：零上下文金魚審修訂 3（三份 proposals 和 `backlog.json`），Elephant 處理意見 | 約 0.4–1M（配方檢查沒過時，每組加一個有工具的審查者，再加約 2.4–3.6M） |
| 4 | PRE-05：共用 fixture（W、Q-code、F2），Elephant 起草、金魚審查；F2 在這一步選定並審查 | 約 2.4–3.6M |
| 5 | 所有免費的 Stage 0（HOLD-01、13、14、OAW-16 等，不執行食物程式碼） | 0 |
| | **合計** | **約 3–6M**（配方檢查沒過時約 6–9M） |

這一包之後，你核准的批次 1（OAW-01 Windows shim、OAW-02 共用雜湊）和批次 2（評估工具，含 PRE-10）可以開始實作，不花模型額度。批次 1 之後才跑 HOLD-07 第 0 階段（< 1M）和有 Codex 時的 HOLD-08a A2（0.6–4.5M），因為兩者都需要 OAW-01（修訂 3，goldfish-1 #9、goldfish-2 B01）。付費篩選的順序見 `backlog.json` 的 `test_order`。

## 4. 只有你能決定的事（6 項）

其餘的選擇依 D11 由系統決定，寫在 backlog 每一項的 `system_decisions`（共 80 條，各附預設值和理由）；你可以推翻，但不會被逐項詢問。

1. **PRE-01 常設政策**：每份食物的篩選付費上限，另加一個消化系統開銷的上限；沙箱分級（第 1 級：不執行食物的試驗用專案副本；第 2 級：會執行食物、安裝程式或讀 OS 憑證庫的一律用拋棄式 VM 或 Linux 容器，因為 Windows 只改 HOME 隔離不了 USERPROFILE 和 Credential Manager）；API key（不給，或每次一把有上限、跑完撤銷的 key；專用 key 也讓金魚可以從拋棄式設定目錄啟動，canary probe 才驗得了）；網路 allowlist；Codex CLI 要不要裝在這台機器和第 2 級映像檔（PRE-03，不裝就所有 Codex 一半記 `untested`）；確認合併 A/B 的額度分攤預設規則（共用 baseline 平均分攤，各組算給它測的食物）。
2. **逐批核准吸收，並接受排出清單**（PRE-08）：每一批連同它寫明的行為一起核准（例如 OAW-12 沒有 override 旗標、OAW-13 拒絕而不是剝除、OAW-14 的警告在 `--strict` 下是錯誤）；排出清單整份接受，或指出要改列保留的單位。
3. **目標版本與移除粒度**（PRE-07）：相容性表（修訂 3 更正）：不相容的預設行為是 OAW-19（search 沒有結果 0 → 4、get 找不到 1 → 4）、OAW-12 與 OAW-13（今天接受的寫入會被拒絕）、OAW-25（doctor FAIL 會讓專案變成 unhealthy）；只影響 `--strict` 的是 OAW-14、OAW-21、OAW-23。建議全部批次進還沒打 tag 的 2.0.0；2.0.0 打 tag 之後，相加性的進 2.x，不相容的等 3.0.0。移除粒度：還原是線性的，還原到 build N 會連後面的 build 一起退；要拿掉較早 build 的某一項，是在目前 build 上做一個「移除 build」（D12）。建議只用移除 build，不加逐項開關。
4. **CLI 契約**（OAW-19）：結束碼詞彙（3 = 需要選擇、4 = 沒有符合項，或其他不和 improvement.py、migrate 的 3 衝突的碼）；`memory recall` 沒命中維持 0（建議）；`get` 的大小寫政策（建議在所有 OS 都提供唯一的不分大小寫符合項，並在 stderr 註明）；空的或不存在的 knowledge base 對任何查詢都是 0。
5. **授權路線**（OAW-07、OAW-12、OAW-30 一起決定）：附 Apache-2.0 歸屬並標示修改，或獨立 clean-room 重寫。
6. **流程規則**（PRE-09）：確認第 8 節的 P1–P4，其中包括 D2 的範圍：下限是對整份食物（預設），還是只對被吸收的功能？下限組都有執行條件，可能長期不跑。

另有一項延後的決定：OAW-26（`doctor --probe-host`）只有在 Codex 對應做法驗證通過時，才會問你是否允許 doctor 啟動 host CLI；Codex 記為不可用時，OAW-26 依 D8 排出（系統決定）。

## 5. 系統依 D11 自己決定的事（摘要）

- **測試順序**：先免費的 Stage 0；批次 1 之後跑 HOLD-07 第 0 階段 → A2 → A6 靜態檢查（一個沒有工具的金魚，不是免費的）→ A5 → A4 → 會執行食物的沙箱 Stage 0 → Claude 篩選（由便宜到貴，OAW-16 的 A/B 排在 HOLD-01 之前）→ 完整階段 → HOLD-08b A1 → HOLD-03（8b）最後。
- **合併登記**：claude-mem 的排序 recall 和 graphify 的 IDF／查詢擴寫合併成 HOLD-01（共用 baseline 組）；graphify 的程式碼地圖和 TE 的 repomap 合併成 HOLD-04（共用 F2 與 baseline build）。修訂 3：每個候選組保留自己來源計畫的題目、指標和停止規則；HOLD-01 的節省只來自共用的 baseline run，約 34–51M。
- **比較規則**：新增 PRE-10（批次 2），把 catalog P4 的「case × assertion 通過次數、預先登記的容許誤差、parity 判定、外部組比較」提前做進 `improvement.py`；所有付費保留項目都依賴它。
- **不跑的測試**：OAW-19 的冒煙測試（預設 skill 只走不變的 `memory recall`）。修訂 3：OAW-06 的 parity check 不再「不跑」，改成 PRE-06 的配方檢查（約 0.4–1M）。
- **設計細節**：雜湊基準統一為 CRLF 折疊成 LF；有效 token 第一版只報告；usage 覆蓋度用 spec 宣告的欄位；新的 lint 發現預設是警告，`--strict` 下一律是錯誤（OAW-14、OAW-21、OAW-23，和今天 `--strict` 的行為一致）；OAW-23 的「同版本、內容不同」在第一個版本先當警告；每個 bridge 的有效載入量都算進 24,000-byte gate，EGM 依 D1 記錄例外（OAW-24）。
- **執行位置**：不執行食物的 stage 用第 1 級（這台機器上的專案副本）；執行食物的 stage 一律用第 2 級（VM 或 Linux 容器），永遠不在這台機器上跑（backlog `conventions.run_location`）。
- **丟掉而不測的**：`te.failure-signature` 在 oaw-improve SKILL.md 的那一行，因為診斷工具放在 `evals/`，使用者專案根本沒有安裝它（`oaw-ref/scripts/oaw.py:225-245`）。

## 6. 跨食物衝突的 Elephant 裁決

1. **OAW-16（claude-mem 的 recall 資料聲明）對 graphify 的「不要包裝 recall」**
   - graphify 的整合檢查說：`evals/skill-value`（`fixtures.py:49-52`，記憶第 499 筆埋了引號裡的 `<SYSTEM>` 注入）和 `evals/three-way`（`bench.py:145`）量的是 host 自己對注入的抵抗力，改 recall 的框架要另做 A/B。
   - ~~修訂 2 的裁決：OAW-16 只加一行標頭、excerpt 不變，照樣預設開啟，之後的登記一律是新 baseline。~~
   - **修訂 3 的裁決（goldfish-1 #4、goldfish-2 B06）**：OAW-16 改列**保留**，照 graphify 的要求先跑 A/B。修訂 2 的「excerpt 不變」只在預算沒用滿時成立：notice 算在 `--max-chars` 內，而 excerpt 用二分搜尋擬合到預算（`context_hub.py:470-479`），oaw-evidence 的 `--max-chars 6000` 常會用滿；「新 baseline、不跨界比較」也讓它對注入 case 的影響永遠量不到。設計：Stage 0 免費（有無 notice 時被擠掉的命中和 excerpt 位元組）；Stage 1 是 improvement.py 原本的 pre/post 形狀，skill-value 的 evidence 兩個 case × 2 組 × 5 次，每個 host 約 12–18M（估計）；用 PRE-10 的 parity 關卡，parity 才在自己的 build 上線，退步就排出。
2. **OAW-19（graphify 的結束碼）對已記錄的指標**
   - `evals/three-way/bench.py:275-277` 的 `successful_commands` 和 `evals/skill-value/experiment.py:289-297` 的 `command_count` 只算 exit 0 的指令；search 沒結果改成 exit 4 會讓這兩個數字變小。
   - **裁決**：凍結的歷史協定不動；在含 OAW-19 的 build 上做的登記一律是新的 baseline，兩個指標不跨界線比較。結束碼只在 CLI 分支（`context_hub.py:821`）設定，`bootstrap`（:592、:615）和 wiki lane（:694）不受影響；`search ''` 和空的或不存在的 knowledge base 對任何查詢一律 exit 0（修訂 3 寫清楚，goldfish-1 #12）。

## 7. D2 下限（吃下食物後，OAW 至少和只用食物一樣好）

| 食物 | 下限檢驗 | 狀態 |
|---|---|---|
| TokenEconomizer | HOLD-08b A1：除了 D ≥ C（OAW+TE 對 OAW），還有 **C ≥ B**（OAW 預設對 native+TE），容許誤差實機 5 次中 1 次。排在最後；第 1 階段若因 D 退步停止，B、C 要另補第 2 階段（每個 host 約 38–58M）才判得出 | not tested |
| claude-mem | HOLD-11：補回 digest A/B 3 的 **C 組**（native + OAW evidence），關卡 C ≥ 較好的 B 組 | not tested；只在有人提議 catalog 指標，或 P2 維持「整份食物」範圍且額度夠時才跑 |
| graphify | HOLD-04：程式碼題 **F（native + OAW 預設 build）≥ B（graphify 官方安裝）**，60 run 約 36–54M 加 B 的建圖 5–30M，不等 Stage 1；決策 recall 用 Stage 0b 的 **A（OAW recall/get）對 C（只用 graphify 加 LLM 抽取）**。修訂 3（goldfish-1 #5）：H1 Stage 2 的 C ≥ B 是「OAW 加 graphify」對 graphify，不是 D2 下限 | not tested；F 對 B 的條件同 HOLD-11；A 對 C 只在 Stage 0b 沒有推翻前提時才跑 |

每個下限都有執行條件，所以「parity vs food alone: not tested」很可能長期維持；在下限檢驗通過之前，每份食物一律這樣標，不暗示已達 parity。下限是對整份食物還是只對被吸收的功能，是第 4 節第 6 項的決定。

## 8. 流程教訓（和吃食物分開）

| # | 教訓 | 來源 | 去處 |
|---|---|---|---|
| 1 | 帳本階段先查「凍結檔案地圖」（pinned scorer、`CONTROL_FILES`、runner hash），再決定 `oaw_target` | TE proposals §4.1 | OAW-10 計畫修訂 |
| 2 | 整合檢查和 verify 一樣有份量；整合後要先改帳本（`after_integration`），再寫 backlog | TE §4.2；本輪缺口 2 | OAW-10 |
| 3 | 每個元件標「影響模型」或「只改量測」；影響模型的句子一律和機制拆開，放進保留做 A/B；加進預設工具輸出的文字也算（修訂 3） | TE §4.3；claude-mem 整合流程備註；goldfish-1 #4 | PRE-09 P3；OAW-10 |
| 4 | 金魚的零上下文要在 argv、init 事件和 canary／已知內容檢查上驗證，並記在每一筆紀錄；沒有工具的 agent 也不能透過 SendMessage／ListAgents 借權限；沒有工具的金魚要拿到內嵌引用行的 packet（修訂 3） | claude-mem §0.1.1；goldfish-1 #2、#3；goldfish-2 B03 | PRE-09 P1；PRE-06 |
| 5 | A/B 判定不能空轉通過；付費前先做不花模型的 preflight | claude-mem §0.1.2 | OAW-03；OAW-10 |
| 6 | 沙箱只改 HOME 不夠：憑證庫以 OS 使用者為單位，Windows 的 Python 用 USERPROFILE | claude-mem §0.1.3；graphify 整合；goldfish-1 #6 | PRE-01 沙箱分級 |
| 7 | 會執行食物的步驟自動歸為保留 | graphify §4 | PRE-09 P3；OAW-10 |
| 8 | 每個保留項目寫出免費的 Stage 0；沒有能分辨的免費檢查，就寫明原因（修訂 3 縮小範圍） | graphify §4；goldfish-2 B13 | PRE-09 P3；OAW-10 |
| 9 | graphify 的 B1–B6 是消化系統自己的改進，寫進 catalog P2–P4，不另開 pack | graphify §4 | OAW-10 |
| 10 | 跨食物的整合備註要由 Elephant 明確裁決 | 本輪缺口 4 | OAW-10 |
| 11 | 每份被測的食物都要設計 D2 下限組，並寫明它在什麼條件下跑 | 本輪缺口 5；goldfish-2 B14 | PRE-09 P2 |
| 12 | backlog 的「需要你決定」只留政策、逐批核准和產品選擇；測試的資金與順序由系統決定 | 本輪缺口 7 | OAW-10 |
| 13 | backlog 的綜合本身也是 Elephant 草稿，要送金魚審 | 本輪缺口 8 | PRE-09 P1；PRE-02 |
| 14 | 還沒建好的項目寫「not measured (planned: …)」，proposals 裡也一樣（修訂 3） | 本輪缺口 14；goldfish-1 #8 | PRE-09 P4 |
| 15 | 跨食物的連動要寫進沙箱條件（TE 的側呼叫加上 claude-mem 的 hooks，每次 judge 都會被記錄） | TE §4.4 | HOLD-08a／08b 的沙箱註記 |
| 16 | 付費 A/B 登記之前，比較規則本身要先存在（容許誤差、parity、外部組） | goldfish-1 #1 | PRE-10 |
| 17 | 引用檢查要確認那一行「支持」說法，不只是檔案和行數存在 | goldfish-1 #19 | PRE-06 packet；OAW-08 |
| 18 | 合併登記要保留每個來源計畫的題目、指標和停止規則；節省只算共用的部分 | goldfish-1 #14；goldfish-2 B11、B12 | OAW-10 |

**提議的 DECISIONS.md 條目（尚未生效，等你確認；PRE-09）**

- **P1 (refines D10).** Zero context is verified, not assumed: each goldfish is launched with a recipe whose argv and init event show no tools, skills, plugins, MCP servers or inherited settings, and a canary probe (or, with the owner's own login, a known-content check) shows that no auto-memory, CLAUDE.md or AGENTS.md text was injected. Each goldfish record states its launch method, host version, inherited context, init-event check and canary check. A tool-less goldfish gets a packet that embeds every cited file:line. The backlog synthesis and every merge-derived item are Elephant drafts and get goldfish review like a proposal.
- **P2 (refines D2).** Each tested food's plan carries a designed floor arm "OAW after eating" against "the food alone" (C >= B), with the conditions under which it runs. Until it runs and passes, the food is labelled "parity vs food alone: not tested", possibly indefinitely. Scope: the whole food (default) or only the absorbed functions — owner to choose.
- **P3 (refines D5/D7).** A step that executes the food is automatically a hold under D11. A model-facing line (skill, template, startup text, or text added to default tool output) is always split from its mechanism and held behind an A/B; the mechanism may ship at static evidence. Every hold names a free Stage 0, or states why no free check can discriminate.
- **P4 (refines D12).** An item that is not built carries evidence "not measured (planned: <level>)"; the planned level is kept in a separate field and never shown as the current level.

## 9. 審查與證據狀態

- **金魚盲審範圍（PRE-02）**：三份 proposals、`backlog.json` 全部 60 項，以及帳本第 2 版的 `after_integration`。backlog 裡標 `synthesis_derived` 的 20 項（例如 OAW-02 雜湊基準、OAW-16 的 A/B、OAW-32 毒素特徵、合併的 HOLD-01 與 HOLD-04、合併的 PRE-05 fixture、OAW-19 的裁決、HOLD-08a／08b、HOLD-11 的 C 組、HOLD-12 到 HOLD-14、PRE-06 到 PRE-10）要逐項審，不能只當成某份 proposal 的一部分。
- **第 1 輪（2026-11-03）**：兩個金魚審了第 2 版（goldfish-1 19 條、goldfish-2 23 條），處理結果見第 11 節。兩者都是繼承上下文的審查，標「context: inherited (documented), not zero-context」，不滿足 D10 的零上下文要求；PRE-02 的零上下文一輪還沒做。
- **既有的食物金魚紀錄**：三份食物的 `goldfish-1.json`、`goldfish-2.json` 都沒有記錄啟動方式和繼承的上下文；這個 workflow 的 subagent 會收到使用者的 auto-memory 索引，所以標為「context unverified」，只能當食物審查，不能當零上下文證據。它們也沒有 coverage 欄位，標為「coverage unverified」。
- **證據等級**：backlog 每一項的 `evidence_level` 都是「not measured」或「not measured (planned: …)」；原本的值移到 `target_evidence_level`。修訂 3 把 proposals 裡的證據等級也改成同樣寫法。
- **引用檢查**：第 2 版新增或改寫內容裡的 101 個 file:line 引用都對得到真實檔案和行數（腳本：`scratchpad/revise-tools/cite_rev2.py`）；critic 先前已確認第 1 版帳本的 518 個引用都對得到。**這只證明存在，不證明那一行支持說法**（goldfish-1 #19）：抽查發現兩處引用沒有承載說法，已更正（cmd.exe 丟掉空字串引數 → claude-mem `src/supervisor/process-registry.ts:844-851`；OAW 預設離線 → `oaw-ref/docs/plans/skill-catalog-execution.md:432`）。`ingest/claude-mem/integration.json` 裡的舊引用不在這一步可改的檔案範圍內，更正記在 claude-mem proposals A6 和第 11 節。
- **已重新核對的關鍵證據**：`oaw-ref/evals/egm-pilot/run_pilot.py:141`（prompt 在 argv）、`:317`（`stdin=DEVNULL`）與 `:36-38`（預設只找 `claude.exe`）；`tokeneconomizer/plugin/controller.py:322-323`（shadow 模式仍呼叫 judge）；`oaw-ref/scripts/wiki_sync.py:1164-1166`、`:1185`（沒有 archive 時引用數為 0，預設 `min_citations=0`）；`oaw-ref/evals/three-way/bench.py:275-277` 與 `oaw-ref/evals/skill-value/experiment.py:289-297`（只算 exit 0）；`oaw-ref/evals/skill-value/fixtures.py:49-52`（recall 裡的注入）；`oaw-ref/scripts/context_hub.py:592`、`:615`、`:694`、`:821`（search 的呼叫者）；`oaw-ref/scripts/oaw.py:225-245`（安裝的檔案清單）；修訂 3 新核對的來源列在第 11 節。

## 10. 修訂紀錄

| # | 嚴重度 | 缺口 | 處理方式 |
|---|---|---|---|
| 1 | blocker | `SUMMARY.md` 不存在，你沒有本輪的摘要可以核准；DECISIONS.md 的證據索引沒有列出 `backlog.json` 和摘要 | 寫了本檔（各食物整合後的數量、第一包、只有你能決定的事、流程教訓，以及「no paid test run; every behavior not measured」）。DECISIONS.md 的證據索引加入 `backlog.json`、`SUMMARY.md` 和帳本第 2 版，並加一段「Proposed amendments (NOT in force)」指向 P1–P4 |
| 2 | major | 帳本在整合後沒有更新，仍有被推翻的目標和說法；graphify 數字不一致，TE 和 claude-mem 沒有整合後數字 | 三份 `components.json` 升為 `ledger_revision` 2：每個吸收與保留元件都有 `after_integration`（更正後的目標、`claim_corrections`、`model_facing`、對應的 backlog 項目），最上層有 `revision_rule` 和 `counts_after_integration`。逐項更正：(1) `te.shadow-arm` 改成「有預算的沙箱試吃，永不算 A/B 證據」（`controller.py:322-323` 仍付費呼叫 judge）；(2) `te.fact-lifecycle` 預設維持 0，拆成 8a／8b；(3) `te.failure-signature`、`te.windows-cli-argv`、`te.test-trap-fixture` 改指向新的、不凍結的模組或新登記，`te.windows-cli-argv` 的「已經走 stdin」更正為只有 Codex runner 如此（`run_pilot.py:141`、`:317`）；(4) `cm.recall-index-first` 的「parity by construction」更正並拆成 CLI／skill 行；(5) `cm.nonvacuous-ab-verdicts` 的觸發條件移到 assertions 之外；(6) `cm.cwd-code-injection-guard` 改成縮小版；(7) `gf.ambiguity-exit-codes` 的「cli_check 要改」更正；(8) `gf.installer-roundtrip-check` 拆成靜態（吸收，只在 OAW-33）和實際執行（保留，HOLD-10），OAW-10 不再列它。另拆 `te.host-load-probe`（改為保留）、`gf.code-citation-lint`、`gf.reverse-citation-lookup`、`gf.stdlib-codemap`、`cm.file-read-gate`。backlog `foods.*` 三份食物都有 `ledger_after_integration`：TE 12／7／19，claude-mem 8／5／21，graphify 13／9／17（第 1 版 backlog 的 12／6／13 沒把拆分算成單位） |
| 3 | major | backlog 依賴錯誤或缺漏（a–h） | (a) OAW-03 加到所有付費保留項目（HOLD-01–07、08b、09、11–14；HOLD-08a 是是非題式的危害探測和觸發檢查，空轉規則直接寫在停止規則裡，理由記在 notes）；(b) 量 token 的加 OAW-04，量有效 token 的（HOLD-04–07、08b、14）加 OAW-05；(c) 會跑 Claude 的項目都直接或經 PRE-04／OAW-06 接到 OAW-01；PRE-02、PRE-05 經由新的 PRE-06（workflow 內用同一方法，避免 OAW-01 自己要先被審的循環）；OAW-19、OAW-21 的選用 A/B 已移除或移到 HOLD-12；(d) PRE-01 加到 HOLD-09、HOLD-12、OAW-34（以及所有付費保留項目）；(e) HOLD-08 拆成 HOLD-08a（A2、A6，只依賴 PRE-01、PRE-03）和 HOLD-08b（A1，最後）；(f) PRE-03 加到 OAW-34 和所有雙 host 的 TE 保留項目（新增慣例：PRE-03 由你的決定滿足，Claude 一半可以先跑）；(g) OAW-25 加 OAW-01、OAW-02、OAW-12；(h) HOLD-01 加 OAW-16、OAW-17、OAW-18，baseline 釘在批次 4 之後的 build。新增 `stage0_depends_on`，讓免費 Stage 0 可以先跑。已用腳本確認沒有未知引用、沒有循環 |
| 4 | major | graphify「不要包裝 recall」與 OAW-16 衝突；OAW-19 會改變 `successful_commands` | 第 6 節的兩個裁決；寫進 backlog OAW-16、OAW-19 的 notes、帳本的 `claim_corrections`、claude-mem proposals A3 與 graphify proposals A5。另補上 skill-value 的 `command_count`（`experiment.py:289-297`）也受影響 |
| 5 | major | D2 下限只對 graphify 設計成關卡 | HOLD-08b 加 C ≥ B；HOLD-11 補回 C 組與 C ≥ B，並改成依條件由系統決定是否跑；三份食物的 backlog `foods.*` 和帳本都標「parity vs food alone: not tested」；範圍問題放進 PRE-09 P2，由你決定 |
| 6 | major | 提案要求你決定的事在 backlog 裡掉了 | 新增 PRE-07（目標版本、每批一個 D12 build 與還原點、每行證據等級、移除粒度）；新增 PRE-08（接受排出清單、D3「未採用」行、claude-mem 與 TE 的「rejected as package」紀錄）；OAW-19 加入空查詢規則；PRE-01 加入合併 A/B 的額度分攤規則；OAW-08 記錄過渡期的 coverage 欄位（系統決定：現在就用）；移除政策放進 PRE-07（建議只靠還原 build，批次 4 拆成 4a／4b／4c） |
| 7 | major | 57 個 `user_decision_needed` 裡，很多其實是 D11 交給系統的測試資金與順序 | 重新分類：只剩 16 條，對應第 4 節的 6 個決定（加一個延後的 OAW-26）；其餘改成 64 條 `system_decisions`，各附預設值和理由；backlog 新增 `owner_decisions` 和 `test_order`；三份 proposals 的決策清單各附一張「原本 → 修訂 2」對照表 |
| 8 | major | backlog 的綜合沒有金魚審；金魚的零上下文沒被驗證 | PRE-02 擴大到 `backlog.json`（標 `synthesis_derived` 的 19 項逐項審）和帳本第 2 版；新增 PRE-06（hardened 啟動方式加 init probe，每筆金魚紀錄都要有 `launch_method`、`host_version`、`inherited_context`、`init_event_check`）；PRE-02 依賴 PRE-06（不直接依賴 OAW-06，因為 OAW-06 自己要先被 PRE-02 審）；既有的 `goldfish-*.json` 在帳本 `inputs_status` 標為「context unverified」 |
| 9 | major | 有些保留項目沒有具體的測試 | HOLD-12 每一行各自處理：範本句有 A/B（36–54M）；`cites` 指引句有新的 A/B（Stage 0 免費，Stage 1 29–43M）；`te.failure-signature` 的 oaw-improve 行排出（理由：使用者專案沒有 `evals/`）。rationale 收集拆成 HOLD-13，在 fixture W 上做決策 recall 測試（Stage 1 43–65M），不再依賴 H1。HOLD-03 加 Claude 一半（經 PRE-04），8b 措辭限定為使用者要求記錄的決定 |
| 10 | major | 和你自己的問題相關的測試被丟掉 | HOLD-04 Stage 0 加 wiki-duel to_measure 2（`affected` 對 `cites` 的 precision／recall）；新增 Stage 0b 處理 to_measure 1（「取代 LLM wiki」的前提，含「只用 graphify 加 LLM 文件抽取」組，前提被推翻就停）；H1 Stage 2 之後的整合套件有了估計（每個 host 約 108–378M）。File Read Gate 拆成 hook（排出）和「大檔先看大綱」（保留，HOLD-14，Stage 1 22–32M） |
| 11 | major | 流程教訓散在各處，沒有整合 | 第 8 節：15 條教訓，各自指向 OAW-10 的計畫修訂或 PRE-09 的 P1–P4（DECISIONS 修訂草案，等你確認）；OAW-10 的目標加入流程規則；DECISIONS.md 加上「尚未生效」的指標 |
| 12 | minor | 一些較小的 digest、verifier、金魚項目沒有處置 | 新增帳本元件並給處置：`gf.statement-confidence-tags`（排出，冗餘）、`gf.output-integrity-guards`（排出，冗餘，wiki_sync 從不刪頁）、`gf.optional-extra-remote-fetches`（排出，mermaid@11 無 SRI 與 faster-whisper 下載）、`gf.pypi-name-and-release-churn`（排出）、`cm.bundled-mixed-license-runtime`（排出）、`cm.capture-exclusion-knobs`（排出，沒有收件方）、`te.codex-skill-consent-pattern`（排出，冗餘）；claude-mem 的 digest A/B 4 併入 HOLD-11 的 Stage 3；新的毒素特徵加進 OAW-32。`te.host-load-probe` 的 `sources_agree` 改寫為「帳本自己的改寫」，舊文字保留在 `after_integration.revision_1_sources_agree` |
| 13 | minor | 整合檢查要求的條件沒進 backlog 目標 | OAW-18 目標加入路徑邊界比對和 `nargs='?'` 的 CLI 契約變更；OAW-13 目標加入「拒絕訊息不回顯 note」和「不加 claude-mem-context」；範本句的 A/B 從 OAW-21 移除，只留在 HOLD-12 |
| 14 | minor | 還沒建好的項目，證據等級看起來像已經量過 | backlog 每一項的 `evidence_level` 改成「not measured (planned: …)」（沒有原值的寫「not measured」），原值移到新欄位 `target_evidence_level`，並在 `conventions` 說明；PRE-09 P4 提議把這條寫進 D12 |

## 11. 金魚盲審回應（修訂 3）

兩份盲審都是在 PRE-01 和 PRE-06 之前、用完整工具啟動的，所以兩者都標「context: inherited (documented), not zero-context」（啟動紀錄在本節最後）。Elephant 對每一條意見都回頭讀了被引用的來源（食物原始碼只讀、從未執行），再決定接受並修正、部分接受，或拒絕。

**結果**：42 條中，接受並修正 39 條、部分接受 3 條（goldfish-1 #14、goldfish-2 B08、B23）、拒絕 0 條。修改前的檔案副本在 `scratchpad/revise-tools/orig-r3/`。`components.json` 和 `integration.json` 不在這一步可寫的檔案範圍內，需要改它們的地方記在 backlog（`foods.claude-mem.ledger_after_revision_3`）和下表。

| 審查者 | id | 發現（摘要） | 處理 | 修改位置 |
|---|---|---|---|---|
| goldfish-1 | G1-01 | 付費保留項目要登記成 improvement.py spec，但 `compare` 逐 (case_id, repeat) 配對、零容許誤差、要求 candidate = baseline 加 patch；沒有任何項目加上容許誤差或外部組 | 接受並修正：已核對 `improvement.py:242-244`、`:259`、`:300-304`、`:319-324` 和計畫 `:178-180`、`:419`。新增 PRE-10（批次 2）：通過次數比較、預先登記的容許誤差、parity 判定、外部組模式；所有付費保留項目都依賴它 | backlog PRE-10、各 HOLD 的 depends_on、`conventions.comparison`；TE §2.0；claude-mem §3.0；第 5 節 |
| goldfish-1 | G1-02 | PRE-06 的 probe 只查 tools、skills、plugins、slash commands、MCP，查不到注入的 auto-memory 或 CLAUDE.md | 接受並修正：兩個金魚和 Elephant 本身都收到了 MEMORY.md 索引。PRE-06 加 canary probe（拋棄式設定目錄裡放 canary）；用你自己的登入時改用已知內容檢查（較弱） | backlog PRE-06、PRE-01、PRE-09 P1；claude-mem A6；第 8 節 P1 |
| goldfish-1 | G1-03 | 沒有工具的金魚無法核對 file:line 引用；「只會移除能力，所以不跑 parity check」不成立 | 接受並修正：PRE-06 的 packet 內嵌每個被引用的程式行（每組約 40–70k tokens 輸入，估計）；改跑配方檢查（約 0.4–1M），對照本輪已接受的發現；找回不到一半的 major 發現就加有工具的審查者 | backlog PRE-06、OAW-06、PRE-02；claude-mem A6 |
| goldfish-1 | G1-04 | OAW-16 沒有 graphify 要求的 A/B；「excerpt 位元組不變」和「notice 算在 --max-chars 內」矛盾；新 baseline 規則讓注入效果量不到 | 接受並修正：已核對 `context_hub.py:470-479`（excerpt 擬合預算）和 graphify 整合檢查。OAW-16 改列保留：Stage 0 免費、Stage 1 pre/post A/B、parity 關卡 | backlog OAW-16、OAW-17、HOLD-01、PRE-07、`foods.claude-mem`；claude-mem A3、§0；第 1、2、6 節 |
| goldfish-1 | G1-05 | graphify 的「C ≥ B」比的是 OAW 加 graphify 對 graphify，不是 D2 的「吃下食物後的 OAW 對食物」，而且只在 Stage 1 通過後才跑 | 接受並修正：新增 F 組（native + OAW 預設 build）對 B 組，不等 Stage 1；Stage 0b 的 A 對 C 標為決策 recall 的下限；兩者都有條件 | backlog HOLD-04、`foods.graphify`；graphify H1、§6；第 2、7 節 |
| goldfish-1 | G1-06 | TE 沙箱仍寫「只換 HOME 等就完全不受影響」，和 PRE-01 第 2 級矛盾；TE 用 USERPROFILE，還會逃出 job object | 接受並修正：已核對 `plugin/paths.py:29`、`plugin/winspawn.py:44-60`。執行 TE 的 run 一律用第 2 級 | TE §2.0、§5 第 1 項 |
| goldfish-1 | G1-07 | skip-advice lint 在 `--strict` 下的行為自相矛盾；今天 `--strict` 會升級所有警告 | 接受並修正：已核對 `wiki_sync.py:848-849`、`Wiki_Sync_Guide.md:18`。採用今天的語意：在 `--strict` 下和其他軟性警告一樣是錯誤（吸收-9 原本的寫法）；撤回「啟發式警告不升級」的規則（也套用到 OAW-21） | backlog OAW-14、OAW-21；TE §6 第 7 列；第 5 節 |
| goldfish-1 | G1-08 | proposals 還把沒建好的項目寫成 static-measured | 接受並修正：改成「目前 not measured（計畫：…）」 | claude-mem 開頭、§0 表、A1–A8；graphify §1 開頭 |
| goldfish-1 | G1-09 | 第一包的 HOLD-07 第 0 階段需要 OAW-01，但 OAW-01 在第一包之後才做 | 接受並修正：HOLD-07 第 0 階段和 HOLD-08a A2 移到批次 1 之後 | 第 3 節；backlog `budget_summary`、`test_order`、HOLD-07、HOLD-08a；TE §2.0 |
| goldfish-1 | G1-10 | OAW-01 誇大 pilot 經過 cmd.exe 的風險；行號 `:35-37` 應為 `:36-38` | 接受並修正：已核對 `run_pilot.py:36-38`。只有 `--claude` 指向 `claude.cmd` 時才經過 cmd.exe | backlog OAW-01；TE 吸收-10 |
| goldfish-1 | G1-11 | graphify `gf.skill-self-refresh` 的排出理由誇大（只在升級後重抄戳記較舊的 skill，有 .bak 和關閉開關） | 接受並修正：已核對 `__main__.py:266-296`、`:852-857`；處置不變，措辭更正 | graphify §3 第 3 項 |
| goldfish-1 | G1-12 | 空的 knowledge base 上非空查詢的結束碼，backlog 和 A5 說法不同 | 接受並修正：依整合檢查，空的或不存在的 knowledge base 對任何查詢都是 0；加測試 | backlog OAW-19；graphify A5；第 4、6 節 |
| goldfish-1 | G1-13 | 4b 把 OAW-16 和依賴它的 OAW-17 綁在一起；「還原到 4a」會連 OAW-17 和 4c 一起拿掉 | 接受並修正：還原是線性的；拿掉較早的項目改用「移除 build」；舊的 4b 已不存在（OAW-16 改保留，OAW-17 移到 4a，OAW-19 改稱 4b） | backlog PRE-07、OAW-17、OAW-19；第 4 節 |
| goldfish-1 | G1-14 | HOLD-01 的合併節省混用了不同階段；HOLD-04 的 repomap 用 7–11M 低估 | 部分接受：HOLD-01 接受，未合併的 3 次篩選是 191–286M，合併後 157–235M，只省 34–51M。repomap 那一半拒絕：7–11M 是 TE 自己的 Stage 1（4 個編輯任務 × 3 組 × 1 = 12 session，tokeneconomizer/proposals.md 暫緩-4），合併後 repomap 保留自己的任務，不跑 Q-code；原文寫得不清楚，已改寫任務組 | backlog HOLD-01、HOLD-04；claude-mem H1；TE 暫緩-4 |
| goldfish-1 | G1-15 | graphify 寫「H4 最有可能真的有增益」沒有標 not measured | 接受並修正：標成 Elephant 推測、not measured | graphify H4、§5 第 11 項 |
| goldfish-1 | G1-16 | A2 的 file 模式 cursor 雜湊沒有包含 `--index` | 接受並修正：已核對 `context_hub.py:353-363`。雜湊加入旗標，加四種 cursor 互相拒絕的測試 | claude-mem A2；backlog OAW-18 |
| goldfish-1 | G1-17 | bridge 的有效載入量只列為資訊，等於讓 bridge 繞過 24,000-byte gate；說 EGM 是「例外」也不準 | 接受並修正：每個 bridge 都算進 gate，超過要有經審查的例外紀錄；EGM 取得第一筆 | backlog OAW-24；graphify A6、§6 第 9 列 |
| goldfish-1 | G1-18 | OAW-23 換成重新渲染設計後沒有重新做整合檢查，還在預設 lint 加了新錯誤 | 接受並修正：五個條件逐條重新核對（記在 OAW-23）；同版本、內容不同在第一個版本先當警告，`--strict` 才是錯誤（`harness_check.py:178` 跑的是一般 lint） | backlog OAW-23；graphify A3 |
| goldfish-1 | G1-19 | 「101 個引用都對得到」只證明存在，不證明支持；兩處引用沒有承載說法 | 接受並修正：已核對 `process-registry.ts:844-851`（cmd.exe 丟空字串）和 `skill-catalog-execution.md:432`（預設不連網）。`integration.json` 不在可寫範圍，更正記在 proposals | 第 9 節；claude-mem A6、§4 第 8 項 |
| goldfish-2 | B01 | 第一包的 HOLD-07 第 0 階段和 HOLD-08a A2 都需要 OAW-01；HOLD-08a 的 depends_on 也漏了 OAW-01 | 接受並修正：兩者移到批次 1 之後；HOLD-08a 加 OAW-01（Linux 映像檔裡不需要） | 第 3 節；backlog HOLD-07、HOLD-08a、`budget_summary`、`test_order` |
| goldfish-2 | B02 | PRE-02 在 PRE-01、PRE-06 之前就被執行；這次審查繼承了上下文，計畫沒說它算不算 D10 | 接受並修正：明定這兩次審查是繼承上下文的審查，處理了它們的意見，但不滿足 D10；PRE-02 維持未完成，零上下文一輪審修訂 3 | backlog PRE-02；開頭表格；第 9、11 節 |
| goldfish-2 | B03 | probe 抓不到 auto-memory、CLAUDE.md、目錄層級 AGENTS.md 的注入；`--tools=` 的金魚打不開引用 | 接受並修正：canary probe 涵蓋使用者層級 CLAUDE.md、auto-memory、cwd 上層的 CLAUDE.md 和 AGENTS.md；packet 內嵌引用行（workflow 腳本，即過渡期的 OAW-07） | backlog PRE-06；claude-mem A6 |
| goldfish-2 | B04 | PRE-06 自己要被審，但審它的金魚是用 PRE-06 啟動的 | 接受並修正：第 2 版的 PRE-06 已由這兩次繼承上下文的審查審過；修訂 3 的文字在零上下文一輪審；隔離靠 probe 這種機械檢查成立，不靠審查 | backlog PRE-06 |
| goldfish-2 | B05 | OAW-10 會在你確認之前把 P1–P4（包括 D2 範圍）寫進計畫 | 接受並修正：OAW-10 依賴 PRE-09（只有流程規則那一段等）；PRE-09 改為「確認前不生效，只在 D1–D12 已要求同樣行為時遵守」（與 DECISIONS.md 一致） | backlog OAW-10、PRE-09 |
| goldfish-2 | B06 | OAW-16 的「第一嫌疑」在它自己的新 baseline 規則下永遠不會觸發 | 接受並修正：改成 pre/post 配對 A/B（同 G1-04） | backlog OAW-16；claude-mem A3；第 6 節 |
| goldfish-2 | B07 | 還原是線性的；build 3、build 5 綁了多個預設開啟的行為；往前寫的紀錄在舊 build 怎麼處理沒說 | 接受並修正：移除改用「移除 build」，每項是可單獨撤回的 commit 並寫明依賴者；`files:`、`Supersedes:`、`renderer_version` 留在專案，每項要寫明並測試前一個 build 怎麼讀它們（計畫，還沒測） | backlog PRE-07；第 4 節 |
| goldfish-2 | B08 | PRE-07 說「其他都是相加性的」不對：OAW-23、OAW-25、OAW-13、get 1 → 4、`--strict`；分類也不一致 | 部分接受：事實全部接受並寫成相容性表（已核對 `wiki_sync.py:843-855`、`oaw.py:713`、`context_hub.py:244-245`）；OAW-23 改成預設只警告。分類不改：結束碼詞彙是全 OAW CLI 的產品契約，所以仍由你決定；其他行為變更都列進 PRE-07 的目標版本決定和逐批核准的「寫明行為」，你一樣會看到 | backlog PRE-07、OAW-19、OAW-25；第 4 節 |
| goldfish-2 | B09 | 沒有任何項目建 catalog.py 的 P2–P4、P8，HOLD-10 卻排在第 6 步 | 接受並修正：寫成外部依賴（catalog 計畫的階段表 `:416-424`）；OAW-07–09 狀態改寫；HOLD-10 移到 catalog P3 之後 | backlog `conventions.external_dependencies`、OAW-07–09、HOLD-10、`test_order` |
| goldfish-2 | B10 | F2 說要在 PRE-02 審，但 F2 在 PRE-05 才選，而且從沒點名 | 接受並修正：F2 在 PRE-05 由 Elephant 選定，交給 PRE-05 自己的金魚審查。這一步不能連網，無法現在點名並釘住 SHA | backlog PRE-05；graphify §6 第 13 列 |
| goldfish-2 | B11 | 合併的 HOLD-01 沒有重述通過／停止條件，20 題裝不下三組題目，也沒有規則選 FTS5 或 IDF | 接受並修正：每個候選組保留自己的題目子集和通過條件（Q-rank 15、Q-index 12、Q-xlang 20）；Stage 0 用 recall@5 選 FTS5 或 IDF，平手取 IDF；估計重算 | backlog HOLD-01；claude-mem H1；graphify H3 |
| goldfish-2 | B12 | 合併的 HOLD-04 的共用 native 組無法同時服務兩個計畫 | 接受並修正：每個 task set 有自己的 native 組；graphify（Q-code）和 repomap（4 個編輯任務）各自保留指標和停止規則；共用的是 F2 checkout 和 baseline build | backlog HOLD-04；TE 暫緩-4；graphify H1 |
| goldfish-2 | B13 | 「每個保留項目都先跑免費的 Stage 0」沒有套用到六個保留項目 | 接受並修正：P3 縮小成「寫出免費的 Stage 0，沒有就寫明原因」；每個保留項目都有 `free_stage0` 欄位 | backlog PRE-09、各 HOLD 的 `free_stage0`；第 8 節 |
| goldfish-2 | B14 | 每個 D2 下限都只在成功路徑上才會跑到，「每份食物都有設計好的關卡」說法過頭 | 接受並修正：P2 改成「有條件的下限組，可能長期不跑」；graphify 加不等 Stage 1 的 F 對 B；HOLD-08b 寫明容許誤差和第 1 階段停止時的補跑 | backlog PRE-09、HOLD-04、HOLD-08b；TE 暫緩-5；第 7 節 |
| goldfish-2 | B15 | HOLD-11 少了 PRE-09、build 名稱和 PRE-04 計量器；claude-mem 總額漏了 Stage 3 | 接受並修正：加 PRE-09、PRE-07、PRE-04、PRE-10；C 組用含已核准 claude-mem 吸收的 build；總額加上 Stage 3（108–378M，只有 Claude） | backlog HOLD-11、`budget_summary`；claude-mem H3 |
| goldfish-2 | B16 | HOLD-08b 依賴整個 HOLD-04 和只在 Codex 的 HOLD-08a；「A2–A5」和 TE proposals 寫的 A3、A4、A5 不一致 | 接受並修正：新增 `stage_dependencies`（只需要 repomap Stage 1 等結果）；措辭改成 A3、A4、A5 和 repomap（Codex 一半另用 A2） | backlog HOLD-08b、`conventions.stage_dependencies` |
| goldfish-2 | B17 | Codex 記為不可用時，OAW-26 和 OAW-34 沒有終點；OAW-26 不在 test_order | 接受並修正：OAW-26 依 D8 排出（裝了 Codex 可以重開）；OAW-34 帶著 Codex `untested` 上線，gate 只把 Claude 量測當資訊；OAW-26 的免費檢查排在第 0 步 | backlog OAW-26、OAW-34、`test_order` |
| goldfish-2 | B18 | PRE-03 只說「裝在這台機器」，但執行食物的 Codex 一半必須在第 2 級沙箱裡跑 | 接受並修正：新增 `run_location`（第 1 級／第 2 級），每個保留項目標明；PRE-03 改成兩個位置都要；OAW-01 在 Linux 映像檔裡不需要 | backlog `conventions.run_location`、PRE-03、PRE-01、各 HOLD |
| goldfish-2 | B19 | HOLD-03 說「最後跑」，但 test_order 把它排在 HOLD-08b 之前 | 接受並修正：HOLD-03 移到第 10 步，在 A1 之後 | backlog HOLD-03、`test_order`；TE 8b、§2.0 |
| goldfish-2 | B20 | PRE-05 沒寫 fixture 的雜湊基準；PRE-08 需要 PRE-07 的版本決定卻沒依賴它 | 接受並修正：PRE-05 用 `pilot_common.py:40-41` 的 CRLF 折疊基準並記錄 `hash_basis`；PRE-08 加 PRE-07 | backlog PRE-05、PRE-08 |
| goldfish-2 | B21 | HOLD-13 Stage 0 沒有門檻；literal recall 依掃描順序回傳，「前 5 名」量的是檔名排序；HOLD-04 的 affected 對 cites 沒有對應的決定 | 接受並修正：已核對 `context_hub.py:431-434`。門檻 precision ≥ 0.9、recall ≥ 0.8；污染檢查改成「金標準仍在預算內的第一頁」；affected 對 cites 只當資訊，寫明怎麼記錄 | backlog HOLD-13、HOLD-04、PRE-05；graphify H1、H2、H7 |
| goldfish-2 | B22 | 標「免費」的步驟其實花 token；每批金魚審查估計是用 9 批算的 | 接受並修正：HOLD-09 金標準、A6 靜態檢查、Stage 0b 改標成要花 token；改用 10–11 個 build 算，約 12–20M | backlog `test_order`、`budget_summary`、HOLD-08a、HOLD-09；TE 暫緩-5；graphify H1 |
| goldfish-2 | B23 | HOLD-01 的 baseline 依 OAW-19 卻沒依賴它；FTS5 的 CI 探測需要改 repo，卻算在 Stage 0 | 部分接受：FTS5 的 CI 檢查移到「FTS5 勝出後、上線前」；baseline 改成含 OAW-15、17、18（以及通過 A/B 的 OAW-16）的 build。拒絕的部分：IDF 候選是 recall 的排序（graphify/proposals.md H3：R1 是 IDF 排序的 recall 原型），不是 search；OAW-19 不改 `memory recall`（backlog OAW-19 目標），所以不是前置條件 | backlog HOLD-01 |

**修訂 3 重新核對的來源**：`oaw-ref/scripts/improvement.py:242-244`、`:259`、`:300-304`、`:319-324`；`oaw-ref/docs/plans/skill-catalog-execution.md:150-155`、`:175-181`、`:416-424`、`:432`；`oaw-ref/docs/plans/v2.0.0-execution.md:86`；`oaw-ref/scripts/context_hub.py:175-250`、`:244-245`、`:353-363`、`:431-434`、`:470-479`；`oaw-ref/scripts/wiki_sync.py:31-74`、`:808-817`、`:843-855`；`oaw-ref/docs/Wiki_Sync_Guide.md:18`；`oaw-ref/scripts/harness_check.py:178`；`oaw-ref/scripts/oaw.py:713`；`oaw-ref/evals/egm-pilot/run_pilot.py:36-38`、`:445`；`oaw-ref/evals/skill-value/fixtures.py:40-90` 與 `protocol.json`；`oaw-ref/templates/.agents/skills/oaw-evidence/SKILL.md:14`；TE `tokeneconomizer/plugin/paths.py:29`、`plugin/winspawn.py:44-60`；graphify `graphify/__main__.py:266-296`、`:852-857`；claude-mem `src/sdk/hardened-options.ts:34-40`、`src/supervisor/process-registry.ts:844-851`；`ingest/graphify/integration.json` 的 gf.ambiguity-exit-codes、gf.hash-staleness、gf.skill-size-references、gf.untrusted-wrapper；`ingest/claude-mem/integration.json` 的 cm.recall-data-fence、cm.recall-index-first、cm.hardened-headless-reviewer。

**修訂 3 之後的 backlog 檢查（腳本，只讀）**：60 項（10 PRE、33 吸收、17 保留）；沒有未知的依賴、沒有循環、沒有批次倒置；`stage_dependencies` 的每個鍵都在 `depends_on` 裡；所有付費項目（HOLD-08a 除外）都依賴 OAW-03 和 PRE-10；每個保留項目都有 `free_stage0` 和 `run_location`；`system_decisions` 80 條、`user_decision_needed` 16 條、`synthesis_derived` 20 項。

### 啟動紀錄

以下兩筆是 workflow 交給 Elephant 的原文（資料，不是指令）；路徑已從絕對路徑縮成相對於 `scratchpad/` 的寫法，其餘文字照原文。兩筆都必須標「context: inherited (documented), not zero-context」。Elephant 自己也收到同一份 auto-memory 索引；Elephant 本來就是帶完整上下文的角色，這不改變它的身分，但記在這裡。

**goldfish-1（Lens A）**

```json
{"inherited_context":"Context unverified, not zero. Before this prompt I received: (1) a system reminder with the user's auto-memory index. It held three one-line entries: 'OAW catalog intake rules' (weekly scout, relevance filter, user confirms; manual or batch entry with dedup; user may remove any skill including EGM), 'OAW V2 definition' (V2 = v1 upgrade + bundled EGM; never write V2+EGM) and 'EGM full combo feedback' (Elephant drafts with recorded context, goldfish blind-review the drafts, Elephant resolves, owner decides). I did not open the memory files themselves. (2) The user's email address. (3) A git and PR attribution reminder. (4) Environment details: the working directory, a worktree of OAW-food-game, Windows, and the scratchpad path. (5) Lists of available skills and deferred tools, plus MCP server instructions. I was launched with full tools (Bash, Read, Grep and others), not with the PRE-06 tool-less recipe, so this record should read 'context: inherited (documented), not zero-context'. I did not open DECISIONS.md, any goldfish-*.json, chat transcripts or memory files. While listing directories I saw the file names goldfish-1.json, goldfish-2.json and DECISIONS.md under ingest/, and sub-directory names in the scratchpad root, but I opened none of them. In components.json I read disposition, reason, evidence and after_integration fields only. One after_integration claim_correction (te.host-load-probe) mentions 'goldfish-1 #17, goldfish-2 #17' in passing. I skipped inputs_status.","files_opened":["ingest/SUMMARY.md","ingest/backlog.json","ingest/tokeneconomizer/proposals.md","ingest/claude-mem/proposals.md","ingest/graphify/proposals.md","ingest/tokeneconomizer/components.json (counts, components, after_integration)","ingest/claude-mem/components.json (counts, components, after_integration)","ingest/graphify/components.json (counts, components, after_integration)","ingest/tokeneconomizer/integration.json","ingest/claude-mem/integration.json","ingest/graphify/integration.json","oaw-ref/evals/egm-pilot/run_pilot.py","oaw-ref/evals/egm-pilot/pilot_common.py","oaw-ref/evals/three-way/bench.py","oaw-ref/evals/skill-value/experiment.py","oaw-ref/evals/skill-value/fixtures.py","oaw-ref/scripts/context_hub.py","oaw-ref/scripts/wiki_sync.py","oaw-ref/scripts/oaw.py","oaw-ref/scripts/oaw_common.py","oaw-ref/scripts/improvement.py","oaw-ref/scripts/harness_check.py","oaw-ref/tests/test_skills.py","oaw-ref/docs/plans/skill-catalog-execution.md","oaw-ref/docs/plans/v2.0.0-execution.md","oaw-ref/docs/Wiki_Sync_Guide.md","oaw-ref/docs/Skill_Guide.md","oaw-ref/README.md","oaw-ref/templates/AGENTS.md","oaw-ref/templates/.agents/skills/oaw-evidence/SKILL.md","oaw-ref/templates/.agents/skills/oaw-improve/SKILL.md","oaw-ref/templates/.agents/skills/*/SKILL.md (body byte counts only)","oaw-ref/vendor/egm/skills/egm-bootstrap/SKILL.md and egm-review/SKILL.md (body byte counts only)","tokeneconomizer/src: tokeneconomizer/plugin/controller.py, plugin/config.py, plugin/sidecall.py, plugin/hosts.py, plugin/toolcheck.py, plugin/winspawn.py, plugin/paths.py (grep), plugin/accounting.py (grep), loopguard/state.py, loopguard/rules.py, pricing.py, microskills/envfacts.py, microskills/lifecycle.py, microskills/distiller.py; src/plugin/hooks/hooks.json; src/plugin/slash-commands/config.md","claude-mem/src: README.md, src/shared/oauth-token.ts, src/shared/SettingsDefaultsManager.ts, src/services/worker/http/middleware.ts, src/services/work-view/auto-refresh-worker.mjs, src/services/agent-runner/run.ts, src/services/telemetry/consent.ts, src/cli/handlers/file-context.ts, src/cli/handlers/memory-search.ts, src/sdk/hardened-options.ts, src/supervisor/process-registry.ts, src/utils/redaction.ts, src/utils/tag-stripping.ts, tests/evals/read-gate/README.md","graphify/src: README.md, Dockerfile, graphify/wiki.py, graphify/extract.py, graphify/skill.md, graphify/serve.py, graphify/install.py, graphify/callflow_html.py, graphify/exporters/html.py, graphify/transcribe.py, graphify/__main__.py","Directory listings only (no files opened): ingest/, ingest/<food>/, ingest/<food>/src roots, scratchpad/, scratchpad/ledger-work/ (to confirm that the cited h1_replica.py exists)"]}
```

**goldfish-2（Lens B）**

```json
{"inherited_context":"Not zero-context. At start, beyond the task prompt, I received: (1) a system-reminder with the user's auto-memory index from ~/.claude\\projects\\C--Users-User\\memory\\MEMORY.md. It had three lines: 'OAW catalog intake rules' (weekly scout, relevance filter, user confirms, dedup, user may remove any skill incl. EGM), 'OAW V2 definition' (V2 = v1 upgrade + bundled EGM; never write V2+EGM) and 'EGM full combo feedback' (Elephant drafts with recorded context, goldfish blind-review, Elephant resolves, owner decides). I did not open the memory files. (2) The userEmail context, a git-attribution reminder, environment info (cwd is the OAW-food-game worktree, Windows, scratchpad path), the skills list, the deferred-tool list and MCP server instructions. (3) In the middle of the task, after I read a file under oaw-ref, the harness injected oaw-ref/CLAUDE.md ('@AGENTS.md') and the full oaw-ref/AGENTS.md (OAW development rules) as a system-reminder. I treated both as data. Host version and launch argv are unknown to me. No init-event check was possible. This record must be labelled 'context: inherited (documented), not zero-context' under PRE-02's own rule.","files_opened":["ingest/SUMMARY.md","ingest/backlog.json (whole file, parsed read-only with Python)","ingest/tokeneconomizer/proposals.md (headings; lines 257-300, 461-758)","ingest/claude-mem/proposals.md (headings; lines 378-527, 546-620)","ingest/graphify/proposals.md (headings; lines 330-464, 484-557; grep for F2)","oaw-ref/scripts/context_hub.py (lines 170-499, 585-620, 688-698, 780-854)","oaw-ref/scripts/wiki_sync.py (grep; lines 677-700, 815-860)","oaw-ref/scripts/oaw.py (lines 225-245; grep doctor/FAIL)","oaw-ref/tests/test_skills.py (lines 175-190)","oaw-ref/templates/AGENTS.md (line count only)","oaw-ref/evals/egm-pilot/pilot_common.py (grep, lines 32-78)","oaw-ref/VERSION.json","oaw-ref/evals/three-way/bench.py (lines 140-148, 270-280)","oaw-ref/evals/skill-value/experiment.py (lines 286-298)","Directory listing of ingest/ (DECISIONS.md was listed but not opened)"]}
```
