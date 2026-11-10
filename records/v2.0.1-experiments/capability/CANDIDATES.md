# 能力型候選：影片剪輯、遊戲製作（2026-11-10，給 owner 勾）

依據：D38（吸收的第二種目的：讓 repo 多一種原本沒有的能力）。這張表只是入口清單。**還沒有 clone、安裝或試吃任何一個**；owner 勾了才開始。

數字怎麼來的：
- 星數、授權、最後 push 日期：2026-11-10 用 GitHub API 逐一查的（16 個全查）。星數照 D26 只當先驗，不是品質。
- 「要什麼工具」：從各 repo 的 README 讀的，沒有實際裝過。
- 「自己怎麼說」：repo 自己的描述，沒有驗證過。

## 影片剪輯

| # | 來源 | 星數 | 授權 | 最後 push | 要什麼工具 | 自己怎麼說 |
|---|---|---|---|---|---|---|
| V1 | heygen-com/hyperframes | 81.7k | Apache-2.0 | 11-10 | Node、Chrome、ffmpeg | 寫 HTML，算成影片 |
| V2 | OpenMontageInc/OpenMontage | 79.2k | AGPL-3.0 | 11-09 | Python、Node、ffmpeg、Remotion；多處要外部 API key | 12 條製作流程的整套影片系統 |
| V3 | Vincentwei1021/video-shotcraft | 18.2k | Apache-2.0 | 11-09 | Node、Remotion、Chrome、ffmpeg；README 說不需要 API key | 用 Remotion 做產品宣傳片的 skill |
| V4 | remotion-dev/skills | 6.7k | **沒有授權檔** | 11-09 | Node、Remotion | Remotion 官方的 agent skill |
| V5 | kajisho5/ffmpeg-skill | 4.9k | MIT | 11-07 | ffmpeg | 42 個 ffmpeg 工具，有機器可讀的介面 |
| V6 | samuelgursky/davinci-resolve-mcp | 4.0k | MIT | 11-09 | DaVinci Resolve Studio（付費桌面程式）、Python | 接 DaVinci Resolve 的 MCP server |
| V7 | 0xsline/OpenChatCut | 3.0k | AGPL-3.0 | 11-06 | Node；多處要外部 API key | 對話式的多軌剪輯器 |
| V8 | nateherkai/herk-edit-kit | 2.7k | **不明** | 10-14 | Node、ffmpeg；素材生成要自備 API key | 剪短影音的工具包 |

## 遊戲製作

| # | 來源 | 星數 | 授權 | 最後 push | 要什麼工具 | 自己怎麼說 |
|---|---|---|---|---|---|---|
| G1 | Donchitos/Claude-Code-Game-Studios | 37.6k | MIT | 11-09 | 引擎自選（Godot、Unity、Unreal）；附 hook | 49 個 agent、72 個 skill 的遊戲工作室 |
| G2 | CoplayDev/unity-mcp | 15.8k | MIT | 10-30 | Unity Editor、Python | 接 Unity Editor 的 MCP |
| G3 | gamedev-skills/awesome-gamedev-agent-skills | 8.0k | Apache-2.0 | 11-09 | 看選哪個引擎 | 77 個遊戲開發 skill（Godot、Unity、Unreal、Phaser…） |
| G4 | htdt/godogen | 7.3k | MIT | 10-16 | Godot；素材生成的 API key 是選配 | 用 Claude Code 或 Codex 自動做 Godot 遊戲 |
| G5 | Coding-Solo/godot-mcp | 6.6k | MIT | 04-16 | Godot、Node | 接 Godot 的 MCP server |
| G6 | IvanMurzak/Unity-MCP | 4.6k | Apache-2.0 | 11-09 | Unity Editor | Unity 的 skill、MCP 工具和 CLI |
| G7 | scenario-labs/skills | 3.6k | MIT | 11-09 | Scenario 的雲端帳號 | 生圖片、影片、音訊、3D 素材 |
| G8 | hi-godot/godot-ai | 3.5k | MIT | 11-09 | Godot | Godot 的 MCP server 和 AI 工具 |

## agent 的建議（owner 可以改）

**先試這幾個**，理由是授權乾淨、不用雲端帳號、成品可以用機械方式檢查：

| 類 | 建議 | 成品怎麼機械檢查 |
|---|---|---|
| 影片 | V5 ffmpeg-skill、V1 hyperframes | `ffprobe` 讀成品的長度、解析度、音軌和視訊軌數量，對得上題目要求才算過 |
| 遊戲 | G4 godogen、G3 的 Godot 部分、G8 godot-ai | `godot --headless` 載入專案結束碼為 0，加上專案自己的 headless 測試腳本 |

**先不試**：
- V2、V7：AGPL-3.0。可以試吃，但不能把內容放進 OAW（OAW 是寬鬆授權）；最多只能寫成「另外自己裝」。
- V4、V8：沒有授權或授權不明。可以試吃，不能收進 OAW。V4 是 Remotion 官方的，想收的話要先問對方。
- V6、G2、G6：要 DaVinci Resolve Studio 或 Unity Editor。這台是沒有畫面的 Linux server，裝不起來，也就沒辦法試吃。
- G7：要雲端帳號和額度（憑證只有 owner 能給）。
- G1：一次 49 個 agent、72 個 skill，還附 hook。照 D21 一個食物最多 3 個單位，要先選哪幾個；hook 要先過安全檢查。

## 需要 owner 決定的

1. 勾哪幾個（可以直接回編號，例如「V5 V1 G4」）。
2. 這台機器現在沒有 ffmpeg 和 Godot（Node、Chrome、Docker 有）。試吃影片類要先裝 ffmpeg，遊戲類要先裝 Godot 的 headless 版，都裝在使用者目錄、不動系統。照 D28 前置條件是 owner 的事：可以裝嗎？

判定方式照 D38 的草案（`claude/oaw-2` 的 `docs/plans/v2.0.1-value-check.md` 第 4 節）：跟「同樣的底層工具裝好、但沒有這個 skill」的原生比，看成品過不過機械檢查；結果只有「可選用」或「排掉」，不進預設；裝了沒用到的時候，啟動 token 不能多超過 2%。
