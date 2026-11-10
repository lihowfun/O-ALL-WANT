# 能力型試吃：PPT 和影片（草案，2026-11-10）

依據：D38（能力型怎麼判，agent 的草案）、D41（owner 選了：先做 harness，再試 PPT skill 和影片製作；遊戲不試）。
這份是 agent 擬的自測計畫，**還沒凍結**。凍結前照 D21 給 Codex 審（最多 3 輪），Codex 的意見成立就照改。

## 1. 順序

1. Claude 訂閱先給 harness：H1 的 Claude 格跑完，再跑 I16 的 Claude 格（D39、D41）。
2. 在那之前只做不花 Claude 的事：裝工具、寫檢查程式、請 Codex 盲出題、跑 Codex 格的校準和正式 run。
3. 能力型的 Claude 格排在 I16 的 Claude 格之後，一次只跑一個 Claude process。

## 2. 候選（每個領域最多 3 個，D21）

星數、授權、最後 push 日期是 2026-11-10 用 GitHub API 查的；星數照 D26 只當先驗。「要什麼」是從 README 讀的，還沒裝過。

### PPT（這次新找的）

| # | 來源 | 星數 | 授權 | 產出 | 要什麼 | 為什麼選 |
|---|---|---|---|---|---|---|
| P1 | iOfficeAI/OfficeCLI | 33.2k | Apache-2.0 | 可編輯的 .pptx（也做 docx、xlsx） | 它自己的 CLI 執行檔，附 12 個 skill | 專門給 agent 用的 Office 工具，星數最高 |
| P2 | alchaincyf/huashu-design | 29.1k | MIT | 網頁、原型、可編輯的 .pptx、動畫 | Node；README 提到生圖，要確認是不是選配 | 中文、以設計品質為主 |
| P3 | owner 自己的 professional-pptx | — | owner 的 | .pptx，附版面檢查器 | python-pptx | owner 已經在用；量它到底比原生好多少 |

- **備選**（前三個有一個裝不起來或要雲端帳號時，依序遞補）：carnot-tech/jinba-consulting-pptx-skill（1.6k，MIT）、Gabberflast/academic-pptx-skill（1.5k，MIT）。
- **不試**：
  - 只產 HTML 簡報、不是 .pptx：zarazhangrui/frontend-slides（32.2k）、lewislulu/html-ppt-skill（9.0k）。
  - AGPL-3.0，不能收進 OAW：op7418/guizang-ppt-skill（29.6k）、chuspeeism/dashi-ppt-skill（10.6k）。
  - 要外部生圖 API：ningzimu/codex-ppt-skill、op7418/NanoBanana-PPT-Skills、JuneYaooo/gpt-image2-ppt-skills。
  - 沒有授權或授權不明：GordenSun/GordenPPTSkill、tfriedel/claude-office-skills、sunbigfly/ppt-agent-skills。
- Claude Code 自己帶的 pptx 外掛不是外部食物，不列。試吃時每次都用全新家目錄，N 組看不到任何外掛。

### 影片（沿用 `CANDIDATES.md` 的建議）

| # | 來源 | 星數 | 授權 | 要什麼 |
|---|---|---|---|---|
| V5 | kajisho5/ffmpeg-skill | 4.9k | MIT | ffmpeg |
| V1 | heygen-com/hyperframes | 81.7k | Apache-2.0 | Node、Chrome、ffmpeg |

- 只試兩個。V3 video-shotcraft 建立在 Remotion 上，Remotion 對公司使用另有授權條件（細節沒查），先不試。

## 3. 組別和格

- **N（原生）**：裝好同樣的底層工具，沒有任何 skill。PPT 是 python-pptx、LibreOffice、Node；影片是 ffmpeg、Node、Chrome。N 跑兩次（N1、N2），看同一組重跑自己會差多少。
- **S_k**：N 再照官方說明裝候選 k。
- **兩格**跟 H1 一樣：Claude Code + Opus 5.5（effort high）；Codex CLI + gpt-6.1-sol（reasoning high）。
- 每次 run 都是全新工作區、全新家目錄（只掛登入檔）。沿用 H1 的 runner 和沙箱，也就是 W5 工具組的第一個用途。

## 4. 題目

- 每個領域 4 題。由零上下文的 Codex 盲出：只知道要產出什麼成品，不知道候選是誰、也不知道組別。
- 每題附輸入素材、需求、機械檢查程式和一份參考成品。驗題：參考成品要過檢查，空交和「只交輸入素材」都要不過。
- 需求刻意放進原生容易漏的地方：
  - PPT：內容多到要拆頁、長中文標題、很多列的表格、圖表要可編輯、指定版型和字級。
  - 影片：精準的剪接點、淡入淡出、燒入字幕、混音音量、指定解析度和幀率。
- 校準：Codex 格的 N 跑一次，拿滿分的題目算頂到天花板、不用，請同一份 brief 的新出題者補，最多補兩次（照 H1 驗題 6）。

## 5. 機械檢查（評分程式看不到組別）

**PPT**
- python-pptx 打得開；頁數、每頁標題、指定的文字和數字在對的頁。
- 表格和圖表是可編輯的物件，不是貼圖；圖表的數列值跟題目給的 CSV 一致。
- 版面：每個形狀都在投影片範圍內；文字框彼此不重疊；字級不低於題目規定；每頁字數不超過題目規定。
- 實際算繪：LibreOffice 轉 PDF，頁數一致；用 pdftotext 的座標確認文字沒有超出自己的文字框和頁面。

**影片**
- ffprobe：長度（容許 ±0.1 秒）、解析度、幀率、編碼、音軌和視訊軌數量。
- 抽格：指定時間點的畫面跟參考成品比 PSNR，要過題目寫的門檻（檢查淡入、字幕、轉場的位置）。
- 音量：volumedetect／ebur128 的數值在題目規定的範圍內。

美感不做判定。PPT 的算繪圖會留下來給人看，只當描述。

## 6. 判定（每個候選、每一格分開判）

- 分數 = 4 題裡通過的題數。
- **可選用**：至少一格 S 通過的題數比 N1、N2 都多；沒有任何一格比 N1、N2 都少；閒置條件也要過。
- **排掉**：任何一格比 N1、N2 都少；或兩格都沒有比 N 多；或閒置條件沒過。
- **閒置條件**：裝了但不用（拿 H1 的 A 類其中 2 題來做一般小改動），啟動 token 不能多超過 2%，也不能做錯。
- 結果只有「可選用」或「排掉」，不進預設。可選用的照授權決定能不能收進 OAW：MIT、Apache 可以；owner 自己的 skill 由 owner 決定。
- **限制**：每題只跑一次、只有 4 題，只看得出大的差別。差一題的寫「沒有結論」。

## 7. 預算

- **Claude**：每個領域上限 30M（D35）。
  - 估計每個領域 (N1 + N2 + 3 個 S) × 4 題 = 20 次。每次約 0.5–1M，所以約 10–20M。
  - 閒置檢查約 1M。
- **Codex**：用 ChatGPT 方案，不算在上限內，另外記錄。
- **工具**：ffmpeg 用靜態版、裝在使用者目錄（D41）。OfficeCLI、hyperframes 照官方說明，也裝在使用者目錄。磁碟剩不多，影片素材用短片，跑完就清。

## 8. 下一步

1. Codex 審這份草案，最多 3 輪。
2. 裝 ffmpeg、寫檢查程式、請 Codex 盲出題、驗題。
3. 跑 Codex 格的校準和正式 run；Claude 格排在 I16 之後。
4. 寫 `RESULT.md`，結果放上進度頁。
