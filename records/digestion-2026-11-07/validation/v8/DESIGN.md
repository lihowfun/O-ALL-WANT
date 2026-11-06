# V8 出題紀錄：codegraph 主戰場（VS Code 架構問答）

依 `../PREREG.md`「V8 codegraph 的主戰場」出題。出題者沒有安裝或執行 codegraph，也沒看過任何作答。

## 結論先講
- 題目 4 題，參考事實每題 8 條，`essential` 每題 3–4 條，見 `questions.json`。
- q1 一字不改照抄 codegraph README 的 VS Code benchmark 題。
- q2、q3 的題句照抄 codegraph 多輪 benchmark 的第 2、3 輪追問，前面加一句前情。原因：我們每題單獨作答，「that path」「that protocol」不補前情就沒有指涉對象。
- q4 是出題者補的。題句取自 codegraph repo 裡一份針對 VS Code 的查詢清單，但那份清單是壓力測試用的，不是 benchmark。
- codegraph benchmark 用的模型是 Claude Opus 4.8（`claude-opus-4-8`）。

## 固定的 repo 版本
- `microsoft/vscode` HEAD：`29ad5e7ec8d963aa67226f58a4472697b21d6f35`。commit 時間 2026-11-06T15:20:31-05:00，訊息是「sessions: prevent sent Inbox prompts from reappearing (#346580)」。
- 取得方式：`git clone --depth 1 https://github.com/microsoft/vscode.git <vscode>`，跟 codegraph benchmark 一樣用 depth 1。
- `git ls-files` 共 20,942 個檔案（含非程式碼）。codegraph README 寫「~11k files」，算法不同，應該只算原始碼檔，這裡不比較。
- 下文的 `<vscode>/` 指這份 clone 的根目錄。`questions.json` 裡的 `where` 都是相對這個根目錄的路徑。

## codegraph 公開的資料（來源）
codegraph repo 讀的是 `main` 上的 commit `f72c9d2efb14454ff4f9fd7b8460abd82f19a287`（2026-11-01），以下網址都固定在這個 commit。

### 用在 VS Code 上的 benchmark 題目
1. README「Benchmark Results」→「Full benchmark details」的 Queries 表，VS Code 那一列：
   「How does the extension host communicate with the main process?」
   - https://github.com/colbymchenry/codegraph/blob/f72c9d2efb14454ff4f9fd7b8460abd82f19a287/README.md （Queries 表，約第 253–255 行）
   - 同一題也出現在 `.claude/skills/agent-eval/corpus.json` 的 vscode 條目，以及 `docs/benchmarks/answer-directly-vs-explore-agent.md`。
2. 重跑 README benchmark 的腳本 `scripts/agent-eval/bench-readme.sh`，預設是三輪 session。VS Code 那一列的第 2、3 輪：
   - 「Where in that path would a message be dropped if the extension host crashes?」
   - 「What would I need to change to add a new message type to that protocol?」
   - https://github.com/colbymchenry/codegraph/blob/f72c9d2efb14454ff4f9fd7b8460abd82f19a287/scripts/agent-eval/bench-readme.sh#L20
   - 這兩句用在 README「A note on context」引用的 residual context（殘留 context，也就是 session 結束時仍佔著 context window 的檢索結果）量測：https://github.com/colbymchenry/codegraph/blob/f72c9d2efb14454ff4f9fd7b8460abd82f19a287/docs/benchmarks/residual-context-occupancy.md
3. 有提到、但沒公開完整題句的：`docs/benchmarks/explore-completeness-note.md` 的 A/B 表列了「vscode: rpcProtocol serialize + dispatch」，這只是摘要，原題句沒有公開，所以不採用。
4. 不是 benchmark 的：`scripts/agent-eval/repro-concurrent-explore.mjs` 和 `repro-daemon-clients.mjs` 有 12 句針對 VS Code 的查詢，是 daemon 併發壓力測試用的。q4 從這裡取題句。
   - https://github.com/colbymchenry/codegraph/blob/f72c9d2efb14454ff4f9fd7b8460abd82f19a287/scripts/agent-eval/repro-concurrent-explore.mjs#L37

### benchmark 用的模型
- README 主表（單題、2026-08-05 重測）：「Claude Opus 4.8, `claude-opus-4-8`」，用 `claude -p` headless 跑。來源：README「Full benchmark details」的 Methodology 段（約第 248 行）。
- README 沒寫 effort。跑 benchmark 的腳本 `scripts/agent-eval/run-all.sh` 預設是 `--model sonnet --effort high`，README 那次把模型換成 Opus 4.8；有沒有改 effort，文件沒說。
  - https://github.com/colbymchenry/codegraph/blob/f72c9d2efb14454ff4f9fd7b8460abd82f19a287/scripts/agent-eval/run-all.sh#L28
- residual context 那輪（三輪 session）用的是 Sonnet，不是 Opus。`residual-context-occupancy.md` 自己也寫明，這輪的數字不能和 README 主表並排比較。
- `answer-directly-vs-explore-agent.md`（2026-05）用的是 `opus` 別名，跑互動式 TUI，n=3。
- 對 V8 的意義：PREREG 規定「照 codegraph benchmark 用的模型」，所以作答模型是 `claude-opus-4-8`。effort 依 PREREG 的備案用 high，剛好也是 codegraph 腳本的預設值。

### codegraph 怎麼量
來源同 README 的 Methodology 段：
- 兩組都是 `claude -p` 加 `--strict-mcp-config`。WITH 組接 CodeGraph 的 MCP server，WITHOUT 組給空的 MCP 設定。兩組都可以用內建的 Read、Grep、Bash。
- 每組同一題跑 4 次，報中位數。
- 指標：
  - Cost 取該次 run 的 `total_cost_usd`。
  - Tokens 是每個 assistant turn 的 input（含 cache read 和 cache creation）加 output，逐 turn 加總。
  - Time 是 wall-clock。
  - Tool calls 計入所有工具呼叫，包括 sub-agent 裡的。
  - File reads 是開過的檔案數中位數。
- repo 用 `--depth 1` clone，索引由同一個 CodeGraph build 建立。
- 兩組都封鎖 `codegraph` CLI：PATH 消毒加上 `PreToolUse` hook，避免 WITHOUT 組從 Bash 偷用。README 回報 28 次 WITHOUT run 全部有嘗試、全部被擋。
- README 只量效率（token、時間、工具次數、成本），沒有評答案品質。V8 另外用參考事實盲評品質，這是 codegraph 的公開數字沒有涵蓋的軸，兩邊的數字不能並排比較。

## 四題怎麼選
| id | 題型 | 來源 | 處理方式 |
|---|---|---|---|
| q1 | mechanism | README benchmark | 一字不改 |
| q2 | flow | bench-readme.sh 第 2 輪 | 題句一字不改，前面加前情 |
| q3 | impact | bench-readme.sh 第 3 輪 | 題句一字不改，前面加前情和釋義 |
| q4 | mechanism | 出題者補（題句取自 repro 腳本） | 首字大寫，句尾加問號 |

### q2：補前情
- 原題在第 2 輪，「that path」指第 1 輪答案描述的路徑。V8 每題單獨作答，所以前面加一句：這題接在 q1 之後，「that path」指 extension host 和 main process 之間的通訊路徑。
- 前情只重述 q1 的題目，不提任何檔名或 symbol，避免替任何一組省掉找程式碼的工作。

### q3：補前情，並釋義「message type」
程式碼裡「message type」有三種合理讀法：
1. 在 `MainThread*Shape` 或 `ExtHost*Shape` 上加一個新的 RPC 呼叫，跨 `extHost.protocol.ts`、`api/browser/mainThread*.ts`、`extensionHost.contribution.ts`、`extHost.api.impl.ts` 等多個檔案。
2. 在 `rpcProtocol.ts` 的 `MessageType` enum 加一個 wire 層的新型別，只動一個檔案。
3. 在 `extensionHostProtocol.ts` 的握手控制訊息（Ready、Initialized、Terminate）加一種，只動少數檔案。

讀法不同，參考事實就完全不同，盲評的雜訊會很大，所以前情裡指定讀法 1：「a new kind of call that the extension host can make to the main side」。選讀法 1 的理由：
- 它要跨好幾個檔案，符合「答對需要跨檔」的偏好。
- codegraph 其他 repo 的第 3 輪也都是這類擴充點問題，例如 Django 的「add a new lookup type」、OkHttp 的「add a new interceptor stage」。

讀法 2 沒有被丟掉：q3f7 寫明 wire 層不用改，以及真要加 wire 型別時要動哪裡，標成非必要事實。

### q4：出題者補的
- PREREG 要求公開題不足 4 題時，由出題者依同題型補足。這個 repo 公開的 VS Code benchmark 題只有上面 3 句，所以補 1 題。
- 題句取自 codegraph 自己寫給 VS Code 的查詢清單，只把首字改成大寫、句尾加問號。原句是「how does the keybinding service resolve a chord to a command」。這是 codegraph 作者認為合理的 VS Code 查詢，但那份清單是壓力測試用的，不是品質 benchmark，所以算出題者補的題。
- 挑這句、不挑同清單的「how does the extension host activate an extension」，理由有三：
  - q1–q3 都在 extension host 的 RPC 上，彼此高度相關。換一個子系統，可以降低題目之間的相關性；V1 的 bootstrap 以題為單位，題目太像，等於有效題數變少。
  - 答案要跨好幾個檔案：workbench 的 `keybindingService.ts`、platform 的 `abstractKeybindingService.ts`、`keybindingResolver.ts`、`keybindingsRegistry.ts`、`commandService.ts`，還有 keyboard mapper。
  - 答案明確，全部可以在程式碼裡核對：chord 狀態、when clause 的比對順序、三種 `ResultKind`、5 秒逾時、狀態列文字。

## 參考事實怎麼核對
- 每條事實都在固定的 vscode commit 上讀原始碼核對，用 `grep` 定位，再用 `sed -n` 讀整段函式。沒有用 codegraph，也沒有用任何索引工具。
- `where` 寫成「repo 相對路徑::類別.方法」，多處用分號隔開。欄位和 `digestion-2026-11-03/taste-graphify/erpnext/questions.json` 相同：題目有 `id`、`type`、`question`、`facts`，事實有 `id`、`fact`、`where`、`essential`。
- 機械檢查：用小程式逐條確認 `where` 裡每個檔案存在、每個 symbol 名稱出現在該檔。0 個問題。事實裡引用的字面字串也逐一 grep 過，包括 `Missing proxy instance`、`received unexpected message`、`Waiting for second key of chord...`、`is not a command.`、`vscode:startExtensionHostMessagePortResult`、`UNRESPONSIVE_TIME = 3 * 1000`、`onCommand:`。
- `essential` 的定義：任何正確答案都必須涵蓋的事實，每題 3–4 條。其餘是完整答案會有、但缺了不算答錯的細節。

## 已知的疑點
- **q1 的「main process」有歧義**：VS Code 的 extension host RPC 對面是 renderer（workbench 視窗），Electron main process 只負責 spawn utility process 和轉交 MessagePort。參考事實照程式碼寫（q1f3、q1f4 都是 essential），所以把對面說成 Electron main process 的答案會漏掉 essential。這是題目本身的歧義，兩組面對的題目相同。
- **q2 依賴 Electron 的行為**：
  - extension host 掛掉之後，renderer 對 MessagePort 的 `postMessage` 會怎樣，是 Electron 或 Chromium 的行為，不在 VS Code 原始碼裡。所以 q2f5 只寫「VS Code 不檢查是否送達」，不斷言訊息去了哪裡。
  - renderer 只透過 `ExtensionHostStarter.onDynamicExit`（`WindowUtilityProcess.onExit`，來自 process 的 `exit` 事件）得知 extension host 結束。`UtilityProcess.onCrash` 沒有轉給 renderer。crash 時 Electron 會不會一定發 `exit`，沒有在程式碼裡驗證，所以 q2f1 標成非必要。
- **q3 的讀法是出題者指定的**（見上）。如果 owner 認為應該保留原句不加釋義，q3 的 essential 要重寫。
- **版本漂移**：VS Code 改得很快。事實只對上面這個 sha 成立，作答一定要用同一個 sha 的 checkout。
