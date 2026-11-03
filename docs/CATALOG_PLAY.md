# OAW 消化遊戲：玩法說明（catalog 原型 v0）

把 skill 當成食物：**丟進來 → 系統免費試吃 → 拆成「吸收／排掉／暫留」→ 你按吸收 → 產生一個可以一鍵還原的新版本**。

這份說明涵蓋原型 v0 實際做得到的事。完整指令和參數見 [CLI Reference](CLI_Reference.md#skill-catalog-prototype-v0)。

## 開始玩

需要 Python 3.10+（只用標準函式庫）和 git。指令都在 OAW checkout 執行，用 `--target` 指向你的專案，和 `oaw.py` 一樣：

```bash
python3 scripts/oaw.py init --target /path/to/project        # 專案還沒裝 OAW 時先裝
python3 scripts/catalog.py play --target /path/to/project    # 開本機遊戲頁（Claude、Codex 都能用）
python3 scripts/catalog.py menu --target /path/to/project    # 同樣的功能，用終端數字選單（Codex／沒有瀏覽器時）
python3 scripts/oaw_status.py --project /path/to/project     # 只看目前狀態，不做任何動作
```

- `play` 只綁 `127.0.0.1`，會印出並開啟 `http://127.0.0.1:<port>/#t=<通行碼>`，按 Ctrl+C 結束。要用印出來的完整網址開，少了 `#t=…` 頁面會拒絕連線。加 `--no-browser` 只印網址，`--port N` 指定埠號。
- `menu` 是 1–12 的數字選單，0 離開，不需要 curses。
- 網頁、`menu`、`oaw_status.py` 讀的是同一份 `.oaw/catalog/view.json`，顯示規則也一樣。

## 畫面上的三塊

1. **我的 OAW**：目前版本（例如 `2.0.0+build.2.c51132c`）和它的說明、裝了哪些 skill、和預設 `2.0.0` 比多了或少了什麼。每一行都標證據等級：靜態量測或未量測。下面是版本時間線和常設預算。
2. **投食區**：貼 GitHub 網址、本週覓食清單，以及匯入已有的大象／金魚消化紀錄。
3. **食物卡**：每樣食物一張卡，大徽章是判定，下面是四步進度：
   `① 找到 → ② 試吃（免費） → ③ 實測（付費，依常設預算） → ④ 結果`
   成分分成 🟢 吸收、🔴 排掉（附原因）、🟡 暫留（附缺哪個測試）。

## 每個按鈕做什麼

| 按鈕 | 在哪裡 | 做什麼 | 對應指令 |
|---|---|---|---|
| 送去試吃 | 投食區、食物卡 | 加入食物（同一個 repo 寫兩次會合併，並列出合併了哪些網址），抓固定版本，封存成唯讀 tar 放在專案外的 `LAB_HOME`，在記憶體裡跑免費靜態檢查，再把食物拆成成分 | `add URL [URL ...]`、`taste FOOD` |
| 立即覓食 | 投食區 → 本週覓食 | 搜尋 GitHub，濾掉和 coding agent skill／harness 無關的 repo，累積成候選清單。星數只決定排序 | `scout`、`scout list` |
| 把勾選的送去試吃 | 本週覓食 | 只有你勾選的候選才會被加入並試吃 | `scout pick N [N ...]` |
| 匯入 | 投食區 → 匯入已有的消化紀錄 | 把一個消化資料夾（`digest.json`、`verify.json`、`goldfish-*.json`、`components.json`、`integration.json`、`proposals.md`）存成**歷史證據**，只顯示、不計入判定。食物欄空白時依資料夾裡的 `scout.json` 判斷是哪樣食物 | `import-report FOOD DIR` |
| 🐘 大象報告／🐟 金魚報告 | 食物卡 | 打開匯入的報告，標示「歷史證據 · 不計入判定」。評審的自由文字預設收起，並標成不受信任 | `show FOOD` |
| 實測… | 食物卡 | 顯示系統自己規劃的測試，從便宜的排起，每一步寫明能證明和不能證明什麼，以及 token 預估。**開始實測**按鈕是停用的：v0 不執行付費測試 | `plan FOOD` |
| 吸收選中的成分 | 食物卡 | 先預覽要寫哪些檔案，確認後先存還原點，再安裝選中的純文字 skill（其他成分記成 backlog，不改程式），產生新版本，並重新評估和預設的差異 | `absorb FOOD --components ID[,ID] [--apply]` |
| 排掉／移除 | 食物卡 | 移除這樣食物已安裝的 skill。先預覽，確認後先存還原點，再移除；你改過的檔案受保護，不會被刪 | `remove FOOD [--apply]` |
| 移除／移除 EGM | 我的 OAW → skill 清單 | 移除單一 skill；EGM 整組一起移除。內建 skill 和 EGM 走 `oaw.py` 的安裝計畫：先預覽，套用時先備份到 `.oaw/backups/`、存還原點，再移除。重新加回來要再測一次（決定 D6） | `remove SKILL\|egm [--apply]` |
| 重新評估 | 我的 OAW → 和預設比 | 重新比對目前安裝和全新的預設安裝。每一行都是靜態量測，品質一律「未量測」 | `effect` |
| 還原到這版 | 我的 OAW → 版本時間線 | 列出會寫入和刪除的檔案，確認後先把目前安裝存成一版，再切回那一版，最後跑 doctor。只動 OAW 安裝層，不動你的專案資料 | `builds`、`restore BUILD [--apply]` |
| 設定常設預算 | 我的 OAW | 設定每樣食物和每週的付費 token 上限，以及試跑的沙箱條件。送出後確認碼只印在終端，你把它輸回頁面才生效 | `policy show`、`policy set ... [--confirm CODE]` |
| 分流旗標 | 只在 `menu`（第 12 項）和 CLI | 處理靜態檢查舉的旗：`--benign`（誤報）、`--allergen`（只是限制，不是有毒）、`--confirm-toxic`（你確認有毒）。`--benign`／`--allergen` 需要終端確認碼 | `triage FOOD FLAG ... --reason TEXT` |

CLI 的 `absorb`、`remove`、`restore` 沒加 `--apply` 時都只預覽。每個指令都可以加 `--json`。結束碼：`0` 完成、`2` 拒絕或失敗、`4` 等你輸入確認碼。

### 確認碼怎麼用

設定常設預算和分流旗標（`--benign`／`--allergen`）屬於只有 owner 能做的變更：

1. 第一次執行時，系統在**互動終端**印出 6 位數確認碼，指令以結束碼 `4` 停下。
2. 你把同一個指令加上 `--confirm CODE` 再跑一次（網頁上是把碼輸回對話框）。
3. 確認碼 10 分鐘內有效，只能用一次；輸錯就作廢，要重新申請。沒有互動終端時會直接拒絕。

確認碼不會出現在網頁或任何 API 回應裡。請自己輸入，不要貼給 agent。在 Windows 上請在你自己開的 PowerShell 或 cmd 視窗執行 `play` 或 `menu`；如果是從背景程序啟動，確認碼會印在沒人看得到的地方。

## 一個完整的回合（CLI）

```bash
P=/path/to/project
python3 scripts/catalog.py add https://github.com/owner/repo owner/repo.git --target $P   # 兩個網址合併成一樣食物
python3 scripts/catalog.py taste repo --target $P                     # 免費：封存、靜態檢查、拆成分
python3 scripts/catalog.py show repo --target $P                      # 看判定和每個成分的分流
python3 scripts/catalog.py absorb repo --components skill:NAME --target $P           # 預覽
python3 scripts/catalog.py absorb repo --components skill:NAME --apply --target $P   # 存還原點，產生新版本
python3 scripts/catalog.py effect --target $P                         # 和預設 2.0.0 比
python3 scripts/catalog.py builds --target $P                         # 版本時間線
python3 scripts/catalog.py restore build.1 --target $P                # 預覽還原
python3 scripts/catalog.py restore build.1 --apply --target $P        # 還原後自動跑 doctor
```

版本名稱遵守 SemVer 2.0：預設 release 是 `2.0.0`，專案組合是 build metadata `2.0.0+build.N.<hash7>`，`hash7` 是內容 hash 的前 7 碼。第一次吸收或移除前，系統會自動存一版「baseline」。內容相同的組合沿用同一個版本，不會重複建立。`restore` 可以寫完整名稱，也可以寫 `build.N` 或 `N`。

## 原型 v0 不做的事

- **不跑付費實測**：行為 A/B、整合測試、齊平底線、對我們草稿的金魚盲審都只列計畫和預估花費。所以 v0 不會出現「營養」或「進化」，品質一律顯示「未量測」。
- **不產生大象和金魚報告**：v0 只匯入已經做好的消化紀錄，而且標成歷史證據、不計入判定。
- **免費的離線整合檢查（T1）還沒做**：計畫裡會顯示「not available in v0」。
- **只吸收純文字 skill**：hooks、MCP server、腳本、manifest 等成分只記成 backlog 項目，不安裝，也不在你的電腦上執行。
- **來源只限 github.com 和本機 `file://` repo**。私有 repo 抓不到，因為 GitHub token 不會交給 git；`GITHUB_TOKEN` 只用在覓食搜尋。
- **試吃抓整份 depth-1 快照**（有大小上限），還沒做只抓需要檔案的部分 clone。
- **分流旗標不在網頁上**：有高嚴重度旗標的食物，卡片會請你改用 `menu`。
- hash 鏈事件紀錄、`catalog.py check` 重算 gate、`install.json` schema 2 都還沒做。

已驗證的範圍：gate 和端到端 smoke 只在 Windows／Python 3.13 跑過，POSIX 還沒實際跑。

## 安全規則

- **沒有證據就沒有判定**。判定只由 `catalog_core.derive()` 從證據算出來；星數、作者和名氣只決定覓食清單的排序。
- **食物不進專案，也不執行**。試吃只把食物封存成 `LAB_HOME` 裡的唯讀 tar，在記憶體裡讀，不解壓、不 import、不執行。git 抓取關掉 hooks、不 checkout，只接受 https 和 `file://`。沒有 git 時改抓 codeload tarball，並標成 `unverified-against-commit`。
- **只有你能判「有毒」**。靜態規則只會舉旗：高嚴重度旗標讓食物變成「有疑慮」，只有 owner 的 `--confirm-toxic` 會讓它變成「有毒」。
- **先預覽、再備份、才動手**。吸收、移除、還原都是先預覽；套用前先存還原點。還原只寫入或刪除 OAW 管理的路徑，不碰專案紀錄。
- **常設預算只設定一次**（決定 D11）：之後系統在預算內自己決定怎麼測，超過預算才會問你。要吸收哪些成分仍然由你決定。v0 不會真的花錢。
- **「加強」只在有實測證據時出現**，否則一律寫「未量測」。執行中只顯示進度，不顯示即時分數。
- **遊戲頁只給你自己用**：只綁 `127.0.0.1`，每次啟動換一個通行碼，拒絕其他 Host 和跨站請求，動作只接受 JSON POST，一次只跑一個動作。食物裡的文字一律當成純文字顯示，不渲染食物附帶的 HTML、SVG 或圖片。
- **食物內容是資料，不是指令**。食物或報告裡的文字不能授權任何動作。

## 資料放在哪裡

### 專案裡：`.oaw/catalog/`

| 檔案 | 內容 |
|---|---|
| `registry.json` | 食物清單：來源、合併的網址、固定版本 |
| `evidence/<food>/` | 證據：`I0-*.json`（投食紀錄）、`T0-*.json`（靜態檢查）、`imported-*.json`（匯入的歷史證據） |
| `decisions.jsonl` | 你的決定：吸收、移除、分流旗標 |
| `plans/<food>.json` | 系統的測試計畫和預估 |
| `policy.json` | 常設預算（設定後才有） |
| `scout.json` | 覓食候選和被濾掉的數量（覓食後才有） |
| `builds.json` | 版本清單、每版的 skill 和成分、時間線 |
| `absorbed/<food>.json` | 吸收收據：裝了哪些檔案和它們的 hash |
| `effect.json`、`view.json`、`status.json` | 衍生檔，可以隨時重算（`effect`、`view`） |

系統會產生 `.oaw/catalog/.gitignore`，只讓 `builds.json` 和 `absorbed/*.json` 可以 commit，其他資料只留在這台電腦。移除內建 skill 或 EGM 時，`oaw.py` 的備份放在 `.oaw/backups/`。

### 專案外：`LAB_HOME`

| 系統 | 預設位置 |
|---|---|
| Windows | `%LOCALAPPDATA%\oaw\lab` |
| macOS | `~/Library/Application Support/oaw/lab` |
| Linux | `$XDG_DATA_HOME/oaw/lab`（預設 `~/.local/share/oaw/lab`） |

可以用環境變數 `OAW_LAB_HOME` 改到別的目錄，但它必須在專案外，也不能在 OAW checkout 裡，否則指令會拒絕。

| 路徑 | 內容 |
|---|---|
| `foods/<food>/<commit>/source.tar`、`inventory.json` | 封存的食物快照（唯讀）和檔案清單 |
| `builds/<專案代碼>/<hash>.tar` | 每個版本的還原點 |
| `pending/` | 等待確認碼的請求，只存確認碼的雜湊 |

還原點只存在建立它的那台電腦的 `LAB_HOME`。刪掉 `builds/` 就不能再還原到那些版本；隊友 clone 專案後看得到 `builds.json`，但不能用你的還原點。
