---
id: Memory_System_Experiments_Report_2026-04-21
title: OAW 記憶系統實驗白話報告 — 2026-04-21
page_type: report
date: 2026-04-21
audience: human readers, not agents
---

# OAW 記憶系統：白話版實驗報告

> 2026-04-21 針對 OAW 的 memory + classify-evidence + wiki pipeline 跑了兩個實驗，
> 看寫入 / 讀取 / 升等 wiki 這三條路徑會不會失準。
> 技術審計細節在 [`docs/archive/Memory_Discipline_Experiment_2026-04-21.md`](archive/Memory_Discipline_Experiment_2026-04-21.md)
> 和 [`docs/archive/Inheritance_And_Promotion_Experiment_2026-04-21.md`](archive/Inheritance_And_Promotion_Experiment_2026-04-21.md)。
> 這份是給人看的摘要。

---

## 一句話結論

OAW 的寫入紀律和升等紀律**都有效**；但在**讀取**這一側意外摸出一個以前沒命名過的失誤模式 —— **過度推辭**。

這是今天最有價值的發現。其他都是「預期中通過」。

---

## 背景：為什麼要測這個

OAW 有三份規則協同運作：

| 規則 | 出現在 | 管什麼 |
|---|---|---|
| `memory.md` TAG 列表 | 每個專案的 `.agents/memory.md` 開頭 | **寫入** — 什麼事值得記、怎麼標 tag |
| `classify-evidence` skill | `templates/.agents/skills/` | **判斷證據強度** — 這是猜測還是確認？T1-T5 |
| `WIKI_PIPELINE.md` | `docs/wiki/` | **升等** — memory 裡哪些條目該變 wiki topic |

三條規則個別合理，但**疊在一起會不會反而讓 agent 寫太多、標過頭、或該答卻不敢答**？只有實際跑一個 fresh agent 丟進去才知道。

---

## 實驗一：寫入紀律（會不會寫太多 / 標過頭 / 寫成作文）

### 怎麼測

給一個**零上下文**的新 agent：
- `memory.md` 的 TAG 規則
- `classify-evidence` 的 T1–T5 判斷流程
- 8 個合成的 session 事件

然後請它對每個事件決定：寫 or 略？如果寫，選什麼 tag、什麼 tier、body 寫什麼。

### 8 個事件長這樣

| # | 事件 | 我事前擬的「正確答案」 |
|---|---|---|
| E1 | 單 seed benchmark 快了 14.2% | 要寫，T2，必配 CAVEAT |
| E2 | README 錯字修掉 | 別寫 |
| E3 | 權衡過冷啟 vs 熱吞吐後選 lazy-load | 要寫，[DECISION] |
| E4 | 試 3 個 config 組合都變糟、沒定位 | 寫或略都行 |
| E5 | Null-pointer crash 在 3 個作業系統都復現 | 要寫，[BUG] T3 |
| E6 | 把變數 tmp 改成 scratch_buf | 別寫 |
| E7 | p95 延遲 3 次量測：142/147/139ms | 要寫，T4 |
| E8 | 使用者順口說「別在 comment 用 emoji」 | 寫或略都行 |

### 結果

- **明確題（6 題）全對**：該寫的都寫、該略的都略
- **邊緣題（2 題）選擇合理**：都選了寫、理由站得住
- **tier 全部正確**：T2 都配了 CAVEAT、T3 有 3 組獨立復現、T4 有量測數據
- **body 長度**：中位 14.5 字、最長 18 字 — 完全沒有小作文傾向

### 但摸到兩個規則模糊地帶

**盲點 1：tier 能不能單獨存在？**
E7 是量測基準（144ms），subagent 選了 `[ARCHITECTURE]` 當 Kind tag + `[T4]`。但 ARCHITECTURE 是「設計決策」，不是「量測」。memory 規則沒講清楚 tier 可不可以單獨用、或必須配一個 Kind tag。

**盲點 2：使用者偏好算專案 memory 嗎？**
E8「別在 comment 用 emoji」是跨專案的個人偏好，但 OAW 規則只暴露 project-level memory，subagent 只好把它寫成 project [DECISION]。規則應該要說清楚：**跨專案的個人偏好該去 user-level memory（例如 Claude Code 的 auto memory），不該塞進專案 memory。**

---

## 實驗二：讀取 + 升等紀律（knowledge 能不能傳承）

### 怎麼測

給一個**零上下文**的新 agent **只讀三個檔**：
- `.agents/memory.md`（昨天手寫的 6 條真實紀錄）
- `docs/wiki/WIKI_PIPELINE.md`
- `classify-evidence` skill

然後兩個任務：

**Task A（傳承）**：問 4 個專案問題，看它能不能從檔裡正確抽出答案。

**Task B（升等）**：對 6 條 memory 分別判斷：STAY（留在 memory）/ PROMOTE（該升到 wiki）/ UNCERTAIN。

### Task A 結果：3 題逐字正確、1 題過度推辭

| 問題 | 結果 |
|---|---|
| Q1 R-1 subagent 獨立性的 tier 是多少？ | ✅ 逐字答出 `T2 + CAVEAT: 單次 spike` |
| Q2 subagent 對 commit 881cb25 的裁決？ | ✅ 逐字 `7/7 PASS, 0 FAIL, 0 UNCERTAIN` 還加碼 ~28k/78s |
| Q3 2026-04-21 有多少 skills 通過 frontmatter lint？ | ⚠️ 答 **「資訊不足」** — 但它自己的括號裡承認「memory 寫了 8」 |
| Q4 harness-evaluator 有挖到 reviewer 不知道的東西嗎？ | ✅ 逐字命中 Merge Gate 括號 drift |

Q3 是這次實驗最有意思的地方 —— 答案就在檔裡，agent 卻不肯講。

### Task B 結果：6/6 通過、0 過度升等

6 條 memory 全部合理判為 STAY，只有 1 條標 UNCERTAIN（8 skills pass lint — 是 T3 但 binary metric 不太算 wiki 主題，這個思辨比我事前擬的還精準）。**沒有任何一條被過度升等**。

---

## 核心發現：三種紀律的對稱失誤

把兩個實驗併起來看，OAW 的 memory + wiki 系統會在三條路徑各自出失誤：

| 路徑 | 理想狀態 | 失誤方向 | 今天觀察到嗎 |
|---|---|---|---|
| **寫（write）** | 只記有 signal 的事 | 寫太多（廢話）／ 標過頭（單次吹成「確認」） | ❌ 沒出現 |
| **升（promote）** | 預設留在 memory | 把單次觀察推上 wiki topic | ❌ 沒出現 |
| **讀（read）** | 從檔裡抽事實 | **答案在檔裡卻不肯答** | ⚠️ 出現了（Q3） |

OAW 目前對「寫太多」和「過度升等」都有明文規則，**對「讀不出來」完全沒規則**。這就是盲點。

### 為什麼 over-refusal 重要

- 寫太多 → memory 變雜訊，但至少還在
- 升等過頭 → wiki 失去可信度，但可以回捲
- **讀不出來 → 知識傳承直接斷鏈**。下一個 session 的 agent 開工時答「資訊不足」，等於 memory.md 根本沒寫

前兩種是「堆垃圾」，第三種是「眼前放黃金但彎不下腰」。嚴重度不同。

---

## 未來建議

### 🟢 短期（可以在下一條 feature branch 做）

1. **新增一條讀取紀律** 到 `classify-evidence.md` 或獨立一個 `read-discipline.md` skill：
   > 「如果答案逐字在檔裡，就抽出來。"INSUFFICIENT EVIDENCE" 只用於檔裡真的沒有答案的情況，不是措辭曖昧時的逃避。遇到曖昧，先給出檔裡有的事實、再標註模糊之處。」

2. **補 memory.md header 兩個盲點**（實驗一浮出的）：
   - Tier tag 可以單獨存在（純量測時不用配 Kind tag，或配 `[EXPERIMENT]`；`[ARCHITECTURE]` 保留給設計決策）
   - 跨專案使用者偏好屬於 user-level memory，不放這裡

### 🟡 中期（需要累積真實 session 資料）

3. **在非合成資料上重跑實驗**。今天兩個實驗都是我手造的 corpus，需要真實的 debug log 或 decision thread 才能把 T2 結論升到 T3。

4. **追蹤 over-refusal 比率**。如果後續觀察到 Q3 這種情況超過 1/20，讀取紀律就從 P3 升 P1 優先。

### 🔴 長期（架構層）

5. **讀取應該也有 evaluator**。現在 `harness-evaluator` 只審「這個改動做對了嗎」，沒審「agent 讀 memory 有讀到嗎」。可以考慮加一個 `inheritance-check` skill：每次 session 開始時，抽問 agent 3 個該知道的事，答不出來就提示它再讀。

6. **Memory → wiki 的升等不要全手動**。現在升等是隱性判斷。可以在 `wiki_sync.py` 加一個 `promote-candidates` 子命令，列出「memory 裡 T3+ 且連續被 3 個以上 session 引用」的條目，給人類做最終決定。

---

## 給未來 session 的 cheat sheet

如果你接手 OAW 某個分支、想要快速進入狀況，按這個順序讀：

1. `CLAUDE.md` — 30 秒看 lane 路由
2. `VERSION.json` 的 `version` 和 `do_not_rerun` — 10 秒知道不要重跑什麼
3. `.agents/memory.md` **最新 5 條** — 不要讀全部，只讀最新的
4. `ROADMAP.md` 開頭 60 行 — 知道當前 phase
5. 有跟你任務相關的 `docs/archive/*` 就讀，沒有就別亂讀

**四個地雷**（不踩）：
- 別 session 開頭就讀所有 .md 檔（禁忌第一條）
- 別重跑 `do_not_rerun` 裡的事
- 別把 `docs/raw/` 當 context 源（那是 fallback）
- 別對 memory.md 裡的 T2 條目直接引用當事實 — T2 要配 CAVEAT

---

## 實驗本身的證據等級（自我校正）

為了不自打臉，這份報告的主張也用 classify-evidence 自我分級：

| 主張 | Tier | 理由 |
|---|---|---|
| 「OAW 寫入紀律有效」 | **T2** [CAVEAT: 單次 subagent、8 個合成事件] | 只跑了一次、題目是我擬的 |
| 「升等紀律預設保守成功」 | **T2** [CAVEAT: 6 條 memory 是同一個 agent 寫的 curated corpus] | 不是天然樣本 |
| 「Over-refusal 是獨立失誤模式」 | **T1**（假設） | 只觀察到 1 次。需要 20+ 筆樣本才能談模式 |

換句話說：這份報告的所有建議**都是從 T1 / T2 推出來的**，不是定論。照做之前請先在你的環境小試一下。
