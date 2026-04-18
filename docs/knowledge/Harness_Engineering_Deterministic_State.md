---
id: Harness_Engineering_Deterministic_State
title: Harness Engineering — Deterministic State Control
page_type: topic
build_origin: manual
last_updated: 2026-04-18
related_topics:
  - Harness_Engineering_Context_Fragmentation
  - Harness_Engineering_Knowledge_Synthesis
---

# Deterministic State Control (確定性狀態控制)

## 核心問題

Agent 在自主模式下容易：
1. 重跑已完成的實驗（浪費 token + 可能產生衝突結果）
2. 在修復迴圈中卡死（fix → break → fix → break...）
3. 不知道目前開發進度在哪，從頭重新規劃

## OAW 的解法：VERSION.json 開發狀態機

```json
{
  "version": "0.0.0-dev",
  "current_phase": "development",
  "next_phase": "v1.0.0-release",
  "task_state": {
    "in_progress": [],
    "blocked": []
  },
  "do_not_rerun": [
    "experiment A — 原因：結果已記錄在 docs/knowledge/Experiment_Findings.md"
  ]
}
```

每次 session 開始，Agent 讀取：
- `version` → 知道目前版本
- `current_phase` / `next_phase` → 知道開發方向
- `task_state.in_progress` → 接手上次未完成的工作
- `task_state.blocked` → 避免重踩已知障礙
- `do_not_rerun` → 跳過已完成的實驗

## 使用方式

告訴 Agent：
> 「這個功能已經驗證過了，幫我加進 `do_not_rerun`，說明原因。」

或在 session 結束時，Agent 應主動更新 `task_state`。

## 實作位置

- `VERSION.json`（每個專案的根目錄）
- `templates/VERSION.json`（安裝模板）
- `CLAUDE.md` → `## Session Startup` 要求讀取 VERSION.json
