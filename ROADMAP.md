# OAW roadmap

Updated 2026-11-14. The working plan is
[docs/plans/v2.0.1-release-path.md](docs/plans/v2.0.1-release-path.md);
work items are GitHub issues grouped by milestone.

## Now: v2.0.1 release line completed through review

v2.0.1 is the first V2 release; 2.0.0 was never released. Steps 1–5 are complete;
the owner's merge and tag are step 6.

1. Done: all six CI jobs (Ubuntu, macOS, Windows × Python 3.10, 3.13) green at `7504eca`, run `43510582580`. #18
2. Done: FIXCHECK disposition applied in `5c4e53b`; M1/M2/R2 reverted, M3/R1 and the path fix retained, with CI fixes through `b898e4d`. #17, #18
3. Done: the one FIXCHECK check on frozen H1 tasks; [result](https://github.com/lihowfun/O-ALL-WANT/blob/e05c4d5a9238fe3ef4529552a27ce9095ead6a3b/records/v2.0.1-experiments/FIXCHECK/RESULT.md). #17
4. Done: measured README claims, version files, upgrade notes and skill-intake SOP synchronized for release. #10, #12
5. Done: three cross-family review rounds; fixes in `b4ca559`, `73fb8f7` and `7504eca`, final review without a blocker. #11
6. Owner: merge pull request #16 and tag `v2.0.1`. #11

Disposition (2026-11-13, confirmed by the owner on 2026-11-14 as D48): M1 (session-end saving), M2 (empty-recall host guidance) and R2 (one deep
code-review round) were implemented, failed the preregistered regression
thresholds in the one FIXCHECK check, and were reverted. M3 (permission-only
pending memory), R1 (native same-family Codex review with explicit cross-family
commands) and the #18 literal-path audit fix ship.

FIXCHECK uses frozen H1 diagnostic tasks, the O arm and one counted answer per
task. All 24 rows are counted and the frozen calculator reports `fail`: two
small-change token limits (`codex/t01`, `claude/t12`) and both cells' memory
thresholds. With one answer per task, neither these failures nor the
differences measured in the other direction can be separated from run-to-run
variation; this is a regression gate, not an effectiveness verdict.
[Result record](https://github.com/lihowfun/O-ALL-WANT/blob/e05c4d5a9238fe3ef4529552a27ce9095ead6a3b/records/v2.0.1-experiments/FIXCHECK/RESULT.md) ·
[Disposition and validation](docs/validation/v2.0.1-final.md).

Release polish is integrated: explicit external-locator consent, concise doctor
output, upstream EGM guide links and the benefit/capability intake SOP (#10,
#12). Its historical Linux gate was 9/9, 685 tests, 0 skips;
[validation](docs/validation/v2.0.1-release-polish.md). FIXCHECK remains pinned
to `c2d9852`. At `7504eca`, the Linux gate passed 9/9 with 718 tests and 0 skips
on Python 3.10.12; the final six-job CI and three review rounds are complete.
Follow-ups are tracked in #21, #22 and #23; see the
[final validation](docs/validation/v2.0.1-final.md).

## Evaluation accounting (U1): next version

On 2026-11-13 the owner explicitly moved Harness2 U1 accounting work forward
(D46), on `codex/harness2-evaluation-u1`, based on release-polish 5af21f6.
It adds an optional read-only ledger/report/comparator bridge, not a model
experiment or a change to the frozen FIXCHECK candidate. Review and validation
are tracked in [U1 validation](docs/validation/harness2-u1.md); usage and evidence
limits are in [evaluation accounting](docs/EVAL_LEDGER.md). U2/U3 model-facing
changes still need separate behavior evidence. On 2026-11-14 the owner asked whether the
release carries the project's evaluation methods (D49) and then chose normal version
iteration (D50): 2.0.1 ships as reviewed, and the ledger together with the overview of
the four measurement methods in [the measurement rules](docs/EVAL_PROTOCOL.md) goes
into the next version. The 2.0.1 line is already merged into this branch.

## Next: after the release

The owner lifted the pre-release experiment restriction for EGM calibration
(#20) and the U2 comparison in D48.

1. Finish capability tasting of presentation skills and its reusable tasting kit. #13, #9
2. Verdict list (#19); independent re-judging of three earlier intake verdicts on existing data (#15).
3. EGM calibration. #20
4. The Harness² U2 comparison.
5. Release-review follow-ups. #21, #22, #23
6. 2.0.2, driven by feedback from real use.

## Parked (each with a restart condition in the plan)

Video-skill tasting (#14), EGM on large design documents, long-term use and
trigger accuracy, moving the memory store out of `.agents/`, an independent
replication of H1, and a Codex counterpart of the digestion view.

## Measured so far

Results and their limits are summarized in section 2 of the plan. Additional
runtimes, vector stores, background curators, and durable workflow
orchestration are not default dependencies.

Completed v1 work and experiments remain in CHANGELOG.md and docs/archive/.
