# FIXCHECK execution status

2026-11-13, updated after the 13:38 Asia/Taipei quota stop. This file is a progress snapshot, not a verdict.

- Preregistration and independent review pushed in records commit `4033f52`.
- Manifest SHA-256: `d1bec84b95004f7d27f9adf6a1acc07ae53be41f45fcbb50943c334f1ea5b80e`.
- Candidate remains `c2d9852bf8cabf13fd86a4340ab89f69044cae5a`.
- Live-process D39 check found no other experiment runners; stale PID files were ignored.
- Codex A/B/C completed all twelve tasks: **12/24 tasks**, **6,802,657 logical Codex tokens** in counted rows. Its guarded runner exited 0. Task 6 was recovered from its same completed answer after ENOSPC; no redraw. Its independent recovery review is 4/4 PASS and both ledgers contain the original attempt exactly once; see [RECOVERY.md](RECOVERY.md).
- Claude A started after Codex finished. The first task (`t01`, attempt 1) stopped with HTTP 429 / `usage_limit_reached`, `seven_day`; runner exit 3. It produced **no counted answer**, not a zero score. The start/end ledger reports **0 tokens**, with no outstanding reservation. Its independent D45 budget remains 17M; no H1 allowance is reused.
- Continue the same state and resume completed attempts. Do not rebuild, alter the manifest, re-draw counted answers or start PPT concurrently.
- Mechanism audit covers all twelve Codex counted rows, with **90 evidence-file references** whose SHA-256 matches. A checks are light. B observations distinguish save, later recall and actual host-history query; a query action is not recall success, and absent events stay absent. All four C tasks have completed native fresh-context code-review evidence; both design tasks separately record design and one code-review round. Claude audit, combined numerical comparison and independent final result review remain pending. No new H1 effectiveness verdict, regression-pass claim or release decision.

CI PR routing still awaits owner choice. The authorized FIXCHECK uses its already-pushed preregistration and D45 budget independently of that PR choice. Final release still requires both the regression disposition and actual six-job CI.

Release polish is separate: `codex/v2.0.1-release-polish@5af21f6`, Linux gate 9/9, 685 tests. It has not been folded into the fixed study candidate. Integrate it after FIXCHECK's keep/revert disposition, then validate the final release commit.

Cost scope: counted-row tokens cover task answers and their native subagents. Controller engineering and independent experiment/recovery review usage are not separately metered here, so these numbers are not the entire study cost.

## Quota stop and next resume

The service reports `resetsAt=1794564000`, **2026-11-13 18:00 Asia/Taipei**
(10:00 UTC). This supersedes the older 17:00 expectation; it is the service's
reported reset time, not a guarantee that a later request will be accepted.
No retry before that time, no alternate account/model, and no raised budget.
No experiment runner remained alive at the subsequent process check.

Resume the existing state through `fixcheck.py run --cell claude --klass A`,
then B and C in order, only after refreshing the actual-process D39 check,
local free-space check and `PREFLIGHT.json` within five minutes of launch.
The original attempt remains in the ledger; the next permitted attempt is a
quota recovery, not a redraw of a valid answer. Keep the candidate and frozen
bytes unchanged. The offline `fixcheck.py check` passed after this stop.
Local free space was 1,628,311,552 bytes at the check; recheck before launch.

The first offline check was denied by the outer read-only tool sandbox's
network-namespace restriction (`bwrap` / NETLINK_ROUTE). Running that same
read-only check with approved namespace access passed; no product change or
model invocation was needed.

## Storage follow-up before resume

At the subsequent 13:50 Asia/Taipei check, local free space had fallen to
approximately 1.07 GB, while no experiment runner was alive. The completed
Codex sessions contain about 1.10 GB in 26 experiment-local `cache` / `plugins`
directories. An attempt to archive only these directories to the existing
private storage area, verify their bytes/modes, preserve their original paths
with symlinks and remove the duplicate local copies was **rejected by automatic
approval review before execution**. The stated concern was unapproved data
relocation/cleanup and potentially sensitive derived cache contents.

The owner has been asked about that precise operation; no answer has been
received. No copy, symlink or cleanup occurred, and no archive/report was
created. Do not infer approval from an automatic goal continuation. The
previous tools-only relocation remains the only completed relocation. Recheck
local space before resuming Claude; cache archival remains optional and requires
that approval. Original H1, credentials, answers, workspaces and ledgers remain
unchanged. This storage preparation is not an additional experiment or a
regression result.
