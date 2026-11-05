// Generated from a real catalog.py run (4 foods tasted on 2026-11-05) plus one synthetic food at approval.
// Local paths are not part of view.json.
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
       "food": "arxiv-2606-03979"
      },
      "stage": "quarantine",
      "where": "both"
     },
     {
      "endpoint": "forget",
      "id": "forget",
      "label_zh": "忘掉這樣食物",
      "params": {
       "food": "arxiv-2606-03979"
      },
      "stage": "quarantine",
      "where": "both"
     }
    ],
    "blocker": {
     "basis_zh": [
      "D7：不自動安裝或套用；食物只封存在專案外，絕不執行"
     ],
     "if_ignored_zh": "這樣食物停在封存：不會被檢查，也不會被吸收",
     "unknown_zh": [],
     "where_zh": "封存：試吃失敗（拒收：只接受 https 和 arXiv 的網址（轉址也一樣）。）"
    },
    "details": [],
    "note_zh": "試吃失敗：拒收：只接受 https 和 arXiv 的網址（轉址也一樣）。",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "quarantine",
    "stage_label_zh": "封存",
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
    "waiting_on": "owner",
    "waiting_zh": "等你"
   },
   "repo": "https://arxiv.org/abs/2606.03979",
   "tasted": false,
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
      "D7：不自動安裝或套用；食物只封存在專案外，絕不執行"
     ],
     "if_ignored_zh": "這樣食物停在封存：不會被檢查，也不會被吸收",
     "unknown_zh": [],
     "where_zh": "封存：試吃失敗（拒收：超過封存的大小或檔案數上限。）"
    },
    "details": [],
    "note_zh": "試吃失敗：拒收：超過封存的大小或檔案數上限。",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "quarantine",
    "stage_label_zh": "封存",
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
    "waiting_on": "owner",
    "waiting_zh": "等你"
   },
   "repo": "https://github.com/thedotmack/claude-mem",
   "tasted": false,
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
    }
   ],
   "counts": {
    "absorb": 0,
    "excrete": 3,
    "hold": 7
   },
   "display": "safishamsi/graphify",
   "id": "graphify",
   "kind": "repo",
   "paper": null,
   "pinned": {
    "commit": "59b5ab1151e031fb42e39cfc9a50bf96f2d57ae0",
    "commit7": "59b5ab1",
    "integrity": "unverified-against-commit",
    "pdf_sha12": null,
    "tree_sha12": "a5bbbc2431af",
    "version": null
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [
     {
      "endpoint": "triage",
      "id": "triage",
      "label_zh": "分流旗標（終端確認碼）",
      "params": {
       "food": "graphify"
      },
      "stage": "static",
      "where": "terminal"
     },
     {
      "endpoint": "forget",
      "id": "forget",
      "label_zh": "忘掉這樣食物",
      "params": {
       "food": "graphify"
      },
      "stage": "static",
      "where": "both"
     }
    ],
    "blocker": {
     "basis_zh": [
      "D5、D7：靜態規則只舉旗、不判有毒；有高嚴重度旗標的成分在你分流之前一律暫留",
      "F-HID graphify/install.py:487：隱藏或雙向控制字元",
      "F-HID graphify/llm.py:638：隱藏或雙向控制字元",
      "F-HID tests/test_build_merge_hyperedges_and_prune.py:331：隱藏或雙向控制字元",
      "另有 29 個高嚴重度旗標（看食物卡的旗標）"
     ],
     "if_ignored_zh": "這樣食物停在靜態：帶旗標的成分一直暫留，整樣食物不會往下走，也不會被吸收",
     "unknown_zh": [],
     "where_zh": "靜態：32 個高嚴重度旗標待你分流"
    },
    "details": [],
    "note_zh": "32 個高嚴重度旗標待你分流",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "static",
    "stage_label_zh": "靜態",
    "stages": {
     "approve": "todo",
     "build": "todo",
     "intake": "done",
     "plan": "todo",
     "quarantine": "done",
     "review": "planned",
     "sort": "todo",
     "static": "blocked",
     "test": "planned"
    },
    "state": "blocked",
    "state_zh": "卡住",
    "waiting_on": "owner",
    "waiting_zh": "等你"
   },
   "repo": "https://github.com/safishamsi/graphify",
   "tasted": true,
   "verdict": {
    "ascii": "[!]",
    "badges": [],
    "chips": [],
    "headline": "risky",
    "label": "risky",
    "label_zh": "有疑慮",
    "level": "static-measured",
    "reasons": [
     "32 high-severity flag(s) not triaged"
    ],
    "reasons_zh": [
     "32 個高嚴重度旗標還沒分流"
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
    "commit": "519c65fff990e14480accca8a7629b3befcb7630",
    "commit7": "519c65f",
    "integrity": "unverified-against-commit",
    "pdf_sha12": null,
    "tree_sha12": "496a0e170e60",
    "version": null
   },
   "pipeline": {
    "ab_holds": 0,
    "actions": [
     {
      "endpoint": "triage",
      "id": "triage",
      "label_zh": "分流旗標（終端確認碼）",
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
      "D5、D7：靜態規則只舉旗、不判有毒；有高嚴重度旗標的成分在你分流之前一律暫留",
      "F-GLOBAL experiments/te_harness/swebench.py:219：動到使用者的全域設定",
      "F-HOST experiments/te_bench/baselines/base.py:123：動到 host agent 設定或 MCP 註冊",
      "F-HOST experiments/te_bench/baselines/rtk.py:175：動到 host agent 設定或 MCP 註冊",
      "另有 20 個高嚴重度旗標（看食物卡的旗標）"
     ],
     "if_ignored_zh": "這樣食物停在靜態：帶旗標的成分一直暫留，整樣食物不會往下走，也不會被吸收",
     "unknown_zh": [],
     "where_zh": "靜態：23 個高嚴重度旗標待你分流"
    },
    "details": [],
    "note_zh": "23 個高嚴重度旗標待你分流",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "static",
    "stage_label_zh": "靜態",
    "stages": {
     "approve": "todo",
     "build": "todo",
     "intake": "done",
     "plan": "todo",
     "quarantine": "done",
     "review": "planned",
     "sort": "todo",
     "static": "blocked",
     "test": "planned"
    },
    "state": "blocked",
    "state_zh": "卡住",
    "waiting_on": "owner",
    "waiting_zh": "等你"
   },
   "repo": "https://github.com/microsoft/TokenEconomizer",
   "tasted": true,
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
   "display": "sweet-notes",
   "id": "sweet-notes",
   "kind": "paper",
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
      "endpoint": "absorb",
      "id": "absorb",
      "label_zh": "吸收選中的成分…",
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
      "D7、D11：你決定吸收哪些成分"
     ],
     "if_ignored_zh": "什麼都不會變",
     "unknown_zh": [],
     "where_zh": "停在核准：等你選要吸收哪些成分"
    },
    "details": [],
    "note_zh": "兩個成分可以吸收，一個排掉。",
    "parity": {
     "label": "parity vs food alone: not tested",
     "label_zh": "和單吃食物比（齊平底線）：未測",
     "state": "not-tested"
    },
    "readded_untested": 0,
    "stage": "approve",
    "stage_label_zh": "核准",
    "stages": {
     "approve": "current",
     "build": "todo",
     "intake": "done",
     "plan": "done",
     "quarantine": "done",
     "review": "done",
     "sort": "done",
     "static": "done",
     "test": "done"
    },
    "state": "current",
    "state_zh": "目前",
    "waiting_on": "optional",
    "waiting_zh": "只有可選的決定"
   },
   "repo": "https://github.com/example/sweet-notes",
   "tasted": false,
   "verdict": {
    "ascii": "[ ]",
    "badges": [],
    "chips": [],
    "headline": "nutritious",
    "label": "nutritious",
    "label_zh": "營養",
    "level": "static-measured",
    "reasons": [
     "no static record (taste not run)"
    ],
    "reasons_zh": [
     "沒有靜態紀錄（還沒試吃）"
    ],
    "stale": false,
    "symbol": "✓"
   }
  }
 ],
 "funnel": {
  "absorbed_parts": 0,
  "backlog_items": 0,
  "by_stage": {
   "approve": 0,
   "build": 0,
   "intake": 0,
   "plan": 0,
   "quarantine": 2,
   "review": 0,
   "sort": 0,
   "static": 2,
   "test": 0
  },
  "measured": 0,
  "submitted": 4,
  "tasted": 2
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
   "owner",
   "mixed",
   "planned"
  ],
  "automation_zh": {
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
      "label_zh": "把 repo 拆成成分（論文的成分要 Elephant 拆，見「計畫」）"
     },
     {
      "automation": "owner",
      "label_zh": "高嚴重度旗標由你分流（終端確認碼）"
     }
    ],
    "summary_zh": "免費靜態檢查，把食物拆成成分；靜態規則只舉旗，不判有毒。"
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
    "actions": [],
    "automation": "planned",
    "decisions": [
     "D11",
     "D13"
    ],
    "id": "test",
    "label": "tests",
    "label_zh": "實測",
    "organ_zh": "小腸",
    "steps": [
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
    "summary_zh": "在常設政策內由便宜到貴自動跑：每個暫留先跑免費 Stage 0；會執行食物程式碼的只在可拋棄沙箱（level 2）。"
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
    "automation": "owner",
    "decisions": [
     "D7",
     "D11"
    ],
    "id": "approve",
    "label": "owner approval",
    "label_zh": "核准",
    "organ_zh": "門靜脈",
    "steps": [
     {
      "automation": "owner",
      "label_zh": "你勾選成分，先預覽再確認"
     }
    ],
    "summary_zh": "你決定吸收哪些成分；系統不會自動安裝或套用。"
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
  }
 },
 "schema": "oaw-catalog-view/2"
} as const
