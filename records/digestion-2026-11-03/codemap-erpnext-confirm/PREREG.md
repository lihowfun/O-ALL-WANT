# Code map 確認實驗（ERPNext，三組）預先登記

2026-11-05，owner 指示「跑確認實驗」。寫在任何新的作答之前，推上 records 之後才開跑。

## 問題
owner 問：「graphify 新增 code map 讓 AI 理解，我們原先沒有這功能對吧，也要確定加進去是否能提升。」OAW 在 `claude/oaw-2` 已經有自己的 code map（`scripts/code_index.py`，D24），還沒 merge 進 main，也還沒預設讓 agent 使用。之前兩次 agent 層試吃（OAW repo 6 題、ERPNext 4 題）每格都只跑 1 次，只抓得到很大的差距。這次問同一件事，但每格跑 3 次，再加一個預算緊的條件：

> 在大型陌生 repo 上，agent 有 code map（OAW 的或 graphify 的），是不是比原生更懂程式怎麼串在一起，或一樣懂但比較省？

## 語料和題目（沿用，不重出）
- `frappe/erpnext` commit `d9cb9169dcc144cba46f7ddfcf90b0ab7b1e6aa9`，和 `../taste-graphify/erpnext/` 同一份。
- 題目：`../taste-graphify/erpnext/questions.json`，sha256 `b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83`，那次已經凍結，這次也不改，`run.sh` 開跑前會先核對。共 4 題：2 題影響、1 題流程、1 題機制，事實數是 8／6／8／7。

## 三組（同一個 commit，各自一份副本）
- **N 原生**：只有 Read、Grep、Glob。
- **G graphify 0.9.102**：和上次同一份副本、同一張圖。官方 `graphify install --project --platform claude` 寫入的 CLAUDE.md 規則、skill 和 PreToolUse hook 都在。工具是 Read、Grep、Glob，加上只能跑 `graphify` 的 Bash。
- **S OAW code map**：
  - 從 `claude/oaw-2` @ 721b2b7 複製 `scripts/code_index.py`（sha256 `67e2d48d…`，這個檔案最後一次修改在 6f2d365），放到副本的 `scripts/code_index.py`。ERPNext 根目錄本來沒有 `scripts/`。
  - CLAUDE.md 用 OAW 那次的 `../taste-graphify/agent/s_block.md`，一字不改。內容是「先跑 `find`，再 grep」，加上 `callers`／`path`／`affected` 的用法。
  - 索引事先建好快取，放在副本外面，用 `OAW_CODE_INDEX_CACHE` 指過去，和 G 的圖事先建好對等。建一次 23 秒，之後每次呼叫約 4 秒，遇到改過的檔案會自動更新。
  - 工具是 Read、Grep、Glob，加上只能跑 `python3 scripts/code_index.py` 的 Bash。

三組共同的設定：
- Claude Code 2.1.287，`--setting-sources project`（user 層設定不載入，各組自己的專案檔照常載入）。
- 沒有 MCP、沒有子 agent、不能改檔。
- 每次都開新的 session，stdin 關閉，session 不保存。
- 作答提示和上次相同。
- 計費來源必須是訂閱（`apiKeySource: none`），不是就停。
- 每次上限 1,200 秒。

## 兩種條件
1. **Opus**：`claude-opus-5-5`、`--effort high`、不限回合，也就是平常的用法。
2. **Sonnet 限 14 回合**：`claude-sonnet-5-5`、`--effort high`、`--max-turns 14`，這是 graphify 自己 benchmark 的回合上限。三組的提示都多加一段，說明「最多回應 14 次，最後的答案也算一次；第 14 次還在呼叫工具，就沒有答案」。被切斷的那次，用它最後一段文字當答案，通常是空的，空的就算 0 分。切斷次數另外列出。

## 次數和順序
- 每個條件都是 3 組 × 4 題 × 3 次。
- 每一次開始時三組的順序輪替：第 1 次 N,G,S，第 2 次 G,S,N，第 3 次 S,N,G。
- Opus 的第 1 次：N 和 G 直接沿用 93e555b 那 8 次（同一份 CLI、模型、effort、提示、副本），只新跑 S。所以 Opus 新跑 28 次，Sonnet 新跑 36 次，總共 64 次。
- 試跑：S 組用一題不在題庫裡的小題，經過 runner 跑過一次，16,761 token，確認 Bash 放行、快取和回合上限都正常。另外用 2 個小檔案試過 `--max-turns`，7,021 token。這兩次都算消化開銷，不計分。

## 評分
- 評分者和上次相同：零上下文（`claude -p`、沒有工具、空資料夾），`claude-opus-5-5` high。
- 逐題判定每個事實是 present、absent 還是 contradicted，並計算錯誤陳述。
- 答案裡會洩漏組別的工具名稱，評分前先遮掉；評分順序打亂。
- 沿用的 8 個答案也重新評分，所有答案用同一批評分。上次的評分不再使用。
- `taste_grade.py` 只改了說明文字。

## 判定規則（先寫死）
每個條件分開判定，S 和 G 各自和同條件的 N 比。下面的數字都先在每題內把 3 次取平均，再跨 4 題彙總：
- **覆蓋率**：4 題平均。
- **token**、**工具呼叫**：4 題的中位數。
- **必要事實全對**：在 12 次中算次數。
- **錯誤陳述**、**切斷**：12 次加總。

判定依序看，先符合的算數：
1. **變差**：符合下面任一條。
   - 覆蓋率比 N 低 0.10 以上。
   - 錯誤陳述比 N 多 3 個以上。
   - 切斷次數比 N 多 3 次以上。
2. **更懂**：符合下面任一條。
   - 覆蓋率比 N 高 0.10 以上，而且 4 題裡至少 3 題的覆蓋率不低於 N。
   - 必要事實全對的次數比 N 多 3 次以上。
3. **一樣懂但比較省**：三條都要符合。
   - 覆蓋率不比 N 低 0.05 以上。
   - 錯誤陳述不比 N 多。
   - token 中位數或工具呼叫中位數不到 N 的 70%，而且同一項在 4 題裡至少 3 題比 N 低。
4. 其他：**沒有證明比原生好**。

回答 owner 的問題（「加進去能不能提升」），一個 code map 要算「有提升」，必須：
- 至少一個條件判定為「更懂」或「一樣懂但比較省」；
- 而且沒有任何一個條件判定為「變差」。

S 和 G 互相直接比較只做描述，不做判定。

## 預算（D13）
- Opus 新跑上限 3,600,000 token，Sonnet 上限 2,400,000 token，合計 6.0M。
- runner 在每一題開始前估算：每組還沒跑的，用它在這題目前最大的一次來估。估計值超過上限就不開始這一題，所以只會比較完整的題目。題數不到 4 題、或次數不到 3 次，會寫明。
- G 的花費算在 graphify 剩下的約 5.2M。N 和 S 算 D24 code map 的額度。
- 評分和試跑算消化開銷。

## 事先寫明的限制
- 題目只有 4 題。每格 3 次，只能看出中等以上的差距。小於 0.05 的覆蓋率差距，這個實驗分辨不出來。
- 這次的數字不能和 graphify 自己的 70.8%／82.0% 比。它用的是 Claude Opus 4.8、它自己的工具、Kimi 評分。這次 Sonnet 只沿用它的 14 回合上限。
- 也不能和 OAW 工具層的 39 題命中率比，那是另一種量法。
- S 的索引會把 `scripts/code_index.py` 本身也收進去，這是把它放進陌生 repo 的副作用。

## 執行
`COND=opus T=<試吃資料夾> CLAUDE=<claude CLI> bash run.sh`，`COND=sonnet` 同樣。兩個條件同時在背景跑。

- `arms-confirm.json`：由上次的 `arms.json` 加上 S 組產生，S 組的 `env` 指向快取。
- 原始 stream-json 留在本機，不公開。
- `out-opus/` 和 `out-sonnet/` 裡的 `rows.jsonl`、`grades.jsonl`、`summary.json`，以及結果頁，會 commit 到這裡。

檔案 sha256（凍結）：

- `taste_run.py`：`dcab377b56afbfde1a4a6316d37ddfa49f4cae69c5dd06d82cf0b179d13bb563`
- `taste_grade.py`：`85e4e114ed1b3f4cfefa82e3397494995e58e5f4d74e8e3441d33fcc5ad6d3ec`
- `confirm_summary.py`：`94b689c8d676c0031b980a324390f083bcc385d43ba378da49471f13438b55bd`
- `run.sh`：`5bd0bdd5274fdd44bcd85c10498a966587deb67abc6dcca5d2ae3e4111973255`
