# H1 凍結前修正 2 的核對（Codex gpt-6.1-sol，reasoning high，2026-11-11）

核對的是 `PREREG.md`「凍結前的修正 2」和相關段落、`h1_run.py` 的 diff（C 類補天花板題、`PRIOR_RUNNERS`）、`checks/freeze_check.py` 新增的檢查和 `DECISIONS.md` 的 D42。原文照錄。用量：輸入 515,525（其中快取 446,976）、輸出 4,271。

處理：沒有阻擋。唯一一項應修（代價寫得太確定）照它的最小修正改了 `PREREG.md`「先講的限制」、修正 2 的決定一項和 D42 的代價一項；補題規則和沿用的紀錄都沒動，所以沒有再送一輪。

---

先改再凍結

1. **應修；PREREG.md「先講的限制」（236 行）、修正 2 的代價敘述，以及 DECISIONS.md D42（468 行）**：把「校準 N 一次滿分」寫成正式比較「只看得出變差」，過於確定，與驗題 5 新增的條件式說明不一致。反例：校準 1.0，正式 N1＝0.8、N2＝0.9、O＝1.0，仍會得到 O−N＝＋0.15。最小修正：統一寫成「校準已見天花板，偵測改善的能力可能降低；若正式 N1、N2 都滿分，才只能顯示持平或變差」。不需改補題規則或重跑紀錄。

已讀：H1/{PREREG.md、h1_run.py（HEAD 與工作樹）、checks/freeze_check.py、h1_judge.py}、DECISIONS.md（本次 diff）；專案規則檔 CLAUDE.md、AI_CONTEXT.md、VERSION.json、OAW-records/AGENTS.md、CURRENT_STATE.md、harness-evaluator.md、memory_nudge.py。