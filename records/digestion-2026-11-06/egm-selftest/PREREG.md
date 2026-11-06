# EGM 自測：拿掉 EGM，用現行 SOP 試吃一遍（預先登記）

2026-11-06，owner：「也要試試看好用的功能在這套消化系統能否被吸收，可以自我測試 EGM 拿掉，用目前 SOP 看看，如果都被排泄，那要謹慎思考可行性。」寫在任何計分作答之前，推上 records 之後才開跑。

## 要回答的問題
1. 把 EGM 當成新食物，照現行 SOP（D25、D26、D28：官方安裝、每組都跑、凍結題目、盲評、事先寫死的規則）試吃，它會被吸收還是排掉？
2. 這套 SOP 的量測工具，量不量得出「好東西」？為此加一組**正對照 P**：一份故意洩題的檢查清單，點名這些案例埋的缺陷類型。它理應有用。如果連 P 都判不出「更好」，代表在這組題目上，SOP 對任何食物都只能排掉，問題在工具，不在食物。
3. 現行試吃規則（更好或更省才吸收）和 D21 的 B 級規則（「齊平以上才吸收」）對同一組數字會不會給出不同結論。

## 題目（沿用，不重出）
- `claude/oaw-2` 的 `evals/egm-local/cases/` 三個設計審查案例：`orders`、`events`、`clean`。2026-10-29 凍結：`spec.json` 的 canonical sha256 `d108b3a9e5993ef7…`（`spec.sha256`），13 個案例檔的 sha256 記在 `spec.json` 的 `case_hashes`。`setup.sh` 開跑前逐一核對。
- 埋的缺陷（rubric，同一份 `spec.json`）：
  - `orders`：嚴重 2（檢查和預留不是原子操作會超賣；重送的訂單換新 UUID 會預留兩次）、主要 2（MongoDB 違反已接受的儲存 ADR；只留 7 天的帳本答不了 30 天的客服查詢）、陷阱 2。
  - `events`：嚴重 2（舊的或重送的事件會蓋掉較新的版本；完整 authorization header 寫進 log）、主要 2（Flux shim 沒有定義；實作計畫沒有可執行的範圍和完成條件）。
  - `clean`：沒有埋缺陷，陷阱 5（例如 Redis 是 ADR-012 核准的例外；舊的 ADR-002 已被取代）。
- 每次重複 8 個埋的缺陷，3 次共 24 個。
- 2026-10-29 用 Codex 跑過同一組題目：三組都抓到 24/24，誤報 0／1／0。這只是先驗，不是這次的判定依據（D25：沒在 Claude 上跑過不下結論）。

## 三組（同一個 CLI、同一個模型）
每組每個案例一個固定工作區：案例檔（README、docs、src）＋ OAW V2（`claude/oaw-2`，`oaw.py init --host claude --skills oaw-evidence`）。
- **「拿掉 EGM」怎麼做**：用支援的作法，安裝時只選 `oaw-evidence`，不裝 EGM 的 skill 和 agent。另外刪掉 `.oaw/integrations/egm`：兩條支援的移除路線（這個 recipe 和 `catalog.py remove egm`）都會把不會執行的 EGM 執行檔留在這裡，`AGENTS.md` 也還寫著「V2 includes the complete pinned EGM runtime」。不刪的話，原生組可能讀到它。`AGENTS.md` 保留原樣。這件事本身記成一個發現。
- **N 原生**：上面的工作區。可以開子 agent（最多 9 個），和 2026-10-29 的原生組相同。
- **E EGM（食物）**：上游 `google/elephant-goldfish-model` @ `f0ba151b252c9abf1318d9fe857a43265d06de89`，也就是 V2 打包的版本。照它的 README 和 `docs/claude.md` 官方安裝：本機 checkout 當 marketplace，`claude plugin marketplace add --scope project`、`claude plugin install --scope project egm@egm`。作答用 `/egm:egm-review`，參數 TargetFile `docs/design.md`、GoldfishContext 是 README、全部 ADR 和 src，Step `uninterrupted`（Consolidated report with all review rubrics：五個階段不停、不改設計）。照 `docs/claude.md` 的 headless 規定，用 `--add-dir` 開放讀取 plugin 根目錄。
- **P 正對照**：N 的工作區，`CLAUDE.md` 多一行專案檢查清單（`setup.sh` 的 `CHECKLIST`），用中性的字點名：原子性和重送、技術選擇對照已接受的 ADR、資料保留期間夠不夠查詢、事件亂序或重送時狀態不能倒退、log 不能有秘密、每個點名的元件都要有定義、實作計畫要有範圍和完成條件。它故意洩題，只用來驗證量測工具。

三組共同的設定：
- Claude Code 2.1.287、`claude-opus-5-5`、`--effort high`、`--setting-sources project`、`--strict-mcp-config`（沒有 MCP）。
- 每次都開新的 session，stdin 關閉，session 不保存，上限 3,600 秒。
- 工具一樣：Read、Write、Glob、Grep、Agent，`--permission-mode acceptEdits`。沒有 Bash、沒有 Edit。
- 計費來源必須是訂閱（`apiKeySource: none`），不是就停。E 的 init 沒有 `egm` plugin 或 `egm:egm-review` 指令就停；N、P 的 init 出現 `egm` 也停。
- 作答提示是 `evals/egm-local/review_prompt.md` 的審查要求改寫給 Claude（`taste_run.py` 的 `TASK`）：最後寫一份 JSON 報告到 `review_out/report.json`，最多 900 字，欄位 `completed`、`findings`、`uncertainties`，不能在發現裡寫方法、工具或審查者的名字。
- 每次作答後，新寫的檔案複製出來，改到原始檔的情形記下來，工作區再從原始 tar 還原。N、P 讀到任何 EGM 路徑都記成污染。

## 次數和順序
- 3 組 × 3 案例 × 3 次 = 27 次。以「次」為外圈：第 1 次跑完三個案例，再跑第 2 次。
- 每個（案例、次）裡三組的順序輪替：第 1 次 N、E、P，第 2 次 E、P、N，第 3 次 P、N、E。
- 試跑（不計分，算消化開銷）：一份不在題庫的小設計（短網址的限流），E 組經過 runner 跑一次，確認 plugin 載入、子 agent 會開、讀得到 plugin 檔案，並量 E 每次的 token。結果寫在本頁最後。

## 評分
- 每份報告一個零上下文評分者（`claude -p`、沒有工具、空資料夾、`claude-opus-5-5` high），給它案例原始檔（加行號）、凍結的 rubric、匿名報告。指示照 `evals/egm-local/grade_prompt.md`。和 2026-10-29 不同：這次每份只有 1 位評分者，沒有仲裁。
- 匿名：只給 `completed`、`findings`、`uncertainties`；會洩漏組別的字（EGM、Goldfish、各 persona 和階段名、checklist）遮成 `[method]`，工作區路徑遮成 `<ws>/`；評分順序依 hash 打亂。
- 每份報告記：有效與否、抓到的埋缺陷（嚴重／主要）、沒有根據的具體指控、違反的陷阱、其他有效發現數、不確定事項數。沒有可解析報告的那次，記成 0 個偵測，不呼叫評分者。

## 判定規則（先寫死）
每組 9 次加總，和 N 比。只比三組都有評分的（案例、次）。
- **變差**：埋缺陷偵測比 N 少 2 個以上，或沒有根據的指控比 N 多 3 個以上。
- **更好**：偵測比 N 多 2 個以上而且嚴重缺陷沒有比 N 少，或沒有根據的指控比 N 少 3 個以上而且偵測不比 N 少。
- **一樣好但比較省**：偵測不比 N 少、沒有根據的指控不比 N 多，而且每次 token 的中位數不到 N 的 70%。
- 其他：**沒有證明比原生好**。

依序看，先符合的算數。每組的結論寫兩次：
1. **現行試吃規則**：「更好」或「比較省」才吸收（absorb）；「變差」不收（decline）；其他是沒證明比原生好（not-shown-better，不收）。
2. **D21 B 級的字面**：「齊平以上才吸收」。齊平 = 偵測不比 N 少，而且沒有根據的指控不比 N 多（不看成本）。

**天花板檢查**：N 抓到 23 個以上（24 個裡），就寫明「這組題目的品質軸，任何食物都不可能判成更好」，因為最多只能再多 1 個，不到門檻 2。

回答 owner 的問題：
- E 照現行規則被排掉，而且 P 也判不出「更好」→ 是量測工具判不出好東西，SOP 照現在的寫法對這類食物不可行，要改的是 SOP，不能把這次的「不收」當成 EGM 沒用。
- E 被排掉、P 判出「更好」→ 工具量得出好東西，EGM 在這組題目上確實沒有勝過原生。
- E 判成「更好」或「比較省」→ 現行 SOP 能吸收 EGM。

## 預算（D13，EGM 當食物，上限 10M）
- 三組合計 9.0M（原本分組的 E 7.0M、N 1.0M、P 1.0M 加總；改成合計，是因為 N 也可以開子 agent，分組上限可能先卡住 N）。runner 在每個（案例、次）開始前，用每組到目前為止最大的一次估算這一組的花費，加起來會超過就不開始，只比完整的組。次數不到 3 次會寫明。E 的第一個估計值用試跑量到的數字。
- 被用量上限切斷的 session 花掉的 token 也算進 9.0M，但不算一筆作答。
- 評分和試跑算消化開銷（2026-11-06 這一輪）。

## 被訂閱用量上限切斷時
- 作答：session 的結果是「hit your … limit」或 HTTP 429，或整次沒有花任何 token，就**不算跑過**：不寫進 `rows.jsonl`，記在 `out/deviations.jsonl`，runner 乾淨地停下（exit 6），重置後重跑會從那一次接著跑。
- 評分：評分者的回覆是錯誤、碰到用量上限、或沒有花任何 token，就**不算評過**：不寫成分數，記在 `grades.jsonl.deviations`，評分停下（exit 6），重跑時接著評。
- 所有這類情形都在結果頁的「偏差」列出。

## 事先寫明的限制
- 只有 3 個案例，每格 3 次；每份報告 1 位評分者，評分者和作答者都是 Opus 5.5（AI 評 AI）。
- JSON 報告最多 900 字，E 要把五個階段的合併報告濃縮進去，可能漏掉它的部分發現；2026-10-29 的協議也是這樣，為了三組可比。E 的完整階段報告留在本機。
- `/egm:egm-review` 在 headless 下沒有人回答 checkpoint，所以用 uninterrupted；這不測 EGM 的互動式流程和修正迴圈。
- P 洩題，只驗證工具；它的結果不代表任何真實食物。
- 這次也不測 EGM 的 brainstorm、draft、resolve、bootstrap、drift-report：這組題目量不到它們。

## 執行
`T=<試吃資料夾> OAW=<claude/oaw-2 checkout> CLAUDE=<claude CLI> RECORDS=<本資料夾> bash setup.sh`，接著 `T=… CLAUDE=… OAW=… bash run.sh`。原始 stream-json 和 E 的階段報告留在本機，不公開；`out/rows.jsonl`（路徑遮掉）、`out/grades.jsonl`、`out/summary.json`、`proof.json` 和結果頁 commit 到這裡。

## 試跑結果（不計分，消化開銷）
- 第 1 次：五個階段跑到第 9 階段時碰到訂閱的 5 小時用量上限，session 以「You've hit your session limit」結束，沒有報告，花了 1,054,525 token。照上面的規則不算跑過；它促成「被用量上限切斷時」這一節。
- 第 2 次（14:36，用量重置後）：exit 0，476 秒，932,952 token。init 有 `egm` plugin 和 `egm:egm-review` 指令，計費來源 none，Claude Code 2.1.287、`claude-opus-5-5`。主 session 開了 9 個真的子 agent（`egm:egm-zoom-out` 2、`egm-comprehension` 1、`egm-design` 1、`egm-structural` 1、`egm-style` 2、`egm-implementation-readiness` 1、`egm-codebase-details` 1），子 agent 都是 Opus 5.5；沒有被拒的權限。五份階段報告、合併報告和 `review_out/report.json`（845 字，5 個發現、8 個不確定事項）都寫出來，原始檔沒有被改。E 的第一個估計值用 932,952。
- init 的 plugin 清單在每一組都還有 4 個主機內建的 `cc-plugin-*`（來自這台機器的 Claude Code 環境，不是食物，`--setting-sources project` 也擋不掉）。N、P 開跑後核對，預期三組相同，記在這裡。
- 兩次試跑共 1,987,477 token，算消化開銷。

檔案 sha256（凍結）：

- `taste_run.py`：`0a2cd83c2e3fcb194f68342c0944b76f8f55e3e21c6ffdf7f9b6ea5deb0f977c`
- `taste_grade.py`：`1c7a3e4ddd9e97d17f470645843d4349ec823cdee4e82e697cc76864dcefbf82`
- `summary.py`：`bf8c506db8a35d235b998dbd93c6352aff8545c833b75b1f56d10e884414acfc`
- `setup.sh`：`7e69ba522d97d2d4bc4fb32ac31baa0eff6445398b9c55804dfece68ece5b20f`
- `run.sh`：`7bab8361197e6f73f17d8dbdf05e69aba6c1ed872c57f98f7c99032126562382`
- `snap_user_state.py`：`5ff049567943cf47ebe80a575f0e3728dd4201474d86c8565e8696f1ad8784ad`
