// Generated from a real catalog.py ledger (5 foods, 2026-11-05) after recording, on a copy, the tastings and the
// D21 absorption its records branch holds (graphify x2, court-skill, arXiv 2606.03979), plus one synthetic
// food at approval whose pipeline the engine computed. Local paths are not part of view.json.
export const VIEW = {
 "foods": [
  {
   "components": [],
   "counts": {
    "absorb": 0,
    "excrete": 0,
    "hold": 0
   },
   "display": "arXiv:2606.03979",
   "id": "arxiv-2606-03979",
   "kind": "paper",
   "paper": {
    "abstract_chars": 1527,
    "arxiv_id": "2606.03979",
    "authors": [
     "Ali Behrouz",
     "Farnoosh Hashemi",
     "Adel Javanmard",
     "Vahab Mirrokni"
    ],
    "authors_total": 4,
    "categories": [
     "cs.LG",
     "cs.AI"
    ],
    "executed": false,
    "from": "static",
    "is_pdf": true,
    "license": "CC-BY-4.0",
    "license_url": "http://creativecommons.org/licenses/by/4.0/",
    "metadata_sha256": "128b886605eb8853b4cb2318dc65663d89aed8af1c03b44756fe3f1a90db7c38",
    "parsed": false,
    "pdf_bytes": 3151827,
    "pdf_sha256": "dab98367e19e99eb8838a6604afddb9ea85a940f2f41d8a1602e55977fb12d14",
    "reuse": "quote-with-attribution",
    "reuse_note": "quoted text may be reused with attribution",
    "reuse_note_zh": "引用原文要附出處（作者、標題、arXiv 編號、版本、授權）",
    "source": "arxiv",
    "title": "Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories",
    "version": "v2",
    "version_date": "2026-07-10",
    "versions": [
     {
      "date": "2026-06-02",
      "version": "v1"
     },
     {
      "date": "2026-07-10",
      "version": "v2"
     }
    ]
   },
   "pinned": {
    "commit": null,
    "commit7": null,
    "integrity": "sha256-recorded",
    "pdf_sha12": "dab98367e19e",
    "tree_sha12": "ece4c4e301eb",
    "version": "v2"
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [],
    "blocker": {
     "basis_zh": [
      "D21：A 級（只改機制）靜態證據就能吸收、B 級（模型會讀的文字）要試吃判定吸收、C 級問你；吸收是 Claude 重建成 OAW 程式和測試",
      "sl.wake-sleep-cycle/manual-pass（A 級）：claude/oaw-2 b14c875、656c539；測試 tests/test_wiki_sync.py::MemoryCheckTests；依據 tier A: mechanism only, static evidence allowed by D17/D21; field usefulness not measured",
      "D21、D28：發布是整個分支一次決定：你合併 PR，這些單位一起進正式版本；不是逐樣核准"
     ],
     "if_ignored_zh": "這些單位留在 claude/oaw-2，不會進正式版本；其他食物不受影響",
     "unknown_zh": [],
     "where_zh": "版本：1 個單位已在 claude/oaw-2 重建，等發布（合併 PR 時一次決定）"
    },
    "details": [
     {
      "id": "plan",
      "label_zh": "看計畫",
      "stage": "plan"
     }
    ],
    "note_zh": "已吸收 1 個單位（D21：在 claude/oaw-2 重建成 OAW 程式和測試）；排掉 11 個、暫留 3 個",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "build",
    "stage_label_zh": "版本",
    "stage_notes_zh": {
     "approve": "D21 吸收：1 個單位（sl.wake-sleep-cycle/manual-pass A 級）",
     "build": "1 個單位等發布（claude/oaw-2）"
    },
    "stages": {
     "approve": "done",
     "build": "current",
     "intake": "done",
     "plan": "partial",
     "quarantine": "done",
     "review": "planned",
     "sort": "partial",
     "static": "done",
     "test": "planned"
    },
    "state": "current",
    "state_zh": "目前",
    "waiting_on": "release",
    "waiting_zh": "等發布（合併 PR 時一次決定）"
   },
   "repo": "https://arxiv.org/abs/2606.03979",
   "tasted": true,
   "tasting": null,
   "verdict": {
    "ascii": "[ ]",
    "badges": [],
    "chips": [
     "free-checks-passed"
    ],
    "headline": "untested",
    "label": "untested",
    "label_zh": "未測",
    "level": "static-measured",
    "reasons": [
     "no measured evidence (paid tests not run)"
    ],
    "reasons_zh": [
     "沒有實測證據（付費實測還沒跑）"
    ],
    "stale": false,
    "symbol": "○"
   }
  },
  {
   "components": [],
   "counts": {
    "absorb": 0,
    "excrete": 0,
    "hold": 0
   },
   "display": "thedotmack/claude-mem",
   "id": "claude-mem",
   "kind": "repo",
   "paper": null,
   "pinned": {
    "commit": null,
    "commit7": null,
    "integrity": null,
    "pdf_sha12": null,
    "tree_sha12": null,
    "version": null
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [
     {
      "endpoint": "taste",
      "id": "taste",
      "label_zh": "再送去試吃",
      "params": {
       "food": "claude-mem"
      },
      "stage": "quarantine",
      "where": "both"
     },
     {
      "endpoint": "forget",
      "id": "forget",
      "label_zh": "忘掉這樣食物",
      "params": {
       "food": "claude-mem"
      },
      "stage": "quarantine",
      "where": "both"
     }
    ],
    "blocker": {
     "basis_zh": [
      "D7：不自動安裝或套用；食物只封存在專案外，絕不執行",
      "D28：只有入口、發布、C 級問題和只有你能做的前置（登入、token、常設規則）才等你"
     ],
     "if_ignored_zh": "Claude 接手（D28）；在那之前這樣食物停在封存：不會被檢查，也不會被吸收",
     "unknown_zh": [
      "Claude 什麼時候接手：沒有排程，在下一次 Claude 工作階段處理（D28）"
     ],
     "where_zh": "封存：試吃失敗（拒收：超過封存的大小或檔案數上限。）"
    },
    "details": [],
    "note_zh": "試吃失敗：拒收：超過封存的大小或檔案數上限。；Claude 會查原因再試，或記下不收的理由",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "quarantine",
    "stage_label_zh": "封存",
    "stage_notes_zh": {},
    "stages": {
     "approve": "todo",
     "build": "todo",
     "intake": "done",
     "plan": "todo",
     "quarantine": "blocked",
     "review": "planned",
     "sort": "todo",
     "static": "todo",
     "test": "planned"
    },
    "state": "blocked",
    "state_zh": "卡住",
    "waiting_on": "agent",
    "waiting_zh": "自動（Claude 接手）"
   },
   "repo": "https://github.com/thedotmack/claude-mem",
   "tasted": false,
   "tasting": null,
   "verdict": {
    "ascii": "[ ]",
    "badges": [],
    "chips": [],
    "headline": "untested",
    "label": "untested",
    "label_zh": "未測",
    "level": "not-measured",
    "reasons": [
     "no static record (taste not run)"
    ],
    "reasons_zh": [
     "沒有靜態紀錄（還沒試吃）"
    ],
    "stale": false,
    "symbol": "○"
   }
  },
  {
   "components": [
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "plugin:.claude-plugin/marketplace.json",
     "name": ".claude-plugin/marketplace.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "plugin:.claude-plugin/plugin.json",
     "name": ".claude-plugin/plugin.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "skill:court",
     "name": "court"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "docs",
     "name": "documentation"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:tests",
     "name": "scripts in tests"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "other",
     "name": "config, assets and other files"
    }
   ],
   "counts": {
    "absorb": 0,
    "excrete": 0,
    "hold": 6
   },
   "display": "alexyc9381/court-skill",
   "id": "court-skill",
   "kind": "repo",
   "paper": null,
   "pinned": {
    "commit": "2abd32db25783720faf2589b456de944534f611d",
    "commit7": "2abd32d",
    "integrity": "git-object-verified",
    "pdf_sha12": null,
    "tree_sha12": "476df81f6efb",
    "version": null
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [
     {
      "endpoint": "forget",
      "id": "forget",
      "label_zh": "忘掉這樣食物",
      "params": {
       "food": "court-skill"
      },
      "stage": "sort",
      "where": "both"
     }
    ],
    "blocker": {
     "basis_zh": [
      "D25、D28：沒有試吃就沒有判定；Claude 在試吃區官方安裝、每一組都跑、盲評，再用 record-tasting 記錄",
      "試吃 2026-11-05：N 4 次（評分 4）、P 4 次（評分 4）、C 4 次（評分 4，食物組）；紀錄 records:records/digestion-2026-11-03/taste-court-skill@1793d42"
     ],
     "if_ignored_zh": "不會被吸收；「忘掉這樣食物」可以把它從食物卡拿掉（可選）",
     "unknown_zh": [],
     "where_zh": "沒有卡點：試吃判定不收"
    },
    "details": [
     {
      "id": "plan",
      "label_zh": "看計畫",
      "stage": "plan"
     }
    ],
    "note_zh": "試吃判定：不收（多此一舉：C 覆蓋率 0.858 對 P 0.958，每案 token 約 80 倍（R2 成立））",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "sort",
    "stage_label_zh": "分流",
    "stage_notes_zh": {
     "sort": "試吃判定：不收（多此一舉：C 覆蓋率 0.858 對 P 0.958，每案 token 約 80 倍（R2 成立））",
     "test": "試吃 2026-11-05：N 4 次（評分 4）、P 4 次（評分 4）、C 4 次（評分 4，食物組）；紀錄 records:records/digestion-2026-11-03/taste-court-skill@1793d42"
    },
    "stages": {
     "approve": "skipped",
     "build": "skipped",
     "intake": "done",
     "plan": "partial",
     "quarantine": "done",
     "review": "planned",
     "sort": "done",
     "static": "done",
     "test": "done"
    },
    "state": "done",
    "state_zh": "完成",
    "waiting_on": "none",
    "waiting_zh": "沒有待辦"
   },
   "repo": "https://github.com/alexyc9381/court-skill",
   "tasted": true,
   "tasting": {
    "date": "2026-11-05",
    "food_arm": "C",
    "food_arm_graded_runs": 4,
    "verdict": "decline",
    "verdict_label_zh": "不收",
    "verdict_zh": "多此一舉：C 覆蓋率 0.858 對 P 0.958，每案 token 約 80 倍（R2 成立）"
   },
   "verdict": {
    "ascii": "[ ]",
    "badges": [],
    "chips": [
     "free-checks-passed"
    ],
    "headline": "untested",
    "label": "untested",
    "label_zh": "未測",
    "level": "static-measured",
    "reasons": [
     "no measured evidence (paid tests not run)"
    ],
    "reasons_zh": [
     "沒有實測證據（付費實測還沒跑）"
    ],
    "stale": false,
    "symbol": "○"
   }
  },
  {
   "components": [
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "skill:graphify",
     "name": "graphify"
    },
    {
     "can_absorb": false,
     "disposition": "excrete",
     "id": "instructions:AGENTS.md",
     "name": "AGENTS.md"
    },
    {
     "can_absorb": false,
     "disposition": "excrete",
     "id": "binaries",
     "name": "binary files"
    },
    {
     "can_absorb": false,
     "disposition": "excrete",
     "id": "deps",
     "name": "dependency manifests"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "docs",
     "name": "documentation"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:scripts",
     "name": "scripts in scripts"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:tests",
     "name": "scripts in tests"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:tools",
     "name": "scripts in tools"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:worked",
     "name": "scripts in worked"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "other",
     "name": "config, assets and other files"
    }
   ],
   "counts": {
    "absorb": 0,
    "excrete": 3,
    "hold": 7
   },
   "display": "Graphify-Labs/graphify",
   "id": "graphify",
   "kind": "repo",
   "paper": null,
   "pinned": {
    "commit": "8e6a6d2129d4aeffc7a0e9ed79b153f7f057f42b",
    "commit7": "8e6a6d2",
    "integrity": "git-object-verified",
    "pdf_sha12": null,
    "tree_sha12": "0c002a9e5425",
    "version": null
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [
     {
      "endpoint": "forget",
      "id": "forget",
      "label_zh": "忘掉這樣食物",
      "params": {
       "food": "graphify"
      },
      "stage": "sort",
      "where": "both"
     }
    ],
    "blocker": {
     "basis_zh": [
      "D25、D28：沒有試吃就沒有判定；Claude 在試吃區官方安裝、每一組都跑、盲評，再用 record-tasting 記錄",
      "試吃 2026-11-05：N 4 次（評分 4）、G 4 次（評分 4，食物組）；紀錄 records:records/digestion-2026-11-03/taste-graphify/erpnext@93e555b"
     ],
     "if_ignored_zh": "不會被吸收；「忘掉這樣食物」可以把它從食物卡拿掉（可選）",
     "unknown_zh": [],
     "where_zh": "沒有卡點：試吃判定沒證明比原生好（不收）"
    },
    "details": [
     {
      "id": "plan",
      "label_zh": "看計畫",
      "stage": "plan"
     }
    ],
    "note_zh": "試吃判定：沒證明比原生好（不收）（覆蓋率相同（0.933），每題 token 中位數多 38%：沒證明比原生好）",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "sort",
    "stage_label_zh": "分流",
    "stage_notes_zh": {
     "sort": "試吃判定：沒證明比原生好（不收）（覆蓋率相同（0.933），每題 token 中位數多 38%：沒證明比原生好）",
     "test": "試吃 2026-11-05：N 4 次（評分 4）、G 4 次（評分 4，食物組）；紀錄 records:records/digestion-2026-11-03/taste-graphify/erpnext@93e555b"
    },
    "stages": {
     "approve": "skipped",
     "build": "skipped",
     "intake": "done",
     "plan": "partial",
     "quarantine": "done",
     "review": "planned",
     "sort": "done",
     "static": "done",
     "test": "done"
    },
    "state": "done",
    "state_zh": "完成",
    "waiting_on": "none",
    "waiting_zh": "沒有待辦"
   },
   "repo": "https://github.com/Graphify-Labs/graphify",
   "tasted": true,
   "tasting": {
    "date": "2026-11-05",
    "food_arm": "G",
    "food_arm_graded_runs": 4,
    "verdict": "not-shown-better",
    "verdict_label_zh": "沒證明比原生好（不收）",
    "verdict_zh": "覆蓋率相同（0.933），每題 token 中位數多 38%：沒證明比原生好"
   },
   "verdict": {
    "ascii": "[!]",
    "badges": [],
    "chips": [],
    "headline": "risky",
    "label": "risky",
    "label_zh": "有疑慮",
    "level": "static-measured",
    "reasons": [
     "30 high-severity flag(s) not triaged"
    ],
    "reasons_zh": [
     "30 個高嚴重度旗標還沒分流"
    ],
    "stale": false,
    "symbol": "▲"
   }
  },
  {
   "components": [
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "hooks:plugin/hooks/hooks.json",
     "name": "plugin/hooks/hooks.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "plugin:.claude-plugin/marketplace.json",
     "name": ".claude-plugin/marketplace.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "plugin:plugin/.claude-plugin/plugin.json",
     "name": "plugin/.claude-plugin/plugin.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "plugin:plugin/.codex-plugin/plugin.json",
     "name": "plugin/.codex-plugin/plugin.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "plugin:plugin/.cursor-plugin/plugin.json",
     "name": "plugin/.cursor-plugin/plugin.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "plugin:plugin/.github/plugin/plugin.json",
     "name": "plugin/.github/plugin/plugin.json"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "skill:config",
     "name": "config"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "skill:microskills",
     "name": "microskills"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "skill:repos",
     "name": "repos"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "skill:status",
     "name": "status"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "skill:toolprune",
     "name": "toolprune"
    },
    {
     "can_absorb": false,
     "disposition": "excrete",
     "id": "instructions:CLAUDE.md",
     "name": "CLAUDE.md"
    },
    {
     "can_absorb": false,
     "disposition": "excrete",
     "id": "deps",
     "name": "dependency manifests"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "docs",
     "name": "documentation"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:docs",
     "name": "scripts in docs"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:experiments",
     "name": "scripts in experiments"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:plugin",
     "name": "scripts in plugin"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:scripts",
     "name": "scripts in scripts"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:tests",
     "name": "scripts in tests"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "exec:tokeneconomizer",
     "name": "scripts in tokeneconomizer"
    },
    {
     "can_absorb": false,
     "disposition": "hold",
     "id": "other",
     "name": "config, assets and other files"
    }
   ],
   "counts": {
    "absorb": 0,
    "excrete": 2,
    "hold": 19
   },
   "display": "microsoft/TokenEconomizer",
   "id": "tokeneconomizer",
   "kind": "repo",
   "paper": null,
   "pinned": {
    "commit": "d58755d849cd9157d29aef539f2beab3d5fee0fc",
    "commit7": "d58755d",
    "integrity": "git-object-verified",
    "pdf_sha12": null,
    "tree_sha12": "60e3957404ae",
    "version": null
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [
     {
      "endpoint": "triage",
      "id": "triage",
      "label_zh": "分流旗標（可選，終端確認碼）",
      "params": {
       "food": "tokeneconomizer"
      },
      "stage": "static",
      "where": "terminal"
     },
     {
      "endpoint": "forget",
      "id": "forget",
      "label_zh": "忘掉這樣食物",
      "params": {
       "food": "tokeneconomizer"
      },
      "stage": "static",
      "where": "both"
     }
    ],
    "blocker": {
     "basis_zh": [
      "D21、D25、D28：旗標只供參考，不擋食物：挑中的單位會重建成 OAW 程式和測試（不複製食物的程式碼），食物只在試吃區執行，旗標交給重建和 Goldfish 盲審。分流是可選的：只有要照原樣複製帶旗標的成分、或確認有毒時才需要",
      "F-GLOBAL experiments/te_harness/swebench.py:219：動到使用者的全域設定",
      "F-HOST experiments/te_bench/baselines/base.py:123：動到 host agent 設定或 MCP 註冊",
      "F-HOST experiments/te_bench/baselines/rtk.py:175：動到 host agent 設定或 MCP 註冊",
      "另有 20 個高嚴重度旗標（看食物卡的旗標）"
     ],
     "if_ignored_zh": "Claude 接手試吃（D28）；帶旗標的成分在你分流之前不能照原樣複製，重建成 OAW 程式不受影響",
     "unknown_zh": [
      "Claude 什麼時候接手：沒有排程，在下一次 Claude 工作階段處理（D28）"
     ],
     "where_zh": "靜態：23 個高嚴重度旗標（只供參考）；下一步：Claude 在試吃區試吃"
    },
    "details": [],
    "note_zh": "23 個高嚴重度旗標：只供參考，不擋這樣食物；下一步：Claude 在試吃區試吃（D25、D28）",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "static",
    "stage_label_zh": "靜態",
    "stage_notes_zh": {},
    "stages": {
     "approve": "todo",
     "build": "todo",
     "intake": "done",
     "plan": "todo",
     "quarantine": "done",
     "review": "planned",
     "sort": "todo",
     "static": "current",
     "test": "planned"
    },
    "state": "current",
    "state_zh": "目前",
    "waiting_on": "agent",
    "waiting_zh": "自動（Claude 接手）"
   },
   "repo": "https://github.com/microsoft/TokenEconomizer",
   "tasted": true,
   "tasting": null,
   "verdict": {
    "ascii": "[!]",
    "badges": [],
    "chips": [],
    "headline": "risky",
    "label": "risky",
    "label_zh": "有疑慮",
    "level": "static-measured",
    "reasons": [
     "23 high-severity flag(s) not triaged"
    ],
    "reasons_zh": [
     "23 個高嚴重度旗標還沒分流"
    ],
    "stale": false,
    "symbol": "▲"
   }
  },
  {
   "components": [
    {
     "can_absorb": true,
     "disposition": "absorb",
     "id": "sn-index",
     "name": "one-line recall index"
    },
    {
     "can_absorb": true,
     "disposition": "absorb",
     "id": "sn-guard",
     "name": "credential guard"
    },
    {
     "can_absorb": false,
     "disposition": "excrete",
     "id": "sn-hook",
     "name": "session hook"
    }
   ],
   "counts": {
    "absorb": 2,
    "excrete": 1,
    "hold": 0
   },
   "display": "example/sweet-notes",
   "id": "sweet-notes",
   "kind": "repo",
   "paper": null,
   "pinned": {
    "commit": "5555555555555555555555555555555555555555",
    "commit7": "5555555",
    "integrity": "git-object-verified",
    "pdf_sha12": null,
    "tree_sha12": "555555555555",
    "version": null
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [
     {
      "endpoint": "absorb",
      "id": "absorb",
      "label_zh": "照原樣複製吸收（可選）…",
      "params": {
       "food": "sweet-notes"
      },
      "stage": "approve",
      "where": "both"
     },
     {
      "endpoint": "forget",
      "id": "forget",
      "label_zh": "忘掉這樣食物",
      "params": {
       "food": "sweet-notes"
      },
      "stage": "approve",
      "where": "both"
     }
    ],
    "blocker": {
     "basis_zh": [
      "D21：A 級（只改機制）靜態證據就能吸收、B 級（模型會讀的文字）要試吃判定吸收、C 級問你；吸收是 Claude 重建成 OAW 程式和測試",
      "D7、D11：系統不會自動安裝或套用；照原樣複製吸收要你勾選、預覽、確認（可選的舊流程）"
     ],
     "if_ignored_zh": "Claude 接手重建（D28）；照原樣複製吸收（「照原樣複製吸收（可選）…」）是可選的舊流程",
     "unknown_zh": [
      "Claude 什麼時候接手：沒有排程，在下一次 Claude 工作階段處理（D28）"
     ],
     "where_zh": "核准：2 個成分可以吸收；Claude 依 D21 重建成 OAW 程式和測試"
    },
    "details": [],
    "note_zh": "可以吸收：2 個成分；Claude 依 D21 重建成 OAW 程式和測試，你在發布時合併（照原樣複製吸收是可選的）",
    "parity": {
     "label": "parity vs food alone: measured",
     "label_zh": "和單吃食物比（齊平底線）：實測",
     "state": "measured"
    },
    "readded_untested": 0,
    "stage": "approve",
    "stage_label_zh": "核准",
    "stage_notes_zh": {},
    "stages": {
     "approve": "current",
     "build": "todo",
     "intake": "done",
     "plan": "partial",
     "quarantine": "done",
     "review": "planned",
     "sort": "partial",
     "static": "done",
     "test": "done"
    },
    "state": "current",
    "state_zh": "目前",
    "waiting_on": "agent",
    "waiting_zh": "自動（Claude 接手）"
   },
   "repo": "https://github.com/example/sweet-notes",
   "tasted": true,
   "tasting": null,
   "verdict": {
    "ascii": "[+]",
    "badges": [],
    "chips": [],
    "headline": "nutritious",
    "label": "nutritious",
    "label_zh": "營養",
    "level": "measured",
    "reasons": [
     "measured gain with parity floor"
    ],
    "reasons_zh": [
     "實測有增益，也過了齊平底線"
    ],
    "stale": false,
    "symbol": "●"
   }
  }
 ],
 "funnel": {
  "absorbed_parts": 1,
  "agent_tasted": 2,
  "backlog_items": 0,
  "by_stage": {
   "approve": 0,
   "build": 1,
   "intake": 0,
   "plan": 0,
   "quarantine": 1,
   "review": 0,
   "sort": 2,
   "static": 1,
   "test": 0
  },
  "by_waiting": {
   "agent": 2,
   "none": 2,
   "optional": 0,
   "owner": 0,
   "planned": 0,
   "release": 1
  },
  "installed_parts": 0,
  "measured": 0,
  "rebuilt_units": 1,
  "submitted": 5,
  "tasted": 4
 },
 "pipeline": {
  "actions": {
   "absorb": {
    "endpoint": "absorb",
    "label_zh": "吸收選中的成分…",
    "where": "both"
   },
   "forget": {
    "endpoint": "forget",
    "label_zh": "忘掉這樣食物",
    "where": "both"
   },
   "remove-food": {
    "endpoint": "remove",
    "label_zh": "移除",
    "where": "both"
   },
   "restore": {
    "endpoint": "restore",
    "label_zh": "還原到這版",
    "where": "both"
   },
   "taste": {
    "endpoint": "taste",
    "label_zh": "送去試吃",
    "where": "both"
   },
   "triage": {
    "endpoint": "triage",
    "label_zh": "分流旗標（終端確認碼）",
    "where": "terminal"
   }
  },
  "automation_order": [
   "automated",
   "agent",
   "owner",
   "mixed",
   "planned"
  ],
  "automation_zh": {
   "agent": "自動（Claude 接手）",
   "automated": "自動",
   "mixed": "部分自動",
   "owner": "需要你",
   "planned": "規劃中"
  },
  "empty_zh": "還沒有食物：在「你點名」貼上 GitHub 網址或 arXiv 論文網址按「送去試吃」，或在「每週偵查」按「立即偵查」再勾選候選。",
  "inlets": [
   {
    "id": "scout",
    "label_zh": "每週偵查 → 相關性過濾 → 你確認",
    "steps": [
     {
      "automation": "owner",
      "label_zh": "你按「立即偵查」，每週一次：沒有排程，漏掉的一週就看不到那週推送的 repo"
     },
     {
      "automation": "automated",
      "label_zh": "系統依更新時間搜尋 GitHub 最近 7 天推送的 repo，只記錄候選"
     },
     {
      "automation": "automated",
      "label_zh": "相關性過濾：和 coding agent skill／harness 無關的不經審查就濾掉；星數只決定排序"
     },
     {
      "automation": "owner",
      "label_zh": "你勾選要試哪些"
     }
    ]
   },
   {
    "id": "named",
    "label_zh": "你點名",
    "steps": [
     {
      "automation": "owner",
      "label_zh": "你給 GitHub repo 或 arXiv 論文的網址，可以一次很多個"
     }
    ]
   }
  ],
  "legend": [
   "done",
   "partial",
   "current",
   "blocked",
   "removed",
   "todo",
   "planned",
   "skipped"
  ],
  "live_stages": {
   "ingest": "intake",
   "quarantine": "quarantine",
   "static": "static"
  },
  "order": [
   "intake",
   "quarantine",
   "static",
   "plan",
   "review",
   "test",
   "sort",
   "approve",
   "build"
  ],
  "stages": [
   {
    "actions": [
     "taste",
     "forget"
    ],
    "automation": "mixed",
    "decisions": [
     "D4"
    ],
    "id": "intake",
    "label": "intake",
    "label_zh": "入口",
    "organ_zh": "口",
    "steps": [
     {
      "automation": "owner",
      "label_zh": "你勾選偵查候選或點名 repo／論文：這就是確認"
     },
     {
      "automation": "automated",
      "label_zh": "批次去重：同一個 repo 只收一次，同一篇論文的各版本也只收一次"
     },
     {
      "automation": "automated",
      "label_zh": "確認後立刻送去免費試吃，不再逐樣問你"
     }
    ],
    "summary_zh": "你勾選或點名就是同意試吃（D4）：兩條入口匯成一份食物清單，同一個 repo 或同一篇論文只收一次，接著立刻免費試吃。"
   },
   {
    "actions": [
     "taste",
     "forget"
    ],
    "automation": "automated",
    "decisions": [
     "D7"
    ],
    "id": "quarantine",
    "label": "quarantine",
    "label_zh": "封存",
    "organ_zh": "食道",
    "steps": [
     {
      "automation": "automated",
      "label_zh": "repo：hardened git fetch，固定 commit"
     },
     {
      "automation": "automated",
      "label_zh": "論文：只用 https 抓 arXiv 中繼資料和固定版本的 PDF（有大小和時間上限），記 sha256；PDF 只檢查開頭，不解析"
     },
     {
      "automation": "automated",
      "label_zh": "唯讀 tar，放在專案外"
     }
    ],
    "summary_zh": "repo 固定在 pinned SHA、論文固定在 arXiv 版本＋sha256，唯讀封存在專案外的 LAB_HOME；不解壓、不 import、不執行。"
   },
   {
    "actions": [
     "taste",
     "triage",
     "forget"
    ],
    "automation": "mixed",
    "decisions": [
     "D5",
     "D7"
    ],
    "id": "static",
    "label": "static checks",
    "label_zh": "靜態",
    "organ_zh": "胃",
    "steps": [
     {
      "automation": "automated",
      "label_zh": "repo：檔案角色、授權、hooks／MCP／腳本、旗標；論文：標題、作者、版本、授權"
     },
     {
      "automation": "automated",
      "label_zh": "把 repo 拆成成分（論文的單位由 Claude 當 Elephant 拆，或匯入紀錄）"
     },
     {
      "automation": "agent",
      "label_zh": "旗標交給重建和 Goldfish 盲審；食物接著送去試吃區（D21、D25、D28）"
     },
     {
      "automation": "owner",
      "label_zh": "可選：你分流高嚴重度旗標（終端確認碼）；只有要照原樣複製帶旗標的成分或確認有毒時才需要"
     }
    ],
    "summary_zh": "免費靜態檢查，把食物拆成成分；靜態規則只舉旗，不判有毒。旗標只供參考，不擋食物（D28）：下一步是 Claude 試吃。"
   },
   {
    "actions": [],
    "automation": "mixed",
    "decisions": [
     "D10",
     "D11"
    ],
    "id": "plan",
    "label": "plan",
    "label_zh": "計畫",
    "organ_zh": "十二指腸",
    "steps": [
     {
      "automation": "automated",
      "label_zh": "系統測試計畫：依證據自動產生"
     },
     {
      "automation": "planned",
      "label_zh": "Elephant 依紀錄的決定擬吸收提案，也替論文拆成分（今天只能匯入，標成歷史證據，不計入判定）"
     }
    ],
    "summary_zh": "系統依證據擬測試計畫，最便宜、又能分辨的測試排前面；Elephant 擬吸收提案。"
   },
   {
    "actions": [],
    "automation": "planned",
    "decisions": [
     "D10",
     "D15"
    ],
    "id": "review",
    "label": "blind review",
    "label_zh": "盲審",
    "organ_zh": "肝",
    "steps": [
     {
      "automation": "planned",
      "label_zh": "Goldfish 零脈絡盲審（啟動 recipe、argv、init event 都要記錄）"
     },
     {
      "automation": "planned",
      "label_zh": "Elephant 解決發現"
     }
    ],
    "summary_zh": "Goldfish 在驗證過的零脈絡下盲審我們的草稿，Elephant 解決發現。"
   },
   {
    "actions": [
     "forget"
    ],
    "automation": "mixed",
    "decisions": [
     "D11",
     "D13",
     "D25"
    ],
    "id": "test",
    "label": "tests",
    "label_zh": "實測",
    "organ_zh": "小腸",
    "steps": [
     {
      "automation": "agent",
      "label_zh": "Claude 在試吃區試吃：題目先凍結、每一組（原生、食物、OAW 版本）都跑、盲評，記成試吃紀錄"
     },
     {
      "automation": "planned",
      "label_zh": "離線整合 T1：名稱碰撞、doctor／migrate 往返"
     },
     {
      "automation": "planned",
      "label_zh": "可拋棄沙箱試跑 TX（level 2）"
     },
     {
      "automation": "planned",
      "label_zh": "行為 A/B：模型面向的文字要過"
     },
     {
      "automation": "planned",
      "label_zh": "整合檢查 T4：退步、觸發衝突、context 預算、指示衝突"
     },
     {
      "automation": "planned",
      "label_zh": "齊平底線 P：OAW 吃完 對 單吃食物（C ≥ B）"
     }
    ],
    "summary_zh": "Claude 在試吃區試吃（D25、D28）：官方安裝、每一組都跑、盲評、照事先寫死的規則判定，結果用 record-tasting 記錄；食物組沒跑就沒有判定。引擎自己的測試在常設政策內由便宜到貴跑，還是規劃中。"
   },
   {
    "actions": [
     "forget"
    ],
    "automation": "mixed",
    "decisions": [
     "D2",
     "D5",
     "D16",
     "D17",
     "D18"
    ],
    "id": "sort",
    "label": "verdicts",
    "label_zh": "分流",
    "organ_zh": "大腸",
    "steps": [
     {
      "automation": "automated",
      "label_zh": "成分判定（今天只有靜態量測）"
     },
     {
      "automation": "automated",
      "label_zh": "模型面向的文字和機制拆開：文字過 A/B 才能吸收"
     },
     {
      "automation": "agent",
      "label_zh": "試吃判定：吸收、插上、不收、沒證明比較好，或沒有判定（照試吃紀錄）"
     },
     {
      "automation": "planned",
      "label_zh": "套用整合檢查（T4）和齊平底線（P）的關口"
     },
     {
      "automation": "planned",
      "label_zh": "沒建的項目寫「未量測（規劃：<等級>）」，規劃的等級另放一欄"
     }
    ],
    "summary_zh": "每個成分判定吸收／排掉／暫留，附原因和證據等級；整合檢查和齊平底線的關口在這裡套用。"
   },
   {
    "actions": [
     "absorb",
     "forget"
    ],
    "automation": "mixed",
    "decisions": [
     "D7",
     "D11",
     "D21"
    ],
    "id": "approve",
    "label": "approval",
    "label_zh": "核准",
    "organ_zh": "門靜脈",
    "steps": [
     {
      "automation": "agent",
      "label_zh": "Claude 依 D21 把挑中的單位重建成 OAW 程式和測試，記成吸收紀錄"
     },
     {
      "automation": "owner",
      "label_zh": "C 級（執行食物程式、新增執行期相依、常設決定沒涵蓋的授權或 CLI 選擇、移除 skill、超出預算）問你"
     },
     {
      "automation": "owner",
      "label_zh": "可選：照原樣複製吸收（你勾選成分，先預覽再確認）"
     }
    ],
    "summary_zh": "D21：Claude 把挑中的單位重建成 OAW 程式和測試（A 級靜態證據就夠、B 級要試吃判定吸收），用 record-absorption 記錄；只有 C 級問你。系統不會自動安裝或套用；照原樣複製吸收是可選的舊流程。"
   },
   {
    "actions": [
     "remove-food",
     "restore",
     "taste",
     "absorb",
     "forget"
    ],
    "automation": "mixed",
    "decisions": [
     "D3",
     "D6",
     "D12",
     "D14"
    ],
    "id": "build",
    "label": "build",
    "label_zh": "版本",
    "organ_zh": "全身",
    "steps": [
     {
      "automation": "owner",
      "label_zh": "發布：你合併 PR，整個分支一次決定，不是逐樣核准（D21、D28）"
     },
     {
      "automation": "automated",
      "label_zh": "還原點 → 安裝 → 版本 → 和預設比"
     },
     {
      "automation": "automated",
      "label_zh": "吸收時照原樣複製 skill 文字，附上食物的授權檔和出處說明（重新實作成 OAW 部件還沒做）"
     },
     {
      "automation": "owner",
      "label_zh": "還原到任何一版（線性：只有移除版本，沒有逐項開關）"
     },
     {
      "automation": "owner",
      "label_zh": "移除（含 EGM）、加回：再加回要重新測試"
     },
     {
      "automation": "planned",
      "label_zh": "每版引用清單：用在哪裡／沒採用的原因"
     },
     {
      "automation": "planned",
      "label_zh": "release 目標：2.0.0 打 tag 之後，相容的新增進 2.x、不相容的等 3.0.0"
     }
    ],
    "summary_zh": "每次吸收或移除都產生 2.0.0+build.N.<hash7> 和還原點，列出和預設比的效果與證據等級；可一鍵線性還原，任何 skill（含 EGM）都能移除。"
   }
  ],
  "states_zh": {
   "blocked": "卡住",
   "current": "目前",
   "done": "完成",
   "partial": "部分完成",
   "planned": "規劃中",
   "removed": "已移除",
   "skipped": "不需要",
   "todo": "還沒到"
  },
  "symbols": {
   "blocked": "⊗",
   "current": "◉",
   "done": "●",
   "partial": "◐",
   "planned": "┄",
   "removed": "⊖",
   "skipped": "–",
   "todo": "○"
  },
  "tasting_verdicts_zh": {
   "absorb": "吸收",
   "decline": "不收",
   "no-verdict": "沒有判定",
   "not-shown-better": "沒證明比原生好（不收）",
   "plug-in": "插上（接上官方版，不吸收）"
  },
  "tiers_zh": {
   "A": "A 級：只改機制、不碰模型會讀的文字、不執行食物程式、可還原（D17 允許靜態證據）",
   "B": "B 級：模型會讀的文字，要試吃判定吸收（齊平以上）",
   "C": "C 級：會執行食物程式、新增執行期相依、常設決定沒涵蓋的授權或 CLI 選擇、移除 skill、超出預算：問你"
  },
  "waiting_order": [
   "owner",
   "agent",
   "release",
   "optional",
   "planned",
   "none"
  ],
  "waiting_zh": {
   "agent": "自動（Claude 接手）",
   "none": "沒有待辦",
   "optional": "只有可選的決定",
   "owner": "等你",
   "planned": "等規劃中的步驟（還沒自動化）",
   "release": "等發布（合併 PR 時一次決定）"
  }
 },
 "release_pending": {
  "branches": [
   "claude/oaw-2"
  ],
  "foods": [
   "arxiv-2606-03979"
  ],
  "note_zh": "D21、D28：發布是整個分支一次決定：你合併 PR，這些單位一起進正式版本；不是逐樣核准",
  "units": 1,
  "waiting_zh": "等發布（合併 PR 時一次決定）"
 },
 "schema": "oaw-catalog-view/3"
} as const
