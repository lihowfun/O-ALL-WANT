# Code map 確認實驗：加測較弱的模型（ERPNext，三組）預先登記

2026-11-05，owner 指示：「多弄幾個比較笨的模型，sonnet、opus 4.8 之類的，跑看看。」寫在任何新的作答之前，推上 records 之後才開跑。

## 問題
前兩次 ERPNext 試吃用的是 Opus 5.5，原生組不靠地圖就答對每題的必要事實，有天花板效應。owner 的假設是：模型越弱，code map 越可能幫得上忙。Sonnet 5.5 已經在 `../codemap-erpnext-confirm/` 的「Sonnet 限 14 回合」條件裡，這次不重跑。這次再加兩個條件：

> 換成更弱的模型（Opus 4.8、Haiku 5.5），agent 有 code map（OAW 的或 graphify 的），是不是比原生更懂程式怎麼串在一起，或一樣懂但比較省？

## 和 `../codemap-erpnext-confirm/` 完全相同的部分（fc0bbc5 凍結，不改）
- 語料：`frappe/erpnext` commit `d9cb9169…`，同一份副本。
- 題目：`../taste-graphify/erpnext/questions.json`，sha256 `b7604bca…`，共 4 題。
- 三組 N、G、S：同一個 `arms-confirm.json`、同一份 G 圖、同一份 S 快取。
- runner、評分、彙總都直接呼叫 `../codemap-erpnext-confirm/` 的 `taste_run.py`、`taste_grade.py`、`confirm_summary.py`，不另外複製。`run.sh` 開跑前會先核對這三個檔案和題目的 sha256。
- 共同設定：Claude Code 2.1.287、`--setting-sources project`、沒有 MCP、沒有子 agent、不能改檔，每次都開新 session；計費來源必須是訂閱。
- `--effort high`、`--max-turns 14`，提示多加回合上限說明。被切斷時，用最後一段文字當答案。
- 每格 3 次，三組順序依次輪替。
- 評分者：零上下文的 `claude-opus-5-5` high。評分前遮掉工具名稱，評分順序打亂。
- 判定規則、每題先平均再彙總的算法，都和 `../codemap-erpnext-confirm/PREREG.md` 一字不差。

## 只改作答的模型
1. **Opus 4.8 限 14 回合**：`claude-opus-4-8`。graphify 自己的 benchmark 就是用這個模型加 14 回合，所以這個條件最接近它的設定。剩下的差別是工具（這次用 Claude Code 原生工具）和評分者（這次是 Opus 5.5，它用 Kimi K2.6）。因此結果仍然不能和它的 70.8%／82.0% 並排比較。
2. **Haiku 5.5 限 14 回合**：`claude-haiku-5-5`。

兩個條件都選 14 回合，是為了和 Sonnet 條件一致。這樣 Sonnet、Opus 4.8、Haiku 三個條件只差在模型。

探測：兩個模型 ID 都經由訂閱跑過一次 1 回合的 `ok`。init 回報的模型就是指定的模型，`apiKeySource` 為 none。Opus 4.8 用了 16,625 token，Haiku 用了 28,659 token。CLI 對 `claude-haiku-5-5` 印出 `unrecognized_model` 警告，但仍正常回答。Haiku 是否真的套用 `--effort high`，從 init 看不出來，照實記錄。探測的 token 算消化開銷。

## 次數和順序
每個條件都是 3 組 × 4 題 × 3 次，共 36 次；兩個條件合計 72 次。先跑 Opus 4.8，跑完再跑 Haiku。同一時間只跑一個條件，避免和其他 session 正在跑的試吃一起搶訂閱的速率。

## 判定
- 每個條件分開判定。S、G 各自和同一條件的 N 比，規則照 `../codemap-erpnext-confirm/PREREG.md`。
- owner 問「加進去能不能提升」時，把這兩個條件和確認實驗的 Opus、Sonnet 條件放在一起，用同一條規則回答：一個 code map 至少要在一個條件判定為「更懂」或「一樣懂但比較省」，而且所有條件都沒有「變差」，才算有提升。
- 另外照實列出（只做描述，不做判定）：按模型強弱排列（Opus 5.5 → Sonnet 5.5 → Opus 4.8 → Haiku 5.5），每個條件的 S−N、G−N 覆蓋率差和 N 的覆蓋率。目的是看假設的方向，也就是「N 越低，地圖的增益越大」有沒有出現。只有 4 題，不做統計檢定。

## 預算（D13）
- Opus 4.8 上限 3,000,000 token，Haiku 上限 2,400,000 token，合計 5.4M。runner 沿用逐題估算的保護機制，只比完整的題目。題數或次數不足的會寫明。
- G 的花費算在 graphify 剩下的約 5.2M。加上確認實驗的 G，預估仍在上限內；每次結束都核對，超過就停下來問 owner。N 和 S 的花費算在 D24 code map 的額度。
- 評分和探測算消化開銷。
