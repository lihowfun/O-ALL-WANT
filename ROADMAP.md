# OAW roadmap

Updated 2026-11-12. The working plan is
[docs/plans/v2.0.1-release-path.md](docs/plans/v2.0.1-release-path.md);
work items are GitHub issues grouped by milestone.

## Now: release v2.0.1 (the only open line)

2.0.0 was never released, so v2.0.1 is the first released V2. No new experiment
starts before it ships.

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

## Next: after the release

1. Capability tasting of presentation skills, with the reusable tasting kit
   built as its runner. #13, #9
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
