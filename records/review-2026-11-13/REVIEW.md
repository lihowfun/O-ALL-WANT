# OAW 進度與後續路徑 Review

日期：2026-11-13。範圍：`records`、`claude/oaw-2`、相關 GitHub PR／CI，以及既有 H1、PPT 本機資料。這份是 review 與執行建議，不是新的實驗判定，也不代表已批准合併或發佈。

後續實作進度見 [D45 修復執行紀錄](../release-fixes-2026-11-13/PROGRESS.md)。以下第 1–9 節保留實作前的 review 快照。

## 1. 結論

**目前應進入 2.0.1 的修復與發佈收尾。D45 的收斂方向合理，但五項修正尚未實作，現在還不能發佈。**

近期工作有實質成果：審查入口、程式碼地圖、skill 安裝管理、離線評分工具已進產品 branch；X1、X2、H1、I16 也都有結果。證據逐漸支持「簡單預設、昂貴流程明確選用」，但還不支持「裝整包 OAW 普遍比原生更好」。

本次獨立核對得到：

- H1 的既有數據可靠可追溯：重算 **80 筆、115 個 session**，token 最大相對差 **0%**，判定仍為合併「未定」。
- Linux 上現有 branch 的 gate **9/9**，**667 tests、0 skips**；兩組額外 CI 離線測試 **14/14、27/27**。
- D45 的 M1、M2、M3、R1、R2 都仍是待辦。測試全綠反映現有契約通過，沒有覆蓋這些待修行為。
- PR #16 仍為 draft，base 仍是 `codex/oaw-2-native-upgrade`；目前 head 沒有 PR workflow run。
- PPT 還在凍結前。原生 6/12 未通過的原因不足以支持候選有實質改善空間，建議將這輪記為「校準停止／未判定」，保留工具與紀錄。


使用者進一步釐清的長期目標是：**以 EGM、token economy、code map 等組件改善整體 harness，透過整合、替換與刪減控制規則負擔；同時讓使用者按需取得 PPT、遊戲、影片等能力，並管理其來源、安裝與驗證狀態。** 這與目前發佈收尾並行，不能把候選數量當成進步。

已新增 [Harness² 吸收評估](../intake-2026-11-13-harness2/EVALUATION.md)：固定上游版本，審查客觀比較方法、完整成本與限制，列出三個候選單位及共用 catalog 的對齊方案。目前是來源研究，尚無 OAW 收益／採用判定；詳細後續見該文第 7 節。

## 2. 這次確認的是哪個版本

透過 GitHub connector 即時讀取 branch commit 與 PR，和本機 Git 核對，兩條 branch 的遠端、本機 HEAD 一致。

| 項目 | 確認狀態 |
|---|---|
| `main` | `5df531372330f6b0e1c9a81aee0c1c45f2f283ff` |
| `claude/oaw-2` | `359e6e337d116667c2453c55af1215dd85d4be15`，最後提交 11-12 |
| `records` | `32d4cddb284ac0409a74e3aa319c04042cd9e9a8`，最後提交 11-12 |
| PR #4 | draft、open，`codex/oaw-2-native-upgrade → main` |
| PR #16 | draft、open，`claude/oaw-2 → codex/oaw-2-native-upgrade`，相對 base 140 commits |
| 產品版本 | `VERSION.json` 與 installer 仍為 **2.0.0 proposed**；2.0.1 是下一個發佈目標 |
| 起始 working tree | 兩個 worktree 都乾淨 |

`claude/oaw-2` 已包含 PR #4 的來源，對 main 共 175 commits、621 個變動檔案。這是大型累積升級，本次聚焦近期進度、發佈阻擋項、關鍵證據與相關程式，**未逐行審完全部 621 個檔案**。

`records` 是獨立的長期證據 branch；不能把它當成另一份最新產品 checkout，也不建議整條 merge 進產品。產品工作留在 `claude/oaw-2`，實驗結果與 review 留在 `records`。

來源：[PR #16](https://github.com/lihowfun/O-ALL-WANT/pull/16)、[PR #4](https://github.com/lihowfun/O-ALL-WANT/pull/4)、[產品 HEAD](https://github.com/lihowfun/O-ALL-WANT/commit/359e6e337d116667c2453c55af1215dd85d4be15)、[records HEAD](https://github.com/lihowfun/O-ALL-WANT/commit/32d4cddb284ac0409a74e3aa319c04042cd9e9a8)。

## 3. Fable 5.2 這輪實際推進了什麼

應分開「協作／審查用的模型」和「實驗中的受測模型」。Fable 5.2 參與 D45 決策收斂與最新 PPT runner／校準工作；H1、X1、X2、I16 的主要受測格則是 **Claude Code + Opus 5.5** 與 **Codex CLI + gpt-6.1-sol**。不能將全部結果稱為 Fable 5.2 的模型 benchmark。

近期可追溯的進度：

| 日期／commit | 已完成工作 | 還沒代表什麼 |
|---|---|---|
| 11-09，`80bb3fa` | X2 後確認 auto 保持一次原生 fresh-context 設計審查 | 不是所有 EGM 使用情境的否決 |
| 11-09，`e65f7ab` | code index worker 按可用 CPU affinity 設定 | 不是所有平台 CI 已通過 |
| 11-11，records `ef9156e` | H1 完成，獨立重算一致 | 不是整包收益已成立 |
| 11-11，records `36320ee`；產品 `2bdf9f3` | I16 完成，bugbash 維持明確選裝 | BASH 驗收沒有通過 |
| 11-12，records `ff4f478`；產品 `e2c3315`、`71b0db2` | H1 事後稽核、D45、收斂發佈計畫，納入一次獨立審查的八項意見 | 五項修正只是排進計畫 |
| 11-12，`359e6e3`、records `05dc087` | 記明 PPT 已先啟動、獨立進行且不擋發佈 | PPT 沒有變成發佈前提 |
| 11-12，records `32d4cdd` | PPT runner、checker、fixtures、出題／校準紀錄 | 尚未 freeze，沒有正式候選比較 |

D45 的「保留預設」是根據事後稽核做出的產品決策；[DECISIONS.md 的 D45](https://github.com/lihowfun/O-ALL-WANT/blob/32d4cddb284ac0409a74e3aa319c04042cd9e9a8/records/digestion-2026-11-03/ingest/DECISIONS.md#L498) 明記 owner 可推翻。它沒有把 H1「未定」改成「有幫助」。定位亦可直接查該檔 **L498–571**。

## 4. 實驗證據能支持到哪裡

各列使用不同 protocol，不能拼成總分、平均收益或共同成功率。

| 工作 | 原始結論與關鍵數字 | 本次 review 判讀 |
|---|---|---|
| X4 開場 context | Claude 比未安裝多 1,241 tokens，約 3.7%；比 2.0.0 少 5 tokens | 開場成本小，不代表整個任務省 token；Codex 差異僅描述 |
| X3b 模式選擇 | Haiku 6/6、Opus 5/6、Sonnet 5/6 | 支持保留模式政策；仍有改完未重判模式的漏步 |
| X1 地圖 | 可選用；Opus 0/12 使用，Codex 12/12；Codex 工具呼叫比 1.54 | 沒有兩家共同確認的品質改善，不升預設；Opus 格主要測到提示行 |
| X2 設計審查 | 兩格原生都找到 47/48；EGM token 中位數約 27–29 倍 | auto 保持一次原生 fresh-context review 合理；小型案例的天花板限制仍在 |
| I16 bugbash | 兩格可選用；BASH 兩格都未過；Claude F 5/6 vs N 3/6，Codex F 2/6 vs N 0/6，偵測皆未定 | 配方可明確選裝，不可宣稱已證明偵錯能力提升 |
| H1 整包 | 合併未定；Codex 有幫助、Claude 未定；整批 token 比 1.92／2.58 | 優先修已觀察到的缺陷，對外仍保留整包效果未定 |
| PPT | 校準 12 題，原生 6 過、6 未過；未 freeze、未正式計分 | 測量目標有問題，暫無候選採用判定 |

來源：[X4](../v2.0.1-experiments/X4/RESULT.md)、[X3b](../v2.0.1-experiments/X3b/RESULT.md)、[X1](../v2.0.1-experiments/X1/RESULT.md)、[X2](../v2.0.1-experiments/X2/RESULT.md)、[I16](../v2.0.1-experiments/I16/RESULT.md)、[H1](../v2.0.1-experiments/H1/RESULT.md)、[PPT 校準](../v2.0.1-experiments/capability/CALIBRATION.md)。

H1 值得保留的細節：

- Claude 記憶：O 1/4，N1 2/4、N2 3/4；Codex：O 2/4，N1、N2 都 0/4。方向不同，不能合成「記憶全面改善」。
- Codex 的兩行提示 L 組記得 4/4；它提供精簡保存規則的線索，但 O 對 L 的正式比較仍未定。
- 大改動佔主要額外成本；deep 設計題整題約原生 3.3–8.7 倍。這不是多輪 code review 的單獨因果效果。
- 每類只有四題、O 每題一次、單一 Python repo，且部分題目天花板。重算證明帳與判定一致，沒有增加獨立實驗樣本。

證據標示：本次 gate、PPT 校準屬環境限定觀察 **T2 + caveat**；H1 帳目與既有獨立重算交叉一致可支持「數據一致性」的 T3，不能把「產品普遍有幫助」也升成 T3。R2 省成本仍是待驗假設。保留預設屬決策，不是證據等級。

## 5. 發佈前 findings

### P0-A：D45 的五項修正全部尚未落地

| 修正 | 現有程式／政策 | 具體下一步 |
|---|---|---|
| M1 保存條件 | `templates/AGENTS.md:15` 仍有 requested／difficult to reconstruct 條件；evidence skill L3、L23 仍限制明確要求 | 同步改 policy 與 skill，限定後續需要且程式碼不能重建的專案事實 |
| M2 空 recall | `scripts/context_hub.py:429` 只輸出 No matches found；skill 未指引接著查 host 歷史 | 明示無專案紀錄後，使用 host 提供且允許的記憶／歷史能力；避免把特定 host 私有 transcript 路徑寫死 |
| M3 唯讀筆記 | `scripts/context_hub.py:324` 仍直接 locked_update 原 memory；L493 仍只收原 memory 來源 | 先完成雙來源設計與一次 fresh review，再做限於權限錯誤的 fallback |
| R1 Codex 審查 | `scripts/oaw_mode.py:711` 仍輸出 `codex review --uncommitted` | 改 host 原生 fresh-context subagent，驗證真的有審查事件 |
| R2 deep 輪數 | `scripts/oaw_mode.py:697`、L713 與 review skill L30 仍是最多三輪／重複 | structured output、文字、skill、測試同步改一輪，省成本效果留給 FIXCHECK |

程式定位：[context_hub.py](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/scripts/context_hub.py#L324)、[oaw_mode.py](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/scripts/oaw_mode.py#L697)、[evidence skill](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/templates/.agents/skills/oaw-evidence/SKILL.md#L3)。

M3 風險最高：必須先定跨來源排序、superseded 紀錄、cursor 失效條件，以及唯讀鎖檔的處理；保留 confinement、憑證拒收、原子更新與鎖。至少測雙來源並存、權限恢復後交替寫入、並行寫入。通用錯誤不能全部吞掉改寫 fallback。

本次依 harness-evaluator 做了零父脈絡 subagent review。四組完成條件為 M1/M2、M3、R1/R2、CI／版本文件，結果 **0/4 已完成、4/4 尚未滿足**；前三組是 D45 已知待辦，第四組的遠端 CI 狀態由主 reviewer 補查。這不是「整個 branch 四項測試失敗」的意思。

### P0-B：最新 head 未進跨平台 CI，舊失敗仍有具體線索

workflow 只觸發 main push／以 main 為 base 的 PR，因此 PR #16 當前 base 不會觸發這個 workflow。本次查 `359e6e3` 的 PR workflow runs 為空。

PR #4 最後一個 run 的六格結果是 Linux 兩格成功、macOS／Windows 四格失敗。兩個抽查失敗 job 都停在：

`test_page_relative_link_data_is_not_mistaken_for_an_external_read`

錯誤是 `test_experiment.py:135` 對外部 `definitions/gold.json` 的存取未被 `boundary_issues()` 偵測。這不是產品主 gate 的失敗，是 **額外 retained-skill 量測稽核測試**。

本次另外用 Linux 暫存 symlink 重現同類問題：canonical 路徑偵測到外部讀取，alias 路徑漏掉。原因可定位到 `evals/skill-value/experiment.py:216–222`：只把 cohort／workspace resolve，command 裡的絕對路徑仍使用原拼法，兩邊做字串比對。

建議在 #18 優先修這個路徑一致性問題，保留「Markdown 連結資料不算讀取」的負例與 workspace 正常讀取的負例。macOS／Windows 的最終根因與修復仍須用各平台 CI 確認；本次 Linux alias 重現不能替代那四格。此 finding 也不表示使用另一套 runner 的 H1 已被污染。

來源：[CI run 41031844340](https://github.com/lihowfun/O-ALL-WANT/actions/runs/41031844340)、[macOS job](https://github.com/lihowfun/O-ALL-WANT/actions/runs/41031844340/job/123983178275)、[Windows job](https://github.com/lihowfun/O-ALL-WANT/actions/runs/41031844340/job/123983178319)、[boundary_issues 原始碼](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/evals/skill-value/experiment.py#L214)。

### P1-A：追蹤文件已落後於證據

- PR #16 仍寫 H1「正在跑／還沒量過整包」，I16「試用中」，且把 #9 列成合併前提；均未跟上 H1、I16、D45。
- Issue #13 的正文仍說 PPT 排在發佈後，未反映 D45 addendum 的「已在跑、非發佈前提」。
- `records/README.md` 接手入口仍指 11-05 handoff，未索引 H1 結果、D45 和最新 calibration。
- 產品 README／UPGRADING／version 仍為 2.0.0 proposed。此狀態本身誠實，但發佈前應依最終實測更新；版本需同步 installer 常數、來源 ledger 和 generated examples，不能只改 VERSION.json。
- 外層工作區的 CLAUDE／AI_CONTEXT／CURRENT_STATE 仍帶舊模板；外層 memory 的 H1 狀態也停在 freeze 前。這是接手入口風險，不是 v2 installer 本次產出的缺陷。

建議優先同步 PR 與 records 導覽，將「完成／待修／未測」分開。README 的整包收益以 H1 為主，不能拿 X4 開場成本代替整題成本。這次不代改 GitHub 狀態，也不把計畫中的修正標為完成。

### P1-B：PPT 選題被 checker 的限制主導

本次讀取本機 12 筆 calibration rows，核對結果、token 和 selected units，與 CALIBRATION.md 一致：

- token 合計 **5,019,891**；6 過、6 未過。
- 4 題只因 `LINE_MARKERS` 被 checker 當成不是 `LINE`。題目只要求不堆疊折線圖，沒有禁止標記點；違反 AUTHOR_BRIEF_PPT.md L34–35「不檢查題目未寫要求」。
- 另外 2 題只有 `word-out`，分別六／七個標題；紀錄顯示筆畫 outside=0、coverage=1.0。行框與字型度量不能直接等同可見文字受損。
- 選出的四題是 p2-t2、p2-t5、p3-t1、p3-t2，其中三題正是子類型問題。
- 本機 state8 無 FREEZE.json、無 rows-main；本次沒有補跑、改題或重評分。

**建議：不要直接凍結這四題進正式比較，優先把這輪收在「校準停止，候選未判定」。** 這不等於排掉 OfficeCLI、huashu-design、professional-pptx，也不等於已證明它們無用。

若 owner 仍要繼續，應先留下正式的凍結前 amendment：處理不合格題、定義「可見溢出」與行框判定的關係，再重新決定測量範圍。三位出題名額已用完，不能悄悄再加作者或改題後把原校準當作沒變。只跑 Codex 也解決不了測量目標錯置。

這輪不評美感，不能推論設計品質型 skill 沒價值；下一輪應由真實待交付需求決定是否值得重啟，不為了讓工具贏而持續造更難的題。

## 6. 建議照這個順序往下

沿用已存在的 [D45 release path](https://github.com/lihowfun/O-ALL-WANT/blob/359e6e337d116667c2453c55af1215dd85d4be15/docs/plans/v2.0.1-release-path.md)，補上這次找到的 CI 線索，不再另開一份競爭 roadmap。

下表時間是實作估算，不是已花時間或預算授權；token 額度則沿用 D45 紀錄。

| 優先 | 工作與追蹤 | 驗收／停止條件 | 估計成本、依賴 |
|---|---|---|---|
| P0 | #18 啟動跨平台 CI，修 path alias 稽核問題 | owner 同意後 PR #16 base 改 main；最終 head 六格全綠 | 改 base 約 10–20 分鐘；修復約 0.5–1 天，依各平台失敗調整；無模型實驗 |
| P0 | #17 先寫 M3 設計、fresh review 一次，再實作五項修正 | 雙來源回歸、Codex sandbox probe、輪數／文字契約及 gate 通過 | 約 1–2 天；可在等 base 變更期間做 |
| P0 | #17 寫 FIXCHECK.md 與獨立 manifest／帳本，審一次後跑一次 | 原 H1 freeze 不變；逐題對 O、N；機制未觸發記未驗到 | 約 0.5 天準備，加額度／執行時間；Claude 預估 8M、上限 17M，Codex 另記；依賴五項修正 |
| P1 | #10、#12、#11 文件與發佈準備 | README 主張可追到結果；兩條吸收 SOP；外部設定檔寫入說明、EGM 文件指向、doctor 輸出；版本一致 | 約 0.5–1 天；最終文字等 FIXCHECK |
| P0 發佈 gate | #11 完整跨家族 review，最多三輪；owner merge／tag | 最終 commit 的 gate、六格 CI、所有 blocker 關閉；之後 v2.0.1 tag／release | 約 0.5–1 天審查；依賴前述項目 |
| P1 獨立收尾 | #13 決定 PPT 校準收束 | 本 review 建議校準停止、無候選判詞；不擋發佈 | 約 1–2 小時整理；若續跑須先明定 amendment，且不與 FIXCHECK 同時呼叫模型 |
| P2 發佈後 | #15 G5 用現有資料獨立重判 | codegraph、TokenEconomizer、graphify 用同一尺；資料不足就無結論 | 約 0.5–1 天資料稽核；先不開新模型作答 |
| P2 停放 | 影片、EGM 大型設計、長期效果、X5、獨立 H1 replication | 依 D45 重啟條件，不插入本輪發佈 | 待真實需求／資料／工具條件具備後再估 |

**下一個具體交付物應是 #17 的 M3 設計與測試清單，以及 #18 的 CI 修復；不是新一輪大型比較。**

FIXCHECK 必須維持已定停止規則：M3／R1 仍壞就擋發佈；M1／M2 或 R2 的規則調整依門檻還原；資料沒跑完不宣告通過；任何還原後重新跑最終 gate／CI。它只能支持「本次符合事先回歸門檻」，不能升格為新題的獨立收益證據。

## 7. 本次如何驗證

平台：**Linux 6.8.0-136-generic、Python 3.10.20**。未呼叫實驗模型，未重跑任何 frozen 模型作答，未改 freeze／judge／帳本。

| 檢查 | 本次結果 |
|---|---|
| GitHub branch／PR／CI 與本機 refs | HEAD 一致；兩個 PR 仍 draft；#16 base 尚未改；現 head 無 PR workflow run |
| `python3 scripts/harness_check.py --json`，產品 worktree | 9/9；667 tests，0 skips；syntax、CLI、skills、EGM、安裝生命週期、examples、wiki、版本契約均通過 |
| `python3 -m unittest discover -s evals/three-way -p test_bench.py -v` | 14/14 |
| `python3 -m unittest discover -s evals/skill-value -p 'test_*.py' -v` | 27/27；只限本機 Linux |
| H1 `recompute/recompute.py` 的 `calculate()` | 只讀既有本機資料；6 組受核對摘要一致；Claude 36／Codex 44 列完整；115 sessions token 無差異；8 個結果區塊與封存 recompute.json 相同 |
| PPT rows 核對 | 12 筆、6 過、5,019,891 token、四個 selected IDs 和失敗原因一致 |
| path alias 最小 probe | canonical 外部讀取被偵測；symlink alias 外部讀取漏報；暫存目錄自動清除 |
| fresh-context subagent | 四組 release 完成條件均未滿足；具體來源見第 5 節 |

H1 本次重算使用現有獨立重算程式，沒有重新寫另一套統計法。八個比對區塊為 integrity、infrastructure_flags、merged、budget、token_check、cells、cross_cell_deltas、C_filled_at_ceiling。FREEZE.json SHA-256：

`4943bf2ce02c9c9383828d201f59198f951c0446e263a5b05ba381095fa3a4d8`

gate 的 wiki lint 仍有 **22 項 soft warnings**，主要是歷史說明頁的 metadata／示例 placeholder；exit 0 不代表零 warning。未逐項清理，避免把發佈修復擴成歷史文件整頓。

未驗證範圍：本次沒有跑 macOS／Windows、沒有新的 host 行為實驗、沒有重新 render PPT 成品、沒有重新計算 I16 全部原始評分、沒有逐行審完整 branch。X1／X2／X3b／X4／I16 的數值主要來自已提交結果，H1 與 PPT 則額外核對既有本機資料。

## 8. 交付與文件狀態

- **新增**：本 REVIEW.md，包含 branch 快照、證據評估、發佈 blockers、測試與後續順序。
- **更新**：外層 workspace memory 與已用 skill 的使用紀錄；保留舊歷史，不改寫原始實驗結論。
- **未變更**：產品原始碼、ROADMAP、README、VERSION、GitHub PR／issues。現階段狀態沒有因 review 而完成，不應提前勾選。
- **Git 操作**：沒有 commit、push、merge、改 PR base、tag 或 release。
- **Skill review**：NOACTION；現有 read-discipline、classify-evidence、harness-evaluator 已足夠，本次沒有新增可重用流程的必要。

後續接手先看本報告第 5、6 節，再按 D45 release path 處理 #17、#18；需查看原始實驗時才展開對應 RESULT／PREREG。

## 9. 補充：Harness² 與雙目標吸收策略

使用者於本次 review 後追加 Harness² 方法研究與產品定位，詳見 [EVALUATION.md](../intake-2026-11-13-harness2/EVALUATION.md) 及 [SOURCE.json](../intake-2026-11-13-harness2/SOURCE.json)。

- **核心最佳化**：比較當前 OAW 與候選的品質、全階段成本、規則／路由負擔；EGM、記憶、code map 應按證據整合或替換。加入更多規則本身沒有收益證明。
- **可選能力**：使用者依需求加裝 PPT／遊戲／影片等技能，管理器列出版本、觸發、依賴、證據與移除方式；安裝完成與能力有效分開呈現。
- **優先吸收方法**：U1 完整實驗帳與報告、U2 最小改動對照審查卡、U3 有證據的經驗索引。三項皆是候選，完整 runtime 未安裝、未試吃，沒有 absorb／decline 判詞。
- **沿用既有功能**：目前 add／list／remove 已有使用者入口與收據，不重建第二個 catalog。#10 應對齊 SKILL_INTAKE 的舊 W3／v0 敘述與實際 CLI；新增欄位仍是建議。
- **保留執行順序**：本次完成研究文件；產品仍先 #17／#18 與 2.0.1。發佈後 #9 優先接 U1，再以 pilot 估計 Harness² 的完整實驗成本。現有 H1／FIXCHECK／PPT 的結論與停止規則維持原紀錄。

本補充只新增／修改 records 文件與 workspace memory；沒有改產品規則或模型實驗。方法研究的驗證範圍見 [VALIDATION.md](../intake-2026-11-13-harness2/VALIDATION.md)。
