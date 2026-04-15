# Merge Analysis & Improvement Plan — feature/self-harness → main

> **Date**: 2026-04-15  
> **Branch**: `feature/self-harness`  
> **Verdict**: ⚠️ **不建議直接 merge** — 需要拆分 scope

---

## Part 1: Merge 分析

### 核心矛盾

> `repo/` 是一個**給大眾用的 template framework repo**。  
> `feature/self-harness` 把這個 repo 變成了**一個被 harness 管理的專案**。  
> 兩件事都對，但不能混在一起。

### 問題拆解

| 檔案 | 性質 | 適合 merge? | 理由 |
|------|------|-------------|------|
| `CLAUDE.md` | ⚠️ 專案實例 | ❌ | 這是「agent-memory-framework 自己的 CLAUDE.md」，不是 template。使用者 clone repo 後看到這個，會以為 CLAUDE.md 應該長這樣，但它應該是空白 template |
| `AI_CONTEXT.md` | ⚠️ 專案實例 | ❌ | 同上。裡面寫的是「Install time < 5s, Skills count 6」，對使用者的專案沒意義 |
| `VERSION.json` | ⚠️ 專案實例 | ❌ | `do_not_rerun` 記載的是 OAW 的 P0 validation，不是使用者的 |
| `ROADMAP.md` | ⚠️ 專案實例 | ❌ | 記載 OAW 自己的 roadmap |
| `.agents/skills/*.md` | ⚠️ 和 templates 重複 | ❌ | 跟 `templates/.agents/skills/` 完全一樣，等於 repo 裡有兩份 |
| `docs/knowledge/*.md` | ⚠️ 空模板 | ❌ | 6 個幾乎空白的 wiki 模板，放在 repo root 會讓人困惑 |
| `docs/raw/*.md` | ⚠️ 空模板 | ❌ | 同上 |
| `.github/copilot-instructions.md` | ✅ 通用 | ✅ | 這個對任何使用者都有用 |
| `.gitignore` 修改 | ✅ 通用 | ✅ | 把 `.agents/memory.md` 加入 ignore 是合理預設 |
| `docs/archive/` 4 份報告 | 🟡 內部文件 | 部分 | Repo Health Review 可以留（展示 framework 自身品質），其他太多了 |

### 結論

如果直接 merge，使用者會看到：

```
repo/
├── CLAUDE.md              ← 這是 OAW 自己的 rules，不是 template
├── AI_CONTEXT.md          ← 這是 OAW 自己的 context，不是 template
├── templates/
│   ├── AGENT_RULES.md     ← 這才是 template...
│   ├── AI_CONTEXT.md      ← ...但跟上面那個不同版本？？
```

**結果**：使用者會困惑「我應該看哪個 `AI_CONTEXT.md`？」

---

## Part 2: 建議策略 — 三種選擇

### Option A: 拆分 merge（推薦 ✅）

只 cherry-pick 對大眾有意義的檔案：

| 該 merge 的 | 理由 |
|-------------|------|
| `.github/copilot-instructions.md` | 所有使用者都受益 |
| `.gitignore` 修改 | 合理預設 |
| `docs/archive/2026-04-15_Repo_Health_Review.md` | 展示 framework 品質意識 |

不 merge 的留在 branch 上作為「self-hosting experiment 記錄」。

### Option B: 移到 example（推薦 ✅✅）

把 self-harness 的成果變成第三個 example：

```
example/
├── minimal-project/       ← 已有：最小安裝快照
├── public-hybrid-demo/    ← 已有：有 raw notes + wiki + skills 的完整示例
└── self-hosting-demo/     ← 新增：用 OAW 管理 OAW 自己的示範
```

**好處**：
- 使用者可以看到「真的有人用這個 framework 管理自己的 repo」
- 不污染 repo root
- 保留所有 self-hosting 的設定作為教學材料

### Option C: Dual-layer（進階）

把 repo 設計成「既是 framework source，也是被 framework 管理的專案」：

- repo root 的 `CLAUDE.md` 負責 OAW 自己的開發
- `templates/` 的 template 負責使用者安裝

**問題**：對新人太混淆，不推薦。

---

## Part 3: README 分析 — 夠吸睛嗎？

### 現狀評分

| 面向 | 分數 | 分析 |
|------|------|------|
| **Hook（吸引力）** | ⭐⭐⭐⭐⭐ | 「我全都要」meme + 痛點清單非常到位 |
| **What（這是什麼）** | ⭐⭐⭐⭐ | 四個功能清單很清楚 |
| **Quick Start** | ⭐⭐⭐⭐ | 兩個方案 + 3 分鐘可用 |
| **Architecture** | ⭐⭐⭐⭐ | Mermaid 圖很棒 |
| **Why not chaos** | ⭐⭐⭐⭐ | 「為什麼不會變亂」段落很有說服力 |
| **After Install（安裝完會看到什麼）** | ⭐⭐ | 缺少！使用者不知道安裝完有什麼檔案 |
| **When To Use What（什麼時候用什麼）** | ⭐⭐ | 缺少！使用者不知道 memory vs wiki 的分界 |
| **LLM Wiki 教學** | ⭐⭐⭐ | 有流程但太抽象，缺少真實情境 |
| **Mobile 顯示** | ⭐⭐⭐ | Meme 圖太大，推擠內容 |

### 建議新增的段落

#### 1. 「What You Get After Install」（安裝完你會看到什麼）

```markdown
## 🎁 安裝完你會看到什麼

```text
your-project/
├── CLAUDE.md              ← Agent 的大腦入口（你的第一件事：編輯它）
├── AI_CONTEXT.md          ← 專案事實手冊（第二件事：填入你的專案資訊）
├── VERSION.json           ← 版本追蹤 + 實驗鎖定
├── ROADMAP.md             ← 階段計畫
├── .agents/
│   ├── memory.md          ← Agent 的日記（自動記錄決策和 bug）
│   └── skills/            ← 可重用的工作流程（像 function call）
├── docs/
│   ├── knowledge/         ← 編譯好的知識 wiki（Agent 讀這裡）
│   └── raw/               ← 你的原始筆記（Agent 不主動讀）
└── scripts/
    ├── context_hub.py     ← 知識管理 CLI
    └── wiki_sync.py       ← 筆記→wiki 編譯器
```

> 💡 **三句話版本**：`CLAUDE.md` 是 Agent 的大腦，`AI_CONTEXT.md` 是你專案的百科，
> `.agents/memory.md` 是 Agent 的日記。其他的，需要的時候再看。
```

#### 2. 「When To Use What」（什麼情況用什麼）

```markdown
## 🧭 什麼時候用什麼？

| 我想要... | 用這個 | 指令 |
|-----------|--------|------|
| 記錄一個決策 | `.agents/memory.md` | `python3 scripts/context_hub.py memory add "[DECISION] 改用方案 X"` |
| 記錄一個 bug | `.agents/memory.md` | `python3 scripts/context_hub.py memory add "[BUG] Windows 上會 crash"` |
| 把亂七八糟的筆記變成知識 | `docs/raw/` → `docs/knowledge/` | `python3 scripts/wiki_sync.py refresh topic_name` |
| 查知識 | `docs/knowledge/` | `python3 scripts/context_hub.py search "關鍵字"` |
| 執行重複性流程 | `.agents/skills/` | 告訴 Agent: `follow .agents/skills/benchmark.md` |
| 看目前專案狀態 | CLI | `python3 scripts/context_hub.py status` |
```

---

## Part 4: Memory vs Wiki — 怎麼用才不衝突？

### 核心原則

```
Memory = 日記（短期、時間序、滾動式）
Wiki   = 教科書（長期、主題式、精煉過）
```

### 生命週期模型

```text
事件發生
   ↓
記到 memory.md          ← 「2026-04-15 [BUG] Windows 上 install.sh 會 hang」
   ↓
累積 3-5 筆同類 memory
   ↓
提煉到 wiki             ← docs/knowledge/Known_Limitations.md 新增一節
   ↓
memory 中的舊條目歸檔   ← 搬到 docs/knowledge/ 或直接標記 archived
   ↓
未來 Agent 讀 wiki      ← 不用再翻 50 條 memory 找那個 Windows bug
```

### 具體例子：開發一個 API 專案

```
📝 Day 1: 你在 debug 一個 API timeout
memory.md ← "[BUG] API timeout on /users endpoint, root cause: N+1 query"

📝 Day 3: 又碰到類似問題
memory.md ← "[BUG] API timeout on /orders, also N+1"

📝 Day 5: 你發現這是一個 pattern
memory.md ← "[INSIGHT] All timeout bugs are N+1 queries. Need eager loading policy."

📚 Day 5: 提煉到 wiki
docs/raw/api_performance_notes.md    ← 把三條 memory 和你的分析整理成筆記
python3 scripts/wiki_sync.py refresh api_performance_notes
→ docs/knowledge/API_Performance.md  ← 精煉的「API Performance 最佳實踐」

🎯 Day 30: 新的 Agent session
Agent 讀 docs/knowledge/API_Performance.md（200 tokens）
而不是翻 memory.md 裡 50 條雜亂的 entries（2000 tokens）
```

### 判斷流程圖

```text
我有一個新資訊要記錄
    ↓
它是一個「事件」（bug、決策、實驗結果）？
    ├── 是 → 記到 memory.md（用 [BUG]/[DECISION]/[EXPERIMENT] tag）
    │         └── 如果同類已累積 3+ 條 → 考慮提煉到 wiki
    │
    └── 否 → 它是「知識」（概念、API 規格、設計原則）？
              ├── 是 → 寫到 docs/raw/，然後 wiki_sync refresh
              │
              └── 否 → 它是「流程」（每次做法都一樣的 SOP）？
                        ├── 是 → 寫成 .agents/skills/ 裡的 skill
                        └── 否 → 直接寫在 AI_CONTEXT.md（專案事實）
```

### 不衝突的關鍵

| 規則 | 為什麼 |
|------|--------|
| Memory 只記事件，不記知識 | 避免 memory 變成第二個 wiki |
| Wiki 只記精煉結論，不記原始過程 | 避免 wiki 變成第二個 memory |
| Raw notes 是草稿，不是永久存儲 | 編譯完就不需要再讀 |
| Memory 條目超過 30-50 條就歸檔 | 避免 Agent 讀太多 |
| Wiki 更新時標記 source_refs | 可以追溯結論的來源 |

---

## Part 5: 行動計畫

### Phase 1: README 改進（1-2 小時）

- [ ] 新增「安裝完你會看到什麼」section
- [ ] 新增「什麼時候用什麼」decision table
- [ ] 改進 LLM Wiki 段落（加入具體例子）
- [ ] 縮小 meme 圖片到 300px
- [ ] 同步更新 `README.en.md`

### Phase 2: Selective merge（30 分鐘）

- [ ] Cherry-pick `.github/copilot-instructions.md` 到 main
- [ ] Cherry-pick `.gitignore` 修改到 main
- [ ] Cherry-pick `docs/archive/2026-04-15_Repo_Health_Review.md` 到 main

### Phase 3: Example 新增（1 小時）

- [ ] 建立 `example/self-hosting-demo/`
- [ ] 把 self-harness 的 CLAUDE.md, AI_CONTEXT.md 等搬過去
- [ ] 寫一個 README 說明「這是 OAW 用自己的 harness 管理自己的示範」

### Phase 4: Skills 對齊（30 分鐘）

- [ ] `example/minimal-project/` 加入 `wiki-refresh.md`（或在 README 說明它是 optional）
- [ ] 確認三處 skills 清單的差異是有意為之且有文件說明

### Phase 5: Design docs 更新（30 分鐘）

- [ ] `Design_Principles.md` 加入命名演進說明（"Fat Skills" → "Hybrid Router"）
- [ ] 加入 Memory vs Wiki 生命週期圖（本報告 Part 4 的內容）

---

## Summary

| 問題 | 建議 |
|------|------|
| Self-harness 適合直接 merge? | ❌ 不適合。會污染 repo root，讓使用者困惑 |
| 該怎麼處理 self-harness? | 拆分 merge + 搬到 example |
| README 夠吸睛嗎? | Hook 很好，但缺 post-install orientation 和 decision table |
| Memory vs Wiki 怎麼不衝突? | Memory = 日記，Wiki = 教科書，3-5 條同類 memory 就提煉 |
| 最該優先做的? | README 改進 → 最高 ROI，直接影響每個新使用者 |
