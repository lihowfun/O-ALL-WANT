---
title: Harness Engineering — Knowledge Synthesis
type: architecture
tags: [harness, wiki-sync, memory, knowledge-distillation]
updated: 2026-04-18
---

# Knowledge Synthesis (知識蒸餾)

## 核心問題

Agentic Workflow 產生大量短期輸出（決策、bug 修復、實驗結果），但這些洞察通常只活在當次 session 的 context 裡，下次開新 session 就消失了。

## OAW 的解法：兩層記憶 + 自動蒸餾 pipeline

```
短期（事件驅動）              長期（知識驅動）
.agents/memory.md     →→→    docs/knowledge/<topic>.md
[DECISION] ...               已結構化、可被 Wiki Lane 讀取
[BUG] ...
[FINDING] ...
                 ↑
         wiki_sync.py refresh
         (由 agent 在 session 結束時呼叫)
```

## 觸發方式

不需要排程，跟著工作節奏自然觸發：

```
你：「把這次的發現同步到 wiki。」
Agent：跑 wiki_sync.py refresh <topic>
     → 讀取 docs/raw/<topic>.md 和相關 memory 條目
     → 產出或更新 docs/knowledge/<topic>.md
```

## 兩層記憶的差異

| | Memory（日記） | Knowledge（教科書） |
|---|---|---|
| **位置** | `.agents/memory.md` | `docs/knowledge/*.md` |
| **壽命** | 短期，滾動更新 | 長期，持續累積 |
| **格式** | 事件條目 `[TAG] 日期 標題` | 結構化主題頁 |
| **誰寫** | Agent 自動記 | `wiki_sync.py` 編譯 |
| **Git** | `.gitignore`（本地日記） | 公開 commit（教科書） |

## 實作位置

- `scripts/wiki_sync.py` → `refresh` / `build` / `lint` 指令
- `templates/.agents/memory.md` → memory 格式模板
- `docs/knowledge/` → 編譯後的 wiki 頁
- `CLAUDE.md` → Session End 強制 wrap-up 規範
