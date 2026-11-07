# X3b 結果：W1 修正後重跑 X3（2026-11-07）

依 `PREREG.md`（b1a7dce）。環境：Linux，Claude Code 2.1.287，只用訂閱（30 次新作答加 6 次沿用，apiKeySource 都是 none）。OAW 2.0.0 = 332c585，2.0.1 = d32561f。

## 結論
**三個模型都通過。** A（一行政策 + `oaw-review` skill，dry run）：
- Haiku 6/6，Opus 5/6，Sonnet 5/6。
- 0 組（2.0.0）在三個模型都是 2/6，只有 light 對。
- 每個模型 A 都至少 5/6，而且比 0 多 3–4 題。

d32561f 的兩個修正都有效：
- 6 個 deep 作答全部在改程式之前跑了 `suggest`、拿到 deep、提出計畫後停下。X3 是 0/2。
- Haiku 這次在 D2 寫的是 `migrations/`，判成 deep。X3 裡寫 `migrations` 被判成 light。

## 數字（每格 1 次；明細在 `rows.json`）

| 模型 | 組 | 做對 | light | standard | deep | 動手前跑 suggest | 改完後跑 suggest | 叫用 oaw-review | token 合計 |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 0（沿用 X3） | 2/6 | 2/2 | 0/2 | 0/2 | 0/6 | 0/6 | 0/6 | 1,290,528 |
| Haiku 5.5 | A | **6/6** | 2/2 | 2/2 | 2/2 | 6/6 | 4/6 | 1/6 | 1,086,561 |
| Opus 5.5 | 0 | 2/6 | 2/2 | 0/2 | 0/2 | 0/6 | 1/6 | 0/6 | 459,494 |
| Opus 5.5 | A | **5/6** | 2/2 | 1/2 | 2/2 | 6/6 | 3/6 | 0/6 | 628,353 |
| Sonnet 5.5 | 0 | 2/6 | 2/2 | 0/2 | 0/2 | 0/6 | 0/6 | 0/6 | 344,137 |
| Sonnet 5.5 | A | **5/6** | 2/2 | 1/2 | 2/2 | 6/6 | 2/6 | 4/6 | 498,119 |

- 「改完後跑 suggest」不含 deep：A 的 deep 作答停在改程式之前，本來就沒有「改完後」。
- 36 次都正常結束，最後測試都通過，沒有 commit，也沒有動 `.oaw/settings.json`。

## 看到的行為
1. **A 唯一的錯是 S2，Opus 和 Sonnet 都錯在這題**：
   - 動手前給的是 `ledger/reports.py ledger/reports/`，路徑清單沒有行數，判成 light。
   - 改完 392 行之後，兩個都沒有再跑 `suggest`，所以沒發現其實是 standard。
   - 同一個模型在 L1、L2 改完後都有再跑。看起來是動手前的檢查一說 light，agent 就把改完後那一步當成可以省略。
   - Haiku 在這題有再跑。
2. **deep 6/6 都停在改程式之前**：
   - 5 次把計畫存成 `docs/plans/*.md`。
   - Haiku D2 把計畫寫在回覆裡，說「主機要我不要主動建立規劃文件」，所以沒存檔。這是 Claude Code 系統提示和 skill「存成 `docs/plans/<name>.md`」之間的衝突，W1 可以考慮處理。
   - 6 次都在最後請使用者選：先跑設計審查（要關掉 dry run），或不審就直接實作。
3. **改完後的檢查有用**：Haiku S2 動手前判 light，改完後判 standard；X3 也看過同樣的情形。
4. **skill 叫用變多了，但還是靠政策行**：
   - A 裡 18 次叫用 `oaw-review` 5 次（Sonnet 4、Haiku 1、Opus 0）。X3 是 0/12。
   - skill 的 description 沒改，所以這是 skill 內容或模型的差別，不是 description 的效果。
   - 每次都另外用 Bash 跑了 `suggest`。
5. **0 組沒跑檢查的情況照舊**：
   - 2.0.0 的 0 組 18 次裡只有 Opus D1 跑了一次 `suggest`，而且是寫完 workflow 之後，拿到 deep 也已經晚了。
   - 其他 deep 都直接寫，standard 都沒審查。

## 花費
- **X3b 新跑 30 次：3,016,664 logical token**，在 9M 上限內，不含 cache 讀取是 516,478。沿用的 Haiku 0 組 6 次（1.29M）在 X3 已經算過。
- 單次 33,820–275,732。Opus、Sonnet 每次的中位數是 60k–82k，Haiku 是 160k 上下：Haiku 比較常一個一個呼叫工具。
- **A 比 0 貴多少**（同模型的 token 合計）：Opus 1.37 倍，Sonnet 1.45 倍，Haiku 0.84 倍。每格只跑 1 次，加上 deep 在 A 組提早停下，這些比值只能當描述，不能當成本判定。

## 偏離 PREREG
沒有。停止規則一次都沒觸發。上一節的「改完後跑 suggest」欄是額外加的描述，不影響判定。
