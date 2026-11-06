# 追加：codegraph 也跑較弱模型的兩個條件

寫在這兩個條件的任何 C 作答之前。

## 為什麼
graphify 和 OAW code map 的結論用了 4 個模型條件：Opus 5.5、Sonnet 5.5（確認實驗，d389fe9），以及 Opus 4.8 限 14 回合、Haiku 5.5 限 14 回合（弱模型加測，fd1895c）。OAW code map 在 Opus 5.5 判「一樣懂但比較省」，但在 Opus 4.8 判「變差」，合起來不算有提升。codegraph 目前只跑了前兩個條件，要用同樣的標準比，才公正。

## 怎麼跑
- 和弱模型加測相同：同一批凍結題目、同一段提示（含「最多回應 14 次」）、`--max-turns 14`、`--effort high`、Claude Code 2.1.287。
- Opus 4.8（`claude-opus-4-8`）：C 跑 4 題 × 3 次。Haiku 5.5（`claude-haiku-5-5`）：C 跑 4 題 × 1 次，因為那次加測的 Haiku 也只完成 1 次。
- N、G、S 沿用 fd1895c 的答案，標 `seeded`。每個條件的全部答案在同一批重新評分（同一個評分者和提示）。
- C 組和 `PREREG.md` 相同：codegraph 1.6.2 的官方 project 安裝（MCP、hook、CLAUDE.md 段落），副本在本機 SSD。
- 預算：Opus 4.8 的 C 上限 1,200,000、Haiku 的 C 上限 1,000,000，算在 codegraph 的 10M 裡。
- 腳本：`run-weaker.sh`。

## 判定
- 每個條件照 `PREREG.md` 的規則，C 和同條件的 N 比。
- 合併規則：4 個條件裡至少一個「更懂」或「一樣懂但比較省」，而且沒有任何一個「變差」，才算有提升，和 graphify、OAW code map 用同一把尺。
- Haiku 只有 1 次，照實寫明。
- 這兩個條件不跑 NB 對照。Opus 5.5 的 NB 對照已經顯示：原生加了唯讀 Bash，工具呼叫並沒有減少。
