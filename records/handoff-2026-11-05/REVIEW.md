# 交接文件的零上下文審查（2026-11-05）

一個沒有專案上下文的 agent 只讀這個資料夾和它指到的檔案，模擬在 Linux 接手。23 個發現（1 blocker、6 major、16 minor），大象處理如下。

| # | 嚴重度 | 發現 | 處理 |
|---|---|---|---|
| 1 | blocker | 交接資料夾還沒推上 GitHub | 本 commit 推上 `records` |
| 2 | major | 第 0 節 `cd OAW` 後的 `records/` 路徑在 main 不存在 | 改成在上層資料夾放三個 worktree，明寫 `cd ~/oaw/OAW-records` |
| 3 | major | 要 sudo 的套件沒標 owner | 標「owner，要 sudo」並給 apt 指令 |
| 4 | major | kit 無法直接拿去測 ERPNext | `setup_arms.sh` 加 `SRC`、`ARMS`、`G_IGNORE`；第 4 節寫明要重寫出題提示 |
| 5 | major | `oaw-catalog-intake-rules` 記憶和 D21、D25 衝突 | 加「部分被取代」段落，後來的決定優先 |
| 6–7 | minor | worktree 數量、記憶資料夾位置不清楚 | 改寫第 0 節 |
| 8 | minor | 兩份食物沒有 repo 和版本 | 補上 repo 和消化時的 SHA |
| 9 | minor | 三份記憶描述舊機器 | 改成不綁機器的寫法 |
| 10 | minor | PR 內文寫 D1–D24；`--body-file` 是佔位 | PR 文件改成 D1–D27；給可執行的指令並去掉重複標題 |
| 11 | minor | 448 是 Windows 的測試數 | 註明 POSIX 下限 426，Linux 以實跑為準 |
| 12 | minor | 紀錄裡的 `arms.json` 用 `~` | 第 8 節註明重跑用 `setup_arms.sh` 產生的 |
| 13 | major | `run_arms.sh` 在預算或計費來源停下後仍去評分 | runner 非 0 就停，不評分 |
| 14 | major | `design.sh` 先 `cd` 才讀相對路徑 | 先轉絕對路徑；`grep` 失敗不中斷；自動取出答案到 `design_result.md` |
| 15 | minor | `setup_arms.sh` 相對路徑、`set -e` 下的 `cat`／`grep -v` | 轉絕對路徑、改用子 shell、失敗容忍 |
| 16 | minor | npm 安裝的 claude 找不到 node | 第 8 節註明用 `path_prepend`；probe 加 node 路徑 |
| 17 | minor | 沒固定模型；出題沒取出 questions | `design.sh` 支援 `CLAUDE_MODEL` 並印出 model；產品化時 `taste_run` 加 `--model`（第 4 節第 5 項） |
| 18 | minor | 輸出資料夾重用會沿用舊評分、算進預算 | 預設每次新資料夾；續跑要 `TASTE_RESUME=1` |
| 19 | minor | probe 靜默略過、看不到 apiKeySource、缺 openssl、遮蔽不完整 | 全部修正（stream-json 取 init，整串 token 用正則遮蔽） |
| 20 | — | `arms.json` 欄位正確 | 無需處理 |
| 21 | minor | 舊進度檔有舊路徑和 game／PLAY 字樣（D19） | 不搬這個檔，待辦已併入 HANDOFF 第 4 節 |
| 22 | minor | 公開了兩個私人 artifact 網址 | 改成「在 owner 的 claude.ai artifacts 裡」 |
| 23 | — | 沒有其他本機路徑、帳號、email、機構名稱、憑證 | 無需處理 |
