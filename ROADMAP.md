# OAW roadmap

Updated 2026-11-17. Work items are GitHub issues grouped by milestone. Measured results and their
limits are in section 2 of [the plan](docs/plans/v2.0.1-release-path.md).

## Direction: know quickly whether something helps

Owner, 2026-11-17 (D54): much of what OAW carries can only be judged by trying it, and the most
efficient way to learn "this helps" or "this does not help" is not ready yet. Getting it ready is the
main job of the next version. It is a way to find out, not a condition for shipping.

Where the [fast screen](docs/FAST_SCREEN.md) stands after the first new food taken through it from start
to finish on 2026-11-16
([record](https://github.com/lihowfun/O-ALL-WANT/blob/c927dc1624dab45e09956604bd14f9ecd5171add/records/fast-screens/2026-11-16-darwin-skill/RESULT.md)):

| Part | Today | Not ready |
|---|---|---|
| Rule | Version 1 (D53): YES needs at least 2 gained items and none lost; above 1.5 times the tokens it is optional, with the ratio stated | It does not say which use is screened. The same food got NO when only installed (called in 0 of 4 answers) and YES when called by name (4 of 4, 2.65 times the tokens) |
| Judge | Claude Haiku 5.5, one call per answer; about 36,000 tokens for 4 answers | A quote that drops Markdown bold fails the check and counts as a loss. That one item turned a screen to NO |
| Runner | A script written for that one food: sandbox, fresh home, answers, judge, verdict | No reusable command (#9). Tasks and checklists are written by hand |
| Cost | 149,475 to 270,853 tokens and 166 to 201 s of answering per screen; the limits are 2,000,000 tokens and 1,800 s | One answer per task, so run-to-run variation is not seen |
| Coverage | 2 foods on real answers: 1 NO at the native step, 1 YES as optional | OAW's own parts and the whole kit have not been through it |

## Next version, in order

1. One command for a fast screen: make the one-off runner the reusable tasting kit. #9
2. Fix what the first screen exposed: the quote check with Markdown emphasis; say which use is screened
   (only installed, or called by name); decide whether gains must come from more than one task.
3. Take OAW's own parts through it one at a time, to learn what each adds and what it costs: memory, the
   fresh-context review, the code map (#28), EGM when switched on. A screen informs; removing a part
   stays the owner's decision.
4. The whole kit against no kit, by the same method, once 1 to 3 work. H1 measured this once on a
   pre-release build: no conclusion, the two hosts in opposite directions, 1.92 and 2.58 times the tokens.
5. Smaller items: verdict list sync (#19); memory ordering, catalogue lock checks, Python 3.11 and 3.12
   in CI (#21, #22, #23); Windows concurrent writers (#26).
6. The next version is cut when enough has accumulated (D50).

## Settled

- EGM stays, with its switch (D52, D55). The default `auto` gives a deep task one fresh-context review.
  The user turns EGM on when they want a stronger review: `python3 scripts/oaw_mode.py egm on`, or
  `/egm-review` for one run. Nothing triggers it automatically. #27
- The code map stays (D52). `code_index.py changes` compares it with an earlier export and the skill says
  when to draw it again (#28, first half).
- Evaluation ledger and the overview of the four measurement methods are on `main`
  ([accounting](docs/EVAL_LEDGER.md), [measurement rules](docs/EVAL_PROTOCOL.md); D46, D49, D50).
- Closed without a change to OAW: the EGM calibration at no conclusion (#20), the minimal-change card
  not absorbed (#24), the presentation tasting stopped before a candidate comparison (#13), three earlier
  verdicts re-judged on existing data (#15). TokenEconomizer was removed from the optional list by owner
  decision (D52).

## Parked (each with a restart condition in the plan)

Video-skill tasting (#14), EGM on large design documents, long-term use and trigger accuracy, moving
the memory store out of `.agents/`, and a Codex counterpart of the digestion view.

## Released: v2.0.1

The first V2 release; 2.0.0 was never released. Merged as `dd91780` and tagged `v2.0.1` on 2026-11-14
(UTC), with all six CI jobs green (Ubuntu, macOS, Windows × Python 3.10, 3.13) and three cross-family
review rounds. Of the five fixes tried after H1, three failed their regression thresholds and were
reverted (session-end saving, empty-recall guidance, one deep code-review round); two ship
(permission-only pending memory, native same-family Codex review). What shipped and how it was checked:
[final validation](docs/validation/v2.0.1-final.md) and [CHANGELOG](CHANGELOG.md). Later work is listed
under Unreleased there.

Additional runtimes, vector stores, background curators and durable workflow orchestration are not
default dependencies. Completed v1 work and experiments remain in CHANGELOG.md and docs/archive/.
