---
id: Harness_Engineering_Context_Fragmentation
title: Harness Engineering — Context Fragmentation
page_type: topic
build_origin: manual
last_updated: 2026-04-18
related_topics:
  - Harness_Engineering_Deterministic_State
  - Harness_Engineering_Knowledge_Synthesis
---

# Context Fragmentation (上下文分流)

## 核心問題

LLM 在長 context 中有「Lost in the Middle」現象：開頭和結尾的資訊被高度保留，中間段落容易被忽略。當整個 repo 的文件都塞進單一 context 時，這個現象尤其嚴重。

## OAW 的解法：Lane 動態路由

`CLAUDE.md` 作為 Master Router，依任務類型只載入對應 lane 的檔案：

| Lane | 觸發情境 | 載入的檔案 |
|------|---------|-----------|
| **Operational** | 查進度、執行實驗、發布 | `AI_CONTEXT.md`, `ROADMAP.md`, `VERSION.json`, `memory.md` 最後 5 條 |
| **Wiki** | 查背景知識、複習設計決策 | `docs/knowledge/index.md` + 相關主題頁 |
| **Execution** | 執行重複性 SOP | `.agents/skills/<matching_skill>.md` |
| **Debug** | 排查錯誤、重現 bug | `docs/knowledge/Known_Limitations.md`, `memory.md` 最後 5 條 |

## 效果

- 每次 session 注入的 context 大幅縮減
- LLM 注意力集中在真正相關的檔案
- Token 消耗下降，推論品質提升

## 實作位置

- `CLAUDE.md` → `## Session Startup` 和 `## Route by lane` 表格
- `templates/AGENT_RULES.md` → 同上（安裝後的版本）
