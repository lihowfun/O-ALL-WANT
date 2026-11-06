# codegraph 試吃（ERPNext，agent 層）預先登記

2026-11-06，owner 指示：「https://github.com/colbymchenry/codegraph.git 加入試吃」，又說「跟 graphify 蠻像，我們過去消化類似的 skills 有相關經驗，這次也一起看能不能更好」。寫在任何計分的作答之前，推上 records 之後才開跑。

## 問題
> 在大型陌生 repo 上，agent 有 codegraph，是不是比原生更懂程式怎麼串在一起，或一樣懂但比較省？

codegraph 自己的主張（README，2026-08-05 重測）：Claude Opus 4.8、7 個 repo、每組 4 次取中位數，工具呼叫少 88%、token 少 62%、花費少 44%；Python 的 Django 是工具呼叫 3 對 14、token 少 41%。它的題目都是「X 怎麼運作」的架構題。

## 這次怎麼借用 graphify 的經驗
- 題目、語料、原生組都沿用 2026-11-05 的確認實驗（`../../digestion-2026-11-03/codemap-erpnext-confirm/`，d389fe9）。只新跑食物組 C，花費大約是重做一次的三分之一。
- 同一批題目上已經有 graphify（G）和 OAW code map（S）的答案，所以 codegraph 可以直接和它們放在同一張表比，而且四組在同一批重新盲評。
- 判定規則一字不改（`summary.py` 就是 `confirm_summary.py`），結果可以和 graphify 的判定直接對照。

## 語料和題目（沿用，不重出）
- `frappe/erpnext` commit `d9cb9169dcc144cba46f7ddfcf90b0ab7b1e6aa9`。
- 題目：`../../digestion-2026-11-03/taste-graphify/erpnext/questions.json`，sha256 `b7604bca63a134d43962924f88d9c209b01060f7020b054b2b3b366790b2ad83`，`run.sh` 開跑前核對。共 4 題：2 題影響、1 題流程、1 題機制。

## 組別
- **N 原生、G graphify、S OAW code map**：沿用確認實驗的答案（Opus 和 Sonnet 各 36 次，同一份 CLI 2.1.287、模型、effort、提示、副本），標 `seeded`，不重跑。
- **C codegraph 1.6.2**（npm 上的最新版，和 repo f72c9d2 的 `package.json` 版本相同）：
  - 照官方 npm 路線安裝，但裝在試吃區自己的 prefix，不裝到全域。
  - 在 ERPNext 副本裡跑官方的非互動安裝 `codegraph install --target=claude --location=local --yes`（只寫這個專案）。它寫了三個檔：
    - `.mcp.json`：`codegraph serve --mcp`，`alwaysLoad: true`。
    - `.claude/settings.json`：允許 `mcp__codegraph__*`，加一個 `UserPromptSubmit` hook `codegraph prompt-hook`（遇到結構類問題時，先把 codegraph 查到的內容塞進提示）。
    - `.claude/CLAUDE.md`：CodeGraph 段落，叫 agent 先用它，再 grep 或讀檔。
  - 安裝程式在另一個 HOME 下執行，使用者層的設定沒有被寫入（已核對）。
  - `codegraph init --yes` 事先建好索引（`.codegraph/`，4,006 個檔案、45,406 個節點、119,954 條邊、189 MB，本機 SSD 上 15 秒），和 G 的圖、S 的快取一樣是事先建好的。
  - 遙測關閉（`CODEGRAPH_TELEMETRY=0`、`DO_NOT_TRACK=1`），不影響它的行為。
  - 工具：Read、Grep、Glob，加上只能跑 `codegraph` 的 Bash（它的 CLAUDE.md 段落教 `codegraph explore`），加上它的 MCP 工具。MCP 設定用它寫的 `.mcp.json`，以 `--mcp-config` 傳入，並保留 `--strict-mcp-config`：C 組只有 codegraph 的 server，其他組仍然沒有任何 MCP。hook 以專案設定載入。
  - runner 唯一的改動就是這個 `mcp_config` 欄位（`taste_run.py` 開頭有寫）。

共同設定和確認實驗相同：Claude Code 2.1.287、`--setting-sources project`、沒有子 agent、不能改檔、每次新 session、stdin 關閉、session 不保存、作答提示相同、計費必須是訂閱（`apiKeySource: none`）、每次上限 1,200 秒。工具呼叫次數包含 MCP 和 Bash 的呼叫。

## 兩種條件（和確認實驗相同，原生組才能沿用）
1. **Opus**：`claude-opus-5-5`、`--effort high`、不限回合。
2. **Sonnet**：`claude-sonnet-5-5`、`--effort high`、`--max-turns 14`，提示多一段「最多回應 14 次」。確認實驗已發現這個上限實際上沒有切斷任何一次，這裡照樣沿用，讓 C 和 N、G、S 條件一致。

## 次數
- 每個條件 C 跑 4 題 × 3 次 = 12 次，兩個條件共 24 次。
- 試跑（已做，凍結前）：用一題不在題庫裡的小題（Journal Entry 的借貸平衡檢查），經過 runner 用 Sonnet 跑一次，43,368 token。init 顯示 codegraph server `connected`、工具清單有 `mcp__codegraph__codegraph_explore`、計費是訂閱。hook 的輸出不會出現在 stream-json 裡；用同一段提示直接執行 `codegraph prompt-hook`，它回傳 `<codegraph_context>` 區塊，裡面有答案用到的函式名，而那次作答第一個工具呼叫就是 grep 這個名字。試跑算消化開銷，不計分。

## 評分
- 和確認實驗相同的評分者：零上下文（`claude -p`、沒有工具、空資料夾），`claude-opus-5-5` high。
- 每個條件的 48 個答案（N、G、S 各 12，C 12）在同一批重新評分，順序打亂；上次的評分不再使用。
- 遮罩加上 codegraph 的名稱（codegraph、code graph、blast radius），評分者分不出組別；`taste_grade.py` 只改了這一行和說明文字。

## 判定規則（和確認實驗一字不差）
每個條件分開判定，C 和同條件的 N 比。下面的數字都先在每題內把 3 次取平均，再跨 4 題彙總：
- **覆蓋率**：4 題平均。
- **token**、**工具呼叫**：4 題的中位數。
- **必要事實全對**：在 12 次中算次數。
- **錯誤陳述**、**切斷**：12 次加總。

判定依序看，先符合的算數：
1. **變差**：覆蓋率比 N 低 0.10 以上，或錯誤陳述比 N 多 3 個以上，或切斷次數比 N 多 3 次以上。
2. **更懂**：覆蓋率比 N 高 0.10 以上而且 4 題裡至少 3 題不低於 N，或必要事實全對的次數比 N 多 3 次以上。
3. **一樣懂但比較省**：覆蓋率不比 N 低 0.05 以上，錯誤陳述不比 N 多，而且 token 中位數或工具呼叫中位數不到 N 的 70%、同一項在 4 題裡至少 3 題比 N 低。
4. 其他：**沒有證明比原生好**。

codegraph 要算「有提升」：至少一個條件判定為「更懂」或「一樣懂但比較省」，而且沒有任何一個條件判定為「變差」。

和 graphify、OAW code map 的直接比較只做描述，不做判定。G 和 S 這次重新評分後得出的判定也只是描述；它們的正式判定仍以 d389fe9 為準。

## 預算（D13）
- codegraph 每樣食物上限 10M。C 組的上限：Opus 2,000,000 token，Sonnet 1,400,000 token。
- runner 每一題開始前估算（用這題目前最大的一次估），超過就不開始這一題；不足 4 題或 3 次時會寫明。
- 評分和試跑算 2026-11-06 這一輪的消化開銷。

## 事先寫明的限制
- 題目只有 4 題，每格 3 次，只能看出中等以上的差距；Opus 5.5 的原生組在這題組幾乎滿分，「更懂」的空間很小。
- 題型和 codegraph 自己的 benchmark 不同：它用單一「X 怎麼運作」的題目，這裡是 2 題影響、1 題流程、1 題機制。不能和它的 62%、88% 並排比較（模型、工具、量法都不同）。
- 原生組的答案是前一天跑的（同一份 CLI 和設定），時間差可能有一點影響；確認實驗也這樣沿用過。
- C 組的副本放在本機 SSD，N、G、S 的副本在 NFS 網路磁碟。原因：codegraph 的索引是 SQLite，在 NFS 上建了 15 分鐘還沒完成，作答時查詢也可能逾時，這對它不公平；先前三組都不依賴資料庫。磁碟只影響秒數，秒數不列入判定。

## 執行
`COND=opus T=<試吃資料夾> CLAUDE=<claude CLI> bash run.sh`，`COND=sonnet` 同樣。兩個條件同時在背景跑。

- `arms-codegraph.json`：N、G、S 沿用確認實驗的定義，C 加上 `mcp_config`、`path_prepend`（codegraph 和 node）和遙測關閉的 `env`。
- 原始 stream-json 留在本機，不公開。
- `out-opus/`、`out-sonnet/` 的 `rows.jsonl`、`grades.jsonl`、`summary.json` 和結果頁會 commit 到這裡。

檔案 sha256（凍結）：見 `SHA256SUMS`。
