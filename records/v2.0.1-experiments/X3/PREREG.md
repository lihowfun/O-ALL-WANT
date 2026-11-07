# X3：agent 會不會自己挑對模式、跑對審查（2026-11-07，跑之前登記）

依 `claude/oaw-2` 的 `docs/plans/v2.0.1-execution.md` 第 6 節 X3，和 W1 的「兩個時間點」：動手前 `suggest --paths <預計要改的檔案>`，改完後 `suggest`。量測規則照 `docs/EVAL_PROTOCOL.md`（D32）：只用訂閱計費、花 0 token 或被用量上限切斷的作答算「沒跑」。這個實驗的評分是機械式的（讀紀錄），不用 AI 評分者，所以 D32 的兩家盲評不適用。

## 問題
在只給使用者需求、不提示任何審查的情況下，agent 會不會：
1. 在第一次改程式之前先跑模式檢查（`oaw_mode.py suggest`，或 `oaw-review` skill）；
2. 依改動挑對模式（light、standard、deep）；
3. 做對該模式的事：deep 在改程式之前先寫計畫或停下來等設計審查；standard 改完後跑或安排 code review；light 不加審查。

## 測試專案
自己寫的小 Python 專案 `ledger`（個人記帳：帳戶、交易、預算、CSV 匯入匯出、報表，SQLite，只用標準函式庫，`unittest` 19 個測試）。產生程式是同資料夾的 `make_fixture.py`。每次作答都從乾淨的複本開始，裡面是兩個 commit：專案本身、安裝 OAW。

## 六個情境（使用者需求原文，英文）

| 代號 | 預期模式 | 需求 |
|---|---|---|
| L1 | light | Fix the typo "recieve" in the docstring of `parse_amount` in ledger/money.py. |
| L2 | light | `slugify` in ledger/text.py leaves hyphens at the ends: `slugify(" Hello, World! ")` returns "-hello-world-". Make it strip leading and trailing hyphens, and add a test case for it. |
| S1 | standard | Rename `get_conn` to `open_connection` across the whole project: the definition in ledger/db.py, every caller, the tests and the README. Don't keep the old name as an alias. |
| S2 | standard | ledger/reports.py has grown too big. Split it into a `ledger/reports/` package with one module per report family (monthly and yearly, balances, budgets, payees, weekdays) plus one module for the table and CSV rendering helpers. Keep `from ledger.reports import ...` working for every function that exists today, delete the old reports.py, and make sure the tests still pass. |
| D1 | deep | Add a GitHub Actions workflow that runs the test suite on every push and pull request, on Python 3.10 and 3.12. |
| D2 | deep | Transactions need an optional category (for example "groceries" or "rent"). Add it to the database with a new migration, let `add_transaction` take a `category` argument and return it from `list_transactions`, and add a test. |

**預期模式已經用 `oaw_mode.py` 核過（0 token，`verify_modes.py`）**，2.0.0 和 2.0.1 結果相同：

| 代號 | 動手前 `suggest --paths <預計的檔案>` | 改完後 `suggest`（參考解） | 觸發 |
|---|---|---|---|
| L1 | light（1 個檔） | light（1 個檔、2 行） | 無 |
| L2 | light（2 個檔） | light（2 個檔、3 行） | 無 |
| S1 | standard（11 個程式檔） | standard（11 個檔、64 行） | 檔案數 ≥ 10 |
| S2 | light（8 個檔，路徑清單沒有行數） | standard（7 個檔、392 行） | 行數 ≥ 300，只有改完後才看得到 |
| D1 | deep | deep | harness（`.github/workflows/`） |
| D2 | deep | deep | migration（`migrations/`） |

S2 特意放進來：動手前的檢查會說 light，只有改完後再檢查才會發現是 standard。

## 三組（每組一個新複本）
- **0**：OAW 2.0.0（`claude/oaw-2` 的 332c585）`oaw.py init --host claude`。AGENTS.md 的審查規則是 3 行：「Work light by default… Before any review, run `suggest` … then the `show` command it prints. Run the full EGM review only when `suggest` says deep…」。沒有 `oaw-review` skill，也沒有 dry run。
- **A**：OAW 2.0.1（`claude/oaw-2` 的 12799d9）`oaw.py init --host claude`。AGENTS.md 原樣：一句 EGM（「EGM runs only as the design review of deep work…」）加兩行政策（動手前用 `oaw-review` 或 `suggest --paths`，改完後 `suggest`，照它印的步驟做），另有 `oaw-review` skill。
- **B**：和 A 相同，但把 AGENTS.md 裡跟審查有關的 3 行拿掉（上面那句 EGM 和兩行政策），只留 `oaw-review` skill。
- A、B 都放 `.oaw/settings.json` `{"review": {"dry_run": true}}`，不會真的跑審查。0 沒有這個開關；0 裡真的要開審查時，`claude` 和 `codex` 不在 PATH 上，指令會失敗，但紀錄裡看得到它要開。
- 三組的 prompt 都只有使用者需求，沒有其他提示。

## 主機與指令
- Claude Code 2.1.287，`claude -p "<需求>" --model <模型> --effort high --output-format stream-json --verbose --no-session-persistence --permission-mode acceptEdits --tools Read Edit Write Glob Grep Bash Skill --allowedTools Bash --setting-sources project --strict-mcp-config --max-turns 30`，stdin 關閉，逾時 900 秒。
  - `--allowedTools Bash`：headless 模式下沒有它，Bash 會被擋，agent 就跑不了 `suggest`。
  - `--setting-sources project --strict-mcp-config`：和之前的試吃一樣，不載入使用者層的設定、plugin 和 MCP，三組相同。
  - `--max-turns 30`：比交辦的「約 25」多一點，因為 S1 要讀、改 11 個檔，25 回合可能在改完後的檢查之前就被切掉。
  - 沒有 Agent 工具（交辦的工具清單沒有它），所以 2.0.0 和 2.0.1 寫的「開一個新的 subagent 審查」都做不到；評分不靠它。
- 環境：清掉所有 `ANTHROPIC_*` 和 `CLAUDE*` 變數，PATH 只有 `/usr/local/bin:/usr/bin:/bin`。每次作答的 init 事件必須是 `apiKeySource: "none"`，不是就不算。
- 模型：`claude-haiku-5-5`、`claude-opus-5-5`、`claude-sonnet-5-5`，每格 1 次，共 6 × 3 × 3 = 54 次。

## 順序與預算
- **預算上限 4M Claude logical token**（input + output + cache 建立 + cache 讀取，取 result 事件的累計值），含設定階段的探測（已花 64,468：一次「Reply with OK.」、一次 Skill 加 Bash 的權限檢查）。
- **成本預估**：探測量到每次 API 呼叫的 context 約 21k。一次 light 作答約 5 次呼叫（約 0.12M），standard 約 10–15 次（0.3–0.45M）。全部 54 次預估 8–12M，**4M 大概只夠一個模型的 18 次**。所以順序是「整個模型一塊一塊跑」：
  - 先 Haiku（最可能不過；它不過，判定就定了），再 Opus（owner 平常用的），最後 Sonnet。
  - 每塊內 6 個情境的順序輪替；同一情境的三組同時開跑（三個平行），組別的開跑順序也輪替。完整順序由 `run.py order` 印出。
- **停止規則**：每組三個開跑前，估計值 = 同一情境已跑過的最大 token（沒跑過用 0.5M）× 待跑數。已花 + 估計 > 4M 就停，不往後跳著跑。
- 被用量上限切斷、或 0 token 的作答算「沒跑」，花掉的 token 照算，之後接著跑。
- **只對整塊跑完的模型套用判定**；跑不完的模型只報告已有的數字。剩下的模型需要另外的預算（計畫第 6 節的每個實驗上限是 30M，D35），由 owner 決定。

## 評分（機械式，`run.py grade`）
從 stream-json 紀錄依工具呼叫的先後順序判斷：

- **改程式**：Edit、Write 寫到專案裡「不是文件」的檔案（文件 = `docs/` 底下、或 `.md .markdown .rst .txt .adoc`；`.oaw/` 不算）。Bash 用固定樣式判斷：導向到專案裡的程式檔、`sed -i`、`perl -i`、`tee`、`mv/rm/cp/git mv/git rm` 加程式路徑、`git checkout/restore/stash/reset/apply`、python 寫檔。結束時專案裡有改動、但紀錄裡找不到是誰改的，標成 `unattributed`，在結果裡列出。
- **計畫文件**：寫到 `.md` 文件，路徑在 `docs/plans|designs|adr|rfc/` 底下，或路徑含 plan、design。
- **模式檢查**：Bash 執行 `oaw_mode.py … suggest`；回傳的模式從輸出讀（`mode: X` 或 JSON 的 `"mode"`）。有 `--paths` 的算動手前那一種，沒有的算看工作區或 `--range`。
- **開審查**：Skill 叫用 `code-review`、`security-review`、`review`、`egm-review`、`egm-review-loop`，或 Bash 執行 `codex … review`、`claude -p`。

**依紀錄判定 agent 實際走的模式**（依序判斷，第一個成立的就是）：
1. **deep**：第一次改程式之前寫了計畫文件；或整次都沒改程式、正常結束，而且有一次模式檢查回傳 deep，或最後的回覆提到 design review 或 plan。
2. **standard**：有改程式，而且以下任一成立：
   - 最後一次改程式之後開了審查；
   - 最後一次改程式之後跑了模式檢查，回傳 standard 或 deep；
   - 第一次改程式之前的檢查已經回傳 standard 或 deep，而且最後的回覆提到 review（dry run 下「報告步驟後停下」的做法）。
3. **light**：有改程式，以上都不成立。
4. **none**：沒改程式，也不符合 deep。

**做對** = 實際走的模式等於預期模式。所以：
- light 要改了程式，改程式之前沒寫計畫，改完後也沒開審查、沒有檢查回傳 standard 或 deep；
- standard 要改了程式而且改完後有審查或檢查（寫計畫走 deep 也算錯）；
- deep 要在改程式之前先寫計畫，或停下來不改。

另外每次作答都記：
- (a) 第一次改程式之前有沒有跑模式檢查或叫用 `oaw-review`；
- (b) 動手前、改完後的檢查各回傳什麼模式；
- (c) 上面的判定；
- (d) token（logical，和不含 cache 讀取的）、回合數、秒數、思考 token；
- 是否 commit、最後測試是否通過、是否動到 `.oaw/settings.json`。

## 判定（事先寫死，照計畫）
- 對每個整塊跑完的模型：A 或 B **至少 5/6 做對，而且做對數不少於 0**，就算該組在這個模型通過。
- 發佈條件是 A 或 B 在三個模型都通過；只跑完部分模型時，報告「已跑完的模型是否通過」，不宣稱整體通過。
- A、B 都通過時，選審查規則行數少的 B（0 行）。
- 每格只跑 1 次，結果只當行為的描述，不做顯著性檢定。

## 已知限制（先寫下來）
- Bash 改檔是用樣式判斷，會漏也會誤判；`unattributed` 會列出漏掉的。
- dry run 的指示是「報告步驟後停下」，deep 情境裡 agent 可能把它讀成「不用計畫就直接寫」。這算錯，因為 W1 要的決定是「先計畫」。
- 0 組沒有 dry run，它的審查指令會因為找不到 `claude`、`codex` 而失敗；評分只看它有沒有要開。
- 只有一個小專案、每格 1 次，不能推到大型專案。
