# OAW roadmap

Updated 2026-11-13. The working plan is
[docs/plans/v2.0.1-release-path.md](docs/plans/v2.0.1-release-path.md);
work items are GitHub issues grouped by milestone.

## Now: release v2.0.1

2.0.0 was never released, so v2.0.1 is the first released V2. No new experiment
starts before it ships. One trial was already under way when this plan was
written and continues in its own session without gating the release: the
capability tasting of presentation skills (#13, #9).

1. Cross-platform CI on the release pull request (Linux, macOS, Windows). It
   needs the pull request's base changed to `main`, which waits for the owner. #18
2. Fix the five defects traced by the installed-versus-native trial (H1):
   when notes are saved, what happens when recall is empty, memory writes in the
   Codex sandbox, the Codex review step, and the number of deep review rounds. #17
3. One check of those fixes on the frozen H1 tasks. #17
4. Documentation: measured claims in the README, version files, upgrade notes,
   the skill-intake SOP. #10, #12
5. One full cross-family review, at most three rounds. #11
6. The owner merges the release pull request and tags `v2.0.1`. #11

Implementation update (2026-11-13): the five fixes and the visible path-audit repair
are implemented on `codex/v2.0.1-release-fixes`. Linux offline gate: 9/9,
677 tests, 0 skips; native Codex sandbox pending-memory probe passed.
[Validation and remaining gates](docs/validation/v2.0.1-release-fixes.md).
FIXCHECK, cross-platform CI, final release review and owner merge are still pending.

Release polish is being prepared separately on `codex/v2.0.1-release-polish`:
explicit external-locator consent, concise doctor output, upstream EGM guide links
and the benefit/capability intake SOP (#10, #12). FIXCHECK remains pinned to
`c2d9852`; integrate this work only after its disposition, then validate the final
release commit. Linux validation: 9/9 gate, 685 tests, 0 skips; independent code
review findings closed. [Validation](docs/validation/v2.0.1-release-polish.md).
The version has not been bumped.

## Evaluation accounting: owner-authorized U1 work

On 2026-11-13 the owner explicitly moved Harness2 U1 accounting work forward
(D46), on `codex/harness2-evaluation-u1`, based on release-polish 5af21f6.
It adds an optional read-only ledger/report/comparator bridge, not a model
experiment or a change to the frozen FIXCHECK candidate. Review and validation
are tracked in [U1 validation](docs/validation/harness2-u1.md); usage and evidence
limits are in [evaluation accounting](docs/EVAL_LEDGER.md). U2/U3 model-facing
changes still need separate behavior evidence. Release integration is pending.

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
