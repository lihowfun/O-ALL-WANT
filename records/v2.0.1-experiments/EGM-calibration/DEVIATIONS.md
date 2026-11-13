# 準備階段偏離與未驗證條件

1. 首次讀取 `DESIGN.draft.md` 時輸出了整份文件，包含指定 §2–5 以外的 §1。該節有歷史 findings 摘要。這超出指定閱讀範圍。沒有讀取 KEY.json、curator 目錄、禁止的兩份 historical reports，或現行 execution plan 的附錄 B。指定的 ANATOMY 也有歷史摘要。因此不能聲稱本次準備模型完全未見歷史背景。prompts 沒有加入這些答案。新的受測 sessions 不繼承本次對話。
2. Literal workspace-only host I/O 無法直接套在 subscription CLI：host 需讀 OS runtime、credential，並寫 fresh HOME 的 accounting state。runner 對 source 採 Landlock 唯讀，允許 review_out 與該次 fresh HOME 寫入。這是明列的 host 例外。Codex shell 的額外 tool boundary 尚未由真實 CLI 驗證。real gate 保持未通過。
3. Round 1 未解條件（歷史記錄，已被 round 2 lead 決策取代）：X2-style counters 加 polling 不能單獨保證 6M 絕對 hard cap。child requests／cache usage 可能晚報。runner 有 live stop 與 inflight reservation gate，但離線沒有建立可證的 unobserved-token bound。不能將預設 0.25M reserve 當成實測上界。需補 meter/reservation 證據或由 experiment lead 明確修訂 enforcement protocol；未解決前拒絕 real launch。

U1 plain-ledger fallback 是 task 明許的選項，不是暗改 U1。其 shared grading scope 限制與本案不合；詳見 PREREG 與 ledger_manifest。

目前只有 deterministic offline tests 和 dry preparation。沒有真實 model runs、EGM、network、實際 grading、git 操作，或工作目錄以外的寫入。

## Round 2：lead 在 freeze 前的明確決策

D48 experiment lead 是 freeze、gate、grader assignment 與 custody 的負責人；repository owner 僅在 room 後決定 funding。
原第 1 項的 §1 與 ANATOMY exposure 記錄保留；本輪沒有讀 key folder、historical reports 或現行 plan Appendix B。
原第 2 項的 runtime／fresh-HOME 例外保留，改以 real preflight 驗證 tool boundary；本輪未啟動任何 model。
原第 3 項的 bound 要求由 lead 在 freeze 前修訂：6M 是 stop threshold、30M 是唯一 absolute limit；
inflight_allowance=max(1M,4×每 cell preflight live/final gap)，是 engineering allowance 而非 bound。
late reporting 超過 6M 記 deviation、停止 launches，但完整 cell 仍評分；metering 不完整或超過 30M 為 no conclusion。
Codex freeze version 更新為 0.167.2，Claude 2.1.322；freeze 後改 version 仍先記 deviation。
Astra grader 亦為 curator，對 key 熟悉是限制；仍 blind to arm/cell。另一 grader 為 Claude Fable 5.2。
lead 須在 freeze 前完成 Claude-family 非受測 primary eligibility check（有爭議者降 tier，不加 item），
並修正 key 的 ad-hoc packet digest 為 official manifest digest；保存前後 key hashes。此準備沒有讀或改 key。

新增 commands 只交給 lead 執行。preflight 的任何 isolation fail／could-not-determine 都讓 gate 維持關閉。
離線測試與 dry-run 不替代 real preflight，不是正式 study freeze 或實驗結果。

## Round 3: final lead decisions before subject data

Round 2's 0.674–0.683M Claude N proxy, 2.66–3.60M stage estimate and 6M stop are
withdrawn BEFORE any subject run: the settled eligibility check measured
3,398,755 Claude logical tokens, 359,512 without cache reads, on 16 items.
Scaling from small documents was unsupported. Stage stop is now 15M; experiment
cap stays 30M; per-N ceiling is 8M in both cells. Inflight engineering allowance,
late-reporting treatment and infrastructure retry policy remain from round 2.
Earlier 6M statements above are historical records, superseded by this section.

Eligibility is done: all 16 original primaries real, 9 blocking kept, 7 disputed
blocking moved secondary, none excluded or added. Corrected key has 30 items,
9 primary, byte hash
6d7497e90b9baf7f872bfd04c4750fee77a523e69169fd840d48df02d8e1f99e.
Preparation has not opened the key or restricted findings/curator files.

Codex completes first; Claude N1 precedes blinded batch-1 grading/reconciliation.
N2 is conditional on N1 not ceiling and the runner's 1.3× measured-cost funding
rule. M is removed; its prompt and code remain frozen, unused. Batch 2, only in
the N2 branch, repeats all three earlier reports with new IDs/shuffle and fresh
sessions; only Claude N2's new labels enter decisions. Original independent
labels supply test–retest agreement. Graders no longer reconsider eligibility.
Claude Fable grades one inline report/request, tools disabled and no packet;
only Codex Astra assesses unsupported claims, descriptively attributed to one
grader. One reconciliation round exchanges initial label/passage/reason; final
consensus alone corrects a primary label. Claude's side is one tool-free request.

Import the already-spent checker through a lead-supplied shared-cost record with
session-transcript evidence, subagents none, and measured time; no private path
is public. Codex curator usage stays separate. No new content, model calls,
network calls or actual results are authorized by this preparation. Real
preflight and the lead's final freeze remain pending; offline tests cannot
supply them. No reading of packet content is needed in round 3 beyond existing
identity verification/dry copies.

Blind review: five blockers fixed before freeze.

## 凍結後、開跑前的偏差（2026-11-14，lead）

第一次凍結（freeze 1）的準備雜湊是 `d046bb592f6c038a9f8a36c01f1fcaa64bd82ebde0dffbad311692e541188ce5`，已推上 records。
之後第一次在真實 host 上跑 Codex preflight，沒有成功，也沒有任何 model request 完成（事件只有連線重試與 `turn.failed`，沒有 token 計數）：

1. 這台 host 的 `/etc/resolv.conf` 是指向 `/run/systemd/resolve/stub-resolv.conf` 的 symlink。Landlock 的讀取 allowlist 只列 `/etc`，
   目標檔不可讀，CLI 無法解析後端主機名稱。修正：allowlist 另加 `resolv.conf`、`hosts`、`nsswitch.conf`、CA bundle 這四個設定檔解析後的**檔案本身**，
   不加它們所在的目錄。agent 工具的網路限制不變。
2. preflight 的檢查程式遇到 Codex 的錯誤事件（`message` 是字串）就當掉，沒有寫出失敗的 proof。修正：只在 `message` 是 mapping 時找 tool_use；
   連線失敗現在會正常落到「preflight 未通過」。

兩處都只影響 host 啟動與 preflight 的檢查，不改 prompts、key、決策表、計分、預算規則。新增 `tests/test_hostfix.py`。
這時還沒有任何 study run 或評分資料。freeze 1 的 manifest 保留為 `freeze_manifest.freeze1.json`；失敗的 preflight 目錄保留在私有 state，
新的 preflight 用新的 state root。重新凍結後的雜湊見 `freeze_manifest.json`（`freeze_tools.py --check`）。

第二次 Codex preflight（freeze 2，`baa1da5d399bbeb0efbfd2022db07ba09e446d4f8e7399428416b120d0edf23c`）連線成功，隔離與計量的檢查通過，
但 agent 的每個工具呼叫都失敗：Codex CLI 要從自己所在的資料夾啟動工具 host，allowlist 只放行 CLI 執行檔本身。花費 105,633 Codex logical token，沒有 study 資料。

3. 修正：lead 以環境變數 `EGMCAL_RUNTIME_ROOTS` 指定 CLI 專用、只含 CLI 檔案的 runtime 資料夾；只有包含該 CLI、而且不是 HOME 或其上層的資料夾才會被放行讀取與執行。
   這不改 prompts、key、決策表、計分或預算規則。重新凍結（freeze 3）的雜湊見 `freeze_manifest.json`；freeze 2 的 manifest 保留為 `freeze_manifest.freeze2.json`。
   兩次失敗的 preflight 都保留在各自的私有 state root，用量記入 Codex 側。



## Pre-data host launch revision 4 — real egmcal-3 / U2 evidence (2026-11-14)

This changes the host launch layer before any study data. Study prompts under
`prompts/`, key, decision table, scoring and budget rules are unchanged. Only the
built-in isolation probe prompt names explicit observable actions now.

The third calibration preflight reached the pinned model with complete metering,
but Landlock prevented Codex's nested bubblewrap from starting every shell and
apply_patch could not write its report. The real U2 namespace launcher worked.
`cal_launch.py` therefore replaces the real Landlock preexec wrapper for both
hosts, native/merge, graders, reconciliation and preflight. It starts from a
bubblewrap tmpfs root: system runtime, resolved DNS/trust files, explicit
EGMCAL_RUNTIME_ROOTS runtime, fresh HOME, read-only workspace and writable
review_out. No study parent, ordinary HOME or credential directory is mounted.
The subscription credential copy remains limited to fresh HOME. The CLI's own
Codex command sandbox remains workspace-write with network off. The outer host
keeps model-transport networking. `cal_sandbox.py` is retired and removed from the freeze list. Offline tests now
exercise the namespace launcher; no production code imports Landlock.

The same real event stream contains a successful codex_apps
search_service.web_run MCP call returning Example Domain content. The prior
parser ignored mcp_tool_call and falsely passed the no-web check. Both runners
now use identical host_policy.py and host_probe.py: all listed external features
are disabled on every inference launch, MCP config is empty, and native MCP,
hosted search/browse, remote tool results and shell network results are checked.
Success fails even if another record is incomplete; an observed denied attempt
passes; absent/ambiguous evidence stays could-not-determine. Claude uses a fresh
HOME, no settings sources, enabledPlugins={}, strict empty MCP and an explicit
tool allowlist. Skill remains available in native review; Bash remains excluded.
A missing attempt is never inferred from Claude's disabled web tools.

Trimmed real event fixtures and their retained fields are documented in
`fixtures/host-preflight/README.md`. Offline tests exercise the launch policy,
namespace writes and nested bubblewrap with a synthetic executable only. No
real CLI or model was invoked. Old proofs/gates bind previous runner bytes and
cannot authorize this revision. Lead must rerun both preflights with new state,
carry forward every previous preflight cost, and confirm native commands,
apply_patch, metering, skills and absent remote tool surfaces on the real hosts.
The previous manifest is preserved byte-for-byte as freeze_manifest.freeze3.json;
new preparation hash is emitted by freeze_tools.py --refresh / --check.

Claude preflight alone includes sandboxed Bash (network.allowedDomains=[],
allowUnsandboxedCommands=false) to emit the concrete curl result. Native/merge
retain their original tools and Bash denial; Fable remains tools-empty. Without
this probe-only tool, web unavailability might produce no observable attempt and
must correctly remain undetermined. This is confined to the pre-data host probe.
CLI --version discovery is also mount-isolated with fresh HOME/no credential.

Fifth pre-data host fix (2026-11-14), following the fourth real Codex preflight: hosted web was absent and isolation/metering plus attempted-action evidence passed, but every command and report patch failed at `bwrap: Can't mkdir /home/dev/proj/.git: Read-only file system`, leaving completion failed and curl undetermined. Per the lead's decision, the outer launcher now binds the per-attempt workspace copy writable so the CLI's workspace-write sandbox can prepare protected mount points. Native source isolation is detection plus the unchanged instruction: verify the copy's official packet digest before/after, record all changed/added/removed paths and terminal `isolation incomplete`, charge usage, never redraw. Only newly added empty top-level `.git`, `.agents`, `.codex`, `.aws` directories/empty directory mount stubs are tolerated and recorded per attempt; U2's second preflight lists the first, third and fourth, while the installed pinned 0.167.2 builder names all four (evidence in fixtures/host-preflight/README.md); existing packet paths, contents, links, regular-file stubs and all other additions remain violations. The harmless preflight now requires a successful overwrite and `source_change_detected: pass`, plus `other_sources_unchanged: pass`; its deliberate mutation correctly records raw isolation incomplete, and the gate uses the detection checks. Web checks and strict grader inventories remain unchanged. All 81 offline tests pass (six new regressions); repeated native dry commands retain exactly two rows per cell, and two dry preflights stay undetermined, all with subprocess creation forbidden and zero usage. These checks make no model calls and do not authorize study data; the lead must rerun both real preflights with new private state, carry all prior costs, confirm commands/patch/report, mutation detection, outside-read refusal, conclusive curl refusal, absent remote tools and complete metering. Prompts, key, scoring and budgets are unchanged; the previous manifest is preserved byte-for-byte as `freeze_manifest.freeze4.json` before refreshing preparation.

第六個開跑前的 host 修正（2026-11-14，lead）：freeze 5（`fcc39b53b5f3eefeaf890dbb2964b28c9e44dc08a1ead09c32feb9d9015c7ed2`）下 Codex preflight 17 項全過；
Claude preflight 16 項通過，`no_web_tool_succeeded` 判不出來。事件顯示 Claude 的兩次 `curl` 都在執行前被 host 的權限層拒絕
（"This command requires approval"、"... can't be checked before it runs"），沒有任何指令連上網路；解析器把含 pipeline 的那一次當成「結果不明」。
修正：host 在執行前拒絕的呼叫一律記為「嘗試了、沒有成功」。只改 preflight 與網路檢查的解析，不改 prompts、key、決策表、計分或預算規則。
freeze 5 的 manifest 保留為 `freeze_manifest.freeze5.json`。這次 Claude preflight 花費 69,446 logical token，計入本階段。


第七次凍結（2026-11-14，lead）：公開前把一個測試 fixture（`fixtures/host-preflight/u2-codex-2-attempts.jsonl`）裡的本機使用者路徑換成中性寫法，其餘位元組不變；沒有程式或文件內容的改動。freeze 6（`ab5b3435288f78489d70ac2d9ab122e6d08b3e98c97f0e2b0588368f7ca0b433`）下兩格 preflight 都通過（Codex 62,931、Claude 54,623 logical token），因為雜湊變了而各重跑一次。freeze 6 的 manifest 保留為 `freeze_manifest.freeze6.json`。
