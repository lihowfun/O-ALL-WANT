# graphify 試吃（agent 層）結果

依 `PREREG.md`（題目 sha256 df4e53cc，凍結於作答之前）。2026-11-04，WSL、Claude Code 訂閱（每次 apiKeySource none），claude-opus-5-5，每組每題 1 次，共 18 次，3.79M token（含 cache），在 graphify 的 10M 上限內。

| 組 | 事實覆蓋率 | 必要事實全對 | 錯誤陳述 | 每題 token 中位數 | 工具呼叫中位數 | 每題秒數中位數 | token 總量 |
|---|---|---|---|---|---|---|---|
| N 原生 | 0.955 | 6/6 | 0 | 202,251 | 17 | 51 | 1,432,773 |
| G graphify 0.9.101 | 0.955 | 6/6 | 3 | 230,086 | 14.5 | 55 | 1,413,267 |
| S OAW `code_index.py` | 0.921 | 6/6 | 3 | 157,762 | 9.5 | 48 | 944,430 |

## 判定（照事先寫死的規則）
- G：沒有證明比原生好（覆蓋率相同，token 中位數多 14%）。
- S：沒有證明比原生好（覆蓋率差 0.034，token 中位數少 22%，未達 30% 門檻；總量少 34%，工具呼叫少 44%）。

## 觀察
- 天花板效應：原生 agent 不靠地圖就答對每一題的必要事實，題目拉不開差距。
- G 每次都照它的 CLAUDE.md 規則先跑 `graphify query`（6 次中 6 次），回傳的是 2,000 token 截斷的子圖（找到 500–1,000 個節點），之後 agent 回到 grep 和讀檔。
- S 每次都先跑 `code_index.py find`，也用 `callers`。

## 偏差
- G、S 有 Bash（只登記了各自的工具），但 Claude Code 會自動放行唯讀指令（grep、sed -n、cat、ls），所以這兩組也用了唯讀的 shell 指令；N 只有 Grep、Read、Glob 工具。功能上等價，照實記錄。
- 每格只跑 1 次，樣本小；預算夠跑第 2 次，但因為天花板效應，第 2 次無法提供更多資訊，改用剩下的預算在 graphify 主打的大型 repo 上測（需要 owner 同意）。

## 還沒測的
graphify 主打的場景：大型、陌生、多語言的 repo（它自己的 benchmark 用 ERPNext）。OAW 的 Python 腳本約 1.5 萬行，對原生 agent 不夠難。

檔案：`out/rows.jsonl`（每次的答案、工具次數、token；原始 transcript 不公開）、`out/grades.jsonl`（盲評）、`out/summary.json`。
