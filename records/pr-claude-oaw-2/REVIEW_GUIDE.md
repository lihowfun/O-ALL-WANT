# 審查指南：`claude/oaw-2`（給 Codex）

PR 很大（約 57 個 commit、56 個檔案，其中一半是新的 catalog 原型和測試）。建議照下面的順序看，並優先看風險最高的地方。

## 先讀
1. `docs/SKILL_INTAKE.md`：正式流程（D4–D24）、站別表、原型 v0 還沒做的事。
2. records 分支 `records/digestion-2026-11-03/ingest/DECISIONS.md`：D1–D27，尤其 D7、D13、D14、D17、D21–D27。
3. records 分支 `records/digestion-2026-11-03/RELEASE_v1.md` 和 `REVIEW_2026-11-04.md`：第一輪做了什麼，以及 owner 自己做的流程審視。

## 風險最高、最值得看的地方
| 地方 | 為什麼 |
|---|---|
| `scripts/oaw_common.py` `SECRET_PATTERNS`、`evidence_write_refusal` | 預設擋下寫入，沒有略過旗標；誤判會擋到正常筆記，漏判會讓憑證寫進 evidence |
| `scripts/goldfish_review.py run` | 啟動 `claude -p` subprocess；計費檢查、遮蔽、零上下文 recipe |
| `scripts/catalog.py` `https_get`、`fetch_arxiv`、`read_local_pdf`、封存 | 唯一新的對外連線；大小上限、https、主機白名單、`%PDF-` 檢查 |
| `scripts/catalog_ui_server.py` `POST /api/question` | 新的寫入 endpoint；token、Host、origin、body 上限、淨化 |
| `scripts/oaw_common.py` `resolve_cli`、`_npm_shim` | 只做字面比對的 node_modules 限制（刻意讓 `npm link` 能用）；Windows 才會用到的路徑 |
| `scripts/improvement.py` `compare` | OAW-03 的 trigger 規則、OAW-04 的覆蓋率；舊 spec 的判定不能改變 |
| `scripts/wiki_sync.py` 引用 lint 和 memory-check | `--strict` 的行為改變；symlink、大小寫、fence 的邊界情況 |
| `scripts/harness_check.py` `CHECK_TIMEOUT` | 從 360 秒改成 900 秒；理由在 commit message |

## 金魚已經提過、已處理的
不用重複回報；如果你認為處理錯了，歡迎指出：
- `records/digestion-2026-11-03/goldfish-diff/resolution.json`：34 個發現，第一輪 8 個單位。
- `records/digestion-2026-11-03/goldfish-diff/resolution-sleep.json`：13 個發現，memory-check。
- `records/digestion-2026-11-03/codemap-stage0/goldfish/`：Stage 0-α 的題目審查，以及 `evals/code-map/PREREG.md` 的修訂紀錄 A1。

## 怎麼跑
- `py -3 scripts/harness_check.py`（Windows）或 `python3 scripts/harness_check.py`。在這台 Windows 11 上要 6–8 分鐘。
- 消化系統頁面：`python scripts/catalog.py ui --target <專案>`。只接受 127.0.0.1。
- 程式碼索引：`python scripts/code_index.py find "<描述>" --root .`。

## 刻意沒有做的
- B 級（模型會讀的文字）都沒有上線：沒有任何 skill 或範本指向 `cites`、`code_index.py` 或 `recall --index`（D17、D24）。
- catalog 原型 v0 的第 8 站還沒自動分級。
- 早期 3 個 commit 的標題含 game 或 play，要 force-push 才能改，所以沒改。
