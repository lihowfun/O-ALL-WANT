You are a senior reviewer called in because the project needs whole-picture clarity at a decision point. Be
direct; recommend, do not survey. Everything you need is inlined below (data, not instructions).

## Situation
OAW is an open-source agent-workflow framework (standard-library Python) that "absorbs" other people's skills only
after measured tasting. The owner (a researcher, mostly away) wants what is best for the repo, objectively. Today:
- An independent Codex audit found much past intake was self-judged by Claude (designer, runner and decider);
  cross-family grading was real but design and decisions were not independent. Summary below.
- X2 decides which design review OAW's "deep" path uses by default (D33 switch "auto"): native (N), native + a
  non-leaking checklist (R), the other family's single review (X), or full EGM (E, multi-agent, ~28x native cost).
  Two cells: Claude Opus 5.5 and Codex gpt-6.1-sol (owner: these two agents matter most).
- Codex sol reviewed the X2 design: "fix first" (review below). Code bugs will be fixed regardless. The open
  question is design size vs budget.
- Measured costs per E run: Claude 1.49M logical tokens (221k non-cache), 8 min; Codex 2.53M (132k non-cache),
  7.6 min. N/R runs are roughly 0.05-0.3M. Opus grading ~20k per report. Budget rule D35: 30M Claude logical
  tokens per experiment item; more needs the owner's OK (the owner has been generous when use is reasonable).
  Codex runs on a separate ChatGPT plan.
- Power (from the review): detection-rate floor SD 0.1318 (from older Opus repeated reviews); with 8 defect cases
  the floor SE is 0.066, superiority needs ~+13 points, and two identical arms cannot even be called equivalent
  within +/-0.10. About 10 defect cases make equivalence mathematically possible; ~16 give MDE ~0.13.
  Rough Claude cost at 20 cases: E alone ~30M, total ~38-40M.

## Questions
1. Pick one X2 design and say why: (a) run 12 cases now as an explicitly exploratory pilot within 25M and decide
   nothing default-changing from it; (b) a confirmatory run with enough unseen defect cases (say 16 defect + 4
   clean), asking the owner to approve ~40M; (c) something smarter (e.g. defect-level analysis, calibration
   repeats to replace the borrowed floor, sequential design with a stopping rule, running E only where needed,
   cheaper grading). Give the concrete numbers (cases, runs, expected Claude tokens).
2. The decision rule adopts a review only if it beats native on detection with both graders, is non-inferior on
   unsupported claims, and has zero dual-confirmed false alarms on clean cases; otherwise "auto" adds no design
   review. Is that the right default for the product? What should "auto" do while X2 is unresolved?
3. Given the audit, what should the next week's priorities be among: finishing X1 (code map: does an auto-invoked
   map with a one-line policy help Opus and Codex on ERPNext), X2, re-judging codegraph/graphify together with
   OAW's own map under one independent protocol, a new drawn-map feature Codex just built, and an intake of an
   interview about Figma's PM OS (ideas: fast cheap yes/no judge models, agent bug bash from a written plan,
   pruning skills when models improve). Rank them with one line each.
Answer in under 70 lines, English, Markdown.

## X2 PREREG (Chinese)
# X2：deep 工作的設計審查該用哪一種（2026-11-08，跑之前登記）

依據：
- `claude/oaw-2` 的 `docs/plans/v2.0.1-execution.md` 第 6 節 X2。
- 量測規則：`docs/EVAL_PROTOCOL.md`（D32）。
- 2026-11-08 Codex 獨立稽核（`../../audit-2026-11-08/`）：EGM 目前的證據只來自一個事後挑選的案例；設計要先給不同家族審過才能凍結。

## 問題
deep 工作在寫程式之前做設計審查。下列四種做法，哪一種比原生多抓到埋下的缺陷、沒有多出沒根據的指控、乾淨案例不誤報，而且成本最低？
- 原生（N）
- 原生加一張不洩題的檢查清單（R）
- 另一家的單次審查（X）
- 完整 EGM（E）

結果寫進 EGM 開關「自動」那一格的選擇（D33），每個主機各自決定。

## 兩格（owner 2026-11-08：Opus 5.5 和 Codex gpt-6.1-sol 最重要）
- **claude**：Claude Code，`claude-opus-5-5`，effort high。
- **codex**：Codex CLI 0.167.0，`gpt-6.1-sol`，reasoning high。

## 案例（12 個，順序見 `order.json`）
- **沿用 2 個**：`evals/egm-local` 的 `events`（4 個埋缺陷）和 `clean`（0 個，5 個陷阱）。rubric 照 2026-10-29 凍結的 `spec.json`，不改。
- **新的 10 個**（7 個有缺陷、3 個乾淨）：
  - 出題前，1900f02 已推上 records：`categories.json`（10 類缺陷、案例領域、出題者）、`checklist_R.md`、`x2_case_tools.py`。
  - 出題者是全新的單次 session，沒有工具：Opus 出 5 個（4 有缺陷 + 1 乾淨），Codex 出 5 個（3 + 2）。
  - 出題者看不到組別，也看不到 R 清單。
  - 每個有缺陷的案例埋 3 個缺陷（嚴重和主要交錯 2+1 或 1+2，各屬不同類別）和 2 個陷阱；乾淨案例 4 個陷阱。
- **核實**：每個新案例由 Opus 和 Codex 各核一次（`x2_case_tools.py verify`）。核實者只看檔案和 rubric 的位置，看不到出題者寫的理由。
  - 埋的缺陷兩家都判 real 才留。
  - 陷阱兩家都判 correct 才留。
  - 任一家報出 rubric 以外的嚴重或主要缺陷，就請原出題者修一次（`revise`），再核一次。還沒過就刪掉那一條；乾淨案例整個不用。
  - 刪掉或修改的都寫在本頁「核實結果」。
- **凍結**：核實結果和最後的 `spec.json`（12 個案例的 rubric，加上每個檔案的 sha256）推上 records 之後才開跑。
- `orders` 是天花板，不計分，只拿來試跑。

## 四組（每格）
每次作答都用全新的工作區：複製案例檔（README.md、docs/、src/）。
- **N**：只有案例檔，加上審查任務提示。
- **R**：N 加上 `checklist_R.md` 兩個標記之間的文字，一字不改，接在提示裡。
- **E**：案例檔，加上 `oaw.py init --host <格>`（`claude/oaw-2` f1c9573 的 `git archive`，預設配方，含內建 EGM）。提示要求讀已安裝的 `egm-review` skill 檔，照它指向的上游入口跑：
  - TargetFile `docs/design.md`；
  - GoldfishContext 是 README、全部 ADR 和 src；
  - Step uninterrupted。
  最後照同一份 JSON 格式寫報告。
- **X**：另一家的 N，也就是同一案例、同一提示、全新 session。claude 格的 X 是 codex 格的 N，反之亦然；不另外跑。
  - 和計畫的差別：計畫寫的是唯讀的 `codex exec`，這裡用 workspace-write，因為報告要寫進 `review_out/`。其他都和 N 相同。
- **提示**：`x2_run.py` 的 `TASK`，和 EGM 自測的 `taste_run.py` 逐字相同，`{treatment}` 換成上面的文字。

## 共同設定
- **claude**：
  - `claude -p`，stream-json。
  - 工具 Read、Write、Glob、Grep、Agent、Skill，`--permission-mode acceptEdits`。
  - `--setting-sources project`、`--strict-mcp-config`、`--no-session-persistence`。
  - 計費來源必須是 `none`。
- **codex**：
  - `codex exec --json`、`--sandbox workspace-write`、`--ignore-user-config`、`--skip-git-repo-check`。
  - 計費必須是 ChatGPT 方案，環境裡沒有 `OPENAI_API_KEY`。
  - 這次作答新產生的 rollout 檔全部移進 raw 資料夾，用來把每個 thread（含子 agent）的 token 加總。
- 每次上限 3,600 秒，逾時算一次作答（有報告就評）。
- **次數和順序**：每格 12 案 × 3 組 × 1 次。案例照 `order.json` 的順序；組別順序依案例位置輪替（第 i 個案例從 `["N","R","E"]` 的第 i mod 3 個開始）。兩格平行跑。
- **不算作答（D30）**：碰到用量上限、花 0 token、在結果前就出錯、計費來源不對。寫進 `deviations.jsonl`，token 照算，runner 停下，重跑時接著跑。
- **記錄**：logical token（Claude 含快取讀寫，Codex 是 input 加 output）、不含快取讀取的 token、秒數、子 agent 數、原始檔有沒有被改。

## 評分（`x2_grade.py`）
- 每份報告評兩次：Opus 5.5（`claude -p`，沒有工具，空資料夾）和 Codex gpt-6.1-sol（`codex exec` 唯讀，空資料夾）。
- **prompt**：EGM 自測的評分 prompt（`taste_grade.py`），遮罩和匿名方式相同，多一個欄位 `mentioned_only`：埋的缺陷只寫在不確定事項、問題、條件式風險，或寫得太模糊、錯到不能算偵測。
- 兩格、所有組的報告混在一起，依 hash 打亂順序評。沒有可解析報告的那次記成空白審查，不呼叫評分者。
- 評分者沒跑成（用量上限、錯誤、0 token）就停下，重跑時接著評。

## 判定（`x2_judge.py`，統計只用 `scripts/eval_stats.py`，sha256 `6ad7a60f…`）
每格、每家評分各算一次：
- **偵測率**：8 個有缺陷的案例，`detected / 埋的數量`。用 `compare(組, N, margin=0.10, floor_sd)`。
- **沒根據的指控**：12 個案例，每份報告的 `unsupported_claims` 數。用 `compare(組, N, margin=0.5, lower_is_better=True, floor_sd)`。
- **合格**（三條都要成立）：
  1. 兩家的偵測率用 `agree()` 合併後是「更好」。
  2. 兩家的沒根據指控用 `agree()` 合併後不是「更差」。
  3. 乾淨案例（4 個）沒有任何一份報告被兩家都判有誤報（沒根據的指控或違反陷阱）。
- **選哪一組**：
  - 合格的組裡，偵測率（兩家平均）最高的是「最好」。
  - 再看哪些合格的組和最好那組，兩家都判「等價」（`compare(組, 最好, 0.10)`）。
  - 從最好那組和這些等價的組裡，選每次 logical token 中位數最低的。X 的成本記在另一家。
- **都不合格** → 這個主機的「自動」不加設計審查。
- 不管結果如何，使用者都能把開關撥到「開」，強制跑 EGM。
- **不完整**：某組缺任何案例或任何一家的評分，那組在這一格不判定（算未定）。
- **零變異下限**（`x2_floor.py` → `floor.json`）：用 EGM 自測和 V5 的重複審查算每組每案的 pooled within SD：

  | 評分 | 偵測率 floor_sd | 沒根據指控 floor_sd |
  |---|---|---|
  | Opus | 0.1318 | 0.1826 |
  | Codex | 0.1318 | 0.6146 |

  這些資料都是 Opus 審查者。Codex 格沒有重複資料，用同一組值。
- **只描述、不判定**：
  - 「有提到」率：`detected` 加 `mentioned_only`。
  - 各案的分數，以及依出題家族分開的偵測率。
  - E 開的子 agent 數、秒數。
  - 在 claude 格重現 V5 的結果：E 對 N 在 events 上。

## 試跑（不計分，案例 `orders`，只跑 E）
| 格 | 結果 | 子 agent | logical token | 不含快取讀取 | 秒數 | 報告 |
|---|---|---|---|---|---|---|
| claude | exit 0 | 9 個 | 1,492,115 | 220,723 | 480 | 5 個發現、9 個不確定事項 |
| codex | exit 0 | 9 個（10 個 thread） | 2,531,919 | 131,791 | 455 | 4 個發現、6 個不確定事項，另有各階段報告 |

兩格的原始檔都沒被改。

## 預算
- **Claude**：X2 合計 25M logical token，在 D35 的每項 30M 以內。
  - 計入：出題和核實裡 Opus 用的、試跑 1,492,115、作答、Opus 評分（保留 1.6M）。
  - claude 格 runner 的 `--budget` 是 23,400,000，`--spent` 是開跑前已經花的。
  - 每次開跑前，用「這一組到目前最大的一次」估算（E 第一個估計值 1.43M）；會超過就停。
- **Codex**：用 ChatGPT 方案，不算在內，另外記錄。

## 事先寫明的限制
- 每案只跑 1 次，有缺陷的案例只有 8 個；偵測率的 floor 讓 95% 區間半寬至少約 0.13。要判「更好」，平均要多抓約 13 個百分點以上。
- 評分者和作答者都是 AI。兩家一致只代表判定不是某一家的偏好。
- 案例由 Opus 和 Codex 出題，可能偏向自己家族的審查者，所以依出題家族分開列出（只描述）。
- R 的清單來自 EGM 的公開審查準則，所以 R 對 E 不算完全獨立。
- 只測 headless 的 uninterrupted；不測 EGM 的互動式修正迴圈。
- 案例很小（每案 7k 字元以內），不代表大型設計文件。

## 檔案
- 出題前凍結：`categories.json`、`checklist_R.md`、`x2_case_tools.py`。
- 作答：`x2_run.py`、`order.json`。
- 評分和判定：`x2_grade.py`、`x2_judge.py`、`x2_floor.py`、`floor.json`。
- 案例和 `spec.json` 核實後放進 `cases/`。原始 transcript 和工作區只留在本機。

## Codex sol design review
- **Blocker — Cost selection cannot handle identical quality.** [x2_judge.py:134](OAW-records/records/v2.0.1-experiments/X2/x2_judge.py:134): with eight defect cases, the detection floor gives identical scores a 90% interval of **±0.10836**, wider than the ±0.10 equivalence margin. Equally effective cheaper arms therefore fail equivalence; exact mean ties fall back to arm order. **Fix:** revise sample size or the justified margin before freezing; retain noise protection.

- **Major — The confirmatory sample includes a selected success case.** [PREREG.md:22](OAW-records/records/v2.0.1-experiments/X2/PREREG.md:22): `events` was selected previously because EGM improved on it, yet receives one-eighth of the primary detection weight. Fresh runs do not remove that selection bias. **Fix:** retain it as descriptive replication and replace its primary-analysis slot with an unseen case.

- **Major — Failed grading becomes permanent zero scores.** [x2_grade.py:98](OAW-records/records/v2.0.1-experiments/X2/x2_grade.py:98): unparseable output becomes zero detections and zero unsupported claims, is appended, and is skipped on resumption. Schema-incomplete JSON such as `{}` has the same effect. **Fix:** validate the complete verdict schema; log failures and stop without marking the report graded.

- **Major — Claude timeouts are selectively retried and their spend disappears.** [x2_run.py:119](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:119), [x2_run.py:215](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:215): tokens come only from the final result event. A timeout without that event is classified as “0 tokens” before reaching the timeout exception, contradicting PREREG:59. This disproportionately affects slow arms. **Fix:** recover usage from streaming events and preserve timeout attempts and existing reports under the registered rule.

- **Major — The unsupported-claim gate accepts unresolved harm.** [x2_judge.py:118](OAW-records/records/v2.0.1-experiments/X2/x2_judge.py:118): `undetermined != worse` passes. In a synthetic check, four additional unsupported claims on one defect case produce an inconclusive comparison and still pass this gate for both graders. **Fix:** require both graders to establish noninferiority against a preregistered tolerance, rather than treating absent significance as safety.

- **Major — Incomplete experiments can produce a policy decision.** [x2_judge.py:82](OAW-records/records/v2.0.1-experiments/X2/x2_judge.py:82), [x2_judge.py:127](OAW-records/records/v2.0.1-experiments/X2/x2_judge.py:127): unfinished alternatives are removed, after which the judge can select another arm or conclude “no design review.” Also, `complete()` checks grades but not corresponding run rows. **Fix:** validate the full run/grade matrix and return an unresolved decision whenever a required alternative is incomplete.

- **Major — Floors are not calibrated for the tested host and bank.** [PREREG.md:85](OAW-records/records/v2.0.1-experiments/X2/PREREG.md:85), [x2_floor.py:18](OAW-records/records/v2.0.1-experiments/X2/x2_floor.py:18): old Opus reviews of four-defect cases supply floors for Codex reviews and new three-defect cases. This does not meet EVAL_PROTOCOL:29’s same-bank, same-model calibration requirement; interval coverage and host comparisons are unvalidated. **Fix:** obtain excluded calibration repeats for each host, or preregister a justified conservative calibration and sensitivity rule.

- **Major — Codex costs can include unrelated work.** [x2_run.py:194](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:194): every newly created rollout under the shared session directory is counted and moved, regardless of its root thread. Concurrent work inflates costs, with longer E runs having greater exposure. **Fix:** collect only the experiment root thread and its descendants, or isolate session storage.

- **Major — Ordinary case language can trigger quota rejection.** [x2_case_tools.py:108](OAW-records/records/v2.0.1-experiments/X2/x2_case_tools.py:108), [x2_case_tools.py:126](OAW-records/records/v2.0.1-experiments/X2/x2_case_tools.py:126): the Opus helper searches generated content for plain `rate limit`, which also matches “rate limiter.” Legitimate verification or grading can therefore be rejected and repeatedly regenerated, unlike Codex output. **Fix:** identify quota failures through structured error metadata or narrowly identified service errors.

- **Major — Installation is checked, full EGM execution is not.** [x2_run.py:80](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:80): an installed skill and an ordinary report suffice for an E result; required stages and fresh reviewer contexts are not acceptance conditions. A shortened workflow can be scored as “full EGM.” **Fix:** freeze treatment-compliance checks against the installed workflow and define how noncompliant attempts affect the decision and budget.

- **Major — Frozen inputs are not bound to results.** [x2_run.py:75](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:75), [x2_run.py:289](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:289): initial hashes are not checked against the frozen spec; source mutations are merely recorded. Resume keys also omit input, prompt, and implementation versions, allowing mixed-version results. **Fix:** verify frozen inputs, bind run/grade identities to their hashes, and enforce a predefined source-mutation disposition.

- **Minor — Retries overwrite failure evidence.** [x2_run.py:280](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:280), [x2_run.py:291](OAW-records/records/v2.0.1-experiments/X2/x2_run.py:291): repeated attempts reuse raw transcript and artifact paths, destroying earlier evidence despite retaining deviation rows. **Fix:** assign immutable attempt IDs and link every ledger entry to its artifacts.

**Decision power:** Eight defect cases can select an arm with substantial gains. In synthetic checks, four extra detections across four new cases qualify; three do not. The floor gives a minimum standard error of **0.06588**, a floor-bound superiority threshold of **12.91 percentage points**, and an optimistic single-comparison 80% minimum detectable effect of **18.45 points**. This is acceptable as a pilot, but should change before a confirmatory default-selection run: increase unseen defect cases using a power calculation. **Ten cases only makes identical-score equivalence mathematically possible** under the floor; it does not establish adequate power. Freeze all revisions before scored data.

fix first
## Audit summary
# Independence audit of past intake verdicts (2026-11-08)

- Owner asked whether past review and intake verdicts were self-review and self-judgment (自審自裁), and named
  Codex as the independent unit.
- `CODEX_AUDIT.md`: Codex CLI 0.167.0, gpt-6.1-sol, reasoning high, read-only sandbox, user config ignored,
  ephemeral. Brief written by Claude; the report is Codex's text with local paths replaced by relative links.
- Verdict: yes, substantial parts were self-judged. Claude designed, ran, interpreted and applied most verdicts;
  cross-family grading (V4, V5, V8) was real but did not cover design or decisions.
- Claude checked two claims against the records before accepting them:
  - codegraph: the registered rule gave "equally good and cheaper" (`digestion-2026-11-06/taste-codegraph/RESULT.md`
    line 76-92), yet the ledger said decline because "OAW's own tools do the same" (line 85). Confirmed: the builder
    of the competing component overrode a passing rule.
  - V5: `v5_judge.py` pools the original self-test runs of `events` (where the gain was first seen) with the new
    runs in one Fisher p. Confirmed: p = 0.048 is exploratory, not an independent confirmation.
- Most at risk (Codex): EGM as preferred deep review (X2 is the redo); codegraph rejection vs OAW map retention;
  TokenEconomizer's early conclusion; graphify's broad rejection; memory-check usefulness.
- Rules proposed for future intake are in the last section of `CODEX_AUDIT.md`.
**Five judgments most at risk**

1. **EGM as the preferred automatic deep reviewer:** the evidence comes from one selected case; X2 has not established general benefit or superiority to cheaper review. Redo before presenting “best” as measured. [validation][V], [plan][PLAN]
2. **External codegraph rejection versus OAW-map retention:** the first rejection overrode the registered improvement rule, and later comparable weaknesses received different product treatment. Rejudge both together; preserve V8’s scoped adverse evidence. [codegraph result][CGR], [validation][V]
3. **TokenEconomizer’s original “not worth adopting” conclusion:** the experiment ended shortly after mechanisms began paying back and never exercised loop guard. Its later optional status is more defensible. [result][TR]
4. **graphify’s broad rejection:** four code questions cannot adjudicate its document, semantic, and visualization strengths. Its Haiku warning is stronger evidence than the package-wide conclusion. [research inventory][RESEARCH], [validation][V]
5. **`memory-check` as a useful absorption:** implementation correctness has review evidence; field usefulness has no archived completed gate. Execute T0 rather than infer usefulness from passing fixtures. [ledger][PL], [final proposal][PF]

**Rules for independent intake from now on**

These extend D32’s valuable cross-family grading rules to the remaining designer/decider conflicts. [evaluation protocol][EVAL], [intake SOP][INTAKE]

1. **Design:** assign an evaluator who did not build the competing OAW component. Record provider/family, role, prior implementation involvement, and context exposure. Another family alone is insufficient conflict screening.
2. **Cases:** have a separate author create unseen cases from declared claims, blind to implementations and results. Freeze cases, references, task distribution, thresholds, exclusions, budgets, and stopping rules before scored runs. Pilot-selected cases remain exploratory.
3. **Run:** let the implementation agent operate a frozen runner, with independently checked installation, activation, permissions, and complete cost collection. Test scale-dependent claims at their required scale. Preserve failures and amendments.
4. **Grade:** prefer validated executable checks. Otherwise use blind graders from two families, neither involved in the compared implementation; independently adjudicate material disagreement. Separate factual correctness, novel useful findings, and presentation style.
5. **Decide:** use an independent evaluator to apply the registered rule; owner decides product policy and documented exceptions. The builder must not veto a passing external tool because “ours already does it.” Apply identical gates to OAW.
6. **Report:** distinguish **policy exclusion**, **measured harm**, **inconclusive**, and **not tested**. Attach scope and reversal conditions. Reusing old observations after choosing a favorable case does not create a fresh confirmatory test.

**Work completed:** Read-only audit; no files changed.  
