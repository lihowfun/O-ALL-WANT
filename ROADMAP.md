# OAW roadmap

Updated 2026-11-14. The working plan is
[docs/plans/v2.0.1-release-path.md](docs/plans/v2.0.1-release-path.md);
work items are GitHub issues grouped by milestone.

## Now: release v2.0.1 (the only open line)

2.0.0 was never released, so v2.0.1 is the first released V2. No new experiment
starts before it ships. One trial was already under way when this plan was
written and continues in its own session without gating the release: the
capability tasting of presentation skills (#13, #9).

1. Cross-platform CI on the release pull request (Linux, macOS, Windows). The
   pull request's base was changed to `main` on 2026-11-14 with the owner's
   approval, so every push now runs the six jobs. #18
2. Apply the preregistered FIXCHECK disposition: revert M1/M2/R2; retain M3/R1
   and the #18 path fix, together with release polish. #17
3. The one FIXCHECK check on the frozen H1 tasks is complete: [result](https://github.com/lihowfun/O-ALL-WANT/blob/e05c4d5a9238fe3ef4529552a27ce9095ead6a3b/records/v2.0.1-experiments/FIXCHECK/RESULT.md). #17
4. Documentation: measured claims in the README, version files, upgrade notes,
   the skill-intake SOP. #10, #12
5. One full cross-family review, at most three rounds. #11
6. The owner merges the release pull request and tags `v2.0.1`. #11

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
to `c2d9852`. Final six-job platform/Python CI, cross-family release review and owner
merge remain pending. The version stays 2.0.0 proposed.

## Next: after the release

1. Finish the capability tasting of presentation skills if it is still
   running, with the reusable tasting kit built as its runner. #13, #9
2. Independent re-judging of three earlier intake verdicts on the existing
   data. #15
3. 2.0.2, driven by feedback from real use.

## Parked (each with a restart condition in the plan)

Video-skill tasting (#14), EGM on large design documents, long-term use and
trigger accuracy, moving the memory store out of `.agents/`, an independent
replication of H1, and a Codex counterpart of the digestion view.

## Measured so far

Results and their limits are summarized in section 2 of the plan. Additional
runtimes, vector stores, background curators, and durable workflow
orchestration are not default dependencies.

Completed v1 work and experiments remain in CHANGELOG.md and docs/archive/.
