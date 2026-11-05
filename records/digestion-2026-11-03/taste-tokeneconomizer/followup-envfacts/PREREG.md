# 追加組 T2（micro-skills 只用不花 token 的 envfacts）預先登記

寫在 T2 任何 session 之前、第 1 輪結果出來之後。第 1 輪（`../PREREG.md`，N 對 T）照規則判定為 decline，原因要先講清楚，這一組才有意義。

## 為什麼加這一組
第 1 輪 T 後段的 effective token 比 N 多 25%（R=1.25），品質一樣（12/12 對 12/12）。拆開看：
- 不算它自己的模型呼叫，後段 T 只多 4%；deny list 生效後的第 9–12 題，T 每個 session 的 cache read 少 40–50%，effective token 少約 10%。
- 多出來的主要是 fact proposer：每 3 個 session 一次 Haiku 呼叫，四次共約 118K effective token。它提出的事實在 12 個 session 內一條都沒變成 active；唯一注入的事實（`python -m pytest` 在這裡找不到，要用 `.venv/bin/python -m pytest`）來自不花 token 的 envfacts 層。
- 第 1 輪把 `microskills` 從作者預設的 off 改成 on，正是這筆成本的來源。D26 要求先懷疑測試、照作者的方式試；所以補一組不用付費 proposer 的設定。
- 第 1 輪還有一個環境問題：試吃區在 NFS 上，NFS 伺服器的時鐘比本機快約 28 分鐘。它用「現在 − 檔案 mtime」判斷 repo 是否閒置，算出負數，所以 `toolprune_quiet_minutes=0` 失效，deny list 在第 5 個 session 後一直 pending。我在第 7 題的 T session 進行中，用文件列出的 `te toolprune apply` 寫入（從第 8 題起生效），並用一個 watcher 照同樣方式處理之後的 pending（之後沒有再出現）。T2 把它的狀態放在本機磁碟，不需要這個處理。

## T2 的設定
和第 1 輪 T 完全相同（同一個 commit 的食物、官方 project scope 安裝在新的副本 `arm-T2`、`refresh-catalog`、同一個 CLI、模型、effort、提示、工具、權限、`--setting-sources project,local`、回合和時間上限、side-call shim、每題前程式碼回到 base、同樣 12 題同樣順序、同樣的機械評分），只差兩點：
1. `microskills=envfacts`（文件列出的模式：只從重複失敗學事實，不呼叫模型）。`toolprune_quiet_minutes=0` 照舊，其他全用預設。
2. 它的狀態（`TOKENECONOMIZER_HOME`）放在本機 ext4 磁碟（時鐘和本機一致），不放 NFS。

## 比較對象
第 1 輪的 N 列（同樣 12 題、同樣順序、同樣設定，2026-11-05 跑完）。T2 單獨跑，不再跑 N。照實記錄：N 和 T2 不是交錯執行，時間不同；第 1 輪裡 N 和 T 交錯時，兩組在 deny list 之前共用同樣的 prompt 前綴，可能互相讀到對方剛寫入的 cache；T2 單獨跑時讀的是自己上一個 session 的 cache，兩邊間隔都在幾分鐘內。

## 判定規則
和 `../PREREG.md` 的第 1–7 條相同，T 換成 T2，R＝後段 T2 ÷ 後段 N（含它自己的模型呼叫；envfacts 不會有 proposer，只剩 loop guard 的 judge，如果它出手）。

## 這份食物的總結論怎麼定（先寫死）
- T2 判定為接上或吸收 → 食物的最終判定採 T2（作者的 off/envfacts 設定比我們開的 on 好，這是設定問題，不是食物的問題）；第 1 輪 decline 照樣留在紀錄上，寫明是 `microskills=on` 的結果。
- T2 不是接上或吸收 → 食物的最終判定採較好的那一輪：T2 是 not-shown-better 就記 not-shown-better；兩輪都是 decline 就記 decline。

## 預算（D13）
第 1 輪兩組用了 5,329,470（含它自己的模型呼叫），上限 10M，剩 4,670,530。T2 的 runner 上限設 4,600,000，成對保護照舊（以單組估計）。
