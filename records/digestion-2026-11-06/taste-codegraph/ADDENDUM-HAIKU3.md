# 補登記：codegraph 的 Haiku 補到 3 次、評兩次，再照 D29 判定

2026-11-06，owner 指示「該補補，幫我往下」。寫在任何新的 C 作答之前，推上 records 之後才開跑。做法照 graphify 的補登記（`../../digestion-2026-11-03/codemap-erpnext-weaker/ADDENDUM-HAIKU.md`，d73c4f8）。

## 為什麼
codegraph 的 Haiku 條件只跑了 1 次（`ADDENDUM-WEAKER.md`）。graphify 和 OAW code map 的 Haiku 已經補到 3 次（9c5886a），codegraph 要用同一把尺。

事先寫明：codegraph 帳本上的判定「因成本不採用（能力未定）」是 Opus 4.8 決定的，那個條件跑了 3 次，token 是原生的 1.722 倍。D29 取最低的條件，所以不論 Haiku 結果如何，判定都還是「排掉」。補跑只會改變理由：如果 Haiku 兩次評分都判「變差」，理由會變成品質較差。

## 不變的部分
語料、題目（sha256 `b7604bca…`）、C 組的官方安裝和索引（本機 SSD 上的副本）、runner（`taste_run.py`，凍結）、評分程式（`taste_grade.py`，凍結）、提示、`--max-turns 14`、`--effort high`，以及評分者：零上下文的 `claude-opus-5-5` high。

## 改的部分
1. **作答**：
   - C 組在 Haiku 補跑第 2、3 次，每次 4 題，共 8 次；第 1 次不重跑。
   - N、G、S 沿用 graphify 那次補完的 3 次答案（`out-weaker-haiku`，9c5886a），標成 `seeded`。
2. **預算**：C 組的上限是 2,200,000，含第 1 次已經用掉的 675,948。runner 的預算保護照舊。
3. **評分兩次（D29）**：
   - 評分 A：保留同一批的 16 筆第 1 次評分，只評新的 32 個答案（N、G、S 的第 2、3 次，以及 C 的第 2、3 次）。
   - 評分 B：另開 `grades-b.jsonl`，把 48 個答案全部重新評一次。
   - D30 第 3 條：評分花 0 token 或被用量上限切斷，就算沒跑，刪掉重評，不記成分數。

## 判定（先寫死）
**Haiku 條件，C 和 N 比，評分 A、B 各判一次，兩次同方向才算數，否則算「一樣」：**
- 變差：覆蓋率低 0.10 以上，或錯誤陳述多 3 個以上，或切斷次數多 3 次以上。
- 更好：覆蓋率高 0.10 以上而且 4 題裡至少 3 題不低於 N，或必要事實全對的比例高 0.25 以上。
- 成本：`tokens_ratio`，評分 A、B 共用，所以只有一個數字。

**codegraph（D29，多個條件取最低）：**
- 其他三個條件沿用帳本：品質都是「一樣」（都只評一次），token 比值 1.200、1.308、1.722。
- Haiku 用這次的結果。
- 照 D29 算出結果，用 `record-tasting` 記一筆新的紀錄，帶 `judgment`，標明是補完後的判定。

## 預期花費
- C 的 8 次作答約 1.4M（codegraph 這份食物，上限 10M，已經用了 3.89M）。
- 評分 80 次，約 0.45M。
