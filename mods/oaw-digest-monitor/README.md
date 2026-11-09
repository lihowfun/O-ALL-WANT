# OAW 消化道（oaw-digest-monitor）

A Claude Code mod that shows OAW's skill-intake process as a digestive tract beside the chat and lets the owner operate it.

這是 OAW 正式 skill 吸收流程（`docs/SKILL_INTAKE.md`，D19、D23）在 Claude Code 對話旁的操作畫面。它讀專案的 `.oaw/catalog/view.json` 和 `status.json`，動作全部交給 OAW 自己的 `scripts/catalog.py`。網頁版（`catalog.py ui`）、終端選單（`catalog.py menu`）、`oaw_status.py` 和這個 mod 用的是同一個引擎、同一份資料。

## 畫面

- **消化道**：九站排成 S 形的一條管子（入口＝口……版本＝全身，器官只是圖說）。每樣食物是停在真正那一站的食糰，顏色代表判定（綠＝營養、灰＝未測、琥珀＝有疑慮、紅＝有毒或變差），藍色 `!` 表示等你（只有入口、C 級問題、只有你能做的前置和移除 skill，D28），橘色 `»` 表示自動、Claude 接手，青色 `↑` 表示等發布（合併 PR 時整個分支一次決定，不是逐樣核准），灰色 `?` 表示只剩可選的決定。選一樣食物時，Claude 記錄的試吃（`record-tasting`）和 D21 吸收（`record-absorption`）寫在它們那一站。站的外框代表這一站由誰做：綠＝自動、橘＝Claude 接手、藍＝需要你、青＝部分自動、灰色虛線＝規劃中。
- **試吃中**：管子出現蠕動波，正在試吃的食糰會脈動，狀態列顯示 `🍽 試吃中：<食物> · <站>`。試吃結束或停止時跳出通知，停止會附上原因。超過 10 分鐘沒有更新，畫面寫「可能中斷了」。
- **選一樣食物**：畫出它走過的路，列出九站進度、判定和證據等級、成分（吸收／暫留／排掉），以及**卡點說明**：卡在哪、依據哪個決定、你不處理會怎樣。紀錄沒寫的就寫「紀錄裡沒有寫」，不會自己編。
- **動作**：按鈕來自 view.json 裡這一站能做的事。
  - 會改專案的動作（忘掉、吸收、移除、還原）先跑預覽，按「確認套用」才加 `--apply`。移除一定要寫原因。
  - 分流旗標要在你自己的終端輸入確認碼，所以按鈕只會複製 `catalog.py menu` 指令，不會替你確認。
  - 「問 Claude 這個卡點」把這樣食物的事實放進輸入框，你在最後打上問題再送出。
  - 「你點名」：貼 GitHub repo 或 arXiv 網址，可以一次貼很多個，送去免費試吃（`catalog.py add`）。
- **EGM 審查開關**（D33）：畫面下方有「開／自動／關」三個按鈕，● 是目前的位置，下面一行說明它的意思。按下去會執行 OAW 自己的 `scripts/oaw_mode.py egm on|auto|off`，和指令、對話裡的 `oaw-review` 用同一個設定（專案的 `.oaw/settings.json`）。沒有這個檔就是預設「自動」：用目前證據最好的設計審查，也就是一次全新 context 審查（D37，X2 實測後保留）；要完整 EGM 就按「開」。只想跑一次 EGM 而不改開關，就打 `/egm-review`。
- 終端機沒有 SVG，改成一站一行的文字版，內容相同。

## 安裝

在終端的 Claude Code 提示列輸入：

```text
/plugin install oaw-digest-monitor --marketplace lihowfun/O-ALL-WANT
```

在 shell 裡：

```bash
claude plugin install oaw-digest-monitor --marketplace lihowfun/O-ALL-WANT
```

開發中想直接從這個資料夾載入：`claude --plugin-dir mods/oaw-digest-monitor`。

這個 mod 是選裝的，安裝 OAW 不會自動裝上它。在 OAW 專案、它的上層資料夾，或這些上層資料夾的其他子資料夾裡開 Claude Code，mod 會自己找到專案（有 `.oaw/catalog` 的資料夾）和 OAW checkout（有 `scripts/catalog.py` 的資料夾），找到專案時會自動打開畫面。之後隨時可以用 `/oaw-digest` 打開。

## 設定

| 欄位 | 預設 | 用途 |
|---|---|---|
| `project` | 空白（自動找） | OAW 專案資料夾 |
| `oawCheckout` | 空白（自動找） | 有 `scripts/catalog.py` 的 OAW 原始碼資料夾；找不到時按鈕會停用 |
| `python` | `python3` | 執行 catalog.py 的 Python 3.10+，Windows 可以填 `py -3` |
| `motion` | 開 | 蠕動和脈動動畫；關掉時畫面靜止（系統設定「減少動態效果」時也會停） |

## 它不做的事

- 不寫任何專案檔：所有改變都經由 `catalog.py`，也遵守 catalog.py 的預覽、套用和確認碼規則。
- 不替你輸入確認碼，不設定常設預算。
- 不顯示紀錄裡沒有的數字；品質沒有實測就寫「未量測」。

## Codex 怎麼用

Codex 目前沒有可以掛畫面的擴充介面，所以這個 mod 只在 Claude Code 裡有。Codex 和任何終端讀的是同一份資料：

```bash
python3 scripts/catalog.py ui --target /path/to/project     # 網頁版消化道，可以直接操作
python3 scripts/catalog.py menu --target /path/to/project   # 終端選單，同樣的站和動作
python3 scripts/oaw_status.py --project /path/to/project    # 只看
```

## 檢查

```bash
claude plugin validate mods/oaw-digest-monitor
claude plugin test mods/oaw-digest-monitor
```

`tests/digest.test.tsx` 用一次真實 `catalog.py add` 產生的 view.json（四樣食物，另加一樣停在核准的合成食物）涵蓋這些情境：

- 找到專案和 OAW checkout（工作資料夾移進子資料夾也找得到），在桌面版和終端版都畫出每樣食物
- 選食物後顯示卡點說明
- 終端限定的動作只複製指令
- 預覽之後才套用；移除要寫原因
- 試吃中顯示動畫，試吃結束跳通知
- 試吃停止時寫出原因；10 分鐘沒更新寫可能中斷
- 沒有專案、沒有 view.json、view.json 格式不對時都有說明
- 關掉動畫
- 貼網址送去試吃

`tests/test_digest_mod.py`（OAW 的 gate）檢查這個 mod 和 catalog 引擎的約定沒有分岔：view 格式版本、view.json 的來源檔清單、每一種動作都有對應的處理。
