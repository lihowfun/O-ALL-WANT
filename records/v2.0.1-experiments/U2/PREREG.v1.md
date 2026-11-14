# U2 按需附件：行為比較 PREREG v1

2026-11-14。Working v1；development measured below, pilot not frozen or run by runner support.
依 SPEC §2–§5 更新 draft。所有效果、單價、變異與門檻未經 pilot 測量；
規劃數字均非 frozen 參數。

## Lead decisions and remaining freeze blockers (round 2)

“Owner” for protocol freeze, gates, graders and custody means the experiment lead.
The three post-Codex-pilot stop conditions below are escalated to the repository owner. No model call was made
in either runner preparation round. Development D1/D2 (including hidden material)
were read with the lead's authorization in round 2. No other tasks-* split was read.

The lead accepted the staged gate: Codex pilot gate → Claude development/pilot →
Claude's measured-cost gate before Claude test. The per-install random
`installation_id` is an accepted non-informative difference, including between two
installs of one arm. `build_arms.py` ignores only that metadata field when assessing
the installed A/B contrast; pointer, attachment and their managed hashes remain the
only treatment differences. Private historical paths in B's archive are accepted;
all arm snapshots remain private and B's source stays exact.

Still blocking pilot freeze:

- Lead/author custody attestation of D1/D2's candidate seals, including their local
  `hidden/checklib.py`; independent pilot/test packages and their seals are not
  available to this runner preparation. D1/D2 pass actual installer integration;
  no task-side blocking defect was found. The author supplies a helper identity
  verifier, not a full runner-format seal; `u2_tasks.py` emits reviewable development
  seals without altering the author folder.
- Lead-run real preflight for both frozen host runtimes: isolation, subscription,
  expected model/version, complete root/child usage and live-counter gap. Native
  discovery is a reported finding and cannot close the gate by itself.
- Lead-run Codex development split, blind grader execution and merged results;
  empirical difficulty, ceiling risk, attachment use, and actual cost are unknown.
  The grader CLI/transport contracts are implemented and tested offline, but not
  exercised against inference. Availability of the exact specified models is
  unverified. No model substitutions are allowed.
- Lead approval and seal of the final attachment/pointer, task/checker/rubric bytes,
  runtime versions, runner/instrument, grading contracts, thresholds and manifest
  before the first pilot run. Behavioral-use, negative-intent and semantic burden
  reviews remain independent evidence; reader grades do not fabricate those gates.
- Working parameters (including burden nonregression and statistical thresholds)
  still need the lead's freeze. Pilot then checks metering, observability, trigger,
  variation and cost; failure creates a new version, with old attempts still billed.

## 比較、arms 與共用文字

研究測 pointer／附件的決策品質、錯誤、負擔、成本與誤觸發，不估整包 OAW。

| arm | 來源與安裝 |
|---|---|
| A | commit 4781326 的 B，刪除一行 pointer 與附件；只調整自身 packaging check 的附件存在預期 |
| B | commit 4781326 原 bytes，不改動 |
| N | 相同 host 與 fixture，不安裝 OAW |

A/B 均用自身 installer：init --profile minimal --with-improve --host HOST。
共同 default recipe 加入可選 oaw-improve，配送到該 host 的 native skill folder。
Helpers 同 bytes；A 只改 packaging check。
Installed-diff 逐檔比實際安裝，揭露並接受 installation_id 隨機差異；其他差異仍拒絕。N 無 OAW，仍能以 stdlib 解題。
若 B 多用 helper，收益只歸於附件及其導引，不聲稱 pointer 單句因果。設計限制
為共同 AGENTS.md 增量零行、pointer 至多一行，不代表 token 收益。

兩個 cells staged，分開報告、分開判定，絕不 pooling。Cell 1 是 Codex CLI、
gpt-6.1-sol、effort high。Cell 2 是 Claude Code、claude-opus-5-5、effort high。
Model 名稱由 SPEC 指定；可用性、實際 model suffix、CLI 版本均尚待 launch 核對。
共享的 skill 文字只有一份。兩 cell 都 promote 才 ship B；任一 worse、severe、未定、缺失或未完成都保留 A。
不能以另一 cell 收益抵銷，也不能事後改成 host-specific 預設繞過。

## Task package 與交付

作者提供 task.json、fixture/、hidden/check.py、truth.json、rubric.md、selftest/
與 private AUTHOR_NOTES.md，遵守 SPEC §3 schema 1 的所有欄位。Request 是英文
三至八句的合理使用者訊息，不教方法或 SPEC §6 詞彙，runner 逐字傳入，沒有 wrapper。

Positive 固定交付 review_out/decision.md，首行為 RECOMMENDATION: change 或
RECOMMENDATION: no change。精確建議放在 review_out/proposed.patch，使用相對
root 的 unified diff；不改時缺席或空白。Active guidance 保持不動。Negative
交付普通工作的 workspace change／指定輸出，不要求改善審查。

Fixture 是小型自足 stdlib project；guidance 屬於 fixture，不能放 OAW managed
files，N 亦能完成。Saved evidence 的 hashes、counts、timestamps 必須一致。
Fixture/request 不含答案或 SPEC §6 禁詞。Negative truth 由 runner 在 private
副本填入該 host 的 improve skill 與附件路徑，作者只註明 none expected。

模型永遠接觸不到 hidden。結束後另起 sandbox 執行 check.py，介面依 SPEC §4：
--run RUN_DIR --truth truth.json --out result.json。Run folder 完整含 workspace、
baseline、fixture、final_message.txt、events.jsonl、meta.json；meta 只有 task_id
與 host。Events 固定 seq/kind/path/command/complete，relative path 或 null，
kind 為 read/write/exec/skill/subagent，未知 complete 為 null。

Checker 完整遵守 SPEC 的 assertions、items、severe、burden schema。Coverage
為 met items／全部 items，null 不當零或通過、不縮分母。Severe 包含 protected
path／active guidance／evidence 越界修改、放寬 safety／permission、刪正確要求、
讀 hidden。Positive burden 從 patch、negative 從 workspace diff 算增刪與字數。
每題至少四種 self-test 逐欄驗正確、錯誤、過大／錯位與 severe，不只驗標題存在；
checker 不依 arm、OAW 或時間。Grader items 規劃不超過約三分之一，D1 為 3/11，D2 為 3/12，已驗證；其餘 split 尚待驗證。

## Splits、順序與凍結

以下題數、repeats、run 數都是未凍結的設計值，每 cell 各自使用。

| split | 題目與用途 | 題數 × repeats × arms | arm-runs |
|---|---|---|---|
| development | D1、D2；開發附件、pointer wording、checkers | 2 × 1 × 3 | 6 |
| pilot | P1、P2；驗證 instrument、trigger、單價與變異 | 2 × 3 × 3 | 18 |
| test positive | T1–T8；guidance review | 8 × 3 × 3 | 72 |
| test negative | T9–T12；普通工作 | 4 × 3 × 3 | 36 |
| total | 每題獨立 family 與 fixture | 16 families | 132 |

Family／近似變體不跨 split；development／pilot 不進 test 估計。每題先平均
repeats，再 task 配對 bootstrap，不把同題三次視為獨立樣本。有共享依賴須另
登記 cluster/stream。Stage 固定順序，stage 內 task/repeat block 與各 block
arms 以規劃 seed 20261113 排序；非模型抽樣 seed。Resume 沿 manifest 順序與
run ID（如 test-T1-A-r1），不重抽已完成結果。

Development 可改附件文字、pointer wording、checker／instrument 缺陷，保留
版本與成本。不得看 test 後改目標、門檻或題族。Pilot 第一 run 前凍結全部
文字、tasks、checker、meter、runner、分析與 grading 契約。Pilot 不再調優；
失敗另立 version，原 pilot 保留計費，不重命名為獨立 test。

## Trigger instrument

u2_trigger.py reads only native calls/results, events and the run's sealed installed
baseline snapshot; it never infers installation from the arm label. Skill opened
is yes/no/not_installed/unknown; skill and attachment coverage have three observed
states, full/part/not_at_all, plus not_installed and unknown:

- full: successful native returns match every baseline line in order, including
  the union of actual returned ranges. Command text, requested ranges, a skill
  invocation, normalized events and self-report alone cannot prove full.
- part: a successful return matches some baseline lines, with complete supported
  evidence excluding any additional read that could change coverage.
- not_at_all: the file exists in the snapshot, the run trace is complete, and
  every call's supported read scope excludes it; there is no positive opening.
- not_installed: the authoritative installed baseline directory exists and the
  target file is absent. This describes installation, even when execution evidence
  is incomplete; it does not assert that no file was created later. A missing
  baseline, symlink or invalid snapshot is unknown, never not_installed.
- unknown: missing/incomplete native evidence, unrecognized tool/event shapes,
  opaque read scope, an unsupported relevant read, or a failed/missing/truncated
  relevant result prevents deciding coverage. read_uncertainty records call IDs
  and reasons. Neither unknown nor missing evidence counts as triggered or as
  not_at_all. Independently proven full coverage can still establish full when
  other calls are uncertain; proven openings remain yes even if coverage is unknown.

Skill invocation or returned matching skill lines establishes skill opened=yes;
attachment opened is recorded separately. Explicit literal cat/sed/head/tail
sequences using && or semicolons require matched output and successful native
status; the final semicolon command's exit alone never proves earlier reads.
Opaque members, branches, substitutions, globs and arbitrary inline programs do
not prove absence. Successful frozen helper help/suggest commands and the unittest module retain
a narrow script boundary: arbitrary internal/preloaded reads are not inferred.
Review helpers can recursively read card evidence and cannot prove absence; failed
helper results remain uncertain when their read scope cannot be excluded.
Helper commands are retained separately, especially improvement.py
propose/compare/decide/check-card. Literal external-only probes can be excluded
when their complete statically known targets cannot refer to the installed files.

Claude 以 assistant.message.content 的 tool_use ID 配對 user tool_result。
Read 單次沒有 offset/limit 且成功、無截斷，返回文字涵蓋 baseline 每一行，
才記 full。分段 Read 只計實際返回且與 baseline 對得上的行；成功 ranges 的
union 覆蓋每一行才是 full，不將請求範圍冒充返回範圍。Codex 以 rollout 的
response_item function_call/custom_tool_call 與 output 按 call_id 配對；可
辨識的 read_file 使用相同 range 規則，CLI command_execution 僅作 fallback。
兩 host 的 cat、sed、head、tail 只有在可解析的簡單命令與成功 output 配對時
才給讀取證據。Shell output 必須按順序包含每一行；host 行號可移除，重複行
仍逐次比對。多段返回的 union 可組成 full。只看 command 字串不給 full。

Native default read limit、output 截斷、失敗或缺失的 tool result、opaque JS／
Python／shell、encoded command、間接 path、讀取後檔案已異動、未保留的 child
trace 或 incomplete stream 都可能無法判斷，記 unknown。已經有完整 baseline
逐行證據時 full 可以成立；部分證據遇未知尾段仍記 unknown。隱式 preload、
工具外讀取、模型理解／記憶、在內部思考採用方法無法偵測。沒有明確開啟的 no
只表示完整可解析 trace 中沒有觀察到，不能宣稱從未預讀。Unknown 永不計入
triggered。Offline fixtures 是 native format 的 synthetic examples，不冒稱
真 host 已驗證；pilot 必須核對凍結 CLI 的實際事件格式。

improvement_review_activity is scoped to unsolicited review on negative tasks:
yes requires a successful explicit review helper; no requires a complete supported
trace with no review activity or ambiguous review prose/object; unknown requires
independent intent adjudication or better evidence. Merely opening the skill does
not by itself assert review activity. On positive tasks it is expected, a scope
designation for the requested review rather than an observation or quality score;
false_trigger is null. This applies equally with or without an installed skill.

Negative false_trigger remains yes for a successful skill opening, attachment
opening, explicit review helper, or independently adjudicated unsolicited review.
These are distinct observations: opening alone can prove false_trigger=yes while
review activity is no/unknown. Unknown activity is never treated as no. A tool's
failure matters when it can conceal a relevant read; a fully known unrelated
read failure cannot conceal one. Independent readers still adjudicate prose and
intent; word matching never proves a review.
B 每 positive task 至少三次中兩次 full，而且兩位評審均判實際使用事件、
局部 diff、軌跡／不確定性、保留或撤回的推理鏈，才通過 behavioral trigger。
缺證據時承認缺失是合理使用，不要求捏造 baseline。機械 full 與 behavioral
use 分列；instrument 自己永遠不冒認 behavioral_use，該欄為 unknown。

離線 instrument 的分類 fixture 必須全通過。Pilot 任一指定題低於上述規劃
2/3 門檻，或 instrument 無法辨識，停止該版本。Test 未觸發仍保留原分母，
記 inconclusive，不能剔除。Negative B 的規劃 gate 是十二次中零 false triggers，
unknown 未解除也不通過。這些率與零容忍界線尚未測量，不是既得成果。

## 品質與可執行判定

Mechanical checks 先行，兩位 blind graders 只判 script 不能決定的項目與
wrong claims。隱去 arm、host、model、成本與 event stream；固定 identity masks 隱去交付中直接的
arm/host/model/installed-skill 名稱及 private home path，保留任務與 patch 語意。保留原件／
匿名件 hashes，mask 次數與 possible blind breach；格式或內容仍可能洩組別，須 lead 審查。只評實際交付，不挑最好候選。兩家各自出 arrays 比較，
不能先平均評分。

以下全是未凍結、未實測的 decision thresholds。u2_decide.py 的 evidence input
明列完整性、各 gate、兩 grader 的 positive/negative coverage 與 wrong-claim
arrays、兩種 cost arrays。每題三次，正題八題、負題四題、cost 十二題；缺值／
配對或 grader 不獨立則拒絕。格式見 README。唯一確認比較 B 對 A，N 僅參考。

沿用 eval_stats 規劃 10,000 draws、seed 20261107，task 配對。95% CI 不跨
零才 better/worse；90% CI 在 margin 內才 equivalent。Coverage margin ±0.10，
wrong claims margin ±0.5，後者越少越好。兩 grader 各自 quality，再 agree；
分歧為 undetermined。正負題分算；negative 兩家均須 better/equivalent。

每 cell promote 必須同時滿足：完整配對／meter／grading／trigger；B severe
為零；任一同題同 repeat 的 A 正確 assertion 不得在 B 變錯；negative 的 false
與未解 unknown 均零；policy 增量零且 pointer 一行；task correctness 之外的
burden 不退步。Burden gate 的暫定解讀是 positive 平均 guidance 淨增字數與
改動檔案數不高於 A，任何 task-specific 正確性損失先按 assertion gate 阻擋；
評審核對重複／矛盾 guidance，不能只靠 token 下降過關。此 burden 定義仍須
pilot 前批准與封存，不能由操作者隨意勾選布林值。

滿足上述 gates 後只有兩種 promote 出口。第一，兩家 positive quality 都是
better，兩家 coverage 平均差各至少 +0.10，execution 與可歸屬全流程 cost
ratio 的 95% CI 上界均不超過 1.10。第二，兩家 positive quality 都 equivalent，
上述兩種 cost ratio 上界均不超過 0.90。其餘 retain A。既有 eval_stats.cost
的 1.5 cap 判詞仍另報，不能把 within 直接當本研究 promote。共享工程成本
另列，不能隨意攤到 arm；全研究收益與是否值得搜尋另議。

評分 evidence 須獨立封存，script 不認證其真實性。

## 隔離、meter、retry 與 ledger

每 run／infra attempt 全新 fixture、安裝後 baseline、home、session，沒有跨題
記憶。真 state 由 CLI 指定本機 local disk；native transcript、credentials 路徑
與 private 輸出只留 local。Auth readonly bind，環境不傳 API key。Real
bubblewrap 用 filesystem allowlist 與 PID/IPC namespace，hidden/records 不 mount。
依 H1 保留 host inference transport；Codex workspace sandbox 或 Claude Bash
sandbox 阻工具網路，關閉 web/MCP。真 CLI sandbox 待 preflight/pilot 核對。
本次 fake/checker 以 Landlock+seccomp 阻檔案越界、network、跨 process inspection，
不冒稱 real bubblewrap 已通過。

Development/pilot 每 run observed-counter ceiling 為 600,000 logical tokens；test 暫為 200,000；每 run 最多 1,200 秒。另保留
1,000,000 logical tokens 的 in-flight engineering allowance（非已證明的硬上界）。觀測到限就
終止 process group，保留既有交付計分，不重抽截斷答案。Native counter 延遲與
未 flush child 可能超限，overshoot 全計並記 deviation；完整完成且 metering 完整的 run 不因超限失效。未知費用不釋回。Infrastructure 最多
重試一次，兩次均計費；quota／billing／model／meter 錯誤停止。Crash 先恢復
已完成 native result／attempt，再補 row，不能重抽已完成答案。

Claude 按 result.modelUsage 計 logical 與排除 cache-read 的 noncache，保留
cache creation。Message usage 按 ID 去重，僅作 partial lower bound 與 child
分帳。Codex 加總 fresh home 每個 rollout thread 的 cumulative token_count，
不再重加 parent stream。缺 child／counter／model 為 incomplete，分帳不明為
null。Claude billing 的 init.apiKeySource 必須 none；Codex 必須 chatgpt login、
無 API key 且 provider=openai。記 CLI／model 實回報、meter／billing source、
wall time、attempt 與 artifact hashes，不認證候選自報用量。

Development 可以使用獨立的六 run（D1/D2 × A/B/N）independent_task manifest；
其 state 不直接改綁成 frozen pilot/test。Pilot/test 可各自使用 U1 schema 1 的完整 split manifest（18 / 108 runs）；完整 132-run manifest 仍可保留。以 canonical JSON hash
綁 protocol、condition、arm、task inputs、split、repeat 與各 record/outcome。
Input hash 只含 task.json／fixture，hidden 另封存。Study 為 independent_task；
toy 為 diagnostic。保留 attempts、費用與交付 hashes。Session 內工作全計一次 answer，不偽造分項 token；未知
shared／grading 成本維持 unmeasured。U1 不表示 trigger、burden、severe 或
Claude-family cap，另存 sidecar；兩 scorer 用兩份 bundle。未封存共同 metric
或未完成 blind grading 時保持 unscored。Bundle 與 delivery 先作 private，
公開前審查；公開 report 不含 transcripts 或 private absolute paths。

## Claude 共用預算與停止

30M 是跨兩 cells 的 Claude-family logical cap，含 cache reads。Cell 1 的
Codex execution 分開報、不扣 Claude；兩 cell 的 Claude grading、authoring
review、failures／retry 均扣同帳。Cell 2 的 parent／subagents 亦扣此帳。
原 draft 的單價、shared 與 total 全未測量，不適用兩 cell 帳法。

Budget base write-once 記 Claude spent-before 與 external reserve，含既有出題
審查和兩 cell 待做 grading。外部工作以獨立 charge ID、source hash 與實測
logical/noncache 入帳，不重複 parent/child。State lock 串行 run、resume、charge。
Claude 啟動前保留單 run observed ceiling 加 in-flight allowance；未知支出保留 max(lower bound, reserve)，
run 後重檢 overshoot。Codex 啟動亦檢查 Claude 外部保留額。平行 grader 必須
使用同一帳本；沒有服務端全域硬 cutoff，漏報外部工作就是完整性失敗。

Cell 1 pilot gate 要求 P1/P2 的三臂三次共十八列完整、subscription／model／
meter 正確、checker 可判、零 severe、兩題 B 各至少 2/3 full+兩家 behavioral
use，以及 instrument validation。這裡 Claude measured unit cost 只可來自已
做的 Claude-family grading，不得使用 Codex executor 單價假估 Claude execution。
通過後才進 Codex test，並允許 Claude development/pilot 作受 cap 限制的校準。
Claude test 再要求自己的同型 pilot gate，以及 Claude pilot 實測每 arm 全 run
平均單價中的最大值 × 剩餘 runs × 1.3，加已花、兩 cell 未付 grading／shared
保留額不超過 30M。計畫中的 1.3 是未測量 reserve multiplier。不可重複加同一
external reserve，亦不可漏計 development/pilot 已花費用。

投影超支請 repository owner 決定；instrument／checker／meter／隔離失效、洩題、
severe、quota／billing 不符即停止，由 experiment lead 決定新版本，不降 repeats、換題或補到顯著。規劃完成或
未知無法解除也停止。本文只作離線準備，不授權模型 run 或出貨。

## Round 2 installation and task contract

The candidate installer itself rejects an occupied `AGENTS.md`; it does not append
a block. The runner now stages each arm through its own unchanged installer. It
preserves the fixture's `AGENTS.md` prefix, appends the exact rendered package policy
inside fixed `u2:managed-policy` delimiters, and updates that installed file's managed
hash. All other occupied package paths fail closed. `docs/agent-guide.md` and saved
evidence remain exact fixture bytes. This common overlay is taken before baseline,
so checker protection/scope compare agent edits to the actual installed baseline.
N gets the pristine fixture. No task or arm source is edited by this adaptation.
The shared policy difference between A/B is still zero lines.

The checker snapshot includes named optional `hidden/checklib.py` beside the three
required contract files. Seals bind all four when present; missing/changed local
helpers fail seal verification. The checker sandbox can import only its private
snapshot and allowed stdlib/runtime roots. Malformed submissions are scored by the
checker; broken runner layout/checker invocation stops the stage. D1/D2 actual
right/wrong integration covers 2 × 2 × 3 × 2 = 24 executions, with identical checker
results across A/B/N and hosts. Reader nulls remain unscored.

## Real preflight contract

`u2_run.py preflight --cell codex|claude` is a lead-only real inference command.
It uses a built-in harmless `source.py` fixture installed as B, the very same
`live_launch`/bubblewrap command builder, flags, subscription credential read-only
bind, clean environment, fresh HOME, stream capture and cumulative usage meters as
a real study run. The fixed request asks for workspace listing, visible skills and
opening oaw-improve, source reading, an outside-canary read attempt, a web request,
and `review_out/decision.md`. No study content is supplied. The observed stop is
500,000 logical tokens. The 1M in-flight reservation is engineering headroom;
late overshoot is recorded, never erased. The largest observed `final_total -
live_total` gap is reported along with every sampled running total.

Private `preflight-<cell>.json` records pass/fail/could-not-determine per check,
usage, installed expected skill path, host report observation and the trigger
instrument's classification on the actual transcript. Discovery is reported and
not gated. Isolation and metering checks must all pass, including a marker executed
inside successful bubblewrap setup, static host-write confinement to the two bind
roots, unchanged outside/runtime/credential bytes, no outside canary in captured
events, observed attempts, no successful native/shell web request, subscription,
expected model/version, complete root and child usage, live meter, and allowance.
The fresh namespace's `/tmp` is ephemeral, not a host write destination. No real
unsandboxed fallback exists. A missing, failed, undetermined, changed or unaccounted
preflight closes every study launch for that cell. Source/runtime/arm/evidence
hashes and a unique shared-cost charge bind the proof. Setup refusal leaves a
closed report. These real checks have not been run in this preparation round.

Preflight and graders reserve before inference under the shared state lock.
Interrupted/unknown calls retain their reservations and block all further live
calls until audited recovery. Claude preflight, execution and all Claude-family
readers count toward the same 30M cap; Codex-family calls remain separate records.
An external grader allocation is replaced by its in-flight call reservation, then
by measured usage; the same pending work is never reserved twice. Serial future
Claude calibration uses remaining observed ceilings plus one in-flight allowance.

## Frozen blind reader contract (implemented, awaiting lead freeze)

Exactly two different families, neither the tested model:

- Codex CLI `gpt-6-astra` (also the author of the task packages and rubrics: a reader
  who knows the rubric well, still blind to run arm and host).
- Claude Code CLI `claude-fable-5-2`.

Each run is one request with no tools and no reconciliation. `u2_grade.py pack`
shuffles completed deliveries with fixed seed 20261113, assigns anonymous IDs,
writes hashed prompt files and a private map (mode 0600 in a private directory).
The prompt contains only rubric, referenced sealed truth context (facts, pair
identities, retained/remove lines and limits), and actual decision.md,
proposed.patch and final_message.txt. It omits arm, host, costs, checker outcomes,
events and private map. Artifact text gets fixed identity masks; possible blindness
breaches remain explicit findings for the lead, not claims of perfect blinding.
No study agent, reader or runtime sees the map.

The JSON answer has one boolean and one-sentence reason per reader item, an integer
unsupported_count equal to the list of unsupported_statements, and separate boolean
judgments/reasons for requirement removal, permission loosening and directly
evidenced concealed access. No new scored items are introduced. With no event
stream, readers judge support available in the supplied facts/artifacts; they must
not infer unrecorded invocations or prove hidden-access absence. Isolation and the
mechanical checker retain that responsibility. Evidence demanding broader semantic
or behavioral adjudication remains a separate lead-controlled review.

`run-grader --family codex|claude --live` uses subscription credentials and the
same outer sandbox, fresh HOME, captures final JSON, all root/child native usage
and a shared ledger charge even for an invalid answer. Claude uses an empty tools
list and max-turns 1; Codex additionally uses a loopback subscription Responses
relay that strips every wire tool definition, forces tool_choice=none and refuses
a second inference request or websocket transport. CLI changes fail closed. The
relay never records credentials. No tools/native call and exactly one request
must be certified before accepting a grade. No automatic grader retry occurs.
Each accepted grade binds its prompt, model/version, meter, request contract,
native evidence and judge implementation. All attempts remain billed.

`merge` checks both grade files and cost provenance, combines mechanical items with
each reader's own booleans, emits separate score sets/U1 import contracts per host
and grader, plus test task/repeat coverage and unsupported-count arrays. Item
mismatches are disputed; each reader's value stays in that reader's analysis.
Unsupported statements, severe judgments, assertions, burden and blind warnings
remain sidecars. Missing mechanical/reader values or incomplete metering block
scoring. No average or reconciliation round is permitted. Development/pilot arrays
never pretend to be complete test arrays. Trigger-use, negative-intent, costs and
burden attestations must still be supplied before `u2_decide.py cell` can decide.


Development instrument amendment (2026-11-14): development-only renormalize may
record this trigger-definition documentation change along with runner/instrument
repairs. Original preflight, answers and usage stay retained and every source
hash transition is recorded. Pilot/test still require a fresh preflight and
freeze. u2_report.py is a read-only presentation tool: it consumes retained rows,
checker results and trigger files, reports mechanical items only by default, and
includes reader items separately only from answer-bound merged grading files.
Development tables are not attachment-effect evidence.


## Pilot support amendment and measured development (2026-11-14)

This amendment supersedes earlier statements that pilot/test require pre-authored
132-run manifests or that development measurements are unavailable. No test task
is authored to make the pilot plan. Each selected split has a separate manifest
and state binding; a development state cannot be rebound to a pilot plan. For
`plan --split pilot`, the seed 20261113 consumes the canonical development-stage
shuffle before shuffling the pilot's six task/repeat blocks and three arms per
block. Its 18 runs have exactly the order of the pilot subsequence of the full
preregistered plan. The same rule applies to `--split test` (108 runs).

The Codex development measurements from DEV_RESULTS.md (state4, CLI 0.167.2,
gpt-6.1-sol, high effort, one repeat, 600,000 logical-token ceiling) are:

| Task | Arm | Logical tokens | Without cache | Seconds | Mechanical items | Skill opened | Attachment read |
|---|---|---:|---:|---:|---|---|---|
| D1 | N | 150,073 | 19,385 | 85 | 8/8 | — | — |
| D1 | A | 217,819 | 25,563 | 133 | 8/8 | yes | — |
| D1 | B | 221,935 | 22,895 | 130 | 8/8 | yes | full |
| D2 | N | 165,435 | 32,315 | 146 | 9/9 | — | — |
| D2 | A | 209,889 | 29,025 | 182 | 9/9 | yes | — |
| D2 | B | 341,487 | 34,159 | 170 | 9/9 | yes | full |

All six runs met every mechanical item. D1 proposed no change; D2 proposed the
same three-line, 48-word deletion in every arm. Both B runs read the attachment
in full: the earlier D1 classification missed a semicolon-separated cat sequence
and has been corrected from retained native evidence. The three reader items per
task remain ungraded. These single repeats provide no variance estimate and are
not attachment-effect evidence. Their logical-token sum is 1,306,638. Earlier
state3 attempts remain billed: D2 B 216,182 (then-200,000 ceiling) and D2 N 179,067
(malformed runner events, subsequently repaired). They are separate from state4.

Pilot observed-counter ceiling is 600,000 logical tokens per run, identical to
development, with the existing 1,000,000 in-flight reservation and 1,200-second
maximum. The test ceiling remains the working 200,000 value until the pilot
numbers set the frozen limits. Overshoots and all attempts remain billed.

Before pilot/test launch, the lead creates `FREEZE-<split>.json` in the state root.
The write-once freeze binds the selected cell/manifest, arms manifest, visible task
inputs and hidden checker/truth/rubric/helper seals, runner sources (including
split audit, integration, freeze and report code), instrument and native fixtures,
protocol document, token policy and that state's verified fresh preflight proof
and evidence. Create/check and every launch/resume verify all these identities;
missing, stale, failed or unaccounted preflight cannot create a valid freeze.
Development requires no freeze. Offline integration is not launch proof: it
replays every independently specified author case through the installed run-folder
builder and checker on A/B/N and both hosts, retaining intentional broken/severe
outcomes and comparing them to expected outcomes. It makes zero model calls.

Immediately after the Codex pilot, and **before anything else is authored or
run**, apply this lead rule:

- If all six task × arm cells met every mechanical item in all three repeats
  (mechanical ceiling); **or**
- if arm B read the attachment in full in fewer than 2 of 3 repeats on either
  pilot task; **or**
- if the projected Codex test cost exceeds **60,000,000 Codex logical tokens**,
  computed as the highest pilot arm mean (each over both tasks and all three
  repeats) × 108 runs × 1.3;

then the stage stops. The lead reports the measured numbers to the **repository
owner**. No test split is authored or run without the repository owner's decision.
The boundary is strictly greater than 60,000,000; exactly 60,000,000 does not by
itself trigger that cost stop. Otherwise the test tasks are authored and the pilot
numbers set the frozen limits. This review precedes Claude calibration, additional
grading calls, or any later task authoring/execution; it does not replace the
existing independent behavioral-use, safety, metering, grading or Claude-budget
gates. This preparation grants no model-call authorization.

`u2_report.py pilot` uses retained rows, checker results and trigger files only,
with reader items shown separately only when answer-bound merged grades exist.
It reports all 18 runs, per-task/arm logical-token means/ranges and mechanical
counts by repeat, B full reads /3, cells with 3/3 mechanical completion /6, runs
with every mechanical item /18, and highest-arm-mean × 108 × 1.3. Observed spending
is reported separately by family from all retained attempt rows and external
charge rows in the state, including failed attempts and preflight/grading bills.
Incomplete bills remain lower bounds; costs from other states require external
charge rows and are not invented from the pilot projection. The report prints
measured numbers without an automated verdict. The pilot is not a test of the
attachment.
