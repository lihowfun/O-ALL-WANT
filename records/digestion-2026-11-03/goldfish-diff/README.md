# D21 零上下文金魚審查：程式 diff

依 D21，這一輪的金魚只審程式 diff 和測試，不審文件。審查包分 3 份，對應 3 組實作：

| 審查包 | 單位 | 主要檔案 |
|---|---|---|
| `packets/measure.md` | OAW-01、OAW-03、OAW-04 | `scripts/improvement.py`、`scripts/oaw_common.py` |
| `packets/evidence.md` | OAW-12、OAW-15 | `scripts/context_hub.py`、`scripts/oaw_common.py` |
| `packets/citations.md` | OAW-02（部分）、OAW-21、OAW-22 | `scripts/wiki_sync.py`、`scripts/oaw_common.py` |

- `build_packets.py`：從 OAW repo 的 diff 和 `../ingest/backlog.json` 的設計產生審查包。
- `run_goldfish.py`：和 PRE-02 同一個執行器。零上下文 recipe、遮蔽、API key 防呆都一樣。

## 怎麼跑
Owner 只要在這台電腦登入一次 Claude Code CLI（`claude auth login --claudeai`，選 Claude 訂閱，不要選 Console）。之後由 Claude 在這台執行：

```
py -3 records/digestion-2026-11-03/goldfish-diff/run_goldfish.py --dry-run
py -3 records/digestion-2026-11-03/goldfish-diff/run_goldfish.py --claude "<claude 執行檔>"
```

- 結果寫到 `results/<packet>.json`，push 回 `records`。
- 依 D20，canary 不會回答 none（CLI 一定帶入預設系統提示和帳號提醒），標記為「零專案上下文」。
- Elephant 處理發現：bug 和 security 直接修在 `claude/oaw-2` 並補測試；只有 Elephant 不接受的 blocker 才交給 owner（D21）。
