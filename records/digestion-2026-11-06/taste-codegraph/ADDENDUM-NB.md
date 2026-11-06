# 追加對照 NB：原生加上同樣的唯讀 Bash（Opus）

寫在 NB 的任何作答之前。C 組 24 次已經跑完並評分（Opus、Sonnet 各 12），這份追加不改 `PREREG.md` 的任何規則，也不改 C 的判定方式；只補一個看到資料後才發現的對照。

## 為什麼追加
看資料時發現三個食物組（G、S、C）和原生組 N 的工具不對等：
- N 只有 Read、Grep、Glob，沒有 Bash。
- G、S、C 為了跑食物的 CLI 有 Bash，只放行 `graphify`、`python3 scripts/code_index.py`、`codegraph`。但 Claude Code 會自動放行唯讀的 shell 指令（`sed -n`、`grep`），所以它們也能用 Bash 讀檔，而且一次可以串好幾個讀取。
- Opus 條件裡，C 組的 Bash 有 50 次，全部是一般讀檔，呼叫 codegraph 本身 0 次；S 組的 Bash 有 56 次，其中 32 次是一般讀檔；G 組 33 次，其中 21 次是一般讀檔。
- 所以「工具呼叫比較少」有一部分是 Bash 可以串讀，不一定是地圖的功勞。這會影響 C 這次、以及 S 在確認實驗（d389fe9）的「一樣懂但比較省（工具呼叫）」。

## NB 組
- 和 N 同一份 ERPNext 副本、同一段提示、同一個 CLI 2.1.287、`claude-opus-5-5`、`--effort high`、不限回合，`--setting-sources project`，每次新 session。
- 工具：Read、Grep、Glob、Bash。自動允許清單只有 Read、Grep、Glob，Bash 只能跑 Claude Code 自動放行的唯讀指令，和食物組除了食物 CLI 以外的權限相同。
- 4 題 × 3 次 = 12 次，只跑 Opus（判出「比較省（工具呼叫）」的條件）。
- 評分：同一個評分者和提示（`taste_grade.py`，凍結），NB 的 12 個答案單獨一批評分。同一批答案重評兩次時，覆蓋率 36/36 完全一樣，錯誤陳述各組差 0 到 2 個，這點會寫在結果裡。
- 預算：1,200,000 token（算在 D24 code map 的額度，因為它同時修正 S 的比較）；runner 的預算守門照舊。

## 怎麼用（先寫死）
- 用 `summary.py` 裡同一個 `judge()`，把 C 和 S 各自和 NB 比，判定規則一字不改。
- **C 的正式判定**：在 Opus 條件下，取「C 對 N」和「C 對 NB」兩個判定中比較差的那個。也就是說，只有兩個都判「一樣懂但比較省」或更好，C 在 Opus 才算省。Sonnet 條件照原本的 C 對 N。合併規則照 `PREREG.md`。
- S 對 NB 只是對確認實驗的修正說明，不改 d389fe9 的紀錄，結果頁會並列。
