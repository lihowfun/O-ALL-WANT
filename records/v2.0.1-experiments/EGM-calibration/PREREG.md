# EGM native calibration — issue #20, round 3 pre-data preparation

Awaiting the experiment lead's real preflight and freeze. D48 is the lead and
controls freeze, gate, grader assignment and blind custody. The repository owner
only decides whether to fund a later EGM stage. This preparation makes no model
calls, network calls, actual grades or quality verdicts.

## Scope and frozen inputs

One pristine plan-sized document: `docs/plans/v2.0.1-execution.md`, 324 lines,
27,907 UTF-8 bytes, in a 572-file packet. The official packet tree SHA-256 is
`3f61293d1b071118f73eb4590dfcefc437ecd12da735c1bd6025b4f24dd21bc1`.
`packet_manifest.json` lists every path, size and byte hash. The tree digest is
SHA-256 of the canonical files array (UTF-8, sorted keys, compact separators,
ensure_ascii=False, allow_nan=False). `build_packet.py` rejects symlinks, special
files, extra/missing/changed files, `.git` and `review_out` at any depth.
`packet_audit.json` records the prior inventory and full-byte answer-marker audit.
Keep the pristine short Appendix B placeholder and historical evidence cited by
the plan; never substitute the current plan or later findings/fixes.

The preparation agent must not read the key, curator directory, two historical
findings reports, or current plan Appendix B. Prior exposure remains recorded in
DEVIATIONS.md. No key content is used to prepare native prompts.

Eligibility is settled before freeze by curator plus non-subject Claude-family
checker (`claude-fable-5-2`). All 16 curated primary items describe real defects:
9 confirmed blocking, 7 disputed blocking moved to secondary, none excluded,
nothing added. Two retained judging texts were tightened; vague report rules now
mean mention-only. The corrected key has 30 items, 9 primary. Its exact byte hash
is `6d7497e90b9baf7f872bfd04c4750fee77a523e69169fd840d48df02d8e1f99e`.
The lead retains private item evidence, eligibility record and old/new key hashes,
including the earlier correction of the key's ad-hoc packet digest to the official
digest. The gate accepts a lead-supplied hash and checked primary count, never a
hand-edited eligibility boolean. Fewer than 3 eligible primaries fails this key
gate; report labels cannot remove a primary or trigger an eligibility re-vote.
Key schema 1 has items with id, tier, cluster, claim, evidence, detected_if,
mention_only_if, not_adjudicable_if. Do not add findings, change tiers, split
clusters or change detection boundaries after data.

## Cells and fixed prompts

| Cell | CLI | Subject model | Effort / billing |
|---|---|---|---|
| Codex | Codex CLI 0.167.2 | gpt-6.1-sol | high / ChatGPT subscription OAuth |
| Claude | Claude Code CLI 2.1.322 | claude-opus-5-5 | high / subscription, apiKeySource none |

Order: complete Codex N1 and N2, then Claude N1. Codex stays fixed at two N
reports. Claude N2 is conditional on reconciled batch-1 scoring and funding.
Claude requires explicit `--only N1` or `--only N2`; no automatic paired launch.
N1 is also the single-native baseline. N1 and N2 use identical
`prompts/native.txt`, at most 1500 whitespace-separated words including JSON field
text. This is X2's empty treatment with only task context, protected paths and
word limit changed; `prompts/native-vs-x2.diff` records the diff and
`prompts/task_context.txt` is unchanged for a possible later EGM stage.

M is removed from this stage and every decision/completeness requirement.
`prompts/merge.txt` and the merge code remain frozen and unused; the stage runner
refuses merge commands. A possible later EGM stage could merge stored N reports.
There is no EGM, extra document, extra N, persona arm or prompt tuning in this stage.

## Isolation, retries and metering

Each attempt gets fresh workspace, HOME and session; no resume. Copy only the
explicit subscription OAuth credential file, never existing config, memory,
plugins or sessions. Reject nonempty API key/token/provider override environment
variables rather than silently unsetting them. Both hosts run through the U2-style
bubblewrap mount allowlist: tmpfs root, system runtime, selected DNS/TLS files,
fresh HOME, explicit dedicated EGMCAL_RUNTIME_ROOTS folder and workspace only.
The per-attempt workspace copy and fresh HOME are host-backed writable mounts
(ephemeral /tmp and dev/proc support the runtime). This lets the CLI prepare its
own protected-path mount points. Isolation of native source is by detection plus
the unchanged instruction not to modify existing files, not by a read-only mount.
No ordinary
HOME, study parent or other research is mounted. HOME is a necessary
host/auth/accounting exception. Packet bytes and exact file set are verified
before/after each native attempt, recording both official packet file-array
digests. Any changed, added or removed packet file, unexpected directory, symlink,
special or unreadable entry produces terminal `isolation incomplete`, with
`source_changed_paths` and categorized `workspace_changes`; the attempt is charged
and never redrawn. Outside review_out, the only new entries tolerated are empty
top-level `.git`, `.agents`, `.codex`, `.aws` directories (including the CLI's
empty directory mount stubs), recorded as `sandbox_placeholders` per attempt.
U2's second Codex preflight listed `.aws`, `.codex`, `.git`; `.agents` already
held packet skills. The installed 0.167.2 protected-path builder names all four;
the evidence and extraction are recorded in fixtures/host-preflight/README.md.
Existing packet paths under those names remain protected by the full inventory;
nonempty directories and regular-file or symlink stubs get no exemption.
Graders/reconciliation retain their strict input inventories without this exception.
Landlock is not used; the obsolete helper is removed from the freeze list. Runtime folders are never guessed.

Native Claude retains X2 Read/Write/Glob/Grep/Agent/Skill. All Claude launches use
no settings sources, enabledPlugins={}, disabled hooks, strict empty MCP and
explicit tools; native excludes Bash/web and Fable uses no tools. The harmless built-in Claude
preflight adds sandboxed Bash solely to observe curl failure; network is denied,
unsandboxed Bash is refused, and source changes are detected after the probe. All Codex
launches disable apps, plugins, remote_plugin, plugin_discovery_prefetch,
browser_use, browser_use_external, browser_use_full_cdp_access, in_app_browser,
computer_use and skill_mcp_dependency_install, with mcp_servers={} and
web_search="disabled". Its own workspace-write sandbox stays on, with network
off. Skills and shell remain available for Codex study runs. Exact per-kind
flags are in RUNBOOK.md. Successful native MCP/hosted/remote web content is a
failed isolation check, denied attempts pass, and no attempt is undetermined.
Real preflight for
both cells must demonstrate a successful source.py overwrite and detection by
the same integrity checker (`source_change_detected: pass`), unchanged other
sources (`other_sources_unchanged: pass`), outside-read denial, tool isolation,
subscription/model/version and complete root/children metering. Missing observable
attempts/counters are could-not-determine, which closes the gate. Probe input is
three harmless files, no study packet/key; observed stop is 500,000 tokens per
probe, late usage still charged. The intentional probe mutation makes its raw
`usage.isolation_complete` false; the gate requires the detection checks to pass.
A refused source overwrite fails this probe; it cannot validate detection.
The web checks remain unchanged: a conclusive refused curl can establish no
network success, while unavailable hosted web alone cannot replace a missing
command result. Dry preparation never invokes even `--version`;
it creates synthetic reports and zero-token rows, cannot authorize a real gate,
and cannot mix with real data or enter grading.

Real private state is under local `/home/.../oaw-egmcal/`; paths and credential
locations are lead inputs, never public constants. Preserve reports, raw events,
stderr, rollouts, HOME, charge intents, usage evidence and PRIVATE-MAP locally.
Do not publish raw state or automatic private summaries. `freeze_manifest.json`
and `prompt_manifest.json` bind protocol, scripts, tests and prompt bytes. Changed
CLI bytes/version, prompt, key, sandbox or meter after freeze requires a deviation
and lead decision before new calls; never mix frozen versions.

Every attempt, including failures, appends an immutable row. Started intents
without accounted rows block launches until usage is recovered and audited. One
structured infrastructure retry is allowed only for native attempts with no
completed report and fully metered, isolated transport/service failure. Quota,
timeout, token stop, model errors and unknown usage do not qualify. No automatic
preflight or grader retries; no redraw to seek a decision.

Claude logical = input + cache creation + cache reads + output, using final
modelUsage across all model buckets, including children. Noncache excludes cache
reads. Streamed assistant usage is deduplicated by message ID and is only a live
lower bound/cross-check. Codex logical = input + output, already including cached
input; noncache subtracts cached input. Sum the last cumulative token_count of
root and every descendant rollout; never add reasoning twice. Missing root/child
counters, stray rollouts, invalid events, absent final modelUsage or billing
mismatch give incomplete metering, never zero usage. Every final Claude bucket
requires integer inputTokens, outputTokens, cacheReadInputTokens and
cacheCreationInputTokens; Codex final turn/rollout counters require integer
input_tokens, output_tokens and cached_input_tokens. All must be nonnegative,
with at least one nonzero usage bucket for a run producing output. Missing,
empty or invalid buckets retain observed lower bounds and incomplete status,
including grader and reconciliation requests.

## Budget and sequential funding

Before any subject run, the earlier Claude N proxy of 0.674–0.683M, the resulting
2.66–3.60M stage estimate and the 6M stop were withdrawn as unsupported scaling
from small documents. The eligibility check alone measured 3,398,755 Claude
logical tokens (359,512 without cache reads) for one model verifying 16 items
against this packet. One native Claude Code review may therefore cost several
million logical tokens. No replacement unit-cost estimate is claimed before data.

Per-N ceiling is 8,000,000 logical tokens in both cells. Stage stop threshold and
default `--budget` are 15,000,000 Claude logical tokens. The unchanged absolute
document experiment cap is 30,000,000 Claude logical tokens. Include all Claude
runs, preflight, grading, reconciliation, curation/checking, preparation/reporting,
failed attempts and external already-spent costs. Codex usage is recorded
separately and does not consume either Claude cap.

Claude N2 may launch only when N1 is complete, batch 1 is graded and reconciled,
N1 has not reached ceiling, and

`stage spent + 1.3 × Claude N1 actual logical tokens + remaining Claude grading reserve ≤ 15,000,000`.

`cal_run.py native --cell claude --only N2` enforces this itself from the audited
batch-1 score and recorded N1 usage, before creating an attempt. It also checks
the unchanged 30M experiment cap. Projection is rounded upward to an integer.
The script computes the remaining reserve, with no free reserve parameter:
(number of remaining Claude-family grader requests fixed by the design) ×
(per-request allowance). N2 reserves exactly five: four batch-2 report requests
plus one reconciliation request. Per-request allowance is 150,000 logical tokens
before any Claude-family grader request has been observed in this state root;
afterwards it is max(150,000, ceil(1.3 × the largest observed Claude-family
grading/reconciliation request in this state root)). Rounding is upward to whole
tokens. This is a planning reserve, never spending. The same rule governs
preflight, native and retained unused merge launch guards (nine slots before
batch 1: three reports + one reconciliation, then five conditional batch-2
requests), both grader hosts and both reconciliation hosts. Request launches
reserve unsettled design slots, excluding the current Claude request; batch 1
retains the five conditional batch-2 slots. Completed reconciliation closes any
unused slot; C1 or terminal NC5 closes conditional batch-2 work. The largest
observed request remains in the allowance calculation after its slot settles.
Other shared work is recorded as spending, not an adjustable reserve. If not
funded, write terminal NC5 and stop the Claude cell; later commands cannot reopen
that funding stop. The lead reports measured native unit cost to
the repository owner. If N1 is ceiling, do not run N2 or create batch 2.

The round 2 inflight allowance remains `max(1,000,000, 4 × cell preflight
live/final gap)`, derived by the gate, never hand-reduced. It is an engineering
allowance, not a proven bound. Gap includes final minus every running observation,
including initial zero. Poll every 0.25 seconds; stop the process group at
observed usage + allowance >= current run allowance. The generous per-N ceiling
still stops runaway attempts. Claude run allowance is also limited by remaining
stage/experiment headroom after reserve. Timeout remains 3600 seconds. N1 launch
reserves its 8M per-N ceiling from available headroom, rather than substituting
another unsupported native cost proxy; measured N1 supplies N2's explicit
1.3 rule. The N2 funding formula does not add the inflight term a second time;
it still applies during execution. Codex launches spend no Claude forecast but
cannot launch new work after a recorded stage/experiment stop.

Late reporting above 15M is a deviation and blocks further launches; complete,
isolated, fully metered cells remain scoreable. Incomplete metering or >30M gives
NC1. Counters/polling do not prove an absolute unobserved-usage bound.

`--spent` and `--experiment-spent` are Claude costs outside this private root,
with experiment >= stage. Internal rows and shared costs are added automatically;
never count a charge in both places. Shared work uses private shared-costs.jsonl,
unique charge IDs, provider/stage, complete logical/noncache usage, wall time,
root/children coverage and evidence hashes. `cal_ledger.py --add-shared` imports a
lead-supplied record. `--eligibility-check` validates the already-spent Claude
curation charge: 3,398,755 / 359,512, session-transcript metering, subagents none.
The lead supplies measured seconds and transcript hash; no private path is
hard-coded. Record Codex curator usage separately. A shared lock and unsettled
intent checks prevent cap races; no external Claude calls may run concurrently.
Scoring and ledger summaries use the same settlement audit: an intent without
its settled native, preflight, grader or reconciliation row is launched work
with unknown final cost, retaining any observed usage lower bound. A Claude N2
intent means N2 launched; NC1 persists until usage is recovered and an audited
row is appended, regardless of an older accounting audit.
The plain ledger is explicitly not U1-compatible: U1 rejects null run_id shared
grading. Do not relabel or arbitrarily allocate shared costs to native runs.

## Blind grading and reconciliation

Before anonymous hashing/packing, recursively rewrite each report's known
attempt workspace, fresh HOME and state-root prefixes to packet-relative paths
in every findings/uncertainties string. Preserve the original private report and
record the rewrite count in the private map; scoring repeats the transformation
to verify its hash. Reject a blind folder containing the state root, an attempt
ID, or codex/claude/N1/N2 as path components. Grader input checks repeat this.
Batch-1 Codex validity, completeness and decision are final; batch 2 may only
invalidate them through later accounting failure. Carry Claude N1 validity and
labels from batch 1; its batch-2 repeats cannot repair invalidity or change labels.

Batch 1 contains exactly Codex N1, Codex N2, Claude N1, packed only when all exist.
Both graders label all three. Private hash order uses fixed seed
`egmcal-issue20-2026-11-14-v1`; strip runner metadata but preserve technical text.
Batch 2 exists only if Claude N2 runs: Claude N2 plus the exact three batch-1
reports, with new anonymous IDs and new hash-order seed
`egmcal-issue20-2026-11-14-v1-batch2`. Fresh sessions grade all four. Only Claude
N2 labels from batch 2 enter decisions; batch-1 decisions/labels stay fixed.
The repeated reports supply original-independent-label test–retest agreement.
The grader-facing index omits seed, batch number and cell/arm. Withhold PRIVATE-MAP,
run rows, transcripts, billing and prior grades. Style can still reveal authorship;
record blinding risks. Batch-1 score is private to the custodian and runner.

Codex grader: gpt-6-astra, fresh Codex session with read-only blind folder, packet,
key and GRADER.md. Label every key item/report and list unsupported factual claims
and severe false alarms with packet source evidence. This output is descriptive
and attributed to one grader. Astra was also curator; key familiarity is a limit.
Claude grader: claude-fable-5-2, one Claude Code print request per report, fresh
HOME, tools disabled, no packet. Inline prompt contains rules, frozen key and
one anonymous report only. JSON gives every label, report passage and one-sentence
reason. It does not assess unsupported claims. Record complete usage per request
as shared grading cost. Preserve failed request usage and stop, without redraw.

Eligibility is not re-decided. Four labels: detected / mention-only / absent /
not adjudicable. Only unreadable or cut-off report text on that point permits
not adjudicable. Vague text is mention-only or absent, never an item exclusion.
Secondary labels are description only. GRADER.md is the complete rubric/schema.

One reconciliation round per batch, before that batch's unblinding. For every
primary-label difference show each grader the other's initial label, passage and
reason, anonymous report ID only. Each independently answers keep/change, final
label, passage, reason. Codex can consult packet; Claude again uses one request,
no tools, no packet. Apply a correction only if their final labels coincide;
retain all other disagreements. Preserve both original grades and responses,
freeze the hash-bound resolution even if there are no disputes or no corrections.
No human deciding vote, extra grader or extra round. `cal_requests.py` implements
this exchange and the consensus overlay. The lead attests custody; hashes alone
do not prove a human never opened a map. Each batch's fresh graders never receive
maps, prior scores or the other grader's responses before the reconciliation call.

## Scriptable per-cell decision table

The key gate has nine eligible primaries (minimum three). No report-dependent
adjudicable subset. The accounting audit must cover all work performed so far,
complete isolation and shared/curation/grading metering, and the 30M experiment
cap. It is refreshed for each scoring point, not a claim that conditional future
work has already been performed. Reconciliation record and both grade files are
required. Stage late-reporting alone does not invalidate complete data.

| Priority | Outcome / rule | Exact condition |
|---|---|---|
| 1 | no conclusion / NC1 | Required run missing/incomplete (Codex N1,N2; Claude N1 and N2 if launched), isolation/metering incomplete, missing grader file or accounting/reconciliation evidence |
| 2 | ceiling / C1 | Every primary is detected in each grader's union over that cell's completed N reports; different reports may supply each grader's detection |
| 3 | no conclusion / NC5, Claude only | N1 not ceiling and N2 not funded under the runner's rule |
| 4 | room / R1 | Both N1 and N2 exist and at least one primary has all four labels absent |
| 5 | no conclusion / NC4 | Neither ceiling nor room after reconciliation: deciding labels disagree, are mention-only or not adjudicable; batch-1 Claude pending N2 also uses NC4 |

Claude C1 can be decided by N1 alone. If N2 was launched but failed, N1 cannot
rescue NC1. room only asks the repository owner about later funding; it is not
an EGM verdict. No EGM follows automatically. Missing grade files emit NC1;
malformed or mismatched evidence fails closed. No M requirement or decision row.

## Reporting and limits

Report primary labels and evidence per report per grader; N1/N2 label agreement,
detected intersection/union/Jaccard for Codex and Claude if N2 ran. Report recall
for catalog-related primary IDs K14,K15,K18 separately from the other six,
per report and native union, with denominators. Secondary items are descriptive.
If batch 2 exists, report test–retest agreement for each repeated report/family,
primary and all-item exact labels, using independent grades before reconciliation.
List unsupported claims/severe alarms from the Codex grader as one grader's
assessment; a non-key finding is not automatically unsupported. Report logical
and noncache tokens and wall time for each run/attempt; shared costs separately.
Native unit cost is the mean of retained completed N attempts (one or two for
Claude), alongside all-attempt cost per retained report. Show it next to the
historical same-document full-EGM cost, 18,480,203 Claude logical tokens, one run
on 2026-11-07, as native/historical plain ratio. State: one historical run, not a
comparison of quality; provider token units remain separately labelled. No
cross-provider vote or detection-gain/population/noninferiority/quality verdict.

The key is the union of two historical reviews: this stage measures recall
against those findings and cannot measure precision. Nine primaries, three in
one code area; concentration limits coverage. Batch 2 occurs only in one branch
of the Claude cell, so test–retest data are conditional and have no corresponding
branch-balanced comparison. One retrospective document, historical family overlap,
Astra key familiarity, possible style leakage and training/family memory remain
limitations. k=2 is not a cost-matched EGM control. Headless reviews do not measure
interactive fixes, implementation quality or human time saved. Offline tests
validate engineering only, not real CLI discovery/auth/isolation/metering or model
quality. Do not replace the document after ceiling or revise prompts after data.
