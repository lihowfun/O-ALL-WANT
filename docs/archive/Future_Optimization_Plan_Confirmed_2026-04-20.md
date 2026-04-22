# OAW Future Optimization Plan — Confirmed (v1)

Date: 2026-04-20
Status: **Decided — authoritative plan for the next 6 weeks.**
Cross-references:
- [Taiwan_MD_Collaboration_Study.md](Taiwan_MD_Collaboration_Study.md) — wiki governance source (2026-04-19)
- [Harness_Engineering_Quality_Audit_2026-04-20.md](Harness_Engineering_Quality_Audit_2026-04-20.md) — 6.7/10 audit
- [Future_Optimization_Plan_2026-04-20.md](Future_Optimization_Plan_2026-04-20.md) — pre-decision synthesis (this doc supersedes it)

## 0. Decision Summary

| # | 項目 | 決定 | 一句話理由 |
|---|------|:---:|-----------|
| §2 | LLM-wiki 8 artifacts merge | ✅ Accept | 已完成的 self-driven 投資,docs-first 近零風險 |
| P1-1 | `harness_check` 一鍵健檢 | ✅ Accept | 最低成本、最可見 ROI |
| P1-2 | `harness-evaluator` skill | 🔬 Research | 同 session 評估 = theater,設計要先想清楚 |
| P1-3 | Lane audit log | 🔬 Research | 沒下游 evaluator 就是孤兒 feature |
| P1-4 | Skill frontmatter lint | ✅ Accept | 便宜、擋 skill 品質倒退 |
| P2-1 | Recovery pattern in template | 🔬 Research | 沒真實失敗案例就設計必過度工程 |
| P2-2 | Task-state CLI | ❌ Reject | `memory.md` + `ROADMAP.md` 已覆蓋 |
| P2-3 | `--json` output | 🔬 Research | 沒 evaluator 消費者 = YAGNI |
| P2-4 | Worktree skill | ❌ Reject (維持 contingent) | 本來就是條件式 defer,不進排程 |
| §3 P3 | 運行時 dashboard / 獨立 evaluator agent / 硬規則攔截 / 品質 scorecard | ❌ 維持 deferred | 需真實使用量或前置條件,現在做是憑空想像 |

**總計**:**3 Accept、4 Research、3 Reject**(其中 P2-4 與 P3 是維持先前 defer)。

## 1. Accepted — 排進 Sprint

### A-1. LLM-wiki governance merge → **v1.1.0**(Week 1)

全盤接受原報告 §2。

- **範圍**:8 個 artifacts(3 wiki guides、3 prompts、`wiki_sync.py` lint 延伸、issue/PR templates)
- **Pre-merge 必過**:預設 `wiki_sync.py lint` 綠;新增的 stale/thin/generic 檢查僅在 `--strict` 下 fail
- **PR**:單一 `feat(wiki): LLM-wiki governance layer`,CHANGELOG 明列 8 artifacts + 3 non-goals(不做 website / i18n dashboard / scoring engine)
- **版號**:`1.0.0 → 1.1.0`(新公開 surface 合理佔 minor)
- **預估**:2–3h
- **此項例外**:原本「不基於單一 feedback 跳 minor」的規則不適用 — 這是 self-driven architectural investment,不是 reactive feature

### A-2. `harness_check` 一鍵健檢(Week 2)

接受原報告 P1-1。步驟清單不動:

1. `py_compile` on `scripts/context_hub.py` + `scripts/wiki_sync.py`
2. `wiki_sync.py lint`(預設模式)
3. Self-install 拒絕 probe
4. 空目錄 install 煙霧測試 + 檔案集合 assert
5. `example/minimal-project/scripts/*.py` 對 `scripts/*.py` drift 檢查

**本次新增決定**:CI 用一個 step(`./scripts/harness_check.py`)取代現在散落的多步,single source of truth。

### A-3. Skill frontmatter lint(Week 2)

接受原報告 P1-4。**本次新增範圍澄清**:

- 檢查對象:`templates/.agents/skills/*.md`(canonical),不檢查 root 自用 skills
- 必要欄位:`triggers` 或 `outputs` 至少一項存在;`Steps` section 必須存在
- 豁免:`_TEMPLATE.md`、`README.md`、`_*`
- **違規預設為 warning,`--strict` 才視為 error** — 降低現存 skills 的立即遷移壓力

## 2. Research — 時間盒 + 決策條件

> **新增規則**:每個 research 項目都有時間盒。超過盒子還沒結論 → 自動 downgrade 到 P3 defer,不拖下去。

### R-1. `harness-evaluator` 設計研究(Week 3,時間盒 5 天)

**核心問題**:audit §3 指同一 agent 兼任 planner / generator / evaluator 是弱點。但一個在**同 session 同 context** 的 evaluator skill,充其量是「結構化自評」,不是「獨立評審」。需要先想清楚什麼叫 independent。

**要回答的三個問題**:

1. 在 Claude Code / Codex 現有能力內,最便宜的「真獨立 context」是什麼?
   - A. Subagent spawn(新 context window)
   - B. 第二次 `claude` CLI 叫起(新 session)
   - C. Pre-commit hook 用純 Python 做結構化靜態檢查(不靠 LLM 判斷)
2. 若只能做 "同 session + 結構化 prompt + 獨立 checklist",這種 evaluator 值得嗎?
3. Evaluator output 寫哪?`memory.md` 加 `[REVIEW]` tag?獨立 `docs/audit/*.md`?

**決策標準**:
- ✅ 若 (1) 有至少一個清楚答案且成本 < 1 天 → 進 Week 4 實作
- ❌ 若三個選項都等於 "same-session theater" → 放棄 evaluator skill,改做 A-3 skill lint 的進階版靜態檢查
- 🔬 若 (1) 有前景但要試才知道 → 用半天做 spike,再決

**Week 3 交付**:`docs/archive/Evaluator_Design_Decision_2026-05-XX.md`(≤ 2 頁)敘述答案 + Week 4 決定。

### R-2. Lane audit log(Week 4,**contingent on R-1**)

**核心問題**:audit log 自己沒價值,價值來自「有某個 evaluator 會讀」。

**決策邏輯完全跟隨 R-1**:
- R-1 選了 subagent / 新 session / CLI evaluator → audit log 變成 evaluator 的輸入 → 做
- R-1 結論 "no independent evaluator" → audit log 是孤兒 → **自動取消**
- 不單獨排期

### R-3. Recovery pattern in skill template(Week 5,時間盒 3 天)

**核心問題**:通用 recovery 骨架在沒真實失敗案例時設計,會犯兩個錯:
1. 過度工程 — 列出想像中的失敗模式,90% 永不觸發
2. 錯過實際模式 — 真實失敗的 pattern 往往你沒想到(通常不是 timeout 而是 auth token 過期或 permission 升級)

**Pre-work(Week 5 上半週)**:
- 掃 `.agents/memory.md` + 你另一 project(SEAL_GNN)過去 30 天的 skill / script 失敗
- 分類:transient(可 retry)/ permission(escalate)/ logic bug(abort)/ partial success(rollback)

**決策標準**:
- ✅ 累積 ≥ 5 個真實案例 + 跨 ≥ 2 類 → 基於實例設計 Recovery section
- ❌ 案例 < 5 或過於均質 → **不做通用骨架**,改成單一 skill 的 case study
- 🔬 ≥ 6 但單一類 → 先只做這一類,其他類繼續 defer

**Week 5 交付**:`docs/archive/Skill_Failure_Modes_2026-05-XX.md` 彙整 + 決定。

### R-4. `--json` output(**時程待定**,contingent on R-1)

**核心問題**:JSON 只在「有會消費 JSON 的 evaluator」存在時有意義。

**觸發條件**:R-1 結論是「實作 subagent/CLI evaluator」**且** evaluator 要結構化輸入 → 屆時做。
**反觸發**:R-1 結論是靜態檢查或不做 → R-4 永久 defer。

## 3. Rejected — 明確不做 + 復活條件

### X-1. P2-2 Task-state CLI

**拒絕理由**:
1. `VERSION.json.task_state.in_progress / blocked` 真正要解決的需求(「agent 現在做到哪」)已被 `.agents/memory.md` + `ROADMAP.md` 覆蓋
2. 加 CLI = 使用者認知負擔 +1,ROI 低
3. 真的要 task tracker 就用 GitHub Projects / Linear,不要在 markdown 裡再造輪子

**復活條件**:`task_state` 欄位在實際 skill 流程中被明確依賴(不只是 metadata),重新評估。

### X-2. P2-4 Worktree collaboration skill — 維持 contingent

**拒絕理由**:原報告已寫 "only build when ≥3 people on a branch"。那是條件式 defer,**不是主動工作,不進排程**。

**復活條件**:你或合作者 ≥ 3 人同時在同 branch ≥ 2 週,碰到實際 merge 痛點。

### X-3. P3 全部

運行時觀察性 / 獨立 evaluator agent / 硬系統級規則攔截 / 品質 scorecard + 回歸趨勢 — 全部維持 deferred。每項都需要「真實使用量」或「先決條件成立」,現在做是憑空想像。

## 4. Revised 6-Week Calendar

| Week | 工作 | DoD | 類別 |
|:----:|------|-----|:----:|
| 1 | LLM-wiki governance merge → `v1.1.0` | Tag + release notes + CHANGELOG + README links 正確 | A-1 |
| 2 | `harness_check` + skill frontmatter lint | 一鍵綠、CI 單步呼叫、CONTRIBUTING 更新 | A-2 + A-3 |
| 3 | **Evaluator design research** (R-1) | `Evaluator_Design_Decision_2026-05-XX.md` 交付 | R-1 |
| 4 | R-1 結論執行 | 根據 Week 3 結論實作 evaluator OR 改做靜態檢查 | R-1 → R-2 |
| 5 | **Recovery research** (R-3):failure 案例彙整 | `Skill_Failure_Modes_2026-05-XX.md` 交付 | R-3 |
| 6 | R-3 結論執行 OR 留白接 community feedback | 根據 Week 5 結論 | R-3 / slack |

**與原報告最關鍵的差異**:
- 原 Week 6 的 "task-state OR --json" **整個刪掉**
- Week 3 從「直接寫 evaluator」改成「先研究 evaluator 設計」
- Week 5 從「直接寫 Recovery 骨架」改成「先彙整 failure 案例」

## 5. 保留的 Open Questions

原報告 §5 有 4 個。重新整理:

| 問題 | 決定時機 |
|------|---------|
| Evaluator 位置(skill / agent / CI) | R-1 結束時一併回答 |
| JSON schema 穩定性 | 只在 R-4 啟動後;不急 |
| Wiki governance CODEOWNERS | Week 1 merge 前可同步決(現只有你一人 committer,目前不需要) |
| Audit log 存放(gitignore vs commit) | 與 R-1 / R-2 綁;R-2 若取消,此題自動消失 |

## 6. Anti-Patterns — 新增一條

> **對每個 P1 項目,先問「這東西的消費者是誰?」。如果答案是"未來某個尚未存在的 evaluator"或"某個還沒發生的使用場景",立刻降級為 Research。**

這條規則直接導致 P1-3(lane audit)和 P2-3(JSON output)的降級。

原有規則(不憑單一 feedback 跳 minor、audit 分數別成 checklist 義務、路由層別再重寫)繼續適用。

## 7. Revised Success Criteria(Week 6 End)

誠實反映 scope 縮減:

| Layer | 原目標 | **新目標** | 理由 |
|-------|:-----:|:--------:|------|
| Tool system | — | **7.0** | `harness_check` + skill lint 明確提升 |
| Execution orchestration | 7.0+ | **6.5 ± 0.5** | 取決於 R-1;做出 evaluator 則 7.0+,反之維持 6.0 |
| Evaluation + observability | 7.0+ | **6.0–7.0** | 同上 |
| Constraints + recovery | 7.0+ | **6.0 ± 0.3** | R-3 若只做 case study 不是通用骨架,分數僅微升 |
| **整體** | 7.8 | **7.2 ± 0.3** | 把 "commitment" 與 "取決於研究結果" 分開 |

這不是退步 — 是把「可驗證 commitment」和「research-dependent」清楚分開,避免到 Week 6 拿不出說好的 7.8 時自我欺騙。

## 8. Monday 第一件事

1. 把**本文件**放進權威位置(建議合併入 main 時放 `docs/archive/`,作為 2026-04-20 的決策記錄,不會動到)
2. 開始執行 **Week 1: LLM-wiki governance merge**
3. 為 R-1 / R-3 在 `ROADMAP.md` 建 placeholder 區(只寫「研究中,預計 Week 3/5 結論」,**不填 DoD**),避免未來看 roadmap 誤以為是 committed 工作

---

## Appendix A — 降級與拒絕的深度理由(可選讀)

### 為什麼 P1-2 evaluator 被降級?

Audit §3 說同一 agent 兼任三角色是弱點 — 這是真問題。但原報告的解法「加 evaluator skill」有個**隱藏前提**:skill 被 invoke 時會有獨立 context。

實際上在 Claude Code / Codex,invoke 一個 skill **不等於**開新 context。通常是同一 agent 在同一 conversation 讀 skill 後依指示行動。結果:
- Evaluator skill 讀要評估的工作 → 還在同一 context → 還在同一 agent 的偏見範圍
- 最多做到「結構化自評」,不是「獨立評審」

真正獨立評審需要「不同 context」。選項:
- Claude Code Agent 子工具(新 context 沙盒) — 可能
- Pre-commit hook 用純 Python 做結構化靜態檢查 — 不靠 LLM,便宜
- 手動 2nd pass — 最可靠但最貴

這三選項成本/效益差別極大,沒想清楚就開工容易做出半成品。所以先 Research。

### 為什麼 task-state CLI 被拒?

三個等價問題:
1. 「agent 現在有哪些 task?」→ `.agents/memory.md` 最近 5 條 `[DECISION]` / `[TODO]` 就知道
2. 「phase 進度到哪?」→ `ROADMAP.md` P0/P1/P2 table 就知道
3. 「下次 session 接著做什麼?」→ `ROADMAP.md` + Session End 第 4 段就知道

`task_state` 欄位當時可能是 placeholder 想之後用。但真實 workflow 已被其他 surface 覆蓋。再做 CLI = 重複造輪子 + 更多同步負擔。

### 為什麼 Recovery pattern 被降級?

通用 recovery 骨架在沒真實失敗案例時設計,必然犯兩個錯:
1. **過度工程** — 列出想像得到的失敗模式,90% 永不觸發
2. **錯過實際模式** — 真實失敗常常你沒想到(不是 timeout 是 auth 過期;不是 network 是 permission 升級)

先累積真案例再設計 OR 只針對一個具體 skill 做 case study。這兩條路都比憑空寫骨架好。

---

*Decided on 2026-04-20. Lives in worktree `study/future-optimization-plan-confirmed` at
`/mnt/drugs/akuo/project/OAW/O-ALL-WANT/.claude/worktrees/future-plan-confirmed` until approved for merge.*
