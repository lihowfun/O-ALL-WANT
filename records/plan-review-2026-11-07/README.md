# OAW 2.0.1 動工計畫的審查（2026-11-07）

被審的是 `claude/oaw-2` 上 `docs/plans/v2.0.1-execution.md` 的初稿，原文在 `draft-as-reviewed.md`。依 D31，新的設計文件屬於 deep，所以給兩位零上下文的審查者各審一次，兩邊互相看不到對方的意見。

## 怎麼跑

兩邊拿到的東西相同：
- 一份初稿；
- 一份 OAW 2.0.0 的程式副本（`claude/oaw-2` HEAD）；
- `evidence/` 底下的檔案：owner 的原話、validation 的 RESULT、code map 比較、EGM 自測的 RESULT、D21–D31 的決定。

### EGM
- 用 Claude Code 2.1.287 跑 `claude -p`，模型是 Opus 5.5，effort high。
- 用 `--plugin-dir` 載入 V2 內附的 EGM（固定在 f0ba151），沒有安裝到使用者層。
- 跑的是 `/egm:egm-review` 的 `Step: uninterrupted` 完整流程，提示在 `egm/prompt.txt`。
- 開放的工具只有 Read、Write、Glob、Grep、Agent。
- 訂閱計費，apiKeySource 是 none。

### Codex
- `codex exec --sandbox read-only`，模型 `gpt-6.1-sol`，reasoning high，提示在 `codex/prompt.txt`。

## 花費

| | EGM | Codex |
|---|---|---|
| logical token | 18,480,203 | 1,085,264 |
| 其中快取讀取 | 17,134,038 | 946,560 |
| 不含快取讀取 | 1,346,165 | 138,704 |
| 子 agent | 9 個（zoom-out ×2、comprehension、design、structural、style ×2、implementation-readiness、codebase-details），全部完成 | — |
| 掛鐘時間 | 約 31 分鐘 | 約 5 分鐘 |

- 明細在 `usage.json`。
- **偏差**：EGM 這一次就超過 D13 每輪 10M 的開銷上限。原因是預估沿用了 EGM 自測在小案例上量到的每次約 1.1M，沒有考慮文件和 context 的大小。計畫的 W1 因此加上「開跑前先估成本、設上限」。

## 結果

- **EGM**：18 個發現，3 blocker、13 major、2 minor，見 `egm/report.json`；各階段的報告也在 `egm/`。
- **Codex**：15 個發現，10 major、5 minor，見 `codex/report.json`。
- **怎麼處理**：寫在計畫的附錄 B。33 個發現裡，30 個照改、1 個部分採納、2 個不改，不改的理由也寫在附錄 B。
- **不能這樣解讀**：只審了一份文件，沒有評分，不能拿來比較 EGM 和 Codex 誰比較好。兩者的正式比較是計畫裡的 X2。

## 不在這裡的東西

- 完整的對話紀錄（stream-json）和工作區留在本機，沒有放上來。
